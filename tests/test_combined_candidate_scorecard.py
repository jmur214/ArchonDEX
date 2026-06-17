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
    ROBO_PROXIES, ScorecardRow, build_scorecard, combine_fixed_weight,
    format_scorecard, robo_proxy_returns, rows_to_dicts, score, to_returns,
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
    assert "deploy-bar" in text and "PRE-TAX" in text
    d = rows_to_dicts(blocks)
    assert d["60_40"][0]["label"] == "base"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
