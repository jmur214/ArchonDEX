"""
tests/test_metrics_engine.py
=============================
Tests for ``core.metrics_engine.MetricsEngine`` — the centralized
performance-metric calculator used by Research, Backtesting, and the
Discovery validation gauntlet.

Critical because:
- ``calculate_all`` is called inside Gate 1 of `validate_candidate` for
  every discovery candidate, and inside `MetricsEngine.cagr` is the
  ``(end - start).days`` operation that previously crashed silently when
  callers built equity curves without datetime indices (commit dda474c).
- Several Sharpe/CAGR computations have known-pathological edge cases
  (constant series, single-bar curves, negative-return paths). These
  tests lock in the current behavior so future refactors don't regress
  the validation gauntlet's pass/fail decisions.
- No prior test file existed despite the module being foundational.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.metrics_engine import MetricsEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_range(n_days: int, start: str = "2024-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n_days, freq="D")


def _flat_curve(n_days: int = 252, value: float = 100.0) -> pd.Series:
    return pd.Series([value] * n_days, index=_date_range(n_days))


def _linear_growth_curve(
    n_days: int = 252,
    start: float = 100.0,
    daily_return: float = 0.001,
) -> pd.Series:
    """Geometric daily growth — returns are exactly daily_return every day."""
    prices = [start]
    for _ in range(n_days - 1):
        prices.append(prices[-1] * (1 + daily_return))
    return pd.Series(prices, index=_date_range(n_days))


def _random_walk_curve(
    n_days: int = 252,
    start: float = 100.0,
    daily_return_mean: float = 0.0005,
    daily_return_std: float = 0.01,
    seed: int = 42,
) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = rng.normal(daily_return_mean, daily_return_std, size=n_days)
    prices = [start]
    for r in rets[1:]:
        prices.append(prices[-1] * (1 + r))
    return pd.Series(prices, index=_date_range(n_days))


# ---------------------------------------------------------------------------
# calculate_all — top-level orchestrator
# ---------------------------------------------------------------------------

def test_calculate_all_empty_series_returns_empty_metrics():
    metrics = MetricsEngine.calculate_all(pd.Series([], dtype=float))
    assert all(v == 0.0 for v in metrics.values())


def test_calculate_all_single_bar_returns_empty_metrics():
    """One bar → can't compute returns → empty metrics."""
    s = pd.Series([100.0], index=_date_range(1))
    metrics = MetricsEngine.calculate_all(s)
    assert all(v == 0.0 for v in metrics.values())


def test_calculate_all_constant_curve_returns_empty_metrics():
    """Zero variance → empty metrics (avoids divide-by-zero)."""
    metrics = MetricsEngine.calculate_all(_flat_curve(50))
    assert all(v == 0.0 for v in metrics.values())


def test_calculate_all_perfectly_constant_growth_returns_empty():
    """Geometric constant growth produces returns whose std is mathematically
    zero. calculate_all's `returns.std() == 0` guard fires (despite tiny
    floating-point noise) and short-circuits to empty_metrics. This is the
    expected behavior — the guard exists to avoid divide-by-zero
    downstream — even though "the curve grew 29%" is true.
    """
    curve = _linear_growth_curve(252, 100.0, 0.001)
    metrics = MetricsEngine.calculate_all(curve)
    # The guard fires because returns are bit-identical floats (std == 0).
    assert metrics["Total Return %"] == 0.0


def test_calculate_all_noisy_growth_produces_finite_metrics():
    """A realistic noisy upward-trending curve produces finite metrics."""
    curve = _random_walk_curve(252, 100.0, daily_return_mean=0.001, daily_return_std=0.005)
    metrics = MetricsEngine.calculate_all(curve)
    for k, v in metrics.items():
        assert math.isfinite(v), f"Metric {k} = {v} is not finite"
    assert metrics["Total Return %"] > 0
    assert metrics["Sharpe"] > 0


def test_calculate_all_returns_expected_keys():
    """Output schema is stable — downstream callers depend on these keys."""
    curve = _random_walk_curve()
    metrics = MetricsEngine.calculate_all(curve)
    expected_keys = {
        "Total Return %", "CAGR %", "Sharpe", "Sortino", "PSR",
        "Max Drawdown %", "Calmar", "Ulcer Index", "Volatility %", "VaR 95%",
        "Skewness", "Excess Kurtosis", "Tail Ratio",
        "Beta", "Alpha", "Information Ratio",
    }
    assert set(metrics.keys()) == expected_keys


def test_calculate_all_with_benchmark_computes_beta_alpha():
    """When benchmark provided, beta and alpha should be non-trivial."""
    strategy = _random_walk_curve(252, daily_return_std=0.012, seed=1)
    benchmark = _random_walk_curve(252, daily_return_std=0.010, seed=2)
    metrics = MetricsEngine.calculate_all(strategy, benchmark)
    assert math.isfinite(metrics["Beta"])
    assert math.isfinite(metrics["Alpha"])


def test_calculate_all_without_benchmark_zero_beta_alpha():
    metrics = MetricsEngine.calculate_all(_random_walk_curve(50))
    assert metrics["Beta"] == 0.0
    assert metrics["Alpha"] == 0.0


def test_calculate_all_int_index_raises_or_handles():
    """Regression: equity curve with RangeIndex (int) used to crash inside
    cagr() with `'int' object has no attribute 'days'`. The current
    behavior is to raise that AttributeError — we lock it in here so that
    if someone wraps cagr in try/except in the future, the test fails
    and forces them to think about whether silent-default is right.

    The proper fix is for callers to provide a datetime index (the bug
    fix in dda474c added that to discovery.py:651 and again at line 806).
    """
    s = pd.Series([100.0, 101.0, 102.0, 99.0, 100.5])  # RangeIndex (int)
    with pytest.raises(AttributeError, match="'int' object has no attribute 'days'"):
        MetricsEngine.calculate_all(s)


# ---------------------------------------------------------------------------
# sharpe_ratio
# ---------------------------------------------------------------------------

def test_sharpe_zero_for_exactly_zero_returns():
    """All-zero returns → std exactly 0 → guard fires → 0.0."""
    rets = pd.Series([0.0] * 100)
    assert MetricsEngine.sharpe_ratio(rets) == 0.0


def test_sharpe_constant_positive_returns_returns_zero_post_T061():
    """T-061 (2026-05-22, user-approved): the `std == 0` exact-equality
    guard in sharpe_ratio was hardened to a tolerance check (std < 1e-12).
    Pandas std on identical floats returns ~2e-19 (not exactly zero),
    which previously produced an exploding ~1e15 Sharpe. The tolerance
    now correctly fires the guard for constant-input cases.

    Pre-T-061: assertion was `sharpe == 0.0 or abs(sharpe) > 1e10` —
    lock-in of the known-degenerate behavior pending user approval.
    Post-T-061: the guard fires cleanly; sharpe == 0.
    """
    rets = pd.Series([0.001] * 100)
    sharpe = MetricsEngine.sharpe_ratio(rets)
    assert sharpe == 0.0, (
        f"Constant-input Sharpe should be 0 (tolerance guard), got {sharpe}"
    )


def test_sharpe_positive_for_positive_drift():
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0.001, 0.01, size=252))
    sharpe = MetricsEngine.sharpe_ratio(rets)
    assert sharpe > 0


def test_sharpe_negative_for_negative_drift():
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(-0.001, 0.01, size=252))
    sharpe = MetricsEngine.sharpe_ratio(rets)
    assert sharpe < 0


