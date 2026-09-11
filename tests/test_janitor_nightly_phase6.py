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


def test_the_janitor_does_not_flag_its_OWN_artifacts_as_a_dirty_worktree(monkeypatch):
    """It writes the report and the ledger, then checks whether the worktree is
    clean. Counting its own output would fail worktree_canon EVERY night over a file
    it just wrote — a permanent false alarm, the alarm-fatigue anti-pattern this
    program keeps closing. (Found by reading the janitor's own first report.)"""
    porcelain = (" M data/state/janitor_report.md\n"
                 " M data/state/autonomy_ledger.jsonl\n")

    class _R:
        def __init__(self, out): self.stdout = out; self.returncode = 0

    def fake_run(cmd, **kw):
        return _R(porcelain if "status" in cmd else "0")

    monkeypatch.setattr(jn, "_run", fake_run)
    c = jn.check_worktree_canon()
    assert c.ok, f"the janitor's own artifacts must not count as dirt: {c.detail}"

    porcelain += " M engines/engine_a_alpha/something.py\n"
    c2 = jn.check_worktree_canon()
    assert not c2.ok and "something.py" in c2.detail, "real dirt must still be reported"


def test_runner_canon_flags_a_non_canonical_checkout(monkeypatch):
    """The pilot's mechanics put the runner in a SHARED worktree, so for the first
    nine nights the nightly job executed whatever feature branch an agent had left
    checked out. The results were not wrong — they were about the wrong tree, which
    is worse, because nothing said so. Every ledger row must now record whether that
    night was canonical."""
    def fake_run(cmd, **kw):
        class _R: returncode = 0
        r = _R()
        if "rev-parse" in cmd:
            r.stdout = "a" * 40 if cmd[-1] == "HEAD" else "b" * 40
        elif "rev-list" in cmd:
            r.stdout = "3"
        elif "--show-current" in cmd:
            r.stdout = "feature/whatever"
        else:
            r.stdout = ""
        return r
    monkeypatch.setattr(jn, "_run", fake_run)
    c = jn.check_runner_canon()
    assert not c.ok
    assert "feature/whatever" in c.detail and "not main" in c.detail


def test_runner_canon_passes_when_HEAD_equals_origin_main(monkeypatch):
    def fake_run(cmd, **kw):
        class _R: returncode = 0
        r = _R(); r.stdout = "c" * 40 if "rev-parse" in cmd else ""
        return r
    monkeypatch.setattr(jn, "_run", fake_run)
    c = jn.check_runner_canon()
    assert c.ok and "canonical" in c.detail


def test_runner_canon_is_REPORTED_not_fatal():
    """A refusal would alarm every night an agent is mid-task — which is most of
    them. Alarm fatigue is the failure this program keeps closing."""
    import inspect
    src = inspect.getsource(jn.check_runner_canon)
    assert "raise" not in src and "sys.exit" not in src
    assert "check_runner_canon()" in inspect.getsource(jn.run_checks)

# ---- the runner VENUE (2026-09-10): a runner must not share a checkout ---------

def test_the_wrapper_is_SELF_LOCATING_not_pinned_to_an_agent_worktree():
    """A wrapper that hardcodes a worktree IS the venue bug in miniature — the path
    was baked in, so the nightly job ran against whatever branch an agent left
    checked out."""
    sh = (REPO / "scripts/run_janitor_nightly.sh").read_text()
    assert 'REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"' in sh
    assert "trading_machine-agent-b" not in sh, "no agent worktree may be hardcoded"


def test_the_wrapper_syncs_to_origin_main_WITHOUT_a_denylisted_reset():
    sh = (REPO / "scripts/run_janitor_nightly.sh").read_text()
    assert "git checkout --detach origin/main" in sh
    # Strip comments first: the file EXPLAINS why reset --hard is avoided, and a
    # naive grep flags the explanation as the offence.
    code = "\n".join(l for l in sh.splitlines() if not l.lstrip().startswith("#"))
    assert "reset --hard" not in code, "reset --hard is deny-listed; checkout --detach is the move"


def test_the_sync_REFUSES_on_a_dirty_tree_rather_than_clobbering():
    """Only safe in a DEDICATED runner worktree. If the tree is dirty it is not a
    clean runner venue, and the run proceeds on the old checkout with runner_canon
    recording exactly that."""
    sh = (REPO / "scripts/run_janitor_nightly.sh").read_text()
    assert 'if [ -z "$(git status --porcelain)" ]; then' in sh
    assert "JANITOR_SYNC_SKIPPED" in sh


def test_runtime_artifacts_live_in_the_GITIGNORED_tree():
    """A TRACKED report makes the runner dirty on every run, so the nightly re-sync
    could never succeed. The venue fix and the artifact location are one problem."""
    assert jn.REPORT.parts[-3:] == ("data", "state", "janitor_report.md"), jn.REPORT
    assert jn.LEDGER.parent == jn.REPORT.parent, "record and report belong together"
    assert str(jn.REPORT.relative_to(REPO)) in jn.SELF_WRITTEN


def test_the_clock_watches_where_the_report_ACTUALLY_lands():
    """Moving an artifact without moving its clock is how a watched promise goes
    quietly unwatched."""
    from paper_trader.clock_census import REGISTRY
    clock = next(c for c in REGISTRY if c.name == "janitor_ran_nightly")
    assert str(jn.REPORT.relative_to(REPO)) in set(clock.covers), clock.covers


def test_the_plist_targets_the_dedicated_runner_not_an_agent_worktree():
    import plistlib
    d = plistlib.load(open(REPO / "ops/com.archondex.janitor.plist", "rb"))
    target = d["ProgramArguments"][1]
    assert "trading_machine-janitor" in target, target
    assert "agent-" not in target, "the runner must not be an agent's worktree"


def test_the_wrapper_RECORDS_which_tree_it_ran_in():
    """The venue defect was invisible for nine nights precisely because nothing
    recorded which tree the job used. The log must answer "where did this run?" on
    its own, without reconstructing what branch was checked out that night."""
    sh = (REPO / "scripts/run_janitor_nightly.sh").read_text()
    assert 'repo=$REPO' in sh, "the log must name the repo it resolved to"
    assert "rev-parse --short HEAD" in sh, "and the commit it ran"


def test_the_bootstrap_requirement_is_written_down_where_it_bites():
    """A self-syncing wrapper cannot bootstrap itself: the sync only runs if the
    ALREADY-CHECKED-OUT wrapper contains it. Creating the runner without a manual
    first advance reproduces the venue defect wearing the fix's clothes — this
    nearly cost a night's observation and must not depend on someone remembering."""
    sh = (REPO / "scripts/run_janitor_nightly.sh").read_text()
    assert "BOOTSTRAP" in sh
    assert "checkout --detach origin/main" in sh
    assert "cannot bootstrap itself" in sh
