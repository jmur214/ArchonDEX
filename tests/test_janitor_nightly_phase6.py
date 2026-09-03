"""The nightly janitor's own contract — Phase-6 rung 0."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import janitor_nightly as jn

REPO = Path(__file__).resolve().parent.parent


def test_interpreter_is_the_running_one_not_a_hardcoded_venv_path():
    """The bug the janitor's FIRST RUN found. The wrapper was hardened against
    bare-`python`; this module then hardcoded ROOT/.venv/bin/python and died on a
    worktree that has no venv. sys.executable is correct by construction."""
    assert jn.PY == sys.executable
    assert Path(jn.PY).exists(), "the interpreter must actually exist"
    src = (REPO / "scripts/janitor_nightly.py").read_text()
    assert '".venv/bin/python"' not in src, "no hardcoded venv path may return"


def test_the_fix_phase_is_OFF_unless_explicitly_asked_for():
    """Authority by record: the pilot's first nights are checks-only, and autonomous
    editing is a thing the director switches on, not a default."""
    import argparse, inspect
    src = inspect.getsource(jn.main)
    assert '"--fix", action="store_true"' in src
    assert "if a.fix and fixable:" in src, "the fix phase must be gated on the flag"


def test_the_janitor_never_merges():
    src = (REPO / "scripts/janitor_nightly.py").read_text()
    for forbidden in ["git\", \"merge", "'merge'", "git merge"]:
        assert forbidden not in src, f"the janitor must never merge ({forbidden})"


def test_a_failing_check_is_REPORTED_not_a_janitor_crash():
    """A red suite is the janitor doing its job. Non-zero rc is reserved for the
    janitor itself failing — otherwise every red test would page someone."""
    import inspect
    src = inspect.getsource(jn.main)
    assert "return 0" in src.split("append_ledger")[-1], "check failures must still exit 0"


def test_report_and_ledger_are_written_with_the_expected_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(jn, "REPORT", tmp_path / "janitor_report.md")
    monkeypatch.setattr(jn, "LEDGER", tmp_path / "autonomy_ledger.jsonl")
    checks = [jn.Check("suite", True, "3000 passed"), jn.Check("doc_lint", False, "1 fail", mechanical=True)]
    jn.write_report(checks, "fix phase DISABLED", None, "2026-08-27")
    jn.append_ledger("2026-08-27", "nightly_schedule", checks, "no changes", "checks_only")

    report = (tmp_path / "janitor_report.md").read_text()
    assert "2026-08-27" in report and "suite" in report and "PASS" in report and "FAIL" in report
    assert "janitor_ran_nightly" in report, "the report must name the clock that watches it"

    row = json.loads((tmp_path / "autonomy_ledger.jsonl").read_text().strip())
    for k in ("ts", "as_of", "session", "rung", "trigger", "checks", "diff_summary", "outcome"):
        assert k in row, f"ledger row missing {k} — the record is what enables demotion"
    assert row["rung"] == 0 and row["checks"]["doc_lint"] == "FAIL"


def test_the_report_surface_is_the_one_the_clock_watches():
    """A report written somewhere the clock does not look is an unwatched promise."""
    from paper_trader.clock_census import REGISTRY
    clock = next(c for c in REGISTRY if c.name == "janitor_ran_nightly")
    watched = set(clock.covers)
    assert str(jn.REPORT.relative_to(REPO)) in watched, watched
