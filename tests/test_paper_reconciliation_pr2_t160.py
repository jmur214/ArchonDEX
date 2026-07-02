# tests/test_paper_reconciliation_pr2_t160.py
"""T-160 PR-2 — ReconciliationEngine (7-class taxonomy) + DRY-RUN scheduler.

A fixture per divergence class asserting the PRE-REGISTERED response
(cash/position drift halt; corporate action manual; the rest neither),
the all-agree clean case, and one logged dry-run day proving the
scheduler walks the §1.1 clock and submits NOTHING.
"""
from __future__ import annotations

import pytest

from paper_trader import (
    ALL_CLASSES,
    FakePaperClient,
    OrderManager,
    PaperScheduler,
    ReconciliationEngine,
    ReconcileInputs,
    TimeInForce,
)
from paper_trader.order_manager import OrderRecord, OrderState
from paper_trader.reconciliation import (
    CLASS_CASH_DRIFT,
    CLASS_CORPORATE_ACTION,
    CLASS_MISSED_FILL,
    CLASS_PARTIAL_FILL,
    CLASS_POSITION_DRIFT,
    CLASS_PRICE_DRIFT,
    CLASS_REJECT,
)

CFG = "cfg-x"
ENGINE = ReconciliationEngine()


def _order(ticker="AAPL", side="buy", qty=10, state=OrderState.ACKED,
           filled_qty=0, filled_avg_price=None, tif="opg") -> OrderRecord:
    return OrderRecord(
        client_order_id=f"coid-{ticker}-{qty}", trade_date="2026-06-15",
        ticker=ticker, side=side, qty=qty, tif=tif, state=state.value,
        filled_qty=filled_qty, filled_avg_price=filled_avg_price,
    )


def _clean_inputs(**over) -> ReconcileInputs:
    base = dict(ledger_positions={}, ledger_cash=5000.0,
                broker_positions={}, broker_cash=5000.0)
    base.update(over)
    return ReconcileInputs(**base)


# --------------------------------------------------------------------- #
# The clean (all-agree) case
# --------------------------------------------------------------------- #
class TestClean:
    def test_all_agree_is_clean(self):
        res = ENGINE.reconcile(_clean_inputs(
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 10},
        ))
        assert res.clean is True
        assert res.halt is False
        assert res.findings == []
        assert sum(res.counts.values()) == 0
        assert set(res.counts) == set(ALL_CLASSES)


# --------------------------------------------------------------------- #
# One fixture per divergence class
# --------------------------------------------------------------------- #
class TestDivergenceClasses:
    def test_missed_fill(self):
        o = _order(state=OrderState.ACKED, filled_qty=0)
        res = ENGINE.reconcile(_clean_inputs(orders=[o], window_closed=True))
        f = _only(res, CLASS_MISSED_FILL)
        assert "NO chase" in f.action and not f.halt and not f.manual

    def test_missed_fill_not_flagged_before_window_closes(self):
        o = _order(state=OrderState.ACKED, filled_qty=0)
        res = ENGINE.reconcile(_clean_inputs(orders=[o], window_closed=False))
        assert res.clean  # still in-window, no finding yet

    def test_partial_fill(self):
        o = _order(qty=100, state=OrderState.CANCELED, filled_qty=40,
                   filled_avg_price=410.0)
        res = ENGINE.reconcile(_clean_inputs(orders=[o]))
        f = _only(res, CLASS_PARTIAL_FILL)
        assert "adopts broker truth" in f.action and not f.halt

    @pytest.mark.parametrize("reason,sub", [
        ("fractional shares not allowed for OPG", "fractional"),
        ("market is closed / after cutoff", "after_cutoff"),
        ("insufficient buying power", "buying_power"),
        ("some other broker reason", "other"),
    ])
    def test_reject_subclassified(self, reason, sub):
        o = _order(state=OrderState.REJECTED)
        res = ENGINE.reconcile(_clean_inputs(
            orders=[o], reject_reasons={o.client_order_id: reason}))
        f = _only(res, CLASS_REJECT)
        assert f"reason={sub}" in f.action and not f.halt

    def test_price_drift_beyond_threshold(self):
        # expected 100.00, fill 100.10 = 10bps > (1 + 5) threshold
        o = _order(state=OrderState.FILLED, filled_qty=10, filled_avg_price=100.10)
        res = ENGINE.reconcile(_clean_inputs(
            orders=[o], expected_prices={o.client_order_id: 100.00},
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 10}))
        f = _only(res, CLASS_PRICE_DRIFT)
        assert "slippage-error series" in f.action and not f.halt

    def test_price_drift_within_threshold_is_clean(self):
        o = _order(state=OrderState.FILLED, filled_qty=10, filled_avg_price=100.02)
        res = ENGINE.reconcile(_clean_inputs(
            orders=[o], expected_prices={o.client_order_id: 100.00},
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 10}))
        assert res.counts[CLASS_PRICE_DRIFT] == 0

    def test_cash_drift_halts(self):
        res = ENGINE.reconcile(_clean_inputs(ledger_cash=5000.0, broker_cash=4990.0))
        f = _only(res, CLASS_CASH_DRIFT)
        assert f.halt is True and "HALT" in f.action

    def test_cash_within_dollar_is_clean(self):
        res = ENGINE.reconcile(_clean_inputs(ledger_cash=5000.00, broker_cash=4999.50))
        assert res.clean

    def test_position_drift_halts(self):
        res = ENGINE.reconcile(_clean_inputs(
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 12},
            known_tickers={"AAPL"}))
        f = _only(res, CLASS_POSITION_DRIFT)
        assert f.halt is True and f.ticker == "AAPL"

    def test_position_drift_explained_by_open_order_is_clean(self):
        # an open order on AAPL legitimately explains a qty gap
        o = _order(ticker="AAPL", state=OrderState.ACKED)
        res = ENGINE.reconcile(_clean_inputs(
            orders=[o], ledger_positions={"AAPL": 10},
            broker_positions={"AAPL": 12}, known_tickers={"AAPL"}))
        assert res.counts[CLASS_POSITION_DRIFT] == 0

    def test_corporate_action_is_manual(self):
        # a symbol we never traded appears at the broker (ticker change)
        res = ENGINE.reconcile(_clean_inputs(
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 10, "GOOG": 5},
            known_tickers={"AAPL"}))
        f = _only(res, CLASS_CORPORATE_ACTION)
        assert f.manual is True and f.ticker == "GOOG"

    def test_halt_flag_aggregates(self):
        # broker 7 vs ledger 10 = a non-ratio mismatch (genuine drift,
        # NOT a clean split ratio — see corporate-action test).
        res = ENGINE.reconcile(_clean_inputs(
            ledger_cash=5000.0, broker_cash=4000.0,
            ledger_positions={"AAPL": 10}, broker_positions={"AAPL": 7},
            known_tickers={"AAPL"}))
        assert res.halt is True
        assert res.counts[CLASS_CASH_DRIFT] == 1
        assert res.counts[CLASS_POSITION_DRIFT] == 1
        assert res.clean is False


