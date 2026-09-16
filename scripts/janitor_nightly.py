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
from scripts.launchd_canon import audit_live                      # noqa: E402
from scripts import ledger_backup                                 # noqa: E402

# Runtime artifacts live in the gitignored data/ tree, beside the ledger. A TRACKED
# report would make the runner worktree dirty on every run, so the nightly
# re-sync to origin/main could never succeed — the venue fix and the artifact
# location are the same problem.
def _canonical_root() -> Path:
    """The MAIN worktree, resolved from wherever this runs.

    The autonomy ledger is a PROGRAM-level record, not a worktree-level one, and
    resolving it against ROOT split it in two: a run from a worktree whose
    data/state is a real directory rather than the usual symlink silently started a
    second file also called "the autonomy ledger". That already cost one hand-merge
    of ten stranded rows, and a manual run afterwards went straight back into the
    phantom. `--git-common-dir` points at the main worktree's .git from ANY worktree,
    so one record exists no matter where the janitor is invoked.
    """
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=15, check=True).stdout.strip()
        if out:
            common = Path(out)
            main = common.parent if common.name == ".git" else common
            if (main / "data").exists():
                return main
    except Exception:
        pass
    return ROOT          # degrade to local rather than lose the row entirely


CANON = _canonical_root()
REPORT = CANON / "data/state/janitor_report.md"
LEDGER = CANON / "data/state/autonomy_ledger.jsonl"
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

#: How many failing test NAMES to persist on a red suite. Names, never tracebacks:
#: enough to diagnose, small enough that a bad night cannot bury the log.
MAX_FORENSIC_LINES = 40


def forensic_lines(pytest_output: str) -> List[str]:
    """The FAILED/ERROR names from a pytest run, in order.

    Kept separate from the subprocess call so it can be tested against REAL
    captured output instead of by re-running a red suite — the thing being parsed
    is pytest's short-summary format, and that is what must not drift.
    """
    out: List[str] = []
    for line in pytest_output.splitlines():
        t = line.strip()
        if t.startswith("FAILED ") or t.startswith("ERROR "):
            out.append(t)
    return out


def check_suite() -> Check:
    """Run the fast tier; on FAILURE, persist WHICH tests failed.

    The 2026-09-11 row cost us a diagnosis: 17 failed + 96 errors, and the janitor
    had kept only the summary line, so by the time anyone looked the tree passed
    clean and the failure was unattributable. A red check that cannot say WHAT was
    red is barely better than no check. Printed to stdout, which the wrapper
    redirects into the dated log.
    """
    r = _run([PY, "-m", "pytest", *FAST_SUITE])
    out = (r.stdout or "") + (r.stderr or "")
    tail = out.strip().splitlines()
    summary = next((l for l in reversed(tail) if "passed" in l or "failed" in l), "no summary")

    if r.returncode != 0:
        names = forensic_lines(out)
        print(f"[JANITOR-FORENSICS] suite FAILED — {len(names)} FAILED/ERROR line(s):")
        for l in names[:MAX_FORENSIC_LINES]:
            print(f"    {l}")
        if len(names) > MAX_FORENSIC_LINES:
            print(f"    ... and {len(names) - MAX_FORENSIC_LINES} more (capped at "
                  f"{MAX_FORENSIC_LINES}; the pattern is in the names, not the volume)")
        # Counts travel in the detail so the LEDGER row is comparable night to night
        # without reading the log at all.
        n_fail = sum(1 for l in names if l.startswith("FAILED"))
        n_err = sum(1 for l in names if l.startswith("ERROR"))
        summary = f"{summary} | failed={n_fail} errors={n_err}"

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


#: The janitor's OWN generated artifacts. They are written by the very run doing the
#: checking, so counting them as "uncommitted" makes worktree_canon fail EVERY night
#: over a file the janitor just wrote — a permanent false alarm, which is the exact
#: alarm-fatigue anti-pattern the per-feed budgets and the census exist to avoid.
#: (Found by reading the janitor's own first report: "2 uncommitted path(s)".)
SELF_WRITTEN = ("data/state/janitor_report.md", "data/state/autonomy_ledger.jsonl")


def check_worktree_canon() -> Check:
    """Worktree hygiene: is this worktree clean — apart from what this run wrote —
    and based on a known origin/main?"""
    raw = _run(["git", "status", "--porcelain"]).stdout.strip()
    dirty = [l for l in raw.splitlines()
             if l.strip() and not any(l.endswith(p) for p in SELF_WRITTEN)]
    behind = _run(["git", "rev-list", "--count", "HEAD..origin/main"]).stdout.strip() or "?"
    ok = not dirty
    detail = "clean (excluding the janitor's own artifacts)" if ok else \
             f"{len(dirty)} uncommitted path(s): {', '.join(l[3:] for l in dirty[:4])}"
    return Check("worktree_canon", ok, f"{detail}; {behind} commit(s) behind origin/main")


def check_launchd_canon() -> Check:
    """Registered launchd jobs must map to LIVE tasks, or carry an exemption.

    The census tripwire one layer down, and BIDIRECTIONAL on purpose: an ORPHANED
    job is a closed task still firing (t295-population fired 88 times over six weeks
    telling its own log to unload it), while a MISSING one is a schedule everyone
    believes is running that quietly is not — the 2026-07-13 silent-outage shape. A
    one-directional check catches the zombies and misses the outage."""
    v = audit_live()
    return Check("launchd_canon", v.ok, v.report())


