"""Tests for scripts/t409_real_money_home.py (T-409 decision study, prereg rev. 5).

Hand-computed tax and lot cases, a fuzz against an independently written Form 1040 worksheet, fail-closed
input checks, the halting controls, the choice rule, determinism and the synthetic-panel plumbing. The
data-backed control test runs only when T409_CONTROL_ROOT points at a tree holding the pinned files.
"""
from __future__ import annotations

import argparse
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


def test_school_year_unused_deduction_shelters_gains():
    y = m.TaxYear(qual=1_000.0, lt=20_000.0)
    tax, st_cf, lt_cf, d = m.annual_tax(y, wages=8_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["taxable_income"] == pytest.approx(12_900.0)   # 8,000 + 21,000 - 16,100
    assert d["at0"] == pytest.approx(12_900.0)              # the other 8,100 sits under the deduction
    assert d["fed"] == pytest.approx(0.0)
    assert tax == pytest.approx(1_050.0)                     # state only
    assert (st_cf, lt_cf) == (0.0, 0.0)


def test_school_year_ordinary_and_short_term_use_the_unused_deduction_first():
    y = m.TaxYear(qual=1_000.0, ordinary=2_000.0, st=3_000.0, lt=10_000.0)
    tax, _, _, d = m.annual_tax(y, wages=8_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["taxable_income"] == pytest.approx(7_900.0) and d["fed"] == pytest.approx(0.0)
    assert tax == pytest.approx(800.0)
    y2 = m.TaxYear(st=20_000.0)
    tax2, _, _, d2 = m.annual_tax(y2, wages=8_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d2["fed"] == pytest.approx(1_190.0)                # 11,900 at 10 %, not 20,000 from the first dollar
    assert tax2 == pytest.approx(2_190.0)


def test_qdcg_worksheets_last_step_takes_the_smaller_of_the_two_taxes():
    """Hand case, from Rev. Proc. 2025-32 rows. Taxable income 50,450: ordinary 49,450 (the top of the 0 % room) +
    1,000 of long-term gain. Worksheet: tax(49,450) = 1,240 + 12 % x 37,050 = 5,686, plus 15 % of the 1,000 =
    5,836. Ordinary tax on 50,450 = 5,800 + 22 % x 50 = 5,811, which is smaller. Incremental 125, not 150."""
    y = m.TaxYear(lt=1_000.0)
    _, _, _, d = m.annual_tax(y, wages=16_100.0 + 49_450.0, idx=1.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d["taxable_income"] == pytest.approx(50_450.0)
    assert d["fed"] == pytest.approx(125.0)


def test_qdcg_worksheet_smaller_of_step():
    y = m.TaxYear(lt=70_000.0)
    _, _, _, d = m.annual_tax(y, wages=0.0, idx=1.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d["taxable_income"] == pytest.approx(53_900.0)
    assert d["pref"] == pytest.approx(0.15 * (53_900.0 - 49_450.0))


def test_post_school_year_hand_case():
    y = m.TaxYear(qual=2_000.0, ordinary=1_000.0, lt=10_000.0)
    tax, _, _, d = m.annual_tax(y, wages=160_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["fed_ord"] == pytest.approx(240.0)
    assert d["pref"] == pytest.approx(1_800.0)
    assert d["niit"] == pytest.approx(0.0)
    assert tax == pytest.approx(240 + 1_800 + 650)


def test_loss_offset_3000_and_carryforward_character():
    y = m.TaxYear(st=-1_000.0, lt=-5_000.0)
    tax, st_cf, lt_cf, d = m.annual_tax(y, wages=160_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["deduction_used"] == pytest.approx(3_000.0)
    assert tax == pytest.approx(-720.0)
    assert st_cf == pytest.approx(0.0) and lt_cf == pytest.approx(3_000.0)
    _, _, _, d2 = m.annual_tax(y, wages=320_000.0, idx=2.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d2["deduction"] == pytest.approx(3_000.0)          # nominal-fixed


def test_negative_taxable_income_does_not_use_up_the_3000_deduction():
    y = m.TaxYear(lt=-10_000.0)
    tax, st_cf, lt_cf, d = m.annual_tax(y, wages=8_000.0, idx=1.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d["deduction_used"] == pytest.approx(0.0)
    assert lt_cf == pytest.approx(10_000.0) and st_cf == 0.0 and tax == pytest.approx(0.0)


def test_niit_crossing_counts_the_3000_offset_and_carryforward_use():
    y = m.TaxYear(lt=20_000.0)
    tax, _, _, d = m.annual_tax(y, wages=195_000.0, idx=1.0, state=0.05, st_cf=0.0, lt_cf=0.0)
    assert d["niit"] == pytest.approx(0.038 * 15_000.0)
    assert tax == pytest.approx(3_000.0 + 570.0 + 1_000.0)
    y2 = m.TaxYear(ordinary=5_000.0, lt=-8_000.0)
    _, _, _, d2 = m.annual_tax(y2, wages=205_000.0, idx=1.0, state=0.0, st_cf=0.0, lt_cf=0.0)
    assert d2["niit"] == pytest.approx(0.038 * 2_000.0)       # NII 5,000 - 3,000 (Form 8960)
    y3 = m.TaxYear(st=5_000.0)
    _, st_cf, _, d3 = m.annual_tax(y3, wages=160_000.0, idx=1.0, state=0.0, st_cf=2_000.0, lt_cf=0.0)
    assert d3["fed_ord"] == pytest.approx(0.24 * 3_000.0) and st_cf == 0.0


def reference_1040(qual, ordinary, st, lt, wages, st_cf, lt_cf):
    """An independent Form 1040 path (Schedule D lines 7/15/16/21, the QDCG worksheet, the Capital Loss
    Carryover Worksheet, Form 8960), idx = 1, state 0. Written separately from `annual_tax`."""
    l7, l15 = st - st_cf, lt - lt_cf
    l16 = l7 + l15
    l21 = 0.0 if l16 >= 0 else -min(3_000.0, -l16)
    cap = l16 if l16 >= 0 else l21
    agi = wages + ordinary + qual + cap
    line15 = agi - 16_100.0
    ti = max(0.0, line15)
    ncg = max(0.0, min(l15, l16)) if l16 > 0 else 0.0
    w4 = min(ti, qual + ncg)
    w5 = ti - w4
    w7 = min(ti, 49_450.0)
    w8 = min(w5, w7)
    w9 = w7 - w8
    w10, w11 = min(ti, w4), w9
    w12 = w10 - w11
    w13 = min(ti, 545_500.0)
    w15 = max(0.0, w13 - (w5 + w9))
    w16 = min(w12, w15)
    w17 = w12 - w16
    worksheet = m.bracket_tax(w5, 1.0) + 0.15 * w16 + 0.20 * w17
    tax = min(worksheet, m.bracket_tax(ti, 1.0)) - m.bracket_tax(max(0.0, wages - 16_100.0), 1.0)
    nii = max(0.0, ordinary + qual + cap)
    niit = 0.038 * min(nii, max(0.0, agi - 200_000.0))
    st_new = lt_new = 0.0
    if l16 < 0:
        c3 = max(0.0, line15 + (-l21))
        c4 = min(-l21, c3)
        c5, c6 = max(0.0, -l7), max(0.0, l15)
        st_new = max(0.0, c5 - (c4 + c6))
        c9, c10 = max(0.0, -l15), max(0.0, l7)
        c11 = max(0.0, c4 - c5)
        lt_new = max(0.0, c9 - (c10 + c11))
    return tax + niit, st_new, lt_new


def test_annual_tax_matches_an_independent_form_1040_path_on_random_years():
    rng = np.random.default_rng(1040)
    for _ in range(3000):
        wages = float(rng.choice([0, 8_000, 30_000, 60_000, 160_000, 230_000, 700_000]))
        qual, ordi = float(rng.uniform(0, 30_000)), float(rng.uniform(0, 15_000))
        st, lt = float(rng.normal(0, 25_000)), float(rng.normal(0, 60_000))
        st_cf, lt_cf = float(rng.choice([0, 0, 2_500, 9_000])), float(rng.choice([0, 0, 4_000, 20_000]))
        got, gst, glt, _ = m.annual_tax(m.TaxYear(qual=qual, ordinary=ordi, st=st, lt=lt), wages, 1.0, 0.0, st_cf, lt_cf)
        want, wst, wlt = reference_1040(qual, ordi, st, lt, wages, st_cf, lt_cf)
        assert got == pytest.approx(want, abs=0.01), (wages, qual, ordi, st, lt, st_cf, lt_cf)
        assert gst == pytest.approx(wst, abs=0.01) and glt == pytest.approx(wlt, abs=0.01)


def test_zero_rate_room_includes_the_unused_deduction():
    room = m.zero_rate_room(m.TaxYear(), wages=8_000.0, idx=1.0, st_cf=0.0, lt_cf=0.0)
    assert room == pytest.approx(49_450.0 + 8_100.0, abs=0.01)
    y = m.TaxYear(qual=1_000.0, ordinary=500.0, lt=2_000.0)
    room2 = m.zero_rate_room(y, wages=30_000.0, idx=1.0, st_cf=0.0, lt_cf=0.0)
    assert room2 == pytest.approx(49_450.0 - (30_000.0 - 16_100.0 + 500.0 + 1_000.0 + 2_000.0), abs=0.01)


# ------------------------------------------------------------------------------------------ lots ----
def test_hifo_sells_highest_basis_first_and_classifies_holding_period():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=0)
    b.buy(100.0, 2.0, t=10)
    proceeds, st, lt = b.sell_hifo(100.0, 2.0, t=12)
    assert proceeds == pytest.approx(100.0) and st == pytest.approx(0.0) and lt == pytest.approx(0.0)
    proceeds, st, lt = b.sell_hifo(50.0, 2.0, t=12)
    assert proceeds == pytest.approx(50.0) and lt == pytest.approx(25.0) and st == pytest.approx(0.0)
    assert b.value(2.0) == pytest.approx(150.0) and b.total_basis == pytest.approx(75.0)


def test_wash_sale_disallows_the_loss_and_moves_it_to_the_replacement():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=0)
    _, st, lt = b.sell_hifo(40.0, 0.8, t=3, wash=True)       # 50 shares sold for 40: a 10 loss
    assert st == 0.0 and lt == 0.0 and b.wash_carry == pytest.approx(10.0)
    assert b.gain(0.8) == pytest.approx(40.0 - 50.0 - 10.0)
    b.buy(50.0, 0.8, t=4)                                     # the replacement absorbs the basis
    assert b.wash_carry == 0.0 and b.total_basis == pytest.approx(50.0 + 50.0 + 10.0)
    _, st2, _ = b.sell_hifo(40.0, 0.8, t=5, wash=False)
    assert st2 < 0


def test_prorata_rebalance_realises_gains_only():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=-24)        # will be a gain lot
    b.buy(100.0, 2.0, t=-20)        # will be a loss lot at price 1.5
    st, lt = b.realize_gains_prorata(0.10, 1.5, t=0)
    assert st == 0.0 and lt == pytest.approx(0.10 * (150.0 - 100.0))
    assert b.value(1.5) == pytest.approx(150.0 + 75.0)
    assert b.gain(1.5) == pytest.approx((150.0 - 100.0) + (75.0 - 100.0) - lt)


def test_harvest_realises_loss_and_resets_basis_and_clock():
    b = m.LotBook()
    b.buy(100.0, 1.0, t=0)
    st, lt = b.harvest(0.90, t=5, theta=0.05)
    assert st == pytest.approx(-10.0) and lt == 0.0
    assert b.total_basis == pytest.approx(90.0) and b.month[0] == 5
    st, lt = b.harvest(0.88, t=6, theta=0.05)
    assert st == 0.0 and lt == 0.0


def test_realize_lt_gains_upto_stops_at_the_room():
    b = m.LotBook()
    b.buy(70.0, 1.0, t=-24)
    b.buy(90.0, 1.0, t=-30)
    price = 100.0 / 70.0
    proceeds, gain = b.realize_lt_gains_upto(35.0, price, t=0)
    assert gain == pytest.approx(35.0)
    assert b.gain(price) == pytest.approx((100 - 70) + (90 * price - 90) - 35.0)


def test_s0_realises_the_legacy_gain_and_k1_does_not():
    panel = synthetic_panel(months=24)
    path = m.make_path(m.panel_arrays(panel))
    own = m.Owner(g=0.30, school_start=10, wages_pre=160_000.0)
    arms = {a.name: a for a in m.ARMS}
    s0, k1 = m.simulate(arms["S0"], own, path), m.simulate(arms["K1"], own, path)
    assert s0.pre_tax_real < k1.pre_tax_real - 1_000.0
    own0 = replace(own, g=0.0)
    s0g0, k1g0 = m.simulate(arms["S0"], own0, path), m.simulate(arms["K1"], own0, path)
    assert s0g0.pre_tax_real > k1g0.pre_tax_real
    s0lo = m.simulate(arms["S0"], m.Owner(g=0.30, school_start=10), path)
    k1lo = m.simulate(arms["K1"], m.Owner(g=0.30, school_start=10), path)
    assert s0lo.terminal_real > k1lo.terminal_real


def test_liquidation_goes_through_annual_tax_with_the_20pct_bracket_and_niit():
    book = m.LotBook()
    book.buy(100_000.0, 1.0, t=-24)
    books = {"voo": book, "robo": m.LotBook(), "sso": m.LotBook()}
    P = {"voo": np.array([1.0, 11.0]), "robo": np.ones(2), "sso": np.ones(2)}
    own = m.Owner(state_rate=0.0, liq_wages=160_000.0)
    tax = m.liquidation_tax(books, P, 1, m.TaxYear(), own, 1.0, 0.0, 0.0)
    want, _, _, d = m.annual_tax(m.TaxYear(lt=1_000_000.0), 160_000.0, 1.0, 0.0, 0.0, 0.0)
    assert tax == pytest.approx(want)
    assert d["niit"] > 0 and tax > 0.15 * 1_000_000.0 + 1e-6


# --------------------------------------------------------------------------------------- the Roth ----
def test_roth_schedule_school_rule_and_post_school_backdoor_flag():
    assert m.Owner().roth_in_school is False                  # the primary: no source for $7,500 on ~$8k of wages
    own = m.Owner(school_start=2, school_years=3, c_taxable_month=100.0, roth_contrib=1_200.0, real_discount=0.0,
                  roth_in_school=True)
    _, roth_c, pv = m.contribution_schedule(own, 60)
    assert list(roth_c[::12]) == [1_200.0] * 5                # school wages 8,000 >= 1,200: contributes
    assert pv[0] == pytest.approx(100.0 * 59 + 4 * 1_200.0)
    big = replace(own, roth_contrib=9_000.0)
    _, rc2, _ = m.contribution_schedule(big, 60)
    assert list(rc2[::12]) == [9_000.0, 0.0, 0.0, 0.0, 9_000.0]   # school wages 8,000 < 9,000: none
    nopost = replace(own, roth_post_school=False)
    _, rc3, _ = m.contribution_schedule(nopost, 60)
    assert list(rc3[::12]) == [1_200.0, 1_200.0, 1_200.0, 1_200.0, 0.0]
    noschool = replace(own, roth_in_school=False)
    _, rc4, _ = m.contribution_schedule(noschool, 60)
    assert list(rc4[::12]) == [1_200.0, 0.0, 0.0, 0.0, 1_200.0]


def test_the_automatic_contribution_can_pause_in_school():
    own = m.Owner(school_start=2, school_years=2, c_taxable_month=100.0, taxable_in_school=False)
    tax_c, _, _ = m.contribution_schedule(own, 60)
    assert tax_c[:12].sum() == 1_200.0 and tax_c[12:36].sum() == 0.0 and tax_c[36:].sum() == 2_400.0
    assert m.contribution_schedule(m.Owner(), 12)[0].sum() == 12 * 500.0


def test_roth_capacity_bounds_household_leverage():
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


def test_a_regenerated_manifest_cannot_launder_a_changed_input(tmp_path):
    f = tmp_path / m.INPUT_NAMES["shiller"]
    f.write_text("date,price,dividend\n2000-01-01,1,1\n")
    (tmp_path / "manifest.json").write_text(json.dumps({"files": {f.name: m.md5_of(f)}}))
    with pytest.raises(m.InputError, match="frozen input"):
        m.read_manifest(tmp_path, ["shiller"])
    assert m.read_manifest(tmp_path, ["shiller"], pinned=None)["shiller"] == f


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


def test_every_preregistered_cohort_must_fit():
    panel = synthetic_panel(months=100, start="1990-01")
    with pytest.raises(m.InputError, match="cohort 1995"):
        m.cohort_index_paths(panel, (1990, 1995), 60)
    with pytest.raises(m.InputError, match="outside"):
        m.cohort_index_paths(panel, (1980,), 12)


def test_run_controls_halts_when_a_control_does_not_reproduce(monkeypatch):
    good = {"t399_bar": 3_363_893.0, "t399_static_2x": 8_864_568.0, "window": ["a", "b"]}
    monkeypatch.setattr(m, "control_t399", lambda root: dict(good))
    monkeypatch.setattr(m, "control_t287", lambda root: {"t287_bh_spy": 929_498.0, "t287_schwab_like": 494_701.0})
    assert all(v["pass"] for v in m.run_controls(Path("."))["checks"].values())
    bad = dict(good, t399_static_2x=8_864_570.5)
    monkeypatch.setattr(m, "control_t399", lambda root: bad)
    with pytest.raises(m.ControlFailed):
        m.run_controls(Path("."))


def test_study_path_control_passes_and_halts_on_a_wrong_simulate(monkeypatch):
    panel = synthetic_panel(months=180, start="1985-01")
    out = m.control_study_path(panel)
    assert out["pass"] and out["abs_diff"] <= m.STUDY_CONTROL_TOL
    real = m.simulate
    monkeypatch.setattr(m, "simulate", lambda arm, own, path: replace(real(arm, own, path),
                                                                     terminal_real=real(arm, own, path).terminal_real + 0.02))
    with pytest.raises(m.ControlFailed, match="study-path"):
        m.control_study_path(panel)


def _run_args(tmp_path, **kw):
    base = dict(smoke=True, inputs=str(tmp_path), out=str(tmp_path / "out"), control_root=str(tmp_path),
                jst=False, decision_row=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_refuses_to_write_under_any_data_tree_even_through_a_symlink(tmp_path):
    (tmp_path / "data").mkdir()
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(_run_args(tmp_path, out=str(tmp_path / "data" / "t409")))
    link = tmp_path / "innocent"
    link.symlink_to(tmp_path / "data")
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(_run_args(tmp_path, out=str(link / "t409")))
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(_run_args(tmp_path, out=str(m.ROOT / "data" / "t409")))


def test_the_guard_also_refuses_the_main_trees_data_from_a_worktree(tmp_path, monkeypatch):
    main, wt = tmp_path / "main", tmp_path / "wt"
    (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
    (main / "data").mkdir()
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n")
    assert m.main_tree_of(wt) == main.resolve()
    monkeypatch.setattr(m, "ROOT", wt)
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(_run_args(tmp_path, control_root=str(wt), out=str(main / "data" / "t409")))
    with pytest.raises(m.InputError, match="refusing"):
        m.cmd_run(_run_args(tmp_path, control_root=str(tmp_path / "elsewhere"), out=str(main / "data" / "t409")))


def test_the_full_run_requires_jst_and_the_owners_decision_row(tmp_path):
    with pytest.raises(m.InputError, match="--jst"):
        m.cmd_run(_run_args(tmp_path, smoke=False, jst=False, decision_row="h=+0.00"))
    with pytest.raises(m.InputError, match="--decision-row"):
        m.cmd_run(_run_args(tmp_path, smoke=False, jst=True, decision_row=None))


@pytest.mark.skipif(not os.environ.get("T409_CONTROL_ROOT"), reason="needs the pinned control files")
def test_controls_reproduce_on_the_pinned_files():
    out = m.run_controls(Path(os.environ["T409_CONTROL_ROOT"]))
    assert all(v["pass"] for v in out["checks"].values())
    diag = out["diagnostics_not_gating"]
    assert diag["diag_spy_days_missing_from_t284_curve"] == 64
    assert diag["diag_bh_spy_calendar_complete"] == pytest.approx(1_025_315.53, abs=1.0)


# ----------------------------------------------------------------------------------- the choice ----
def _coh(arms, ratio=0.9):
    return {a: {"ratio_min": ratio} for a in arms}


def test_choice_band_is_per_decision_and_ignores_non_candidate_arms():
    raw = {"K1": np.zeros(400), "K0": np.full(400, 0.02), "B1_upro": np.zeros(400)}
    rng = np.random.default_rng(3)
    raw["K0"] = raw["K0"] + rng.normal(0, 0.01, 400)
    blocks = {12: {"K1": np.zeros(400), "K0": np.full(400, 0.019), "B1_upro": np.full(400, 0.05)},
              120: {"K1": np.zeros(400), "K0": np.full(400, 0.021), "B1_upro": np.full(400, -0.05)}}
    out = m.choose(raw, blocks, _coh(["K0", "K1"]), None, ("K0", "K1"), "K1", 0.5)
    assert out["choice"] == "K0"
    c = out["contrasts"]["K0"]
    assert c["band"] == pytest.approx(max(2 * c["paired_mcse"], c["block_spread"]))
    assert c["block_spread"] < 0.01                 # B1_upro's 0.10 spread is not part of decision A


def test_choice_takes_a_lower_arm_that_clearly_leads_when_the_top_arm_ties():
    rng = np.random.default_rng(4)
    raw = {"K1": np.zeros(400), "B1": 0.05 + rng.normal(0, 2.0, 400), "B2": 0.02 + rng.normal(0, 0.005, 400),
           "B3": np.zeros(400) - 0.01}
    raw["B1"] = raw["B1"] - raw["B1"].mean() + 0.05
    raw["B2"] = raw["B2"] - raw["B2"].mean() + 0.02
    out = m.choose(raw, {}, _coh(["K1", "B1", "B2", "B3"]), None, ("K1", "B1", "B2", "B3"), "K1", 0.5)
    assert out["contrasts"]["B1"]["distinct"] is False and out["contrasts"]["B2"]["distinct"] is True
    assert out["choice"] == "B2"


def test_the_band_uses_the_paired_se_not_the_spread_of_the_arms():
    rng = np.random.default_rng(11)
    common = rng.normal(12.0, 0.5, 400)                                  # the paths' shared luck
    raw = {"K1": common, "K0": common + 0.01 + rng.normal(0.0, 0.001, 400)}
    out = m.choose(raw, {}, _coh(["K0", "K1"]), None, ("K0", "K1"), "K1", 0.5)
    assert out["choice"] == "K0"                  # paired SE ~ 5e-5; the arms' own SE (~0.025) would call it a tie
    assert out["contrasts"]["K0"]["paired_mcse"] < 1e-3


def test_an_ineligible_default_yields_the_best_eligible_arm():
    raw = {"K1": np.full(50, 13.0), "K0": np.full(50, 12.0)}
    out = m.choose(raw, {}, {"K0": {"ratio_min": 0.9}, "K1": {"ratio_min": 0.4}}, None, ("K0", "K1"), "K1", 0.5)
    assert out["eligible"] == ["K0"] and out["choice"] == "K0" and "ineligible" in out["rule"]
    none = m.choose(raw, {}, _coh(["K0", "K1"], 0.3), None, ("K0", "K1"), "K1", 0.5)
    assert none["choice"] is None


def test_the_highest_mean_arm_is_reported_and_never_decides():
    raw = {"K1": np.full(1000, 12.0), "K0": np.where(np.arange(1000) % 10 == 0, 14.0, 11.7)}
    out = m.choose(raw, {}, _coh(["K0", "K1"]), None, ("K0", "K1"), "K1", 0.5)
    assert np.mean(raw["K0"]) < np.mean(raw["K1"])                       # lower typical outcome
    assert out["choice"] == "K1" and out["highest_mean_eligible_arm"] == "K0"
    assert out["mean_terminal_real"]["K0"] > out["mean_terminal_real"]["K1"]


def _pair_choice(a0, a1, b0, b1, elig_a=("K0", "K1"), elig_b=("K1", "B1", "B2", "B3")):
    r0, r1 = m.DECISION_PAIR
    return {r0: {"A": {"choice": a0, "eligible": list(elig_a)}, "B": {"choice": b0, "eligible": list(elig_b)}},
            r1: {"A": {"choice": a1, "eligible": list(elig_a)}, "B": {"choice": b1, "eligible": list(elig_b)}}}


def test_pair_rule_agreement_is_the_choice_and_disagreement_is_the_default():
    out = m.resolve_pair(_pair_choice("K1", "K1", "B1", "B2"))
    assert out["A"]["resolved"] == "K1" and out["A"]["agree"] is True
    assert out["B"]["resolved"] == "K1" and out["B"]["agree"] is False and "DISAGREE" in out["B"]["flag"]
    assert out["B"]["choices"] == {"param:h=+0.00": "B1", "param:h=-0.02": "B2"}     # both choices are written
    assert m.resolve_pair(_pair_choice("K0", "K0", "B3", "B3"))["B"]["resolved"] == "B3"
    assert m.resolve_pair(_pair_choice("K0", "K1", "B1", "B1"))["A"]["resolved"] == "K1"


def test_pair_rule_never_takes_a_default_that_fails_the_loss_bound():
    out = m.resolve_pair(_pair_choice("K0", "K1", "B1", "B1", elig_a=("K0",)))
    assert out["A"]["resolved"] is None and "fails the loss bound" in out["A"]["flag"]
    both_none = m.resolve_pair(_pair_choice(None, None, "B1", "B1"))
    assert both_none["A"]["resolved"] is None and both_none["A"]["agree"] is True


def test_decision_row_is_checked_before_any_input_is_read(tmp_path):
    with pytest.raises(m.InputError, match="decision row 'h=\\+0.55'"):
        m.cmd_run(_run_args(tmp_path, smoke=True, decision_row="h=+0.55"))
    with pytest.raises(m.InputError, match="missing input"):          # a valid row gets as far as the manifest
        m.cmd_run(_run_args(tmp_path, smoke=True, decision_row="pair"))
    assert m.decision_rows(m.Config())[-1] == "pair"
    assert "pair" not in m.decision_rows(replace(m.Config(), param_rows=(0.0,)))


def test_choice_eligibility_reads_the_unshifted_cohorts():
    raw = {"K1": np.zeros(50), "K0": np.full(50, 1.0)}
    unshifted = {"K0": {"ratio_min": 0.49}, "K1": {"ratio_min": 0.9}}
    shifted = {"K0": {"ratio_min": 0.9}, "K1": {"ratio_min": 0.9}}
    out = m.choose(raw, {}, unshifted, shifted, ("K0", "K1"), "K1", 0.5)
    assert out["eligible"] == ["K1"] and out["choice"] == "K1"
    assert out["worst_cohort_ratio_this_row"]["K0"] == 0.9


# -------------------------------------------------------------------------- the tax-sale details ----
def test_tax_payment_sales_never_realise_a_washed_loss(monkeypatch):
    """A falling market and a dividend tax: VOO (bought every month) is sold at a loss to pay the bill, which the
    wash-sale rule disallows. Every monthly sale except SSO's must carry the wash flag; the final sale does not."""
    n = 36
    falling = {"voo": np.full(n, -0.01), "robo": np.full(n, -0.01), "sso": np.full(n, -0.02),
               "upro": np.full(n, -0.03), "rf": np.zeros(n), "days": np.full(n, 30.4),
               "cash_robo": np.zeros(n), "infl": np.zeros(n), "dy": np.full(n, 0.04 / 12)}
    path = m.make_path(falling)
    calls = []
    real = m.LotBook.sell_hifo

    def spy(self, dollars, price, t, wash=False):
        calls.append((t, wash))
        return real(self, dollars, price, t, wash)

    monkeypatch.setattr(m.LotBook, "sell_hifo", spy)
    arm = next(a for a in m.ARMS if a.name == "K1")
    m.simulate(arm, m.Owner(state_rate=0.10), path)
    monthly = [(t, w) for t, w in calls if t < n]
    assert monthly and all(w for _, w in monthly)
    assert [w for t, w in calls if t == n].count(False) >= 1


def test_liquidation_counts_a_disallowed_loss_still_waiting_for_a_replacement():
    book = m.LotBook()
    book.buy(100_000.0, 1.0, t=-24)
    book.wash_carry = 20_000.0
    books = {"voo": book, "robo": m.LotBook(), "sso": m.LotBook()}
    P = {"voo": np.array([1.0, 1.5]), "robo": np.ones(2), "sso": np.ones(2)}
    own = m.Owner(state_rate=0.0, liq_wages=160_000.0)
    got = m.liquidation_tax(books, P, 1, m.TaxYear(), own, 1.0, 0.0, 0.0)
    want, _, _, _ = m.annual_tax(m.TaxYear(lt=50_000.0 - 20_000.0), 160_000.0, 1.0, 0.0, 0.0, 0.0)
    assert got == pytest.approx(want)


@pytest.mark.parametrize("balance,years", [(49_000.0, 0), (50_000.0, 2), (51_000.0, 2)])
def test_robo_harvesting_is_active_only_from_50_000(balance, years):
    n = 24
    payout = m.ROBO_DY_UPLIFT / 12.0                     # the robo's whole return is its distribution: a flat price
    flat = {"voo": np.zeros(n), "robo": np.full(n, payout), "sso": np.zeros(n), "upro": np.zeros(n),
            "rf": np.zeros(n), "days": np.full(n, 30.4), "cash_robo": np.zeros(n), "infl": np.zeros(n),
            "dy": np.zeros(n)}
    own = m.Owner(taxable0=balance, g=0.0, c_taxable_month=0.0, roth_contrib=0.0, state_rate=0.0,
                  robo_rebal=0.0, liquidate=False)
    k0 = next(a for a in m.ARMS if a.name == "K0")
    assert m.simulate(k0, own, m.make_path(flat)).tlh_years == years


# ------------------------------------------------------------------------------------- vehicles ----
def test_monthly_panel_matches_a_hand_computed_levered_month():
    """Three bars (1, 1 and 3 calendar days) in January. SSO = 2g - (bill + 0.86 % x d/360) - 0.89 % x d/365.25;
    UPRO = 3g - 2(bill + 0.85 % x d/360) - 0.90 % x d/365.25; VOO and the robo are the market less their fees."""
    idx = pd.DatetimeIndex(["2010-01-04", "2010-01-05", "2010-01-08", "2010-02-01"])
    french = pd.DataFrame({"mkt_rf": [0.010, -0.020, 0.005, 0.010], "rf": [0.0001, 0.0001, 0.0002, 0.0001]}, index=idx)
    per = pd.period_range("2009-12", "2010-02", freq="M")
    cpi = pd.Series([100.0, 101.0, 102.0], index=per)
    dp = pd.Series([0.02, 0.02, 0.02], index=per)
    panel = m.build_monthly_panel(french, cpi, dp)
    sso = upro = voo = robo = 1.0
    for g, rf, d in ((0.0101, 0.0001, 1), (-0.0199, 0.0001, 1), (0.0052, 0.0002, 3)):
        sso *= 1 + 2 * g - (rf + 0.0086 * d / 360) - 0.0089 * d / 365.25
        upro *= 1 + 3 * g - 2 * (rf + 0.0085 * d / 360) - 0.0090 * d / 365.25
        voo *= 1 + g - 0.0003 * d / 365.25
        robo *= 1 + g - 0.0015 * d / 365.25
    row = panel.loc[pd.Period("2010-01", "M")]
    assert row["sso"] == pytest.approx(sso - 1, abs=1e-12) and row["upro"] == pytest.approx(upro - 1, abs=1e-12)
    assert row["voo"] == pytest.approx(voo - 1, abs=1e-12) and row["robo"] == pytest.approx(robo - 1, abs=1e-12)
    assert row["infl"] == pytest.approx(0.01) and row["dy"] == pytest.approx(0.02 / 12)
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
    assert sens["step_up"]["h=+0.00"]["cohorts"]["K1"]["median"] > base["K1"]["median"]
    assert "roth_25k" in sens and set(sens["roth_25k"]["h=+0.00"]) == {"cohorts", "bootstrap"}


def test_study_is_deterministic_and_the_arms_differ():
    panel = synthetic_panel()
    cfg = replace(TINY, block_sensitivity=(6, 24), decision_row="param:h=+0.00")
    a = m.study(panel, cfg, m.Owner(taxable0=60_000.0), log=lambda s: None)
    b = m.study(panel, cfg, m.Owner(taxable0=60_000.0), log=lambda s: None)
    assert m.canonical_md5(a) == m.canonical_md5(b)
    row = a["results"]["bootstrap"]["h=+0.00"]["g=0.30"]
    for x, y in (("K0", "K1"), ("K1", "B3"), ("B1", "B4"), ("S0", "K1"), ("B1", "B1_upro")):
        assert row[x]["E_log"] != row[y]["E_log"], (x, y)
    assert row["REF"]["dlog_vs_ref_mean"] == 0.0
    assert row["K0"]["tlh_years_median"] > 0 and row["K0_noTLH"]["tlh_years_median"] == 0
    assert set(a["choice"]) == {"h=+0.00", "h=-0.02", "param:h=+0.00"}
    assert "K0" in a["choice"]["param:h=+0.00"]["A"]["worst_cohort_ratio_unshifted"]
    assert a["decision"]["row"] == "param:h=+0.00"
    coh = a["results"]["cohorts"]["h=+0.00"]["g=0.30"]["K1"]
    assert "dlog_vs_ref_mcse" not in coh and "p_below_ref" not in coh
    assert coh["effective_independent_windows"] == pytest.approx((1988 + 5 - 1986) / 5)
    assert "share_of_cohorts_below_ref" in coh
    with pytest.raises(m.InputError, match="decision row"):
        m.study(panel, replace(TINY, decision_row="h=+0.07"), m.Owner(), log=lambda s: None)


def test_lower_belief_row_lowers_levered_wealth_more_than_one_x():
    panel = synthetic_panel()
    res = m.study(panel, TINY, m.Owner(), log=lambda s: None)
    hi, lo = res["results"]["cohorts"]["h=+0.00"]["g=0.30"], res["results"]["cohorts"]["h=-0.02"]["g=0.30"]
    drop_k1 = hi["K1"]["E_log"] - lo["K1"]["E_log"]
    drop_b3 = hi["B3"]["E_log"] - lo["B3"]["E_log"]
    assert drop_b3 > drop_k1 > 0


def test_rehearsal_of_the_full_configs_structure(monkeypatch):
    """The whole Config (60 cohorts, four h rows, two parameter rows, blocks 12 and 120) on a 100-year synthetic
    panel, with a 5-year horizon and 12 paths. Spies on run_paths and choose: every row gets block runs at the full
    path count, the parameter rows (main and block) use the same deltas, K0 is in every row, and the loss bound
    always reads the unshifted cohorts."""
    cfg = replace(m.Config(), horizon_years=5, n_paths=12, owner_sensitivity=(), decision_row="pair")
    panel = synthetic_panel(months=1203, start="1926-07")
    calls, chooses = [], []
    real_run, real_choose = m.run_paths, m.choose

    def spy_run(index_paths, arrays, owner, arms, h, deltas=None):
        calls.append({"n": len(index_paths), "h": h, "deltas": deltas, "arms": [a.name for a in arms]})
        return real_run(index_paths, arrays, owner, arms, h, deltas)

    def spy_choose(raw, raw_blocks, unshifted, shifted, candidates, default, bound):
        chooses.append({"blocks": {b: {a: len(v[a]) for a in candidates} for b, v in raw_blocks.items()},
                        "unshifted": unshifted, "shifted": shifted, "candidates": tuple(candidates)})
        return real_choose(raw, raw_blocks, unshifted, shifted, candidates, default, bound)

    monkeypatch.setattr(m, "run_paths", spy_run)
    monkeypatch.setattr(m, "choose", spy_choose)
    prog = m.Progress(m.arm_path_total(cfg), False)
    out = m.study(panel, cfg, m.Owner(), log=lambda s: None, progress=prog)
    assert prog.done == prog.total                     # the counter counts exactly the work done

    rows = ["h=+0.00", "h=-0.01", "h=-0.02", "h=-0.03", "param:h=+0.00", "param:h=-0.02"]
    assert list(out["choice"]) == rows and len(chooses) == 12
    for c in chooses:
        assert set(c["blocks"]) == {12, 120}
        assert all(n == cfg.n_paths for by_arm in c["blocks"].values() for n in by_arm.values())
    # the loss bound: one unshifted cohort table for every row, and it is the h = 0 one
    assert all(c["unshifted"] is chooses[0]["unshifted"] for c in chooses)
    coh = out["results"]["cohorts"]
    un, sh = chooses[0]["unshifted"], chooses[-1]["shifted"]
    for arm in ("K0", "K1", "B1", "B2", "B3"):
        assert un[arm]["ratio_min"] == pytest.approx(coh["h=+0.00"]["g=0.15"][arm]["ratio_min"], abs=1e-5)
    assert any(abs(un[a]["ratio_min"] - sh[a]["ratio_min"]) > 1e-6 for a in ("K0", "B1", "B2", "B3"))
    assert all(out["choice"][r]["A"]["worst_cohort_ratio_unshifted"]
               == out["choice"][rows[0]]["A"]["worst_cohort_ratio_unshifted"] for r in rows)
    assert "K0" in out["choice"]["param:h=-0.02"]["A"]["worst_cohort_ratio_unshifted"]
    # deltas: exactly the parameter rows (3 g levels + 2 block runs each) use them, and always the same draws
    with_d = [c for c in calls if c["deltas"] is not None]
    assert len(with_d) == 2 * (3 + 2)
    assert all(c["deltas"] is with_d[0]["deltas"] for c in with_d)
    assert sorted(c["h"] for c in with_d) == [-0.02] * 5 + [0.0] * 5
    plain = [c for c in calls if c["deltas"] is None and c["n"] == cfg.n_paths]
    assert len(plain) == 4 * (3 + 2)
    # the block runs carry the choice arms on every row
    blocks = [c for c in calls if c["arms"] == ["REF", "K0", "K1", "B1", "B2", "B3"]]
    assert len(blocks) == 6 * 2 and all(c["n"] == cfg.n_paths for c in blocks)
    # the progress total is the work actually done
    assert sum(c["n"] * len(c["arms"]) for c in calls) == m.arm_path_total(cfg)
    assert out["decision"]["mode"] == "pair" and set(out["decision"]) >= {"A", "B", "rows"}


def test_the_smoke_covers_a_parameter_row_and_a_block_run():
    assert m.SMOKE.param_rows and m.SMOKE.block_sensitivity
    assert m.PAIR_ROW in m.decision_rows(m.SMOKE)


def test_progress_is_stderr_only_and_counts_the_work(capsys):
    prog = m.Progress(100, True)
    prog.add(40, "x")
    err = capsys.readouterr()
    assert "40/100" in err.err and err.out == ""


def test_gate_uses_monthly_periods_for_sortino():
    panel = synthetic_panel()
    g = m.gate_and_sortino(panel, seed=0)
    assert g["voo"]["sortino_point"] == pytest.approx(MetricsEngine.sortino_ratio(panel["voo"], periods=12))
    assert g["voo"]["sortino_point"] != pytest.approx(MetricsEngine.sortino_ratio(panel["voo"], periods=252))
