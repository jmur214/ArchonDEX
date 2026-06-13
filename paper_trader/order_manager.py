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
    "done_for_day": OrderState.CANCELED,
    "canceled": OrderState.CANCELED,
    "expired": OrderState.EXPIRED,
    "rejected": OrderState.REJECTED,
    "stopped": OrderState.REJECTED,
    "pending_cancel": None,
    "pending_replace": None,
    "replaced": None,
}


def _is_duplicate_coid(exc: Exception) -> bool:
    """A broker reject for a reused client_order_id (Alpaca 422
    'client_order_id must be unique') means the order is ALREADY live —
    a prior POST landed. Detected by message substring (the SDK surfaces
    it as a generic APIError)."""
    msg = str(exc).lower()
    return (
        "client_order_id" in msg
        and ("unique" in msg or "already exists" in msg or "duplicate" in msg)
    )


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
        self._replay_from_journal()
        # T-163 crit-2: a restart must reconcile its replayed belief
        # against broker TRUTH before acting — the journal alone can be
        # stale (a SUBMITTED-intent record whose POST landed, or didn't).
        if reconcile_on_start:
            self.reconcile_with_broker()

    # ------------------------------------------------------------------ #
    def _replay_from_journal(self) -> None:
        """Rebuild in-memory order state from the append-only journal —
        the crash-recovery path. Last event per client_order_id wins.

        Tolerant to OrderRecord schema drift (extra journal keys are
        dropped) so an older journal still replays."""
        import inspect
        fields = set(inspect.signature(OrderRecord).parameters)
        for rec in self.journal.read_all():
            coid = rec.get("client_order_id")
            if not coid:
                continue
            payload = {k: v for k, v in rec.items()
                       if k != "event" and k in fields}
            self.orders[coid] = OrderRecord(**payload)

    def reconcile_with_broker(self) -> None:
        """T-163 crit-2: for every replayed non-terminal order, ask the
        broker for truth and adopt it. A SUBMITTED order the broker has
        NO record of (POST never landed) reverts to STAGED — safe to
        resubmit. A SUBMITTED order the broker DOES know is adopted
        (acked/filled/etc.) — never re-POSTed. This is what makes
        restart idempotent against the broker, not just the journal."""
        for order in list(self.orders.values()):
            st = OrderState(order.state)
            if st.is_terminal or st == OrderState.STAGED:
                continue
            resp = self.client.get_order(order.client_order_id)
            if resp is not None:
                self._apply_broker(order, resp)
            elif st == OrderState.SUBMITTED:
                # The broker never saw it → the POST didn't land. Revert
                # to STAGED so a fresh, deliberate submit can happen
                # (NOT a blind re-POST of an order we think is live).
                self._record(order, event="broker_absent_revert_staged",
                             new_state=OrderState.STAGED)

    def _record(self, order: OrderRecord, event: str,
                new_state: Optional[OrderState] = None) -> None:
        if new_state is not None and new_state.value != order.state:
            order.state = new_state.value
            order.history.append(new_state.value)
        self.orders[order.client_order_id] = order
        self.journal.append(order.to_journal(event))

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
                # Already live at the broker — adopt its truth.
                existing = self.client.get_order(order.client_order_id)
                if existing is not None:
                    self._apply_broker(order, existing)
                    return order
            raise
        order.broker_order_id = resp.get("broker_order_id")
        order.last_broker_status = resp.get("status")
        self._record(order, event="submit_acked")
        # An immediate ack in the submit response is applied right away.
        self._apply_broker(order, resp)
        return order

    def poll(self, order: OrderRecord) -> OrderRecord:
        """Pull the broker's current truth for one order and apply it."""
        if order.state == OrderState.STAGED.value or order.state in (
            s.value for s in OrderState if s.is_terminal
        ):
            return order
        resp = self.client.get_order(order.client_order_id)
        if resp is not None:
            self._apply_broker(order, resp)
        return order

    def cancel(self, order: OrderRecord) -> OrderRecord:
        """Request cancel (e.g. an OPG order still open past its window).
        Terminal orders are left untouched.

        T-163 crit-3: if we never captured a broker_order_id (a
        SUBMITTED order that never acked), look it up by client_order_id
        first; if the broker has no record, the order is not live →
        mark CANCELED locally (nothing to cancel)."""
        if order.state in (s.value for s in OrderState if s.is_terminal):
            return order
        broker_id = order.broker_order_id
        if broker_id is None:
            resp = self.client.get_order(order.client_order_id)
            if resp is not None:
                broker_id = resp.get("broker_order_id")
                if broker_id and not order.broker_order_id:
                    order.broker_order_id = broker_id
        if broker_id is not None:
            self.client.cancel_order(broker_id)
        self._record(order, event="cancel", new_state=OrderState.CANCELED)
        return order

    def expire_unfilled(self, order: OrderRecord) -> OrderRecord:
        """T-163 crit-3: an order that did not fill by the close of its
        auction window. Cancels at the broker if live, then EXPIRED.
        Covers SUBMITTED-but-never-acked (otherwise invisible) as well
        as ACKED-unfilled."""
        st = OrderState(order.state)
        if st.is_terminal or st == OrderState.STAGED:
            return order
        if order.filled_qty > 0:
            # Partial: cancel the remainder, keep the fill (terminal
            # CANCELED with a recorded partial — reconciliation handles
            # the partial-fill class).
            return self.cancel(order)
        broker_id = order.broker_order_id
        if broker_id is None:
            resp = self.client.get_order(order.client_order_id)
            if resp is not None:
                broker_id = resp.get("broker_order_id")
        if broker_id is not None:
            self.client.cancel_order(broker_id)
        self._record(order, event="window_expired", new_state=OrderState.EXPIRED)
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
