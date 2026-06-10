"""
engines/engine_a_alpha/edges/overnight_intraday_edge.py
=======================================================
Overnight/intraday return-composition edge (Lou-Polk-Skouras) — T-2026-06-10-135.

First frontier edge off the T-132 Alpha-Frontier Map (#1: free-now, XS-native,
low FF5-span risk). External research independently ranked the same item #2 of
its intraday-as-features list.

Canonical construction implemented (documented per brief)
----------------------------------------------------------
Lou, Polk & Skouras, "A tug of war: Overnight momentum transmission" (JFE 2019),
overnight-return PERSISTENCE portfolio: sort stocks on trailing one-month
average OVERNIGHT return (r_on,t = Open_t / Close_{t-1} − 1); long the high
past-overnight names, short the low ones. LPS document strong cross-sectional
persistence of the overnight component ("the tug of war").

House-style deviations from the paper, stated plainly:
  - terciles instead of deciles (our 250-650-name universe makes deciles thin);
  - inverse-vol leg weights + dollar-neutral re-centering + portfolio
    vol-target (the xsec_momentum/BAB house risk convention);
  - daily close-to-close fills realize the TOTAL return — a daily-bar system
    cannot harvest a purely-overnight return. Whether the persistent overnight
    structure survives in TOTAL returns is exactly the gauntlet question
    (T-135 audit); the companion analysis decomposes the strategy P&L into
    overnight/intraday components to show where it accrues.

Candidate-only: status='candidate'. Engine F gates promotion.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ..edge_base import EdgeBase


def _ann_vol(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    return float(r.std() * np.sqrt(252.0))


class OvernightIntradayEdge(EdgeBase):
    EDGE_ID = "overnight_intraday_v1"
    CATEGORY = "composition"
    DESCRIPTION = (
        "Cross-sectional overnight-return persistence (Lou-Polk-Skouras): long "
        "high trailing-21d-mean overnight-return names, short low; inverse-vol, "
        "dollar-neutral, vol-targeted."
    )

    DEFAULT_PARAMS = {
        # Trailing window for mean overnight return (LPS use one month).
        "on_lookback": 21,
        # Minimum panel history before trading.
        "min_lookback": 42,
        "vol_window": 20,
        "vol_target": 0.10,
        "min_universe": 10,
        "tercile": 1.0 / 3.0,
    }

    def __init__(self):
        super().__init__()
        self.params = dict(self.DEFAULT_PARAMS)

    @classmethod
    def sample_params(cls):
        return dict(cls.DEFAULT_PARAMS)

    def compute_signals(self, prices, as_of) -> dict[str, float]:
        lookback = int(self.params.get("on_lookback", 21))
        min_lb = int(self.params.get("min_lookback", 42))
        vol_window = int(self.params.get("vol_window", 20))
        vol_target = float(self.params.get("vol_target", 0.10))
        min_universe = int(self.params.get("min_universe", 10))
        tercile = float(self.params.get("tercile", 1.0 / 3.0))

        if not isinstance(prices, dict):
            return {}

        on_mean: dict[str, float] = {}
        rets_cols: dict[str, pd.Series] = {}
        for ticker, df in prices.items():
            if not isinstance(df, pd.DataFrame):
                continue
            if not {"Open", "Close"} <= set(df.columns) or len(df) < min_lb:
                continue
            sub = df.loc[:as_of].tail(lookback + 1)
            if len(sub) < lookback + 1:
                continue
            o = sub["Open"].astype(float)
            c = sub["Close"].astype(float)
            r_on = (o / c.shift(1) - 1.0).dropna()
            if len(r_on) < lookback:
                continue
            m = float(r_on.tail(lookback).mean())
            if np.isfinite(m):
                on_mean[ticker] = m
                rets_cols[ticker] = c.pct_change()

        if len(on_mean) < min_universe:
            return {t: 0.0 for t in prices}

        ranks = pd.Series(on_mean).rank(pct=True)
        high = ranks.index[ranks >= 1 - tercile]   # long: persistent-overnight
        low = ranks.index[ranks <= tercile]        # short: weak-overnight
        rets = pd.DataFrame(rets_cols)
        asset_vol = rets.rolling(vol_window).std().iloc[-1] * np.sqrt(252.0)

        weights: dict[str, float] = {}
        for t in high:
            weights[t] = 1.0
        for t in low:
            weights[t] = weights.get(t, 0.0) - 1.0
        for t in list(weights):
            v = float(asset_vol.get(t, np.nan))
            weights[t] = (weights[t] / v) if (np.isfinite(v) and v > 0) else (weights[t] * 0.1)

        # dollar-neutral re-centering (determinism-safe fsum, house pattern)
        s = math.fsum(sorted(weights.values()))
        if abs(s) > 1e-12 and weights:
            mean_w = s / len(weights)
            for t in weights:
                weights[t] -= mean_w

        if weights:
            w = pd.Series(weights).reindex(rets.columns).fillna(0.0)
            port = (rets * w).sum(axis=1)
            sigma = _ann_vol(port)
            if sigma and np.isfinite(sigma) and sigma > 0:
                scale = vol_target / sigma
                for t in weights:
                    weights[t] *= float(scale)
            for t in weights:
                weights[t] = float(np.clip(weights[t], -1.0, 1.0))

        out = {t: 0.0 for t in prices}
        out.update(weights)
        return out


# ---------------------------------------------------------------------------
# Auto-register on import as a CANDIDATE (NOT active). Engine F gates promotion.
# ---------------------------------------------------------------------------
from engines.engine_a_alpha.edge_registry import EdgeRegistry, EdgeSpec  # noqa: E402

try:
    _reg = EdgeRegistry()
    _reg.ensure(EdgeSpec(
        edge_id=OvernightIntradayEdge.EDGE_ID,
        category=OvernightIntradayEdge.CATEGORY,
        module=__name__,
        version="1.0.0",
        params=dict(OvernightIntradayEdge.DEFAULT_PARAMS),
        status="candidate",
    ))
except Exception:
    pass