def _only(res, klass):
    fs = [f for f in res.findings if f.klass == klass]
    assert len(fs) == 1, f"expected exactly one {klass}, got {res.counts}"
    return fs[0]


# --------------------------------------------------------------------- #
# DRY-RUN scheduler: walks the clock, submits nothing
# --------------------------------------------------------------------- #
class TestDryRunDay:
    def test_dry_run_day_submits_nothing_and_logs_clock(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "orders.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "recon.jsonl"),
                               dry_run=True)

        o1 = om.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        o2 = om.stage("2026-06-15", "SPY", "sell", 3, TimeInForce.CLS, CFG)

        # Clean reconcile inputs every cycle (ledger == broker, no orders done).
        def inputs_fn(step):
            return ReconcileInputs(
                ledger_positions={}, ledger_cash=5000.0,
                broker_positions={}, broker_cash=5000.0)

        summary = sched.run_day("2026-06-15", [o1, o2], inputs_fn)

        # Submitted NOTHING through the broker.
        assert client.submitted == []
        assert summary.submitted_count == 0
        # Clock fully walked.
        assert [s.step for s in summary.steps] == [
            "pull_close_bars", "compute_signals_targets", "preflight",
            "submit_opg", "submit_day", "ack_sweep", "reconcile_1", "submit_cls",
            "eod_reconcile_snapshot",
        ]
        # OPG/CLS batches counted but not sent.
        opg_step = next(s for s in summary.steps if s.step == "submit_opg")
        cls_step = next(s for s in summary.steps if s.step == "submit_cls")
        assert opg_step.would_submit == 1 and cls_step.would_submit == 1
        assert "submitting NOTHING" in opg_step.note
        # 3 reconcile cycles, all clean, no halt.
        assert summary.reconcile_total_cycles == 3
        assert summary.reconcile_clean_cycles == 3
        assert summary.halted is False

    def test_dry_run_day_records_dirty_cycle(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "orders.jsonl"))
        log_path = str(tmp_path / "recon.jsonl")
        sched = PaperScheduler(om, reconcile_log_path=log_path, dry_run=True)
        o = om.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)

        def inputs_fn(step):
            # cash drift only at EOD
            broker_cash = 4000.0 if step == "eod_reconcile_snapshot" else 5000.0
            return ReconcileInputs(ledger_positions={}, ledger_cash=5000.0,
                                   broker_positions={}, broker_cash=broker_cash)

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        assert summary.reconcile_clean_cycles == 2   # preflight + reconcile_1
        assert summary.reconcile_total_cycles == 3
        assert summary.halted is True

        # reconcile_log is append-only and carries per-cycle clean bool.
        from paper_trader._jsonl import JsonlStore
        rows = JsonlStore(log_path).read_all()
        assert len(rows) == 3
        assert [r["clean"] for r in rows] == [True, True, False]
        assert rows[-1]["halt"] is True

    def test_live_mode_unarmed_submit_step_raises(self, tmp_path):
        # T-163: live mode (dry_run=False) WITHOUT armed=True must refuse
        # to submit — the arm gate, not a NotImplementedError stub.
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                               dry_run=False, armed=False)
        o = om.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        with pytest.raises(RuntimeError, match="not armed"):
            sched.run_day("2026-06-15", [o],
                          lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
