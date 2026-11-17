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

    # --------------------------- corporate actions --------------------------- #
    def apply_split(self, ticker: str, ratio: float, ex_date: Any) -> bool:
        """Apply a CONFIRMED split as an explicit journaled event: qty × ratio,
        avg_price ÷ ratio, cash untouched. ``ratio`` = new shares per old share.

        EXACTLY ONCE per (ticker, ex_date): the event text
        ``split:<TICKER>:<ex_date>:ratio=<r>`` is the idempotence key, read back
        from the durable journal itself — so a re-run, or tomorrow's container
        resuming from S3, finds it and applies nothing. Returns True iff it was
        applied now. A flat ticker journals nothing (there is nothing to scale).
        RAISES ``ValueError`` when the result is not whole shares: a fractional
        remainder is cash-in-lieu, which this ledger must not round away."""
        import math
        ticker = ticker.upper()
        ex = str(ex_date)[:10]
        r = float(ratio)
        if not math.isfinite(r) or r <= 0:
            raise ValueError(f"invalid split ratio {ratio!r}")
        if f"{ticker}:{ex}" in self.applied_split_keys():
            return False
        pos = self.state.positions.get(ticker)
        if pos is None or int(pos["qty"]) == 0:
            return False
        new_qty = int(pos["qty"]) * r
        if abs(new_qty - round(new_qty)) > 1e-6:
            raise ValueError(f"{ticker} {int(pos['qty'])} × {r:g} = {new_qty:g} is not "
                             "whole shares (cash-in-lieu)")
        pos["qty"] = int(round(new_qty))
        pos["avg_price"] = float(pos.get("avg_price", 0.0)) / r
        self.state.positions[ticker] = pos
        self._snapshot(event=f"split:{ticker}:{ex}:ratio={r:g}")
        return True

    def applied_splits(self) -> list:
        """Every split this ledger has journaled, as ``SplitEvent``s, replayed
        from the journal (the durable record, not process memory)."""
        from datetime import date as _date
        from paper_trader.corporate_actions import SplitEvent
        out = []
        for rec in self.store.read_all():
            ev = str(rec.get("event", ""))
            if not ev.startswith("split:"):
                continue
            try:
                _, tkr, ex, rat = ev.split(":", 3)
                out.append(SplitEvent(tkr, _date.fromisoformat(ex),
                                      float(rat.split("=", 1)[1])))
            except (ValueError, IndexError):
                continue        # not one of ours; an unreadable marker applies nothing
        return out

    def applied_split_keys(self) -> set:
        return {s.key for s in self.applied_splits()}

    def last_event_date(self) -> "Optional[Any]":
        """The date carried by the most recent DATED journal event (the adopt
        and split events name their day; ``fill``/``init`` do not), or None."""
        import re
        from datetime import date as _date
        for rec in reversed(self.store.read_all()):
            m = re.search(r"(\d{4}-\d{2}-\d{2})", str(rec.get("event", "")))
            if m:
                try:
                    return _date.fromisoformat(m.group(1))
                except ValueError:
                    continue
        return None

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
