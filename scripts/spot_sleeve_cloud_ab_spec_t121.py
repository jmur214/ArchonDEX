"""T-121 cloud A/B spec for the spot sleeve integration — full 16/26-yr.

PER INBOX: this spec is BUILT + LOCALLY-VERIFIED but **NOT LAUNCHED**.
The cloud launch holds for T-109's fresh ECR image (the existing :dev
image predates T-120/T-121 and would silently no-op the new flag).

When the director signals the image is ready:
    python scripts/spot_sleeve_cloud_ab_spec_t121.py --launch

Arms:
    arm0_off                  — spot_sleeve_enabled = False (baseline)
    arm1_on_25pct             — spot_sleeve_enabled = True, capital_pct = 0.25
    arm2_on_30pct             — spot_sleeve_enabled = True, capital_pct = 0.30

Windows (canonical T-115 deep substrates):
    16-yr: 2010-01-01 → 2025-12-31 (the T-092 16yr arm0_off best window)
    26-yr: 2000-01-01 → 2025-12-31 (the T-092 26yr 2008-inclusive substrate)

5 reps per (arm × window) for determinism + bootstrap CI substrate.
Total cells: 3 arms × 2 windows × 5 reps = 30 cells.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


CAMPAIGN_SPEC = {
    "campaign_name": "spot-sleeve-integration-t121",
    "task_id": "T-2026-06-06-121",
    "description": (
        "Integrated A/B of the spot 8-ETF sleeve at 25% and 30% capital "
        "allocation vs the production baseline (arm0_off). The integrated "
        "result is the TRUE A/B — the T-115 analytical partition was an "
        "external linear combination; this is the in-engine semantics."
    ),
    "arms": [
        {
            "arm_id": "arm0_off",
            "label": "Baseline (sleeve OFF)",
            "config_patches": {
                "portfolio_settings.json": {
                    "spot_sleeve_enabled": False,
                },
            },
        },
        {
            "arm_id": "arm1_on_25pct",
            "label": "Spot sleeve ON @ 25% capital (T-115 recommended allocation)",
            "config_patches": {
                "portfolio_settings.json": {
                    "spot_sleeve_enabled": True,
                    "spot_sleeve_capital_pct": 0.25,
                },
            },
        },
        {
            "arm_id": "arm2_on_30pct",
            "label": "Spot sleeve ON @ 30% capital (T-115 bigger-MDD-slash arm)",
            "config_patches": {
                "portfolio_settings.json": {
                    "spot_sleeve_enabled": True,
                    "spot_sleeve_capital_pct": 0.30,
                },
            },
        },
    ],
    "windows": [
        {
            "window_id": "2010-2025_16yr",
            "start_date": "2010-01-01",
            "end_date": "2025-12-31",
            "label": "T-092 16-yr arm0_off best window (Sharpe 1.018, ci_low 0.560)",
        },
        {
            "window_id": "2000-2025_26yr",
            "start_date": "2000-01-01",
            "end_date": "2025-12-31",
            "label": "T-092 26-yr 2008-inclusive substrate (Sharpe 0.246, ci_low -0.119)",
        },
    ],
    "reps_per_cell": 5,
    "total_cells": 3 * 2 * 5,  # 30
    "deferred_until": "T-109 fresh ECR image (the :dev image predates T-120/T-121)",
    "primary_kpis": [
        "MDD reduction (rel + abs pp) vs arm0_off",
        "Sharpe ci_low delta vs arm0_off",
        "Calmar improvement",
        "Calm-year Sharpe delta",
        "Crisis-period return aggregate",
        "Reproduction-vs-T-115 (integrated vs analytical divergence)",
    ],
    "decision_gate": (
        "MDD reduction >= 15% AND Sharpe ci_low not down AND calm-Sharpe drag "
        ">= -0.20 — same gate as T-115 analytical."
    ),
}


def write_spec_json():
    out = REPO / "docs/Measurements/2026-06/t121_cloud_ab_spec.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(CAMPAIGN_SPEC, indent=2))
    print(f"[T-121] wrote spec → {out}")


def verify_locally():
    """Pre-flight check: confirm both arms produce different canon md5s
    on a quick single-year (2024) cell, confirming the spec arms
    actually differ before any cloud-spend."""
    import json as _json
    import subprocess

    print("\n[T-121 pre-flight] Verifying arm differentiation on 2024 cell...")
    print("  (uses run_isolated --year 2024 — ~60-90s per arm)")

    settings_path = REPO / "config/portfolio_settings.json"
    backup_path = REPO / "/tmp/t121_preflight_orig.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    orig = settings_path.read_text()
    backup_path.write_text(orig)

    canons = {}
    try:
        for arm in CAMPAIGN_SPEC["arms"]:
            patch = arm["config_patches"]["portfolio_settings.json"]
            cfg = _json.loads(orig)
            cfg.update(patch)
            settings_path.write_text(_json.dumps(cfg, indent=4))

            print(f"  → Running {arm['arm_id']}...")
            result = subprocess.run(
                ["python", "-m", "scripts.run_isolated", "--runs", "1", "--year", "2024"],
                capture_output=True, text=True, cwd=str(REPO),
                env={"PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"},
            )
            for line in result.stdout.splitlines():
                if "trades_canon_md5:" in line:
                    canons[arm["arm_id"]] = line.split("trades_canon_md5:")[-1].strip()
                    print(f"    canon = {canons[arm['arm_id']]}")
                    break
    finally:
        settings_path.write_text(orig)
        print("  reverted config/portfolio_settings.json")

    distinct = len(set(canons.values()))
    print(f"\n[T-121 pre-flight] {distinct}/{len(canons)} distinct canon md5s across arms")
    if distinct == len(canons):
        print("  PASS — all arms differ → cloud launch is safe (no silent no-op)")
    else:
        print("  FAIL — arms collide. Investigate before cloud launch.")
    return canons


def launch_to_cloud():
    """NOT IMPLEMENTED in this branch — cloud submit holds for T-109 image."""
    print(
        "\n[T-121] Cloud launch is HELD per inbox. When T-109 ships the fresh "
        "ECR image, the launch path will route through "
        "scripts/submit_arms_campaign.py with this spec."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--launch", action="store_true",
                    help="(BLOCKED until T-109 image ready) launch the campaign to AWS Batch")
    ap.add_argument("--verify", action="store_true",
                    help="run local pre-flight on 2024 cell to confirm arm differentiation")
    args = ap.parse_args()

    write_spec_json()
    if args.verify:
        verify_locally()
    if args.launch:
        launch_to_cloud()


if __name__ == "__main__":
    main()
