"""engines/engine_b_risk/cross_account_wash_guard.py — T-319 (spec: A/T-317 §1).

The CROSS-ACCOUNT wash-sale guard: it refuses a buy that would trip IRC §1091 /
Rev. Rul. 2008-5 against a substantially-identical LOSS sale in ANY sibling
account inside the 61-day window.

Why the existing single-account ``WashSaleAvoidance`` is not enough (spec §1.1):
  * it is SINGLE-account — a loss in the taxable account cannot block a buy in the
    Roth (and vice versa); that cross-account case is the fatal one;
  * it matches EXACT tickers — but a Roth VOO buy after a taxable SPY loss is
    "substantially identical" and trips 2008-5;
  * it uses a 30-day FORWARD window — the rule is 61 days, BOTH directions;
  * it returns a bool that is silently skipped — this guard REFUSES LOUDLY.

The asymmetry that makes this fail-CLOSED (spec §1.1): a normal wash sale merely
DEFERS the loss (basis moves to the replacement lot). **Rev. Rul. 2008-5 — an
IRA/Roth purchase — PERMANENTLY DISALLOWS it. The loss is gone forever, no basis
addition.** A monthly rebalancer running the same tickers in two accounts trips
this by construction. So when in doubt the guard REFUSES: a refused rebalance
costs basis points of tracking error; a permanently-disallowed loss costs the
entire TLH thesis.

REPORT-vs-REFUSE boundary: the guard is an AUTHORITY, not an advisor — a REFUSE
raises ``WashSaleRefusal`` before the order reaches the broker. It never
logs-and-allows and it is never double-run against the single-account guard (one
authority per order — spec §1.3).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_CLASSES_PATH = "config/substantially_identical.json"
DEFAULT_LEDGER_PATH = "data/state/tax_lots.jsonl"
WASH_WINDOW_DAYS = 30            # 30 before ∪ sale day ∪ 30 after = the 61-day window
TAXABLE = "taxable"


# ── equivalence classes (config, not code — a reviewable tax judgment) ─────────
class EquivalenceClasses:
    """Maps a ticker → its substantially-identical class. A ticker not in any
    class is its OWN class (only exact-ticker identity, the conservative floor)."""

    def __init__(self, classes: Dict[str, List[str]], version: str = "unknown"):
        self.version = version
        self._by_symbol: Dict[str, str] = {}
        for cls, members in classes.items():
            for m in members:
                self._by_symbol[m.upper()] = cls

    @classmethod
    def load(cls, path: str = DEFAULT_CLASSES_PATH) -> "EquivalenceClasses":
        cfg = json.loads(Path(path).read_text())
        return cls(cfg.get("classes", {}), version=cfg.get("version", "unknown"))

    def class_of(self, symbol: str) -> str:
        """The equivalence class of ``symbol`` — or a self-class ``SELF:<TICKER>``
        when it is in no configured class (so two unrelated tickers never collide
        on a shared 'unclassified' bucket)."""
        s = symbol.upper()
        return self._by_symbol.get(s, f"SELF:{s}")


# ── the cross-account tax-lot ledger (durable, append-only, FIFO) ──────────────
@dataclass
class LotEvent:
    event_id: str
    ts: str                       # ISO-8601 date/datetime the fill occurred
    account: str                  # "taxable" | "roth" | "<paper-N>"
    symbol: str
    side: str                     # "buy" | "sell"
    qty: int
    price: float
    lot_id: str
    is_loss_sale: bool = False
    realized_pnl: Optional[float] = None
    client_order_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _event_id(account: str, symbol: str, side: str, ts: str, coid: Optional[str]) -> str:
    raw = f"{account}|{symbol.upper()}|{side.lower()}|{ts}|{coid or ''}"
    return "lot-" + hashlib.sha1(raw.encode()).hexdigest()[:16]


def _as_date(ts) -> _dt.date:
    if isinstance(ts, _dt.date) and not isinstance(ts, _dt.datetime):
        return ts
    if isinstance(ts, _dt.datetime):
        return ts.date()
    s = str(ts)
    return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date() \
        if ("T" in s or "+" in s) else _dt.date.fromisoformat(s[:10])


class TaxLotLedger:
    """Append-only cross-account lot ledger. BUY fills open lots; SELL fills
    consume open lots FIFO to compute realized P&L + is_loss_sale (the broker
    gives fill price/qty/side, NOT cost basis — so the LEDGER derives the loss).
    Persisted as JSONL so it survives the ephemeral Fargate disk (the T-308
    durability lesson — a reset would silently empty the 61-day window)."""

    def __init__(self, path: str = DEFAULT_LEDGER_PATH):
        self.path = Path(path)
        self.events: List[LotEvent] = []
        self._open: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}   # (acct,sym)->[lots]
        self._seen: set = set()
        self._replay()

    # -- persistence --------------------------------------------------------- #
    def _replay(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                ev = LotEvent(**{k: d[k] for k in d if k in LotEvent.__dataclass_fields__})
            except Exception:
                continue                      # a torn line is skipped, never fatal
            self._apply(ev, persist=False)

    def _append(self, ev: LotEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(ev.to_dict(), default=str) + "\n")

    # -- the FIFO state machine --------------------------------------------- #
    def _apply(self, ev: LotEvent, persist: bool) -> LotEvent:
        if ev.event_id in self._seen:         # idempotent replay/record
            return ev
        self._seen.add(ev.event_id)
        key = (ev.account, ev.symbol.upper())
        if ev.side == "buy":
            self._open.setdefault(key, []).append(
                {"qty": int(ev.qty), "price": float(ev.price), "lot_id": ev.lot_id})
        else:  # sell — consume FIFO, derive realized P&L if not already stamped
            if ev.realized_pnl is None:
                remaining, pnl = int(ev.qty), 0.0
                lots = self._open.get(key, [])
                while remaining > 0 and lots:
                    lot = lots[0]
                    take = min(remaining, lot["qty"])
                    pnl += (float(ev.price) - lot["price"]) * take
                    lot["qty"] -= take
                    remaining -= take
                    if lot["qty"] == 0:
                        lots.pop(0)
                ev.realized_pnl = round(pnl, 6)
                ev.is_loss_sale = ev.realized_pnl < 0.0
        self.events.append(ev)
        if persist:
            self._append(ev)
        return ev

    # -- public API ---------------------------------------------------------- #
    def record_fill(self, *, account: str, symbol: str, side: str, qty: int,
                    price: float, ts, client_order_id: Optional[str] = None,
                    lot_id: Optional[str] = None) -> LotEvent:
        """Append a fill (broker truth). Returns the stamped LotEvent (with the
        derived realized_pnl/is_loss_sale for sells)."""
        ts_s = _as_date(ts).isoformat() if not isinstance(ts, str) else ts
        eid = _event_id(account, symbol, side, ts_s, client_order_id)
        ev = LotEvent(event_id=eid, ts=ts_s, account=account, symbol=symbol.upper(),
                      side=side.lower(), qty=int(qty), price=float(price),
                      lot_id=lot_id or eid, client_order_id=client_order_id)
        return self._apply(ev, persist=True)

    def loss_sales(self, *, cls: str, window: Tuple[_dt.date, _dt.date],
                   classes: EquivalenceClasses,
                   accounts: Optional[List[str]] = None) -> List[LotEvent]:
        """Every LOSS sale whose symbol's class == ``cls`` inside ``window``
        (inclusive), across ``accounts`` (ALL when None)."""
        lo, hi = window
        out = []
        for ev in self.events:
            if ev.side != "sell" or not ev.is_loss_sale:
                continue
            if accounts is not None and ev.account not in accounts:
                continue
            if classes.class_of(ev.symbol) != cls:
                continue
            if lo <= _as_date(ev.ts) <= hi:
                out.append(ev)
        return out

    def buys(self, *, cls: str, window: Tuple[_dt.date, _dt.date],
             classes: EquivalenceClasses,
             accounts: Optional[List[str]] = None) -> List[LotEvent]:
        """Every BUY whose symbol's class == ``cls`` inside ``window`` — the
        BACKWARD-direction lookup (a buy in [T−30, T) poisons a later loss-sale)."""
        lo, hi = window
        out = []
        for ev in self.events:
            if ev.side != "buy":
                continue
            if accounts is not None and ev.account not in accounts:
                continue
            if classes.class_of(ev.symbol) != cls:
                continue
            if lo <= _as_date(ev.ts) <= hi:
                out.append(ev)
        return out


# ── the decision + the typed refusal ───────────────────────────────────────────
@dataclass
class Decision:
    allow: bool
    reason: Optional[str] = None            # e.g. "rev_rul_2008_5_permanent_disallowance"
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        return not self.allow


ALLOW = Decision(allow=True)


class WashSaleRefusal(Exception):
    """Raised pre-submission when a buy would trip the wash-sale rule. Typed so the
    order path records REJECTED with a specific reason and NEVER reaches the broker."""

    def __init__(self, reason: str, evidence: List[Dict[str, Any]]):
        self.reason = reason
        self.evidence = evidence
        super().__init__(f"wash_sale:{reason} — {len(evidence)} substantially-identical loss-sale(s) in window")


class CrossAccountWashGuard:
    """The order-path authority. One instance per fleet (shared ledger across
    accounts). ``check_order`` is fail-closed by design."""

    def __init__(self, ledger: TaxLotLedger, classes: EquivalenceClasses):
        self.ledger = ledger
        self.classes = classes

    def check_order(self, *, account: str, symbol: str, side: str, ts) -> Decision:
        """The pre-submission decision (spec §1.2). Sells never trip the guard;
        a buy is REFUSED if a substantially-identical LOSS sale sits in the
        61-day window in ANY account (Roth-buy vs any taxable loss = the fatal
        permanent-disallowance case)."""
        if side.lower() != "buy":
            return ALLOW
        cls = self.classes.class_of(symbol)
        day = _as_date(ts)
        window = (day - _dt.timedelta(days=WASH_WINDOW_DAYS),
                  day + _dt.timedelta(days=WASH_WINDOW_DAYS))
        hits = self.ledger.loss_sales(cls=cls, window=window, classes=self.classes)
        if not hits:
            return ALLOW
        # a deferral (taxable→taxable) is still refused; a Roth/IRA buy against a
        # taxable loss is the PERMANENT disallowance (Rev. Rul. 2008-5).
        buyer_taxable = account == TAXABLE
        all_hits_taxable = all(h.account == TAXABLE for h in hits)
        reason = ("wash_sale_deferral" if buyer_taxable and all_hits_taxable
                  else "rev_rul_2008_5_permanent_disallowance")
        return Decision(allow=False, reason=reason,
                        evidence=[h.to_dict() for h in hits])

    def check_loss_sale(self, *, account: str, symbol: str, ts) -> Decision:
        """BACKWARD direction (spec §1.2): before a LOSS sale, flag it
        WOULD_BE_WASH if a substantially-identical buy occurred in the prior 30
        days in ANY account (the sale poisons — or is poisoned by — that buy).
        Report-only signal here (``reason='would_be_wash'``); the order path
        decides to defer or accept-with-disallowed-marked (never silently)."""
        cls = self.classes.class_of(symbol)
        day = _as_date(ts)
        window = (day - _dt.timedelta(days=WASH_WINDOW_DAYS), day)
        prior_buys = self.ledger.buys(cls=cls, window=window, classes=self.classes)
        if not prior_buys:
            return ALLOW
        return Decision(allow=False, reason="would_be_wash",
                        evidence=[b.to_dict() for b in prior_buys])
