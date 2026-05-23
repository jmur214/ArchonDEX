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

    `estimator_type` (T-2026-05-22-055d) selects between:
      * "rolling" (default, T-055 behavior): equal-weighted stdev over
        a trailing `realized_vol_window_days` window.
      * "ewma": RiskMetrics 1996 EWMA, σ²_t = λσ²_{t-1} + (1-λ)r²_t.
        Faster vol-up response (λ=0.94 half-life ≈ 11 days). Addresses
        the T-055c 2025 vol-shock failure mode (Harvey-et-al-2018
        vol-expansion trap).

    Production default stays "rolling" so default-OFF callers (and
    enabled-but-unspecified callers) keep the T-055 / T-055c
    behavior. EWMA opts in via config.
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
    # T-055d: estimator selection. "rolling" preserves T-055 default.
    estimator_type: str = "rolling"
    # T-055d: EWMA decay factor (RiskMetrics standard).
    # Effective half-life = ln(0.5) / ln(λ) ≈ 11.2 days for λ=0.94.
    ewma_lambda: float = 0.94

    # T-2026-05-23-055e — regime-conditional target multiplier.
    # When `regime_aware=True` AND `compute_portfolio_vol_scale` is
    # called with a non-None `advisory` dict, the base
    # `target_annual_vol` is multiplied by the regime-summary-keyed
    # multiplier below before computing the scale. Defaults preserve
    # T-055d behavior:
    #   * regime_aware=False (default) → multiplier ignored entirely
    #   * regime_aware=True but advisory=None → multiplier ignored
    #   * unknown regime_summary value → multiplier = 1.0 (safe fallback)
    #
    # Rationale (T-055d 2022 bear degradation): EWMA's faster response
    # over-degrosses in bear/stress windows because the estimator
    # picks up vol clustering before the regime resolves. Muting the
    # target (lowering effective target_vol) in stress regimes
    # reduces over-degross by lowering the target → ratio numerator
    # stays smaller → realized vol scales down less aggressively
    # against a lower yardstick. Net: less aggressive degross in
    # stress, preserved benign-regime behavior.
    regime_aware: bool = False
    benign_target_multiplier: float = 1.0       # no-op
    cautious_target_multiplier: float = 0.85    # mild degross-bias
    stressed_target_multiplier: float = 0.60    # aggressive degross
    crisis_target_multiplier: float = 0.40      # heavy degross


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


def compute_realized_vol_from_history_ewma(
    history: Sequence[Dict[str, Any]],
    ewma_lambda: float,
    min_returns_required: int,
) -> Optional[float]:
    """Annualized realized portfolio vol via RiskMetrics 1996 EWMA.

    σ²_t = λ · σ²_{t-1} + (1 - λ) · r²_t

    Initialized as σ²_0 = r²_0 (the first observed daily return
    squared) — equivalent to assuming the pre-history state matches
    the first observation. Subsequent observations decay it
    exponentially with weight λ. Default λ=0.94 (RiskMetrics
    standard, half-life ≈ 11.2 days).

    Uses ALL daily-cadence returns in history (no window cutoff), so
    the recursive update can warm up over the full available series.
    Returns None when fewer than `min_returns_required` returns are
    available — matches the rolling estimator's warmup discipline.

    Same no-look-ahead guarantee as `compute_realized_vol_from_history`:
    operates only on `history` already present at call time, which is
    the prior-bar snapshot list at `prepare_order` time.
    """
    if not 0.0 < ewma_lambda < 1.0:
        # Degenerate λ values would collapse to one-sided estimators
        # or zero variance — refuse to fire rather than emit garbage.
        return None
    equity_series = _equity_at_end_of_each_day(history)
    if len(equity_series) < min_returns_required + 1:
        return None
    eq_arr = np.asarray(equity_series, dtype=float)
    if np.any(eq_arr <= 0.0):
        return None
    daily_returns = np.diff(eq_arr) / eq_arr[:-1]
    if len(daily_returns) < min_returns_required:
        return None
    # EWMA variance recursion. Vectorized via numpy iteration —
    # explicit loop is clearer than scipy.signal.lfilter for this
    # short series (≤ 2000 days), and avoids a scipy dependency.
    sigma2 = float(daily_returns[0] ** 2)
    one_minus_lambda = 1.0 - ewma_lambda
    for r in daily_returns[1:]:
        sigma2 = ewma_lambda * sigma2 + one_minus_lambda * float(r) ** 2
    sigma_daily = float(np.sqrt(sigma2))
    if sigma_daily <= 0.0 or not np.isfinite(sigma_daily):
        return None
    return sigma_daily * np.sqrt(TRADING_DAYS_PER_YEAR)


