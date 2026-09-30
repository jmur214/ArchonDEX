"""
Proposed referee repairs — FAILING tests that document apparatus defects found
by the alpha-frontier review (docs/Sources/alpha_frontier_review_2026_09_30/01_gap_report.md).

Every test here is marked xfail(strict=True): it FAILS today (documenting the
defect) and will start PASSING — and therefore XPASS-fail the suite — the day
the corresponding repair lands, at which point the marker must be removed and
the test promoted to a regression pin. The referee is propose-first by project
rule (`autonomous_development_prestatement.md`); nothing in this file modifies
measurement code. Each test names its probe script in scripts/probe_*.py.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import integrate, stats

XFAIL_REASON = "proposed referee repair — see docs/Sources/alpha_frontier_review_2026_09_30/01_gap_report.md"


# --------------------------------------------------------------------------- #
# 1A.1  Gate 4 permutation null is degenerate (significance.py:84)
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.1 Gate-4 null")
def test_gate4_permutation_null_has_nonzero_spread():
    """A permutation of the strategy's OWN returns leaves mean/std invariant,
    so every null Sharpe == actual Sharpe and null_std ~ 1e-16. A correct null
    (permute the signal against returns, or sign-flip) has null_std ~ 0.6 on a
    3-year daily series. Probe: scripts/probe_gate4_permutation_null.py"""
    from engines.engine_d_discovery.significance import monte_carlo_permutation_test

    rng = np.random.RandomState(0)
    r = rng.normal(0.0004, 0.01, 756)  # ~SR 0.63 annualized
    res = monte_carlo_permutation_test(r, n_permutations=500, random_state=1)
    assert res["null_std"] > 0.05, f"degenerate null: null_std={res['null_std']:.3e}"


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.1 Gate-4 power")
def test_gate4_rejects_a_sharpe_5_series():
    """A Sharpe-5 series must get p < 0.01 under any valid null. The production
    test returned p=0.973 for SR 5.2 in the probe (rounding noise, not a test)."""
    from engines.engine_d_discovery.significance import monte_carlo_permutation_test

    rng = np.random.RandomState(0)
    r = rng.normal(0.0, 0.01, 756)
    r = r - r.mean() + (5.2 / math.sqrt(252)) * r.std()
    res = monte_carlo_permutation_test(r, n_permutations=1000, random_state=42)
    assert res["p_value"] < 0.01, f"p={res['p_value']} for SR≈5.2"


# --------------------------------------------------------------------------- #
# 1A.2  Engine F retirement gate: kill-on-ci_low inverts the burden of proof;
#       sqrt(252) on per-trade PnL regardless of trade frequency.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.2 Engine-F burden of proof")
def test_engine_f_does_not_retire_a_true_sr_0p6_edge_after_1000_trades():
    """An edge with true annualized SR 0.6 trading 50x/yr (20 years of record at
    1000 trades) must not be retired against a SPY-like benchmark (0.8 − 0.3
    margin = 0.5 threshold). Under the ci_low kill rule + sqrt(252)-on-per-trade
    annualization it is retired in most simulations.
    Probe: scripts/probe_engine_f_retirement_burden.py"""
    from engines.engine_f_governance.lifecycle_manager import (
        _bootstrap_sharpe_ci_low_from_pnls,
    )

    rng = np.random.default_rng(0)
    per_trade_sr = 0.6 / math.sqrt(50)
    retired = 0
    sims = 8
    for _ in range(sims):
        pnls = rng.normal(per_trade_sr * 100.0, 100.0, 1000)
        ci_low = _bootstrap_sharpe_ci_low_from_pnls(pnls)
        if ci_low < 0.8 - 0.3:
            retired += 1
    assert retired <= sims // 4, f"true-SR-0.6 edge retired in {retired}/{sims} sims"


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.2 Engine-F annualization")
def test_engine_f_sharpe_annualization_respects_trade_frequency():
    """`_edge_sharpe_from_pnl` scales per-trade mean/std by sqrt(252) no matter
    how often the edge trades. An edge with per-trade SR 0.085 trading 50x/yr
    has true annual SR 0.6; the helper reports ~1.35."""
    from engines.engine_f_governance.lifecycle_manager import _edge_sharpe_from_pnl

    rng = np.random.default_rng(0)
    per_trade_sr = 0.6 / math.sqrt(50)
    pnls = rng.normal(per_trade_sr * 100.0, 100.0, 20000)
    reported = _edge_sharpe_from_pnl(pnls)
    assert abs(reported - 0.6) < 0.15, f"reported {reported:.2f} for a true-SR-0.6 edge at 50 trades/yr"


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.2 [NN-FP-GUARDS] in the referee")
def test_engine_f_sharpe_helper_uses_tolerance_std_guard():
    """CLAUDE.md [NN-FP-GUARDS]: std guards must be `std < 1e-12 or not isfinite`,
    never bare `== 0`. `_edge_sharpe_from_pnl` uses `if std == 0`. A constant
    PnL series with float noise (~2e-19 std) must return 0.0, not ~1e15."""
    from engines.engine_f_governance.lifecycle_manager import _edge_sharpe_from_pnl

    pnls = np.array([0.001] * 100, dtype=float)
    pnls = pnls + np.array([1e-20 * ((-1) ** i) for i in range(100)])  # sub-ulp noise
    val = _edge_sharpe_from_pnl(pnls)
    assert abs(val) < 1.0, f"bare-equality guard let a constant series through: {val:.3e}"


# --------------------------------------------------------------------------- #
# 1A.4  MBL uses the 2·ln(N) upper bound, not E[max_N]²
# --------------------------------------------------------------------------- #
def _emax_exact(n: int) -> float:
    f = lambda x: x * n * stats.norm.pdf(x) * stats.norm.cdf(x) ** (n - 1)
    v, _ = integrate.quad(f, -10, 10, limit=200)
    return v


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.4 MBL upper bound")
def test_mbl_min_uses_exact_expected_max_not_upper_bound():
    """Bailey-Borwein-López de Prado-Zhu (2014) MinBTL ∝ E[max_N]²; 2·ln(N) is
    the upper bound they quote for intuition. At N=260 the bound overstates
    required years by ~39%. Probe: scripts/probe_mbl_n_effective.py"""
    from core.measurement.mbl_gate import compute_mbl_min

    n, sr = 260, 1.0
    exact_years = _emax_exact(n) ** 2 / sr ** 2
    got = compute_mbl_min(n, sr)
    assert abs(got - exact_years) / exact_years < 0.05, f"compute_mbl_min={got:.2f}yr vs exact {exact_years:.2f}yr"


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.4 N_effective counts every run")
def test_n_effective_is_not_a_raw_row_count():
    """`compute_n_effective` is `SELECT COUNT(*) FROM runs`: determinism reps,
    infra reruns, and ρ≈0.9 overlay A/Bs each count as an independent trial.
    The repair must expose a correlation-aware N_eff (ONC clustering or the
    equicorrelated identity E[max]² · (1−ρ̄)). This test asserts the API
    surface exists; the empirical ρ̄ is the repair brief's first deliverable."""
    import core.measurement.mbl_gate as mbl

    assert hasattr(mbl, "compute_n_effective_correlated"), "no correlation-aware N_eff in mbl_gate"


