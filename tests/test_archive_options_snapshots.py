"""T-416 locks (2026-11-20): the daily options snapshot archive judges a row by a USABLE
value, fails closed, alarms on thin coverage, and stays small.

The defect this guards against is the 2026-11-19 Kalshi one: a fail-closed check that asked
whether a price field was PRESENT passed $0 bids and $1.00 placeholder asks as "priced" for
five months while the freshness gate said OK. Here:

1. Field mapping: every stored column comes from the right snapshot / contract field;
   timestamps of both fraction widths parse; a stale daily bar is not today's volume.
2. The real-quote rule (``real_quote_mask``): fresh quote on the ET session date AND (bid > 0
   OR a fresh last trade > 0) AND a sane ask AND finite positive IV (waived for an index).
   Zero quotes, $1.00 placeholders, stale quotes, stale trades, crossed and out-of-bound asks
   and bad IV are all NOT real.
3. Fail closed: zero real quotes -> FAILED, nothing written; coverage below the floor ->
   FAILED with the rows kept; a non-trading day -> SKIP without a single chain request.
4. Dedup on (snap_date, contract): a real row is never replaced by a non-real one.
5. Size: zstd, and a realistic day stays far below the disk budget.
6. The local verifier re-judges by content and is trading-day aware; the launchd wrapper
   gives the archiver its own rc inside the alarm condition.

The network is stubbed everywhere; every write goes to tmp_path. No key is ever printed.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

import scripts.archive_options_snapshots as m

REPO = Path(__file__).resolve().parent.parent
SNAP = date(2026, 11, 20)                                    # a Friday
NOW = datetime(2026, 11, 20, 23, 30, tzinfo=timezone.utc)    # 18:30 ET, the launchd time
SESSION_TS = "2026-11-20T21:00:00.123456789Z"                # 16:00 ET, 9 fraction digits
TRADE_TS = "2026-11-20T20:10:00Z"                            # 15:10 ET, no fraction
STALE_TS = "2026-11-19T20:59:59.5Z"                          # the previous session
KEY, SECRET = "k-SENTINEL-KEY-7731", "s-SENTINEL-SECRET-9912"


# ───────────────────────────── a fake Alpaca ─────────────────────────────

class FakeResp:
    def __init__(self, status: int = 200, payload: Any = None,
                 headers: Optional[dict[str, str]] = None) -> None:
        self.status_code = status
        self._payload = payload
        self.headers = headers or {"X-RateLimit-Limit": "200", "X-RateLimit-Remaining": "199"}
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON")
        return self._payload


def occ(root: str, exp: date, cp: str, k: float) -> str:
    return f"{root}{exp:%y%m%d}{cp}{int(round(k * 1000)):08d}"


def real_snapshot(k: float, cp: str) -> dict[str, Any]:
    return {"latestQuote": {"bp": 1.0, "ap": 1.1, "bs": 10, "as": 12, "bx": "C", "ax": "M",
                            "c": "A", "t": SESSION_TS},
            "latestTrade": {"p": 1.05, "s": 3, "x": "C", "c": "I", "t": TRADE_TS},
            "impliedVolatility": 0.25,
            "greeks": {"delta": 0.5 if cp == "C" else -0.5, "gamma": 0.01, "theta": -0.2,
                       "vega": 0.3, "rho": 0.05},
            "dailyBar": {"o": 1, "h": 1.2, "l": 0.9, "c": 1.05, "v": 100, "n": 7,
                         "t": "2026-11-20T05:00:00Z"}}


def zero_snapshot(k: float, cp: str) -> dict[str, Any]:
    """The Kalshi-parlay shape: everything present, nothing usable."""
    return {"latestQuote": {"bp": 0.0, "ap": 0.0, "bs": 0, "as": 0, "bx": "C", "ax": "C",
                            "c": " ", "t": SESSION_TS},
            "latestTrade": {"p": 0.0, "s": 0, "x": "C", "c": " ", "t": STALE_TS},
            "impliedVolatility": 0.0, "greeks": {"delta": 0.0}}


def placeholder_snapshot(k: float, cp: str) -> dict[str, Any]:
    """A $0 bid with a $1.00 placeholder ask and no trade: present, not priced."""
    return {"latestQuote": {"bp": 0.0, "ap": 1.00, "bs": 0, "as": 1, "bx": "C", "ax": "C",
                            "c": " ", "t": SESSION_TS},
            "impliedVolatility": 0.31, "greeks": {"delta": 0.1}}


@dataclass
class Market:
    spots: dict[str, float] = field(default_factory=lambda: {"SPY": 700.0, "AAPL": 340.0})
    snapshot: Callable[[str, float, str], dict[str, Any]] = lambda u, k, cp: real_snapshot(k, cp)
    calendar: Any = None                  # None -> rule-based trading days; or a list / FakeResp
    fail: dict[str, Any] = field(default_factory=dict)   # underlying -> FakeResp | Exception
    page_size: int = 0                    # >0 -> paginate the chain
    first_status: dict[str, list[FakeResp]] = field(default_factory=dict)  # path -> queue
    calls: list[tuple[str, dict[str, Any], dict[str, str]]] = field(default_factory=list)

    def listed_expiries(self, e0: date, e1: date) -> list[date]:
        """Dailies: every rule-based trading day in the requested window."""
        return [e0 + timedelta(days=i) for i in range((e1 - e0).days + 1)
                if m.is_trading_day_rules(e0 + timedelta(days=i))]

    def strikes(self, spot: float) -> list[float]:
        return [float(round(spot * f)) for f in (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)]

    # the Session interface -------------------------------------------------
    def get(self, url: str, headers: Optional[dict[str, str]] = None,
            params: Optional[dict[str, Any]] = None, timeout: Any = None) -> FakeResp:
        params = dict(params or {})
        self.calls.append((url, params, dict(headers or {})))
        path = urlparse(url).path
        queue = self.first_status.get(path)
        if queue:
            return queue.pop(0)
        if path == "/v2/calendar":
            if isinstance(self.calendar, FakeResp):
                return self.calendar
            if isinstance(self.calendar, list):
                return FakeResp(payload=self.calendar)
            d0 = date.fromisoformat(params["start"])
            return FakeResp(payload=[{"date": d0.isoformat(), "open": "09:30",
                                      "close": "16:00"}] if m.is_trading_day_rules(d0) else [])
        if path == "/v2/stocks/snapshots":
            out = {}
            for s in params["symbols"].split(","):
                if s in self.spots:
                    out[s] = {"latestTrade": {"p": self.spots[s], "t": "2026-11-20T23:15:00Z"},
                              "dailyBar": {"c": self.spots[s] - 1, "t": "2026-11-20T05:00:00Z"}}
            return FakeResp(payload=out)
        if path == "/v2/options/contracts":
            u = params["underlying_symbols"]
            if u in self.fail:
                return self._fail(u)
            spot = self._spot(u)
            lo, hi = float(params["strike_price_gte"]), float(params["strike_price_lte"])
            e0 = date.fromisoformat(params["expiration_date_gte"])
            e1 = date.fromisoformat(params["expiration_date_lte"])
            rows = [{"symbol": occ(u, e, cp, k), "root_symbol": u, "underlying_symbol": u,
                     "expiration_date": e.isoformat(), "type": "call" if cp == "C" else "put",
                     "style": "european" if u == "XSP" else "american",
                     "strike_price": str(k), "open_interest": "1234",
                     "open_interest_date": "2026-11-18"}
                    for e in self.listed_expiries(e0, e1)
                    for k in self.strikes(spot) if lo <= k <= hi for cp in "CP"]
            return FakeResp(payload={"option_contracts": rows, "next_page_token": None})
        if path.startswith("/v1beta1/options/snapshots/"):
            u = path.rsplit("/", 1)[-1]
            if u in self.fail:
                return self._fail(u)
            spot = self._spot(u)
            e = date.fromisoformat(params["expiration_date"])
            lo, hi = float(params["strike_price_gte"]), float(params["strike_price_lte"])
            snaps = {occ(u, e, cp, k): self.snapshot(u, k, cp)
                     for k in self.strikes(spot) if lo <= k <= hi for cp in "CP"}
            if u == "XSP":                 # Alpaca computes no IV/greeks for index options
                for s in snaps.values():
                    s.pop("impliedVolatility", None)
                    s.pop("greeks", None)
            items = sorted(snaps.items())
            if self.page_size:
                off = int(params.get("page_token") or 0)
                page = dict(items[off:off + self.page_size])
                nxt = str(off + self.page_size) if off + self.page_size < len(items) else None
                return FakeResp(payload={"snapshots": page, "next_page_token": nxt})
            return FakeResp(payload={"snapshots": dict(items), "next_page_token": None})
        return FakeResp(404, {"message": "not found"})

    def _spot(self, u: str) -> float:
        return self.spots["SPY"] if u == "XSP" else self.spots[u]

    def _fail(self, u: str) -> FakeResp:
        out = self.fail[u]
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


def client_for(market: Market, clock: Optional[FakeClock] = None) -> m.AlpacaReadClient:
    clock = clock or FakeClock()
    return m.AlpacaReadClient(KEY, SECRET, session=market, sleep=clock.sleep,  # type: ignore[arg-type]
                              clock=clock.clock)


def cfg_for(symbols: tuple[str, ...] = ("SPY", "AAPL", "XSP"), floor: float = 0.9,
            min_real: int = 3, min_share: float = 0.0,
            required: tuple[str, ...] = ()) -> m.ArchiveConfig:
    specs = tuple(m.UnderlyingSpec(s, "index", "SPY", False, s in required) if s == "XSP"
                  else m.UnderlyingSpec(s, "stock", None, True, s in required) for s in symbols)
    return m.ArchiveConfig(specs, "indicative", 0.20, 4, 2, 100, floor, min_real, 600.0, "md5",
                           min_share)


def quote_frame(**over: Any) -> pd.DataFrame:
    """One fully real row (a call), with column overrides."""
    row: dict[str, Any] = dict(
        snap_date="2026-11-20", underlying="SPY", option_type="C", strike=700.0,
        ref_price=700.0, bid=1.0, ask=1.1, last_price=1.05, iv=0.25,
        quote_ts=pd.Timestamp(SESSION_TS), last_ts=pd.Timestamp(TRADE_TS))
    row.update(over)
    df = pd.DataFrame([row])
    for c in ("quote_ts", "last_ts"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df


def is_real(no_iv: tuple[str, ...] = (), **over: Any) -> bool:
    return bool(m.real_quote_mask(quote_frame(**over), no_iv).iloc[0])


# ───────────────────────────── 1. field mapping ─────────────────────────────

def test_snapshot_fields_map_to_the_stored_columns() -> None:
    sym = occ("SPY", date(2026, 12, 18), "P", 650.5)
    snap = real_snapshot(650.5, "P")
    df, stats = m.snapshots_frame({sym: snap}, SNAP)
    r = df.iloc[0]
    assert stats == {"unparsed_symbol": 0, "unparsed_ts": 0}
    assert (r.contract, r.root, r.expiry, r.option_type, r.strike) == (
        sym, "SPY", date(2026, 12, 18), "P", 650.5)
    assert (r.bid, r.ask, r.bid_size, r.ask_size) == (1.0, 1.1, 10, 12)
    assert (r.bid_exchange, r.ask_exchange, r.quote_condition) == ("C", "M", "A")
    assert (r.last_price, r.last_size, r.last_exchange, r.last_condition) == (1.05, 3, "C", "I")
    assert (r.iv, r.delta, r.gamma, r.theta, r.vega, r.rho) == (0.25, -0.5, 0.01, -0.2, 0.3, 0.05)
    assert (r.day_volume, r.day_trade_count) == (100, 7)
    assert r.quote_ts == pd.Timestamp("2026-11-20T21:00:00.123456Z")   # us, ns truncated
    assert r.last_ts == pd.Timestamp(TRADE_TS)


def test_both_timestamp_shapes_parse_in_both_orders_and_garbage_is_counted() -> None:
    for order in ([TRADE_TS, SESSION_TS], [SESSION_TS, TRADE_TS]):
        out, bad = m._parse_ts(pd.Series(order))
        assert out.notna().all() and bad == 0, order
    out, bad = m._parse_ts(pd.Series([SESSION_TS, "yesterday-ish", None]))
    assert bad == 1 and out.isna().tolist() == [False, True, True]


def test_a_stale_daily_bar_is_not_todays_volume() -> None:
    snap = real_snapshot(700, "C")
    snap["dailyBar"]["t"] = "2026-10-16T04:00:00Z"        # the SPX-root shape seen live
    df, _ = m.snapshots_frame({occ("SPY", date(2026, 12, 18), "C", 700): snap}, SNAP)
    assert pd.isna(df.iloc[0].day_volume) and pd.isna(df.iloc[0].day_trade_count)


def test_occ_parse_handles_adjusted_roots_fractional_strikes_and_garbage() -> None:
    p = m.parse_occ(pd.Series(["XSP261211C00687500", "AAPL1261218P00150000", "NOT-A-SYMBOL"]))
    assert p.root.tolist()[:2] == ["XSP", "AAPL1"] and pd.isna(p.root.iloc[2])
    assert p.strike.tolist()[:2] == [687.5, 150.0]
    assert p.expiry.tolist()[:2] == [date(2026, 12, 11), date(2026, 12, 18)]
    assert p.option_type.tolist()[:2] == ["C", "P"]


def test_contract_listing_maps_open_interest_and_style() -> None:
    c = m.contracts_frame([{"symbol": "SPY261218C00700000", "root_symbol": "SPY",
                            "expiration_date": "2026-12-18", "style": "american",
                            "open_interest": "2509", "open_interest_date": "2026-11-18"},
                           {"symbol": "SPY261218P00700000", "root_symbol": "SPY",
                            "expiration_date": "2026-12-18", "style": "american",
                            "open_interest": None, "open_interest_date": None}])
    assert c.open_interest.tolist()[0] == 2509 and pd.isna(c.open_interest.iloc[1])
    assert c.open_interest_date.tolist() == [date(2026, 11, 18), None]
    assert c["style"].tolist() == ["american", "american"]


# ───────────────────────────── 2. the real-quote rule ─────────────────────────────

def test_a_normal_two_sided_quote_is_real() -> None:
    assert is_real()


def test_a_ZERO_quote_row_is_not_real() -> None:
    assert not is_real(bid=0.0, ask=0.0, last_price=0.0)


def test_a_ONE_DOLLAR_placeholder_ask_with_no_bid_and_no_trade_is_not_real() -> None:
    assert not is_real(bid=0.0, ask=1.00, last_price=np.nan, last_ts=pd.NaT)


def test_the_zero_and_placeholder_shapes_end_to_end_through_the_flattener() -> None:
    snaps = {occ("SPY", date(2026, 12, 18), "C", 700): zero_snapshot(700, "C"),
             occ("SPY", date(2026, 12, 18), "P", 700): placeholder_snapshot(700, "P")}
    df, _ = m.snapshots_frame(snaps, SNAP)
    df = df.assign(snap_date="2026-11-20", underlying="SPY", ref_price=700.0)
    assert not m.real_quote_mask(df).any()


def test_a_zero_bid_with_a_fresh_trade_and_a_sane_ask_is_real() -> None:
    assert is_real(bid=0.0, ask=0.05, last_price=0.03)


def test_a_zero_bid_with_a_STALE_trade_is_not_real() -> None:
    assert not is_real(bid=0.0, ask=0.05, last_price=0.03, last_ts=pd.Timestamp(STALE_TS))


def test_a_STALE_quote_is_not_real_even_with_a_bid() -> None:
    assert not is_real(quote_ts=pd.Timestamp(STALE_TS))


def test_the_session_is_the_ET_day_not_the_UTC_day() -> None:
    assert is_real(quote_ts=pd.Timestamp("2026-11-21T00:30:00Z"))      # 19:30 ET on 11-20
    assert not is_real(quote_ts=pd.Timestamp("2026-11-20T04:30:00Z"))  # 23:30 ET on 11-19


def test_a_missing_quote_time_is_not_real() -> None:
    assert not is_real(quote_ts=pd.NaT)


def test_crossed_missing_and_out_of_bound_asks_are_not_real() -> None:
    assert not is_real(bid=2.0, ask=1.5)                               # crossed
    assert not is_real(ask=np.nan)                                     # one-sided bid
    assert not is_real(option_type="C", ref_price=700.0, ask=700.01, bid=1.0)   # call > S
    assert not is_real(option_type="P", strike=650.0, ask=650.01, bid=1.0)      # put > K
    assert is_real(option_type="P", strike=650.0, ask=649.99, bid=1.0)


def test_bad_implied_vol_is_not_real_unless_the_feed_has_none_for_that_underlying() -> None:
    for bad in (np.nan, 0.0, -0.1, np.inf):
        assert not is_real(iv=bad), bad
    assert is_real(no_iv=("XSP",), underlying="XSP", iv=np.nan)
    assert not is_real(no_iv=("XSP",), underlying="SPY", iv=np.nan)


def test_the_rule_is_vectorized_over_mixed_rows() -> None:
    df = pd.concat([quote_frame(), quote_frame(bid=0.0, ask=0.0, last_price=0.0),
                    quote_frame(iv=np.nan)], ignore_index=True)
    assert m.real_quote_mask(df).tolist() == [True, False, False]
    assert not m.real_quote_mask(df.iloc[0:0]).any()


# ───────────────────────────── 3. calendar and expiries ─────────────────────────────

def test_rule_calendar_matches_the_paper_fallback_for_2026_and_known_edges() -> None:
    from paper_trader.market_calendar import _FALLBACK_HOLIDAYS_2026
    assert m.nyse_holidays(2026) == frozenset(_FALLBACK_HOLIDAYS_2026)
    assert date(2027, 3, 26) in m.nyse_holidays(2027)          # Good Friday 2027
    assert date(2027, 12, 24) in m.nyse_holidays(2027)         # Christmas on a Saturday
    assert date(2021, 12, 31) not in m.nyse_holidays(2021)     # Sat New Year: no Friday close
    assert date(2021, 6, 18) not in m.nyse_holidays(2021)      # no Juneteenth before 2022
    assert not m.is_trading_day_rules(date(2026, 11, 21))      # Saturday
    assert m.previous_trading_day_rules(date(2026, 11, 23)) == date(2026, 11, 20)
    assert m.previous_trading_day_rules(date(2026, 11, 27)) == date(2026, 11, 25)


def test_expiry_rule_takes_fridays_then_third_friday_monthlies() -> None:
    dailies = [SNAP + timedelta(days=i) for i in range(0, 101)
               if m.is_trading_day_rules(SNAP + timedelta(days=i))]
    got = m.select_expiries(dailies, SNAP, 4, 2)
    assert got == [date(2026, 11, 27), date(2026, 12, 4), date(2026, 12, 11),
                   date(2026, 12, 18), date(2027, 1, 15), date(2027, 2, 19)]
    assert SNAP not in got


def test_expiry_rule_moves_a_holiday_friday_expiry_to_thursday() -> None:
    d0 = date(2026, 6, 1)                     # Juneteenth 2026 is the third Friday of June
    dailies = [d0 + timedelta(days=i) for i in range(0, 120)
               if m.is_trading_day_rules(d0 + timedelta(days=i))]
    got = m.select_expiries(dailies, d0, 4, 1)
    assert date(2026, 6, 18) in got and date(2026, 6, 19) not in got
    assert m.select_expiries(dailies, d0, 2, 1)[-1] == date(2026, 6, 18)   # it is the monthly


def test_expiry_rule_with_nothing_listed_returns_nothing() -> None:
    assert m.select_expiries([SNAP], SNAP, 4, 2) == []


# ───────────────────────────── 4. judge, dedup, write, size ─────────────────────────────

def _rows(sym: str, n: int, real: bool, snap_ts: str = "2026-11-20T23:30:00Z") -> pd.DataFrame:
    return pd.DataFrame({"snap_date": "2026-11-20", "underlying": sym,
                         "contract": [f"{sym}-{i}" for i in range(n)], "real_quote": real,
                         "snap_ts": pd.Timestamp(snap_ts), "expiry": date(2026, 12, 18),
                         "option_type": "C", "strike": np.arange(n, dtype=float)})


def test_judge_fails_closed_on_zero_real_and_writes_nothing() -> None:
    v = m.judge(_rows("SPY", 50, False), ["SPY"], 3, 0.9)
    assert (v.status, v.write, v.n_real) == ("FAILED", False, 0)
    assert "nothing written" in v.message


def test_judge_fails_on_thin_coverage_but_keeps_the_rows() -> None:
    df = pd.concat([_rows("SPY", 5, True), _rows("AAPL", 2, True)])
    v = m.judge(df, ["SPY", "AAPL", "XSP"], 3, 0.9)
    assert (v.status, v.write) == ("FAILED", True)
    assert v.covered == ["SPY"] and v.missing == ["AAPL", "XSP"]
    assert "coverage 1/3" in v.message and "AAPL, XSP" in v.message
    ok = m.judge(df, ["SPY", "AAPL"], 2, 0.9)
    assert ok.status == "OK"


def test_a_REQUIRED_underlying_not_covered_fails_even_above_the_floor() -> None:
    names = [f"S{i:02d}" for i in range(19)]
    df = pd.concat([_rows(n, 5, True) for n in names] + [_rows("XSP", 5, False)])
    declared = [*names, "XSP"]
    assert m.judge(df, declared, 3, 0.9).status == "OK"            # 19/20 = 95 % >= floor
    v = m.judge(df, declared, 3, 0.9, required=("SPY", "XSP"))
    assert (v.status, v.write) == ("FAILED", True)
    assert "required underlying not covered: XSP" in v.message


def test_a_MOSTLY_JUNK_underlying_is_not_covered_under_the_share_floor() -> None:
    df = pd.concat([_rows("SPY", 50, True), _rows("AAPL", 12, True),
                    _rows("AAPL", 88, False).assign(contract=lambda d: "J" + d.contract)])
    assert m.judge(df, ["SPY", "AAPL"], 10, 0.9).status == "OK"     # 12 real >= 10
    v = m.judge(df, ["SPY", "AAPL"], 10, 0.9, min_share=0.30)      # but only 12 % real
    assert v.status == "FAILED" and v.missing == ["AAPL"]


def test_dedup_never_replaces_a_real_row_with_a_non_real_one() -> None:
    early_real = _rows("SPY", 3, True, "2026-11-20T21:00:00Z")
    late_junk = _rows("SPY", 3, False, "2026-11-20T23:30:00Z")
    late_real = _rows("SPY", 3, True, "2026-11-20T23:45:00Z")
    out = m.dedup([early_real, late_junk])
    assert len(out) == 3 and out.real_quote.all()
    assert (out.snap_ts == pd.Timestamp("2026-11-20T21:00:00Z")).all()
    out2 = m.dedup([early_real, late_junk, late_real])
    assert (out2.snap_ts == pd.Timestamp("2026-11-20T23:45:00Z")).all()
    assert len(m.dedup([_rows("SPY", 3, True), _rows("AAPL", 3, True)])) == 6


def _realistic_day(n: int, seed: int = 7) -> pd.DataFrame:
    """Realistically-shaped rows: cent prices, 4-decimal greeks, session-time stamps."""
    rng = np.random.default_rng(seed)
    unds = np.array(["SPY", "QQQ", "IWM", "AAPL", "MSFT"])[rng.integers(0, 5, n)]
    strike = np.round(rng.uniform(400, 800, n))
    bid = np.round(rng.gamma(1.0, 5.0, n), 2)
    base = pd.Timestamp("2026-11-20T20:59:00Z")
    df = pd.DataFrame({
        "snap_date": "2026-11-20", "snap_ts": pd.Timestamp("2026-11-20T23:30:00Z"),
        "underlying": unds, "root": unds, "expiry": date(2026, 12, 18), "strike": strike,
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
        "underlying_day_close": 693.06, "ref_price": 693.38, "ref_source": "underlying",
        "feed": "indicative", "real_quote": True, "quote_rule": "v1"})
    df["contract"] = [f"{u}261218{c}{i:08d}" for i, (u, c) in
                      enumerate(zip(df.underlying, df.option_type))]
    return df


def test_write_day_is_atomic_schema_exact_and_merges_a_rerun(tmp_path: Path) -> None:
    day = _realistic_day(400).drop_duplicates("contract")
    path, nbytes, nrows = m.write_day(day, tmp_path, SNAP)
    assert path == tmp_path / "options_snapshot_2026-11-20.parquet" and nbytes > 0
    assert pq.read_schema(path).equals(m.SCHEMA, check_metadata=False)
    assert not list(tmp_path.glob(".*"))                       # no temp file left behind
    m.write_day(day.iloc[:50], tmp_path, SNAP)                 # a re-run of a subset
    assert len(pd.read_parquet(path)) == nrows                 # deduped, nothing lost
    m.append_run_log(tmp_path, {"snap_date": "2026-11-20", "status": "OK"})
    m.write_day(day.assign(snap_date="2026-11-23"), tmp_path, date(2026, 11, 23))
    both = pd.read_parquet(tmp_path)                           # the run log is ignored
    assert set(both.snap_date) == {"2026-11-20", "2026-11-23"} and len(both) == 2 * nrows


def test_a_realistic_day_is_small_and_zstd_compressed(tmp_path: Path) -> None:
    """Budget lock: the real 2026-11-20 file measured ~51 bytes/row; the task's ceiling is
    ~20 MB/day. A ~17k-row day must stay under 2 MB here (synthetic rows compress worse)."""
    n = 17_000
    path, nbytes, _ = m.write_day(_realistic_day(n).drop_duplicates("contract"), tmp_path, SNAP)
    rows = pq.ParquetFile(path).metadata.num_rows
    codec = pq.ParquetFile(path).metadata.row_group(0).column(0).compression
    assert codec == "ZSTD"
    assert nbytes / rows < 110, f"{nbytes / rows:.1f} bytes/row"
    assert nbytes < 2_000_000


# ───────────────────────────── 5. one run, end to end ─────────────────────────────

def run(tmp_path: Path, market: Market, cfg: Optional[m.ArchiveConfig] = None,
        now: datetime = NOW) -> m.RunOutcome:
    return m.run_archive(cfg or cfg_for(), client_for(market), tmp_path, now)


def runs(tmp_path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (tmp_path / m.RUN_LOG_NAME).read_text().splitlines()]


def test_a_healthy_day_writes_real_rows_for_every_underlying(tmp_path: Path) -> None:
    out = run(tmp_path, Market())
    assert (out.exit_code, out.status) == (0, "OK"), out.message
    df = pd.read_parquet(m.day_path(tmp_path, SNAP))
    assert len(df) == 3 * 6 * 7 * 2 and df.real_quote.all()
    assert sorted(df.expiry.unique()) == [date(2026, 11, 27), date(2026, 12, 4),
                                          date(2026, 12, 11), date(2026, 12, 18),
                                          date(2027, 1, 15), date(2027, 2, 19)]
    assert set(df.feed) == {"indicative"} and set(df.quote_rule) == {"v1"}
    assert set(df.snap_date) == {"2026-11-20"}
    assert (df.open_interest == 1234).all()
    rec = runs(tmp_path)[-1]
    assert rec["status"] == "OK" and rec["n_real"] == len(df) and rec["file_bytes"] > 0


def test_the_index_stores_no_proxy_as_its_price_and_needs_no_iv(tmp_path: Path) -> None:
    run(tmp_path, Market())
    df = pd.read_parquet(m.day_path(tmp_path, SNAP))
    x = df[df.underlying == "XSP"]
    assert len(x) and x.real_quote.all() and x.iv.isna().all()
    assert x.underlying_price.isna().all() and x.underlying_price_ts.isna().all()
    assert set(x.ref_source) == {"proxy:SPY"} and set(x["style"]) == {"european"}
    s = df[df.underlying == "SPY"]
    assert (s.underlying_price == 700.0).all() and set(s.ref_source) == {"underlying"}
    assert (s.underlying_day_close == 699.0).all()


def test_ZERO_real_quotes_fails_closed_and_writes_nothing(tmp_path: Path) -> None:
    out = run(tmp_path, Market(snapshot=lambda u, k, cp: zero_snapshot(k, cp)))
    assert (out.exit_code, out.status) == (1, "FAILED")
    assert "0 real quotes" in out.message and "nothing written" in out.message
    assert not list(tmp_path.glob("*.parquet"))
    assert runs(tmp_path)[-1]["status"] == "FAILED"


def test_PLACEHOLDER_asks_fail_closed_too(tmp_path: Path) -> None:
    out = run(tmp_path, Market(snapshot=lambda u, k, cp: placeholder_snapshot(k, cp)))
    assert out.status == "FAILED" and not list(tmp_path.glob("*.parquet"))


def test_thin_coverage_fails_loud_but_keeps_what_came_back(tmp_path: Path) -> None:
    mk = Market(fail={"AAPL": FakeResp(500, {"message": "upstream"})})
    out = run(tmp_path, mk)
    assert (out.exit_code, out.status) == (1, "FAILED")
    assert "coverage 2/3" in out.message and "AAPL" in out.message
    df = pd.read_parquet(m.day_path(tmp_path, SNAP))
    assert set(df.underlying) == {"SPY", "XSP"}
    assert "AAPL" in runs(tmp_path)[-1]["errors"]


def test_a_junk_underlying_is_not_covered(tmp_path: Path) -> None:
    junk = Market(snapshot=lambda u, k, cp: zero_snapshot(k, cp) if u == "AAPL"
                  else real_snapshot(k, cp))
    out = run(tmp_path, junk)
    assert out.status == "FAILED" and runs(tmp_path)[-1]["missing"] == ["AAPL"]


def test_a_WIPED_required_index_fails_the_day_and_keeps_the_rest(tmp_path: Path) -> None:
    """The 2026-11-20 close shape: XSP quotes zeroed (0/0, size 0, exchange '?'), freshly
    stamped. With a lenient floor the day would pass; XSP is required, so it fails."""
    def wipe(u: str, k: float, cp: str) -> dict[str, Any]:
        s = real_snapshot(k, cp)
        if u == "XSP":
            s["latestQuote"].update(bp=0.0, ap=0.0, bs=0, **{"as": 0}, bx="?", ax="?")
        return s
    lenient = cfg_for(floor=0.5)
    assert run(tmp_path / "a", Market(snapshot=wipe), lenient).status == "OK"
    strict = cfg_for(floor=0.5, required=("SPY", "XSP"))
    out = run(tmp_path / "b", Market(snapshot=wipe), strict)
    assert out.status == "FAILED" and "required underlying not covered: XSP" in out.message
    df = pd.read_parquet(m.day_path(tmp_path / "b", SNAP))
    assert not df[df.underlying == "XSP"].real_quote.any() and df[df.underlying == "SPY"].real_quote.all()


def test_a_NON_TRADING_day_skips_without_a_single_market_data_call(tmp_path: Path) -> None:
    mk = Market()
    sat = datetime(2026, 11, 21, 23, 30, tzinfo=timezone.utc)
    out = run(tmp_path, mk, now=sat)
    assert (out.exit_code, out.status) == (0, "SKIP")
    assert [urlparse(c[0]).path for c in mk.calls] == ["/v2/calendar"]
    assert runs(tmp_path)[-1]["status"] == "SKIP" and not list(tmp_path.glob("*.parquet"))


def test_an_ad_hoc_closure_from_alpacas_calendar_skips(tmp_path: Path) -> None:
    out = run(tmp_path, Market(calendar=[]))                   # a weekday Alpaca says closed
    assert out.status == "SKIP" and runs(tmp_path)[-1]["calendar_source"] == "alpaca"


def test_a_broken_calendar_falls_back_to_the_rules(tmp_path: Path) -> None:
    out = run(tmp_path, Market(calendar=FakeResp(404, {"message": "gone"})))
    assert out.status == "OK" and runs(tmp_path)[-1]["calendar_source"] == "rules"
    sat = datetime(2026, 11, 21, 23, 30, tzinfo=timezone.utc)
    out2 = run(tmp_path, Market(calendar=FakeResp(404, {"message": "gone"})), now=sat)
    assert out2.status == "SKIP"


def test_rejected_keys_fail_loud_and_are_logged(tmp_path: Path) -> None:
    mk = Market(first_status={"/v2/stocks/snapshots": [FakeResp(401, {"message": "unauth"})]})
    out = run(tmp_path, mk)
    assert out.status == "FAILED" and runs(tmp_path)[-1]["status"] == "FAILED"
    assert "rejected the keys" in json.dumps(runs(tmp_path)[-1])


def test_429_is_retried_after_the_reset_and_counted(tmp_path: Path) -> None:
    mk = Market(first_status={"/v1beta1/options/snapshots/SPY": [
        FakeResp(429, {"message": "too many"}, {"X-RateLimit-Limit": "200"})]})
    clk = FakeClock()
    client = client_for(mk, clk)
    out = m.run_archive(cfg_for(), client, tmp_path, NOW)
    assert out.status == "OK" and client.n_429 == 1 and client.n_retries == 1


def test_a_persistent_5xx_gives_up_instead_of_hanging() -> None:
    mk = Market()
    clk = FakeClock()
    c = client_for(mk, clk)
    mk.first_status["/v2/calendar"] = [FakeResp(503, {"message": "down"}) for _ in range(9)]
    with pytest.raises(m.ApiError, match="gave up after 4 attempts"):
        c.calendar(SNAP, SNAP)
    assert c.requests["paper-api.alpaca.markets"] == 4


def test_requests_are_paced_under_the_measured_limit() -> None:
    mk = Market()
    clk = FakeClock()
    c = client_for(mk, clk)
    for _ in range(5):
        c.calendar(SNAP, SNAP)
    gaps = 60.0 / m.TRADE_PER_MIN
    assert sum(clk.slept) == pytest.approx(4 * gaps)
    assert m.DATA_PER_MIN < 200 and m.TRADE_PER_MIN < 200


def test_pagination_is_followed_and_a_repeated_token_is_an_error(tmp_path: Path) -> None:
    out = run(tmp_path, Market(page_size=5))
    assert out.status == "OK"
    assert len(pd.read_parquet(m.day_path(tmp_path, SNAP))) == 3 * 6 * 7 * 2
    mk = Market()
    loop = FakeResp(payload={"snapshots": {}, "next_page_token": "same"})
    mk.first_status["/v1beta1/options/snapshots/SPY"] = [loop, loop]
    with pytest.raises(m.ApiError, match="repeated page token"):
        client_for(mk).chain("SPY", date(2026, 12, 18), 1.0, 2.0, "indicative")


def test_a_non_object_payload_is_that_underlyings_error_not_a_crash(tmp_path: Path) -> None:
    mk = Market(first_status={"/v1beta1/options/snapshots/SPY": [FakeResp(payload=[1, 2])]})
    out = run(tmp_path, mk)
    assert out.status == "FAILED" and "coverage 2/3" in out.message
    assert "payload is not an object" in runs(tmp_path)[-1]["errors"]["SPY"]


def test_the_feed_and_filters_are_sent_and_only_GET_is_used(tmp_path: Path) -> None:
    mk = Market()
    run(tmp_path, mk)
    chain = [p for u, p, _ in mk.calls if "/v1beta1/options/snapshots/" in u]
    assert chain and all(p["feed"] == "indicative" and "expiration_date" in p for p in chain)
    stocks = [p for u, p, _ in mk.calls if u.endswith("/v2/stocks/snapshots")]
    assert stocks[0]["feed"] == "delayed_sip"
    assert not hasattr(m.AlpacaReadClient, "post")


# ───────────────────────────── 6. the local verifier ─────────────────────────────

def _good_store(tmp_path: Path, session: date, cfg: m.ArchiveConfig) -> None:
    mk = Market()
    now = datetime.combine(session, datetime.min.time(), tzinfo=m.ET).replace(hour=18, minute=30)
    stamp = f"{session.isoformat()}T21:00:00Z"

    def snap(u: str, k: float, cp: str) -> dict[str, Any]:
        s = real_snapshot(k, cp)
        s["latestQuote"]["t"] = stamp
        return s

    mk.snapshot = snap
    out = m.run_archive(cfg, client_for(mk), tmp_path, now.astimezone(timezone.utc))
    assert out.status == "OK", out.message


def test_verifier_passes_a_good_trading_day_and_fails_a_missing_one(tmp_path: Path) -> None:
    cfg = cfg_for()
    ok, msg = m.verify_store(tmp_path, cfg, SNAP)
    assert not ok and "no capture for session 2026-11-20" in msg
    _good_store(tmp_path, SNAP, cfg)
    ok, msg = m.verify_store(tmp_path, cfg, SNAP)
    assert ok and msg.startswith("OK"), msg


def test_verifier_checks_the_PREVIOUS_session_on_a_weekend(tmp_path: Path) -> None:
    cfg = cfg_for()
    ok, msg = m.verify_store(tmp_path, cfg, date(2026, 11, 21))
    assert ok and msg.startswith("SKIP"), "an empty store before the first capture is not a miss"
    _good_store(tmp_path, date(2026, 11, 19), cfg)             # Thursday only: Friday missed
    ok, msg = m.verify_store(tmp_path, cfg, date(2026, 11, 21))
    assert not ok and "session 2026-11-20" in msg
    _good_store(tmp_path, SNAP, cfg)
    assert m.verify_store(tmp_path, cfg, date(2026, 11, 22))[0]   # Sunday reads Friday


def test_verifier_honours_the_archivers_alpaca_closure_skip(tmp_path: Path) -> None:
    cfg = cfg_for()
    _good_store(tmp_path, date(2026, 11, 19), cfg)
    run(tmp_path, Market(calendar=[]))                         # Friday: Alpaca says closed
    ok, msg = m.verify_store(tmp_path, cfg, SNAP)
    assert ok and "session 2026-11-19" in msg, msg


def test_verifier_rejudges_by_CONTENT_not_the_stored_flag(tmp_path: Path) -> None:
    """A file whose rows all CLAIM real_quote=True but hold zero quotes must fail."""
    cfg = cfg_for()
    _good_store(tmp_path, SNAP, cfg)
    path = m.day_path(tmp_path, SNAP)
    df = pd.read_parquet(path)
    df[["bid", "ask", "last_price"]] = 0.0
    pq.write_table(m.to_table(df.assign(real_quote=True)), path)
    ok, msg = m.verify_store(tmp_path, cfg, SNAP)
    assert not ok and "0 real quotes" in msg


def test_the_altdata_verifier_runs_the_options_check(tmp_path: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.verify_altdata_snapshot as v
    from paper_trader.altdata_archive import _SNAPSHOT_FRESHNESS

    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    for _, rel, col in _SNAPSHOT_FRESHNESS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({col: [today]}).to_parquet(tmp_path / rel)
    monkeypatch.setattr(v, "ROOT", tmp_path)
    assert v.main() == 1, "no options store on a trading day (or a missed session) must fail"
    cfg = m.load_config(m.DEFAULT_CONFIG)
    now_et = datetime.now(m.ET).date()
    session = now_et if m.is_trading_day_rules(now_et) else m.previous_trading_day_rules(now_et)
    mk = Market(spots={u.symbol: 100.0 for u in cfg.underlyings})
    stamp = f"{session.isoformat()}T21:00:00Z"

    def snap(u: str, k: float, cp: str) -> dict[str, Any]:
        s = real_snapshot(k, cp)
        s["latestQuote"]["t"] = stamp
        return s

    mk.snapshot = snap
    when = datetime.combine(session, datetime.min.time(), tzinfo=m.ET).replace(hour=18)
    out = m.run_archive(cfg, client_for(mk), tmp_path / v.OPTIONS_REL, when.astimezone(timezone.utc))
    assert out.status == "OK", out.message
    assert v.main() == 0


# ───────────────────────────── 7. CLI, keys, config ─────────────────────────────

def test_the_committed_config_loads_and_stays_within_the_declared_bounds() -> None:
    cfg = m.load_config(m.DEFAULT_CONFIG)
    singles = [u for u in cfg.underlyings if u.kind == "stock"]
    assert len(singles) <= 50 and len(cfg.declared) == len(set(cfg.declared))
    assert {"SPY", "QQQ", "IWM", "XSP"} <= set(cfg.declared)
    assert cfg.no_iv == frozenset({"XSP"}) and cfg.feed == "indicative"
    assert cfg.coverage_floor == 0.90 and cfg.min_real_share == 0.30
    assert cfg.required == ["SPY", "QQQ", "IWM", "XSP"]


def test_a_missing_or_broken_config_is_exit_2(tmp_path: Path,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    assert m.main(["--config", str(tmp_path / "nope.json"), "--out-dir", str(tmp_path)]) == 2
    (tmp_path / "bad.json").write_text('{"underlyings": []}')
    assert m.main(["--config", str(tmp_path / "bad.json"), "--out-dir", str(tmp_path)]) == 2
    assert "FAILED options: config" in capsys.readouterr().out


def test_missing_keys_are_exit_2_and_name_no_value(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch,
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    rc = m.main(["--env-file", str(tmp_path / "absent.env"), "--out-dir", str(tmp_path)])
    assert rc == 2 and "ALPACA_API_KEY" in capsys.readouterr().out


def test_no_key_or_secret_ever_reaches_stdout_or_the_run_log(tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SECRET)
    mk = Market(fail={"AAPL": FakeResp(403, {"message": "forbidden"})},
                first_status={"/v2/calendar": [FakeResp(401, {"message": "unauthorized"})]})
    real_client = m.AlpacaReadClient
    monkeypatch.setattr(m, "AlpacaReadClient",
                        lambda k, s: real_client(k, s, session=mk, sleep=lambda _: None))  # type: ignore[arg-type]
    m.main(["--out-dir", str(tmp_path), "--underlyings", "SPY,AAPL"])
    seen = capsys.readouterr()
    blob = seen.out + seen.err + (tmp_path / m.RUN_LOG_NAME).read_text()
    assert KEY not in blob and SECRET not in blob
    assert all(h.get("APCA-API-KEY-ID") == KEY for _, _, h in mk.calls)   # keys only in headers
    assert all(KEY not in json.dumps(p) for _, p, _ in mk.calls)


def test_verify_flag_makes_no_api_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, "AlpacaReadClient", lambda *a, **k: pytest.fail("API used"))
    assert m.main(["--verify", "--out-dir", str(tmp_path)]) in (0, 1)


# ───────────────────────────── 8. the launchd wrapper ─────────────────────────────

def _run_wrapper(tmp_path: Path, rc_options: int, rc_verify: int = 0,
                 drill: bool = False) -> tuple[str, str]:
    """Execute a COPY of the real wrapper with a stub interpreter and stub alarm channels.
    The copy differs only in REPO (a temp dir) and the aws fallback paths (the stub), so no
    real archiver, SNS message or notification can run."""
    repo, stubs = tmp_path / "repo", tmp_path / "stubs"
    (repo / ".venv/bin").mkdir(parents=True)
    stubs.mkdir()
    calls = tmp_path / "calls.txt"
    py = repo / ".venv/bin/python"
    py.write_text("#!/bin/bash\n"
                  f'echo "PY $1" >> "{calls}"\n'
                  'case "$1" in\n'
                  f'  *archive_options_snapshots.py) exit {rc_options};;\n'
                  f'  *verify_altdata_snapshot.py) exit {rc_verify};;\n'
                  '  *) exit 0;;\nesac\n')
    for name in ("aws", "osascript"):
        (stubs / name).write_text(f'#!/bin/bash\necho "{name.upper()} $*" >> "{calls}"\n')
    for f in (py, stubs / "aws", stubs / "osascript"):
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
    env = {**os.environ, "PATH": f"{stubs}:/usr/bin:/bin:/usr/sbin:/sbin"}
    env.pop("ARCHONDEX_ALARM_DRILL", None)
    if drill:
        env["ARCHONDEX_ALARM_DRILL"] = "1"
    calls.touch()
    subprocess.run(["/bin/bash", str(wrapper)], env=env, check=True, timeout=60)
    logs = list((repo / "data/macro_data/alt/logs").glob("archive_*.log"))
    assert len(logs) == 1
    return logs[0].read_text(), calls.read_text()


def test_the_wrapper_alarms_on_the_options_rc_ALONE(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, rc_options=1)
    assert "options=1" in log and "ALTDATA_ARCHIVER_FAILED" in log
    assert "AWS sns publish" in calls and "options=1" in calls
    order = [line.split()[1] for line in calls.splitlines() if line.startswith("PY ")]
    assert order.index("scripts/archive_options_snapshots.py") < order.index(
        "scripts/verify_altdata_snapshot.py"), "the verifier must read the file just written"


def test_the_wrapper_stays_quiet_when_every_rc_is_zero(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, rc_options=0)
    assert "options=0" in log and "ALTDATA_ARCHIVER_FAILED" not in log
    assert "AWS" not in calls and "OSASCRIPT" not in calls


def test_the_wrapper_drill_covers_the_options_rc(tmp_path: Path) -> None:
    log, calls = _run_wrapper(tmp_path, rc_options=0, drill=True)
    assert "options=99" in log and "ALTDATA_ARCHIVER_FAILED" in log
    assert "PY " not in calls, "a drill runs no archiver"
    assert "AWS sns publish" in calls and "options=99" in calls
