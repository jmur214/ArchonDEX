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
Files whose span starts on/after ALPACA_HISTORY_START come from Alpaca (`adjustment="all"`); deep
files (single names from 1970, SPY from 1993) come from yfinance (`auto_adjust=True`). On the
measured cadence (33 of 39 twinned names step at ex-dates, most quarterly) this branch is the
STEADY STATE — ~580 of ~730 files a quarter — and every pass is a substrate re-pin.

What the writer proves, rather than assumes (R's C-3/C-4):
  * the fetch MODE is asserted in a write record, never inferred from a parameter;
  * the basis is MEASURED at write time with a two-mode fetch (adjusted vs dividend-unadjusted):
    "measured_tr" when the ratio steps at ex-dates, "unverified: no ex-date in window" otherwise;
  * the re-fetch must COVER the cached span, or it is refused;
  * the parquet + csv pair is written ATOMICALLY: a failure of either leaves both originals intact.
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

ALPACA_HISTORY_START = pd.Timestamp("2016-01-01")
SPAN_SLACK_DAYS = 7            # a provider's first bar may trail the cached first bar by a holiday
BASIS_WINDOW_DAYS = 90         # calendar days ≈ 60 trading days for the two-mode basis measure
ROUNDING = 0.005               # adjusted closes round to the cent: 0.005/price per bar (R §3.1)
FP_NOISE = 1e-9
SEAM_RAIL = 0.25               # |first appended return| above this is refused unless a rescale was seen
OVERLAP_MIN_BARS = 10
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

#: (ticker, start, end, adjusted) -> OHLCV DataFrame on a tz-naive DatetimeIndex.
#: adjusted=True -> total return (dividends + splits); False -> split-adjusted only.
Provider = Callable[[str, pd.Timestamp, pd.Timestamp, bool], pd.DataFrame]


class WriterRefusal(RuntimeError):
    """The writer will not write: the evidence for a safe replacement is missing."""


@dataclass
class WriteRecord:
    ticker: str
    provider: str
    mode: str                      # the fetch mode ASSERTED: "adjusted" (total return)
    span_start: str
    span_end: str
    n_rows: int
    basis: str                     # "measured_tr" | "unverified: ..." — measured, not claimed
    basis_detail: dict
    cached_span: Optional[list]
    written_at: str


# ── pure primitives ───────────────────────────────────────────────────────────────

def choose_provider(cached_start: Optional[pd.Timestamp], requested_start: pd.Timestamp) -> str:
    """ONE provider per file, chosen by the span it must cover."""
    starts = [s for s in (cached_start, requested_start) if s is not None]
    return "alpaca" if min(starts) >= ALPACA_HISTORY_START else "yfinance"


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
                 write: bool = True, log_path: Optional[Path] = None) -> WriteRecord:
    """Replace `<ticker>_1d` whole with a total-return re-fetch from ONE provider — or refuse.

    Never writes unless: the provider covers the cached span, the basis is not anomalous, and the
    pair can be written atomically. `write=False` measures and returns the record only (the
    proof-on-a-copy mode).
    """
    cache_dir = Path(cache_dir)
    cached = _read_cached(cache_dir, ticker)
    cached_start = None if cached is None or cached.empty else pd.Timestamp(cached.index.min())
    if cached_start is None and new_ticker_start is None:
        raise WriterRefusal(f"{ticker}: no cached file and no start given for a new ticker")
    provider = choose_provider(cached_start, new_ticker_start or cached_start)
    start = cached_start if cached_start is not None else new_ticker_start
    fetched = providers[provider](ticker, start, today, True)
    ok, why = covers_span(fetched, cached)
    if not ok:
        raise WriterRefusal(f"{ticker} via {provider}: {why}")
    tail_start = today - pd.Timedelta(days=BASIS_WINDOW_DAYS)
    unadjusted = providers[provider](ticker, tail_start, today, False)
    basis = measure_basis(fetched["Close"][fetched.index >= tail_start], unadjusted["Close"])
    if basis["basis"].startswith("anomalous"):
        raise WriterRefusal(f"{ticker} via {provider}: {basis['basis']} — not writing")
    out = with_derived_columns(fetched)
    record = WriteRecord(
        ticker=ticker, provider=provider, mode="adjusted",
        span_start=str(out.index.min().date()), span_end=str(out.index.max().date()),
        n_rows=int(len(out)), basis=basis["basis"], basis_detail=basis,
        cached_span=(None if cached is None or cached.empty
                     else [str(cached.index.min().date()), str(cached.index.max().date())]),
        written_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if write:
        write_pair_atomically(out, cache_dir / "parquet" / f"{ticker}_1d.parquet",
                              cache_dir / f"{ticker}_1d.csv")
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


def alpaca_provider(ticker: str, start: pd.Timestamp, end: pd.Timestamp, adjusted: bool) -> pd.DataFrame:
    """Alpaca, same feed as DataManager (IEX): adjustment="all" -> total return; "split" otherwise."""
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    key = os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY")
    if not (key and secret):
        raise WriterRefusal("no Alpaca keys — the writer will not substitute another provider")
    client = StockHistoricalDataClient(key, secret)
    req = StockBarsRequest(symbol_or_symbols=ticker, timeframe=TimeFrame.Day,
                           start=pd.Timestamp(start).tz_localize("UTC"),
                           end=pd.Timestamp(end).tz_localize("UTC"),
                           adjustment="all" if adjusted else "split", feed="iex", limit=10000)
    df = client.get_stock_bars(req).df
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index().set_index("timestamp")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                            "close": "Close", "volume": "Volume"})
    return df[COLUMNS].sort_index()


DEFAULT_PROVIDERS: Dict[str, Provider] = {"alpaca": alpaca_provider, "yfinance": yfinance_provider}
