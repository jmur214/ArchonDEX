"""
scripts/verify_altdata_snapshot.py
==================================
Fail-LOUD verifier for the launchd alt-data archiver path (fresh-eyes
finding #1, 2026-07-08): the T-136 archivers return 0 unconditionally and
report failures as strings, so the wrapper could never detect silent
capture loss. This verifier makes the launchd path fail-closed at the
process-exit layer: it checks that TODAY's snap_date rows actually landed
in the 24/7 market-snapshot parquets (the sources where "zero fresh rows"
can only mean breakage, never a quiet market).

Reuses the SAME source list + freshness logic as the cloud pulse's
orchestrator (paper_trader/altdata_archive.py) so the two paths cannot
drift on what "fresh" means.

Exit codes:
  0 — every 24/7 snapshot source has >=1 row stamped today
  1 — one or more sources have ZERO fresh rows (names printed)
  2 — verifier itself broke (import/read error) — also a loud failure
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import pandas as pd

        from paper_trader.altdata_archive import _SNAPSHOT_FRESHNESS, _fresh_rows

        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        stale = []
        for label, rel, datecol in _SNAPSHOT_FRESHNESS:
            n = _fresh_rows(ROOT / rel, datecol, today)
            print(f"[verify-altdata] {label}: {n} rows @ {today}")
            if n == 0:
                stale.append(label)
        if stale:
            print(f"[verify-altdata] FAIL — zero fresh rows: {', '.join(stale)}")
            return 1
        print("[verify-altdata] OK")
        return 0
    except Exception as e:  # a broken verifier must also be loud
        print(f"[verify-altdata] VERIFIER ERROR: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
