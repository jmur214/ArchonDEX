"""
scripts/assess_vol_collapse_t153.py
===================================
T-2026-06-11-153 Part 1 — RISK ASSESSMENT of the production EWMA
vol-estimator's collapse-to-near-zero state (D's T-150 structural finding),
quantified on canonical history. Diagnostics only — no engine wiring.

Two sweeps:

(A) PORTFOLIO-LEVEL (the production-config consequence): replay BOTH
    `vol_target.py` estimators (rolling-60 + EWMA λ=0.94) bar-by-bar over
    the canonical 26-yr arm0 equity history (T-118 pre-flight artifact,
    run bd510194, canon 529e5520) exactly as `compute_portfolio_vol_scale`
    would at each prepare_order call, and measure:
      - bars where the estimator emits a near-zero annualized σ
        (< 2% = scale pinned at ceiling vs the 10% target; < 0.5% = deep
        collapse), with episode counts;
      - the leverage the targeter would have REQUESTED in those states
        (clip(target/σ, floor, ceiling)) vs what a sanity-floored σ
        (max(σ, 0.5 × full-sample σ)) would have requested.
    NOTE the production defaults: `portfolio_vol_target_enabled=False`
    AND `estimator_type="rolling"`. The EWMA is the T-055d opt-in arm.
    This sweep quantifies the risk IF enabled — the "today-risk" is
    conditional on two flag-flips, and the audit states that honestly.

(B) PER-NAME (the estimator-level defect across the substrate): the same
    EWMA recursion per ticker over data/processed/*_1d.csv closes
    (pandas ewm(alpha=1-λ, adjust=False) on r² — identical recursion,
    σ²₀=r²₀ init), joined against D's T-150 Yang-Zhang panel
    (yz_vol_21) on the same (ticker, date): how often is EWMA in a
    near-zero state while YZ reads sane vol? This is D's QLIKE-explosion
    mechanism counted directly.

Deterministic: pure arithmetic, no seeds, no wall-clock in the artifact.
Output: data/research/t153_assessment/assessment.json + printed headline.

Usage: python -m scripts.assess_vol_collapse_t153
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SNAPSHOTS = ROOT / "data" / "research" / "t153_assessment" / "canonical_26yr_snapshots.csv"
YZ_PANEL = ROOT / "data" / "research" / "ohlc_features_t150" / "features.parquet"
OUT_JSON = ROOT / "data" / "research" / "t153_assessment" / "assessment.json"

LAM = 0.94                      # production ewma_lambda (vol_target.py)
TARGET = 0.10                   # production target_annual_vol
FLOOR, CEIL = 0.5, 2.0          # production leverage floor/ceiling
WINDOW, MIN_RET = 60, 60        # production rolling window / warmup
ANN = np.sqrt(252.0)
NEAR_ZERO = 0.02                # annualized σ below this → scale pinned at ceiling (0.10/0.02 = 5 > 2.0)
DEEP_ZERO = 0.005               # deep-collapse threshold


def _episodes(mask: np.ndarray) -> int:
    """Count maximal runs of True."""
    if mask.size == 0:
        return 0
    return int(np.sum(mask & ~np.roll(mask, 1)) - (1 if mask[0] and mask[-1] and mask.all() else 0)) \
        if False else int(np.sum(np.diff(np.concatenate([[0], mask.astype(int)])) == 1))


def portfolio_sweep() -> dict:
    snaps = pd.read_csv(SNAPSHOTS, parse_dates=["timestamp"])
    # Last snapshot per unique date — mirrors _equity_at_end_of_each_day.
    eq = snaps.groupby(snaps["timestamp"].dt.date)["equity"].last()
    eq = eq[np.isfinite(eq.values) & (eq.values > 0)]
    r = pd.Series(np.diff(eq.values) / eq.values[:-1], index=eq.index[1:])
    n = len(r)

    # --- EWMA replay: per-bar expanding, σ²₀ = r²₀ (vol_target.py init) ---
    # pandas ewm(adjust=False) on r² reproduces σ²_t = λσ²_{t-1} + (1-λ)r²_t
    # with σ²₀ = r²₀ exactly.
    sigma2_ewma = r.pow(2).ewm(alpha=1.0 - LAM, adjust=False).mean()
    sig_ewma_ann = np.sqrt(sigma2_ewma) * ANN
    # --- rolling-60 replay (ddof=1, trailing) ---
    sig_roll_ann = r.rolling(WINDOW).std(ddof=1) * ANN

    # Warmup gate: estimator returns None (scale 1.0) until MIN_RET returns.
    live = np.arange(n) >= MIN_RET

    def scale(sig: pd.Series) -> np.ndarray:
        s = np.where(
            live & np.isfinite(sig.values) & (sig.values > 0.0),
            np.clip(TARGET / np.where(sig.values > 0, sig.values, np.nan), FLOOR, CEIL),
            1.0,
        )
        return np.nan_to_num(s, nan=1.0)

    full_sample_sigma = float(np.std(r.values, ddof=1)) * ANN
    sanity_floor = 0.5 * full_sample_sigma
    sig_ewma_floored = np.maximum(sig_ewma_ann.values, sanity_floor)

    out = {}
    for name, sig in [("ewma", sig_ewma_ann), ("rolling", sig_roll_ann)]:
        v = sig.values
        near = live & np.isfinite(v) & (v > 0) & (v < NEAR_ZERO)
        deep = live & np.isfinite(v) & (v > 0) & (v < DEEP_ZERO)
        exact_zero_or_nan = live & (~np.isfinite(v) | (v <= 0))
        req = scale(sig)
        req_floored = np.where(
            live, np.clip(TARGET / np.maximum(v, sanity_floor), FLOOR, CEIL), 1.0
        )
        over_lever = np.where(near, req / req_floored, 1.0)
        out[name] = {
            "bars_live": int(live.sum()),
            "near_zero_bars": int(near.sum()),
            "near_zero_pct_of_live": round(100.0 * near.sum() / max(live.sum(), 1), 3),
            "near_zero_episodes": _episodes(near),
            "deep_zero_bars": int(deep.sum()),
            "guarded_zero_or_nan_bars": int(exact_zero_or_nan.sum()),
            "ceiling_pinned_bars": int((live & (req >= CEIL)).sum()),
            "ceiling_pinned_in_near_zero": int((near & (req >= CEIL)).sum()),
            "max_over_lever_ratio_vs_floored": round(float(over_lever.max()), 3),
            "min_sigma_ann_observed": round(float(np.nanmin(np.where(live & (v > 0), v, np.nan))), 6),
        }
    out["full_sample_sigma_ann"] = round(full_sample_sigma, 4)
    out["sanity_floor_ann_used"] = round(sanity_floor, 4)
    out["n_daily_returns"] = n
    return out


def per_name_sweep() -> dict:
    yz = pd.read_parquet(YZ_PANEL, columns=["ticker", "date", "yz_vol_21"])
    yz["date"] = pd.to_datetime(yz["date"]).dt.date
    yz = yz.set_index(["ticker", "date"])["yz_vol_21"]

    total_bars = 0
    near_bars = 0
    names_with_near = 0
    n_names = 0
    ratios = []          # YZ σ / EWMA σ on EWMA-near-zero bars (the divergence)
    yz_sane_on_near = 0  # near-zero EWMA bars where YZ ≥ 5% annual

    for f in sorted(glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv"))):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True, usecols=lambda c: c in ("Date", "date", "Close", "") or c == 0)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 300:
            continue
        t = f.split("/")[-1].replace("_1d.csv", "")
        c = df["Close"].astype(float)
        r = c.pct_change().dropna()
        if len(r) < MIN_RET + 1:
            continue
        sig = np.sqrt(r.pow(2).ewm(alpha=1.0 - LAM, adjust=False).mean()) * ANN
        sig = sig.iloc[MIN_RET:]
        near = sig[(sig > 0) & (sig < NEAR_ZERO)]
        n_names += 1
        total_bars += len(sig)
        near_bars += len(near)
        if len(near):
            names_with_near += 1
            idx = pd.MultiIndex.from_arrays(
                [[t] * len(near), [d.date() for d in near.index]]
            )
            yz_match = yz.reindex(idx)
            ok = yz_match.notna().values
            if ok.any():
                yz_v = yz_match.values[ok]
                ew_v = near.values[ok]
                ratios.extend((yz_v / ew_v).tolist())
                yz_sane_on_near += int((yz_v >= 0.05).sum())

    ratios_arr = np.asarray(ratios, dtype=float)
    return {
        "n_names": n_names,
        "total_live_bars": total_bars,
        "ewma_near_zero_bars": near_bars,
        "ewma_near_zero_pct": round(100.0 * near_bars / max(total_bars, 1), 4),
        "names_with_near_zero": names_with_near,
        "near_zero_bars_with_yz_match": int(ratios_arr.size),
        "yz_sane_ge5pct_on_those_bars": yz_sane_on_near,
        "median_yz_over_ewma_ratio_on_collapse": round(float(np.median(ratios_arr)), 1) if ratios_arr.size else None,
        "p90_yz_over_ewma_ratio_on_collapse": round(float(np.percentile(ratios_arr, 90)), 1) if ratios_arr.size else None,
    }


def main() -> int:
    res = {
        "task": "T-2026-06-11-153 risk assessment",
        "thresholds": {"near_zero_ann": NEAR_ZERO, "deep_zero_ann": DEEP_ZERO},
        "production_defaults_note": (
            "portfolio_vol_target_enabled=False AND estimator_type='rolling' "
            "are the on-main defaults; the EWMA collapse risk is conditional "
            "on both flags flipping (the T-055d arm)."
        ),
        "portfolio_26yr_canonical": portfolio_sweep(),
        "per_name_substrate": per_name_sweep(),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"\n[T153] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
