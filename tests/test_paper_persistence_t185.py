# tests/test_paper_persistence_t185.py
"""T-185 — the host-independent persistence pieces: trading-calendar +
auction-window gating, the dead-man's-switch heartbeat, and the
reconcile-on-restart self-heal (proven, not assumed).
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from paper_trader import (
    FakePaperClient,
    MarketCalendar,
    OrderManager,
    OrderState,
    PaperConfig,
    PaperHeartbeat,
    PaperScheduler,
    ReconcileInputs,
    TimeInForce,
    make_client_order_id,
)

ET = ZoneInfo("America/New_York")
CFG = "cfg-t185"


def _et(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=ET)


# ===================================================================== #
# Trading-calendar + auction-window awareness
# ===================================================================== #
class TestMarketCalendar:
    def test_offline_fallback_skips_weekends_and_holidays(self):
        cal = MarketCalendar()                      # offline fallback
        assert cal.is_trading_day(date(2026, 6, 17)) is True    # Wed
        assert cal.is_trading_day(date(2026, 6, 20)) is False   # Sat
        assert cal.is_trading_day(date(2026, 6, 21)) is False   # Sun
        assert cal.is_trading_day(date(2026, 6, 19)) is False   # Juneteenth

    def test_broker_calendar_is_authoritative(self):
        class _Client:
            def trading_days(self, start, end):
                return {date(2026, 6, 17), date(2026, 6, 18)}   # 19 closed
        cal = MarketCalendar(client=_Client())
        assert cal.is_trading_day(date(2026, 6, 17)) is True
        assert cal.is_trading_day(date(2026, 6, 19)) is False

    def test_broker_failure_falls_back_not_raises(self):
        class _Bad:
            def trading_days(self, start, end):
                raise ConnectionError("down")
        cal = MarketCalendar(client=_Bad())
        assert cal.is_trading_day(date(2026, 6, 17)) is True    # fallback

    @pytest.mark.parametrize("hour,minute,expected", [
        (19, 0, True), (23, 30, True), (3, 0, True), (9, 27, True),
        (9, 28, False), (12, 0, False), (15, 56, False), (18, 59, False),
    ])
    def test_opg_window(self, hour, minute, expected):
        cal = MarketCalendar()
        assert cal.is_opg_window(_et(2026, 6, 17, hour, minute)) is expected

    @pytest.mark.parametrize("hour,minute,expected", [
        (9, 35, True), (15, 49, True), (15, 50, False), (16, 5, False),
    ])
    def test_cls_window(self, hour, minute, expected):
        cal = MarketCalendar()
        assert cal.is_cls_window(_et(2026, 6, 17, hour, minute)) is expected

    def test_auction_window_open_routes_by_tif(self):
        cal = MarketCalendar()
        now = _et(2026, 6, 17, 15, 56)              # midday: OPG closed, CLS closed
        assert cal.auction_window_open("opg", now) is False
        assert cal.auction_window_open("cls", now) is False
        assert cal.auction_window_open("day", now) is True   # unrestricted


# ===================================================================== #
# Scheduler window gate (the T-169 finding, fixed)
# ===================================================================== #
class TestSchedulerWindowGate:
    def _armed(self, tmp_path, now):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(
            om, reconcile_log_path=str(tmp_path / "r.jsonl"),
            dry_run=False, armed=True,
            paper_config=PaperConfig(allocator="mean_variance"),
            designated_allocator="mean_variance",
            calendar=MarketCalendar(), now_fn=lambda: now)
        return sched, om, client

    def test_opg_outside_window_is_deferred_not_submitted(self, tmp_path):
        # 15:56 ET — outside the OPG window → DEFER, do NOT submit.
        sched, om, client = self._armed(tmp_path, _et(2026, 6, 17, 15, 56))
        o = om.stage("2026-06-17", "SPY", "buy", 1, TimeInForce.OPG, CFG)
        summary = sched.run_day("2026-06-17", [o],
                                lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
        assert client.submitted == []               # nothing submitted
        opg = next(s for s in summary.steps if s.step == "submit_opg")
        assert "DEFERRED" in opg.note and "window" in opg.note
        assert o.state == OrderState.STAGED.value   # order held for the window

    def test_opg_inside_window_submits(self, tmp_path):
        # 20:00 ET — inside the OPG window → submit.
        sched, om, client = self._armed(tmp_path, _et(2026, 6, 17, 20, 0))
        o = om.stage("2026-06-17", "SPY", "buy", 1, TimeInForce.OPG, CFG)
        sched.run_day("2026-06-17", [o],
                      lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
        assert any(x["client_order_id"] == o.client_order_id for x in client.submitted)


# ===================================================================== #
# Trading-day skip
# ===================================================================== #
class TestTradingDaySkip:
    def test_non_trading_day_skips(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                               dry_run=True, calendar=MarketCalendar())
        o = om.stage("2026-06-20", "SPY", "buy", 1, TimeInForce.OPG, CFG)  # Sat
        result = sched.run_trading_day("2026-06-20", [o],
                                       lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
        assert result is None                       # skipped, no run


# ===================================================================== #
# The dead-man's-switch heartbeat
# ===================================================================== #
class TestHeartbeat:
    def test_clean_run_is_canonical_and_alive(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        hb.record_run("2026-06-17", reconcile_clean_cycles=3,
                      reconcile_total_cycles=3, halted=False, submitted=1,
                      fills=1, account_explained=True)
        v = hb.check(date(2026, 6, 17), is_trading_day=True)
        assert v.alive and not v.alert

    def test_miss_alerts(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        hb.record_run("2026-06-15", reconcile_clean_cycles=3,
                      reconcile_total_cycles=3, halted=False, submitted=1,
                      fills=1, account_explained=True)
        # today is 06-17 (trading day) but the last run was 06-15 → MISS
        v = hb.check(date(2026, 6, 17), is_trading_day=True)
        assert not v.alive and v.alert and "silently stopped" in v.reason
        assert (tmp_path / "al.log").read_text().strip()        # alert logged

    def test_non_canonical_run_alerts(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        hb.record_run("2026-06-17", reconcile_clean_cycles=2,   # 2/3 = not clean
                      reconcile_total_cycles=3, halted=True, submitted=1,
                      fills=0, account_explained=True)
        v = hb.check(date(2026, 6, 17), is_trading_day=True)
        assert not v.alive and v.alert
        import json
        status = json.loads((tmp_path / "hb.json").read_text())
        assert status["alert"] is True             # dashboard surfaces it

    def test_never_ran_alerts(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        v = hb.check(date(2026, 6, 17), is_trading_day=True)
        assert v.alert and "never ran" in v.reason

    def test_non_trading_day_is_alive_without_run(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        # no run recorded, but it's a Saturday → alive (no run expected)
        v = hb.check(date(2026, 6, 20), is_trading_day=False)
        assert v.alive and not v.alert

    def test_census_failure_makes_run_non_canonical(self, tmp_path):
        hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                            alert_log=str(tmp_path / "al.log"))
        # a summary whose census block fails (zero-trade)
        bad_summary = {"census": {"n_trades": 0, "trades_empty": True}}
        rec = hb.record_run("2026-06-17", reconcile_clean_cycles=3,
                            reconcile_total_cycles=3, halted=False, submitted=1,
                            fills=1, account_explained=True, summary=bad_summary)
        assert rec.canonical is False and rec.census_failures


# ===================================================================== #
# Reconcile-on-restart self-heal — PROVEN, not assumed
# ===================================================================== #
class TestReconcileOnRestart:
    def test_crash_mid_cycle_restart_reconciles_and_resumes(self, tmp_path):
        """Submit an order, 'crash' (drop the manager), restart from the
        journal, and confirm: (a) it reconciles the live order vs broker
        truth, (b) it does NOT re-POST, (c) the loop can resume."""
        jp = str(tmp_path / "o.jsonl")
        coid = make_client_order_id("2026-06-17", "SPY", "buy", 1, CFG)
        client1 = FakePaperClient()
        client1.script_submit(coid, status="accepted", broker_order_id="bkr-live")
        mgr1 = OrderManager(client1, journal_path=jp)
        o = mgr1.submit(mgr1.stage("2026-06-17", "SPY", "buy", 1, TimeInForce.OPG, CFG))
        assert o.state == OrderState.ACKED.value
        assert len(client1.submitted) == 1

        # "Crash" → a brand-new process restarts from the same journal.
        # The broker still knows the order (acked).
        client2 = FakePaperClient()
        client2.script_polls(coid, [{"status": "accepted", "broker_order_id": "bkr-live"}])
        mgr2 = OrderManager(client2, journal_path=jp)       # reconciles on __init__
        recovered = mgr2.get(coid)
        assert recovered is not None
        assert recovered.state == OrderState.ACKED.value     # adopted broker truth
        # Resume: a submit attempt does NOT re-POST (idempotent across restart).
        mgr2.submit(recovered)
        assert client2.submitted == []                       # ZERO new POSTs
        # And the loop can proceed: poll → fill.
        client2.script_polls(coid, [{"status": "filled", "filled_qty": 1,
                                     "filled_avg_price": 600.0}])
        mgr2.poll(recovered)
        assert recovered.state == OrderState.FILLED.value

    def test_crash_before_post_lands_reverts_to_staged(self, tmp_path):
        """Crash after the SUBMITTED intent but before the POST landed
        (broker has no record) → restart reverts to STAGED so the
        in-window cadence can deliberately re-submit (not blind-resubmit)."""
        from paper_trader._jsonl import JsonlStore
        jp = str(tmp_path / "o.jsonl")
        coid = make_client_order_id("2026-06-17", "SPY", "buy", 1, CFG)
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-17", "ticker": "SPY",
            "side": "buy", "qty": 1, "tif": "opg", "state": "submitted",
            "broker_order_id": None, "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting"})
        client = FakePaperClient()                  # broker has NO record → ABSENT
        mgr = OrderManager(client, journal_path=jp)
        assert mgr.get(coid).state == OrderState.STAGED.value
