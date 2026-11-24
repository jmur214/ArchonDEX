"""T-416 locks (2026-11-20, hardened 2026-11-24): the daily options snapshot archive judges a row
by a USABLE value, fails closed against what it EXPECTED, and never loses a day quietly.

The defect this guards against is the 2026-11-19 Kalshi one: a fail-closed check that asked
whether a price field was PRESENT passed $0 bids and $1.00 placeholder asks as "priced" for
five months while the freshness gate said OK. An independent review of the first build then
found the same shape again (144 pulled XSP quotes passed because a morning trade stood in for a
bid) and nine ways to lose or mislabel a day that cannot be recaptured; each has a lock here,
marked R1-R9.

The network is stubbed everywhere (the two HTTP-level tests use a local socket), every write
goes to tmp_path, the wall clock is pinned for every test, and no key is ever printed.
"""
from __future__ import annotations

import ast
import http.server
import json
import os
import socket
import stat
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
import requests

import scripts.archive_options_snapshots as m

REPO = Path(__file__).resolve().parent.parent
SNAP = date(2026, 11, 20)                                    # a Friday
KEY, SECRET = "k-SENTINEL-KEY-7731", "s-SENTINEL-SECRET-9912"


def et(d: date, hour: int = 18, minute: int = 30) -> datetime:
    """A moment in New York, as the UTC datetime the archiver takes."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=m.ET).astimezone(timezone.utc)


NOW = et(SNAP)                                               # 18:30 ET, the launchd time


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may depend on the day it runs (R2: the first build's verifier test asserted a
    failure that only happens on a trading day, so it would have broken on Thanksgiving)."""
    monkeypatch.setattr(m, "_utcnow", lambda: NOW)


# ───────────────────────────── a fake Alpaca ─────────────────────────────

class FakeResp:
    def __init__(self, status: int = 200, payload: Any = None,
                 headers: Optional[dict[str, str]] = None, text: Optional[str] = None) -> None:
        self.status_code = status
        self._payload = payload
        self.headers = headers or {"X-RateLimit-Limit": "200", "X-RateLimit-Remaining": "199"}
        self.text = text if text is not None else json.dumps(payload)

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON")
        return self._payload


def occ(root: str, exp: date, cp: str, k: float) -> str:
    return f"{root}{exp:%y%m%d}{cp}{int(round(k * 1000)):08d}"


def snapshot(k: float, cp: str, spot: float, session: date = SNAP) -> dict[str, Any]:
    """A usable contract: intrinsic + about $1 (varying by contract, as real quotes do), stamped
    at that session's 15:59:30 ET."""
    bid = max(spot - k if cp == "C" else k - spot, 0.0) + 1.0 + 0.01 * (k % 50) + 0.6 * (cp == "P")
    stamp = et(session, 15, 59).strftime("%Y-%m-%dT%H:%M:30.123456789Z")
    return {"latestQuote": {"bp": bid, "ap": bid + 0.1, "bs": 10, "as": 12, "bx": "C", "ax": "M",
                            "c": "A", "t": stamp},
            "latestTrade": {"p": bid + 0.05, "s": 3, "x": "C", "c": "I",
                            "t": et(session, 15, 10).strftime("%Y-%m-%dT%H:%M:00Z")},
            "impliedVolatility": 0.25,
            "greeks": {"delta": 0.5 if cp == "C" else -0.5, "gamma": 0.01, "theta": -0.2,
                       "vega": 0.3, "rho": 0.05},
            "dailyBar": {"o": 1, "h": 1.2, "l": 0.9, "c": 1.05, "v": 100, "n": 7,
                         "t": f"{session}T05:00:00Z"}}


def quoted(**over: Any) -> Callable[..., dict[str, Any]]:
    """A snapshot function whose latestQuote is overridden (``as_`` spells the JSON key "as")."""
    over = {("as" if k == "as_" else k): v for k, v in over.items()}

    def make(u: str, k: float, cp: str, spot: float, session: date) -> dict[str, Any]:
        s = snapshot(k, cp, spot, session)
        s["latestQuote"].update(over)
        return s
    return make


WIPED = dict(bp=0.0, ap=0.0, bs=0, as_=0, bx="?", ax="?")      # the 2026-11-20 XSP close shape


@dataclass
class Market:
    """A requests.Session stand-in that serves the four endpoints for any session date."""
    spots: dict[str, float] = field(default_factory=lambda: {"SPY": 700.0, "AAPL": 340.0})
    session: date = SNAP
    snap: Callable[..., dict[str, Any]] = lambda u, k, cp, spot, d: snapshot(k, cp, spot, d)
    last: dict[str, float] = field(default_factory=dict)       # after-hours last trade
    calendar: Any = None                    # None -> rule days; else the payload / FakeResp
    closes: dict[date, str] = field(default_factory=dict)
    fail: dict[str, Any] = field(default_factory=dict)         # underlying -> FakeResp | Exception
    hook: Optional[Callable[[str, dict[str, Any]], Any]] = None  # (path, params) -> FakeResp | None
    extra_root: str = ""                    # also list and serve adjusted contracts of this root
    page_size: int = 0
    queue: dict[str, list[Any]] = field(default_factory=dict)  # path -> answers used first
    calls: list[tuple[str, dict[str, Any], dict[str, str]]] = field(default_factory=list)
    on_call: Callable[[], None] = lambda: None
    redirects_allowed: list[Any] = field(default_factory=list)

    def strikes(self, spot: float) -> list[float]:
        return [float(round(spot * f)) for f in (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)]

    def expiries(self, e0: date, e1: date) -> list[date]:
        days = [e0 + timedelta(days=i) for i in range((e1 - e0).days + 1)]
        return [d for d in days if m.is_trading_day_rules(d)]

    def spot(self, u: str) -> float:
        return self.spots["SPY"] if u == "XSP" else self.spots[u]

    def get(self, url: str, headers: Optional[dict[str, str]] = None,
            params: Optional[dict[str, Any]] = None, timeout: Any = None,
            allow_redirects: Any = None) -> Any:
        params = dict(params or {})
        self.calls.append((url, params, dict(headers or {})))
        self.redirects_allowed.append(allow_redirects)
        self.on_call()
        path = urlparse(url).path
        if self.queue.get(path):
            return self._answer(self.queue[path].pop(0))
        if self.hook is not None and (out := self.hook(path, params)) is not None:
            return self._answer(out)
        if path == "/v2/calendar":
            if isinstance(self.calendar, FakeResp):
                return self.calendar
            if self.calendar is not None:
                return FakeResp(payload=self.calendar)
            return FakeResp(payload=[
                {"date": d.isoformat(), "open": "09:30", "close": self.closes.get(d, "16:00")}
                for d in self.expiries(date.fromisoformat(params["start"]),
                                       date.fromisoformat(params["end"]))])
        if path == "/v2/stocks/snapshots":
            return FakeResp(payload={
                s: {"latestTrade": {"p": self.last.get(s, self.spots[s]),
                                    "t": et(self.session, 18, 14).strftime("%Y-%m-%dT%H:%M:00Z")},
                    "dailyBar": {"c": self.spots[s], "t": f"{self.session}T05:00:00Z"}}
                for s in params["symbols"].split(",") if s in self.spots})
        if path == "/v2/options/contracts":
            u = params["underlying_symbols"]
            if u in self.fail:
                return self._answer(self.fail[u])
            lo, hi = float(params["strike_price_gte"]), float(params["strike_price_lte"])
            exps = self.expiries(date.fromisoformat(params["expiration_date_gte"]),
                                 date.fromisoformat(params["expiration_date_lte"]))
            return FakeResp(payload={"next_page_token": None, "option_contracts": [
                {"symbol": occ(root, e, cp, k), "root_symbol": root, "underlying_symbol": u,
                 "expiration_date": e.isoformat(), "style": "european" if u == "XSP" else "american",
                 "open_interest": "1234", "open_interest_date": "2026-11-18"}
                for root in filter(None, (u, self.extra_root and u + self.extra_root))
                for e in exps for k in self.strikes(self.spot(u)) if lo <= k <= hi for cp in "CP"]})
        if path.startswith("/v1beta1/options/snapshots/"):
            u = path.rsplit("/", 1)[-1]
            if u in self.fail:
                return self._answer(self.fail[u])
            e = date.fromisoformat(params["expiration_date"])
            return self.page(self.chain(u, e), params)
        return FakeResp(404, {"message": "not found"})

    def chain(self, u: str, e: date) -> dict[str, Any]:
        out = {occ(root, e, cp, k): self.snap(u, k, cp, self.spot(u), self.session)
               for root in filter(None, (u, self.extra_root and u + self.extra_root))
               for k in self.strikes(self.spot(u)) for cp in "CP"}
        for s in out.values():
            if u == "XSP" and isinstance(s, dict):   # Alpaca computes no IV for index options
                s.pop("impliedVolatility", None)
                s.pop("greeks", None)
        return out

    def page(self, snaps: dict[str, Any], params: dict[str, Any]) -> FakeResp:
        items = sorted(snaps.items())
        size = self.page_size or len(items) or 1
        off = int(params.get("page_token") or 0)
        nxt = str(off + size) if off + size < len(items) else None
        return FakeResp(payload={"snapshots": dict(items[off:off + size]), "next_page_token": nxt})

    @staticmethod
    def _answer(out: Any) -> Any:
        if isinstance(out, Exception):
            raise out
        return out


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


def client_for(market: Market, clock: Optional[FakeClock] = None, **kw: Any) -> m.AlpacaReadClient:
    clock = clock or FakeClock()
    return m.AlpacaReadClient(KEY, SECRET, session=market, sleep=clock.sleep,  # type: ignore[arg-type]
                              clock=clock.clock, **kw)


def cfg_for(symbols: tuple[str, ...] = ("SPY", "AAPL", "XSP"), floor: float = 0.9,
            min_real: int = 3, min_share: float = 0.0, required: tuple[str, ...] = (),
            budget: float = 600.0, gaps: tuple[date, ...] = ()) -> m.ArchiveConfig:
    specs = tuple(m.UnderlyingSpec(s, "index", "SPY", False, s in required) if s == "XSP"
                  else m.UnderlyingSpec(s, "stock", None, True, s in required) for s in symbols)
    return m.ArchiveConfig(specs, "indicative", 0.20, 4, 2, 100, floor, min_real, budget, "md5",
                           min_share, 0.9, frozenset(gaps))


ALL = 3 * 6 * 7 * 2                    # underlyings x expiries x strikes x types


def run(tmp_path: Path, market: Market, cfg: Optional[m.ArchiveConfig] = None,
        now: datetime = NOW, slot: str = "eod") -> m.RunOutcome:
    return m.run_archive(cfg or cfg_for(), client_for(market), tmp_path, now, slot)


def runs(tmp_path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (tmp_path / m.RUN_LOG_NAME).read_text().splitlines()]


