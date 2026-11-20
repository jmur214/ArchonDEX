"""
scripts/archive_options_snapshots.py
====================================
T-416 (2026-11-20): a daily snapshot archive of option quotes, implied vol and greeks.

Why: Alpaca serves option bars and trade prints back to ~2024-01, but NO historical quotes
(``/v1beta1/options/quotes`` is a 404), and its implied vol and greeks exist only as CURRENT
values on the snapshot/chain endpoints. No free source sells an options history with quotes.
So the only free way to own one is to save the snapshots every trading day, starting now
(owner approval 2026-11-20; census ``docs/Sources/ideas_census_desk_t410_2026-11-20.md`` §4.1).

What one run does (all GETs; nothing is ever posted to any API):
  1. Trading-day gate: Alpaca's ``/v2/calendar`` (authoritative, includes ad-hoc closures);
     if that call fails, a rule-based NYSE holiday calendar. A non-trading day prints SKIP and
     exits 0, so weekends and holidays never alarm.
  2. Reference prices: one ``/v2/stocks/snapshots`` call on the ``delayed_sip`` feed (the
     free tier refuses recent ``sip``). An index (XSP) has no price on Alpaca; it declares a
     proxy (SPY), used ONLY for the strike band and the call-ask bound, and its
     ``underlying_price`` is stored as null, never as the proxy.
  3. Per underlying (``config/options_archive_universe.json``): the trading API's
     ``/v2/options/contracts`` lists expiries and open interest; the expiry rule picks the
     next weekly and monthly expiries; one ``/v1beta1/options/snapshots/{u}`` call per expiry
     (``feed=indicative``, the free feed — OPRA is a 403 on this account) fetches quotes,
     last trade, implied vol and greeks for strikes within the band.
  4. The real-quote rule (``real_quote_mask``) judges every row by a USABLE value, never by a
     field being present (the 2026-11-19 Kalshi defect: a "not null" check passed $0 parlay
     quotes as prices for five months).
  5. Fail closed: zero real quotes -> FAILED, nothing written. Fewer than ``coverage_floor``
     of the declared underlyings covered -> FAILED, the rows that came back are kept.

Output: one parquet file per ET session date, ``<out>/options_snapshot_YYYY-MM-DD.parquet``
(explicit pyarrow schema, zstd), deduped by (snap_date, contract): a real-quote row beats a
non-real one, then the later snapshot wins. One JSON line per run is appended to
``<out>/_archive_runs.jsonl`` (the underscore keeps parquet dataset readers off it).

Exit codes: 0 = OK or SKIP; 1 = FAILED (no real quotes, coverage below the floor, or a
--verify failure); 2 = broken (missing keys or config, or a crash). The launchd wrapper
``scripts/run_altdata_archivers.sh`` alarms on any non-zero code.

Usage:
  .venv/bin/python scripts/archive_options_snapshots.py                  # production run
  .venv/bin/python scripts/archive_options_snapshots.py --out-dir /tmp/opt_smoke
  .venv/bin/python scripts/archive_options_snapshots.py --verify         # store check only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data" / "macro_data" / "options"
DEFAULT_CONFIG = ROOT / "config" / "options_archive_universe.json"
DEFAULT_ENV_FILE = ROOT / ".env"

ET = ZoneInfo("America/New_York")
DATA_URL = "https://data.alpaca.markets"
# Calendar and contract listings are reference data, identical on paper and live; the paper
# host is used so this script never addresses a live-account endpoint.
TRADE_URL = "https://paper-api.alpaca.markets"

QUOTE_RULE = "v1"
FILE_PREFIX = "options_snapshot_"
RUN_LOG_NAME = "_archive_runs.jsonl"
TAG = "[options-archive]"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BROKEN = 2

# Measured 2026-11-20 from X-RateLimit-Limit: 200/min on data.alpaca.markets (free plan) and
# 200/min on the paper trading API's /v2/options/contracts (its /v2/calendar reported 1000).
# Pace below both so a concurrent job on the same key keeps headroom.
DATA_PER_MIN = 170
TRADE_PER_MIN = 170

#: The stored schema. Fixed explicitly so every daily file has identical column types and a
#: directory read (``pd.read_parquet(out_dir)``) never trips on an all-null day.
SCHEMA = pa.schema([
    ("snap_date", pa.string()),            # ET session date of the run, ISO
    ("snap_ts", pa.timestamp("us", tz="UTC")),   # when this underlying's chain was requested
    ("underlying", pa.string()),
    ("contract", pa.string()),             # OCC symbol
    ("root", pa.string()),
    ("expiry", pa.date32()),
    ("strike", pa.float64()),
    ("option_type", pa.string()),          # "C" | "P"
    ("style", pa.string()),                # american | european (contracts endpoint)
    ("bid", pa.float64()),
    ("ask", pa.float64()),
    ("bid_size", pa.int32()),
    ("ask_size", pa.int32()),
    ("bid_exchange", pa.string()),
    ("ask_exchange", pa.string()),
    ("quote_condition", pa.string()),
    ("quote_ts", pa.timestamp("us", tz="UTC")),
    ("last_price", pa.float64()),
    ("last_size", pa.int32()),
    ("last_exchange", pa.string()),
    ("last_condition", pa.string()),
    ("last_ts", pa.timestamp("us", tz="UTC")),
    ("iv", pa.float64()),
    ("delta", pa.float64()),
    ("gamma", pa.float64()),
    ("theta", pa.float64()),
    ("vega", pa.float64()),
    ("rho", pa.float64()),
    ("day_volume", pa.int64()),            # session daily bar; null when no bar this session
    ("day_trade_count", pa.int32()),
    ("open_interest", pa.int64()),         # OCC open interest as of open_interest_date
    ("open_interest_date", pa.date32()),
    ("underlying_price", pa.float64()),    # delayed-SIP latest trade; null for an index
    ("underlying_price_ts", pa.timestamp("us", tz="UTC")),
    ("underlying_day_close", pa.float64()),  # delayed-SIP daily bar close, this session only
    ("ref_price", pa.float64()),           # the price the band and the call-ask bound used
    ("ref_source", pa.string()),           # "underlying" | "proxy:<SYM>"
    ("feed", pa.string()),
    ("real_quote", pa.bool_()),
    ("quote_rule", pa.string()),
])
COLUMNS: list[str] = SCHEMA.names
DEDUP_KEY = ["snap_date", "contract"]
_TS_COLS = ["snap_ts", "quote_ts", "last_ts", "underlying_price_ts"]

# Snapshot JSON paths -> stored column (pd.json_normalize flattens nested keys with ".").
_SNAP_MAP: dict[str, str] = {
    "latestQuote.bp": "bid", "latestQuote.ap": "ask",
    "latestQuote.bs": "bid_size", "latestQuote.as": "ask_size",
    "latestQuote.bx": "bid_exchange", "latestQuote.ax": "ask_exchange",
    "latestQuote.c": "quote_condition", "latestQuote.t": "quote_ts",
    "latestTrade.p": "last_price", "latestTrade.s": "last_size",
    "latestTrade.x": "last_exchange", "latestTrade.c": "last_condition",
    "latestTrade.t": "last_ts",
    "impliedVolatility": "iv",
    "greeks.delta": "delta", "greeks.gamma": "gamma", "greeks.theta": "theta",
    "greeks.vega": "vega", "greeks.rho": "rho",
    "dailyBar.v": "day_volume", "dailyBar.n": "day_trade_count", "dailyBar.t": "_day_bar_ts",
}


# ───────────────────────────── configuration ─────────────────────────────

class ConfigError(RuntimeError):
    """The universe config is missing or malformed: the run cannot know what to expect."""


@dataclass(frozen=True)
class UnderlyingSpec:
    """One declared underlying; an index declares a price proxy and may have no IV."""
    symbol: str
    kind: str
    price_proxy: Optional[str] = None
    iv_expected: bool = True


@dataclass(frozen=True)
class ArchiveConfig:
    """The validated universe config (see config/options_archive_universe.json)."""
    underlyings: tuple[UnderlyingSpec, ...]
    feed: str
    strike_band: float
    n_weekly: int
    n_monthly: int
    horizon_days: int
    coverage_floor: float
    min_real_per_underlying: int
    wall_budget_seconds: float
    md5: str

    @property
    def declared(self) -> list[str]:
        return [u.symbol for u in self.underlyings]

    @property
    def no_iv(self) -> frozenset[str]:
        return frozenset(u.symbol for u in self.underlyings if not u.iv_expected)

    def subset(self, symbols: Collection[str]) -> "ArchiveConfig":
        """The same rules on a declared subset (a smoke run); the subset is the denominator."""
        unknown = set(symbols) - set(self.declared)
        if unknown:
            raise ConfigError(f"not in the declared universe: {sorted(unknown)}")
        keep = tuple(u for u in self.underlyings if u.symbol in set(symbols))
        return ArchiveConfig(keep, self.feed, self.strike_band, self.n_weekly, self.n_monthly,
                             self.horizon_days, self.coverage_floor,
                             self.min_real_per_underlying, self.wall_budget_seconds, self.md5)


def load_config(path: Path) -> ArchiveConfig:
    """Parse and validate the universe config. Every malformation is a ConfigError."""
    try:
        raw_bytes = Path(path).read_bytes()
        raw = json.loads(raw_bytes)
    except FileNotFoundError as e:
        raise ConfigError(f"config not found: {path}") from e
    except (OSError, ValueError) as e:
        raise ConfigError(f"config unreadable: {path}: {type(e).__name__}: {e}") from e
    try:
        unds = tuple(
            UnderlyingSpec(symbol=str(u["symbol"]).upper(), kind=str(u["kind"]),
                           price_proxy=(str(u["price_proxy"]).upper()
                                        if u.get("price_proxy") else None),
                           iv_expected=bool(u.get("iv_expected", True)))
            for u in raw["underlyings"])
        cfg = ArchiveConfig(
            underlyings=unds, feed=str(raw["feed"]), strike_band=float(raw["strike_band"]),
            n_weekly=int(raw["n_weekly"]), n_monthly=int(raw["n_monthly"]),
            horizon_days=int(raw["horizon_days"]), coverage_floor=float(raw["coverage_floor"]),
            min_real_per_underlying=int(raw["min_real_per_underlying"]),
            wall_budget_seconds=float(raw["wall_budget_seconds"]),
            md5=hashlib.md5(raw_bytes).hexdigest())
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"config malformed: {path}: {type(e).__name__}: {e}") from e
    syms = cfg.declared
    if not syms:
        raise ConfigError(f"config declares no underlyings: {path}")
    if len(set(syms)) != len(syms):
        raise ConfigError(f"config declares a symbol twice: {path}")
    if not (0.0 < cfg.strike_band < 1.0 and 0.0 < cfg.coverage_floor <= 1.0
            and cfg.n_weekly >= 1 and cfg.n_monthly >= 0 and cfg.horizon_days >= 7
            and cfg.min_real_per_underlying >= 1 and cfg.wall_budget_seconds > 0):
        raise ConfigError(f"config value out of range: {path}")
    for u in cfg.underlyings:
        if u.kind == "index" and not u.price_proxy:
            raise ConfigError(f"index {u.symbol} declares no price_proxy: {path}")
    return cfg


def load_keys(env_file: Path) -> tuple[str, str]:
    """Alpaca keys from the process environment, else from ``env_file`` (read, not loaded
    into os.environ). Raises KeyError naming only the variable names, never a value."""
    key = os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID")
    sec = os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY")
    if not (key and sec) and Path(env_file).exists():
        from dotenv import dotenv_values
        vals = dotenv_values(env_file)
        key = key or vals.get("ALPACA_API_KEY") or vals.get("APCA_API_KEY_ID")
        sec = sec or vals.get("ALPACA_SECRET_KEY") or vals.get("APCA_API_SECRET_KEY")
    if not (key and sec):
        raise KeyError(f"ALPACA_API_KEY / ALPACA_SECRET_KEY not found in the environment "
                       f"or in {env_file}")
    return str(key), str(sec)


# ───────────────────────────── trading calendar ─────────────────────────────

def _easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous / Meeus-Jones-Butcher algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = (h + ll - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """NYSE observance: a Saturday holiday closes Friday, a Sunday holiday closes Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> frozenset[date]:
    """Full-day NYSE closures by rule (the offline fallback; Alpaca's calendar is primary
    and also carries ad-hoc closures, e.g. a national day of mourning)."""
    hol: set[date] = set()
    ny = date(year, 1, 1)
    if ny.weekday() == 6:
        hol.add(ny + timedelta(days=1))
    elif ny.weekday() < 5:
        hol.add(ny)          # a Saturday New Year's Day is not observed on Friday Dec 31
    hol.add(_nth_weekday(year, 1, 0, 3))            # Martin Luther King Jr. Day
    hol.add(_nth_weekday(year, 2, 0, 3))            # Washington's Birthday
    hol.add(_easter(year) - timedelta(days=2))      # Good Friday
    hol.add(_last_weekday(year, 5, 0))              # Memorial Day
    if year >= 2022:
        hol.add(_observed(date(year, 6, 19)))       # Juneteenth
    hol.add(_observed(date(year, 7, 4)))            # Independence Day
    hol.add(_nth_weekday(year, 9, 0, 1))            # Labor Day
    hol.add(_nth_weekday(year, 11, 3, 4))           # Thanksgiving
    hol.add(_observed(date(year, 12, 25)))          # Christmas
    return frozenset(hol)


