"""
scripts/interaction_diagnostic_t132.py
======================================
T-2026-06-10-132 Part B — the non-linear interaction go/no-go diagnostic.

QUESTION: is there exploitable NON-LINEAR / INTERACTION structure between the
existing edges' signals and forward returns — i.e., is training the (built,
never-trained) metalearner even worthwhile? T-117 closed LINEAR recombination;
this closes (or opens) the non-linear door. Research Q4.

PRE-REGISTERED (fixed before running):
  - Data: per-ticker signal panel `data/research/per_ticker_scores/695b0b21-…`
    (1.85M rows, 109 tickers × 1004 dates, 2021-2024, 17 edges, norm_score).
    The metalearner consumes per-ticker edge signals → this is the faithful
    object. (T-117's PnL streams are returns, not signals — wrong object for a
    combination-of-signals question.)
  - Features: edges with nonzero norm_score on ≥1% of panel rows (→ 10 of 17;
    6 edges are all-zero in this log, panic_v1 at 0.4% drops).
  - Target: 1-day forward log close-to-close return per (ticker, date).
  - De-correlation FIRST (Friedman-Popescu: collinearity manufactures spurious
    H): greedy — order features by fire-rate desc; keep a feature only if
    max |ρ| vs already-kept < 0.5 (Phase-0 gate threshold).
  - Subsample: 30,000 rows (seed 0) for MI; GBM fit on the same subsample.
  - MI: sklearn mutual_info_regression (KSG-type kNN), n_neighbors=3, seed 0.
  - H-statistic: Friedman-Popescu pairwise H² via partial dependence on an 8×8
    per-feature-quantile grid, weighted by empirical cell frequency, model =
    GradientBoostingRegressor(200 trees, depth 3, lr 0.05, subsample 0.7,
    seed 0). PD-based route — no new dependency (per brief).
  - NULL (block-bootstrap, CLAUDE.md #6 — iid shuffles NOT acceptable): the
    forward-return panel is circularly time-shifted by a random offset
    k ∈ [21, T−21] (same k across tickers → preserves the target's full
    autocorrelation AND cross-sectional dependence; breaks signal↔return
    alignment). 200 null draws for MI; 60 null draws for H (GBM refit each)
    evaluated on the TOP-3 observed pairs.
  - VERDICT: METALEARNER GO iff ≥1 de-correlated pair has H² > its null 97.5th
    percentile AND H = sqrt(H²) > 0.10 (non-trivial interaction). Otherwise
    NO-GO (door closed; with T-117's linear negative, combination on existing
    edges is hopeless). Per-feature MI > null 97.5th pct reported as
    supporting context (marginal predictivity), not verdict-bearing.
  - N-accounting: this is a DIAGNOSTIC — no backtest configs consumed
    (N_trials += 0).

Usage: PYTHONHASHSEED=0 python -m scripts.interaction_diagnostic_t132
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.feature_selection import mutual_info_regression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PARQUET = ROOT / "data" / "research" / "per_ticker_scores" / \
    "695b0b21-18f0-4493-b593-e62abf091519.parquet"
OUT_DIR = ROOT / "data" / "measurements" / "alpha_frontier_t132"
OUT_JSON = OUT_DIR / "interaction_diagnostic.json"

MIN_NONZERO_FRAC = 0.01
DECORR_MAX_ABS_RHO = 0.5
SUBSAMPLE = 30_000
MI_NEIGHBORS = 3
N_NULL_MI = 200
N_NULL_H = 60
TOP_PAIRS_FOR_NULL = 3
GRID_Q = 8
H_NONTRIVIAL = 0.10
SEED = 0


# --------------------------------------------------------------------------- #
# Panel assembly
# --------------------------------------------------------------------------- #

def assemble_panel():
    df = pd.read_parquet(PARQUET, columns=["timestamp", "ticker", "edge_id", "norm_score"])
    fire = df.groupby("edge_id")["norm_score"].agg(lambda s: float((s != 0).mean()))
    feats = fire[fire >= MIN_NONZERO_FRAC].sort_values(ascending=False)
    X = (df[df.edge_id.isin(feats.index)]
         .pivot_table(index=["timestamp", "ticker"], columns="edge_id",
                      values="norm_score", aggfunc="last")
         .fillna(0.0))

    # forward 1-day log return per (ticker, date)
    closes = {}
    for t in X.index.get_level_values("ticker").unique():
        f = ROOT / "data" / "processed" / f"{t}_1d.csv"
        if not f.exists():
            continue
        c = pd.read_csv(f, index_col=0, parse_dates=True)["Close"].astype(float)
        closes[t] = np.log(c).diff().shift(-1)  # fwd return aligned to signal date
    fwd = pd.DataFrame(closes)
    fwd.index.name = "timestamp"
    y = fwd.stack()
    y.index.names = ["timestamp", "ticker"]
    y.name = "fwd_1d"

    panel = X.join(y, how="inner").dropna()
    return panel, feats


def decorrelate(panel: pd.DataFrame, feats_by_fire: pd.Series):
    cols = [c for c in feats_by_fire.index if c in panel.columns]
    corr = panel[cols].corr().abs()
    kept, dropped = [], {}
    for c in cols:  # already fire-rate-desc ordered
        if not kept:
            kept.append(c)
            continue
        mx = corr.loc[c, kept].max()
        if mx < DECORR_MAX_ABS_RHO:
            kept.append(c)
        else:
            dropped[c] = {"max_abs_rho_vs_kept": float(mx),
                          "vs": corr.loc[c, kept].idxmax()}
    return kept, dropped, corr


# --------------------------------------------------------------------------- #
# Null machinery: circular time-shift of the forward-return panel
# --------------------------------------------------------------------------- #

def make_shifted_targets(panel: pd.DataFrame, n_draws: int, rng: np.random.Generator):
    """Yield y vectors where the (date×ticker) forward-return matrix is rolled
    along the DATE axis by a random offset (same offset for all tickers)."""
    ymat = panel["fwd_1d"].unstack("ticker")  # date × ticker
    T = ymat.shape[0]
    offsets = rng.integers(21, T - 21, size=n_draws)
    for k in offsets:
        rolled = pd.DataFrame(np.roll(ymat.values, int(k), axis=0),
                              index=ymat.index, columns=ymat.columns)
        ys = rolled.stack()
        ys.index.names = ["timestamp", "ticker"]
        yield ys.reindex(panel.index), int(k)


# --------------------------------------------------------------------------- #
# Friedman-Popescu pairwise H² (grid PD, cell-frequency weighted)
# --------------------------------------------------------------------------- #

def _pd_1d(model, Xb: np.ndarray, j: int, grid: np.ndarray) -> np.ndarray:
    out = np.empty(len(grid))
    Xw = Xb.copy()
    for g, v in enumerate(grid):
        Xw[:, j] = v
        out[g] = model.predict(Xw).mean()
    return out - out.mean()


def _pd_2d(model, Xb: np.ndarray, j: int, k: int,
           gj: np.ndarray, gk: np.ndarray) -> np.ndarray:
    out = np.empty((len(gj), len(gk)))
    Xw = Xb.copy()
    for a, vj in enumerate(gj):
        Xw[:, j] = vj
        for b, vk in enumerate(gk):
            Xw[:, k] = vk
            out[a, b] = model.predict(Xw).mean()
    return out - out.mean()


def h2_pair(model, Xb: np.ndarray, j: int, k: int) -> float:
    qs = np.linspace(0.05, 0.95, GRID_Q)
    gj = np.unique(np.quantile(Xb[:, j], qs))
    gk = np.unique(np.quantile(Xb[:, k], qs))
    if len(gj) < 2 or len(gk) < 2:
        return 0.0
    pdj = _pd_1d(model, Xb, j, gj)
    pdk = _pd_1d(model, Xb, k, gk)
    pdjk = _pd_2d(model, Xb, j, k, gj, gk)
    # empirical cell-frequency weights
    cj = np.clip(np.digitize(Xb[:, j], gj) - 1, 0, len(gj) - 1)
    ck = np.clip(np.digitize(Xb[:, k], gk) - 1, 0, len(gk) - 1)
    w = np.zeros((len(gj), len(gk)))
    np.add.at(w, (cj, ck), 1.0)
    w /= w.sum()
    num = float((w * (pdjk - pdj[:, None] - pdk[None, :]) ** 2).sum())
    den = float((w * pdjk ** 2).sum())
    return num / den if den > 1e-18 else 0.0


def fit_gbm(X: np.ndarray, y: np.ndarray) -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.7, random_state=SEED,
    ).fit(X, y)


# --------------------------------------------------------------------------- #

def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    panel, fire = assemble_panel()
    kept, dropped, corr = decorrelate(panel, fire)
    print(f"[T132-B] panel: {len(panel)} rows | features kept {len(kept)}: {kept}")
    drop_desc = {k: "%.2f vs %s" % (v["max_abs_rho_vs_kept"], v["vs"])
                 for k, v in dropped.items()}
    print(f"[T132-B] dropped (|rho|>{DECORR_MAX_ABS_RHO}): {drop_desc}")

    sub_idx = rng.choice(len(panel), size=min(SUBSAMPLE, len(panel)), replace=False)
    sub_idx.sort()
    Xs = panel[kept].to_numpy()[sub_idx]
    ys = panel["fwd_1d"].to_numpy()[sub_idx]

    # ---- observed MI ----
    mi_obs = mutual_info_regression(Xs, ys, n_neighbors=MI_NEIGHBORS, random_state=SEED)
    # ---- MI nulls ----
    mi_null = np.zeros((N_NULL_MI, len(kept)))
    for i, (yshift, _k) in enumerate(make_shifted_targets(panel, N_NULL_MI, rng)):
        yv = yshift.to_numpy()[sub_idx]
        m = np.isfinite(yv)  # rolled cells where a ticker lacked data drop out
        mi_null[i] = mutual_info_regression(
            Xs[m], yv[m], n_neighbors=MI_NEIGHBORS, random_state=SEED)
        if (i + 1) % 50 == 0:
            print(f"[T132-B] MI nulls {i+1}/{N_NULL_MI} ({time.time()-t0:.0f}s)", flush=True)
    mi_p975 = np.percentile(mi_null, 97.5, axis=0)
    mi_pass = {kept[i]: {"mi": float(mi_obs[i]), "null_p975": float(mi_p975[i]),
                         "exceeds": bool(mi_obs[i] > mi_p975[i])}
               for i in range(len(kept))}

    # ---- observed H² on all kept pairs ----
    model = fit_gbm(Xs, ys)
    pairs = [(a, b) for a in range(len(kept)) for b in range(a + 1, len(kept))]
    h_obs = {}
    for (a, b) in pairs:
        h_obs[(a, b)] = h2_pair(model, Xs, a, b)
    top = sorted(h_obs, key=h_obs.get, reverse=True)[:TOP_PAIRS_FOR_NULL]
    print(f"[T132-B] observed H² computed for {len(pairs)} pairs "
          f"({time.time()-t0:.0f}s); top: "
          f"{[(kept[a], kept[b], round(h_obs[(a,b)],4)) for a,b in top]}", flush=True)

    # ---- H nulls on top pairs (GBM refit per draw) ----
    h_null = {p: [] for p in top}
    for i, (yshift, _k) in enumerate(make_shifted_targets(panel, N_NULL_H, rng)):
        yv = yshift.to_numpy()[sub_idx]
        m = np.isfinite(yv)
        m_null = fit_gbm(Xs[m], yv[m])
        for p in top:
            h_null[p].append(h2_pair(m_null, Xs[m], p[0], p[1]))
        if (i + 1) % 20 == 0:
            print(f"[T132-B] H nulls {i+1}/{N_NULL_H} ({time.time()-t0:.0f}s)", flush=True)

    h_report = {}
    any_go = False
    for p in top:
        null_arr = np.array(h_null[p])
        p975 = float(np.percentile(null_arr, 97.5))
        h2 = h_obs[p]
        h = float(np.sqrt(max(h2, 0.0)))
        passes = bool(h2 > p975 and h > H_NONTRIVIAL)
        any_go = any_go or passes
        h_report[f"{kept[p[0]]}__x__{kept[p[1]]}"] = {
            "h2_observed": float(h2), "h_observed": h,
            "null_p975_h2": p975, "null_median_h2": float(np.median(null_arr)),
            "exceeds_null": bool(h2 > p975), "h_above_0.10": bool(h > H_NONTRIVIAL),
            "PASSES": passes,
        }

    verdict = "GO" if any_go else "NO-GO"
    results = {
        "task": "T-2026-06-10-132 Part B",
        "panel_rows": int(len(panel)), "subsample": int(len(sub_idx)),
        "features_kept": kept,
        "features_dropped_decorr": dropped,
        "fire_rates": {k: float(fire[k]) for k in fire.index if fire[k] > 0},
        "mi_vs_null": mi_pass,
        "n_mi_features_exceeding_null": int(sum(v["exceeds"] for v in mi_pass.values())),
        "h_statistic_all_pairs_observed": {
            f"{kept[a]}__x__{kept[b]}": float(h_obs[(a, b)]) for a, b in pairs},
        "h_vs_null_top_pairs": h_report,
        "preregistered_verdict_rule": "GO iff >=1 pair: H2 > null 97.5pct AND H > 0.10",
        "VERDICT": verdict,
        "n_trials_consumed": 0,
    }
    # wall time deliberately NOT in the JSON — it would break bit-determinism
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    wall = round(time.time() - t0, 1)
    print(f"[T132-B] MI features exceeding null: "
          f"{results['n_mi_features_exceeding_null']}/{len(kept)}")
    for name, r in h_report.items():
        print(f"[T132-B] {name}: H²={r['h2_observed']:.4f} (H={r['h_observed']:.3f}) "
              f"null_p975={r['null_p975_h2']:.4f} PASSES={r['PASSES']}")
    print(f"[T132-B] VERDICT: METALEARNER {verdict}  ({wall}s)")
    print(f"[T132-B] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