def stored(tmp_path: Path, session: date = SNAP) -> pd.DataFrame:
    return pd.read_parquet(m.day_path(tmp_path, session))


def day_files(tmp_path: Path) -> list[str]:
    return sorted(p.name for p in tmp_path.glob("options_snapshot_*.parquet"))


def capture(tmp_path: Path, session: date, cfg: Optional[m.ArchiveConfig] = None,
            snap: Optional[Callable[..., dict[str, Any]]] = None) -> m.RunOutcome:
    """A normal 18:30 ET run for ``session``."""
    mk = Market(session=session)
    if snap is not None:
        mk.snap = snap
    return run(tmp_path, mk, cfg, et(session))


def quote_frame(**over: Any) -> pd.DataFrame:
    """One fully real row (an at-the-money call), with column overrides."""
    row: dict[str, Any] = dict(
        snap_date="2026-11-20", underlying="SPY", option_type="C", strike=700.0, ref_low=700.0,
        ref_high=700.0, bid=1.0, ask=1.1, bid_size=10, ask_size=12, iv=0.25,
        quote_ts=pd.Timestamp("2026-11-20T20:59:30.1Z"),
        last_price=1.05, last_ts=pd.Timestamp("2026-11-20T20:10:00Z"))
    row.update(over)
    return pd.DataFrame({k: pd.Series([v], dtype=object) if isinstance(v, (str, bool, list))
                         else [v] for k, v in row.items()})


def is_real(no_iv: tuple[str, ...] = (), **over: Any) -> bool:
    return bool(m.real_quote_mask(quote_frame(**over), no_iv).iloc[0])


# ───────────────────────────── 1. field mapping ─────────────────────────────

def test_snapshot_fields_map_to_the_stored_columns() -> None:
    sym = occ("SPY", date(2026, 12, 18), "P", 650.5)
    s = snapshot(650.5, "P", 650.5)
    s["latestQuote"].update(bp=1.0, ap=1.1)
    s["latestTrade"]["p"] = 1.05
    df, stats = m.snapshots_frame({sym: s}, SNAP)
    r = df.iloc[0]
    assert not any(stats.values())
    assert (r.contract, r.root, r.expiry, r.option_type, r.strike) == (
        sym, "SPY", date(2026, 12, 18), "P", 650.5)
    assert (r.bid, r.ask, r.bid_size, r.ask_size) == (1.0, 1.1, 10, 12)
    assert (r.bid_exchange, r.ask_exchange, r.quote_condition) == ("C", "M", "A")
    assert (r.last_price, r.last_size, r.last_exchange, r.last_condition) == (1.05, 3, "C", "I")
    assert (r.iv, r.delta, r.gamma, r.theta, r.vega, r.rho) == (0.25, -0.5, 0.01, -0.2, 0.3, 0.05)
    assert (r.day_volume, r.day_trade_count) == (100, 7)
    assert r.quote_ts == pd.Timestamp("2026-11-20T20:59:30.123456Z")   # ns truncated to us
    assert r.last_ts == pd.Timestamp("2026-11-20T20:10:00Z")


def test_both_timestamp_shapes_parse_in_both_orders_and_garbage_is_counted() -> None:
    a, b = "2026-11-20T20:10:00Z", "2026-11-20T20:59:30.123456789Z"
    for order in ([a, b], [b, a]):
        out, bad = m._parse_ts(pd.Series(order))
        assert out.notna().all() and bad == 0, order
    out, bad = m._parse_ts(pd.Series([b, "yesterday-ish", None, 1732000000, [1]], dtype=object))
    assert bad == 3 and out.isna().tolist() == [False, True, True, True, True]
    long = pd.Series([a] * 80 + [[1]], dtype=object)     # > 50 rows: pandas hashes the values
    out, bad = m._parse_ts(long)
    assert bad == 1 and out.notna().sum() == 80


def test_a_stale_daily_bar_is_not_todays_volume() -> None:
    s = snapshot(700, "C", 700)
    s["dailyBar"]["t"] = "2026-10-16T04:00:00Z"        # the SPX-root shape seen live
    df, _ = m.snapshots_frame({occ("SPY", date(2026, 12, 18), "C", 700): s}, SNAP)
    assert pd.isna(df.iloc[0].day_volume) and pd.isna(df.iloc[0].day_trade_count)


def test_occ_parse_handles_adjusted_roots_fractional_strikes_and_garbage() -> None:
    p = m.parse_occ(pd.Series(["XSP261211C00687500", "AAPL1261218P00150000", "NOT-A-SYMBOL"]))
    assert p.root.tolist()[:2] == ["XSP", "AAPL1"] and pd.isna(p.root.iloc[2])
    assert p.strike.tolist()[:2] == [687.5, 150.0]
    assert p.expiry.tolist()[:2] == [date(2026, 12, 11), date(2026, 12, 18)]


def test_contract_listing_maps_open_interest_and_style() -> None:
    base = {"root_symbol": "SPY", "expiration_date": "2026-12-18", "style": "american"}
    c = m.contracts_frame([
        {"symbol": "SPY261218C00700000", "open_interest": "2509",
         "open_interest_date": "2026-11-18", **base},
        {"symbol": "SPY261218P00700000", "open_interest": None, "open_interest_date": None, **base},
        None, 7, {"symbol": "X"}])                    # odd entries are dropped, not fatal
    assert c.open_interest.tolist()[0] == 2509 and pd.isna(c.open_interest.iloc[1])
    assert c.open_interest_date.iloc[0] == date(2026, 11, 18)
    assert c["style"].tolist() == ["american", "american"]


# ───────────────────────────── 2. the real-quote rule, v2 (R4) ─────────────────────────────

def test_a_normal_two_sided_quote_is_real() -> None:
    assert is_real()


def test_a_ZERO_quote_row_is_not_real() -> None:
    assert not is_real(bid=0.0, ask=0.0, bid_size=0, ask_size=0)


def test_a_placeholder_ask_with_no_bid_is_not_real() -> None:
    assert not is_real(bid=0.0, ask=1.00, bid_size=0)


def test_R4_a_same_session_TRADE_does_not_stand_in_for_a_bid() -> None:
    """144 pulled XSP quotes passed rule v1 this way: bid 0, size 0, ask ~3.7x a morning trade."""
    assert not is_real(no_iv=("XSP",), underlying="XSP", iv=np.nan, bid=0.0, bid_size=0, ask=4.0,
                       last_price=1.05)
    assert not is_real(bid=0.0, ask=0.05, last_price=0.03)


@pytest.mark.parametrize("side", ["bid_size", "ask_size"])
@pytest.mark.parametrize("value", [0, np.nan, float("inf"), 3e9])
def test_R4_a_side_without_size_is_not_real(side: str, value: float) -> None:
    assert not is_real(**{side: value})


def test_R4_constant_placeholders_fail_on_intrinsic_or_spread() -> None:
    assert not is_real(strike=560.0, bid=1.0, ask=1.0)                  # call worth >= 140
    assert not is_real(option_type="P", strike=840.0, bid=1.0, ask=1.0)
    assert not is_real(bid=0.01, ask=79.0)                              # the wide placeholder
    assert is_real(strike=560.0, bid=139.0, ask=140.5)


def test_R4_intrinsic_slack_is_two_percent_and_uses_the_lenient_reference() -> None:
    deep = dict(strike=560.0, bid=125.9)                                # intrinsic 140, slack 14
    assert is_real(ask=126.5, **deep) and not is_real(ask=125.95, **{**deep, "bid": 125.0})
    # after-hours +25 %: the quote is from the close, so the CLOSE sets a call's intrinsic
    assert is_real(strike=100.0, ref_low=100.0, ref_high=125.0, bid=3.0, ask=3.2)
    assert is_real(option_type="P", strike=100.0, ref_low=75.0, ref_high=100.0, bid=3.0, ask=3.2)


def test_R4_the_spread_leg_is_ten_cents_or_half_the_mid() -> None:
    assert is_real(bid=0.01, ask=0.11) and not is_real(bid=0.01, ask=0.13)
    assert is_real(bid=3.0, ask=5.0) and not is_real(bid=3.0, ask=5.1)  # 2/4 = 50 %, 2.1/4.05


@pytest.mark.parametrize("bad", [np.nan, 0.0, -0.1, np.inf, 1e-9, 0.009, 5.01, 999.0, True, "abc",
                                 None, [0.3]])
def test_R4_implied_vol_must_be_between_1_and_500_percent(bad: Any) -> None:
    assert not is_real(iv=bad)
    assert is_real(no_iv=("XSP",), underlying="XSP", iv=np.nan)
    assert not is_real(no_iv=("XSP",), underlying="SPY", iv=np.nan)


def test_iv_bounds_are_inclusive_and_numeric_text_is_a_number() -> None:
    assert is_real(iv=0.01) and is_real(iv=5.0) and is_real(iv="0.3")


def test_a_STALE_quote_is_not_real_even_with_a_bid() -> None:
    assert not is_real(quote_ts=pd.Timestamp("2026-11-19T20:59:59.5Z"))


def test_the_session_is_the_ET_day_not_the_UTC_day() -> None:
    assert is_real(quote_ts=pd.Timestamp("2026-11-21T00:30:00Z"))      # 19:30 ET on 11-20
    assert not is_real(quote_ts=pd.Timestamp("2026-11-20T04:30:00Z"))  # 23:30 ET on 11-19


def test_a_missing_quote_time_or_reference_is_not_real() -> None:
    assert not is_real(quote_ts=pd.NaT)
    assert not is_real(ref_high=np.nan)


def test_crossed_missing_and_out_of_bound_asks_are_not_real() -> None:
    assert not is_real(bid=2.0, ask=1.5)                               # crossed
    assert not is_real(ask=np.nan)                                     # one-sided bid
    assert not is_real(bid=700.0, ask=700.01)                          # call > S
    assert not is_real(option_type="P", strike=650.0, bid=650.0, ask=650.01)    # put > K


def test_the_call_bound_is_the_underlying_not_the_strike() -> None:
    assert is_real(strike=100.0, bid=600.0, ask=601.0)                 # deep ITM: ask >> strike
    assert not is_real(strike=900.0, bid=1.0, ask=1.1, ref_high=1.05, ref_low=1.05)


def test_the_rule_is_vectorized_over_mixed_rows() -> None:
    df = pd.concat([quote_frame(), quote_frame(bid=0.0), quote_frame(iv=np.nan)],
                   ignore_index=True)
    assert m.real_quote_mask(df).tolist() == [True, False, False]
    assert not m.real_quote_mask(df.iloc[0:0]).any()


# ───────────────────────────── 3. calendar, session and slot (R2, R5) ──────────────────────

