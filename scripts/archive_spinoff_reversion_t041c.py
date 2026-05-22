"""scripts/archive_spinoff_reversion_t041c.py
===============================================
T-041c-archive Part A: route a status='paused' → status='archived'
transition for `spinoff_reversion_v1` through the LifecycleJournal +
journal_apply mechanism.

Per CLAUDE.md: "Never manually edit data/governor/edges.yml... Engine
F manages lifecycle autonomously."

This script:
  1. Reads current registry; confirms spinoff_reversion_v1 is paused
  2. Appends a status_change JournalEntry
  3. Invokes journal_apply (non-dry-run) to commit the registry change
  4. Re-reads registry; asserts status == archived
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_a_alpha.edge_registry import EdgeRegistry  # noqa: E402
from engines.engine_f_governance.journal import (  # noqa: E402
    LifecycleJournal,
    make_status_change,
)
from scripts.journal_apply import apply  # noqa: E402

TARGET_EDGE_ID = "spinoff_reversion_v1"
NEW_STATUS = "archived"
ARCHIVE_REASON = "gauntlet_T-041b_paused_tier_masking_confound"
RUN_ID = "t041c_archive_2026_05_22"


def main() -> int:
    reg = EdgeRegistry()
    spec = reg.get(TARGET_EDGE_ID)
    if spec is None:
        print(f"[T-041c] {TARGET_EDGE_ID} not in registry — aborting",
              file=sys.stderr)
        return 1
    prior_status = spec.status
    print(f"[T-041c] before: {TARGET_EDGE_ID} status={prior_status!r}",
          flush=True)
    if prior_status == NEW_STATUS:
        print(f"[T-041c] already archived; nothing to do.")
        return 0

    journal = LifecycleJournal()
    entry = make_status_change(
        run_id=RUN_ID,
        edge_id=TARGET_EDGE_ID,
        new_status=NEW_STATUS,
        prior_status=prior_status,
        reason=ARCHIVE_REASON,
    )
    print(f"[T-041c] appending journal entry: {entry.to_json_line()}",
          flush=True)
    journal.append(entry)

    print("[T-041c] running journal_apply (non-dry-run)...", flush=True)
    result = apply(dry_run=False, verbose=True)
    print(f"[T-041c] apply result: processed={result.n_processed} "
          f"status_changes={result.n_status_changes}", flush=True)

    # Verify
    reg2 = EdgeRegistry()
    spec2 = reg2.get(TARGET_EDGE_ID)
    if spec2 is None or spec2.status != NEW_STATUS:
        print(
            f"[T-041c] FAILED verification — expected status={NEW_STATUS!r}, "
            f"got {spec2.status if spec2 else 'None'!r}",
            file=sys.stderr,
        )
        return 2
    print(f"[T-041c] after: {TARGET_EDGE_ID} status={spec2.status!r}  OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