def check_runner_canon() -> Check:
    """Is the janitor running CANONICAL code?

    The pilot's mechanics put the runner in a shared worktree, so the nightly job
    executes whatever branch an agent happened to leave checked out at 03:00 — for
    the first nine nights of this ledger that was a feature branch, and the checks
    were measuring in-progress work rather than main. The results were not wrong;
    they were about the wrong tree, which is worse, because nothing said so.

    Reported, not fatal: a refusal would alarm on every night an agent is mid-task,
    which is most of them. A recorded PASS/FAIL makes every ledger row INTERPRETABLE
    after the fact — you can ask "was this night canonical?" instead of guessing.
    The durable fix (a dedicated runner worktree pinned to origin/main) needs a plist
    repoint, which is deploy-shaped and therefore propose-first."""
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    main = _run(["git", "rev-parse", "origin/main"]).stdout.strip()
    if not head or not main:
        return Check("runner_canon", False, "could not resolve HEAD or origin/main")
    if head == main:
        return Check("runner_canon", True, f"HEAD == origin/main ({head[:8]}) — canonical")
    ahead = _run(["git", "rev-list", "--count", "origin/main..HEAD"]).stdout.strip() or "?"
    branch = _run(["git", "branch", "--show-current"]).stdout.strip() or "detached"
    return Check("runner_canon", False,
                 f"running {branch!r} at {head[:8]}, {ahead} commit(s) off origin/main "
                 f"({main[:8]}) — these checks describe THAT tree, not main")


def check_ledger_backup() -> Check:
    """Does a readable REMOTE copy of the authority record exist, and is it current?

    Runs at the START, before tonight's row is appended, so it reports on LAST
    night's sync. A push that failed silently is then caught within 24 hours instead
    of at the moment of loss — which, for a single-copy record, is the only moment
    that is too late (T-337: Arm-1's run dirs were gone before anyone asked)."""
    v = ledger_backup.verify(LEDGER)
    return Check("ledger_backup", v.ok, v.detail)


def run_checks() -> List[Check]:
    return [check_runner_canon(), check_worktree_canon(), check_launchd_canon(),
            check_ledger_backup(), check_doc_lint(), check_census(), check_suite()]


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


def _env_snapshot() -> dict:
    """Cheap environment facts worth having on every row, not just bad ones."""
    import shutil
    try:
        usage = shutil.disk_usage(str(ROOT))
        disk_free_gb = round(usage.free / 1024 ** 3, 2)
    except Exception:
        disk_free_gb = None
    try:
        load1 = round(os.getloadavg()[0], 2)
    except Exception:
        load1 = None
    return {"disk_free_gb": disk_free_gb, "load1": load1}


def append_ledger(as_of: str, trigger: str, checks: List[Check],
                  diff_summary: str, outcome: str) -> None:
    """The autonomy ledger — every autonomous action, so the stream can be SCORED and
    a bad class DEMOTED (symmetric, no ratchet)."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of, "session": "janitor_nightly", "rung": 0, "trigger": trigger,
        "checks": {c.name: ("PASS" if c.ok else "FAIL") for c in checks},
        # ENVIRONMENT, recorded every night whether or not anything failed. The
        # disk-pressure hypothesis for the 09-11..09-13 failures could not be tested
        # because nothing measured the disk at 03:00 — by the time a human looked,
        # the balloon had refilled. A hypothesis you cannot test from the record is
        # a shrug; one number per row makes tomorrow's row able to confirm or refute it.
        "env": _env_snapshot(),
        "detail": {c.name: c.detail for c in checks},
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
    # A manual run and a scheduled one were indistinguishable in the ledger except
    # by timestamp — working out that row 10 was manual cost the director a check of
    # the file's mtime. The wrapper (and only the wrapper) passes the scheduled
    # trigger, so a bare invocation is honestly labelled `manual`.
    ap.add_argument("--trigger", default="manual",
                    help="what caused this run; the launchd wrapper passes nightly_schedule")
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
    append_ledger(as_of, trigger=a.trigger, checks=checks,
                  diff_summary=diff_summary, outcome=outcome)

    # SURVIVAL, after the row is written so tonight's row is the thing that survives.
    # Never `allow_rewrite` on the scheduled path: a nightly job must not be able to
    # overwrite history, only extend it. Reported, never fatal — losing the backup is
    # serious, but a janitor that dies on an S3 hiccup stops producing the record it
    # is protecting.
    v = ledger_backup.sync(LEDGER, as_of=as_of)
    print(f"[JANITOR] ledger_sync {v.status}: {v.detail}")

    print(f"[JANITOR] {as_of} outcome={outcome} "
          f"checks={{{', '.join(f'{c.name}={"PASS" if c.ok else "FAIL"}' for c in checks)}}}")
    # A check failure is REPORTED, not a janitor crash: the report + ledger are the
    # artifact. Non-zero only when the janitor itself could not do its job.
    return 0


if __name__ == "__main__":
    sys.exit(main())
