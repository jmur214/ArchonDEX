# paper_trader/reconciliation.py
"""ReconciliationEngine — the three-way diff (§2 of the T-159 design).

Every cycle diffs three states:
  (a) ledger — positions/cash AS WE BELIEVE (LedgerStore)
  (b) broker — truth (PaperClient: positions, account, orders)
  (c) journal-expected — what this cycle's orders imply (OrderRecords)

and classifies every divergence into one of SEVEN pre-registered
classes, each with its response chosen NOW (the T-152 philosophy — not
during the event). Only cash/position drift HALT new submissions; only
corporate actions are intentionally manual. The engine never mutates
state — it returns findings; the caller (scheduler/loop) applies the
ledger adoption and halt flag.

A cycle is ``clean`` iff it produced ZERO findings — ledger, journal,
and broker all agree. The reconcile_log's per-cycle ``clean`` bool feeds
promotion criterion §5.3 (clean-rate ≥ 99%).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from paper_trader.order_manager import OrderRecord, OrderState

# The seven classes (frozen — these are the pre-registered taxonomy).
CLASS_MISSED_FILL = "missed_fill"
CLASS_PARTIAL_FILL = "partial_fill"
CLASS_REJECT = "reject"
CLASS_PRICE_DRIFT = "price_drift"
CLASS_CASH_DRIFT = "cash_drift"
CLASS_POSITION_DRIFT = "position_drift"
CLASS_CORPORATE_ACTION = "corporate_action"

ALL_CLASSES = (
    CLASS_MISSED_FILL, CLASS_PARTIAL_FILL, CLASS_REJECT, CLASS_PRICE_DRIFT,
    CLASS_CASH_DRIFT, CLASS_POSITION_DRIFT, CLASS_CORPORATE_ACTION,
)


@dataclass
class ReconcileInputs:
    ledger_positions: Dict[str, int]
    ledger_cash: float
    broker_positions: Dict[str, int]
    broker_cash: float
    orders: List[OrderRecord] = field(default_factory=list)
    expected_prices: Dict[str, float] = field(default_factory=dict)   # coid -> auction print
    reject_reasons: Dict[str, str] = field(default_factory=dict)      # coid -> raw reason
    known_tickers: Optional[set] = None        # tickers the system trades
    window_closed: bool = False                # auction window has passed
    # T-163 crit-5: explicit corporate-action feed (tickers with a known
    # split / symbol change today) — authoritative over the ratio
    # heuristic when present.
    corporate_action_tickers: Optional[set] = None
    # price-drift threshold = auction_safety_bps + extra
    auction_safety_bps: float = 1.0
    price_drift_extra_bps: float = 5.0
    cash_tol: float = 1.0


@dataclass
class ReconcileFinding:
    klass: str
    action: str
    halt: bool = False
    manual: bool = False
    ticker: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> Dict:
        return {
            "klass": self.klass, "action": self.action, "halt": self.halt,
            "manual": self.manual, "ticker": self.ticker, "detail": self.detail,
        }


@dataclass
class ReconcileResult:
    clean: bool
    halt: bool
    findings: List[ReconcileFinding]
    counts: Dict[str, int]

    def to_dict(self) -> Dict:
        return {
            "clean": self.clean, "halt": self.halt,
            "counts": self.counts,
            "findings": [f.to_dict() for f in self.findings],
        }


def _looks_like_corporate_action(ledger_qty: int, broker_qty: int) -> bool:
    """T-163 crit-5: a split / reverse-split morphs a HELD position by a
    clean small-integer ratio (2:1, 3:1, 4:1, … or reverse 1:2 …). A
    genuine position drift is an arbitrary mismatch. Same sign, ratio is
    a near-exact small integer either way → treat as a corporate action
    (manual review), NOT a halt-class position drift."""
    if ledger_qty == 0 or broker_qty == 0:
        return False
    if (ledger_qty > 0) != (broker_qty > 0):
        return False                       # a sign flip is never a split
    a, b = abs(ledger_qty), abs(broker_qty)
    hi, lo = max(a, b), min(a, b)
    if lo == 0:
        return False
    ratio = hi / lo
    nearest = round(ratio)
    return 2 <= nearest <= 20 and abs(ratio - nearest) < 1e-6


def _classify_reject(reason: str) -> str:
    r = (reason or "").lower()
    if "fractional" in r:
        return "fractional"
    if "after" in r or "cutoff" in r or "closed" in r or "tradable" in r:
        return "after_cutoff"
    if "buying power" in r or "insufficient" in r or "cash" in r:
        return "buying_power"
    return "other"


class ReconciliationEngine:
    def reconcile(self, inp: ReconcileInputs) -> ReconcileResult:
        findings: List[ReconcileFinding] = []
        open_tickers = {
            o.ticker for o in inp.orders
            if not OrderState(o.state).is_terminal
            and o.state != OrderState.STAGED.value
        }

        # ---- per-order classes: reject / missed-fill / partial / price-drift
        for o in inp.orders:
            st = OrderState(o.state)
            if st == OrderState.REJECTED:
                sub = _classify_reject(inp.reject_reasons.get(o.client_order_id, ""))
                findings.append(ReconcileFinding(
                    klass=CLASS_REJECT, ticker=o.ticker,
                    action=f"skip ticker for the day (reason={sub}); "
                           "alarm if >3 rejects/week",
                    detail=f"{o.client_order_id} rejected ({sub})",
                ))
                continue

            # T-163 crit-3: a SUBMITTED-but-never-acked order past the
            # window is ALSO a missed fill (previously invisible — only
            # ACKED was checked).
            if (st in (OrderState.ACKED, OrderState.SUBMITTED)
                    and inp.window_closed and o.filled_qty == 0):
                findings.append(ReconcileFinding(
                    klass=CLASS_MISSED_FILL, ticker=o.ticker,
                    action="cancel/expire; log; NO chase (re-enters via tomorrow's signal)",
                    detail=f"{o.client_order_id} {st.value} but unfilled past window",
                ))
                continue

            # partial: filled some but not all, and the order is done OR
            # the window has closed (won't fill the remainder).
            if (0 < o.filled_qty < o.qty
                    and (st in (OrderState.CANCELED, OrderState.EXPIRED)
                         or inp.window_closed)):
                findings.append(ReconcileFinding(
                    klass=CLASS_PARTIAL_FILL, ticker=o.ticker,
                    action="ledger adopts broker truth; remainder canceled "
                           "(>1/wk partials = alarm)",
                    detail=f"{o.client_order_id} filled {o.filled_qty}/{o.qty}",
                ))
                # NB partial is also a price-drift candidate; fall through.

            # price drift on any fill we have a price + expectation for.
            if o.filled_qty > 0 and o.filled_avg_price is not None:
                exp = inp.expected_prices.get(o.client_order_id)
                if exp is not None and exp > 0:
                    drift_bps = abs(o.filled_avg_price - exp) / exp * 1e4
                    thresh = inp.auction_safety_bps + inp.price_drift_extra_bps
                    if drift_bps > thresh:
                        findings.append(ReconcileFinding(
                            klass=CLASS_PRICE_DRIFT, ticker=o.ticker,
                            action="accept fill (it is truth); feed slippage-error series",
                            detail=f"{o.client_order_id} fill {o.filled_avg_price:.4f} "
                                   f"vs expected {exp:.4f} = {drift_bps:.1f}bps "
                                   f"(>{thresh:.1f})",
                        ))

        # ---- cash drift (halt class) ----
        cash_gap = abs(inp.ledger_cash - inp.broker_cash)
        if cash_gap > inp.cash_tol:
            findings.append(ReconcileFinding(
                klass=CLASS_CASH_DRIFT, halt=True, action="HALT new submissions",
                detail=f"ledger cash {inp.ledger_cash:.2f} vs broker "
                       f"{inp.broker_cash:.2f} (gap {cash_gap:.2f})",
            ))

        # ---- position drift + corporate action (halt / manual) ----
        known = inp.known_tickers if inp.known_tickers is not None else set(
            inp.ledger_positions
        )
        all_tickers = set(inp.ledger_positions) | set(inp.broker_positions)
        for t in sorted(all_tickers):
            lq = int(inp.ledger_positions.get(t, 0))
            bq = int(inp.broker_positions.get(t, 0))
            if lq == bq:
                continue
            if t in open_tickers:
                continue   # an open order legitimately explains the gap
            ca_feed = inp.corporate_action_tickers or set()
            unknown_symbol = t not in known and t not in inp.ledger_positions
            # T-163 crit-5: a split/morph on a HELD name (clean ratio) OR
            # an explicitly-fed corporate action is the MANUAL class — not
            # a halt-class position drift. An unknown symbol appearing
            # (ticker change) is also a corporate action.
            held_split = (lq != 0 and _looks_like_corporate_action(lq, bq))
            if unknown_symbol or held_split or t in ca_feed:
                detail = (f"unknown symbol {t} at broker (qty {bq}) — "
                          "suspected ticker change" if unknown_symbol else
                          f"{t} held {lq} → broker {bq} (clean ratio — "
                          "suspected split)" if held_split else
                          f"{t} on corporate-action feed (ledger {lq}, broker {bq})")
                findings.append(ReconcileFinding(
                    klass=CLASS_CORPORATE_ACTION, ticker=t, manual=True,
                    action="halt the ticker; manual review", detail=detail,
                ))
            else:
                findings.append(ReconcileFinding(
                    klass=CLASS_POSITION_DRIFT, ticker=t, halt=True,
                    action="HALT new submissions; adopt broker truth only "
                           "after the journal explains it",
                    detail=f"{t} ledger {lq} vs broker {bq}",
                ))

        counts = {c: 0 for c in ALL_CLASSES}
        for f in findings:
            counts[f.klass] += 1
        halt = any(f.halt for f in findings)
        return ReconcileResult(
            clean=(len(findings) == 0), halt=halt,
            findings=findings, counts=counts,
        )
