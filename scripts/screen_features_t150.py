"""
scripts/screen_features_t150.py
===============================
T-2026-06-11-150 Part C — pre-registered predictive screens on the new
feature panels. DIAGNOSTICS ONLY (N_trials += 0; no backtest configs, no
edge construction, no engine wiring — consumers get dispatched on these
numbers).

PRE-REGISTERED (committed before computing):

  SCREEN 1 — alpha-relevance MI vs block nulls (the T-132 machinery):
    For each Part-A feature {yz_vol_21, gk_vol_21, on_mean_21, on_share_21,
    gap_abs_z, gap_freq_21}: pooled (ticker,day) MI (KSG, k=3, seed 0)
    against the NEXT-DAY cross-sectional return, on a 30,000-row subsample,
    vs 200 circular-time-shift nulls (same scheme as T-132: shift the
    (date×ticker) forward-return matrix by a random offset ≥21d, same offset
    across tickers). PASS = MI > null 97.5th pct.
    For each Part-B index feature {fhh_ret, or_frac, last30_ret} (SPY):
    time-series MI against next-day SPY return vs the same null scheme.

  SCREEN 2 — THE YZ-vs-EWMA HORSE-RACE (the Engine-B thickening go/no-go
  input, computed WITHOUT touching Engine B):
    Forecast target: next-day realized variance proxied by gk_var_{t+1}
    (primary; range-based, opens-filtered) and r²_{t+1} (secondary).
    Competitors (variance forecasts):
      EWMA: RiskMetrics recursion on close-to-close returns, λ=0.94 — the
            EXACT production spec (engines/engine_b_risk/vol_target.py:70).
      YZ:   yz_vol_21² (the Part-A feature).
    Losses: QLIKE (primary; robust to noisy proxies) and MSE on variance.
    Verdict statistic: per-day cross-sectional mean QLIKE difference
    (EWMA − YZ; positive = YZ better) → block-bootstrap CI (B=1000, block=21,
    seed 0) + the SPA test (core.multiple_testing). Also report % of names
    with lower YZ QLIKE.

  Determinism: seed 0, no wall-clock in artifact, ×2.

Usage: PYTHONHASHSEED=0 python -m scripts.screen_features_t150
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_regression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402
from core.multiple_testing import spa_test  # noqa: E402

FEAT_A = ROOT / "data" / "research" / "ohlc_features_t150" / "features.parquet"
FEAT_B_DIR = ROOT / "data" / "research" / "minute_features_t150"
OUT_DIR = ROOT / "data" / "measurements" / "intraday_features_t150"
OUT_JSON = OUT_DIR / "screen_results.json"

A_FEATURES = ["yz_vol_21", "gk_vol_21", "on_mean_21", "on_share_21",
              "gap_abs_z", "gap_freq_21"]
B_FEATURES = ["fhh_ret", "or_frac", "last30_ret"]
SUBSAMPLE = 30_000
N_NULL = 200
EWMA_LAMBDA = 0.94          # production spec, vol_target.py:70
SEED = 0


def load_returns() -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 300:
            continue
        cols.append(np.log(df["Close"].astype(float)).diff().rename(
            f.split("/")[-1].replace("_1d.csv", "")))
    return pd.concat(cols, axis=1).sort_index()


def mi_with_nulls(X: np.ndarray, y_panel: pd.DataFrame, sub_idx: np.ndarray,
                  feat_names: list[str], row_day: pd.Series,
                  row_tic: pd.Series, rng) -> dict:
    """Pooled MI per feature vs forward return, with circular-shift nulls.

    Vectorized lookup: rows map into the (date, ticker)-stacked return panel
    via a MultiIndex reindex (the naive per-row .at lookup is O(rows × draws)
    and unusably slow at 30k × 201)."""
    mi_rows = pd.MultiIndex.from_arrays(
        [row_day.iloc[sub_idx].values, row_tic.iloc[sub_idx].values])
    Xsub = X[sub_idx]

    def _mi_against(panel: pd.DataFrame) -> np.ndarray:
        stacked = panel.stack()
        y = stacked.reindex(mi_rows).to_numpy()
        m = np.isfinite(y)
        return mutual_info_regression(Xsub[m], y[m], n_neighbors=3,
                                      random_state=SEED)

    mi_obs = _mi_against(y_panel)
    T = len(y_panel.index)
    mi_null = np.zeros((N_NULL, len(feat_names)))
    for i in range(N_NULL):
        k = int(rng.integers(21, T - 21))
        rolled = pd.DataFrame(np.roll(y_panel.values, k, axis=0),
                              index=y_panel.index, columns=y_panel.columns)
        mi_null[i] = _mi_against(rolled)
        if (i + 1) % 50 == 0:
            print(f"[T150-C] MI nulls {i+1}/{N_NULL}", flush=True)
    p975 = np.percentile(mi_null, 97.5, axis=0)
    return {feat_names[j]: {"mi": float(mi_obs[j]), "null_p975": float(p975[j]),
                            "exceeds": bool(mi_obs[j] > p975[j])}
            for j in range(len(feat_names))}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rets = load_returns()
    fwd = rets.shift(-1)

    # ---------- SCREEN 1A: Part-A features ----------
    fa = pd.read_parquet(FEAT_A)
    fa["date"] = pd.to_datetime(fa["date"])
    fa = fa.dropna(subset=A_FEATURES, how="any")
    fa = fa[fa["date"] >= "2005-01-01"]          # mature window, dense panel
    sub_idx = rng.choice(len(fa), size=min(SUBSAMPLE, len(fa)), replace=False)
    sub_idx.sort()
    mi_a = mi_with_nulls(fa[A_FEATURES].to_numpy(), fwd, sub_idx,
                         A_FEATURES, fa["date"], fa["ticker"], rng)

    # ---------- SCREEN 1B: Part-B index features (SPY) ----------
    mi_b = {}
    spy_p = FEAT_B_DIR / "SPY.parquet"
    if spy_p.exists() and "SPY" in fwd.columns:
        fb = pd.read_parquet(spy_p)
        fb.index = pd.to_datetime(fb.index)
        yb = fwd["SPY"].reindex(fb.index)
        ok = yb.notna() & fb[B_FEATURES].notna().all(axis=1)
        Xb, ybv = fb.loc[ok, B_FEATURES].to_numpy(), yb[ok].to_numpy()
        obs = mutual_info_regression(Xb, ybv, n_neighbors=3, random_state=SEED)
        Tb = len(ybv)
        nulls = np.zeros((N_NULL, len(B_FEATURES)))
        for i in range(N_NULL):
            k = int(rng.integers(21, Tb - 21))
            nulls[i] = mutual_info_regression(Xb, np.roll(ybv, k),
                                              n_neighbors=3, random_state=SEED)
        p975 = np.percentile(nulls, 97.5, axis=0)
        mi_b = {B_FEATURES[j]: {"mi": float(obs[j]), "null_p975": float(p975[j]),
                                "exceeds": bool(obs[j] > p975[j]),
                                "n_days": int(Tb)}
                for j in range(len(B_FEATURES))}
    else:
        mi_b = {"status": "SPY minute features not on disk yet"}

    # ---------- SCREEN 2: YZ vs production EWMA(0.94) ----------
    wide_yz = fa.pivot_table(index="date", columns="ticker", values="yz_vol_21")
    yz_var = (wide_yz ** 2) / 252.0                       # daily variance forecast
    # production EWMA recursion on close-to-close returns
    ewma_var = (rets ** 2).ewm(alpha=1 - EWMA_LAMBDA, adjust=False).mean()
    # target: next-day GK variance (primary), next-day r² (secondary)
    wide_gk = fa.pivot_table(index="date", columns="ticker", values="gk_vol_21")
    # use the 1-DAY gk variance: reconstruct from feature? gk_vol_21 is 21d —
    # for a single-day proxy use r²; for the smoothed proxy use gk_var_{t+1}.
    gk_var_next = ((wide_gk ** 2) / 252.0).shift(-1)
    r2_next = (rets ** 2).shift(-1)

    def qlike(f: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
        F = f.reindex_like(target).clip(lower=1e-10)
        T = target.clip(lower=1e-10)
        return np.log(F) + T / F

    common_cols = yz_var.columns.intersection(ewma_var.columns)
    idx = yz_var.index.intersection(ewma_var.index)
    out2 = {}
    for tname, target in [("gk_next_primary", gk_var_next),
                          ("r2_next_secondary", r2_next)]:
        tgt = target.reindex(index=idx, columns=common_cols)
        ql_e = qlike(ewma_var.reindex(index=idx, columns=common_cols), tgt)
        ql_y = qlike(yz_var.reindex(index=idx, columns=common_cols), tgt)
        d = (ql_e - ql_y)                       # positive = YZ better
        d_day = d.mean(axis=1).dropna()
        bd = MetricsEngine.bootstrap_distribution(
            d_day, lambda r: float(np.mean(r)), n_iterations=1000, seed=SEED)
        spa = spa_test({"yz_beats_ewma": d_day}, b=1000, block=21, seed=SEED)
        valid = d.notna()
        pct_names_yz_wins = float(
            (d.where(valid).mean(axis=0) > 0).mean())
        mse_e = float(((ewma_var.reindex(index=idx, columns=common_cols) - tgt) ** 2)
                      .stack().mean())
        mse_y = float(((yz_var.reindex(index=idx, columns=common_cols) - tgt) ** 2)
                      .stack().mean())
        out2[tname] = {
            "mean_daily_qlike_improvement_ewma_minus_yz": round(float(d_day.mean()), 6),
            "ci_low": round(float(bd["ci_low"]), 6),
            "ci_high": round(float(bd["ci_high"]), 6),
            "spa_p": spa["spa_p_value"],
            "yz_wins": bool(spa["rejects_h0_at_05"] and bd["ci_low"] > 0),
            "pct_names_where_yz_better": round(pct_names_yz_wins, 3),
            "mse_ewma": mse_e, "mse_yz": mse_y,
            "n_days": int(len(d_day)),
        }

    results = {
        "task": "T-2026-06-11-150 PartC",
        "n_trials_consumed": 0,
        "screen1_partA_mi_vs_null": mi_a,
        "screen1_partB_index_mi_vs_null": mi_b,
        "screen2_yz_vs_ewma094": out2,
        "notes": [
            "diagnostics only; no engine wiring; consumers dispatched on these numbers",
            "IEX price-shape caveat applies to Part-B features (volume features not computed)",
            f"EWMA spec = production vol_target.py lambda={EWMA_LAMBDA}",
        ],
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print("[T150-C] MI Part-A:", {k: v["exceeds"] for k, v in mi_a.items()})
    if "status" not in mi_b:
        print("[T150-C] MI Part-B:", {k: v["exceeds"] for k, v in mi_b.items()})
    for tname, r in out2.items():
        print(f"[T150-C] YZ-vs-EWMA [{tname}]: ΔQLIKE={r['mean_daily_qlike_improvement_ewma_minus_yz']:+.5f} "
              f"ci[{r['ci_low']:+.5f},{r['ci_high']:+.5f}] SPA p={r['spa_p']:.3f} "
              f"YZ_WINS={r['yz_wins']} (names better: {r['pct_names_where_yz_better']:.0%})")
    print(f"[T150-C] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
