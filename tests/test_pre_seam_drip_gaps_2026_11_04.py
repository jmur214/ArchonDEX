"""The `pre_seam_drip_gap` class (ruled 2026-10-23, built 2026-11-04): the kept pre-seam DRIP's own
holes are a DECLARED, COUNTED class keyed to the convention label — never silent, never a
tolerance. Locks, each through the real guard (`coverage.stale_files_record`), the real gate reader
(`core.census.coverage_defects` / `assert_census`), both producers and the REAL measured-run
admission (`ModeController.run_backtest`):

  * the drip's own pre-seam holes are excused and COUNTED (per name, in total, in the record);
  * a planted POST-seam hole under a drip label is NOT excused;
  * a planted PRE-seam hole the file does not have is NOT excused (the frame's hole is not the
    kept drip's); a file whose pre-seam bar count no longer equals the kept count excuses nothing;
  * without `cache_dir` the class is OFF (fail closed); an unlabelled name, or a label with no
    drip span, gets no excuse; an explicit `holed_inside` declaration excuses first;
  * the real COPY reads 215 names / 380 days (the item-1(b) computation of the cutover record),
    holed 1 (SLE: post-seam, class (i)), stale 3 (CCR, DLPH, FSR: the membership identity defect);
  * the measured-run admission ADMITS a real canonical name whose only holes are the kept drip's.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.census import assert_census, coverage_defects
from engines.data_manager import coverage
from engines.data_manager.coverage import PRE_SEAM_DRIP_GAP, stale_files_record
from engines.data_manager.tr_writer import CANONICAL_CACHE_DIR, WRITE_RECORDS_DIR

ROOT = Path(__file__).resolve().parents[1]
COPY = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/cutover_copy_2026_10_22")
DAYS = pd.bdate_range("2017-01-02", "2018-06-29")
START, END = str(DAYS[0].date()), str(DAYS[-1].date())
SEAM = pd.Timestamp("2018-01-02")
DRIP_HOLES = [pd.Timestamp("2017-03-15"), pd.Timestamp("2017-09-20")]       # the kept drip's own


@pytest.fixture(autouse=True)
def _isolate_the_per_process_membership_exclusion_log(monkeypatch):
    """This file loads the REAL PIT membership (the COPY lock below), and `exclusions.py` keeps
    `_MEMBERSHIP_APPLIED` / `_TICKER_MEMBERSHIP_APPLIED` PER PROCESS (`reset_exclusion_log` skips
    them by design: membership loads once). In suite order the dal_pre2007 / MTD / NVR records that
    load wrote leaked into test_price_levels_item_d (…served_whole) and
    test_ticker_exclusion_scale_defect (…KEEP_BOTH_reasons) — both pass alone. Each test here gets
    fresh dicts; the module's own are restored untouched (found at the merge, 2026-11-04)."""
    from engines.data_manager import exclusions
    monkeypatch.setattr(exclusions, "_MEMBERSHIP_APPLIED", {})
    monkeypatch.setattr(exclusions, "_TICKER_MEMBERSHIP_APPLIED", {})


def _csv(path: Path, dates) -> None:
    rows = ["Date,Open,High,Low,Close,Volume"] + [f"{d.date()},1,1,1,1,1" for d in dates]
    path.write_text("\n".join(rows) + "\n")


def _cache(tmp_path: Path, file_holes=DRIP_HOLES, kept: int | None = None, convention=None) -> tuple:
    """A cache with DRP's file (DAYS minus `file_holes`) and its pinned write record: the seam at
    2018-01-02 and the kept pre-seam bar count (the file's own, unless `kept` overrides it)."""
    d = tmp_path / "cache"
    d.mkdir()
    dates = DAYS.drop([h for h in file_holes if h in DAYS])
    _csv(d / "DRP_1d.csv", dates)
    (d / WRITE_RECORDS_DIR).mkdir()
    conv = convention if convention is not None else {"pre_seam": "drip", "seam_date": "2018-01-02",
                                                      "post_seam": "exact_tr"}
    rec = {"ticker": "DRP", "convention": conv,
           "seam": {"date": "2018-01-02", "source": "merge_meta",
                    "n_pre_seam_bars_kept": int((dates < SEAM).sum()) if kept is None else kept}}
    (d / WRITE_RECORDS_DIR / "DRP.json").write_text(json.dumps(rec))
    return d, dates


