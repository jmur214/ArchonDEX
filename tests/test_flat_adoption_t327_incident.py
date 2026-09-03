# tests/test_flat_adoption_t327_incident.py
"""T-327 — account-3's first FAILED run (2026-09-03): going FLAT wedged the ledger.

The AI's note took the account to zero (sell 5 AGG, 1 GLD, 1 SPY). The fills
executed at the broker; the ledger never learned. `LedgerStore.apply_fill` has
ZERO production callers — the ledger is not an independent record, it is a
MIRROR kept in sync by re-adopting broker truth — and `adopt_explained_broker_truth`
skipped adoption whenever the broker held nothing (`if explained and bpos`).

Consequences, all observed in the live artifacts: ledger 5/1/1 vs broker 0/0/0,
cash gap $1,664.10, position_drift + cash_drift (both halt-class), run
NON-CANONICAL, exit 70. And it would NOT have self-healed: with the broker flat,
every subsequent run skips adoption too, so preflight halts and BLOCKS submission
every day forever.

These tests lock the fix and, just as importantly, the guard it must not break.
"""
from paper_trader.held_reconcile import adopt_explained_broker_truth
from paper_trader.order_manager import OrderRecord, OrderState


class _Ledger:
    def __init__(self, positions, cash):
        self._p, self._c, self.adoptions = dict(positions), cash, []

    def positions(self):
        return dict(self._p)

    def cash(self):
        return self._c

    def adopt_broker_truth(self, positions, cash=None, reason=""):
        self._p = {t: q for t, q in positions.items() if q}
        if cash is not None:
            self._c = cash
        self.adoptions.append({"positions": dict(self._p), "cash": self._c,
                               "reason": reason})


def _filled(ticker, side, qty):
    return OrderRecord(client_order_id=f"{ticker}-{side}-{qty}", trade_date="2026-09-03",
                       ticker=ticker, side=side, qty=qty, tif="day",
                       state=OrderState.FILLED.value, filled_qty=qty)


def test_going_flat_by_our_own_fills_ADOPTS_the_flat_truth():
    """THE INCIDENT. Ledger holds yesterday's book; today's fills sold it all;
    broker is flat. Before the fix this adopted NOTHING and wedged the account."""
    led = _Ledger({"AGG": 5, "GLD": 1, "SPY": 1}, 98_377.56)
    orders = [_filled("AGG", "buy", 5), _filled("GLD", "buy", 1), _filled("SPY", "buy", 1),
              _filled("AGG", "sell", 5), _filled("GLD", "sell", 1), _filled("SPY", "sell", 1)]
    explained = adopt_explained_broker_truth(
        led, {}, 100_041.66, orders, reason="cloud cycle 2026-09-03 reconcile")
    assert explained is True
    assert led.adoptions, "the flat account was never adopted — the wedge"
    assert led.positions() == {}
    assert led.cash() == 100_041.66          # the cash moved BECAUSE of those fills


def test_a_flat_ledger_with_a_STANDALONE_cash_gap_still_adopts_nothing():
    """The guard's real purpose, preserved: no explained position change means the
    cash mystery is NOT papered over — it is left to the reconciler's CASH_DRIFT."""
    led = _Ledger({}, 98_000.00)
    explained = adopt_explained_broker_truth(led, {}, 100_041.66, [], reason="r")
    assert explained is True
    assert led.adoptions == []               # nothing adopted
    assert led.cash() == 98_000.00           # the gap SURVIVES to be reported


def test_a_held_explained_position_still_adopts_as_before():
    led = _Ledger({}, 99_000.0)
    orders = [_filled("SPY", "buy", 1)]
    assert adopt_explained_broker_truth(led, {"SPY": 1}, 98_200.0, orders, reason="r") is True
    assert led.positions() == {"SPY": 1} and led.cash() == 98_200.0


def test_an_UNEXPLAINED_broker_position_is_never_adopted():
    """A mystery position must stay unexplained → non-canonical, never absorbed."""
    led = _Ledger({}, 99_000.0)
    assert adopt_explained_broker_truth(led, {"TSLA": 3}, 98_000.0, [], reason="r") is False
    assert led.adoptions == []
