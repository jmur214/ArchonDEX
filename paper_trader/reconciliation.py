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

            if st == OrderState.ACKED and inp.window_closed and o.filled_qty == 0:
                findings.append(ReconcileFinding(
                    klass=CLASS_MISSED_FILL, ticker=o.ticker,
                    action="cancel; log; NO chase (re-enters via tomorrow's signal)",
                    detail=f"{o.client_order_id} acked but unfilled past window",
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
            if t not in known and t not in inp.ledger_positions:
                # a symbol we never traded showed up at the broker — a
                # split/ticker-change morph (the manual class).
                findings.append(ReconcileFinding(
                    klass=CLASS_CORPORATE_ACTION, ticker=t, manual=True,
                    action="halt the ticker; manual review",
                    detail=f"unknown symbol {t} at broker (qty {bq}) — "
                           "suspected split/ticker change",
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
