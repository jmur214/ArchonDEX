"""
scripts/archive_options_snapshots.py
====================================
T-416 (2026-11-20; hardened 2026-11-24): a daily snapshot archive of option quotes, implied
vol and greeks.

Why: Alpaca serves option bars and trade prints back to ~2024-01, but NO historical quotes
(``/v1beta1/options/quotes`` is a 404), and its implied vol and greeks exist only as CURRENT
values on the snapshot/chain endpoints. No free source sells an options history with quotes.
So the only free way to own one is to save the snapshots every trading day, starting now
(owner approval 2026-11-20; census ``docs/Sources/ideas_census_desk_t410_2026-11-20.md`` §4.1).
A day that is not captured cannot be recaptured, so a problem may cost one contract or one
underlying but never the day, and nothing is lost quietly.

What one run does (all GETs; nothing is ever posted to any API):
  1. Session. Alpaca's calendar (+/-7 days) AND a rule-based NYSE calendar; a day is skipped
     only when neither says it is open. An empty or malformed calendar answer is never a
     closure; a disagreement is printed loudly and the capture still runs.
     ``--slot eod`` (default) captures the last session that has closed. After midnight, before
     the next open, or on a weekend it captures the previous session late if it is missing
     (Alpaca still serves its closing quotes). ``--slot near_close`` is for an intraday capture.
     A slot that does not match the clock is refused (rc 2): it would mislabel the rows.
  2. Reference prices: one ``/v2/stocks/snapshots`` call on ``delayed_sip``. The strike band is
     [0.8 x min, 1.2 x max] of the session close and the last trade, so an after-hours move
     cannot shift it off the close. An index (XSP) has no price on Alpaca; a declared proxy
     (SPY) sets its band, and its own ``underlying_price`` is stored as null.
  3. Per underlying (``config/options_archive_universe.json``): ``/v2/options/contracts`` lists
     expiries and open interest; one ``/v1beta1/options/snapshots/{u}`` call per selected
     expiry (``feed=indicative``; OPRA is a 403 on this account).
  4. ``real_quote_mask`` (rule v2) judges every row by a USABLE value, never by presence (the
     2026-11-19 Kalshi defect: a "not null" check passed $0 parlay quotes for five months).
  5. ``judge`` fails closed on what was EXPECTED, not only on what came back: see its docstring.

Output: ``<out>/options_snapshot_YYYY-MM-DD.parquet`` per ET session (fixed schema, zstd),
deduped by (snap_date, slot, contract), plus one JSON line per run in
``<out>/_archive_runs.jsonl`` (the underscore keeps parquet dataset readers off it; ``--verify``
needs it to know what was expected). A file that cannot be read is renamed ``_corrupt_...``.

Exit codes: 0 = OK or SKIP; 1 = FAILED (or OK rows with a corrupt earlier file moved aside);
2 = broken (keys, config, slot, crash). ``scripts/run_altdata_archivers.sh`` alarms on any
non-zero code and bounds the whole step with a hard timeout (142 when it fires).

Usage:
  .venv/bin/python scripts/archive_options_snapshots.py                  # production run
  .venv/bin/python scripts/archive_options_snapshots.py --slot near_close --out-dir /tmp/smoke
  .venv/bin/python scripts/archive_options_snapshots.py --verify         # store check only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import numbers
import os
import sys
import threading
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping, Optional, Sequence, Union
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
REGULAR_OPEN = dtime(9, 30)
REGULAR_CLOSE = dtime(16, 0)      # the default; Alpaca's calendar carries early closes
CALENDAR_WINDOW = timedelta(days=7)
DATA_URL = "https://data.alpaca.markets"
# Calendar and contract listings are reference data, identical on paper and live; the paper
# host is used so this script never addresses a live-account endpoint.
TRADE_URL = "https://paper-api.alpaca.markets"

SLOTS = ("eod", "near_close")
FILE_PREFIX = "options_snapshot_"
CORRUPT_PREFIX = "_corrupt_"
RUN_LOG_NAME = "_archive_runs.jsonl"
TAG = "[options-archive]"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BROKEN = 2

# Read from X-RateLimit-Limit on 2026-11-20: 200/min on data.alpaca.markets (free plan) and on
# the paper trading API's /v2/options/contracts. Pace below both so a concurrent job on the
# same key keeps headroom.
DATA_PER_MIN = 170
TRADE_PER_MIN = 170
#: One GET may take this long IN TOTAL. requests' timeout is per socket read, so a server that
#: drips one byte a second would otherwise block for ever.
REQUEST_HARD_CAP_S = 60.0

# The real-quote rule, v2 (2026-11-24).
QUOTE_RULE = "v2"
SPREAD_ABS = 0.10          # dollars
SPREAD_FRAC = 0.50         # of the mid
INTRINSIC_SLACK = 0.02     # of the underlying: 15-min delayed prices vs real-time quotes
IV_MIN, IV_MAX = 0.01, 5.0
COUNT_MAX = 1e9            # a size / volume / open interest outside [0, this] is not a value
#: A coverage leg, not a row rule: one (bid, ask) pair on more than this share of a name's real
#: rows is a placeholder feed. Measured on real days: at most 3 % (2026-11-20 and 2026-11-24).
MAX_SAME_QUOTE_SHARE = 0.25

#: The stored schema. Fixed explicitly so every daily file has identical column types and a
#: directory read (``pd.read_parquet(out_dir)``) never trips on an all-null day.
SCHEMA = pa.schema([
    ("snap_date", pa.string()),            # the ET session the quotes belong to, ISO
    ("slot", pa.string()),                 # "eod" | "near_close"
    ("snap_ts", pa.timestamp("us", tz="UTC")),   # when this underlying's chain was requested
    ("underlying", pa.string()),
    ("contract", pa.string()),             # OCC symbol
    ("root", pa.string()),
    ("expiry", pa.date32()),
    ("strike", pa.float64()),
    ("option_type", pa.string()),          # "C" | "P"
    ("listed", pa.bool_()),                # in the active contract listing (else no style / OI)
    ("style", pa.string()),                # american | european (contracts endpoint)
    ("bid", pa.float64()),
    ("ask", pa.float64()),
    ("bid_size", pa.int64()),
    ("ask_size", pa.int64()),
    ("bid_exchange", pa.string()),
    ("ask_exchange", pa.string()),
    ("quote_condition", pa.string()),
    ("quote_ts", pa.timestamp("us", tz="UTC")),
    ("last_price", pa.float64()),
    ("last_size", pa.int64()),
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
    ("day_trade_count", pa.int64()),
    ("open_interest", pa.int64()),         # OCC open interest as of open_interest_date
    ("open_interest_date", pa.date32()),
    ("underlying_price", pa.float64()),    # delayed-SIP latest trade; null for an index
    ("underlying_price_ts", pa.timestamp("us", tz="UTC")),
    ("underlying_day_close", pa.float64()),  # delayed-SIP daily bar close, this session only
    ("ref_low", pa.float64()),             # min(session close, last trade): band low, intrinsic
    ("ref_high", pa.float64()),            # max(session close, last trade): band high, bounds
    ("ref_source", pa.string()),           # "underlying" | "proxy:<SYM>"
    ("feed", pa.string()),
    ("real_quote", pa.bool_()),
    ("quote_rule", pa.string()),
])
COLUMNS: list[str] = SCHEMA.names
DEDUP_KEY = ["snap_date", "slot", "contract"]
_TS_COLS = [f.name for f in SCHEMA if pa.types.is_timestamp(f.type)]
_DATE_COLS = [f.name for f in SCHEMA if pa.types.is_date(f.type)]
_INT_COLS = [f.name for f in SCHEMA if pa.types.is_integer(f.type)]
_FLOAT_COLS = [f.name for f in SCHEMA if pa.types.is_floating(f.type)]
_TEXT_COLS = [f.name for f in SCHEMA if pa.types.is_string(f.type)]
_BOOL_COLS = [f.name for f in SCHEMA if pa.types.is_boolean(f.type)]

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


def _utcnow() -> datetime:
    """The ONLY wall-clock read in this module (a test scans for others); tests pin it."""
    return datetime.now(timezone.utc)


def _where(e: BaseException) -> str:
    """An exception as its type and code location. Never its message: a message may carry a
    header value (requests.InvalidHeader does)."""
    tb = traceback.extract_tb(e.__traceback__)
    return f"{type(e).__name__} at {Path(tb[-1].filename).name}:{tb[-1].lineno}" if tb \
        else type(e).__name__


# ───────────────────────────── configuration ─────────────────────────────

class ConfigError(RuntimeError):
    """The universe config is missing or malformed: the run cannot know what to expect."""


class KeysError(RuntimeError):
    """Alpaca keys are missing or cannot go into a header (the message names no value)."""


class SlotError(RuntimeError):
    """The requested slot does not match the clock; the rows would be mislabelled."""


@dataclass(frozen=True)
class UnderlyingSpec:
    """One declared underlying; an index declares a price proxy and may have no IV."""
    symbol: str
    kind: str
    price_proxy: Optional[str] = None
    iv_expected: bool = True
    required: bool = False           # not covered -> FAILED whatever the coverage share


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
    min_real_share: float = 0.0      # an underlying's real rows / its rows, to count as covered
    min_returned_share: float = 0.9  # its returned listed contracts / the contracts expected
    acknowledged_gaps: frozenset[date] = frozenset()

    @property
    def declared(self) -> list[str]:
        return [u.symbol for u in self.underlyings]

    @property
    def required(self) -> list[str]:
        return [u.symbol for u in self.underlyings if u.required]

    @property
    def no_iv(self) -> frozenset[str]:
        return frozenset(u.symbol for u in self.underlyings if not u.iv_expected)

    def subset(self, symbols: Collection[str]) -> "ArchiveConfig":
        """The same rules on a declared subset (a smoke run); the subset is the denominator."""
        unknown = set(symbols) - set(self.declared)
        if unknown:
            raise ConfigError(f"not in the declared universe: {sorted(unknown)}")
        return replace(self, underlyings=tuple(u for u in self.underlyings
                                               if u.symbol in set(symbols)))


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
                           iv_expected=bool(u.get("iv_expected", True)),
                           required=bool(u.get("required", False)))
            for u in raw["underlyings"])
        cfg = ArchiveConfig(
            underlyings=unds, feed=str(raw["feed"]), strike_band=float(raw["strike_band"]),
            n_weekly=int(raw["n_weekly"]), n_monthly=int(raw["n_monthly"]),
            horizon_days=int(raw["horizon_days"]), coverage_floor=float(raw["coverage_floor"]),
            min_real_per_underlying=int(raw["min_real_per_underlying"]),
            wall_budget_seconds=float(raw["wall_budget_seconds"]),
            md5=hashlib.md5(raw_bytes).hexdigest(),
            min_real_share=float(raw["min_real_share_per_underlying"]),
            min_returned_share=float(raw["min_returned_share_per_underlying"]),
            acknowledged_gaps=frozenset(date.fromisoformat(d)
                                        for d in dict(raw["acknowledged_gaps"])))
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"config malformed: {path}: {type(e).__name__}: {e}") from e
    syms = cfg.declared
    if not syms:
        raise ConfigError(f"config declares no underlyings: {path}")
    if len(set(syms)) != len(syms):
        raise ConfigError(f"config declares a symbol twice: {path}")
    if not (0.0 < cfg.strike_band < 1.0 and 0.0 < cfg.coverage_floor <= 1.0
            and cfg.n_weekly >= 1 and cfg.n_monthly >= 0 and cfg.horizon_days >= 7
            and cfg.min_real_per_underlying >= 1 and cfg.wall_budget_seconds > 0
            and 0.0 <= cfg.min_real_share < 1.0 and 0.0 < cfg.min_returned_share <= 1.0):
        raise ConfigError(f"config value out of range: {path}")
    for u in cfg.underlyings:
        if u.kind == "index" and not u.price_proxy:
            raise ConfigError(f"index {u.symbol} declares no price_proxy: {path}")
    return cfg


def load_keys(env_file: Path) -> tuple[str, str]:
    """Alpaca keys from the process environment, else from ``env_file`` (read, not loaded into
    os.environ), always as a pair from ONE source. Stripped; a value that cannot go into an
    HTTP header is refused here, because requests would quote it in its error message."""
    names = (("ALPACA_API_KEY", "ALPACA_SECRET_KEY"), ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY"))
    sources: list[Mapping[str, Optional[str]]] = [os.environ]
    if Path(env_file).exists():
        from dotenv import dotenv_values
        sources.append(dotenv_values(env_file))
    for src in sources:
        for kn, sn in names:
            key, sec = (src.get(kn) or "").strip(), (src.get(sn) or "").strip()
            if not (key and sec):
                continue
            if not all(v.isascii() and v.isprintable() and " " not in v for v in (key, sec)):
                raise KeysError(f"{kn} / {sn} hold characters that cannot go into an HTTP "
                                f"header (values not shown)")
            return key, sec
    raise KeysError(f"ALPACA_API_KEY / ALPACA_SECRET_KEY not found in the environment or in "
                    f"{env_file}")


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
    """Full-day NYSE closures by rule (ad-hoc closures are only in Alpaca's calendar)."""
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


def _previous(d: date, is_open: Callable[[date], bool]) -> date:
    """The latest open day strictly before ``d``."""
    p = d - timedelta(days=1)
    while not is_open(p):
        p -= timedelta(days=1)
    return p


def previous_trading_day_rules(d: date) -> date:
    """The latest rule-based trading day strictly before ``d``."""
    return _previous(d, is_trading_day_rules)


@dataclass(frozen=True)
class CalendarView:
    """Alpaca's calendar around ``today`` next to the rules. ``is_open`` is the union: a day is
    skipped only when BOTH say closed, so neither source alone can lose a session."""
    today: date
    usable: bool
    days: frozenset[date] = frozenset()
    closes: Mapping[date, dtime] = field(default_factory=dict)
    note: str = ""

    def is_open(self, d: date) -> bool:
        return is_trading_day_rules(d) or (self.usable and d in self.days)

    def close_time(self, d: date) -> dtime:
        return self.closes.get(d, REGULAR_CLOSE)

    def disagreement(self, d: date) -> Optional[str]:
        if not self.usable or abs(d - self.today) > CALENDAR_WINDOW:
            return None
        rules, alpaca = is_trading_day_rules(d), d in self.days
        if rules == alpaca:
            return None
        return (f"CALENDAR DISAGREEMENT {d}: rules say {'open' if rules else 'closed'}, Alpaca "
                f"{'lists' if alpaca else 'omits'} it - not skipped")

    def record(self) -> dict[str, Any]:
        return {"source": "alpaca" if self.usable else "rules",
                "from": (self.today - CALENDAR_WINDOW).isoformat(),
                "to": (self.today + CALENDAR_WINDOW).isoformat(),
                "days": sorted(d.isoformat() for d in self.days) if self.usable else [],
                "note": self.note}


def read_calendar(client: "AlpacaReadClient", today: date) -> CalendarView:
    """Alpaca's calendar for +/-7 days. Usable only if every entry parses and the list holds a
    day on BOTH sides of today; an empty or odd answer falls back to the rules, loudly."""
    try:
        payload = client.calendar(today - CALENDAR_WINDOW, today + CALENDAR_WINDOW)
    except ApiError as e:
        return CalendarView(today, False, note=f"alpaca calendar failed ({type(e).__name__})")
    days: set[date] = set()
    closes: dict[date, dtime] = {}
    bad = 0
    for entry in payload:
        try:
            d = date.fromisoformat(entry["date"])
        except (TypeError, KeyError, ValueError, AttributeError):
            bad += 1
            continue
        days.add(d)
        try:
            closes[d] = dtime.fromisoformat(str(entry.get("close")))
        except ValueError:
            pass                       # close_time falls back to 16:00 ET
    usable = not bad and bool(days) and min(days) < today < max(days)
    note = "" if usable else (f"alpaca calendar unusable ({len(payload)} entries, {bad} "
                              f"unparseable) - an empty answer is not a closure")
    return CalendarView(today, usable, frozenset(days), closes, note)


def resolve_session(now_et: datetime, view: CalendarView, slot: str) -> tuple[Optional[date], str]:
    """(session to capture, reason). None = nothing is due (closed day, near_close slot).
    Raises SlotError when the slot does not match the clock."""
    today, t = now_et.date(), now_et.time()
    is_open, close = view.is_open(today), view.close_time(today)
    in_session = is_open and REGULAR_OPEN <= t < close
    if slot == "near_close":
        if in_session:
            return today, "intraday"
        if not is_open:
            return None, f"{today} is not a trading day"
        raise SlotError(f"slot near_close needs the open session (09:30-{close:%H:%M} ET)")
    if is_open and t >= close:
        return today, "after the close"
    if in_session:
        raise SlotError(f"slot eod needs a closed session; {today} closes {close:%H:%M} ET "
                        f"(use --slot near_close for an intraday capture)")
    return _previous(today, view.is_open), "late: the last session that closed"


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


# ───────────────────────────── value coercion (one odd value costs one value) ──────────

def _is_number_or_text(v: Any) -> bool:
    return isinstance(v, (numbers.Real, str)) and not isinstance(v, (bool, np.bool_))


def _num(s: pd.Series) -> pd.Series:
    """float64, where anything that is not a finite number (bool, list, inf, null, text that
    does not parse) is NaN. Numeric columns take the vectorized path."""
    if pd.api.types.is_bool_dtype(s.dtype):
        return pd.Series(np.nan, index=s.index, dtype="float64")
    if not pd.api.types.is_numeric_dtype(s.dtype):
        s = s.astype(object)
        s = s.where(s.map(_is_number_or_text).astype(bool))
    out = pd.to_numeric(s, errors="coerce").astype("float64")
    return out.where(np.isfinite(out))


def _count(s: pd.Series) -> pd.Series:
    """Int64 counts (sizes, volume, open interest); outside [0, COUNT_MAX] -> null."""
    n = _num(s)
    return n.where(n.between(0, COUNT_MAX)).round().astype("Int64")


def _text(s: pd.Series) -> pd.Series:
    """Text or null; a non-text value (an int exchange code) becomes its text."""
    obj = s.astype(object)
    return obj.map(str).where(obj.notna(), None)


def _parse_ts(s: pd.Series) -> tuple[pd.Series, int]:
    """ISO-8601 API timestamps -> datetime64[us, UTC]. Alpaca mixes fraction widths
    ("...:00Z", "...:56.868680653Z"); without format="ISO8601" pandas infers one shape and
    NaTs the rest silently. Returns (parsed, n present-but-unparseable)."""
    obj = s.astype(object)
    present = obj.notna()
    txt = obj.where(obj.map(lambda v: isinstance(v, str)).astype(bool), None)
    out = pd.to_datetime(txt, format="ISO8601", utc=True, errors="coerce").astype(
        "datetime64[us, UTC]")
    return out, int((present & out.isna()).sum())


def _et_day(ts: pd.Series) -> pd.Series:
    """The America/New_York calendar day of a UTC timestamp column, as naive midnight."""
    return ts.dt.tz_convert(ET).dt.normalize().dt.tz_localize(None)


# ───────────────────────────── the real-quote rule ─────────────────────────────

def real_quote_mask(df: pd.DataFrame, no_iv: Collection[str] = ()) -> pd.Series:
    """Rule v2: a row is a REAL quote only when its values are usable, never merely present:

      * the quote is stamped on the row's session (``snap_date``, ET);
      * two-sided: bid > 0 with both sizes > 0. A trade does NOT stand in for a bid: at the
        2026-11-20 close that admitted 144 pulled XSP quotes (bid 0, size 0);
      * bid <= ask <= the no-arbitrage bound (``ref_high`` for a call, the strike for a put),
        and ask >= intrinsic - 2 % of the underlying (a constant placeholder fails this);
      * spread <= max($0.10, 50 % of the mid);
      * 1 % <= implied vol <= 500 %, unless the underlying is in ``no_iv`` (Alpaca computes no
        IV for index options).
    Null or unparseable values fail their leg. Vectorized; returns a bool Series."""
    if df.empty:
        return pd.Series(False, index=df.index, dtype=bool)
    session = pd.to_datetime(df["snap_date"].astype(str), format="%Y-%m-%d", errors="coerce")
    q_ts = pd.to_datetime(df["quote_ts"], utc=True, errors="coerce")
    fresh = _et_day(q_ts).eq(session).fillna(False).to_numpy(dtype=bool)
    bid, ask, bid_size, ask_size, iv, strike, low, high = (
        _num(df[c]).to_numpy() for c in ("bid", "ask", "bid_size", "ask_size", "iv", "strike",
                                         "ref_low", "ref_high"))
    is_call = df["option_type"].astype(str).eq("C").to_numpy(dtype=bool)
    with np.errstate(invalid="ignore"):
        bound = np.where(is_call, high, strike)
        intrinsic = np.maximum(np.where(is_call, low - strike, strike - high), 0.0)
        two_sided = ((bid > 0) & (bid_size > 0) & (bid_size <= COUNT_MAX)
                     & (ask_size > 0) & (ask_size <= COUNT_MAX))
        ask_ok = (ask >= bid) & (ask <= bound) & (ask >= intrinsic - INTRINSIC_SLACK * high)
        tight = (ask - bid) <= np.maximum(SPREAD_ABS, SPREAD_FRAC * (bid + ask) / 2.0) + 1e-9
        iv_ok = (iv >= IV_MIN) & (iv <= IV_MAX)
    iv_waived = df["underlying"].astype(str).isin(list(no_iv)).to_numpy(dtype=bool)
    mask = fresh & two_sided & ask_ok & tight & (iv_ok | iv_waived)
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
    reasons: dict[str, str]
    message: str


def coverage_table(df: pd.DataFrame, declared: Sequence[str],
                   expected: Mapping[str, int]) -> pd.DataFrame:
    """Per declared underlying: rows, real, listed (returned AND in the contract listing),
    expiries that came back, the real rows sharing the most common (bid, ask), and the
    contracts the listing said to expect."""
    cols = ["rows", "real", "listed", "expiries", "same"]
    if len(df):
        g = df.groupby("underlying")
        pairs = df[df["real_quote"].astype(bool)].groupby(["underlying", "bid", "ask"]).size()
        t = pd.DataFrame({"rows": g.size(), "real": g["real_quote"].sum(),
                          "listed": g["listed"].sum(), "expiries": g["expiry"].nunique(),
                          "same": pairs.groupby(level="underlying").max()})
    else:
        t = pd.DataFrame(columns=cols)
    t = t.reindex(list(declared)).fillna(0).astype("int64")
    t["expected"] = pd.Series(dict(expected), dtype="float64").reindex(
        list(declared)).fillna(0).astype("int64")
    return t


def judge(df: pd.DataFrame, cfg: ArchiveConfig, expected: Mapping[str, int]) -> Verdict:
    """Fail closed, against what was EXPECTED. An underlying is covered when all hold:
    >= ``min_real_per_underlying`` real rows; real rows >= ``min_real_share`` of its rows;
    returned listed contracts >= ``min_returned_share`` of those the listing named (a listing
    that named none is not covered); >= ``n_weekly`` expiries came back (a truncated listing
    shrinks "expected", so it is caught here); no single (bid, ask) pair on more than
    ``MAX_SAME_QUOTE_SHARE`` of the real rows (a constant feed looks real out of the money).

    Zero real quotes -> FAILED, nothing written. Coverage below ``coverage_floor``, or any
    ``required`` underlying not covered -> FAILED, rows kept. Otherwise OK, naming every
    underlying that was not covered."""
    t = coverage_table(df, cfg.declared, expected)
    legs = pd.DataFrame({
        "real": t["real"] >= cfg.min_real_per_underlying,
        "share": t["real"] >= cfg.min_real_share * t["rows"],
        "returned": (t["expected"] > 0) & (t["listed"] >= cfg.min_returned_share * t["expected"]),
        "expiries": t["expiries"] >= cfg.n_weekly,
        "varied": t["same"] <= MAX_SAME_QUOTE_SHARE * t["real"]})
    ok = legs.all(axis=1)
    covered, missing = t.index[ok].tolist(), t.index[~ok].tolist()
    reasons = {s: (f"real {t.at[s, 'real']}/{t.at[s, 'rows']}, returned "
                   f"{t.at[s, 'listed']}/{t.at[s, 'expected']}, {t.at[s, 'expiries']} expiries"
                   + ("" if legs.at[s, "varied"] else f", one quote on {t.at[s, 'same']} rows"))
               for s in missing}
    n_rows, n_real = int(len(df)), int(t["real"].sum())
    share = len(covered) / len(cfg.declared)
    named = "; ".join(f"{s} [{why}]" for s, why in reasons.items())
    if n_real == 0:
        return Verdict("FAILED", False, n_rows, 0, covered, missing, reasons,
                       f"0 real quotes in {n_rows:,} rows across {len(cfg.declared)} "
                       f"underlyings - nothing written")
    req_missing = [s for s in missing if s in set(cfg.required)]
    if share < cfg.coverage_floor or req_missing:
        why = f"required underlying not covered: {', '.join(req_missing)}; " if req_missing else ""
        return Verdict("FAILED", True, n_rows, n_real, covered, missing, reasons,
                       f"{why}coverage {len(covered)}/{len(cfg.declared)} = {share:.0%} (floor "
                       f"{cfg.coverage_floor:.0%}); not covered: {named} - {n_rows:,} rows kept")
    return Verdict("OK", True, n_rows, n_real, covered, missing, reasons,
                   f"{len(covered)}/{len(cfg.declared)} underlyings covered"
                   + (f" (NOT COVERED: {named})" if missing else "")
                   + f", {n_rows:,} rows, {n_real:,} real ({n_real / n_rows:.0%})")


# ───────────────────────────── frames ─────────────────────────────

def empty_frame() -> pd.DataFrame:
    return SCHEMA.empty_table().to_pandas()


def to_table(df: pd.DataFrame) -> pa.Table:
    """Coerce a frame to the fixed SCHEMA, value by value (an odd value becomes null)."""
    out = df.reindex(columns=COLUMNS).copy()
    for c in _TS_COLS:
        out[c] = pd.to_datetime(out[c], utc=True, errors="coerce").astype("datetime64[us, UTC]")
    for c in _DATE_COLS:
        d = pd.to_datetime(out[c], errors="coerce")
        out[c] = d.dt.date.where(d.notna(), None)
    for c in _INT_COLS:
        out[c] = _count(out[c])
    for c in _FLOAT_COLS:
        out[c] = _num(out[c])
    for c in _TEXT_COLS:
        out[c] = _text(out[c])
    for c in _BOOL_COLS:
        out[c] = out[c].eq(True).fillna(False).astype(bool)
    return pa.Table.from_pandas(out, schema=SCHEMA, preserve_index=False, safe=True)


def snapshots_frame(snaps: Mapping[str, Any], snap_date: date) -> tuple[pd.DataFrame, dict[str, int]]:
    """Flatten an Alpaca option-snapshot payload ({OCC symbol: snapshot}) into stored columns.
    Returns (frame, counters); a non-object snapshot or unparseable symbol drops that row."""
    good = {k: v for k, v in snaps.items() if isinstance(v, dict)}
    stats = {"bad_entry": len(snaps) - len(good), "unparsed_symbol": 0, "unparsed_ts": 0}
    if not good:
        return pd.DataFrame(columns=["contract", "root", "expiry", "option_type", "strike",
                                     *(c for c in _SNAP_MAP.values() if c[0] != "_")]), stats
    flat = pd.json_normalize(list(good.values()))
    flat = flat.reindex(columns=list(_SNAP_MAP)).rename(columns=_SNAP_MAP)
    flat.insert(0, "contract", list(good.keys()))
    for c in ("quote_ts", "last_ts", "_day_bar_ts"):
        flat[c], bad = _parse_ts(flat[c])
        stats["unparsed_ts"] += bad
    # The daily bar describes the bar's own session; a stale bar is not today's volume.
    this_session = _et_day(flat["_day_bar_ts"]).eq(pd.Timestamp(snap_date)).fillna(False)
    for c in ("day_volume", "day_trade_count"):
        flat[c] = _count(flat[c]).where(this_session)
    flat = flat.drop(columns="_day_bar_ts")
    occ = parse_occ(flat["contract"])
    keep = occ["root"].notna() & occ["expiry"].notna()
    stats["unparsed_symbol"] = int((~keep).sum())
    return pd.concat([flat, occ], axis=1)[keep].reset_index(drop=True), stats


def contracts_frame(rows: Sequence[Any]) -> pd.DataFrame:
    """The trading API's option_contracts listing -> contract, root, expiry, style, OI.
    Entries that are not objects, or have no symbol or expiry, are dropped."""
    c = pd.DataFrame([r for r in rows if isinstance(r, dict)]).reindex(
        columns=["symbol", "root_symbol", "expiration_date", "style", "open_interest",
                 "open_interest_date"])
    exp = pd.to_datetime(_text(c["expiration_date"]), format="%Y-%m-%d", errors="coerce")
    oid = pd.to_datetime(_text(c["open_interest_date"]), format="%Y-%m-%d", errors="coerce")
    out = pd.DataFrame({
        "contract": _text(c["symbol"]), "root": _text(c["root_symbol"]),
        "expiry": exp.dt.date.where(exp.notna(), None), "style": _text(c["style"]),
        "open_interest": _count(c["open_interest"]),
        "open_interest_date": oid.dt.date.where(oid.notna(), None)})
    out = out[out["contract"].notna() & out["expiry"].notna()]
    return out.drop_duplicates("contract").reset_index(drop=True)


def dedup(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Union and dedup on (snap_date, slot, contract): a real-quote row beats a non-real one,
    then the later snapshot wins. Deterministic order: underlying, expiry, type, strike."""
    frames = [f for f in frames if f is not None and len(f)]
    if not frames:
        return empty_frame()
    df = pd.concat([f.reindex(columns=COLUMNS) for f in frames], ignore_index=True)
    df["real_quote"] = df["real_quote"].eq(True).fillna(False).astype(bool)
    df["snap_ts"] = pd.to_datetime(df["snap_ts"], utc=True)
    df = df.sort_values([*DEDUP_KEY, "real_quote", "snap_ts"], kind="mergesort")
    df = df.drop_duplicates(DEDUP_KEY, keep="last")
    return df.sort_values(["underlying", "expiry", "option_type", "strike", "slot"],
                          kind="mergesort").reset_index(drop=True)


def day_path(out_dir: Path, snap_date: date) -> Path:
    return Path(out_dir) / f"{FILE_PREFIX}{snap_date.isoformat()}.parquet"


def read_day(path: Path) -> pd.DataFrame:
    """A day file, or ValueError if it is unreadable or lacks a stored column."""
    try:
        df = pd.read_parquet(path)
    except Exception as e:  # noqa: BLE001 - any unreadable file is the same condition
        raise ValueError(f"{Path(path).name} unreadable ({type(e).__name__})") from e
    lacking = sorted(set(COLUMNS) - set(df.columns))
    if lacking:
        raise ValueError(f"{Path(path).name} lacks column(s) {', '.join(lacking[:4])}")
    return df


def _move_aside(path: Path) -> Path:
    """Rename (never delete) a file that cannot be read; the leading underscore hides it from
    dataset readers and from the day-file glob."""
    stamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{CORRUPT_PREFIX}{path.name}.{stamp}")
    n = 1
    while target.exists():
        target = path.with_name(f"{CORRUPT_PREFIX}{path.name}.{stamp}.{n}")
        n += 1
    os.replace(path, target)
    return target


def write_day(df: pd.DataFrame, out_dir: Path, snap_date: date) -> tuple[Path, int, int, Optional[str]]:
    """Merge with the session's existing file (dedup) and write atomically (temp +
    os.replace): a failed write leaves the existing file untouched. A corrupt existing file is
    moved aside first. Returns (path, bytes, rows, name of a moved-aside file or None)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = day_path(out_dir, snap_date)
    frames, moved = [df], None
    if path.exists():
        try:
            frames.insert(0, read_day(path))
        except ValueError:
            moved = _move_aside(path).name
    table = to_table(dedup(frames))
    tmp = out_dir / f".{path.name}.{os.getpid()}.tmp"
    try:
        pq.write_table(table, tmp, compression="zstd", compression_level=9)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)      # our own temp file, left only by a failed write
    return path, path.stat().st_size, int(table.num_rows), moved


