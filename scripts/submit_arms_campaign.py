"""scripts/submit_arms_campaign.py
=================================
T-2026-05-23-085: generic per-arm A/B campaign launcher on AWS Batch.

Generalization of `scripts/submit_substrate_run.py` (hardcoded for
substrate-measurement reps × arms shape). This script lets the director
or an agent submit ANY arm-grid A/B campaign with per-cell config
patches, without re-baking the Docker image.

Each cell is one (arm, year, rep) combination. Each cell runs as one
AWS Batch job using the `:dev` image and `cloud_entrypoint.sh`. The
entrypoint applies the per-cell config patch (delivered via the
`ARCHONDEX_CONFIG_PATCH_B64` env var) before invoking the harness.

Usage
-----
A campaign is defined by a JSON spec file with this shape:

    {
      "campaign_id": "t057b-confidence-gate-flip-verify",
      "years": [2021, 2022, 2023, 2024, 2025],
      "reps": 5,
      "arms": {
        "arm0_off": {
          "config_patch": {}                        // baseline (no patch)
        },
        "arm2_n3": {
          "config_patch": {
            "config/alpha_settings.json": {
              "confidence_gate.enabled": true,
              "confidence_gate.n_threshold": 3
            }
          }
        }
      }
    }

    python -m scripts.submit_arms_campaign --spec /tmp/t057b_spec.json

Outputs
-------
- Submits N = reps × len(years) × len(arms) Batch jobs in parallel
- Polls Batch describe-jobs until all reach terminal state
- Fetches per-cell manifests from S3
- Writes a CSV + JSON summary to
  `data/cloud_runs/<campaign_id>_<launch_ts>.{csv,json}`

Per-cell S3 prefix
------------------
  s3://archondex-results-<acct>/<campaign_id>/<arm>/<year>/rep<rep>/<run_id>/

Cost
----
Fargate Spot ~$0.02/hour per cell; typical cell ~10-30 min on extended
substrate. A 75-cell campaign runs ~$0.40-1.20 total.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ACCOUNT_ID = "407539788432"
REGION = "us-east-1"
RESULTS_BUCKET = f"archondex-results-{ACCOUNT_ID}"
JOB_QUEUE = "archondex-backtest-queue"
JOB_DEFINITION = "archondex-backtest"  # uses latest revision
TERMINAL_STATES = {"SUCCEEDED", "FAILED"}


def aws(*args: str) -> str:
    """Run an AWS CLI command via the `archondex` profile + `us-east-1`.
    Returns stdout. Raises on non-zero exit."""
    cmd = [
        "aws", *args, "--region", REGION, "--profile", "archondex",
        "--output", "json",
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


@dataclass
class Cell:
    campaign_id: str
    arm: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    window_label: str  # "2024" for single year, "2014-2025" for multi-year
    rep: int
    config_patch: Dict[str, Dict[str, object]]
    job_id: Optional[str] = None
    status: Optional[str] = None
    manifest: Optional[Dict] = field(default=None)

    @property
    def cell_id(self) -> str:
        return f"{self.campaign_id}/{self.arm}/{self.window_label}/rep{self.rep}"

    @property
    def s3_prefix(self) -> str:
        return f"s3://{RESULTS_BUCKET}/{self.cell_id}"

    @property
    def year_int_for_legacy(self) -> Optional[int]:
        """Return integer year iff the window is a single calendar year
        (start = YYYY-01-01, end = YYYY-12-31). Otherwise None.
        Used to populate the legacy ARCHONDEX_YEAR env var for
        backward compat in containers that only know about --year.
        """
        if (self.start_date.endswith("-01-01") and
            self.end_date.endswith("-12-31") and
            self.start_date[:4] == self.end_date[:4]):
            try:
                return int(self.start_date[:4])
            except ValueError:
                return None
        return None

    def submit(self, job_definition: str = JOB_DEFINITION,
               timeout_seconds: Optional[int] = None) -> str:
        """Submit one Batch job for this cell. Returns the AWS job ID.

        ``timeout_seconds`` overrides the job definition's default
        attemptDurationSeconds (typically 1800s). Required for multi-year
        windows where a 12-yr cell needs ~7,200s — the default 30-min
        timeout would kill the job mid-backtest.
        """
        patch_b64 = base64.b64encode(
            json.dumps(self.config_patch).encode()
        ).decode()
        env = [
            {"name": "ARCHONDEX_RESULTS_BUCKET", "value": RESULTS_BUCKET},
            {"name": "ARCHONDEX_CELL_ID",        "value": self.cell_id},
            {"name": "ARCHONDEX_CONFIG_PATCH_B64", "value": patch_b64},
            # T-053b: cell window passes through as start/end. The
            # entrypoint prefers these over ARCHONDEX_YEAR. We ALSO
            # set ARCHONDEX_YEAR for single-year windows so any
            # downstream tooling that grepped for it still works
            # (back-compat).
            {"name": "ARCHONDEX_START_DATE",     "value": self.start_date},
            {"name": "ARCHONDEX_END_DATE",       "value": self.end_date},
            {"name": "ARCHONDEX_REP",            "value": str(self.rep)},
            {"name": "PYTHONHASHSEED",           "value": "0"},
            # T-142: cloud cells run HERMETIC by default — yfinance network
            # fallbacks are blocked loudly instead of burning wall-time
            # (T-134 profile: 52% of cell wall) and risking split-only-cache
            # contamination (T-088 hazard note in data_manager). Blocked-call
            # lines in CloudWatch double as the substrate-gap inventory.
            # Local runs are unaffected (env unset = off).
            {"name": "ARCHONDEX_HERMETIC",       "value": "1"},
        ]
        legacy_year = self.year_int_for_legacy
        if legacy_year is not None:
            env.append({"name": "ARCHONDEX_YEAR", "value": str(legacy_year)})
        # Job name: alphanumeric, dashes only — Batch is strict
        safe_name = (
            f"{self.campaign_id}-{self.arm}-{self.window_label}-r{self.rep}"
            .replace("_", "-").replace(".", "-").lower()[:128]
        )
        submit_args = [
            "batch", "submit-job",
            "--job-name", safe_name,
            "--job-queue", JOB_QUEUE,
            "--job-definition", job_definition,
            "--container-overrides", json.dumps({"environment": env}),
        ]
        if timeout_seconds is not None:
            submit_args.extend([
                "--timeout", json.dumps({"attemptDurationSeconds": int(timeout_seconds)}),
            ])
        result_json = aws(*submit_args)
        self.job_id = json.loads(result_json)["jobId"]
        return self.job_id


def load_spec(spec_path: Path) -> Dict:
    """Load + validate the campaign spec JSON.

    Schema (post-T-053b):
        campaign_id: str
        windows: list[{start: YYYY-MM-DD, end: YYYY-MM-DD, label?: str}]
                 OR equivalent `years: list[int]` (legacy, desugared)
        reps: int
        arms: dict[str, {config_patch: {file_path: {dotted_key: value}}}]

    Exactly one of `windows` or `years` must be present. `years` is
    desugared in build_cells() to single-year windows so the rest of
    the launcher uses the unified Cell shape.
    """
    spec = json.loads(spec_path.read_text())
    has_windows = "windows" in spec
    has_years = "years" in spec
    if has_windows and has_years:
        raise SystemExit("Spec must specify exactly one of 'windows' or 'years', not both")
    if not (has_windows or has_years):
        raise SystemExit("Spec must specify either 'windows' or 'years'")
    required = {"campaign_id", "reps", "arms"}
    missing = required - set(spec.keys())
    if missing:
        raise SystemExit(f"Spec missing required keys: {missing}")
    # T-2026-06-10-134 ADDENDUM: the planned optional-reps-default-1 is ON
    # HOLD — A's T-128 found cross-task determinism broken (placement
    # lottery; two canon attractors per image). Reps stay spec-required
    # until T-140 lands; then reps→1 + a CROSS-TASK canary unanimity check
    # become valid (the canary machinery below is already cross-task: each
    # canary rep is its own Batch task).
    if not isinstance(spec["arms"], dict) or not spec["arms"]:
        raise SystemExit("Spec 'arms' must be a non-empty dict")
    if has_windows:
        if not isinstance(spec["windows"], list) or not spec["windows"]:
            raise SystemExit("Spec 'windows' must be a non-empty list")
        for w in spec["windows"]:
            if not isinstance(w, dict) or "start" not in w or "end" not in w:
                raise SystemExit(f"Each window must be {{start, end, label?}}; got {w}")
    return spec


def _window_label(start: str, end: str, override: Optional[str] = None) -> str:
    """Build the S3 path segment for a window. Override takes precedence;
    otherwise auto-generate from the dates."""
    if override:
        return override
    # Single calendar year: "YYYY"
    if (start.endswith("-01-01") and end.endswith("-12-31") and
        start[:4] == end[:4]):
        return start[:4]
    # Multi-year span: "YYYY-YYYY"
    if start[:4] != end[:4]:
        return f"{start[:4]}-{end[:4]}"
    # Sub-year: "YYYY-MM-DD_YYYY-MM-DD"
    return f"{start}_{end}"


def build_cells(spec: Dict) -> List[Cell]:
    """Build the list of cells from spec. Desugars `years` to single-year
    windows if present."""
    if "windows" in spec:
        windows = [
            (w["start"], w["end"], w.get("label"))
            for w in spec["windows"]
        ]
    else:
        windows = [
            (f"{y}-01-01", f"{y}-12-31", None)
            for y in spec["years"]
        ]
    cells = []
    for arm, arm_cfg in spec["arms"].items():
        patch = arm_cfg.get("config_patch", {})
        for start, end, label_override in windows:
            label = _window_label(start, end, label_override)
            for rep in range(1, spec["reps"] + 1):
                cells.append(Cell(
                    campaign_id=spec["campaign_id"],
                    arm=arm,
                    start_date=start,
                    end_date=end,
                    window_label=label,
                    rep=rep,
                    config_patch=patch,
                ))
    return cells


# T-2026-06-10-134: per-campaign determinism canary.
# With the rep default at 1, the campaign needs an in-band check that the
# determinism floor still holds on the exact image/config it runs.
# 3 reps of ONE cheap cell (single-year window, the spec's FIRST arm) ride
# along with every campaign; if their canon_md5s are not 3/3 identical the
# campaign result is declared UNTRUSTED (exit code 2) — that's a finding
# (the floor broke: image, base, harness, or substrate changed), not noise.
CANARY_ARM_PREFIX = "_canary"
CANARY_YEAR = "2022"          # well-populated reference year
CANARY_REPS = 3


def build_canary_cells(spec: Dict) -> List[Cell]:
    """3-rep single-year canary on the spec's first arm."""
    first_arm = next(iter(spec["arms"]))
    patch = spec["arms"][first_arm].get("config_patch", {})
    return [
        Cell(
            campaign_id=spec["campaign_id"],
            arm=f"{CANARY_ARM_PREFIX}_{first_arm}",
            start_date=f"{CANARY_YEAR}-01-01",
            end_date=f"{CANARY_YEAR}-12-31",
            window_label=CANARY_YEAR,
            rep=rep,
            config_patch=patch,
        )
        for rep in range(1, CANARY_REPS + 1)
    ]


