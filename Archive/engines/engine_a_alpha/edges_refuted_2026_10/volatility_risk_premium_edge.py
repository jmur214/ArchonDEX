"""
engines/engine_a_alpha/edges/volatility_risk_premium_edge.py
============================================================
Volatility Risk Premium (VRP) edge — T-2026-06-06-122.

First literature edge dispatched AFTER T-117 proved the existing inventory
has no factor-orthogonal alpha (all 13 dense edges factor-NEGATIVE vs FF5+Mom).
VRP is the chosen first pick because it is STRUCTURALLY non-factor: it harvests
the volatility insurance premium (implied vol systematically exceeds realized
vol), which is NOT a stock-characteristic factor spanned by FF5+Mom. So unlike
QMJ / gross-profitability (which load on RMW), VRP has a real shot at clearing
the factor-α gate every existing edge fails.

Literature
----------
- Bollerslev, Tauchen & Zhou (2009, RFS): the variance risk premium (implied −
  realized variance) is positive on average and predicts equity returns.
- Carr & Wu (2009, RFS): variance risk premium is large, negative for the
  buyer of variance (i.e. positive for the seller / harvester).
- Moreira & Muir (2017, JF) "Volatility-Managed Portfolios": scaling market
  exposure DOWN when volatility is high earns positive alpha vs FF factors —
  the timing mechanism by which a vol-premium signal can be factor-orthogonal.

Mechanism (equity-only v1; the options/variance-swap version is a follow-up)
--------------------------------------------------------------------------
The pure VRP harvest is SHORT volatility (sell insurance). We cannot trade
options/VIX futures in this equity backtest, so the defensible equity proxy is
a volatility-managed market-exposure overlay:

  - implied_vol = VIXCLS at `as_of` / 100               (forward-looking, from FRED cache)
  - realized_vol = annualized std of the equal-weight market return over
                   `rv_lookback` days, computed from `data_map` (no SPY dependency)
  - vrp_spread = implied_vol − realized_vol

  When vrp_spread > threshold the insurance premium is POSITIVE (the normal
  calm-regime state, avg ≈ +3-4 vol pts) → take long market exposure sized by
  the spread (harvest the premium by bearing the risk being insured). When the
  spread compresses or INVERTS (realized catching up to / exceeding implied =
  stress onset) → flat. This de-risks precisely when the risk-return tradeoff
  is poor — the Moreira-Muir alpha mechanism.

This is deliberately a MARKET-TIMING breadth signal (uniform across the
universe). The make-or-break orthogonality test (T-122 audit) is whether the
TIMING produces α on top of the MktRF beta it necessarily carries — or whether
it is just beta-timing that collapses to ~0 α like everything else.

Honest risk: VRP is short-vol — it "picks up pennies in front of a steamroller"
(bleeds in calm? no — it EARNS in calm; it gets hurt when vol spikes faster than
the trailing RV de-risks). The gauntlet + factor decomp is exactly the test of
whether the premium survives net of that tail risk on our substrate.

Candidate-only: registered status='candidate'. Engine F gates promotion.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..edge_base import EdgeBase

log = logging.getLogger("VolatilityRiskPremiumEdge")


class VolatilityRiskPremiumEdge(EdgeBase):
    EDGE_ID = "volatility_risk_premium_v1"
    CATEGORY = "macro"
    DESCRIPTION = (
        "Volatility risk premium harvest (equity proxy): volatility-managed "
        "long market exposure sized by the VIX − realized-vol spread; flat "
        "when the premium inverts (stress)."
    )

    DEFAULT_PARAMS = {
        # Trailing window (trading days) for the market realized-vol estimate.
        # 21d ≈ 1 month, matching the VIX 30-calendar-day horizon reasonably.
        "rv_lookback": 21,
        # Minimum VRP spread (in decimal vol, e.g. 0.0 = 0 vol pts) to take
        # exposure. 0.0 = long whenever implied > realized (the premium is
        # positive). Not tuned per backtest — the economic prior is "harvest
        # when the premium exists."
        "vrp_threshold": 0.0,
        # Spread (decimal vol) that maps to full long_score. avg VRP ≈ 0.035
        # (3.5 vol pts); 0.05 → full strength at a fat premium, partial below.
        "vrp_full_scale": 0.05,
        # Max per-name signal magnitude (the market-exposure dial).
        "long_score": 1.0,
        # Need at least this many tickers with valid returns to estimate the
        # market realized vol. Below this, abstain.
        "min_universe": 10,
        # FRED series id for implied vol (cached parquet on disk, 2000-2026).
        "vix_series": "VIXCLS",
    }

    def __init__(self):
        super().__init__()
        self.params = dict(self.DEFAULT_PARAMS)
        self._vix_series: pd.Series | None = None
        self._vix_loaded = False

    @classmethod
    def sample_params(cls):
        """Canonical defaults — this edge is not hyperparameter-tuned."""
        return dict(cls.DEFAULT_PARAMS)

    # -- external (macro) data: VIX implied vol, cache-first, PIT-correct -- #
    def _ensure_vix_loaded(self) -> pd.Series | None:
        """Lazy-load the cached VIX series (FRED VIXCLS). Mirrors the macro
        edges' pattern: cache-only read, abstain gracefully on any failure."""
        if self._vix_loaded:
            return self._vix_series
        self._vix_loaded = True
        try:
            from engines.data_manager import MacroDataManager
        except Exception as exc:  # pragma: no cover - import guard
            log.debug(f"MacroDataManager import failed ({exc}); abstaining")
            return None
        try:
            mgr = MacroDataManager()
            df = mgr.load_cached(self.params["vix_series"])
        except Exception as exc:
            log.debug(f"VIX cache load failed ({exc}); abstaining")
            return None
        if df is None or df.empty or "value" not in df.columns:
            log.debug("VIX cache empty; abstaining")
            return None
        s = df["value"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        self._vix_series = s.sort_index()
        return self._vix_series

    def _implied_vol_at(self, as_of: pd.Timestamp) -> float | None:
        """Most recent VIX at or before `as_of` (point-in-time; no lookahead),
        as a decimal annualized vol (VIX/100)."""
        s = self._ensure_vix_loaded()
        if s is None:
            return None
        try:
            ts = pd.Timestamp(as_of)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
        except Exception:
            return None
        val = s.asof(ts)
        if pd.isna(val) or val <= 0:
            return None
        return float(val) / 100.0

    # ------------------------------ signal ------------------------------- #
    def _market_realized_vol(self, data_map, lookback: int) -> float | None:
        """Annualized realized vol of the equal-weight market return over the
        trailing `lookback` days, built from `data_map` (no SPY dependency)."""
        rets = []
        for _ticker, df in data_map.items():
            if df is None or "Close" not in df.columns or len(df) < lookback + 2:
                continue
            close = df["Close"].astype(float).iloc[-(lookback + 1):]
            r = np.log(close).diff().dropna()
            if len(r) >= lookback:
                rets.append(r.iloc[-lookback:].reset_index(drop=True))
        if len(rets) < int(self.params.get("min_universe", 10)):
            return None
        mkt = pd.concat(rets, axis=1).mean(axis=1)  # equal-weight market return
        if len(mkt) < 2 or not np.isfinite(mkt.std()) or mkt.std() < 1e-12:
            return None
        return float(mkt.std() * np.sqrt(252))

    def compute_signals(self, data_map, now):
        lookback = int(self.params.get("rv_lookback", 21))
        threshold = float(self.params.get("vrp_threshold", 0.0))
        full_scale = float(self.params.get("vrp_full_scale", 0.05))
        long_score = float(self.params.get("long_score", 1.0))

        implied = self._implied_vol_at(now)
        realized = self._market_realized_vol(data_map, lookback)
        if implied is None or realized is None:
            # No VIX or universe too thin — abstain (flat across the book).
            return {ticker: 0.0 for ticker in data_map}

        vrp_spread = implied - realized
        if vrp_spread <= threshold:
            # Premium inverted / compressed — stress regime → de-risk to flat.
            return {ticker: 0.0 for ticker in data_map}

        # Size long exposure by the premium magnitude (clipped to [0, 1]).
        scale = min(max((vrp_spread - threshold) / max(full_scale, 1e-9), 0.0), 1.0)
        score = long_score * scale
        return {ticker: score for ticker in data_map}


# ---------------------------------------------------------------------------
# Auto-register on import as a CANDIDATE (NOT active). Engine F gates promotion.
# `EdgeRegistry.ensure()` write-protects status on pre-existing specs, so a
# re-import never reverts a lifecycle decision.
# ---------------------------------------------------------------------------
from engines.engine_a_alpha.edge_registry import EdgeRegistry, EdgeSpec  # noqa: E402

try:
    _reg = EdgeRegistry()
    _reg.ensure(EdgeSpec(
        edge_id=VolatilityRiskPremiumEdge.EDGE_ID,
        category=VolatilityRiskPremiumEdge.CATEGORY,
        module=__name__,
        version="1.0.0",
        params=dict(VolatilityRiskPremiumEdge.DEFAULT_PARAMS),
        status="candidate",
    ))
except Exception:
    pass