# ───────────────────────────── HTTP ─────────────────────────────

class ApiError(RuntimeError):
    """An Alpaca call failed for good. The message is built here (path, status, redacted
    body), never copied from an exception that might quote a header."""

    def __init__(self, status: Optional[int], message: str) -> None:
        super().__init__(f"HTTP {status}: {message}" if status else message)
        self.status = status


class AuthError(ApiError):
    """401: the keys are wrong — every later call would fail the same way."""


class BudgetSpent(ApiError):
    """The run's wall-clock budget is gone; no further request is made."""


class AlpacaReadClient:
    """GET-only Alpaca client: per-host pacing under the published limits, retries with backoff
    on 429 / 5xx / timeouts, a TOTAL time cap per request and per run, no redirects followed
    (the key headers would travel to the new host), and no secret in any message."""

    def __init__(self, key: str, secret: str, *, session: Optional[requests.Session] = None,
                 data_url: str = DATA_URL, trade_url: str = TRADE_URL,
                 data_per_min: float = DATA_PER_MIN, trade_per_min: float = TRADE_PER_MIN,
                 timeout: tuple[float, float] = (10.0, 30.0), max_attempts: int = 4,
                 hard_cap: float = REQUEST_HARD_CAP_S,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._secrets = tuple(v for v in (key, secret) if v)
        self._headers = {"APCA-API-KEY-ID": key.strip(), "APCA-API-SECRET-KEY": secret.strip(),
                         "Accept": "application/json"}
        self._injected = session
        self._s = session or requests.Session()
        self.data_url, self.trade_url = data_url.rstrip("/"), trade_url.rstrip("/")
        self._interval = {urlparse(self.data_url).netloc: 60.0 / data_per_min,
                          urlparse(self.trade_url).netloc: 60.0 / trade_per_min}
        self._last: dict[str, float] = {}
        self._timeout, self._max_attempts, self._hard_cap = timeout, max_attempts, hard_cap
        self._sleep_fn, self.clock = sleep, clock
        self.deadline: Optional[float] = None
        self.requests: Counter[str] = Counter()
        self.n_429 = 0
        self.n_retries = 0
        self.n_hung = 0
        self.limits_seen: dict[str, str] = {}

    # time ------------------------------------------------------------------
    def set_budget(self, seconds: float) -> None:
        self.deadline = self.clock() + seconds

    @property
    def budget_spent(self) -> bool:
        return self.deadline is not None and self.clock() >= self.deadline

    def _remaining(self) -> float:
        if self.deadline is None:
            return float("inf")
        left = self.deadline - self.clock()
        if left <= 0:
            raise BudgetSpent(None, "wall budget spent")
        return left

    def _sleep(self, seconds: float) -> None:
        self._sleep_fn(min(seconds, self._remaining()))

    def _pace(self, host: str) -> None:
        wait = self._last.get(host, float("-inf")) + self._interval.get(host, 0.0) - self.clock()
        if wait > 0:
            self._sleep(wait)
        self._last[host] = self.clock()

    def _reset_wait(self, headers: Mapping[str, str], default: float) -> float:
        try:
            reset = float(headers.get("X-RateLimit-Reset", ""))
        except (TypeError, ValueError):
            return default
        return min(max(reset - _utcnow().timestamp(), 0.0) + 0.5, 65.0)

    # one request -------------------------------------------------------------
    def _redact(self, text: str) -> str:
        for s in self._secrets:
            for form in {s, s.strip()}:
                text = text.replace(form, "***") if form else text
        return text

    def _fetch(self, url: str, params: Mapping[str, Any]) -> Any:
        """One GET bounded in TOTAL time (DNS, connect, headers and body), by running it in a
        daemon thread. A hung request is abandoned with its session; nothing ever joins it
        without a limit, so it cannot hold up the run or the interpreter's exit."""
        box: dict[str, Any] = {}
        session = self._s

        def work() -> None:
            try:
                box["response"] = session.get(url, headers=self._headers, params=dict(params),
                                              timeout=self._timeout, allow_redirects=False)
            except BaseException as e:  # noqa: BLE001 - carried to the caller's thread
                box["error"] = e

        worker = threading.Thread(target=work, daemon=True, name="alpaca-get")
        worker.start()
        worker.join(min(self._hard_cap, self._remaining()))
        if worker.is_alive():
            self.n_hung += 1
            self._s = self._injected or requests.Session()
            raise requests.Timeout("hung request abandoned")
        if "error" in box:
            raise box["error"]
        return box["response"]

    def get(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        host, path = urlparse(url).netloc, urlparse(url).path
        last_err = "no attempt made"
        for attempt in range(1, self._max_attempts + 1):
            self._remaining()                        # raises BudgetSpent
            if attempt > 1:
                self.n_retries += 1
            self._pace(host)
            try:
                r = self._fetch(url, params or {})
            except ApiError:                         # BudgetSpent, from the remaining-time check
                raise
            except (requests.Timeout, requests.ConnectionError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ContentDecodingError) as e:
                last_err = type(e).__name__
                self._sleep(min(2.0 ** (attempt - 1), 8.0))
                continue
            except Exception as e:  # noqa: BLE001 - InvalidHeader and friends quote the header
                raise ApiError(None, f"{path}: {type(e).__name__}") from None
            self.requests[host] += 1
            if r.headers.get("X-RateLimit-Limit"):
                self.limits_seen[host] = str(r.headers["X-RateLimit-Limit"])
            if r.status_code == 200:
                try:
                    payload = r.json()
                except ValueError:
                    raise ApiError(200, f"{path}: non-JSON body") from None
                remaining = str(r.headers.get("X-RateLimit-Remaining", ""))
                if remaining.isdigit() and int(remaining) <= 1:
                    self._sleep(self._reset_wait(r.headers, 5.0))
                return payload
            body = self._redact((r.text or "")[:200]).replace("\n", " ")
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
            raise ApiError(r.status_code, f"{path}: {body}")
        raise ApiError(None, f"{path}: gave up after {self._max_attempts} attempts ({last_err})")

    def _paged(self, url: str, params: Mapping[str, Any], key: str, kind: type,
               max_pages: int = 50) -> list[Any]:
        """Follow next_page_token. A page WITHOUT its key (or with the wrong type) is an error,
        never an empty page; a repeated token or > max_pages is an error, not a loop."""
        path = urlparse(url).path
        pages: list[Any] = []
        token: Optional[str] = None
        seen: set[str] = set()
        for _ in range(max_pages):
            p = dict(params)
            if token:
                p["page_token"] = token
            payload = self.get(url, p)
            if not isinstance(payload, dict):
                raise ApiError(200, f"{path}: payload is not an object")
            if not isinstance(payload.get(key), kind):
                raise ApiError(200, f"{path}: page has no usable '{key}'")
            pages.append(payload[key])
            token = payload.get("next_page_token")
            if not token:
                return pages
            if not isinstance(token, str) or token in seen:
                raise ApiError(None, f"{path}: repeated page token")
            seen.add(token)
        raise ApiError(None, f"{path}: more than {max_pages} pages")

    # endpoints ------------------------------------------------------------
    def calendar(self, start: date, end: date) -> list[Any]:
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
                  strike_lte: float) -> list[Any]:
        pages = self._paged(f"{self.trade_url}/v2/options/contracts", {
            "underlying_symbols": underlying, "status": "active", "limit": 10000,
            "expiration_date_gte": exp_gte.isoformat(),
            "expiration_date_lte": exp_lte.isoformat(),
            "strike_price_gte": f"{strike_gte:.2f}", "strike_price_lte": f"{strike_lte:.2f}"},
            "option_contracts", list)
        return [row for page in pages for row in page]

    def chain(self, underlying: str, expiry: date, strike_gte: float, strike_lte: float,
              feed: str) -> dict[str, Any]:
        pages = self._paged(f"{self.data_url}/v1beta1/options/snapshots/{underlying}", {
            "feed": feed, "limit": 1000, "expiration_date": expiry.isoformat(),
            "strike_price_gte": f"{strike_gte:.2f}", "strike_price_lte": f"{strike_lte:.2f}"},
            "snapshots", dict)
        merged: dict[str, Any] = {}
        for page in pages:
            merged.update(page)
        return merged


# ───────────────────────────── one run ─────────────────────────────

@dataclass
class RefPrice:
    """The band/bound references and the stored underlying fields for one underlying."""
    ref_low: float
    ref_high: float
    ref_source: str
    underlying_price: float
    underlying_price_ts: Optional[pd.Timestamp]
    underlying_day_close: float


@dataclass
class UnderlyingResult:
    """One underlying's rows plus what was expected, returned, and any error."""
    symbol: str
    rows: pd.DataFrame = field(default_factory=empty_frame)
    expiries: list[date] = field(default_factory=list)
    n_expected: int = 0
    n_listed: int = 0                # returned AND in the contract listing
    n_unlisted: int = 0              # returned but not in it (no style / OI)
    error: Optional[str] = None
    auth_failed: bool = False


@dataclass
class RunOutcome:
    """A run's exit code, status, one-line message and its run-log record."""
    exit_code: int
    status: str
    message: str
    record: dict[str, Any]


def reference_prices(client: AlpacaReadClient, cfg: ArchiveConfig,
                     snap_date: date) -> tuple[dict[str, RefPrice], dict[str, str]]:
    """Delayed-SIP latest trade and this session's close for every stock/ETF and every declared
    proxy, in one call. The references are the min and max of the two. An index gets its
    proxy's references and null underlying fields. Returns (prices, errors by symbol)."""
    needed = sorted({u.price_proxy or u.symbol for u in cfg.underlyings})
    snap = client.stock_snapshots(needed)
    flat = pd.json_normalize([v if isinstance(v := snap.get(s), dict) else {} for s in needed])
    rows = flat.reindex(columns=["latestTrade.p", "latestTrade.t", "dailyBar.c", "dailyBar.t",
                                 "prevDailyBar.c", "prevDailyBar.t"], index=range(len(needed)))
    rows.columns = ["p", "t", "c", "bt", "pc", "pbt"]
    rows.index = pd.Index(needed)
    last = _num(rows["p"])
    t, _ = _parse_ts(rows["t"])
    day = pd.Timestamp(snap_date)
    bar = _num(rows["c"]).where(_et_day(_parse_ts(rows["bt"])[0]).eq(day).fillna(False))
    prev = _num(rows["pc"]).where(_et_day(_parse_ts(rows["pbt"])[0]).eq(day).fillna(False))
    close = bar.fillna(prev)                         # the bar of THIS session, if either is it
    refs = pd.DataFrame({"last": last.where(last > 0), "close": close.where(close > 0)})
    low, high = refs.min(axis=1), refs.max(axis=1)
    prices: dict[str, RefPrice] = {}
    errors: dict[str, str] = {}
    for u in cfg.underlyings:
        src = u.price_proxy or u.symbol
        if not np.isfinite(low[src]):
            errors[u.symbol] = f"no usable reference price for {src}"
            continue
        if high[src] > 1.10 * low[src]:
            print(f"{TAG} WARN {u.symbol}: close and last trade differ by "
                  f"{high[src] / low[src] - 1:.0%}; the strike band spans both", flush=True)
        own = u.price_proxy is None
        prices[u.symbol] = RefPrice(
            float(low[src]), float(high[src]), "underlying" if own else f"proxy:{src}",
            float(last[src]) if own else np.nan,
            t[src] if own and pd.notna(t[src]) else None,
            float(close[src]) if own else np.nan)
    return prices, errors


def build_rows(snaps: Mapping[str, Any], listed: pd.DataFrame, spec: UnderlyingSpec,
               ref: RefPrice, cfg: ArchiveConfig, expiries: Sequence[date], snap_date: date,
               slot: str, snap_ts: datetime) -> pd.DataFrame:
    """One underlying's stored rows in the fixed schema, with the real-quote flag."""
    rows, stats = snapshots_frame(snaps, snap_date)
    if any(stats.values()):
        print(f"{TAG} WARN {spec.symbol}: dropped {stats['bad_entry']} non-object snapshots and "
              f"{stats['unparsed_symbol']} unparseable symbols; {stats['unparsed_ts']} "
              f"unparseable timestamps (those rows cannot be real)", flush=True)
    rows = rows[rows["root"].astype(str).eq(spec.symbol) & rows["expiry"].isin(list(expiries))]
    rows = rows.merge(listed[["contract", "style", "open_interest", "open_interest_date"]],
                      on="contract", how="left")
    rows = rows.assign(
        listed=rows["contract"].isin(listed["contract"]), snap_date=snap_date.isoformat(),
        slot=slot, snap_ts=snap_ts, underlying=spec.symbol,
        underlying_price=ref.underlying_price, underlying_price_ts=ref.underlying_price_ts,
        underlying_day_close=ref.underlying_day_close, ref_low=ref.ref_low,
        ref_high=ref.ref_high, ref_source=ref.ref_source, feed=cfg.feed, quote_rule=QUOTE_RULE,
        real_quote=False)
    out = to_table(rows).to_pandas()                 # cast here: an odd value stays in here
    out["real_quote"] = real_quote_mask(out, cfg.no_iv)
    return out


def fetch_underlying(client: AlpacaReadClient, spec: UnderlyingSpec, ref: RefPrice,
                     cfg: ArchiveConfig, snap_date: date, slot: str) -> UnderlyingResult:
    """Contracts (expiries + OI), then one chain call per selected expiry. Any failure becomes
    this underlying's error; the expiries that did come back are kept."""
    res = UnderlyingResult(spec.symbol)
    lo = round(ref.ref_low * (1.0 - cfg.strike_band), 2)
    hi = round(ref.ref_high * (1.0 + cfg.strike_band), 2)
    errors: list[str] = []
    snaps: dict[str, Any] = {}
    try:
        listed = contracts_frame(client.contracts(
            spec.symbol, snap_date + timedelta(days=1),
            snap_date + timedelta(days=cfg.horizon_days), lo, hi))
        listed = listed[listed["root"].astype(str).eq(spec.symbol)]
        res.expiries = select_expiries(listed["expiry"], snap_date, cfg.n_weekly, cfg.n_monthly)
        listed = listed[listed["expiry"].isin(res.expiries)]
        res.n_expected = int(len(listed))
        snap_ts = _utcnow()
        for exp in res.expiries:           # one network call per expiry (≤ n_weekly+n_monthly)
            try:
                snaps.update(client.chain(spec.symbol, exp, lo, hi, cfg.feed))
            except (AuthError, BudgetSpent):
                raise
            except ApiError as e:
                errors.append(f"{exp}: {e}")
    except AuthError as e:
        res.auth_failed = True
        errors.append(f"Alpaca rejected the keys ({e})")
    except ApiError as e:
        errors.append(str(e))
    except Exception as e:  # noqa: BLE001 - one underlying's odd payload must not cost the day
        errors.append(_where(e))
    if snaps:
        try:
            res.rows = build_rows(snaps, listed, spec, ref, cfg, res.expiries, snap_date, slot,
                                  snap_ts)
        except Exception as e:  # noqa: BLE001 - as above
            errors.append(f"rows not parsed: {_where(e)}")
    res.n_listed = int(res.rows["listed"].sum()) if len(res.rows) else 0
    res.n_unlisted = int(len(res.rows)) - res.n_listed
    if not errors and not res.expiries:
        errors.append("no listed expiries in the horizon")
    res.error = "; ".join(errors)[:300] or None
    return res


def append_run_log(out_dir: Path, record: Mapping[str, Any]) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(out_dir) / RUN_LOG_NAME, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str, sort_keys=True) + "\n")