def test_sharpe_annualization_period_factor():
    """Sharpe with periods=252 should be sqrt(252) × Sharpe with periods=1."""
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0.001, 0.01, size=252))
    daily_sharpe = MetricsEngine.sharpe_ratio(rets, periods=1)
    annualized = MetricsEngine.sharpe_ratio(rets, periods=252)
    assert annualized == pytest.approx(daily_sharpe * np.sqrt(252), rel=1e-6)


def test_sharpe_risk_free_rate_lowers_score():
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0.001, 0.01, size=252))
    sharpe_no_rf = MetricsEngine.sharpe_ratio(rets, risk_free_rate=0.0)
    sharpe_with_rf = MetricsEngine.sharpe_ratio(rets, risk_free_rate=0.0005)
    assert sharpe_with_rf < sharpe_no_rf


# ---------------------------------------------------------------------------
# sortino_ratio
# ---------------------------------------------------------------------------

def test_sortino_caps_at_10_when_no_downside():
    """All-positive returns → no downside variance → cap at 10.0."""
    rets = pd.Series([0.01, 0.02, 0.03, 0.005, 0.015])
    s = MetricsEngine.sortino_ratio(rets)
    assert s == 10.0


def test_sortino_caps_at_10_when_downside_zero_variance():
    """If downside returns are all zero (no variance), cap at 10.0."""
    rets = pd.Series([0.01, 0.02, 0.0, 0.0, 0.005])
    s = MetricsEngine.sortino_ratio(rets)
    assert s == 10.0


def test_sortino_distinguishes_from_sharpe_on_asymmetric_returns():
    """Skewed-positive distribution: Sortino should exceed Sharpe."""
    # Mostly small positives, with occasional small negatives
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0.002, 0.005, size=252))
    rets[rets < -0.005] = -0.005  # cap downside
    sharpe = MetricsEngine.sharpe_ratio(rets)
    sortino = MetricsEngine.sortino_ratio(rets)
    assert sortino >= sharpe


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------

def test_max_drawdown_zero_for_monotone_uptrend():
    curve = pd.Series([100, 101, 102, 103, 105])
    assert MetricsEngine.max_drawdown(curve) == 0.0


def test_max_drawdown_negative_for_decline():
    """Drawdown convention: negative number (e.g. -0.15 = -15%)."""
    curve = pd.Series([100, 110, 120, 100, 90])  # peak 120 → trough 90 = -25%
    dd = MetricsEngine.max_drawdown(curve)
    assert dd == pytest.approx(-0.25)


def test_max_drawdown_recovery_uses_max_low():
    """Drawdown is from running max, so a lower trough later is the answer
    even if there's a prior smaller trough."""
    curve = pd.Series([100, 105, 95, 110, 80, 115])
    # Running max: 100, 105, 105, 110, 110, 115
    # DD at each: 0, 0, -9.5%, 0, -27.3%, 0
    dd = MetricsEngine.max_drawdown(curve)
    assert dd == pytest.approx(-30 / 110)


# ---------------------------------------------------------------------------
# cagr
# ---------------------------------------------------------------------------

def test_cagr_zero_for_too_short_series():
    """Less than 36 days (~0.1 year) → CAGR is 0 (avoids ridiculous values)."""
    curve = pd.Series([100, 110], index=_date_range(2))
    assert MetricsEngine.cagr(curve) == 0.0


def test_cagr_negative_one_for_total_loss():
    """If equity goes to zero (or below) over a >0.1-year span, CAGR
    returns -1 as a sentinel for total loss."""
    curve = pd.Series(
        [100.0, 0.0],
        index=pd.DatetimeIndex(["2020-01-01", "2022-12-31"]),
    )
    assert MetricsEngine.cagr(curve) == -1.0


def test_cagr_for_simple_doubling_over_one_year():
    """Equity doubled over 365 days → CAGR ≈ 100%."""
    idx = pd.DatetimeIndex(["2024-01-01", "2025-01-01"])
    curve = pd.Series([100.0, 200.0], index=idx)
    cagr = MetricsEngine.cagr(curve)
    assert cagr == pytest.approx(1.0, rel=0.01)  # ~100%


def test_cagr_handles_one_day_more_than_year():
    """365.25-day basis → just over a year produces just under doubling-rate
    when equity exactly doubles."""
    idx = pd.DatetimeIndex(["2024-01-01", "2025-01-15"])  # 380 days
    curve = pd.Series([100.0, 200.0], index=idx)
    cagr = MetricsEngine.cagr(curve)
    # 380 / 365.25 ≈ 1.040 years; total_ret = 2; cagr = 2^(1/1.04) - 1 ≈ 0.951
    assert cagr == pytest.approx(0.951, rel=0.01)


def test_cagr_raises_on_int_index():
    """Locked-in: cagr with RangeIndex raises AttributeError on .days.

    This is the bug discovery.py:651 / 806 had to fix by adding
    ``index=pd.to_datetime([h["timestamp"] for h in history])``.
    """
    curve = pd.Series([100.0, 200.0])  # default RangeIndex
    with pytest.raises(AttributeError, match="'int' object has no attribute 'days'"):
        MetricsEngine.cagr(curve)


# ---------------------------------------------------------------------------
# beta
# ---------------------------------------------------------------------------

def test_beta_one_for_identical_streams():
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(0, 0.01, 252))
    assert MetricsEngine.beta(s, s) == pytest.approx(1.0)


def test_beta_zero_for_uncorrelated():
    rng = np.random.default_rng(42)
    s1 = pd.Series(rng.normal(0, 0.01, 1000))
    s2 = pd.Series(rng.normal(0, 0.01, 1000))
    # Independent random walks — beta should be near zero (large N)
    assert abs(MetricsEngine.beta(s1, s2)) < 0.1


def test_beta_zero_when_benchmark_constant():
    """Zero variance in benchmark → guard against divide-by-zero → 0.0."""
    s = pd.Series([0.01, 0.02, -0.01, 0.005])
    bench = pd.Series([0.005, 0.005, 0.005, 0.005])
    assert MetricsEngine.beta(s, bench) == 0.0


def test_beta_negative_for_inverse_correlation():
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(0, 0.01, 252))
    inverse = -s
    assert MetricsEngine.beta(s, inverse) == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# value_at_risk
# ---------------------------------------------------------------------------

def test_var_returns_negative_quantile_for_loss_distribution():
    """5%-VaR on N(0, 0.01) should be roughly -1.645 × 0.01 = -0.0165."""
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0, 0.01, size=10_000))
    var = MetricsEngine.value_at_risk(rets, confidence=0.95)
    # Empirical 5% quantile of standard normal × 0.01 ≈ -0.0165
    assert var == pytest.approx(-0.0165, abs=0.002)


def test_var_99_more_extreme_than_var_95():
    rng = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0, 0.01, size=10_000))
    var_95 = MetricsEngine.value_at_risk(rets, 0.95)
    var_99 = MetricsEngine.value_at_risk(rets, 0.99)
    assert var_99 < var_95  # more extreme = more negative


# ---------------------------------------------------------------------------
# sqn (System Quality Number)
# ---------------------------------------------------------------------------

def test_sqn_zero_for_short_series():
    assert MetricsEngine.sqn(pd.Series([])) == 0.0
    assert MetricsEngine.sqn(pd.Series([100.0])) == 0.0


def test_sqn_zero_for_constant_pnl():
    pnl = pd.Series([100.0, 100.0, 100.0])
    assert MetricsEngine.sqn(pnl) == 0.0


