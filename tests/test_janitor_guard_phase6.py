"""The janitor's constitutional guard — Phase-6 rung 0.

These are the tests that make autonomous editing safe to switch on. The pilot's
exclusions (`docs/Core/autonomous_development_prestatement.md`) are enforced against
the DIFF, not requested in a prompt: a prompt is a request, and a session that
misreads it — or is steered by something it read during the run — produces a diff
nobody vetted.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.janitor_guard import ALLOWED_GLOBS, FORBIDDEN, classify

REPO = Path(__file__).resolve().parent.parent


# ---- the exclusions, clause by clause ---------------------------------------

@pytest.mark.parametrize("path,clause", [
    ("CLAUDE.md", "the gates themselves"),
    ("docs/Core/NON_NEGOTIABLES.md", "the gates themselves"),
    ("docs/Core/autonomous_development_prestatement.md", "the pilot's own constitution"),
    ("core/census.py", "the referee"),
    ("core/metrics_engine.py", "the referee"),
    ("core/measurement/mbl_gate.py", "the referee"),
    ("core/benchmark.py", "the referee"),
    ("paper_trader/clock_census.py", "the referee"),
    ("engines/engine_b_risk/risk_engine.py", "propose-first"),
    ("live_trader/oms.py", "propose-first"),
    ("requirements.txt", "propose-first: dependencies"),
    ("config/regime_settings.json", "frozen config"),
    ("data/governor/edge_weights.json", "[NN-NO-MANUAL-EDGES]"),
    ("cockpit/dashboard/app.py", "[NN-NO-EDIT-DASHBOARD]"),
])
def test_each_constitutional_exclusion_is_refused(path, clause):
    v = classify([path])
    assert not v.ok, f"{path} ({clause}) must be refused"
    assert v.violations and v.violations[0][0] == path


def test_the_guard_cannot_edit_its_own_exclusions():
    """Otherwise the first mechanical 'cleanup' could widen the guard."""
    assert not classify(["scripts/janitor_guard.py"]).ok


def test_the_gate_the_janitor_is_checked_BY_is_off_limits():
    assert not classify(["scripts/doc_lint.py"]).ok


# ---- all-or-nothing ---------------------------------------------------------

def test_ONE_forbidden_path_refuses_the_WHOLE_branch():
    """A session that reached for the referee is not then trusted on the rest of
    its diff — partial acceptance would launder exactly the judgment we distrust."""
    v = classify(["docs/State/health_check.md", "tests/test_x.py", "core/census.py"])
    assert not v.ok
    assert len(v.changed) == 3, "the whole diff is the unit of refusal"
    assert "REFUSED IN FULL" in v.report()


# ---- what IS allowed --------------------------------------------------------

def test_the_mechanical_classes_are_allowed():
    v = classify(["docs/State/health_check.md", "tests/test_foo.py",
                  "scripts/some_helper.py", "engines/engine_a_alpha/edges/x.py"])
    assert v.ok, v.report()


def test_a_path_outside_every_allowlist_is_refused_not_ignored():
    """Deny-by-default: an unfamiliar location is refused, not waved through."""
    v = classify(["some_new_top_level_dir/thing.py", "/etc/passwd"])
    assert not v.ok
    assert len(v.unclassified) == 2


def test_denylist_beats_allowlist_even_inside_an_allowed_tree():
    """core/ is broadly allowed; core/census.py is not. Deny must win."""
    assert any(g.startswith("core") for g in ALLOWED_GLOBS)
    assert not classify(["core/census.py"]).ok
    assert classify(["core/some_unrelated_helper.py"]).ok


# ---- the exclusions must stay traceable to the constitution ------------------

def test_every_forbidden_entry_carries_a_stated_reason():
    """An unexplained exclusion is one a future reader will delete."""
    for pattern, why in FORBIDDEN:
        assert why and len(why) > 8, pattern


def test_the_constitution_still_names_what_the_guard_enforces():
    """If the pre-statement is rewritten, this fails and the guard is re-derived
    rather than silently drifting from the document it implements."""
    doc = (REPO / "docs/Core/autonomous_development_prestatement.md").read_text()
    for phrase in ["The referee", "The gates themselves", "propose-first",
                   "WRITES TO THE APPROVALS QUEUE AND STOPS"]:
        assert phrase in doc, f"constitution no longer says {phrase!r} — re-derive the guard"
