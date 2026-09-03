# paper_trader/held_reconcile.py
"""Held-position adoption for the daily loop (T-198).

The cloud pulse was a flat-account heartbeat: it built a fresh ledger
(empty) each day and never converged it to broker truth, so the moment a
position is held the three-way reconcile saw ledger-empty vs broker-holds
and (a) mislabeled the held name a CORPORATE_ACTION (empty known_tickers),
(b) raised CASH_DRIFT → HALT, (c) tripped the `account_flat=False`
canonical gate → the dead-man's-switch inverted into a daily cry-wolf.

The fix: before the reconcile cycles run, CONVERGE the ledger to broker
truth for the part that is EXPLAINED — i.e. attributable to known fills in
the order journal. A genuinely UNEXPLAINED broker position (a ticker we
never ordered, or a quantity our fills don't account for) is NOT adopted:
it must still HALT + read non-canonical (the FAIL-SAFE rule — an
unexplained broker state ⇒ assume nothing).

Pure functions over (orders, broker truth, ledger) so the decision is
unit-testable without a broker.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from paper_trader.order_manager import OrderRecord


def journal_net_positions(orders: List[OrderRecord]) -> Dict[str, int]:
    """Net signed quantity per ticker implied by OBSERVED fills in the
    journal (buy +filled_qty, sell -filled_qty). Belief only updates on an
    observed fill (the LedgerStore contract), so we count filled_qty, not
    intended qty. Zero-net tickers are dropped."""
    net: Dict[str, int] = {}
    for o in orders:
        fq = int(getattr(o, "filled_qty", 0) or 0)
        if fq <= 0:
            continue
        side = str(o.side).lower()
        signed = fq if side in ("buy", "long", "cover") else -fq
        t = o.ticker.upper()
        net[t] = net.get(t, 0) + signed
    return {t: q for t, q in net.items() if q != 0}


def explain_broker_positions(
    broker_positions: Dict[str, int], orders: List[OrderRecord]
) -> Tuple[bool, Dict[str, int]]:
    """Is every held broker position attributable to known journal fills,
    and vice-versa? Strict equality: a mystery broker position (no fill
    explains it) OR a fill-implied position the broker doesn't show makes
    the state UNEXPLAINED. Returns (explained, journal_net)."""
    bpos = {t.upper(): int(q) for t, q in broker_positions.items() if int(q) != 0}
    jnet = journal_net_positions(orders)
    return bpos == jnet, jnet


def known_tickers_for(orders: List[OrderRecord],
                      ledger_positions: Dict[str, int]) -> set:
    """Every ticker the loop has touched — ordered (any state) or held —
    so a legitimately-held name is never mislabeled an unknown-symbol
    ticker change by the reconcile."""
    known = {o.ticker.upper() for o in orders}
    known |= {t.upper() for t in ledger_positions}
    return known


def adopt_explained_broker_truth(
    ledger, broker_positions: Dict[str, int], broker_cash: float,
    orders: List[OrderRecord], *, reason: str,
) -> bool:
    """Converge the ledger to broker truth IFF the held state is explained
    by known fills. Adopts positions + the associated cash (the cash moved
    *because* of those explained fills). Returns ``account_explained``:
    True  = flat, or held positions all explained (canonical-eligible);
    False = a genuine UNEXPLAINED position (stays non-canonical/HALT).

    A flat-but-cash-drifted account is left to the reconcile's CASH_DRIFT
    check (we adopt cash only alongside explained POSITION changes, never
    to paper over a standalone cash mystery)."""
    explained, _jnet = explain_broker_positions(broker_positions, orders)
    bpos = {t.upper(): int(q) for t, q in broker_positions.items() if int(q) != 0}
    # T-327 (2026-09-03, account-3's first FAILED run): the guard here used to read
    # ``if explained and bpos`` — "are there broker positions NOW" — which skipped
    # adoption in exactly the case that needs it most: an account our own fills took
    # FLAT. The ledger has no fill-application path (LedgerStore.apply_fill has zero
    # production callers); it stays in sync ONLY by re-adopting broker truth. So on
    # the day the AI sold everything, the ledger kept 5 AGG / 1 GLD / 1 SPY and
    # $1,664 of already-spent cash, the reconciler correctly raised position_drift +
    # cash_drift, and the run went NON-CANONICAL. It would have stayed wedged: with
    # the broker flat, every later run skipped adoption too, so preflight would halt
    # and block submission every day, forever.
    #
    # The condition the docstring actually describes is an explained position
    # CHANGE, not a non-empty position SET — and going flat is a position change.
    # So adopt when the broker holds explained positions OR when the LEDGER still
    # holds positions the (strictly-equal) journal says are gone. A flat ledger with
    # a standalone cash gap still adopts NOTHING and is left to CASH_DRIFT, which is
    # the mystery this guard exists to protect.
    ledger_stale_positions = any(int(q) != 0 for q in (ledger.positions() or {}).values())
    if explained and (bpos or ledger_stale_positions):
        ledger.adopt_broker_truth(bpos, cash=broker_cash, reason=reason)
    return explained
