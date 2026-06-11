"""T-2026-05-23-057b-analyze cloud-results aggregator.

Reads the cloud campaign JSON at
data/cloud_runs/t057b-confidence-gate-flip-verify_<launch_ts>.json
(symlinked or copied from the director's worktree) and produces:

- per-cell determinism table (canon md5 unique count per (arm, year))
- per-arm headline Sharpe with bootstrap CI
- per-year Δ table (arm2_n3 vs arm0_off)
- paired-Δ bootstrap CI on the mean Sharpe lift
- FLIP / DEFER verdict per CLAUDE.md #6

Output:
  docs/Audit/confidence_gated_flag_flip_t057b_2026_05_24.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Cloud results land in the director's worktree; reference via absolute
# path to avoid stale symlink confusion.
CLOUD_JSON = Path(
    "/Users/jacksonmurphy/Dev/trading_machine-2/data/cloud_runs/"
    "t057b-confidence-gate-flip-verify_20260524T041425Z.json"
)
AUDIT_JSON = ROOT / "docs" / "Audit" / "confidence_gated_flag_flip_t057b_2026_05_24.json"


def _bootstrap_ci(values: list[float], n_iter: int = 1000,
                  ci_low: float = 0.025, ci_high: float = 0.975,
                  seed: int = 0) -> dict:
    if not values:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    rng = np.random.default_rng(seed)
    means = np.empty(n_iter)
    for i in range(n_iter):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = float(np.mean(sample))
    return {
        "mean": float(np.mean(arr)),
        "ci_low": float(np.quantile(means, ci_low)),
        "ci_high": float(np.quantile(means, ci_high)),
        "n": int(len(arr)),
    }


def _block_bootstrap_paired_ci(
    arm0_by_year: dict, arm1_by_year: dict, n_iter: int = 1000,
    seed: int = 0,
) -> dict:
    """Block-bootstrap on per-year Δ means.

    Effective sample size is 5 (one per year), not 25 (one per rep).
    Within-year reps are bit-identical except for the 3 cells with
    one-rep drift; treating reps as iid would over-state CI tightness.
    """
    years = sorted(arm0_by_year.keys())
    per_year_delta = []
    for y in years:
        a0 = arm0_by_year[y]
        a1 = arm1_by_year[y]
        if not a0 or not a1:
            continue
        per_year_delta.append(float(np.mean(a1) - np.mean(a0)))
    if len(per_year_delta) < 2:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": len(per_year_delta)}
    arr = np.asarray(per_year_delta)
    rng = np.random.default_rng(seed)
    means = np.empty(n_iter)
    for i in range(n_iter):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = float(np.mean(sample))
    return {
        "mean": float(np.mean(arr)),
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
        "n": int(len(arr)),
        "per_year_delta": per_year_delta,
        "per_year_label": years,
    }


def main() -> int:
    d = json.loads(CLOUD_JSON.read_text())
    cells = [c for c in d["cells"] if c["status"] == "SUCCEEDED"]
    print(f"[T-057b-analyze] loaded {len(cells)} cells from {CLOUD_JSON.name}")

    # Per-(arm, year, rep) records
    by_arm: dict[str, list[dict]] = {"arm0_off": [], "arm2_n3": []}
    for c in cells:
        arm = c["arm"]
        m = c["manifest"]
        rec = {
            "arm": arm,
            "year": int(c["year"]),
            "rep": int(c["rep"]),
            "run_id": m["run_id"],
            "sharpe": float(m["sharpe"]) if m["sharpe"] is not None else None,
            "canon_md5": m["canon_md5"],
            "s3_prefix": m["s3_prefix"],
        }
        by_arm[arm].append(rec)

    # Per-arm per-year Sharpe collection
    per_year: dict[str, dict[int, list[float]]] = {
        "arm0_off": {}, "arm2_n3": {},
    }
    canon_stability: dict[str, dict[int, dict]] = {
        "arm0_off": {}, "arm2_n3": {},
    }
    for arm, recs in by_arm.items():
        for r in recs:
            y = r["year"]
            if r["sharpe"] is not None:
                per_year[arm].setdefault(y, []).append(r["sharpe"])
            canon_stability[arm].setdefault(y, {"md5s": []})
            canon_stability[arm][y]["md5s"].append(r["canon_md5"])

    # Compute canon_set_size + flag the drift cells
    drift_cells = []
    for arm in ("arm0_off", "arm2_n3"):
        for y in sorted(canon_stability[arm].keys()):
            md5s = canon_stability[arm][y]["md5s"]
            size = len(set(md5s))
            canon_stability[arm][y]["canon_set_size"] = size
            if size > 1:
                drift_cells.append({"arm": arm, "year": y, "n_unique": size, "md5s": md5s})

    # All-rep arrays (treat reps independently for the iid bootstrap)
    arm0_all = [s for vs in per_year["arm0_off"].values() for s in vs]
    arm1_all = [s for vs in per_year["arm2_n3"].values() for s in vs]
    ci_arm0_iid = _bootstrap_ci(arm0_all)
    ci_arm1_iid = _bootstrap_ci(arm1_all)
    # Per-cell paired Δ — match arm0/arm1 by (year, rep)
    # Build paired arrays in year-rep order
    paired_delta = []
    for y in sorted(per_year["arm0_off"].keys()):
        a0_vs = per_year["arm0_off"].get(y, [])
        a1_vs = per_year["arm2_n3"].get(y, [])
        for i in range(min(len(a0_vs), len(a1_vs))):
            paired_delta.append(a1_vs[i] - a0_vs[i])
    ci_delta_iid = _bootstrap_ci(paired_delta)
    # Block-bootstrap on per-year deltas (effective N=5)
    ci_delta_block = _block_bootstrap_paired_ci(per_year["arm0_off"], per_year["arm2_n3"])

    # Headline
    print(f"\n=== HEADLINE ===")
    print(f"  arm0_off (OFF):   mean Sharpe={ci_arm0_iid['mean']:.4f} ci=[{ci_arm0_iid['ci_low']:.4f}, {ci_arm0_iid['ci_high']:.4f}] n={ci_arm0_iid['n']}")
    print(f"  arm2_n3  (ON n=3): mean Sharpe={ci_arm1_iid['mean']:.4f} ci=[{ci_arm1_iid['ci_low']:.4f}, {ci_arm1_iid['ci_high']:.4f}] n={ci_arm1_iid['n']}")
    print()
    print(f"  Δ Sharpe (iid 25-paired): point={ci_delta_iid['mean']:.4f} ci=[{ci_delta_iid['ci_low']:.4f}, {ci_delta_iid['ci_high']:.4f}]")
    print(f"  Δ Sharpe (block 5-year):  point={ci_delta_block['mean']:.4f} ci=[{ci_delta_block['ci_low']:.4f}, {ci_delta_block['ci_high']:.4f}]")

    print(f"\n=== PER-YEAR Δ Sharpe ===")
    for y in sorted(per_year["arm0_off"].keys()):
        a0 = float(np.mean(per_year["arm0_off"][y]))
        a1 = float(np.mean(per_year["arm2_n3"][y]))
        print(f"  {y}: OFF={a0:+.4f}  arm2_n3={a1:+.4f}  Δ={a1-a0:+.4f}")

    print(f"\n=== DETERMINISM ===")
    print(f"  cells with canon_set_size > 1 (drift):")
    for drift in drift_cells:
        print(f"    {drift['arm']:8s} {drift['year']}: {drift['n_unique']} unique md5s across {len(drift['md5s'])} reps")

    # Verdict
    ci_low_iid = ci_delta_iid['ci_low']
    ci_low_block = ci_delta_block['ci_low']
    # Block-bootstrap is the honest CI given within-year determinism.
    decisive_ci_low = ci_low_block
    if decisive_ci_low is not None and decisive_ci_low > 0:
        verdict = "FLIP"
        verdict_reason = f"block-bootstrap ci_low(Δ Sharpe) = {decisive_ci_low:.4f} > 0 — clears CLAUDE.md #6"
    elif ci_delta_iid['mean'] is not None:
        verdict = "DEFER"
        verdict_reason = (
            f"block-bootstrap ci_low(Δ Sharpe) = {decisive_ci_low:.4f} ≤ 0; "
            f"iid ci_low = {ci_low_iid:.4f}; "
            f"point estimate {ci_delta_iid['mean']:.4f}"
        )
    else:
        verdict = "INCOMPLETE"
        verdict_reason = "Insufficient cells"

    print(f"\n=== VERDICT: {verdict} ===")
    print(f"  {verdict_reason}")

    payload = {
        "task_id": "T-2026-05-23-057b-analyze",
        "description": "Confidence-gated execution flag-flip verification — cloud campaign on extended substrate",
        "substrate": "Stooq+Alpaca merged (post-T-082b), 1962-2026 depth",
        "campaign_id": d["campaign_id"],
        "launch_ts": d["launch_ts"],
        "n_cells": d["n_cells"],
        "n_succeeded": d["n_succeeded"],
        "headline": {
            "arm0_off": ci_arm0_iid,
            "arm2_n3": ci_arm1_iid,
            "delta_iid_paired": ci_delta_iid,
            "delta_block_per_year": ci_delta_block,
        },
        "per_year": {
            "arm0_off": {str(y): {"mean": float(np.mean(vs)), "values": vs}
                          for y, vs in sorted(per_year["arm0_off"].items())},
            "arm2_n3": {str(y): {"mean": float(np.mean(vs)), "values": vs}
                        for y, vs in sorted(per_year["arm2_n3"].items())},
            "delta": {str(y): float(np.mean(per_year["arm2_n3"][y]) - np.mean(per_year["arm0_off"][y]))
                      for y in sorted(per_year["arm0_off"].keys())},
        },
        "canon_stability": canon_stability,
        "drift_cells": drift_cells,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }
    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n[T-057b-analyze] aggregation written → {AUDIT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