def _frame(dates) -> pd.DataFrame:
    return pd.DataFrame({"Close": [1.0] * len(dates)}, index=pd.DatetimeIndex(dates))


def _map(drp_dates) -> dict:
    m = {t: _frame(DAYS) for t in ("SPY", "AAA", "BBB", "CCC")}
    m["DRP"] = _frame(drp_dates)
    return m


def _stale_failures(rec: dict) -> list:
    """The gate's stale_files failures for this record (the other invariants are not under test)."""
    v = assert_census({"census": {"stale_files": rec}, "bootstrap_ci_skip_reason": "test"})
    return [f for f in v.failures if f.startswith("stale_files")]


# ---------------------------------------------------------------- the class, on planted data ------

def test_the_kept_drips_own_pre_seam_holes_are_EXCUSED_and_COUNTED(tmp_path):
    cache, dates = _cache(tmp_path)
    rec = stale_files_record(_map(dates), START, END, declared={}, cache_dir=cache)
    r = rec["names"]["DRP"]
    assert r["missing_trading_days"] == 2 and r["undeclared_missing_days"] == 0
    assert r["pre_seam_drip_gap_days"] == 2 and r["declared"] == [PRE_SEAM_DRIP_GAP]
    assert "pre_seam_drip_gap_not_excused" not in r
    assert rec["n_holed"] == 0 and rec["n_declared"] == 1
    dg = rec["pre_seam_drip_gaps"]
    assert dg["class"] == PRE_SEAM_DRIP_GAP and dg["cache_dir"] == str(cache)
    assert dg["n_names"] == 1 and dg["n_days"] == 2 and dg["per_name"] == {"DRP": 2} and dg["not_excused"] == {}
    assert coverage_defects(rec) == [] and _stale_failures(rec) == []


def test_a_planted_POST_seam_hole_under_a_drip_label_is_NOT_excused(tmp_path):
    post = pd.Timestamp("2018-03-14")
    cache, dates = _cache(tmp_path, file_holes=DRIP_HOLES + [post])      # the file lacks it too
    rec = stale_files_record(_map(dates), START, END, declared={}, cache_dir=cache)
    r = rec["names"]["DRP"]
    assert r["pre_seam_drip_gap_days"] == 2 and r["undeclared_missing_days"] == 1     # the two still counted
    assert "post-seam" in r["pre_seam_drip_gap_not_excused"] and rec["n_holed"] == 1
    assert rec["pre_seam_drip_gaps"]["n_days"] == 2 and "DRP" in rec["pre_seam_drip_gaps"]["not_excused"]
    fails = _stale_failures(rec)
    assert fails and any("DRP" in f and "post-seam" in f for f in fails), fails


def test_a_planted_PRE_seam_hole_the_file_does_NOT_have_is_NOT_excused(tmp_path):
    """The frame lacks 2017-06-14; the file has it: not the kept drip's hole. The witness fails for
    the name, so NONE of its pre-seam holes are excused (the span is not proven to be the drip)."""
    cache, dates = _cache(tmp_path)
    planted = dates.drop(pd.Timestamp("2017-06-14"))
    rec = stale_files_record(_map(planted), START, END, declared={}, cache_dir=cache)
    r = rec["names"]["DRP"]
    assert r["missing_trading_days"] == 3 and r["undeclared_missing_days"] == 3 and r["pre_seam_drip_gap_days"] == 0
    assert "the file does not have" in r["pre_seam_drip_gap_not_excused"] and "2017-06-14" in r["pre_seam_drip_gap_not_excused"]
    assert rec["n_holed"] == 1 and rec["pre_seam_drip_gaps"]["n_names"] == 0
    fails = _stale_failures(rec)
    assert fails and any("DRP" in f and "the file does not have" in f for f in fails), fails