# T-055e regime-summary → multiplier-field mapping. Centralized so
# both the dispatcher AND tests have a single source of truth.
_REGIME_SUMMARY_TO_MULTIPLIER_FIELD: Dict[str, str] = {
    "benign": "benign_target_multiplier",
    "cautious": "cautious_target_multiplier",
    "stressed": "stressed_target_multiplier",
    "crisis": "crisis_target_multiplier",
}


def _regime_target_multiplier(
    cfg: VolTargetConfig,
    advisory: Optional[Dict[str, Any]],
) -> float:
    """T-055e: select the target-vol multiplier for the current regime.

    Returns 1.0 (no-op) when:
      * `cfg.regime_aware=False` (default) — feature opt-in flag,
      * `advisory` is None or empty — no regime signal available,
      * advisory["regime_summary"] is missing or has an unknown value.

    Engine E's `_risk_to_summary` emits one of
    {"benign", "cautious", "stressed", "crisis"} per
    `engines/engine_e_regime/advisory.py:326`. Unknown values fall
    back to 1.0 — safer than a hard error on schema drift.
    """
    if not getattr(cfg, "regime_aware", False):
        return 1.0
    if not advisory:
        return 1.0
    summary = advisory.get("regime_summary")
    field_name = _REGIME_SUMMARY_TO_MULTIPLIER_FIELD.get(summary)
    if field_name is None:
        return 1.0
    return float(getattr(cfg, field_name, 1.0))


def compute_portfolio_vol_scale(
    history: Sequence[Dict[str, Any]],
    cfg: VolTargetConfig,
    advisory: Optional[Dict[str, Any]] = None,
) -> float:
    """Composer: realized vol from snapshot history → bounded scale.

    Returns 1.0 (no-op) when:
      * the feature is disabled (cfg.enabled=False)
      * insufficient history for the realized-vol estimator
      * realized vol is zero / non-finite

    Otherwise returns the bounded scale per `compute_vol_scale`.

    Dispatches between the rolling estimator (T-055 default) and the
    EWMA estimator (T-055d) per `cfg.estimator_type`. Unknown values
    fall back to "rolling" for safety — preserves no-op invariant when
    a stale config slips through.

    T-2026-05-23-055e: optional `advisory` kwarg. When
    `cfg.regime_aware=True` AND advisory is non-None, the BASE
    `cfg.target_annual_vol` is multiplied by a regime-summary-keyed
    multiplier before the scale is computed. When `regime_aware=False`
    OR advisory is None, behavior is identical to T-055d (no breaking
    change to existing on-main / harness call sites).
    """
    if not cfg.enabled:
        return 1.0
    if getattr(cfg, "estimator_type", "rolling") == "ewma":
        realized_vol = compute_realized_vol_from_history_ewma(
            history,
            ewma_lambda=cfg.ewma_lambda,
            min_returns_required=cfg.min_returns_required,
        )
    else:
        realized_vol = compute_realized_vol_from_history(
            history,
            window_days=cfg.realized_vol_window_days,
            min_returns_required=cfg.min_returns_required,
        )
    # T-055e: apply the regime-conditional target multiplier. Defaults
    # to 1.0 (no-op) for the entire T-055/T-055c/T-055d code path.
    multiplier = _regime_target_multiplier(cfg, advisory)
    effective_target_vol = float(cfg.target_annual_vol) * multiplier
    return compute_vol_scale(
        realized_vol=realized_vol,
        target_vol=effective_target_vol,
        floor=cfg.leverage_floor,
        ceiling=cfg.leverage_ceiling,
    )