def check_canary(canary_cells: List[Cell]) -> bool:
    """True if all canary canons are present and identical.

    The canon lives in the fetched manifest dict (`cell.manifest`), set by
    fetch_manifests() — NOT a top-level Cell attribute.
    """
    def canon(c: Cell) -> Optional[str]:
        return (c.manifest or {}).get("canon_md5")

    md5s = {canon(c) for c in canary_cells if canon(c)}
    ok = (len(md5s) == 1
          and sum(1 for c in canary_cells if canon(c)) == len(canary_cells))
    if ok:
        print(f"[canary] PASS — {len(canary_cells)}/{len(canary_cells)} bitwise-identical "
              f"canon {next(iter(md5s))}")
    else:
        print("=" * 72)
        print("[canary] *** FAIL — DETERMINISM FLOOR BROKEN ***")
        for c in canary_cells:
            print(f"  {c.cell_id}: canon={canon(c)}")
        print("[canary] The campaign's results are UNTRUSTED. Do not compare arms.")
        print("[canary] Investigate: image change? base digest? harness? substrate?")
        print("=" * 72)
    return ok


def submit_all(cells: List[Cell], job_definition: str,
               max_workers: int = 20,
               timeout_seconds: Optional[int] = None) -> None:
    """Submit cells in parallel (Batch handles N concurrent submits fine).

    ``timeout_seconds`` overrides the job definition default for every
    cell. Required for multi-year windows.
    """
    print(f"[campaign] Submitting {len(cells)} cells (parallel={max_workers}, "
          f"timeout={timeout_seconds or 'job-def-default'}s)...")
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(cell.submit, job_definition, timeout_seconds): cell
            for cell in cells
        }
        for fut in as_completed(futures):
            cell = futures[fut]
            try:
                jid = fut.result()
                print(f"  submitted: {cell.cell_id} -> {jid[:8]}...")
            except Exception as exc:
                print(f"  FAILED submit: {cell.cell_id}: {exc}", file=sys.stderr)


