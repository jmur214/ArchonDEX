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


# ---------------------------------------------------------------- AMENDMENT 3 (review F1/F2)
T0, QE = pd.Timestamp("2021-03-31"), pd.Timestamp("2021-06-30")
DAYS = pd.bdate_range("2020-01-01", "2022-12-30")


def _s(a="2020-01-01", b="2022-12-30"):
    idx = DAYS[(DAYS >= pd.Timestamp(a)) & (DAYS <= pd.Timestamp(b))]
    return pd.Series(100.0, index=idx)


def _px(proc=None, t265=None, t265_of_cik=None, iv_end=None):
    return H.Prices(t265_of_cik or {}, t265 or {}, proc or {}, _s(), _s(), iv_end=iv_end or {})


def test_resolve_prefers_processed_then_t265_by_cik_and_names_the_cause():
    full = _s()
    assert H.Prices.resolve(_px(proc={"AAA": full}), 1, "AAA", 0, T0, QE)["cause"] == "ok"
    # truncated processed file of a live member (AVGO ends 2025-04-23): T-265 by CIK fills
    px = _px(proc={"AVGO": _s(b="2021-04-23")}, t265={"AVGO": full}, t265_of_cik={2: "AVGO"})
    r = px.resolve(2, "AVGO", 0, T0, QE)
    assert (r["source"], r["cause"]) == ("t265_fill", "truncated")
    # rename (CDAY -> DAY): the CIK's T-265 ticker differs
    px = _px(proc={"CDAY": _s(b="2021-05-01")}, t265={"DAY": full}, t265_of_cik={3: "DAY"})
    assert px.resolve(3, "CDAY", 0, T0, QE)["cause"] == "rename"
    # a different security under the ticker (FB file starts 2025-06-26): no bar at t -> T-265
    px = _px(proc={"FB": _s(a="2022-06-26")}, t265={"META": full}, t265_of_cik={4: "META"})
    assert px.resolve(4, "FB", 0, T0, QE)["cause"] == "no_bar_at_t"
    # no file at all (MMC)
    px = _px(t265={"MMC": full}, t265_of_cik={5: "MMC"})
    assert px.resolve(5, "MMC", 0, T0, QE)["cause"] == "no_file"


def test_share_class_spelling_is_resolved():
    px = _px(proc={"BRK.B": _s()})
    assert px.resolve(6, "BRK-B", 0, T0, QE)["source"] == "processed"


def test_an_exit_needs_a_recorded_index_deletion_else_the_census_halts():
    ended = _s(b="2021-05-14")
    px = _px(proc={"XYZ": ended}, iv_end={7: pd.Timestamp("2021-05-17")})
    r = px.resolve(1, "XYZ", 7, T0, QE)
    assert r["cause"] == "real_exit" and r["exit"] == pd.Timestamp("2021-05-14")
    px = _px(proc={"XYZ": ended}, iv_end={7: pd.NaT})            # still a member: no deletion
    assert px.resolve(1, "XYZ", 7, T0, QE)["cause"] == "unresolved"
    census = pd.DataFrame([{"rebalance": "2021-03-31", "ranked": 400, "share": 0.9, "long": 130,
                            "short": 130, "cause_unresolved": 1}])
    assert any("recorded index deletion" in b for b in H.check_census(census))
    assert px.resolve(1, "QQQ", 7, T0, QE)["cause"] == "no_price_at_t"


def test_amendment_4_shared_ticker_fills_only_with_a_unique_date_aware_holder():
    """AVGO: T-265 maps the symbol to several CIKs (Avago, Broadcom Ltd, Broadcom Inc). The CIK fill
    is allowed when exactly ONE CIK holds the symbol at the rebalance date and it is this member's."""
    full = _s()
    holders = {"AVGO": [(1649338, pd.Timestamp("2016-02-02"), pd.Timestamp("2018-03-28")),
                        (1730168, pd.Timestamp("2018-04-06"), pd.Timestamp("2026-03-27"))]}
    px = _px(proc={"AVGO": _s(b="2021-04-23")}, t265={"AVGO": full})
    px.t265_of_cik_all = {1730168: "AVGO", 1649338: "AVGO"}
    px.shared, px.holders = {"AVGO"}, holders
    r = px.resolve(1730168, "AVGO", 0, T0, QE)
    assert (r["source"], r["cause"], r["shared_resolved"]) == ("t265_fill", "truncated", True)
    # the older issuer does NOT hold the symbol at t -> its bars are not attributable to it
    assert px.resolve(1649338, "AVGO", 0, T0, QE)["source"] != "t265_fill"
    # two concurrent holders at t -> not unique -> no fill -> unresolved (the census halts)
    px.holders = {"AVGO": holders["AVGO"] + [(999, pd.Timestamp("2020-01-01"), pd.Timestamp("2022-01-01"))]}
    assert px.resolve(1730168, "AVGO", 0, T0, QE)["cause"] == "unresolved"
