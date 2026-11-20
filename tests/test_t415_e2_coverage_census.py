"""Locks for the T-415 (E-2) Phase-1 census: the date rules, identity resolution, coverage modes and
the fail-closed paths. Hermetic: synthetic inputs in tmp_path only; no repo data is read."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import t415_e2_coverage_census as c


def _td(start: str = "2023-01-02", end: str = "2025-12-31") -> pd.DatetimeIndex:
    return pd.bdate_range(start, end)


def _panel(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    """rows: (ticker, filing_date, acceptance ET 'HH:MM', items)."""
    out = []
    for i, (t, d, hhmm, items) in enumerate(rows):
        et = pd.Timestamp(f"{d} {hhmm}", tz="America/New_York")
        out.append(dict(ticker=t, cik=1, accession=f"acc-{i:04d}", filing_date=pd.Timestamp(d),
                        acceptance_dt=et.tz_convert("UTC"), items=items))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ dates
def test_after_close_release_reacts_next_trading_day_and_pre_open_same_day():
    td = _td()
    ev = c.earnings_events(_panel([("X", "2024-10-31", "16:30", "2.02,9.01"),
                                   ("Y", "2024-10-31", "07:00", "2.02")]), td)
    got = dict(zip(ev.ticker, ev.react))
    assert got["X"] == pd.Timestamp("2024-11-01")
    assert got["Y"] == pd.Timestamp("2024-10-31")


def test_friday_after_close_rolls_over_the_weekend():
    ev = c.earnings_events(_panel([("X", "2024-11-01", "16:05", "2.02")]), _td())
    assert ev.react.iloc[0] == pd.Timestamp("2024-11-04")


def test_item_12_counts_and_non_earnings_items_do_not():
    ev = c.earnings_events(_panel([("X", "2024-02-01", "08:00", "12,7"),
                                   ("X", "2024-05-01", "08:00", "5.02,9.01"),
                                   ("X", "2024-08-01", "08:00", "2.020")]), _td())
    assert list(ev.react) == [pd.Timestamp("2024-02-01")]


def test_dedupe_keeps_one_release_per_quarter():
    ev = c.earnings_events(_panel([("X", "2024-02-01", "08:00", "2.02"),
                                   ("X", "2024-02-20", "08:00", "2.02"),   # guidance update: dropped
                                   ("X", "2024-05-02", "08:00", "2.02")]), _td())
    assert list(ev.react) == [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-05-02")]


def test_no_earnings_filings_halts():
    with pytest.raises(c.CensusError):
        c.earnings_events(_panel([("X", "2024-02-01", "08:00", "8.01")]), _td())


def test_predict_adds_364_days_and_rolls_to_a_trading_day():
    td = _td()
    ev = pd.DataFrame({"ticker": ["X", "X"],
                       "react": [pd.Timestamp("2023-11-03"), pd.Timestamp("2023-12-29")]})
    p = c.predict(ev, td)
    assert list(p.pred) == [pd.Timestamp("2024-11-01"), pd.Timestamp("2024-12-27")]


def test_prediction_census_exact_annual_pattern_scores_zero_error():
    td = _td("2003-01-01", "2026-12-31")
    d0 = pd.Timestamp("2010-02-05")
    dates = [d0 + pd.Timedelta(days=364 * k) for k in range(8)]
    ev = pd.DataFrame({"ticker": "X", "react": dates})
    out = c.prediction_census(ev, td, pd.Timestamp("2005-01-01"))
    assert out["share_no_prior_year_release"] == pytest.approx(1 / 8)
    assert out["share_abs_err_0_tdays"] == 1.0


def test_announcers_per_week_respects_membership_interval():
    td = _td()
    wk = c.week_ends(td)
    pred = pd.DataFrame({"ticker": ["A", "B"], "react": pd.NaT,
                         "pred": [pd.Timestamp("2024-11-01"), pd.Timestamp("2024-11-01")]})
    memb = pd.DataFrame({"ticker": ["A", "B"], "start": [pd.Timestamp("2020-01-01")] * 2,
                         "end": [pd.Timestamp("2099-12-31"), pd.Timestamp("2024-06-30")]})
    cnt = c.announcers_per_week(pred, memb, wk)
    assert cnt[pd.Timestamp("2024-11-01")] == 1   # B left the index before its predicted date
    assert cnt.sum() == 1


# ------------------------------------------------------------------ identity and departures
def _syms() -> pd.DataFrame:
    return pd.DataFrame({
        "sym": ["FB", "META", "OLD", "OLD", "REUSE"],
        "cik": [100, 100, 200, 201, 300],
        "first": pd.to_datetime(["2012-06-01", "2022-06-10", "2006-01-01", "2006-01-01", "2006-01-01"]),
        "last": pd.to_datetime(["2022-06-08", "2026-03-01", "2010-01-01", "2010-01-01", "2012-01-01"]),
        "n": [500, 300, 40, 5, 50]})


def test_member_cik_picks_the_issuer_with_most_filings_in_the_interval():
    s = _syms()
    assert c.member_cik(s, "OLD", pd.Timestamp("2007-01-01"), pd.Timestamp("2009-01-01")) == 200
    assert c.member_cik(s, "FB", pd.Timestamp("2013-12-23"), pd.Timestamp("2022-06-09")) == 100
    assert c.member_cik(s, "NOPE", pd.Timestamp("2013-12-23"), pd.Timestamp("2022-06-09")) is None


def test_resolve_candidates_lineage_reuse_and_blocked():
    s = _syms()
    live_t2c = {"META": 100, "REUSE": 999}
    live_c2t = {100: ["META"], 999: ["REUSE"]}
    own, succ, ident = c.resolve_candidates("FB", 100, live_t2c, live_c2t, s, set())
    assert own == ["FB"] and succ == ["META"] and ident == "unverified"
    _, _, ident = c.resolve_candidates("REUSE", 300, live_t2c, live_c2t, s, set())
    assert ident == "own_file_other_cik"
    assert c.resolve_candidates("CCE", 1, live_t2c, live_c2t, s, {"CCE"}) == ([], [], "identity_blocked")


def test_departure_kind_rules():
    ch = pd.DataFrame({"rem_t": ["TWX"], "date": [pd.Timestamp("2018-06-18")], "kind": ["M&A"]})
    assert c.departure_kind("AAPL", pd.Timestamp("2099-12-31"), True, ch) == "continuing"
    assert c.departure_kind("LEHMQ", pd.Timestamp("2008-09-17"), False, ch) == "failure"
    assert c.departure_kind("MERQ", pd.Timestamp("2006-01-04"), False, ch) == "no_reason_row"  # 4 letters
    assert c.departure_kind("TWX", pd.Timestamp("2018-06-15"), False, ch) == "M&A"


@pytest.mark.parametrize("reason,kind", [
    ("Lehman Brothers filed for bankruptcy.", "failure"),
    ("S&P 500 constituent Devon Energy Corp. acquired Coterra Energy.", "M&A"),
    ("Market capitalization change.", "demotion"),
    ("Ticker symbol change.", "rename"),
    ("FedEx spun off FedEx Freight.", "spin"),
])
def test_classify_reason(reason, kind):
    assert c.classify_reason(reason) == kind


# ------------------------------------------------------------------ bars and modes
def _write_csv(path: Path, dates: list[str], vols: list[float]) -> None:
    pd.DataFrame({"Date": dates, "Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 10.0,
                  "Volume": vols}).to_csv(path, index=False)


def test_bar_index_modes_volume_dotnames_and_declared_exclusions(tmp_path: Path):
    proc, t265 = tmp_path / "processed", tmp_path / "t265"
    proc.mkdir()
    t265.mkdir()
    _write_csv(proc / "AAA_1d.csv", ["2019-01-02", "2019-01-03", "2021-01-04"], [100, 0, 100])
    _write_csv(proc / "BRK.B_1d.csv", ["2021-01-04"], [100])
    _write_csv(proc / "AZO_1d.csv", ["2021-01-04"], [100])
    pd.DataFrame({"close": [5.0, 5.0], "volume": [10.0, 10.0]},
                 index=pd.DatetimeIndex(["2017-03-01", "2017-03-02"], tz="UTC")).to_parquet(t265 / "AAA.parquet")
    b = c.BarIndex(proc, t265)
    anyd = b.dates("AAA", "any")
    assert pd.Timestamp("2019-01-03") not in anyd          # zero-volume bar is not usable
    assert {pd.Timestamp("2019-01-02"), pd.Timestamp("2017-03-01"), pd.Timestamp("2021-01-04")} <= set(anyd)
    clean = b.dates("AAA", "clean")
    assert pd.Timestamp("2019-01-02") not in clean         # processed refused before 2020-04-09
    assert pd.Timestamp("2017-03-01") in clean             # T-265 bars allowed at any date
    assert pd.Timestamp("2021-01-04") in clean
    assert list(b.dates("BRK-B", "any")) == [pd.Timestamp("2021-01-04")]
    assert len(b.dates("AZO", "any")) == 0 and "AZO" in b.withheld
    with pytest.raises(c.CensusError):
        b.dates("AAA", "other")


# ------------------------------------------------------------------ fail-closed
def test_require_and_loaders_fail_closed(tmp_path: Path):
    with pytest.raises(c.CensusError):
        c.require(tmp_path / "missing.parquet")
    m = pd.DataFrame({"ticker": ["A"], "start": [pd.Timestamp("1990-01-01")],
                      "end": [pd.Timestamp("1995-01-01")]})
    m.to_parquet(tmp_path / "m.parquet")
    with pytest.raises(c.CensusError):
        c.load_membership(tmp_path / "m.parquet", pd.Timestamp("2004-01-01"), pd.Timestamp("2026-01-01"))
    pd.DataFrame({"Date": pd.bdate_range("2024-01-01", periods=20)}).to_csv(tmp_path / "spy.csv", index=False)
    with pytest.raises(c.CensusError):
        c.load_calendar(tmp_path / "spy.csv", pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01"))
    with pytest.raises(c.CensusError):
        c.load_issuer_symbols(str(tmp_path / "*_form345.zip"))


def test_refuses_to_write_under_a_data_tree(tmp_path: Path):
    root = tmp_path / "data"
    root.mkdir()
    with pytest.raises(c.CensusError):
        c.refuse_data_path(root / "out" / "census.json", root)
    c.refuse_data_path(tmp_path / "scratch" / "census.json", root)   # outside: allowed


def test_positive_control_miss_halts():
    cov = pd.DataFrame({"ticker": ["AAPL"], "year": [2010], "n": [252], "any_lenient": [0],
                        "any_strict": [0], "clean_lenient": [0], "clean_strict": [0]})
    ev = pd.DataFrame({"ticker": ["AAPL"], "react": [pd.Timestamp("2023-11-03")]})
    with pytest.raises(c.CensusError):
        c.positive_controls(cov, ev, _td())


def test_main_exits_nonzero_on_a_missing_data_root(tmp_path: Path):
    rc = c.main(["--data-root", str(tmp_path / "nope"), "--out", str(tmp_path / "o.json")])
    assert rc == 2
    assert not (tmp_path / "o.json").exists()


def test_md5_manifest_is_order_independent(tmp_path: Path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("1")
    b.write_text("2")
    assert c.md5_manifest([a, b]) == c.md5_manifest([b, a])
    assert np.isfinite(len(c.md5_file(a)))
