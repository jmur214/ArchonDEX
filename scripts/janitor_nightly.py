"""The nightly janitor — Phase-6 rung 0 (autonomous development pilot).

Per `docs/Core/autonomous_development_prestatement.md`: a scheduled nightly session
that runs the suite + doc_lint + census review + worktree-canon checks, fixes ONLY
mechanical classes on a branch, opens a merge request to the director pass, and
NEVER merges itself.

WHAT MAKES THIS SAFE IS NOT THE PROMPT. The fix phase runs a headless `claude -p`
session, and a prompt is a request, not a gate. So every diff it produces is vetted
mechanically by `scripts/janitor_guard.py` against the constitution's exclusions —
the referee, the gates, the propose-first list — and a branch touching any of them is
REFUSED IN FULL before anything is offered for merge. The guard is on its own denylist.

TWO PHASES, SEPARATELY AUTHORIZED:
  * CHECKS (always) — read-only. Produces the nightly report, the autonomy-ledger row,
    and the merge request. Cannot modify the repo.
  * FIX (`--fix`, opt-in) — the autonomous edit phase. Off by default so the pilot's
    first nights establish the record before any autonomous edit happens; the director
    turns it on with the checks' record in hand (authority by record, per the ladder).

Cadence: nightly. Watched by the `janitor_ran_nightly` clock — a silent janitor alarms
like any dead feed (the census watches the watchmen).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.janitor_guard import vet_branch                      # noqa: E402

REPORT = ROOT / "docs/State/janitor_report.md"
LEDGER = ROOT / "data/state/autonomy_ledger.jsonl"
MERGE_REQUESTS = ROOT / "data/coordination/janitor_merge_requests.md"
# THE INTERPRETER. Never a bare `python` (launchd has no PATH), and never a
# hardcoded ROOT/.venv either: worktrees do not each carry a venv, and this module
# ran first on a worktree that has none — the same interpreter-resolution class the
# WRAPPER was already hardened against, reintroduced one layer down. sys.executable
# is the interpreter already running us, so it is correct by construction in every
# worktree, venv, and launchd context. (Caught by the janitor's own first run:
# 22 tests green, integration dead on first contact — `[NN-FIRST-ARTIFACT]`.)
PY = sys.executable
FAST_SUITE = ["-q", "-p", "no:randomly", "-m", "not slow"]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    mechanical: bool = False        # is this a class the janitor may fix?


def _run(cmd: List[str], cwd: Path = ROOT, timeout: int = 3600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


# ── the checks ─────────────────────────────────────────────────────────────────

def check_suite() -> Check:
    r = _run([PY, "-m", "pytest", *FAST_SUITE])
    tail = (r.stdout or r.stderr).strip().splitlines()
    summary = next((l for l in reversed(tail) if "passed" in l or "failed" in l), "no summary")
    return Check("suite", r.returncode == 0, summary, mechanical=False)


def check_doc_lint() -> Check:
    r = _run([PY, "scripts/doc_lint.py"])
    fails = [l for l in (r.stdout or "").splitlines() if l.startswith("[FAIL")]
    return Check("doc_lint", r.returncode == 0,
                 "; ".join(fails) if fails else "all doc-lint checks pass",
                 mechanical=True)          # doc drift IS a mechanical class


def check_census() -> Check:
    """Read-only census review. The census is the referee — the janitor READS it and
    never edits it (clock_census.py is on the guard's denylist)."""
    r = _run([PY, "-c",
              "import sys;sys.path.insert(0,'.');"
              "from paper_trader.clock_census import REGISTRY;"
              "print(f'{len(REGISTRY)} clocks registered')"])
    return Check("census_review", r.returncode == 0,
                 (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "no output")


def check_worktree_canon() -> Check:
    """Worktree hygiene: is this worktree clean and based on a known origin/main?"""
    dirty = _run(["git", "status", "--porcelain"]).stdout.strip()
    behind = _run(["git", "rev-list", "--count", "HEAD..origin/main"]).stdout.strip() or "?"
    ok = (dirty == "")
    detail = "clean" if ok else f"{len(dirty.splitlines())} uncommitted path(s)"
    return Check("worktree_canon", ok, f"{detail}; {behind} commit(s) behind origin/main")


def run_checks() -> List[Check]:
    return [check_worktree_canon(), check_doc_lint(), check_census(), check_suite()]


# ── the record ─────────────────────────────────────────────────────────────────

def write_report(checks: List[Check], guard_note: str, branch: Optional[str], as_of: str) -> None:
    lines = [f"# Janitor nightly report — {as_of}", "",
             "Rung-0 autonomous pilot (`docs/Core/autonomous_development_prestatement.md`). "
             "This surface is watched by the `janitor_ran_nightly` clock: if it stops being "
             "written, the census alarms like any dead feed.", "",
             "| check | result | detail |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c.name} | {'PASS' if c.ok else 'FAIL'} | {c.detail} |")
    lines += ["", f"**Fix phase:** {guard_note}", ""]
    if branch:
        lines.append(f"**Branch offered for merge:** `{branch}` — the janitor NEVER merges; "
                     f"the director pass decides.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")


def append_ledger(as_of: str, trigger: str, checks: List[Check],
                  diff_summary: str, outcome: str) -> None:
    """The autonomy ledger — every autonomous action, so the stream can be SCORED and
    a bad class DEMOTED (symmetric, no ratchet)."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of, "session": "janitor_nightly", "rung": 0, "trigger": trigger,
        "checks": {c.name: ("PASS" if c.ok else "FAIL") for c in checks},
        "diff_summary": diff_summary, "outcome": outcome,
    }
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")


def open_merge_request(branch: str, as_of: str, checks: List[Check], diff_summary: str) -> None:
    MERGE_REQUESTS.parent.mkdir(parents=True, exist_ok=True)
    entry = [f"\n## 🧹 JANITOR MERGE REQUEST — {as_of} — branch `{branch}`", "",
             f"Mechanical fixes only, vetted by the constitutional guard. {diff_summary}", "",
             "| check | result | detail |", "|---|---|---|"]
    for c in checks:
        entry.append(f"| {c.name} | {'PASS' if c.ok else 'FAIL'} | {c.detail} |")
    entry.append("\nThe janitor does not merge. Review and merge, or close with a reason.\n")
    with open(MERGE_REQUESTS, "a") as f:
        f.write("\n".join(entry))


# ── the fix phase (opt-in) ─────────────────────────────────────────────────────

FIX_PROMPT = """You are the ArchonDEX nightly janitor (Phase-6 rung 0).

Fix ONLY mechanical problems from the findings below. Mechanical means: documentation
drift, stale cross-references or pointers, imports broken by a merge, and obvious test
flake. Nothing else — no refactors, no behaviour changes, no new features, no config
flips, no "while I'm here" improvements.

You MUST NOT touch: CLAUDE.md, the non-negotiables, the autonomous-development
pre-statement, the measurement stack (census, metrics engine, benchmark, clock census,
discovery gates), Engine B, live_trader, config/, dependencies, deploy scripts, or the
firewall family. If a finding can only be fixed by touching one of those, LEAVE IT and
say so — a diff touching them is refused in full by the guard and the whole night is
wasted.

Do not commit and do not merge. Leave your changes in the working tree.

FINDINGS:
{findings}
"""


def run_fix_phase(findings: str, timeout: int) -> str:
    """Invoke the headless session. Returns its stdout tail (for the record)."""
    r = _run(["claude", "-p", FIX_PROMPT.format(findings=findings)], timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()[-2000:]


def main() -> int:
    ap = argparse.ArgumentParser(description="ArchonDEX nightly janitor (Phase-6 rung 0)")
    ap.add_argument("--fix", action="store_true",
                    help="enable the autonomous fix phase (off by default — the pilot's "
                         "first nights establish a checks-only record first)")
    ap.add_argument("--branch", default=None, help="branch name for fixes")
    ap.add_argument("--timeout", type=int, default=1800, help="fix-phase timeout (s)")
    a = ap.parse_args()

    as_of = datetime.now().strftime("%Y-%m-%d")
    checks = run_checks()
    failed = [c for c in checks if not c.ok]
    fixable = [c for c in failed if c.mechanical]

    branch: Optional[str] = None
    diff_summary = "no changes"
    outcome = "checks_only"
    guard_note = ("fix phase DISABLED (checks-only run — the record comes first)"
                  if not a.fix else "fix phase enabled")

    if a.fix and fixable:
        branch = a.branch or f"janitor/{as_of}"
        _run(["git", "checkout", "-b", branch])
        findings = "\n".join(f"- {c.name}: {c.detail}" for c in fixable)
        tail = run_fix_phase(findings, a.timeout)
        verdict = vet_branch(ROOT)
        guard_note = verdict.report()
        if not verdict.ok:
            # REFUSED IN FULL. Leave the branch for forensics; offer nothing.
            outcome = "guard_refused"
            diff_summary = f"{len(verdict.changed)} file(s) — REFUSED: {len(verdict.violations)} forbidden"
        elif not verdict.changed:
            outcome = "no_fix_produced"
        else:
            post = run_checks()
            if all(c.ok for c in post):
                diff_summary = f"{len(verdict.changed)} file(s): {', '.join(verdict.changed[:6])}"
                open_merge_request(branch, as_of, post, diff_summary)
                outcome = "merge_requested"
            else:
                outcome = "post_check_failed"
                diff_summary = "fixes did not leave the checks green — not offered"
        _ = tail
    elif a.fix:
        guard_note = "fix phase enabled, but no mechanical findings to fix"

    write_report(checks, guard_note, branch if outcome == "merge_requested" else None, as_of)
    append_ledger(as_of, trigger="nightly_schedule", checks=checks,
                  diff_summary=diff_summary, outcome=outcome)

    print(f"[JANITOR] {as_of} outcome={outcome} "
          f"checks={{{', '.join(f'{c.name}={"PASS" if c.ok else "FAIL"}' for c in checks)}}}")
    # A check failure is REPORTED, not a janitor crash: the report + ledger are the
    # artifact. Non-zero only when the janitor itself could not do its job.
    return 0


if __name__ == "__main__":
    sys.exit(main())