def test_rule_calendar_matches_the_paper_fallback_for_2026_and_known_edges() -> None:
    from paper_trader.market_calendar import _FALLBACK_HOLIDAYS_2026
    assert m.nyse_holidays(2026) == frozenset(_FALLBACK_HOLIDAYS_2026)
    assert date(2027, 3, 26) in m.nyse_holidays(2027)          # Good Friday 2027
    assert date(2027, 12, 24) in m.nyse_holidays(2027)         # Christmas on a Saturday
    assert date(2021, 12, 31) not in m.nyse_holidays(2021)     # Sat New Year: no Friday close
    assert date(2021, 6, 18) not in m.nyse_holidays(2021)      # no Juneteenth before 2022
    assert m.previous_trading_day_rules(date(2026, 11, 23)) == date(2026, 11, 20)
    assert m.previous_trading_day_rules(date(2026, 11, 27)) == date(2026, 11, 25)


def _dailies(d0: date, n: int) -> list[date]:
    return [d0 + timedelta(days=i) for i in range(n) if m.is_trading_day_rules(d0 + timedelta(days=i))]


def test_expiry_rule_takes_fridays_then_third_friday_monthlies() -> None:
    got = m.select_expiries(_dailies(SNAP, 101), SNAP, 4, 2)
    assert got == [date(2026, 11, 27), date(2026, 12, 4), date(2026, 12, 11),
                   date(2026, 12, 18), date(2027, 1, 15), date(2027, 2, 19)]


def test_the_third_friday_window_is_day_15_to_21() -> None:
    """August 2026: the third Friday is the 21st and the second is the 14th."""
    d0 = date(2026, 7, 27)
    assert m.select_expiries(_dailies(d0, 40), d0, 1, 1) == [date(2026, 7, 31), date(2026, 8, 21)]


def test_expiry_rule_moves_a_holiday_friday_expiry_to_thursday() -> None:
    d0 = date(2026, 6, 1)                     # Juneteenth 2026 is the third Friday of June
    dailies = _dailies(d0, 120)
    got = m.select_expiries(dailies, d0, 4, 1)
    assert date(2026, 6, 18) in got and date(2026, 6, 19) not in got
    assert m.select_expiries(dailies, d0, 2, 1)[-1] == date(2026, 6, 18)   # it is the monthly


def test_expiry_rule_with_nothing_listed_returns_nothing() -> None:
    assert m.select_expiries([SNAP], SNAP, 4, 2) == []


@pytest.mark.parametrize("payload", [[], [1], [None], {"a": 1}, "x", [{"date": "soon"}],
                                     [{"date": "2026-11-20"}]])
def test_R5_an_empty_or_odd_calendar_answer_is_never_a_closure(tmp_path: Path, payload: Any) -> None:
    out = run(tmp_path, Market(calendar=payload))
    assert out.status == "OK", out.message
    assert runs(tmp_path)[-1]["calendar"]["source"] == "rules"


@pytest.mark.parametrize("status", [404, 401, 500])
def test_R5_a_failing_calendar_falls_back_to_the_rules(tmp_path: Path, status: int) -> None:
    assert run(tmp_path, Market(calendar=FakeResp(status, {"message": "no"}))).status == "OK"


def test_R5_alpaca_omitting_an_open_day_is_LOUD_and_not_skipped(tmp_path: Path,
                                                               capsys: pytest.CaptureFixture[str]) -> None:
    mk = Market(calendar=[{"date": d.isoformat(), "close": "16:00"} for d in
                          _dailies(SNAP - timedelta(days=7), 15) if d != SNAP])
    out = run(tmp_path, mk)
    assert out.status == "OK" and "CALENDAR DISAGREEMENT 2026-11-20" in out.message
    assert "CALENDAR DISAGREEMENT" in capsys.readouterr().out and len(stored(tmp_path)) == ALL


def test_R5_alpaca_listing_a_rule_closed_day_is_captured_too(tmp_path: Path) -> None:
    sat = date(2026, 11, 21)
    days = sorted({*_dailies(SNAP - timedelta(days=7), 15), sat})
    out = run(tmp_path, Market(session=sat, calendar=[{"date": d.isoformat(), "close": "16:00"}
                                                      for d in days]), now=et(sat))
    assert out.status == "OK" and "Alpaca lists it" in out.message and len(stored(tmp_path, sat)) == ALL


def test_a_closed_day_after_a_good_capture_SKIPS_with_only_the_calendar_call(tmp_path: Path) -> None:
    capture(tmp_path, SNAP)
    mk = Market()
    out = run(tmp_path, mk, now=et(date(2026, 11, 21)))
    assert (out.exit_code, out.status) == (0, "SKIP")
    assert [urlparse(c[0]).path for c in mk.calls] == ["/v2/calendar"]
    assert runs(tmp_path)[-1]["status"] == "SKIP"


@pytest.mark.parametrize("when", [et(date(2026, 11, 21), 0, 30), et(date(2026, 11, 21), 18, 30),
                                  et(date(2026, 11, 22), 12, 0), et(date(2026, 11, 23), 8, 0)])
def test_a_late_wake_captures_the_session_that_was_missed(tmp_path: Path, when: datetime) -> None:
    """After midnight, on the weekend or before Monday's open, Friday's quotes are still served."""
    out = run(tmp_path, Market(), now=when)
    assert out.status == "OK" and day_files(tmp_path) == ["options_snapshot_2026-11-20.parquet"]
    assert set(stored(tmp_path).snap_date) == {"2026-11-20"} and stored(tmp_path).real_quote.all()


def test_a_slot_that_does_not_match_the_clock_is_REFUSED(tmp_path: Path) -> None:
    for slot, when in (("eod", et(SNAP, 12, 0)), ("near_close", et(SNAP, 18, 30)),
                       ("near_close", et(SNAP, 8, 0))):
        with pytest.raises(m.SlotError):
            run(tmp_path, Market(), now=when, slot=slot)
        assert runs(tmp_path)[-1]["status"] == "REFUSED" and not day_files(tmp_path)


def test_a_half_day_is_eod_after_its_own_close(tmp_path: Path) -> None:
    half = date(2026, 11, 27)
    mk = Market(session=half, closes={half: "13:00"})
    mk.snap = quoted(t=et(half, 12, 59).strftime("%Y-%m-%dT%H:%M:00Z"))
    assert run(tmp_path, mk, now=et(half, 14, 0)).status == "OK"
    with pytest.raises(m.SlotError):
        run(tmp_path, Market(session=half, closes={half: "13:00"}), now=et(half, 12, 0))


def test_near_close_and_eod_rows_do_not_overwrite_each_other(tmp_path: Path) -> None:
    assert run(tmp_path, Market(), now=et(SNAP, 15, 45), slot="near_close").status == "OK"
    assert run(tmp_path, Market(snap=quoted(bx="Z"))).status == "OK"
    df = stored(tmp_path)
    assert df.slot.value_counts().to_dict() == {"near_close": ALL, "eod": ALL}
    assert set(df[df.slot == "eod"].bid_exchange) == {"Z"}
    assert set(df[df.slot == "near_close"].bid_exchange) == {"C"}


# ───────────────────────────── 4. judge: what was EXPECTED (R3) ─────────────────────────────

def _rows(sym: str, n: int, real: bool, n_exp: int = 6, tag: str = "") -> pd.DataFrame:
    exps = [date(2026, 12, 4) + timedelta(days=7 * i) for i in range(n_exp)]
    return pd.DataFrame({
        "snap_date": "2026-11-20", "slot": "eod", "underlying": sym, "real_quote": real,
        "contract": [f"{tag}{sym}-{i}" for i in range(n)], "snap_ts": pd.Timestamp(NOW),
        "bid": 1.0 + 0.01 * np.arange(n), "ask": 1.1 + 0.01 * np.arange(n),
        "expiry": [exps[i % n_exp] for i in range(n)], "option_type": "C",
        "strike": np.arange(n, dtype=float), "listed": True})


def test_judge_fails_closed_on_zero_real_and_writes_nothing() -> None:
    v = m.judge(_rows("SPY", 50, False), cfg_for(("SPY",)), {"SPY": 50})
    assert (v.status, v.write, v.n_real) == ("FAILED", False, 0) and "nothing written" in v.message


def test_judge_fails_on_thin_coverage_but_keeps_the_rows() -> None:
    df = pd.concat([_rows("SPY", 12, True), _rows("AAPL", 2, True)])
    v = m.judge(df, cfg_for(), {"SPY": 12, "AAPL": 2, "XSP": 12})
    assert (v.status, v.write) == ("FAILED", True)
    assert v.covered == ["SPY"] and v.missing == ["AAPL", "XSP"] and "coverage 1/3" in v.message


def test_a_name_lost_inside_the_floor_is_NAMED_on_the_OK_line() -> None:
    names = tuple(f"S{i:02d}" for i in range(19))
    df = pd.concat([_rows(n, 12, True) for n in names])
    v = m.judge(df, cfg_for((*names, "DEAD")), {n: 12 for n in names})
    assert v.status == "OK" and "NOT COVERED: DEAD [real 0/0, returned 0/0" in v.message


def test_a_REQUIRED_underlying_not_covered_fails_even_above_the_floor() -> None:
    names = tuple(f"S{i:02d}" for i in range(19))
    df = pd.concat([_rows(n, 12, True) for n in names] + [_rows("XSP", 12, False)])
    expected = {**{n: 12 for n in names}, "XSP": 12}
    assert m.judge(df, cfg_for((*names, "XSP")), expected).status == "OK"      # 19/20 = 95 %
    v = m.judge(df, cfg_for((*names, "XSP"), required=("XSP",)), expected)
    assert v.status == "FAILED" and "required underlying not covered: XSP" in v.message


def test_a_MOSTLY_JUNK_underlying_is_not_covered_under_the_share_floor() -> None:
    df = pd.concat([_rows("SPY", 50, True), _rows("AAPL", 12, True),
                    _rows("AAPL", 88, False, tag="J")])
    expected = {"SPY": 50, "AAPL": 100}
    assert m.judge(df, cfg_for(("SPY", "AAPL"), min_real=10), expected).status == "OK"
    v = m.judge(df, cfg_for(("SPY", "AAPL"), min_real=10, min_share=0.30), expected)
    assert v.status == "FAILED" and v.missing == ["AAPL"]


def test_min_real_is_a_leg_of_its_own() -> None:
    v = m.judge(_rows("SPY", 9, True), cfg_for(("SPY",), min_real=10), {"SPY": 9})
    assert v.status == "FAILED" and v.missing == ["SPY"]


@pytest.mark.parametrize("n,expected,n_exp,covered", [
    (90, 100, 6, True), (89, 100, 6, False),      # returned >= 90 % of expected
    (100, 0, 6, False),                           # a listing that named nothing
    (100, 100, 4, True), (100, 100, 3, False)])   # >= n_weekly expiries
