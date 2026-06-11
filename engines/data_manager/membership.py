"""
engines/data_manager/membership.py
==================================
Point-in-time S&P 500 membership loader (T-2026-06-10-136 Part A).

Data: data/universe/sp500_membership.parquet — (ticker, start, end) intervals
built by scripts/build_membership_panel_t136.py from the free fja05680/sp500
repo (Clenow base + maintained changes, 1996+), cross-checked against the
repo's own date-stamped component lists (99.8-100% agreement at 5 sample
dates) and Wikipedia current constituents (100%).

Caveats (documented in sp500_membership_meta.json): pre-2000 accuracy is
weaker in all free sources; ticker share-classes normalized '.' -> '-'.

API:
  load_membership() -> DataFrame[ticker, start, end]
  members_on(date) -> set[str]
  in_index(tickers, dates) -> DataFrame[bool]  (date x ticker membership mask)

No engine wiring here — pure data access. The universe_resolver integration
(per-date PIT universes inside a backtest) is a separate, flagged follow-up.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MEMBERSHIP_PARQUET = ROOT / "data" / "universe" / "sp500_membership.parquet"


@lru_cache(maxsize=1)
def load_membership(path: str | None = None) -> pd.DataFrame:
    """Membership intervals. `end` is NaT for current members."""
    p = Path(path) if path else MEMBERSHIP_PARQUET
    if not p.exists():
        raise FileNotFoundError(
            f"membership parquet missing: {p}. "
            f"Build via: python -m scripts.build_membership_panel_t136")
    df = pd.read_parquet(p)
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    return df


def members_on(date, path: str | None = None) -> set:
    d = pd.Timestamp(date)
    m = load_membership(path)
    mask = (m["start"] <= d) & (m["end"].isna() | (m["end"] >= d))
    return set(m.loc[mask, "ticker"])


def in_index(tickers: Iterable[str], dates: pd.DatetimeIndex,
             path: str | None = None) -> pd.DataFrame:
    """Boolean (date x ticker) membership mask, vectorized over intervals."""
    m = load_membership(path)
    tickers = list(tickers)
    out = pd.DataFrame(False, index=dates, columns=tickers)
    by_ticker = m.groupby("ticker")
    for t in tickers:
        if t not in by_ticker.groups:
            continue
        for _, row in by_ticker.get_group(t).iterrows():
            end = row["end"] if pd.notna(row["end"]) else dates[-1]
            out.loc[(out.index >= row["start"]) & (out.index <= end), t] = True
    return out


__all__ = ["load_membership", "members_on", "in_index", "MEMBERSHIP_PARQUET"]
