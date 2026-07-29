"""T-332a — the cash-drag ANNOTATION is an annotation, never a restatement.

Verified gap: the backtest credits idle cash at the daily short rate (T-255) but live
Alpaca paper cash earns 0%, biasing every live NAV AGAINST its own backtest spec. The
books now accrue what cash WOULD have earned and report it BESIDE the raw NAV.

These tests exist to make the honesty property STRUCTURAL: the raw number stays primary,
the adjustment can never silently replace it, and a missing rate accrues NOTHING rather
than being assumed 0%.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.live_books import (  # noqa: E402
    CASH_RATE_TICKER, QUALITY_SAT, SPY_NULL, LiveBook)


def _px(spy=600.0, qual=150.0, bil=None):
    d = {"SPY": spy, "QUAL": qual}
    if bil is not None:
        d[CASH_RATE_TICKER] = bil
    return d


# ---------- THE LOCK: raw stays primary ----------
def test_raw_nav_is_never_overwritten_by_the_adjustment(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px(bil=91.00))
    s = b.record("2026-07-29", _px(spy=660.0, bil=91.01))     # BIL +~1.1bp
    raw = s["book_nav"]
    adj = s["cash_adj"]["book_nav_cash_adj"]
    # the raw key still holds the RAW number …
    assert raw == b._state()["days"][-1]["book_nav"]
    # … and the adjusted figure lives under a SEPARATE key, never in its place
    assert "book_nav_cash_adj" not in s
    assert adj >= raw                                          # the annotation only adds
    assert s["cash_adj"]["book_accrued"] > 0


def test_annotation_carries_its_own_disclaimer(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px(bil=91.00))
    s = b.record("2026-07-29", _px(bil=91.01))
    note = s["cash_adj"]["note"]
    assert "ANNOTATION ONLY" in note and "raw NAV above is the record" in note
    assert "Never a restatement" in note


def test_excess_growth_raw_and_adjusted_both_present(tmp_path):
    """Both readings travel together — the reader is never forced to pick blind."""
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px(bil=91.00))
    s = b.record("2026-07-29", _px(spy=606.0, bil=91.01))
    assert "excess_growth" in s                                 # raw
    assert "excess_growth_cash_adj" in s["cash_adj"]             # annotated


# ---------- FAIL-CLOSED: a missing rate accrues NOTHING ----------
def test_missing_rate_accrues_nothing_and_is_counted(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px())                               # no BIL at all
    s = b.record("2026-07-29", _px(spy=606.0))
    assert s["cash_adj"]["book_accrued"] == 0.0                 # never assumed 0% *rate*
    assert s["cash_adj"]["rate_missing_days"] == 2
    assert "INCOMPLETE" in s["cash_adj"]["note"]                # the gap is announced


def test_first_day_has_no_prior_price_so_no_fabricated_accrual(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    s = b.record("2026-07-28", _px(bil=91.00))                  # BIL present but no PREV px
    assert s["cash_adj"]["book_accrued"] == 0.0
    assert s["cash_adj"]["rate_missing_days"] == 1              # honestly counted, not hidden


def test_accrual_resumes_after_a_missing_day_without_backfilling(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px(bil=91.00))
    b.record("2026-07-29", _px())                               # rate gap
    s = b.record("2026-07-30", _px(bil=91.02))
    assert s["cash_adj"]["rate_missing_days"] == 2              # the gap stays on the record
    assert s["cash_adj"]["book_accrued"] > 0                    # resumes, never backfills


# ---------- the twin is annotated too ----------
def test_twin_cash_is_annotated_on_the_same_basis(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", _px(bil=91.00))
    s = b.record("2026-07-29", _px(bil=91.01))
    assert "twin_accrued" in s["cash_adj"] and "twin_nav_cash_adj" in s["cash_adj"]
    assert s["cash_adj"]["twin_nav_cash_adj"] >= s["twin_nav"]


def test_fully_invested_book_accrues_little_or_nothing(tmp_path):
    """SPY-null is ~100% invested (fractional shares), so its cash drag is ~0 — the
    adjustment must scale with ACTUAL cash held, not be a blanket uplift."""
    b = LiveBook(SPY_NULL, root=str(tmp_path))
    b.record("2026-07-28", {"SPY": 600.0, CASH_RATE_TICKER: 91.00})
    s = b.record("2026-07-29", {"SPY": 606.0, CASH_RATE_TICKER: 91.01})
    assert abs(s["cash_adj"]["book_accrued"]) < 1.0             # cents on a $100k book
    q = LiveBook(QUALITY_SAT, root=str(tmp_path / "q"))
    q.record("2026-07-28", _px(bil=91.00))
    sq = q.record("2026-07-29", _px(bil=91.01))
    # the whole-share book leaves real cash idle, so its drag is strictly larger
    assert sq["cash_adj"]["book_accrued"] > s["cash_adj"]["book_accrued"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