def run_archive(cfg: ArchiveConfig, client: AlpacaReadClient, out_dir: Path,
                now_utc: Optional[datetime] = None, slot: str = "eod") -> RunOutcome:
    """One archive run. Whatever happens, one record of it reaches the run log."""
    now_utc = now_utc or _utcnow()
    rec: dict[str, Any] = {"run_ts": now_utc.isoformat(), "slot": slot,
                           "run_date_et": now_utc.astimezone(ET).date().isoformat(),
                           "quote_rule": QUOTE_RULE, "config_md5": cfg.md5,
                           "declared": len(cfg.declared)}
    try:
        return _run(cfg, client, Path(out_dir), now_utc, slot, rec)
    except Exception as e:
        rec.update(status="REFUSED" if isinstance(e, SlotError) else "CRASHED",
                   message=str(e) if isinstance(e, SlotError) else _where(e))
        try:
            append_run_log(out_dir, rec)
        except OSError:
            print(f"{TAG} WARN the run log could not be written either", flush=True)
        raise


def _run(cfg: ArchiveConfig, client: AlpacaReadClient, out_dir: Path, now_utc: datetime,
         slot: str, rec: dict[str, Any]) -> RunOutcome:
    t0 = client.clock()
    client.set_budget(cfg.wall_budget_seconds)
    now_et = now_utc.astimezone(ET)
    view = read_calendar(client, now_et.date())
    rec["calendar"] = view.record()
    if view.note:
        print(f"{TAG} WARN {view.note}; using the rule-based NYSE calendar", flush=True)
    session, why = resolve_session(now_et, view, slot)
    late = session is not None and session != now_et.date()
    if session is None or (late and _judge_session(out_dir, cfg, session, slot)[0]):
        msg = why if session is None else (f"{now_et.date()} {now_et:%H:%M} ET: nothing due; "
                                           f"session {session} is already captured")
        rec.update(status="SKIP", message=msg, wall_seconds=round(client.clock() - t0, 1))
        append_run_log(out_dir, rec)
        return RunOutcome(EXIT_OK, "SKIP", msg, rec)
    rec["snap_date"] = session.isoformat()
    disagreement = view.disagreement(now_et.date())
    for note in filter(None, (disagreement, f"late capture of session {session}" if late else "")):
        print(f"{TAG} WARN {note}", flush=True)

    results: list[UnderlyingResult] = []
    prices: dict[str, RefPrice] = {}
    price_errors: dict[str, str] = {}
    abort: Optional[str] = None
    try:
        prices, price_errors = reference_prices(client, cfg, session)
    except ApiError as e:
        abort = (f"Alpaca rejected the keys ({e})" if isinstance(e, AuthError)
                 else f"reference prices failed ({e})")
    except Exception as e:  # noqa: BLE001 - an odd payload is a FAILED day, not a crash
        abort = f"reference prices failed ({_where(e)})"
    for spec in cfg.underlyings:           # sequential by design: one paced key, no deadlock
        if client.budget_spent:
            abort = abort or "wall budget spent"
        if abort:
            results.append(UnderlyingResult(spec.symbol, error=f"not attempted: {abort}"))
        elif spec.symbol in price_errors:
            results.append(UnderlyingResult(spec.symbol, error=price_errors[spec.symbol]))
        else:
            res = fetch_underlying(client, spec, prices[spec.symbol], cfg, session, slot)
            results.append(res)
            if res.auth_failed:
                abort = res.error
    if abort:
        print(f"{TAG} ERROR {abort} - remaining underlyings not attempted", flush=True)

    df = dedup([r.rows for r in results])
    expected = {r.symbol: r.n_expected for r in results}
    verdict = judge(df, cfg, expected)
    cov = coverage_table(df, cfg.declared, expected)
    for r in results:
        c = cov.loc[r.symbol]
        print(f"{TAG} {r.symbol}: {c['expiries']}/{len(r.expiries)} expiries, {r.n_listed:,}/"
              f"{r.n_expected:,} contracts, {c['real']:,} real"
              + (f", {r.n_unlisted:,} served but not in the listing (no style/OI)"
                 if r.n_unlisted else "") + (f" - ERROR {r.error}" if r.error else ""),
              flush=True)
    unlisted = {r.symbol: r.n_unlisted for r in results if r.n_unlisted}
    rec.update(n_rows=verdict.n_rows, n_real=verdict.n_real,
               real_share=round(verdict.n_real / verdict.n_rows, 4) if verdict.n_rows else 0.0,
               covered=len(verdict.covered), missing=verdict.missing,
               errors={r.symbol: r.error for r in results if r.error},
               per_symbol={r.symbol: {"exp": r.n_expected, "ret": r.n_listed,
                                      "unl": r.n_unlisted, "nexp": len(r.expiries),
                                      "nret": int(cov.at[r.symbol, "expiries"]),
                                      "real": int(cov.at[r.symbol, "real"])} for r in results},
               requests=dict(client.requests), n_429=client.n_429, n_retries=client.n_retries,
               n_hung=client.n_hung, rate_limits=dict(client.limits_seen))
    status, msg = verdict.status, verdict.message
    if verdict.write:
        path, nbytes, nrows, moved = write_day(df, out_dir, session)
        rec.update(path=path.name, file_bytes=nbytes, file_rows=nrows, corrupt_moved=moved)
        msg += f"; wrote {path.name} ({nbytes / 1e6:.2f} MB, {nrows:,} rows)"
        if moved:
            status = "FAILED"
            msg = f"the earlier file was unreadable and moved aside to {moved}; {msg}"
    if unlisted:
        msg += f"; {sum(unlisted.values()):,} rows not in the contract listing {unlisted}"
    if disagreement:
        msg = f"{disagreement}; {msg}"
    wall = round(client.clock() - t0, 1)
    rec.update(status=status, message=msg, wall_seconds=wall)
    append_run_log(out_dir, rec)
    msg = f"{msg}; {sum(client.requests.values())} requests, {client.n_429} x 429, {wall:.0f} s"
    return RunOutcome(EXIT_OK if status == "OK" else EXIT_FAILED, status, msg, rec)


