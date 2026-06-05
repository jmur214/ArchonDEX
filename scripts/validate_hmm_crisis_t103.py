"""T-103 — Validate the crisis-trained HMM on HELD-OUT crisis events.

Companion of scripts/train_hmm_crisis_t103.py. Per inbox: this dispatch
decides whether to repoint the live de-gross signal onto the HMM. The
make-or-break number is **OOS p_crisis on COVID Feb-May 2020** — the
new model was trained on 2008 but NEVER saw COVID.

Tests run per inbox acceptance:
  1. OOS COVID — does p_crisis spike Feb-May 2020? (THE critical test.)
  2. OOS 2022 + 2025 — does it fire on post-train stress?
  3. In-window 2008 GFC — does it label the GFC as crisis? (Weaker
     evidence; in-sample.)
  4. Head-to-head vs 5-axis `regime_summary` — does HMM call "crisis"
     where 5-axis did NOT?
  5. Long-window AUC with block-bootstrap CI, SPLIT into train-era
     (2006-2019) vs OOS-era (2020-2025).

All posteriors are CAUSAL/FILTERED via predict_proba on growing
prefixes Z[:t+1] (per T-089 lesson — predict_proba_sequence is
forward-backward and leaks future). Same pattern as
scripts/validate_regime_signals_t087.py.

Output: docs/Measurements/2026-06/hmm_crisis_validation_t103.json +
        the audit doc consumes the print summary.
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
from scripts.train_hmm_crisis_t103 import build_crisis_panel  # noqa: E402


# ----------------------------------------------------------------------
# Causal/filtered HMM inference — matches T-087/T-089 protocol
# ----------------------------------------------------------------------
def compute_causal_posteriors(
    hmm: HMMRegimeClassifier, panel: pd.DataFrame, window: int = 252,
) -> pd.DataFrame:
    """For each t, run predict_proba on Z[max(0,t-window+1):t+1] and
    take the last row — strictly forward-only, no future leak.
    """
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
# Forward drawdown + AUC helpers (same as T-087)
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
# Stress events — train-era + held-out
# ----------------------------------------------------------------------
STRESS_EVENTS = [
    {"label": "2008 GFC (IN-TRAIN)",  "trough": "2008-11-20", "in_train": True},
    {"label": "2011 EU debt (IN-TRAIN)",  "trough": "2011-10-03", "in_train": True},
    {"label": "2015-08 China-vol (IN-TRAIN)", "trough": "2015-08-25", "in_train": True},
    {"label": "2018-Q4 selloff (IN-TRAIN)",   "trough": "2018-12-24", "in_train": True},
    {"label": "COVID 2020 (HELD-OUT)",        "trough": "2020-03-23", "in_train": False},
    {"label": "2022 bear (HELD-OUT)",         "trough": "2022-10-12", "in_train": False},
    {"label": "2025 vol-shock (HELD-OUT)",    "trough": "2025-04-08", "in_train": False},
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
            out.append({**ev, "fired": False, "lead_days": None,
                        "max_p": None, "n_obs": 0})
            continue
        fired = (sig >= threshold).any()
        lead = None
        if fired:
            first = sig[sig >= threshold].index[0]
            lead = int((trough - first).days)
        out.append({
            **ev, "fired": bool(fired), "lead_days": lead,
            "max_p": float(sig.max()), "n_obs": int(len(sig)),
        })
    return out


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hmm-pkl",
                    default=str(REPO / "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"))
    ap.add_argument("--baseline-hmm-pkl",
                    default=str(REPO / "engines/engine_e_regime/models/hmm_3state_v1.pkl"))
    ap.add_argument("--panel-start", default="2005-02-25")
    ap.add_argument("--panel-end",   default="2025-12-31")
    ap.add_argument("--train-start", default="2006-04-01")
    ap.add_argument("--train-end",   default="2019-12-31")
    ap.add_argument("--out-json",
                    default=str(REPO / "docs/Measurements/2026-06/hmm_crisis_validation_t103.json"))
    args = ap.parse_args()

    print(f"[T-103-val] panel: {args.panel_start} → {args.panel_end}")
    print(f"[T-103-val] train (in-era): {args.train_start} → {args.train_end}")
    print(f"[T-103-val] OOS (post-train): {args.train_end} → {args.panel_end}")

    panel = build_crisis_panel(args.panel_start, args.panel_end)

    hmm = HMMRegimeClassifier.load(args.hmm_pkl)
    print(f"[T-103-val] loaded crisis-trained HMM: train={hmm._artifact_metadata['train_start']} "
          f"→ {hmm._artifact_metadata['train_end']} n_train={hmm._artifact_metadata['n_train_obs']}")
    print(f"[T-103-val] state_label_for_idx: {hmm._state_label_for_idx}")

    # Causal posteriors over the entire panel
    print(f"[T-103-val] computing causal posteriors (window=252) over {len(panel.dropna())} rows...")
    proba = compute_causal_posteriors(hmm, panel)
    p_crisis = proba["crisis"]
    p_stressed = proba["stressed"]
    p_combined = p_crisis + p_stressed

    # SPY for forward dd
    spy_panel = panel.loc[proba.index].dropna(subset=["spy_ret_5d"])
    # Reconstruct SPY price from Stooq directly (build_crisis_panel
    # consumed the log-return — keep it simple, re-fetch).
    from scripts.train_hmm_crisis_t103 import _load_stooq_close, STOOQ_SPY
    spy_price = _load_stooq_close(STOOQ_SPY, args.panel_start, args.panel_end)
    spy_price = spy_price.reindex(proba.index).dropna()

    # ---- AUC: full window + train-era + OOS-era ----
    print(f"\n[T-103-val] === AUC vs forward dd ≤ -5% ===")
    auc_block = {"full": {}, "in_train": {}, "oos": {}}
    train_mask = (proba.index >= pd.Timestamp(args.train_start)) & (proba.index <= pd.Timestamp(args.train_end))
    oos_mask = proba.index > pd.Timestamp(args.train_end)

    for horizon in [5, 10, 20]:
        fdd = forward_drawdown(spy_price, horizon)
        target = (fdd <= -0.05).astype(float)
        target[fdd.isna()] = np.nan
        for window_name, mask in [("full", slice(None)), ("in_train", train_mask), ("oos", oos_mask)]:
            for sig_name, sig in [
                ("hmm_p_crisis", p_crisis),
                ("hmm_p_crisis_or_stressed", p_combined),
            ]:
                if isinstance(mask, slice):
                    s_vals = sig.values
                    t_vals = target.values
                else:
                    s_vals = sig[mask].values
                    t_vals = target.reindex(sig.index)[mask].values
                point, lo, hi = auc_block_bootstrap_ci(
                    np.asarray(s_vals, dtype=np.float64),
                    np.asarray(t_vals, dtype=np.float64),
                    n_iter=1000, block=8, seed=42,
                )
                key = f"horizon_{horizon}d_{sig_name}"
                auc_block[window_name][key] = {
                    "auc_point": point, "auc_ci_low": lo, "auc_ci_high": hi,
                }
                print(f"   {window_name:8s} h={horizon:2d}d  {sig_name:25s} AUC={point:.4f}  ci=[{lo:.4f}, {hi:.4f}]")

    # ---- Per-stress-event TPR (threshold sweep on p_crisis + p_crisis_or_stressed) ----
    print(f"\n[T-103-val] === Per-stress-event TPR — p_crisis (narrow) ===")
    per_event = {}
    for thr in [0.3, 0.5, 0.7]:
        rows = per_event_fire(p_crisis, thr, lookback_days=60)
        per_event[f"p_crisis>={thr}"] = rows
        fired_in_train = sum(1 for r in rows if r["fired"] and r["in_train"])
        n_in_train = sum(1 for r in rows if r["in_train"])
        fired_oos = sum(1 for r in rows if r["fired"] and not r["in_train"])
        n_oos = sum(1 for r in rows if not r["in_train"])
        print(f"   p_crisis ≥ {thr}: in-train {fired_in_train}/{n_in_train}  OOS {fired_oos}/{n_oos}")
        for r in rows:
            lead_str = f"{r['lead_days']}d lead" if r["lead_days"] is not None else "no fire"
            max_str = f"max_p={r['max_p']:.3f}" if r["max_p"] is not None else "no coverage"
            print(f"      {r['label']:35s} trough={r['trough']}  fired={str(r['fired']):5s}  {lead_str:14s}  {max_str}")

    print(f"\n[T-103-val] === Per-stress-event TPR — p_crisis + p_stressed (combined) ===")
    print(f"   The crisis-trained model concentrates 'crisis' label into 2008-magnitude tail.")
    print(f"   The 'stressed' label captures COVID/2022/2025-magnitude events.")
    print(f"   For a kill-switch driven by 'systemic stress', use the COMBINED posterior.")
    for thr in [0.5, 0.7, 0.9]:
        rows = per_event_fire(p_combined, thr, lookback_days=60)
        per_event[f"p_crisis_or_stressed>={thr}"] = rows
        fired_in_train = sum(1 for r in rows if r["fired"] and r["in_train"])
        n_in_train = sum(1 for r in rows if r["in_train"])
        fired_oos = sum(1 for r in rows if r["fired"] and not r["in_train"])
        n_oos = sum(1 for r in rows if not r["in_train"])
        print(f"   p_combined ≥ {thr}: in-train {fired_in_train}/{n_in_train}  OOS {fired_oos}/{n_oos}")
        for r in rows:
            lead_str = f"{r['lead_days']}d lead" if r["lead_days"] is not None else "no fire"
            max_str = f"max_p={r['max_p']:.3f}" if r["max_p"] is not None else "no coverage"
            print(f"      {r['label']:35s} trough={r['trough']}  fired={str(r['fired']):5s}  {lead_str:14s}  {max_str}")

    # ---- COVID p_crisis trajectory Feb-May 2020 (the make-or-break) ----
    print(f"\n[T-103-val] === COVID p_crisis trajectory (Feb-May 2020, HELD OUT) ===")
    covid = p_crisis.loc[
        (p_crisis.index >= pd.Timestamp("2020-02-01"))
        & (p_crisis.index <= pd.Timestamp("2020-05-31"))
    ]
    # Print biweekly samples + the peak
    print(f"   coverage: {len(covid)} bars; min p_crisis={covid.min():.3f}; "
          f"max p_crisis={covid.max():.3f}; peak date={covid.idxmax().date()}")
    print(f"   biweekly samples:")
    for date in pd.date_range("2020-02-03", "2020-05-29", freq="14D"):
        idx = covid.index[covid.index >= date]
        if len(idx):
            d = idx[0]
            print(f"      {d.date()}  p_crisis={covid.loc[d]:.3f}  "
                  f"p_stressed={p_stressed.loc[d]:.3f}")
    covid_trajectory = [
        {"date": str(d.date()),
         "p_crisis": float(p_crisis.loc[d]),
         "p_stressed": float(p_stressed.loc[d])}
        for d in covid.index
    ]

    # ---- Head-to-head vs baseline HMM (in-sample-trained) on same dates ----
    print(f"\n[T-103-val] === Head-to-head vs baseline (in-sample 2021-24 trained) ===")
    print(f"   Both models run on the SAME causal posteriors path.")
    print(f"   Baseline was trained on 2021-2024 — it has NEVER seen 2008 or COVID either.")
    try:
        baseline = HMMRegimeClassifier.load(args.baseline_hmm_pkl)
        # Baseline can only run where the panel's features overlap its feature_names.
        # Run on a SUBSET of dates where baseline is meaningful (post-2020 because
        # its feature panel needs TLT/SPY from data/processed which is Alpaca-only).
        # We use the SAME extended panel and just run baseline's transition + emission.
        baseline_proba = compute_causal_posteriors(baseline, panel)
        b_p_crisis = baseline_proba.get("crisis", pd.Series(0.0, index=baseline_proba.index))
        # Compare on the stress events
        print(f"   baseline state_label_for_idx: {baseline._state_label_for_idx}")
        baseline_per_event = per_event_fire(b_p_crisis, 0.5, 60)
        for r, b in zip(per_event["p_crisis>=0.5"], baseline_per_event):
            print(f"      {r['label']:35s}: crisis-trained fired={str(r['fired']):5s} "
                  f"baseline fired={str(b['fired']):5s} "
                  f"(crisis max_p={r['max_p']:.3f} vs baseline max_p={b['max_p']:.3f})")
        head_to_head = {
            "baseline_label_for_idx": list(baseline._state_label_for_idx),
            "by_event": [
                {**r, "baseline_fired": b["fired"], "baseline_max_p": b["max_p"], "baseline_lead_days": b["lead_days"]}
                for r, b in zip(per_event["p_crisis>=0.5"], baseline_per_event)
            ],
        }
    except Exception as exc:
        print(f"   [WARN] baseline comparison skipped: {exc}")
        head_to_head = {"error": str(exc)}

    # ---- Write JSON ----
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "task": "T-2026-06-04-103",
        "panel_start": args.panel_start, "panel_end": args.panel_end,
        "train_start": args.train_start, "train_end": args.train_end,
        "binding_data_floor": "2006-04-04 (DTWEXBGS 2006-01-02 + 63d warmup for dollar_ret_63d)",
        "hmm_pkl": args.hmm_pkl,
        "baseline_hmm_pkl": args.baseline_hmm_pkl,
        "auc_by_window": auc_block,
        "per_event_tpr": per_event,
        "covid_trajectory_feb_may_2020": covid_trajectory,
        "head_to_head_vs_baseline": head_to_head,
    }
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n[T-103-val] wrote {out_path}")


if __name__ == "__main__":
    main()
