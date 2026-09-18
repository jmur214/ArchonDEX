# tests/test_cash_adj_feed_t360.py
"""T-360 — FEED the cash_adj channel (C's retraction).

C's original flag said the deploy tracker's near-zero `cash_adj` beside
MOMENTUM_SAT's small-nonzero one was "T-332a working". C then looked: `cash_adj`
had NEVER been written on any family tracker point — 0 of 43 on account-1's
whole life, 0 of 2 on account-2 — and `cash_rate` had no call site in the pulse.
The zero a reader would have taken as confirmation was a DEAD CHANNEL.

The tracker's machinery was already complete. It was only ever missing its
caller — the T-342 shape again: a field that is present, plausible, and never
fed.
"""
from __future__ import annotations

import pandas as pd
import pytest

from paper_trader.live_books import CASH_RATE_TICKER, accrue_cash_adj
from paper_trader.sleeve_tracker import SleeveTracker

CLOSES = {"SPY": 754.05, "AGG": 95.81, "GLD": 391.74}


def test_the_channel_is_DEAD_when_the_caller_passes_nothing(tmp_path):
    """The pre-fix state, kept as the contrast that makes the fix legible."""
    t = SleeveTracker(path="data/state/x.json", root=str(tmp_path))
    t.record("2026-09-18", 100_000.0, CLOSES)
    pt = t._load()[-1]
    assert "cash_adj" not in pt


def test_the_channel_MEASURES_when_both_cash_and_rate_are_supplied(tmp_path):
    t = SleeveTracker(path="data/state/y.json", root=str(tmp_path))
    t.record("2026-09-18", 100_000.0, CLOSES,
             cash_balance=21.58, cash_rate=0.00018)
    pt = t._load()[-1]
    assert pt["cash_adj"]["cash_balance"] == 21.58
    assert pt["cash_adj"]["day_accrual"] == round(21.58 * 0.00018, 4)


def test_a_MISSING_RATE_writes_no_annotation_rather_than_a_silent_zero(tmp_path):
    """'We don't know what cash earned' and 'cash earned nothing' are different
    facts. Writing 0.0 for the first is how the channel looked alive while dead."""
    t = SleeveTracker(path="data/state/z.json", root=str(tmp_path))
    t.record("2026-09-18", 100_000.0, CLOSES, cash_balance=21.58, cash_rate=None)
    assert "cash_adj" not in t._load()[-1]


# ---------------- the shared accrual (one implementation, two surfaces) ------

def test_the_accrual_is_ONE_shared_function_so_the_surfaces_cannot_drift():
    total, ok = accrue_cash_adj(0.0, 1000.0, 100.10, 100.00)
    assert ok and total == pytest.approx(1.0, abs=1e-6)


def test_the_accrual_FAILS_CLOSED_on_a_missing_price():
    total, ok = accrue_cash_adj(5.0, 1000.0, None, 100.0)
    assert total == 5.0 and ok is False, "a missing rate must not accrue 0%"
    total, ok = accrue_cash_adj(5.0, 1000.0, 100.1, None)
    assert total == 5.0 and ok is False


# ---------------- the hazard I nearly shipped --------------------------------

def test_BIL_is_NOT_in_any_trading_fetch_universe():
    """A cash-ANNOTATION ticker must never hold veto power over trading. The
    trading fetches are fail-CLOSED on a missing or stale ticker (_FailClosed
    68), so BIL inside one would let a BIL outage refuse the day's trades. It
    is fetched separately and fail-OPEN instead."""
    import inspect

    import scripts.run_paper_cloud_day as drv
    src = inspect.getsource(drv)
    for bad in ('"GLD", "BIL")', '"IBIT", "BIL")', 'SLEEVE_UNIVERSE) + ("BIL",)',
                'list(SLEEVE_UNIVERSE) + ["BIL"]'):
        assert bad not in src, f"BIL is back inside a fail-closed fetch: {bad}"
    assert "def _cash_rate(client)" in src


def test_the_rate_helper_returns_None_instead_of_raising(tmp_path):
    """Fail-open in the literal sense: a broken price call must not propagate."""
    import scripts.run_paper_cloud_day as drv

    class _Boom:
        def fetch_daily_closes(self, *a, **k):
            raise RuntimeError("feed down")

    assert drv._cash_rate(_Boom()) is None

    class _Short:
        def fetch_daily_closes(self, *a, **k):
            return {CASH_RATE_TICKER: pd.Series([100.0])}      # one bar: no return

    assert drv._cash_rate(_Short()) is None

    class _Good:
        def fetch_daily_closes(self, *a, **k):
            return {CASH_RATE_TICKER: pd.Series([100.00, 100.02])}

    assert drv._cash_rate(_Good()) == pytest.approx(0.0002, abs=1e-9)
