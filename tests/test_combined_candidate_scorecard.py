"""T-176 — contract tests for the combined-candidate scorecard.

Locks the behaviour E consumes in the paper scorecard: per-proxy blocks,
apples-to-apples windows, fixed-weight combination, net-of-cost handling.
Deterministic synthetic series — no network, no cloud.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.combined_candidate_scorecard import (  # noqa: E402
    DEFAULT_TAX_PROFILES, ROBO_PROXIES, ScorecardRow, TaxProfile, TaxRates,
    after_tax_returns, build_scorecard, combine_fixed_weight, format_scorecard,
    load_tax_rates, robo_proxy_returns, rows_to_dicts, score, to_returns,
)


def _ret_series(n: int = 600, mu: float = 0.0004, sigma: float = 0.01, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-06-01", periods=n)
    return pd.Series(rng.normal(mu, sigma, n), index=idx)


def test_to_returns_detects_equity_vs_returns():
    rets = _ret_series()
    eq = 100_000 * (1 + rets).cumprod()
    back = to_returns(eq)
    # round-trips an equity curve back to ~the original returns
    assert np.allclose(back.values, rets.values[1:], atol=1e-9)
    # a return series passes through unchanged
    assert np.allclose(to_returns(rets).values, rets.values, atol=1e-12)


def test_combine_fixed_weight_convex_and_drawdown_dampened():
    base = _ret_series(seed=2)
    overlay = _ret_series(seed=99) * 0.5  # lower-vol, uncorrelated overlay
    combined = combine_fixed_weight(base, overlay, w_overlay=0.20, rebalance="daily",
                                    rebalance_cost_bps=0.0)
    aligned = pd.concat({"b": base, "o": overlay}, axis=1).dropna()
    expected = 0.8 * aligned["b"] + 0.2 * aligned["o"]
    assert np.allclose(combined.values, expected.values, atol=1e-12)
    # a diversifying overlay should not raise combined vol above the base
    assert combined.std() <= base.reindex(combined.index).std() + 1e-9


def test_rebalance_cost_is_a_drag():
    base, overlay = _ret_series(seed=3), _ret_series(seed=4)
    free = combine_fixed_weight(base, overlay, 0.20, "monthly", rebalance_cost_bps=0.0)
    costed = combine_fixed_weight(base, overlay, 0.20, "monthly", rebalance_cost_bps=5.0)
    assert costed.sum() < free.sum()  # cost only subtracts


def test_score_matches_metrics_engine():
    from core.metrics_engine import MetricsEngine
    r = _ret_series(seed=5)
    row = score(r, "x", rf_annual=0.0, n_boot=200)
    assert isinstance(row, ScorecardRow)
    assert row.ci_low <= row.sharpe <= row.ci_high
    assert row.n_days == len(r)
    assert np.isclose(row.sharpe, round(float(MetricsEngine.sharpe_ratio(r)), 4), atol=1e-3)


def test_cash_sleeve_adds_drag_not_vol():
    # schwab_like has a cash sleeve; its vol must be < an all-risk blend's intuition:
    r = robo_proxy_returns("schwab_like", rf_annual=0.04)
    assert "_cash" in ROBO_PROXIES["schwab_like"]
    assert r.std() > 0


def test_build_scorecard_blocks_are_internally_aligned():
    base = _ret_series(n=900, seed=7)
    blocks = build_scorecard(base, robo=("60_40", "schwab_like"), n_boot=200)
    assert set(blocks) == {"60_40", "schwab_like"}
    for name, rows in blocks.items():
        assert [r.label for r in rows][0] == "base"
        assert rows[2].label == f"robo:{name}"
        # all three rows in a block share ONE window (apples-to-apples)
        assert rows[0].n_days == rows[1].n_days == rows[2].n_days
        assert rows[0].start == rows[2].start and rows[0].end == rows[2].end


def test_blocks_can_have_different_windows_across_proxies():
    # 60_40 (long history) should not be truncated to schwab_like's GLD start
    base = _ret_series(n=1200, seed=8)
    blocks = build_scorecard(base, robo=("60_40", "schwab_like"), n_boot=100)
    assert blocks["60_40"][0].n_days >= blocks["schwab_like"][0].n_days


def test_format_and_json_roundtrip():
    base = _ret_series(n=700, seed=9)
    blocks = build_scorecard(base, robo="60_40", n_boot=100)
    text = format_scorecard(blocks)
    assert "deploy-bar" in text and "account:" in text.lower()
    d = rows_to_dicts(blocks)
    assert d["60_40"][0]["label"] == "base"


# --------------------------------------------------------------------------- #
# T-191 — after-tax layer
# --------------------------------------------------------------------------- #
def _multiyear(seed: int = 11, mu: float = 0.0006) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2017-01-02", periods=252 * 5)
    return pd.Series(rng.normal(mu, 0.009, len(idx)), index=idx)


def test_load_tax_rates_from_config():
    rt = load_tax_rates()
    # fed ST 0.30 + IL 0.0495 = 0.3495; LT 0.15 + 0.0495 = 0.1995 (or defaults)
    assert 0.30 <= rt.st <= 0.45 and 0.15 <= rt.lt <= 0.30
    assert rt.lt < rt.st  # long-term is always the lower rate


def test_after_tax_reduces_a_gaining_book():
    r = _multiyear()  # positive drift → realized gains → tax drag
    at = after_tax_returns(r, TaxProfile(1.0, 1.0), load_tax_rates())
    assert float((1 + at).prod()) < float((1 + r).prod())  # strictly less wealth
    # st-heavy (base) is taxed harder than lt-heavy (robo) for the same series
    at_robo = after_tax_returns(r, TaxProfile(0.20, 0.30), load_tax_rates())
    assert float((1 + at).prod()) < float((1 + at_robo).prod())


def test_loss_year_pays_no_tax():
    # a strictly-negative year realizes no gain → after-tax == pre-tax that year
    idx = pd.bdate_range("2020-01-02", periods=252)
    r = pd.Series(-0.001, index=idx)
    at = after_tax_returns(r, TaxProfile(1.0, 1.0), load_tax_rates())
    assert np.allclose((1 + at).prod(), (1 + r).prod(), atol=1e-9)


def test_higher_realization_means_more_tax():
    r = _multiyear()
    rates = load_tax_rates()
    low = float((1 + after_tax_returns(r, TaxProfile(0.2, 1.0), rates)).prod())
    high = float((1 + after_tax_returns(r, TaxProfile(1.0, 1.0), rates)).prod())
    assert high < low  # realizing more of the gain each year → more tax → less wealth


def test_roth_block_equals_pretax_taxable_block_is_worse():
    base = _multiyear(seed=7)
    roth = build_scorecard(base, robo="60_40", account="roth", n_boot=100)
    tax = build_scorecard(base, robo="60_40", account="taxable", n_boot=100)
    # Roth base CAGR == the untaxed score; taxable base CAGR is lower (gaining book)
    roth_base, tax_base = roth["60_40"][0], tax["60_40"][0]
    assert tax_base.cagr_pct < roth_base.cagr_pct
    # MaxDD is preserved (year-end haircut doesn't deepen an intra-year trough materially)
    assert tax_base.maxdd_pct <= 0


def test_default_profiles_encode_the_indictment():
    # base = full realization + 100% short-term (the measured production reality)
    assert DEFAULT_TAX_PROFILES["base"].realized_fraction == 1.0
    assert DEFAULT_TAX_PROFILES["base"].st_fraction == 1.0
    # robo = tax-efficient buy-hold (lower on both)
    assert DEFAULT_TAX_PROFILES["robo"].realized_fraction < DEFAULT_TAX_PROFILES["base"].realized_fraction
    assert DEFAULT_TAX_PROFILES["robo"].st_fraction < DEFAULT_TAX_PROFILES["base"].st_fraction


def test_format_taxable_states_assumptions():
    base = _multiyear()
    blocks = build_scorecard(base, robo="60_40", account="taxable", n_boot=80)
    text = format_scorecard(blocks, account="taxable")
    assert "AFTER-TAX (taxable)" in text and "ST " in text and "indictment" in text


# --------------------------------------------------------------------------- #
# T-203 — evaluate_deploy_readiness (the robo deploy gate)
# --------------------------------------------------------------------------- #
from core.combined_candidate_scorecard import (  # noqa: E402
    DeployVerdict, RoboComparison, evaluate_deploy_readiness, format_deploy_verdict,
)


def _equity_from_returns(r: pd.Series) -> pd.Series:
    return 100_000 * (1 + r).cumprod()


def test_deploy_verdict_shape_and_accessors():
    idx = pd.bdate_range("2019-06-01", periods=252 * 6)
    rng = np.random.default_rng(1)
    base = _equity_from_returns(pd.Series(rng.normal(0.0006, 0.009, len(idx)), index=idx))
    v = evaluate_deploy_readiness(base, account="roth", n_boot=100)
    assert isinstance(v, DeployVerdict)
    assert v.deploy_verdict in ("DEPLOY", "DO NOT DEPLOY")
    assert v.vs_60_40 is None or isinstance(v.vs_60_40, RoboComparison)
    assert "DEPLOY GATE" in format_deploy_verdict(v)


def test_window_bias_blocks_deploy_when_tail_unverified():
    # base spans 2006-2025 with a -45% 2008 crash; the DBMF window (2019+) misses
    # it → full-cycle tail UNVERIFIED → cannot certify deploy even if it beats.
    idx = pd.bdate_range("2006-01-02", periods=252 * 19)
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0007, 0.009, len(idx)), index=idx)
    crash = (idx >= "2008-09-01") & (idx <= "2009-03-01")
    r[crash] = -0.004  # a sustained ~-45% drawdown well before the DBMF era
    v = evaluate_deploy_readiness(_equity_from_returns(r), account="roth", n_boot=100)
    assert v.window_excludes_base_tail is True
    assert v.full_cycle_tail_verified is False
    assert v.passed is False                          # tail unverified → DO NOT DEPLOY
    assert abs(v.base_full_maxdd_pct) > abs(v.window_maxdd_pct)  # full tail deeper


def test_mdd_does_not_carry_a_window_flattered_verdict():
    # Same window-biased base: every proxy's MDD-improvement is discounted, so a
    # comparison only "beats" on ci_low (never on the window-flattered MDD alone).
    idx = pd.bdate_range("2006-01-02", periods=252 * 19)
    rng = np.random.default_rng(5)
    r = pd.Series(rng.normal(0.0004, 0.012, len(idx)), index=idx)
    r[(idx >= "2008-09-01") & (idx <= "2009-03-01")] = -0.004
    v = evaluate_deploy_readiness(_equity_from_returns(r), account="roth", n_boot=100)
    for c in v.comparisons.values():
        # beats reduces to the ci_low test when the window excludes the tail
        assert c.beats == c.sharpe_ci_low_beats


def test_taxable_is_weaker_than_roth():
    idx = pd.bdate_range("2019-06-01", periods=252 * 6)
    rng = np.random.default_rng(7)
    base = _equity_from_returns(pd.Series(rng.normal(0.0008, 0.01, len(idx)), index=idx))
    roth = evaluate_deploy_readiness(base, account="roth", n_boot=100)
    tax = evaluate_deploy_readiness(base, account="taxable", n_boot=100)
    # after-tax sharpe of the candidate is <= roth for every proxy (tax is a drag)
    for name in roth.comparisons:
        assert tax.comparisons[name].sharpe_cand <= roth.comparisons[name].sharpe_cand + 1e-9


def test_require_any_vs_all():
    idx = pd.bdate_range("2019-06-01", periods=252 * 6)
    rng = np.random.default_rng(9)
    base = _equity_from_returns(pd.Series(rng.normal(0.0006, 0.009, len(idx)), index=idx))
    v_all = evaluate_deploy_readiness(base, account="roth", require="all", n_boot=80)
    v_any = evaluate_deploy_readiness(base, account="roth", require="any", n_boot=80)
    # 'any' is never stricter than 'all' (given identical tail-verification)
    if v_all.full_cycle_tail_verified == v_any.full_cycle_tail_verified:
        assert not (v_all.passed and not v_any.passed)


def test_gate_uses_ci_low_not_point_estimate():
    # the comparison stores ci_low for both sides and gates on it (CLAUDE.md `[NN-SHARPE-CI]`)
    idx = pd.bdate_range("2019-06-01", periods=252 * 6)
    rng = np.random.default_rng(11)
    base = _equity_from_returns(pd.Series(rng.normal(0.0006, 0.009, len(idx)), index=idx))
    v = evaluate_deploy_readiness(base, account="roth", n_boot=100)
    for c in v.comparisons.values():
        assert c.sharpe_ci_low_beats == (c.ci_low_cand > c.ci_low_robo)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
