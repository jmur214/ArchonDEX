"""Engine B — sleeve-level CONDITIONAL vol-targeting (T-2026-06-26-252).

Vol-target the EQUITY sleeve (e.g. SPY) toward a vol target. The fresh-eyes
brief endorsed this as one of two transferable structural edges, with a crucial
qualifier: the ROBUST variant is CONDITIONAL — act ONLY in extreme realized-vol
states — because *continuous* targeting can INCREASE drawdown (Perchet et al.,
FAJ 2020): levering up in calm regimes adds exposure right before vol clusters.
The Sharpe benefit is risk-asset-only (the leverage/return-vol effect); the
cross-asset win is the TAIL (drawdown) reduction.

This module is a NEW, pure, DEFAULT-OFF building block — it is not wired into any
active sizing path, so the production canon is byte-identical. Engine C composes
it into the barbell safe-core (T-251). It is NEVER a risk override: it only
scales sleeve exposure; in the conditional/deployable mode the sleeve stays
long/flat (`ceiling <= 1.0`, no leverage/borrow). Reuses the Moreira-Muir clip
semantics of `vol_target.compute_vol_scale` (vectorized, same guards).

Pre-registration (bound here, BEFORE the gauntlet; NO sweep — the brief's
corrected methodology: Sortino/MaxDD are a SCORECARD, not an optimization target):
  estimator   = `vol_window`-day trailing realized vol of the asset, annualized
  target_vol  = 0.15 (equity-appropriate; fixed)
  floor       = 0.50 (never de-gross below half)
  extreme     = realized vol above its own EXPANDING `extreme_percentile` (causal)
  conditional ceiling = 1.0 (de-gross in storms only, never lever)
  continuous  ceiling = 1.5 (the FAJ-critiqued lever-in-calm variant, for contrast)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass
class SleeveVolTargetConfig:
    """Defense-first config. `enabled=False` ⇒ `apply_sleeve_vol_target` is the
    identity (the sleeve returns pass through unchanged) ⇒ canon byte-identical."""
    enabled: bool = False
    conditional: bool = True          # True = act ONLY in extreme-vol states (robust)
    target_vol: float = 0.15          # annualized equity vol target (fixed, not swept)
    vol_window: int = 20              # trailing realized-vol window (days)
    floor: float = 0.5                # don't de-gross below 50%
    ceiling: float = 1.0              # <=1.0 ⇒ long/flat (deployable); >1 allows lever
    extreme_percentile: float = 0.80  # "extreme" = realized vol above this expanding pct
    min_history: int = 252            # min bars before a state can be called / sizing acts
    cost_bps: float = 5.0             # one-way turnover cost (liquid ETF)


def realized_vol(returns: pd.Series, window: int) -> pd.Series:
    """Trailing annualized realized vol (causal: uses returns up to t)."""
    return returns.rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)


def extreme_state(
    rv: pd.Series, percentile: float, min_history: int,
) -> pd.Series:
    """Causal extreme-vol mask: True where rv_t exceeds the EXPANDING
    `percentile` quantile of rv over its own history [0..t]. Below
    `min_history` observations the state is never 'extreme' (not enough
    history to judge). No look-ahead — the quantile uses only data ≤ t."""
    thr = rv.expanding(min_periods=max(2, min_history)).quantile(percentile)
    return (rv > thr) & thr.notna()


def vol_scale_series(rv: pd.Series, cfg: SleeveVolTargetConfig) -> pd.Series:
    """Per-bar vol-target scale, vectorized, mirroring `compute_vol_scale`'s
    guards (rv None/≤0/non-finite ⇒ 1.0). Continuous ⇒ clip(target/rv, floor,
    ceiling) every bar; conditional ⇒ that scale ONLY in extreme-vol states,
    else 1.0 (full exposure — de-gross in storms, never touch calm)."""
    rv = rv.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = (float(cfg.target_vol) / rv).clip(float(cfg.floor), float(cfg.ceiling))
    # guard: non-finite / non-positive rv ⇒ no scaling (1.0), like compute_vol_scale
    raw = raw.where(np.isfinite(rv) & (rv > 0.0), 1.0)
    if not cfg.conditional:
        return raw
    mask = extreme_state(rv, cfg.extreme_percentile, cfg.min_history)
    return raw.where(mask.reindex(raw.index).fillna(False), 1.0)


def apply_sleeve_vol_target(
    asset_returns: pd.Series, cfg: SleeveVolTargetConfig,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Apply the (conditional or continuous) vol-target overlay to ONE asset's
    daily return stream. Returns (net_returns, scale, gross_returns).

    No look-ahead: the position over day t is `scale_{t-1}` (act on yesterday's
    vol estimate). Net-of-cost: turnover_t = |pos_t − pos_{t-1}| charged at
    `cost_bps` one-way. DEFAULT-OFF (`enabled=False`) ⇒ identity: returns the
    input unchanged + a unit scale (canon byte-identical). [NN-FAIL-CLOSED]:
    enabled with an empty/None return stream ⇒ raise (never silently pass)."""
    if not getattr(cfg, "enabled", False):
        unit = pd.Series(1.0, index=asset_returns.index) if asset_returns is not None else pd.Series(dtype=float)
        return asset_returns, unit, asset_returns
    if asset_returns is None or len(asset_returns) == 0:
        raise ValueError(
            "[SLEEVE-VT][T-252] enabled but asset_returns is empty/None — "
            "refusing to size on a missing input ([NN-FAIL-CLOSED])."
        )
    rets = asset_returns.astype(float)
    rv = realized_vol(rets, cfg.vol_window)
    scale = vol_scale_series(rv, cfg)
    pos = scale.shift(1)                       # act on yesterday's scale (causal)
    gross = (pos * rets)
    turnover = pos.diff().abs().fillna(0.0)
    cost = turnover * (float(cfg.cost_bps) / 1e4)
    net = (gross - cost).dropna()
    return net, scale, gross.dropna()
