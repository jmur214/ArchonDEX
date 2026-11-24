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

T-416 (2026-11-20) adds a LOCAL-ONLY options check (``_check_options``): the options
snapshot archive (scripts/archive_options_snapshots.py) runs only on this launchd path, so it
is judged here and deliberately NOT added to the shared ``_SNAPSHOT_FRESHNESS`` list, which
the cloud paper pulse also reads (the cloud never collects options; adding it there would
false-alarm every cloud run). The check re-judges the latest session's file by CONTENT (the
real-quote rule recomputed from raw columns) and is trading-day aware: on a weekend or
holiday it checks the previous session instead of alarming.

Exit codes:
  0 — every 24/7 snapshot source has >=1 row stamped today, and the options check passed
  1 — one or more sources have ZERO fresh rows, or the options check failed (names printed)
  2 — verifier itself broke (import/read error) — also a loud failure
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OPTIONS_REL = "data/macro_data/options"


def _now_utc() -> datetime:
    """The wall clock (tests pin it)."""
    return datetime.now(timezone.utc)


def _check_options(root: Path) -> tuple[bool, str]:
    """The options archive's own store check (local-only; see above). Never raises: a broken
    options check is its own FAIL line and must not mask the alt-data verdict."""
    try:
        from scripts.archive_options_snapshots import (DEFAULT_CONFIG, ET, load_config,
                                                       verify_store)

        return verify_store(root / OPTIONS_REL, load_config(DEFAULT_CONFIG),
                            _now_utc().astimezone(ET))
    except Exception as e:  # noqa: BLE001 - any breakage is this check's failure, loudly
        return False, f"FAILED: the options check broke ({type(e).__name__})"


def main() -> int:
    try:
        from paper_trader.altdata_archive import _SNAPSHOT_FRESHNESS, _fresh_rows

        today = _now_utc().astimezone().strftime("%Y-%m-%d")   # local date, as the rows are
        stale = []
        for label, rel, datecol in _SNAPSHOT_FRESHNESS:
            n = _fresh_rows(ROOT / rel, datecol, today)
            print(f"[verify-altdata] {label}: {n} rows @ {today}")
            if n == 0:
                stale.append(label)
        if stale:      # printed (and flushed) first: nothing in the options check can hide it
            print(f"[verify-altdata] FAIL — zero fresh rows: {', '.join(stale)}", flush=True)
        options_ok, options_msg = _check_options(ROOT)
        print(f"[verify-altdata] options: {options_msg}")
        if not options_ok:
            print("[verify-altdata] FAIL — options check (see the options line above)")
        if stale or not options_ok:
            return 1
        print("[verify-altdata] OK")
        return 0
    except Exception as e:  # a broken verifier must also be loud
        print(f"[verify-altdata] VERIFIER ERROR: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
