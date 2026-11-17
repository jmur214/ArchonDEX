"""B-6 AMENDMENT 7 — the overlap gap fill's selection, its condition (a) check, and the S&P harness's
rebalance grid as the T-265 census applies it. Synthetic inputs only; no network, no price."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.lazy_prices import b6_census as C
from scripts.lazy_prices import b6_harness_sp as H
from scripts.lazy_prices.b6_stream_t265 import select_ciks


def _write_fill_inputs(tmp_path, monkeypatch) -> None:
    fl = pd.DataFrame({"cik": [1, 2, 2, 3], "accession": ["a1", "b1", "x", "c1"]})
    cand = pd.DataFrame({
        "cik": [1, 1, 2, 2, 3, 3, 4, 5],
        "form": ["10-K", "10-Q", "10-K", "10-Q", "10-K", "10-Q", "10-K", "10-K"],
        # CIK 1: a 2014 filing outside the fetch list (before FILL_SINCE -> not a gap)
        # CIK 2: fully fetched
        # CIK 3: shares accession 'x' with CIK 2 (a co-registrant); 'x' is fetched for 2 only
        # CIK 4: not in the fetch list (not an overlap firm); CIK 5: overlap but not T-265 priced
        "accession": ["a1", "a0", "b1", "x", "c1", "x", "d1", "e1"],
        "acceptance_dt": ["2016-02-01T00:00:00.000Z", "2014-11-01T00:00:00.000Z",
                          "2016-02-01T00:00:00.000Z", "2016-05-01T00:00:00.000Z",
                          "2017-02-01T00:00:00.000Z", "2016-05-01T00:00:00.000Z",
                          "2016-02-01T00:00:00.000Z", "2016-02-01T00:00:00.000Z"]})
    fl.loc[len(fl)] = {"cik": 5, "accession": "e0"}
    fl.to_parquet(tmp_path / "fl.parquet", index=False)
    cand.to_parquet(tmp_path / "cand.parquet", index=False)
    monkeypatch.setattr(C, "SP_FETCH_LIST", tmp_path / "fl.parquet")
    monkeypatch.setattr(C, "SP_CANDIDATES", tmp_path / "cand.parquet")


def test_overlap_gap_is_keyed_on_cik_and_accession_and_starts_2015(tmp_path, monkeypatch):
    _write_fill_inputs(tmp_path, monkeypatch)
    universe = {1, 2, 3, 4}
    assert C.overlap_gap_ciks(universe) == [3]
    assert C.overlap_gap_accessions(universe) == {(3, "x")}


def test_select_ciks_default_skips_the_sp_overlap_and_fill_takes_exactly_the_gap():
    universe = [1, 2, 3, 4, 7]
    sp = {2, 3, 7}
    assert select_ciks(False, sp, universe) == [1, 4]
    assert select_ciks(True, sp, universe, [7, 3]) == [3, 7]
    assert select_ciks(True, sp, universe, []) == []


def test_select_ciks_halts_on_a_fill_cik_outside_the_overlap():
    with pytest.raises(SystemExit):
        select_ciks(True, {2, 3}, [1, 2, 3], [1])        # not an S&P-overlap CIK
    with pytest.raises(SystemExit):
        select_ciks(True, {2, 3, 9}, [1, 2, 3], [9])     # not T-265 priced


def _rates(panel: str, k: float, q: float) -> list[dict]:
    rows = []
    for form, v in (("10-K", k), ("10-Q", q)):
        rows.append({"panel": panel, "form": form, **{r: v for r in C.FILL_RATES}})
        if form == "10-K":
            rows[-1]["qoq_mda_pair_pct_2016on"] = float("nan")
    return rows


def test_fill_check_is_two_sided_at_three_points():
    rates = pd.DataFrame(_rates("base", 90.0, 90.0) + _rates("fill", 93.0, 86.9))
    chk = C.fill_check(rates, "base", "fill")
    assert len(chk) == 5 + 6                              # 10-K has no adjacent pair rate
    assert chk[chk.form == "10-K"].within_3pp.all()      # +3.0 exactly is within
    assert not chk[chk.form == "10-Q"].within_3pp.any()  # -3.1 is outside
    better = C.fill_check(pd.DataFrame(_rates("base", 90.0, 90.0) + _rates("fill", 93.5, 90.0)),
                          "base", "fill")
    assert not better[better.form == "10-K"].within_3pp.any()   # better by > 3 also fails (as written)


def test_harness_grid_is_the_sp_harness_rule_last_spy_bar_on_or_before_quarter_end(tmp_path, monkeypatch):
    days = pd.bdate_range("2016-12-20", "2017-04-05")
    days = days[days != pd.Timestamp("2017-03-31")]       # a quarter-end with no bar
    (tmp_path / "SPY_1d.csv").write_text("Date,Close\n" + "".join(f"{d.date()},1.0\n" for d in days))
    monkeypatch.setattr(H, "TWINS", tmp_path)
    grid = C.harness_grid("2016-12-31", "2017-03-31")
    assert grid == [pd.Timestamp("2016-12-30"), pd.Timestamp("2017-03-30")]
    assert grid == H.rebalance_dates(pd.DatetimeIndex(days), "2016-12-31", "2017-03-31")


def test_eligibility_uses_the_grid_date_not_the_calendar_quarter_end():
    sig = pd.DataFrame({
        "cik": [1, 1, 2],
        "form": ["10-Q", "10-K", "10-Q"],
        # CIK 1: a 10-Q, then a 10-K accepted Fri 2016-12-30 -> floor Sat 2016-12-31
        "acc": pd.to_datetime(["2016-11-10", "2016-12-30", "2016-06-01"]),
        "floor": pd.to_datetime(["2016-11-11", "2016-12-31", "2016-06-02"]),
        "gate_ok": [True, False, True], "hoos_ok": [True, False, True]})
    sig["acceptance_dt"] = sig.acc.dt.strftime("%Y-%m-%d")
    sig = sig.sort_values(["floor", "acceptance_dt"])
    on_grid = C._eligibility(sig, [pd.Timestamp("2016-12-30")], set())
    on_cal = C._eligibility(sig, [pd.Timestamp("2016-12-31")], set())
    assert on_grid.iloc[0].gate_usable == 1 and on_grid.iloc[0].ciks_with_recent_filing == 1
    assert on_cal.iloc[0].gate_usable == 0 and on_cal.iloc[0].ciks_with_recent_filing == 1


def _pop_rows() -> pd.DataFrame:
    """One CIK's 10-K rows covering every A8.3 case (the 2015 row is a prior only)."""
    r = [  # accession, year, risk_status, prior_accession, combo why, mda why
        ("p15", "2015", "OK", None, "no_prior", "no_prior"),
        ("a", "2016", "OK", "p15", "ok", "ok"),                                  # counts, ok
        ("b", "2017", "OK", None, "no_prior", "no_prior"),                       # (a) excluded
        ("c", "2018", "NOT_COVERED:not_required", "a", "current_not_ok", "ok"),   # (b) combo only
        ("d", "2019", "OK", "c", "prior_not_ok", "ok"),                           # (b) prior NC, combo only
        ("e", "2020", "NOT_LOCATED", "d", "current_not_ok", "ok"),                # stays a failure
        ("f", "2021", "OK", "e", "mda_source_switch", "mda_source_switch"),       # stays a failure
        ("g", "2022", "TOO_SHORT", "f", "current_not_ok", "current_not_ok"),      # stays a failure
    ]
    return pd.DataFrame([{"cik": 1, "form": "10-K", "accession": a, "acceptance_dt": f"{y}-03-01T00:00:00.000Z",
                          "risk_status": rs, "prior_accession": pa, "yoy_combo_why": cw, "yoy_mda_why": mw}
                         for a, y, rs, pa, cw, mw in r])


