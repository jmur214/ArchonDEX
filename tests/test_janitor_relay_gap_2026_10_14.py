"""relay_gap — every janitor row states WHICH TREE its checks certified (2026-10-14).

The finding: the runner verifies origin/main by design; the director merges into local
main and pushes wait for the user. Local main ran 65 commits ahead: the anchor lint never
ran at night, every "suite PASS" certified an older tree, and runner_canon read green.
This check is a STATEMENT — WARN when there is a gap, never FAIL.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from scripts import janitor_nightly as jn


def _fake_git(monkeypatch, *, ahead="0", behind="0", main="aaa1111", origin="aaa1111",
              head="aaa1111", fail=False):
    """Answer the five git questions relay_gap asks; anything else is a test bug."""
    answers = {
        ("rev-list", "--count", "origin/main..main"): ahead,
        ("rev-list", "--count", "main..origin/main"): behind,
        ("rev-parse", "--short", "main"): main,
        ("rev-parse", "--short", "origin/main"): origin,
        ("rev-parse", "--short", "HEAD"): head,
    }

    def run(cmd, cwd=None, timeout=None):
        assert cmd[0] == "git", cmd
        if fail:
            return subprocess.CompletedProcess(cmd, 128, "", "fatal: not a git repository")
        return subprocess.CompletedProcess(cmd, 0, answers[tuple(cmd[1:])] + "\n", "")

    monkeypatch.setattr(jn, "_run", run)


def test_a_gap_is_stated_as_WARN_naming_the_count_and_what_tonight_covered(monkeypatch):
    _fake_git(monkeypatch, ahead="65", main="e9bf070", origin="5d3af1e", head="5d3af1e")
    c = jn.check_relay_gap()
    assert c.ok and c.status == "WARN"
    assert "65 commit(s) AHEAD of origin/main 5d3af1e" in c.detail
    assert "NO nightly coverage until pushed" in c.detail
    assert "tonight covers origin only (the runner is at 5d3af1e)" in c.detail


def test_no_gap_is_a_plain_PASS(monkeypatch):
    _fake_git(monkeypatch)
    c = jn.check_relay_gap()
    assert c.status == "PASS" and "local main == origin/main" in c.detail


def test_a_runner_on_NEITHER_ref_is_stated_not_assumed(monkeypatch):
    """A refused sync leaves the runner behind both refs — 'covers origin' would lie."""
    _fake_git(monkeypatch, head="0ld0ld0")
    c = jn.check_relay_gap()
    assert c.status == "WARN" and "NEITHER origin/main nor local main" in c.detail


def test_origin_ahead_of_local_main_is_stated_too(monkeypatch):
    _fake_git(monkeypatch, behind="3", main="aaa1111", origin="bbb2222", head="bbb2222")
    c = jn.check_relay_gap()
    assert c.status == "WARN" and "3 commit(s) ahead of local main" in c.detail


def test_git_failure_is_UNKNOWN_WARN_never_a_silent_pass(monkeypatch):
    _fake_git(monkeypatch, fail=True)
    c = jn.check_relay_gap()
    assert c.ok and c.status == "WARN" and c.detail.startswith("UNKNOWN")


@pytest.mark.parametrize("ahead", ["0", "1", "65", "5000"])
def test_relay_gap_NEVER_fails(monkeypatch, ahead):
    """A statement, not a gate: the fix for a gap is to publish, not to fail the night."""
    _fake_git(monkeypatch, ahead=ahead, main="e9bf070", origin="5d3af1e", head="5d3af1e")
    assert jn.check_relay_gap().ok


def test_WARN_is_rendered_in_the_ledger_row_and_the_report(tmp_path, monkeypatch):
    """The row must say WARN — a gap rendered as PASS is the lie this check closes."""
    monkeypatch.setattr(jn, "REPORT", tmp_path / "janitor_report.md")
    monkeypatch.setattr(jn, "LEDGER", tmp_path / "autonomy_ledger.jsonl")
    checks = [jn.Check("relay_gap", True, "65 ahead", warn=True),
              jn.Check("suite", True, "ok"), jn.Check("doc_lint", False, "1 fail")]
    jn.write_report(checks, "checks-only", None, "2026-10-14")
    jn.append_ledger("2026-10-14", "manual", checks, "no changes", "checks_only")
    row = json.loads(jn.LEDGER.read_text().strip().splitlines()[-1])
    assert row["checks"] == {"relay_gap": "WARN", "suite": "PASS", "doc_lint": "FAIL"}
    assert "| relay_gap | WARN | 65 ahead |" in jn.REPORT.read_text()


def test_the_janitor_runs_relay_gap(monkeypatch):
    for name in [n for n in dir(jn) if n.startswith("check_")]:
        label = name[len("check_"):]
        monkeypatch.setattr(jn, name, lambda label=label: jn.Check(label, True, "stub"))
    assert "relay_gap" in [c.name for c in jn.run_checks()]


def test_on_the_real_repo_it_answers_without_raising():
    """Live smoke: whatever the gap is today, the check states it and never fails."""
    c = jn.check_relay_gap()
    assert c.ok and c.status in ("PASS", "WARN") and c.detail
