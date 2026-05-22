"""Engine B portfolio-level vol-targeting (T-2026-05-12-055).

Implements Moreira-Muir 2017 portfolio-level vol-targeting as a
SIZING MODIFIER. Per the T-055 spec + CLAUDE.md non-negotiable rules:

- Vol-targeting is NEVER a risk override. Kill-switch / drawdown-halt
  fire BEFORE sizing; this module only adjusts the *magnitude* of
  orders that already passed those gates.
- Realized vol uses ONLY bars [t-window, t-1] — no look-ahead.
- Ships with `enabled=False` (defense-first). The flag-flip post-A/B
  validation is a separate sub-dispatch (T-055b).
- Pure-function `compute_vol_scale` for math; `compute_portfolio_vol_scale`
  composes against the live PortfolioEngine snapshot history.

The standard Moreira-Muir scaling is `scale = target_vol /
realized_vol`. With a floor (typ 0.5) we prevent zero-exposure in
calm regimes; with a ceiling (typ 2.0) we prevent the Feb-2018-style
over-leveraging trap.

Per-day equity is extracted by taking the LAST snapshot per unique
trading-date in `portfolio.history`. This handles the typical mode
where mode_controller emits multiple snapshots per bar (initial,
post-fill, bar-end) — only one value per day is used in the rolling
vol estimator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


TRADING_DAYS_PER_YEAR = 252


@dataclass
class VolTargetConfig:
    """Portfolio-level vol-targeting configuration.

    Defense-first: defaults to disabled. Director flag-flips after the
    A/B harness confirms expected Moreira-Muir +0.10-0.20 Sharpe lift.
    """
    enabled: bool = False
    target_annual_vol: float = 0.10
    realized_vol_window_days: int = 60
    leverage_floor: float = 0.5
    leverage_ceiling: float = 2.0
    # `min_returns_required` guards against early-cycle warmup: if
    # fewer than this many daily returns are available, the scalar
    # falls back to 1.0 (no-op). Default = window_days so we don't
    # compute on a partial window.
    min_returns_required: int = 60


def compute_vol_scale(
    realized_vol: Optional[float],
    target_vol: float,
    floor: float,
    ceiling: float,
) -> float:
    """Standard Moreira-Muir scaling clamped to [floor, ceiling].

    `realized_vol` is the ANNUALIZED realized portfolio volatility
    computed from a strictly-trailing returns window. `None` or
    non-positive values (insufficient data, zero variance) trigger
    no-op passthrough (return 1.0).

    Returns the leverage multiplier to apply to portfolio gross
    exposure. The caller is responsible for ensuring this is invoked
    only when the vol-target feature is enabled.
    """
    if realized_vol is None or not np.isfinite(realized_vol) or realized_vol <= 0.0:
        return 1.0
    if target_vol <= 0.0:
        return 1.0
    raw = float(target_vol) / float(realized_vol)
    return float(np.clip(raw, floor, ceiling))


def _equity_at_end_of_each_day(history: Sequence[Dict[str, Any]]) -> List[float]:
    """Extract the LAST snapshot's equity per unique trading-date.

    `portfolio.history` may contain multiple snapshots per day
    (initial bar, post-fill, bar-end). For a daily realized-vol
    estimator we need one value per trading day.
    """
    if not history:
        return []
    per_day: Dict[Any, float] = {}
    for snap in history:
        ts = snap.get("timestamp")
        if ts is None:
            continue
        # Normalize to date-key — works for pandas Timestamp, datetime,
        # or anything with .date(); falls back to identity for strings.
        try:
            key = ts.date() if hasattr(ts, "date") else ts
        except Exception:
            key = ts
        eq = snap.get("equity")
        if eq is None or not np.isfinite(float(eq)):
            continue
        per_day[key] = float(eq)
    # Preserve chronological order by key.
    return [per_day[k] for k in sorted(per_day.keys())]


def compute_realized_vol_from_history(
    history: Sequence[Dict[str, Any]],
    window_days: int,
    min_returns_required: int,
) -> Optional[float]:
    """Annualized realized portfolio vol from the trailing `window_days`
    of daily-cadence equity values.

    Uses ONLY data at-or-before the most recent snapshot — equivalent
    to "as of bar t-1" given the spec's no-look-ahead rule (the most
    recent snapshot in `history` IS yesterday's bar-end during the
    next bar's prepare_order call). Returns None when insufficient
    data is available.

    Computation:
        equity_d = end-of-day equity per unique date
        returns_d = equity_d.pct_change() over the trailing window
        sigma = stdev(returns_d, ddof=1) * sqrt(252)
    """
    equity_series = _equity_at_end_of_each_day(history)
    if len(equity_series) < min_returns_required + 1:
        # Need at least `min_returns_required + 1` equity values to
        # produce `min_returns_required` returns via diff.
        return None
    eq_arr = np.asarray(equity_series, dtype=float)
    if np.any(eq_arr <= 0.0):
        # Defensive: a non-positive equity invalidates pct-change semantics.
        return None
    # Take only the trailing window_days + 1 equity values so we get
    # exactly window_days returns.
    if len(eq_arr) > window_days + 1:
        eq_arr = eq_arr[-(window_days + 1):]
    daily_returns = np.diff(eq_arr) / eq_arr[:-1]
    if len(daily_returns) < min_returns_required:
        return None
    sigma_daily = float(np.std(daily_returns, ddof=1))
    if sigma_daily <= 0.0 or not np.isfinite(sigma_daily):
        return None
    return sigma_daily * np.sqrt(TRADING_DAYS_PER_YEAR)


def compute_portfolio_vol_scale(
    history: Sequence[Dict[str, Any]],
    cfg: VolTargetConfig,
) -> float:
    """Composer: realized vol from snapshot history → bounded scale.

    Returns 1.0 (no-op) when:
      * the feature is disabled (cfg.enabled=False)
      * insufficient history for the realized-vol estimator
      * realized vol is zero / non-finite

    Otherwise returns the bounded scale per `compute_vol_scale`.
    """
    if not cfg.enabled:
        return 1.0
    realized_vol = compute_realized_vol_from_history(
        history,
        window_days=cfg.realized_vol_window_days,
        min_returns_required=cfg.min_returns_required,
    )
    return compute_vol_scale(
        realized_vol=realized_vol,
        target_vol=cfg.target_annual_vol,
        floor=cfg.leverage_floor,
        ceiling=cfg.leverage_ceiling,
    )
