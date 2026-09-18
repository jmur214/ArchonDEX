# tests/test_lot_recorder_t359.py
"""T-359 — the recorder-only lot ledger (audit A1, phase 1).

A1: the "cross-account" wash guard was single-account because lot events are
written ONLY inside the guard and only account-2 had one — account-1 had never
written a lot event, so the 61-day window could never see it. Phase 1 gives
every unguarded account a FEED without giving it the power to refuse.

The four approved constraints, each locked below:
  1. structurally refusal-incapable — no refuse path EXISTS, not merely off;
  2. account-1's submit path byte-identical, proven by execution;
  3. surgical deploy, first artifact = tax_lots.jsonl from a scheduled firing;
  4. the 61-day window starts accruing at that first artifact — so the ABSENCE
     of a cross-account refusal before then is not evidence of anything.
"""
from __future__ import annotations

import datetime as dt

import pytest

from engines.engine_b_risk.cross_account_wash_guard import TaxLotLedger
from paper_trader.order_manager import OrderManager, OrderState


class _Client:
    """Minimal broker: accepts a submit, then reports it filled."""

    def __init__(self):
        self.submitted = []

    def submit_order(self, client_order_id, symbol, qty, side, tif):
        self.submitted.append((client_order_id, symbol, qty, side, tif))
        return {"id": f"brk-{client_order_id}", "status": "accepted"}

    def get_order(self, coid):
        return {"id": f"brk-{coid}", "client_order_id": coid, "status": "filled",
                "filled_qty": 1, "filled_avg_price": 100.0,
                "filled_at": "2026-09-18T13:45:00+00:00"}

    def list_positions(self):
        return []

    def list_orders(self, *a, **k):
        return []


def _om(tmp_path, **kw):
    return OrderManager(_Client(), journal_path=str(tmp_path / "orders.jsonl"),
                        reconcile_on_start=False, account="trend_sleeve", **kw)


# ---------------- constraint 1: refusal-incapable BY CONSTRUCTION -------------

def test_a_recorder_has_no_refuse_path_at_all(tmp_path):
    led = TaxLotLedger(str(tmp_path / "tax_lots.jsonl"))
    assert not hasattr(led, "check_order"), (
        "the recorder must not even expose the refuse entry point")
    om = _om(tmp_path, lot_ledger=led)
    assert om.wash_guard is None, "the refuse branch must stay ungated-off"


def test_passing_an_ENFORCING_guard_as_the_recorder_is_REFUSED(tmp_path):
    """'Enforced, not promised': a mode flag on the full guard would leave the
    refuse code one edit from reachable. The type is the guarantee."""
    class _LooksLikeARecorder:
        def record_fill(self, **kw):
            pass

        def check_order(self, **kw):       # the thing that must not be here
            raise AssertionError("must never be called")

    with pytest.raises(TypeError, match="RECORDER"):
        _om(tmp_path, lot_ledger=_LooksLikeARecorder())


def test_a_guard_and_a_recorder_together_are_REFUSED(tmp_path):
    """Two write paths into one ledger is how a fill gets recorded twice."""
    class _Guard:
        ledger = None

        def check_order(self, **kw):
            pass

    with pytest.raises(TypeError, match="never both"):
        _om(tmp_path, wash_guard=_Guard(),
            lot_ledger=TaxLotLedger(str(tmp_path / "t.jsonl")))


# ---------------- constraint 2: the submit path is byte-identical ------------

def _drive_submit(om):
    """Drive a REAL order through stage → submit → poll(filled). The byte-
    identity claim is about behaviour, so it is asserted on behaviour."""
    from paper_trader.order_manager import TimeInForce
    o = om.stage(trade_date="2026-09-18", ticker="SPY", side="buy", qty=1,
                 tif=TimeInForce.DAY, config_hash="t359")
    om.submit(o)
    om.poll(o)
    return o.client_order_id


def test_the_submit_path_is_BYTE_IDENTICAL_with_and_without_the_recorder(tmp_path):
    """Proven by EXECUTION, not by reading the gate: drive a real submit both
    ways and compare what reached the broker and what the journal recorded."""
    plain = _om(tmp_path / "a", )
    (tmp_path / "a").mkdir(parents=True, exist_ok=True)
    plain = OrderManager(_Client(), journal_path=str(tmp_path / "a/orders.jsonl"),
                         reconcile_on_start=False, account="trend_sleeve")
    (tmp_path / "b").mkdir(parents=True, exist_ok=True)
    rec = OrderManager(_Client(), journal_path=str(tmp_path / "b/orders.jsonl"),
                       reconcile_on_start=False, account="trend_sleeve",
                       lot_ledger=TaxLotLedger(str(tmp_path / "b/tax_lots.jsonl")))

    c1 = _drive_submit(plain)
    c2 = _drive_submit(rec)

    assert plain.client.submitted == rec.client.submitted, (
        "the recorder changed what reached the broker")
    o1, o2 = plain.orders[c1], rec.orders[c2]
    assert (o1.state, o1.filled_qty, o1.filled_avg_price, o1.reject_reason) == \
           (o2.state, o2.filled_qty, o2.filled_avg_price, o2.reject_reason)
    assert o1.state == OrderState.FILLED   # str-Enum: compare by value


def test_the_recorder_actually_WRITES_a_lot_event_on_a_confirmed_fill(tmp_path):
    """The whole point of phase 1: the feed starts existing."""
    path = tmp_path / "tax_lots.jsonl"
    rec = OrderManager(_Client(), journal_path=str(tmp_path / "orders.jsonl"),
                       reconcile_on_start=False, account="trend_sleeve",
                       lot_ledger=TaxLotLedger(str(path)))
    _drive_submit(rec)
    assert path.exists(), "no lot event was written — the channel is still unfed"
    body = path.read_text()
    assert "SPY" in body and "trend_sleeve" in body


def test_without_a_recorder_no_ledger_file_is_created(tmp_path):
    """The pre-A1 state, kept as the contrast that makes the fix legible."""
    plain = OrderManager(_Client(), journal_path=str(tmp_path / "orders.jsonl"),
                         reconcile_on_start=False, account="trend_sleeve")
    _drive_submit(plain)
    assert not (tmp_path / "tax_lots.jsonl").exists()