# --------------------------------------------------------------------------- #
# 1A.6  The ci_low < 0.4 kill thesis kills a SPY-shaped 12-year series
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " §1A.6 kill thesis kills SPY")
def test_ci_low_kill_threshold_does_not_kill_spy_shaped_series():
    """The project's own bootstrap on a SPY-calibrated 12-yr GARCH-t series
    (mean 13%, vol 17.5%, point SR ≈ 0.8) returns ci_low ≈ 0.2–0.3 on 4/5 seeds.
    A kill rule that kills the benchmark it is trying to beat is not a kill
    rule. Repair: kill on ci_low(Δ vs SPY) < 0, not on absolute ci_low < 0.4.
    Probe: scripts/probe_spy_ci_low_kill_threshold.py (NOT a measurement of
    real SPY — the container has no market data)."""
    from core.metrics_engine import MetricsEngine

    rng = np.random.default_rng(0)
    n = 252 * 12
    alpha, beta = 0.08, 0.90
    tv = (0.175 ** 2) / 252
    omega = tv * (1 - alpha - beta)
    h = tv
    out = np.empty(n)
    mu = 0.13 / 252
    for t in range(n):
        z = rng.standard_t(4) / math.sqrt(2.0)
        eps = math.sqrt(h) * z
        out[t] = mu + eps
        h = omega + alpha * eps * eps + beta * h
    s = pd.Series(out, index=pd.bdate_range("2014-01-02", periods=n))
    res = MetricsEngine.bootstrap_distribution(s, MetricsEngine.sharpe_ratio, n_iterations=500, seed=0)
    assert res["ci_low"] >= 0.4, f"SPY-shaped series: point={res['point_estimate']:.2f} ci_low={res['ci_low']:.2f}"


