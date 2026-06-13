# paper_trader/paper_client.py
"""Paper broker client — PAPER endpoint ONLY, by construction.

``PaperClient`` is the minimal interface OrderManager/ReconciliationEngine
depend on. ``AlpacaPaperClient`` wraps alpaca-py's TradingClient pinned
to ``paper=True`` (it raises if anyone asks for live). ``FakePaperClient``
is the scripted cassette double for deterministic unit tests — no
network.

Credential names (``ALPACA_API_KEY`` / ``ALPACA_SECRET_KEY``) are read
from the environment by NAME; values never appear in code, logs, or any
returned dict. NB (T-160 finding): the existing ``brokers/alpaca_broker.py``
reads ``ALPACA_API_SECRET``, which is NOT the name in ``.env``
(``ALPACA_SECRET_KEY``) — that stub would fail to authenticate. This
client uses the correct name.
"""
from __future__ import annotations

import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Protocol, Union


# T-163-fix B1: a get_order result is tri-state. A transient failure
# (network/500/timeout/429/auth) is NOT the same as a definitive 404 —
# conflating them to None lets a live order be re-staged or mark-flat.
class _Sentinel:
    __slots__ = ("_name",)

    def __init__(self, name: str):
        self._name = name

    def __repr__(self) -> str:
        return f"<{self._name}>"


ORDER_ABSENT = _Sentinel("ORDER_ABSENT")     # broker PROVABLY has no such order (404)
ORDER_UNKNOWN = _Sentinel("ORDER_UNKNOWN")   # could not determine — fail-safe, never act
GetOrderResult = Union[Dict[str, Any], _Sentinel]

# Alpaca error codes we special-case.
_DUP_COID_CODE = 42210000        # "client order id must be unique."
_ORDER_NOT_FOUND_CODE = 40410000  # order not found


def _api_error_code(exc: Exception) -> Optional[int]:
    """Safely read APIError.code (it json-parses the body and can raise)."""
    try:
        c = getattr(exc, "code", None)
        return int(c) if c is not None else None
    except Exception:
        return None


def _is_definitive_absent(exc: Exception) -> bool:
    """True iff the exception PROVES the order is not at the broker (404 /
    order-not-found) — as opposed to a transient/indeterminate failure."""
    if _api_error_code(exc) == _ORDER_NOT_FOUND_CODE:
        return True
    if getattr(exc, "status_code", None) == 404:
        return True
    msg = str(getattr(exc, "message", "") or exc).lower()
    return "not found" in msg or "does not exist" in msg


class PaperClient(Protocol):
    def submit_order(self, client_order_id: str, symbol: str, qty: int,
                     side: str, tif: str) -> Dict[str, Any]: ...
    def get_order(self, client_order_id: str) -> GetOrderResult: ...
    def cancel_order(self, broker_order_id: str) -> bool: ...
    def list_positions(self) -> List[Dict[str, Any]]: ...
    def get_account(self) -> Dict[str, Any]: ...
    def list_orders(self, after: Optional[str] = None) -> List[Dict[str, Any]]: ...


def _normalize_order(o: Any) -> Dict[str, Any]:
    """alpaca-py order object → the normalized dict OrderManager expects.
    Defensive getattr (SDK field shapes drift across versions)."""
    def g(name, default=None):
        v = getattr(o, name, default)
        return getattr(v, "value", v)  # unwrap enums (status, side, tif)

    return {
        "broker_order_id": str(g("id")) if g("id") is not None else None,
        "client_order_id": g("client_order_id"),
        "status": str(g("status", "")).lower(),
        "symbol": g("symbol"),
        "qty": int(float(g("qty", 0) or 0)),
        "filled_qty": int(float(g("filled_qty", 0) or 0)),
        "filled_avg_price": (float(g("filled_avg_price"))
                             if g("filled_avg_price") not in (None, "") else None),
        "side": str(g("side", "")).lower(),
        "tif": str(g("time_in_force", "")).lower(),
    }


