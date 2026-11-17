"""Locks for the B-10 (T-385) harness guards — synthetic data only, no dependence on data/.

Each guard is proven where it runs: a planted defect must RAISE (prereg §8), and the parity lock has
a positive control (identical functions pass) and a negative control (a 1-bp ER perturbation fails).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import b10_gold_leg as b10
from scripts import deep_reverify_sleeve_t311 as t311


def _legs(n: int = 800, seed: int = 1, start: str = "2001-01-02") -> dict:
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(seed)
    eq = pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n)), index=idx)
    au = pd.Series(50 * np.cumprod(1 + rng.normal(0.0002, 0.012, n)), index=idx)
    return {"equity": eq, "gold": au}


# --------------------------------------------------------------------------- G3: planted hole
def test_G3_planted_15_day_native_hole_raises():
    s = _legs()["gold"]
    holed = s.drop(s.index[(s.index > "2001-06-01") & (s.index < "2001-06-19")])
    base, end = pd.Timestamp("2001-01-02"), pd.Timestamp("2003-12-31")
    assert b10.max_native_gap(s.index, base, end) <= 4          # clean series passes
    b10.assert_native_gaps(s.index, base, end, "gold")
    with pytest.raises(b10.B10Halt, match="G3"):
        b10.assert_native_gaps(holed.index, base, end, "gold")


def test_G3_hole_is_invisible_after_ffill_which_is_why_the_guard_reads_the_native_index():
    """The T-311 defect class: after reindex+ffill onto a full calendar the hole is gone."""
    s = _legs()["gold"]
    holed = s.drop(s.index[(s.index > "2001-06-01") & (s.index < "2001-06-19")])
    filled = holed.reindex(s.index).ffill()
    base, end = pd.Timestamp("2001-01-02"), pd.Timestamp("2003-12-31")
    b10.assert_native_gaps(filled.index, base, end, "gold")    # passes — the hole is masked
    with pytest.raises(b10.B10Halt):
        b10.assert_native_gaps(holed.index, base, end, "gold")


# --------------------------------------------------------------------------- G4: staleness
def test_G4_staleness_over_7_days_raises():
    s = _legs()["gold"]
    holed = s.drop(s.index[(s.index > "2001-06-01") & (s.index < "2001-06-19")])
    cal = s.index
    assert b10.assert_staleness(cal, s.index, "gold") == 0
    with pytest.raises(b10.B10Halt, match="G4"):
        b10.assert_staleness(cal, holed.index, "gold")


# --------------------------------------------------------------------------- G5: flat ffilled tail
def test_G5_end_after_a_legs_native_end_raises_the_t311_flat_tail():
    legs = _legs()
    gold_native = legs["gold"][legs["gold"].index <= "2003-06-30"]
    natives = {"equity": legs["equity"].index, "gold": gold_native.index}
    # T-311-style alignment would carry gold flat to the equity end:
    flat = gold_native.reindex(legs["equity"].index).ffill()
    assert flat[flat.index > "2003-06-30"].nunique() == 1
    b10.assert_end_within_native(pd.Timestamp("2003-06-30"), natives)
    with pytest.raises(b10.B10Halt, match="G5"):
        b10.assert_end_within_native(legs["equity"].index[-1], natives)


def test_G6_base_without_a_recent_native_print_raises():
    legs = _legs()
    natives = {"equity": legs["equity"].index, "gold": legs["gold"].index[legs["gold"].index >= "2001-03-01"]}
    with pytest.raises(b10.B10Halt, match="G6"):
        b10.assert_base_print(pd.Timestamp("2001-02-01"), natives)


# --------------------------------------------------------------------------- G2
@pytest.mark.parametrize("defect", ["dup", "nan", "nonpos", "unsorted"])
def test_G2_native_integrity_defects_raise(defect):
    s = _legs()["gold"].copy()
    if defect == "dup":
        s = pd.concat([s, s.iloc[[5]]]).sort_index()
    elif defect == "nan":
        s.iloc[10] = np.nan
    elif defect == "nonpos":
        s.iloc[10] = 0.0
    else:
        s = s.iloc[::-1]
    with pytest.raises(b10.B10Halt, match="G2"):
        b10.assert_native_integrity(s, "gold")


# --------------------------------------------------------------------------- G9: parity lock
def test_G9_parity_positive_control_matches_t311_robo_returns():
    legs = _legs()
    px = pd.DataFrame(legs)
    assert b10.assert_parity(px, legs) <= b10.PARITY_TOL


def test_G9_parity_negative_control_a_1bp_er_perturbation_fails():
    legs = _legs()
    px = pd.DataFrame(legs)
    mine, _ = b10.rebal_returns(px, b10.WEIGHTS, {"equity": t311.ER["equity"],
                                                  "gold": t311.ER["gold"] + 0.0001})
    ref = b10.t311_rebal(legs)
    assert np.max(np.abs(mine.to_numpy() - ref.to_numpy())) > b10.PARITY_TOL


def test_G10_rebalance_census_counts_month_boundaries_and_charges_turnover():
    legs = _legs()
    _, cen = b10.rebal_returns(pd.DataFrame(legs), b10.WEIGHTS, b10.ER_PRIMARY)
    idx = legs["equity"].index[1:]
    months = len(set(zip(idx.year, idx.month)))
    assert cen["n_rebalances"] == months - 1
    assert cen["turnover_sum"] > 0 and cen["cost_sum"] > 0


# --------------------------------------------------------------------------- G7 / G8
def test_G7_misaligned_arms_raise():
    a = pd.Series(0.001, index=pd.bdate_range("2001-01-02", periods=600))
    with pytest.raises(b10.B10Halt, match="G7"):
        b10.paired_diff(a, a.iloc[1:])


def test_G8_short_bootstrap_input_raises_instead_of_returning_zeros():
    d = pd.Series(np.random.default_rng(0).normal(0, 1e-3, 100),
                  index=pd.bdate_range("2001-01-02", periods=100))
    with pytest.raises(b10.B10Halt, match="G8"):
        b10.boot(d, None)


# --------------------------------------------------------------------------- decision rule
@pytest.mark.parametrize("ci71,ci00,mdd,want", [
    (0.10, 0.05, 4.0, "H1 MET"),
    (0.10, -0.01, 4.0, "REFUTED"),          # amendment 1 ruling 1: the refutation takes precedence
    (-0.01, 0.20, 9.0, "REFUTED"),
    (0.10, 0.05, 2.9, "NOT MET, not refuted"),
])
def test_outcome_rule_matches_prereg(ci71, ci00, mdd, want):
    assert b10.outcome(ci71, ci00, mdd) == want


def test_drawdown_counts_a_first_day_loss_via_the_base_value():
    r = pd.Series([-0.10, 0.01, 0.01], index=pd.bdate_range("2001-01-03", periods=3))
    eq = b10.curve(r, pd.Timestamp("2001-01-02"))
    assert abs(b10.drawdown(eq)["mdd"] - (-0.10)) < 1e-12