# =========================================================================== #
# DEFECTS THE PRIOR PASS DID NOT LIST (found 2026-09-30)
# =========================================================================== #

# --------------------------------------------------------------------------- #
# NEW-1  Backtester sizes from a frozen `portfolio.capital` (initial capital),
#        so sizing equity = initial_capital + market value ≈ 2× true equity
#        once cash is deployed. backtest_controller.py:158, :325, :647.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-1 frozen portfolio.capital")
def test_backtester_sizing_capital_tracks_deployed_cash():
    """`get_portfolio_capital()` must reflect cash actually available, not the
    initial capital set once at construction. This is the likely root cause of
    the 1.7–2.3× gross the code comments attribute to held-position accumulation."""
    from backtester.backtest_controller import BacktestController
    from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

    ctl = BacktestController.__new__(BacktestController)
    ctl.portfolio = PortfolioEngine(initial_capital=100_000.0)
    ctl.initial_capital = 100_000.0
    # mimic backtest_controller.py:157-158
    if float(getattr(ctl.portfolio, "capital", 0.0)) <= 0.0:
        ctl.portfolio.capital = ctl.initial_capital
    # deploy 60% of cash into positions (what a fill does at portfolio_engine.py:217)
    ctl.portfolio.cash -= 60_000.0
    assert abs(ctl.get_portfolio_capital() - ctl.portfolio.cash) < 1e-6, (
        f"sizing capital {ctl.get_portfolio_capital():.0f} vs cash {ctl.portfolio.cash:.0f}"
    )


# --------------------------------------------------------------------------- #
# NEW-2  Idle cash earns nothing in the equity-book backtester
#        (portfolio_engine.py:90, :353; no accrual anywhere in backtester/).
#        The trend-sleeve harness credits the T-bill rate (deep_reverify_sleeve_t311.py:90),
#        the robo proxy credits DGS3MO (combined_candidate_scorecard.py:244).
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-2 idle cash 0% in backtester")
def test_portfolio_engine_has_cash_accrual_api():
    """The repair adds a per-bar cash accrual at the DGS3MO path (the same
    convention the sleeve harness and scorecard robo already use). This test
    pins the API surface; the repair brief pins the number."""
    from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

    pe = PortfolioEngine(initial_capital=100_000.0)
    assert hasattr(pe, "accrue_cash_interest"), "no cash-interest accrual on PortfolioEngine"


# --------------------------------------------------------------------------- #
# NEW-3  MBL / DSR gate fails OPEN when the run registry is absent:
#        compute_n_effective → 1 → compute_mbl_min → 0.0 → Gate 0 auto-pass;
#        discovery.py:1740 `if n_trials_for_dsr > 1` → Gate 8 skipped.
#        [NN-FAIL-CLOSED] violation in the measurement path.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-3 MBL gate fails open at N=1")
def test_mbl_n_effective_fails_closed_when_registry_absent(tmp_path):
    from core.measurement.mbl_gate import compute_n_effective

    with pytest.raises(Exception):
        compute_n_effective(tmp_path / "does_not_exist.sqlite")


# --------------------------------------------------------------------------- #
# NEW-4  `stream_sharpe` (the Sharpe Gates 2–4 and DSR consume) uses a bare
#        `if s == 0.0` guard — attribution.py:113-115 — [NN-FP-GUARDS].
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-4 [NN-FP-GUARDS] in stream_sharpe")
def test_stream_sharpe_uses_tolerance_guard():
    from engines.engine_d_discovery.attribution import stream_sharpe

    s = pd.Series([0.001] * 100, dtype=float) + pd.Series([1e-20 * ((-1) ** i) for i in range(100)])
    val = stream_sharpe(s)
    assert abs(val) < 1.0, f"bare-equality guard let a constant series through: {val:.3e}"


