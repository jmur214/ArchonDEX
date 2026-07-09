"""T-288 — EconHealth: the economic/behavioral tripwires the dead-man's-switch
can't see. Pure evaluator (fixed dates, zero I/O) + the report-only heartbeat
stamp (must NEVER flip canonical)."""
from __future__ import annotations

import datetime as dt

from paper_trader.econ_health import (evaluate_econ_health, _weekday_count,
                                      EconHealthReport)
from paper_trader.heartbeat import PaperHeartbeat

TODAY = dt.date(2026, 7, 9)   # a Thursday


# --- Channel A: no-trade-in-N-days ------------------------------------------ #
def test_no_trade_fresh_loop_is_skipped_not_tripped():
    r = evaluate_econ_health(today=TODAY, last_trade_date=None,
                             managed_universe=["SPY"], broker_positions={})
    f = next(x for x in r.findings if x.channel == "no_trade")
    assert f.status == "skipped" and not r.degraded


def test_no_trade_recent_is_ok():
    r = evaluate_econ_health(today=TODAY, last_trade_date=dt.date(2026, 7, 7),
                             managed_universe=["SPY"], broker_positions={})
    f = next(x for x in r.findings if x.channel == "no_trade")
    assert f.status == "ok" and f.value == 2.0


def test_no_trade_beyond_threshold_trips():
    # 30 calendar days back, well over the 20-trading-day default.
    r = evaluate_econ_health(today=TODAY, last_trade_date=dt.date(2026, 5, 20),
                             managed_universe=["SPY"], broker_positions={})
    f = next(x for x in r.findings if x.channel == "no_trade")
    assert f.status == "tripped" and r.degraded and f.value > 20


def test_no_trade_threshold_is_configurable():
    r = evaluate_econ_health(today=TODAY, last_trade_date=dt.date(2026, 7, 6),
                             managed_universe=["SPY"], broker_positions={},
                             no_trade_max_trading_days=1)
    assert next(x for x in r.findings if x.channel == "no_trade").status == "tripped"


# --- Channel B: stale-data freshness ---------------------------------------- #
def test_stale_data_fresh_is_ok():
    r = evaluate_econ_health(today=TODAY, latest_bar_date=dt.date(2026, 7, 8),
                             managed_universe=["SPY"], broker_positions={})
    assert next(x for x in r.findings if x.channel == "stale_data").status == "ok"


def test_stale_data_old_bar_trips():
    # bar from 10 days ago, over the 3-trading-day default.
    r = evaluate_econ_health(today=TODAY, latest_bar_date=dt.date(2026, 6, 29),
                             managed_universe=["SPY"], broker_positions={})
    f = next(x for x in r.findings if x.channel == "stale_data")
    assert f.status == "tripped" and r.degraded


def test_stale_data_no_bar_is_skipped():
    r = evaluate_econ_health(today=TODAY, latest_bar_date=None,
                             managed_universe=["SPY"], broker_positions={})
    assert next(x for x in r.findings if x.channel == "stale_data").status == "skipped"


# --- Channel C: positions-without-exit-coverage ----------------------------- #
def test_orphan_position_trips():
    r = evaluate_econ_health(today=TODAY, managed_universe=["SPY", "AGG", "GLD"],
                             broker_positions={"SPY": 4, "TSLA": 10})
    f = next(x for x in r.findings if x.channel == "orphan_positions")
    assert f.status == "tripped" and "TSLA" in f.detail and r.degraded


def test_all_holdings_managed_is_ok():
    r = evaluate_econ_health(today=TODAY, managed_universe=["SPY", "AGG", "GLD"],
                             broker_positions={"SPY": 4, "AGG": 11})
    assert next(x for x in r.findings if x.channel == "orphan_positions").status == "ok"


def test_zero_qty_position_is_not_an_orphan():
    r = evaluate_econ_health(today=TODAY, managed_universe=["SPY"],
                             broker_positions={"SPY": 4, "TSLA": 0})
    assert next(x for x in r.findings if x.channel == "orphan_positions").status == "ok"


def test_orphan_channel_case_insensitive():
    r = evaluate_econ_health(today=TODAY, managed_universe=["sso"],
                             broker_positions={"SSO": 149})
    assert next(x for x in r.findings if x.channel == "orphan_positions").status == "ok"


def test_missing_universe_skips_orphan_channel():
    r = evaluate_econ_health(today=TODAY, managed_universe=None,
                             broker_positions={"SPY": 4})
    assert next(x for x in r.findings if x.channel == "orphan_positions").status == "skipped"


# --- counting + injected calendar ------------------------------------------- #
def test_weekday_count_excludes_weekend():
    # Thu 2026-07-09 → Mon 2026-07-13 = Fri + Mon = 2 weekdays (Sat/Sun skipped).
    assert _weekday_count(dt.date(2026, 7, 9), dt.date(2026, 7, 13)) == 2


def test_weekday_count_nonpositive_span_is_zero():
    assert _weekday_count(TODAY, TODAY) == 0
    assert _weekday_count(TODAY, dt.date(2026, 7, 8)) == 0


def test_injected_counter_is_used():
    # a holiday-aware counter that returns a fixed large number → trips.
    r = evaluate_econ_health(today=TODAY, last_trade_date=dt.date(2026, 7, 8),
                             managed_universe=["SPY"], broker_positions={},
                             trading_day_counter=lambda a, b: 99)
    assert next(x for x in r.findings if x.channel == "no_trade").status == "tripped"


# --- the report-only contract on the heartbeat ------------------------------ #
def test_record_econ_health_never_touches_canonical(tmp_path):
    hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                        alert_log=str(tmp_path / "a.log"))
    # record a CLEAN canonical run first
    hb.record_run("2026-07-09", reconcile_clean_cycles=3, reconcile_total_cycles=3,
                  halted=False, submitted=0, fills=0, account_explained=True)
    import json
    before = json.loads((tmp_path / "hb.json").read_text())
    assert before["last_run"]["canonical"] is True and before["alert"] is False

    # now stamp a DEGRADED econ-health report — canonical/alert must be untouched
    degraded = evaluate_econ_health(
        today=TODAY, managed_universe=["SPY"], broker_positions={"TSLA": 10})
    assert degraded.degraded
    hb.record_econ_health(degraded)
    after = json.loads((tmp_path / "hb.json").read_text())
    assert after["last_run"]["canonical"] is True      # UNCHANGED
    assert after["alert"] is False                     # UNCHANGED
    assert after["econ_health"]["degraded"] is True    # recorded separately
    assert after["econ_health"]["_schema"] == "paper_econ_health/v1"


def test_record_econ_health_writes_the_notify_channel_on_trip(tmp_path):
    alog = tmp_path / "alerts.log"
    hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"), alert_log=str(alog))
    hb.record_econ_health(evaluate_econ_health(
        today=TODAY, managed_universe=["SPY"], broker_positions={"TSLA": 10}))
    assert alog.exists() and "ECON-HEALTH" in alog.read_text()


def test_record_econ_health_clean_report_no_alert(tmp_path):
    alog = tmp_path / "alerts.log"
    hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"), alert_log=str(alog))
    clean = evaluate_econ_health(today=TODAY, managed_universe=["SPY"],
                                 broker_positions={"SPY": 4},
                                 last_trade_date=dt.date(2026, 7, 8),
                                 latest_bar_date=dt.date(2026, 7, 8))
    assert not clean.degraded
    hb.record_econ_health(clean)
    # no alert line written for a clean report
    assert not alog.exists() or "ECON-HEALTH" not in alog.read_text()