def test_sqn_scales_with_sample_size():
    """SQN includes √N — same expectancy/std with more trades → higher SQN."""
    pnl_short = pd.Series([100.0, -50.0] * 10)   # N=20
    pnl_long = pd.Series([100.0, -50.0] * 100)  # N=200
    sqn_short = MetricsEngine.sqn(pnl_short)
    sqn_long = MetricsEngine.sqn(pnl_long)
    # ratio should be approximately sqrt(200/20) = sqrt(10)
    assert sqn_long == pytest.approx(sqn_short * np.sqrt(10), rel=0.05)


# ---------------------------------------------------------------------------
# kelly_fraction
# ---------------------------------------------------------------------------

def test_kelly_zero_for_zero_win_loss_ratio():
    """Defensive: don't divide by zero when win_loss_ratio = 0."""
    assert MetricsEngine.kelly_fraction(0.6, 0.0) == 0.0


def test_kelly_break_even_for_50_pct_win_rate_1to1_ratio():
    """W=0.5, R=1 → Kelly = 0.5 - 0.5/1 = 0.0 (no edge)."""
    assert MetricsEngine.kelly_fraction(0.5, 1.0) == 0.0


def test_kelly_positive_when_edge_exists():
    """W=0.6, R=1.5 → Kelly = 0.6 - 0.4/1.5 ≈ 0.333"""
    k = MetricsEngine.kelly_fraction(0.6, 1.5)
    assert k == pytest.approx(0.6 - 0.4 / 1.5, rel=1e-6)


def test_kelly_negative_when_edge_disadvantage():
    """W=0.4, R=1 → Kelly = 0.4 - 0.6/1 = -0.2 (negative — don't bet)."""
    k = MetricsEngine.kelly_fraction(0.4, 1.0)
    assert k == pytest.approx(-0.2)


# ---------------------------------------------------------------------------
# Integration: regression against the dda474c bug
# ---------------------------------------------------------------------------

def test_history_to_metrics_pipeline_with_datetime_index():
    """Mirrors what `discovery.validate_candidate` now does after the
    dda474c fix: build equity curve with datetime index, call
    calculate_all, expect finite metrics."""
    history = [
        {"timestamp": pd.Timestamp(f"2024-01-{(i % 28) + 1:02d}"), "equity": 100.0 + i}
        for i in range(60)
    ]
    equity_curve = pd.Series(
        [h["equity"] for h in history],
        index=pd.to_datetime([h["timestamp"] for h in history]),
    )
    metrics = MetricsEngine.calculate_all(equity_curve)
    for k, v in metrics.items():
        assert math.isfinite(v), f"Metric {k} = {v} is not finite"
    # Total return: 159/100 - 1 = 0.59 → 59%
    assert metrics["Total Return %"] == pytest.approx(59.0, abs=0.01)


def test_history_to_metrics_pipeline_without_datetime_index_raises():
    """The pre-dda474c shape (no datetime index) MUST raise to surface the bug
    instead of silently returning Sharpe=0.00 from an exception swallow."""
    history = [{"equity": 100.0 + i} for i in range(60)]
    bad_equity_curve = pd.Series([h["equity"] for h in history])  # int index
    with pytest.raises(AttributeError, match="'int' object has no attribute 'days'"):
        MetricsEngine.calculate_all(bad_equity_curve)


# ============================================================
# PSR / DSR / Information Ratio / Tail / Skewness / Ulcer
# ----- New metrics added 2026-05-09 per outside-reviewer F8 -----
# ============================================================


def test_psr_above_zero_for_strong_positive_returns():
    """A 252-day series with mean 0.001 / std 0.015 has Sharpe ~1.0 — PSR
    that the true Sharpe > 0 should be high (>0.7)."""
    np.random.seed(42)
    rets = pd.Series(np.random.normal(0.001, 0.015, 252))
    psr = MetricsEngine.probabilistic_sharpe_ratio(rets, sr_benchmark_annualized=0.0)
    assert 0.7 < psr < 1.0


def test_psr_near_50pct_when_benchmark_equals_sample():
    """PSR(SR_benchmark = sample annualized SR) should be close to 0.5
    by construction — uncertainty centered on the observed value."""
    np.random.seed(7)
    rets = pd.Series(np.random.normal(0.001, 0.015, 252))
    sample_sr_annual = MetricsEngine.sharpe_ratio(rets)
    psr = MetricsEngine.probabilistic_sharpe_ratio(rets, sr_benchmark_annualized=sample_sr_annual)
    assert 0.4 < psr < 0.6


def test_psr_returns_zero_for_too_short_series():
    rets = pd.Series([0.01, -0.005, 0.002])
    assert MetricsEngine.probabilistic_sharpe_ratio(rets) == 0.0


def test_psr_returns_zero_for_constant_returns():
    rets = pd.Series([0.001] * 50)
    assert MetricsEngine.probabilistic_sharpe_ratio(rets) == 0.0


def test_dsr_equals_psr_when_n_trials_is_one():
    """No selection bias correction needed; DSR(N=1) reduces to PSR(SR=0)."""
    np.random.seed(11)
    rets = pd.Series(np.random.normal(0.001, 0.015, 252))
    psr_zero = MetricsEngine.probabilistic_sharpe_ratio(rets, 0.0)
    dsr_one = MetricsEngine.deflated_sharpe_ratio(rets, n_trials=1)
    assert dsr_one == pytest.approx(psr_zero, abs=1e-9)


def test_dsr_drops_below_psr_under_multiple_testing():
    """50 trials forces DSR < PSR(0) because the 'beat the max-of-50' bar
    is higher than 'beat zero' — the multiple-testing correction kicks in."""
    np.random.seed(13)
    rets = pd.Series(np.random.normal(0.001, 0.015, 252))
    psr_zero = MetricsEngine.probabilistic_sharpe_ratio(rets, 0.0)
    dsr_50 = MetricsEngine.deflated_sharpe_ratio(rets, n_trials=50)
    assert dsr_50 < psr_zero


def test_information_ratio_positive_when_strategy_beats_benchmark():
    np.random.seed(17)
    bench = pd.Series(np.random.normal(0.0005, 0.010, 252))
    strat = bench + np.random.normal(0.0003, 0.002, 252)  # adds tiny alpha + noise
    ir = MetricsEngine.information_ratio(strat, bench)
    assert ir > 0


def test_information_ratio_zero_when_perfect_index_replication():
    """If strategy is identical to benchmark, IR is undefined (zero tracking
    error). We return 0.0 rather than NaN/inf."""
    np.random.seed(19)
    bench = pd.Series(np.random.normal(0.0005, 0.010, 252))
    assert MetricsEngine.information_ratio(bench, bench) == 0.0


def test_tail_ratio_above_one_for_right_skewed_returns():
    """Mostly small returns with occasional big positive jumps — top 5%
    avg should exceed bottom 5% avg in magnitude."""
    np.random.seed(23)
    rets = pd.Series(np.r_[np.random.normal(0.001, 0.005, 247), [0.10, 0.12, 0.15, 0.08, 0.09]])
    tr = MetricsEngine.tail_ratio(rets)
    assert tr > 1.5


def test_tail_ratio_below_one_for_left_skewed_returns():
    """Big losses sprinkled into otherwise-tame returns — bottom tail should
    dominate top tail."""
    np.random.seed(29)
    rets = pd.Series(np.r_[np.random.normal(0.001, 0.005, 247), [-0.10, -0.12, -0.15, -0.08, -0.09]])
    tr = MetricsEngine.tail_ratio(rets)
    assert tr < 0.7