# --------------------------------------------------------------------------- #
# NEW-5  Gate 6 subtracts RF from an ATTRIBUTION SPREAD (with − base), biasing
#        alpha down by ~RF/yr — larger than the 2%/yr threshold in 2023–24.
#        discovery.py:1582 passes `returns=attribution`; factor_decomposition.py:233.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-5 Gate 6 RF subtracted from a spread")
def test_gate6_alpha_of_a_factor_neutral_spread_is_not_shifted_by_rf():
    """A spread with true alpha +2.5%/yr and zero factor loadings, regressed
    with RF = 5%/yr in the factor frame, must recover ≈ +2.5%/yr. The current
    convention returns ≈ −2.5%/yr because RF is subtracted from a series that
    is already an excess-of-baseline spread."""
    from core.factor_decomposition import regress_returns_on_factors

    rng = np.random.default_rng(0)
    n = 1500
    idx = pd.bdate_range("2019-01-01", periods=n)
    factors = pd.DataFrame(
        {c: rng.normal(0, 0.01, n) for c in ["MktRF", "SMB", "HML", "RMW", "CMA", "Mom"]},
        index=idx,
    )
    factors["RF"] = 0.05 / 252
    true_alpha_daily = 0.025 / 252
    spread = pd.Series(true_alpha_daily + rng.normal(0, 0.002, n), index=idx)
    dec = regress_returns_on_factors(spread, factors, edge_name="spread")
    assert dec is not None
    assert abs(dec.alpha_annualized - 0.025) < 0.015, f"alpha_annualized={dec.alpha_annualized:.4f}"


# --------------------------------------------------------------------------- #
# NEW-6  Production Discovery: the orchestrator passes `significance_threshold=None`
#        (→ Gate 4 forced FAIL for every candidate) and then OVERWRITES
#        `passed_all_gates` in "Pass 2" with (ensemble sharpe > 0 AND PBO ≥ 0.7 AND
#        BH-reject of the degenerate p). Gates 1/5/6/7/8 are non-binding on
#        promotion. orchestration/mode_controller.py:1338, :1397-1403.
#        NOTE: this is a call-site defect; the honest test is an execution test
#        (repair brief RR-2 converts it). A text assertion documents it until then.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-6 Pass-2 overwrites the gauntlet verdict")
def test_production_discovery_does_not_overwrite_gauntlet_verdict():
    import inspect
    import orchestration.mode_controller as mc

    src = inspect.getsource(mc)
    assert "significance_threshold=None" not in src, "production passes significance_threshold=None"
    assert 'result["passed_all_gates"] = (' not in src, "Pass 2 overwrites validate_candidate's verdict"


# --------------------------------------------------------------------------- #
# NEW-7  Engine F paused→retired path gates on the POINT estimate while
#        active→retired gates on ci_low — lifecycle_manager.py:958-960.
#        Same `[NN-SHARPE-CI]` rule, two conventions in one module.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-7 paused→retired uses point estimate")
def test_paused_retirement_gate_reads_ci_low_not_point():
    import inspect
    from engines.engine_f_governance import lifecycle_manager as lm

    src = inspect.getsource(lm.LifecycleManager._check_paused_retirement)
    assert "_bootstrap_sharpe_ci_low_from_pnls" in src, "paused→retired compares edge_sharpe (point) to threshold"


# --------------------------------------------------------------------------- #
# NEW-8  `alpha_settings.prod.json` keys `news_sentiment_edge` but the edge's
#        EDGE_ID is `news_sentiment_v2`, so its 0.5 weight is never applied
#        (defaults to 1.0). Small, but it means the recorded weight is a lie.
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON + " NEW-8 edge-weight key mismatch")
def test_prod_edge_weight_keys_match_edge_ids():
    import json
    from pathlib import Path

    from engines.engine_a_alpha.edges.news_sentiment_edge import NewsSentimentEdge  # type: ignore

    cfg = json.loads(Path("config/alpha_settings.prod.json").read_text())
    keys = set(cfg.get("edge_weights", {}).keys())
    assert NewsSentimentEdge.EDGE_ID in keys, f"{NewsSentimentEdge.EDGE_ID} not in edge_weights; found {sorted(k for k in keys if 'news' in k)}"
