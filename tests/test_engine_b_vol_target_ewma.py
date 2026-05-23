"""T-2026-05-22-055d regression suite — EWMA estimator alternative
for Engine B portfolio-level vol-targeting.

Validates per the T-055d dispatch acceptance:

1. test_ewma_default_is_rolling                  — un-annotated cfg keeps rolling default
2. test_ewma_estimator_dispatcher                — cfg.estimator_type="ewma" routes to EWMA
3. test_ewma_known_input_matches_riskmetrics     — closed-form check against the standard recursion
4. test_ewma_responds_faster_than_rolling_on_vol_shock  — the acceptance-critical fixture
5. test_ewma_rejects_invalid_lambda              — λ ≤ 0 or ≥ 1 returns None (no-op safety)
6. test_ewma_passthrough_disabled                — cfg.enabled=False short-circuits
7. test_ewma_warmup_gate                         — insufficient history → None
8. test_ewma_determinism                         — bit-identical across repeat calls
9. test_ewma_no_lookahead                        — uses only history at call time
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

import numpy as np

from engines.engine_b_risk.vol_target import (
    TRADING_DAYS_PER_YEAR,
    VolTargetConfig,
    compute_portfolio_vol_scale,
    compute_realized_vol_from_history,
    compute_realized_vol_from_history_ewma,
    compute_vol_scale,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _build_history_from_returns(returns: np.ndarray,
                                start: datetime = datetime(2024, 1, 2),
                                initial_equity: float = 100.0) -> list[dict]:
    """Convert a daily-returns array into a portfolio.history-shaped
    snapshot list (one entry per trading day)."""
    eq = [initial_equity]
    for r in returns:
        eq.append(eq[-1] * (1.0 + float(r)))
    return [
        {"timestamp": start + timedelta(days=i), "equity": eq[i]}
        for i in range(len(eq))
    ]


# ----------------------------------------------------------------------
# 1. Default behavior preserved
# ----------------------------------------------------------------------

def test_ewma_default_is_rolling():
    """A VolTargetConfig with no estimator_type field set MUST default
    to "rolling" — preserves T-055 + T-055c on-main behavior."""
    cfg = VolTargetConfig(enabled=True)
    assert cfg.estimator_type == "rolling"
    assert cfg.ewma_lambda == 0.94  # RiskMetrics standard


# ----------------------------------------------------------------------
# 2. Dispatcher routes correctly
# ----------------------------------------------------------------------

def test_ewma_estimator_dispatcher():
    """When cfg.estimator_type='ewma', `compute_portfolio_vol_scale`
    must dispatch to `compute_realized_vol_from_history_ewma`, NOT
    the rolling version. Test by giving a history that the EWMA
    estimator would handle but the rolling would not — namely a
    history with EXACTLY 60 daily returns (rolling-60 requires 61
    equities for 60 returns; EWMA accepts the same minimum).
    Both estimators here produce non-None, but check they're DIFFERENT
    (EWMA weights recent returns more, so will differ from equal-weighted
    rolling stdev on non-stationary returns)."""
    rng = np.random.default_rng(seed=11)
    # Mix calm + spike segments → non-stationary → estimators differ.
    rets = np.concatenate([
        rng.normal(0.0, 0.005, 40),
        rng.normal(0.0, 0.020, 21),
    ])
    history = _build_history_from_returns(rets)
    cfg_rolling = VolTargetConfig(
        enabled=True, estimator_type="rolling",
        realized_vol_window_days=60, min_returns_required=60,
    )
    cfg_ewma = VolTargetConfig(
        enabled=True, estimator_type="ewma",
        realized_vol_window_days=60, min_returns_required=60,
        ewma_lambda=0.94,
    )
    s_rolling = compute_portfolio_vol_scale(history, cfg_rolling)
    s_ewma = compute_portfolio_vol_scale(history, cfg_ewma)
    # Both produce non-trivial scales (not the no-op 1.0 from missing data).
    assert 0.5 <= s_rolling <= 2.0
    assert 0.5 <= s_ewma <= 2.0
    # And the two MUST differ on this non-stationary input — if they
    # match, the dispatcher is not routing to the EWMA path.
    assert abs(s_rolling - s_ewma) > 0.01, (
        f"dispatcher not routing: rolling={s_rolling}, ewma={s_ewma}"
    )


# ----------------------------------------------------------------------
# 3. EWMA matches RiskMetrics closed-form
# ----------------------------------------------------------------------

def test_ewma_known_input_matches_riskmetrics():
    """Closed-form check: feed a 3-return sequence with known values,
    verify the EWMA variance recursion produces the expected number.

    σ²_t = λ · σ²_{t-1} + (1 - λ) · r²_t

    Initialization: σ²_0 = r²_0. With λ=0.94, returns r=[0.01, 0.02, 0.03]:
        σ²_0 = 0.01² = 1.0e-4
        σ²_1 = 0.94 · 1.0e-4 + 0.06 · (0.02)² = 9.4e-5 + 0.06·4e-4 = 9.4e-5 + 2.4e-5 = 1.18e-4
        σ²_2 = 0.94 · 1.18e-4 + 0.06 · (0.03)² = 1.1092e-4 + 5.4e-5 = 1.6492e-4
        σ_daily = sqrt(1.6492e-4) ≈ 0.01284
        annualized = 0.01284 · sqrt(252) ≈ 0.2038
    """
    # Build minimal history that produces EXACTLY these returns.
    # equity = [100, 101, 103.02, 106.1106] gives returns [0.01, 0.02, 0.03].
    history = [
        {"timestamp": datetime(2024, 1, 2), "equity": 100.0},
        {"timestamp": datetime(2024, 1, 3), "equity": 101.0},
        {"timestamp": datetime(2024, 1, 4), "equity": 103.02},
        {"timestamp": datetime(2024, 1, 5), "equity": 106.1106},
    ]
    # Use min_returns_required=3 so the 3-return series fires.
    sigma = compute_realized_vol_from_history_ewma(history, 0.94, 3)
    assert sigma is not None
    expected = math.sqrt(1.6492e-4) * math.sqrt(TRADING_DAYS_PER_YEAR)
    assert abs(sigma - expected) < 1e-3, (
        f"EWMA closed-form mismatch: got {sigma}, expected {expected}"
    )


# ----------------------------------------------------------------------
# 4. ACCEPTANCE-CRITICAL fixture — EWMA must respond faster on shock
# ----------------------------------------------------------------------

def test_ewma_responds_faster_than_rolling_on_vol_shock():
    """T-055d dispatch acceptance fixture (verbatim):

      "σ doubles at t=T/2, EWMA scale crosses 0.7 within 10 bars,
       rolling-60d does not"

    Construct a 200-day daily-return series. First 100 days at σ=0.005
    (annualized ≈ 7.9%, scalar ≈ ceiling). Next 100 days at σ=0.020
    (annualized ≈ 31.7%, scalar ≈ 0.10/0.317 ≈ 0.315 capped at floor).

    At t=110 (10 bars after shock):
      * EWMA scalar should be < 0.7 (faster response)
      * Rolling-60d scalar should be > 0.7 (window still 50/50 split,
        averaged realized vol still close to target → scalar near 1.0)
    """
    rng = np.random.default_rng(seed=42)
    pre_shock = rng.normal(0.0, 0.005, 100)
    post_shock = rng.normal(0.0, 0.020, 100)
    returns = np.concatenate([pre_shock, post_shock])
    history = _build_history_from_returns(returns)
    # history has 201 entries (initial + 200 daily updates). At index
    # 110 (10 bars after shock), we have returns 0..109 (110 returns).
    t_check = 110
    # min_returns_required=60 means both estimators need 60+ returns.
    # At t_check=110 we have plenty.
    history_at_t = history[: t_check + 1]  # equity values include initial
    cfg_rolling = VolTargetConfig(
        enabled=True, estimator_type="rolling", target_annual_vol=0.10,
        realized_vol_window_days=60, min_returns_required=60,
        leverage_floor=0.5, leverage_ceiling=2.0,
    )
    cfg_ewma = VolTargetConfig(
        enabled=True, estimator_type="ewma", target_annual_vol=0.10,
        ewma_lambda=0.94, min_returns_required=60,
        leverage_floor=0.5, leverage_ceiling=2.0,
    )
    s_rolling = compute_portfolio_vol_scale(history_at_t, cfg_rolling)
    s_ewma = compute_portfolio_vol_scale(history_at_t, cfg_ewma)
    # Diagnostic prints (visible with pytest -s) — leave for failure debug.
    print(f"\n  at t={t_check}: rolling_scale={s_rolling:.3f}, ewma_scale={s_ewma:.3f}")
    assert s_ewma < 0.7, (
        f"EWMA failed acceptance — scale {s_ewma:.3f} should be < 0.7 "
        f"(σ doubled 10 bars ago; faster response expected)"
    )
    assert s_rolling > 0.7, (
        f"rolling NOT failing acceptance as expected — scale "
        f"{s_rolling:.3f} should be > 0.7 (60d window still half-old)"
    )
    # The contrast: EWMA degrosses materially while rolling still
    # near target. This is the 2025 vol-shock failure mode T-055c saw.
    assert s_rolling > s_ewma + 0.20, (
        f"insufficient contrast: rolling={s_rolling:.3f} vs ewma={s_ewma:.3f}; "
        f"expected ≥ 0.20 gap to confirm faster EWMA response"
    )


# ----------------------------------------------------------------------
# 5. Invalid lambda safety
# ----------------------------------------------------------------------

def test_ewma_rejects_invalid_lambda():
    """λ outside (0, 1) is a degenerate estimator. The function must
    return None rather than emit garbage."""
    rng = np.random.default_rng(seed=3)
    history = _build_history_from_returns(rng.normal(0.0, 0.01, 100))
    for bad in (0.0, 1.0, -0.5, 1.5, float("nan")):
        result = compute_realized_vol_from_history_ewma(history, bad, 60)
        assert result is None, (
            f"λ={bad} should be rejected but got {result}"
        )


# ----------------------------------------------------------------------
# 6. Disabled passthrough
# ----------------------------------------------------------------------

def test_ewma_passthrough_disabled():
    """cfg.enabled=False short-circuits before estimator runs — no
    EWMA work. Result must be 1.0."""
    rng = np.random.default_rng(seed=5)
    history = _build_history_from_returns(rng.normal(0.0, 0.02, 100))
    cfg = VolTargetConfig(enabled=False, estimator_type="ewma")
    assert compute_portfolio_vol_scale(history, cfg) == 1.0


# ----------------------------------------------------------------------
# 7. Warmup gate
# ----------------------------------------------------------------------

def test_ewma_warmup_gate():
    """Fewer than min_returns_required+1 equity points → None →
    scalar=1.0 passthrough."""
    rng = np.random.default_rng(seed=7)
    history = _build_history_from_returns(rng.normal(0.0, 0.01, 10))
    assert compute_realized_vol_from_history_ewma(history, 0.94, 60) is None
    cfg = VolTargetConfig(enabled=True, estimator_type="ewma",
                          min_returns_required=60)
    assert compute_portfolio_vol_scale(history, cfg) == 1.0


# ----------------------------------------------------------------------
# 8. Determinism
# ----------------------------------------------------------------------

def test_ewma_determinism():
    """Repeated calls on the same history produce bit-identical results."""
    rng = np.random.default_rng(seed=99)
    history = _build_history_from_returns(rng.normal(0.0008, 0.012, 100))
    sigmas = [
        compute_realized_vol_from_history_ewma(history, 0.94, 60)
        for _ in range(10)
    ]
    first = sigmas[0]
    assert first is not None
    for s in sigmas[1:]:
        assert s == first, f"non-deterministic EWMA: {sigmas}"


# ----------------------------------------------------------------------
# 9. No look-ahead
# ----------------------------------------------------------------------

def test_ewma_no_lookahead():
    """Result computed at history[:t] must equal the result computed
    later from the same history[:t] — even if `history` has grown
    beyond t in the interim. Concretely: append a future outlier and
    re-compute on the ORIGINAL slice; results must match."""
    rng = np.random.default_rng(seed=13)
    history = _build_history_from_returns(rng.normal(0.0, 0.01, 100))
    sigma_first = compute_realized_vol_from_history_ewma(history, 0.94, 60)
    # Add an extreme future point to the same list (mutation simulating
    # the next bar landing in history). Re-compute on a SLICED copy
    # representing the original moment.
    extended = list(history) + [{
        "timestamp": history[-1]["timestamp"] + timedelta(days=1),
        "equity": history[-1]["equity"] * 2.0,  # 100% one-day return
    }]
    # Slice to the original length → should match sigma_first.
    sigma_resliced = compute_realized_vol_from_history_ewma(
        extended[: len(history)], 0.94, 60,
    )
    assert sigma_resliced == sigma_first, (
        f"look-ahead leak: original {sigma_first}, resliced {sigma_resliced}"
    )
    # And the EXTENDED history (including the outlier) MUST produce
    # a different (larger) sigma — confirms the estimator IS sensitive
    # to the new data when it is present.
    sigma_extended = compute_realized_vol_from_history_ewma(
        extended, 0.94, 60,
    )
    assert sigma_extended != sigma_first, (
        "extending with outlier should perturb sigma — confirms "
        "estimator consumes the latest data when available"
    )