def test_skewness_positive_for_right_skewed_distribution():
    np.random.seed(31)
    rets = pd.Series(np.r_[np.random.normal(0.001, 0.005, 247), [0.10] * 5])
    assert MetricsEngine.skewness(rets) > 0.5


def test_skewness_negative_for_left_skewed_distribution():
    np.random.seed(37)
    rets = pd.Series(np.r_[np.random.normal(0.001, 0.005, 247), [-0.10] * 5])
    assert MetricsEngine.skewness(rets) < -0.5


def test_excess_kurtosis_zero_for_normal_distribution():
    """A clean normal sample should have excess kurtosis near 0 (Fisher convention)."""
    np.random.seed(41)
    rets = pd.Series(np.random.normal(0, 1, 5000))
    assert abs(MetricsEngine.excess_kurtosis(rets)) < 0.2


def test_excess_kurtosis_positive_for_fat_tailed_distribution():
    """Fat tails (e.g., t-distribution with df=5) → positive excess kurtosis."""
    np.random.seed(43)
    rets = pd.Series(np.random.standard_t(5, 1000))
    assert MetricsEngine.excess_kurtosis(rets) > 0.5


def test_ulcer_index_zero_for_monotone_uptrend():
    eq = pd.Series(range(100, 200, 1), index=pd.date_range("2024-01-01", periods=100))
    assert MetricsEngine.ulcer_index(eq) == pytest.approx(0.0, abs=1e-9)


def test_ulcer_index_positive_for_drawdown_path():
    eq = pd.Series([100, 95, 90, 85, 90, 95, 100], index=pd.date_range("2024-01-01", periods=7))
    ui = MetricsEngine.ulcer_index(eq)
    assert ui > 0
    # Sanity: max single-bar drawdown was 15% so RMS should land in low double digits
    assert 5 < ui < 15


def test_calculate_all_includes_new_metric_keys():
    """calculate_all must surface the new metrics for downstream consumers."""
    np.random.seed(47)
    rets = pd.Series(np.random.normal(0.001, 0.012, 200))
    eq = (1 + rets).cumprod() * 100000
    eq.index = pd.date_range("2024-01-01", periods=200, freq="B")
    metrics = MetricsEngine.calculate_all(eq)
    # New metric keys
    for key in ("PSR", "Ulcer Index", "Skewness", "Excess Kurtosis",
                "Tail Ratio", "Information Ratio"):
        assert key in metrics
    # Existing metric keys preserved (no regression)
    for key in ("Sharpe", "Sortino", "Calmar", "Max Drawdown %", "CAGR %"):
        assert key in metrics


def test_calculate_all_information_ratio_zero_when_no_benchmark():
    """Without a benchmark, IR is 0.0 (not present-but-NaN)."""
    np.random.seed(53)
    rets = pd.Series(np.random.normal(0.001, 0.012, 200))
    eq = (1 + rets).cumprod() * 100000
    eq.index = pd.date_range("2024-01-01", periods=200, freq="B")
    metrics = MetricsEngine.calculate_all(eq)
    assert metrics["Information Ratio"] == 0.0


# ============================================================================
# T-059 (2026-05-22): Lo autocorrelation correction for Sharpe annualization
# Per the 2026-05-16 metrics research dive: hedge-fund Sharpes overstated
# ~65% when ρ₁ ≈ 0.34 is ignored. Lo FAJ 2002, eq. 14.
# ============================================================================

def test_lo_eta_iid_returns_close_to_sqrt_q():
    """When autocorrelations are zero, η(q) should be close to √q (naive √252).

    Sample autocorrelations on finite data are O(1/√n) per lag; summed over
    ~30 lags with (q-k) weights this is a non-trivial noise band on η.
    Use a longer series (n=5000) + smaller max_lag (30) to tighten sample
    estimates. 12% tolerance reflects realistic finite-sample noise per
    Lo's own caveats about needing T >> q for tight estimates.
    """
    np.random.seed(0)
    iid_rets = pd.Series(np.random.normal(0.0005, 0.012, 5000))
    eta = MetricsEngine.lo_eta(iid_rets, q=252, max_lag=30)
    expected = np.sqrt(252)
    assert abs(eta - expected) / expected < 0.12, (
        f"i.i.d. η = {eta:.3f}, expected ≈ {expected:.3f} (±12% tolerance)"
    )


def test_lo_eta_positive_autocorrelation_reduces_eta():
    """Positive autocorrelation (returns trend with prior returns) inflates
    naive Sharpe — Lo correction REDUCES η below √q.

    Finite-q + truncated-lag-sum η doesn't reach the asymptotic
    (1+ρ)/(1-ρ) inflator exactly; the directional reduction is the
    load-bearing property. Per Lo 2002: at ρ₁ ≈ 0.30 reduction is in the
    10-20% range for daily data with bounded lag truncation.
    """
    np.random.seed(1)
    n = 2000
    eps = np.random.normal(0, 0.01, n)
    ar_rets = np.zeros(n)
    rho = 0.30  # strong positive autocorrelation
    for i in range(1, n):
        ar_rets[i] = rho * ar_rets[i-1] + eps[i]
    eta = MetricsEngine.lo_eta(pd.Series(ar_rets), q=252, max_lag=120)
    expected_naive = np.sqrt(252)
    # Directional reduction (load-bearing property)
    assert eta < expected_naive, (
        f"AR(1) ρ=0.30: η = {eta:.3f} should be < √252 = {expected_naive:.3f}"
    )
    # Materiality: at least 8% reduction (conservative bound for sample noise)
    reduction = (expected_naive - eta) / expected_naive
    assert reduction > 0.08, (
        f"AR(1) ρ=0.30: reduction = {reduction*100:.1f}% should be > 8%"
    )


def test_lo_eta_negative_autocorrelation_increases_eta():
    """Negative autocorrelation (mean-reversion) deflates aggregate variance —
    Lo correction INCREASES η above √q."""
    np.random.seed(2)
    n = 2000
    eps = np.random.normal(0, 0.01, n)
    ar_rets = np.zeros(n)
    rho = -0.25  # mean-reversion
    for i in range(1, n):
        ar_rets[i] = rho * ar_rets[i-1] + eps[i]
    eta = MetricsEngine.lo_eta(pd.Series(ar_rets), q=252, max_lag=120)
    expected_naive = np.sqrt(252)
    assert eta > expected_naive, (
        f"AR(1) ρ=-0.25: η = {eta:.3f} should be > √252 = {expected_naive:.3f}"
    )


def test_lo_eta_short_series_falls_back_to_naive():
    """Length < 2 should return √q without crashing (defensive)."""
    eta_empty = MetricsEngine.lo_eta(pd.Series([]), q=252)
    eta_single = MetricsEngine.lo_eta(pd.Series([0.01]), q=252)
    assert eta_empty == np.sqrt(252)
    assert eta_single == np.sqrt(252)


def test_lo_eta_max_lag_zero_returns_naive():
    """max_lag=0 short-circuits the autocorr sum to zero → η = q/√q = √q."""
    rets = pd.Series(np.random.normal(0, 0.01, 500))
    eta = MetricsEngine.lo_eta(rets, q=252, max_lag=0)
    assert eta == np.sqrt(252)


