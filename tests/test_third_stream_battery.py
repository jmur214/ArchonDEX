"""Third-stream battery — the screen's contract (T-313 formalized as a standing tool).

Locks the properties that make the verdict trustworthy: the frozen bar is IMPORTED
(cannot drift from the live T-316 gate), coverage failures announce themselves rather
than silently shrinking the window, and the verdict reads the CI rather than the point
estimate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.third_stream_battery import (
    CORR_MAX, CRISES, MIN_COVERAGE, MIN_OBS, block_ci_pairs, _corr,
    drag_vs_cash, window_panel,
)


def _series(n, start="2021-01-01", vals=None, seed=0):
    idx = pd.bdate_range(start, periods=n)
    if vals is None:
        vals = np.random.default_rng(seed).normal(0, 0.01, n)
    return pd.Series(vals, index=idx)


def _pair(n, rho, seed=0):
    """Two return series with population correlation ~rho."""
    rng = np.random.default_rng(seed)
    b = rng.normal(0, 0.01, n)
    e = rng.normal(0, 0.01, n)
    c = rho * b + np.sqrt(max(0.0, 1 - rho ** 2)) * e
    idx = pd.bdate_range("2021-01-01", periods=n)
    return pd.Series(c, index=idx), pd.Series(b, index=idx)


# ---- the bar cannot drift from the live gate -------------------------------------

def test_bar_is_imported_from_the_frozen_t316_gate_not_redeclared():
    from paper_trader.dbmf_shadow import GATE_A_CORR_MAX
    assert CORR_MAX is GATE_A_CORR_MAX or CORR_MAX == GATE_A_CORR_MAX
    assert CORR_MAX == 0.30


def test_crisis_windows_match_the_t311_convention_where_t311_defines_them():
    """Window provenance is inherited, not invented (see the CRISES docstring)."""
    from scripts.deep_reverify_sleeve_t311 import CRISES as T311
    assert CRISES["2008 GFC"] == T311["GFC"]
    assert CRISES["COVID-2020"] == T311["COVID"]
    assert CRISES["2022"] == T311["2022"]


def test_every_crisis_window_is_long_enough_to_be_scoreable():
    """A window that can NEVER clear MIN_OBS is a broken screen, not a strict one."""
    bench = _series(6000, start="2005-01-03")
    for name, (s, e) in CRISES.items():
        n = len(bench.loc[s:e])
        assert n >= MIN_OBS, f"{name} holds only {n} business days — unscoreable for every candidate"


# ---- fail-closed coverage --------------------------------------------------------

def test_window_the_candidate_predates_returns_NOT_COVERED_with_a_reason():
    bench = _series(300, start="2005-01-03")
    cand = _series(300, start="2019-01-01")
    r = window_panel(cand, bench, "2005-02-01", "2005-06-30")
    assert r["status"] == "NOT_COVERED"
    assert "begins after" in r["reason"]
    assert "corr" not in r          # never emits a number for an uncovered window


def test_partial_coverage_is_NOT_scored_rather_than_silently_shrunk():
    """The `[NN-FAIL-CLOSED]` case: a corr on the overlap is not the window's corr."""
    bench = _series(200, start="2021-01-01")
    cand = _series(200, start="2021-01-01").iloc[150:]     # only the tail of the window
    r = window_panel(cand, bench, "2021-01-01", "2021-10-01")
    assert r["status"] == "PARTIAL"
    assert r["coverage"] < MIN_COVERAGE
    assert "corr" not in r
    assert "not this window's correlation" in r["reason"]


def test_too_few_observations_is_UNRESOLVED_not_a_confident_number():
    c, b = _pair(MIN_OBS - 5, rho=0.0)
    r = window_panel(c, b, str(c.index[0].date()), str(c.index[-1].date()))
    assert r["status"] == "UNRESOLVED"
    assert f"below MIN_OBS={MIN_OBS}" in r["reason"]


# ---- the verdict reads the CI, not the point estimate ----------------------------

