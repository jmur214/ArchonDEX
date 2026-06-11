"""
scripts/metalearner_falsification_t149.py
=========================================
T-2026-06-11-149 Part B — the metalearner FALSIFICATION (not train-to-deploy).

T-132 left a weak-prior GO (1-of-28 interactions, door ajar); the external
research predicts "ridge wins at our scale" and its >=5-individually-clearing-
edges precondition is unmet (we have 0). This is the pre-registered kill test
so the door closes (or genuinely surprises) WITH EVIDENCE.

PRE-REGISTERED (this file + the audit's pre-registration section are COMMITTED
BEFORE the run touches data; the kill bar is immovable afterward):

  DATA: the T-132 panel (per-ticker signal log 695b0b21, 109 tickers x 1004
  days, 2021-2024), the SAME 8 de-correlated features (assembly + greedy
  |rho|>0.5 de-correlation IMPORTED from scripts.interaction_diagnostic_t132 —
  one implementation). Target: 1-day forward log close-to-close return.

  MODELS (the complete config family — no architecture shopping; N_trials += 3):
    1. GBM stacker: sklearn HistGradientBoostingRegressor, max_depth=3,
       min_samples_leaf=500 (heavy), learning_rate=0.05, max_iter=300,
       monotonic_cst=+1 on ALL features (edge signals are constructed
       bullish-positive — the research's monotonicity guardrail),
       early_stopping=False, random_state=0.
    2. RIDGE (the null-hypothesis combiner): standardized features, alpha
       chosen per training set from the fixed grid {0.1, 1, 10, 100} by
       internal 5-fold MSE.
    3. LINEAR weighted_sum baseline (production proxy): uniform mean of the
       8 signals. Reported for context; the kill bar is GBM vs RIDGE.

  VALIDATION: Combinatorially Purged Cross-Validation — N=6 contiguous
  date groups, k=2 test groups -> C(6,2)=15 paths; PURGE = the 1-day label
  horizon at every train/test boundary; EMBARGO = 1% of the sample
  (~10 trading days) after each test block. No plain k-fold, no single split.

  METRIC: per-OOS-day cross-sectional Spearman rank-IC (prediction vs
  realized forward return; days with <30 names skipped). Per model, the
  per-day ICs are averaged across the paths in which that day is OOS ->
  ONE daily IC series per model on the union OOS calendar.

  THE KILL BAR (immovable): the metalearner survives ONLY IF BOTH
    (a) SPA test (core.multiple_testing.spa_test) on d_t = IC_gbm(t) -
        IC_ridge(t) rejects H0 at 5% (one family-wise comparison), AND
    (b) the block-bootstrap (B=1000, block=21, seed 0) ci_low of mean(d) > 0.
  Anything less => the door CLOSES: "non-linear combination cannot extract
  compound alpha from these edges" joins T-117's linear closure, and the
  2026-05-01 metalearner falsification stands reinforced. The production
  `enabled` flag stays false REGARDLESS of outcome.

  Determinism: seed 0 end-to-end; no wall-clock in the artifact; x2.

Usage: PYTHONHASHSEED=0 python -m scripts.metalearner_falsification_t149
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402
from core.multiple_testing import spa_test  # noqa: E402
from scripts.interaction_diagnostic_t132 import assemble_panel, decorrelate  # noqa: E402

OUT_DIR = ROOT / "data" / "measurements" / "metalearner_falsification_t149"
OUT_JSON = OUT_DIR / "falsification_results.json"

N_GROUPS = 6
K_TEST = 2
PURGE_DAYS = 1          # = label horizon
EMBARGO_FRAC = 0.01
MIN_NAMES_PER_DAY = 30
RIDGE_ALPHAS = [0.1, 1.0, 10.0, 100.0]
SEED = 0


def fit_predict(model_name: str, Xtr, ytr, Xte) -> np.ndarray:
    if model_name == "gbm":
        m = HistGradientBoostingRegressor(
            max_depth=3, min_samples_leaf=500, learning_rate=0.05,
            max_iter=300, early_stopping=False,
            monotonic_cst=[1] * Xtr.shape[1], random_state=SEED)
        m.fit(Xtr, ytr)
        return m.predict(Xte)
    if model_name == "ridge":
        sc = StandardScaler().fit(Xtr)
        m = RidgeCV(alphas=RIDGE_ALPHAS, cv=5).fit(sc.transform(Xtr), ytr)
        return m.predict(sc.transform(Xte))
    if model_name == "linear":
        return Xte.mean(axis=1)  # uniform weighted_sum (production proxy)
    raise ValueError(model_name)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel, fire = assemble_panel()
    kept, dropped, _ = decorrelate(panel, fire)
    print(f"[T149-B] panel {len(panel)} rows | features {len(kept)}: {kept}")

    dates = panel.index.get_level_values("timestamp")
    udays = pd.DatetimeIndex(sorted(dates.unique()))
    n_days = len(udays)
    bounds = np.linspace(0, n_days, N_GROUPS + 1).astype(int)
    groups = [udays[bounds[i]:bounds[i + 1]] for i in range(N_GROUPS)]
    embargo_n = max(1, int(round(n_days * EMBARGO_FRAC)))

    X_all = panel[kept].to_numpy()
    y_all = panel["fwd_1d"].to_numpy()
    day_of_row = dates

    # per-model: per (day) list of ICs across paths
    ic_store: dict[str, dict[pd.Timestamp, list[float]]] = {
        "gbm": {}, "ridge": {}, "linear": {}}

    paths = list(combinations(range(N_GROUPS), K_TEST))
    for pi, (gi, gj) in enumerate(paths, 1):
        test_days = groups[gi].union(groups[gj])
        # purge: drop train days within PURGE_DAYS of any test day;
        # embargo: drop train days in the embargo_n days AFTER each test block
        excluded = set(test_days)
        for g in (groups[gi], groups[gj]):
            lo = udays.searchsorted(g[0])
            hi = udays.searchsorted(g[-1])
            for off in range(1, PURGE_DAYS + 1):
                if lo - off >= 0:
                    excluded.add(udays[lo - off])
                if hi + off < n_days:
                    excluded.add(udays[hi + off])
            for off in range(1, embargo_n + 1):
                if hi + off < n_days:
                    excluded.add(udays[hi + off])
        train_mask = ~day_of_row.isin(excluded)
        test_mask = day_of_row.isin(set(test_days))
        Xtr, ytr = X_all[train_mask], y_all[train_mask]
        Xte = X_all[test_mask]
        te_days = day_of_row[test_mask]
        yte = y_all[test_mask]

        for mname in ("gbm", "ridge", "linear"):
            pred = fit_predict(mname, Xtr, ytr, Xte)
            df = pd.DataFrame({"day": te_days, "p": pred, "y": yte})
            for d, g in df.groupby("day"):
                if len(g) < MIN_NAMES_PER_DAY or g["p"].nunique() < 3:
                    continue
                ic = spearmanr(g["p"], g["y"]).statistic
                if np.isfinite(ic):
                    ic_store[mname].setdefault(d, []).append(float(ic))
        print(f"[T149-B] path {pi}/{len(paths)} done", flush=True)

    # aggregate: mean IC across paths per unique OOS day
    ic_series = {m: pd.Series({d: float(np.mean(v))
                               for d, v in ic_store[m].items()}).sort_index()
                 for m in ic_store}
    summary = {m: {"mean_daily_ic": round(float(s.mean()), 5),
                   "n_oos_days": int(len(s))}
               for m, s in ic_series.items()}

    d_gbm_ridge = (ic_series["gbm"] - ic_series["ridge"]).dropna()
    spa = spa_test({"gbm_minus_ridge": d_gbm_ridge}, b=1000, block=21, seed=SEED)
    bd = MetricsEngine.bootstrap_distribution(
        d_gbm_ridge, lambda r: float(np.mean(r)), n_iterations=1000, seed=SEED)

    survives = bool(spa["rejects_h0_at_05"] and bd["ci_low"] > 0)
    results = {
        "task": "T-2026-06-11-149 PartB",
        "features": kept,
        "models": ["gbm(monotonic,depth3,msl500)", "ridge(cv-alpha)",
                   "linear(uniform)"],
        "cpcv": {"n_groups": N_GROUPS, "k_test": K_TEST, "n_paths": len(paths),
                 "purge_days": PURGE_DAYS, "embargo_days": embargo_n},
        "n_trials_consumed": 3,
        "oos_ic_summary": summary,
        "kill_bar": {
            "spa": spa,
            "mean_ic_diff_gbm_minus_ridge": round(float(d_gbm_ridge.mean()), 6),
            "ci_low_ic_diff": round(float(bd["ci_low"]), 6),
            "ci_high_ic_diff": round(float(bd["ci_high"]), 6),
        },
        "VERDICT": "SURPRISE-SURVIVES" if survives else "DOOR CLOSED",
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T149-B] OOS mean daily IC: " +
          " | ".join(f"{m}={summary[m]['mean_daily_ic']:+.5f}" for m in summary))
    print(f"[T149-B] GBM−ridge: mean={results['kill_bar']['mean_ic_diff_gbm_minus_ridge']:+.6f} "
          f"ci[{results['kill_bar']['ci_low_ic_diff']:+.6f},{results['kill_bar']['ci_high_ic_diff']:+.6f}] "
          f"SPA p={spa['spa_p_value']:.3f}")
    print(f"[T149-B] VERDICT: {results['VERDICT']}")
    print(f"[T149-B] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
