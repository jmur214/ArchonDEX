# tests/test_paper_pr3_criteria_t163.py
"""T-163 PR-3 Part A — the 5 review entry criteria, each with a test,
plus the two durability tests the T-160 review flagged as missing:
torn/partial-journal crash-replay and zero-broker-POST-across-restart.
These gate arming the paper submit.
"""
from __future__ import annotations

import pytest

from paper_trader import (
    FakePaperClient,
    OrderManager,
    OrderState,
    PaperScheduler,
    ReconcileInputs,
    ReconciliationEngine,
    TimeInForce,
    make_client_order_id,
)
from paper_trader._jsonl import JsonlStore
from paper_trader.reconciliation import (
    CLASS_CORPORATE_ACTION,
    CLASS_MISSED_FILL,
    CLASS_POSITION_DRIFT,
)

CFG = "cfg-pr3"
ENGINE = ReconciliationEngine()


def _coid(ticker="AAPL", side="buy", qty=10):
    return make_client_order_id("2026-06-15", ticker, side, qty, CFG)


# ===================================================================== #
# Crit-1: journal intent BEFORE the broker POST
# ===================================================================== #
class TestCrit1IntentBeforePost:
    def test_submitting_record_written_before_post(self, tmp_path):
        """A submit journals SUBMITTED-intent before the POST. We prove
        ordering with a client that raises on POST: the journal must
        already hold the SUBMITTED record."""
        jp = str(tmp_path / "o.jsonl")

        class RaisingClient(FakePaperClient):
            def submit_order(self, **kw):
                raise ConnectionError("network died mid-POST")

        mgr = OrderManager(RaisingClient(), journal_path=jp)
        o = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        with pytest.raises(ConnectionError):
            mgr.submit(o)
        events = [r["event"] for r in JsonlStore(jp).read_all()]
        # The intent landed on disk BEFORE the POST that then failed.
        assert "submitting" in events
        states = [r["state"] for r in JsonlStore(jp).read_all()]
        assert OrderState.SUBMITTED.value in states


# ===================================================================== #
# Crit-2: restart reconciles vs broker truth
# ===================================================================== #
class TestCrit2RestartReconcilesVsBroker:
    def test_submitted_intent_with_broker_record_is_adopted(self, tmp_path):
        """Crash after the SUBMITTED intent but the POST DID land: on
        restart, the broker knows the order → adopt (acked), never
        re-POST."""
        jp = str(tmp_path / "o.jsonl")
        coid = _coid()
        # Hand-write a SUBMITTED-intent journal line (the crash state).
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-15",
            "ticker": "AAPL", "side": "buy", "qty": 10, "tif": "opg",
            "state": OrderState.SUBMITTED.value, "broker_order_id": None,
            "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting",
        })
        # Broker DID receive it (it's live/accepted).
        client = FakePaperClient()
        client.script_polls(coid, [{"status": "accepted",
                                    "broker_order_id": "bkr-live-1"}])
        mgr = OrderManager(client, journal_path=jp)   # __init__ reconciles
        o = mgr.get(coid)
        assert o.state == OrderState.ACKED.value
        assert o.broker_order_id == "bkr-live-1"
        # And it is NOT re-submitted.
        mgr.submit(o)
        assert client.submitted == []

    def test_submitted_intent_with_no_broker_record_reverts_to_staged(self, tmp_path):
        """Crash after SUBMITTED intent but the POST never landed: broker
        has NO record → revert to STAGED (safe to resubmit deliberately)."""
        jp = str(tmp_path / "o.jsonl")
        coid = _coid()
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-15",
            "ticker": "AAPL", "side": "buy", "qty": 10, "tif": "opg",
            "state": OrderState.SUBMITTED.value, "broker_order_id": None,
            "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting",
        })
        client = FakePaperClient()              # broker has NO record
        mgr = OrderManager(client, journal_path=jp)
        assert mgr.get(coid).state == OrderState.STAGED.value

    def test_duplicate_coid_reject_is_adopted_not_rejected(self, tmp_path):
        """A duplicate-client_order_id reject means the order is already
        live → adopt broker truth, NOT terminal-REJECTED."""
        coid = _coid()

        class DupClient(FakePaperClient):
            def submit_order(self, **kw):
                raise RuntimeError("client_order_id must be unique")

        client = DupClient()
        client.script_polls(coid, [{"status": "accepted", "broker_order_id": "bkr-dup"}])
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"),
                           reconcile_on_start=False)
        o = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        mgr.submit(o)
        assert o.state == OrderState.ACKED.value     # adopted, not rejected
        assert o.broker_order_id == "bkr-dup"


