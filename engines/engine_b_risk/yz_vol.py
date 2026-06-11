"""
engines/engine_b_risk/yz_vol.py
===============================
T-2026-06-11-153 — Yang-Zhang (2000) range-based volatility estimator for
the Engine-B vol-target path.

WHY (D's T-150 horse-race, `docs/Audit/intraday_features_t150_2026_06_11.md`):
Yang-Zhang beats the production-spec EWMA(0.94) at next-day vol forecasting
under the pre-registered bar (SPA p=0.013-0.024, ci_low>0 on both targets,
60-97% of names), AND it is structurally immune to the EWMA's
collapse-to-near-zero failure mode on quiet stretches: daily high-low
ranges are never all-zero, so a range-based σ cannot decay to ~0 the way
a close-to-close r² recursion does (T-153 assessment: median YZ/EWMA
divergence on collapsed bars = 6,533x).

PORT, NOT REWRITE: the YZ math below (r_on/r_id decomposition, the
T-135 corrupt-opens snap-back repair, var_on + k*var_oc + (1-k)*RS with
k = 0.34 / (1.34 + (W+1)/(W-1)), x252 annualization) is ported verbatim
from D's `scripts/build_ohlc_features_t150.py::_features_one` — the
implementation whose outputs passed the T-150 pre-registered screens.
The ONLY changes are packaging: operate on one OHLC frame and return the
latest value; aggregate per-name values into a portfolio-level proxy.

CORRUPT-OPENS FILTER (MANDATORY): YZ consumes opens. D's T-135 found 83
snap-back prints (|r_on|>25% AND |r_id|>25%, opposite signs) where the
open is untrusted -> repaired to prev close BEFORE any feature math.
The same repair runs here on every call.

PORTFOLIO AGGREGATION SEMANTICS (stated honestly): the portfolio-level
value is the GROSS-WEIGHTED AVERAGE of per-name YZ vols. That ignores
diversification (correlations < 1), so it is an UPPER BOUND on true
portfolio vol -> the vol-targeter divides by a larger sigma -> requests
LESS leverage. Conservative-by-construction, which is the correct bias
for a defect whose failure mode is over-levering. The A/B (pre-registered,
not run here) measures whether that bias costs Sharpe.

Causal: uses only rows of each OHLC frame at-or-before the call (the
df slices Engine B receives are strictly trailing). No look-ahead.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def yang_zhang_vol(ohlc: pd.DataFrame, window: int = 21) -> Optional[float]:
    """Latest annualized Yang-Zhang vol from a trailing OHLC frame.

    Returns None when the frame lacks OHLC columns, has fewer than
    ``window + 1`` rows, or the math yields a non-finite/non-positive
    value — callers treat None as "estimator unavailable" (no-op 1.0
    scale upstream), never as zero vol.
    """
    if ohlc is None or not {"Open", "High", "Low", "Close"} <= set(ohlc.columns):
        return None
    if len(ohlc) < window + 1:
        return None
    o = ohlc["Open"].astype(float)
    h = ohlc["High"].astype(float)
    l = ohlc["Low"].astype(float)
    c = ohlc["Close"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_on = np.log(o / c.shift(1))
        r_id = np.log(c / o)
    # T-135 corrupt-opens repair (mandatory; ported verbatim from T-150).
    snap = (r_on.abs() > 0.25) & (r_id.abs() > 0.25) & (np.sign(r_on) != np.sign(r_id))
    o = o.where(~snap, c.shift(1))
    with np.errstate(divide="ignore", invalid="ignore"):
        r_on = np.log(o / c.shift(1))
        log_co = np.log(c / o)
        log_ho = np.log(h / o)
        log_lo = np.log(l / o)

    # Yang-Zhang: sigma^2 = var(on) + k*var(oc) + (1-k)*RS ; k per YZ(2000)
    var_on = r_on.rolling(window).var()
    var_oc = log_co.rolling(window).var()
    rs = (log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)).rolling(window).mean()
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    yz_var = var_on + k * var_oc + (1 - k) * rs

    last = yz_var.iloc[-1]
    if not np.isfinite(last) or last < 0:
        return None
    sigma = float(np.sqrt(last * TRADING_DAYS_PER_YEAR))
    if not np.isfinite(sigma) or sigma <= 0.0:
        return None
    return sigma


def portfolio_yang_zhang_vol(
    data_map: Optional[Dict[str, pd.DataFrame]],
    positions: Optional[Dict[str, Any]],
    window: int = 21,
) -> Optional[float]:
    """Gross-weighted average of per-name YZ vols over open positions.

    Upper bound on true portfolio vol (ignores correlations — see module
    docstring). Returns None (estimator unavailable) when:
      * data_map or positions is None/empty (e.g. live path that never
        cached a data_map, or an all-cash book),
      * no open position has a usable OHLC frame.
    Names lacking OHLC are skipped; weights renormalize over the usable
    subset. Iteration is sorted for FP determinism (T-057c-det lesson).
    """
    if not data_map or not positions:
        return None
    weights: Dict[str, float] = {}
    for t in sorted(positions.keys()):
        pos = positions[t]
        qty = float(getattr(pos, "qty", 0.0) or 0.0)
        px = getattr(pos, "last_price", None)
        if qty == 0.0 or px is None or not np.isfinite(float(px)):
            continue
        weights[t] = abs(qty * float(px))
    if not weights:
        return None
    contribs = []
    total = 0.0
    for t in sorted(weights.keys()):
        sigma = yang_zhang_vol(data_map.get(t), window=window)
        if sigma is None:
            continue
        contribs.append(weights[t] * sigma)
        total += weights[t]
    if not contribs or total <= 0.0:
        return None
    import math
    return float(math.fsum(contribs) / total)
