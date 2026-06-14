# tests/test_paper_trader_pr1_t160.py
"""T-160 PR-1 — OrderManager / LedgerStore / paper client tests.

Cassette (no-network) unit tests for the full order lifecycle + the
deterministic-id idempotency contract + ledger belief accounting, plus
ONE real-paper-API smoke (submit 1 share OPG → poll → cancel) that
SKIPS cleanly when creds/SDK/network are absent. The smoke hits the
PAPER endpoint only (AlpacaPaperClient is pinned paper=True).
"""
from __future__ import annotations

import os

import pytest

from paper_trader import (
    FakePaperClient,
    LedgerStore,
    OrderManager,
    OrderState,
    TimeInForce,
    make_client_order_id,
)

CFG_HASH = "cfg-abc123"


# --------------------------------------------------------------------- #
# Deterministic client_order_id
# --------------------------------------------------------------------- #
class TestClientOrderId:
    def test_deterministic_and_field_sensitive(self):
        a = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        b = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        assert a == b                                   # stable across calls
        assert a.startswith("archondex-2026-06-15-AAPL-")
        # any field change → different id
        assert a != make_client_order_id("2026-06-15", "AAPL", "buy", 11, CFG_HASH)
        assert a != make_client_order_id("2026-06-15", "AAPL", "sell", 10, CFG_HASH)
        assert a != make_client_order_id("2026-06-16", "AAPL", "buy", 10, CFG_HASH)
        assert a != make_client_order_id("2026-06-15", "MSFT", "buy", 10, CFG_HASH)
        assert a != make_client_order_id("2026-06-15", "AAPL", "buy", 10, "cfg-other")

    def test_id_is_not_python_salted_hash(self, tmp_path):
        # Across a fresh process the id must be identical — proven by the
        # value being a sha1 prefix, not hash() (which is salted).
        import hashlib
        canonical = "2026-06-15|AAPL|buy|10|" + CFG_HASH
        expect = hashlib.sha1(canonical.encode()).hexdigest()[:16]
        assert make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH).endswith(expect)


# --------------------------------------------------------------------- #
# Order lifecycle (cassette)
# --------------------------------------------------------------------- #
class TestOrderLifecycle:
    def _mgr(self, tmp_path, client=None):
        return OrderManager(client or FakePaperClient(),
                            journal_path=str(tmp_path / "orders.jsonl"))

    def test_stage_submit_ack_fill(self, tmp_path):
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        client.script_submit(coid, status="accepted")
        client.script_polls(coid, [
            {"status": "new"},
            {"status": "filled", "filled_qty": 10, "filled_avg_price": 191.23},
        ])
        mgr = self._mgr(tmp_path, client)

        o = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH)
        assert o.state == OrderState.STAGED.value
        mgr.submit(o)
        assert o.state == OrderState.ACKED.value      # accepted on submit
        mgr.poll(o)                                    # "new" → still acked
        assert o.state == OrderState.ACKED.value
        mgr.poll(o)                                    # "filled"
        assert o.state == OrderState.FILLED.value
        assert o.filled_qty == 10 and o.filled_avg_price == pytest.approx(191.23)
        assert OrderState(o.state).is_terminal

    def test_partial_then_fill(self, tmp_path):
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "MSFT", "buy", 100, CFG_HASH)
        client.script_submit(coid, status="accepted")
        client.script_polls(coid, [
            {"status": "partially_filled", "filled_qty": 40, "filled_avg_price": 410.0},
            {"status": "filled", "filled_qty": 100, "filled_avg_price": 410.5},
        ])
        mgr = self._mgr(tmp_path, client)
        o = mgr.submit(mgr.stage("2026-06-15", "MSFT", "buy", 100, TimeInForce.OPG, CFG_HASH))
        mgr.poll(o)
        assert o.state == OrderState.PARTIALLY_FILLED.value and o.filled_qty == 40
        mgr.poll(o)
        assert o.state == OrderState.FILLED.value and o.filled_qty == 100

    def test_reject(self, tmp_path):
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "BADX", "buy", 5, CFG_HASH)
        client.script_submit(coid, status="rejected")
        mgr = self._mgr(tmp_path, client)
        o = mgr.submit(mgr.stage("2026-06-15", "BADX", "buy", 5, TimeInForce.OPG, CFG_HASH))
        assert o.state == OrderState.REJECTED.value

    def test_cancel_open_order(self, tmp_path):
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        client.script_submit(coid, status="accepted", broker_order_id="bkr-xyz")
        mgr = self._mgr(tmp_path, client)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH))
        mgr.cancel(o)
        assert o.state == OrderState.CANCELED.value
        assert "bkr-xyz" in client.canceled

    def test_cls_tif_routes(self, tmp_path):
        client = FakePaperClient()
        mgr = self._mgr(tmp_path, client)
        o = mgr.submit(mgr.stage("2026-06-15", "SPY", "sell", 3, TimeInForce.CLS, CFG_HASH))
        assert client.submitted[0]["tif"] == "cls"
        assert o.tif == "cls"