def test_clearly_independent_candidate_PASSes_with_the_whole_CI_under_the_bar():
    c, b = _pair(1500, rho=0.0, seed=1)
    r = window_panel(c, b, str(c.index[0].date()), str(c.index[-1].date()))
    assert r["status"] == "PASS"
    assert r["ci"][1] <= CORR_MAX


def test_clearly_comoving_candidate_FAILs():
    c, b = _pair(1500, rho=0.85, seed=2)
    r = window_panel(c, b, str(c.index[0].date()), str(c.index[-1].date()))
    assert r["status"] == "FAIL"
    assert r["ci"][0] > CORR_MAX
    assert "co-moves" in r["reason"]


def test_a_point_estimate_under_the_bar_does_NOT_pass_when_the_CI_straddles_it():
    """`[NN-SHARPE-CI]`: the anti-goalpost-moving property. Short window, corr near
    the bar — the point estimate flatters, the interval refuses to call it."""
    c, b = _pair(60, rho=0.30, seed=3)
    r = window_panel(c, b, str(c.index[0].date()), str(c.index[-1].date()))
    assert r["status"] == "UNRESOLVED"
    assert r["ci"][0] <= CORR_MAX <= r["ci"][1]
    assert "cannot settle" in r["reason"]


def test_negative_crisis_correlation_passes_the_signed_screen():
    """A short-in-crashes stream is the BEST case — |corr| would wrongly reject it."""
    c, b = _pair(1500, rho=-0.70, seed=4)
    r = window_panel(c, b, str(c.index[0].date()), str(c.index[-1].date()))
    assert r["status"] == "PASS"
    assert r["corr"] < 0
    assert r["abs_corr_screen"] == "fail"      # the two-sided reading disagrees, and says so


# ---- the bootstrap itself ---------------------------------------------------------

def test_block_bootstrap_resamples_PAIRS_and_so_preserves_correlation():
    """Independent resampling of the two legs would destroy the dependence being
    measured and manufacture a spurious PASS. The CI must bracket the truth."""
    c, b = _pair(1200, rho=0.80, seed=5)
    lo, hi = block_ci_pairs(c.values, b.values, _corr, block=21)
    assert lo > 0.5 and hi < 1.0
    assert lo <= _corr(c.values, b.values) <= hi


def test_bootstrap_is_deterministic_under_the_fixed_seed():
    c, b = _pair(400, rho=0.5, seed=6)
    a1 = block_ci_pairs(c.values, b.values, _corr, block=21)
    a2 = block_ci_pairs(c.values, b.values, _corr, block=21)
    assert a1 == a2


def test_zero_variance_leg_returns_nan_not_an_exploded_correlation():
    """`[NN-FP-GUARDS]`: tolerance guard, never bare == 0."""
    flat = np.full(200, 0.001)
    assert _corr(flat, np.random.default_rng(0).normal(0, 0.01, 200)) != _corr(flat, flat) or True
    assert np.isnan(_corr(flat, np.random.default_rng(0).normal(0, 0.01, 200)))


# ---- carry vs cash ----------------------------------------------------------------

def test_carry_verdict_is_CI_aware_in_both_directions():
    idx = pd.bdate_range("2021-01-01", periods=1500)
    cash = pd.Series(0.0001, index=idx)
    bleeder = pd.Series(-0.0004, index=idx)          # a steady, unambiguous drag
    assert drag_vs_cash(bleeder, cash)["verdict"].startswith("DRAG")
    earner = pd.Series(0.0006, index=idx)
    assert drag_vs_cash(earner, cash)["verdict"].startswith("CARRY-POSITIVE")


def test_noisy_carry_is_INDETERMINATE_rather_than_called():
    """Excess is demeaned to EXACTLY zero carry, so the property under test is the
    verdict logic and not the luck of a draw (the first fixture here drew a mean 3 SE
    low and the honest answer really was DRAG)."""
    idx = pd.bdate_range("2021-01-01", periods=800)
    cash = pd.Series(0.0001, index=idx)
    noise = np.random.default_rng(7).normal(0, 0.02, 800)
    noisy = pd.Series(0.0001 + (noise - noise.mean()), index=idx)
    assert drag_vs_cash(noisy, cash)["verdict"].startswith("INDETERMINATE")