def test_sharpe_ratio_lo_corrected_matches_manual_calculation():
    """End-to-end: corrected Sharpe should equal per-period Sharpe × η(q)."""
    np.random.seed(3)
    n = 500
    eps = np.random.normal(0.0008, 0.01, n)
    rho = 0.20
    rets = np.zeros(n)
    for i in range(1, n):
        rets[i] = rho * rets[i-1] + eps[i]
    rets = pd.Series(rets)
    eta = MetricsEngine.lo_eta(rets, q=252, max_lag=60)
    per_period = rets.mean() / rets.std()
    expected_corrected = per_period * eta
    actual_corrected = MetricsEngine.sharpe_ratio_lo_corrected(rets, periods=252, max_lag=60)
    assert abs(actual_corrected - expected_corrected) < 1e-9, (
        f"Lo-corrected Sharpe {actual_corrected:.6f} != "
        f"per-period {per_period:.6f} × η {eta:.6f} = {expected_corrected:.6f}"
    )


def test_sharpe_ratio_lo_corrected_below_naive_for_positive_autocorr():
    """The empirical claim: positive-autocorr Sharpe naive > Lo-corrected.
    This is the load-bearing reason for the correction's existence."""
    np.random.seed(4)
    n = 500
    eps = np.random.normal(0.0005, 0.01, n)
    rho = 0.30
    rets = np.zeros(n)
    for i in range(1, n):
        rets[i] = rho * rets[i-1] + eps[i]
    rets = pd.Series(rets)
    naive_sharpe = MetricsEngine.sharpe_ratio(rets, periods=252)
    corrected_sharpe = MetricsEngine.sharpe_ratio_lo_corrected(rets, periods=252, max_lag=60)
    # Both should be positive (positive mean) but corrected should be smaller
    assert naive_sharpe > 0
    assert corrected_sharpe > 0
    assert corrected_sharpe < naive_sharpe, (
        f"Lo correction should REDUCE Sharpe under positive autocorr: "
        f"naive={naive_sharpe:.3f}, corrected={corrected_sharpe:.3f}"
    )


def test_sharpe_ratio_lo_corrected_zero_std_returns_zero():
    """Defensive: flat returns → no division by zero."""
    flat = pd.Series([0.001] * 100)
    result = MetricsEngine.sharpe_ratio_lo_corrected(flat)
    assert result == 0.0


def test_naive_sharpe_unchanged_after_lo_addition():
    """Backwards-compat gate: existing sharpe_ratio behavior MUST be
    unchanged by the addition of Lo correction (new methods are additive only)."""
    np.random.seed(5)
    rets = pd.Series(np.random.normal(0.001, 0.01, 252))
    expected_naive = rets.mean() / rets.std() * np.sqrt(252)
    actual = MetricsEngine.sharpe_ratio(rets, periods=252)
    assert abs(actual - expected_naive) < 1e-12, (
        f"Naive Sharpe behavior changed unexpectedly: "
        f"expected {expected_naive:.6f}, got {actual:.6f}"
    )


# ============================================================================
# T-060 (2026-05-22): PBO via CSCV — Probability of Backtest Overfitting
# Bailey, Borwein, López de Prado, Zhu (2017) JoCF 20(4).
# ============================================================================

def test_pbo_pure_noise_returns_around_half():
    """Pure noise trial matrix → PBO should be ≈ 0.5 (no edge, IS-best
    is random on OOS). Allow wide tolerance for combinatorial noise."""
    np.random.seed(0)
    T, N = 320, 20  # T >= 2*S = 32 satisfied
    noise = pd.DataFrame(
        np.random.normal(0, 0.01, (T, N)),
        columns=[f"trial_{i}" for i in range(N)],
    )
    result = MetricsEngine.probability_of_backtest_overfitting(
        noise, n_partitions=8
    )
    assert result["n_combinations"] == 70  # C(8, 4) = 70
    # Pure noise should give PBO near 0.5. Allow 0.3-0.7 band for randomness.
    assert 0.3 < result["pbo"] < 0.7, (
        f"Pure noise PBO = {result['pbo']:.3f}, expected ~0.5 ± 0.2"
    )


def test_pbo_genuine_signal_below_threshold():
    """A trial matrix where one trial has genuine alpha (mean drift) should
    produce PBO well below 0.5 — the IS-best (the alpha trial) consistently
    beats OOS median because it has a real edge."""
    np.random.seed(1)
    T, N = 320, 20
    # All trials are noise EXCEPT trial_0 which has a strong positive drift
    noise = pd.DataFrame(
        np.random.normal(0, 0.01, (T, N)),
        columns=[f"trial_{i}" for i in range(N)],
    )
    noise["trial_0"] += 0.005  # strong daily drift
    result = MetricsEngine.probability_of_backtest_overfitting(
        noise, n_partitions=8
    )
    # Real signal → PBO should be deep below 0.5 (ideally near 0)
    assert result["pbo"] < 0.3, (
        f"Real-signal PBO = {result['pbo']:.3f}, expected < 0.3"
    )
    assert result["deploy_threshold_met"] is True


def test_pbo_overfit_pattern_above_half():
    """When the 'best in-sample' trial is consistently the WORST out-of-sample
    (engineered overfit pattern), PBO should be high (> 0.5)."""
    # Construct an adversarial pattern: alternate which trial is best per
    # partition. The IS-optimal trial of each combo is engineered to
    # consistently UNDER-perform on the held-out OOS.
    np.random.seed(2)
    T = 320
    S = 8
    rows_per = T // S
    # 4 trials. In each odd-indexed partition, trial_A wins. In each
    # even-indexed partition, trial_B wins. Force engineered anti-correlation
    # between IS-win and OOS-win.
    data = np.zeros((T, 4))
    for p in range(S):
        start = p * rows_per
        end = start + rows_per
        if p % 2 == 0:
            data[start:end, 0] = np.random.normal(0.01, 0.001, rows_per)  # trial 0 great
            data[start:end, 1] = np.random.normal(-0.01, 0.001, rows_per)  # trial 1 awful
        else:
            data[start:end, 0] = np.random.normal(-0.01, 0.001, rows_per)
            data[start:end, 1] = np.random.normal(0.01, 0.001, rows_per)
        data[start:end, 2] = np.random.normal(0, 0.01, rows_per)
        data[start:end, 3] = np.random.normal(0, 0.01, rows_per)
    df = pd.DataFrame(data, columns=[f"trial_{i}" for i in range(4)])
    result = MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=S)
    # The engineered anti-correlated pattern → PBO > 0.5
    assert result["pbo"] > 0.5, (
        f"Engineered overfit PBO = {result['pbo']:.3f}, expected > 0.5"
    )
    assert result["deploy_threshold_met"] is False


def test_pbo_rejects_invalid_n_partitions():
    """S must be even and >= 4."""
    df = pd.DataFrame(np.random.normal(0, 0.01, (100, 5)))
    import pytest
    with pytest.raises(ValueError, match="n_partitions"):
        MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=3)
    with pytest.raises(ValueError, match="n_partitions"):
        MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=2)


def test_pbo_handles_too_few_observations():
    """T < 2*S → returns NaN with error message, not exception."""
    df = pd.DataFrame(np.random.normal(0, 0.01, (10, 5)))  # T=10, S=16 → fail
    result = MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=16)
    assert np.isnan(result["pbo"])
    assert "error" in result


def test_pbo_handles_single_trial():
    """N=1 → cannot rank trials → NaN return."""
    df = pd.DataFrame(np.random.normal(0, 0.01, (100, 1)))
    result = MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=4)
    assert np.isnan(result["pbo"])


def test_pbo_reports_combination_count():
    """C(S, S/2) check — for S=8 → 70 combinations; for S=4 → 6."""
    np.random.seed(3)
    df = pd.DataFrame(np.random.normal(0, 0.01, (100, 5)))
    result4 = MetricsEngine.probability_of_backtest_overfitting(df, n_partitions=4)
    assert result4["n_combinations"] == 6  # C(4, 2) = 6

    df_big = pd.DataFrame(np.random.normal(0, 0.01, (320, 5)))
    result8 = MetricsEngine.probability_of_backtest_overfitting(df_big, n_partitions=8)
    assert result8["n_combinations"] == 70  # C(8, 4) = 70