class AlpacaPaperClient:
    """Thin wrapper over alpaca-py TradingClient, PINNED to paper."""

    def __init__(self, env_path: Optional[str] = None,
                 url_override: Optional[str] = None):
        # Best-effort .env load (repo root); real creds may already be in
        # the environment. Never logged.
        try:
            from dotenv import load_dotenv
            root = Path(__file__).resolve().parents[1]
            load_dotenv(env_path or (root / ".env"))
        except Exception:
            pass

        # T-163-fix minor: refuse any non-paper base URL. The only
        # endpoint this client may ever reach is the paper one.
        if url_override and "paper-api" not in str(url_override):
            raise ValueError(
                "AlpacaPaperClient refuses a non-paper url_override "
                f"({url_override!r}) — paper endpoint only."
            )

        key = os.getenv("ALPACA_API_KEY")
        secret = os.getenv("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError(
                "Missing ALPACA_API_KEY / ALPACA_SECRET_KEY in environment "
                "(.env). Paper client cannot authenticate."
            )
        from alpaca.trading.client import TradingClient
        # paper=True is the whole point — this client cannot reach live.
        self._client = TradingClient(api_key=key, secret_key=secret, paper=True)
        self._OrderSide = None  # lazy-imported enums (set on first use)

    # ------------------------------------------------------------------ #
    def _enums(self):
        from alpaca.trading.enums import OrderSide, TimeInForce as ATif
        return OrderSide, ATif

    def submit_order(self, client_order_id: str, symbol: str, qty: int,
                     side: str, tif: str) -> Dict[str, Any]:
        from alpaca.trading.requests import MarketOrderRequest
        OrderSide, ATif = self._enums()
        req = MarketOrderRequest(
            symbol=symbol,
            qty=int(qty),
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            time_in_force=ATif(tif.lower()),     # "opg" / "cls"
            client_order_id=client_order_id,
        )
        return _normalize_order(self._client.submit_order(req))

    def get_order(self, client_order_id: str) -> GetOrderResult:
        """Tri-state (B1): a found order dict, ORDER_ABSENT (the broker
        PROVABLY has no such order — a 404), or ORDER_UNKNOWN (any other
        failure — transient/network/auth). Consumers must NOT treat
        UNKNOWN as absent (never re-stage/mark-flat on it)."""
        try:
            o = self._client.get_order_by_client_id(client_order_id)
        except Exception as exc:
            return ORDER_ABSENT if _is_definitive_absent(exc) else ORDER_UNKNOWN
        if o is None:
            return ORDER_ABSENT
        return _normalize_order(o)

    def cancel_order(self, broker_order_id: str) -> bool:
        """True iff the cancel is CONFIRMED (broker accepted it) OR the
        order is provably already gone (404). False on any transient/
        indeterminate failure — the caller must then NOT mark the order
        flat (fail-safe; a live order could still fill)."""
        try:
            self._client.cancel_order_by_id(broker_order_id)
            return True
        except Exception as exc:
            return _is_definitive_absent(exc)   # already-gone == effectively canceled

    def list_positions(self) -> List[Dict[str, Any]]:
        out = []
        for p in self._client.get_all_positions():
            out.append({
                "symbol": getattr(p, "symbol", None),
                "qty": int(float(getattr(p, "qty", 0) or 0)),
                "avg_entry_price": float(getattr(p, "avg_entry_price", 0) or 0),
            })
        return out

    def get_account(self) -> Dict[str, Any]:
        a = self._client.get_account()
        return {
            "cash": float(getattr(a, "cash", 0) or 0),
            "equity": float(getattr(a, "equity", 0) or 0),
            "status": str(getattr(a, "status", "")),
        }

    def list_orders(self, after: Optional[str] = None) -> List[Dict[str, Any]]:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        req = GetOrdersRequest(status=QueryOrderStatus.ALL, after=after)
        return [_normalize_order(o) for o in self._client.get_orders(req)]