def test_a_file_whose_pre_seam_span_is_NOT_the_kept_drip_excuses_NOTHING(tmp_path):
    """The record says one more pre-seam bar was kept than the file holds (a bar dropped since the
    write — a hole the canonical never had): the kept-count identity fails; nothing is excused."""
    cache, dates = _cache(tmp_path, kept=int((DAYS < SEAM).sum()) - 1)       # file = kept − 1
    rec = stale_files_record(_map(dates), START, END, declared={}, cache_dir=cache)
    r = rec["names"]["DRP"]
    assert r["undeclared_missing_days"] == 2 and r["pre_seam_drip_gap_days"] == 0
    assert "NOT the kept drip" in r["pre_seam_drip_gap_not_excused"]
    assert rec["n_holed"] == 1 and any("NOT the kept drip" in f for f in _stale_failures(rec))


def test_without_cache_dir_the_class_is_OFF_fail_closed(tmp_path):
    cache, dates = _cache(tmp_path)
    rec = stale_files_record(_map(dates), START, END, declared={})
    r = rec["names"]["DRP"]
    assert r["undeclared_missing_days"] == 2 and r["pre_seam_drip_gap_days"] == 0 and rec["n_holed"] == 1
    assert "no cache_dir" in r["pre_seam_drip_gap_not_excused"]
    dg = rec["pre_seam_drip_gaps"]
    assert dg["cache_dir"] is None and dg["n_days"] == 0 and "DRP" in dg["not_excused"]
    assert any("no cache_dir" in f for f in _stale_failures(rec))


def test_a_holed_inside_declaration_excuses_FIRST_and_the_class_counts_only_what_remains(tmp_path):
    cache, dates = _cache(tmp_path)
    decl = {"DRP": {"holed_inside": {"n": 1, "runs": [["2017-03-15", "2017-03-15"]]}, "reason": "t", "source": "p"}}
    rec = stale_files_record(_map(dates), START, END, declared=decl, cache_dir=cache)
    r = rec["names"]["DRP"]
    assert r["undeclared_missing_days"] == 0 and r["pre_seam_drip_gap_days"] == 1
    assert r["declared"] == ["holed_inside", PRE_SEAM_DRIP_GAP]
    assert rec["pre_seam_drip_gaps"]["per_name"] == {"DRP": 1} and rec["n_holed"] == 0


def test_an_UNLABELLED_name_and_a_label_with_NO_drip_span_get_no_excuse(tmp_path):
    cache, dates = _cache(tmp_path, convention={"whole": "exact_tr"})      # labelled, but no drip span
    m = _map(dates)
    m["NOLBL"] = _frame(DAYS.drop(DRIP_HOLES))                               # no record, no merge entry
    rec = stale_files_record(m, START, END, declared={}, cache_dir=cache)
    assert rec["n_holed"] == 2 and rec["pre_seam_drip_gaps"]["n_days"] == 0
    assert "no pre-seam drip span" in rec["names"]["DRP"]["pre_seam_drip_gap_not_excused"]
    assert rec["names"]["NOLBL"]["pre_seam_drip_gap_not_excused"].startswith("no convention label")
    assert any("DRP" in f and "NOLBL" in f for f in _stale_failures(rec))


# ---------------------------------------------------------------- the real copy and the canonical --

