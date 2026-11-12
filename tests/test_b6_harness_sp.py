"""T-383 (B-6) — locks for the S&P-arm harness (scripts/lazy_prices/b6_harness_sp.py).
Synthetic data only: no real price is read by these tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.lazy_prices import b6_harness_sp as H

CAL = pd.bdate_range("2015-12-01", "2018-06-29")


def _sig(rows):
    d = pd.DataFrame(rows)
    d["floor"] = pd.to_datetime(d.decision_floor_date)
    d["acc"] = pd.to_datetime(d.acceptance_dt.str[:10])
    return d


def _row(cik, form, acc, floor, cos, why="ok"):
    return {"cik": cik, "form": form, "accession": f"{cik}-{acc}", "acceptance_dt": acc + "T21:00:00Z",
            "decision_floor_date": floor, "yoy_combo_cos": cos if form == "10-K" else np.nan,
            "yoy_mda_cos": cos, "yoy_combo_why": why if form == "10-K" else "n/a",
            "yoy_mda_why": why}


def test_signal_is_point_in_time_and_fresh():
    sig = _sig([
        _row(1, "10-K", "2016-02-20", "2016-02-21", 0.9),
        _row(1, "10-Q", "2016-04-01", "2016-04-02", 0.5),     # after t: must NOT be used at 2016-03-31
        _row(2, "10-Q", "2015-08-01", "2015-08-02", 0.7),     # older than 6 months: stale
    ])
    s = H.signals_at(sig, pd.Timestamp("2016-03-31"), H.SPECS["gate_similarity"], {1, 2})
    assert s.set_index("cik").value.to_dict() == {1: 0.9}


def test_ranking_is_within_form_then_pooled():
    df = pd.DataFrame({"cik": range(6), "form": ["10-K"] * 3 + ["10-Q"] * 3,
                       "value": [0.1, 0.2, 0.3, 0.97, 0.98, 0.99]})
    r = H.rank_terciles(df).set_index("cik").leg.to_dict()
    # 10-Q levels are higher, but ranking within form puts the top of EACH form long
    assert r[2] == "long" and r[5] == "long" and r[0] == "short" and r[3] == "short"


def test_exit_at_last_close_then_bil_and_the_minus_30_diagnostic():
    t0 = pd.Timestamp("2016-03-31")
    marks = [pd.Timestamp("2016-04-29"), pd.Timestamp("2016-05-31"), pd.Timestamp("2016-06-30")]
    a = pd.Series([100.0, 110.0, 121.0, 133.1], index=[t0] + marks)               # +10%/month
    b = pd.Series([100.0, 90.0], index=[t0, pd.Timestamp("2016-04-15")])            # exits mid-April
    bil = pd.Series(100.0, index=CAL)                                               # 0% cash
    r0, _, ex0 = H.leg_returns([(1, a), (2, b)], t0, marks, bil, exit_d=0.0)
    V = np.array([(1.1 + 0.9) / 2, (1.21 + 0.9) / 2, (1.331 + 0.9) / 2])
    assert np.allclose(r0, V / np.concatenate([[1.0], V[:-1]]) - 1.0)
    assert ex0 == [{"cik": 2, "exit_date": "2016-04-15", "from": "2016-03-31"}]
    r3, _, _ = H.leg_returns([(1, a), (2, b)], t0, marks, bil, exit_d=-0.30)
    assert np.isclose(r3[0], (1.1 + 0.9 * 0.7) / 2 - 1.0)


def test_nan_return_without_an_exit_halts():
    t0 = pd.Timestamp("2016-03-31")
    marks = [pd.Timestamp("2016-04-29")]
    late = pd.Series([100.0, 101.0], index=[pd.Timestamp("2016-04-05"), pd.Timestamp("2016-04-29")])
    with pytest.raises(H.CensusHalt):
        H.leg_returns([(1, late)], t0, marks, pd.Series(100.0, index=CAL), 0.0)


def test_turnover_counts_both_sides():
    assert H.turnover({}, [1, 2]) == pytest.approx(1.0)                      # first build: 100%
    assert H.turnover({1: 0.6, 2: 0.4}, [2, 3]) == pytest.approx(0.6 + 0.1 + 0.5)


def test_census_halts_below_eighty_percent_and_on_thin_terciles():
    census = pd.DataFrame([
        {"rebalance": "2016-03-31", "ranked": 338, "share": 0.679, "long": 113, "short": 113},
        {"rebalance": "2016-06-30", "ranked": 450, "share": 0.90, "long": 150, "short": 150},
        {"rebalance": "2016-09-30", "ranked": 120, "share": 0.90, "long": 30, "short": 30},
    ])
    bad = H.check_census(census)
    assert any("2016-03-31" in b and "share" in b for b in bad)
    assert not any("2016-06-30" in b for b in bad)
    assert any("2016-09-30" in b and "ranked 120" in b for b in bad)


def test_returns_and_summary_are_deterministic_and_paired():
    rng = np.random.default_rng(1)
    cal = pd.bdate_range("2016-01-01", "2019-12-31")
    names = list(range(1, 61))
    t265 = {f"T{c}": pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.01, len(cal))), index=cal)
            for c in names}
    spy = pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.008, len(cal))), index=cal)
    px = H.Prices({c: f"T{c}" for c in names}, t265, {}, spy, pd.Series(100.0, index=cal))
    sig = _sig([_row(c, "10-Q", d.strftime("%Y-%m-%d"), (d + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                     float(rng.uniform(0.8, 1.0)))
                for c in names for d in pd.date_range("2015-10-01", "2019-10-15", freq="QS-JAN")
                + pd.Timedelta(days=14)])
    months = pd.date_range("2016-01-01", "2019-12-01", freq="MS")
    uni = pd.DataFrame([{"month": m, "cik": c, "ticker": f"X{c}"} for m in months for c in names])
    spec = H.Spec("t", **H.SIM, start="2016-03-31", end="2018-12-31")
    panel, census = H.build_panel(spec, sig, uni, px, pd.DatetimeIndex(cal))
    assert (census.src_t265 == census.ranked).all() and (census.ranked == 60).all()
    hold_end = pd.Timestamp("2019-03-29")
    a = H.summarize(H.run_returns(spec, panel, px, pd.DatetimeIndex(cal), hold_end))
    b = H.summarize(H.run_returns(spec, panel, px, pd.DatetimeIndex(cal), hold_end))
    assert a == b
    assert a["n_months"] == 36
    assert a["dlogw_ci_low_1p25"] <= a["dlogw_ci_low_2p5"] <= a["dlogw_point"] <= a["dlogw_ci_high_97p5"]
