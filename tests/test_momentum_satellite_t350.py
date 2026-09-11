"""tests/test_momentum_satellite_t350.py — T-350.

The Act-2 rider: the MOMENTUM_SAT attribution book for E's deploy candidate
(VOO+MTUM+SGOV), plus the confirmation that a newly-added book inherits the standard
guards rather than needing them re-attached by hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.live_books import (  # noqa: E402
    ALL_BOOKS, CASH_RATE_TICKER, MOMENTUM_SAT, QUALITY_SAT, LiveBook)


def _px(mtum, spy, bil=100.0):
    return {"MTUM": mtum, "SPY": spy, CASH_RATE_TICKER: bil}


# ---------- the book ----------
def test_registered_and_satellite_only_against_a_spy_twin():
    assert MOMENTUM_SAT in ALL_BOOKS
    assert MOMENTUM_SAT.weights_fn({}, 0.0) == {"MTUM": 1.0}
    assert MOMENTUM_SAT.twin_weights_fn({}, 0.0) == {"SPY": 1.0}


def test_satellite_only_NOT_blended_like_the_quality_book():
    """The construction differs deliberately. QUALITY_SAT holds 80/20, so the tilt's own
    signal is diluted by its weight. The deploy account holds the core itself, so
    attribution is clean only if the book isolates the satellite."""
    assert set(QUALITY_SAT.weights_fn({}, 0.0)) == {"SPY", "QUAL"}     # blended
    assert set(MOMENTUM_SAT.weights_fn({}, 0.0)) == {"MTUM"}          # isolated


def test_the_gate_carries_T320s_bar_and_does_not_relitigate_it():
    g = MOMENTUM_SAT.gate
    assert "No promotion gate" in g and "attribution" in g.lower()
    assert "3.02" in g and "6.25" in g, "the decay must be quoted, not summarised away"


def test_cannot_evidence_names_the_regime_this_book_actually_lives_in():
    """The sharp point: T-320's significance rests on PRE-publication data and the decayed
    arm straddles — and the decayed arm is the present. A book that omitted this would read
    as if it were accruing toward a significant result."""
    c = MOMENTUM_SAT.cannot_evidence
    assert "PRE-publication" in c and "straddle" in c
    assert "short leg" in c, "the long-only/long-short distinction is load-bearing (T-320)"


# ---------- the guards are INHERITED, not re-attached ----------
def test_a_new_book_inherits_the_NOT_EVALUABLE_guard(tmp_path):
    """The guard lives on status(), which is what carries the can/cannot lines — a summary
    read without it is exactly the "short record read as a verdict" this prevents."""
    b = LiveBook(spec=MOMENTUM_SAT, root=str(tmp_path))
    b.record("2026-09-10", closes=_px(300.0, 760.0))
    st = b.status()
    assert "NOT EVALUABLE" in st["verdict"] and "days accrued" in st["verdict"]
    assert st["days_accrued"] == 1
    assert st["can_evidence"] and st["cannot_evidence"] and st["gate"]


def test_a_new_book_inherits_the_cash_drag_annotation(tmp_path):
    b = LiveBook(spec=MOMENTUM_SAT, root=str(tmp_path))
    b.record("2026-09-10", closes=_px(300.0, 760.0))
    b.record("2026-09-11", closes=_px(303.0, 764.0))
    d = b._state()["days"][-1]
    for k in ("cash_adj_book", "cash_adj_twin", "cash_rate_available"):
        assert k in d, f"{k} missing — the T-332a annotation must travel with every book"


def test_the_annotation_travels_WITH_the_raw_and_never_replaces_it(tmp_path):
    """T-332a's standing rule: raw records byte-unchanged; the annotation is additive."""
    b = LiveBook(spec=MOMENTUM_SAT, root=str(tmp_path))
    b.record("2026-09-10", closes=_px(300.0, 760.0))
    d = b._state()["days"][-1]
    assert d["book_nav"] > 0 and d["twin_nav"] > 0 and "excess_growth" in d


def test_the_twin_strands_more_cash_than_the_book_but_the_gap_is_NEGLIGIBLE(tmp_path):
    """The whole-share asymmetry, measured rather than assumed.

    A $762 SPY twin strands more residual cash than a $309 MTUM book — direction is
    structural. But at the book's actual $100k notional the stranded amounts are ~0.1% of
    notional, not the several percent a $10k notional would produce. Stating that
    plainly matters: the direction alone would invite treating the annotation as a
    material bias correction on this book, and at this notional it is not one. Holding
    SHARES rather than weights is deliberate — granularity must be VISIBLE — so a small
    nonzero cash_adj is the machinery working, not a defect."""
    b = LiveBook(spec=MOMENTUM_SAT, root=str(tmp_path))
    b.record("2026-09-10", closes=_px(309.29, 762.40))
    side = b._state()["side"]
    cash_book, cash_twin = side["book"]["cash"], side["twin"]["cash"]
    assert cash_twin > cash_book, "the pricier twin must strand more"
    for c in (cash_book, cash_twin):
        assert c < 0.01 * MOMENTUM_SAT.notional, (
            "at $100k notional the stranded residual is immaterial; if this ever exceeds "
            "1% the annotation has become a real correction and the notional needs a look")


def test_every_book_in_the_registry_declares_both_evidence_fields():
    """Covered-or-exempted, applied to books: a book without can/cannot is a number
    travelling without its framing."""
    for spec in ALL_BOOKS:
        assert spec.can_evidence.strip(), f"{spec.name} has no can_evidence"
        assert spec.cannot_evidence.strip(), f"{spec.name} has no cannot_evidence"
        assert spec.gate.strip(), f"{spec.name} has no gate"


# ---------- the class fix: a BookSpec alone is NOT the unit ----------
def test_every_live_book_is_durable_AND_clocked():
    """Adding a BookSpec is ~6 lines; shipping a BOOK is not.

    A LiveBook that is not in DURABLE_PATHS resets to a single point every run on the
    ephemeral Fargate disk — the T-238 class, which is why the sleeve tracker was made
    durable in the first place. One that has no rolled-clock stalls with nobody noticing.
    MOMENTUM_SAT had neither when its spec was first written, and the pulse iterates
    ALL_BOOKS automatically, so it would have run, evaporated, and looked fine.

    This is the covered-or-exempted pattern applied to books: the next one cannot be added
    without both halves."""
    from paper_trader.clock_census import REGISTRY as CLOCKS
    from paper_trader.cloud_state import DURABLE_PATHS
    clocked = {p for c in CLOCKS for p in c.covers}
    missing = {b.name: [half for half, ok in
                        (("durable", b.state_path in DURABLE_PATHS),
                         ("clocked", b.state_path in clocked)) if not ok]
               for b in ALL_BOOKS}
    missing = {k: v for k, v in missing.items() if v}
    assert not missing, f"books shipped without persistence and/or a clock: {missing}"