def _dates_map(cache: Path) -> dict:
    out = {}
    for p in sorted(cache.glob("*_1d.csv")):
        t = p.name[:-7]
        pq = cache / "parquet" / f"{t}_1d.parquet"
        out[t] = (pd.read_parquet(pq, columns=["Close"]) if pq.exists()
                  else pd.read_csv(p, usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date"))
    return out


@pytest.mark.skipif(not COPY.is_dir(), reason=f"the cutover copy is absent on this host: {COPY}")
def test_the_real_COPY_reads_215_names_and_380_days_under_the_class_holed_1_stale_3():
    """The item-1(b) computation of docs/Audit/cutover_step1_record_2026_10_22.md, locked: over
    2000-01-03 → 2025-12-31 under PIT intervals the kept drip's pre-seam holes the class excuses
    are 380 days over 215 names; what remains is SLE (428 post-seam holes; class (i), a non-member
    required to the window end in a cache-wide read) and the three stale names of the membership
    identity defect (CCR, DLPH, FSR). READ-ONLY on the copy."""
    from engines.data_manager.membership import load_membership
    rec = stale_files_record(_dates_map(COPY), "2000-01-03", "2025-12-31", intervals=load_membership(),
                             cache_dir=COPY)
    dg = rec["pre_seam_drip_gaps"]
    assert dg["n_names"] == 215 and dg["n_days"] == 380, (dg["n_names"], dg["n_days"])
    assert all(v >= 1 for v in dg["per_name"].values()) and sum(dg["per_name"].values()) == 380
    assert rec["n_holed"] == 1 and list(dg["not_excused"]) == ["SLE"] and "post-seam" in dg["not_excused"]["SLE"]
    assert rec["n_stale"] == 3
    assert sorted(t for t, v in rec["names"].items() if v["ends_before_required"]
                  and not v["end_declared_as_delisting"]) == ["CCR", "DLPH", "FSR"]
    assert rec["calendar"]["checked_against"] == "SPY" and not rec["calendar"]["calendar_missing_days"]


def _canonical_frames(names) -> dict:
    out = {}
    for t in names:
        p = CANONICAL_CACHE_DIR / f"{t}_1d.csv"
        out[t] = pd.read_csv(p, usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date")
    return out


def test_on_the_CANONICAL_cache_a_real_drip_names_pre_seam_holes_are_the_classs_merge_record_witnessed():
    """A (seam 2018-01-02 from the merge record; the Stooq years holed) over 2000 → 2003 with SPY as
    the calendar: its pre-seam holes are excused under the class and counted; the record names the
    canonical cache; the gate passes."""
    rec = stale_files_record(_canonical_frames(["SPY", "A"]), "2000-01-03", "2003-12-31",
                             cache_dir=CANONICAL_CACHE_DIR)
    a = rec["names"]["A"]
    assert a["missing_trading_days"] >= 1 and a["pre_seam_drip_gap_days"] == a["missing_trading_days"]
    assert a["undeclared_missing_days"] == 0 and rec["n_holed"] == 0
    assert rec["pre_seam_drip_gaps"]["per_name"] == {"A": a["missing_trading_days"]}
    assert rec["pre_seam_drip_gaps"]["cache_dir"] == str(CANONICAL_CACHE_DIR)
    assert coverage_defects(rec) == []


class _Reached(Exception):
    """run_backtest got PAST the admission (to edge loading)."""


def _mode_controller(tmp_path, data_map, monkeypatch, start, end):
    from orchestration.mode_controller import ModeController

    class _DM:
        def ensure_data(self, tickers, start, end, timeframe="1d"):
            return data_map

        def prefetch_fundamentals(self, tickers):
            return None

    mc = object.__new__(ModeController)
    mc.root = tmp_path
    mc.cfg_bt = {"start_date": start, "end_date": end, "tickers": sorted(data_map),
                 "timeframe": "1d", "initial_capital": 100000.0, "use_historical_universe": False}
    mc.dm = _DM()

    def _stop(*a, **k):
        raise _Reached()
    monkeypatch.setattr(mc, "_load_edges_via_registry", _stop, raising=False)
    return mc


def test_the_MEASURED_admission_ADMITS_a_real_canonical_name_whose_only_holes_are_the_kept_drips(tmp_path, monkeypatch):
    """The real `ModeController.run_backtest`, measured mode, A + SPY over 2000 → 2003: the admission
    reads the same class as the census and ADMITS the run (reaches edge loading). The positive
    control: the same admission with the class OFF (the guard forced to `cache_dir=None`) HALTS on A
    — so the admission above is the class's doing, not a fixture's."""
    from core.measured import MeasurementHalt
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    monkeypatch.setattr(coverage, "DATA_GAPS_PATH", tmp_path / "none.json")
    mc = _mode_controller(tmp_path, _canonical_frames(["SPY", "A"]), monkeypatch, "2000-01-03", "2003-12-31")
    with pytest.raises(_Reached):
        mc.run_backtest()
    real = stale_files_record                       # the admission imports the name at call time

    def _class_off(*a, **k):
        return real(*a, **{**k, "cache_dir": None})
    monkeypatch.setattr(coverage, "stale_files_record", _class_off)
    with pytest.raises(MeasurementHalt, match=r"coverage\.stale_or_holed.*HOLED.*\bA\b"):
        mc.run_backtest()
