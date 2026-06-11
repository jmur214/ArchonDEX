# engines/engine_c_portfolio/dynamic_optimizer.py
"""Carver-style dynamic optimization — the integer-position layer (T-139).

At small capital (the $5K deployment tier) a multi-name target portfolio
cannot be expressed in whole shares: naive per-name rounding destroys the
diversification the allocator worked to construct. This module chooses the
INTEGER position set that best approximates the unrounded optimal
portfolio, by greedily minimizing tracking error net of a shadow-scaled
trading-cost penalty.

Concept ported from Robert Carver's pysystemtrade
(``systems/provided/dynamic_small_system_optimise/`` — ``greedy_algo.py``,
``optimisation.py``, ``buffering.py``, ``set_up_constraints.py``; Carver's
2021-22 "dynamic optimisation" blog posts are the design rationale).
This is a CONCEPT port for ArchonDEX's per-share equity book — no code is
vendored. Faithful elements and deliberate deviations:

Faithful to source:
  * All optimization happens in WEIGHT space. ``per-share value``
    (price/equity) plays the role of pysystemtrade's per-contract value.
  * Objective = ``sqrt((w-w*)' Σ (w-w*)) + shadow_cost · Σ c_i·|w_i-w_prior_i|``
    — tracking error as an annualized STD (pysystemtrade
    ``objectiveFunctionForGreedy.evaluate``), NOT the variance form; costs
    are linear in the weight-space trade gap vs the PRIOR position.
  * Greedy search starts from zero weights and steps one share at a time,
    only in the direction of the unrounded optimal weight, accepting the
    single best objective-reducing step per round, stopping when no step
    improves (``greedy_algo_across_integer_values``).
  * Tracking-error buffer: if the PRIOR portfolio already tracks the
    optimal within ``tracking_error_buffer``, no trades at all. Otherwise
    the optimized trade is scaled by ``(TE_prior - buffer)/TE_prior`` and
    re-rounded in share space (``buffering.calculate_adjustment_factor`` /
    ``adjust_weights_with_factor``).
  * Defaults ``shadow_cost=10`` and ``tracking_error_buffer=0.02`` match
    pysystemtrade's production config values. (The source dataclass
    literals are accidental 1-tuples — ``(10,)`` — and never bind; the
    intended scalars are used here.)

Deviations (each deliberate, each documented in the T-139 audit doc):
  * MULTI-START: the Carver walk runs from zero (source-faithful) AND
    from the production naive-truncation book when that book is feasible;
    the better final objective wins. Guarantees the optimizer never does
    worse than what Engine B's truncation produces today. The source uses
    a single zero start and accepts greedy stalls.
  * BIDIRECTIONAL POLISH: after each walk, a ±1-share local search
    (sign-preserving, bounds-respecting, strict-improvement) cleans up
    stalls the toward-target-only walk cannot escape in correlated books
    — e.g. overweighting one name to compensate an unreachable
    underweight in a correlated sibling, which is precisely the
    diversification-recovery effect wanted at $5K. The source restricts
    steps to the target direction only.
  * Per-trade costs are a flat ``cost_per_trade_bps`` of traded notional
    (uniform across names) instead of pysystemtrade's per-instrument cost
    estimates — our book is liquid US equities at sub-ADV sizes where a
    flat spread/2 + bps model is the project standard.
  * A hard gross-notional buying-power bound (Σ|w_i| ≤ fraction) replaces
    pysystemtrade's optional ``maximum_positions`` / constraint-function
    machinery. Steps that would breach it are infeasible (equivalent to
    Carver's "very large number" penalty, but exact).
  * Negative tracking-error variance (possible under a non-PSD covariance
    estimate) FAILS OPEN to "keep prior positions" instead of raising —
    an autonomous backtest must degrade gracefully (CLAUDE.md operating
    constraint), and no-trade is the conservative direction. The source
    raises. Tiny negatives within float tolerance clamp to 0.0 (the
    project's tolerance-not-equality guard discipline, T-061/T-065).
  * Output weights carry a ±1e-6-share directional nudge so Engine B's
    Path A truncation ``int(delta_notional/price)`` lands exactly on the
    chosen integers (see ``_engine_b_feasible_weights``). pysystemtrade
    emits contract counts directly; we must round-trip through the
    existing weight pipe without touching Engine B.

Engine boundary: this is Engine C (portfolio construction). It consumes
Engine C target weights + portfolio state downstream of the allocator and
emits adjusted target weights. It does NOT touch Engine B sizing logic —
Engine B keeps applying its own gates (rebalance tolerance, min notional,
exposure caps) to the adjusted weights exactly as it does today.

Determinism: pure NumPy on arrays built in sorted-ticker order; no RNG,
no wall-clock, no dict-iteration-order dependence (T-057c lesson). Ties
in the greedy step resolve to the first ticker in sorted order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "DynamicOptimizationConfig",
    "DynamicOptimizationResult",
    "optimize_integer_positions",
    "naive_rounded_positions",
    "tracking_error_std",
]

# Float-tolerance guards (project discipline: tolerance, never exact equality).
_VAR_CLAMP_TOL = 1e-10      # |negative variance| below this clamps to 0.0
_BOUND_TOL = 1e-12          # feasibility comparisons
_NUDGE_SHARES = 1e-6        # directional nudge for Engine B truncation safety
_MAX_GREEDY_ITER = 100_000  # hard stop; never binds at realistic book sizes


@dataclass
class DynamicOptimizationConfig:
    """Tunables for the integer-position optimizer.

    Defaults mirror pysystemtrade production values where a counterpart
    exists (shadow_cost, tracking_error_buffer); the rest mirror existing
    Engine C conventions (cov_lookback / use_ledoit_wolf match HRPConfig,
    cost_per_trade_bps matches PortfolioOptimizerSettings.turnover_flat_cost_bps).
    """
    shadow_cost: float = 10.0            # multiplier on the cost term (Carver default)
    cost_per_trade_bps: float = 10.0     # per-trade cost, bps of traded notional
    tracking_error_buffer: float = 0.02  # annualized TE below which we don't trade
    buying_power_fraction: float = 1.0   # gross Σ|w| hard cap (1.0 = no leverage)
    max_weight_per_asset: Optional[float] = None  # |w_i| hard cap; None = uncapped
    annualization_factor: float = 252.0  # daily→annual variance scaling


@dataclass
class DynamicOptimizationResult:
    """Output of one optimization call (one rebalance bar)."""
    positions: Dict[str, int]            # chosen integer share counts (optimized tickers)
    weights: Dict[str, float]            # Engine-B-feasible weights for ALL input tickers
    trades: Dict[str, int]               # positions - current (optimized tickers, nonzero only)
    current_positions: Dict[str, int]    # prior integer positions (optimized tickers)
    naive_positions: Dict[str, int]      # prod-parity truncation baseline
    tracking_error_optimized: float      # annualized TE of chosen positions vs unrounded
    tracking_error_naive: float          # annualized TE of naive rounding vs unrounded
    tracking_error_prior: float          # annualized TE of prior positions vs unrounded
    buffered: bool                       # True → prior kept (TE within buffer)
    skipped: bool = False                # True → optimization not attempted (fail-open)
    skip_reason: Optional[str] = None
    dropped_tickers: List[str] = field(default_factory=list)  # passed through unoptimized
    diagnostics: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------- #
def tracking_error_std(
    weights: np.ndarray, target: np.ndarray, sigma_annual: np.ndarray
) -> float:
    """Annualized tracking-error std ``sqrt((w-w*)' Σ (w-w*))``.

    Negative variance beyond float tolerance returns ``nan`` so callers
    can fail open (source raises; we degrade gracefully).
    """
    gap = weights - target
    var = float(gap @ sigma_annual @ gap)
    if var < -_VAR_CLAMP_TOL:
        return float("nan")
    return float(np.sqrt(max(var, 0.0)))


def naive_rounded_positions(
    target_weights: np.ndarray,
    prices: np.ndarray,
    current_qty: np.ndarray,
    equity: float,
) -> np.ndarray:
    """Production-parity naive rounding: Engine B Path A truncates the
    DELTA notional toward zero (``add_qty = int(delta_notional / price)``),
    so the naive baseline is ``current + trunc((w*·E − cur·p)/p)`` —
    not round-half-even of the target.
    """
    delta_shares = (target_weights * equity - current_qty * prices) / prices
    return current_qty + np.trunc(delta_shares).astype(np.int64)


def _greedy_search(
    n_start: np.ndarray,
    w_star: np.ndarray,
    pcv: np.ndarray,
    w_prior: np.ndarray,
    sigma_annual: np.ndarray,
    cfg: DynamicOptimizationConfig,
) -> Tuple[np.ndarray, float]:
    """One Carver greedy walk in INTEGER share space, from ``n_start``.

    Per asset the step is one share in the fixed direction of the
    unrounded optimal; take the single best improving step per round;
    stop when nothing improves (``greedy_algo_across_integer_values``).
    Working in share counts (weights derived as ``n·pcv`` per evaluation)
    avoids accumulating float error along the walk.

    Returns ``(positions, objective_value)``.
    """
    n = len(w_star)
    cost_rate = cfg.cost_per_trade_bps / 1e4

    def evaluate(n_vec: np.ndarray) -> float:
        w = n_vec * pcv
        te = tracking_error_std(w, w_star, sigma_annual)
        if np.isnan(te):
            return float("inf")
        cost = cfg.shadow_cost * float(np.sum(cost_rate * np.abs(w - w_prior)))
        return te + cost

    # Direction: sign of the optimal weight; zero/NaN targets walk +1 but
    # immediately fail to improve, so they stay put (source behavior).
    direction = np.where(w_star > 0.0, 1, np.where(w_star < 0.0, -1, 1)).astype(np.int64)

    minima, maxima = _weight_bounds(n, cfg)
    gross_cap = float(cfg.buying_power_fraction)

    best = n_start.astype(np.int64).copy()
    best_value = evaluate(best)
    at_limit = np.zeros(n, dtype=bool)

    for _ in range(_MAX_GREEDY_ITER):
        improved = False
        round_best_value = best_value
        round_best_idx = -1
        gross_now = float(np.sum(np.abs(best * pcv)))
        for i in range(n):
            if at_limit[i]:
                continue
            stepped_n_i = best[i] + direction[i]
            stepped_w_i = stepped_n_i * pcv[i]
            if stepped_w_i > maxima[i] + _BOUND_TOL or stepped_w_i < minima[i] - _BOUND_TOL:
                at_limit[i] = True
                continue
            # Buying-power feasibility: stepping in the fixed direction
            # only ever grows |w_i| (starts share the target's sign), so
            # once gross breaches the cap this asset can never step again.
            new_gross = gross_now - abs(best[i] * pcv[i]) + abs(stepped_w_i)
            if new_gross > gross_cap + _BOUND_TOL:
                at_limit[i] = True
                continue
            candidate = best.copy()
            candidate[i] = stepped_n_i
            value = evaluate(candidate)
            if value < round_best_value:
                round_best_value = value
                round_best_idx = i
                improved = True
        if not improved:
            break
        best[round_best_idx] += direction[round_best_idx]
        best_value = round_best_value
    return best, best_value


def _weight_bounds(n: int, cfg: DynamicOptimizationConfig) -> Tuple[np.ndarray, np.ndarray]:
    if cfg.max_weight_per_asset is not None:
        cap = abs(float(cfg.max_weight_per_asset))
        return np.full(n, -cap), np.full(n, cap)
    return np.full(n, -np.inf), np.full(n, np.inf)


def _within_bounds(n_vec: np.ndarray, pcv: np.ndarray, cfg: DynamicOptimizationConfig) -> bool:
    """Feasibility of a candidate integer book under the hard constraints."""
    w = n_vec * pcv
    minima, maxima = _weight_bounds(len(w), cfg)
    if np.any(w > maxima + _BOUND_TOL) or np.any(w < minima - _BOUND_TOL):
        return False
    return float(np.sum(np.abs(w))) <= float(cfg.buying_power_fraction) + _BOUND_TOL


def _bidirectional_polish(
    n_in: np.ndarray,
    w_star: np.ndarray,
    pcv: np.ndarray,
    w_prior: np.ndarray,
    sigma_annual: np.ndarray,
    cfg: DynamicOptimizationConfig,
) -> Tuple[np.ndarray, float]:
    """Local ±1-share polish (deviation from source, documented).

    The toward-target-only walk can stall in a correlated book where no
    single toward-target step improves but a small overweight in one name
    compensates an unreachable underweight in another — exactly the
    diversification-recovery behavior wanted at small capital. This pass
    tries ±1 share per asset (sign-preserving: a position never flips
    through zero past the target's sign — cash-account reality), accepts
    the single best strictly-improving feasible step per round, and stops
    when none improves. Strict improvement on a bounded lattice ⇒
    terminates.
    """
    n = len(w_star)
    cost_rate = cfg.cost_per_trade_bps / 1e4

    def evaluate(n_vec: np.ndarray) -> float:
        w = n_vec * pcv
        te = tracking_error_std(w, w_star, sigma_annual)
        if np.isnan(te):
            return float("inf")
        cost = cfg.shadow_cost * float(np.sum(cost_rate * np.abs(w - w_prior)))
        return te + cost

    minima, maxima = _weight_bounds(n, cfg)
    gross_cap = float(cfg.buying_power_fraction)

    best = n_in.astype(np.int64).copy()
    best_value = evaluate(best)

    for _ in range(_MAX_GREEDY_ITER):
        round_best_value = best_value
        round_best: Optional[Tuple[int, int]] = None
        gross_now = float(np.sum(np.abs(best * pcv)))
        for i in range(n):
            for step in (1, -1):
                stepped_n_i = best[i] + step
                # Sign-preserving: stay on the target's side of zero.
                if w_star[i] >= 0.0 and stepped_n_i < 0:
                    continue
                if w_star[i] <= 0.0 and stepped_n_i > 0:
                    continue
                stepped_w_i = stepped_n_i * pcv[i]
                if stepped_w_i > maxima[i] + _BOUND_TOL or stepped_w_i < minima[i] - _BOUND_TOL:
                    continue
                new_gross = gross_now - abs(best[i] * pcv[i]) + abs(stepped_w_i)
                if new_gross > gross_cap + _BOUND_TOL:
                    continue
                candidate = best.copy()
                candidate[i] = stepped_n_i
                value = evaluate(candidate)
                if value < round_best_value:
                    round_best_value = value
                    round_best = (i, step)
        if round_best is None:
            break
        best[round_best[0]] += round_best[1]
        best_value = round_best_value
    return best, best_value


def _apply_te_buffer_adjustment(
    w_optimized: np.ndarray,
    w_prior: np.ndarray,
    pcv: np.ndarray,
    sigma_annual: np.ndarray,
    buffer: float,
) -> np.ndarray:
    """Carver's speed control: scale the desired trade by the fraction of
    prior tracking error (measured against the OPTIMIZED portfolio) in
    excess of the buffer, then re-round the scaled trade in share space.
    """
    te_prior_vs_opt = tracking_error_std(w_prior, w_optimized, sigma_annual)
    if np.isnan(te_prior_vs_opt) or te_prior_vs_opt <= 0.0:
        return w_prior.copy()
    adj_factor = max((te_prior_vs_opt - buffer) / te_prior_vs_opt, 0.0)
    if adj_factor <= 0.0:
        return w_prior.copy()
    desired_trade_w = (w_optimized - w_prior) * adj_factor
    rounded_trade_shares = np.round(desired_trade_w / pcv)
    return w_prior + rounded_trade_shares * pcv


# --------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------- #
def optimize_integer_positions(
    target_weights: Dict[str, float],
    prices: Dict[str, float],
    current_positions: Dict[str, int],
    equity: float,
    covariance: pd.DataFrame,
    cfg: Optional[DynamicOptimizationConfig] = None,
) -> DynamicOptimizationResult:
    """Choose integer positions approximating the unrounded target book.

    Parameters
    ----------
    target_weights : unrounded target weights from the allocation path
        (post vol-target / exposure-cap overlays). Keys define the
        tradable set this bar.
    prices : last Close per ticker (same bar/source Engine B sizes from).
    current_positions : current signed integer share counts (0 if flat).
    equity : total portfolio equity Engine B will size against this bar.
    covariance : DAILY returns covariance (tickers × tickers DataFrame),
        e.g. from ``HRPOptimizer._estimate_cov``. Annualized internally.
    cfg : tunables; defaults are the Carver-parity values.

    Fail-open contract: any input that can't be optimized (bad equity,
    missing/invalid prices, no covariance overlap) degrades to passing the
    affected weights through unchanged — Engine B then behaves exactly as
    it does today for those names. The OFF flag is enforced by the caller;
    this function assumes it is wanted.
    """
    cfg = cfg or DynamicOptimizationConfig()

    def _passthrough(reason: str) -> DynamicOptimizationResult:
        return DynamicOptimizationResult(
            positions={},
            weights=dict(target_weights),
            trades={},
            current_positions={},
            naive_positions={},
            tracking_error_optimized=float("nan"),
            tracking_error_naive=float("nan"),
            tracking_error_prior=float("nan"),
            buffered=False,
            skipped=True,
            skip_reason=reason,
            dropped_tickers=sorted(target_weights.keys()),
        )

    if not target_weights:
        return _passthrough("empty_target_weights")
    if equity is None or not np.isfinite(equity) or equity <= 0.0:
        return _passthrough("invalid_equity")
    if covariance is None or covariance.empty:
        return _passthrough("no_covariance")

    # Sorted-ticker canonical order; per-ticker validity filtering.
    cov_index = set(covariance.index)
    tickers: List[str] = []
    dropped: List[str] = []
    for t in sorted(target_weights.keys()):
        w = target_weights[t]
        p = prices.get(t)
        valid = (
            w is not None and np.isfinite(w)
            and p is not None and np.isfinite(p) and p > 0.0
            and t in cov_index
        )
        (tickers if valid else dropped).append(t)
    if not tickers:
        return _passthrough("no_optimizable_tickers")

    w_star = np.array([float(target_weights[t]) for t in tickers])
    px = np.array([float(prices[t]) for t in tickers])
    cur = np.array([int(current_positions.get(t, 0)) for t in tickers], dtype=np.int64)
    pcv = px / float(equity)                     # one share's weight
    w_prior = cur.astype(float) * pcv

    sigma = covariance.loc[tickers, tickers].to_numpy(dtype=float)
    sigma = 0.5 * (sigma + sigma.T) * float(cfg.annualization_factor)
    if not np.all(np.isfinite(sigma)):
        return _passthrough("non_finite_covariance")

    te_prior = tracking_error_std(w_prior, w_star, sigma)
    if np.isnan(te_prior):
        return _passthrough("negative_te_variance")

    n_naive = naive_rounded_positions(w_star, px, cur, float(equity))
    te_naive = tracking_error_std(n_naive.astype(float) * pcv, w_star, sigma)

    diagnostics: Dict[str, Any] = {
        "n_tickers": len(tickers),
        "equity": float(equity),
        "gross_target": float(np.sum(np.abs(w_star))),
    }

    # Carver buffer: prior already tracks within tolerance → no trades.
    if te_prior < float(cfg.tracking_error_buffer):
        n_final = cur.copy()
        buffered = True
        te_opt = te_prior
    else:
        # Multi-start: zero (source-faithful) + the naive book when
        # feasible. Greedy from the naive start can only improve on it,
        # so the chosen objective dominates production naive rounding by
        # construction whenever naive is feasible under the constraints.
        starts = [np.zeros(len(tickers), dtype=np.int64)]
        if _within_bounds(n_naive, pcv, cfg):
            starts.append(n_naive)
        best_n: Optional[np.ndarray] = None
        best_val = float("inf")
        for n_start in starts:
            n_walk, _ = _greedy_search(n_start, w_star, pcv, w_prior, sigma, cfg)
            n_pol, val = _bidirectional_polish(n_walk, w_star, pcv, w_prior, sigma, cfg)
            if val < best_val:
                best_val = val
                best_n = n_pol
        w_opt = best_n.astype(float) * pcv
        w_adj = _apply_te_buffer_adjustment(
            w_opt, w_prior, pcv, sigma, float(cfg.tracking_error_buffer)
        )
        # Integer share counts: w_adj is prior + (rounded trade)·pcv by
        # construction, so this rounding is exact recovery, not a re-round.
        n_final = np.round(w_adj / pcv).astype(np.int64)
        buffered = False
        te_opt = tracking_error_std(n_final.astype(float) * pcv, w_star, sigma)

    # Engine-B-feasible output weights: ±1e-6-share directional nudge so
    # Path A's int(delta_notional/price) truncation lands exactly on
    # n_final - cur (truncation is toward zero; the nudge keeps the FP
    # quotient strictly on the far side of the intended integer).
    trade = n_final - cur
    nudge = np.sign(trade) * _NUDGE_SHARES
    w_out = (n_final.astype(float) + nudge) * pcv

    weights_out: Dict[str, float] = {t: float(target_weights[t]) for t in dropped}
    for i, t in enumerate(tickers):
        weights_out[t] = float(w_out[i])

    return DynamicOptimizationResult(
        positions={t: int(n_final[i]) for i, t in enumerate(tickers)},
        weights=weights_out,
        trades={t: int(trade[i]) for i, t in enumerate(tickers) if trade[i] != 0},
        current_positions={t: int(cur[i]) for i, t in enumerate(tickers)},
        naive_positions={t: int(n_naive[i]) for i, t in enumerate(tickers)},
        tracking_error_optimized=float(te_opt),
        tracking_error_naive=float(te_naive),
        tracking_error_prior=float(te_prior),
        buffered=buffered,
        dropped_tickers=dropped,
        diagnostics=diagnostics,
    )
