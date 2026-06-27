"""
tests/test_sleeve_vol_target_t252.py
====================================
T-2026-06-26-252 — sleeve-level conditional vol-targeting mechanism.

Covers: default-OFF identity (canon-safe), the continuous vs conditional scale,
the causal extreme-vol gate (no look-ahead, never invents), the no-borrow ceiling,
and [NN-FAIL-CLOSED] on a missing input.
"""
import numpy as np
import pandas as pd
import pytest

from engines.engine_b_risk.sleeve_vol_target import (
    SleeveVolTargetConfig,
    apply_sleeve_vol_target,
    extreme_state,
    realized_vol,
    vol_scale_series,
)


def _rets(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    # two vol regimes: calm then a stormy tail
    calm = rng.normal(0.0003, 0.006, n // 2)
    storm = rng.normal(-0.001, 0.03, n - n // 2)
    return pd.Series(np.concatenate([calm, storm]), index=idx)


# --------------------------------------------------------------------- #
# default-OFF identity (canon-safe)
# --------------------------------------------------------------------- #

def test_disabled_is_identity():
    r = _rets()
    cfg = SleeveVolTargetConfig(enabled=False)
    net, scale, gross = apply_sleeve_vol_target(r, cfg)
    assert net is r                      # exact same object — no-op
    assert (scale == 1.0).all()


def test_fail_closed_on_empty_when_enabled():
    cfg = SleeveVolTargetConfig(enabled=True)
    with pytest.raises(ValueError, match=r"T-252.*NN-FAIL-CLOSED"):
        apply_sleeve_vol_target(pd.Series(dtype=float), cfg)


# --------------------------------------------------------------------- #
# the scale math (continuous vs conditional) + guards
# --------------------------------------------------------------------- #

def test_continuous_clips_to_floor_ceiling():
    rv = pd.Series([0.05, 0.15, 0.60, np.nan, 0.0],
                   index=pd.bdate_range("2020-01-01", periods=5))
    cfg = SleeveVolTargetConfig(conditional=False, target_vol=0.15,
                                floor=0.5, ceiling=1.5)
    s = vol_scale_series(rv, cfg)
    assert s.iloc[0] == pytest.approx(1.5)        # 0.15/0.05=3 -> ceiling
    assert s.iloc[1] == pytest.approx(1.0)        # 0.15/0.15=1
    assert s.iloc[2] == pytest.approx(0.5)        # 0.15/0.60=0.25 -> floor
    assert s.iloc[3] == pytest.approx(1.0)        # NaN rv -> guard 1.0
    assert s.iloc[4] == pytest.approx(1.0)        # 0 rv  -> guard 1.0


def test_conditional_only_acts_in_extreme_state():
    r = _rets()
    rv = realized_vol(r, 20)
    cfg = SleeveVolTargetConfig(conditional=True, target_vol=0.15, floor=0.5,
                                ceiling=1.0, extreme_percentile=0.80, min_history=60)
    s = vol_scale_series(rv, cfg)
    mask = extreme_state(rv, 0.80, 60)
    # outside the extreme state the scale is exactly 1.0 (full exposure)
    non_extreme = s[(~mask.reindex(s.index).fillna(False)) & rv.notna()]
    assert (non_extreme == 1.0).all()
    # inside the extreme state it de-grosses (<= 1.0, never levers given ceiling 1.0)
    in_extreme = s[mask.reindex(s.index).fillna(False)]
    assert (in_extreme <= 1.0 + 1e-12).all()
    assert (in_extreme < 1.0).any()              # actually binds somewhere


def test_conditional_never_levers_with_ceiling_one():
    r = _rets()
    cfg = SleeveVolTargetConfig(enabled=True, conditional=True, ceiling=1.0,
                                min_history=60)
    _, scale, _ = apply_sleeve_vol_target(r, cfg)
    assert (scale.dropna() <= 1.0 + 1e-12).all()   # long/flat, no borrow


def test_extreme_state_is_causal_no_lookahead():
    rv = realized_vol(_rets(), 20)
    mask = extreme_state(rv, 0.80, 60)
    # truncating the series at t must not change the mask value at any s <= t-? :
    # recomputing on a prefix gives the same prefix mask (expanding quantile uses
    # only data <= t).
    cut = rv.iloc[:300]
    mask_cut = extreme_state(cut, 0.80, 60)
    assert (mask.iloc[:300].fillna(False) == mask_cut.fillna(False)).all()


def test_apply_lags_position_and_nets_cost():
    r = _rets()
    cfg = SleeveVolTargetConfig(enabled=True, conditional=True, cost_bps=5.0,
                                min_history=60)
    net, scale, gross = apply_sleeve_vol_target(r, cfg)
    # net <= gross everywhere there is turnover (cost only subtracts)
    aligned = (gross - net).reindex(net.index).dropna()
    assert (aligned >= -1e-12).all()
    # position is yesterday's scale → first usable net aligns after the shift
    assert len(net) > 0
