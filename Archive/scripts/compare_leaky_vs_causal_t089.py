"""T-2026-05-31-089 — quantify leaky-vs-causal AUC inflation.

Computes BOTH leaky (predict_proba_sequence, forward-backward smoothed)
AND causal (per-bar growing prefix, T-087 pattern) HMM posteriors over
the same SPY panel/window, then computes AUC of p_crisis vs forward
20-day drawdown for each path. Reports the inflation delta and a
bootstrap CI on each AUC per CLAUDE.md non-negotiable `[NN-SHARPE-CI]`.

Output: docs/Audit/regime_validator_causal_fix_t089_2026_05_31.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier  # noqa: E402
from scripts._hmm_causal_proba import causal_proba_sequence  # noqa: E402


def _bootstrap_auc_ci(scores: np.ndarray, labels: np.ndarray,
                      n_iter: int = 1000, seed: int = 0) -> dict:
    """Stratified non-parametric bootstrap CI for binary-classification
    AUC (ROC). Sub-samples positives + negatives with replacement,
    recomputes AUC per resample, returns the 95% CI quantiles."""
    from sklearn.metrics import roc_auc_score
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]
    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    rng = np.random.default_rng(seed)
    aucs = np.empty(n_iter, dtype=np.float64)
    for i in range(n_iter):
        s_pos = rng.choice(pos_idx, size=len(pos_idx), replace=True)
        s_neg = rng.choice(neg_idx, size=len(neg_idx), replace=True)
        s_idx = np.concatenate([s_pos, s_neg])
        try:
            aucs[i] = roc_auc_score(labels[s_idx], scores[s_idx])
        except ValueError:
            aucs[i] = np.nan
    aucs = aucs[~np.isnan(aucs)]
    point = float(roc_auc_score(labels, scores))
    return {
        "mean": point,
        "ci_low": float(np.quantile(aucs, 0.025)),
        "ci_high": float(np.quantile(aucs, 0.975)),
        "n": int(len(pos_idx) + len(neg_idx)),
        "n_positives": int(len(pos_idx)),
    }


def _build_panel_and_spy(start: str, end: str) -> tuple:
    """Same panel + SPY load as the T-087 validator. Uses local
    data/processed/SPY_1d.csv for SPY; build_feature_panel for HMM
    inputs."""
    from engines.engine_e_regime.macro_features import build_feature_panel
    panel = build_feature_panel(root=REPO, start="2020-04-01", end=end, include_aux=False)
    # SPY for forward-drawdown target.
    spy_df = pd.read_csv(REPO / "data" / "processed" / "SPY_1d.csv", parse_dates=["Date"])
    spy_df = spy_df.set_index("Date").sort_index()
    spy_df = spy_df[(spy_df.index >= pd.Timestamp(start)) & (spy_df.index <= pd.Timestamp(end))]
    return panel, spy_df


def _forward_drawdown(spy: pd.DataFrame, horizon: int) -> pd.Series:
    """Max forward drawdown over next `horizon` trading days."""
    close = spy["Close"].astype(float)
    fwd = close.rolling(horizon + 1).apply(
        lambda w: float(w.min() / w[0] - 1.0), raw=True,
    ).shift(-horizon)
    return fwd


def _auc_for_path(label: str, p_crisis: pd.Series, fdd: pd.Series,
                  dd_threshold: float) -> dict:
    """Align p_crisis and fdd by index, build binary label, compute AUC + CI."""
    common = p_crisis.index.intersection(fdd.index)
    s = p_crisis.loc[common].dropna()
    t = fdd.loc[common].dropna()
    common2 = s.index.intersection(t.index)
    s = s.loc[common2].values.astype(np.float64)
    t = t.loc[common2].values.astype(np.float64)
    y = (t <= dd_threshold).astype(int)
    if y.sum() == 0:
        return {"path": label, "auc": None, "ci_low": None, "ci_high": None,
                "n_rows": int(len(y)), "n_positives": 0}
    ci = _bootstrap_auc_ci(s, y)
    return {
        "path": label,
        "auc_point": ci["mean"],
        "ci_low": ci["ci_low"],
        "ci_high": ci["ci_high"],
        "n_rows": int(len(y)),
        "n_positives": int(y.sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hmm-pkl",
                    default=str(REPO / "engines" / "engine_e_regime" / "models" / "hmm_3state_v1.pkl"))
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default="2025-04-30")
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--dd-threshold", type=float, default=-0.05)
    ap.add_argument("--out-json",
                    default=str(REPO / "docs" / "Audit" / "regime_validator_causal_fix_t089_2026_05_31.json"))
    args = ap.parse_args()

    print(f"[T-089] loading HMM from {args.hmm_pkl}", flush=True)
    hmm = HMMRegimeClassifier.load(args.hmm_pkl)
    print(f"[T-089] HMM states: {hmm._state_label_for_idx}", flush=True)

    print(f"[T-089] building panel + loading SPY ({args.start} → {args.end})", flush=True)
    panel, spy = _build_panel_and_spy(args.start, args.end)
    print(f"[T-089] panel rows={len(panel)}, SPY rows={len(spy)}", flush=True)

    # ---- LEAKY path ----
    print(f"[T-089] computing LEAKY (forward-backward smoothed) posteriors...", flush=True)
    proba_leaky = hmm.predict_proba_sequence(panel)

    # ---- CAUSAL path ----
    print(f"[T-089] computing CAUSAL (per-bar growing prefix, T-087 pattern)...", flush=True)
    proba_causal = causal_proba_sequence(hmm, panel, window=252)

    # Restrict both to the validation window.
    mask = (proba_leaky.index >= pd.Timestamp(args.start)) & (proba_leaky.index <= pd.Timestamp(args.end))
    proba_leaky = proba_leaky.loc[mask]
    mask2 = (proba_causal.index >= pd.Timestamp(args.start)) & (proba_causal.index <= pd.Timestamp(args.end))
    proba_causal = proba_causal.loc[mask2]

    # ---- Forward target ----
    fdd = _forward_drawdown(spy, args.horizon)

    # ---- AUC per path ----
    results = {}
    for state in ("crisis", "stressed"):
        if state not in proba_leaky.columns:
            continue
        leaky_auc = _auc_for_path(f"leaky_p_{state}",
                                  proba_leaky[state], fdd, args.dd_threshold)
        causal_auc = _auc_for_path(f"causal_p_{state}",
                                   proba_causal[state], fdd, args.dd_threshold)
        results[state] = {
            "leaky": leaky_auc,
            "causal": causal_auc,
            "delta_point": (
                None if (leaky_auc.get("auc_point") is None or causal_auc.get("auc_point") is None)
                else round(leaky_auc["auc_point"] - causal_auc["auc_point"], 4)
            ),
        }
        print(f"\n=== p_{state} ===", flush=True)
        print(f"  LEAKY:  AUC={leaky_auc.get('auc_point')} ci=[{leaky_auc.get('ci_low')}, {leaky_auc.get('ci_high')}] n={leaky_auc.get('n_rows')} pos={leaky_auc.get('n_positives')}", flush=True)
        print(f"  CAUSAL: AUC={causal_auc.get('auc_point')} ci=[{causal_auc.get('ci_low')}, {causal_auc.get('ci_high')}]", flush=True)
        print(f"  Δ (leaky-causal): {results[state]['delta_point']}", flush=True)

    payload = {
        "task_id": "T-2026-05-31-089",
        "hmm_pkl": str(args.hmm_pkl),
        "window": f"{args.start}_to_{args.end}",
        "horizon_days": args.horizon,
        "dd_threshold": args.dd_threshold,
        "panel_rows": int(len(panel)),
        "spy_rows": int(len(spy)),
        "results": results,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n[T-089] aggregation written → {args.out_json}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
