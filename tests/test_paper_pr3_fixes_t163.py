# tests/test_paper_pr3_fixes_t163.py
"""T-163-fix — the adversarial-review blockers + majors, each with a
test that FAILS before the fix and passes after.

B1 transient-vs-absent (the believe-flat-while-live hazard), B2 the real
Alpaca duplicate-coid APIError shape, M1 per-order/EOD-always error
handling, M2 truthful preflight log, M3 ratio-needs-feed, M4 allocator
hard interlock, M5 armed-halt asserts ZERO broker POSTs.
"""
from __future__ import annotations

import pytest

from paper_trader import (
    FakePaperClient,
    OrderManager,
    OrderState,
    PaperConfig,
    PaperScheduler,
    ReconcileInputs,
    TimeInForce,
    make_client_order_id,
)
from paper_trader.order_manager import OrderRecord, _is_duplicate_coid

CFG = "cfg-fix"


def _coid(t="AAPL", s="buy", q=10):
    return make_client_order_id("2026-06-15", t, s, q, CFG)


def _submitted_record(jp, coid, broker_id=None, state=OrderState.SUBMITTED):
    from paper_trader._jsonl import JsonlStore
    JsonlStore(jp).append({
        "client_order_id": coid, "trade_date": "2026-06-15", "ticker": "AAPL",
        "side": "buy", "qty": 10, "tif": "opg", "state": state.value,
        "broker_order_id": broker_id, "filled_qty": 0, "filled_avg_price": None,
        "last_broker_status": None, "history": ["staged", "submitted"],
        "event": "submitting",
    })


# ===================================================================== #
# B1 — transient UNKNOWN must NOT be treated as absent
# ===================================================================== #
class TestB1TransientVsAbsent:
    def test_unknown_on_restart_does_not_revert_to_staged(self, tmp_path):
        """A live SUBMITTED order whose restart GET fails transiently
        (UNKNOWN) must stay SUBMITTED — reverting to STAGED would
        re-submit a live order (double-submit)."""
        jp = str(tmp_path / "o.jsonl")
        coid = _coid()
        _submitted_record(jp, coid)
        client = FakePaperClient()
        client.script_get_unknown(coid)          # transient GET failure
        mgr = OrderManager(client, journal_path=jp)   # reconciles on start
        assert mgr.get(coid).state == OrderState.SUBMITTED.value   # NOT staged
        # And a resubmit attempt does NOT POST (still non-STAGED).
        mgr.submit(mgr.get(coid))
        assert client.submitted == []

    def test_absent_on_restart_does_revert_to_staged(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        coid = _coid()
        _submitted_record(jp, coid)
        client = FakePaperClient()               # authoritative → ABSENT
        mgr = OrderManager(client, journal_path=jp)
        assert mgr.get(coid).state == OrderState.STAGED.value

    def test_cancel_on_unknown_does_not_mark_flat(self, tmp_path):
        """cancel() on a transient failure must NOT terminalize — we
        could believe-flat while a live OPG can still fill."""
        client = FakePaperClient()
        coid = _coid()
        client.script_get_unknown(coid)
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"),
                           reconcile_on_start=False)
        rec = OrderRecord(client_order_id=coid, trade_date="2026-06-15",
                          ticker="AAPL", side="buy", qty=10, tif="opg",
                          state=OrderState.SUBMITTED.value)   # no broker_id
        mgr.orders[coid] = rec
        mgr.cancel(rec)
        assert rec.state == OrderState.SUBMITTED.value   # NOT canceled

    def test_cancel_with_failed_broker_cancel_stays_open(self, tmp_path):
        client = FakePaperClient()
        coid = _coid()
        client.script_submit(coid, status="accepted", broker_order_id="bkr-1")
        client.script_cancel_fails("bkr-1")      # transient cancel failure
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        mgr.cancel(o)
        assert o.state == OrderState.ACKED.value         # NOT canceled (unconfirmed)

    def test_expire_on_unknown_stays_open(self, tmp_path):
        client = FakePaperClient()
        coid = _coid()
        client.script_submit(coid, status="accepted", broker_order_id="bkr-1")
        client.script_cancel_fails("bkr-1")
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        mgr.expire_unfilled(o)
        assert o.state != OrderState.EXPIRED.value       # not believe-flat


