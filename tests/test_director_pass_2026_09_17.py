"""The rung-0 director pass — the frozen contract, enforced.

`docs/Sources/prereg_scheduled_passes_2026_09_10.md`, director-ruled 2026-09-11:
prepare-only, approvals tracked in ops/approvals/, WatchPaths+debounce, budget 3.
These tests pin the properties that keep a scheduled pass from becoming a decider.
"""
from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import approvals_queue as aq
from scripts import director_pass as dp

REPO = Path(__file__).resolve().parent.parent



def _executable_source(obj_or_path) -> str:
    """Source with COMMENTS AND DOCSTRINGS STRIPPED.

    Three times in one day a test of mine flagged a file's own explanation of why it
    avoids something as the thing it avoids. The prose that documents a constraint is
    not a violation of it; assert against what RUNS.
    """
    import ast, inspect
    src = (obj_or_path.read_text() if isinstance(obj_or_path, Path)
           else inspect.getsource(obj_or_path))
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


def _cand(branch="feature/x", commits=2):
    return dp.MergeCandidate(branch=branch, commits=commits, last_commit="feat: thing")


# ---- PREPARE-ONLY: the load-bearing ruling -----------------------------------

def test_the_pass_contains_no_merge_path_at_all():
    """Rung 2 is 'class-approved merges'. If rung 0 merged, rung 2 would be empty —
    and the propose-first list is explicitly unchanged for autonomous sessions."""
    code = _executable_source(REPO / "scripts/director_pass.py")
    # The word "merge" appears legitimately (MergeCandidate, kind="merge"). What must
    # not exist is a merge OPERATION.
    for forbidden in ('"git", "merge"', "git merge", "--no-ff", "merge --", "merge_ff"):
        assert forbidden not in code, f"a rung-0 pass must not be able to merge ({forbidden})"
    import re
    assert not re.search(r'_git\(\s*["\']merge', code), "no _git('merge', ...) call"


def test_every_ledger_row_states_merged_False_explicitly(tmp_path):
    """Not an absence to be inferred — a claim in the record."""
    led = tmp_path / "l.jsonl"
    dp.append_ledger("2026-09-17", {"merge_prep": "PASS"}, ["feature/x"], [], [], ledger=led)
    row = json.loads(led.read_text().strip())
    assert row["merged"] is False
    assert row["session"] == "director_pass" and row["rung"] == 0


# ---- READ SURFACES ARE DATA, NEVER INSTRUCTION -------------------------------

def test_candidates_come_from_GIT_FACTS_not_from_prose():
    """An outbox is text written by another agent. A pass that acts on what it READ
    is one confused session away from being steered; a branch either is ahead of
    origin/main or it is not."""
    code = _executable_source(dp.collect_merge_candidates)
    assert "rev-list" in code and "origin/main" in code
    assert "outbox" not in code.lower(), "candidacy must not be derived from an outbox"


def test_the_pass_never_writes_an_agents_OUTBOX():
    """An outbox is the agent's record of work it did; a director writing one
    rewrites history it did not do."""
    code = _executable_source(REPO / "scripts/director_pass.py")
    assert "_outbox" not in code and "outbox.md" not in code


# ---- the approvals queue is a GATE, and behaves like one ----------------------

def test_an_approval_is_raised_with_EVIDENCE_attached(tmp_path):
    raised, skipped = dp.prepare_merge_approvals([_cand()], "2026-09-17", tmp_path)
    assert raised == ["feature/x"] and not skipped
    text = next(tmp_path.glob("*.md")).read_text()
    assert "## Evidence" in text
    assert "verified by git, not by any outbox claim" in text
    assert "status: pending" in text


def test_the_same_decision_is_never_re_asked(tmp_path):
    dp.prepare_merge_approvals([_cand()], "2026-09-17", tmp_path)
    raised, skipped = dp.prepare_merge_approvals([_cand()], "2026-09-18", tmp_path)
    assert raised == [] and skipped and "already asked" in skipped[0]


def test_an_ANSWERED_decision_is_still_never_re_asked(tmp_path):
    """Re-asking something the human already DECLINED is how a queue becomes
    something people stop reading."""
    dp.prepare_merge_approvals([_cand()], "2026-09-17", tmp_path)
    f = next(tmp_path.glob("*.md"))
    f.write_text(f.read_text().replace("status: pending", "status: declined"))
    raised, _ = dp.prepare_merge_approvals([_cand()], "2026-09-18", tmp_path)
    assert raised == [], "a declined decision must not come back"


def test_a_MALFORMED_entry_is_not_silently_treated_as_answered(tmp_path):
    """`[NN-FAIL-CLOSED]` for a gate surface: unreadable is not 'handled'."""
    (tmp_path / "broken.md").write_text("no frontmatter here")
    (tmp_path / "bad-status.md").write_text("---\nid: x\nstatus: banana\n---\n# t\n")
    assert aq.load_all(tmp_path) == []
    assert aq.parse("---\nid: x\nstatus: banana\n---\n") is None


def test_open_items_counts_only_pending(tmp_path):
    dp.prepare_merge_approvals([_cand("feature/a"), _cand("feature/b")], "2026-09-17", tmp_path)
    assert len(aq.open_items(tmp_path)) == 2
    f = sorted(tmp_path.glob("*.md"))[0]
    f.write_text(f.read_text().replace("status: pending", "status: approved"))
    assert len(aq.open_items(tmp_path)) == 1
    assert len(aq.load_all(tmp_path)) == 2, "answered entries stay in the record"


