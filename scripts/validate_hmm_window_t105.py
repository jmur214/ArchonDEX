"""T-105 — Re-validate T-103's crisis-HMM at the LIVE 60-bar inference window
+ dwell-time / run-length measurement.

The adversarial review caught a disqualifying gap: T-103 measured
OOS AUC 0.914 (combined posterior) on a 252-bar trailing window
(`scripts/validate_hmm_crisis_t103.py:50`), but the live production
engine infers on 60 bars
(`engines/engine_e_regime/regime_config.py:175`
`history_window_daily: int = 60`; prod `config/regime_settings.json`
has no override). A 60-bar Gaussian-HMM posterior is a different,
noisier, faster-switching random variable than a 252-bar one. Before
any repoint proposal, we need the number at the production window
plus dwell-time (the "always-on light leverage" pathology check from
the 2026-05-06 regime-analyst memory).

Three measurements per inbox T-2026-06-05-105:

  1. Side-by-side OOS AUC at window ∈ {60, 252}, horizons 5/10/20d,
     with block-bootstrap CI and train-era vs OOS-era split — same
     methodology as T-103, just two window settings.

  2. Per-event fire + lead-time on held-out crises (COVID, 2022,
     2025) at window=60 (the production value).

  3. Dwell-time on `1-p_benign` at window=60: median + p90
     run-length above thresholds {0.30, 0.50, 0.70} on 16-yr +
     26-yr substrate, plus the days-above-trigger fraction. Verdict
     against the project's ≤20-day-dwell rule (regime-analyst
     memory 2026-05-06): "a signal consumed as a LEVEL for de-
     grossing must have median run-length ≤ ~20 trading days OR be
     a transition trigger."

Uses the crisis-trained model `hmm_3state_crisis_v1.pkl` (T-103).
Causal/filtered posteriors only (predict_proba on trailing
[max(0, t-window+1):t+1], no forward-backward leak).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier  # noqa: E402
from scripts.train_hmm_crisis_t103 import (  # noqa: E402
    build_crisis_panel, _load_stooq_close, STOOQ_SPY,
)


# ----------------------------------------------------------------------
# Causal posteriors — variable trailing window
# ----------------------------------------------------------------------
def compute_causal_posteriors(
    hmm: HMMRegimeClassifier, panel: pd.DataFrame, window: int,
) -> pd.DataFrame:
    """For each t, run predict_proba on the trailing `window` bars
    ending at t (or fewer if t < window-1). Returns DataFrame of
    state posteriors aligned to panel.dropna()."""
    feature_names = list(hmm.feature_names)
    valid = panel[feature_names].dropna()
    Z = (valid.values - hmm._feature_means) / hmm._feature_stds
    n_rows = len(Z)
    proba = np.empty((n_rows, hmm.n_states), dtype=np.float64)
    for t in range(n_rows):
        start_t = max(0, t - window + 1)
        proba[t] = hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]
    cols = list(hmm._state_label_for_idx)
    return pd.DataFrame(proba, index=valid.index, columns=cols)


# ----------------------------------------------------------------------
# Forward drawdown + AUC helpers (mirror T-103)
# ----------------------------------------------------------------------
def forward_drawdown(price: pd.Series, horizon: int) -> pd.Series:
    rolling_min = price.shift(-1).rolling(horizon, min_periods=1).min()
    out = (rolling_min - price) / price
    out.iloc[-horizon:] = np.nan
    return out


def auc_score(scores: np.ndarray, labels: np.ndarray) -> float:
    mask = ~(np.isnan(scores) | np.isnan(labels))
    s = scores[mask]
    y = labels[mask].astype(int)
    if len(s) == 0 or y.sum() == 0 or y.sum() == len(y):
        return float("nan")
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=np.float64)
    sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    n_pos = y.sum()
    n_neg = len(y) - n_pos
    sum_pos_ranks = ranks[y == 1].sum()
    return float((sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def auc_block_bootstrap_ci(
    scores: np.ndarray, labels: np.ndarray, n_iter: int = 1000,
    block: int = 8, seed: int = 0,
) -> Tuple[float, float, float]:
    mask = ~(np.isnan(scores) | np.isnan(labels))
    s = scores[mask]
    y = labels[mask]
    n = len(s)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    point = auc_score(s, y)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_iter):
        idx = []
        while len(idx) < n:
            start = rng.randint(0, max(1, n - block))
            idx.extend(range(start, min(start + block, n)))
        idx = np.array(idx[:n])
        boots.append(auc_score(s[idx], y[idx]))
    boots = [b for b in boots if not math.isnan(b)]
    if not boots:
        return point, float("nan"), float("nan")
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


# ----------------------------------------------------------------------
# Stress events — held-out + in-train
# ----------------------------------------------------------------------
STRESS_EVENTS = [
    {"label": "2008 GFC (IN-TRAIN)",   "trough": "2008-11-20", "in_train": True},
    {"label": "2011 EU debt (IN-TRAIN)",   "trough": "2011-10-03", "in_train": True},
    {"label": "2015-08 China-vol (IN-TRAIN)",   "trough": "2015-08-25", "in_train": True},
    {"label": "2018-Q4 selloff (IN-TRAIN)",   "trough": "2018-12-24", "in_train": True},
    {"label": "COVID 2020 (HELD-OUT)",   "trough": "2020-03-23", "in_train": False},
    {"label": "2022 bear (HELD-OUT)",   "trough": "2022-10-12", "in_train": False},
    {"label": "2025 vol-shock (HELD-OUT)",   "trough": "2025-04-08", "in_train": False},
]


def per_event_fire(
    p_series: pd.Series, threshold: float, lookback_days: int = 60,
) -> List[Dict]:
    out = []
    for ev in STRESS_EVENTS:
        trough = pd.Timestamp(ev["trough"])
        window_start = trough - pd.Timedelta(days=lookback_days)
        sig = p_series.loc[(p_series.index >= window_start) & (p_series.index <= trough)].dropna()
        if len(sig) == 0:
            out.append({**ev, "fired": False, "lead_days": None, "max_p": None, "n_obs": 0})
            continue
        fired = (sig >= threshold).any()
        lead = None
        if fired:
            first = sig[sig >= threshold].index[0]
            lead = int((trough - first).days)
        out.append({**ev, "fired": bool(fired), "lead_days": lead,
                    "max_p": float(sig.max()), "n_obs": int(len(sig))})
    return out


# ----------------------------------------------------------------------
# Dwell-time / run-length analysis
# ----------------------------------------------------------------------
def run_length_stats(
    p_series: pd.Series, threshold: float,
) -> Dict[str, float]:
    """Median + p90 run-length above `threshold`, plus days-above-trigger
    fraction. A 'run' = consecutive trading days where p ≥ threshold."""
    p = p_series.dropna()
    if len(p) == 0:
        return {"n_obs": 0, "frac_above": float("nan"), "median_run": float("nan"),
                "p90_run": float("nan"), "max_run": float("nan"), "n_runs": 0}
    above = (p >= threshold).astype(int).values
    runs = []
    cur = 0
    for v in above:
        if v == 1:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    n_runs = len(runs)
    if n_runs == 0:
        return {"n_obs": int(len(p)), "frac_above": 0.0, "median_run": 0.0,
                "p90_run": 0.0, "max_run": 0, "n_runs": 0}
    runs_arr = np.array(runs)
    return {
        "n_obs": int(len(p)),
        "frac_above": float(above.mean()),
        "median_run": float(np.median(runs_arr)),
        "p90_run": float(np.percentile(runs_arr, 90)),
        "max_run": int(runs_arr.max()),
        "n_runs": int(n_runs),
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hmm-pkl",
                    default=str(REPO / "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"))
    ap.add_argument("--panel-start", default="2005-02-25")
    ap.add_argument("--panel-end",   default="2025-12-31")
    ap.add_argument("--train-start", default="2006-04-01")
    ap.add_argument("--train-end",   default="2019-12-31")
    ap.add_argument("--out-json",
                    default=str(REPO / "docs/Measurements/2026-06/hmm_window_revalidate_t105.json"))
    args = ap.parse_args()

    # Live window from the dataclass default (prod config has no override)
    LIVE_WINDOW = 60
    BASELINE_WINDOW = 252  # T-103's 252-bar setting

    print(f"[T-105] panel: {args.panel_start} → {args.panel_end}")
    print(f"[T-105] train (in-era): {args.train_start} → {args.train_end}")
    print(f"[T-105] OOS (post-train): {args.train_end} → {args.panel_end}")
    print(f"[T-105] LIVE inference window: {LIVE_WINDOW} bars (engine_e_regime/regime_config.py:175 default; no override in config/regime_settings.json)")
    print(f"[T-105] T-103 baseline window: {BASELINE_WINDOW} bars")

    panel = build_crisis_panel(args.panel_start, args.panel_end)
    hmm = HMMRegimeClassifier.load(args.hmm_pkl)
    print(f"[T-105] crisis-HMM: train={hmm._artifact_metadata['train_start']} → {hmm._artifact_metadata['train_end']}")
    print(f"[T-105] state_label_for_idx: {hmm._state_label_for_idx}")

    # SPY prices for forward-dd
    spy_price = _load_stooq_close(STOOQ_SPY, args.panel_start, args.panel_end)

    results: Dict = {
        "task": "T-2026-06-05-105",
        "live_window_bars": LIVE_WINDOW,
        "baseline_window_bars": BASELINE_WINDOW,
        "panel_start": args.panel_start, "panel_end": args.panel_end,
        "train_start": args.train_start, "train_end": args.train_end,
        "hmm_pkl": args.hmm_pkl,
        "auc_by_window": {},
        "per_event_60_bar": {},
        "dwell_time_60_bar": {},
        "windows": {},
    }

    # --- AUC at both windows ---
    posteriors = {}
    for window in [LIVE_WINDOW, BASELINE_WINDOW]:
        print(f"\n[T-105] computing causal posteriors at window={window} over {len(panel.dropna())} rows...")
        proba = compute_causal_posteriors(hmm, panel, window=window)
        posteriors[window] = proba
        p_crisis = proba["crisis"]
        p_stressed = proba["stressed"]
        p_combined = p_crisis + p_stressed
        spy_aligned = spy_price.reindex(proba.index).dropna()

        train_mask = (proba.index >= pd.Timestamp(args.train_start)) & (proba.index <= pd.Timestamp(args.train_end))
        oos_mask = proba.index > pd.Timestamp(args.train_end)

        win_results = {"by_horizon": {}}
        for horizon in [5, 10, 20]:
            fdd = forward_drawdown(spy_aligned, horizon)
            target = (fdd <= -0.05).astype(float)
            target[fdd.isna()] = np.nan
            h_res = {}
            for window_name, mask in [
                ("full", slice(None)),
                ("in_train", train_mask),
                ("oos", oos_mask),
            ]:
                if isinstance(mask, slice):
                    sig_vals = p_combined.values
                    t_vals = target.reindex(p_combined.index).values
                else:
                    sig_vals = p_combined[mask].values
                    t_vals = target.reindex(p_combined.index)[mask].values
                point, lo, hi = auc_block_bootstrap_ci(
                    np.asarray(sig_vals, dtype=np.float64),
                    np.asarray(t_vals, dtype=np.float64),
                    n_iter=1000, block=8, seed=42,
                )
                h_res[window_name] = {"auc_point": point, "auc_ci_low": lo, "auc_ci_high": hi}
            win_results["by_horizon"][f"h_{horizon}d"] = h_res
            print(f"  h={horizon}d  full=[{h_res['full']['auc_ci_low']:.4f}, {h_res['full']['auc_point']:.4f}, {h_res['full']['auc_ci_high']:.4f}]  "
                  f"in_train=[{h_res['in_train']['auc_ci_low']:.4f}, {h_res['in_train']['auc_point']:.4f}, {h_res['in_train']['auc_ci_high']:.4f}]  "
                  f"oos=[{h_res['oos']['auc_ci_low']:.4f}, {h_res['oos']['auc_point']:.4f}, {h_res['oos']['auc_ci_high']:.4f}]")
        results["auc_by_window"][f"window_{window}"] = win_results
        results["windows"][f"window_{window}"] = {
            "p_combined_mean": float(p_combined.mean()),
            "p_crisis_mean": float(p_crisis.mean()),
            "p_stressed_mean": float(p_stressed.mean()),
            "n_obs": int(len(p_combined)),
        }

    # --- Per-event TPR at LIVE window only ---
    print(f"\n[T-105] === Per-event TPR at LIVE window (60 bar), p_combined ≥ thr, 60d lookback ===")
    live_combined = posteriors[LIVE_WINDOW]["crisis"] + posteriors[LIVE_WINDOW]["stressed"]
    for thr in [0.5, 0.7, 0.9]:
        rows = per_event_fire(live_combined, thr, lookback_days=60)
        results["per_event_60_bar"][f"thr_{thr}"] = rows
        fired_in = sum(1 for r in rows if r["fired"] and r["in_train"])
        n_in = sum(1 for r in rows if r["in_train"])
        fired_oos = sum(1 for r in rows if r["fired"] and not r["in_train"])
        n_oos = sum(1 for r in rows if not r["in_train"])
        print(f"  thr≥{thr}: in-train {fired_in}/{n_in}  OOS {fired_oos}/{n_oos}")
        for r in rows:
            lead_str = f"{r['lead_days']}d lead" if r["lead_days"] is not None else "no fire"
            max_str = f"max_p={r['max_p']:.3f}" if r["max_p"] is not None else "no coverage"
            print(f"     {r['label']:35s} trough={r['trough']}  fired={str(r['fired']):5s}  {lead_str:14s}  {max_str}")

    # --- Side-by-side per-event TPR comparison: LIVE vs BASELINE ---
    print(f"\n[T-105] === Per-event TPR head-to-head: window=60 vs window=252 (p_combined ≥ 0.5, 60d lookback) ===")
    baseline_combined = posteriors[BASELINE_WINDOW]["crisis"] + posteriors[BASELINE_WINDOW]["stressed"]
    live_rows = per_event_fire(live_combined, 0.5, 60)
    baseline_rows = per_event_fire(baseline_combined, 0.5, 60)
    head_to_head = []
    for lr, br in zip(live_rows, baseline_rows):
        print(f"  {lr['label']:35s}  "
              f"60={'YES' if lr['fired'] else 'no '} lead={str(lr['lead_days']) if lr['lead_days'] else '-':>4}d max_p={lr['max_p']:.3f}  "
              f"|  252={'YES' if br['fired'] else 'no '} lead={str(br['lead_days']) if br['lead_days'] else '-':>4}d max_p={br['max_p']:.3f}")
        head_to_head.append({
            "label": lr["label"], "trough": lr["trough"], "in_train": lr["in_train"],
            "live_60": {"fired": lr["fired"], "lead_days": lr["lead_days"], "max_p": lr["max_p"]},
            "baseline_252": {"fired": br["fired"], "lead_days": br["lead_days"], "max_p": br["max_p"]},
        })
    results["head_to_head_per_event"] = head_to_head

    # --- Dwell-time / run-length at LIVE window (60-bar) ---
    print(f"\n[T-105] === Dwell-time at LIVE window=60, p_combined above thresholds ===")
    print(f"   Rule (regime-analyst memory 2026-05-06): median run-length ≤ ~20 trading days OR transition trigger.")
    print(f"   16-yr substrate (2010-01-01 → 2025-12-31):")
    p16 = live_combined.loc[
        (live_combined.index >= pd.Timestamp("2010-01-01"))
        & (live_combined.index <= pd.Timestamp("2025-12-31"))
    ]
    print(f"     n_obs={len(p16)}")
    print(f"   26-yr substrate (panel start 2006-04-04 → 2025-12-31):")
    p26 = live_combined.loc[
        (live_combined.index >= pd.Timestamp("2006-04-04"))
        & (live_combined.index <= pd.Timestamp("2025-12-31"))
    ]
    print(f"     n_obs={len(p26)}")

    dwell = {"window_60_bar": {}}
    for label, p in [("16yr_2010_2025", p16), ("26yr_2006_2025", p26)]:
        dwell["window_60_bar"][label] = {}
        for thr in [0.30, 0.50, 0.70]:
            r = run_length_stats(p, thr)
            dwell["window_60_bar"][label][f"thr_{thr}"] = r
            ok_dwell = "OK" if (not math.isnan(r["median_run"]) and r["median_run"] <= 20) else "FAIL"
            print(f"   {label:18s} thr≥{thr}: "
                  f"frac_above={r['frac_above']*100:5.1f}%  "
                  f"median_run={r['median_run']:5.1f}d  p90_run={r['p90_run']:5.1f}d  "
                  f"max_run={r['max_run']:4d}d  n_runs={r['n_runs']:3d}  → ≤20d rule: {ok_dwell}")
    results["dwell_time_60_bar"] = dwell

    # Also report dwell at 252-bar for direct comparison
    print(f"\n[T-105] === Dwell-time at BASELINE window=252 (for direct comparison) ===")
    dwell_baseline = {"window_252_bar": {}}
    p16_b = baseline_combined.loc[
        (baseline_combined.index >= pd.Timestamp("2010-01-01"))
        & (baseline_combined.index <= pd.Timestamp("2025-12-31"))
    ]
    p26_b = baseline_combined.loc[
        (baseline_combined.index >= pd.Timestamp("2006-04-04"))
        & (baseline_combined.index <= pd.Timestamp("2025-12-31"))
    ]
    for label, p in [("16yr_2010_2025", p16_b), ("26yr_2006_2025", p26_b)]:
        dwell_baseline["window_252_bar"][label] = {}
        for thr in [0.30, 0.50, 0.70]:
            r = run_length_stats(p, thr)
            dwell_baseline["window_252_bar"][label][f"thr_{thr}"] = r
            ok_dwell = "OK" if (not math.isnan(r["median_run"]) and r["median_run"] <= 20) else "FAIL"
            print(f"   {label:18s} thr≥{thr}: "
                  f"frac_above={r['frac_above']*100:5.1f}%  "
                  f"median_run={r['median_run']:5.1f}d  p90_run={r['p90_run']:5.1f}d  "
                  f"max_run={r['max_run']:4d}d  n_runs={r['n_runs']:3d}  → ≤20d rule: {ok_dwell}")
    results["dwell_time_252_bar"] = dwell_baseline

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n[T-105] wrote {out_path}")


if __name__ == "__main__":
    main()
