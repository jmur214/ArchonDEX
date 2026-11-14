"""T-399 — the static arms' annual rebalance cost is charged once per year-change, not every day.

The July 2026 line was `cost[yr != yr.shift(1)]` with `yr = index.to_period("Y")`. On a PeriodIndex,
`.shift(1)` moves the PERIOD, so the mask was true on every row and each static arm above 1x paid 0.51 bp
per DAY (~1.29 %/yr). These tests plant the input condition (a series spanning year-changes), assert the
count of charged bars, and pin the arms the defect never touched (the 1x bar, the glide, the gated arm) to
values computed from the PRE-FIX source (commit ccd60c8), so the fix is proven to have left them alone.

Proven by reversion 2026-11-14 (see the module's commit message for the counts): with the July line
restored the cost tests fail and the unaffected-arm pins still pass.
"""
import numpy as np
import pandas as pd
import pytest

from scripts import offense_campaign_t312_t315 as oc
from scripts import t315_static_cost_rerun_t399 as t399
from scripts.deep_reverify_sleeve_t311 import ER, TD

# Two calendar years of business days, one year-change inside.
_IDX2 = pd.bdate_range("2021-01-04", "2022-12-30")
# Three calendar years, starting mid-year: two year-changes inside.
_IDX3 = pd.bdate_range("2019-07-01", "2022-06-30")


