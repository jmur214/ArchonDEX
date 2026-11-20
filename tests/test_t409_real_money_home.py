"""Tests for scripts/t409_real_money_home.py (T-409 decision study, prereg rev. 3).

Hand-computed tax and lot cases, fail-closed input checks, the halting controls, determinism and the
synthetic-panel plumbing. The data-backed control test runs only when T409_CONTROL_ROOT points at a tree
holding the pinned control files (read-only).
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.metrics_engine import MetricsEngine
from scripts import t409_real_money_home as m


# ------------------------------------------------------------------------------------------- tax ----
def test_bracket_tax_matches_rev_proc_2025_32_cumulative_amounts():
    assert m.bracket_tax(12_400, 1.0) == pytest.approx(1_240.0)
    assert m.bracket_tax(50_400, 1.0) == pytest.approx(5_800.0)
    assert m.bracket_tax(105_700, 1.0) == pytest.approx(17_966.0)
    assert m.bracket_tax(201_775, 1.0) == pytest.approx(41_024.0)
    assert m.bracket_tax(256_225, 1.0) == pytest.approx(58_448.0)
    assert m.bracket_tax(640_600, 1.0) == pytest.approx(192_979.25)
    assert m.bracket_tax(2 * 105_700, 2.0) == pytest.approx(2 * 17_966.0)


def test_school_year_long_term_gain_is_zero_rate_federally():
    y = m.TaxYear(qual=1_000.0, lt=20_000.0)
    tax, st_cf, lt_cf, d = m.annual_tax(y, wages=8_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["at0"] == pytest.approx(21_000.0)
    assert d["pref"] == pytest.approx(0.0) and d["fed_ord"] == pytest.approx(0.0)
    assert tax == pytest.approx(1_050.0)          # state only
    assert (st_cf, lt_cf) == (0.0, 0.0)


def test_post_school_year_hand_case():
    y = m.TaxYear(qual=2_000.0, ordinary=1_000.0, lt=10_000.0)
    tax, _, _, d = m.annual_tax(y, wages=160_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["fed_ord"] == pytest.approx(240.0)   # 1,000 at 24 %
    assert d["pref"] == pytest.approx(1_800.0)    # 12,000 at 15 %
    assert d["niit"] == pytest.approx(0.0)        # MAGI 173,000 < 200,000
    assert tax == pytest.approx(240 + 1_800 + 650)


def test_loss_offset_3000_and_carryforward_character():
    y = m.TaxYear(st=-1_000.0, lt=-5_000.0)
    tax, st_cf, lt_cf, d = m.annual_tax(y, wages=160_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["deduction"] == pytest.approx(3_000.0)
    assert tax == pytest.approx(-720.0)           # 3,000 x 24 % against wages
    assert st_cf == pytest.approx(0.0) and lt_cf == pytest.approx(3_000.0)
    # the $3,000 is nominal-fixed: at idx 2 it is still $3,000
    _, _, _, d2 = m.annual_tax(y, wages=320_000.0, idx=2.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d2["deduction"] == pytest.approx(3_000.0)


def test_niit_crossing_and_carryforward_use():
    y = m.TaxYear(lt=20_000.0)
    tax, _, _, d = m.annual_tax(y, wages=195_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["niit"] == pytest.approx(0.038 * 15_000.0)
    assert tax == pytest.approx(3_000.0 + 570.0 + 1_000.0)
    y2 = m.TaxYear(st=5_000.0)
    _, st_cf, _, d3 = m.annual_tax(y2, wages=160_000.0, idx=1.0, state=0.0, st_cf=2_000.0, lt_cf=0.0)
    assert d3["fed_ord"] == pytest.approx(0.24 * 3_000.0) and st_cf == 0.0


def test_zero_rate_room_counts_ordinary_income_and_existing_gains():
    y = m.TaxYear(qual=1_000.0, ordinary=500.0, lt=2_000.0)
    room = m.zero_rate_room(y, wages=10_000.0, idx=1.0, st_cf=0.0, lt_cf=0.0)
    assert room == pytest.approx(49_450.0 - 500.0 - 3_000.0)


# ------------------------------------------------------------------------------------------ lots ----
def test_hifo_sells_highest_basis_first_and_classifies_holding_period():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=0)     # 100 shares, basis 100
    b.buy(100.0, 2.0, t=10)    # 50 shares, basis 100 (higher basis per share)
    proceeds, st, lt = b.sell_hifo(100.0, 2.0, t=12)
    assert proceeds == pytest.approx(100.0) and st == pytest.approx(0.0) and lt == pytest.approx(0.0)
    proceeds, st, lt = b.sell_hifo(50.0, 2.0, t=12)
    assert proceeds == pytest.approx(50.0) and lt == pytest.approx(25.0) and st == pytest.approx(0.0)
    assert b.value(2.0) == pytest.approx(150.0) and b.total_basis == pytest.approx(75.0)


def test_harvest_realises_loss_and_resets_basis_and_clock():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=0)
    st, lt = b.harvest(0.90, t=5, theta=0.05)
    assert st == pytest.approx(-10.0) and lt == 0.0
    assert b.total_basis == pytest.approx(90.0) and b.month[0] == 5
    st, lt = b.harvest(0.88, t=6, theta=0.05)   # only 2.2 % below the new basis
    assert st == 0.0 and lt == 0.0


def test_realize_lt_gains_upto_stops_at_the_room():
    b = m.LotBook()
    b.buy(70.0, 1.0, t=-24)            # value 100 at price 100/70 -> gain 30
    b.buy(90.0, 1.0, t=-30)            # value ~128.6 -> gain ~38.6, lower gain fraction? check below
    price = 100.0 / 70.0
    proceeds, gain = b.realize_lt_gains_upto(35.0, price, t=0)
    assert gain == pytest.approx(35.0)
    assert b.gain(price) == pytest.approx((100 - 70) + (90 * price - 90) - 35.0)


def test_s0_realises_the_legacy_gain_and_k1_does_not():
    panel = synthetic_panel(months=24)
    path = m.make_path(m.panel_arrays(panel))
    # A high-wage year: S0's sale is taxed at 15 % + state now, K1 defers the same gain.
    own = m.Owner(g=0.30, school_start=10, wages_pre=160_000.0)
    arms = {a.name: a for a in m.ARMS}
    s0, k1 = m.simulate(arms["S0"], own, path), m.simulate(arms["K1"], own, path)
    assert s0.pre_tax_real < k1.pre_tax_real - 1_000.0          # ~ (0.15 + 0.05) x 7,500 paid early
    own0 = replace(own, g=0.0)
    s0g0, k1g0 = m.simulate(arms["S0"], own0, path), m.simulate(arms["K1"], own0, path)
    assert s0g0.pre_tax_real > k1g0.pre_tax_real                 # no gain: switching only cuts the fee
    # At the default $60k wage, year 1 has 0 % room (49,450 - 43,900 = 5,550), so part of S0's sale is free.
    s0lo = m.simulate(arms["S0"], m.Owner(g=0.30, school_start=10), path)
    k1lo = m.simulate(arms["K1"], m.Owner(g=0.30, school_start=10), path)
    assert s0lo.terminal_real > k1lo.terminal_real


# --------------------------------------------------------------------------------- fail closed ----
def test_missing_and_mismatched_inputs_halt(tmp_path):
    with pytest.raises(m.InputError):
        m.require_file(tmp_path / "nope.csv")
    f = tmp_path / "a.csv"
    f.write_text("x")
    with pytest.raises(m.InputError):
        m.require_file(f, "0" * 32)
    (tmp_path / "manifest.json").write_text(json.dumps({"files": {}}))
    with pytest.raises(m.InputError):
        m.read_manifest(tmp_path, ["french"])


def test_french_sentinel_halts(tmp_path):
    lines = ["header", "", ",Mkt-RF,SMB,HML,RF"]
    d = pd.bdate_range("2000-01-03", periods=1200)
    for i, day in enumerate(d):
        v = "-99.99" if i == 600 else "0.10"
        lines.append(f"{day:%Y%m%d},{v},0.00,0.00,0.01")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("F-F_Research_Data_Factors_daily.csv", "\n".join(lines))
    p = tmp_path / "ff.zip"
    p.write_bytes(buf.getvalue())
    with pytest.raises(m.InputError, match="sentinel"):
        m.load_french_daily(p)


def test_dividend_yield_carry_cap_and_cpi_gap_halt(tmp_path):
    dates = pd.date_range("2000-01-01", "2020-12-01", freq="MS")
    df = pd.DataFrame({"date": dates, "price": 100.0, "dividend": 2.0})
    p = tmp_path / "sh.csv"
    df.to_csv(p, index=False)
    dp, carried = m.load_dividend_yield(p, pd.Period("2022-06", "M"))
    assert carried == 18 and dp.iloc[-1] == pytest.approx(0.02)
    with pytest.raises(m.InputError, match="carried"):
        m.load_dividend_yield(p, pd.Period("2023-12", "M"))
    c = pd.DataFrame({"date": pd.date_range("2000-01-01", periods=10, freq="MS").delete(4), "value": 100.0})
    cp = tmp_path / "cpi.csv"
    c.to_csv(cp, index=False)
    with pytest.raises(m.InputError, match="missing months"):
        m.load_cpi(cp)


def test_only_the_declared_october_2025_cpi_gap_is_interpolated(tmp_path):
    months = pd.date_range("2025-07-01", "2026-01-01", freq="MS")
    vals = {d: 300.0 + i for i, d in enumerate(months)}
    df = pd.DataFrame({"date": [d for d in months if d != pd.Timestamp("2025-10-01")],
                       "value": [v for d, v in vals.items() if d != pd.Timestamp("2025-10-01")]})
    p = tmp_path / "cpi.csv"
    df.to_csv(p, index=False)
    s = m.load_cpi(p)
    assert s[pd.Period("2025-10", "M")] == pytest.approx((302.0 * 304.0) ** 0.5)
    assert len(s) == len(months)


def test_run_controls_halts_when_a_control_does_not_reproduce(monkeypatch):
    good = {"t399_bar": 3_363_893.0, "t399_static_2x": 8_864_568.0, "window": ["a", "b"]}
    monkeypatch.setattr(m, "control_t399", lambda root: dict(good))
    monkeypatch.setattr(m, "control_t287", lambda root: {"t287_bh_spy": 929_498.0, "t287_schwab_like": 494_701.0})
    assert all(v["pass"] for v in m.run_controls(Path("."))["checks"].values())
    bad = dict(good, t399_static_2x=8_864_570.5)
    monkeypatch.setattr(m, "control_t399", lambda root: bad)
    with pytest.raises(m.ControlFailed):
        m.run_controls(Path("."))


def test_refuses_to_write_under_the_control_roots_data(tmp_path):
    (tmp_path / "data").mkdir()
    args = m.argparse.Namespace(smoke=True, inputs=str(tmp_path), out=str(tmp_path / "data" / "t409"),
                                control_root=str(tmp_path), jst=False)
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(args)


@pytest.mark.skipif(not os.environ.get("T409_CONTROL_ROOT"), reason="needs the pinned control files")
def test_controls_reproduce_on_the_pinned_files():
    out = m.run_controls(Path(os.environ["T409_CONTROL_ROOT"]))
    assert all(v["pass"] for v in out["checks"].values())


# ------------------------------------------------------------------------------------- vehicles ----
def test_bar252_mode_reproduces_the_t315_lev_daily_formula():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2001-01-02", periods=500)
    r = rng.normal(0.0004, 0.01, len(idx))
    cash = np.full(len(idx), 0.0001)
    fee, fin = m.accrual_fractions(idx, "bar252")
    got = m.levered_fund_returns(r + 0.0009 / 252, cash, 2.0, 0.0060, 0.0089, fee, fin)
    want = 2.0 * (r + 0.0009 / 252) - 1.0 * (cash + 0.0060 / 252) - 0.0089 / 252
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-15)


def test_year_change_mask_is_positional():
    idx = pd.DatetimeIndex(["2020-12-30", "2020-12-31", "2021-01-04", "2021-01-05", "2022-01-03"])
    assert m.year_change_mask(idx).tolist() == [True, False, True, False, True]


def test_monthly_belief_shift_matches_the_daily_arithmetic_shift():
    rng = np.random.default_rng(1)
    days = pd.bdate_range("2010-03-01", "2010-03-31")
    r = rng.normal(0.0005, 0.012, len(days))
    d = np.concatenate([[1.0], np.diff(days.values).astype("timedelta64[D]").astype(float)])
    h = -0.03
    for k in (1.0, 2.0):
        exact = np.prod(1 + k * r + k * h * d / 365.25) - 1
        approx = (1 + (np.prod(1 + k * r) - 1)) * np.exp(k * h * d.sum() / 365.25) - 1
        assert abs(exact - approx) < 2e-4


def test_stationary_bootstrap_is_deterministic_and_has_the_mean_block():
    a = m.stationary_bootstrap(500, 480, 20, 60, np.random.default_rng(5))
    b = m.stationary_bootstrap(500, 480, 20, 60, np.random.default_rng(5))
    np.testing.assert_array_equal(a, b)
    assert a.min() >= 0 and a.max() < 500
    runs = (np.diff(a, axis=1) != 1) & ~((a[:, :-1] == 499) & (a[:, 1:] == 0))
    mean_block = a.size / (runs.sum() + a.shape[0])
    assert 40 < mean_block < 85


def test_contribution_schedule_pauses_roth_in_school_and_pv_is_exact():
    own = m.Owner(school_start=2, school_years=3, c_taxable_month=100.0, roth_contrib=1_200.0, real_discount=0.0)
    tax_c, roth_c, pv = m.contribution_schedule(own, 60)
    assert roth_c[0] == 1_200.0 and roth_c[12] == roth_c[24] == roth_c[36] == 0.0 and roth_c[48] == 1_200.0
    assert pv[0] == pytest.approx(100.0 * 59 + 1_200.0)   # undiscounted flows after month 0


# ------------------------------------------------------------------------------------ plumbing ----
def synthetic_panel(months: int = 180, start: str = "1985-01", seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.period_range(start, periods=months, freq="M")
    eq = rng.normal(0.008, 0.045, months)
    rf = np.full(months, 0.003)
    return pd.DataFrame({
        "voo": eq - 0.0003 / 12, "robo": eq - 0.0015 / 12,
        "sso": 2 * eq - (rf + 0.0086 / 12) - 0.0089 / 12 - 0.5 * 0.045 ** 2,
        "upro": 3 * eq - 2 * (rf + 0.0085 / 12) - 0.009 / 12 - 1.5 * 0.045 ** 2,
        "rf": rf, "days": np.full(months, 30.4), "cash_robo": rf - 0.0003,
        "infl": np.full(months, 0.0025), "dy": np.full(months, 0.02 / 12),
    }, index=idx)


TINY = m.Config(horizon_years=5, cohort_starts=(1986, 1987, 1988), n_paths=6, block_mean=12,
                block_sensitivity=(), rows=(0.0, -0.02), param_rows=(0.0,), g_grid=(0.0, 0.30),
                g_primary=0.30, owner_sensitivity=(("roth_25k", (("roth0", 25_000.0),)),
                                                   ("step_up", (("liquidate", False),))),
                owner_sensitivity_rows=(0.0,), smoke=True)


def test_owner_sensitivities_move_in_the_expected_direction():
    panel = synthetic_panel()
    res = m.study(panel, TINY, m.Owner(), log=lambda s: None)
    base = res["results"]["cohorts"]["h=+0.00"]["g=0.30"]
    sens = res["results"]["owner_sensitivity"]
    step = sens["step_up"]["h=+0.00"]["cohorts"]
    assert step["K1"]["median"] > base["K1"]["median"]            # no year-40 gain tax
    assert "roth_25k" in sens and set(sens["roth_25k"]["h=+0.00"]) == {"cohorts", "bootstrap"}


def test_roth_capacity_bounds_household_leverage():
    """A fixed 1.5x household target: with a $5k Roth (share 1/6) SSO in the Roth can reach only ~1.17x;
    with a $25k Roth (share 1/2) it reaches 1.5x. On a path where leverage pays, the bigger Roth gains more."""
    n = 24
    arrays = {"voo": np.full(n, 0.01), "robo": np.full(n, 0.01), "sso": np.full(n, 0.02),
              "upro": np.full(n, 0.03), "rf": np.zeros(n), "days": np.full(n, 30.4),
              "cash_robo": np.zeros(n), "infl": np.zeros(n), "dy": np.zeros(n)}
    path = m.make_path(arrays)
    arm = m.Arm("S15", "k1", roth="static", static_L=1.5, decision="B")
    k1 = next(a for a in m.ARMS if a.name == "K1")
    ratio = {}
    for roth0 in (5_000.0, 25_000.0):
        own = m.Owner(taxable0=25_000.0, roth0=roth0, g=0.0, c_taxable_month=0.0, roth_contrib=0.0,
                      state_rate=0.0, liquidate=False)
        ratio[roth0] = m.simulate(arm, own, path).pre_tax_real / m.simulate(k1, own, path).pre_tax_real
    assert ratio[25_000.0] > ratio[5_000.0] > 1.0


def test_study_is_deterministic_and_the_arms_differ():
    panel = synthetic_panel()
    a = m.study(panel, TINY, m.Owner(taxable0=60_000.0), log=lambda s: None)
    b = m.study(panel, TINY, m.Owner(taxable0=60_000.0), log=lambda s: None)
    assert m.canonical_md5(a) == m.canonical_md5(b)
    row = a["results"]["bootstrap"]["h=+0.00"]["g=0.30"]
    for x, y in (("K0", "K1"), ("K1", "B3"), ("B1", "B4"), ("S0", "K1"), ("B1", "B1_upro")):
        assert row[x]["E_log"] != row[y]["E_log"], (x, y)
    assert row["REF"]["dlog_vs_ref_mean"] == 0.0
    # K0 starts above the $50k activation balance here, so its harvesting must have run
    assert row["K0"]["tlh_years_median"] > 0 and row["K0_noTLH"]["tlh_years_median"] == 0
    assert set(a["choice"]["h=+0.00"]) == {"A", "B"}


def test_lower_belief_row_lowers_levered_wealth_more_than_one_x():
    panel = synthetic_panel()
    res = m.study(panel, TINY, m.Owner(), log=lambda s: None)
    hi, lo = res["results"]["cohorts"]["h=+0.00"]["g=0.30"], res["results"]["cohorts"]["h=-0.02"]["g=0.30"]
    drop_k1 = hi["K1"]["E_log"] - lo["K1"]["E_log"]
    drop_b3 = hi["B3"]["E_log"] - lo["B3"]["E_log"]
    assert drop_b3 > drop_k1 > 0


def test_gate_uses_monthly_periods_for_sortino():
    panel = synthetic_panel()
    g = m.gate_and_sortino(panel, seed=0)
    assert g["voo"]["sortino_point"] == pytest.approx(MetricsEngine.sortino_ratio(panel["voo"], periods=12))
    assert g["voo"]["sortino_point"] != pytest.approx(MetricsEngine.sortino_ratio(panel["voo"], periods=252))
