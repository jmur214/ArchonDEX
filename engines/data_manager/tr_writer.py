"""The TOTAL-RETURN writer for the processed price cache (data/processed/<TICKER>_1d.{csv,parquet}).

RULING (director, 2026-10-15, for the user to override): the cache convention is TOTAL RETURN —
exact post-seam, a constant-yield approximation pre-seam (`apply_dividend_strip`). No writer of
that convention existed in the code: the Alpaca fetch asks `adjustment="split"` and the yfinance
fallback `auto_adjust=False`. Agent R's design read (C-1) requires THIS writer to exist and be
proven on a copy BEFORE any convention guard is switched on, or the first ex-date after switch-on
refuses an append nothing can satisfy and the cache stalls stale.

Why it REPLACES files whole: a dividend back-adjusted series is not append-only — every new ex-date
rescales the provider's entire past. So a refresh is a whole-file re-fetch from ONE provider that
covers the cached span (mixing two providers' back-adjustments at a seam is the T-082b class).
ONE provider for the WHOLE universe — yfinance (`auto_adjust=True`) — never chosen per file
(director ruling 2026-10-15, provisional until the yfinance re-measure of the files below confirms
it). Measured on a copy, this overturns the per-span rule first built here (C-1: Alpaca for spans
starting on/after 2016): the project's Alpaca feed is IEX, whose daily history starts 2020-07-27.
Of the 172 files that rule sent to Alpaca, 69 came back empty, 69 of the 103 that returned could
not cover the cached span, and 99 of the 103 read DIFFERENT_CONVENTION against the cache — an IEX
tail is not the tape the cache was built from. The Alpaca writer provider is archived
(Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py). On the measured cadence (33 of 39
twinned names step at ex-dates, most quarterly) this branch is the STEADY STATE — ~580 of ~730
files a quarter — and every pass is a substrate re-pin.

What the writer proves, rather than assumes (R's C-3/C-4):
  * the fetch MODE is asserted in a write record, never inferred from a parameter;
  * the basis is MEASURED at write time with a two-mode fetch (adjusted vs dividend-unadjusted):
    "measured_tr" when the ratio steps at ex-dates, "unverified: no ex-date in window" otherwise;
  * the re-fetch must COVER the cached span, or it is refused;
  * the re-fetch must AGREE with the cache up to a rescale over the last OVERLAP_TAIL_BARS cached
    bars (classify_overlap: APPEND or RESCALED), or it is refused. The basis measure cannot catch a
    provider on the other convention — a split-only provider's two modes are identical, so it reads
    "unverified", exactly like a non-payer — so without this a split-only series replaces a
    total-return cache under a clean write record (Agent R's planted mismatch, 2026-10-15);
  * the cache's LAST BAR must equal the provider's true print (unadjusted close × splits after it),
    up to the dividends its own adjustment applied (the LEVEL rail, adopted 2026-10-15). A level
    change outside the identity needs a declaration (`config/level_declarations.json`), and a
    declared reused ticker is never written. Each write pins a per-file record under the cache;
  * the parquet + csv pair is written ATOMICALLY: a failure of either leaves both originals intact;
  * the Yahoo symbol comes from ONE table (`yahoo_symbols`): a share class is a spelling (BRK.B ->
    BRK-B); a rename is an IDENTITY claim held to the same span and overlap rails, and the record
    says "symbol mapped: X -> Y (kind)". No other symbol is ever tried.
The guard primitives (overlap classification at the rounding floor, the seam-return rail) live
here too, so the writer and the guard share one definition of "same convention".
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from engines.data_manager.yahoo_symbols import yahoo_symbol

UNIVERSE_PROVIDER = "yfinance"  # ONE provider for every file — see the module docstring
SPAN_SLACK_DAYS = 7            # a provider's first bar may trail the cached first bar by a holiday
BASIS_WINDOW_DAYS = 90         # calendar days ≈ 60 trading days for the two-mode basis measure
ROUNDING = 0.005               # adjusted closes round to the cent: 0.005/price per bar (R §3.1)
FP_NOISE = 1e-9
SEAM_RAIL = 0.25               # |first appended return| above this is refused unless a rescale was seen
OVERLAP_MIN_BARS = 10
#: The cached tail a whole-file replacement must agree with: one trading year, so the window holds
#: an ex-date of every payer that pays at least annually. Inside a window with no ex-date a
#: total-return tail and a split-only tail are IDENTICAL, so a short tail passes the other
#: convention. Measured on a copy of the cache (532 covered files): verdicts are identical at 126,
#: 252 and 504 bars and over the whole post-seam region — 419 RESCALED, 110 APPEND, and
#: DIFFERENT_CONVENTION on exactly AGG, EFA, VNQ (the split-only files backfill_t052 wrote) — while
#: a 40-bar tail reads EFA and VNQ as RESCALED.
OVERLAP_TAIL_BARS = 252
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

# ── the LEVEL rail (adopted 2026-10-15; docs/Sources/proposal_level_rail_last_bar_identity_2026-10-15.md)
#: |ln residual| tolerance for the last-bar level identity. Measured: legitimate files sit within
#: 0.0053 (APH, stale); scale defects at ln 10 = 2.30 — a factor of ~400 of separation.
LEVEL_TOLERANCE = 0.01
#: A cached file with no pinned write record was written by the pre-T-167 DataManager on
#: 2026-04-18/25 (the pre-merge backup); its total-return adjustment is as of this date, so the
#: identity's dividend factor runs from the file's last bar to here (a stale file's last bar was
#: scaled by the dividends paid between the two — APH 0.9947, explained to 1.0000).
LEGACY_ADJUSTED_AS_OF = pd.Timestamp("2026-04-25")
#: Per-file write records, pinned UNDER the cache (inside the substrate manifest's scope, so the
#: census can read them in the image) — R's condition (c).
WRITE_RECORDS_DIR = "_write_records"
LEVEL_DECLARATIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "level_declarations.json"
CANONICAL_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

#: symbol -> DataFrame indexed by date with columns "Dividends" and "Stock Splits" (the provider's
#: corporate-actions record, in the same split basis as its unadjusted closes).
Actions = Callable[[str], pd.DataFrame]

#: (ticker, start, end, adjusted) -> OHLCV DataFrame on a tz-naive DatetimeIndex.
#: adjusted=True -> total return (dividends + splits); False -> split-adjusted only.
Provider = Callable[[str, pd.Timestamp, pd.Timestamp, bool], pd.DataFrame]


class WriterRefusal(RuntimeError):
    """The writer will not write: the evidence for a safe replacement is missing."""

    def __init__(self, message: str, detail: Optional[dict] = None):
        super().__init__(message)
        self.detail = detail or {}       # the measured evidence, for the caller's record


@dataclass
class WriteRecord:
    ticker: str
    provider: str
    symbol_mapped: Optional[str]   # "X -> Y (share class|rename)"; None when fetched as named
    mode: str                     # the fetch mode ASSERTED: "adjusted" (total return)
    span_start: str
    span_end: str
    n_rows: int
    basis: str                     # "measured_tr" | "unverified: ..." — measured, not claimed
    basis_detail: dict
    overlap: Optional[dict]        # classify_overlap vs the cached tail; None for a new ticker
    cached_span: Optional[list]
    written_at: str
    level: Optional[dict] = None   # the last-bar identity (None for a new ticker)
    level_declared: Optional[dict] = None   # the declaration a level change was written under
    adjusted_as_of: Optional[str] = None    # the date this file's total-return adjustment is as of


# ── pure primitives ───────────────────────────────────────────────────────────────

def covers_span(new: Optional[pd.DataFrame], cached: Optional[pd.DataFrame],
                slack_days: int = SPAN_SLACK_DAYS) -> Tuple[bool, str]:
    """A whole-file replacement must cover everything the cached file holds."""
    if new is None or new.empty:
        return False, "the provider returned no bars"
    if cached is None or cached.empty:
        return True, "no cached span to cover (a new ticker)"
    lead = (new.index.min() - cached.index.min()).days
    if lead > slack_days:
        return False, (f"re-fetch starts {new.index.min().date()} but the cached span starts "
                       f"{cached.index.min().date()} ({lead} days later) — it cannot replace the file")
    if new.index.max() < cached.index.max():
        return False, (f"re-fetch ends {new.index.max().date()}, before the cached end "
                       f"{cached.index.max().date()}")
    return True, "covers the cached span"


def _floor(price: pd.Series) -> pd.Series:
    """Per-bar rounding floor in log-ratio units: a cent of rounding at this price level."""
    return ROUNDING / price.abs().clip(lower=1e-6) + FP_NOISE


def measure_basis(adjusted_close: pd.Series, unadjusted_close: pd.Series) -> dict:
    """Two-mode measurement (R's C-4). Total-return back-adjustment makes adjusted/unadjusted RISE
    toward 1 in steps at ex-dates; identical series mean no ex-date fell in the window."""
    j = pd.concat([adjusted_close.rename("adj"), unadjusted_close.rename("raw")],
                  axis=1, join="inner").dropna()
    if len(j) < 20:
        return {"basis": "unverified: too few common bars", "n_common": int(len(j))}
    lr = np.log(j["adj"] / j["raw"])
    d = lr.diff().dropna()
    floor = _floor(j["raw"]).reindex(d.index)
    steps = d[d.abs() > 2 * floor]
    detail = {"n_common": int(len(j)), "n_steps": int(len(steps)),
              "step_dates": [str(x.date()) for x in steps.index[:12]],
              "log_ratio_first": float(lr.iloc[0]), "log_ratio_last": float(lr.iloc[-1])}
    if steps.empty:
        return {"basis": "unverified: no ex-date in window", **detail}
    if (steps < 0).any():
        return {"basis": "anomalous: adjusted/unadjusted ratio FELL at a step", **detail}
    return {"basis": "measured_tr", **detail}


def classify_overlap(cached_close: pd.Series, fetched_close: pd.Series) -> dict:
    """The guard's test on an overlap window (R §3.1): the same convention reads ratio 1 at the
    rounding floor; a rescale (a new ex-date or split after the window) reads a CONSTANT ratio ≠ 1;
    anything that moves within the window — a step or a slope — is a different convention."""
    j = pd.concat([cached_close.rename("c"), fetched_close.rename("f")], axis=1, join="inner").dropna()
    if len(j) < OVERLAP_MIN_BARS:
        return {"verdict": "INSUFFICIENT", "n": int(len(j))}
    lr = np.log(j["f"] / j["c"])
    floor = _floor(j["c"])
    med = float(lr.median())
    resid = lr - med
    t = (j.index - j.index[0]).days.to_numpy(dtype=float)
    slope = float(np.polyfit(t, lr.to_numpy(), 1)[0]) if t[-1] > 0 else 0.0
    slope_move = abs(slope * t[-1])                      # total drift across the window
    detail = {"n": int(len(j)), "median_log_ratio": med, "slope_move": slope_move,
              "max_resid": float(resid.abs().max()), "floor_median": float(floor.median())}
    if (resid.abs() > 3 * floor).any() or slope_move > 3 * float(floor.median()):
        return {"verdict": "DIFFERENT_CONVENTION", **detail}
    if abs(med) <= 2 * float(floor.median()):
        return {"verdict": "APPEND", **detail}
    return {"verdict": "RESCALED", "ratio": float(np.exp(med)), **detail}


def seam_return_ok(last_cached_close: float, first_new_close: float, rescaled: bool) -> Tuple[bool, float]:
    """R's C-3 rail: an UNADJUSTED provider after a split matches the pre-split overlap and would
    append post-split bars at a fraction of the price. Catch the jump at the seam."""
    r = first_new_close / last_cached_close - 1.0
    return (rescaled or abs(r) < SEAM_RAIL), float(r)


def with_derived_columns(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """ATR + PrevClose per project convention (scripts/merge_stooq_alpaca_substrate.py)."""
    df = ohlcv[COLUMNS].sort_index().copy()
    tr = pd.concat([(df["High"] - df["Low"]).abs(),
                    (df["High"] - df["Close"].shift()).abs(),
                    (df["Low"] - df["Close"].shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    df["PrevClose"] = df["Close"].shift(1)
    df.index.name = "Date"
    return df


def write_pair_atomically(df: pd.DataFrame, parquet_path: Path, csv_path: Path) -> None:
    """Both temp files are written first; only then are both swapped in. A failure while writing
    either leaves BOTH originals untouched (R §3.2: today each write swallows the other's failure,
    and readers use parquet first)."""
    parquet_path, csv_path = Path(parquet_path), Path(csv_path)
    tmp_pq = parquet_path.with_name(parquet_path.name + ".writing")
    tmp_csv = csv_path.with_name(csv_path.name + ".writing")
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(tmp_pq, index=True)
        df.to_csv(tmp_csv, date_format="%Y-%m-%d")
    except Exception:
        for tmp in (tmp_pq, tmp_csv):
            if tmp.exists():
                tmp.unlink()              # temps only — the originals were never opened
        raise
    os.replace(tmp_csv, csv_path)
    os.replace(tmp_pq, parquet_path)


# ── the LEVEL rail ────────────────────────────────────────────────────────────────

def load_level_declarations(path: Path = LEVEL_DECLARATIONS_PATH) -> Dict[str, dict]:
    """The hand-set facts the identity cannot establish: per name, `kind` (`scale_defect` — a level
    change the write may make if `declared_ratio` explains it; `reused_ticker` — class (i), never
    written), with its source. An absent file means no declarations; an unreadable one raises."""
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("declarations", {})


def level_identity(cached_close: pd.Series, unadjusted: pd.Series, actions: pd.DataFrame,
                   adjusted_as_of: pd.Timestamp) -> dict:
    """The cache's last bar against the TRUE PRINT the provider reconstructs:
    true_print = unadjusted(d) × Π(split factors after d);  identity = cache(d) / true_print;
    the dividend factor the cache's own adjustment applied after d (ex-dates in (d, adjusted_as_of]);
    residual = identity / that factor. A correct cached LEVEL reads residual 1."""
    d = pd.Timestamp(cached_close.index.max())
    c = float(cached_close.iloc[-1])
    upto = unadjusted.loc[:d]
    if upto.empty:
        raise WriterRefusal(f"no provider print at or before the cache's last bar {d.date()}",
                            detail={"level": {"d_last": str(d.date())}})
    raw_d = float(upto.iloc[-1])
    actions = actions.copy()
    actions.index = pd.to_datetime(actions.index)      # an EMPTY record has no datetime index
    splits = actions["Stock Splits"] if "Stock Splits" in actions else pd.Series(dtype=float)
    splits = splits[(splits > 0) & (splits.index > d)]
    mult = float(splits.prod()) if len(splits) else 1.0
    true_print = raw_d * mult
    divs = actions["Dividends"] if "Dividends" in actions else pd.Series(dtype=float)
    divs = divs[(divs > 0) & (divs.index > d) & (divs.index <= pd.Timestamp(adjusted_as_of))]
    factor = 1.0
    for ex, dv in divs.items():
        prev = unadjusted.loc[:ex - pd.Timedelta(days=1)]
        if prev.empty:
            raise WriterRefusal(f"no provider close before ex-date {ex.date()}",
                                detail={"level": {"d_last": str(d.date())}})
        factor *= 1.0 - float(dv) / float(prev.iloc[-1])
    identity = c / true_print
    residual = identity / factor
    return {"d_last": str(d.date()), "cache_close": c, "unadjusted_close": raw_d,
            "splits_after": mult, "true_print": true_print, "identity": identity,
            "dividend_factor": factor, "adjusted_as_of": str(pd.Timestamp(adjusted_as_of).date()),
            "residual": residual, "log_residual": float(np.log(residual))}


def _write_record_path(cache_dir: Path, ticker: str) -> Path:
    return Path(cache_dir) / WRITE_RECORDS_DIR / f"{ticker}.json"


def _read_write_record(cache_dir: Path, ticker: str) -> Optional[dict]:
    p = _write_record_path(cache_dir, ticker)
    return json.loads(p.read_text()) if p.exists() else None


def _write_record_atomically(cache_dir: Path, record: "WriteRecord") -> None:
    p = _write_record_path(cache_dir, record.ticker)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".writing")
    tmp.write_text(json.dumps(asdict(record), indent=1, default=str))
    os.replace(tmp, p)


def substrate_level_declarations(cache_dir: Path) -> dict:
    """The census block (`level_declarations`): every file in this substrate whose CURRENT version
    was written under a level declaration, read from the pinned per-file records. The records
    directory's presence is reported, never assumed: a substrate written before the rail has no
    records, which reads `records_dir_present: False`, not as a clean zero."""
    d = Path(cache_dir) / WRITE_RECORDS_DIR
    out = {"records_dir_present": d.is_dir(), "declared": {}}
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        rec = json.loads(p.read_text())
        if rec.get("level_declared"):
            out["declared"][rec["ticker"]] = {"kind": rec["level_declared"].get("kind"),
                                              "declared_ratio": rec["level_declared"].get("declared_ratio"),
                                              "written_at": rec.get("written_at")}
    return out


# ── the writer ────────────────────────────────────────────────────────────────────

def _read_cached(cache_dir: Path, ticker: str) -> Optional[pd.DataFrame]:
    pq = cache_dir / "parquet" / f"{ticker}_1d.parquet"
    csv = cache_dir / f"{ticker}_1d.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    if csv.exists():
        return pd.read_csv(csv, parse_dates=["Date"]).set_index("Date")
    return None


def full_refetch(ticker: str, cache_dir: Path, providers: Dict[str, Provider], *,
                 today: pd.Timestamp, new_ticker_start: Optional[pd.Timestamp] = None,
                 write: bool = True, log_path: Optional[Path] = None,
                 actions: Optional[Actions] = None,
                 declarations: Optional[Dict[str, dict]] = None) -> WriteRecord:
    """Replace `<ticker>_1d` whole with a total-return re-fetch from THE universe provider — or refuse.

    Never writes unless: the provider covers the cached span, the basis is not anomalous, the
    re-fetch agrees with the cached tail up to a rescale (APPEND or RESCALED — DIFFERENT_CONVENTION,
    and an overlap too short to measure when a cache exists, are refused), the cache's LAST BAR
    equals the provider's true print up to the dividends its own adjustment applied (the LEVEL rail;
    a level change outside it needs a matching declaration, and a declared reused ticker is never
    written), and the pair can be written atomically. `actions` (the provider's dividend/split
    record) is REQUIRED when a cache exists: without it the identity cannot be checked, and the
    writer refuses. `write=False` measures and returns the record only (the proof-on-a-copy mode).
    """
    cache_dir = Path(cache_dir)
    cached = _read_cached(cache_dir, ticker)
    cached_start = None if cached is None or cached.empty else pd.Timestamp(cached.index.min())
    if cached_start is None and new_ticker_start is None:
        raise WriterRefusal(f"{ticker}: no cached file and no start given for a new ticker")
    provider = UNIVERSE_PROVIDER
    if provider not in providers:
        raise WriterRefusal(f"{ticker}: no {provider} provider given — the writer will not "
                            f"substitute another provider for the universe's")
    symbol, kind = yahoo_symbol(ticker)      # the universe provider's ONE table; no symbol is guessed
    mapped = None if kind is None else f"{ticker} -> {symbol} ({kind})"
    who = f"{ticker} via {provider}" + ("" if mapped is None else f" [symbol mapped: {mapped}]")
    declarations = load_level_declarations() if declarations is None else declarations
    decl = declarations.get(ticker)
    if decl and decl.get("kind") == "reused_ticker":       # before any provider call
        raise WriterRefusal(f"{who}: declared a REUSED TICKER (class (i): {decl.get('source', '')}) — "
                            f"the cached file is another entity; never written",
                            detail={"level_declared": decl, "symbol_mapped": mapped})
    start = cached_start if cached_start is not None else new_ticker_start
    fetched = providers[provider](symbol, start, today, True)
    ok, why = covers_span(fetched, cached)
    if not ok:
        raise WriterRefusal(f"{who}: {why}", detail={"symbol_mapped": mapped})
    tail_start = today - pd.Timedelta(days=BASIS_WINDOW_DAYS)
    unadjusted = providers[provider](symbol, tail_start, today, False)
    basis = measure_basis(fetched["Close"][fetched.index >= tail_start], unadjusted["Close"])
    if basis["basis"].startswith("anomalous"):
        raise WriterRefusal(f"{who}: {basis['basis']} — not writing",
                            detail={"basis": basis, "symbol_mapped": mapped})
    overlap = None
    if cached is not None and not cached.empty:
        cached_tail = cached["Close"].iloc[-OVERLAP_TAIL_BARS:]
        overlap = classify_overlap(cached_tail,
                                   fetched["Close"][fetched.index >= cached_tail.index.min()])
        if overlap["verdict"] not in ("APPEND", "RESCALED"):
            raise WriterRefusal(
                f"{who}: the re-fetch reads {overlap['verdict']} against the last "
                f"{len(cached_tail)} cached bars (basis {basis['basis']!r}) — a whole-file "
                f"replacement must agree with the cache up to a rescale; not writing",
                detail={"overlap": overlap, "basis": basis, "symbol_mapped": mapped})
    level, level_declared = None, None
    if cached is not None and not cached.empty:
        if actions is None:
            raise WriterRefusal(f"{who}: no corporate-actions record given — the last-bar level "
                                f"identity cannot be checked; not writing",
                                detail={"symbol_mapped": mapped})
        prior = _read_write_record(cache_dir, ticker)
        as_of = (pd.Timestamp(prior["adjusted_as_of"]) if prior and prior.get("adjusted_as_of")
                 else LEGACY_ADJUSTED_AS_OF)
        d_last = pd.Timestamp(cached.index.max())
        unadj = providers[provider](symbol, d_last - pd.Timedelta(days=10),
                                    max(d_last, as_of) + pd.Timedelta(days=3), False)
        level = level_identity(cached["Close"], unadj["Close"], actions(symbol), as_of)
        lr = level["log_residual"]
        if decl and decl.get("kind") == "scale_defect":
            if abs(lr + float(np.log(decl["declared_ratio"]))) <= LEVEL_TOLERANCE:
                level_declared = decl
            elif abs(lr) <= LEVEL_TOLERANCE:
                raise WriterRefusal(
                    f"{who}: a scale defect is DECLARED but the level identity holds (residual "
                    f"{level['residual']:.4f}) — the declaration no longer matches the data; re-rule it",
                    detail={"level": level, "level_declared": decl, "symbol_mapped": mapped})
            else:
                raise WriterRefusal(
                    f"{who}: the declared ratio {decl['declared_ratio']} does not explain the level "
                    f"residual {level['residual']:.4f}; not writing",
                    detail={"level": level, "level_declared": decl, "symbol_mapped": mapped})
        elif abs(lr) > LEVEL_TOLERANCE:
            raise WriterRefusal(
                f"{who}: LEVEL IDENTITY fails — the cache's last bar ({level['d_last']}) is "
                f"{level['identity']:.4f} of the provider's true print, residual "
                f"{level['residual']:.4f} after the provider's dividends; a level change outside the "
                f"identity needs a declaration; not writing",
                detail={"level": level, "symbol_mapped": mapped})
    out = with_derived_columns(fetched)
    record = WriteRecord(
        ticker=ticker, provider=provider, symbol_mapped=mapped, mode="adjusted",
        span_start=str(out.index.min().date()), span_end=str(out.index.max().date()),
        n_rows=int(len(out)), basis=basis["basis"], basis_detail=basis, overlap=overlap,
        cached_span=(None if cached is None or cached.empty
                     else [str(cached.index.min().date()), str(cached.index.max().date())]),
        written_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        level=level, level_declared=level_declared, adjusted_as_of=str(pd.Timestamp(today).date()))
    if write:
        write_pair_atomically(out, cache_dir / "parquet" / f"{ticker}_1d.parquet",
                              cache_dir / f"{ticker}_1d.csv")
        _write_record_atomically(cache_dir, record)      # pinned under the substrate (R's (c))
        if log_path is not None:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(asdict(record)) + "\n")
    return record


# ── real providers (network; injected, so tests never touch them) ─────────────────

def yfinance_provider(ticker: str, start: pd.Timestamp, end: pd.Timestamp, adjusted: bool) -> pd.DataFrame:
    """yfinance: auto_adjust=True -> total return; False -> split-adjusted Close."""
    import yfinance as yf
    df = yf.download(ticker, start=str(pd.Timestamp(start).date()),
                     end=str((pd.Timestamp(end) + pd.Timedelta(days=1)).date()),
                     auto_adjust=adjusted, progress=False, actions=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[COLUMNS].sort_index()


def yfinance_actions(symbol: str) -> pd.DataFrame:
    """yfinance's corporate-actions record (dividends and split factors), tz-naive."""
    import yfinance as yf
    a = yf.Ticker(symbol).actions
    if a is None or a.empty:
        return pd.DataFrame(columns=["Dividends", "Stock Splits"])
    idx = pd.to_datetime(a.index)
    a.index = idx.tz_localize(None) if idx.tz is not None else idx
    return a


#: The default actions record for the universe provider (passed explicitly; never implied).
DEFAULT_ACTIONS: Actions = yfinance_actions

#: The universe provider only. The Alpaca provider is archived
#: (Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py) — see the module docstring.
DEFAULT_PROVIDERS: Dict[str, Provider] = {UNIVERSE_PROVIDER: yfinance_provider}
