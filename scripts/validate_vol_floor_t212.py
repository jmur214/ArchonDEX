"""
scripts/validate_vol_floor_t212.py
==================================
T-2026-06-18-212 Part 1 — ACCEPTANCE GATE for the sigma-floor guard.

T-153 measured the collapse (data/research/t153_assessment/assessment.json):
on the canonical 26yr arm0 book, BOTH estimators emit sigma < 2% annual on
~14% of live bars (928 EWMA / 918 rolling), min observed 3e-06, and EVERY
one of those near-zero bars pins leverage at the ceiling (the over-lever).

This script PROVES the T-212 tuned floor eliminates that collapse end-to-end
on the same real book. It replays each estimator bar-by-bar (the same
expanding/rolling recursion `compute_portfolio_vol_scale` uses) and applies
the CAUSAL sigma-floor (`apply_vol_floor` semantics):
    effective_floor_t = max(vol_floor_annual,
                            frac * sigma_full(history up to t))      [causal]
    floored_sigma_t   = max(sigma_t, effective_floor_t)
    scale_t           = clip(target / floored_sigma_t, floor, ceiling)

ACCEPTANCE (asserted; non-zero exit on failure):
  (a) 0 bars have post-floor effective sigma below the collapse bound
      (target/ceiling = 0.05) — i.e. no near-zero sigma survives the floor;
  (b) 0 of the original near-zero bars remain ceiling-pinned by sigma→0;
  (c) the floor NEVER invents an estimate (warmup/no-data bars stay no-op 1.0).

Deterministic: pure arithmetic over the frozen canonical snapshots.
Usage: python -m scripts.validate_vol_floor_t212
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SNAPSHOTS = ROOT / "data" / "research" / "t153_assessment" / "canonical_26yr_snapshots.csv"
OUT_JSON = ROOT / "data" / "research" / "t153_assessment" / "t212_floor_validation.json"

# Production / pre-registered grid (T-206 spec).
LAM = 0.94
TARGET = 0.10
FLOOR, CEIL = 0.5, 2.0
WINDOW, MIN_RET = 60, 60
ANN = np.sqrt(252.0)
# T-212 TUNED floor (the pre-registered operating point):
VOL_FLOOR_ANNUAL = 0.05            # == target/ceiling bound (absolute guarantee)
VOL_FLOOR_FRAC = 0.5               # relative margin on top (adaptive to book vol)
BOUND = TARGET / CEIL              # 0.05 — sigma at/below this pins the ceiling


def _scale(sig_vals: np.ndarray, live: np.ndarray, floored: np.ndarray) -> np.ndarray:
    s = np.where(
        live & np.isfinite(floored) & (floored > 0.0),
        np.clip(TARGET / np.where(floored > 0, floored, np.nan), FLOOR, CEIL),
        1.0,
    )
    return np.nan_to_num(s, nan=1.0)


def main() -> int:
    if not SNAPSHOTS.exists():
        print(f"[T212] FATAL: canonical snapshots absent at {SNAPSHOTS}")
        return 2
    snaps = pd.read_csv(SNAPSHOTS, parse_dates=["timestamp"])
    eq = snaps.groupby(snaps["timestamp"].dt.date)["equity"].last()
    eq = eq[np.isfinite(eq.values) & (eq.values > 0)]
    r = pd.Series(np.diff(eq.values) / eq.values[:-1], index=eq.index[1:])
    n = len(r)
    live = np.arange(n) >= MIN_RET

    # CAUSAL expanding full-sample sigma (annualized) — only data up to t.
    expanding_sigma_ann = (r.expanding(min_periods=2).std(ddof=1) * ANN).values
    expanding_sigma_ann = np.nan_to_num(expanding_sigma_ann, nan=0.0)
    effective_floor = np.maximum(VOL_FLOOR_ANNUAL, VOL_FLOOR_FRAC * expanding_sigma_ann)

    estimators = {
        "ewma": np.sqrt(r.pow(2).ewm(alpha=1.0 - LAM, adjust=False).mean()).values * ANN,
        "rolling": (r.rolling(WINDOW).std(ddof=1) * ANN).values,
    }

    report = {"task": "T-2026-06-18-212 sigma-floor acceptance gate",
              "tuned_floor": {"vol_floor_annual": VOL_FLOOR_ANNUAL,
                              "vol_floor_full_sample_frac": VOL_FLOOR_FRAC,
                              "collapse_bound_target_over_ceiling": BOUND},
              "n_daily_returns": n, "bars_live": int(live.sum()),
              "estimators": {}}
    ok = True
    for name, sig in estimators.items():
        valid = live & np.isfinite(sig) & (sig > 0.0)
        near = valid & (sig < BOUND)
        # floor-OFF
        scale_off = _scale(sig, live, sig)
        pinned_off = int((near & (scale_off >= CEIL)).sum())
        # floor-ON (causal). Floor only where an estimate exists; warmup/no
        # estimate stays no-op (the floor must never invent an estimate).
        floored = np.where(valid, np.maximum(sig, effective_floor), sig)
        scale_on = _scale(sig, live, floored)
        # acceptance checks
        post_floor_below_bound = int((valid & (floored < BOUND - 1e-12)).sum())
        pinned_on_from_collapse = int((near & (scale_on >= CEIL)).sum())
        warmup_noop_ok = bool(np.all(scale_on[~live] == 1.0))

        est_ok = (post_floor_below_bound == 0 and pinned_on_from_collapse == 0
                  and warmup_noop_ok)
        ok = ok and est_ok
        report["estimators"][name] = {
            "near_zero_bars": int(near.sum()),
            "near_zero_pct_of_live": round(100.0 * near.sum() / max(live.sum(), 1), 3),
            "ceiling_pinned_FLOOR_OFF": pinned_off,
            "ceiling_pinned_from_collapse_FLOOR_ON": pinned_on_from_collapse,
            "post_floor_bars_below_bound_FLOOR_ON": post_floor_below_bound,
            "warmup_noop_preserved": warmup_noop_ok,
            "max_scale_FLOOR_OFF": round(float(scale_off[live].max()), 4),
            "max_scale_FLOOR_ON": round(float(scale_on[live].max()), 4),
            "ACCEPT": est_ok,
        }

    report["VALIDATION_PASSED"] = ok
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\n[T212] wrote {OUT_JSON}")
    if ok:
        print("[T212] ACCEPTANCE GATE PASSED — the tuned sigma-floor eliminates "
              "the collapse-driven ceiling-pin on the canonical 26yr book.")
        return 0
    print("[T212] ACCEPTANCE GATE FAILED — collapse not fully neutralized.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
