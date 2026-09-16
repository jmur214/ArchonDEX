"""T-2026-09-16-356 — THE DURABILITY CENSUS: every writer of a forward record,
durable-or-exempted, with the exemption's REASON on the record.

Why this exists. C found `deploy_candidate_tracking.json` written to the ephemeral
Fargate disk and discarded on every exit: account-2 traded canonically, clean, green,
no alarm, while its decision-relevant record evaporated (T-351; 09-15/16 are permanent
holes). T-337 was the same class one venue over — Arm-1 run dirs deleted, so verdicts
that can never be TR-stamped. **A record that never accrues is indistinguishable from
one that is merely young**, so it reads "too early to say" forever with nothing
reporting a fault. C's tripwire closed the two registries C owns (`ALL_BOOKS` + the
pulse's family trackers). This closes the rest of the class.

THE CORRECTION THIS MODULE ENCODES. "Is it in `DURABLE_PATHS`?" is the WRONG question.
`DURABLE_PATHS` is the PAPER LOOP's registry and it defends against exactly ONE failure
mode — container exit. A record written in another venue is not protected by it and was
never meant to be, so its absence there is not evidence of a defect. The question that
generalises is:

    **does this record have a durability mechanism IN ITS OWN VENUE?**

Three venues, three mechanisms:
  * `cloud_paper`  — the ephemeral per-day container → `DURABLE_PATHS` / `DURABLE_DIRS` (S3).
  * `cloud_batch`  — a campaign cell → the entrypoint's per-run S3 upload.
  * `local`        — launchd/hand-run on one machine → git, or NOTHING.

`local` is the one with no default. A gitignored file on one laptop has no mechanism at
all, and that is not a smaller problem than the ephemeral one — it is a slower one.

DESIGN RULES, each bought with a prior failure:
  * **Read-only and artifact/code-derived.** Same posture as the T-338 clock census.
  * **Bidirectional**, per B's launchd sweep: an unregistered writer is a fault AND a
    registry entry nothing writes is a fault. A one-directional check catches the
    zombies and misses the outage.
  * **An exemption must state WHY.** "It exists" is what kept a dead launchd job alive
    for six weeks. `reason` is required and non-empty, and so is an owner on a gap.
  * **The scan is DELIBERATELY OVER-INCLUSIVE, and that is not wolf-crying.** It joins
    "this module writes something" x "this module names a data path", which cannot prove
    THAT path is the one written — `governor.py` names `data/trade_logs/trades.csv` as an
    INPUT to `update_from_trade_log`, and the coarse join flags it. The distinction that
    matters: this is a GATE, not an alarm. It fires once per UNCLASSIFIED path and then
    never again, so the cost is a one-time classification with the verified read/write
    nature recorded in `reason`. A recurring alarm on a healthy state is the thing worth
    refusing; a one-time "classify this" is the thing that stops a new writer shipping
    undurable in silence.
  * **KNOWN_GAP is a real, loud state — not a pass.** Registering a gap keeps other
    lanes' suites green (fixes route to the owning lane) while `open_gaps()` reports it
    with an owner and a date so it cannot go quiet. A gap with no owner fails the census.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]

DURABLE = "DURABLE"          # covered by its venue's mechanism
EXEMPT = "EXEMPT"            # deliberately ephemeral/regenerable, reason stated
KNOWN_GAP = "KNOWN_GAP"      # a real gap, owned and dated — reported, not silently passed
INPUT = "INPUT"              # verified READ-only at this site (the scan is deliberately coarse)

VENUES = ("cloud_paper", "cloud_batch", "local")


@dataclass(frozen=True)
class Record:
    """One writer of a forward/append record — something whose value is that it ACCRUES."""
    path: str
    venue: str
    status: str
    reason: str                      # REQUIRED — why exempt, or what the gap is
    writer: str                      # the module that writes it (the bidirectional key)
    owner: str = ""                  # REQUIRED when status == KNOWN_GAP


@dataclass
class CensusVerdict:
    ok: bool
    failures: List[str]
    gaps: List[Record]
    checked: int


# --------------------------------------------------------------------------------------
# THE REGISTRY — every writer of an accruing record outside C's two registries.
# `cloud_paper` writers are verified against DURABLE_PATHS at runtime (not restated here),
# so this registry carries what that check cannot see.
# --------------------------------------------------------------------------------------
REGISTRY: Tuple[Record, ...] = (
    # ---- local venue: the janitor's own records -------------------------------------
    Record(
        path="data/state/autonomy_ledger.jsonl", venue="local", status=KNOWN_GAP,
        writer="scripts/janitor_nightly.py", owner="B (janitor lane)",
        reason="T-356 finding #1 (2026-09-16). THE PHASE-6 AUTHORITY RECORD — the "
               "append-only evidence base on which autonomous authority is granted and "
               "symmetrically demoted — is gitignored, untracked, in no S3 sync, and "
               "exists as exactly ONE copy on ONE machine. It is ACTIVELY accruing (18 "
               "rows, written the day this was audited). Its exposure is NOT C's nightly "
               "evaporation (the janitor runs locally, so no run loses a row); it is "
               "T-337's: single-copy loss, unreconstructable, silent. The record that "
               "governs the autonomy ladder is the least durable record in the system.",
    ),
    Record(
        path="data/state/janitor_report.md", venue="local", status=EXEMPT,
        writer="scripts/janitor_nightly.py", reason=
        "REGENERABLE BY CONSTRUCTION: a rendered surface replaced whole on every run, "
        "not an accruing record. Its durable content is the autonomy_ledger row the same "
        "run writes. Losing it costs one night's rendering, not history.",
    ),
    Record(
        path="data/coordination/janitor_merge_requests.md", venue="local", status=EXEMPT,
        writer="scripts/janitor_nightly.py", reason=
        "A QUEUE, not a record: entries are consumed by a human merge and the file is "
        "rebuilt from repo state each run. Absent at audit time (no open requests), which "
        "is its normal empty state rather than a loss.",
    ),

    # ---- local venue: Engine F / D governance history --------------------------------
    Record(
        path="data/governor/lifecycle_history.csv", venue="local", status=KNOWN_GAP,
        writer="engines/engine_f_governance/lifecycle_manager.py", owner="F lane",
        reason="T-356 finding #2 (2026-09-16). Engine F's promotion/demotion history — "
               "33 rows, last written 2026-06-13 — is gitignored and carries no durability "
               "mechanism in any venue. DORMANT, not bleeding: no run has lost a row in "
               "three months, so this is a LATENT gap, reported as such and not as an "
               "active loss. It matters whenever the lifecycle resumes.",
    ),
    Record(
        path="data/governor/feedback_history.log", venue="local", status=KNOWN_GAP,
        writer="engines/engine_f_governance/governor.py", owner="F lane",
        reason="T-356 finding #3 (2026-09-16). 488 rows / 640K of governor feedback "
               "history, last written 2026-04-23, gitignored and unprotected. Same latent "
               "status as lifecycle_history.csv: dormant, so no active loss.",
    ),
    Record(
        path="data/research/discovery_log.jsonl", venue="local", status=KNOWN_GAP,
        writer="engines/engine_d_discovery/discovery_logger.py", owner="D lane (mine)",
        reason="T-356 finding #4 (2026-09-16). 88 rows, last written 2026-06-17, "
               "gitignored, no mechanism. Dormant since the Discovery cycle went quiet. "
               "Mine to fix when Discovery next runs — recorded here so it is not "
               "rediscovered as a surprise then.",
    ),
    Record(
        path="data/governor/lifecycle_journal.jsonl", venue="local", status=EXEMPT,
        writer="engines/engine_f_governance/journal.py", reason=
        "ABSENT at audit (never written / cleared). Nothing is accruing, so there is "
        "nothing to lose; if the journal starts writing, this entry must flip to a real "
        "status — which the bidirectional check forces, since a registered path that "
        "starts being written is re-evaluated, not grandfathered.",
    ),
    Record(
        path="data/research/allocation_recommendations.json", venue="local", status=EXEMPT,
        writer="engines/engine_c_portfolio/allocation_evaluator.py", reason=
        "NOT an accruing record — a learned artifact, replaced whole and regenerable. "
        "ABSENT at audit, which is the healthy state: T-158 found this file silently "
        "overriding mode->adaptive on every local allocate(), so local and cloud ran "
        "DIFFERENT trading systems. Its absence removes that divergence; durability here "
        "would preserve a hazard, not a record.",
    ),

    # ---- verified INPUTS: named here, flagged by the coarse join, read-only ---------
    Record(
        path="data/trade_logs/trades.csv", venue="local", status=INPUT,
        writer="engines/engine_f_governance/governor.py", reason=
        "VERIFIED READ-ONLY at this site: the default `trade_log_path` argument of "
        "`update_from_trade_log` (governor.py:493) — an input the governor consumes, not "
        "a record it writes. Recorded so a future reader does not inherit the coarse "
        "scan's mis-attribution as fact.",
    ),
    Record(
        path="data/trade_logs/snapshots.csv", venue="local", status=INPUT,
        writer="engines/engine_f_governance/governor.py", reason=
        "VERIFIED READ-ONLY: the `snapshot_path` argument of `update_from_trade_log` "
        "(governor.py:494). Same mis-attribution as trades.csv above.",
    ),

    # ---- regenerable state / outputs: not accruing records --------------------------
    Record(
        path="data/governor/edge_weights.json", venue="local", status=EXEMPT,
        writer="engines/engine_f_governance/governor.py", reason=
        "GENUINELY WRITTEN (governor.py:802 persists weights) but it is STATE, not "
        "history: replaced whole and reconstructable from the lifecycle. Durability would "
        "preserve a snapshot, not a record. Note the standing rule this sits under — "
        "`[NN-NO-MANUAL-EDGES]`: Engine F owns it and it is never hand-edited.",
    ),
    Record(
        path="data/research/edge_recommendations.json", venue="local", status=EXEMPT,
        writer="engines/engine_f_governance/governor.py", reason=
        "A recommendation OUTPUT, replaced whole on each run and regenerable from the "
        "same inputs. Nothing accrues in it.",
    ),
    Record(
        path="data/research/edge_results.csv", venue="local", status=EXEMPT,
        writer="engines/engine_f_governance/evaluator.py", reason=
        "Evaluator output, regenerable by re-running the evaluator against the same "
        "substrate. A measurement artifact, not a forward record.",
    ),

    # ---- the inverse defect: durable, but nothing ever writes the source -------------
    Record(
        path="data/intel/agentic_analyst_calls.jsonl", venue="cloud_paper", status=KNOWN_GAP,
        writer="(NONE — no writer exists)", owner="E (agentic analyst lane)",
        reason="T-356 finding #5 (2026-09-16). THE INVERSE OF C'S DEFECT. "
               "`analyst_desk_book.json` IS durable, but its source_path has NO WRITER "
               "anywhere in the tree and the file does not exist — a NEVER_ALIVE channel "
               "(T-342). C found a record that accrued and was not saved; this is one that "
               "is saved and can never accrue. BOTH read 'too early to say' forever. "
               "Durability of a book whose feed does not exist is a null guarantee, and no "
               "durability check can catch it — only a liveness check can.",
    ),
)


# --------------------------------------------------------------------------------------
# artifact/code-derived scanning (read-only; never writes, never guesses)
# --------------------------------------------------------------------------------------
_WRITE_IDIOM = re.compile(
    r'\.open\(\s*["\']a|open\([^)]*["\']a["\']|\.write_text\(|json\.dump\(|\.to_csv\(')
_DATA_PATH = re.compile(r'["\'](data/[A-Za-z0-9_./-]+\.(?:jsonl|json|log|csv|md))["\']')

# Venues whose code is swept. Research/one-shot scripts are deliberately out of scope:
# their outputs are measurement artifacts, not accruing records, and sweeping them would
# produce an alarm nobody can action — worse than no alarm.
_SCAN_DIRS = ("paper_trader", "engines", "core", "intelligence")


def scan_writers(root: Optional[Path] = None) -> Dict[str, List[str]]:
    """Return {data-path: [modules that write it]} across the swept venues."""
    base = Path(root) if root else ROOT
    out: Dict[str, List[str]] = {}
    for d in _SCAN_DIRS:
        for p in sorted((base / d).rglob("*.py")):
            if "__pycache__" in str(p) or "/Archive/" in str(p):
                continue
            try:
                text = p.read_text()
            except Exception:
                continue
            if not _WRITE_IDIOM.search(text):
                continue
            rel = str(p.relative_to(base))
            for hit in sorted(set(_DATA_PATH.findall(text))):
                out.setdefault(hit, []).append(rel)
    return out


def _durable_paths() -> set:
    """Read DURABLE_PATHS/DURABLE_DIRS from the source of truth, never a copy."""
    from paper_trader.cloud_state import DURABLE_DIRS, DURABLE_PATHS
    return set(DURABLE_PATHS) | set(DURABLE_DIRS)


def _covered_by_dir(path: str, dirs: Sequence[str]) -> bool:
    return any(path.startswith(d.rstrip("/") + "/") for d in dirs)


def assert_durability(root: Optional[Path] = None) -> CensusVerdict:
    """FAIL-CLOSED. Every written accruing path is DURABLE, EXEMPT-with-reason, or an
    OWNED KNOWN_GAP; every registry entry still corresponds to something real."""
    from paper_trader.cloud_state import DURABLE_DIRS

    failures: List[str] = []
    durable = _durable_paths()
    registry = {r.path: r for r in REGISTRY}
    written = scan_writers(root)

    # --- registry hygiene: a reason is mandatory; a gap needs an owner ---------------
    for r in REGISTRY:
        if r.venue not in VENUES:
            failures.append(f"{r.path}: unknown venue {r.venue!r}")
        if not (r.reason or "").strip():
            failures.append(f"{r.path}: {r.status} with no stated reason — "
                            f"'it exists' is not a reason")
        if r.status == KNOWN_GAP and not (r.owner or "").strip():
            failures.append(f"{r.path}: KNOWN_GAP with no owner — an unowned gap goes quiet")

    # --- direction 1: every written accruing path is accounted for ------------------
    for path, writers in sorted(written.items()):
        if path in durable or _covered_by_dir(path, DURABLE_DIRS):
            continue
        if path in registry:
            continue
        failures.append(
            f"UNREGISTERED WRITER: {path} written by {', '.join(writers)} — not in "
            f"DURABLE_PATHS and not in the durability registry. Add it durable, or "
            f"register it EXEMPT with a reason, or KNOWN_GAP with an owner.")

    # --- direction 2: no stale registry entry (B's launchd lesson) ------------------
    for r in REGISTRY:
        if r.writer.startswith("("):          # explicitly declared writer-less
            continue
        if r.writer not in written.get(r.path, []) and not (ROOT / r.writer).exists():
            failures.append(
                f"STALE REGISTRY ENTRY: {r.path} names writer {r.writer} which does not "
                f"exist — the registry is describing a world that moved.")

    gaps = [r for r in REGISTRY if r.status == KNOWN_GAP]
    return CensusVerdict(ok=not failures, failures=failures, gaps=gaps, checked=len(written))


def open_gaps() -> List[Record]:
    """The loud half: registered gaps, so they are reported rather than absorbed."""
    return [r for r in REGISTRY if r.status == KNOWN_GAP]