def is_trading_day_rules(d: date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def previous_trading_day_rules(d: date) -> date:
    """The latest rule-based trading day strictly before ``d``."""
    p = d - timedelta(days=1)
    while not is_trading_day_rules(p):
        p -= timedelta(days=1)
    return p


# ───────────────────────────── expiries and symbols ─────────────────────────────

def select_expiries(expiries: Iterable[date], snap_date: date, n_weekly: int,
                    n_monthly: int) -> list[date]:
    """The next ``n_weekly`` weekly expiries, then the next ``n_monthly`` monthlies.

    Weekly = the last listed expiry of each Monday-Sunday week (Friday, or Thursday when
    Friday is a holiday), which skips the Mon-Thu dailies. Monthly = a weekly whose week holds
    the month's third Friday (day 15-21). Only expiries strictly after ``snap_date``."""
    idx = pd.DatetimeIndex(sorted({pd.Timestamp(e) for e in expiries}))
    idx = idx[idx > pd.Timestamp(snap_date)]
    if idx.empty:
        return []
    weekly = pd.Series(idx, index=idx).groupby(idx.to_period("W-SUN")).max().sort_values()
    first = weekly.iloc[:n_weekly]
    rest = weekly.iloc[n_weekly:]
    friday = rest + pd.to_timedelta(4 - rest.dt.weekday, unit="D")
    monthly = rest[friday.dt.day.between(15, 21)].iloc[:n_monthly]
    return sorted(d.date() for d in pd.concat([first, monthly]))


def parse_occ(symbols: pd.Series) -> pd.DataFrame:
    """Vectorized OCC symbol parse: root (1-6 chars), YYMMDD, C/P, strike x1000 (8 digits).
    The tail is fixed-width, so the root is everything before the last 15 characters.
    Unparseable symbols come back with null fields (the caller drops and counts them)."""
    s = symbols.astype(str)
    ok = s.str.fullmatch(r"[A-Z0-9]{1,6}\d{6}[CP]\d{8}")
    root = s.str[:-15].where(ok)
    expiry = pd.to_datetime(s.str[-15:-9].where(ok), format="%y%m%d", errors="coerce")
    return pd.DataFrame({
        "root": root,
        "expiry": expiry.dt.date.where(expiry.notna(), None),
        "option_type": s.str[-9].where(ok),
        "strike": pd.to_numeric(s.str[-8:].where(ok), errors="coerce") / 1000.0,
    }, index=symbols.index)


def _parse_ts(s: pd.Series) -> tuple[pd.Series, int]:
    """ISO-8601 API timestamps -> datetime64[us, UTC]. Alpaca mixes fraction widths
    ("...:00Z", "...:56.868680653Z"); without format="ISO8601" pandas infers one shape and
    NaTs the rest silently. Returns (parsed, n present-but-unparseable)."""
    present = s.notna() & s.astype(str).str.len().gt(0)
    out = pd.to_datetime(s, format="ISO8601", utc=True, errors="coerce").astype(
        "datetime64[us, UTC]")
    return out, int((present & out.isna()).sum())


def _et_day(ts: pd.Series) -> pd.Series:
    """The America/New_York calendar day of a UTC timestamp column, as naive midnight."""
    return ts.dt.tz_convert(ET).dt.normalize().dt.tz_localize(None)


# ───────────────────────────── the real-quote rule ─────────────────────────────

def real_quote_mask(df: pd.DataFrame, no_iv: Collection[str] = ()) -> pd.Series:
    """A row is a REAL quote only when its values are usable, never merely present:

      * the quote is stamped on the row's ET session date (``snap_date``) — a quote carried
        over from an earlier session is not today's price;
      * bid > 0, OR a last trade > 0 stamped on that session;
      * 0 < ask, bid <= ask, and ask <= the no-arbitrage bound (the reference price for a
        call, the strike for a put) — catches zero, placeholder and garbage asks;
      * implied vol finite and > 0, unless the underlying is in ``no_iv`` (Alpaca computes no
        IV for index options).
    Null, NaN or unparseable values fail their leg. Vectorized; returns a bool Series."""
    if df.empty:
        return pd.Series(False, index=df.index, dtype=bool)
    session = pd.to_datetime(df["snap_date"].astype(str), format="%Y-%m-%d", errors="coerce")
    num = {c: pd.to_numeric(df[c], errors="coerce").astype("float64")
           for c in ("bid", "ask", "last_price", "iv", "strike", "ref_price")}
    q_ts = pd.to_datetime(df["quote_ts"], utc=True, errors="coerce")
    t_ts = pd.to_datetime(df["last_ts"], utc=True, errors="coerce")
    fresh_quote = _et_day(q_ts).eq(session).fillna(False).to_numpy(dtype=bool)
    fresh_trade = _et_day(t_ts).eq(session).fillna(False).to_numpy(dtype=bool)
    bid, ask, last = num["bid"].to_numpy(), num["ask"].to_numpy(), num["last_price"].to_numpy()
    iv = num["iv"].to_numpy()
    is_call = df["option_type"].astype(str).eq("C").to_numpy(dtype=bool)
    bound = np.where(is_call, num["ref_price"].to_numpy(), num["strike"].to_numpy())
    with np.errstate(invalid="ignore"):
        bid_ok = np.isfinite(bid) & (bid > 0)
        trade_ok = np.isfinite(last) & (last > 0) & fresh_trade
        ask_ok = (np.isfinite(ask) & (ask > 0) & (ask >= np.where(np.isfinite(bid), bid, 0.0))
                  & np.isfinite(bound) & (ask <= bound))
        iv_ok = np.isfinite(iv) & (iv > 0)
    iv_waived = df["underlying"].astype(str).isin(list(no_iv)).to_numpy(dtype=bool)
    mask = fresh_quote & (bid_ok | trade_ok) & ask_ok & (iv_ok | iv_waived)
    return pd.Series(mask, index=df.index, dtype=bool)


@dataclass(frozen=True)
class Verdict:
    """The day's judgement: status, whether to write, and the coverage detail."""
    status: str                      # "OK" | "FAILED"
    write: bool
    n_rows: int
    n_real: int
    covered: list[str]
    missing: list[str]
    message: str


def judge(df: pd.DataFrame, declared: Sequence[str], min_real: int, floor: float) -> Verdict:
    """Fail closed: zero real quotes -> FAILED and nothing written; coverage below the floor
    -> FAILED with the rows kept; otherwise OK."""
    n_rows = int(len(df))
    real = df["real_quote"].astype(bool) if n_rows else pd.Series(dtype=bool)
    n_real = int(real.sum())
    counts = df.loc[real, "underlying"].value_counts() if n_real else pd.Series(dtype="int64")
    have = counts.reindex(list(declared), fill_value=0)
    covered = have.index[have >= min_real].tolist()
    missing = have.index[have < min_real].tolist()
    share = len(covered) / len(declared) if declared else 0.0
    if n_real == 0:
        return Verdict("FAILED", False, n_rows, 0, covered, missing,
                       f"0 real quotes in {n_rows:,} rows across {len(declared)} underlyings "
                       f"- nothing written")
    if share < floor:
        return Verdict("FAILED", True, n_rows, n_real, covered, missing,
                       f"coverage {len(covered)}/{len(declared)} = {share:.0%} < floor "
                       f"{floor:.0%} (below {min_real} real quotes: {', '.join(missing)}) "
                       f"- {n_rows:,} rows kept")
    return Verdict("OK", True, n_rows, n_real, covered, missing,
                   f"{len(covered)}/{len(declared)} underlyings covered, {n_rows:,} rows, "
                   f"{n_real:,} real ({n_real / n_rows:.0%})")


# ───────────────────────────── frames ─────────────────────────────

def empty_frame() -> pd.DataFrame:
    return SCHEMA.empty_table().to_pandas()


def snapshots_frame(snaps: Mapping[str, Mapping[str, Any]], snap_date: date) -> tuple[pd.DataFrame, dict[str, int]]:
    """Flatten an Alpaca option-snapshot payload ({OCC symbol: snapshot}) into stored columns.
    Returns (frame, counters) where counters names dropped/unparsed values."""
    stats = {"unparsed_symbol": 0, "unparsed_ts": 0}
    if not snaps:
        return pd.DataFrame(columns=["contract", *_SNAP_MAP.values()]), stats
    flat = pd.json_normalize(list(snaps.values()))
    flat = flat.reindex(columns=list(_SNAP_MAP)).rename(columns=_SNAP_MAP)
    flat.insert(0, "contract", list(snaps.keys()))
    for c in ("bid", "ask", "last_price", "iv", "delta", "gamma", "theta", "vega", "rho"):
        flat[c] = pd.to_numeric(flat[c], errors="coerce").astype("float64")
    for c in ("bid_size", "ask_size", "last_size", "day_volume", "day_trade_count"):
        flat[c] = pd.to_numeric(flat[c], errors="coerce").round().astype("Int64")
    for c in ("quote_ts", "last_ts", "_day_bar_ts"):
        flat[c], bad = _parse_ts(flat[c])
        stats["unparsed_ts"] += bad
    # The daily bar describes the bar's own session; a stale bar is not today's volume.
    this_session = _et_day(flat["_day_bar_ts"]).eq(pd.Timestamp(snap_date)).fillna(False)
    flat["day_volume"] = flat["day_volume"].where(this_session)
    flat["day_trade_count"] = flat["day_trade_count"].where(this_session)
    flat = flat.drop(columns="_day_bar_ts")
    occ = parse_occ(flat["contract"])
    stats["unparsed_symbol"] = int(occ["root"].isna().sum())
    flat = pd.concat([flat, occ], axis=1)
    return flat[occ["root"].notna()].reset_index(drop=True), stats


def contracts_frame(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """The trading API's option_contracts listing -> contract, root, expiry, style, OI."""
    cols = ["contract", "root", "expiry", "style", "open_interest", "open_interest_date"]
    if not rows:
        return pd.DataFrame(columns=cols)
    c = pd.DataFrame(list(rows))
    c = c.reindex(columns=["symbol", "root_symbol", "expiration_date", "style",
                           "open_interest", "open_interest_date"])
    exp = pd.to_datetime(c["expiration_date"], format="%Y-%m-%d", errors="coerce")
    oid = pd.to_datetime(c["open_interest_date"], format="%Y-%m-%d", errors="coerce")
    return pd.DataFrame({
        "contract": c["symbol"].astype(str),
        "root": c["root_symbol"],
        "expiry": exp.dt.date.where(exp.notna(), None),
        "style": c["style"],
        "open_interest": pd.to_numeric(c["open_interest"], errors="coerce").round().astype("Int64"),
        "open_interest_date": oid.dt.date.where(oid.notna(), None),
    })


def to_table(df: pd.DataFrame) -> pa.Table:
    """Cast a frame to the fixed SCHEMA (raises on a column that cannot be cast)."""
    out = df.reindex(columns=COLUMNS).copy()
    for c in _TS_COLS:
        out[c] = pd.to_datetime(out[c], utc=True).astype("datetime64[us, UTC]")
    for c in ("expiry", "open_interest_date"):
        d = pd.to_datetime(out[c], errors="coerce")
        out[c] = d.dt.date.where(d.notna(), None)
    for c in ("bid_size", "ask_size", "last_size", "day_volume", "day_trade_count",
              "open_interest"):
        out[c] = pd.to_numeric(out[c], errors="coerce").round().astype("Int64")
    out["real_quote"] = out["real_quote"].fillna(False).astype(bool)
    return pa.Table.from_pandas(out, schema=SCHEMA, preserve_index=False, safe=True)


def dedup(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Union and dedup on (snap_date, contract): a real-quote row beats a non-real one, then
    the later snapshot wins. Deterministic order: underlying, expiry, type, strike."""
    frames = [f for f in frames if f is not None and len(f)]
    if not frames:
        return empty_frame()
    df = pd.concat([f.reindex(columns=COLUMNS) for f in frames], ignore_index=True)
    df["real_quote"] = df["real_quote"].fillna(False).astype(bool)
    df["snap_ts"] = pd.to_datetime(df["snap_ts"], utc=True)
    df = df.sort_values([*DEDUP_KEY, "real_quote", "snap_ts"], kind="mergesort")
    df = df.drop_duplicates(DEDUP_KEY, keep="last")
    return df.sort_values(["underlying", "expiry", "option_type", "strike"],
                          kind="mergesort").reset_index(drop=True)


def day_path(out_dir: Path, snap_date: date) -> Path:
    return Path(out_dir) / f"{FILE_PREFIX}{snap_date.isoformat()}.parquet"


def write_day(df: pd.DataFrame, out_dir: Path, snap_date: date) -> tuple[Path, int, int]:
    """Merge with the session's existing file (dedup), write atomically (temp + os.replace),
    return (path, bytes, rows). The temp name starts with '.' so dataset readers skip it."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = day_path(out_dir, snap_date)
    frames = [df]
    if path.exists():
        frames.insert(0, pd.read_parquet(path))
    merged = dedup(frames)
    table = to_table(merged)
    tmp = out_dir / f".{path.name}.tmp"
    pq.write_table(table, tmp, compression="zstd", compression_level=9)
    os.replace(tmp, path)
    return path, path.stat().st_size, int(table.num_rows)


# ───────────────────────────── HTTP ─────────────────────────────

class ApiError(RuntimeError):
    """An Alpaca call failed for good (status + the first 200 bytes of the body)."""

    def __init__(self, status: Optional[int], message: str) -> None:
        super().__init__(f"HTTP {status}: {message}" if status else message)
        self.status = status


class AuthError(ApiError):
    """401: the keys are wrong — every later call would fail the same way."""


class AlpacaReadClient:
    """GET-only Alpaca client: per-host pacing under the measured limits, retries with
    backoff on 429 / 5xx / timeouts, and no secret ever in a message (keys travel only in
    headers; errors carry the status and the first 200 bytes of the body)."""

    def __init__(self, key: str, secret: str, *, session: Optional[requests.Session] = None,
                 data_url: str = DATA_URL, trade_url: str = TRADE_URL,
                 data_per_min: float = DATA_PER_MIN, trade_per_min: float = TRADE_PER_MIN,
                 timeout: tuple[float, float] = (10.0, 30.0), max_attempts: int = 4,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._s = session or requests.Session()
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
                         "Accept": "application/json"}
        self.data_url, self.trade_url = data_url.rstrip("/"), trade_url.rstrip("/")
        self._interval = {urlparse(self.data_url).netloc: 60.0 / data_per_min,
                          urlparse(self.trade_url).netloc: 60.0 / trade_per_min}
        self._last: dict[str, float] = {}
        self._timeout, self._max_attempts = timeout, max_attempts
        self._sleep, self._clock = sleep, clock
        self.requests: Counter[str] = Counter()
        self.n_429 = 0
        self.n_retries = 0
        self.limits_seen: dict[str, str] = {}

    def _pace(self, host: str) -> None:
        wait = self._last.get(host, float("-inf")) + self._interval.get(host, 0.0) - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last[host] = self._clock()

    def _reset_wait(self, headers: Mapping[str, str], default: float) -> float:
        try:
            return min(max(float(headers.get("X-RateLimit-Reset", "")) - time.time(), 0.0)
                       + 0.5, 65.0)
        except ValueError:
            return default

    def get(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        host = urlparse(url).netloc
        last_err = "no attempt made"
        for attempt in range(1, self._max_attempts + 1):
            if attempt > 1:
                self.n_retries += 1
            self._pace(host)
            try:
                r = self._s.get(url, headers=self._headers, params=dict(params or {}),
                                timeout=self._timeout)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = f"{type(e).__name__}"
                self._sleep(min(2.0 ** (attempt - 1), 8.0))
                continue
            self.requests[host] += 1
            if r.headers.get("X-RateLimit-Limit"):
                self.limits_seen[host] = str(r.headers["X-RateLimit-Limit"])
            if r.status_code == 200:
                try:
                    payload = r.json()
                except ValueError as e:
                    raise ApiError(200, f"non-JSON body from {urlparse(url).path}") from e
                remaining = r.headers.get("X-RateLimit-Remaining")
                if remaining is not None and remaining.isdigit() and int(remaining) <= 1:
                    self._sleep(self._reset_wait(r.headers, 5.0))
                return payload
            body = (r.text or "")[:200].replace("\n", " ")
            if r.status_code == 401:
                raise AuthError(401, body)
            if r.status_code == 429:
                self.n_429 += 1
                last_err = f"HTTP 429: {body}"
                self._sleep(self._reset_wait(r.headers, min(2.0 ** attempt, 30.0)))
                continue
            if r.status_code >= 500:
                last_err = f"HTTP {r.status_code}: {body}"
                self._sleep(min(2.0 ** (attempt - 1), 8.0))
                continue
            raise ApiError(r.status_code, f"{urlparse(url).path}: {body}")
        raise ApiError(None, f"{urlparse(url).path}: gave up after {self._max_attempts} "
                             f"attempts ({last_err})")

    def _paged(self, url: str, params: Mapping[str, Any], key: str,
               max_pages: int = 50) -> list[Any]:
        """Follow next_page_token; a repeated token or > max_pages is an error, not a loop."""
        pages: list[Any] = []
        token: Optional[str] = None
        seen: set[str] = set()
        for _ in range(max_pages):
            p = dict(params)
            if token:
                p["page_token"] = token
            payload = self.get(url, p)
            pages.append(payload.get(key) or ({} if key == "snapshots" else []))
            token = payload.get("next_page_token")
            if not token:
                return pages
            if token in seen:
                raise ApiError(None, f"{urlparse(url).path}: repeated page token")
            seen.add(token)
        raise ApiError(None, f"{urlparse(url).path}: more than {max_pages} pages")

    # endpoints ------------------------------------------------------------
    def calendar(self, start: date, end: date) -> list[dict[str, Any]]:
        out = self.get(f"{self.trade_url}/v2/calendar",
                       {"start": start.isoformat(), "end": end.isoformat()})
        if not isinstance(out, list):
            raise ApiError(200, "calendar payload is not a list")
        return out

    def stock_snapshots(self, symbols: Sequence[str]) -> dict[str, Any]:
        out = self.get(f"{self.data_url}/v2/stocks/snapshots",
                       {"symbols": ",".join(symbols), "feed": "delayed_sip"})
        if not isinstance(out, dict):
            raise ApiError(200, "stock snapshot payload is not an object")
        return out

    def contracts(self, underlying: str, exp_gte: date, exp_lte: date, strike_gte: float,
                  strike_lte: float) -> list[dict[str, Any]]:
        pages = self._paged(f"{self.trade_url}/v2/options/contracts", {
            "underlying_symbols": underlying, "status": "active", "limit": 10000,
            "expiration_date_gte": exp_gte.isoformat(),
            "expiration_date_lte": exp_lte.isoformat(),
            "strike_price_gte": f"{strike_gte:.2f}", "strike_price_lte": f"{strike_lte:.2f}"},
            "option_contracts")
        return [row for page in pages for row in page]

    def chain(self, underlying: str, expiry: date, strike_gte: float, strike_lte: float,
              feed: str) -> dict[str, Any]:
        pages = self._paged(f"{self.data_url}/v1beta1/options/snapshots/{underlying}", {
            "feed": feed, "limit": 1000, "expiration_date": expiry.isoformat(),
            "strike_price_gte": f"{strike_gte:.2f}", "strike_price_lte": f"{strike_lte:.2f}"},
            "snapshots")
        merged: dict[str, Any] = {}
        for page in pages:
            merged.update(page)
        return merged


# ───────────────────────────── one run ─────────────────────────────

@dataclass
class RefPrice:
    """The band/bound reference and the stored underlying fields for one underlying."""
    ref_price: float
    ref_source: str
    underlying_price: float
    underlying_price_ts: Optional[pd.Timestamp]
    underlying_day_close: float


@dataclass
class UnderlyingResult:
    """One underlying's rows plus what was expected, returned, and any error."""
    symbol: str
    rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    expiries: list[date] = field(default_factory=list)
    n_expected: int = 0
    n_snapshots: int = 0
    error: Optional[str] = None


@dataclass
class RunOutcome:
    """A run's exit code, status, one-line message and its run-log record."""
    exit_code: int
    status: str
    message: str
    record: dict[str, Any]


def reference_prices(client: AlpacaReadClient, cfg: ArchiveConfig,
                     snap_date: date) -> tuple[dict[str, RefPrice], dict[str, str]]:
    """Delayed-SIP latest trade (and this session's daily close) for every stock/ETF and
    every declared proxy, in one call. An index gets its proxy's price as the REFERENCE and
    a null underlying_price. Returns (prices, errors by symbol)."""
    needed = sorted({u.price_proxy or u.symbol for u in cfg.underlyings})
    snap = client.stock_snapshots(needed)
    flat = pd.json_normalize([snap.get(s) or {} for s in needed])
    rows = flat.reindex(columns=["latestTrade.p", "latestTrade.t", "dailyBar.c", "dailyBar.t"])
    rows.columns = ["p", "t", "c", "bt"]
    rows.index = needed
    p = pd.to_numeric(rows["p"], errors="coerce")
    t, _ = _parse_ts(rows["t"])
    bt, _ = _parse_ts(rows["bt"])
    close = pd.to_numeric(rows["c"], errors="coerce").where(
        _et_day(bt).eq(pd.Timestamp(snap_date)).fillna(False))
    prices: dict[str, RefPrice] = {}
    errors: dict[str, str] = {}
    for u in cfg.underlyings:
        src = u.price_proxy or u.symbol
        px = float(p.get(src, np.nan))
        if not (np.isfinite(px) and px > 0):
            errors[u.symbol] = f"no usable reference price for {src}"
            continue
        if u.price_proxy:
            prices[u.symbol] = RefPrice(px, f"proxy:{src}", np.nan, None, np.nan)
        else:
            ts = t.get(src)
            prices[u.symbol] = RefPrice(px, "underlying", px, None if pd.isna(ts) else ts,
                                        float(close.get(src, np.nan)))
    return prices, errors


def fetch_underlying(client: AlpacaReadClient, spec: UnderlyingSpec, ref: RefPrice,
                     cfg: ArchiveConfig, snap_date: date) -> UnderlyingResult:
    """Contracts (expiries + OI) then one chain call per selected expiry. Every API error is
    caught here and becomes this underlying's error (the run continues), except AuthError."""
    res = UnderlyingResult(spec.symbol)
    lo = round(ref.ref_price * (1.0 - cfg.strike_band), 2)
    hi = round(ref.ref_price * (1.0 + cfg.strike_band), 2)
    try:
        listed = contracts_frame(client.contracts(
            spec.symbol, snap_date + timedelta(days=1),
            snap_date + timedelta(days=cfg.horizon_days), lo, hi))
        listed = listed[listed["root"].astype(str).eq(spec.symbol)]
        res.expiries = select_expiries(listed["expiry"].dropna(), snap_date, cfg.n_weekly,
                                       cfg.n_monthly)
        if not res.expiries:
            res.error = "no listed expiries in the horizon"
            return res
        res.n_expected = int(listed["expiry"].isin(res.expiries).sum())
        snap_ts = pd.Timestamp.now(tz="UTC")
        snaps: dict[str, Any] = {}
        for exp in res.expiries:           # one network call per expiry (≤ n_weekly+n_monthly)
            snaps.update(client.chain(spec.symbol, exp, lo, hi, cfg.feed))
    except AuthError:
        raise
    except (ApiError, requests.RequestException, ValueError, KeyError, TypeError) as e:
        res.error = f"{type(e).__name__}: {e}"[:300]
        return res
    rows, stats = snapshots_frame(snaps, snap_date)
    if stats["unparsed_symbol"] or stats["unparsed_ts"]:
        print(f"{TAG} WARN {spec.symbol}: {stats['unparsed_symbol']} unparseable symbols, "
              f"{stats['unparsed_ts']} unparseable timestamps (those rows cannot be real)",
              flush=True)
    rows = rows[rows["root"].astype(str).eq(spec.symbol) & rows["expiry"].isin(res.expiries)]
    res.n_snapshots = int(len(rows))
    if rows.empty:
        res.error = "chain returned no snapshots"
        return res
    rows = rows.merge(listed[["contract", "style", "open_interest", "open_interest_date"]],
                      on="contract", how="left")
    rows = rows.assign(
        snap_date=snap_date.isoformat(), snap_ts=snap_ts, underlying=spec.symbol,
        underlying_price=ref.underlying_price, underlying_price_ts=ref.underlying_price_ts,
        underlying_day_close=ref.underlying_day_close, ref_price=ref.ref_price,
        ref_source=ref.ref_source, feed=cfg.feed, quote_rule=QUOTE_RULE)
    rows["real_quote"] = real_quote_mask(rows, cfg.no_iv)
    res.rows = rows.reindex(columns=COLUMNS)
    return res


def trading_day_status(client: AlpacaReadClient, d: date) -> tuple[bool, str, str]:
    """(is a trading day, source, note). Alpaca's calendar first; the rules on its failure."""
    try:
        days = {str(e.get("date")) for e in client.calendar(d, d)}
        return d.isoformat() in days, "alpaca", ""
    except (ApiError, requests.RequestException, ValueError) as e:
        return is_trading_day_rules(d), "rules", f"alpaca calendar unavailable ({type(e).__name__})"


def append_run_log(out_dir: Path, record: Mapping[str, Any]) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(out_dir) / RUN_LOG_NAME, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str, sort_keys=True) + "\n")


def run_archive(cfg: ArchiveConfig, client: AlpacaReadClient, out_dir: Path,
                now_utc: Optional[datetime] = None) -> RunOutcome:
    """One archive run: calendar gate, reference prices, every underlying, judge, write."""
    t0 = time.monotonic()
    now_utc = now_utc or datetime.now(timezone.utc)
    snap_date = now_utc.astimezone(ET).date()
    rec: dict[str, Any] = {"run_ts": now_utc.isoformat(), "snap_date": snap_date.isoformat(),
                           "quote_rule": QUOTE_RULE, "config_md5": cfg.md5,
                           "declared": len(cfg.declared)}
    trading, cal_src, note = trading_day_status(client, snap_date)
    rec["calendar_source"] = cal_src
    if note:
        print(f"{TAG} WARN {note}; using the rule-based NYSE calendar", flush=True)
    if not trading:
        msg = f"{snap_date} is not a trading day (calendar={cal_src}) - nothing to capture"
        rec.update(status="SKIP", message=msg, wall_seconds=round(time.monotonic() - t0, 1))
        append_run_log(out_dir, rec)
        return RunOutcome(EXIT_OK, "SKIP", msg, rec)

    results: list[UnderlyingResult] = []
    abort: Optional[str] = None
    try:
        prices, price_errors = reference_prices(client, cfg, snap_date)
    except AuthError as e:
        prices, price_errors, abort = {}, {}, f"Alpaca rejected the keys ({e})"
    except (ApiError, requests.RequestException, ValueError) as e:
        prices, price_errors, abort = {}, {}, f"reference prices failed ({type(e).__name__}: {e})"
    for spec in cfg.underlyings:           # sequential by design: one paced key, no deadlock
        if abort:
            results.append(UnderlyingResult(spec.symbol, error=f"not attempted: {abort}"))
        elif spec.symbol in price_errors:
            results.append(UnderlyingResult(spec.symbol, error=price_errors[spec.symbol]))
        elif time.monotonic() - t0 > cfg.wall_budget_seconds:
            results.append(UnderlyingResult(spec.symbol, error="not attempted: wall budget spent"))
        else:
            try:
                results.append(fetch_underlying(client, spec, prices[spec.symbol], cfg,
                                                snap_date))
            except AuthError as e:
                abort = f"Alpaca rejected the keys ({e})"
                results.append(UnderlyingResult(spec.symbol, error=abort))
    if abort:
        print(f"{TAG} ERROR {abort} - remaining underlyings not attempted", flush=True)

    df = dedup([r.rows for r in results])
    verdict = judge(df, cfg.declared, cfg.min_real_per_underlying, cfg.coverage_floor)
    real_by = df.loc[df["real_quote"].astype(bool), "underlying"].value_counts() if len(df) else {}
    for r in results:
        n_real = int(real_by.get(r.symbol, 0)) if len(df) else 0
        line = (f"{TAG} {r.symbol}: {len(r.expiries)} expiries, {r.n_snapshots:,}/"
                f"{r.n_expected:,} contracts, {n_real:,} real")
        print(line + (f" - ERROR {r.error}" if r.error else ""), flush=True)

    rec.update(n_rows=verdict.n_rows, n_real=verdict.n_real,
               real_share=round(verdict.n_real / verdict.n_rows, 4) if verdict.n_rows else 0.0,
               covered=len(verdict.covered), missing=verdict.missing,
               errors={r.symbol: r.error for r in results if r.error},
               requests=dict(client.requests), n_429=client.n_429, n_retries=client.n_retries,
               rate_limits=dict(client.limits_seen))
    if verdict.write:
        path, nbytes, nrows = write_day(df, out_dir, snap_date)
        rec.update(path=path.name, file_bytes=nbytes, file_rows=nrows)
        wrote = f"; wrote {path.name} ({nbytes / 1e6:.2f} MB, {nrows:,} rows)"
    else:
        wrote = ""
    rec.update(status=verdict.status, message=verdict.message,
               wall_seconds=round(time.monotonic() - t0, 1))
    append_run_log(out_dir, rec)
    msg = (f"{verdict.message}{wrote}; {sum(client.requests.values())} requests, "
           f"{client.n_429} x 429, {rec['wall_seconds']:.0f} s")
    return RunOutcome(EXIT_OK if verdict.status == "OK" else EXIT_FAILED, verdict.status, msg, rec)


# ───────────────────────────── the store check (local verifier) ─────────────────────────────

def _runs_for(out_dir: Path, d: date) -> list[dict[str, Any]]:
    path = Path(out_dir) / RUN_LOG_NAME
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("snap_date") == d.isoformat():
            out.append(rec)
    return out


def verify_store(out_dir: Path, cfg: ArchiveConfig, today: date) -> tuple[bool, str]:
    """Re-judge the latest session's file BY CONTENT (the rule recomputed from raw columns,
    never the stored flag or a row count). Offline: the rule-based calendar, overridden only
    by the archiver's own SKIP from Alpaca's calendar (an ad-hoc closure).

    Trading day -> today's file must pass; non-trading day -> the previous session's file
    must exist and pass (a capture missed on Friday is caught on Saturday), unless the store
    has no capture at all yet (before the first trading-day run)."""
    out_dir = Path(out_dir)
    trading = is_trading_day_rules(today)
    if trading and any(r.get("status") == "SKIP" and r.get("calendar_source") == "alpaca"
                       for r in _runs_for(out_dir, today)):
        trading = False
    files = sorted(out_dir.glob(f"{FILE_PREFIX}*.parquet")) if out_dir.exists() else []
    if not trading and not files:
        return True, f"SKIP: {today} is not a trading day and the store has no capture yet"
    session = today if trading else previous_trading_day_rules(today)
    path = day_path(out_dir, session)
    if not path.exists():
        return False, f"FAILED: no capture for session {session} ({path.name} missing)"
    df = pd.read_parquet(path)
    df = df[df["snap_date"].astype(str).eq(session.isoformat())].copy()
    df["real_quote"] = real_quote_mask(df, cfg.no_iv)
    v = judge(df, cfg.declared, cfg.min_real_per_underlying, cfg.coverage_floor)
    return v.status == "OK", f"{v.status}: session {session}: {v.message}"


# ───────────────────────────── CLI ─────────────────────────────

def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                    help="store directory (default: data/macro_data/options)")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE,
                    help="read Alpaca keys from this file if not in the environment")
    ap.add_argument("--underlyings", default="",
                    help="comma list: a declared SUBSET (smoke runs); it becomes the denominator")
    ap.add_argument("--verify", action="store_true",
                    help="check the store's latest session by content; no API calls")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.underlyings:
            cfg = cfg.subset([s.strip().upper() for s in args.underlyings.split(",") if s.strip()])
        if args.verify:
            ok, msg = verify_store(args.out_dir, cfg, datetime.now(ET).date())
            print(f"{TAG} verify {msg}", flush=True)
            return EXIT_OK if ok else EXIT_FAILED
        key, secret = load_keys(args.env_file)
        client = AlpacaReadClient(key, secret)
        out = run_archive(cfg, client, args.out_dir)
    except (ConfigError, KeyError) as e:
        print(f"{TAG} FAILED options: {e}", flush=True)
        return EXIT_BROKEN
    except AuthError as e:
        print(f"{TAG} FAILED options: Alpaca rejected the keys ({e})", flush=True)
        return EXIT_FAILED
    except Exception as e:  # noqa: BLE001 — a crashed archiver must still be loud
        print(f"{TAG} FAILED options: archiver crashed: {type(e).__name__}: {e}", flush=True)
        return EXIT_BROKEN
    print(f"{TAG} {out.status} options: {out.message}", flush=True)
    return out.exit_code


if __name__ == "__main__":
    sys.exit(main())