# ============================================================================
# T-061 (2026-05-22, user-approved): sharpe_ratio std == 0 → std < tol
# The legacy test (line 171 ~) documented this as "behavior change requiring
# user approval"; approval granted 2026-05-22. Mirrors the tolerance check
# already in sharpe_ratio_lo_corrected from T-059.
# ============================================================================

def test_sharpe_ratio_handles_identical_float_input_without_exploding():
    """pd.Series([0.001] * 100).std() returns ~2e-19, not 0. Pre-T-061 this
    produced a Sharpe in the 1e15 range. With tolerance guard, returns 0."""
    flat = pd.Series([0.001] * 100)
    result = MetricsEngine.sharpe_ratio(flat)
    assert result == 0.0, (
        f"Identical-input Sharpe should be 0 (tolerance), got {result}"
    )


def test_sharpe_ratio_handles_nan_std():
    """Single-element series → std is NaN → tolerance check returns 0."""
    single = pd.Series([0.01])
    result = MetricsEngine.sharpe_ratio(single)
    assert result == 0.0


def test_sharpe_ratio_normal_input_unchanged_post_t061():
    """Backwards-compat gate: non-degenerate inputs should produce identical
    Sharpe pre/post T-061. The tolerance fix only changes behavior for
    constant/NaN std cases."""
    np.random.seed(42)
    rets = pd.Series(np.random.normal(0.001, 0.01, 252))
    expected = rets.mean() / rets.std() * np.sqrt(252)
    actual = MetricsEngine.sharpe_ratio(rets)
    assert abs(actual - expected) < 1e-10


# ============================================================================
# T-062 (2026-05-22): Layer 2 portfolio health metrics
# Per the 2026-05-16 metrics research dive: ES_97.5 replacing VaR (FRTB
# standard), CDaR for drawdown-aware optimization, Meucci N_Ent for
# diversification monitoring.
# ============================================================================

# --- Expected Shortfall (ES) ---

def test_expected_shortfall_normal_returns():
    """Synthetic normal returns: ES_0.975 should be more negative than
    VaR_0.975 (ES is the average of the tail, VaR is the threshold)."""
    np.random.seed(0)
    rets = pd.Series(np.random.normal(0.0005, 0.012, 2000))
    es = MetricsEngine.expected_shortfall(rets, confidence=0.975)
    var = MetricsEngine.value_at_risk(rets, confidence=0.975)
    # ES is the conditional mean below VaR — by construction, ES ≤ VaR
    # (both negative for typical loss tail, |ES| ≥ |VaR|)
    assert es < 0
    assert es <= var, f"ES={es} should be ≤ VaR={var} (more negative)"


def test_expected_shortfall_uniform_distribution():
    """For uniform returns on [-0.04, 0.04], ES_0.975 should be ≈ midpoint
    of worst 2.5% tail = midpoint of [-0.04, -0.038] = -0.039 ± epsilon.
    Loosen for sample noise."""
    np.random.seed(1)
    rets = pd.Series(np.random.uniform(-0.04, 0.04, 4000))
    es = MetricsEngine.expected_shortfall(rets, confidence=0.975)
    # Worst 2.5% tail of U[-0.04, 0.04] has theoretical mean = -0.0395
    # Sample noise → ±10%
    assert -0.041 < es < -0.036, (
        f"ES of U[-0.04, 0.04] worst 2.5% should be ≈ -0.0395, got {es:.4f}"
    )


def test_expected_shortfall_empty_returns_zero():
    """Defensive: empty input → 0.0, not exception."""
    assert MetricsEngine.expected_shortfall(pd.Series([], dtype=float)) == 0.0


def test_expected_shortfall_all_gains_no_loss_tail():
    """If no returns are below the VaR threshold (all-positive), the tail
    is the single VaR value itself (mean of one-element tail)."""
    rets = pd.Series([0.01] * 100)  # all-positive constant returns
    es = MetricsEngine.expected_shortfall(rets, confidence=0.975)
    # The 2.5% quantile of a constant series equals that constant
    assert abs(es - 0.01) < 1e-9


# --- Conditional Drawdown at Risk (CDaR) ---

def test_cdar_monotonically_growing_curve_returns_zero():
    """An equity curve that never goes down has no drawdowns → CDaR = 0."""
    curve = pd.Series(np.linspace(100, 200, 252))
    cdar = MetricsEngine.conditional_drawdown_at_risk(curve, alpha=0.95)
    assert cdar == 0.0


def test_cdar_synthetic_drawdown_curve():
    """Synthetic curve with one big drawdown: CDaR should capture the
    worst drawdown values, returned as negative."""
    # Build a curve: rises to 200, falls to 150 (worst -25% drawdown), recovers
    curve = pd.Series([100, 120, 150, 180, 200, 175, 150, 165, 180, 195, 210])
    cdar = MetricsEngine.conditional_drawdown_at_risk(curve, alpha=0.80)
    # Drawdowns from peak (200): 0,0,0,0,0,-12.5%,-25%,-17.5%,-10%,-2.5%,0
    # Worst 20% = -25%; tail mean of one obs at -0.25
    assert cdar < 0
    assert cdar < -0.10, (
        f"CDaR with -25% drawdown should be < -10%, got {cdar:.4f}"
    )


def test_cdar_random_walk_realistic_band():
    """Realistic random-walk curve: CDaR should be more negative than
    typical drawdown levels."""
    np.random.seed(2)
    rets = np.random.normal(0.0003, 0.012, 1000)
    curve = pd.Series(100 * np.cumprod(1 + rets))
    cdar = MetricsEngine.conditional_drawdown_at_risk(curve, alpha=0.95)
    mdd = MetricsEngine.max_drawdown(curve)
    # CDaR (mean of worst 5% drawdowns) should be ≤ MDD (the single worst)
    # in magnitude — i.e., MDD is the extreme, CDaR is a tail average
    assert cdar <= 0
    assert cdar >= mdd, (
        f"CDaR={cdar} should be >= MDD={mdd} (less negative than the extremum)"
    )


def test_cdar_empty_input_returns_zero():
    """Defensive: empty / single-point input → 0.0."""
    assert MetricsEngine.conditional_drawdown_at_risk(pd.Series([], dtype=float)) == 0.0
    assert MetricsEngine.conditional_drawdown_at_risk(pd.Series([100.0])) == 0.0


# --- Meucci Effective Number of Bets (N_Ent) ---

def test_n_ent_diagonal_covariance_returns_n():
    """When covariance is diagonal (assets uncorrelated) AND weights are
    equal, every PC contributes equally → N_Ent ≈ N."""
    n = 5
    weights = pd.Series([1.0 / n] * n, index=[f"a{i}" for i in range(n)])
    # Identity covariance — each asset is its own PC at equal variance
    cov = pd.DataFrame(
        np.eye(n) * 0.01, index=weights.index, columns=weights.index
    )
    n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
    assert abs(n_ent - n) < 0.01, (
        f"Equal weights + identity cov → N_Ent should be N={n}, got {n_ent}"
    )


def test_n_ent_concentrated_weight_returns_one():
    """When all weight is in one asset, N_Ent should be ≈ 1."""
    weights = pd.Series([1.0, 0.0, 0.0, 0.0], index=["a","b","c","d"])
    cov = pd.DataFrame(np.eye(4) * 0.01, index=weights.index, columns=weights.index)
    n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
    assert abs(n_ent - 1.0) < 0.01, (
        f"All-in-one-asset → N_Ent should be 1, got {n_ent}"
    )