def test_R3_covered_means_what_was_EXPECTED_came_back(n: int, expected: int, n_exp: int,
                                                      covered: bool) -> None:
    v = m.judge(_rows("SPY", n, True, n_exp), cfg_for(("SPY",)), {"SPY": expected})
    assert (v.covered == ["SPY"]) is covered


def test_R3_rows_outside_the_listing_do_not_fill_in_for_missing_listed_ones() -> None:
    df = pd.concat([_rows("SPY", 50, True), _rows("SPY", 50, True, tag="U").assign(listed=False)])
    assert m.judge(df, cfg_for(("SPY",)), {"SPY": 100}).status == "FAILED"


def test_one_quote_repeated_across_a_name_is_a_placeholder_feed() -> None:
    """$1.00 x $1.00 everywhere is plausible out of the money, so no row rule can catch it."""
    df = _rows("SPY", 40, True)
    df.loc[df.index[:10], ["bid", "ask"]] = 1.0
    assert m.judge(df, cfg_for(("SPY",)), {"SPY": 40}).status == "OK"          # 25 %
    df.loc[df.index[:11], ["bid", "ask"]] = 1.0
    v = m.judge(df, cfg_for(("SPY",)), {"SPY": 40})
    assert v.status == "FAILED" and "one quote on 11 rows" in v.message


def _only_first_expiry(answer: Any) -> Callable[[str, dict[str, Any]], Any]:
    def hook(path: str, params: dict[str, Any]) -> Any:
        if path.startswith("/v1beta1") and params["expiration_date"] != "2026-11-27":
            return FakeResp(payload=answer)
        return None
    return hook


@pytest.mark.parametrize("answer", [{"snapshots": {}, "next_page_token": None},
                                    {"message": "internal"}, {"snapshots": None},
                                    {"snapshots": []}])
def test_R3_one_of_six_expiries_is_not_OK(tmp_path: Path, answer: Any) -> None:
    out = run(tmp_path, Market(hook=_only_first_expiry(answer)))
    assert out.status == "FAILED" and "returned 14/84, 1 expiries" in out.message
    assert len(stored(tmp_path)) == ALL / 6, "what did come back is kept"
    assert not m.verify_store(tmp_path, cfg_for(), SNAP)[0]


def test_R3_a_page_without_its_key_is_an_error_not_an_empty_page(tmp_path: Path) -> None:
    run(tmp_path, Market(hook=_only_first_expiry({"message": "internal"})))
    assert "no usable 'snapshots'" in runs(tmp_path)[-1]["errors"]["SPY"]
    mk = Market(hook=lambda p, _: FakeResp(payload={"oops": 1}) if p == "/v2/options/contracts" else None)
    out = run(tmp_path / "b", mk)
    assert out.status == "FAILED"
    assert "no usable 'option_contracts'" in runs(tmp_path / "b")[-1]["errors"]["SPY"]


def test_R3_a_truncated_contract_list_is_not_OK(tmp_path: Path) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        if path != "/v2/options/contracts":
            return None
        u = params["underlying_symbols"]
        return FakeResp(payload={"next_page_token": None, "option_contracts": [
            {"symbol": occ(u, date(2026, 11, 27), cp, 700.0 if u != "AAPL" else 340.0),
             "root_symbol": u, "expiration_date": "2026-11-27"} for cp in "CP"]})
    out = run(tmp_path, Market(hook=hook))
    assert out.status == "FAILED" and "1 expiries" in out.message


def test_R3_ten_of_108_contracts_is_not_OK_and_verify_rejudges_from_the_run_log(tmp_path: Path) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        if path.endswith("/XSP"):
            e = date.fromisoformat(params["expiration_date"])
            return FakeResp(payload={"next_page_token": None, "snapshots":
                                     {occ("XSP", e, "C", 700.0): snapshot(700.0, "C", 700.0)}})
        return None
    lenient = cfg_for(floor=0.5)
    out = run(tmp_path, Market(hook=hook), cfg_for(floor=0.5, required=("XSP",)))
    assert out.status == "FAILED" and "XSP [real 6/6, returned 6/84" in out.message
    assert runs(tmp_path)[-1]["per_symbol"]["XSP"] == {"exp": 84, "ret": 6, "unl": 0, "nexp": 6,
                                                       "nret": 6, "real": 6}
    ok, msg = m.verify_store(tmp_path, cfg_for(floor=0.5, required=("XSP",)), SNAP)
    assert not ok and "returned 6/84" in msg
    assert m.verify_store(tmp_path, lenient, SNAP)[0], "and XSP alone is what failed it"


def test_R3_verify_without_a_run_record_cannot_judge_completeness(tmp_path: Path) -> None:
    capture(tmp_path, SNAP)
    (tmp_path / m.RUN_LOG_NAME).write_text("not json\n[]\n")
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "no run record" in msg


def test_R3_a_later_truncated_run_does_not_lower_the_bar(tmp_path: Path) -> None:
    rec = {"snap_date": "2026-11-20", "slot": "eod", "file_rows": 9}
    got = m._expected_for([{**rec, "per_symbol": {"SPY": {"exp": 84}}},
                           {**rec, "per_symbol": {"SPY": {"exp": 14}}},
                           {**rec, "per_symbol": {"SPY": "odd"}},
                           {**rec, "slot": "near_close", "per_symbol": {"SPY": {"exp": 999}}}],
                          SNAP, "eod")
    assert got == {"SPY": 84}


# ───────────────────────────── 5. dedup, write, size ─────────────────────────────

def test_dedup_never_replaces_a_real_row_with_a_non_real_one() -> None:
    def at(real: bool, ts: str) -> pd.DataFrame:
        return _rows("SPY", 3, real).assign(snap_ts=pd.Timestamp(ts))
    early, junk = at(True, "2026-11-20T21:00:00Z"), at(False, "2026-11-20T23:30:00Z")
    late = at(True, "2026-11-20T23:45:00Z")
    out = m.dedup([early, junk])
    assert len(out) == 3 and out.real_quote.all()
    assert (out.snap_ts == pd.Timestamp("2026-11-20T21:00:00Z")).all()
    assert (m.dedup([early, junk, late]).snap_ts == pd.Timestamp("2026-11-20T23:45:00Z")).all()
    assert len(m.dedup([_rows("SPY", 3, True), _rows("AAPL", 3, True)])) == 6


def _realistic_day(n: int, seed: int = 7) -> pd.DataFrame:
    """Realistically-shaped rows: cent prices, 4-decimal greeks, session-time stamps."""
    rng = np.random.default_rng(seed)
    unds = np.array(["SPY", "QQQ", "IWM", "AAPL", "MSFT"])[rng.integers(0, 5, n)]
    bid = np.round(rng.gamma(1.0, 5.0, n), 2)
    base = pd.Timestamp("2026-11-20T20:59:00Z")
    df = pd.DataFrame({
        "snap_date": "2026-11-20", "slot": "eod", "snap_ts": pd.Timestamp("2026-11-20T23:30:00Z"),
        "underlying": unds, "root": unds, "expiry": date(2026, 12, 18),
        "strike": np.round(rng.uniform(400, 800, n)), "listed": True,
        "option_type": np.where(rng.random(n) < 0.5, "C", "P"), "style": "american",
        "bid": bid, "ask": np.round(bid * (1 + rng.uniform(0.01, 0.2, n)) + 0.01, 2),
        "bid_size": rng.integers(1, 300, n), "ask_size": rng.integers(1, 300, n),
        "bid_exchange": "C", "ask_exchange": "M", "quote_condition": "A",
        "quote_ts": base + pd.to_timedelta(rng.integers(0, 60_000_000, n), unit="us"),
        "last_price": bid, "last_size": rng.integers(1, 20, n), "last_exchange": "C",
        "last_condition": "I",
        "last_ts": base - pd.to_timedelta(rng.integers(0, 20_000_000_000, n), unit="us"),
        "iv": np.round(rng.uniform(0.15, 0.9, n), 4),
        "delta": np.round(rng.uniform(-1, 1, n), 4), "gamma": np.round(rng.uniform(0, .05, n), 4),
        "theta": np.round(rng.uniform(-1, 0, n), 4), "vega": np.round(rng.uniform(0, 1, n), 4),
        "rho": np.round(rng.uniform(-.5, .5, n), 4),
        "day_volume": rng.integers(0, 5000, n), "day_trade_count": rng.integers(0, 300, n),
        "open_interest": rng.integers(0, 50_000, n), "open_interest_date": date(2026, 11, 18),
        "underlying_price": 693.38, "underlying_price_ts": pd.Timestamp("2026-11-20T23:15:00Z"),
        "underlying_day_close": 693.06, "ref_low": 693.06, "ref_high": 693.38,
        "ref_source": "underlying", "feed": "indicative", "real_quote": True, "quote_rule": "v2"})
    df["contract"] = df["underlying"] + "261218" + df["option_type"] + pd.Series(
        range(n), dtype="str").str.zfill(8)
    return df


def test_write_day_is_schema_exact_and_merges_a_rerun(tmp_path: Path) -> None:
    day = _realistic_day(400)
    path, nbytes, nrows, moved = m.write_day(day, tmp_path, SNAP)
    assert path == tmp_path / "options_snapshot_2026-11-20.parquet" and nbytes > 0
    assert (nrows, moved) == (400, None)
    assert pq.read_schema(path).equals(m.SCHEMA, check_metadata=False)
    m.write_day(day.iloc[:50], tmp_path, SNAP)                 # a re-run of a subset
    assert len(pd.read_parquet(path)) == nrows                 # deduped, nothing lost
    m.append_run_log(tmp_path, {"snap_date": "2026-11-20", "status": "OK"})
    m.write_day(day.assign(snap_date="2026-11-23"), tmp_path, date(2026, 11, 23))
    both = pd.read_parquet(tmp_path)                           # the run log is ignored
    assert set(both.snap_date) == {"2026-11-20", "2026-11-23"} and len(both) == 2 * nrows


