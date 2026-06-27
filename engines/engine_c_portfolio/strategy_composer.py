"""Strategy-level risk-parity composition (T-2026-06-26-248).

Allocates risk budget ACROSS SLEEVE return series {base, trend, carry, ...} —
NOT ticker-level. Reuses the existing `HRPOptimizer` (Ledoit-Wolf shrinkage,
single-linkage HRP). The #2 free avenue: a CONSTRUCTION multiplier on the
existing sleeves, not a new alpha source.

Honest framing (pre-registered, T-248): better risk-budgeting across sleeves can
only TIDY the frontier — it cannot manufacture alpha that isn't in the sleeves.
If the sleeves are H0 / downside-only, the best this does is improve Sortino at
equal-or-lower MaxDD. Its real value is as the multiplier on CARRY once that
sleeve lands (Wave 2).

Default-OFF: when ``risk_parity_enabled`` is False the composer returns naive
equal-weight, so any consumer's existing (naive) composition is byte-identical.
This module is NOT wired into the per-ticker book/backtest path, so the equity
canon is unaffected (proven: 2022 trades_canon_md5 unchanged).

Factor-neutralization (netting cross-sleeve factor exposure) is an Engine-B RISK
decision — ``FactorRiskModel`` lives in ``engine_b_risk/factor_analysis.py``. The
toggle exists here for the composition API, but enabling it without the B
integration HALTS rather than silently making a risk call
(``[NN-FAIL-CLOSED]`` / ``[NN-ENGINE-BOUNDARIES]``; propose-first).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .optimizers.hrp import HRPOptimizer, HRPConfig


@dataclass
class StrategyCompositionConfig:
    """Strategy-level (sleeve) composition settings."""
    risk_parity_enabled: bool = False   # default-OFF → naive equal-weight (canon-safe)
    cov_lookback: int = 252             # sleeve cov history (sleeves are lower-freq than tickers)
    min_history: int = 60               # below this → equal-weight fallback (per HRPOptimizer)
    factor_neutralize: bool = False     # Engine-B-gated (propose-first); FAIL-CLOSED if set ON


class StrategyRiskParityComposer:
    """Risk-budget allocation across sleeve return series.

    ``risk_budget_weights`` returns long-only weights summing to 1.0 over the
    sleeves with usable history: equal-weight when OFF (the naive baseline), or
    HRP over the sleeve covariance when ON.
    """

    def __init__(self, cfg: Optional[StrategyCompositionConfig] = None):
        self.cfg = cfg or StrategyCompositionConfig()

    def risk_budget_weights(self, sleeve_returns: pd.DataFrame) -> pd.Series:
        """Compute sleeve weights from a DataFrame of sleeve return series
        (one column per sleeve). Sleeves with no usable history are dropped."""
        cols = [c for c in sleeve_returns.columns if sleeve_returns[c].notna().any()]
        if not cols:
            return pd.Series(dtype=float)

        if self.cfg.factor_neutralize:
            # Netting cross-sleeve factor exposure is a RISK decision and
            # FactorRiskModel is an Engine-B component — do NOT make it here.
            # Fail closed (never silently no-op) so an ON toggle can't quietly
            # ship an un-neutralized book that reads as neutralized.
            raise NotImplementedError(
                "factor_neutralize requires Engine-B FactorRiskModel integration "
                "(engine_b_risk/factor_analysis.py) — propose-first, B-gated. "
                "It is intentionally NOT wired in the engine_c composer; do not "
                "enable without Engine-B review.")

        if not self.cfg.risk_parity_enabled or len(cols) == 1:
            # naive equal-weight — the default/baseline (canon-safe)
            n = len(cols)
            return pd.Series([1.0 / n] * n, index=cols)

        # ON: hierarchical risk parity over the sleeve covariance (reuse the
        # existing ticker-level optimizer — it is asset-agnostic).
        hrp = HRPOptimizer(HRPConfig(cov_lookback=self.cfg.cov_lookback,
                                     min_history=self.cfg.min_history))
        return hrp.optimize(sleeve_returns[cols])

    def compose_returns(self, sleeve_returns: pd.DataFrame,
                        weights: Optional[pd.Series] = None) -> pd.Series:
        """Combine sleeve return series into a single composed return series
        using static risk-budget weights (rebalanced implicitly to the weights
        each bar). If ``weights`` is None they are computed from the same
        sleeve_returns. Bars missing a sleeve renormalize over present sleeves."""
        if weights is None:
            weights = self.risk_budget_weights(sleeve_returns)
        if weights.empty:
            return pd.Series(dtype=float)
        sub = sleeve_returns[list(weights.index)]
        # renormalize the weight vector per-bar over the sleeves that are present
        mask = sub.notna()
        w = pd.DataFrame([weights.values] * len(sub), index=sub.index, columns=sub.columns)
        w = w.where(mask, 0.0)
        row_sum = w.sum(axis=1)
        w = w.div(row_sum.where(row_sum > 0, 1.0), axis=0)
        return (w * sub.fillna(0.0)).sum(axis=1)


@dataclass
class BarbellConfig:
    """Barbell composition settings (T-2026-06-26-251)."""
    enabled: bool = False              # default-OFF → callers keep their existing composition (canon-safe)
    satellite_weight: float = 0.15     # convex satellite (trend overlay) weight — PRE-REGISTERED midpoint of [0.10, 0.20]
    vol_lookback: int = 60             # rolling window for the safe-core inverse-vol weights
    min_vol_periods: int = 30          # min history before inverse-vol weights are defined
    equity_vol_target: bool = False    # Engine-B conditional vol-target on the EQUITY sleeve (T-252); FAIL-CLOSED if set


class BarbellComposer(StrategyRiskParityComposer):
    """Barbell composition: a near-zero-cost SAFE CORE (inverse-vol over the core
    assets, e.g. SPY/AGG/GLD) + a small CONVEX SATELLITE (the trend overlay, 10-20%).

    A structural SHAPE bet, not an alpha bet (fresh-eyes brief #1, ~35-45% prior):
    it buys convexity per unit of carry and exploits the Roth's two real edges
    (zero tax-drag, free liquid-ETF turnover). The core uses PLAIN inverse-vol —
    NOT HRP — per the brief: with 3-4 sleeves HRP buys nothing (confirms T-248).

    Default-OFF and NOT wired into the per-ticker book path → equity canon
    untouched. Conditional vol-targeting on the equity sleeve is an Engine-B risk
    decision (T-252); the toggle is FAIL-CLOSED here (propose-first, B-gated).
    """

    def __init__(self, cfg: Optional[BarbellConfig] = None):
        self.bcfg = cfg or BarbellConfig()
        super().__init__()

    def core_weights(self, core_returns: pd.DataFrame) -> pd.DataFrame:
        """Per-bar inverse-vol weights over the safe-core assets (causal: uses the
        trailing-window vol; the caller shifts by 1 bar before applying)."""
        vol = core_returns.rolling(self.bcfg.vol_lookback,
                                   min_periods=self.bcfg.min_vol_periods).std()
        inv = 1.0 / vol.where(vol > 0, np.nan)
        return inv.div(inv.sum(axis=1), axis=0)

    def core_returns(self, core_returns: pd.DataFrame) -> pd.Series:
        """Daily returns of the inverse-vol SAFE CORE (no lookahead: yesterday's
        inverse-vol weights act on today's returns)."""
        w = self.core_weights(core_returns).shift(1)
        return (w * core_returns).sum(axis=1, min_count=1).dropna()

    def compose_returns(self, core_assets: pd.DataFrame,
                        satellite_returns: pd.Series) -> pd.Series:
        """Barbell daily returns: (1 - w_sat) * inverse-vol core + w_sat * convex
        satellite. ``core_assets`` is a DataFrame of core asset return series;
        ``satellite_returns`` the convex sleeve (e.g. the trend overlay)."""
        if self.bcfg.equity_vol_target:
            # Conditional vol-targeting on the equity sleeve is Engine-B's call
            # (T-252, FactorRiskModel/risk_engine). Fail closed — never silently
            # ship an un-vol-targeted core that reads as targeted.
            raise NotImplementedError(
                "equity_vol_target is Engine-B's conditional vol-targeting (T-252) "
                "— propose-first, B-gated. Not wired in the engine_c barbell composer.")
        core = self.core_returns(core_assets)
        ws = self.bcfg.satellite_weight
        bar = pd.concat({"core": core, "sat": satellite_returns}, axis=1, sort=True).dropna()
        return (1.0 - ws) * bar["core"] + ws * bar["sat"]
