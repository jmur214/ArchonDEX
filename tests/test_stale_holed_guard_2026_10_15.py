"""The stale/holed-files guard (2026-10-15) — coverage counts BARS, never file presence.

Locks, each on planted data and each through the code that runs (the shared record, the shared
gate reader, both census producers, and the measured-run admission inside the REAL
`ModeController.run_backtest`):
  * R's binding correction — the END test is PER NAME against the EARLIER of the window end and the
    member's exit (a band victim that later exited is stale; a genuine exit is not);
  * holes counted against the trading calendar, holidays never counted;
  * the calendar PROVEN against SPY both ways (a holed SPY; a mass hole the majority cannot see — the
    real cache's 1999-11-16 shape; no SPY → unverified, a failure); SPY's own early end is SPY's
    stale entry, never a calendar hole;
  * declarations excuse exactly what they declare (`holed_inside` runs; `ends_at_delisting` last
    bar), neither excuses the other, and a malformed declaration file raises;
  * formation coverage counts rows FORMED on the date, never a file on disk (the B-1 defect);
  * a measured run with an undeclared stale name HALTS (MeasurementHalt via halt_or_degrade), never
    a silent drop; outside measured mode it WARNs and the census gate fails the run.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from core.census import assert_census, coverage_defects
from core.measured import MeasurementHalt
from engines.data_manager import coverage
from engines.data_manager.coverage import load_data_gaps, stale_files_record

DAYS = pd.bdate_range("2024-01-01", "2024-06-28")
START, END = str(DAYS[0].date()), str(DAYS[-1].date())


def _frame(dates) -> pd.DataFrame:
    dates = pd.DatetimeIndex(dates)
    return pd.DataFrame({"Close": [100.0] * len(dates)}, index=dates)


def _clean_map(extra: dict | None = None) -> dict:
    m = {t: _frame(DAYS) for t in ("SPY", "AAA", "BBB", "CCC", "DDD")}
    m.update(extra or {})
    return m


def _gate(rec: dict):
    return assert_census({"census": {"stale_files": rec}, "bootstrap_ci_skip_reason": "test"})


def _stale_failures(rec: dict) -> list:
    return [f for f in _gate(rec).failures if f.startswith("stale_files")]


def _intervals(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["ticker", "start", "end"]).assign(
        start=lambda d: pd.to_datetime(d["start"]), end=lambda d: pd.to_datetime(d["end"]))


# ---------------------------------------------------------------- the END test, per name ----------

def test_a_live_name_whose_file_ends_early_is_STALE_and_the_gate_fails():
    rec = stale_files_record(_clean_map({"NVX": _frame(DAYS[DAYS <= "2024-04-30"])}), START, END,
                             declared={})
    assert rec["n_stale"] == 1 and rec["names"]["NVX"]["ends_before_required"]
    assert rec["names"]["NVX"]["required_end"] == END
    assert any("END before their required end" in f and "NVX" in f for f in _stale_failures(rec))


def test_R_correction_a_band_victim_that_LATER_EXITED_is_stale_against_its_exit():
    """The drafted test asked only names still live at the window end. A member that exited inside
    the window (here 2024-05-31) whose file stops months earlier (2024-02-15, the band's cut) passed
    it — its stale months inside its membership are exactly the band's (R's binding correction)."""
    iv = _intervals([("BVX", "2010-01-04", "2024-05-31")])
    rec = stale_files_record(_clean_map({"BVX": _frame(DAYS[DAYS <= "2024-02-15"])}), START, END,
                             intervals=iv, declared={})
    r = rec["names"]["BVX"]
    assert r["exited_in_window"] and r["required_end"] == "2024-05-31"
    assert r["ends_before_required"] and rec["n_stale"] == 1


def test_a_genuine_exit_whose_file_ends_at_the_exit_is_NOT_stale():
    iv = _intervals([("GEX", "2010-01-04", "2024-05-31"), ("LIV", "2010-01-04", None)])
    rec = stale_files_record(_clean_map({"GEX": _frame(DAYS[DAYS <= "2024-05-29"]),
                                         "LIV": _frame(DAYS)}), START, END, intervals=iv, declared={})
    assert rec["n_stale"] == 0 and "GEX" not in rec["names"]
    assert rec["n_exited_in_window"] == 1


def test_a_name_with_no_membership_inside_the_window_is_not_required():
    iv = _intervals([("OLD", "2001-01-02", "2015-06-30")])
    rec = stale_files_record(_clean_map({"OLD": _frame(DAYS[:10])}), START, END, intervals=iv,
                             declared={})
    assert "OLD" not in rec["names"] and rec["n_stale"] == 0 and rec["n_holed"] == 0


# ---------------------------------------------------------------- holes and holidays --------------

def test_a_planted_hole_is_counted_with_its_longest_run():
    holed = DAYS.delete(list(range(40, 47)) + [90])          # a 7-day run and a single day
    rec = stale_files_record(_clean_map({"HLD": _frame(holed)}), START, END, declared={})
    r = rec["names"]["HLD"]
    assert r["missing_trading_days"] == 8 and r["undeclared_missing_days"] == 8
    assert r["longest_missing_run"] == 7 and rec["n_holed"] == 1
    assert any("HOLED" in f and "HLD" in f for f in _stale_failures(rec))


def test_holidays_never_count():
    """A date EVERY file lacks is not a trading day (no holiday table: the calendar is data)."""
    holiday = DAYS[30]
    m = {t: _frame(DAYS.delete(30)) for t in ("SPY", "AAA", "BBB", "CCC")}
    rec = stale_files_record(m, START, END, declared={})
    assert holiday not in set(pd.to_datetime(m["SPY"].index))
    assert rec["n_holed"] == 0 and rec["names"] == {}
    assert rec["calendar"]["trading_days"] == len(DAYS) - 1 and coverage_defects(rec) == []


# ---------------------------------------------------------------- the calendar, proven ------------

def test_a_clean_run_passes_with_the_calendar_checked_against_SPY():
    rec = stale_files_record(_clean_map(), START, END, declared={})
    assert rec["calendar"]["checked_against"] == "SPY" and coverage_defects(rec) == []
    assert _stale_failures(rec) == []


def test_a_HOLED_SPY_fails_the_gate():
    m = _clean_map({"SPY": _frame(DAYS.delete(50))})
    rec = stale_files_record(m, START, END, declared={})
    assert rec["calendar"]["spy_missing_days"] == [str(DAYS[50].date())]
    assert any("SPY is holed" in f for f in _stale_failures(rec))


def test_a_MASS_hole_the_majority_cannot_see_is_caught_by_SPY():
    """The real cache's 1999-11-16: 244 of 248 active files lack a day SPY traded, so the majority
    calendar drops it and no file is counted holed. The reverse check names it and the gate fails."""
    m = {"SPY": _frame(DAYS)}
    m.update({t: _frame(DAYS.delete(60)) for t in ("AAA", "BBB", "CCC", "DDD")})
    rec = stale_files_record(m, START, END, declared={})
    assert rec["n_holed"] == 0                                 # invisible to the per-name count
    assert rec["calendar"]["calendar_missing_days"] == [str(DAYS[60].date())]
    assert any("reference calendar is holed" in f for f in _stale_failures(rec))


def test_SPYs_own_early_end_is_its_STALE_entry_not_a_calendar_hole():
    """The real cache's SPY ends 2026-04-17 while 481 files run to 04-24: that is SPY stale, not
    SPY holed."""
    m = _clean_map({"SPY": _frame(DAYS[:-5])})
    rec = stale_files_record(m, START, END, declared={})
    assert rec["calendar"]["spy_missing_days"] == []
    assert rec["names"]["SPY"]["ends_before_required"] and rec["n_stale"] == 1


def test_no_SPY_means_an_UNVERIFIED_calendar_which_fails():
    m = {t: _frame(DAYS) for t in ("AAA", "BBB", "CCC")}
    rec = stale_files_record(m, START, END, declared={})
    assert rec["calendar"]["checked_against"] is None
    assert any("UNVERIFIED" in f for f in _stale_failures(rec))


# ---------------------------------------------------------------- declarations, facet by facet ----

def _decl(**facets) -> dict:
    return {**facets, "reason": "test", "source": "planted"}


def test_holed_inside_runs_excuse_EXACTLY_the_declared_days():
    holed = DAYS.delete(list(range(40, 47)))
    run = [str(DAYS[40].date()), str(DAYS[46].date())]
    rec = stale_files_record(_clean_map({"HLD": _frame(holed)}), START, END,
                             declared={"HLD": _decl(holed_inside={"n": 7, "runs": [run]})})
    r = rec["names"]["HLD"]
    assert r["missing_trading_days"] == 7 and r["undeclared_missing_days"] == 0
    assert rec["n_holed"] == 0 and rec["n_declared"] == 1 and r["declared"] == ["holed_inside"]
    assert _stale_failures(rec) == []
    # one more hole, outside the declared run → undeclared → the gate fails
    rec2 = stale_files_record(_clean_map({"HLD": _frame(holed.delete(80))}), START, END,
                              declared={"HLD": _decl(holed_inside={"n": 7, "runs": [run]})})
    assert rec2["names"]["HLD"]["undeclared_missing_days"] == 1 and rec2["n_holed"] == 1
    assert _stale_failures(rec2)


def test_ends_at_delisting_excuses_the_end_ONLY_at_its_declared_last_bar():
    """JNPR's shape: last print 2025-07-01, the index's recorded exit 07-09 — six trading days, one
    beyond the slack. Declared, never absorbed by widening the slack."""
    iv = _intervals([("JNX", "2010-01-04", "2024-05-31")])
    data = _clean_map({"JNX": _frame(DAYS[DAYS <= "2024-05-21"])})
    last = "2024-05-21"
    ok = stale_files_record(data, START, END, intervals=iv,
                            declared={"JNX": _decl(ends_at_delisting={"last_bar": last})})
    assert ok["names"]["JNX"]["ends_before_required"] and ok["names"]["JNX"]["end_declared_as_delisting"]
    assert ok["n_stale"] == 0 and ok["n_declared"] == 1 and _stale_failures(ok) == []
    wrong = stale_files_record(data, START, END, intervals=iv,
                               declared={"JNX": _decl(ends_at_delisting={"last_bar": "2024-05-24"})})
    assert wrong["n_stale"] == 1 and _stale_failures(wrong)
    assert stale_files_record(data, START, END, intervals=iv, declared={})["n_stale"] == 1


def test_a_holed_declaration_never_excuses_an_early_END():
    data = _clean_map({"XHD": _frame(DAYS[DAYS <= "2024-04-30"])})
    rec = stale_files_record(data, START, END, declared={"XHD": _decl(
        holed_inside={"n": 1, "runs": [["2024-05-01", "2024-06-28"]]})})
    assert rec["n_stale"] == 1 and not rec["names"]["XHD"]["end_declared_as_delisting"]


def test_an_end_declaration_never_excuses_a_HOLE():
    data = _clean_map({"XDH": _frame(DAYS.delete(20))})
    rec = stale_files_record(data, START, END, declared={"XDH": _decl(
        ends_at_delisting={"last_bar": str(DAYS[-1].date())})})
    assert rec["n_holed"] == 1 and rec["names"]["XDH"]["undeclared_missing_days"] == 1


@pytest.mark.parametrize("bad", [
    {"declarations": {"X": {"holed_inside": {"runs": []}, "source": "s"}}},              # no reason
    {"declarations": {"X": {"reason": "r", "source": "s"}}},                             # no facet
    {"declarations": {"X": {"holed_inside": {"runs": [["2024-02-01", "2024-01-01"]]},
                            "reason": "r", "source": "s"}}},                             # reversed
    {"declarations": {"X": {"ends_at_delisting": {"last_bar": "not-a-date"},
                            "reason": "r", "source": "s"}}},
])
def test_a_malformed_declaration_file_RAISES(tmp_path, bad):
    p = tmp_path / "data_gaps.json"
    p.write_text(json.dumps(bad))
    with pytest.raises((ValueError, KeyError)):
        load_data_gaps(p)


def test_the_SHIPPED_declarations_load_and_name_the_first_set():
    """The first set (2026-10-15): every holed file NO provider can fill, built mechanically from the
    holes census; ends_at_delisting only where the PIT exit evidences it; plus one PROVIDER GAP on a
    day the security traded (FISV 2025-11-12: absent from the universe provider in both modes,
    present in an independent source), declared with that evidence."""
    d = load_data_gaps()
    assert len(d) == 46
    assert {"BBBY", "PSKY", "CPWR", "CCE", "NCC", "CFC"} <= set(d)
    ends = {t for t, v in d.items() if "ends_at_delisting" in v}
    assert len(ends) == 19 and d["JNPR"]["ends_at_delisting"] == {
        "last_bar": "2025-07-01", "pit_exit": "2025-07-09"}
    assert all("holed_inside" in v and v["holed_inside"]["runs"] for v in d.values())
    assert sum(v["holed_inside"]["n"] for v in d.values()) == 1299
    assert d["FISV"]["holed_inside"] == {"n": 1, "runs": [["2025-11-12", "2025-11-12"]]}
    assert d["FISV"]["reason"].startswith("provider gap") and "Alpaca" in d["FISV"]["source"]


# ---------------------------------------------------------------- formation coverage --------------

def test_formation_coverage_counts_rows_FORMED_on_the_date_not_files_on_disk():
    """A member with a file but no bar on the formation date is UNCOVERED (B-1's coverage_pct
    counted the file)."""
    fdate = DAYS[60]
    iv = _intervals([(t, "2010-01-04", None) for t in ("AAA", "BBB", "CCC", "DDD")])
    m = _clean_map({"DDD": _frame(DAYS[DAYS > fdate])})        # DDD's file starts after the date
    rec = stale_files_record(m, START, END, intervals=iv, declared={}, formation_dates=[fdate])
    fc = rec["formation_coverage"]
    assert fc["rule"] == "rows FORMED on the formation date"
    # five members on the date (SPY is outside the membership: required throughout); DDD formed no row
    assert fc["dates"] == 1 and fc["min"] == pytest.approx(4 / 5) and fc["dates_below_0_80"] == 0
    m["CCC"] = _frame(DAYS[DAYS > fdate])
    fc2 = stale_files_record(m, START, END, intervals=iv, declared={},
                             formation_dates=[fdate])["formation_coverage"]
    assert fc2["min"] == pytest.approx(3 / 5) and fc2["dates_below_0_80"] == 1


# ---------------------------------------------------------------- both producers ------------------

def test_the_candidate_producer_writes_the_record_and_its_gate_reads_it():
    from engines.engine_d_discovery.discovery import candidate_census_block

    class _C:
        nonzero_calls, errors = 5, 0

    block = candidate_census_block("cand_v1", _C(), n_trades=50,
                                   data_map=_clean_map({"NVX": _frame(DAYS[DAYS <= "2024-04-30"])}),
                                   window=(START, END))
    assert block["stale_files"]["n_stale"] == 1
    v = assert_census({"census": block, "bootstrap_ci_skip_reason": "test"})
    assert any("NVX" in f for f in v.failures)
    errored = candidate_census_block("cand_v1", _C(), n_trades=50)
    assert "error" in errored["stale_files"]
    v2 = assert_census({"census": errored, "bootstrap_ci_skip_reason": "test"})
    assert any("stale_files record errored" in f for f in v2.failures)


def test_the_backtest_producer_writes_the_record_over_the_run_window(tmp_path):
    from backtester.backtest_controller import BacktestController

    class _Alpha:
        class collector:
            _signal_counts, _bars_collected, _edge_errors, _edge_error_samples = {"e": 3}, 40, {}, {}

        class processor:
            paused_edge_ids: set = set()
        edges = {"e": object()}

    ctrl = object.__new__(BacktestController)
    ctrl.alpha, ctrl.regime_detector = _Alpha(), object()
    ctrl.data_map = _clean_map({"NVX": _frame(DAYS[DAYS <= "2024-04-30"])})
    ctrl._census_n_resolved = len(ctrl.data_map)
    ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 40, 3
    ctrl._membership_intervals = None
    ctrl._census_window = (START, END)
    p = tmp_path / "trades.csv"
    pd.DataFrame({"ticker": ["SPY"], "pnl": [1.0]}).to_csv(p, index=False)
    census = ctrl._build_census(str(p))
    assert census["stale_files"]["window"] == [START, END] and census["stale_files"]["n_stale"] == 1
    ctrl._census_window = None                       # a run() that never recorded its window
    assert "error" in ctrl._build_census(str(p))["stale_files"]


# ---------------------------------------------------------------- the admission, real entrypoint --

class _Reached(Exception):
    """run_backtest got PAST the admission (to edge loading)."""


def _mode_controller(tmp_path, data_map, monkeypatch):
    from orchestration.mode_controller import ModeController

    class _DM:
        def ensure_data(self, tickers, start, end, timeframe="1d"):
            return data_map

        def prefetch_fundamentals(self, tickers):
            return None

    mc = object.__new__(ModeController)
    mc.root = tmp_path
    mc.cfg_bt = {"start_date": START, "end_date": END, "tickers": sorted(data_map),
                 "timeframe": "1d", "initial_capital": 100000.0, "use_historical_universe": False}
    mc.dm = _DM()

    def _stop(*a, **k):
        raise _Reached()
    monkeypatch.setattr(mc, "_load_edges_via_registry", _stop, raising=False)
    return mc


def test_a_MEASURED_run_with_an_undeclared_stale_name_HALTS_at_admission(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    monkeypatch.setattr(coverage, "DATA_GAPS_PATH", tmp_path / "none.json")
    mc = _mode_controller(tmp_path, _clean_map({"NVX": _frame(DAYS[DAYS <= "2024-04-30"])}),
                          monkeypatch)
    with pytest.raises(MeasurementHalt, match=r"coverage\.stale_or_holed.*NVX"):
        mc.run_backtest()


def test_outside_measured_mode_the_admission_WARNS_and_the_run_proceeds(tmp_path, monkeypatch,
                                                                         capsys):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "0")
    monkeypatch.setattr(coverage, "DATA_GAPS_PATH", tmp_path / "none.json")
    mc = _mode_controller(tmp_path, _clean_map({"NVX": _frame(DAYS[DAYS <= "2024-04-30"])}),
                          monkeypatch)
    with pytest.raises(_Reached):
        mc.run_backtest()
    assert "[RUN_BACKTEST][WARN] coverage:" in capsys.readouterr().out


def test_a_MEASURED_run_on_clean_data_is_ADMITTED(tmp_path, monkeypatch, capsys):
    """The positive control: the halt above is the guard's, not a fixture's."""
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    monkeypatch.setattr(coverage, "DATA_GAPS_PATH", tmp_path / "none.json")
    mc = _mode_controller(tmp_path, _clean_map(), monkeypatch)
    with pytest.raises(_Reached):
        mc.run_backtest()
    assert "coverage:" not in capsys.readouterr().out
