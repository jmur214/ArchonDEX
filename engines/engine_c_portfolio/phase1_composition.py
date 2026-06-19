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
PROCESSED = ROOT / "data" / "processed"


def now_from_price_data(price_data: Dict[str, pd.DataFrame]) -> Optional[pd.Timestamp]:
    """The bar's as-of timestamp = the latest last-index across the sliced frames."""
    last = None
    for df in price_data.values():
        if df is not None and len(df):
            ts = df.index[-1]
            last = ts if last is None else max(last, ts)
    return pd.Timestamp(last) if last is not None else None


def apply_phase1_composition(
    weights: Dict[str, float],
    price_data: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    quality_haircut: float = 0.5,
    trend_lookback_days: int = 105,
    trend_assets: Tuple[str, ...] = ("SPY", "AGG", "GLD"),
) -> Dict[str, float]:
    """Shape the target weights with the defensive tilt + trend-overlay scalar."""
    if not weights:
        return weights
    out: Dict[str, float] = dict(weights)

    # --- 1. defensive tilt (best-effort; fails open) ---
    try:
        from engines.engine_a_alpha.screens.defensive_tilt import (
            high_ivol_exclusion, quality_tilt_longs,
        )
        excluded = high_ivol_exclusion(price_data, now) or set()
        if excluded:
            out = {t: (0.0 if t in excluded else w) for t, w in out.items()}
        quality = set((quality_tilt_longs(price_data, now) or {}).keys())
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
    except Exception:
        pass

    # --- 2. trend overlay exposure scalar (best-effort; fails open to 1.0) ---
    try:
        exp = _trend_exposure(now, int(trend_lookback_days), tuple(trend_assets))
        if exp is not None and np.isfinite(exp):
            out = {t: w * float(exp) for t, w in out.items()}
    except Exception:
        pass

    return out


@lru_cache(maxsize=8)
def _overlay_series(lookback_days: int, assets: Tuple[str, ...]) -> Optional[pd.Series]:
    """EW long/flat exposure across ``assets``: per-asset 1{close > SMA(lookback)},
    averaged, shift(1)'d (no-lookahead). Cached per (lookback, assets)."""
    sigs = []
    for a in assets:
        p = PROCESSED / f"{a}_1d.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        df.columns = [c.strip("<>").strip().lower() for c in df.columns]
        dcol = next((c for c in df.columns if c in ("date", "timestamp", "index")), None)
        ccol = next((c for c in df.columns if c in ("close", "adj close", "adj_close")), None)
        if not dcol or not ccol:
            continue
        s = pd.Series(pd.to_numeric(df[ccol], errors="coerce").values,
                      index=pd.to_datetime(df[dcol], errors="coerce")).dropna().sort_index()
        sma = s.rolling(lookback_days).mean()
        sig = (s > sma).astype(float)
        sig[sma.isna()] = np.nan
        sigs.append(sig.shift(1))   # today holds yesterday's close-state
    if not sigs:
        return None
    return pd.concat(sigs, axis=1).mean(axis=1)   # EW exposure ∈ [0,1]


def _trend_exposure(now: pd.Timestamp, lookback_days: int, assets: Tuple[str, ...]) -> Optional[float]:
    ew = _overlay_series(lookback_days, assets)
    if ew is None or now is None:
        return None
    sub = ew.loc[:pd.Timestamp(now)].dropna()
    return float(sub.iloc[-1]) if len(sub) else 1.0   # default full exposure
