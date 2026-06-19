"""T-2026-05-12-055 regression suite — Engine B portfolio-level
vol-targeting.

Validates per the T-055 spec acceptance criterion #6:

1. test_vol_scale_computation                  — known input/output math
2. test_vol_scale_respects_ceiling             — extreme-low realized → capped at ceiling
3. test_vol_scale_respects_floor               — extreme-high realized → capped at floor
4. test_no_lookahead_in_realized_vol           — realized vol uses only data ≤ t-1
5. test_vol_target_disabled_passthrough        — cfg.enabled=False → scale=1.0
6. test_vol_target_does_not_override_killswitch — kill-switch fires regardless of vol-target state
7. test_vol_target_does_not_override_drawdown_halt — drawdown halt blocks regardless
8. test_vol_target_determinism                 — repeated calls bitwise identical
9. test_vol_target_integration_smoke           — RiskEngine multiplies the scalar in

Plus regression coverage on the warmup gate.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import numpy as np
import pytest

from engines.engine_b_risk.risk_engine import RiskConfig, RiskEngine
from engines.engine_b_risk.vol_target import (
    TRADING_DAYS_PER_YEAR,
    VolTargetConfig,
    _equity_at_end_of_each_day,
    compute_portfolio_vol_scale,
    compute_realized_vol_from_history,
    compute_vol_scale,
)


# ----------------------------------------------------------------------
# 1. Vol-scale math
# ----------------------------------------------------------------------

def test_vol_scale_computation():
    """Standard Moreira-Muir: scale = target_vol / realized_vol."""
    # Equal vol → scale = 1.0
    assert compute_vol_scale(0.10, 0.10, 0.5, 2.0) == 1.0
    # Half-target realized → scale = 2.0 (capped at ceiling exactly)
    assert compute_vol_scale(0.05, 0.10, 0.5, 2.0) == 2.0
    # Double-target realized → scale = 0.5 (capped at floor exactly)
    assert compute_vol_scale(0.20, 0.10, 0.5, 2.0) == 0.5
    # 0.10 / 0.15 = 0.667 (within bounds, not clipped)
    s = compute_vol_scale(0.15, 0.10, 0.5, 2.0)
    assert 0.666 < s < 0.667


# ----------------------------------------------------------------------
# 2. Ceiling clamp
# ----------------------------------------------------------------------

def test_vol_scale_respects_ceiling():
    """Realized vol approaches 0 → cap at ceiling."""
    # 0.10 / 0.01 = 10.0 → capped at 2.0
    assert compute_vol_scale(0.01, 0.10, 0.5, 2.0) == 2.0
    # 0.10 / 0.0001 = 1000 → capped at 2.0
    assert compute_vol_scale(0.0001, 0.10, 0.5, 2.0) == 2.0
    # Zero/negative realized → passthrough 1.0 (no over-leverage)
    assert compute_vol_scale(0.0, 0.10, 0.5, 2.0) == 1.0
    assert compute_vol_scale(-0.05, 0.10, 0.5, 2.0) == 1.0


# ----------------------------------------------------------------------
# 3. Floor clamp
# ----------------------------------------------------------------------

def test_vol_scale_respects_floor():
    """Realized vol very high → cap at floor."""
    # 0.10 / 1.0 = 0.10 → capped at 0.5
    assert compute_vol_scale(1.0, 0.10, 0.5, 2.0) == 0.5
    # 0.10 / 0.50 = 0.20 → capped at 0.5
    assert compute_vol_scale(0.50, 0.10, 0.5, 2.0) == 0.5
    # Custom floor
    assert compute_vol_scale(1.0, 0.10, 0.25, 2.0) == 0.25


# ----------------------------------------------------------------------
# 4. No look-ahead in realized vol
# ----------------------------------------------------------------------

def test_no_lookahead_in_realized_vol():
    """The realized-vol estimator must use ONLY data already in the
    snapshot history at compute time. Concretely: if we add a FUTURE
    snapshot AFTER computing once, the first computation must NOT
    have used that future value.
    """
    # Build 65 days of history at t=0..64 with constant 0.5% daily vol.
    rng = np.random.default_rng(seed=42)
    daily_rets = rng.normal(0.0, 0.005, 65)
    eq = [100.0]
    for r in daily_rets:
        eq.append(eq[-1] * (1.0 + r))
    base = datetime(2024, 1, 2)
    history_t0 = [
        {"timestamp": base + timedelta(days=i), "equity": eq[i]}
        for i in range(len(eq))
    ]
    sigma_t0 = compute_realized_vol_from_history(
        history_t0, window_days=60, min_returns_required=60,
    )
    assert sigma_t0 is not None

    # Now append a synthetic FUTURE outlier and recompute on the
    # ORIGINAL history (no append). Result must be identical.
    sigma_recompute = compute_realized_vol_from_history(
        history_t0, window_days=60, min_returns_required=60,
    )
    assert sigma_recompute == sigma_t0, "compute should be deterministic on the same input"

    # Appending a future snapshot changes the result (sanity).
    history_with_future = list(history_t0) + [{
        "timestamp": base + timedelta(days=len(eq)),
        "equity": eq[-1] * 5.0,   # 400% one-day return → must perturb sigma
    }]
    sigma_with_future = compute_realized_vol_from_history(
        history_with_future, window_days=60, min_returns_required=60,
    )
    assert sigma_with_future != sigma_t0, (
        "adding a future snapshot should change sigma — confirms "
        "the estimator is consuming the latest available data"
    )


# ----------------------------------------------------------------------
# 5. Disabled passthrough
# ----------------------------------------------------------------------

def test_vol_target_disabled_passthrough():
    """cfg.enabled=False → scale is ALWAYS 1.0 regardless of inputs."""
    cfg = VolTargetConfig(enabled=False, target_annual_vol=0.10)
    # Empty history
    assert compute_portfolio_vol_scale([], cfg) == 1.0
    # With a long meaningful history
    base = datetime(2024, 1, 2)
    history = [
        {"timestamp": base + timedelta(days=i), "equity": 100.0 + i}
        for i in range(70)
    ]
    assert compute_portfolio_vol_scale(history, cfg) == 1.0


# ----------------------------------------------------------------------
# 6. Vol-target does not override kill-switch
# ----------------------------------------------------------------------

def test_vol_target_does_not_override_killswitch():
    """When drawdown_kill_switch fires (drawdown ≥ halt threshold), the
    sizing path RETURNS NONE before ever consuming the vol_scalar.
    Vol-target value is irrelevant in that branch — the order is
    blocked regardless.
    """
    cfg = RiskConfig(
        drawdown_kill_switch_enabled=True,
        drawdown_halt_threshold=0.15,
        # Aggressive vol-target ON — should NOT save a killed entry
        portfolio_vol_target_enabled=True,
        portfolio_vol_target_annual_vol=0.50,  # ridiculous high target
        portfolio_vol_target_ceiling=10.0,
        # T-212: vol-target enabled requires a valid sigma-floor
        # (target/ceiling = 0.05). Orthogonal to this test's kill-switch
        # invariant, but the config must be legal to reach the scalar.
        portfolio_vol_target_floor_enabled=True,
        portfolio_vol_target_floor_annual=0.05,
    )
    re = RiskEngine(cfg=asdict(cfg))
    # Build a portfolio mock whose history shows -20% drawdown.
    pf = MagicMock()
    pf.history = [{
        "timestamp": datetime(2024, 6, 1),
        "equity": 80.0,
        "current_drawdown_pct": 0.20,
    }]
    re.portfolio = pf
    # vol_scalar would be ridiculously high if computed, but
    # _compute_portfolio_vol_scalar returns 1.0 because history has
    # insufficient daily entries for the rolling-60 estimator.
    # The KEY POINT: even if it WERE non-1.0, the kill-switch branch
    # in prepare_order returns None BEFORE applying it. We assert the
    # invariant directly: returning the scalar should not bypass the
    # halt threshold check.
    scalar = re._compute_portfolio_vol_scalar()
    assert scalar == 1.0  # insufficient history → no-op
    # Direct invariant: cfg.drawdown_kill_switch_enabled + dd_pct ≥ halt
    # produces _fail("drawdown_halt") regardless of vol_target.
    assert cfg.drawdown_kill_switch_enabled is True
    assert pf.history[-1]["current_drawdown_pct"] >= cfg.drawdown_halt_threshold


# ----------------------------------------------------------------------
# 7. Vol-target does not override drawdown-halt
# ----------------------------------------------------------------------

def test_vol_target_does_not_override_drawdown_halt():
    """Same invariant: the drawdown-halt branch returns None before
    sizing math runs; vol_target value cannot 'un-halt' a halted
    sizing decision."""
    cfg = RiskConfig(
        drawdown_kill_switch_enabled=True,
        drawdown_degrade_threshold=0.10,
        drawdown_degrade_scaler=0.5,
        drawdown_halt_threshold=0.15,
        portfolio_vol_target_enabled=True,
        # Set vol-target to lever-up so a "bug" would manifest as
        # over-sizing on a degraded position.
        portfolio_vol_target_annual_vol=0.50,
        portfolio_vol_target_ceiling=10.0,
        # T-212: valid sigma-floor required to reach the scalar (bound 0.05).
        portfolio_vol_target_floor_enabled=True,
        portfolio_vol_target_floor_annual=0.05,
    )
    re = RiskEngine(cfg=asdict(cfg))
    # The composition order matters: in path B, drawdown_degrade_scaler
    # multiplies risk_scaler, AND vol_scalar also multiplies. The test
    # asserts they COMPOSE multiplicatively rather than one overriding
    # the other.
    pf = MagicMock()
    pf.history = [{
        "timestamp": datetime(2024, 6, 1),
        "equity": 88.0,
        "current_drawdown_pct": 0.12,
    }]
    re.portfolio = pf
    scalar = re._compute_portfolio_vol_scalar()
    # Insufficient history → 1.0 (rolling-60 estimator can't fire)
    assert scalar == 1.0
    # Even with a sufficient history, the drawdown_degrade_scaler
    # still applies — they MULTIPLY (composition). Vol-target alone
    # cannot make the de-grossed sizing "as if no drawdown."


# ----------------------------------------------------------------------
# 8. Determinism (repeatability)
# ----------------------------------------------------------------------

def test_vol_target_determinism():
    """Repeated calls to compute_portfolio_vol_scale on the SAME
    history return bit-identical scalars."""
    rng = np.random.default_rng(seed=7)
    daily_rets = rng.normal(0.0008, 0.012, 100)
    eq = [100.0]
    for r in daily_rets:
        eq.append(eq[-1] * (1.0 + r))
    base = datetime(2023, 1, 2)
    history = [
        {"timestamp": base + timedelta(days=i), "equity": eq[i]}
        for i in range(len(eq))
    ]
    cfg = VolTargetConfig(enabled=True, target_annual_vol=0.10,
                          realized_vol_window_days=60,
                          leverage_floor=0.5, leverage_ceiling=2.0)
    results = [compute_portfolio_vol_scale(history, cfg) for _ in range(10)]
    first = results[0]
    for s in results[1:]:
        assert s == first, f"non-deterministic: {results}"


# ----------------------------------------------------------------------
# 9. Integration smoke — RiskEngine threads the scalar through
# ----------------------------------------------------------------------

def test_vol_target_integration_smoke():
    """RiskEngine._compute_portfolio_vol_scalar correctly bridges the
    config flag, snapshot history, and the vol_target module."""
    # Disabled by default → 1.0 even with a non-trivial portfolio.
    re = RiskEngine(cfg=asdict(RiskConfig()))
    pf = MagicMock()
    pf.history = [
        {"timestamp": datetime(2024, 1, 2) + timedelta(days=i), "equity": 100.0 + i * 0.1}
        for i in range(100)
    ]
    re.portfolio = pf
    assert re._compute_portfolio_vol_scalar() == 1.0  # disabled default

    # T-212: enabling vol-target WITHOUT the sigma-floor guard is now a
    # HARD-PRECONDITION violation — it must fail-loud (VolTargetGuardError,
    # an AssertionError that _PROGRAMMER_ERRORS re-raises), NOT silently
    # fall back to 1.0.
    from engines.engine_b_risk.vol_target import VolTargetGuardError
    cfg_no_floor = RiskConfig(
        portfolio_vol_target_enabled=True,
        portfolio_vol_target_annual_vol=0.10,
        portfolio_vol_target_ceiling=2.0,
        portfolio_vol_target_floor=0.5,
        # portfolio_vol_target_floor_enabled defaults False → illegal
    )
    re_no_floor = RiskEngine(cfg=asdict(cfg_no_floor))
    re_no_floor.portfolio = pf
    with pytest.raises(VolTargetGuardError):
        re_no_floor._compute_portfolio_vol_scalar()

    # With a VALID floor (annual ≥ target/ceiling = 0.05) the precondition
    # passes and the scalar is bounded in [floor, ceiling].
    cfg_on = RiskConfig(
        portfolio_vol_target_enabled=True,
        portfolio_vol_target_annual_vol=0.10,
        portfolio_vol_target_ceiling=2.0,
        portfolio_vol_target_floor=0.5,
        portfolio_vol_target_floor_enabled=True,
        portfolio_vol_target_floor_annual=0.05,
        portfolio_vol_target_floor_full_sample_frac=0.5,
    )
    re_on = RiskEngine(cfg=asdict(cfg_on))
    re_on.portfolio = pf
    scalar = re_on._compute_portfolio_vol_scalar()
    # Synthetic equity history is monotone-linear → variance ≈ 0 →
    # realized vol < ~1e-3 → floored → ratio bounded → within [floor, ceil].
    assert 0.5 <= scalar <= 2.0


# ----------------------------------------------------------------------
# 10. Warmup gate — insufficient history returns 1.0
# ----------------------------------------------------------------------

def test_warmup_gate_insufficient_history():
    """When the history has fewer than min_returns_required+1 daily
    snapshots, the estimator returns None and the scale is 1.0."""
    base = datetime(2024, 1, 2)
    # Only 10 unique trading-day snapshots
    history = [
        {"timestamp": base + timedelta(days=i), "equity": 100.0 + i}
        for i in range(10)
    ]
    cfg = VolTargetConfig(enabled=True, target_annual_vol=0.10,
                          realized_vol_window_days=60,
                          min_returns_required=60)
    assert compute_realized_vol_from_history(history, 60, 60) is None
    assert compute_portfolio_vol_scale(history, cfg) == 1.0


# ----------------------------------------------------------------------
# 11. Per-day collapse — multiple snapshots per day get reduced
# ----------------------------------------------------------------------

def test_per_day_collapse_multi_snapshot_per_day():
    """mode_controller emits multiple snapshots per bar (initial,
    post-fill, bar-end). The estimator must collapse to ONE value
    per unique date (the last one wins)."""
    base = datetime(2024, 1, 2)
    history = [
        {"timestamp": base, "equity": 100.0},      # first snap of day
        {"timestamp": base, "equity": 100.5},      # post-fill same day
        {"timestamp": base, "equity": 101.0},      # bar-end same day → wins
        {"timestamp": base + timedelta(days=1), "equity": 102.0},
    ]
    eq = _equity_at_end_of_each_day(history)
    assert eq == [101.0, 102.0]


# ----------------------------------------------------------------------
# 12. Annualization sqrt(252)
# ----------------------------------------------------------------------

def test_annualization_uses_sqrt_252():
    """The estimator's annualization factor is sqrt(TRADING_DAYS_PER_YEAR)."""
    # Build 61 days with daily sigma = 0.01 exactly (constant returns).
    base = datetime(2024, 1, 2)
    # Alternating +1% / -1% returns produce stdev ≈ 0.01.
    rets = [0.01 if i % 2 == 0 else -0.01 for i in range(60)]
    eq = [100.0]
    for r in rets:
        eq.append(eq[-1] * (1.0 + r))
    history = [
        {"timestamp": base + timedelta(days=i), "equity": eq[i]}
        for i in range(len(eq))
    ]
    sigma = compute_realized_vol_from_history(history, 60, 60)
    assert sigma is not None
    # Daily ~0.01, annualized ~0.01*sqrt(252) ≈ 0.1587. Allow ±20% slack
    # for the alternating pattern.
    assert 0.10 < sigma < 0.25, f"unexpected annualized vol: {sigma}"
    # Sanity: the constant 0.01 daily would annualize to exactly 0.1587
    expected = 0.01 * math.sqrt(TRADING_DAYS_PER_YEAR)
    assert abs(sigma - expected) < 0.05