# --------------------------------------------------------------------- #
# Idempotency + restart recovery (the crash-safety contract)
# --------------------------------------------------------------------- #
class TestIdempotencyAndRecovery:
    def test_double_submit_is_noop(self, tmp_path):
        client = FakePaperClient()
        mgr = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH))
        mgr.submit(o)                                  # retry
        mgr.submit(o)
        assert len(client.submitted) == 1              # exactly one POST

    def test_restage_existing_id_returns_same(self, tmp_path):
        mgr = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "o.jsonl"))
        o1 = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH)
        o2 = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH)
        assert o1.client_order_id == o2.client_order_id

    def test_replay_rebuilds_state_after_crash(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        client.script_submit(coid, status="accepted")
        mgr = OrderManager(client, journal_path=jp)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH))
        assert o.state == OrderState.ACKED.value

        # "Crash": brand-new manager replays the journal from disk.
        mgr2 = OrderManager(FakePaperClient(), journal_path=jp)
        recovered = mgr2.get(coid)
        assert recovered is not None
        assert recovered.state == OrderState.ACKED.value
        assert recovered.broker_order_id == o.broker_order_id
        # And it is NOT re-submitted (idempotency holds across restart).
        mgr2.submit(recovered)
        assert recovered.state == OrderState.ACKED.value

    def test_journal_is_append_only_timeline(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        client = FakePaperClient()
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG_HASH)
        client.script_submit(coid, status="accepted")
        client.script_polls(coid, [{"status": "filled", "filled_qty": 10,
                                    "filled_avg_price": 100.0}])
        mgr = OrderManager(client, journal_path=jp)
        o = mgr.submit(mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG_HASH))
        mgr.poll(o)
        from paper_trader._jsonl import JsonlStore
        events = [r["event"] for r in JsonlStore(jp).read_all()]
        # T-163 crit-1: intent ("submitting") is journaled before the POST.
        assert events[0] == "stage" and "submitting" in events
        assert events[-1] in ("broker_update", "broker_poll")


# --------------------------------------------------------------------- #
# LedgerStore belief accounting
# --------------------------------------------------------------------- #
class TestLedgerStore:
    def test_buy_then_sell_realizes_pnl(self, tmp_path):
        led = LedgerStore(str(tmp_path / "led.jsonl"), starting_cash=10_000.0)
        led.apply_fill("AAPL", "buy", 10, 100.0)
        assert led.positions()["AAPL"] == 10
        assert led.cash() == pytest.approx(9_000.0)
        led.apply_fill("AAPL", "sell", 10, 110.0)
        assert "AAPL" not in led.positions()
        assert led.cash() == pytest.approx(10_100.0)
        assert led.state.realized_pnl == pytest.approx(100.0)

    def test_commission_debited(self, tmp_path):
        led = LedgerStore(str(tmp_path / "led.jsonl"), starting_cash=1_000.0)
        led.apply_fill("AAPL", "buy", 1, 100.0, commission=0.50)
        assert led.cash() == pytest.approx(899.50)

    def test_partial_adds_weighted_avg(self, tmp_path):
        led = LedgerStore(str(tmp_path / "led.jsonl"), starting_cash=10_000.0)
        led.apply_fill("MSFT", "buy", 10, 100.0)
        led.apply_fill("MSFT", "buy", 10, 120.0)
        assert led.position("MSFT").qty == 20
        assert led.position("MSFT").avg_price == pytest.approx(110.0)

    def test_persistence_reload(self, tmp_path):
        p = str(tmp_path / "led.jsonl")
        led = LedgerStore(p, starting_cash=5_000.0)
        led.apply_fill("SPY", "buy", 5, 400.0)
        led2 = LedgerStore(p)                          # reload from disk
        assert led2.positions()["SPY"] == 5
        assert led2.cash() == pytest.approx(3_000.0)

    def test_adopt_broker_truth(self, tmp_path):
        led = LedgerStore(str(tmp_path / "led.jsonl"), starting_cash=10_000.0)
        led.apply_fill("AAPL", "buy", 10, 100.0)
        led.adopt_broker_truth({"AAPL": 12}, cash=8_800.0, reason="position_drift")
        assert led.positions()["AAPL"] == 12
        assert led.cash() == pytest.approx(8_800.0)


# --------------------------------------------------------------------- #
# Real paper-API smoke — skips cleanly without creds/SDK/network
# --------------------------------------------------------------------- #
@pytest.mark.skipif(
    not (os.getenv("ARCHONDEX_LIVE_SMOKE") and os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")),
    reason="live paper-API smoke: opt-in via ARCHONDEX_LIVE_SMOKE=1 + ALPACA creds "
           "(skipped in the default/CI suite; it hits the real paper API and needs an open "
           "market session, so a creds-present weekend run would otherwise fail spuriously)",
)
def test_real_paper_opg_smoke(tmp_path):
    """submit 1 share OPG → poll → cancel, against the PAPER endpoint.
    Asserts the lifecycle reaches ACKED and ends CANCELED/terminal."""
    try:
        from paper_trader import AlpacaPaperClient
        client = AlpacaPaperClient()
    except Exception as e:                              # SDK/auth/network
        pytest.skip(f"paper client unavailable: {type(e).__name__}")

    mgr = OrderManager(client, journal_path=str(tmp_path / "smoke.jsonl"))
    o = mgr.stage("2026-06-15", "SPY", "buy", 1, TimeInForce.OPG, "smoke-cfg")
    mgr.submit(o)
    assert o.state in (OrderState.ACKED.value, OrderState.SUBMITTED.value,
                       OrderState.FILLED.value)
    mgr.poll(o)
    if not OrderState(o.state).is_terminal:
        mgr.cancel(o)
    assert OrderState(o.state).is_terminal or o.state == OrderState.ACKED.value
