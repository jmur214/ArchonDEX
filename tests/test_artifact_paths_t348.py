"""tests/test_artifact_paths_t348.py — T-348.

The analyst-note clock could NEVER advance: it matched `<as_of>*.json` while the pulse
writes `note_<as_of>.json`. Third instance of one disease — a reader encoding a writer's
naming independently of the writer (T-331 eval harness, T-346 news clock, this).

These tests lock the instance AND the class: the naming is declared once, writer and
reader derive from it, and nothing may spell it a fourth time.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intelligence.analyst.eval_harness import NOTE_GLOBS  # noqa: E402
from paper_trader.artifact_paths import (  # noqa: E402
    ANALYST_NOTE, ANALYST_NOTE_AGENTIC, REGISTRY)
from paper_trader.clock_census import ADVANCED, MISS, _analyst_note  # noqa: E402
from paper_trader.cloud_state import DURABLE_PATHS  # noqa: E402


def _notes(root: Path, day: str, *, constrained=True, agentic=True, name="note_{d}.json"):
    for keep, art in ((constrained, ANALYST_NOTE), (agentic, ANALYST_NOTE_AGENTIC)):
        d = root / art.directory
        d.mkdir(parents=True, exist_ok=True)
        if keep:
            (d / name.format(d=day)).write_text("{}")
    return root


# ---------- the instance ----------
def test_the_clock_advances_on_the_name_the_pulse_ACTUALLY_writes(tmp_path):
    """The regression that could not have passed before: the real files are named
    `note_<date>.json`, and the clock matched `<date>*.json`."""
    r = _analyst_note(_notes(tmp_path, "2026-08-28"), "2026-08-28")
    assert r.status == ADVANCED, r.detail


def test_the_old_pattern_would_have_failed_this_fixture(tmp_path):
    """Pins WHY it was broken, so nobody 'simplifies' the fix back into the bug."""
    _notes(tmp_path, "2026-08-28")
    d = tmp_path / ANALYST_NOTE.directory
    assert not any(f.name.startswith("2026-08-28") for f in d.glob("*.json"))
    assert any(f.name == "note_2026-08-28.json" for f in d.glob("*.json"))


def test_the_archived_spelling_is_still_readable(tmp_path):
    """T-331 kept the older `analyst_note_<date>.json` readable; that must survive."""
    r = _analyst_note(_notes(tmp_path, "2026-08-28", name="analyst_note_{d}.json"),
                      "2026-08-28")
    assert r.status == ADVANCED


def test_a_genuinely_missing_note_still_misses_and_names_the_side(tmp_path):
    """The false alarm HID a real miss (no constrained note for 2026-08-27). Once the
    clock can advance, a true miss has to remain visible — and say which side."""
    r = _analyst_note(_notes(tmp_path, "2026-08-27", constrained=False), "2026-08-27")
    assert r.status == MISS and "constrained" in r.detail and "agentic" not in r.detail


def test_the_real_2026_08_27_gap_reproduces(tmp_path):
    """Mirrors the actual S3 state: agentic has 08-27, constrained does not."""
    _notes(tmp_path, "2026-08-26")
    _notes(tmp_path, "2026-08-27", constrained=False)
    _notes(tmp_path, "2026-08-28")
    assert _analyst_note(tmp_path, "2026-08-26").status == ADVANCED
    assert _analyst_note(tmp_path, "2026-08-27").status == MISS
    assert _analyst_note(tmp_path, "2026-08-28").status == ADVANCED


# ---------- the class ----------
def test_writer_and_reader_derive_from_the_SAME_declaration(tmp_path):
    """THE class-fix assertion: the path the pulse writes is byte-identical to the one
    the census looks for, because both come from one object."""
    written = ANALYST_NOTE.path_for(tmp_path, "2026-08-28")
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text("{}")
    (tmp_path / ANALYST_NOTE_AGENTIC.directory).mkdir(parents=True, exist_ok=True)
    ANALYST_NOTE_AGENTIC.path_for(tmp_path, "2026-08-28").write_text("{}")
    assert _analyst_note(tmp_path, "2026-08-28").status == ADVANCED


def test_the_pulse_writes_through_the_declaration_not_a_literal():
    """If the writer goes back to spelling the name inline, the drift can recur."""
    src = (ROOT / "paper_trader/intel_pulse.py").read_text()
    assert "ANALYST_NOTE.path_for" in src and "ANALYST_NOTE_AGENTIC.path_for" in src
    assert 'f"note_{as_of_s}.json"' not in src


def test_the_eval_harness_globs_come_from_the_declaration():
    """The harness was the FIRST instance of this drift (T-331) — it is the last place
    that should keep a private copy of the spelling."""
    assert tuple(NOTE_GLOBS) == ANALYST_NOTE.globs()


def test_no_module_spells_a_note_filename_outside_the_declaration():
    """The class lock: a fourth spelling cannot be introduced quietly. Anything that
    needs the name must import it."""
    pat = re.compile(r'["\']((?:analyst_)?note_)\{|["\'](?:analyst_)?note_\*')
    offenders = []
    for d in ("paper_trader", "intelligence", "scripts"):
        for f in sorted((ROOT / d).rglob("*.py")):
            if f.name == "artifact_paths.py":
                continue
            txt = f.read_text()
            if pat.search(txt) and "artifact_paths" not in txt:
                offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, (
        f"these spell a note filename without importing the declaration: {offenders}")


def test_the_registry_is_keyed_and_non_empty():
    assert REGISTRY and all(k == a.key for k, a in REGISTRY.items())


# ---------- the doc surfaces round-trip ----------
def test_the_rendered_doc_surfaces_are_durable():
    """The T-344 Friday step writes the digest INSIDE the container and pushes it for
    archival, but nothing pulled it BACK — so the census read whatever copy was baked
    into the git image rather than what the step wrote. A clock measuring a proxy for
    the event instead of the event is the same defect one layer up."""
    for rel in ("docs/State/performance_digest.md", "docs/State/advisor_surface.md"):
        assert rel in DURABLE_PATHS, f"{rel} evaporates when the container exits"


def test_durable_doc_paths_are_covered_by_a_clock():
    """Covered-or-exempted still holds for the paths just made durable."""
    from paper_trader.clock_census import REGISTRY as CLOCKS
    covered = {p for c in CLOCKS for p in c.covers}
    for rel in ("docs/State/performance_digest.md", "docs/State/advisor_surface.md"):
        assert rel in covered