class FakePaperClient:
    """Deterministic cassette double — no network.

    A "cassette" scripts the broker's responses per client_order_id:
    ``submit_responses[coid]`` is the dict returned by submit_order, and
    ``poll_responses[coid]`` is a FIFO queue of dicts returned by
    successive get_order calls (the last one repeats once drained).
    Positions/account are settable for reconciliation fixtures.
    """

    def __init__(self):
        self.submit_responses: Dict[str, Dict[str, Any]] = {}
        self.poll_responses: Dict[str, Deque[Dict[str, Any]]] = defaultdict(deque)
        self._positions: List[Dict[str, Any]] = []
        self._account: Dict[str, Any] = {"cash": 0.0, "equity": 0.0, "status": "ACTIVE"}
        self.submitted: List[Dict[str, Any]] = []
        self.canceled: List[str] = []
        self._last_poll: Dict[str, Dict[str, Any]] = {}
        # B1 scripting: coids whose get_order should report a transient
        # UNKNOWN (not a definitive absence); and cancels that fail.
        self._unknown_coids: set = set()
        self._cancel_fail_ids: set = set()
        self._submit_raises: Dict[str, Exception] = {}

    # --- scripting helpers ---
    def script_submit(self, coid: str, status: str = "accepted",
                      broker_order_id: Optional[str] = None, **extra) -> None:
        self.submit_responses[coid] = {
            "broker_order_id": broker_order_id or f"bkr-{coid[-8:]}",
            "client_order_id": coid, "status": status, **extra,
        }

    def script_polls(self, coid: str, statuses: List[Dict[str, Any]]) -> None:
        for s in statuses:
            self.poll_responses[coid].append({"client_order_id": coid, **s})

    def script_get_unknown(self, coid: str) -> None:
        """get_order(coid) will return ORDER_UNKNOWN (a transient failure
        the fake cannot resolve) — used to test the fail-safe path."""
        self._unknown_coids.add(coid)

    def script_submit_raises(self, coid: str, exc: Exception) -> None:
        self._submit_raises[coid] = exc

    def script_cancel_fails(self, broker_order_id: str) -> None:
        self._cancel_fail_ids.add(broker_order_id)

    def set_positions(self, positions: List[Dict[str, Any]]) -> None:
        self._positions = list(positions)

    def set_account(self, **kw) -> None:
        self._account.update(kw)

    # --- PaperClient interface ---
    def submit_order(self, client_order_id: str, symbol: str, qty: int,
                     side: str, tif: str) -> Dict[str, Any]:
        if client_order_id in self._submit_raises:
            raise self._submit_raises[client_order_id]
        self.submitted.append({"client_order_id": client_order_id,
                               "symbol": symbol, "qty": qty, "side": side, "tif": tif})
        resp = self.submit_responses.get(
            client_order_id,
            {"broker_order_id": f"bkr-{client_order_id[-8:]}",
             "client_order_id": client_order_id, "status": "accepted"},
        )
        return dict(resp)

    def get_order(self, client_order_id: str) -> GetOrderResult:
        if client_order_id in self._unknown_coids:
            return ORDER_UNKNOWN
        q = self.poll_responses.get(client_order_id)
        if q:
            self._last_poll[client_order_id] = q.popleft()
        if client_order_id in self._last_poll:
            return dict(self._last_poll[client_order_id])
        # The fake is authoritative — a coid it has never seen is
        # DEFINITIVELY absent (not unknown).
        return ORDER_ABSENT

    def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self._cancel_fail_ids:
            return False                 # transient cancel failure
        self.canceled.append(broker_order_id)
        return True

    def list_positions(self) -> List[Dict[str, Any]]:
        return list(self._positions)

    def get_account(self) -> Dict[str, Any]:
        return dict(self._account)

    def list_orders(self, after: Optional[str] = None) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._last_poll.values()]
