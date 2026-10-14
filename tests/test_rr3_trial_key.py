"""The trial-key definition behind RR-3's dedupe — locked so the numbers R reproduced cannot drift.

`scripts.rr3_empirical_rho.trial_key`: md5 of the daily equity series as CSV, date as int64 ns and
equity rounded to the CENT. One definition shared by rr3_empirical_rho and rr3b_population_pass
(previously two copies of one inline expression). The golden below was computed from the inline
expression BEFORE it was extracted, so it locks the definition R checked, not a later rewrite.
"""
from __future__ import annotations

import pandas as pd

from scripts import rr3_empirical_rho as rho

IDX = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
EQ = pd.Series([100000.0, 100123.456, 99987.004, 100250.1], index=IDX)


def test_the_definition_is_byte_stable():
    assert rho.trial_key(EQ) == "9b4c7af0ffb1f6157b83ce49ca6f155d"


def test_sub_cent_floating_point_drift_is_the_same_trial():
    """T-057c: the same config in another container differs in the last float bits."""
    assert rho.trial_key(EQ + 1e-7) == rho.trial_key(EQ)


def test_a_one_cent_difference_is_a_different_trial():
    assert rho.trial_key(EQ.where(EQ.index != IDX[2], EQ.iloc[2] + 0.01)) != rho.trial_key(EQ)


def test_the_same_equity_on_other_dates_is_a_different_trial():
    shifted = pd.Series(EQ.values, index=IDX + pd.Timedelta(days=7))
    assert rho.trial_key(shifted) != rho.trial_key(EQ)


def test_the_population_pass_uses_the_same_definition(tmp_path):
    """rr3b_population_pass must key a run exactly as rr3_empirical_rho does."""
    from scripts import rr3b_population_pass as pop
    days = pd.bdate_range("2023-01-02", periods=120)
    eq = 100_000 * (1 + pd.Series(range(120), index=days) * 1e-4 + (pd.Series(range(120), index=days) % 7) * 3e-4)
    run = tmp_path / "camp" / "12345678-0000-0000-0000-000000000000"
    run.mkdir(parents=True)
    pd.DataFrame({"timestamp": days, "equity": eq.values}).to_csv(run / "portfolio_snapshots.csv", index=False)
    runs = rho.discover_runs([("s3", tmp_path)])
    keyed = pop.trial_keys(runs)
    (rid, rec), = keyed.items()
    assert rec["trial_key"] == rho.trial_key(rho.daily_equity(runs[rid]["snapshot"]))
