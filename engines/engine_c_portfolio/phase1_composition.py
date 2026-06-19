"""
engines/engine_c_portfolio/phase1_composition.py
================================================
T-2026-06-18-211 — Phase-1 COMPOSITION post-processor (Engine C scope only).

THE CONVERGENCE: compose the already-merged Phase-1 levers onto the book's
target weights. Default-OFF; OFF ⇒ this module is never imported and the
backtest canon is bitwise-identical (same OFF-default contract as
dynamic_optimization / position_buffering).

Two shaping steps, applied to the target weights AFTER allocate()/dyn-opt/
buffering:

  1. DEFENSIVE TILT (A/T-205 screens, as a CONSTRUCTION tilt — NOT an Engine-B
     admission gate): zero the high-IVOL/lottery exclusions; haircut non-quality
     LONG weights toward the quality set, then renormalize the longs so the tilt
     is a RELATIVE shift (re-allocate toward quality) and NOT a covert de-gross.

  2. TREND OVERLAY (E/T-204): scale the whole book's gross by the EW SPY/AGG/GLD
     5-month long/flat exposure scalar ∈ [0,1] (cash when flat). This is the
     drawdown-cutting lever ("the trend overlay alone already ~halves the MDD").
     No-lookahead: today holds YESTERDAY's close-state (the signal is shift(1)'d).

Vol-target (Engine B) is EXCLUDED here — it is propose-first (B/T-212). Position
buffering (T-148, lower-turnover) is a SEPARATE Engine-C flag toggled in the run
config, composed upstream of this post-processor.

Fails OPEN (returns the unmodified weights) on any insufficient input — the
screens abstain to empty defaults and the overlay defaults to full exposure, so
a thin-data bar is never silently zeroed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# T-211 FIX 1 — source the trend-overlay assets from the SAME on-disk substrate
# E/T-204 validated the overlay on (STOOQ raw ETF files), NOT data/processed
# (which bypasses the book's normalization AND whose GLD only starts 2020-04).
# The overlay itself is the VALIDATED core.trend_overlay.TrendOverlay component
# (consumed below) — no inline reimplementation.
_STOOQ = ROOT / "data" / "raw" / "stooq" / "daily" / "us"
_STOOQ_PATHS = {
    "SPY": _STOOQ / "nyse etfs" / "2" / "spy.us.txt",
    "AGG": _STOOQ / "nyse etfs" / "1" / "agg.us.txt",
    "GLD": _STOOQ / "nyse etfs" / "1" / "gld.us.txt",
}


def now_from_price_data(price_data: Dict[str, pd.DataFrame]) -> Optional[pd.Timestamp]:
    """The bar's as-of timestamp = the latest last-index across the sliced frames."""
    last = None
    for df in price_data.values():
        if df is not None and len(df):
            ts = df.index[-1]
            last = ts if last is None else max(last, ts)
    return pd.Timestamp(last) if last is not None else None


# T-211 FIX 2 — MONTHLY screen cache (BAR B, a declared strategy change, not a
# transparent optimization: the screens recompute per-bar and change daily, so
# computing them per-bar vs monthly is NOT bit-identical — see the re-pre-reg).
# Causal-by-construction: the cache key is the TRAILING last-completed-month
# (NEVER first-of-month-forward = intra-month lookahead, NEVER end-of-month-
# retroactive = future leak); the screen is computed as-of that month-end, on
# data that is by construction <= now. Universe-scoped so a different (PIT)
# universe never reuses another's screens.
_SCREEN_CACHE: Dict[tuple, tuple] = {}


def _trailing_month_asof(now: pd.Timestamp) -> tuple:
    """(month_key, asof) for the LAST COMPLETED month strictly before `now`'s
    month. asof = that month's last calendar day (<= now → causal)."""
    prev = pd.Timestamp(now).to_period("M") - 1
    return str(prev), prev.end_time


def _cached_defensive_screens(price_data: Dict[str, pd.DataFrame], now: pd.Timestamp):
    """(excluded:set, quality:set) computed once per trailing-month per universe,
    as-of the trailing month-end. Slow-moving screens (quarterly fundamentals,
    30d vol) → monthly staleness is a minor, causal perturbation."""
    from engines.engine_a_alpha.screens.defensive_tilt import (
        high_ivol_exclusion, quality_tilt_longs,
    )
    month_key, asof = _trailing_month_asof(now)
    uhash = hash(tuple(sorted(price_data.keys())))
    key = (month_key, uhash)
    if key not in _SCREEN_CACHE:
        excluded = set(high_ivol_exclusion(price_data, asof) or set())
        quality = set((quality_tilt_longs(price_data, asof) or {}).keys())
        _SCREEN_CACHE[key] = (excluded, quality)
    return _SCREEN_CACHE[key]