# ===================================================================== #
# Crit-3: unacked timeout + uncancellable path
# ===================================================================== #
class TestCrit3UnackedTimeout:
    def test_submitted_unfilled_is_a_missed_fill(self):
        """A SUBMITTED-but-never-acked order past the window is now a
        missed_fill (was invisible — only ACKED was checked)."""
        o = OrderManager(FakePaperClient(), journal_path="/dev/null",
                         reconcile_on_start=False)  # unused; build a record
        from paper_trader.order_manager import OrderRecord
        rec = OrderRecord(client_order_id=_coid(), trade_date="2026-06-15",
                          ticker="AAPL", side="buy", qty=10, tif="opg",
                          state=OrderState.SUBMITTED.value)
        res = ENGINE.reconcile(ReconcileInputs(
            ledger_positions={}, ledger_cash=5000.0, broker_positions={},
            broker_cash=5000.0, orders=[rec], window_closed=True))
        assert res.counts[CLASS_MISSED_FILL] == 1

    def test_expire_unfilled_cancels_and_terminates(self, tmp_path):
        client = FakePaperClient()
        coid = _coid()
        client.script_submit(coid, status="accepted", broker_order_id="bkr-1")
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        mgr.expire_unfilled(o)
        assert o.state == OrderState.EXPIRED.value
        assert "bkr-1" in client.canceled

    def test_cancel_by_coid_when_no_broker_id(self, tmp_path):
        """An order with no captured broker_order_id is still cancellable
        via a client_order_id lookup."""
        client = FakePaperClient()
        coid = _coid()
        # submit returns NO broker_order_id, but a later lookup has it.
        client.submit_responses[coid] = {"client_order_id": coid,
                                         "status": "accepted",
                                         "broker_order_id": None}
        client.script_polls(coid, [{"status": "accepted", "broker_order_id": "bkr-late"}])
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"),
                           reconcile_on_start=False)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        o.broker_order_id = None                  # simulate never-captured
        mgr.cancel(o)
        assert "bkr-late" in client.canceled
        assert o.state == OrderState.CANCELED.value


# ===================================================================== #
# Crit-4: the computed halt GATES submit (not cosmetic)
# ===================================================================== #
class TestCrit4HaltGatesSubmit:
    def test_preflight_halt_blocks_submission(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                               dry_run=True)
        o = om.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)

        def inputs_fn(step):
            # cash drift at preflight → halt BEFORE the submit step
            bc = 4000.0 if step == "preflight" else 5000.0
            return ReconcileInputs(ledger_positions={}, ledger_cash=5000.0,
                                   broker_positions={}, broker_cash=bc)

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        opg = next(s for s in summary.steps if s.step == "submit_opg")
        assert "BLOCKED" in opg.note
        assert summary.halted is True
        assert summary.submitted_count == 0