def test_a_failed_write_leaves_the_existing_file_and_no_temp_file(tmp_path: Path,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    m.write_day(_realistic_day(50), tmp_path, SNAP)
    before = m.day_path(tmp_path, SNAP).read_bytes()

    def disk_full(table: Any, path: Any, **kw: Any) -> None:
        Path(path).write_bytes(b"partial")
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(m.pq, "write_table", disk_full)
    with pytest.raises(OSError):
        m.write_day(_realistic_day(80), tmp_path, SNAP)
    assert m.day_path(tmp_path, SNAP).read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["options_snapshot_2026-11-20.parquet"]


def test_a_realistic_day_is_small_and_zstd_compressed(tmp_path: Path) -> None:
    """Budget lock: the real 2026-11-20 file measured ~46 bytes/row; the ceiling is ~20 MB/day.
    A 25k-row day must stay under 3 MB here (synthetic rows compress worse than real ones)."""
    path, nbytes, rows, _ = m.write_day(_realistic_day(25_000), tmp_path, SNAP)
    assert pq.ParquetFile(path).metadata.row_group(0).column(0).compression == "ZSTD"
    assert rows == 25_000 and nbytes / rows < 115 and nbytes < 3_000_000


# ───────────────────────────── 6. one run, end to end ─────────────────────────────

def test_a_healthy_day_writes_real_rows_for_every_underlying(tmp_path: Path) -> None:
    out = run(tmp_path, Market())
    assert (out.exit_code, out.status) == (0, "OK"), out.message
    df = stored(tmp_path)
    assert len(df) == ALL and df.real_quote.all() and df.listed.all()
    assert sorted(df.expiry.unique()) == [date(2026, 11, 27), date(2026, 12, 4),
                                          date(2026, 12, 11), date(2026, 12, 18),
                                          date(2027, 1, 15), date(2027, 2, 19)]
    assert set(df.feed) == {"indicative"} and set(df.quote_rule) == {"v2"}
    assert set(df.slot) == {"eod"} and (df.open_interest == 1234).all()
    rec = runs(tmp_path)[-1]
    assert rec["status"] == "OK" and rec["n_real"] == len(df) and rec["file_bytes"] > 0


def test_the_index_stores_no_proxy_as_its_price_and_needs_no_iv(tmp_path: Path) -> None:
    run(tmp_path, Market(last={"SPY": 702.0}))
    df = stored(tmp_path)
    x, s = df[df.underlying == "XSP"], df[df.underlying == "SPY"]
    assert len(x) and x.real_quote.all() and x.iv.isna().all()
    assert x.underlying_price.isna().all() and x.underlying_price_ts.isna().all()
    assert x.underlying_day_close.isna().all() and set(x.ref_source) == {"proxy:SPY"}
    assert (x.ref_low == 700.0).all() and (x.ref_high == 702.0).all()
    assert (s.underlying_price == 702.0).all() and (s.underlying_day_close == 700.0).all()


def test_R6_the_band_spans_the_close_and_the_after_hours_price(tmp_path: Path) -> None:
    """+25 % after hours: the first build asked for strikes 100-150 and nothing below the close."""
    mk = Market(spots={"SPY": 700.0, "AAPL": 100.0}, last={"AAPL": 125.0})
    out = run(tmp_path, mk)
    asked = [(p["strike_price_gte"], p["strike_price_lte"]) for u, p, _ in mk.calls
             if p.get("underlying_symbols") == "AAPL"]
    assert asked == [("80.00", "150.00")] and out.status == "OK"
    df = stored(tmp_path)
    a = df[df.underlying == "AAPL"]
    assert a.strike.min() == 85 and a.real_quote.all() and (a.ref_low == 100).all()


def test_the_session_close_may_be_the_previous_daily_bar_on_a_late_run(tmp_path: Path) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        if path != "/v2/stocks/snapshots":
            return None
        return FakeResp(payload={s: {"latestTrade": {"p": 350.0, "t": "2026-11-23T13:00:00Z"},
                                     "dailyBar": {"c": 350.0, "t": "2026-11-23T05:00:00Z"},
                                     "prevDailyBar": {"c": 340.0, "t": "2026-11-20T05:00:00Z"}}
                                 for s in params["symbols"].split(",")})
    run(tmp_path, Market(hook=hook, spots={"SPY": 340.0, "AAPL": 340.0}), now=et(date(2026, 11, 23), 8))
    a = stored(tmp_path)
    a = a[a.underlying == "AAPL"]
    assert (a.underlying_day_close == 340).all() and (a.ref_low == 340).all() and (a.ref_high == 350).all()


def test_ZERO_real_quotes_fails_closed_and_writes_nothing(tmp_path: Path) -> None:
    out = run(tmp_path, Market(snap=quoted(**WIPED)))
    assert (out.exit_code, out.status) == (1, "FAILED") and "nothing written" in out.message
    assert not day_files(tmp_path) and runs(tmp_path)[-1]["status"] == "FAILED"


@pytest.mark.parametrize("over", [dict(bp=0.0, ap=1.00, bs=0), dict(bp=1.0, ap=1.0),
                                  dict(bp=0.01, ap=79.0), dict(bp=0.0, ap=79.0, bs=0),
                                  dict(bs=0, as_=0, bx="?", ax="?")])
def test_R4_a_placeholder_feed_is_FAILED(tmp_path: Path, over: dict[str, Any]) -> None:
    out = run(tmp_path, Market(snap=quoted(**over)), cfg_for(min_share=0.30))
    assert out.status == "FAILED", out.message


def test_thin_coverage_fails_loud_but_keeps_what_came_back(tmp_path: Path) -> None:
    out = run(tmp_path, Market(fail={"AAPL": FakeResp(500, {"message": "upstream"})}))
    assert (out.exit_code, out.status) == (1, "FAILED")
    assert "coverage 2/3" in out.message and "AAPL" in out.message
    assert set(stored(tmp_path).underlying) == {"SPY", "XSP"}
    assert "AAPL" in runs(tmp_path)[-1]["errors"]


def _only(symbol: str, over: dict[str, Any]) -> Callable[..., dict[str, Any]]:
    make = quoted(**over)
    return lambda u, k, cp, spot, d: (make if u == symbol else
                                      (lambda *a: snapshot(k, cp, spot, d)))(u, k, cp, spot, d)


def test_a_junk_underlying_is_not_covered(tmp_path: Path) -> None:
    out = run(tmp_path, Market(snap=_only("AAPL", WIPED)))
    assert out.status == "FAILED" and runs(tmp_path)[-1]["missing"] == ["AAPL"]


def test_a_WIPED_required_index_fails_the_day_and_keeps_the_rest(tmp_path: Path) -> None:
    mk = Market(snap=_only("XSP", WIPED))
    assert run(tmp_path / "a", mk, cfg_for(floor=0.5)).status == "OK"
    out = run(tmp_path / "b", mk, cfg_for(floor=0.5, required=("SPY", "XSP")))
    assert out.status == "FAILED" and "required underlying not covered: XSP" in out.message
    df = stored(tmp_path / "b")
    assert not df[df.underlying == "XSP"].real_quote.any()
    assert df[df.underlying == "SPY"].real_quote.all()


def test_only_the_standard_root_is_stored_or_expected(tmp_path: Path) -> None:
    out = run(tmp_path, Market(extra_root="1"))
    assert out.status == "OK" and len(stored(tmp_path)) == ALL
    assert set(stored(tmp_path).root) == {"SPY", "AAPL", "XSP"}
    assert runs(tmp_path)[-1]["per_symbol"]["SPY"]["exp"] == 84


def test_rows_served_but_not_listed_are_kept_flagged_and_reported(tmp_path: Path) -> None:
    """COST, 2026-11-24: 100 strikes still served after the listing dropped them."""
    def hook(path: str, params: dict[str, Any]) -> Any:
        if path.endswith("/AAPL"):
            e = date.fromisoformat(params["expiration_date"])
            s = {occ("AAPL", e, cp, k): snapshot(k, cp, 340.0) for k in
                 (289.0, 306.0, 323.0, 340.0, 357.0, 374.0, 391.0) for cp in "CP"}
            s[occ("AAPL", e, "C", 341.0)] = snapshot(341.0, "C", 340.0)
            return FakeResp(payload={"snapshots": s, "next_page_token": None})
        return None
    out = run(tmp_path, Market(hook=hook))
    df = stored(tmp_path)
    extra = df[~df.listed]
    assert len(extra) == 6 and set(extra.strike) == {341.0} and extra["style"].isna().all()
    assert out.status == "OK" and "6 rows not in the contract listing {'AAPL': 6}" in out.message


def _first_contract(value: Any) -> Callable[[str, dict[str, Any]], Any]:
    """AAPL's first snapshot of each chain page is replaced (or mutated) by ``value``."""
    def hook(path: str, params: dict[str, Any]) -> Any:
        if not path.endswith("/AAPL"):
            return None
        snaps = Market().chain("AAPL", date.fromisoformat(params["expiration_date"]))
        k = sorted(snaps)[0]
        if callable(value):
            value(snaps[k])
        else:
            snaps[k] = value
        return FakeResp(payload={"snapshots": snaps, "next_page_token": None})
    return hook


ODD_SNAPSHOTS: dict[str, Any] = {
    "null": None, "string": "oops", "list": [1],
    "size inf": lambda s: s["latestQuote"].update(bs=float("inf")),
    "size 3e9": lambda s: s["latestQuote"].update(bs=3_000_000_000),
    "bid list": lambda s: s["latestQuote"].update(bp=[1, 2]),
    "bid inf": lambda s: s["latestQuote"].update(bp=float("inf"), ap=float("inf")),
    "exchange int": lambda s: s["latestQuote"].update(bx=5),
    "time int": lambda s: s["latestQuote"].update(t=1732000000),
    "quote null": lambda s: s.update(latestQuote=None, greeks=None, latestTrade=None),
    "quote string": lambda s: s.update(latestQuote="x"),
    "iv dict": lambda s: s.update(impliedVolatility={"v": 1}),
    "oversized int": lambda s: s["dailyBar"].update(v=10 ** 30),
}


@pytest.mark.parametrize("name", list(ODD_SNAPSHOTS))
def test_R7_one_odd_value_costs_at_most_its_own_row(tmp_path: Path, name: str) -> None:
    out = run(tmp_path, Market(hook=_first_contract(ODD_SNAPSHOTS[name])))
    assert out.status == "OK", out.message                # 78 of 84 (93 %) still listed
    df = stored(tmp_path)
    assert (df.underlying == "SPY").sum() == 84 and (df.underlying == "AAPL").sum() >= 78
    assert not np.isinf(df.select_dtypes("float")).any().any(), "an infinity is stored as null"
    assert pq.read_schema(m.day_path(tmp_path, SNAP)).equals(m.SCHEMA, check_metadata=False)


def test_R7_a_parse_crash_is_that_underlyings_error(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    real = m.snapshots_frame

    def boom(snaps: Any, d: date) -> Any:
        if next(iter(snaps)).startswith("AAPL"):
            raise AttributeError("k-SENTINEL-KEY-7731 in a message")
        return real(snaps, d)
    monkeypatch.setattr(m, "snapshots_frame", boom)
    out = run(tmp_path, Market(), cfg_for(floor=0.5))
    assert out.status == "OK" and set(stored(tmp_path).underlying) == {"SPY", "XSP"}
    err = runs(tmp_path)[-1]["errors"]["AAPL"]
    assert "AttributeError" in err and KEY not in err


@pytest.mark.parametrize("body", [{"option_contracts": [1, 2]}, {"option_contracts": [None]},
                                  {"option_contracts": {"a": 1}}, [1], "x",
                                  {"option_contracts": [{"symbol": "X"}]}])
def test_R7_an_odd_contract_listing_costs_one_underlying(tmp_path: Path, body: Any) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        return (FakeResp(payload=body) if params.get("underlying_symbols") == "AAPL" else None)
    out = run(tmp_path, Market(hook=hook), cfg_for(floor=0.5))
    assert out.status == "OK" and set(stored(tmp_path).underlying) == {"SPY", "XSP"}


@pytest.mark.parametrize("aapl", [None, [1], "x", {"latestTrade": {"p": "abc"}}, {"latestTrade": [1]}])
def test_R7_an_odd_stock_snapshot_costs_one_underlying(tmp_path: Path, aapl: Any) -> None:
    good = {"latestTrade": {"p": 700.0, "t": "2026-11-20T23:15:00Z"}}
    mk = Market(queue={"/v2/stocks/snapshots": [FakeResp(payload={"SPY": good, "AAPL": aapl})]})
    out = run(tmp_path, mk, cfg_for(floor=0.5))
    assert out.status == "OK" and set(stored(tmp_path).underlying) == {"SPY", "XSP"}


@pytest.mark.parametrize("body", [[], "x", {}, 7])
def test_R7_an_odd_stock_payload_is_a_FAILED_day_not_a_crash(tmp_path: Path, body: Any) -> None:
    out = run(tmp_path, Market(queue={"/v2/stocks/snapshots": [FakeResp(payload=body)]}))
    assert out.status == "FAILED" and runs(tmp_path)[-1]["status"] == "FAILED"


@pytest.mark.parametrize("bad", ["garbage", "lacks columns"])
def test_R7_a_corrupt_day_file_is_moved_aside_never_deleted(tmp_path: Path, bad: str) -> None:
    path = m.day_path(tmp_path, SNAP)
    if bad == "garbage":
        path.write_bytes(b"garbage")
    else:
        pd.DataFrame({"snap_date": ["2026-11-20"]}).to_parquet(path)
    before = path.read_bytes()
    out = run(tmp_path, Market())
    assert (out.exit_code, out.status) == (1, "FAILED"), "a damaged store must alarm once"
    assert "moved aside" in out.message and len(stored(tmp_path)) == ALL, "and the day is saved"
    aside = list(tmp_path.glob("_corrupt_*"))
    assert len(aside) == 1 and aside[0].read_bytes() == before
    assert len(pd.read_parquet(tmp_path)) == ALL                # dataset readers skip it
    assert m.verify_store(tmp_path, cfg_for(), SNAP)[0]


def test_the_expiries_before_an_error_are_kept(tmp_path: Path) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        return (FakeResp(404, {"message": "gone"}) if path.endswith("/AAPL")
                and params["expiration_date"] == "2027-02-19" else None)
    out = run(tmp_path, Market(hook=hook))
    df = stored(tmp_path)
    assert out.status == "FAILED" and (df.underlying == "AAPL").sum() == 70
    assert "2027-02-19: HTTP 404" in runs(tmp_path)[-1]["errors"]["AAPL"]


def test_keys_rejected_mid_run_keep_the_underlyings_already_captured(tmp_path: Path) -> None:
    def hook(path: str, params: dict[str, Any]) -> Any:
        return FakeResp(401, {"message": "unauthorized"}) if path.endswith("/AAPL") else None
    mk = Market(hook=hook)
    out = run(tmp_path, mk)
    assert out.status == "FAILED" and set(stored(tmp_path).underlying) == {"SPY"}
    assert "rejected the keys" in json.dumps(runs(tmp_path)[-1])
    assert not [u for u, _, _ in mk.calls if u.endswith("/XSP")], "nothing is tried after a 401"


def test_rejected_keys_at_the_start_fail_loud_and_are_logged(tmp_path: Path) -> None:
    out = run(tmp_path, Market(queue={"/v2/stocks/snapshots": [FakeResp(401, {"message": "no"})]}))
    assert out.status == "FAILED" and "rejected the keys" in json.dumps(runs(tmp_path)[-1])


def test_R1_the_wall_budget_stops_the_run_and_keeps_what_came_back(tmp_path: Path) -> None:
    clk = FakeClock()
    mk = Market()
    mk.on_call = lambda: clk.sleep(60.0)                   # every request takes a minute
    out = m.run_archive(cfg_for(budget=600.0), client_for(mk, clk), tmp_path, NOW)
    df = stored(tmp_path)
    assert out.status == "FAILED" and set(df.underlying) >= {"SPY"}
    assert "wall budget spent" in json.dumps(runs(tmp_path)[-1]["errors"])
    assert len(mk.calls) <= 11, "no request starts after the budget is gone"


def test_a_run_that_crashes_still_leaves_a_run_log_record(tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any) -> None:
        raise OSError(28, "No space left; k-SENTINEL-KEY-7731")
    monkeypatch.setattr(m, "write_day", boom)
    with pytest.raises(OSError):
        run(tmp_path, Market())
    rec = runs(tmp_path)[-1]
    assert rec["status"] == "CRASHED" and "OSError" in rec["message"] and KEY not in json.dumps(rec)


# ───────────────────────────── 7. the HTTP client (R1, R9) ─────────────────────────────

def test_429_is_retried_after_the_reset_and_counted(tmp_path: Path) -> None:
    mk = Market(queue={"/v1beta1/options/snapshots/SPY": [
        FakeResp(429, {"message": "too many"}, {"X-RateLimit-Limit": "200"})]})
    client = client_for(mk)
    out = m.run_archive(cfg_for(), client, tmp_path, NOW)
    assert out.status == "OK" and client.n_429 == 1 and client.n_retries == 1


@pytest.mark.parametrize("first", [FakeResp(503, {"message": "down"}), requests.ReadTimeout("x"),
                                   requests.ConnectionError("x"),
                                   requests.exceptions.ChunkedEncodingError("x")])
def test_a_transient_failure_is_retried(first: Any) -> None:
    c = client_for(Market(queue={"/v2/calendar": [first]}))
    assert c.calendar(SNAP, SNAP) and c.n_retries == 1


def test_a_persistent_5xx_gives_up_instead_of_hanging() -> None:
    c = client_for(Market(queue={"/v2/calendar": [FakeResp(503, {"m": 1}) for _ in range(9)]}))
    with pytest.raises(m.ApiError, match="gave up after 4 attempts"):
        c.calendar(SNAP, SNAP)
    assert c.requests["paper-api.alpaca.markets"] == 4


def test_requests_are_paced_under_the_published_limit() -> None:
    clk = FakeClock()
    c = client_for(Market(), clk)
    for _ in range(5):
        c.calendar(SNAP, SNAP)
    assert sum(clk.slept) == pytest.approx(4 * 60.0 / m.TRADE_PER_MIN)
    assert m.DATA_PER_MIN < 200 and m.TRADE_PER_MIN < 200


def test_pagination_is_followed_and_a_repeated_token_is_an_error(tmp_path: Path) -> None:
    assert run(tmp_path, Market(page_size=5)).status == "OK" and len(stored(tmp_path)) == ALL
    for token in ("same", ["x"]):
        loop = FakeResp(payload={"snapshots": {}, "next_page_token": token})
        c = client_for(Market(queue={"/v1beta1/options/snapshots/SPY": [loop, loop]}))
        with pytest.raises(m.ApiError, match="repeated page token"):
            c.chain("SPY", date(2026, 12, 18), 1.0, 2.0, "indicative")


def test_the_feed_and_filters_are_sent_and_only_GET_is_used(tmp_path: Path) -> None:
    mk = Market()
    run(tmp_path, mk)
    chain = [p for u, p, _ in mk.calls if "/v1beta1/options/snapshots/" in u]
    assert chain and all(p["feed"] == "indicative" and "expiration_date" in p for p in chain)
    stocks = [p for u, p, _ in mk.calls if u.endswith("/v2/stocks/snapshots")]
    assert stocks[0]["feed"] == "delayed_sip" and not hasattr(m.AlpacaReadClient, "post")
    assert {urlparse(u).netloc for u, _, _ in mk.calls} == {"data.alpaca.markets",
                                                            "paper-api.alpaca.markets"}
    assert set(mk.redirects_allowed) == {False}


@pytest.fixture
def drip_server() -> Iterator[int]:
    """A server that sends headers and then one byte at a time, for ever."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    stop = threading.Event()

    def handle(c: socket.socket) -> None:
        try:
            c.recv(4096)
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n{")
            while not stop.wait(0.05):
                c.sendall(b" ")
        except OSError:
            pass

    def serve() -> None:
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            threading.Thread(target=handle, args=(c,), daemon=True).start()
    threading.Thread(target=serve, daemon=True).start()
    yield srv.getsockname()[1]
    stop.set()
    srv.close()


def test_R1_a_dripping_server_is_abandoned_at_the_total_cap(drip_server: int) -> None:
    """requests' read timeout is per socket read, so a drip blocks it for ever."""
    url = f"http://127.0.0.1:{drip_server}"
    c = m.AlpacaReadClient("k", "s", data_url=url, trade_url=url, timeout=(2.0, 3.0),
                           max_attempts=2, hard_cap=0.4, sleep=lambda _: None)
    t0 = time.monotonic()
    with pytest.raises(m.ApiError, match="gave up after 2 attempts"):
        c.get(f"{url}/x")
    assert time.monotonic() - t0 < 5 and c.n_hung == 2


def test_R9_a_redirect_is_refused_so_the_key_headers_do_not_travel() -> None:
    seen: list[tuple[str, Optional[str]]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append((self.path, self.headers.get("APCA-API-SECRET-KEY")))
            self.send_response(302 if self.path == "/x" else 200)
            if self.path == "/x":
                self.send_header("Location", f"http://localhost:{srv.server_port}/elsewhere")
            self.end_headers()

        def log_message(self, *a: Any) -> None:
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"
    try:
        with pytest.raises(m.ApiError, match="HTTP 302"):
            m.AlpacaReadClient("k", "s", data_url=url, trade_url=url).get(f"{url}/x")
    finally:
        srv.shutdown()
        srv.server_close()
    assert [p for p, _ in seen] == ["/x"]


@pytest.mark.parametrize("raw", [" " + SECRET, SECRET + "\n", "“" + SECRET])
def test_R9_a_header_error_never_quotes_the_key(tmp_path: Path, raw: str,
                                                capsys: pytest.CaptureFixture[str]) -> None:
    """requests.InvalidHeader puts the header VALUE in its message. Force the raw value into the
    header (past the strip) with a real Session; header checks fail before any network."""
    c = m.AlpacaReadClient(KEY, SECRET, sleep=lambda _: None)
    c._headers["APCA-API-SECRET-KEY"] = raw

    class NoNetwork(requests.adapters.HTTPAdapter):
        def send(self, *a: Any, **k: Any) -> Any:
            raise requests.ConnectionError("blocked in tests")
    c._s.mount("https://", NoNetwork())
    out = m.run_archive(cfg_for(), c, tmp_path, NOW)
    seen = capsys.readouterr()
    blob = seen.out + seen.err + out.message + (tmp_path / m.RUN_LOG_NAME).read_text()
    assert out.status == "FAILED" and SECRET not in blob and KEY not in blob


def test_R9_keys_are_stripped_and_a_body_that_echoes_them_is_redacted() -> None:
    c = m.AlpacaReadClient(f" {KEY}\n", f"{SECRET} ", session=Market(  # type: ignore[arg-type]
        queue={"/v2/calendar": [FakeResp(403, {"message": f"bad key {KEY} / {SECRET}"})]}))
    assert c._headers["APCA-API-KEY-ID"] == KEY and c._headers["APCA-API-SECRET-KEY"] == SECRET
    with pytest.raises(m.ApiError) as e:
        c.calendar(SNAP, SNAP)
    assert KEY not in str(e.value) and SECRET not in str(e.value) and "***" in str(e.value)


# ───────────────────────────── 8. the local verifier (R2, R5, R8) ─────────────────────────────

def test_verifier_passes_a_good_trading_day_and_fails_a_missing_one(tmp_path: Path) -> None:
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "no eod capture for session 2026-11-20" in msg
    capture(tmp_path, SNAP)
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert ok and msg.startswith("OK"), msg


@pytest.mark.parametrize("now", [et(date(2026, 11, 21), 0, 30), et(date(2026, 11, 21)),
                                 et(date(2026, 11, 22)), et(date(2026, 11, 23), 8, 0),
                                 et(date(2026, 11, 23), 12, 0)])
def test_verifier_checks_the_last_session_that_CLOSED(tmp_path: Path, now: datetime) -> None:
    """After midnight, on a weekend, and before today's close, that is Friday."""
    ok, msg = m.verify_store(tmp_path, cfg_for(), now)
    assert ok and msg.startswith("SKIP"), "an empty store before the first capture is not a miss"
    capture(tmp_path, date(2026, 11, 19))                      # Thursday only: Friday missed
    ok, msg = m.verify_store(tmp_path, cfg_for(), now)
    assert not ok and "session 2026-11-20" in msg
    capture(tmp_path, SNAP)
    assert m.verify_store(tmp_path, cfg_for(), now)[0]


def test_a_gap_alarms_every_day_until_it_is_acknowledged(tmp_path: Path) -> None:
    for d in (date(2026, 11, 17), date(2026, 11, 19), SNAP):   # 11-18 was never captured
        capture(tmp_path, d)
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "no eod capture for session(s) 2026-11-18" in msg
    assert m.verify_store(tmp_path, cfg_for(gaps=(date(2026, 11, 18),)), SNAP)[0]
    m.day_path(tmp_path, date(2026, 11, 18)).write_bytes(b"not parquet")
    assert not m.verify_store(tmp_path, cfg_for(), SNAP)[0], "an unreadable file is still a gap"


def test_a_near_close_capture_does_not_fill_an_eod_gap(tmp_path: Path) -> None:
    capture(tmp_path, date(2026, 11, 18))
    run(tmp_path, Market(session=date(2026, 11, 19)), now=et(date(2026, 11, 19), 15, 45),
        slot="near_close")
    capture(tmp_path, SNAP)
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "2026-11-19" in msg


def test_R5_verify_believes_a_closure_only_from_a_LATER_runs_calendar(tmp_path: Path) -> None:
    """2026-11-19 (Thu) is closed ad hoc: Alpaca omits it; the rules say open."""
    thu = date(2026, 11, 19)

    def omitting(today: date) -> list[dict[str, str]]:
        return [{"date": d.isoformat(), "close": "16:00"}
                for d in _dailies(today - timedelta(days=7), 15) if d != thu]
    capture(tmp_path, date(2026, 11, 18))
    stale = Market(session=date(2026, 11, 18), calendar=omitting(thu))   # quotes are Wednesday's
    assert run(tmp_path, stale, now=et(thu)).status == "FAILED"
    assert not m.verify_store(tmp_path, cfg_for(), thu)[0], "today's own claim is not believed"
    run(tmp_path, Market(calendar=omitting(SNAP)))
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert ok and "excused as ad-hoc closures: 2026-11-19" in msg, msg
    run(tmp_path, Market(session=date(2026, 11, 23)), now=et(date(2026, 11, 23)))  # lists 11-19
    ok, msg = m.verify_store(tmp_path, cfg_for(), date(2026, 11, 23))
    assert not ok and "for session(s) 2026-11-19" in msg and "excused" not in msg, (
        "a later calendar that lists the day wins")


def test_verifier_rejudges_by_CONTENT_not_the_stored_flag(tmp_path: Path) -> None:
    """A file whose rows all CLAIM real_quote=True but hold zero quotes must fail."""
    capture(tmp_path, SNAP)
    df = stored(tmp_path)
    df[["bid", "ask"]] = 0.0
    pq.write_table(m.to_table(df.assign(real_quote=True)), m.day_path(tmp_path, SNAP))
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "0 real quotes" in msg


def test_verifier_judges_only_rows_of_that_session(tmp_path: Path) -> None:
    """Yesterday's file copied under today's name holds no row of today."""
    capture(tmp_path, date(2026, 11, 19))
    capture(tmp_path, SNAP)
    m.day_path(tmp_path, SNAP).write_bytes(m.day_path(tmp_path, date(2026, 11, 19)).read_bytes())
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "0 real quotes in 0 rows" in msg


def test_verifier_judges_only_rows_of_that_slot(tmp_path: Path) -> None:
    """A good near_close XSP must not stand in for a wiped one at the close."""
    cfg = cfg_for(floor=0.5, required=("XSP",))
    run(tmp_path, Market(), cfg, et(SNAP, 15, 45), "near_close")
    run(tmp_path, Market(snap=_only("XSP", WIPED)), cfg)
    ok, msg = m.verify_store(tmp_path, cfg, SNAP)
    assert not ok and "required underlying not covered: XSP" in msg


def test_verifier_applies_the_required_list_and_the_share_floor(tmp_path: Path) -> None:
    capture(tmp_path, SNAP, cfg_for(floor=0.5), _only("XSP", WIPED))
    assert m.verify_store(tmp_path, cfg_for(floor=0.5), SNAP)[0]
    ok, msg = m.verify_store(tmp_path, cfg_for(floor=0.5, required=("XSP",)), SNAP)
    assert not ok and "required underlying not covered: XSP" in msg
    half = tmp_path / "half"
    mostly = quoted(**WIPED)
    capture(half, SNAP, cfg_for(floor=0.5),
            lambda u, k, cp, s, d: mostly(u, k, cp, s, d) if u == "AAPL" and k > 323
            else snapshot(k, cp, s, d))
    assert m.verify_store(half, cfg_for(), SNAP)[0]            # 36 of 84 AAPL rows are real
    assert not m.verify_store(half, cfg_for(min_share=0.50), SNAP)[0]


def test_verifier_reports_an_unreadable_file_instead_of_raising(tmp_path: Path) -> None:
    capture(tmp_path, SNAP)
    m.day_path(tmp_path, SNAP).write_bytes(b"x" * 50)
    ok, msg = m.verify_store(tmp_path, cfg_for(), SNAP)
    assert not ok and "unreadable" in msg


def _altdata_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, now: datetime,
                  fresh: bool = True) -> Any:
    """verify_altdata_snapshot pointed at tmp_path, its clock pinned, its 3 sources fresh."""
    import scripts.verify_altdata_snapshot as v
    from paper_trader.altdata_archive import _SNAPSHOT_FRESHNESS
    monkeypatch.setattr(v, "ROOT", tmp_path)
    monkeypatch.setattr(v, "_now_utc", lambda: now)
    today = now.astimezone().strftime("%Y-%m-%d") if fresh else "2020-01-01"
    for _, rel, col in _SNAPSHOT_FRESHNESS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({col: [today]}).to_parquet(tmp_path / rel)
    return v


@pytest.mark.parametrize("now,empty_store_rc", [
    (et(SNAP), 1), (et(date(2026, 11, 26)), 0), (et(date(2026, 11, 21)), 0),
    (et(date(2026, 11, 24), 0, 30), 0), (et(date(2026, 12, 25)), 0)])
def test_R2_the_altdata_verifier_runs_the_options_check_on_any_date(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, now: datetime, empty_store_rc: int) -> None:
    """Pinned to a trading day, Thanksgiving, a Saturday, after midnight and Christmas."""
    v = _altdata_root(tmp_path, monkeypatch, now)
    small = json.loads(m.DEFAULT_CONFIG.read_text())
    small["underlyings"] = [u for u in small["underlyings"] if u["symbol"] in ("SPY", "AAPL", "XSP")]
    (tmp_path / "cfg.json").write_text(json.dumps(small))
    monkeypatch.setattr(m, "DEFAULT_CONFIG", tmp_path / "cfg.json")
    assert v.main() == empty_store_rc
    cfg = m.load_config(m.DEFAULT_CONFIG)
    local = now.astimezone(m.ET)
    due = m.is_trading_day_rules(local.date()) and local.hour >= 16
    session = local.date() if due else m.previous_trading_day_rules(local.date())
    mk = Market(session=session, spots={u.symbol: 100.0 for u in cfg.underlyings})
    out = run(tmp_path / v.OPTIONS_REL, mk, cfg, et(session))
    assert out.status == "OK" and v.main() == 0


def test_the_altdata_verifier_passes_on_the_committed_universe(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    v = _altdata_root(tmp_path, monkeypatch, NOW)
    cfg = m.load_config(m.DEFAULT_CONFIG)
    mk = Market(spots={u.symbol: 100.0 for u in cfg.underlyings})
    assert run(tmp_path / v.OPTIONS_REL, mk, cfg).status == "OK" and v.main() == 0


def test_R8_a_broken_options_check_does_not_mask_the_altdata_verdict(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    v = _altdata_root(tmp_path, monkeypatch, NOW, fresh=False)

    def boom(*a: Any) -> Any:
        raise RuntimeError("k-SENTINEL-KEY-7731")
    monkeypatch.setattr(m, "verify_store", boom)
    assert v.main() == 1
    out = capsys.readouterr().out
    assert "FAIL — zero fresh rows: kalshi, kxfed, polymarket" in out
    assert "the options check broke (RuntimeError)" in out and KEY not in out
    v2 = _altdata_root(tmp_path, monkeypatch, NOW)
    assert v2.main() == 1 and "VERIFIER ERROR" not in capsys.readouterr().out


# ───────────────────────────── 9. CLI, keys, config ─────────────────────────────

def test_the_committed_config_loads_and_stays_within_the_declared_bounds() -> None:
    cfg = m.load_config(m.DEFAULT_CONFIG)
    singles = [u for u in cfg.underlyings if u.kind == "stock"]
    assert len(singles) <= 50 and len(cfg.declared) == len(set(cfg.declared))
    assert cfg.no_iv == frozenset({"XSP"}) and cfg.feed == "indicative"
    assert (cfg.coverage_floor, cfg.min_real_share, cfg.min_returned_share) == (0.90, 0.30, 0.90)
    assert cfg.required == ["SPY", "QQQ", "IWM", "XSP"] and not cfg.acknowledged_gaps


def test_a_missing_or_broken_config_is_exit_2(tmp_path: Path,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    good = json.loads(m.DEFAULT_CONFIG.read_text())
    assert m.main(["--config", str(tmp_path / "nope.json"), "--out-dir", str(tmp_path)]) == 2
    for change in ({"underlyings": []}, {"acknowledged_gaps": {"soon": "x"}},
                   {"min_returned_share_per_underlying": 0}, {"feed": None, "n_weekly": "x"}):
        (tmp_path / "bad.json").write_text(json.dumps({**good, **change}))
        assert m.main(["--config", str(tmp_path / "bad.json"), "--out-dir", str(tmp_path)]) == 2
    assert capsys.readouterr().out.count("FAILED options: config") == 5


def test_keys_come_as_a_pair_from_one_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / "k.env"
    env.write_text("ALPACA_API_KEY= fk \nALPACA_SECRET_KEY=fs\n")
    monkeypatch.setenv("ALPACA_API_KEY", "only-half-a-pair")
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    assert m.load_keys(env) == ("fk", "fs")
    monkeypatch.setenv("ALPACA_SECRET_KEY", " es ")
    assert m.load_keys(env) == ("only-half-a-pair", "es")


@pytest.mark.parametrize("value", ["bad key", "“quoted”"])
def test_R9_keys_that_cannot_be_headers_are_exit_2_and_name_no_value(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
        value: str) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", value)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SECRET)
    assert m.main(["--env-file", str(tmp_path / "no.env"), "--out-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "cannot go into an HTTP header" in out and value not in out and SECRET not in out


def test_missing_keys_are_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    rc = m.main(["--env-file", str(tmp_path / "absent.env"), "--out-dir", str(tmp_path)])
    assert rc == 2 and "ALPACA_API_KEY" in capsys.readouterr().out


def _main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mk: Market, *argv: str) -> int:
    monkeypatch.setenv("ALPACA_API_KEY", KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SECRET)
    real = m.AlpacaReadClient
    monkeypatch.setattr(m, "AlpacaReadClient", lambda k, s: real(
        k, s, session=mk, sleep=lambda _: None))  # type: ignore[arg-type]
    return m.main(["--out-dir", str(tmp_path), "--underlyings", "SPY,AAPL", *argv])


def test_no_key_or_secret_ever_reaches_stdout_or_the_run_log(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    mk = Market(fail={"AAPL": FakeResp(403, {"message": "forbidden"})},
                queue={"/v2/calendar": [FakeResp(401, {"message": "unauthorized"})]})
    assert _main(tmp_path, monkeypatch, mk) == 1
    seen = capsys.readouterr()
    blob = seen.out + seen.err + (tmp_path / m.RUN_LOG_NAME).read_text()
    assert "HTTP 403" in blob and KEY not in blob and SECRET not in blob
    assert all(h.get("APCA-API-KEY-ID") == KEY for _, _, h in mk.calls)   # keys only in headers
    assert all(KEY not in json.dumps(p) and KEY not in u for u, p, _ in mk.calls)


def test_main_maps_ok_refused_and_crashed_to_0_2_2(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main(tmp_path, monkeypatch, Market()) == 0
    assert m.main(["--out-dir", str(tmp_path), "--slot", "near_close"]) == 2     # 18:30 ET
    monkeypatch.setattr(m, "_run", lambda *a: (_ for _ in ()).throw(ValueError(SECRET)))
    assert m.main(["--out-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "archiver crashed: ValueError at" in out and SECRET not in out


def test_verify_flag_makes_no_api_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    capture(tmp_path / "good", SNAP)
    monkeypatch.setattr(m, "AlpacaReadClient", lambda *a, **k: pytest.fail("API used"))
    assert m.main(["--verify", "--out-dir", str(tmp_path / "none")]) == 1   # pinned: one is due
    assert m.main(["--verify", "--out-dir", str(tmp_path / "good"), "--underlyings", "SPY,XSP"]) == 0


# ───────────────────────────── 10. the launchd wrapper (R1) ─────────────────────────────

def _run_wrapper(tmp_path: Path, options: str, rc_altdata: int = 0, drill: bool = False,
                 timeout_s: str = "20", python: bool = True) -> tuple[str, str]:
    """Execute a COPY of the real wrapper with a stub interpreter and stub alarm channels. The
    copy differs only in REPO (a temp dir) and the aws fallback paths (the stub), so no real
    archiver, SNS message or notification can run. ``options`` is the options step's shell body."""
    repo, stubs = tmp_path / "repo", tmp_path / "stubs"
    (repo / ".venv/bin").mkdir(parents=True)
    stubs.mkdir()
    calls = tmp_path / "calls.txt"
    calls.touch()
    py = repo / ".venv/bin/python"
    if python:
        py.write_text("#!/bin/bash\n"
                      f'echo "PY $1" >> "{calls}"\n'
                      'case "$1" in\n'
                      f'  *archive_options_snapshots.py) {options};;\n'
                      '  *verify_altdata_snapshot.py) exit 0;;\n'
                      f'  *altdata*) exit {rc_altdata};;\n'
                      '  *) exit 0;;\nesac\n')
    for name in ("aws", "osascript"):
        (stubs / name).write_text(f'#!/bin/bash\necho "{name.upper()} $*" >> "{calls}"\n')
    for f in (py, stubs / "aws", stubs / "osascript"):
        if f.exists():
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
    src = (REPO / "scripts/run_altdata_archivers.sh").read_text()
    real_repo = 'REPO="/Users/jacksonmurphy/Dev/trading_machine-2"'
    assert src.count(real_repo) == 1
    copy = src.replace(real_repo, f'REPO="{repo}"')
    for p in ("/opt/homebrew/bin/aws", "/usr/local/bin/aws", "/usr/bin/aws"):
        copy = copy.replace(p, str(stubs / "aws"))
    wrapper = tmp_path / "wrapper.sh"
    wrapper.write_text(copy)
    # Derived from os.environ (the provider-refusal guard must reach any child); PATH is the
    # launchd PATH behind the stubs, so `command -v aws` and bare `osascript` hit the stubs.
    env = {**os.environ, "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin",
           "ARCHONDEX_OPTIONS_TIMEOUT_S": timeout_s}
    env.pop("ARCHONDEX_ALARM_DRILL", None)
    if drill:
        env["ARCHONDEX_ALARM_DRILL"] = "1"
    subprocess.run(["/bin/bash", str(wrapper)], env=env, check=True, timeout=60)
    logs = list((repo / "data/macro_data/alt/logs").glob("archive_*.log"))
    assert len(logs) == 1
    return logs[0].read_text(), calls.read_text()


def test_the_wrapper_alarms_on_the_options_rc_ALONE(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, "exit 1")
    assert "options=1" in log and "ALTDATA_ARCHIVER_FAILED" in log
    assert "AWS sns publish" in calls and "options=1" in calls
    order = [line.split()[1] for line in calls.splitlines() if line.startswith("PY ")]
    assert order.index("scripts/archive_options_snapshots.py") < order.index(
        "scripts/verify_altdata_snapshot.py"), "the verifier must read the file just written"


def test_the_wrapper_stays_quiet_when_every_rc_is_zero(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, "exit 0")
    assert "options=0" in log and "ALTDATA_ARCHIVER_FAILED" not in log
    assert "AWS" not in calls and "OSASCRIPT" not in calls


def test_R1_a_HUNG_options_step_is_killed_and_the_verifier_and_alarm_still_run(tmp_path: Path) -> None:
    t0 = time.monotonic()
    log, calls = _run_wrapper(tmp_path, "exec /bin/sleep 45", rc_altdata=1, timeout_s="1")
    assert time.monotonic() - t0 < 20
    assert "altdata=1" in log and "options=142" in log and "ALTDATA_ARCHIVER_FAILED" in log
    assert "PY scripts/verify_altdata_snapshot.py" in calls
    assert "AWS sns publish" in calls and "options=142" in calls and "OSASCRIPT" in calls


def test_R1_a_bad_timeout_value_falls_back_to_the_bound_not_to_none() -> None:
    sh = (REPO / "scripts/run_altdata_archivers.sh").read_text()
    line = next(ln for ln in sh.splitlines() if ln.startswith('case "$OPT_TIMEOUT"'))
    for value, want in (("", "2400"), ("abc", "2400"), ("0", "2400"), ("5x", "2400"),
                        ("-1", "2400"), ("90", "90")):
        got = subprocess.run(["/bin/bash", "-c", f'OPT_TIMEOUT="$1"; {line}; echo "$OPT_TIMEOUT"',
                              "_", value], capture_output=True, text=True, check=True).stdout.strip()
        assert got == want, value


def test_R1_an_interpreter_that_cannot_start_is_not_a_success(tmp_path: Path) -> None:
    """perl falls off the end with 0 when exec fails; the wrapper's `exit 127` must not."""
    log, calls = _run_wrapper(tmp_path, "exit 0", python=False)
    assert "options=127" in log and "AWS sns publish" in calls


def test_the_wrapper_drill_covers_the_options_rc(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, "exit 0", drill=True)
    assert "options=99" in log and "ALTDATA_ARCHIVER_FAILED" in log
    assert "PY " not in calls, "a drill runs no archiver"
    assert "AWS sns publish" in calls and "options=99" in calls


# ───────────────────────────── 11. no hidden clock (R2) ─────────────────────────────

CLOCK_READS = {"now", "today", "utcnow", "time", "localtime", "gmtime"}


def _clock_reads(path: Path) -> list[tuple[str, int]]:
    """(enclosing function, line) of every wall-clock call: datetime.now(), date.today(),
    pd.Timestamp.now(), time.time() ... (``.time()`` on a datetime has no clock: exempt when
    the receiver is not the time module)."""
    found: list[tuple[str, int]] = []

    class Visitor(ast.NodeVisitor):
        stack: list[str] = ["<module>"]

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in CLOCK_READS:
                receiver = ast.unparse(f.value)
                if f.attr != "time" or receiver == "time":
                    found.append((self.stack[-1], node.lineno))
            self.generic_visit(node)
    Visitor().visit(ast.parse(path.read_text()))
    return found


def test_R2_the_wall_clock_is_read_in_exactly_one_pinnable_place_per_module() -> None:
    assert {f for f, _ in _clock_reads(REPO / "scripts/archive_options_snapshots.py")} == {"_utcnow"}
    assert {f for f, _ in _clock_reads(REPO / "scripts/verify_altdata_snapshot.py")} == {"_now_utc"}
    assert _clock_reads(Path(__file__)) == [], "this test file must not read the date"