# ===================================================================== #
# B2 — the real Alpaca duplicate-coid APIError
# ===================================================================== #
class TestB2RealApiError:
    def _real_dup_error(self):
        from alpaca.common.exceptions import APIError
        return APIError('{"code":42210000,"message":"client order id must be unique."}')

    def test_detector_matches_real_apierror_body(self):
        exc = self._real_dup_error()
        # The old underscore-substring matcher returned False on this.
        assert _is_duplicate_coid(exc) is True

    def test_detector_rejects_unrelated_error(self):
        from alpaca.common.exceptions import APIError
        assert _is_duplicate_coid(
            APIError('{"code":40010001,"message":"some other error"}')) is False

    def test_submit_adopts_on_real_duplicate(self, tmp_path):
        client = FakePaperClient()
        coid = _coid()
        client.script_submit_raises(coid, self._real_dup_error())
        client.script_polls(coid, [{"status": "accepted", "broker_order_id": "bkr-live"}])
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"),
                           reconcile_on_start=False)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        assert o.state == OrderState.ACKED.value         # adopted, not raised
        assert o.broker_order_id == "bkr-live"

    def test_submit_on_duplicate_then_unknown_stays_submitted(self, tmp_path):
        """Duplicate reject + the follow-up GET is transient (UNKNOWN):
        stay SUBMITTED (never rejected, never re-POST)."""
        client = FakePaperClient()
        coid = _coid()
        client.script_submit_raises(coid, self._real_dup_error())
        client.script_get_unknown(coid)
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"),
                           reconcile_on_start=False)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG))
        assert o.state == OrderState.SUBMITTED.value


# ===================================================================== #
# M4 — allocator hard interlock
# ===================================================================== #
class TestM4AllocatorInterlock:
    def _armed_sched(self, tmp_path, designated, alloc):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        return PaperScheduler(
            om, reconcile_log_path=str(tmp_path / "r.jsonl"),
            dry_run=False, armed=True,
            paper_config=PaperConfig(allocator=alloc),
            designated_allocator=designated), client

    def test_arm_refuses_without_designated_allocator(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        with pytest.raises(ValueError, match="allocator"):
            PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                           dry_run=False, armed=True,
                           paper_config=PaperConfig(allocator="adaptive"))

    def test_arm_refuses_on_allocator_mismatch(self, tmp_path):
        with pytest.raises(ValueError, match="!= director-designated"):
            self._armed_sched(tmp_path, designated="mean_variance", alloc="adaptive")

    def test_arm_succeeds_on_allocator_match(self, tmp_path):
        sched, _ = self._armed_sched(tmp_path, designated="adaptive", alloc="adaptive")
        assert sched.armed is True

    def test_arm_in_dry_run_fails_loud(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        with pytest.raises(ValueError, match="dry-run"):
            PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                           dry_run=True, armed=True)


# ===================================================================== #
# M5 — armed halt asserts ZERO broker POSTs (was vacuous in dry-run)
# ===================================================================== #
class TestM5ArmedHaltZeroPosts:
    def test_armed_halt_blocks_real_submission(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(
            om, reconcile_log_path=str(tmp_path / "r.jsonl"),
            dry_run=False, armed=True,
            paper_config=PaperConfig(allocator="adaptive"),
            designated_allocator="adaptive")
        assert sched.armed is True
        o = om.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)

        def inputs_fn(step):
            bc = 4000.0 if step == "preflight" else 5000.0   # halt at preflight
            return ReconcileInputs(ledger_positions={}, ledger_cash=5000.0,
                                   broker_positions={}, broker_cash=bc)

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        assert summary.halted is True
        # The ARMED path was exercised (not dry-run) and submitted ZERO.
        assert client.submitted == []
        assert summary.submitted_count == 0
        opg = next(s for s in summary.steps if s.step == "submit_opg")
        assert "BLOCKED" in opg.note


