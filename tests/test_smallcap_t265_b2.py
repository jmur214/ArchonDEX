"""Hermetic locks for the B-2 (T-381) harnesses — synthetic inputs only, no data files.

Each test pins one frozen rule of `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md` (+ A1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import smallcap_t265_b2_common as cm
from scripts import smallcap_momentum_t265_b2 as mom
from scripts import smallcap_insider_t265_b2 as ins


def _cal(n=400, start="2016-01-04"):
    return pd.bdate_range(start, periods=n)


def _file(cal, close, volume):
    return pd.DataFrame({"close": close, "volume": volume}, index=cal)


def test_phantom_tail_is_truncated_and_the_last_traded_bar_is_the_death():
    cal = _cal(100)
    vol = np.r_[np.full(60, 1000.0), np.zeros(40)]            # 40 phantom zero-volume bars
    df = _file(cal, np.linspace(10, 5, 100), vol)
    segs = cm.split_segments("X", df, cal)
    assert len(segs) == 1
    assert segs[0].last == cal[59] and segs[0].death == cal[59]
    assert cm.file_census(df, cal)["trailing_zero_vol_bars"] == 40


def test_a_63_day_no_trade_gap_splits_a_reused_ticker_and_the_first_segment_dies():
    cal = _cal(300)
    vol = np.ones(300) * 1000.0
    vol[100:163] = 0.0                                          # exactly 63 market days, no trade
    segs = cm.split_segments("Y", _file(cal, np.full(300, 20.0), vol), cal,
                             death_cutoff=cal[-1])
    assert [s.seg_id for s in segs] == ["Y#0", "Y#1"]
    assert segs[0].death == cal[99] and segs[1].death is None
    assert segs[1].first == cal[163]
    vol[162] = 1000.0                                           # 62 days: a halt, not a splice
    assert len(cm.split_segments("Y", _file(cal, np.full(300, 20.0), vol), cal)) == 1


def test_final_segment_trading_into_the_last_week_is_alive():
    cal = pd.bdate_range("2026-03-02", "2026-06-30")
    segs = cm.split_segments("Z", _file(cal, np.full(len(cal), 3.0), np.ones(len(cal))), cal)
    assert segs[0].death is None


def test_momentum_death_inside_the_month_takes_D_then_BIL():
    cal = pd.bdate_range("2016-01-04", "2016-03-31")
    me = cm.month_ends(cal)
    px = pd.Series(10.0, index=cal)
    death = pd.Timestamp("2016-02-10")
    px[px.index > death] = np.nan
    px[death] = 8.0
    C = pd.DataFrame({"A#0": px})
    MC = C.groupby(C.index.to_period("M")).last()
    bil = pd.Series(np.linspace(100, 101, len(cal)), index=cal)
    hr = mom.holding_returns(["A#0"], 0, me, C, MC, {"A#0": px.dropna()}, {"A#0": death}, bil, -0.30)
    want = 0.8 * 0.7 * (bil[me[1]] / bil[death]) - 1.0
    assert hr.loc["A#0", "dead"] and hr.loc["A#0", "r"] == pytest.approx(want)
    hr0 = mom.holding_returns(["A#0"], 0, me, C, MC, {"A#0": px.dropna()}, {"A#0": death}, bil, 0.0)
    assert hr0.loc["A#0", "r"] == pytest.approx(0.8 * (bil[me[1]] / bil[death]) - 1.0)


def test_decile_is_floor_n_over_10_ties_broken_by_segment_id():
    idx = [f"S{i:04d}#0" for i in range(600)]
    fr = pd.DataFrame({"sig": np.r_[np.full(10, 5.0), np.linspace(1, 0, 590)],
                       "traded": True, "adv": 5e6, "univ": True}, index=idx)
    out = mom.select_decile(fr)
    assert out["k"] == 60 and out["sel"][:10] == idx[:10]
    fr.loc[idx[0], "adv"] = 3e8                                 # >= $200M leaves the band
    out = mom.select_decile(fr)
    assert idx[0] not in out["sel"] and out["n_ge200M"] == 1


def test_cmp_routine_from_the_year_after_the_third_same_month_year():
    rows = pd.DataFrame({"owner": [1.0] * 4 + [2.0] * 3, "issuer": [9.0] * 7,
                         "trans_date": pd.to_datetime(["2010-03-05", "2011-03-09", "2013-03-01",
                                                       "2014-07-01", "2010-03-05", "2011-04-09",
                                                       "2013-05-01"])})
    ys = ins.routine_from_year(rows)
    assert ys.loc[(1, 9)] == 2014 and (2, 9) not in ys.index


def test_cluster_is_point_in_time_on_filing_date_and_cools_off_for_the_hold():
    cal_full = pd.bdate_range("2015-01-01", "2017-12-29")
    f = pd.to_datetime
    rows = pd.DataFrame({
        "issuer": [5.0] * 6, "owner": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "filing_date": f(["2016-03-01", "2016-03-02", "2016-03-10", "2016-03-11",
                          "2016-05-02", "2016-11-01"]),
        "trans_date": f(["2016-02-27", "2016-03-01", "2016-01-15", "2016-03-09",
                         "2016-04-29", "2016-10-28"])})
    ev = ins.detect_clusters(rows, cal_full)
    # owner 3's trade is > 30 days before 03-10, so the 3rd insider arrives on 03-11 (size 3)
    assert list(ev["d"]) == [pd.Timestamp("2016-03-11")] and list(ev["size"]) == [3]
    rows2 = pd.concat([rows, pd.DataFrame({"issuer": [5.0, 5.0], "owner": [7.0, 8.0],
                                           "filing_date": f(["2016-11-01", "2016-11-02"]),
                                           "trans_date": f(["2016-10-31", "2016-11-01"])})])
    ev2 = ins.detect_clusters(rows2.sort_values("filing_date"), cal_full)
    # 2016-11-02 is beyond the 126-day hold of the 03-11 event -> a second event
    assert list(ev2["d"]) == [pd.Timestamp("2016-03-11"), pd.Timestamp("2016-11-02")]


def test_event_path_applies_D_after_the_last_traded_close_then_bil():
    close = pd.Series([10.0, 11.0, 12.0, 12.0, 12.0])
    bil = np.array([100.0, 100.0, 100.0, 101.0, 102.0])
    p = ins.event_path(close, 0, 2, bil, -1.0, 4)
    assert p[0] == pytest.approx(0.1) and p[1] == pytest.approx(12 / 11 - 1)
    assert p[2] == pytest.approx(-1.0 * 1.0 + (1.01 - 1.0) * 0.0)   # (1-1) * 101/100 - 1 = -1
    assert p[3] == pytest.approx(102 / 101 - 1)                      # then BIL, never 0/0
    p3 = ins.event_path(close, 0, 2, bil, -0.3, 4)
    assert p3[2] == pytest.approx(0.7 * 101 / 100 - 1)
    p0 = ins.event_path(close, 0, ins.NO_DEATH, bil, -0.3, 4)
    assert np.allclose(np.cumprod(1 + p0)[-1], 1.2)


def test_book_caps_at_40_and_skips_new_arrivals():
    cal = pd.bdate_range("2016-01-04", periods=200)
    ev = pd.DataFrame({"e": [1] * 45, "issuer": list(range(45)), "death_idx": [ins.NO_DEATH] * 45})
    paths = {i: np.full(126, 0.001) for i in ev.index}
    cost = {i: 0.0 for i in ev.index}
    V, bc = ins.simulate_book(ev, paths, cost, cal, np.zeros(200), 1, 150)
    assert bc["skipped_cap"] == 5 and bc["n_live_max"] == 40 and bc["cap_binding_days"] == 1
    assert V.iloc[-1] == pytest.approx(1.001 ** 126)


def test_satellite_label_rule_A1_6():
    assert cm.satellite_label({"ci_low": 0.01, "point": 0.2}, 0.43) == "ci_low > 0"
    assert "not demonstrable" in cm.satellite_label({"ci_low": -0.3, "point": 0.1}, 0.43)
    assert "not demonstrable" not in cm.satellite_label({"ci_low": -0.01, "point": 0.5}, 0.43)


def test_canonical_md5_ignores_key_order_and_run_meta():
    a = {"x": 1.0, "y": {"b": 2, "a": 0.1 + 0.2}, "run_meta": {"wall": 1}}
    b = {"y": {"a": 0.30000000000000004, "b": 2}, "x": 1.0, "run_meta": {"wall": 9}}
    assert cm.canonical_md5(a) == cm.canonical_md5(b)


def test_bootstrap_refuses_short_windows():
    with pytest.raises(cm.Halt):
        cm.boot(12, lambda i: 0.0)


# ============================================================ review hardening (2026-11-11)
import zipfile  # noqa: E402

SUB_H = "ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\tISSUERTRADINGSYMBOL\n"
ND_H = ("ACCESSION_NUMBER\tSECURITY_TITLE\tTRANS_DATE\tTRANS_CODE\tTRANS_SHARES\t"
        "TRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n")
OWN_H = "ACCESSION_NUMBER\tRPTOWNERCIK\n"
FN_H = "ACCESSION_NUMBER\tFOOTNOTE_ID\tFOOTNOTE_TXT\n"


def _zip(tmp_path, sub=None, nd=None, own=None, fn=None, name="2016q1_form345.zip"):
    sub = sub if sub is not None else SUB_H + "A1\t01-FEB-2016\t4\t0000049196\tHBAN\n"
    nd = nd if nd is not None else ND_H + "A1\tCommon\t01-FEB-2016\tP\t100\t8.5\tA\n"
    own = own if own is not None else OWN_H + "A1\t0001000001\n"
    fn = fn if fn is not None else FN_H + "A1\tF1\tplain footnote\n"
    with zipfile.ZipFile(tmp_path / name, "w") as z:
        for nm, body in (("SUBMISSION.tsv", sub), ("NONDERIV_TRANS.tsv", nd),
                         ("REPORTINGOWNER.tsv", own), ("FOOTNOTES.tsv", fn)):
            z.writestr(nm, body)
    return tmp_path


def test_scan_zips_positive_control_reads_one_clean_quarter(tmp_path):
    rows, any4, any4z = ins.scan_zips(_zip(tmp_path), expected_quarters=1)
    assert len(rows) == 1 and int(rows["owner"].iloc[0]) == 1000001
    assert any4 == {2016: {49196}} and any4z == {2016: {49196}}


def test_scan_zips_halts_on_a_wrong_quarter_count(tmp_path):
    with pytest.raises(cm.Halt, match="quarters"):
        ins.scan_zips(_zip(tmp_path), expected_quarters=81)


@pytest.mark.parametrize("bad", ["A1\tCommon\t01-FEB-2016\tP\t100\t8.5\tA\tEXTRA\n",   # too many
                                 "A1\tCommon\t01-FEB-2016\tP\n"])                       # too few
def test_a_malformed_line_halts_never_skips(tmp_path, bad):
    with pytest.raises(cm.Halt, match="field count"):
        ins.scan_zips(_zip(tmp_path, nd=ND_H + bad), expected_quarters=1)


@pytest.mark.parametrize("field,nd", [
    ("TRANS_DATE", ND_H + "A1\tCommon\t31-FOO-2016\tP\t100\t8.5\tA\n"),
    ("TRANS_SHARES", ND_H + "A1\tCommon\t01-FEB-2016\tP\tlots\t8.5\tA\n"),
    ("TRANS_PRICEPERSHARE", ND_H + "A1\tCommon\t01-FEB-2016\tP\t100\t$8.5\tA\n")])
def test_an_unparseable_value_halts_never_coerces(tmp_path, field, nd):
    with pytest.raises(cm.Halt, match=field):
        ins.scan_zips(_zip(tmp_path, nd=nd), expected_quarters=1)


def test_an_unparseable_filing_date_or_cik_halts(tmp_path):
    with pytest.raises(cm.Halt, match="FILING_DATE"):
        ins.scan_zips(_zip(tmp_path, sub=SUB_H + "A1\t2016-02-01\t4\t49196\tHBAN\n"),
                      expected_quarters=1)
    with pytest.raises(cm.Halt, match="ISSUERCIK"):
        ins.scan_zips(_zip(tmp_path, sub=SUB_H + "A1\t01-FEB-2016\t4\tCIK49196\tHBAN\n"),
                      expected_quarters=1)


def test_a_purchase_without_a_reporting_owner_halts(tmp_path):
    with pytest.raises(cm.Halt, match="missing a required id"):
        ins.scan_zips(_zip(tmp_path, own=OWN_H + "ZZ\t0001000001\n"), expected_quarters=1)


def test_an_empty_optional_value_is_not_a_parse_failure():
    s = ins.strict_parse(pd.Series(["8.5", None]), "num", "x")
    assert s.iloc[0] == 8.5 and np.isnan(s.iloc[1])


def test_count_rows_refuses_rows_without_ids():
    rows = pd.DataFrame({"owner": [np.nan], "issuer": [1.0],
                         "trans_date": [pd.Timestamp("2016-01-04")],
                         "filing_date": [pd.Timestamp("2016-01-05")], "shares": [1.0],
                         "price": [1.0], "pref": [False], "aff": [False], "fn": [False]})
    with pytest.raises(cm.Halt):
        ins.count_rows(rows, pd.Series(dtype=float), "base")


def test_too_few_cohorts_is_NOT_EVALUABLE_and_the_gate_halts():
    entry = pd.to_datetime(["2016-02-02", "2016-03-02", "2016-04-04"])
    ev = pd.DataFrame({"entry": entry}, index=[0, 1, 2])
    car = pd.Series([0.1, -0.05, 0.02], index=[0, 1, 2])
    with pytest.raises(cm.NotEvaluable):
        cm.nw_mean_t(car.to_numpy())
    with pytest.raises(cm.Halt):
        ins.study_stats(ev, car, gate=True)
    out = ins.study_stats(ev, car, gate=False)
    assert out["t_hac"] == cm.NOT_EVALUABLE and out["cohort_mean_of_means"] == cm.NOT_EVALUABLE
    with pytest.raises(cm.Halt):
        ins.study_stats(ev.iloc[:0], car.iloc[:0], gate=True)


def test_alpha_regression_refuses_short_or_nonfinite_input():
    with pytest.raises(cm.NotEvaluable):
        cm.nw_alpha(np.zeros(5), np.zeros(5))
    with pytest.raises(cm.NotEvaluable):
        cm.nw_alpha(np.r_[np.zeros(30), np.nan], np.zeros(31))


def test_any_census_count_that_disagrees_halts_and_a_match_is_recorded():
    rec = cm.enforce_census({"a": 1, "b": "x"}, {"a": 1, "b": "x"})
    assert all(r["ok"] for r in rec.values())
    with pytest.raises(cm.Halt, match="'a'"):
        cm.enforce_census({"a": 2, "b": "x"}, {"a": 1, "b": "x"})
    with pytest.raises(cm.Halt):
        cm.enforce_census({"b": "x"}, {"a": 1, "b": "x"})      # a missing recomputation


# ============================================================ main() census wiring (review round 2)
# Each harness's main() must HALT (exit 2) when a census count disagrees with its declaration. The
# fixtures are tiny synthetic substrates; the default-arg paths are redirected by wrapping the
# loaders (module constants are bound at def time), and the declared counts are set to the
# fixture's truth (positive control) or to the truth with ONE count off (the refusal).
def _twins(d, cal: pd.DatetimeIndex) -> None:
    d.mkdir()
    rng = np.random.default_rng(7)
    for name, sd in (("SPY", 0.01), ("IWM", 0.012), ("BIL", 0.0001)):
        px = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, sd, len(cal)))
        pd.DataFrame({"Date": cal.strftime("%Y-%m-%d"), "Close": px}).to_csv(d / f"{name}_1d.csv",
                                                                            index=False)


def _prices(d, cal: pd.DatetimeIndex, n: int) -> None:
    d.mkdir()
    rng = np.random.default_rng(11)
    for i in range(n):
        px = 10.0 * np.cumprod(1.0 + rng.normal(0.0001 * (i - n / 2), 0.012, len(cal)))
        df = pd.DataFrame({"close": px, "volume": 2e6 / px},               # $2M/day: in band
                          index=pd.DatetimeIndex(cal, name="timestamp"))
        df.to_parquet(d / f"T{i:02d}.parquet")


def _redirect(monkeypatch, twins, prices) -> pd.DatetimeIndex:
    oc, ot, ou = cm.market_calendar, cm.twins_on, cm.load_universe
    monkeypatch.setattr(cm, "market_calendar",
                        lambda twins_dir=None, start=cm.PANEL_START: oc(twins, start))
    monkeypatch.setattr(cm, "twins_on", lambda cal, twins_dir=None: ot(cal, twins))
    monkeypatch.setattr(cm, "load_universe",
                        lambda cal, prices_dir=None, tickers=None: ou(cal, prices, tickers))
    monkeypatch.setattr(cm, "EXPECTED_PHANTOM_TAIL_FILES", 0)
    monkeypatch.setattr(cm, "EXPECTED_SPLICE_FILES", 0)
    cal = cm.market_calendar()
    monkeypatch.setattr(cm, "EXPECTED_PRICE_CENSUS",
                        cm.price_census_observed(cm.load_universe(cal)[2]))   # the fixture's truth
    return cal


def _off_by_one(d: dict, key: str) -> dict:
    out = dict(d)
    out[key] = out[key] + 1
    return out


@pytest.fixture
def mom_fixture(tmp_path, monkeypatch):
    cal = pd.bdate_range("2016-01-04", "2025-10-31")     # -> 105 formations, not the declared 111
    _twins(tmp_path / "tw", cal)
    # prices run past DEATH_CUTOFF so the survivor-only arm has survivors; the twins set the calendar
    _prices(tmp_path / "px", pd.bdate_range("2016-01-04", "2026-06-30"), 15)
    _redirect(monkeypatch, tmp_path / "tw", tmp_path / "px")
    monkeypatch.setattr(mom, "MIN_ELIGIBLE", 10)
    monkeypatch.setattr(mom, "MIN_DECILE", 1)
    return tmp_path


def test_momentum_main_positive_control_passes_its_census(mom_fixture):
    assert mom.main(["--smoke", "--out", str(mom_fixture / "ok")]) == 0
    rec = __import__("json").loads((mom_fixture / "ok" / "momentum_census_check.json").read_text())
    assert rec["price"] and all(v["ok"] for v in rec["price"].values())


def test_momentum_main_halts_on_a_price_census_mismatch(mom_fixture, monkeypatch, capsys):
    monkeypatch.setattr(cm, "EXPECTED_PRICE_CENSUS", _off_by_one(cm.EXPECTED_PRICE_CENSUS, "files"))
    assert mom.main(["--smoke", "--out", str(mom_fixture / "bad")]) == 2
    assert "census recomputation disagrees" in capsys.readouterr().err
    assert not (mom_fixture / "bad" / "momentum_results.json").exists()


def test_momentum_main_halts_on_a_window_census_mismatch(mom_fixture, capsys):
    # 105 >= MIN_MONTHS, so only the §3.6 window check (111 declared) can stop this run
    assert mom.main(["--out", str(mom_fixture / "win")]) == 2
    err = capsys.readouterr().err
    assert "census recomputation disagrees" in err and "'formations': (111, 105)" in err
    assert not (mom_fixture / "win" / "momentum_results.json").exists()


@pytest.fixture
def ins_fixture(tmp_path, monkeypatch):
    cal = pd.bdate_range("2016-01-04", "2017-09-29")
    _twins(tmp_path / "tw", cal)
    _prices(tmp_path / "px", cal, 12)
    cal = _redirect(monkeypatch, tmp_path / "tw", tmp_path / "px")
    t265 = tmp_path / "t265"
    t265.mkdir()
    pd.DataFrame({"cik": np.arange(1000, 1012, dtype=np.int64),
                  "ticker": [f"T{i:02d}" for i in range(12)]}).to_parquet(t265 / "cik_ticker_final.parquet")
    monkeypatch.setattr(cm, "T265", t265)
    sub, nd, own = [SUB_H], [ND_H], [OWN_H]
    for i in range(12):                                   # one 3-insider cluster a month, 12 issuers
        d = pd.Timestamp("2016-02-01") + pd.DateOffset(months=i) + pd.offsets.Week(weekday=0)
        ds = d.strftime("%d-%b-%Y").upper()
        for j in range(3):
            acc = f"A{i:02d}{j}"
            sub.append(f"{acc}\t{ds}\t4\t{1000 + i:010d}\tT{i:02d}\n")
            nd.append(f"{acc}\tCommon Stock\t{ds}\tP\t100\t10.0\tA\n")
            own.append(f"{acc}\t{5000 + 3 * i + j:010d}\n")
    zd = tmp_path / "zips"
    zd.mkdir()
    _zip(zd, sub="".join(sub), nd="".join(nd), own="".join(own), fn=FN_H)
    osz = ins.scan_zips
    monkeypatch.setattr(ins, "scan_zips", lambda zdir=None, expected_quarters=None: osz(zd, 1))
    rows, _, any4z = ins.scan_zips()
    fin = pd.read_parquet(t265 / "cik_ticker_final.parquet")
    truth = ins.form4_census_observed(rows, any4z, fin, cm.load_universe(cal)[2], cal,
                                      ins.EXPECTED_ZIPS)
    monkeypatch.setattr(ins, "EXPECTED_F4_CENSUS", truth)
    return tmp_path


def test_insider_main_positive_control_passes_its_census(ins_fixture):
    assert ins.main(["--smoke", "--out", str(ins_fixture / "ok")]) == 0
    rec = __import__("json").loads((ins_fixture / "ok" / "insider_census_check.json").read_text())
    assert all(v["ok"] for blk in ("price", "form4") for v in rec[blk].values())


def test_insider_main_halts_on_a_form4_census_mismatch(ins_fixture, monkeypatch, capsys):
    monkeypatch.setattr(ins, "EXPECTED_F4_CENSUS", _off_by_one(ins.EXPECTED_F4_CENSUS, "inwin_rows"))
    assert ins.main(["--smoke", "--out", str(ins_fixture / "bad")]) == 2
    err = capsys.readouterr().err
    assert "census recomputation disagrees" in err and "inwin_rows" in err
    assert not (ins_fixture / "bad" / "insider_results.json").exists()


def test_insider_main_halts_on_a_price_census_mismatch(ins_fixture, monkeypatch, capsys):
    monkeypatch.setattr(cm, "EXPECTED_PRICE_CENSUS",
                        _off_by_one(cm.EXPECTED_PRICE_CENSUS, "zero_volume_bars"))
    assert ins.main(["--smoke", "--out", str(ins_fixture / "bad")]) == 2
    err = capsys.readouterr().err
    assert "census recomputation disagrees" in err and "zero_volume_bars" in err
    assert not (ins_fixture / "bad" / "insider_results.json").exists()


def test_price_census_observed_uses_the_census_definitions():
    cal = _cal(300)
    vol = np.ones(300) * 1000.0
    vol[-7:] = 0.0                                               # a 7-bar phantom tail
    df = _file(cal, np.full(300, 5.0), vol)
    fc = cm.file_census(df, cal)
    fcen = pd.DataFrame([dict(fc, ticker="T")]).set_index("ticker")
    obs = cm.price_census_observed(fcen)
    assert obs["files"] == 1 and obs["zero_volume_bars"] == 7 and obs["phantom_tail_files_ge5"] == 1
    assert obs["files_lt_60_bars"] == 0 and obs["nonpositive_close_files"] == 0
    assert set(obs) == set(cm.EXPECTED_PRICE_CENSUS)