def _fail_closed_if_measured(site: str, reason: str) -> None:
    """In a MEASURED run (cloud/anchor/hermetic-strict) a missing load-bearing
    input for the ACTIVE composition must fail LOUD (census-FAIL via HALT), NOT
    silently pass through at full exposure. Outside measured mode → no-op (the
    caller fails open, fine for the thin OFF/paper bar)."""
    try:
        from core.measured import halt_or_degrade
        halt_or_degrade(site=site, load_bearing=True, active=True, reason=reason)
    except Exception as e:
        if type(e).__name__ == "MeasurementHalt":
            raise


def apply_phase1_composition(
    weights: Dict[str, float],
    price_data: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    quality_haircut: float = 0.5,
    trend_lookback_days: int = 105,
    trend_assets: Tuple[str, ...] = ("SPY", "AGG", "GLD"),
) -> Dict[str, float]:
    """Shape the target weights with the defensive tilt + trend-overlay scalar.
    Fail-closed in measured mode; fail-open (return unmodified) otherwise."""
    if not weights:
        return weights
    out: Dict[str, float] = dict(weights)

    # --- 1. defensive tilt (monthly-cached, causal) ---
    try:
        excluded, quality = _cached_defensive_screens(price_data, now)
        if excluded:
            out = {t: (0.0 if t in excluded else w) for t, w in out.items()}
        if quality and 0.0 <= quality_haircut < 1.0:
            pre_long = sum(w for w in out.values() if w > 0)
            tilted = {t: (w * quality_haircut if (w > 0 and t not in quality) else w)
                      for t, w in out.items()}
            post_long = sum(w for w in tilted.values() if w > 0)
            if post_long > 1e-12 and pre_long > 1e-12:
                scale = pre_long / post_long   # renormalize longs → relative shift
                out = {t: (w * scale if w > 0 else w) for t, w in tilted.items()}
            else:
                out = tilted
    except Exception as e:
        _fail_closed_if_measured("phase1_composition.defensive_tilt",
                                 f"screen failed: {type(e).__name__}: {e}")

    # --- 2. trend overlay exposure scalar ---
    exp = None
    try:
        exp = _trend_exposure(now, int(trend_lookback_days), tuple(trend_assets))
    except Exception as e:
        _fail_closed_if_measured("phase1_composition.trend_overlay",
                                 f"overlay failed: {type(e).__name__}: {e}")
    if exp is not None and np.isfinite(exp):
        out = {t: w * float(exp) for t, w in out.items()}
    else:
        # a missing overlay would silently leave the book at FULL exposure — in
        # measured mode that is the silent-fail-open class → HALT.
        _fail_closed_if_measured("phase1_composition.trend_overlay",
                                 "overlay exposure unavailable (would leave full exposure)")

    return out


def _load_stooq_close(path: Path) -> pd.Series:
    """STOOQ raw close series — the SAME loader E/T-204 validated the overlay on."""
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df.set_index("date").sort_index()["close"].astype(float)


@lru_cache(maxsize=8)
def _overlay_series(lookback_days: int, assets: Tuple[str, ...]) -> Optional[pd.Series]:
    """EW long/flat exposure ∈ [0,1] across ``assets``, CONSUMING the validated
    `core.trend_overlay.TrendOverlay` (no inline reimplementation) on E/T-204's
    STOOQ substrate, shift(1)'d (no-lookahead — today holds yesterday's
    close-state, matching `trend_overlay.overlay_returns`). Cached."""
    from core.trend_overlay import TrendOverlay
    sigs = []
    for a in assets:
        p = _STOOQ_PATHS.get(a)
        if p is None or not p.exists():
            continue
        close = _load_stooq_close(p)
        # the VALIDATED component's as-of-close long/flat signal, lagged a day
        sig = TrendOverlay(int(lookback_days), enabled=True).exposure(close).shift(1)
        sigs.append(sig)
    if not sigs:
        return None
    return pd.concat(sigs, axis=1).mean(axis=1)


def _trend_exposure(now: pd.Timestamp, lookback_days: int, assets: Tuple[str, ...]) -> Optional[float]:
    ew = _overlay_series(lookback_days, assets)
    if ew is None or now is None:
        return None
    sub = ew.loc[:pd.Timestamp(now)].dropna()
    return float(sub.iloc[-1]) if len(sub) else 1.0   # default full exposure
