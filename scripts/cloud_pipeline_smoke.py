#!/usr/bin/env python3
"""scripts/cloud_pipeline_smoke.py — MANDATORY both-paths pre-flight before any
expensive cloud campaign (T-2026-06-24-215).

Why this exists
---------------
T-215 burned a ~30h full-cycle run discovering a SEAM bug that a 5-minute smoke
would have caught: `cloud_entrypoint.sh` ran the harness as `… | tee` under
`set -euo pipefail`, so when the harness census-FAILED (exit 2) the whole script
aborted BEFORE its forensics-upload step — census-failed cells uploaded NOTHING,
and the equity needed for the verdict was lost. The "upload artifacts even when
NON-CANONICAL" design was silently defeated. This is the orchestration/seam class
of bug: it only surfaces on the full expensive run, never in unit tests.

What it asserts
---------------
Run the REAL `cloud_entrypoint.sh` (the same script the campaign uses) on a TINY
(~1-month) window in TWO modes and assert BOTH upload their artifacts to S3:

  * PASS cell  — census-canonical config  → exit 0, artifacts in S3.
  * FAIL cell  — deliberately census-NON-CANONICAL → exit non-zero, BUT artifacts
                 STILL in S3 (this is the leg that regressed and cost the 30h).

A run-dir with `performance_summary.json` + the trade/equity CSVs must land under
`s3://<bucket>/<cell_id>/<run_id>/` for EACH cell. If the FAIL cell uploads
nothing, the pipeline is broken — fail loud, do NOT launch the campaign.

Usage
-----
    python -m scripts.cloud_pipeline_smoke --job-def archondex-backtest-t215 \
        [--window 2020-02-01:2020-03-13] [--keep]

Exit 0 iff BOTH cells uploaded a performance_summary.json (PASS cell additionally
census-canonical, FAIL cell additionally NON-canonical — i.e. the two paths are
genuinely distinct AND both persisted). Make this a required gate in the campaign
runbook: no `submit_arms_campaign` for a real campaign until this is green on the
image that campaign will use.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

ACCOUNT_ID = "407539788432"
REGION = "us-east-1"
RESULTS_BUCKET = f"archondex-results-{ACCOUNT_ID}"
JOB_QUEUE = "archondex-backtest-queue"
TERMINAL = {"SUCCEEDED", "FAILED"}
SMOKE_PREFIX = "t215-pipeline-smoke"

# A short, trade-dense window (COVID crash) so n_trades>0 is reliable on the
# PASS cell. ~6 trading weeks.
DEFAULT_WINDOW = "2020-02-01:2020-03-13"

# PASS cell: census-canonical. Price edges fire daily (no edges_blind), and we
# allowlist the slow fundamental + stray edges that a 1-month window can't
# exercise, plus the 2 known degenerate-stub names (SRCL/RX) for the panel.
PASS_DORMANT = (
    "value_earnings_yield_v1,value_book_to_market_v1,accruals_inv_sloan_v1,"
    "accruals_inv_asset_growth_v1,news_sentiment_edge"
)
PASS_PANEL_ALLOW = "8"  # generous on a tiny window; the point is upload, not the number


def aws(*args: str, _json: bool = True) -> str:
    cmd = ["aws", *args, "--region", REGION, "--profile", "archondex"]
    if _json:
        cmd += ["--output", "json"]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


@dataclass
class SmokeCell:
    label: str
    expect_canonical: bool
    env: list
    job_id: Optional[str] = None
    status: Optional[str] = None
    uploaded: bool = False
    census_canonical: Optional[bool] = None

    @property
    def cell_id(self) -> str:
        return f"{SMOKE_PREFIX}/{self.label}"

    def submit(self, job_def: str) -> None:
        out = aws(
            "batch", "submit-job",
            "--job-name", f"{SMOKE_PREFIX}-{self.label}".replace("_", "-"),
            "--job-queue", JOB_QUEUE,
            "--job-definition", job_def,
            "--container-overrides", json.dumps({"environment": self.env}),
            "--timeout", json.dumps({"attemptDurationSeconds": 3600}),
        )
        self.job_id = json.loads(out)["jobId"]


def _base_env(cell_id: str, start: str, end: str) -> list:
    # Mirrors submit_arms_campaign's per-cell env (PIT × realistic-cost substrate).
    patch = {
        "config/backtest_settings.json": {
            "use_historical_universe": True,
            "slippage_extra.realistic_retail_costs": True,
        },
        "config/portfolio_settings.json": {
            "phase1_composition_enabled": False,
            "mode": "mean_variance",
        },
    }
    return [
        {"name": "ARCHONDEX_RESULTS_BUCKET", "value": RESULTS_BUCKET},
        {"name": "ARCHONDEX_CELL_ID", "value": cell_id},
        {"name": "ARCHONDEX_CONFIG_PATCH_B64",
         "value": base64.b64encode(json.dumps(patch).encode()).decode()},
        {"name": "ARCHONDEX_START_DATE", "value": start},
        {"name": "ARCHONDEX_END_DATE", "value": end},
        {"name": "ARCHONDEX_REP", "value": "1"},
        {"name": "PYTHONHASHSEED", "value": "0"},
        {"name": "ARCHONDEX_HERMETIC", "value": "1"},
    ]


def build_cells(start: str, end: str) -> list:
    pass_env = _base_env(f"{SMOKE_PREFIX}/pass_canonical", start, end) + [
        {"name": "CENSUS_EXPECTED_DORMANT", "value": PASS_DORMANT},
        {"name": "CENSUS_PANEL_ALLOWLIST", "value": PASS_PANEL_ALLOW},
    ]
    # FAIL cell: NO allowlists → the slow edges are blind on a 1-month window →
    # census NON-CANONICAL. The whole point: it must STILL upload.
    fail_env = _base_env(f"{SMOKE_PREFIX}/fail_noncanonical", start, end)
    return [
        SmokeCell("pass_canonical", True, pass_env),
        SmokeCell("fail_noncanonical", False, fail_env),
    ]


def poll(cells: list, interval: int = 30, timeout_s: int = 3600) -> None:
    waited = 0
    while waited < timeout_s:
        pending = [c for c in cells if c.status not in TERMINAL]
        if not pending:
            return
        out = aws("batch", "describe-jobs", "--jobs", *[c.job_id for c in pending])
        by_id = {j["jobId"]: j for j in json.loads(out)["jobs"]}
        for c in pending:
            c.status = by_id.get(c.job_id, {}).get("status")
        done = sum(1 for c in cells if c.status in TERMINAL)
        print(f"  [{waited}s] {done}/{len(cells)} terminal "
              f"({', '.join(f'{c.label}={c.status}' for c in cells)})")
        if done == len(cells):
            return
        time.sleep(interval)
        waited += interval


def check_uploads(cells: list) -> None:
    for c in cells:
        out = aws("s3api", "list-objects-v2", "--bucket", RESULTS_BUCKET,
                  "--prefix", f"{c.cell_id}/",
                  "--query", "Contents[].Key")
        keys = json.loads(out) or []
        c.uploaded = any(k.endswith("performance_summary.json") for k in keys)
        # read the manifest's canonical flag if present
        man = [k for k in keys if k.endswith("manifest.json")]
        if man:
            raw = subprocess.run(
                ["aws", "s3", "cp", f"s3://{RESULTS_BUCKET}/{man[0]}", "-",
                 "--region", REGION, "--profile", "archondex"],
                check=True, capture_output=True, text=True).stdout
            try:
                c.census_canonical = json.loads(raw).get("census_canonical")
            except Exception:
                c.census_canonical = None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-def", required=True,
                    help="Batch job-def the campaign will use (smoke runs the SAME image).")
    ap.add_argument("--window", default=DEFAULT_WINDOW, help="start:end (YYYY-MM-DD:YYYY-MM-DD)")
    ap.add_argument("--keep", action="store_true", help="keep the S3 smoke artifacts")
    args = ap.parse_args()
    start, end = args.window.split(":")

    cells = build_cells(start, end)
    print(f"[smoke] both-paths pipeline gate on {args.job_def} (window {start}→{end})")
    for c in cells:
        c.submit(args.job_def)
        print(f"  submitted {c.label} → {c.job_id}")
    poll(cells)
    check_uploads(cells)

    print("\n==== SMOKE RESULT ====")
    ok = True
    for c in cells:
        canon_ok = (c.census_canonical == c.expect_canonical) if c.uploaded else False
        verdict = "OK" if (c.uploaded and canon_ok) else "FAIL"
        if verdict != "OK":
            ok = False
        print(f"  {c.label:18} status={c.status:9} uploaded={c.uploaded} "
              f"census_canonical={c.census_canonical} (expect {c.expect_canonical}) [{verdict}]")

    if not args.keep:
        for c in cells:
            subprocess.run(["aws", "s3", "rm", f"s3://{RESULTS_BUCKET}/{c.cell_id}/",
                            "--recursive", "--region", REGION, "--profile", "archondex",
                            "--only-show-errors"], check=False)

    if ok:
        print("\n[smoke] PASS — both census paths persisted artifacts to S3. Campaign may launch.")
        return 0
    print("\n[smoke] FAIL — a census path did NOT upload (or canonical flag wrong). "
          "DO NOT launch the campaign; the pipeline would lose results. "
          "(This is exactly the T-215 entrypoint pipefail bug.)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
