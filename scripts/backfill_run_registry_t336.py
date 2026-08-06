"""T-336 Part 1(a) — refresh the run registry that feeds compute_n_effective.

THE PROBLEM: the registry has been FROZEN at 125 rows since 2026-05-08 (it is built
by scanning run DIRECTORIES, and the project moved to task-based measurement runs
whose artifacts don't land there), while CURRENT_STATE reports honest N ≈ 260+. So
`compute_n_effective()` — the input to every DSR/MBL deflation — has been reporting
125 when the truth is ~2x that. Everything downstream under-deflates.

THE RECONSTRUCTION METHOD (documented, auditable, conservative):
  1. KEEP every existing run-dir-derived row untouched (source='run_dir').
  2. Parse `docs/State/TASK_LEDGER.md` for each task row's recorded N increment —
     the forms actually used in the ledger: `N_trials += <k>`, `N+=<k>`, `N+= <k>`.
     Each increment is inserted as <k> synthetic rows tagged source='ledger:<task_id>'.
  3. A trial is a trial: a ledger-recorded N+=1 is exactly as real, for
     multiple-testing purposes, as a run-dir row. What differs is PROVENANCE, so the
     `source` column records it and every reconstructed row is reversible/auditable.
  4. Rows are keyed `ledger:<task_id>:<i>` → the backfill is IDEMPOTENT (re-running
     does not double-count).
  5. `N+=0` rows are recorded as ZERO trials (re-analyses of existing runs consume no
     new multiple-testing budget) — parsed and skipped, not silently dropped.

HONEST LIMITS (stated, not hidden):
  * The ledger is the project's own record of N; if a measured task failed to record
    its increment, this backfill cannot invent it. So the result is a LOWER BOUND on
    honest N — which is the conservative direction for a deflation input only in the
    sense that it is *less* wrong than 125; it is still potentially an undercount.
  * No PCA/correlation reduction is applied (same policy as compute_n_effective's own
    docstring): raw count = honest upper bound per trial, no clustering credit.

Usage:  python -m scripts.backfill_run_registry_t336 [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LEDGER = ROOT / "docs" / "State" / "TASK_LEDGER.md"
DB = ROOT / "data" / "observability" / "run_registry.sqlite"

# the N-increment forms actually present in the ledger
_N_PAT = re.compile(r"N_trials\s*\+=\s*(\d+)|N\s*\+=\s*(\d+)", re.I)
_TASK_PAT = re.compile(r"^\|\s*(T-[0-9A-Za-z\-\.]+)\s*\|")


def parse_ledger(path: Path = LEDGER):
    """-> (rows, total_increment, zero_rows). One entry per task row that records N."""
    rows, total, zeros = [], 0, 0
    for line in path.read_text().splitlines():
        m = _TASK_PAT.match(line)
        if not m:
            continue
        task = m.group(1)
        hits = _N_PAT.findall(line)
        if not hits:
            continue
        k = sum(int(a or b) for a, b in hits)
        if k == 0:
            zeros += 1                      # explicit N+=0 → zero trials, recorded
            continue
        rows.append((task, k))
        total += k
    return rows, total, zeros


def ensure_source_column(conn: sqlite3.Connection) -> None:
    cols = [r[1] for r in conn.execute("pragma table_info(runs)")]
    if "source" not in cols:
        conn.execute("alter table runs add column source text")
        conn.execute("update runs set source='run_dir' where source is null")


def backfill(dry_run: bool = False) -> dict:
    conn = sqlite3.connect(DB)
    ensure_source_column(conn)
    before = conn.execute("select count(*) from runs").fetchone()[0]
    ledger_rows, total, zeros = parse_ledger()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for task, k in ledger_rows:
        for i in range(k):
            rid = f"ledger:{task}:{i}"
            if conn.execute("select 1 from runs where run_id=?", (rid,)).fetchone():
                continue                    # idempotent
            if not dry_run:
                conn.execute(
                    "insert into runs (run_id, snapshot_at, source) values (?,?,?)",
                    (rid, now, f"ledger:{task}"))
            inserted += 1
    if not dry_run:
        conn.commit()
    after = conn.execute("select count(*) from runs").fetchone()[0]
    by_src = dict(conn.execute(
        "select coalesce(source,'run_dir'), count(*) from runs group by 1").fetchall())
    conn.close()
    return {"before": before, "after": after, "inserted": inserted,
            "ledger_tasks": len(ledger_rows), "ledger_total_N": total,
            "zero_N_rows": zeros, "by_source": by_src}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = backfill(a.dry_run)
    print(f"[T336-a] registry backfill {'(DRY RUN)' if a.dry_run else ''}")
    print(f"  ledger task-rows carrying N : {r['ledger_tasks']}  (total N recorded {r['ledger_total_N']})")
    print(f"  explicit N+=0 rows (0 trials): {r['zero_N_rows']}")
    print(f"  registry rows  {r['before']} -> {r['after']}   (+{r['inserted']})")
    print(f"  by source: {r['by_source']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