def poll_until_terminal(cells: List[Cell], interval_sec: int = 30, timeout_sec: int = 7200) -> None:
    """Poll Batch describe-jobs until all cells reach SUCCEEDED or FAILED."""
    cells_by_jid = {c.job_id: c for c in cells if c.job_id}
    start = time.time()
    while True:
        pending = [jid for jid, c in cells_by_jid.items() if c.status not in TERMINAL_STATES]
        if not pending:
            return
        if time.time() - start > timeout_sec:
            print(f"[campaign] TIMEOUT after {timeout_sec}s; {len(pending)} cells still pending")
            return
        # Batch describe-jobs accepts up to 100 IDs at a time
        for chunk_start in range(0, len(pending), 100):
            chunk = pending[chunk_start:chunk_start + 100]
            result_json = aws("batch", "describe-jobs", "--jobs", *chunk)
            jobs = json.loads(result_json).get("jobs", [])
            for j in jobs:
                cell = cells_by_jid.get(j["jobId"])
                if cell:
                    cell.status = j["status"]
        # Summary
        n_succeeded = sum(1 for c in cells if c.status == "SUCCEEDED")
        n_failed = sum(1 for c in cells if c.status == "FAILED")
        n_total = len(cells_by_jid)
        elapsed = int(time.time() - start)
        print(f"[campaign] t+{elapsed}s: {n_succeeded} ok / {n_failed} fail / {n_total - n_succeeded - n_failed} pending")
        if n_succeeded + n_failed == n_total:
            return
        time.sleep(interval_sec)


