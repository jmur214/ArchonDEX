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


class LedgerStore:
    def __init__(self, path: str, starting_cash: float = 0.0,
                 account: str = "roth"):
        self.store = JsonlStore(path)
        self.account = account
        existing = self.store.read_all()
        if existing:
            last = existing[-1]
            self.state = _LedgerState(
                cash=float(last["cash"]),
                positions=dict(last["positions"]),
                realized_pnl=float(last.get("realized_pnl", 0.0)),
                seq=int(last.get("seq", 0)),
            )
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
