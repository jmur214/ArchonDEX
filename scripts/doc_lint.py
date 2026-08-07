"""doc_lint — anti-rot guard for the documentation system.

Runs seven checks against the docs tree + scripts/ + the memory file
that's loaded into every Claude session. Each check is independent;
all run on every invocation. The exit code is non-zero iff at least
one FAIL check fired. WARN-only runs exit zero.

Checks (T-093 dispatch acceptance):

  1. MEMORY.md byte count vs the 24.4 KB loader cap.
     WARN at >=80%, FAIL at >100%.

  2. CURRENT_STATE.md modification time within N days (default 3).
     WARN-only — staleness is informational, not blocking.

  3. Every `(SUPERSEDED by X)` marker in MEMORY.md resolves to an
     existing memory entry (file under the memory dir).

  4. Every audit-doc path referenced in MEMORY.md exists on disk.

  5. Every MEMORY.md entry has a date in its header line.

  6. TASK_LEDGER.md rows have all required columns populated.

  7. (dev item H) Every script in scripts/*.py has a one-line entry
     in docs/Core/execution_manual.md. WARN-only by default (134
     scripts in repo, execution_manual is unlikely to cover all on
     first install). Promote to FAIL when coverage gap is closed.

Usage:

    python scripts/doc_lint.py               # run all checks
    python scripts/doc_lint.py --pre-commit  # quieter output for hooks
    python scripts/doc_lint.py --json        # machine-readable

The script makes NO assumptions about its CWD; all paths are
computed relative to the repo root (the parent of `scripts/`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parents[1]
MEMORY_DIR = (
    Path.home()
    / ".claude"
    / "projects"
    / "-Users-jacksonmurphy-Dev-trading-machine-2"
    / "memory"
)
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

# 24.4 KB Claude loader cap on per-session-loaded files. WARN at 80%
# so we have headroom to land a couple more entries before hitting the
# cap and needing to archive old ones.
MEMORY_CAP_BYTES = int(24.4 * 1024)
MEMORY_WARN_FRACTION = 0.80

# CURRENT_STATE freshness window. Per the dispatch refinement #6, more
# than 3 days old means the reader should re-read source docs before
# trusting the dashboard.
CURRENT_STATE_STALE_DAYS = 3

# Required columns for TASK_LEDGER row validation.
TASK_LEDGER_REQUIRED_COLUMNS = [
    "T-ID", "date", "title", "status",
    "cells_attempted", "cells_succeeded", "outcome", "audit doc",
]

# Statuses allowed in TASK_LEDGER. One canonical token per state — these match
# actual ledger usage (`dispatched` = sent to a worker / in flight is the term
# the ledger uses; `in-flight` was aspirational and never used). Keep this set
# small and unambiguous; do not invent variants like `done (prep)` — use
# `blocked` for staged-waiting-on-a-dependency.
TASK_LEDGER_VALID_STATUSES = {
    "done", "refuted", "superseded", "dispatched", "blocked",
}


@dataclass
class CheckResult:
    name: str
    severity: str  # "PASS" | "WARN" | "FAIL"
    summary: str
    details: List[str] = field(default_factory=list)


def _format_human(results: List[CheckResult], pre_commit: bool) -> str:
    """Render results for terminal output. Pre-commit mode is quieter."""
    out: List[str] = []
    for r in results:
        prefix = {"PASS": "  ok", "WARN": "WARN", "FAIL": "FAIL"}[r.severity]
        out.append(f"[{prefix}] {r.name}: {r.summary}")
        if not pre_commit or r.severity in ("WARN", "FAIL"):
            for d in r.details:
                out.append(f"    {d}")
    return "\n".join(out)


# ---------------------------------------------------------------------
# Check 1 — MEMORY.md byte count vs cap
# ---------------------------------------------------------------------

def check_memory_size() -> CheckResult:
    name = "MEMORY.md within loader cap"
    if not MEMORY_FILE.exists():
        return CheckResult(name, "WARN", f"file not found: {MEMORY_FILE}")
    size = MEMORY_FILE.stat().st_size
    frac = size / MEMORY_CAP_BYTES
    pct = frac * 100
    summary = f"{size:,} / {MEMORY_CAP_BYTES:,} bytes ({pct:.1f}% of cap)"
    if frac > 1.0:
        return CheckResult(name, "FAIL", summary + " — over cap, archive entries")
    if frac >= MEMORY_WARN_FRACTION:
        return CheckResult(name, "WARN", summary + " — within 20% of cap, plan archival")
    return CheckResult(name, "PASS", summary)


# ---------------------------------------------------------------------
# Check 2 — CURRENT_STATE.md freshness
# ---------------------------------------------------------------------

def check_current_state_freshness(days: int = CURRENT_STATE_STALE_DAYS) -> CheckResult:
    name = "CURRENT_STATE.md freshness"
    cs = REPO / "docs" / "State" / "CURRENT_STATE.md"
    if not cs.exists():
        return CheckResult(name, "FAIL", f"missing file: {cs.relative_to(REPO)}")
    age_seconds = time.time() - cs.stat().st_mtime
    age_days = age_seconds / 86400.0
    summary = f"modified {age_days:.1f} days ago (limit {days})"
    if age_days > days:
        return CheckResult(name, "WARN", summary + " — re-read source docs before quoting state")
    return CheckResult(name, "PASS", summary)


# ---------------------------------------------------------------------
# Check 3 — MEMORY supersession markers resolve
# Check 4 — MEMORY audit-doc references exist on disk
# Check 5 — MEMORY entries have a date in their header
# ---------------------------------------------------------------------

# MEMORY.md format (per CLAUDE.md auto-memory spec):
#   - [Title](filename.md) — one-line hook
# Some entries have richer bracketed markdown links. We look for them
# generically.

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_SUPERSEDED_RE = re.compile(r"SUPERSEDED by ([A-Za-z0-9._/+\-]+)")


def _memory_entries() -> List[str]:
    """Return the bullet-line text of each MEMORY.md entry."""
    if not MEMORY_FILE.exists():
        return []
    return [
        line for line in MEMORY_FILE.read_text().splitlines()
        if line.startswith("- ")
    ]


def check_memory_supersession_markers() -> CheckResult:
    name = "MEMORY supersession markers resolve"
    entries = _memory_entries()
    if not MEMORY_DIR.exists():
        return CheckResult(name, "WARN", f"memory dir not found: {MEMORY_DIR}")
    missing: List[str] = []
    seen = 0
    # Cache memory-file bodies for tag-style reference resolution.
    body_cache = {
        f.name: f.read_text()
        for f in MEMORY_DIR.glob("*.md")
        if f.name != "MEMORY.md"
    }
    for line in entries:
        for ref in _SUPERSEDED_RE.findall(line):
            seen += 1
            # 1. Slug match: filename minus .md.
            if (MEMORY_DIR / f"{ref}.md").exists():
                continue
            # 2. T-ID reference: a memory body contains the T-ID.
            if re.match(r"T-\d+[a-z]*", ref) and any(
                ref in body for body in body_cache.values()
            ):
                continue
            # 3. Tag-style reference (e.g., 'C-collapses-1'): the tag
            # appears as a title prefix or anywhere in a memory body.
            if any(ref in body for body in body_cache.values()):
                continue
            missing.append(
                f"`{ref}` not found as slug, T-ID, or tag in any memory file"
            )
    if not seen:
        return CheckResult(name, "PASS", "no `SUPERSEDED by` markers present")
    if missing:
        return CheckResult(
            name, "FAIL",
            f"{len(missing)} unresolved marker(s) of {seen} total",
            missing,
        )
    return CheckResult(name, "PASS", f"all {seen} markers resolve")


def check_memory_audit_doc_refs() -> CheckResult:
    name = "MEMORY audit-doc refs exist on disk"
    entries = _memory_entries()
    missing: List[str] = []
    seen = 0
    for line in entries:
        for _, link in _LINK_RE.findall(line):
            # Strip url fragments.
            link_clean = link.split("#")[0]
            if not (
                link_clean.startswith("docs/Audit/")
                or link_clean.endswith(".md")
            ):
                continue
            # Only check audit-doc links — those are the brittle ones.
            if not link_clean.startswith("docs/Audit/"):
                continue
            seen += 1
            target = REPO / link_clean
            if not target.exists():
                missing.append(f"{link_clean} (referenced in MEMORY.md)")
    if not seen:
        return CheckResult(name, "PASS", "no docs/Audit/ links in MEMORY.md")
    if missing:
        return CheckResult(
            name, "FAIL",
            f"{len(missing)} broken link(s) of {seen} audit refs",
            missing,
        )
    return CheckResult(name, "PASS", f"all {seen} audit-doc refs exist")


def check_memory_entries_have_dates() -> CheckResult:
    name = "MEMORY entries have a date in header"
    entries = _memory_entries()
    undated: List[str] = []
    seen = 0
    for line in entries:
        seen += 1
        if not _DATE_RE.search(line):
            # Truncate to 80 chars for readability.
            display = line[:80] + ("..." if len(line) > 80 else "")
            undated.append(display)
    if not seen:
        return CheckResult(name, "WARN", "MEMORY.md has no list entries")
    if undated:
        # WARN-only by default: the 10 legacy archived hooks
        # (feedback_no_manual_tuning, project_phantom_stops_fix, etc.)
        # pre-date the dating convention. Promote to FAIL after those
        # are backfilled. New entries should already include a date in
        # their header; if undated count grows beyond the legacy 10,
        # the reviewer should investigate.
        return CheckResult(
            name, "WARN",
            f"{len(undated)} undated entries of {seen} total — "
            f"legacy entries pre-date the dating convention; backfill follow-up",
            undated,
        )
    return CheckResult(name, "PASS", f"all {seen} entries dated")


# ---------------------------------------------------------------------
# Check 6 — TASK_LEDGER row completeness
# ---------------------------------------------------------------------

def check_task_ledger_columns() -> CheckResult:
    name = "TASK_LEDGER rows complete"
    ledger = REPO / "docs" / "State" / "TASK_LEDGER.md"
    if not ledger.exists():
        return CheckResult(name, "FAIL", f"missing file: {ledger.relative_to(REPO)}")
    text = ledger.read_text()
    # Pull every Markdown table row that looks like a T-ID row.
    rows = [
        ln for ln in text.splitlines()
        if ln.startswith("|") and re.search(r"T-\d", ln) and "---" not in ln
    ]
    issues: List[str] = []
    for row in rows:
        # Split table row by `|`, strip empties from the rail.
        cells = [c.strip() for c in row.split("|")[1:-1]]
        if len(cells) != len(TASK_LEDGER_REQUIRED_COLUMNS):
            issues.append(
                f"row column count mismatch ({len(cells)} != "
                f"{len(TASK_LEDGER_REQUIRED_COLUMNS)}): {row[:80]}"
            )
            continue
        for i, col in enumerate(TASK_LEDGER_REQUIRED_COLUMNS):
            if not cells[i]:
                issues.append(f"empty `{col}` in row: {row[:80]}")
        # Validate status if present.
        status = cells[3]
        if status and status not in TASK_LEDGER_VALID_STATUSES:
            issues.append(
                f"invalid status `{status}` in row: {row[:80]} "
                f"(allowed: {sorted(TASK_LEDGER_VALID_STATUSES)})"
            )
    if not rows:
        return CheckResult(name, "WARN", "no T-ID rows found in ledger")
    if issues:
        return CheckResult(
            name, "FAIL",
            f"{len(issues)} issue(s) across {len(rows)} rows",
            issues,
        )
    return CheckResult(name, "PASS", f"all {len(rows)} rows complete")


# ---------------------------------------------------------------------
# Check 7 — scripts/*.py covered in execution_manual.md (WARN-only)
# ---------------------------------------------------------------------

def check_scripts_in_execution_manual() -> CheckResult:
    name = "scripts/*.py documented in execution_manual.md"
    manual = REPO / "docs" / "Core" / "execution_manual.md"
    scripts_dir = REPO / "scripts"
    if not manual.exists():
        return CheckResult(name, "FAIL", f"missing file: {manual.relative_to(REPO)}")
    if not scripts_dir.exists():
        return CheckResult(name, "PASS", "no scripts/ dir")
    manual_text = manual.read_text()
    py_files = sorted(
        f.name for f in scripts_dir.glob("*.py")
        if not f.name.startswith("_")
        and f.name != "__init__.py"
    )
    missing: List[str] = []
    for s in py_files:
        # A script is "documented" if its basename appears anywhere in
        # execution_manual.md — either as `python -m scripts.X` or as
        # `scripts/X.py`. Cheap but adequate.
        stem = s[:-3]  # strip .py
        if (
            stem in manual_text
            or f"scripts/{s}" in manual_text
            or f"scripts.{stem}" in manual_text
        ):
            continue
        missing.append(s)
    if not py_files:
        return CheckResult(name, "PASS", "no .py files in scripts/")
    covered = len(py_files) - len(missing)
    summary = (
        f"{covered}/{len(py_files)} scripts documented "
        f"({len(missing)} missing) — WARN-only"
    )
    if missing:
        return CheckResult(name, "WARN", summary, missing)
    return CheckResult(name, "PASS", summary)


# ---------------------------------------------------------------------
# Check 8 — non-negotiables cited by stable [NN-SLUG] anchor, not number
# ---------------------------------------------------------------------

# Positional numbers rot when the rule list grows: the 2026-06 doc audit
# found 159 refs that ALL mispointed after the non-negotiable set grew from
# ~9 to 15 (e.g. "CLAUDE.md #6" resolved to edge_weights.json when the author
# meant the Sharpe-CI gate). Rules now carry stable `[NN-SLUG]` anchors in
# CLAUDE.md / NON_NEGOTIABLES.md; any numbered reference is a regression.
# NOTE: "lessons rule #N" points to lessons_learned.md (a different list) and
# is intentionally NOT matched — the prefixes below are non-negotiable-only.
NUMBERED_NONNEG_RE = re.compile(
    r"(CLAUDE\.md|non[- ]?negotiable|NON_NEGOTIABLE)\s*#\d+", re.IGNORECASE
)


def check_no_numbered_nonneg_refs() -> CheckResult:
    name = "Non-negotiables cited by stable anchor, not number"
    targets = [REPO / "CLAUDE.md"] + sorted((REPO / "docs").rglob("*.md"))
    offenders: List[str] = []
    for f in targets:
        if not f.is_file():
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if NUMBERED_NONNEG_RE.search(line):
                offenders.append(f"{f.relative_to(REPO)}:{i}: {line.strip()[:80]}")
    if offenders:
        return CheckResult(
            name, "FAIL",
            f"{len(offenders)} numbered non-negotiable ref(s) — cite by "
            f"`[NN-SLUG]` anchor instead (see CLAUDE.md)",
            offenders,
        )
    return CheckResult(name, "PASS", "no numbered non-negotiable refs")


# ---------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------


def check_closure_receipts() -> CheckResult:
    """T-339: a MEASURED closure must have a locatable receipt set.

    THE DEFECT THIS PREVENTS (C/T-337): all five Arm-1 run dirs under the
    T-215/T-180-v2 closures were deleted — the ledger still says "refuted", but the
    evidence is unobtainable. The manifest sweep found the problem is wider AND
    deeper than deletion: 49 performance_summary.json survive under UUID run dirs
    that NO document cites, so they are already unverifiable while sitting on disk.
    A receipt nothing points at cannot support a closure.

    ENFORCEMENT POINT (stated deliberately): doc_lint, not the census. The closure
    CLAIM is made in the ledger — a document — so the check belongs where the claim
    is; doc_lint already runs pre-commit; and a census check fires at RUN time,
    before a closure exists to have a receipt.

    FORWARD-ONLY (grandfathered): enforced for rows dated on/after ACTIVATION. The
    105 historical measured closures are reported by
    `scripts/closure_manifest_t339.py`, not failed here — retroactive enforcement
    would block every commit for a debt this check exists to stop ACCRUING.
    """
    name = "Measured closures cite a locatable receipt (T-339, forward-only)"
    ACTIVATION = "2026-08-06"
    ledger = REPO / "docs" / "State" / "TASK_LEDGER.md"
    if not ledger.exists():
        return CheckResult(name, "FAIL", "missing TASK_LEDGER.md")
    try:
        # doc_lint may run with a bare sys.path (pre-commit hook) — make the repo
        # importable so this check ACTUALLY RUNS. A checker that silently no-ops is
        # worse than no checker: it reports green while enforcing nothing.
        import sys as _sys
        if str(REPO) not in _sys.path:
            _sys.path.insert(0, str(REPO))
        from scripts.closure_manifest_t339 import resolve_receipts, _MEASURED, _ROW
    except Exception as exc:  # never block a commit on the checker itself
        return CheckResult(name, "WARN",
                           f"receipt check INERT — manifest module unimportable "
                           f"({type(exc).__name__}); fix before trusting this gate")
    issues: List[str] = []
    checked = 0
    for line in ledger.read_text().splitlines():
        m = _ROW.match(line)
        if not m or not _MEASURED.search(line):
            continue
        cells = [c.strip() for c in line.split("|")]
        date = cells[2] if len(cells) > 2 else ""
        if date < ACTIVATION:          # grandfathered (ISO dates sort lexically)
            continue
        checked += 1
        task = m.group(1)
        res = resolve_receipts(task, cells[-2] if len(cells) > 2 else "")
        if res["state"] == "MISSING":
            issues.append(f"{task}: measured verdict with NO locatable receipt "
                          f"(archive it under closures/{task}/ and cite the audit doc)")
    if issues:
        return CheckResult(name, "FAIL", "; ".join(issues))
    return CheckResult(name, "PASS",
                       f"{checked} post-{ACTIVATION} measured closure(s) have receipts "
                       f"(historical rows grandfathered — see closure_manifest_t339)")


CHECKS = [
    check_memory_size,
    check_current_state_freshness,
    check_memory_supersession_markers,
    check_memory_audit_doc_refs,
    check_memory_entries_have_dates,
    check_task_ledger_columns,
    check_scripts_in_execution_manual,
    check_no_numbered_nonneg_refs,
    check_closure_receipts,
]


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ArchonDEX doc-system lint.")
    p.add_argument(
        "--pre-commit", action="store_true",
        help="Quieter output for pre-commit hook contexts.",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable JSON instead of human text.",
    )
    args = p.parse_args(argv)
    results = [chk() for chk in CHECKS]
    if args.json:
        payload = [
            {"name": r.name, "severity": r.severity, "summary": r.summary,
             "details": r.details}
            for r in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(_format_human(results, args.pre_commit))
    exit_code = 1 if any(r.severity == "FAIL" for r in results) else 0
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
