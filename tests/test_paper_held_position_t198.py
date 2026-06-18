# tests/test_paper_held_position_t198.py
"""T-198 — the cloud loop must correctly TRACK held positions (the manual
first fill, fills filling at the open) instead of going permanently
non-canonical. Tests the REAL operating shape the prior suite never
exercised: broker HOLDS, ledger starts EMPTY → adopt the explained part →
clean → canonical; a genuinely UNEXPLAINED position still HALTs +
non-canonical; and the non-trading (Juneteenth) driver branch end-to-end.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from paper_trader import (
    FakePaperClient,
    LedgerStore,
    MarketCalendar,
    OrderManager,
    PaperHeartbeat,
    PaperScheduler,
    ReconcileInputs,
    TimeInForce,
)
from paper_trader.held_reconcile import (
    adopt_explained_broker_truth,
    explain_broker_positions,
    journal_net_positions,
    known_tickers_for,
)

ET = ZoneInfo("America/New_York")
CFG = "cfg-t198"


def _filled_buy(client, om, ticker="SPY", qty=1, price=600.0):
    """Drive one order through to FILLED in the journal."""
    o = om.stage("2026-06-18", ticker, "buy", qty, TimeInForce.OPG, CFG)
    client.script_submit(o.client_order_id, status="accepted")
    om.submit(o)
    client.script_polls(o.client_order_id,
                        [{"status": "filled", "filled_qty": qty,
                          "filled_avg_price": price}])
    om.poll(o)
    return o


# ===================================================================== #
# Pure helpers
# ===================================================================== #
class TestJournalNetAndExplain:
    def test_journal_net_counts_observed_fills_only(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1)
        # an unfilled staged order contributes nothing
        om.stage("2026-06-18", "AAPL", "buy", 3, TimeInForce.OPG, CFG)
        assert journal_net_positions(list(om.orders.values())) == {"SPY": 1}

    def test_explained_when_broker_matches_fills(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1)
        ok, jnet = explain_broker_positions({"SPY": 1}, list(om.orders.values()))
        assert ok is True and jnet == {"SPY": 1}

    def test_unexplained_unknown_symbol(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        ok, _ = explain_broker_positions({"XYZ": 5}, list(om.orders.values()))
        assert ok is False

    def test_unexplained_qty_mismatch(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1)
        ok, _ = explain_broker_positions({"SPY": 5}, list(om.orders.values()))
        assert ok is False           # fills explain 1, broker holds 5

    def test_flat_is_trivially_explained(self):
        ok, jnet = explain_broker_positions({}, [])
        assert ok is True and jnet == {}


class TestAdoption:
    def test_explained_held_is_adopted(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1, price=600.0)
        led = LedgerStore(str(tmp_path / "l.jsonl"), starting_cash=5000.0)
        explained = adopt_explained_broker_truth(
            led, {"SPY": 1}, 4400.0, list(om.orders.values()), reason="test")
        assert explained is True
        assert led.positions() == {"SPY": 1}     # ledger converged
        assert led.cash() == 4400.0              # cash adopted alongside

    def test_unexplained_is_not_adopted(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        led = LedgerStore(str(tmp_path / "l.jsonl"), starting_cash=5000.0)
        explained = adopt_explained_broker_truth(
            led, {"XYZ": 5}, 4000.0, list(om.orders.values()), reason="test")
        assert explained is False
        assert led.positions() == {}             # NOT adopted — assume nothing
        assert led.cash() == 5000.0

    def test_known_tickers_includes_ordered_and_held(self, tmp_path):
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1)
        assert "SPY" in known_tickers_for(list(om.orders.values()), {})


# ===================================================================== #
# Integrated cycle — the real operating shape
# ===================================================================== #
def _run_cycle(tmp_path, broker_positions, broker_cash, orders_om, *,
               starting_cash=5000.0):
    """Mirror run_paper_cloud_day's adopt-then-reconcile flow."""
    led = LedgerStore(str(tmp_path / "l.jsonl"), starting_cash=starting_cash)
    explained = adopt_explained_broker_truth(
        led, broker_positions, broker_cash, list(orders_om.orders.values()),
        reason="cycle")
    ktickers = known_tickers_for(list(orders_om.orders.values()), led.positions())
    hb = PaperHeartbeat(status_path=str(tmp_path / "hb.json"),
                        alert_log=str(tmp_path / "al.log"))
    sched = PaperScheduler(orders_om,
                           reconcile_log_path=str(tmp_path / "r.jsonl"),
                           dry_run=True, calendar=MarketCalendar(), heartbeat=hb)

    def inputs_fn(step):
        return ReconcileInputs(
            ledger_positions=led.positions(), ledger_cash=led.cash(),
            broker_positions=broker_positions, broker_cash=broker_cash,
            orders=list(orders_om.orders.values()), known_tickers=ktickers)

    summary = sched.run_trading_day("2026-06-18", [], inputs_fn,
                                    account_explained=explained)
    v = hb.check(date(2026, 6, 18), is_trading_day=True)
    return summary, v, explained