# ===================================================================== #
# M1 — per-order + EOD-always error handling on the armed path
# ===================================================================== #
class TestM1ErrorHandling:
    def _armed(self, tmp_path, client):
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        return PaperScheduler(
            om, reconcile_log_path=str(tmp_path / "r.jsonl"),
            dry_run=False, armed=True,
            paper_config=PaperConfig(allocator="adaptive"),
            designated_allocator="adaptive"), om

    def test_one_order_error_does_not_abort_batch(self, tmp_path):
        client = FakePaperClient()
        sched, om = self._armed(tmp_path, client)
        bad = om.stage("2026-06-15", "BADX", "buy", 1, TimeInForce.OPG, CFG)
        good = om.stage("2026-06-15", "AAPL", "buy", 1, TimeInForce.OPG, CFG)
        client.script_submit_raises(bad.client_order_id, RuntimeError("boom 500"))
        client.script_submit(good.client_order_id, status="accepted")
        summary = sched.run_day("2026-06-15", [bad, good],
                                lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
        # the good order was still submitted despite the bad one raising
        # (the batch was NOT aborted). It acks at submit, then the EOD
        # step expires it as unfilled — both are non-STAGED progress.
        assert any(x["client_order_id"] == good.client_order_id
                   for x in client.submitted)
        assert good.state in (OrderState.ACKED.value, OrderState.EXPIRED.value)
        assert good.state != OrderState.STAGED.value

    def test_eod_runs_even_if_a_step_raises(self, tmp_path):
        client = FakePaperClient()
        sched, om = self._armed(tmp_path, client)
        o = om.stage("2026-06-15", "AAPL", "buy", 1, TimeInForce.OPG, CFG)
        client.script_submit(o.client_order_id, status="accepted")
        calls = {"n": 0}

        def inputs_fn(step):
            calls["n"] += 1
            if step == "reconcile_1":
                raise RuntimeError("reconcile build blew up")
            return ReconcileInputs({}, 5000.0, {}, 5000.0)

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        # EOD still ran (its reconcile cycle counted) despite the raise.
        eod = [s for s in summary.steps if s.step == "eod_reconcile_snapshot"]
        assert len(eod) == 1


# ===================================================================== #
# M2 — preflight log matches the actual gate
# ===================================================================== #
class TestM2TruthfulPreflightLog:
    def test_nonhalt_findings_say_PROCEEDS(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                               dry_run=True)
        o = om.stage("2026-06-15", "AAPL", "buy", 1, TimeInForce.OPG, CFG)
        # a non-halt finding at preflight: a reject (no halt)
        rej = OrderRecord(client_order_id="c-rej", trade_date="2026-06-15",
                          ticker="AAPL", side="buy", qty=1, tif="opg",
                          state=OrderState.REJECTED.value)

        def inputs_fn(step):
            orders = [rej] if step == "preflight" else []
            return ReconcileInputs(ledger_positions={}, ledger_cash=5000.0,
                                   broker_positions={}, broker_cash=5000.0,
                                   orders=orders,
                                   reject_reasons={"c-rej": "some reason"})

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        pf = next(s for s in summary.steps if s.step == "preflight")
        assert "PROCEEDS" in pf.note and "BLOCKED" not in pf.note

    def test_halt_says_BLOCKED(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        sched = PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                               dry_run=True)
        o = om.stage("2026-06-15", "AAPL", "buy", 1, TimeInForce.OPG, CFG)

        def inputs_fn(step):
            bc = 4000.0 if step == "preflight" else 5000.0
            return ReconcileInputs({}, 5000.0, {}, bc)

        summary = sched.run_day("2026-06-15", [o], inputs_fn)
        pf = next(s for s in summary.steps if s.step == "preflight")
        assert "BLOCKED" in pf.note
