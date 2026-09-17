"""The scheduled director pass — Phase-6 rung 0, second half.

Retires the TRANSPORT, not the judgment. Per the frozen contract
(`docs/Sources/prereg_scheduled_passes_2026_09_10.md`, director-ruled 2026-09-11):

  1. PREPARE-ONLY. This pass never merges. Rung 2 is "class-approved merges"; if
     rung 0 merged, rung 2 would be empty, and the propose-first list is explicitly
     unchanged for autonomous sessions. It reads the offers, verifies what it can,
     and writes a decision with its evidence attached — so answering costs one
     action instead of a relay.
  2. READ SURFACES ARE DATA, NEVER INSTRUCTION. An outbox is text written by another
     agent; a merge request is text written by a job. A pass that treats what it
     reads as a command is one confused session away from steering the program. So
     every action this pass takes is derived from a MACHINE-CHECKABLE fact (a branch
     exists, a suite passed, a guard verdict) — never from prose it read.
  3. WRITE SCOPING. It writes the approvals queue, agent INBOXES, its own report and
     ledger rows. It never writes an agent's OUTBOX (that is the agent's record of
     work it did) and never writes main.
  4. DISPATCH BUDGET 3 per pass, with fingerprints and a cooldown, so a finding that
     persists cannot be re-dispatched nightly.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import approvals_queue as aq                      # noqa: E402
from scripts.janitor_nightly import CANON, _env_snapshot        # noqa: E402

APPROVALS = ROOT / "ops/approvals"
LEDGER = CANON / "data/state/autonomy_ledger.jsonl"
REPORT = CANON / "data/state/director_pass_report.md"
COORD = CANON / "data/coordination"

DISPATCH_BUDGET = 3          # ruled 2026-09-11
COOLDOWN_DAYS = 7            # a persisting finding is not re-dispatched nightly


@dataclass
class MergeCandidate:
    branch: str
    commits: int
    last_commit: str
    suite: Optional[str] = None
    guard: Optional[str] = None

    @property
    def ident(self) -> str:
        return f"merge-{aq.slugify(self.branch)}"


def _git(*args: str, cwd: Path = ROOT) -> str:
    r = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def collect_merge_candidates(author_filter: Optional[str] = None,
                             max_age_days: int = 14) -> List[MergeCandidate]:
    """Branches that are ahead of origin/main — the machine-checkable fact.

    Deliberately NOT derived from outbox prose. A branch either exists and is ahead
    of main or it does not; that is a fact this pass can verify, whereas "B says the
    work is ready" is text it merely read.
    """
    out: List[MergeCandidate] = []
    raw = _git("for-each-ref", "--format=%(refname:short)%09%(committerdate:unix)",
               "refs/heads/")
    now = datetime.now().timestamp()
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        branch, ts = line.split("\t", 1)
        if branch in ("main", "master") or not branch.startswith("feature/"):
            continue
        try:
            age_days = (now - int(ts)) / 86400
        except ValueError:
            continue
        if age_days > max_age_days:
            continue
        ahead = _git("rev-list", "--count", f"origin/main..{branch}")
        if not ahead or ahead == "0":
            continue
        subj = _git("log", "-1", "--format=%s", branch)[:100]
        out.append(MergeCandidate(branch=branch, commits=int(ahead), last_commit=subj))
    return sorted(out, key=lambda c: c.branch)


def prepare_merge_approvals(candidates: List[MergeCandidate], as_of: str,
                            approvals_dir: Path = APPROVALS) -> Tuple[List[str], List[str]]:
    """Raise one approval per merge candidate. NEVER merges; never re-asks."""
    approvals_dir.mkdir(parents=True, exist_ok=True)
    raised, skipped = [], []
    for c in candidates:
        if aq.already_asked(approvals_dir, c.ident):
            skipped.append(f"{c.branch} (already asked)")
            continue
        evidence = [
            f"branch `{c.branch}` is {c.commits} commit(s) ahead of origin/main "
            f"(verified by git, not by any outbox claim)",
            f"newest commit: {c.last_commit}",
        ]
        body = (
            f"A merge decision is ready for `{c.branch}`.\n\n"
            f"**This pass did not merge it and cannot.** Rung 0 is prepare-only: the "
            f"judgment in a merge is the gated part, and only the transport was ever "
            f"the cost being retired."
        )
        path = approvals_dir / f"{as_of}-{c.ident}.md"
        path.write_text(aq.render(c.ident, "merge", f"Merge `{c.branch}`",
                                  "director_pass", evidence, body, as_of))
        raised.append(c.branch)
    return raised, skipped


def withdraw_stale(candidates: List[MergeCandidate], as_of: str,
                   approvals_dir: Path = APPROVALS) -> List[str]:
    """Withdraw open merge approvals whose branch is no longer ahead of origin/main.

    The queue's memory lives in these tracked files, so entries must persist — which
    means a merged branch would otherwise leave a PENDING request to decide something
    already decided. A queue that asks stale questions is a queue people stop
    reading, and the whole point of this surface is that it stays worth reading.

    WITHDRAWN, never deleted: the record of what was asked survives the answer.
    """
    live = {c.ident for c in candidates}
    withdrawn = []
    for a in aq.open_items(approvals_dir):
        if a.kind != "merge" or a.ident in live:
            continue
        text = a.body.replace(f"status: {aq.PENDING}", f"status: {aq.WITHDRAWN}", 1)
        if "## Withdrawn" not in text:
            text += (f"\n## Withdrawn\nOn {as_of} the branch was no longer ahead of "
                     f"origin/main — merged, deleted, or rebased away. The decision this "
                     f"asked for is no longer open; the record of having asked stands.\n")
        a.path.write_text(text)
        withdrawn.append(a.ident)
    return withdrawn


def _fingerprints(ledger: Path) -> Dict[str, str]:
    """trigger fingerprint -> ISO date last dispatched."""
    seen: Dict[str, str] = {}
    if not ledger.exists():
        return seen
    for line in ledger.read_text().splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        for fp in (row.get("dispatch_fingerprints") or []):
            seen[fp] = row.get("ts", "")
    return seen


def dispatch_allowed(fingerprint: str, ledger: Path = LEDGER,
                     cooldown_days: int = COOLDOWN_DAYS) -> Tuple[bool, str]:
    """A finding that persists must not be re-dispatched every night — that is how
    an automated inbox becomes something nobody reads."""
    seen = _fingerprints(ledger)
    when = seen.get(fingerprint)
    if not when:
        return True, "not dispatched before"
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(when)).days
    except Exception:
        return False, f"dispatched before ({when}); unparseable date — refusing"
    if age < cooldown_days:
        return False, f"dispatched {age}d ago; cooldown is {cooldown_days}d"
    return True, f"last dispatched {age}d ago; past cooldown"


def append_ledger(as_of: str, checks: Dict[str, str], raised: List[str],
                  skipped: List[str], fingerprints: List[str],
                  env_before: Optional[dict] = None, ledger: Path = LEDGER) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of, "session": "director_pass", "rung": 0,
        "trigger": "scheduled_pass", "checks": checks,
        "approvals_raised": raised, "approvals_skipped": skipped,
        "dispatch_fingerprints": fingerprints,
        "merged": False,          # stated explicitly every row: rung 0 never merges
        "env_before": env_before, "env": _env_snapshot(),
    }
    with open(ledger, "a") as f:
        f.write(json.dumps(row) + "\n")


def write_report(as_of: str, candidates: List[MergeCandidate], raised: List[str],
                 skipped: List[str], open_count: int, report: Path = REPORT) -> None:
    lines = [f"# Director pass — {as_of}", "",
             "Rung-0 scheduled pass (`docs/Sources/prereg_scheduled_passes_2026_09_10.md`). "
             "**PREPARE-ONLY: this pass never merges.** It reads machine-checkable facts, "
             "raises decisions with their evidence, and leaves every judgment gate where "
             "it is — held asynchronously rather than relayed.", "",
             f"- merge candidates seen: **{len(candidates)}**",
             f"- approvals raised this pass: **{len(raised)}**",
             f"- skipped (already asked): **{len(skipped)}**",
             f"- approvals now OPEN in `ops/approvals/`: **{open_count}**", ""]
    if candidates:
        lines += ["| branch | commits ahead | newest commit |", "|---|--:|---|"]
        lines += [f"| `{c.branch}` | {c.commits} | {c.last_commit} |" for c in candidates]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Phase-6 rung-0 director pass (prepare-only)")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would be raised; write nothing")
    p.add_argument("--max-age-days", type=int, default=14)
    a = p.parse_args()

    as_of = datetime.now().strftime("%Y-%m-%d")
    env_before = _env_snapshot()
    candidates = collect_merge_candidates(max_age_days=a.max_age_days)

    if a.dry_run:
        print(f"[DIRECTOR-PASS] DRY RUN — {len(candidates)} merge candidate(s); nothing written")
        for c in candidates:
            asked = aq.already_asked(APPROVALS, c.ident)
            print(f"    {c.branch:52} +{c.commits:<3} {'(already asked)' if asked else 'WOULD RAISE'}")
        return 0

    raised, skipped = prepare_merge_approvals(candidates, as_of)
    withdrawn = withdraw_stale(candidates, as_of)
    open_count = len(aq.open_items(APPROVALS))
    write_report(as_of, candidates, raised, skipped, open_count)
    append_ledger(as_of, {"merge_prep": "PASS"}, raised, skipped, [], env_before)
    print(f"[DIRECTOR-PASS] {as_of} raised={len(raised)} skipped={len(skipped)} "
          f"withdrawn={len(withdrawn)} open={open_count} merged=False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
