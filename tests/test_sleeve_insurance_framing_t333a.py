"""T-333a — the sleeve records carry the INSURANCE-COST framing.

T-333 measured the sleeve's timing component as significantly value-destroying net of cash
in the modern era (−5.16pp/yr, CI excludes 0): the sleeve is a drawdown instrument bought
WITH return, priced precisely. So the honest question a live sleeve record answers is
"what does the drawdown insurance cost, live?" — NOT "is the sleeve winning?". A record
reading as the latter would mislead even though every number in it is correct.

These tests lock three things:
  1. the framing TRAVELS WITH the numbers (a doc does not);
  2. the RAW record is byte-unchanged — this is a framing field, like NOT-EVALUABLE;
  3. both surfaces import the SAME constant, so the wording cannot drift (and A's digest
     imports it too rather than re-typing it).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.live_books import (  # noqa: E402
    SLEEVE_HONEST_QUESTION, SLEEVE_INSURANCE_FRAMING, SLEEVE_TIER50K, SPY_NULL, LiveBook)
from paper_trader.sleeve_tracker import SleeveTracker  # noqa: E402


def _sleeve_px(spy=317.0, agg=93.0, gld=181.0, expo=1.0):
    return {"SPY": spy, "AGG": agg, "GLD": gld,
            "_sleeve_expo_SPY": expo, "_sleeve_expo_AGG": expo, "_sleeve_expo_GLD": expo}


# ---------- the framing says the right thing ----------
def test_the_honest_question_is_the_cost_not_the_win():
    q = SLEEVE_HONEST_QUESTION.lower()
    assert "cost" in q and "not 'is the sleeve winning?'" in q


def test_cannot_evidence_names_the_T333_measurement_and_normalizes_lagging():
    c = SLEEVE_INSURANCE_FRAMING["cannot_evidence"]
    assert "−5.16pp/yr" in c and "CI excludes 0" in c
    # the two directions a reader could misread a short record — both pre-empted
    assert "EXPECTED shape, not a failure" in c        # behind the twin ≠ broken
    assert "not a refutation of T-333" in c            # ahead briefly ≠ vindicated


def test_can_evidence_frames_the_record_as_a_PRICE():
    assert "PRICE" in SLEEVE_INSURANCE_FRAMING["can_evidence"]
    assert "drawdown it actually" in SLEEVE_INSURANCE_FRAMING["can_evidence"]


# ---------- it travels WITH the numbers, on both surfaces ----------
def test_tier_book_status_carries_the_framing(tmp_path):
    b = LiveBook(SLEEVE_TIER50K, root=str(tmp_path))
    b.record("2026-07-30", _sleeve_px())
    st = b.status()
    assert st["sleeve_framing"] == SLEEVE_INSURANCE_FRAMING     # the SAME object, not a copy
    assert "days_accrued" in st                                  # alongside the existing guard


def test_sleeve_tracker_summary_carries_the_framing(tmp_path):
    t = SleeveTracker(root=str(tmp_path))
    s = t.record("2026-07-30", 10_000.0, {"SPY": 600.0, "AGG": 98.0, "GLD": 180.0})
    assert s["sleeve_framing"] == SLEEVE_INSURANCE_FRAMING
    assert SLEEVE_HONEST_QUESTION == s["sleeve_framing"]["honest_question"]


def test_both_surfaces_share_ONE_constant_so_wording_cannot_drift(tmp_path):
    """The coordination mechanism: one importable constant, not prose copied twice."""
    b = LiveBook(SLEEVE_TIER50K, root=str(tmp_path))
    b.record("2026-07-30", _sleeve_px())
    t = SleeveTracker(root=str(tmp_path / "trk"))
    ts = t.record("2026-07-30", 10_000.0, {"SPY": 600.0, "AGG": 98.0, "GLD": 180.0})
    assert b.status()["sleeve_framing"] is ts["sleeve_framing"]  # identity, not equality


def test_tier_book_keeps_its_OWN_lesson_primary(tmp_path):
    """The T-333 guard is APPENDED — the granularity lesson this book exists for stays."""
    ce = SLEEVE_TIER50K.cannot_evidence
    assert "identical by" in ce and "granularity differs" in ce   # the original lesson
    assert "T-333" in ce                                          # plus the new guard


# ---------- non-sleeve books are NOT mislabeled ----------
def test_non_sleeve_books_do_not_carry_sleeve_framing(tmp_path):
    b = LiveBook(SPY_NULL, root=str(tmp_path))
    b.record("2026-07-30", {"SPY": 600.0})
    assert "sleeve_framing" not in b.status()


# ---------- THE LOCK: the raw record is untouched ----------
def test_raw_record_is_byte_unchanged_by_the_framing(tmp_path):
    b = LiveBook(SLEEVE_TIER50K, root=str(tmp_path))
    b.record("2026-07-30", _sleeve_px())
    day = b._state()["days"][-1]
    # framing lives in status()/summary() reporting — NEVER in the persisted day record
    assert "sleeve_framing" not in day
    assert "honest_question" not in day
    # and summary()'s numeric keys are untouched by it
    s = b.summary()
    assert "sleeve_framing" not in s          # summary stays numeric; status() carries framing
    assert s["book_nav"] == day["book_nav"]


def test_framing_never_replaces_a_number(tmp_path):
    t = SleeveTracker(root=str(tmp_path))
    s = t.record("2026-07-30", 12_345.67, {"SPY": 600.0, "AGG": 98.0, "GLD": 180.0})
    pt = [p for p in t._load() if p["date"] == "2026-07-30"][0]
    assert pt["sleeve_equity"] == 12_345.67   # the record is the record
    assert isinstance(s["sleeve_framing"], dict)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