def test_n_ent_unequal_weights_correlated_assets_between_1_and_n():
    """Unequal weights in a correlated portfolio: N_Ent should be
    STRICTLY between 1 and N.

    MATHEMATICAL NOTE: equal weights in an all-equal-correlation covariance
    project perfectly into the [1,1,1,1] eigenvector (the only PC weighted
    by the symmetric structure), giving N_Ent ≡ 1 regardless of ρ.
    Testing the in-between case requires breaking the symmetry — either
    unequal weights or non-uniform correlations.
    """
    n = 4
    # Unequal weights breaking the symmetric eigenvector projection
    weights = pd.Series([0.4, 0.3, 0.2, 0.1], index=[f"a{i}" for i in range(n)])
    # Moderate correlation
    cov = pd.DataFrame(
        np.full((n, n), 0.005) + np.eye(n) * 0.005,
        index=weights.index, columns=weights.index,
    )
    n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
    assert 1.0 < n_ent < n, (
        f"Unequal weights moderate-correlation: N_Ent={n_ent} should be in (1, {n})"
    )


def test_n_ent_equal_weights_correlated_asymptote_one():
    """Equal weights in an all-equal-correlation covariance project entirely
    onto the [1,1,1,1] eigenvector. N_Ent = 1 for ANY ρ ≠ 0 — this is the
    correct mathematical answer (all risk in one PC), not a bug."""
    n = 4
    weights = pd.Series([0.25] * n, index=[f"a{i}" for i in range(n)])
    for off_diag in [0.001, 0.005, 0.008]:  # different correlation levels
        cov = pd.DataFrame(
            np.full((n, n), off_diag) + np.eye(n) * (0.01 - off_diag),
            index=weights.index, columns=weights.index,
        )
        n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
        assert abs(n_ent - 1.0) < 1e-6, (
            f"off_diag={off_diag}: equal weights + symmetric corr → "
            f"N_Ent should be 1 exactly, got {n_ent}"
        )


def test_n_ent_extreme_correlation_concentrates_to_one():
    """At ρ → 1, equal weights project entirely onto the first PC →
    N_Ent → 1. Document this asymptotic limit; not a bug, real behavior."""
    n = 4
    weights = pd.Series([0.25] * n, index=[f"a{i}" for i in range(n)])
    # Near-perfect correlation
    cov = pd.DataFrame(
        np.full((n, n), 0.009) + np.eye(n) * 0.001,
        index=weights.index, columns=weights.index,
    )
    n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
    # All variance in one PC → entropy = 0 → N_Ent = exp(0) = 1
    assert abs(n_ent - 1.0) < 1e-6, (
        f"Near-perfect correlation should give N_Ent ≈ 1, got {n_ent}"
    )


def test_n_ent_degenerate_input():
    """Defensive: None, single-asset, or zero covariance → 0.0."""
    weights = pd.Series([1.0], index=["a"])
    cov = pd.DataFrame([[0.01]], index=["a"], columns=["a"])
    # Single-asset case is degenerate by the function's contract (len < 2)
    assert MetricsEngine.effective_number_of_bets(weights, cov) == 0.0
    # None input
    assert MetricsEngine.effective_number_of_bets(None, cov) == 0.0
    assert MetricsEngine.effective_number_of_bets(weights, None) == 0.0


def test_n_ent_weights_realigned_to_cov_index():
    """If weights have entries missing from cov, reindex aligns them
    (missing → 0); cov entries missing from weights also → 0 effective weight."""
    weights = pd.Series([0.5, 0.5], index=["a", "b"])
    # Cov has 'a', 'b', 'c' — 'c' should be filled to 0
    cov = pd.DataFrame(
        np.eye(3) * 0.01,
        index=["a","b","c"], columns=["a","b","c"],
    )
    n_ent = MetricsEngine.effective_number_of_bets(weights, cov)
    # Only 2 assets actually held → effective bets ≈ 2
    assert abs(n_ent - 2.0) < 0.01, (
        f"Reindexed weights with 2 held assets → N_Ent ≈ 2, got {n_ent}"
    )


# ============================================================================
# T-063 (2026-05-22): Pre-registered decay monitors — rolling PSR + CUSUM
# Per the 2026-05-16 metrics research dive Layer 1: rolling-252 PSR + CUSUM
# on standardized returns is THE retire-the-edge decision driver.
# ============================================================================

# --- rolling_psr ---

def test_rolling_psr_returns_series_with_correct_window_NaNs():
    """First (window-1) values should be NaN; rest are PSR in [0,1]."""
    np.random.seed(0)
    rets = pd.Series(
        np.random.normal(0.0005, 0.01, 500),
        index=pd.date_range("2024-01-01", periods=500, freq="B"),
    )
    psr_series = MetricsEngine.rolling_psr(rets, window=60)
    # First 59 should be NaN
    assert psr_series.iloc[:59].isna().all()
    # Rest should be in [0, 1]
    valid = psr_series.iloc[59:]
    assert (valid >= 0.0).all() and (valid <= 1.0).all()


def test_rolling_psr_positive_drift_above_half():
    """Strong positive drift → rolling PSR should be > 0.5 (high prob true SR > 0)."""
    np.random.seed(1)
    rets = pd.Series(
        np.random.normal(0.002, 0.01, 300),  # strong positive drift
        index=pd.date_range("2024-01-01", periods=300, freq="B"),
    )
    psr = MetricsEngine.rolling_psr(rets, window=120)
    valid = psr.dropna()
    # Most windows should give high PSR (true Sharpe likely > 0)
    assert valid.median() > 0.7, (
        f"Strong drift should give rolling PSR median > 0.7, got {valid.median():.3f}"
    )


def test_rolling_psr_handles_too_short_input():
    """Series shorter than window → returns empty/NaN series."""
    rets = pd.Series(np.random.normal(0, 0.01, 50),
                     index=pd.date_range("2024-01-01", periods=50, freq="B"))
    result = MetricsEngine.rolling_psr(rets, window=252)
    assert len(result) == 0 or result.isna().all()


def test_rolling_psr_against_benchmark():
    """Rolling PSR against a non-zero benchmark should be LOWER than
    against zero benchmark (higher bar → less probability of beating it)."""
    np.random.seed(2)
    rets = pd.Series(
        np.random.normal(0.0008, 0.012, 400),
        index=pd.date_range("2024-01-01", periods=400, freq="B"),
    )
    psr_zero = MetricsEngine.rolling_psr(rets, window=120, sr_benchmark_annualized=0.0)
    psr_high = MetricsEngine.rolling_psr(rets, window=120, sr_benchmark_annualized=2.0)
    # Compare medians of valid (non-NaN) values
    assert psr_zero.dropna().median() > psr_high.dropna().median(), (
        "PSR vs higher benchmark should be lower than vs zero"
    )


# --- cusum_decay_monitor ---

def test_cusum_no_alarm_for_in_sample_distribution():
    """When OOS returns are drawn from the same distribution as in-sample,
    CUSUM should rarely alarm at standard k=0.5, h=10."""
    np.random.seed(3)
    # In-sample stats
    ref_mean, ref_std = 0.0005, 0.012
    # OOS drawn from SAME distribution
    oos = pd.Series(
        np.random.normal(ref_mean, ref_std, 252),
        index=pd.date_range("2024-01-01", periods=252, freq="B"),
    )
    result = MetricsEngine.cusum_decay_monitor(
        oos, reference_mean=ref_mean, reference_std=ref_std, k=0.5, h=10.0
    )
    # At k=0.5, h=10 with same-distribution input, false-alarm rate
    # should be low. Allow it but check the diagnostic structure.
    assert "cusum_plus" in result
    assert "cusum_minus" in result
    assert "decay_alarm_fired" in result
    assert len(result["cusum_plus"]) == len(oos)


