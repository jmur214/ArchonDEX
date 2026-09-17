"""T-2026-09-16-356 — the durability census tripwire.

C's T-351 tripwire closed the two registries C owns (ALL_BOOKS + the pulse's family
trackers). This closes the rest of the class: a NEW writer of an accruing record cannot
ship without being durable, exempted-with-a-reason, or an OWNED known gap.

The load-bearing tests are the ones proven BY REVERSION — a text assertion that some
line exists proves nothing (the 2026-09-14 lesson: 53 green tests passed on a broken
line because they read source text instead of executing it). These drive the real
scanner against the real tree.
"""
from __future__ import annotations

import pytest

from core.durability_census import (
    EXEMPT,
    INPUT,
    KNOWN_GAP,
    REGISTRY,
    VENUES,
    assert_durability,
    open_gaps,
    scan_writers,
)


def test_the_scan_finds_writers_so_nothing_here_can_pass_vacuously():
    """The guard against a green suite that checked nothing — the failure mode behind
    every 'passing tests, broken integration' finding in this program."""
    written = scan_writers()
    assert len(written) >= 20, f"scanner found only {len(written)} paths — it is broken"
    assert "data/state/paper_heartbeat.json" in written
    assert "data/state/autonomy_ledger.jsonl" not in written, (
        "scripts/ is deliberately out of the swept venues; the janitor's ledger is "
        "carried by the REGISTRY instead — if that changed, the registry entry is stale")


def test_the_census_is_green_on_the_current_tree():
    v = assert_durability()
    assert v.ok, "unclassified writer(s):\n  " + "\n  ".join(v.failures)


def test_every_registry_entry_states_a_reason():
    """'It exists' is what kept a dead launchd job alive for six weeks."""
    for r in REGISTRY:
        assert r.reason.strip(), f"{r.path}: no reason stated"
        assert len(r.reason) > 40, f"{r.path}: reason too thin to be a reason"
        assert r.venue in VENUES, f"{r.path}: bad venue {r.venue!r}"


def test_every_known_gap_carries_an_owner():
    """An unowned gap goes quiet — the supersession-dependents failure, one layer over."""
    for r in open_gaps():
        assert r.owner.strip(), f"{r.path}: KNOWN_GAP with no owner"
        assert "T-356" in r.reason, f"{r.path}: gap not traceable to its finding"


def test_the_findings_are_on_the_record_and_closures_are_EXPLICIT():
    """The sweep's output, locked so a later edit cannot quietly drop a gap.

    T-355 closed finding #5 (`agentic_analyst_calls.jsonl`) by RETIRING its
    consumer rather than adding a writer. This lock objected to that edit, which
    is the lock working: a gap may leave this set only by being resolved on the
    record, never by being deleted from it. The closed one is asserted BELOW, so
    the count going 5 → 4 is a statement, not an omission."""
    gaps = {r.path for r in open_gaps()}
    assert gaps == {
        "data/state/autonomy_ledger.jsonl",
        "data/governor/lifecycle_history.csv",
        "data/governor/feedback_history.log",
        "data/research/discovery_log.jsonl",
    }, f"the recorded gap set changed: {sorted(gaps)}"


def test_finding_5_is_CLOSED_by_retirement_and_says_so():
    """Closed, with the mechanism stated — and closed the RIGHT way. Adding a
    writer for a feed the agentic arm never emits would have manufactured a live
    channel to satisfy a check; retiring the consumer that could not be fed is
    the honest resolution, and the arm is booked by LlmShadowBook instead."""
    rec = next(r for r in REGISTRY
               if r.path == "data/intel/agentic_analyst_calls.jsonl")
    assert rec.status == "EXEMPT", "finding #5 must be CLOSED, not silently dropped"
    assert "T-355" in rec.reason and "RETIRE" in rec.reason.upper()
    assert "llm_shadow_book_agentic" in rec.reason, (
        "a retirement must name what covers the need instead, or it reads as "
        "abandoning the measurement")


