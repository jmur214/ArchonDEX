"""T-251 — barbell composer: inverse-vol SAFE CORE + convex SATELLITE (trend overlay).

A structural shape bet. Default-OFF; core uses plain inverse-vol (NOT HRP);
equity vol-targeting is fail-closed (Engine-B-gated, T-252).
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
    BarbellConfig, BarbellComposer)


def _core(n=400, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "SPY": rng.normal(0.0004, 0.011, n),   # higher vol
        "AGG": rng.normal(0.0001, 0.003, n),   # lowest vol → most inverse-vol weight
        "GLD": rng.normal(0.0002, 0.009, n),
    }, index=idx)


def test_core_weights_inverse_vol_favours_low_vol_asset():
    c = BarbellComposer()
    w = c.core_weights(_core()).dropna()
    assert np.allclose(w.sum(axis=1).values, 1.0)          # weights sum to 1 each bar
    assert (w["AGG"] > w["SPY"]).all()                     # lowest-vol asset gets the most budget
    assert (w["AGG"] > w["GLD"]).all()


def test_core_returns_is_causal():
    # using yesterday's weights → the first weighted bar is NaN-dropped, length < input
    c = BarbellComposer()
    core = _core()
    cr = c.core_returns(core)
    assert len(cr) < len(core)
    assert cr.notna().all()


def test_compose_returns_is_weighted_core_plus_satellite():
    c = BarbellComposer(BarbellConfig(satellite_weight=0.15))
    core = _core()
    sat = pd.Series(np.full(len(core), 0.002), index=core.index)   # constant +20bps satellite
    bar = c.compose_returns(core, sat)
    cr = c.core_returns(core)
    j = pd.concat({"b": bar, "c": cr}, axis=1).dropna()
    # barbell - 0.85*core should equal 0.15*0.002 on every aligned bar
    resid = j["b"] - 0.85 * j["c"]
    assert np.allclose(resid.values, 0.15 * 0.002)


def test_equity_vol_target_is_fail_closed():
    c = BarbellComposer(BarbellConfig(equity_vol_target=True))
    core = _core()
    sat = pd.Series(np.zeros(len(core)), index=core.index)
    with pytest.raises(NotImplementedError, match="Engine-B"):
        c.compose_returns(core, sat)


def test_default_is_off_and_satellite_weight_in_band():
    cfg = BarbellConfig()
    assert cfg.enabled is False
    assert 0.10 <= cfg.satellite_weight <= 0.20


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