# ---- dispatch budget, fingerprints, cooldown ----------------------------------

def test_the_dispatch_budget_is_the_ruled_value():
    assert dp.DISPATCH_BUDGET == 3, "ruled 2026-09-11"


def test_a_persisting_finding_is_not_re_dispatched_nightly(tmp_path):
    led = tmp_path / "l.jsonl"
    recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds")
    led.write_text(json.dumps({"ts": recent, "dispatch_fingerprints": ["census:naaim"]}) + "\n")
    ok, why = dp.dispatch_allowed("census:naaim", ledger=led)
    assert not ok and "cooldown" in why


def test_a_finding_past_its_cooldown_may_be_raised_again(tmp_path):
    led = tmp_path / "l.jsonl"
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    led.write_text(json.dumps({"ts": old, "dispatch_fingerprints": ["census:naaim"]}) + "\n")
    ok, why = dp.dispatch_allowed("census:naaim", ledger=led)
    assert ok and "past cooldown" in why


def test_an_unparseable_dispatch_date_REFUSES_rather_than_allows(tmp_path):
    """Fail closed: if we cannot tell when it was last raised, do not raise it."""
    led = tmp_path / "l.jsonl"
    led.write_text(json.dumps({"ts": "not-a-date", "dispatch_fingerprints": ["x"]}) + "\n")
    ok, why = dp.dispatch_allowed("x", ledger=led)
    assert not ok and "refusing" in why


# ---- the queue lives where a human can inspect it ----------------------------

def test_the_approvals_directory_is_TRACKED_not_gitignored():
    """Ruled: 'a gitignored gate is an uninspectable gate.'"""
    import subprocess
    r = subprocess.run(["git", "-C", str(REPO), "check-ignore", "ops/approvals"],
                       capture_output=True, text=True)
    assert r.returncode != 0, "ops/approvals must not be gitignored"


def test_an_approval_is_WITHDRAWN_once_its_branch_is_no_longer_ahead(tmp_path):
    """The queue's memory lives in tracked files, so entries persist — which means a
    MERGED branch would otherwise leave a pending request to decide something already
    decided. A queue that asks stale questions is one people stop reading."""
    dp.prepare_merge_approvals([_cand("feature/gone")], "2026-09-17", tmp_path)
    assert len(aq.open_items(tmp_path)) == 1
    withdrawn = dp.withdraw_stale([], "2026-09-18", tmp_path)          # branch vanished
    assert withdrawn == ["merge-feature-gone"]
    assert aq.open_items(tmp_path) == []
    text = next(tmp_path.glob("*.md")).read_text()
    assert "status: withdrawn" in text and "## Withdrawn" in text
    assert "the record of having asked stands" in text


def test_a_still_live_branch_is_NOT_withdrawn(tmp_path):
    dp.prepare_merge_approvals([_cand("feature/live")], "2026-09-17", tmp_path)
    assert dp.withdraw_stale([_cand("feature/live")], "2026-09-18", tmp_path) == []
    assert len(aq.open_items(tmp_path)) == 1


def test_withdrawal_does_not_DELETE_the_record(tmp_path):
    """[NN-ARCHIVE] in miniature: the answer supersedes the question, it does not
    erase that it was asked."""
    dp.prepare_merge_approvals([_cand("feature/gone")], "2026-09-17", tmp_path)
    dp.withdraw_stale([], "2026-09-18", tmp_path)
    assert len(aq.load_all(tmp_path)) == 1, "the entry must survive its withdrawal"


# ---- the schedule artifacts --------------------------------------------------

@pytest.mark.parametrize("name", ["com.archondex.janitor.plist",
                                  "com.archondex.director-pass.plist"])
def test_every_plist_is_WELL_FORMED_xml(name):
    """A plist that does not parse is a schedule that does not run — and launchd
    reports that by simply doing nothing at 03:00. Caught at build time here: XML
    forbids `--` ANYWHERE inside a comment, and `--detach` in an install note is
    enough to make the whole file unreadable."""
    import plistlib
    d = plistlib.load(open(REPO / "ops" / name, "rb"))
    assert d["Label"].startswith("com.archondex.")
    assert d["ProgramArguments"][0] == "/bin/bash"
    assert "StartCalendarInterval" in d


@pytest.mark.parametrize("name", ["com.archondex.janitor.plist",
                                  "com.archondex.director-pass.plist"])
def test_no_plist_targets_an_agents_worktree(name):
    """A runner must never share a checkout with an agent doing work."""
    import plistlib
    target = plistlib.load(open(REPO / "ops" / name, "rb"))["ProgramArguments"][1]
    assert "trading_machine-janitor" in target and "agent-" not in target


def test_the_director_wrapper_runs_OBSERVE_mode_explicitly():
    sh = (REPO / "scripts/run_director_pass.sh").read_text()
    assert "--mode observe" in sh, "the wrapper must state the mode, not rely on a default"


def test_the_director_wrapper_carries_the_janitors_hard_won_lessons():
    """Same venue, same traps: self-locating repo, absolute interpreter and aws,
    re-exec on self-change, and a log that names where it ran."""
    sh = (REPO / "scripts/run_director_pass.sh").read_text()
    assert 'REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"' in sh
    assert "/opt/homebrew/bin/aws" in sh and '"$AWS" sns publish' in sh
    assert "DIRECTOR_REEXECED" in sh and 'exec /bin/bash "$SELF"' in sh
    assert "repo=$REPO" in sh