def fetch_manifests(cells: List[Cell]) -> None:
    """Pull per-cell manifest.json from S3 for cells that SUCCEEDED.

    The entrypoint uploads to `<cell_id>/<run_id>/manifest.json` (the
    run_id subdirectory is set by the entrypoint, unknown to us at
    submit-time). We list the cell prefix to discover the run_id, then
    fetch that manifest.
    """
    for cell in cells:
        if cell.status != "SUCCEEDED":
            continue
        try:
            # List the cell prefix to find the run_id subdir(s)
            ls_result = subprocess.run(
                ["aws", "s3", "ls", f"{cell.s3_prefix}/",
                 "--profile", "archondex", "--region", REGION],
                check=True, capture_output=True, text=True,
            )
            # Output lines like:  "                           PRE c02f582b-.../"
            run_dirs = [
                line.strip().rstrip("/").split()[-1]
                for line in ls_result.stdout.splitlines()
                if "PRE " in line
            ]
            if not run_dirs:
                print(f"  no run_id subdir found under {cell.s3_prefix}", file=sys.stderr)
                continue
            # Most-recent run_id wins if multiple (re-runs); ls returns
            # them in name-sort order which is fine for uuid4
            run_id = run_dirs[-1]
            cat_result = subprocess.run(
                ["aws", "s3", "cp", f"{cell.s3_prefix}/{run_id}/manifest.json", "-",
                 "--profile", "archondex", "--region", REGION],
                check=True, capture_output=True, text=True,
            )
            cell.manifest = json.loads(cat_result.stdout)
        except subprocess.CalledProcessError as exc:
            print(f"  manifest fetch failed for {cell.cell_id}: {exc.stderr}", file=sys.stderr)
        except (ValueError, IndexError) as exc:
            print(f"  manifest parse failed for {cell.cell_id}: {exc}", file=sys.stderr)


