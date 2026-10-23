"""
engines/engine_a_alpha/edges/betting_against_beta_edge.py
=========================================================
Betting-Against-Beta (BAB) edge — T-2026-06-06-123.

The DECISIVE cross-sectional alpha test. T-117 showed the existing 11 edges are
factor-losers/closet-beta; T-122 showed the equity-cross-sectional harness washes
out market-timing/overlay signals (only cross-sectional stock-picking gets tested).
BAB is the friendliest possible test of "can ANY well-constructed cross-sectional
literature edge clear factor-α t>2 in our harness?":
  - it is CROSS-SECTIONAL (ranks stocks by market-beta) → it will NOT wash out;
  - it is the best-documented FREE-data factor whose α is KNOWN to survive FF5
    (Frazzini-Pedersen 2014, JFE — FF does not span the low-beta anomaly);
  - it is maximally orthogonal to our momentum/value/quality crowd.

Mechanism (Frazzini-Pedersen 2014, "Betting Against Beta")
----------------------------------------------------------
Leverage-constrained investors bid up high-beta assets, depressing their
risk-adjusted returns; low-beta assets are underpriced. The BAB factor goes LONG
low-beta (levered to β=1) and SHORT high-beta (de-levered to β=1), earning the
risk-adjusted spread. Empirically positive α vs the FF factors.

Equity-cross-sectional implementation (mirrors xsec_momentum.py structure)
--------------------------------------------------------------------------
  - market return = equal-weight mean of the universe's daily returns (self-
    contained from the price panel; no external data — same convention the rest
    of the edge stack uses).
  - per-name market beta β_i = cov(r_i, r_mkt)/var(r_mkt) over a trailing window.
  - cross-sectional tilt = −(β_i − mean β): LONG below-average-beta names, SHORT
    above-average-beta names. Demeaned → dollar-neutral by construction.
  - Frazzini-Pedersen beta-neutralization SPIRIT: inverse-vol scale per name
    (lower-vol low-beta names get larger weight; higher-vol high-beta names
    smaller), then portfolio vol-target + clip — same risk plumbing as
    xsec_momentum. (A literal leverage-to-β=1 needs gross-exposure control the
    cross-sectional edge bus does not expose; documented simplification.)

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


class BettingAgainstBetaEdge(EdgeBase):
    EDGE_ID = "betting_against_beta_v1"
    CATEGORY = "factor"
    DESCRIPTION = (
        "Cross-sectional betting-against-beta (Frazzini-Pedersen): long low "
        "market-beta / short high-beta, demeaned (dollar-neutral), inverse-vol "
        "scaled and vol-targeted."
    )

    DEFAULT_PARAMS = {
        # Trailing window (trading days) for rolling market-beta. 252 = 1y,
        # the academic standard for beta estimation.
        "beta_lookback": 252,
        # Minimum panel history before trading.
        "min_lookback": 252,
        # Window for inverse-vol scaling.
        "vol_window": 20,
        # Annualized portfolio vol target (matches xsec_momentum house style).
        "vol_target": 0.10,
        # Need at least this many names with valid betas to rank.
        "min_universe": 10,
    }

    def __init__(self):
        super().__init__()
        self.params = dict(self.DEFAULT_PARAMS)

    @classmethod
    def sample_params(cls):
        return dict(cls.DEFAULT_PARAMS)

    def _close_panel(self, prices, as_of) -> pd.DataFrame | None:
        """Combine a {ticker: OHLCV} map (or a price DataFrame) into a Close
        panel truncated to as_of. Mirrors xsec_momentum's combine logic."""
        if isinstance(prices, dict):
            frames = []
            for ticker, df in prices.items():
                if not isinstance(df, pd.DataFrame):
                    continue
                cols = [c for c in df.columns if "close" in str(c).lower()]
                if not cols:
                    continue
                frames.append(df[cols[0]].rename(ticker))
            if not frames:
                return None
            p = pd.concat(frames, axis=1)
        else:
            p = prices.copy()
        p = p.loc[:as_of].copy()
        if p.empty:
            return None
        return p

    def compute_signals(self, prices, as_of) -> dict[str, float]:
        beta_lb = int(self.params.get("beta_lookback", 252))
        min_lb = int(self.params.get("min_lookback", 252))
        vol_window = int(self.params.get("vol_window", 20))
        vol_target = float(self.params.get("vol_target", 0.10))
        min_universe = int(self.params.get("min_universe", 10))

        p = self._close_panel(prices, as_of)
        if p is None or p.shape[0] < min_lb:
            return {} if not isinstance(prices, dict) else {t: 0.0 for t in prices}

        rets = p.pct_change().dropna(how="all")
        if rets.shape[0] < beta_lb:
            return {t: 0.0 for t in p.columns}

        window = rets.tail(beta_lb)
        mkt = window.mean(axis=1)  # equal-weight market return
        var_m = float(mkt.var())
        if not np.isfinite(var_m) or var_m <= 0:
            return {t: 0.0 for t in p.columns}

        # Per-name beta over the trailing window (names with enough overlap).
        betas: dict[str, float] = {}
        for t in window.columns:
            r = window[t]
            pair = pd.concat([r, mkt], axis=1).dropna()
            if len(pair) < max(60, beta_lb // 2):
                continue
            cov = float(pair.iloc[:, 0].cov(pair.iloc[:, 1]))
            b = cov / var_m
            if np.isfinite(b):
                betas[t] = b
        if len(betas) < min_universe:
            return {t: 0.0 for t in p.columns}

        # Betting-against-beta tilt: long below-mean-beta, short above-mean-beta.
        bser = pd.Series(betas)
        tilt = -(bser - bser.mean())  # demeaned → dollar-neutral

        # Inverse-vol scale per name (FP beta-neutralization spirit).
        asset_vol = (rets.rolling(vol_window).std().iloc[-1] * np.sqrt(252.0))
        weights: dict[str, float] = {}
        for t, w in tilt.items():
            v = float(asset_vol.get(t, np.nan))
            weights[t] = (w / v) if (np.isfinite(v) and v > 0) else (w * 0.1)

        # Re-center to dollar-neutral (determinism-safe fsum, per xsec_momentum).
        if weights:
            s = math.fsum(sorted(weights.values()))
            if abs(s) > 1e-12:
                mean_w = s / len(weights)
                for t in weights:
                    weights[t] -= mean_w

        # Portfolio vol-target + clip to [-1, 1].
        if weights:
            w = pd.Series(weights).reindex(rets.columns).fillna(0.0)
            port = (rets.tail(beta_lb) * w).sum(axis=1)
            sigma = _ann_vol(port)
            if sigma and np.isfinite(sigma) and sigma > 0:
                scale = vol_target / sigma
                for t in weights:
                    weights[t] *= float(scale)
            for t in weights:
                weights[t] = float(np.clip(weights[t], -1.0, 1.0))

        # Fill non-ranked names with 0 so the output covers the universe.
        out = {t: 0.0 for t in p.columns}
        out.update(weights)
        return out


# ---------------------------------------------------------------------------
# Auto-register on import as a CANDIDATE (NOT active). Engine F gates promotion.
# ---------------------------------------------------------------------------
from engines.engine_a_alpha.edge_registry import EdgeRegistry, EdgeSpec  # noqa: E402

try:
    _reg = EdgeRegistry()
    _reg.ensure(EdgeSpec(
        edge_id=BettingAgainstBetaEdge.EDGE_ID,
        category=BettingAgainstBetaEdge.CATEGORY,
        module=__name__,
        version="1.0.0",
        params=dict(BettingAgainstBetaEdge.DEFAULT_PARAMS),
        status="candidate",
    ))
except Exception:
    pass
