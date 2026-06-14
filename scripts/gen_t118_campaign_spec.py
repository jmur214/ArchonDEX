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
# HA is the LOCKED T-118b PRIMARY-config hysteresis = the shipped RiskConfig
# overlay defaults (degross_delta 0.4 / regross_level 0.3 / regross_bars 10).
# So arm_L05_k5_HA == the pre-registered primary config the gate is evaluated
# on (level 0.5 × k=5 × 0.4/0.3/10). The original HA used regross_bars=5 — a
# DEFECT (the grid did not contain the locked primary config); corrected to 10
# per t118b_preregistration_2026_06_10.md §v2.4. This is a grid-coverage fix to
# satisfy the LOCKED gate, NOT a threshold edit.
HYSTERESIS = {
    "HA": (0.40, 0.30, 10),   # PRIMARY (shipped defaults)
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

# T-118b §v2.2: the overlay is driven by the CRISIS-trained HMM
# (hmm_3state_crisis_v1, 2006-04→2019-12; the validated AUC@5d 0.914 signal).
# Held constant across ALL arms (incl arm0) so overlay-on vs overlay-off is an
# identical base (pre-reg §116). arm0 = crisis-model + overlay-OFF, which is
# canon-invariant to the prod v1 model at overlay-OFF (T-118-RUN STEP 1: the
# HMM is invisible to Path A except through the overlay) → arm0 must reproduce
# the published v1 prod anchor (the launcher's hard anchor gate confirms it).
CRISIS_MODEL = "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"
V1_MODEL = "engines/engine_e_regime/models/hmm_3state_v1.pkl"


def _arm_patch(lvl, k, dd, rl, rb, model):
    return {
        RISK_CFG: {
            "regime_transition_overlay_enabled": True,
            "regime_overlay_degross_level": lvl,
            "regime_overlay_k_days": k,
            "regime_overlay_degross_delta": dd,
            "regime_overlay_regross_level": rl,
            "regime_overlay_regross_bars": rb,
            "advisory_risk_scalar_apply_on_path_a": False,  # T-116 lift OFF
        },
        REGIME_CFG: {"hmm.model_path": model},
    }


def build_arms(include_null: bool, v1_blind: bool) -> dict:
    # arm0: crisis model + overlay OFF → reproduces the published anchor.
    arms = {"arm0_off": {"config_patch": {REGIME_CFG: {"hmm.model_path": CRISIS_MODEL}}}}
    for lvl in DEGROSS_LEVELS:
        if lvl == 1.0 and not include_null:
            continue  # null/placebo control
        for k in K_DAYS:
            for hname, (dd, rl, rb) in HYSTERESIS.items():
                lvl_tag = str(lvl).replace(".", "")
                arms[f"arm_L{lvl_tag}_k{k}_{hname}"] = {
                    "config_patch": _arm_patch(lvl, k, dd, rl, rb, CRISIS_MODEL)}
    if v1_blind:
        # mechanism-commentary only (pre-reg §147 — never gates): the PRIMARY
        # config on the BLIND v1 posterior.
        dd, rl, rb = HYSTERESIS["HA"]
        arms["arm_v1blind_L05_k5_HA"] = {
            "config_patch": _arm_patch(0.5, 5, dd, rl, rb, V1_MODEL)}
    return arms


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--include-null-arms", action="store_true",
                    help="include the 12 degross_level=1.0 placebo controls")
    ap.add_argument("--out", default="data/cloud_runs/specs/t118_overlay.json")
    ap.add_argument("--v1-blind-disambig", action="store_true",
                    help="add the primary config on the blind v1 model (mechanism only)")
    args = ap.parse_args()

    arms = build_arms(args.include_null_arms, args.v1_blind_disambig)
    spec = {
        "campaign_id": "t118r-hmm-transition-overlay",
        "windows": WINDOWS,
        "reps": args.reps,
        # T-140 canon-anchor gate — the T-167 re-anchor (2026-06-14, cov-pin,
        # N=5 bitwise-unanimous; mean_variance config-true; regime LIVE).
        # arm0 (crisis+OFF) must reproduce 26yr 158fe678 by model-invariance.
        "anchor": {
            "canon_md5": "158fe678",  # 26yr arm0 / Sharpe 0.751 / ci_low 0.382 / MDD -33%
            "source": ("T-167 re-anchor 2026-06-14: 26yr 158fe678/0.751, "
                       "16yr 3e9ea427/1.162, 2022 eb48742e/1.512. arm0's crisis-model "
                       "patch is canon-invariant at overlay-OFF (T-118-RUN STEP 1)."),
            "image": "sha-4c0fc16",
        },
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
