"""T-382 (B-5) — the levered-ETF simulator's identities and the bootstrap replay.

Pure-function tests: no data files, no network. They lock the frozen formulas of
docs/Sources/prereg_b5_levered_diversified_2026-11-11.md (§5, §9, amendment 1 A1.1-6).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.metrics_engine import MetricsEngine as ME
from scripts import b5_levered_diversified as b5


def test_daily_reset_is_the_brief_formula():
    u = np.array([0.01, -0.02, 0.005])
    f = np.array([0.0002, 0.0002, 0.0006])
    got = b5.daily_reset(u, f, 2.0, 0.0089)
    want = 2.0 * u - 1.0 * f - 0.0089 / 252
    assert np.allclose(got, want, atol=0, rtol=0)


def test_mm_from_discount_is_above_discount_and_exact():
    d = np.array([0.05, 0.15])
    got = b5.mm_from_discount(d)
    assert np.allclose(got, 360 * d / (360 - 91 * d))
    assert (got > d).all()
    assert abs(got[1] - 0.15591) < 1e-4            # 1981-level rates: +59 bp over discount


def test_stacked_fund_day_one_identity_and_borrowing():
    e, b, f = np.array([0.01]), np.array([-0.004]), np.array([0.0003])
    r = b5.stacked_fund(e, b, f, 1.0, 1.0, 0.0041, np.array([False]))
    assert r[0] == pytest.approx(0.01 - 0.004 - 1.0 * 0.0003 - 0.0041 / 252, abs=1e-15)
    r_ntsx = b5.stacked_fund(e, b, f, 0.9, 0.6, 0.0020, np.array([False]))
    assert r_ntsx[0] == pytest.approx(0.9 * 0.01 + 0.6 * -0.004 - 0.5 * 0.0003 - 0.0020 / 252, abs=1e-15)


def test_stacked_fund_resets_exposure_after_rebalance_and_charges_5bp():
    e = np.array([0.10, 0.0])
    b = np.array([0.0, 0.0])
    f = np.zeros(2)
    r = b5.stacked_fund(e, b, f, 1.0, 1.0, 0.0, np.array([True, False]))
    # day 1: +10 % on equity; NAV 1.1, E 1.1, F 1.0 -> reset to 1.1/1.1: trade 0.1 of F
    assert r[0] == pytest.approx((1.1) * (1 - 0.0005 * 0.1 / 1.1) - 1, abs=1e-15)
    assert r[1] == pytest.approx(0.0, abs=1e-15)


def test_drifting_portfolio_rebalance_cost_and_weights():
    rets = np.array([[0.10, 0.0], [0.0, 0.0]])
    tgt = np.tile([0.6, 0.4], (2, 1))
    rp, cost = b5.drifting_portfolio_init(rets, np.array([0.6, 0.4]), tgt, np.array([True, False]))
    assert rp[0] == pytest.approx(0.06)
    wd = np.array([0.66, 0.4]) / 1.06
    assert cost[0] == pytest.approx(0.0005 * np.abs(np.array([0.6, 0.4]) - wd).sum())
    assert cost[1] == 0.0


def test_arm_iv_monthly_identity_before_cost():
    e = np.array([0.02])
    tau = np.array([0.01])
    r = b5.arm_iv_monthly(e, tau, 0.5, 0.005)
    pre = 0.5 * (0.02 - 0.0009 / 12) + 0.5 * (0.02 + 0.01 - 0.005 / 12 - 0.01 / 12)
    assert r[0] <= pre + 1e-15 and r[0] > pre - 1e-5   # only the tiny 5 bp drift cost differs


@pytest.mark.parametrize("n,L", [(500, 21), (1000, None), (257, 252), (60, 1)])
def test_bootstrap_replay_equals_metricsengine(n, L):
    rng = np.random.default_rng(7)
    d = rng.normal(0.0002, 0.01, size=n)
    Le = b5.auto_block(n) if L is None else L
    boot = b5.Boot().stat(d, Le)
    me = ME.bootstrap_distribution(pd.Series(d), lambda x: float(np.sum(np.asarray(x))),
                                   n_iterations=1000, block_length=L, seed=0)
    assert boot["block_length"] == me["block_length"]
    for k_b, k_m in (("ci_low", "ci_low"), ("ci_high", "ci_high"), ("mean", "mean"),
                     ("point", "point_estimate")):
        assert abs(boot[k_b] - me[k_m]) < 1e-12


def test_bootstrap_curve_is_monotone_in_spread():
    rng = np.random.default_rng(3)
    u = rng.normal(0.0003, 0.01, size=800)
    bench = u.copy()
    boot = b5.Boot()
    lows = []
    for s in (0.0, 0.01, 0.02, 0.04):
        r = b5.daily_reset(u, np.full(800, (0.02 + s) / 360), 2.0, 0.0041)
        lows.append(boot.stat(b5.log_diff(r, bench), 21)["ci_low"])
    assert all(a > b for a, b in zip(lows, lows[1:]))


def test_crossing_and_binding_sentence_three_cases():
    s = [0, 50, 100]
    assert b5.crossing(s, [-0.1, -0.2, -0.3])["label"].startswith("< 0")
    assert b5.crossing(s, [0.3, 0.2, 0.1])["label"] == "> 100"
    x = b5.crossing(s, [0.2, -0.2, -0.4])
    assert x["s_star_bp"] == pytest.approx(25.0)
    assert b5.binding_sentence([0.2, -0.2, -0.4], x).startswith("BINDING")
    assert b5.binding_sentence([-0.1, -0.2], b5.crossing([0, 5], [-0.1, -0.2])).startswith("NOT BINDING: ci_low <= 0")
    y = b5.crossing(s, [0.4, 0.1, -0.2])
    assert b5.binding_sentence([0.4, 0.1, -0.2], y).startswith("NOT BINDING at today's spread")


def test_guard_std_fails_closed_on_degenerate_input():
    with pytest.raises(b5.B5Halt):
        b5._guard_std(float(pd.Series([0.001] * 100).std()), "constant")
    with pytest.raises(b5.B5Halt):
        b5._guard_std(float("nan"), "nan")


# --------------------------------------------------------------------------- amendment 2 parsers
_H15 = (
    '"Series Description","Federal funds effective rate","3-month Treasury bill secondary market rate, '
    'discount basis"\n'
    '"Unit:","Percent:_Per_Year","Percent:_Per_Year"\n'
    '"Multiplier:","1","1"\n'
    '"Currency:","NA","NA"\n'
    '"Unique Identifier: ","H15/H15/RIFSPFF_N.B","H15/H15/RIFSGFSM03_N.B"\n'
    '"Time Period","RIFSPFF_N.B","RIFSGFSM03_N.B"\n'
)


def _h15_file(tmp_path, desc_ok=True, rows=10050):
    body = _H15 if desc_ok else _H15.replace("3-month Treasury bill secondary market", "6-month Treasury bill")
    dates = pd.bdate_range("1960-01-01", periods=rows)
    lines = [f"{d.date()},4.00,{'ND' if i == 3 else '5.00'}" for i, d in enumerate(dates)]
    p = tmp_path / "h15.csv"
    p.write_text(body + "\n".join(lines) + "\n")
    return p


def test_parse_h15_bill_extracts_by_identifier_and_drops_ND(tmp_path):
    s, desc = b5.parse_h15_bill(_h15_file(tmp_path))
    assert "3-month" in desc and len(s) == 10049            # the ND row is dropped, not filled
    assert float(s.iloc[0]) == pytest.approx(0.05)


def test_parse_h15_bill_halts_on_wrong_description(tmp_path):
    with pytest.raises(b5.B5Halt):
        b5.parse_h15_bill(_h15_file(tmp_path, desc_ok=False))


def test_parse_nyfed_sofr_checks_type_and_rows(tmp_path):
    dates = pd.bdate_range("2018-04-02", periods=1950)
    good = "Effective Date,Rate Type,Rate (%)\n" + "\n".join(f"{d:%m/%d/%Y},SOFR,1.80" for d in dates)
    p = tmp_path / "sofr.csv"
    p.write_text(good)
    s = b5.parse_nyfed_sofr(p)
    assert len(s) == 1950 and float(s.iloc[0]) == pytest.approx(0.018)
    p.write_text(good.replace(",SOFR,", ",EFFR,", 1))
    with pytest.raises(b5.B5Halt):
        b5.parse_nyfed_sofr(p)


def _sdmx_zip(tmp_path, desc="3-month Treasury bill secondary market rate, discount basis", n=10010):
    import zipfile
    obs = "".join(f'<frb:Obs OBS_STATUS="A" OBS_VALUE="{"ND" if i == 5 else "4.50"}" TIME_PERIOD="{d.date()}"/>'
                  for i, d in enumerate(pd.bdate_range("1960-01-01", periods=n)))
    xml = ('<?xml version="1.0"?><message:MessageGroup xmlns:message="urn:m" xmlns:frb="urn:frb" '
           'xmlns:kf="urn:kf" xmlns:common="urn:c"><frb:DataSet>'
           '<kf:Series SERIES_NAME="RIFLGFCM03_N.B"><frb:Annotations><common:Annotation>'
           '<common:AnnotationText>3-month constant maturity</common:AnnotationText></common:Annotation>'
           '</frb:Annotations><frb:Obs OBS_VALUE="1.0" TIME_PERIOD="2000-01-03"/></kf:Series>'
           f'<kf:Series SERIES_NAME="RIFSGFSM03_N.B"><frb:Annotations><common:Annotation>'
           f'<common:AnnotationText>{desc}</common:AnnotationText></common:Annotation></frb:Annotations>'
           f'{obs}</kf:Series></frb:DataSet></message:MessageGroup>')
    p = tmp_path / "h15.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("FRB_H15.xml", xml)
    return p


def test_parse_h15_sdmx_zip_selects_by_series_name(tmp_path):
    s, desc = b5.parse_h15_bill(_sdmx_zip(tmp_path))
    assert len(s) == 10009 and float(s.iloc[0]) == pytest.approx(0.045) and "secondary market" in desc


def test_parse_h15_sdmx_zip_halts_on_wrong_description(tmp_path):
    with pytest.raises(b5.B5Halt):
        b5.parse_h15_bill(_sdmx_zip(tmp_path, desc="6-month Treasury bill, investment basis"))