# ───────────────────────────── the store check (local verifier) ─────────────────────────────

def _run_records(out_dir: Path) -> list[dict[str, Any]]:
    path = Path(out_dir) / RUN_LOG_NAME
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _expected_for(records: Sequence[Mapping[str, Any]], session: date, slot: str) -> Optional[dict[str, int]]:
    """Per symbol, the most contracts any run that WROTE this session and slot expected (max: a
    later run with a truncated listing must not lower the bar). None = no such run."""
    mine = [r for r in records if r.get("snap_date") == session.isoformat()
            and r.get("slot") == slot and r.get("file_rows")]
    if not mine:
        return None
    out: dict[str, int] = {}
    for r in mine:
        try:
            counts = {str(sym): int(v["exp"]) for sym, v in r["per_symbol"].items()}
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        for sym, n in counts.items():
            out[sym] = max(out.get(sym, 0), n)
    return out or None


def _judge_session(out_dir: Path, cfg: ArchiveConfig, session: date, slot: str,
                   ) -> tuple[bool, str]:
    """Re-judge one session and slot by CONTENT: rows of that session only, the real-quote rule
    recomputed from raw columns (never the stored flag), completeness against the run log."""
    path = day_path(out_dir, session)
    if not path.exists():
        return False, f"FAILED: no {slot} capture for session {session} ({path.name} missing)"
    try:
        df = read_day(path)
    except ValueError as e:
        return False, f"FAILED: session {session}: {e}"
    df = df[df["snap_date"].astype(str).eq(session.isoformat())
            & df["slot"].astype(str).eq(slot)].copy()
    expected = _expected_for(_run_records(out_dir), session, slot)
    if expected is None:
        return False, (f"FAILED: session {session}: no run record for slot {slot}, so "
                       f"completeness cannot be judged")
    df["real_quote"] = real_quote_mask(df, cfg.no_iv)
    v = judge(df, cfg, expected)
    return v.status == "OK", f"{v.status}: session {session} {slot}: {v.message}"


