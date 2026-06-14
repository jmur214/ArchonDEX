# paper_trader/order_manager.py
"""OrderManager — the order-state machine the codebase did not have.

T-159's named biggest gap: every prior path (live_trader stub,
mode_controller's AlpacaExecutionAdapter, the paper controllers)
assumes submit == filled-at-intended-price. This is the real lifecycle:

    STAGED → SUBMITTED → ACKED → (FILLED | PARTIAL | REJECTED | EXPIRED
                                  | CANCELED)

Every transition is journaled append-only BEFORE the next action, so a
crash mid-order is recoverable (``replay`` rebuilds in-memory state from
the journal and the broker's truth).

Idempotency (the restart-safety contract): the ``client_order_id`` is a
deterministic hash of (trade_date, ticker, side, qty, config_hash).
Submitting an order whose id is already SUBMITTED-or-later is a NO-OP
that returns the existing record — so a crash-and-retry never
double-submits, and (per the T-146 live one-pager) we NEVER blind-
resubmit after the 9:28 OPG cutoff.

This module is execution-only: it takes already-CONSTRUCTED orders
(ticker/side/qty/tif) and drives them to a terminal state. Order
CONSTRUCTION (Engine A→C→B) is PR-3, propose-first.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from paper_trader._jsonl import JsonlStore
from paper_trader.paper_client import (
    ORDER_ABSENT,
    ORDER_UNKNOWN,
    classify_broker_error,
    ERR_DUPLICATE,
)


def _is_order_dict(resp) -> bool:
    """A get_order result that is an actual order (not a sentinel)."""
    return isinstance(resp, dict)


def _is_duplicate_coid(exc: Exception) -> bool:
    """T-163-fix2 SURFACE 1: delegate to the SINGLE hardened broker-error
    classifier (never raises; structured-signal absence; body-safe
    message). One classifier, applied everywhere."""
    return classify_broker_error(exc) == ERR_DUPLICATE


class OrderState(str, Enum):
    STAGED = "staged"          # constructed, not yet submitted
    SUBMITTED = "submitted"    # POST sent, awaiting ack
    ACKED = "acked"            # broker accepted (queued for the auction)
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELED = "canceled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            OrderState.FILLED, OrderState.REJECTED,
            OrderState.EXPIRED, OrderState.CANCELED,
        )


class TimeInForce(str, Enum):
    # Auction-only by design (T-146): OPG = opening auction, CLS = close.
    OPG = "opg"
    CLS = "cls"


# Broker (Alpaca) status → our normalized state. Transient broker
# statuses (pending_*) map to None = "no transition, keep prior".
_BROKER_STATE_MAP: Dict[str, Optional[OrderState]] = {
    "new": OrderState.ACKED,
    "accepted": OrderState.ACKED,
    "pending_new": OrderState.ACKED,
    "accepted_for_bidding": OrderState.ACKED,
    "held": OrderState.ACKED,
    "calculated": OrderState.ACKED,
    "suspended": OrderState.ACKED,
    "partially_filled": OrderState.PARTIALLY_FILLED,
    "filled": OrderState.FILLED,
    # done_for_day → CANCELED is SAFE for an OPG/CLS auction order: it is
    # terminal (the session ended unfilled), and any filled_qty is adopted
    # SEPARATELY from `resp` before this map is applied — so no fill is
    # ever lost by terminalizing here (T-163-fix2 minor confirmed).
    "done_for_day": OrderState.CANCELED,
    "canceled": OrderState.CANCELED,
    "expired": OrderState.EXPIRED,
    "rejected": OrderState.REJECTED,
    "stopped": OrderState.REJECTED,
    "pending_cancel": None,
    "pending_replace": None,
    "replaced": None,
}


def make_client_order_id(
    trade_date: str, ticker: str, side: str, qty: int, config_hash: str
) -> str:
    """Deterministic, restart-stable order id (NOT Python's salted
    ``hash()``). Same (date,ticker,side,qty,config) → same id, so a
    retry collides with the already-submitted order at the broker."""
    canonical = f"{trade_date}|{ticker.upper()}|{side.lower()}|{int(qty)}|{config_hash}"
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    # Alpaca client_order_id: ≤128 chars, our prefix keeps it greppable.
    return f"archondex-{trade_date}-{ticker.upper()}-{digest}"


@dataclass
class OrderRecord:
    client_order_id: str
    trade_date: str
    ticker: str
    side: str                  # "buy" | "sell"
    qty: int
    tif: str                   # TimeInForce value
    state: str = OrderState.STAGED.value
    broker_order_id: Optional[str] = None
    filled_qty: int = 0
    filled_avg_price: Optional[float] = None
    last_broker_status: Optional[str] = None
    history: List[str] = field(default_factory=list)

    def to_journal(self, event: str) -> Dict[str, Any]:
        rec = asdict(self)
        rec["event"] = event
        return rec


_VALID_SIDES = ("buy", "sell")


def _validate_order_values(order: "OrderRecord") -> None:
    """T-163-fix3 major-2: validate replayed field VALUES (not just
    shape). A schema-complete but wrong-typed / invalid-enum record must
    be REJECTED on replay (quarantined), not loaded into bad state.
    Raises ValueError on any invalid value."""
    if order.state not in (s.value for s in OrderState):
        raise ValueError(f"invalid state {order.state!r}")
    if order.tif not in (t.value for t in TimeInForce):
        raise ValueError(f"invalid tif {order.tif!r}")
    if order.side not in _VALID_SIDES:
        raise ValueError(f"invalid side {order.side!r}")
    if not isinstance(order.qty, int) or order.qty <= 0:
        raise ValueError(f"invalid qty {order.qty!r}")
    if not isinstance(order.filled_qty, int) or order.filled_qty < 0:
        raise ValueError(f"invalid filled_qty {order.filled_qty!r}")
    if order.filled_avg_price is not None:
        fap = float(order.filled_avg_price)
        if fap < 0 or not _finite(fap):
            raise ValueError(f"invalid filled_avg_price {order.filled_avg_price!r}")
    if not isinstance(order.history, list):
        raise ValueError("history is not a list")


def _finite(x: float) -> bool:
    import math
    return math.isfinite(x)


class OrderManager:
    """Drives staged orders to a terminal state against a PaperClient.

    The journal is the source of truth for what we BELIEVE; the broker
    is the source of truth for what HAPPENED. Reconciliation (PR-2)
    diffs the two — OrderManager's job is only to keep our belief
    journaled and to apply broker status updates honestly.
    """

    def __init__(self, client, journal_path: str,
                 reconcile_on_start: bool = True):
        self.client = client
        self.journal = JsonlStore(journal_path)
        self.orders: Dict[str, OrderRecord] = {}
        self.quarantined: List[Dict[str, Any]] = []   # malformed journal lines
        self._replay_from_journal()
        # T-163 crit-2: a restart must reconcile its replayed belief
        # against broker TRUTH before acting. T-163-fix2 SURFACE 1: a
        # broker OUTAGE on restart must NOT crash construction — degrade
        # gracefully (every order then stays exactly as the journal left
        # it, which is the fail-safe state).
        self.reconcile_start_error: Optional[str] = None
        if reconcile_on_start:
            try:
                self.reconcile_with_broker()
            except Exception as exc:
                # fix3 nit: a restart broker outage must not crash
                # construction, but RECORD the swallowed error so a
                # non-outage logic bug is observable (not silently
                # masked). Belief is left exactly as the journal had it.
                self.reconcile_start_error = f"{type(exc).__name__}: {exc}"

    # ------------------------------------------------------------------ #
    def _replay_from_journal(self) -> None:
        """Rebuild in-memory order state from the append-only journal —
        the crash-recovery path. Last event per client_order_id wins.

        T-163-fix2 SURFACE 2 + fix3: DEFENSIVE — a malformed/schema-
        incomplete line (raw error-event, torn record) OR a
        schema-complete-but-INVALID-VALUE line (bad enum/type) is
        QUARANTINED (logged + skipped), never crashing construction or
        replaying into bad state. A line missing client_order_id is also
        quarantined (was silently dropped — no observability)."""
        import inspect
        fields = set(inspect.signature(OrderRecord).parameters)
        for rec in self.journal.read_all():
            coid = rec.get("client_order_id")
            if not coid:
                # fix3 minor: quarantine (don't silently drop) so a
                # missing-coid line is observable.
                self.quarantined.append({"line": rec, "error": "missing_client_order_id"})
                continue
            payload = {k: v for k, v in rec.items()
                       if k != "event" and k in fields}
            try:
                order = OrderRecord(**payload)
                _validate_order_values(order)   # fix3 major-2: value check
                self.orders[coid] = order
            except Exception as exc:
                # Quarantine, do NOT brick the restart. A prior good
                # record for this coid (if any) stays in self.orders.
                self.quarantined.append({"line": rec, "error": type(exc).__name__})

    def reconcile_with_broker(self) -> None:
        """T-163 crit-2 (+fix B1): for every replayed non-terminal order,
        ask the broker for truth and adopt it. A SUBMITTED order the
        broker PROVABLY does not have (definitive 404 → ORDER_ABSENT)
        reverts to STAGED — safe to resubmit. A SUBMITTED order the
        broker DOES know is adopted (never re-POSTed). On ORDER_UNKNOWN
        (a transient GET failure) we leave the order EXACTLY as-is — we
        do NOT revert (that would risk a double-submit of a live order).
        Fail-safe is the rule."""
        for order in list(self.orders.values()):
            st = OrderState(order.state)
            if st.is_terminal or st == OrderState.STAGED:
                continue
            resp = self.client.get_order(order.client_order_id)
            if _is_order_dict(resp):
                self._apply_broker(order, resp)
            elif resp is ORDER_ABSENT and st == OrderState.SUBMITTED:
                # PROVABLY not at the broker → the POST didn't land.
                self._record(order, event="broker_absent_revert_staged",
                             new_state=OrderState.STAGED)
            elif resp is ORDER_UNKNOWN:
                # Indeterminate — DO NOT act. Leave belief untouched.
                self._record(order, event="broker_unknown_left_as_is")

    def _record(self, order: OrderRecord, event: str,
                new_state: Optional[OrderState] = None) -> None:
        if new_state is not None and new_state.value != order.state:
            order.state = new_state.value
            order.history.append(new_state.value)
        self.orders[order.client_order_id] = order
        self.journal.append(order.to_journal(event))

    def note_event(self, order: OrderRecord, event: str) -> None:
        """Journal an annotation (no state change) through the SAME
        schema-complete path every write uses. T-163-fix2 SURFACE 2: the
        scheduler's submit-error path MUST use this — a raw partial dict
        appended directly to the journal bricks the next restart's
        replay (OrderRecord(**payload) with missing required fields)."""
        self._record(order, event=event)

    # ------------------------------ lifecycle -------------------------- #
    def stage(self, trade_date: str, ticker: str, side: str, qty: int,
              tif: TimeInForce, config_hash: str) -> OrderRecord:
        """Construct + journal a STAGED order. Idempotent on
        client_order_id (re-staging an existing id returns it)."""
        coid = make_client_order_id(trade_date, ticker, side, qty, config_hash)
        if coid in self.orders:
            return self.orders[coid]
        order = OrderRecord(
            client_order_id=coid, trade_date=trade_date, ticker=ticker.upper(),
            side=side.lower(), qty=int(qty), tif=TimeInForce(tif).value,
            state=OrderState.STAGED.value, history=[OrderState.STAGED.value],
        )
        self._record(order, event="stage")
        return order

    def submit(self, order: OrderRecord) -> OrderRecord:
        """Submit a STAGED order. Idempotent: if already SUBMITTED-or-
        later, returns it untouched (the restart double-submit guard).

        T-163 crit-1: the SUBMITTED intent record is journaled BEFORE
        the broker POST, so a crash in the POST window leaves a
        SUBMITTED record (not STAGED) — and ``reconcile_with_broker``
        then routes it through a broker GET, never a blind re-POST.

        T-163 crit-2: a duplicate-client_order_id reject means the order
        is ALREADY LIVE at the broker (a prior POST landed) — we adopt
        broker truth, NOT mark it terminal-REJECTED."""
        if order.state != OrderState.STAGED.value:
            return order
        # 1. Journal intent FIRST (durable before the side-effecting POST).
        self._record(order, event="submitting", new_state=OrderState.SUBMITTED)
        # 2. POST.
        try:
            resp = self.client.submit_order(
                client_order_id=order.client_order_id,
                symbol=order.ticker, qty=order.qty,
                side=order.side, tif=order.tif,
            )
        except Exception as exc:
            if _is_duplicate_coid(exc):
                # Already live at the broker (B2). Adopt its truth IF we
                # can read it; on UNKNOWN, leave SUBMITTED (do NOT mark
                # rejected and do NOT re-POST — the intent record stands).
                existing = self.client.get_order(order.client_order_id)
                if _is_order_dict(existing):
                    self._apply_broker(order, existing)
                else:
                    self._record(order, event="duplicate_coid_unresolved_left_submitted")
                return order
            raise
        order.broker_order_id = resp.get("broker_order_id")
        order.last_broker_status = resp.get("status")
        self._record(order, event="submit_acked")
        # An immediate ack in the submit response is applied right away.
        self._apply_broker(order, resp)
        return order

    def poll(self, order: OrderRecord) -> OrderRecord:
        """Pull the broker's current truth and apply it. On ORDER_ABSENT
        or ORDER_UNKNOWN, leave belief as-is (fail-safe — never infer a
        terminal state from a poll)."""
        if order.state == OrderState.STAGED.value or order.state in (
            s.value for s in OrderState if s.is_terminal
        ):
            return order
        resp = self.client.get_order(order.client_order_id)
        if _is_order_dict(resp):
            self._apply_broker(order, resp)
        return order

    def _resolve_broker_id(self, order: OrderRecord):
        """Return (broker_id, lookup_result). lookup_result is None when
        no lookup was needed, else the tri-state get_order result."""
        if order.broker_order_id is not None:
            return order.broker_order_id, None
        resp = self.client.get_order(order.client_order_id)
        if _is_order_dict(resp):
            bid = resp.get("broker_order_id")
            if bid and not order.broker_order_id:
                order.broker_order_id = bid
            return bid, resp
        return None, resp

    def cancel(self, order: OrderRecord) -> OrderRecord:
        """Cancel an open order. T-163-fix B1: terminalize to CANCELED
        ONLY when we have a CONFIRMED broker cancel OR the order is
        PROVABLY absent (ORDER_ABSENT). On a transient/unknown failure we
        DO NOT mark it flat (a live OPG could still fill) — we leave it
        open and log, to keep watching it."""
        if order.state in (s.value for s in OrderState if s.is_terminal):
            return order
        broker_id, lookup = self._resolve_broker_id(order)
        if broker_id is not None:
            if self.client.cancel_order(broker_id):
                self._record(order, event="cancel", new_state=OrderState.CANCELED)
            else:
                self._record(order, event="cancel_failed_left_open")
            return order
        # No broker id: terminalize only if provably absent.
        if lookup is ORDER_ABSENT:
            self._record(order, event="cancel_absent", new_state=OrderState.CANCELED)
        else:   # ORDER_UNKNOWN — cannot confirm; never believe-flat.
            self._record(order, event="cancel_unknown_left_open")
        return order

    def expire_unfilled(self, order: OrderRecord) -> OrderRecord:
        """T-163 crit-3: an order that did not fill by the close of its
        auction window → EXPIRED. Fail-safe (B1): EXPIRE only on a
        confirmed broker cancel or provable absence; on unknown, leave
        open (never believe-flat while it could still be live)."""
        st = OrderState(order.state)
        if st.is_terminal or st == OrderState.STAGED:
            return order
        if order.filled_qty > 0:
            # Partial: cancel the remainder, keep the fill.
            return self.cancel(order)
        broker_id, lookup = self._resolve_broker_id(order)
        if broker_id is not None:
            if self.client.cancel_order(broker_id):
                self._record(order, event="window_expired", new_state=OrderState.EXPIRED)
            else:
                self._record(order, event="expire_cancel_failed_left_open")
            return order
        if lookup is ORDER_ABSENT:
            self._record(order, event="window_expired_absent", new_state=OrderState.EXPIRED)
        else:   # ORDER_UNKNOWN
            self._record(order, event="expire_unknown_left_open")
        return order

    # ------------------------------------------------------------------ #
    def _apply_broker(self, order: OrderRecord, resp: Dict[str, Any]) -> None:
        """Map a broker order dict onto our record, journaling any state
        transition. Fill quantities/prices always adopt broker truth."""
        status = str(resp.get("status", "")).lower()
        order.last_broker_status = status or order.last_broker_status
        if resp.get("broker_order_id") and not order.broker_order_id:
            order.broker_order_id = resp["broker_order_id"]
        fq = resp.get("filled_qty")
        if fq is not None:
            order.filled_qty = int(float(fq))
        fap = resp.get("filled_avg_price")
        if fap is not None:
            order.filled_avg_price = float(fap)
        new_state = _BROKER_STATE_MAP.get(status, None)
        if new_state is not None and new_state.value != order.state:
            self._record(order, event="broker_update", new_state=new_state)
        else:
            # No state change, but fills/status may have advanced — record
            # the observation so the journal stays a faithful timeline.
            self._record(order, event="broker_poll")

    # ------------------------------ helpers ---------------------------- #
    def open_orders(self) -> List[OrderRecord]:
        return [o for o in self.orders.values()
                if not OrderState(o.state).is_terminal
                and o.state != OrderState.STAGED.value]

    def get(self, client_order_id: str) -> Optional[OrderRecord]:
        return self.orders.get(client_order_id)
