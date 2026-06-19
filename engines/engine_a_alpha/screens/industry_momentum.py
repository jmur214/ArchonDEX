"""Industry/sector momentum, sector-neutral (T-2026-06-18-213).

Moskowitz-Grinblatt (1999) industry momentum on the 9 original GICS SPDRs
(XLK/XLF/XLE/XLV/XLI/XLY/XLP/XLU/XLB). Ranks sectors by trailing 12-1
momentum and rotates dollar-neutral toward the strong / away from the weak
sectors — NOT individual-stock momentum (which is closet beta).

COMPOSABLE + OFF by construction: ``sector_momentum_weights`` is a pure
function returning a ``{sector_etf: weight}`` dict. It is NOT imported by
the production backtest path and does NOT touch Engine-B/C live
composition (that is a later Engine-C step). Default-OFF ⇒ prod canon
unchanged.

Sector-NEUTRAL: dollar-neutral long-top-K / short-bottom-K, equal-weight
within each leg, so it is not a persistent long-tech/short-utility tilt.
The validation harness reports realized per-sector net exposure to confirm.

PIT-correct: weights at rebalance ``t`` use only prices through ``t``.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# The 9 original GICS SPDRs with clean 2005+ history. XLRE (2015) / XLC
# (2018) excluded — staggered inception would bias the cross-sectional rank.
GICS9: List[str] = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]

# Pre-registered structure (fixed a-priori; see audit T-213).
LOOKBACK = 252   # 12 months
SKIP = 21        # skip most-recent month (12-1 momentum)
TOP_K = 3        # long top-3 / short bottom-3 of 9


def momentum_12_1(close: pd.Series, asof: pd.Timestamp,
                  *, lookback: int = LOOKBACK, skip: int = SKIP) -> Optional[float]:
    """Trailing 12-1 total return of a sector ETF as-of ``asof``:
    P(t−skip) / P(t−lookback) − 1. None if insufficient history."""
    s = close.loc[close.index <= asof]
    if len(s) < lookback + 1:
        return None
    p_recent = s.iloc[-(skip + 1)]
    p_old = s.iloc[-(lookback + 1)]
    if p_old <= 0 or not np.isfinite(p_old) or not np.isfinite(p_recent):
        return None
    return float(p_recent / p_old - 1.0)


def sector_momentum_weights(
    closes: Dict[str, pd.Series],
    asof: pd.Timestamp,
    *,
    universe: Optional[List[str]] = None,
    lookback: int = LOOKBACK,
    skip: int = SKIP,
    top_k: int = TOP_K,
) -> Dict[str, float]:
    """Dollar-neutral long-top-K / short-bottom-K sector-momentum weights.

    Returns ``{sector: weight}`` summing to ~0 (long +1/K each, short −1/K
    each, others 0). Abstains to {} if fewer than ``2*top_k`` sectors have
    a computable 12-1 momentum as-of ``asof`` (can't form both legs).
    """
    universe = universe or GICS9
    mom: Dict[str, float] = {}
    for sec in universe:
        c = closes.get(sec)
        if c is None:
            continue
        m = momentum_12_1(c, pd.Timestamp(asof), lookback=lookback, skip=skip)
        if m is not None:
            mom[sec] = m
    if len(mom) < 2 * top_k:
        return {}
    ranked = sorted(mom, key=lambda s: mom[s], reverse=True)
    longs, shorts = ranked[:top_k], ranked[-top_k:]
    w = {s: 0.0 for s in mom}
    for s in longs:
        w[s] += 1.0 / top_k
    for s in shorts:
        w[s] -= 1.0 / top_k
    return w
