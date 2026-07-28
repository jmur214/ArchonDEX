"""T-328 — LiveBook: the four report-only NAV-vs-twin performance books.

Verifies the shared mechanics (shares+cash, whole-share granularity, costs, scale-free
growth comparison, fail-closed parking, idempotency, days-accrued always displayed) and
the per-book contracts (the SPY null is its own twin; the tier book's divergence IS the
whole-share lesson).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.live_books import (  # noqa: E402
    ALL_BOOKS, DAMPED_OFFENSE, QUALITY_SAT, SLEEVE_TIER50K, SPY_NULL, LiveBook)


def _sleeve_px(spy=100.0, agg=100.0, gld=100.0, expo=1.0):
    return {"SPY": spy, "AGG": agg, "GLD": gld,
            "_sleeve_expo_SPY": expo, "_sleeve_expo_AGG": expo, "_sleeve_expo_GLD": expo}


# ---------- the SPY null ----------
def test_spy_null_is_its_own_twin_so_excess_is_zero(tmp_path):
    b = LiveBook(SPY_NULL, root=str(tmp_path))
    b.record("2026-07-28", {"SPY": 600.0})
    s = b.record("2026-07-29", {"SPY": 660.0})
    assert s["book_growth"] == pytest.approx(s["twin_growth"])
    assert s["excess_growth"] == pytest.approx(0.0, abs=1e-9)
    assert s["book_growth"] > 1.0                       # +10% actually compounded


def test_spy_null_states_it_is_the_yardstick_not_a_contender(tmp_path):
    st = LiveBook(SPY_NULL, root=str(tmp_path)).status()
    assert "null" in st["gate"].lower()
    assert "yardstick" in st["cannot_evidence"]


# ---------- shared mechanics ----------
def test_days_accrued_displayed_and_verdict_never_premature(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    for i, px in enumerate([600.0, 606.0, 612.0]):
        b.record(f"2026-07-2{8+i}", {"SPY": px, "QUAL": 150.0})
    st = b.status()
    assert st["days_accrued"] == 3
    assert "NOT EVALUABLE" in st["verdict"] and "3 clean days" in st["verdict"]
    assert "cannot_evidence" in st and "CI straddled" in st["cannot_evidence"]


def test_fail_closed_parking_on_missing_price(tmp_path):
    b = LiveBook(QUALITY_SAT, root=str(tmp_path))
    b.record("2026-07-28", {"SPY": 600.0})              # QUAL missing
    d = b._state()["days"][-1]
    assert d["degraded"] is True and "missing prices" in d["reason"]
    assert b.summary()["days_accrued"] == 0             # a parked day never counts


def test_fail_closed_when_strategy_stance_unavailable(tmp_path):
    b = LiveBook(DAMPED_OFFENSE, root=str(tmp_path))
    b.record("2026-07-28", {"SSO": 100.0, "SPY": 600.0})   # no _offense_expo_SSO
    d = b._state()["days"][-1]
    assert d["degraded"] is True and "stance unavailable" in d["reason"]


def test_idempotent_per_date(tmp_path):
    b = LiveBook(SPY_NULL, root=str(tmp_path))
    b.record("2026-07-28", {"SPY": 600.0})
    b.record("2026-07-28", {"SPY": 600.0})
    assert len(b._state()["days"]) == 1


def test_costs_are_charged_on_rebalance(tmp_path):
    b = LiveBook(SPY_NULL, root=str(tmp_path))
    s = b.record("2026-07-28", {"SPY": 600.0})
    # the opening trade pays 1.5bps, so NAV starts marginally below the notional
    assert s["book_nav"] < SPY_NULL.notional
    assert s["book_nav"] > SPY_NULL.notional * 0.999


# ---------- the tier book: whole-share granularity IS the lesson ----------
def test_tier_book_holds_whole_shares_on_both_sides(tmp_path):
    b = LiveBook(SLEEVE_TIER50K, root=str(tmp_path))
    b.record("2026-07-28", _sleeve_px(spy=317.0, agg=93.0, gld=181.0))
    st = b._state()["side"]
    for side in ("book", "twin"):
        for q in st[side]["shares"].values():
            assert q == pytest.approx(round(q))          # integral share counts
    # the $10K twin necessarily holds fewer shares than the $50K book
    assert st["twin"]["shares"]["SPY"] < st["book"]["shares"]["SPY"]


def test_tier_divergence_is_scale_free_growth_not_raw_dollars(tmp_path):
    """The twin starts at a DIFFERENT notional ($10K vs $50K), so the comparison must be
    growth-vs-growth — a raw-dollar excess would be meaningless here."""
    b = LiveBook(SLEEVE_TIER50K, root=str(tmp_path))
    b.record("2026-07-28", _sleeve_px(spy=317.0, agg=93.0, gld=181.0))
    s = b.record("2026-07-29", _sleeve_px(spy=330.0, agg=93.0, gld=181.0))
    assert s["notional"] == 50_000.0 and s["twin_notional"] == 10_000.0
    assert s["book_nav"] > s["twin_nav"] * 4            # raw dollars differ ~5×…
    assert abs(s["excess_growth"]) < 0.05               # …but growth is comparable
    # the granularity drag is real and non-zero at these odd prices
    assert s["excess_growth"] != 0.0


def test_tier_book_declines_to_claim_a_better_tier(tmp_path):
    st = LiveBook(SLEEVE_TIER50K, root=str(tmp_path)).status()
    assert "identical by" in st["cannot_evidence"]      # same STRATEGY, only granularity differs
    assert "No promotion gate" in st["gate"]


# ---------- every book states its frozen contract ----------
@pytest.mark.parametrize("spec", ALL_BOOKS, ids=[s.name for s in ALL_BOOKS])
def test_every_book_declares_gate_and_evidence_limits(spec, tmp_path):
    st = LiveBook(spec, root=str(tmp_path)).status()
    assert spec.gate and spec.can_evidence and spec.cannot_evidence
    assert st["days_accrued"] == 0
    assert "NOT EVALUABLE" in st["verdict"]             # nothing is evaluable at t=0


def test_all_four_books_have_distinct_state_files(tmp_path):
    paths = {LiveBook(s, root=str(tmp_path))._file() for s in ALL_BOOKS}
    assert len(paths) == len(ALL_BOOKS)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
