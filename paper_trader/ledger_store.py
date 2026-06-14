# paper_trader/ledger_store.py
"""LedgerStore — positions/cash AS WE BELIEVE, append-only.

This is the (a) leg of the three-way reconciliation (§2): what our loop
thinks it holds, derived only from fills we have OBSERVED (never from
intended orders — that conflation is exactly the
mode_controller-adapter bug T-159 flagged, where fills are fabricated
at intended prices). The broker is truth (leg b); the order journal is
expectation (leg c). The ledger is belief, and belief only updates on
an observed fill.

Append-only: every mutation writes a new snapshot line, so the position
history is auditable and crash-recovery replays to the last good line.
``load`` returns the latest snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

from paper_trader._jsonl import JsonlStore


@dataclass
class LedgerPosition:
    ticker: str
    qty: int = 0                  # signed: long > 0, short < 0
    avg_price: float = 0.0


@dataclass
class _LedgerState:
    cash: float = 0.0
    positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    realized_pnl: float = 0.0
    seq: int = 0                  # monotonic snapshot counter


def _parse_ledger_state(rec: Dict[str, Any]) -> "_LedgerState":
    """Validate + parse one ledger snapshot line by VALUE (T-163-fix3
    major-1/2): cash/realized_pnl must be finite floats, seq an int, and
    positions a dict of {ticker: {qty:int, ...}}. Raises ValueError on
    any invalid value so the caller can quarantine it (the SAME
    defensive contract as the order-journal replay)."""
    import math
    cash = float(rec["cash"])
    if not math.isfinite(cash):
        raise ValueError("non-finite cash")
    pnl = float(rec.get("realized_pnl", 0.0))
    if not math.isfinite(pnl):
        raise ValueError("non-finite realized_pnl")
    seq = int(rec.get("seq", 0))
    positions = rec.get("positions", {})
    if not isinstance(positions, dict):
        raise ValueError("positions is not a dict")
    clean_pos: Dict[str, Any] = {}
    for tkr, p in positions.items():
        if not isinstance(p, dict):
            raise ValueError(f"position {tkr} is not a dict")
        int(p["qty"])           # must be int-coercible
        float(p.get("avg_price", 0.0))
        clean_pos[str(tkr)] = p
    return _LedgerState(cash=cash, positions=clean_pos, realized_pnl=pnl, seq=seq)


class LedgerStore:
    def __init__(self, path: str, starting_cash: float = 0.0,
                 account: str = "roth"):
        self.store = JsonlStore(path)
        self.account = account
        self.quarantined: list = []      # malformed/invalid ledger lines
        # T-163-fix3 major-1: DEFENSIVE read-back — walk the snapshots and
        # adopt the LAST VALID one. A malformed/invalid last line (e.g. a
        # crash mid-ledger-write — the exact recovery scenario) is
        # QUARANTINED, never crashing construction; good earlier lines
        # still load.
        last_valid: "_LedgerState | None" = None
        for rec in self.store.read_all():
            try:
                last_valid = _parse_ledger_state(rec)
            except Exception as exc:
                self.quarantined.append({"line": rec, "error": type(exc).__name__})
        if last_valid is not None:
            self.state = last_valid
        else:
            self.state = _LedgerState(cash=float(starting_cash))
            self._snapshot(event="init")

    # ------------------------------------------------------------------ #
    def _snapshot(self, event: str) -> None:
        self.state.seq += 1
        rec = asdict(self.state)
        rec["event"] = event
        rec["account"] = self.account
        self.store.append(rec)

    def apply_fill(self, ticker: str, side: str, qty: int, price: float,
                   commission: float = 0.0) -> None:
        """Update belief from an OBSERVED fill (buy/sell). FIFO-less avg-
        price accounting mirroring PortfolioEngine.apply_fill's identity
        (equity = cash + Σ qty·price) without importing it (pure-new)."""
        ticker = ticker.upper()
        side = side.lower()
        qty = int(qty)
        if qty <= 0 or price <= 0:
            return
        pos = self.state.positions.get(ticker, {"ticker": ticker, "qty": 0, "avg_price": 0.0})
        cur = int(pos["qty"])
        signed = qty if side in ("buy", "long", "cover") else -qty

        if cur == 0 or (cur > 0) == (signed > 0):
            # Opening or adding in the same direction: weighted avg.
            new_qty = cur + signed
            if new_qty != 0:
                pos["avg_price"] = (
                    abs(cur) * pos["avg_price"] + abs(signed) * price
                ) / abs(new_qty)
            pos["qty"] = new_qty
            self.state.cash -= signed * price
        else:
            # Reducing/closing/flipping: realize against avg_price.
            close_qty = min(abs(cur), abs(signed))
            direction = 1 if cur > 0 else -1
            self.state.realized_pnl += (price - pos["avg_price"]) * close_qty * direction
            self.state.cash += direction * close_qty * price
            remaining = cur + signed
            pos["qty"] = remaining
            if remaining == 0:
                pos["avg_price"] = 0.0
            elif (remaining > 0) != (cur > 0):
                # Flipped past zero: residual opens at fill price.
                pos["avg_price"] = price

        self.state.cash -= float(commission)
        if pos["qty"] == 0:
            self.state.positions.pop(ticker, None)
        else:
            self.state.positions[ticker] = pos
        self._snapshot(event="fill")

    def adopt_broker_truth(self, positions: Dict[str, int],
                           cash: Optional[float] = None,
                           reason: str = "reconcile") -> None:
        """Overwrite belief with broker truth — the reconciliation path
        for explained position/cash drift (§2). Records WHY."""
        self.state.positions = {
            t.upper(): {"ticker": t.upper(), "qty": int(q),
                        "avg_price": float(self.state.positions.get(t.upper(), {}).get("avg_price", 0.0))}
            for t, q in positions.items() if int(q) != 0
        }
        if cash is not None:
            self.state.cash = float(cash)
        self._snapshot(event=f"adopt_broker:{reason}")

    # ------------------------------ reads ------------------------------ #
    def positions(self) -> Dict[str, int]:
        return {t: int(p["qty"]) for t, p in self.state.positions.items()}

    def cash(self) -> float:
        return float(self.state.cash)

    def position(self, ticker: str) -> LedgerPosition:
        p = self.state.positions.get(ticker.upper())
        if p is None:
            return LedgerPosition(ticker=ticker.upper())
        return LedgerPosition(ticker=p["ticker"], qty=int(p["qty"]),
                              avg_price=float(p["avg_price"]))