def test_the_authority_record_gap_is_stated_as_a_DIFFERENT_failure_than_C_found():
    """The finding is only useful if its mechanism is precise. The janitor runs LOCALLY,
    so it does not suffer C's nightly evaporation; its exposure is single-copy loss."""
    led = next(r for r in open_gaps() if r.path.endswith("autonomy_ledger.jsonl"))
    assert led.venue == "local"
    assert "single" in led.reason.lower() or "one copy" in led.reason.lower()
    assert "T-337" in led.reason, "the gap must name the class it belongs to"


# --------------------------------------------------------------------------------------
# PROOF BY REVERSION — the tests that would fail if the guard stopped guarding
# --------------------------------------------------------------------------------------
def test_an_unregistered_new_writer_FAILS(tmp_path):
    """THE TRIPWIRE. A new module writing an accruing record it never registered must
    fail the census — this is the whole point of the unit."""
    import core.durability_census as dc

    pkg = tmp_path / "paper_trader"
    pkg.mkdir()
    (pkg / "brand_new_tracker.py").write_text(
        'import json\nP = "data/state/brand_new_forward_record.jsonl"\n'
        'def save(x):\n    json.dump(x, open(P, "a"))\n')
    for d in ("engines", "core", "intelligence"):
        (tmp_path / d).mkdir()

    found = dc.scan_writers(tmp_path)
    assert "data/state/brand_new_forward_record.jsonl" in found

    v = dc.assert_durability(tmp_path)
    assert not v.ok, "an unregistered writer passed — the tripwire is inert"
    assert any("brand_new_forward_record" in f for f in v.failures)
    assert any("UNREGISTERED WRITER" in f for f in v.failures)


def test_a_reasonless_exemption_FAILS(monkeypatch):
    """Reversion on the reason rule: strip a reason, the census must refuse."""
    import core.durability_census as dc
    from dataclasses import replace

    bad = tuple(replace(r, reason="") if r.status == EXEMPT else r for r in dc.REGISTRY)
    monkeypatch.setattr(dc, "REGISTRY", bad)
    v = dc.assert_durability()
    assert not v.ok
    assert any("no stated reason" in f for f in v.failures)


def test_an_unowned_gap_FAILS(monkeypatch):
    import core.durability_census as dc
    from dataclasses import replace

    bad = tuple(replace(r, owner="") if r.status == KNOWN_GAP else r for r in dc.REGISTRY)
    monkeypatch.setattr(dc, "REGISTRY", bad)
    v = dc.assert_durability()
    assert not v.ok
    assert any("no owner" in f for f in v.failures)


def test_a_stale_registry_entry_FAILS(monkeypatch):
    """BIDIRECTIONAL, per B's launchd sweep: a registry describing a world that moved is
    itself a fault. A one-directional check catches zombies and misses outages."""
    import core.durability_census as dc
    from dataclasses import replace

    bad = tuple(
        replace(r, writer="engines/engine_z_nonexistent/ghost.py")
        if r.path.endswith("edge_weights.json") else r
        for r in dc.REGISTRY)
    monkeypatch.setattr(dc, "REGISTRY", bad)
    v = dc.assert_durability()
    assert not v.ok
    assert any("STALE REGISTRY ENTRY" in f for f in v.failures)


def test_the_census_never_writes(tmp_path):
    """Read-only, like the clock census. A guard that mutates state is not a guard."""
    import core.durability_census as dc

    for d in ("paper_trader", "engines", "core", "intelligence"):
        (tmp_path / d).mkdir()
    before = set(p for p in tmp_path.rglob("*"))
    dc.assert_durability(tmp_path)
    assert set(p for p in tmp_path.rglob("*")) == before, "the census wrote something"


@pytest.mark.parametrize("status", [EXEMPT, INPUT, KNOWN_GAP])
def test_each_status_is_actually_used(status):
    """A status nobody uses is dead vocabulary that invites misuse later."""
    assert any(r.status == status for r in REGISTRY), f"{status} unused"
