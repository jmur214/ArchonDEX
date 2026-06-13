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
from typing import Any, Deque, Dict, List, Optional, Protocol


class PaperClient(Protocol):
    def submit_order(self, client_order_id: str, symbol: str, qty: int,
                     side: str, tif: str) -> Dict[str, Any]: ...
    def get_order(self, client_order_id: str) -> Optional[Dict[str, Any]]: ...
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

    def __init__(self, env_path: Optional[str] = None):
        # Best-effort .env load (repo root); real creds may already be in
        # the environment. Never logged.
        try:
            from dotenv import load_dotenv
            root = Path(__file__).resolve().parents[1]
            load_dotenv(env_path or (root / ".env"))
        except Exception:
            pass

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

    def get_order(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        try:
            o = self._client.get_order_by_client_id(client_order_id)
        except Exception:
            return None
        return _normalize_order(o) if o is not None else None

    def cancel_order(self, broker_order_id: str) -> bool:
        try:
            self._client.cancel_order_by_id(broker_order_id)
            return True
        except Exception:
            return False

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

    def set_positions(self, positions: List[Dict[str, Any]]) -> None:
        self._positions = list(positions)

    def set_account(self, **kw) -> None:
        self._account.update(kw)

    # --- PaperClient interface ---
    def submit_order(self, client_order_id: str, symbol: str, qty: int,
                     side: str, tif: str) -> Dict[str, Any]:
        self.submitted.append({"client_order_id": client_order_id,
                               "symbol": symbol, "qty": qty, "side": side, "tif": tif})
        resp = self.submit_responses.get(
            client_order_id,
            {"broker_order_id": f"bkr-{client_order_id[-8:]}",
             "client_order_id": client_order_id, "status": "accepted"},
        )
        return dict(resp)

    def get_order(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        q = self.poll_responses.get(client_order_id)
        if q:
            self._last_poll[client_order_id] = q.popleft()
        return dict(self._last_poll[client_order_id]) if client_order_id in self._last_poll else None

    def cancel_order(self, broker_order_id: str) -> bool:
        self.canceled.append(broker_order_id)
        return True

    def list_positions(self) -> List[Dict[str, Any]]:
        return list(self._positions)

    def get_account(self) -> Dict[str, Any]:
        return dict(self._account)

    def list_orders(self, after: Optional[str] = None) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._last_poll.values()]
