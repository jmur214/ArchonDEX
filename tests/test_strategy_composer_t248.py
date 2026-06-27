"""T-248 — strategy-level risk-parity composer (HRP over SLEEVE return series).

Default-OFF → naive equal-weight (canon-safe). ON → HRP risk-budget across
sleeves. Factor-neutralization is fail-closed (Engine-B-gated, propose-first).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_c_portfolio.strategy_composer import (  # noqa: E402
    StrategyCompositionConfig, StrategyRiskParityComposer)


def _sleeves(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    # base: higher vol; trend: lower vol, mild neg-corr to base (a defensive sleeve)
    base = rng.normal(0.0004, 0.012, n)
    trend = -0.3 * base + rng.normal(0.0002, 0.004, n)
    return pd.DataFrame({"base": base, "trend": trend}, index=idx)


def test_off_is_equal_weight_baseline():
    c = StrategyRiskParityComposer()  # risk_parity_enabled defaults False
    w = c.risk_budget_weights(_sleeves())
    assert set(w.index) == {"base", "trend"}
    assert w["base"] == pytest.approx(0.5) and w["trend"] == pytest.approx(0.5)


def test_on_hrp_weights_sum_to_one_nonneg_and_tilt_to_lower_vol():
    c = StrategyRiskParityComposer(StrategyCompositionConfig(risk_parity_enabled=True))
    w = c.risk_budget_weights(_sleeves())
    assert w.sum() == pytest.approx(1.0)
    assert (w >= 0).all()
    # HRP risk-parity puts MORE budget on the lower-vol (trend) sleeve than equal-weight
    assert w["trend"] > 0.5 > w["base"]


def test_factor_neutralize_is_fail_closed():
    c = StrategyRiskParityComposer(StrategyCompositionConfig(factor_neutralize=True))
    with pytest.raises(NotImplementedError, match="Engine-B"):
        c.risk_budget_weights(_sleeves())


def test_single_sleeve_gets_full_weight():
    c = StrategyRiskParityComposer(StrategyCompositionConfig(risk_parity_enabled=True))
    s = _sleeves()[["base"]]
    w = c.risk_budget_weights(s)
    assert w.to_dict() == pytest.approx({"base": 1.0})


def test_empty_is_empty():
    c = StrategyRiskParityComposer(StrategyCompositionConfig(risk_parity_enabled=True))
    assert c.risk_budget_weights(pd.DataFrame()).empty


def test_compose_returns_matches_weighted_blend():
    c = StrategyRiskParityComposer()  # equal-weight
    s = _sleeves(n=100)
    composed = c.compose_returns(s)
    expected = 0.5 * s["base"] + 0.5 * s["trend"]
    assert np.allclose(composed.values, expected.values)


def test_compose_returns_renormalizes_when_a_sleeve_is_missing_early():
    c = StrategyRiskParityComposer()  # equal-weight 50/50
    s = _sleeves(n=10)
    s.iloc[:3, s.columns.get_loc("trend")] = np.nan   # trend absent for first 3 bars
    composed = c.compose_returns(s)
    # first 3 bars: only base present → weight renormalizes to 100% base
    assert composed.iloc[0] == pytest.approx(s["base"].iloc[0])
    # later bars: 50/50
    assert composed.iloc[-1] == pytest.approx(0.5 * s["base"].iloc[-1] + 0.5 * s["trend"].iloc[-1])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
