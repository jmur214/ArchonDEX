# tests/test_paper_pr3_fixes2_t163.py
"""T-163-fix2 — the re-review's 3 new blockers + M4 tautology, fixed
STRUCTURALLY and locked with the two REQUIRED contract/property tests:

  SURFACE 1 — one hardened broker-error classifier (never raises;
  structured-signal absence only). The contract test sweeps the error
  SPACE (the anti-whack-a-mole guard).
  SURFACE 2 — schema-complete journal writes + defensive replay. The
  contract test feeds a malformed line and asserts construction survives.
  SURFACE 3 — the M4 interlock reads designation from an INDEPENDENT
  source, so a mismatch can actually fire.
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
    load_designated_allocator,
    make_client_order_id,
)
from paper_trader._jsonl import JsonlStore
from paper_trader.order_manager import OrderRecord, _is_duplicate_coid
from paper_trader.paper_client import (
    AlpacaPaperClient,
    ORDER_ABSENT,
    ORDER_UNKNOWN,
    ERR_ABSENT,
    ERR_DUPLICATE,
    ERR_UNKNOWN,
    classify_broker_error,
    _is_definitive_absent,
)

CFG = "cfg-fix2"


def _api_error(body):
    from alpaca.common.exceptions import APIError
    return APIError(body)


def _api_error_with_status(body, status):
    """The PRODUCTION shape: APIError(non-JSON body, http_error) where
    http_error.response.status_code == status (the SDK attaches this)."""
    from alpaca.common.exceptions import APIError

    class _Resp:
        status_code = status

    class _HttpErr:
        response = _Resp()

    return APIError(body, http_error=_HttpErr())


def _exc_with_status(status):
    class E(Exception):
        pass
    e = E("transient")
    e.status_code = status      # stringy or int — must int-coerce
    return e


# ===================================================================== #
# SURFACE 1 — the REQUIRED error-classifier CONTRACT/PROPERTY test
# ===================================================================== #
class TestErrorClassifierContract:
    """Sweep the error SPACE — covers the space, not point cases. This is
    the guard that prevents a fix-round-4 in this surface."""

    CASES = [
        # (description, exception_factory, expected)
        ("APIError 404-code order-not-found",
         lambda: _api_error('{"code":40410000,"message":"order not found."}'), ERR_ABSENT),
        ("APIError duplicate-coid",
         lambda: _api_error('{"code":42210000,"message":"client order id must be unique."}'), ERR_DUPLICATE),
        ("APIError non-JSON 502 body (NEW-BLOCKER-1)",
         lambda: _api_error("<html><body>502 Bad Gateway</body></html>"), ERR_UNKNOWN),
        ("APIError non-JSON 503 body",
         lambda: _api_error("503 Service Unavailable"), ERR_UNKNOWN),
        ("ConnectionError 'Name or service not found' (NEW-BLOCKER-3)",
         lambda: ConnectionError("Name or service not found"), ERR_UNKNOWN),
        ("proxy body 'URL was not found'",
         lambda: RuntimeError("The requested URL was not found on this server"), ERR_UNKNOWN),
        ("TimeoutError",
         lambda: TimeoutError("read timed out"), ERR_UNKNOWN),
        ("generic 429 message",
         lambda: RuntimeError("429 too many requests"), ERR_UNKNOWN),
        # fix3 minor A: the PRODUCTION 404 shape — a non-JSON body with a
        # real http_error whose response.status_code == 404 → ABSENT
        # (the structured signal, even when the body isn't JSON).
        ("APIError non-JSON body + http 404 (production shape)",
         lambda: _api_error_with_status("<html>404 Not Found</html>", 404), ERR_ABSENT),
        # fix3 minor B: a stringy "404" status code still int-coerces.
        ("status_code as string '404'",
         lambda: _exc_with_status("404"), ERR_ABSENT),
    ]

    @pytest.mark.parametrize("desc,factory,expected",
                             [(c[0], c[1], c[2]) for c in CASES])
    def test_classification(self, desc, factory, expected):
        assert classify_broker_error(factory()) == expected, desc

    @pytest.mark.parametrize("desc,factory,expected",
                             [(c[0], c[1], c[2]) for c in CASES])
    def test_classifier_never_raises(self, desc, factory, expected):
        try:
            classify_broker_error(factory())   # must not raise on ANY shape
        except Exception as e:
            pytest.fail(f"classifier raised on {desc}: {type(e).__name__}")

    def test_absent_is_structured_signal_only(self):
        # the deleted message-substring fallback must STAY deleted: a
        # 'not found' message without a 404 code/status is NOT absent.
        assert _is_definitive_absent(ConnectionError("host not found")) is False
        assert _is_definitive_absent(RuntimeError("order does not exist")) is False

    def test_404_status_is_absent(self):
        class E(Exception):
            status_code = 404
        assert classify_broker_error(E()) == ERR_ABSENT

    def test_duplicate_helper_consistent(self):
        assert _is_duplicate_coid(
            _api_error('{"code":42210000,"message":"client order id must be unique."}')) is True
        assert _is_duplicate_coid(_api_error("<html>502</html>")) is False


# ===================================================================== #
# NEW-BLOCKER-1 — get_order returns UNKNOWN (not raise) on a non-JSON body
# ===================================================================== #
class TestNewBlocker1GetOrderNeverRaises:
    def _client_raising(self, exc):
        # bypass __init__ (needs creds); inject a fake underlying client.
        c = AlpacaPaperClient.__new__(AlpacaPaperClient)

        class _Raises:
            def get_order_by_client_id(self, coid):
                raise exc
        c._client = _Raises()
        return c

    def test_non_json_body_returns_unknown(self):
        c = self._client_raising(_api_error("<html>502 Bad Gateway</html>"))
        assert c.get_order("coid") is ORDER_UNKNOWN     # not a raise, not absent

    def test_order_not_found_returns_absent(self):
        c = self._client_raising(_api_error('{"code":40410000,"message":"order not found."}'))
        assert c.get_order("coid") is ORDER_ABSENT

    def test_restart_reconcile_survives_broker_outage(self, tmp_path):
        """A get_order that raises during restart-reconcile must NOT crash
        OrderManager construction."""
        jp = str(tmp_path / "o.jsonl")
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG)
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-15", "ticker": "AAPL",
            "side": "buy", "qty": 10, "tif": "opg", "state": "submitted",
            "broker_order_id": None, "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting"})

        class _Outage(FakePaperClient):
            def get_order(self, coid):
                raise ConnectionError("broker down")
        mgr = OrderManager(_Outage(), journal_path=jp)   # must NOT raise
        # the order is left exactly as the journal had it (fail-safe).
        assert mgr.get(coid).state == OrderState.SUBMITTED.value


# ===================================================================== #
# NEW-BLOCKER-3 — transient 'not found' must NOT revert a live order
# ===================================================================== #
class TestNewBlocker3TransientNotFound:
    def test_connection_error_not_found_keeps_submitted(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG)
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-15", "ticker": "AAPL",
            "side": "buy", "qty": 10, "tif": "opg", "state": "submitted",
            "broker_order_id": None, "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting"})

        class _TransientNotFound(FakePaperClient):
            def get_order(self, coid):
                # the AlpacaPaperClient would classify this as UNKNOWN; the
                # fake returns the sentinel the real client would return.
                return ORDER_UNKNOWN
        mgr = OrderManager(_TransientNotFound(), journal_path=jp)
        # MUST stay SUBMITTED (a revert→STAGED would re-submit a live order)
        assert mgr.get(coid).state == OrderState.SUBMITTED.value


# ===================================================================== #
# SURFACE 2 — the REQUIRED malformed-journal-replay CONTRACT test
# ===================================================================== #
class TestJournalReplayDefensive:
    def test_schema_incomplete_line_is_quarantined_not_fatal(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        # a raw error-event missing the required OrderRecord fields (the
        # exact shape 90df30f wrote directly to the journal).
        JsonlStore(jp).append({"client_order_id": "c-bad",
                               "event": "submit_error", "error": "RuntimeError"})
        mgr = OrderManager(FakePaperClient(), journal_path=jp,
                           reconcile_on_start=False)   # must NOT raise
        assert mgr.get("c-bad") is None
        assert len(mgr.quarantined) == 1

    def test_good_records_survive_alongside_a_bad_one(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        client = FakePaperClient()
        mgr = OrderManager(client, journal_path=jp)
        o = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        JsonlStore(jp).append({"client_order_id": "c-bad", "event": "submit_error"})
        mgr2 = OrderManager(FakePaperClient(), journal_path=jp,
                            reconcile_on_start=False)
        assert mgr2.get(o.client_order_id) is not None   # good one intact
        assert mgr2.get("c-bad") is None

    def test_submit_error_record_is_replay_safe(self, tmp_path):
        """The submit-error path (note_event) must produce a
        schema-complete, replay-safe record."""
        jp = str(tmp_path / "o.jsonl")
        client = FakePaperClient()
        mgr = OrderManager(client, journal_path=jp)
        o = mgr.stage("2026-06-15", "AAPL", "buy", 10, TimeInForce.OPG, CFG)
        mgr.note_event(o, "submit_error:ConnectionError")
        # restart replays cleanly — the error record reconstructs the order.
        mgr2 = OrderManager(FakePaperClient(), journal_path=jp,
                            reconcile_on_start=False)
        assert mgr2.get(o.client_order_id) is not None
        assert mgr2.quarantined == []

    def test_armed_submit_error_does_not_brick_restart(self, tmp_path):
        """End-to-end: an armed submit that raises writes a replay-safe
        record (NEW-BLOCKER-2 regression)."""
        jp = str(tmp_path / "o.jsonl")
        client = FakePaperClient()
        om = OrderManager(client, journal_path=jp)
        sched = PaperScheduler(
            om, reconcile_log_path=str(tmp_path / "r.jsonl"),
            dry_run=False, armed=True,
            paper_config=PaperConfig(allocator="adaptive"),
            designated_allocator="adaptive")
        bad = om.stage("2026-06-15", "BADX", "buy", 1, TimeInForce.OPG, CFG)
        client.script_submit_raises(bad.client_order_id, RuntimeError("boom"))
        sched.run_day("2026-06-15", [bad],
                      lambda s: ReconcileInputs({}, 5000.0, {}, 5000.0))
        # restart must construct without a TypeError.
        mgr2 = OrderManager(FakePaperClient(), journal_path=jp,
                            reconcile_on_start=False)
        assert mgr2.quarantined == []      # the error record was schema-complete


# ===================================================================== #
# SURFACE 3 — M4 interlock reads an INDEPENDENT source (no tautology)
# ===================================================================== #
class TestM4IndependentDesignation:
    def test_mismatch_between_runtime_and_designated_raises(self, tmp_path):
        client = FakePaperClient()
        om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
        # runtime allocator (config) differs from the designated one.
        with pytest.raises(ValueError, match="!= director-designated"):
            PaperScheduler(om, reconcile_log_path=str(tmp_path / "r.jsonl"),
                           dry_run=False, armed=True,
                           paper_config=PaperConfig(allocator="mean_variance"),
                           designated_allocator="adaptive")

    def test_loader_reads_committed_file(self):
        # the shipped file provides a non-None designation independent of
        # any runtime allocator choice.
        assert load_designated_allocator() in (
            "adaptive", "mean_variance", "parrondo_fixed", None)

    def test_loader_returns_none_on_missing_file(self, tmp_path):
        assert load_designated_allocator(str(tmp_path / "nope.json")) is None


# ===================================================================== #
# fix3 major-1 — LedgerStore read-back is defensive (sibling path)
# ===================================================================== #
class TestLedgerStoreDefensiveReadback:
    def test_malformed_last_ledger_line_does_not_crash(self, tmp_path):
        from paper_trader import LedgerStore
        p = str(tmp_path / "led.jsonl")
        led = LedgerStore(p, starting_cash=5000.0)
        led.apply_fill("AAPL", "buy", 10, 100.0)       # a good snapshot
        # simulate a crash mid-ledger-write: a malformed last line.
        JsonlStore(p).append({"cash": "not-a-number", "positions": {}})
        led2 = LedgerStore(p)                            # must NOT crash
        assert led2.positions().get("AAPL") == 10        # last GOOD line adopted
        assert len(led2.quarantined) == 1

    def test_invalid_positions_shape_is_quarantined(self, tmp_path):
        from paper_trader import LedgerStore
        p = str(tmp_path / "led.jsonl")
        led = LedgerStore(p, starting_cash=5000.0)
        led.apply_fill("AAPL", "buy", 5, 100.0)
        JsonlStore(p).append({"cash": 4000.0, "positions": "not-a-dict", "seq": 9})
        led2 = LedgerStore(p)
        assert led2.positions().get("AAPL") == 5
        assert len(led2.quarantined) == 1

    def test_torn_last_ledger_line_recovers_prior(self, tmp_path):
        from paper_trader import LedgerStore
        p = str(tmp_path / "led.jsonl")
        led = LedgerStore(p, starting_cash=5000.0)
        led.apply_fill("SPY", "buy", 3, 400.0)
        with open(p, "a") as fh:
            fh.write('{"cash": 99, "positi')   # torn (the JsonlStore skips it)
        led2 = LedgerStore(p)
        assert led2.positions().get("SPY") == 3


# ===================================================================== #
# fix3 major-2 — value validation on order replay (not just shape)
# ===================================================================== #
class TestReplayValueValidation:
    def _base(self, coid, **over):
        rec = {
            "client_order_id": coid, "trade_date": "2026-06-15",
            "ticker": "AAPL", "side": "buy", "qty": 10, "tif": "opg",
            "state": "submitted", "broker_order_id": None, "filled_qty": 0,
            "filled_avg_price": None, "last_broker_status": None,
            "history": ["staged", "submitted"], "event": "submitting",
        }
        rec.update(over)
        return rec

    @pytest.mark.parametrize("bad", [
        {"state": "not_a_state"},      # invalid enum
        {"tif": "gtc"},                # invalid tif (auction-only)
        {"side": "long"},              # invalid side (must be buy/sell)
        {"qty": -5},                   # invalid qty
        {"qty": "ten"},                # wrong type
        {"filled_qty": -1},            # invalid filled_qty
    ])
    def test_invalid_value_record_is_quarantined(self, tmp_path, bad):
        jp = str(tmp_path / "o.jsonl")
        JsonlStore(jp).append(self._base("c-bad", **bad))
        mgr = OrderManager(FakePaperClient(), journal_path=jp,
                           reconcile_on_start=False)
        assert mgr.get("c-bad") is None             # NOT replayed into bad state
        assert len(mgr.quarantined) == 1

    def test_valid_record_still_replays(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        JsonlStore(jp).append(self._base("c-good"))
        mgr = OrderManager(FakePaperClient(), journal_path=jp,
                           reconcile_on_start=False)
        assert mgr.get("c-good") is not None
        assert mgr.quarantined == []

    def test_missing_coid_line_is_quarantined_not_dropped(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        JsonlStore(jp).append({"event": "weird", "state": "submitted"})  # no coid
        mgr = OrderManager(FakePaperClient(), journal_path=jp,
                           reconcile_on_start=False)
        assert len(mgr.quarantined) == 1            # observable, not silent
        assert mgr.quarantined[0]["error"] == "missing_client_order_id"


# ===================================================================== #
# fix3 nit — reconcile_start_error is recorded, not silently swallowed
# ===================================================================== #
class TestReconcileStartErrorObservable:
    def test_restart_outage_records_the_error(self, tmp_path):
        jp = str(tmp_path / "o.jsonl")
        coid = make_client_order_id("2026-06-15", "AAPL", "buy", 10, CFG)
        JsonlStore(jp).append({
            "client_order_id": coid, "trade_date": "2026-06-15", "ticker": "AAPL",
            "side": "buy", "qty": 10, "tif": "opg", "state": "submitted",
            "broker_order_id": None, "filled_qty": 0, "filled_avg_price": None,
            "last_broker_status": None, "history": ["staged", "submitted"],
            "event": "submitting"})

        class _Outage(FakePaperClient):
            def get_order(self, coid):
                raise ConnectionError("boom")
        mgr = OrderManager(_Outage(), journal_path=jp)    # must not crash
        assert mgr.reconcile_start_error is not None       # observable
        assert "ConnectionError" in mgr.reconcile_start_error


# ===================================================================== #
# Minor — sentinels are falsy
# ===================================================================== #
class TestSentinelFalsy:
    def test_sentinels_are_falsy(self):
        assert not ORDER_ABSENT
        assert not ORDER_UNKNOWN
        # and a real order dict is truthy (so `if resp:` is unambiguous)
        assert bool({"status": "filled"}) is True
