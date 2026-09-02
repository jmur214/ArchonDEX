"""The janitor's constitutional guard — Phase-6 rung 0.

THE POINT OF THIS MODULE. `docs/Core/autonomous_development_prestatement.md` names
things an autonomous session may never modify: the referee (the measurement stack),
the gates themselves, and the standing propose-first list. Those exclusions cannot
live only in the janitor's PROMPT. A prompt is a request; a model that misreads it,
or is steered by content it reads during the run, produces a diff nobody vetted.

So the exclusions are enforced HERE, mechanically, against the actual diff, after the
session has finished and before anything is offered for merge. The janitor cannot
edit this file either — it is on the denylist by name.

DESIGN: allowlist AND denylist, with DENY WINNING. The allowlist says where mechanical
work is plausible; the denylist says what is constitutionally off-limits wherever it
lives. A path must clear both.

ALL-OR-NOTHING: one forbidden path fails the WHOLE branch, not just that file. A
session that reached for the referee has demonstrated judgment we should not then
trust on the rest of its diff.
"""
from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Tuple

# ── THE CONSTITUTIONAL DENYLIST ────────────────────────────────────────────────
# Every entry traces to a clause in the pre-statement. Deny wins over any allow.
FORBIDDEN: Tuple[Tuple[str, str], ...] = (
    # "The gates themselves" — the rules that constrain the capability.
    ("CLAUDE.md", "the always-loaded non-negotiables"),
    ("docs/Core/NON_NEGOTIABLES.md", "the expanded non-negotiables"),
    ("docs/Core/autonomous_development_prestatement.md", "this pilot's own constitution"),
    ("scripts/janitor_guard.py", "the guard may not edit its own exclusions"),
    ("scripts/doc_lint.py", "a gate the janitor is checked BY"),
    # "The referee" — the measurement stack. The thing measured never controls the measure.
    ("core/census.py", "referee: the census"),
    ("core/metrics_engine.py", "referee: the metrics engine"),
    ("core/measurement/*", "referee: honest-N / MBL machinery"),
    ("core/benchmark.py", "referee: the benchmark gate"),
    ("paper_trader/clock_census.py", "referee: clock-registry semantics"),
    ("engines/engine_d_discovery/gate*.py", "referee: the discovery gates"),
    ("core/calendar_guard.py", "referee: calendar integrity"),
    # The standing propose-first list — an autonomous session WRITES TO THE QUEUE AND STOPS.
    ("engines/engine_b_risk/*", "propose-first: Engine B (Risk)"),
    ("live_trader/*", "propose-first: live trading"),
    ("requirements*.txt", "propose-first: new dependencies"),
    ("pyproject.toml", "propose-first: new dependencies"),
    ("setup.py", "propose-first: new dependencies"),
    ("config/*", "frozen configs — flag flips are a director decision"),
    ("data/governor/edge_weights.json", "[NN-NO-MANUAL-EDGES]: Engine F owns edge lifecycle"),
    ("scripts/*deploy*", "propose-first: deploys to live AWS state"),
    ("scripts/submit_*.py", "propose-first: cloud spend"),
    ("*firewall*", "the firewall family (bias/seed/injection/action)"),
    ("cockpit/dashboard/*", "[NN-NO-EDIT-DASHBOARD]: deprecated tree"),
    (".github/*", "CI definition is a gate"),
    ("*.plist", "the schedule that runs the janitor is not the janitor's to edit"),
)

# ── WHERE MECHANICAL WORK IS PLAUSIBLE ─────────────────────────────────────────
# The constitution's mechanical classes: doc drift, stale pointers, broken imports
# from merges, test flake triage. Anything outside this is not "mechanical".
ALLOWED_GLOBS: Tuple[str, ...] = (
    "docs/*", "tests/*", "scripts/*", "engines/*", "core/*", "paper_trader/*",
    "intelligence/*", "orchestration/*", "backtester/*", "research/*", "utils/*",
)


@dataclass
class GuardVerdict:
    ok: bool
    changed: List[str] = field(default_factory=list)
    violations: List[Tuple[str, str]] = field(default_factory=list)   # (path, reason)
    unclassified: List[str] = field(default_factory=list)

    def report(self) -> str:
        if self.ok:
            return f"GUARD PASS — {len(self.changed)} file(s), all within the mechanical allowlist"
        lines = ["GUARD FAIL — the branch is REFUSED IN FULL (all-or-nothing: a session that "
                 "reached for an excluded path is not trusted on the rest of its diff)."]
        for p, why in self.violations:
            lines.append(f"  FORBIDDEN  {p}  — {why}")
        for p in self.unclassified:
            lines.append(f"  OUTSIDE ALLOWLIST  {p}  — not a mechanical-class location")
        return "\n".join(lines)


def _match(path: str, pattern: str) -> bool:
    """Glob match that treats a trailing /* as 'this directory, recursively'."""
    if pattern.endswith("/*"):
        return path == pattern[:-2] or path.startswith(pattern[:-1])
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)


def classify(paths: Sequence[str]) -> GuardVerdict:
    """Vet a list of repo-relative changed paths against the constitution."""
    v = GuardVerdict(ok=True, changed=list(paths))
    for p in paths:
        for pattern, why in FORBIDDEN:
            if _match(p, pattern):
                v.violations.append((p, why))
                break
        else:
            if not any(_match(p, g) for g in ALLOWED_GLOBS):
                v.unclassified.append(p)
    v.ok = not v.violations and not v.unclassified
    return v


def changed_paths(repo: Path, base: str = "origin/main") -> List[str]:
    """Files the working branch changes relative to `base` (committed + working tree)."""
    out = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", base],
        capture_output=True, text=True, check=True,
    ).stdout
    untracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout
    seen, paths = set(), []
    for line in (out + untracked).splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            paths.append(line)
    return paths


def vet_branch(repo: Path, base: str = "origin/main") -> GuardVerdict:
    return classify(changed_paths(repo, base))