def _first_session(out_dir: Path) -> Optional[date]:
    """The earliest session with a day file (a stray file name is ignored)."""
    found: list[date] = []
    for p in Path(out_dir).glob(f"{FILE_PREFIX}*.parquet"):
        try:
            found.append(date.fromisoformat(p.stem[len(FILE_PREFIX):]))
        except ValueError:
            continue
    return min(found, default=None)


def _has_slot(path: Path, slot: str) -> bool:
    try:
        return slot in pq.read_table(path, columns=["slot"]).column("slot").unique().to_pylist()
    except Exception:  # noqa: BLE001 - an unreadable file is not a capture
        return False


def verify_store(out_dir: Path, cfg: ArchiveConfig, now: Union[date, datetime]) -> tuple[bool, str]:
    """Is every session that is due captured? (now: a datetime in ET, or a date = 18:30 ET.)

    The last session that has closed is re-judged by content; every earlier session since the
    first file must have a readable eod capture, so an unrepaired gap alarms every day until it
    is recorded under ``acknowledged_gaps`` in the config. Offline: the rule-based calendar,
    corrected only by LATER runs' recorded Alpaca calendars (a past day they all omit was an
    ad-hoc closure). A run that claims today is closed is not believed."""
    out_dir = Path(out_dir)
    now_et = (now.astimezone(ET) if isinstance(now, datetime)
              else datetime.combine(now, dtime(18, 30), tzinfo=ET))
    today = now_et.date()
    records = _run_records(out_dir)
    listed: set[date] = set()
    omitted: set[date] = set()
    for r in records:
        try:
            cal = r["calendar"]
            if cal["source"] != "alpaca" or not cal["days"]:
                continue
            days = {date.fromisoformat(x) for x in cal["days"]}
            d, stop = date.fromisoformat(cal["from"]), date.fromisoformat(r["run_date_et"])
        except (KeyError, TypeError, ValueError):
            continue
        while d < stop:                              # only days already past at that run
            (listed if d in days else omitted).add(d)
            d += timedelta(days=1)
    closures = omitted - listed

    def is_open(d: date) -> bool:
        return d in listed or (is_trading_day_rules(d) and d not in closures)

    due_today = is_open(today) and now_et.time() >= REGULAR_CLOSE
    first = _first_session(out_dir)
    if first is None and not due_today:
        return True, f"SKIP: no capture is due yet ({today} {now_et:%H:%M} ET; the store is empty)"
    session = today if due_today else _previous(today, is_open)
    ok, msg = _judge_session(out_dir, cfg, session, "eod")
    gaps: list[date] = []
    if first is not None:
        d = first
        while d < session:
            if (is_open(d) and d not in cfg.acknowledged_gaps
                    and not _has_slot(day_path(out_dir, d), "eod")):
                gaps.append(d)
            d += timedelta(days=1)
    if gaps:
        msg = (f"FAILED: no eod capture for session(s) {', '.join(map(str, gaps))} (record them "
               f"under acknowledged_gaps once known); {msg}")
    excused = sorted(d for d in closures if is_trading_day_rules(d))
    if excused:
        msg += f"; excused as ad-hoc closures: {', '.join(map(str, excused))}"
    return ok and not gaps, msg


# ───────────────────────────── CLI ─────────────────────────────

def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                    help="store directory (default: data/macro_data/options)")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE,
                    help="read Alpaca keys from this file if not in the environment")
    ap.add_argument("--slot", choices=SLOTS, default="eod",
                    help="capture slot, part of the dedup key; must match the clock")
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
            ok, msg = verify_store(args.out_dir, cfg, _utcnow().astimezone(ET))
            print(f"{TAG} verify {msg}", flush=True)
            return EXIT_OK if ok else EXIT_FAILED
        client = AlpacaReadClient(*load_keys(args.env_file))
        out = run_archive(cfg, client, args.out_dir, slot=args.slot)
    except (ConfigError, KeysError, SlotError) as e:
        print(f"{TAG} FAILED options: {e}", flush=True)
        return EXIT_BROKEN
    except Exception as e:  # noqa: BLE001 — a crashed archiver must still be loud
        print(f"{TAG} FAILED options: archiver crashed: {_where(e)}", flush=True)
        return EXIT_BROKEN
    print(f"{TAG} {out.status} options: {out.message}", flush=True)
    return out.exit_code


if __name__ == "__main__":
    sys.exit(main())
