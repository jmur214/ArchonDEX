"""ARCHIVED 2026-05-31 (T-091).

Superseded by run_vol_target_arms_full.py, run_vol_target_arms_ewma_t055d.py,
run_vol_target_arms_regime_t055e.py, and run_vol_target_arms_multiplier_sweep_t055g.py.
The vol-target chapter is CLOSED on 12-yr per T-055h (Δ -0.214); this
minimal single-rep harness has no remaining use. The 4 silent-mismatch
bug sites it carried (Sharpe / Max Drawdown% / CAGR_pct / MDD_pct
reading keys cockpit/metrics.py:_compute_summary never emits) are
retired with the file. Re-read history via git log if you need it.

T-2026-05-12-055 vol-target A/B harness.

Two arms on the same substrate:
  Arm 1 (control): portfolio_vol_target_enabled=False (default)
  Arm 2 (treatment): portfolio_vol_target_enabled=True

Mirrors the run_substrate_arms.py pattern — uses run_isolated.py's
isolated() context manager for governor-state + module-globals isolation,
plus a temporary patch to config/risk_settings.json for Arm 2.

Output: a JSON summary at docs/Audit/engine_b_vol_targeting_ab_2026_05_22.json
with per-arm trades_canon_md5, Sharpe, CAGR, MDD.

Per the T-055 spec acceptance #4, the canonical campaign is 3 reps × 5
years × 2 arms = 30 runs (~6 hr). This minimal harness is a
single-rep-per-arm gate that surfaces:
  * code correctness (vol-target ON differs from OFF)
  * determinism within an arm (matches prior runs of the same config)
  * directional sanity (Sharpe doesn't tank)

The full 3-rep × 5-yr campaign is recommended as a follow-up sub-
dispatch — this harness defines the structure but caps wall-time.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RISK_CFG = ROOT / "config" / "risk_settings.json"
AUDIT_OUT = ROOT / "docs" / "Audit" / "engine_b_vol_targeting_ab_2026_05_22.json"


def _patch_risk_settings_enabled(enabled: bool) -> None:
    """Toggle portfolio_vol_target_enabled in-place. Caller MUST snapshot
    the file before invoking and restore after the arm completes."""
    cfg = json.loads(RISK_CFG.read_text())
    cfg["portfolio_vol_target_enabled"] = bool(enabled)
    RISK_CFG.write_text(json.dumps(cfg, indent=2))


def _run_one_arm(label: str, enabled: bool, task: str) -> dict:
    """Execute one arm: patch config, run_isolated single rep, restore."""
    from scripts.run_isolated import (
        isolated, _find_run_id, _trades_canon_md5, _run_q1_inside_context,
        TRADES_DIR,
    )
    backup = RISK_CFG.with_suffix(".json.t055_bak")
    shutil.copy2(RISK_CFG, backup)
    try:
        _patch_risk_settings_enabled(enabled)
        print(f"[ARMS] === {label} (enabled={enabled}) start ===")
        before_run_ids = {
            p.name for p in TRADES_DIR.iterdir()
            if p.is_dir() and p.name != "backup"
        }
        t0 = time.perf_counter()
        with isolated():
            _run_q1_inside_context(apply_journal_at_end=True)
        elapsed = time.perf_counter() - t0
        run_id = _find_run_id(before_run_ids)
        canon = _trades_canon_md5(run_id) if run_id else None
        # Read perf summary from the run's output if available
        sharpe = None
        cagr = None
        mdd = None
        try:
            summary_path = ROOT / "data" / "trade_logs" / run_id / "performance_summary.json"
            if summary_path.exists():
                summary = json.loads(summary_path.read_text())
                sharpe = summary.get("Sharpe") or summary.get("sharpe")
                cagr = summary.get("CAGR%") or summary.get("CAGR_pct")
                mdd = summary.get("Max Drawdown%") or summary.get("MDD_pct")
        except Exception:
            pass
        print(f"[ARMS] === {label} done in {elapsed:.1f}s ===")
        print(f"        run_id={run_id} canon={canon} sharpe={sharpe}")
        return {
            "arm": label,
            "enabled": enabled,
            "task": task,
            "wall_seconds": round(elapsed, 1),
            "run_id": run_id,
            "trades_canon_md5": canon,
            "sharpe": sharpe,
            "cagr_pct": cagr,
            "mdd_pct": mdd,
        }
    finally:
        shutil.copy2(backup, RISK_CFG)
        backup.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="q1", choices=["q1"])
    args = ap.parse_args()

    print(f"[ARMS] T-2026-05-12-055 vol-target A/B harness — task={args.task}")
    result_off = _run_one_arm("ARM_OFF", enabled=False, task=args.task)
    result_on = _run_one_arm("ARM_ON", enabled=True, task=args.task)

    payload = {
        "task_id": "T-2026-05-12-055",
        "ab_pair": "portfolio_vol_target ON vs OFF",
        "harness_scope": "single rep × 1 task per arm (minimal smoke; full 3-rep × 5-yr deferred to sub-dispatch)",
        "arms": [result_off, result_on],
        "delta": {
            "canon_identical": result_off["trades_canon_md5"] == result_on["trades_canon_md5"],
            "sharpe_delta": (
                None if (result_off["sharpe"] is None or result_on["sharpe"] is None)
                else round(result_on["sharpe"] - result_off["sharpe"], 4)
            ),
        },
    }
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(payload, indent=2))
    print(f"\n[ARMS] Audit JSON written to {AUDIT_OUT}")
    print(f"[ARMS] canon_identical={payload['delta']['canon_identical']} sharpe_delta={payload['delta']['sharpe_delta']}")


if __name__ == "__main__":
    main()