def test_amendment8_check_excludes_exactly_no_prior_and_combo_not_covered():
    sig = _pop_rows()
    # combo: denominator = a, e, f, g (b excluded by (a); c, d by (b)); numerator = a
    assert C.pop_rate(sig, "10-K", "yoy_combo_why", True) == (25.0, 1, 4)
    # MD&A: denominator = a, c, d, e, f, g (only b excluded); numerator = a, c, d, e
    assert C.pop_rate(sig, "10-K", "yoy_mda_why", False) == (66.7, 4, 6)


def test_amendment8_check_halts_when_a_prior_cannot_be_looked_up():
    sig = _pop_rows()
    sig.loc[sig.accession == "a", "prior_accession"] = "missing"
    with pytest.raises(SystemExit):
        C.pop_rate(sig, "10-K", "yoy_combo_why", True)


def test_holder_table_build_halts_when_there_are_no_insider_zips(tmp_path, monkeypatch):
    """Review finding 6: no zips must HALT, never return an empty holder table (which would silently
    drop every ambiguous T-265 ticker from the ranking)."""
    from scripts.lazy_prices import b6_cik_map as M
    monkeypatch.setattr(M, "INSIDER_DIR", tmp_path)
    with pytest.raises(SystemExit, match="no insider zips"):
        M.symbol_users({"AAA", "BBB"})
