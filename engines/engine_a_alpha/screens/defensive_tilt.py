"""Defensive-tilt cross-sectional signals (T-2026-06-18-205, Phase 1).

Two composable, low-turnover, evidence-backed defensive tilts:

1. ``quality_score`` / ``quality_tilt_longs`` — a cross-sectional QUALITY
   score that REPOINTS the dormant ``quality_gross_profitability_v1`` +
   ``quality_roic_v1`` edge formulas (Novy-Marx gross profitability +
   Asness-Frazzini-Pedersen ROIC) into one continuous score = the mean of
   the two metrics' cross-sectional percentile ranks. The tilt basket is
   the top ``quality_quantile`` of that score.

2. ``high_ivol_exclusion`` — a lottery/high-vol EXCLUSION screen
   (Novy-Marx: the anomaly is the terrible HIGH-vol names, so the edge is
   *avoiding* them). Excludes tickers whose trailing realized vol is above
   a cross-sectional percentile cutoff. Honest label: this is a defensive
   UNDER-participation tilt (it sits out high-vol rally names).

DESIGN NOTE — OFF by construction:
    These are pure functions. They are NOT imported by the production
    backtest path and do NOT touch Engine-B admission/sizing (that
    application is propose-first). Wiring them in is a separate, gated
    step; until then prod canon-md5 is unchanged because this module is
    never on the live path.

PIT-correctness: quality metrics use the same publish_date-gated panel
helpers the edges use; IVOL uses only price history up to ``now``.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

from ..edges._fundamentals_helpers import get_panel, latest_value, ttm_sum

ROIC_TAX_RATE = 0.21
DEFAULT_MIN_UNIVERSE = 30
DEFAULT_IVOL_LOOKBACK = 30  # trading days


# --------------------------------------------------------------------------- #
# Quality / profitability tilt
# --------------------------------------------------------------------------- #

def _gp_assets(panel: pd.DataFrame, ticker: str, asof: pd.Timestamp) -> Optional[float]:
    """Novy-Marx gross profitability = TTM gross_profit / latest total_assets.
    Exact reuse of quality_gross_profitability_v1's formula."""
    gp = ttm_sum(panel, ticker, asof, "gross_profit")
    assets = latest_value(panel, ticker, asof, "total_assets")
    if gp is None or assets is None or assets <= 0:
        return None
    return gp / assets


def _roic(panel: pd.DataFrame, ticker: str, asof: pd.Timestamp) -> Optional[float]:
    """ROIC = NOPAT / invested_capital. Exact reuse of quality_roic_v1:
    NOPAT = TTM operating_income·(1−0.21); invested = equity + LTD (None→0);
    distressed (equity≤0) dropped."""
    ttm_oi = ttm_sum(panel, ticker, asof, "operating_income")
    equity = latest_value(panel, ticker, asof, "total_equity")
    if ttm_oi is None or equity is None or equity <= 0:
        return None
    lt_debt = latest_value(panel, ticker, asof, "long_term_debt") or 0.0
    invested = equity + lt_debt
    if invested <= 0:
        return None
    return (ttm_oi * (1.0 - ROIC_TAX_RATE)) / invested


def _pct_rank(values: Dict[str, float]) -> Dict[str, float]:
    """Cross-sectional percentile rank in [0,1] (higher value → higher rank)."""
    if not values:
        return {}
    s = pd.Series(values)
    return s.rank(pct=True).to_dict()


def quality_score(
    data_map: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    panel: Optional[pd.DataFrame] = None,
    min_universe: int = DEFAULT_MIN_UNIVERSE,
) -> Dict[str, float]:
    """Composite cross-sectional quality score in [0,1] per ticker.

    score = mean( pctrank(gp/assets), pctrank(roic) ), over names that have
    BOTH metrics present as-of ``now``. Returns {} (abstain) if fewer than
    ``min_universe`` names are scorable — the abstention floor the edges use.
    Higher = higher quality.
    """
    panel = panel if panel is not None else get_panel()
    if panel is None:
        return {}
    asof = pd.Timestamp(now)
    gp_raw: Dict[str, float] = {}
    roic_raw: Dict[str, float] = {}
    for ticker in data_map:
        gp = _gp_assets(panel, ticker, asof)
        rc = _roic(panel, ticker, asof)
        if gp is not None and rc is not None:   # both required (abstain else)
            gp_raw[ticker] = gp
            roic_raw[ticker] = rc
    if len(gp_raw) < min_universe:
        return {}
    gp_rank = _pct_rank(gp_raw)
    roic_rank = _pct_rank(roic_raw)
    return {t: 0.5 * (gp_rank[t] + roic_rank[t]) for t in gp_raw}


def quality_tilt_longs(
    data_map: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    quality_quantile: float = 0.20,
    long_score: float = 1.0,
    panel: Optional[pd.DataFrame] = None,
    min_universe: int = DEFAULT_MIN_UNIVERSE,
) -> Dict[str, float]:
    """Top-``quality_quantile`` names by composite quality score → long_score.
    The composable defensive QUALITY-TILT signal (abstains to {} below the
    universe floor)."""
    scores = quality_score(data_map, now, panel=panel, min_universe=min_universe)
    if not scores:
        return {}
    cutoff = pd.Series(scores).quantile(1.0 - quality_quantile)
    return {t: long_score for t, s in scores.items() if s >= cutoff}


# --------------------------------------------------------------------------- #
# High-IVOL / lottery exclusion
# --------------------------------------------------------------------------- #

def realized_vol(
    data_map: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    lookback: int = DEFAULT_IVOL_LOOKBACK,
) -> Dict[str, float]:
    """Trailing-``lookback`` annualized realized vol per ticker as-of ``now``
    (idiosyncratic-vol PROXY = total realized vol; not market-residualized
    this round — labeled honestly). Uses only Close history ≤ now."""
    asof = pd.Timestamp(now)
    out: Dict[str, float] = {}
    for ticker, df in data_map.items():
        if df is None or "Close" not in df.columns:
            continue
        idx = pd.to_datetime(df.index)
        closes = df.loc[idx <= asof, "Close"].astype(float)
        if len(closes) < lookback + 1:
            continue
        rets = np.log(closes / closes.shift(1)).dropna().tail(lookback)
        if len(rets) < lookback:
            continue
        sd = float(rets.std(ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            continue
        out[ticker] = sd * np.sqrt(252.0)
    return out


def high_ivol_exclusion(
    data_map: Dict[str, pd.DataFrame],
    now: pd.Timestamp,
    *,
    ivol_cutoff: float = 0.75,
    lookback: int = DEFAULT_IVOL_LOOKBACK,
    min_universe: int = DEFAULT_MIN_UNIVERSE,
) -> Set[str]:
    """Return the set of EXCLUDED tickers — those whose trailing realized
    vol is ABOVE the ``ivol_cutoff`` cross-sectional percentile. The
    defensive lottery-exclusion screen (under-participation tilt). Returns
    an empty set (exclude nothing) if fewer than ``min_universe`` names are
    measurable — abstain rather than exclude on thin data."""
    vols = realized_vol(data_map, now, lookback=lookback)
    if len(vols) < min_universe:
        return set()
    cut = pd.Series(vols).quantile(ivol_cutoff)
    return {t for t, v in vols.items() if v > cut}
