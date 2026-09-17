# tests/test_tracker_framing_matches_the_book_t357.py
"""T-357 — a framing block that travels with the numbers must match THE BOOK.

Found on the live 2026-09-17 artifact. `deploy_candidate_tracking.json` carried
`sleeve_framing`:

    "honest_question": "what does the drawdown insurance COST, live? — NOT
                        'is the sleeve winning?'"
    "cannot_evidence": "that the sleeve 'beats' its twin on return … the sleeve
                        is a drawdown instrument"

on a book whose entire purpose is beating buy-and-hold SPY at the same tier.
Every sentence in it is true — about the trend sleeve. On the deploy candidate
it states the opposite of what the record is for.

The framing exists precisely so "this surface and A's digest cannot drift
apart". Attaching it unconditionally produced that drift in the surface it was
written to protect.
"""
from __future__ import annotations

from intelligence.analyst.performance_digest import DEPLOY_CANDIDATE_FRAMING
from paper_trader.live_books import SLEEVE_INSURANCE_FRAMING
from paper_trader.sleeve_tracker import SleeveTracker

POINT = dict(closes={"SPY": 754.05, "AGG": 95.81, "GLD": 391.74})


def _summary(tmp_path, strategy, path):
    t = SleeveTracker(path=path, root=str(tmp_path), strategy=strategy)
    return t.record("2026-09-17", sleeve_equity=100_434.77, **POINT)


def test_the_deploy_candidate_does_NOT_wear_the_sleeves_framing(tmp_path):
    """THE REGRESSION, from the live artifact."""
    s = _summary(tmp_path, "deploy_candidate", "data/state/deploy_candidate_tracking.json")
    assert "sleeve_framing" not in s, (
        "the deploy candidate is not a drawdown instrument — it must not carry "
        "the sleeve's can/cannot-evidence contract")
    assert s["deploy_candidate_framing"] == DEPLOY_CANDIDATE_FRAMING


def test_the_sleeve_keeps_its_own_framing_unchanged(tmp_path):
    """The fix must not strip the framing from the book it was written for."""
    s = _summary(tmp_path, "trend_sleeve", "data/state/sleeve_tracking.json")
    assert s["sleeve_framing"] == SLEEVE_INSURANCE_FRAMING
    assert "deploy_candidate_framing" not in s


def test_the_default_is_the_sleeve_so_existing_callers_are_byte_neutral(tmp_path):
    """Every other family tracker (btc_shadow, dbmf, offense, llm_analyst) still
    resolves to the sleeve framing exactly as before — this change must not
    quietly re-label four other records."""
    s = _summary(tmp_path, "trend_sleeve", "data/state/other_tracking.json")
    assert s["sleeve_framing"] == SLEEVE_INSURANCE_FRAMING


def test_the_framing_is_IMPORTED_not_retyped():
    """Two copies of a framing sentence is how a digest and a record start
    disagreeing — which is the defect this whole block exists to prevent."""
    import inspect

    import paper_trader.sleeve_tracker as st
    src = inspect.getsource(st._framing if hasattr(st, "_framing")
                            else st.SleeveTracker._framing)
    assert "import" in src and "DEPLOY_CANDIDATE_FRAMING" in src
    assert "drawdown insurance" not in src, "framing text was re-typed, not imported"
