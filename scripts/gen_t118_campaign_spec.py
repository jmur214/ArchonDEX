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
REGIME_CFG = "config/regime_settings.json"

# Director decision (T-118-RUN): drive the overlay with the CRISIS model
# (validated AUC@5d 0.914, T-103/T-105), NOT production v1 (the original
# that scored the false-negative AUC 0.49). Model-INVARIANCE at overlay-OFF
# was verified empirically: crisis-model + overlay-OFF reproduces the T-092
# baseline canon (2022 cell `0145c03a…`), because the HMM is invisible to
# Path A except through the overlay (advisory.py:204 — HMM modulates only
# risk_scalar, which is dead on Path A here). So the crisis model is patched
# into ALL arms (incl arm0) to hold the model constant; the only thing that
# varies arm0 -> treatment is the overlay flag. Loading the crisis model to
# drive the EXPERIMENT is NOT a production repoint (prod default stays v1,
# overlay-OFF).
CRISIS_MODEL = "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"
V1_MODEL = "engines/engine_e_regime/models/hmm_3state_v1.pkl"


def _overlay_patch(lvl, k, dd, rl, rb, model):
    """A risk-overlay patch plus the regime model_path patch."""
    return {
        RISK_CFG: {
            "regime_transition_overlay_enabled": True,
            "regime_overlay_degross_level": lvl,
            "regime_overlay_k_days": k,
            "regime_overlay_degross_delta": dd,
            "regime_overlay_regross_level": rl,
            "regime_overlay_regross_bars": rb,
            # T-116 lift stays OFF — the overlay is the de-gross under test;
            # don't stack the risk_scalar lift (explicit for clarity).
            "advisory_risk_scalar_apply_on_path_a": False,
        },
        REGIME_CFG: {"hmm.model_path": model},
    }


def build_arms(include_null: bool, v1_blind: bool) -> dict:
    # arm0: overlay OFF, crisis model loaded -> canon-invariant == T-092
    # baseline (verified). Holds the model constant vs the treatment arms.
    arms = {"arm0_off": {"config_patch": {REGIME_CFG: {"hmm.model_path": CRISIS_MODEL}}}}
    for lvl in DEGROSS_LEVELS:
        if lvl == 1.0 and not include_null:
            continue  # null/placebo control — skip unless explicitly requested
        for k in K_DAYS:
            for hname, (dd, rl, rb) in HYSTERESIS.items():
                lvl_tag = str(lvl).replace(".", "")
                arm = f"arm_L{lvl_tag}_k{k}_{hname}"
                arms[arm] = {"config_patch": _overlay_patch(lvl, k, dd, rl, rb, CRISIS_MODEL)}

    # OPTIONAL (+2 cells/window per arm) — signal-quality disambiguation:
    # the SAME overlay config driven by the BLIND v1 model. Expectation:
    # v1-blind overlay does nothing/hurts while crisis-signal helps -> a
    # clean "it's the signal, not just the mechanism" contrast.
    if v1_blind:
        dd, rl, rb = HYSTERESIS["HB"]  # representative fast/slow-asymmetric pair
        arms["arm_v1blind_L05_k5_HB"] = {
            "config_patch": _overlay_patch(0.5, 5, dd, rl, rb, V1_MODEL)
        }
    return arms


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--include-null-arms", action="store_true",
                    help="include the 12 degross_level=1.0 placebo controls (full grid)")
    ap.add_argument("--v1-blind-disambig", action="store_true",
                    help="add 1 v1-model overlay arm (+2 cells) for signal-quality contrast")
    ap.add_argument("--out", default="data/cloud_runs/specs/t118_overlay.json")
    args = ap.parse_args()

    arms = build_arms(args.include_null_arms, args.v1_blind_disambig)
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