def _flat(idx: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Zero equity return and zero cash: the arm's daily return is a constant, so cost is the only thing
    that can make one bar differ from another."""
    return pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)


def _charged(idx: pd.DatetimeIndex, L: float) -> tuple[int, float]:
    eq, cash = _flat(idx)
    base = oc.lev_daily(eq, cash, L)
    r = oc.static_arm(eq, cash, L)
    paid = (base - r).values
    return int((paid > 1e-12).sum()), float(paid.sum())


def test_year_change_mask_is_positional_on_a_two_year_series():
    m = oc.year_change_mask(_IDX2)
    assert m.dtype == bool and len(m) == len(_IDX2)
    assert int(m.sum()) == 2
    assert m[0]
    first_2022 = int(np.argmax(_IDX2.year == 2022))
    assert m[first_2022] and _IDX2[first_2022].year == 2022 and _IDX2[first_2022 - 1].year == 2021
    assert not m[1:first_2022].any() and not m[first_2022 + 1:].any()


def test_the_july_idiom_is_true_on_every_row():
    """The witness: why the old line charged daily. If pandas ever changes PeriodIndex.shift to be
    positional, this fails and the comment in year_change_mask needs re-reading."""
    yr = _IDX2.to_period("Y")
    assert bool((yr != yr.shift(1)).all())


@pytest.mark.parametrize("L", [1.25, 1.35, 1.5, 1.75, 2.0])
def test_static_arm_pays_the_cost_once_per_year_change(L):
    n, total = _charged(_IDX2, L)
    assert len(_IDX2) > 500                      # the planted condition: far more bars than year-changes
    assert n == 2
    assert total == pytest.approx(2 * oc.SLIP_EQ, rel=1e-9)


def test_static_arm_cost_count_follows_the_calendar_not_the_length():
    """2019-07 -> 2022-06 holds the first bar and three year-changes (2020, 2021, 2022): four charges."""
    n, total = _charged(_IDX3, 1.5)
    assert len(_IDX3) > 750
    assert n == 4 == int(oc.year_change_mask(_IDX3).sum())
    assert total == pytest.approx(4 * oc.SLIP_EQ, rel=1e-9)


def test_one_x_pays_no_rebalance_cost():
    eq, cash = _flat(_IDX2)
    pd.testing.assert_series_equal(oc.static_arm(eq, cash, 1.0), oc.lev_daily(eq, cash, 1.0))


def test_the_published_defect_reproduction_charges_every_bar_and_only_the_runner_has_it():
    """The ORIGINAL column is the defect on purpose. It must differ from the fixed arm by exactly
    (bars - year-changes) x 0.51 bp, and must not exist in the campaign module."""
    eq, cash = _flat(_IDX2)
    orig = t399.static_arm_as_published(eq, cash, 1.5)
    fixed = oc.static_arm(eq, cash, 1.5)
    assert float((fixed - orig).sum()) == pytest.approx((len(_IDX2) - 2) * oc.SLIP_EQ, rel=1e-9)
    assert not hasattr(oc, "static_arm_as_published")


# ---- the arms the defect never touched: pinned to the PRE-FIX source (ccd60c8) ----
def _synthetic() -> tuple[pd.Series, pd.Series, pd.Series]:
    idx = pd.bdate_range("2015-01-02", periods=900)
    rng = np.random.default_rng(399)
    ret = rng.normal(0.0004, 0.011, size=len(idx))
    px = pd.Series(100.0 * np.cumprod(1.0 + ret), index=idx)
    eq = px.pct_change().dropna()
    cash = pd.Series(0.00012, index=eq.index)
    return px, eq, cash


# Computed 2026-11-14 by executing the pre-fix source (git show ccd60c8:scripts/offense_campaign_t312_t315.py)
# on _synthetic(); the post-fix module reproduced each to the last bit on the same machine.
_PIN_BAR_SUM = 0.7103989427248713
_PIN_GLIDE_SUM = 0.7825370884668611
_PIN_GATED_SUM = 0.42353371207761475
_PIN_GATED_MEAN_EXP = 0.9873793615441722


def test_unaffected_arms_equal_their_pre_fix_values():
    px, eq, cash = _synthetic()
    bar = (eq - ER["equity"] / TD).dropna()
    glide = oc.glide_arm(eq, cash, 2.0)
    gated, viol, mexp = oc.gated_t298(px, eq, cash)
    assert viol == 0
    assert float(bar.sum()) == pytest.approx(_PIN_BAR_SUM, rel=1e-12, abs=1e-15)
    assert float(glide.sum()) == pytest.approx(_PIN_GLIDE_SUM, rel=1e-12, abs=1e-15)
    assert float(gated.sum()) == pytest.approx(_PIN_GATED_SUM, rel=1e-12, abs=1e-15)
    assert mexp == pytest.approx(_PIN_GATED_MEAN_EXP, rel=1e-12)


def test_unaffected_arms_never_reach_the_cost_mask(monkeypatch):
    """Structural: the bar, the glide and the gated arm run with static_arm and the mask removed."""
    def boom(*a, **k):
        raise AssertionError("an arm the defect never touched called the static cost path")
    monkeypatch.setattr(oc, "static_arm", boom)
    monkeypatch.setattr(oc, "year_change_mask", boom)
    px, eq, cash = _synthetic()
    assert len(oc.glide_arm(eq, cash, 2.0)) == len(eq)
    assert len(oc.gated_t298(px, eq, cash)[0]) > 0
    with pytest.raises(AssertionError):
        oc.static_arm(eq, cash, 1.5)


# ---- the runner's statistics and sensitivities ----
def test_paired_boot_reproduces_the_frozen_paired_dw():
    px, eq, cash = _synthetic()
    bar = (eq - ER["equity"] / TD).dropna()
    arm = oc.static_arm(eq, cash, 1.5)
    lo, hi = oc.paired_dw(arm, bar)
    b = t399.paired_boot(arm, bar, t399.span_years(bar))
    assert (b["dw_lo"], b["dw_hi"]) == (lo, hi)
    assert b["dlog_lo"] <= b["dlog_hi"] and 0.0 <= b["p_ahead"] <= 1.0


def test_s1_blend_equals_the_fund_at_two_x_and_pays_less_fee_below():
    px, eq, cash = _synthetic()
    pd.testing.assert_series_equal(t399.blend_arm(eq, cash, 2.0), oc.static_arm(eq, cash, 2.0), check_names=False,
                                   rtol=1e-12, atol=1e-15)
    for L in (1.25, 1.5, 1.75):
        gap = (t399.blend_arm(eq, cash, L) - oc.static_arm(eq, cash, L)).values
        want = ((2.0 - L) * oc.SSO_ER - 2.0 * (2.0 - L) * ER["equity"]) / TD      # SSO ER saved, less the 1x fund's ER
        assert np.allclose(gap, want, rtol=0, atol=1e-15)
    with pytest.raises(t399.T399Halt):
        t399.blend_arm(eq, cash, 2.5)


def test_acceptance_halts_when_the_reproduction_does_not_reproduce():
    """A refusal lock with its positive control: an empty result set must halt, never pass."""
    with pytest.raises((t399.T399Halt, KeyError)):
        t399.acceptance({"windows": {}, "haircuts": {}, "crisis_1929": {}, "accumulation_race": {}})
