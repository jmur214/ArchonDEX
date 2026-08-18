"""T-341b — the similarity-panel REFRESH job + its receipt.

THE DEFECT (D's T-341 spec): data/edgar/similarity_panel.parquet went 8 weeks stale
with NO CLOCK. Nothing was due to refresh it and nothing would have said so.

WHY A RECEIPT, NOT JUST max(decision_date) — the design point that matters:
aging the panel's newest decision_date CONFLATES two different states:
    (a) "no new 10-Ks were filed"  (healthy — filings are seasonal: 2026 ran
        Feb 408 -> Jun 5, a 80x swing), and
    (b) "we never ran the refresh"  (a dead clock).
Both look identical in the artifact. The census contract is explicit that NOT_DUE is
legitimate ONLY when artifact-verifiable — "probably no new filings" is the same
silence the census exists to eliminate. So the refresh writes its OWN receipt and the
clock ages THAT: a refresh that ran and found nothing is ADVANCED (and says so); a
refresh that never ran is a MISS. The two can no longer be confused.

Cadence (measured, not guessed): distinct decision-date gaps are median 2d, p95 14d,
MAX 35d all-time (25d in the 2024+ era). A 45-day refresh budget clears the largest
natural lull with margin while still catching the 53-day stall that prompted this.

Usage:  python -m scripts.refresh_similarity_panel_t341b [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = Path("/Users/jacksonmurphy/Dev/trading_machine-2")
PANEL = STORE / "data" / "edgar" / "similarity_panel.parquet"
RECEIPT = STORE / "data" / "edgar" / "similarity_panel_refresh.json"
REFRESH_BUDGET_DAYS = 45


def panel_stats() -> dict:
    import pandas as pd
    if not PANEL.exists():
        return {"rows": 0, "newest_decision_date": None, "error": "panel missing"}
    d = pd.read_parquet(PANEL)
    dd = pd.to_datetime(d["decision_date"], errors="coerce").dropna()
    return {"rows": int(len(d)),
            "newest_decision_date": str(dd.max().date()) if len(dd) else None,
            "distinct_decision_dates": int(dd.nunique()),
            "parse_ok_frac": (round(float(d["ok"].mean()), 4) if "ok" in d.columns else None)}


def refresh(dry_run: bool = False) -> dict:
    """Run the T-237 similarity stage, then write the receipt REGARDLESS of whether
    new rows appeared — 'ran and found nothing' is a healthy, recordable outcome."""
    before = panel_stats()
    ran, rc, err = False, None, None
    if not dry_run:
        try:
            p = subprocess.run(
                [sys.executable, "-m", "scripts.lazy_prices.similarity_t237", "all"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=3600)
            ran, rc = True, p.returncode
            if rc != 0:
                err = (p.stderr or p.stdout or "")[-400:]
        except Exception as exc:
            ran, rc, err = True, -1, f"{type(exc).__name__}: {exc}"
    after = panel_stats()
    receipt = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "ran": ran, "returncode": rc, "error": err,
        "rows_before": before.get("rows"), "rows_after": after.get("rows"),
        "rows_added": (after.get("rows") or 0) - (before.get("rows") or 0),
        "newest_decision_date": after.get("newest_decision_date"),
        "parse_ok_frac": after.get("parse_ok_frac"),
        "budget_days": REFRESH_BUDGET_DAYS,
        "_schema": "similarity_panel_refresh/v1",
    }
    if not dry_run:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, indent=2))
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--receipt-only", action="store_true",
                    help="write the receipt from the CURRENT panel without rebuilding "
                         "(bootstraps the clock without a 1hr EDGAR re-parse)")
    a = ap.parse_args()
    if a.receipt_only:
        s = panel_stats()
        r = {"refreshed_at": datetime.now(timezone.utc).isoformat(), "ran": False,
             "returncode": None, "error": None, "rows_before": s.get("rows"),
             "rows_after": s.get("rows"), "rows_added": 0,
             "newest_decision_date": s.get("newest_decision_date"),
             "parse_ok_frac": s.get("parse_ok_frac"),
             "budget_days": REFRESH_BUDGET_DAYS,
             "note": "receipt-only bootstrap: panel NOT rebuilt; clock starts from here",
             "_schema": "similarity_panel_refresh/v1"}
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(r, indent=2))
        print(json.dumps(r, indent=2))
        return 0
    print(json.dumps(refresh(a.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