class TestHeldPositionCycleCanonical:
    def test_held_fill_adopts_then_clean_and_canonical(self, tmp_path):
        # broker holds SPY=1 (the first fill, filled at the open); ledger
        # starts empty; the journal has the FILLED buy that explains it.
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1, price=600.0)
        summary, v, explained = _run_cycle(tmp_path, {"SPY": 1}, 4400.0, om)
        assert explained is True
        assert summary.reconcile_total_cycles > 0
        assert summary.reconcile_clean_cycles == summary.reconcile_total_cycles
        assert not summary.halted
        assert v.alive and not v.alert           # CANONICAL with a held position


class TestUnexplainedHeldNonCanonical:
    def test_known_ticker_qty_mismatch_halts_and_non_canonical(self, tmp_path):
        # broker holds SPY=5 but our fills explain only 1 → unexplained →
        # NOT adopted → POSITION_DRIFT halt → non-canonical.
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        _filled_buy(c, om, "SPY", 1, price=600.0)
        summary, v, explained = _run_cycle(tmp_path, {"SPY": 5}, 2000.0, om)
        assert explained is False
        assert summary.halted                    # position_drift HALT
        assert not v.alive and v.alert           # non-canonical

    def test_unknown_symbol_is_non_canonical(self, tmp_path):
        # a position in a ticker we never ordered → unexplained → at least
        # non-canonical (corporate-action/manual, never silently adopted).
        c = FakePaperClient()
        om = OrderManager(c, journal_path=str(tmp_path / "o.jsonl"))
        summary, v, explained = _run_cycle(tmp_path, {"XYZ": 5}, 4000.0, om)
        assert explained is False
        assert summary.reconcile_clean_cycles < summary.reconcile_total_cycles
        assert not v.alive and v.alert


# ===================================================================== #
# Driver end-to-end through the non-trading (Juneteenth) branch (4c)
# ===================================================================== #
class _RecordingCloud:
    """A CloudState stub that records emit_metrics calls and no-ops S3."""
    class _Cfg:
        enabled = False
        s3_root = "s3://test/paper_state"
    cfg = _Cfg()

    def __init__(self):
        self.metrics = []

    def pull(self):
        return False

    def push(self):
        pass

    def emit_metrics(self, *, happened, canonical):
        self.metrics.append((happened, canonical))


class TestDriverNonTradingBranch:
    def test_juneteenth_drives_happened_canonical_return0(self):
        import scripts.run_paper_cloud_day as drv
        fake = FakePaperClient()                  # no trading_days → offline fallback
        cloud = _RecordingCloud()
        juneteenth = datetime(2026, 6, 19, 8, 0, tzinfo=ET)   # a market holiday
        rc = drv.main(["--allocator", "mean_variance"],
                      now=juneteenth, client=fake, cloud=cloud)
        assert rc == 0
        assert cloud.metrics == [(True, True)]    # happened=True, canonical=True
