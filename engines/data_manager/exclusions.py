"""Declared data exclusions: bars the loader WITHHOLDS, by name, with a reason, and records.

Ruled 2026-10-15 (item (d)). DAL's cached history is two securities stitched under one ticker: the
old Delta (equity cancelled in the 2005–07 bankruptcy) at 3,000–8,000, then the new Delta from its
2007-05-03 listing. The loader used to divide such a series by 10 "to fix scaling", which half-masked
the corruption. Now the series loads at its stored level, and the pre-2007 bars are WITHHELD by this
declaration — acknowledged, never silent:

  * every application is recorded process-wide (reset per run with the data-feed record), and the
    census emits it under the ruled key (`dal_pre2007_excluded`);
  * nothing is deleted: the stitched file stays on disk as the archived artifact;
  * it FAILS CLOSED if the declaration and the data disagree (a bar that survives the exclusion
    still carries the corruption signature) — then the declaration is wrong, and nothing is served.

No discontinuity at the cutoff: the corrupt block ENDS earlier — the raw bars just before
2007-05-03 already sit near 16.9, not at the 5,000 level. The cutoff is the new listing date BY
DECLARATION, and the 1,000 signature (`max_close_after`) is the guard, so a reader should not expect
a price jump at the cutoff. (Agent R's O-4.)

Interim by ruling: at the substrate cutover, DAL becomes DAL_OLD + DAL if a delisted-capable
total-return source exists; otherwise this exclusion stands permanently, with its reason.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

DECLARED_EXCLUSIONS: Dict[str, dict] = {
    "DAL": {
        "before": "2007-05-03",
        "census_key": "dal_pre2007_excluded",
        "reason": ("stitched identity — old Delta cancelled in the 2005–07 bankruptcy; "
                   "new Delta listed 2007-05"),
        # The corruption signature: if any bar served AFTER the exclusion exceeds this close, the
        # declaration no longer matches the data (fail closed).
        "max_close_after": 1000.0,
    },
}

#: The second exclusion KIND — `ticker` — ruled 2026-10-15 (the AZO/MTD/NVR HIGH). A bars-kind
#: withholding of a WHOLE history would serve an empty frame for a ticker that stays resolved: the
#: panel then runs short of the resolved universe and census invariant 2 fails every canonical run —
#: and raising the panel allow-list to hide that would also hide a genuine shrink (the T-167 class).
#: So a ticker-kind name is removed at universe RESOLUTION (`resolve_universe`) and from PIT
#: membership (`clip_membership`): the resolved universe and the panel BOTH exclude it, and the
#: allow-list stays 0. Recorded under its own census key, written by BOTH census producers.
#:
#: AZO, MTD and NVR sit at exactly one tenth of their true price for their whole history in the
#: canonical cache: the old loader's ÷10 auto-scale fired on their Alpaca legs (true medians above
#: 1,000) at MERGE time and `fit_ratio_loglinear` carried the 0.1 back through the Stooq years. The
#: files are NOT edited (a substrate change would invalidate every anchor's digest). The exclusion
#: lifts at re-pin #2 only through `lift_verified`: each written level must agree with the declared
#: ratio at the evidence date.
DECLARED_TICKER_EXCLUSIONS: Dict[str, dict] = {
    t: {"census_key": "scale_defect_div10",
        "reason": "scale defect ÷10 baked at the T-082b merge",
        "declared_ratio": 10.0,
        # the evidence the declaration was made on: the canonical cache's close at a reference date
        "evidence": {"date": "2021-06-01", "cache_close": close}}
    for t, close in (("AZO", 141.08), ("MTD", 129.63), ("NVR", 484.10))
}
LIFT_TOLERANCE = 1e-3          # |written / (cache_close × declared_ratio) − 1| for the lift

_BARS_APPLIED: Dict[str, dict] = {}        # reset per run
_MEMBERSHIP_APPLIED: Dict[str, dict] = {}  # membership loads once per process (lru_cache)
_TICKERS_APPLIED: Dict[str, set] = {}      # ticker -> where withheld ("resolution"); reset per run
_TICKER_MEMBERSHIP_APPLIED: Dict[str, int] = {}  # ticker -> intervals dropped; kept per process


class ExclusionMismatchError(RuntimeError):
    """A declared exclusion no longer matches the data it was declared for."""


def _dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    """The bar dates of a RAW frame: its DatetimeIndex, or a Date/timestamp column (csv reads)."""
    if isinstance(df.index, pd.DatetimeIndex):
        return pd.DatetimeIndex(df.index).tz_localize(None) if df.index.tz is not None else df.index
    for col in ("Date", "date", "timestamp", "Datetime"):
        if col in df.columns:
            d = pd.to_datetime(df[col], errors="coerce", utc=True)
            return pd.DatetimeIndex(d).tz_convert(None)
    return pd.DatetimeIndex(pd.to_datetime(df.index, errors="coerce"))


def truncate_declared(ticker: str, raw: pd.DataFrame) -> pd.DataFrame:
    """STEP (a), on the RAW frame BEFORE normalization: drop the declared-excluded bars and record
    it. Before, not after — normalization's bad-tick band is a ROLLING window, so excluded bars
    left in would still shape the cleaning of the legitimate bars next to them (found by test: a
    stitched 5,000-level block made the band drop the first weeks of good post-cutoff bars).
    A pure filter: it never raises, so no read-failure handler can mistake it for corruption."""
    spec = DECLARED_EXCLUSIONS.get(ticker)
    if spec is None or raw is None or len(raw) == 0:
        return raw
    dates = _dates(raw)
    keep = ~(dates < pd.Timestamp(spec["before"]))
    n_withheld = int((~keep).sum())
    prev = _BARS_APPLIED.get(ticker, {})
    _BARS_APPLIED[ticker] = {"census_key": spec["census_key"], "before": spec["before"],
                             "reason": spec["reason"],
                             "n_bars_withheld": max(n_withheld, prev.get("n_bars_withheld", 0))}
    return raw.loc[keep]


def check_declared(ticker: str, served: pd.DataFrame) -> pd.DataFrame:
    """STEP (b), on the SERVED frame, outside any read error handling: fail closed if a bar that
    survived the exclusion still carries the corruption signature — the declaration is then wrong."""
    spec = DECLARED_EXCLUSIONS.get(ticker)
    if spec is None or served is None or len(served) == 0 or "Close" not in served.columns:
        return served
    worst = float(served["Close"].max())
    if worst > spec["max_close_after"]:
        raise ExclusionMismatchError(
            f"{ticker}: declared exclusion '{spec['census_key']}' withholds bars before "
            f"{spec['before']}, but a bar served after it closes at {worst:.2f} "
            f"(> {spec['max_close_after']}) — the declaration no longer matches the data; "
            f"nothing is served until it is re-ruled ({spec['reason']}).")
    return served


def withhold_excluded_bars(ticker: str, df: pd.DataFrame) -> pd.DataFrame:
    """Both steps on an already-normalized frame (the network-fetch serve point)."""
    return check_declared(ticker, truncate_declared(ticker, df))


def clip_membership(m: pd.DataFrame) -> pd.DataFrame:
    """Apply the declarations to PIT membership intervals (`ticker`, `start`, `end`): an interval
    is clipped to start at the cutoff, and dropped if it ended before it."""
    out = m.copy()
    for ticker, spec in DECLARED_EXCLUSIONS.items():
        cutoff = pd.Timestamp(spec["before"])
        rows = out["ticker"] == ticker
        if not rows.any():
            continue
        ended_before = rows & out["end"].notna() & (out["end"] < cutoff)
        clipped = rows & ~ended_before & (out["start"] < cutoff)
        out.loc[clipped, "start"] = cutoff
        out = out.loc[~ended_before]
        _MEMBERSHIP_APPLIED[ticker] = {"census_key": spec["census_key"], "before": spec["before"],
                                       "intervals_dropped": int(ended_before.sum()),
                                       "intervals_clipped": int(clipped.sum())}
    for ticker in DECLARED_TICKER_EXCLUSIONS:      # the ticker kind: every interval goes
        rows = out["ticker"] == ticker
        if rows.any():
            _TICKER_MEMBERSHIP_APPLIED[ticker] = int(rows.sum())
            out = out.loc[~rows]
    return out


def withhold_declared_tickers(tickers, *, where: str) -> list:
    """The ticker kind at a UNIVERSE: remove every declared name and record where it was withheld.
    A pure filter (never raises), order preserved."""
    kept = []
    for t in tickers:
        if t in DECLARED_TICKER_EXCLUSIONS:
            _TICKERS_APPLIED.setdefault(t, set()).add(where)
        else:
            kept.append(t)
    return kept


def lift_verified(ticker: str, written_close_at_evidence_date: float) -> bool:
    """The re-pin #2 lift lock: a ticker-kind declaration may be lifted only when the WRITTEN level
    at the evidence date equals the declared cache level × the declared ratio (the defect undone,
    exactly). Anything else — still ÷10, or a different factor — keeps the exclusion."""
    spec = DECLARED_TICKER_EXCLUSIONS[ticker]
    expected = spec["evidence"]["cache_close"] * spec["declared_ratio"]
    return abs(float(written_close_at_evidence_date) / expected - 1.0) <= LIFT_TOLERANCE


def ticker_exclusions_applied() -> Dict[str, dict]:
    """The census block for the ticker kind: every declared name withheld in this run (at
    resolution) or in this process's PIT membership, keyed by census key."""
    out: Dict[str, dict] = {}
    names = sorted(set(_TICKERS_APPLIED) | set(_TICKER_MEMBERSHIP_APPLIED))
    for t in names:
        spec = DECLARED_TICKER_EXCLUSIONS[t]
        entry = out.setdefault(spec["census_key"], {"reason": spec["reason"],
                                                    "declared_ratio": spec["declared_ratio"],
                                                    "tickers": {}})
        entry["tickers"][t] = {"withheld_at": sorted(_TICKERS_APPLIED.get(t, set())),
                               "membership_intervals_dropped": _TICKER_MEMBERSHIP_APPLIED.get(t, 0)}
    return out


def exclusions_applied() -> Dict[str, dict]:
    """The census block: every declaration applied in this run, keyed by its census key."""
    out: Dict[str, dict] = {}
    for ticker, rec in _BARS_APPLIED.items():
        out.setdefault(rec["census_key"], {"ticker": ticker, "before": rec["before"],
                                           "reason": rec["reason"]})["n_bars_withheld"] = rec["n_bars_withheld"]
    for ticker, rec in _MEMBERSHIP_APPLIED.items():
        entry = out.setdefault(rec["census_key"], {"ticker": ticker, "before": rec["before"],
                                                   "reason": DECLARED_EXCLUSIONS[ticker]["reason"]})
        entry["membership"] = {k: rec[k] for k in ("intervals_dropped", "intervals_clipped")}
    return out


def reset_exclusion_log() -> None:
    """Start a run's bar and resolution records (membership is applied once per process and kept)."""
    _BARS_APPLIED.clear()
    _TICKERS_APPLIED.clear()