# ===================================================================== #
# Crit-5: corporate-action-on-held-name classification
# ===================================================================== #
class TestCrit5CorporateActionOnHeldName:
    @pytest.mark.parametrize("ledger,broker", [(10, 20), (10, 40), (10, 30),
                                               (20, 10), (100, 25)])
    def test_clean_ratio_on_held_name_is_corporate_action(self, ledger, broker):
        res = ENGINE.reconcile(ReconcileInputs(
            ledger_positions={"AAPL": ledger}, ledger_cash=5000.0,
            broker_positions={"AAPL": broker}, broker_cash=5000.0,
            known_tickers={"AAPL"}))
        assert res.counts[CLASS_CORPORATE_ACTION] == 1
        assert res.counts[CLASS_POSITION_DRIFT] == 0
        f = next(f for f in res.findings if f.klass == CLASS_CORPORATE_ACTION)
        assert f.manual is True and f.halt is False

    def test_non_ratio_on_held_name_is_position_drift(self):
        res = ENGINE.reconcile(ReconcileInputs(
            ledger_positions={"AAPL": 10}, ledger_cash=5000.0,
            broker_positions={"AAPL": 13}, broker_cash=5000.0,
            known_tickers={"AAPL"}))
        assert res.counts[CLASS_POSITION_DRIFT] == 1
        assert res.counts[CLASS_CORPORATE_ACTION] == 0

    def test_sign_flip_is_position_drift_not_split(self):
        # 10 long → 10 short is a |ratio| of 1 but a sign flip — never a split
        res = ENGINE.reconcile(ReconcileInputs(
            ledger_positions={"AAPL": 10}, ledger_cash=5000.0,
            broker_positions={"AAPL": -10}, broker_cash=5000.0,
            known_tickers={"AAPL"}))
        assert res.counts[CLASS_POSITION_DRIFT] == 1

    def test_explicit_corporate_action_feed_overrides(self):
        res = ENGINE.reconcile(ReconcileInputs(
            ledger_positions={"AAPL": 10}, ledger_cash=5000.0,
            broker_positions={"AAPL": 13}, broker_cash=5000.0,
            known_tickers={"AAPL"}, corporate_action_tickers={"AAPL"}))
        assert res.counts[CLASS_CORPORATE_ACTION] == 1
        assert res.counts[CLASS_POSITION_DRIFT] == 0


# ===================================================================== #
# The two durability tests the T-160 review flagged as missing
# ===================================================================== #
class TestDurability:
    def test_torn_journal_final_line_is_ignored_on_replay(self, tmp_path):
        """A crash mid-append leaves a torn final JSON line. Replay must
        skip it and recover everything before it intact."""
        jp = tmp_path / "o.jsonl"
        client = FakePaperClient()
        coid = _coid()
        client.script_submit(coid, status="accepted")
        mgr = OrderManager(client, journal_path=str(jp))
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        good_state = o.state
        # Simulate a torn final line (partial write from a crash).
        with open(jp, "a") as fh:
            fh.write('{"client_order_id": "torn", "state": "submi')  # no newline, truncated
        # Fresh manager replays — torn line skipped, good order intact.
        mgr2 = OrderManager(FakePaperClient(), journal_path=str(jp),
                            reconcile_on_start=False)
        assert mgr2.get(coid) is not None
        assert mgr2.get(coid).state == good_state
        assert mgr2.get("torn") is None

    def test_zero_broker_post_across_restart(self, tmp_path):
        """THE durability primitive: an order submitted, then the process
        restarts — the new process must NOT re-POST it. Count POSTs
        across the restart: exactly one, ever."""
        jp = str(tmp_path / "o.jsonl")
        coid = _coid()

        client1 = FakePaperClient()
        client1.script_submit(coid, status="accepted", broker_order_id="bkr-1")
        mgr1 = OrderManager(client1, journal_path=jp)
        o = mgr1.submit(mgr1.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        assert len(client1.submitted) == 1
        assert o.state == OrderState.ACKED.value

        # Restart: a NEW client + manager replay the same journal. The
        # broker still knows the order (acked). It must NOT be re-POSTed.
        client2 = FakePaperClient()
        client2.script_polls(coid, [{"status": "accepted", "broker_order_id": "bkr-1"}])
        mgr2 = OrderManager(client2, journal_path=jp)   # reconciles on start
        recovered = mgr2.get(coid)
        mgr2.submit(recovered)                          # retry submit
        # ZERO new POSTs on the restarted process.
        assert client2.submitted == []
        # Total POSTs across both processes = exactly 1.
        assert len(client1.submitted) + len(client2.submitted) == 1