def write_summary(cells: List[Cell], campaign_id: str, launch_ts: str) -> None:
    out_dir = REPO / "data/cloud_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{campaign_id}_{launch_ts}.csv"
    json_path = out_dir / f"{campaign_id}_{launch_ts}.json"

    # CSV — post-T-053b columns; window_label replaces year for the
    # human-readable column, with start/end_date for the precise window
    rows = ["cell_id,arm,window_label,start_date,end_date,rep,status,job_id,run_id,canon_md5,sharpe,s3_prefix"]
    for c in cells:
        m = c.manifest or {}
        rows.append(
            f"{c.cell_id},{c.arm},{c.window_label},{c.start_date},{c.end_date},"
            f"{c.rep},{c.status or ''},{c.job_id or ''},"
            f"{m.get('run_id', '')},{m.get('canon_md5', '')},{m.get('sharpe', '')},{c.s3_prefix}"
        )
    csv_path.write_text("\n".join(rows) + "\n")

    # JSON
    json_path.write_text(json.dumps({
        "campaign_id": campaign_id,
        "launch_ts": launch_ts,
        "n_cells": len(cells),
        "n_succeeded": sum(1 for c in cells if c.status == "SUCCEEDED"),
        "n_failed": sum(1 for c in cells if c.status == "FAILED"),
        "cells": [
            {"cell_id": c.cell_id, "arm": c.arm,
             "window_label": c.window_label,
             "start_date": c.start_date, "end_date": c.end_date,
             "rep": c.rep,
             "status": c.status, "job_id": c.job_id, "manifest": c.manifest,
             "s3_prefix": c.s3_prefix}
            for c in cells
        ],
    }, indent=2, default=str))

    print()
    print(f"[campaign] summary: {csv_path.relative_to(REPO)}")
    print(f"[campaign] json:    {json_path.relative_to(REPO)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help="Campaign spec JSON path")
    ap.add_argument("--job-def", default=JOB_DEFINITION,
                    help=f"Batch job definition (default {JOB_DEFINITION})")
    ap.add_argument("--poll-interval", type=int, default=30,
                    help="Seconds between Batch describe-jobs polls (default 30)")
    ap.add_argument("--timeout", type=int, default=14400,
                    help="Total seconds (launcher-side) to wait before bailing (default 14400=4hr)")
    ap.add_argument("--job-timeout", type=int, default=None,
                    help="Per-job timeout override (attemptDurationSeconds). "
                         "Default: use the job definition's value (typically 1800s). "
                         "REQUIRED for multi-year windows — 12-yr cells need ~7200s, "
                         "single-year ~1800s.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be submitted; do not submit.")
    ap.add_argument("--reps", type=int, default=None,
                    help="Override the spec's reps (spec default is 1 since "
                         "T-134; use 3 for explicit determinism checks).")
    ap.add_argument("--no-canary", action="store_true",
                    help="Skip the 3-rep determinism canary (NOT recommended "
                         "— the canary is the safety net that lets reps "
                         "default to 1).")
    args = ap.parse_args()

    spec = load_spec(Path(args.spec))
    if args.reps is not None:
        spec["reps"] = args.reps
    cells = build_cells(spec)
    canary_cells = [] if args.no_canary else build_canary_cells(spec)
    launch_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    n_windows = (len(spec["windows"]) if "windows" in spec
                 else len(spec.get("years", [])))
    print(f"[campaign] {spec['campaign_id']}")
    print(f"[campaign] {len(cells)} cells "
          f"({len(spec['arms'])} arms × {n_windows} windows × {spec['reps']} reps)"
          + (f" + {len(canary_cells)} canary" if canary_cells else " (canary SKIPPED)"))

    if args.dry_run:
        print("[campaign] DRY RUN — would submit:")
        for c in (canary_cells + cells)[:8]:
            print(f"  {c.cell_id}  patch={list(c.config_patch.keys())}")
        if len(canary_cells) + len(cells) > 8:
            print(f"  ... and {len(canary_cells) + len(cells) - 8} more")
        return 0

    all_cells = canary_cells + cells
    submit_all(all_cells, args.job_def, timeout_seconds=args.job_timeout)
    poll_until_terminal(all_cells, args.poll_interval, args.timeout)
    fetch_manifests(all_cells)
    write_summary(all_cells, spec["campaign_id"], launch_ts)

    canary_ok = check_canary(canary_cells) if canary_cells else True
    n_failed = sum(1 for c in all_cells if c.status == "FAILED")
    if not canary_ok:
        return 2  # determinism floor broke — results untrusted
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
