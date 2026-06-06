"""
scripts/gen_t118_campaign_spec.py
=================================
Emit the pre-registered T-118 HMM-transition-overlay A/B campaign spec for
``scripts/submit_arms_campaign.py``. The grid is FROZEN per
docs/Audit/hmm_transition_trigger_overlay_t118_2026_06_06.md §3:

  degross_level in {1.0, 0.5, 0.0}   (1.0 = null/placebo control)
  k_days        in {3, 5, 10}
  hysteresis    in {H_A, H_B, H_C, H_D}   (re-gross strictly slower)
  => 36 configs + arm0 (overlay OFF), on 16-yr and 26-yr windows.

Patches go to config/risk_settings.prod.json (flat keys -> RiskConfig).
arm0 = empty patch == the T-092 baseline (canon 16yr b9cb088f / 26yr c579566c).

MODEL FORK (audit §6): this generates Option (1) = PRODUCTION model
(hmm_3state_v1, recommended — keeps arm0 == T-092 canon). For Option (2)
crisis model, add to EVERY arm's patch (incl. arm0):
  "config/regime_settings.json": {"hmm.model_path":
      "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"}
(note: that breaks arm0 == T-092 canon and folds in the unshipped repoint —
see the audit doc before choosing it).

Usage:
  python scripts/gen_t118_campaign_spec.py [--reps 1] [--include-null-arms]
    [--out data/cloud_runs/specs/t118_overlay.json]
Then (after director approval + an image built off this branch):
  python -m scripts.submit_arms_campaign --spec <out> --job-timeout 18000
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Pre-registered grid (FROZEN) ------------------------------------------------
DEGROSS_LEVELS = [1.0, 0.5, 0.0]
K_DAYS = [3, 5, 10]
# (degross_delta tau_on, regross_level tau_off, regross_bars n_off)
HYSTERESIS = {
    "HA": (0.40, 0.30, 5),
    "HB": (0.30, 0.25, 10),
    "HC": (0.50, 0.25, 10),
    "HD": (0.30, 0.20, 15),
}
WINDOWS = [
    {"start": "2010-01-01", "end": "2025-12-31", "label": "16yr"},
    {"start": "2000-01-01", "end": "2025-12-31", "label": "26yr"},
]
RISK_CFG = "config/risk_settings.prod.json"


def build_arms(include_null: bool) -> dict:
    arms = {"arm0_off": {"config_patch": {}}}  # == T-092 baseline
    for lvl in DEGROSS_LEVELS:
        if lvl == 1.0 and not include_null:
            continue  # null/placebo control — skip unless explicitly requested
        for k in K_DAYS:
            for hname, (dd, rl, rb) in HYSTERESIS.items():
                lvl_tag = str(lvl).replace(".", "")
                arm = f"arm_L{lvl_tag}_k{k}_{hname}"
                arms[arm] = {"config_patch": {RISK_CFG: {
                    "regime_transition_overlay_enabled": True,
                    "regime_overlay_degross_level": lvl,
                    "regime_overlay_k_days": k,
                    "regime_overlay_degross_delta": dd,
                    "regime_overlay_regross_level": rl,
                    "regime_overlay_regross_bars": rb,
                }}}
    return arms


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--include-null-arms", action="store_true",
                    help="include the 12 degross_level=1.0 placebo controls")
    ap.add_argument("--out", default="data/cloud_runs/specs/t118_overlay.json")
    args = ap.parse_args()

    arms = build_arms(args.include_null_arms)
    spec = {
        "campaign_id": "t118-hmm-transition-overlay",
        "windows": WINDOWS,
        "reps": args.reps,
        "arms": arms,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2))
    n_arms = len(arms)
    n_cells = n_arms * len(WINDOWS) * args.reps
    print(f"Wrote {out}")
    print(f"  arms: {n_arms} (incl arm0) | windows: {len(WINDOWS)} | reps: {args.reps}")
    print(f"  total cells: {n_cells}")
    print(f"  null arms (L1.0) included: {args.include_null_arms}")


if __name__ == "__main__":
    main()