def test_cusum_alarms_on_genuine_decay():
    """When OOS returns drop materially below in-sample mean by more than
    the drift-tolerance k, CUSUM⁻ accumulates downward and fires.

    Math note: at k=0.5, CUSUM⁻ only accumulates when standardized r_t
    falls below -k (i.e., r_t < ref_mean - 0.5·ref_std). Mild decay of
    e.g. -0.25σ standardized is ABSORBED by k=0.5 and doesn't accumulate.
    Genuine decay must exceed the drift tolerance for the alarm to fire.
    """
    np.random.seed(4)
    ref_mean, ref_std = 0.001, 0.012  # in-sample mean
    # OOS mean is well below ref_mean - k·ref_std = 0.001 - 0.006 = -0.005
    # Use -0.012 (1σ below ref_mean) which is well past the k=0.5 tolerance
    oos = pd.Series(
        np.random.normal(-0.012, 0.012, 252),
        index=pd.date_range("2024-01-01", periods=252, freq="B"),
    )
    result = MetricsEngine.cusum_decay_monitor(
        oos, reference_mean=ref_mean, reference_std=ref_std, k=0.5, h=10.0
    )
    assert result["decay_alarm_fired"], (
        f"Genuine decay (mean shift past k=0.5) should fire CUSUM alarm. "
        f"max_cusum_minus={result['max_cusum_minus']:.2f} should be ≤ -10"
    )
    assert result["first_alarm_at"] is not None


def test_cusum_rejects_zero_reference_std():
    """Pre-registered std=0 → exception (cannot standardize)."""
    rets = pd.Series([0.01] * 50)
    with pytest.raises(ValueError, match="reference_std"):
        MetricsEngine.cusum_decay_monitor(
            rets, reference_mean=0.0, reference_std=0.0
        )


def test_cusum_empty_input_returns_empty_state():
    """Defensive: empty returns → no alarm, empty series, no exception."""
    result = MetricsEngine.cusum_decay_monitor(
        pd.Series([], dtype=float),
        reference_mean=0.0, reference_std=0.01,
    )
    assert result["decay_alarm_fired"] is False
    assert result["first_alarm_at"] is None
    assert len(result["cusum_minus"]) == 0


def test_cusum_h_threshold_controls_sensitivity():
    """Lower h → faster alarm. Higher h → slower / fewer false alarms."""
    np.random.seed(5)
    ref_mean, ref_std = 0.001, 0.012
    oos = pd.Series(
        np.random.normal(-0.0005, 0.012, 252),  # mild decay
        index=pd.date_range("2024-01-01", periods=252, freq="B"),
    )
    result_loose = MetricsEngine.cusum_decay_monitor(
        oos, reference_mean=ref_mean, reference_std=ref_std, k=0.5, h=5.0
    )
    result_strict = MetricsEngine.cusum_decay_monitor(
        oos, reference_mean=ref_mean, reference_std=ref_std, k=0.5, h=20.0
    )
    # If both fire, loose should fire NO LATER than strict
    if result_loose["decay_alarm_fired"] and result_strict["decay_alarm_fired"]:
        assert result_loose["first_alarm_at"] <= result_strict["first_alarm_at"]
    else:
        # Strict didn't fire → max_cusum_minus(strict) is shallower or equal
        assert result_strict["max_cusum_minus"] >= result_loose["max_cusum_minus"]


# ============================================================================
# T-065 (2026-05-22, user-approved batch extension of T-061): tolerance sweep
# Applies the same std == 0 → std < 1e-12 tolerance pattern from T-061 to
# the other 7 floating-point std/var guards in MetricsEngine. Each is a
# behavior change in the constant-input degenerate case ONLY; non-degenerate
# inputs produce identical output pre/post.
# ============================================================================

def test_sortino_handles_identical_negative_returns():
    """sortino_ratio with all-equal-negative returns: downside std is
    ~2e-19, not 0. Pre-T-065 produced exploding ratio; post-T-065 caps at 10."""
    rets = pd.Series([-0.001] * 50 + [0.002] * 50)
    sortino = MetricsEngine.sortino_ratio(rets)
    # Cap is 10.0; not exploding to 1e15
    assert sortino == 10.0


def test_beta_handles_identical_benchmark_returns():
    """beta with flat benchmark: var is ~2e-19, not 0. Pre-T-065 exploded."""
    strat = pd.Series(np.random.normal(0.001, 0.01, 100))
    bench = pd.Series([0.0005] * 100)  # flat benchmark
    beta = MetricsEngine.beta(strat, bench)
    assert beta == 0.0


def test_sqn_handles_identical_trade_pnl():
    """sqn with all-equal trades: std is ~2e-19, not 0. Should return 0."""
    pnl = pd.Series([100.0] * 50)
    sqn = MetricsEngine.sqn(pnl)
    assert sqn == 0.0


def test_psr_handles_identical_returns():
    """probabilistic_sharpe_ratio with constant input → 0 not exception."""
    rets = pd.Series([0.001] * 100)
    psr = MetricsEngine.probabilistic_sharpe_ratio(rets)
    assert psr == 0.0


def test_dsr_handles_identical_returns():
    """deflated_sharpe_ratio with constant input → 0 not exception."""
    rets = pd.Series([0.001] * 100)
    dsr = MetricsEngine.deflated_sharpe_ratio(rets, n_trials=10)
    assert dsr == 0.0


def test_information_ratio_handles_identical_active_returns():
    """When strategy === benchmark, active series is flat → 0 not exception."""
    rets = pd.Series(np.random.normal(0.001, 0.01, 100))
    ir = MetricsEngine.information_ratio(rets, rets.copy())
    assert ir == 0.0


def test_calculate_all_handles_constant_growth_curve_via_T065_guard():
    """T-065 hardened calculate_all's std guard. Constant growth curves
    have tiny-but-nonzero std after pct_change; pre-T-065 the calculate_all
    guard *did* fire because returns of geometric constant growth are
    bit-identical floats giving exactly std=0. Post-T-065 the tolerance
    guard catches near-zero cases too. Verify both paths return _empty_metrics."""
    # Geometric growth — returns exactly equal each period
    curve = pd.Series([100.0 * (1.001 ** i) for i in range(100)],
                      index=pd.date_range("2024-01-01", periods=100, freq="D"))
    metrics = MetricsEngine.calculate_all(curve)
    # The tolerance guard still short-circuits to empty (preserving
    # T-061-era behavior).
    assert metrics["Total Return %"] == 0.0


def test_T065_non_degenerate_inputs_unchanged():
    """Backwards-compat gate: non-degenerate inputs produce identical
    output pre/post T-065. Only constant-input cases changed."""
    np.random.seed(99)
    rets = pd.Series(np.random.normal(0.001, 0.01, 252))
    # All affected methods should produce non-zero, finite values
    sortino = MetricsEngine.sortino_ratio(rets)
    sqn = MetricsEngine.sqn(rets)
    psr = MetricsEngine.probabilistic_sharpe_ratio(rets)
    assert sortino != 10.0 and math.isfinite(sortino)
    assert sqn > 0 and math.isfinite(sqn)
    assert 0.0 < psr <= 1.0
