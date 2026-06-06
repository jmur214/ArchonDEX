"""
scripts/edge_compression_t117.py
================================
T-2026-06-06-117 — Edge compression to orthogonal sleeves (MEASURE + PROPOSE).

Hypothesis (Daniel-Hirshleifer-Sun 2020, Anton-Polk 2014, restated by the
director's brief): the active/tradeable edge inventory is heavily REDUNDANT by
theme (momentum variants, value/quality variants, PEAD siblings). Redundant
variants SPLIT one underlying signal and inflate the multiple-testing penalty
without adding independent information. So a COMPRESSED set of 3-4 orthogonal
sleeves MIGHT clear joint factor-alpha t>2 where the bloated set did not.

This script MEASURES the compression. It does NOT retire edges, edit edges.yml,
or touch the governor. Output is evidence + a retirement PROPOSAL for the
director to gate through Engine F lifecycle.

Reuse (no reimplementation of the factor model):
  - core.factor_decomposition.load_factor_data            -> FF5+Mom+RF panel
  - scripts.factor_decomp_substrate_honest.regress_with_hac -> HAC alpha/t/CI
  - scripts.factor_decomp_substrate_honest.{newey_west_lag,newey_west_cov,
        FACTOR_COLS, INITIAL_CAPITAL}
  - engines.engine_f_governance.factor_alpha_gate.compute_alpha_tstat_with_bootstrap_ci
        -> HAC alpha-t-stat with residual moving-block bootstrap CI (the
           project-canonical joint-alpha + CI used by the retirement gate)
  - core.metrics_engine.MetricsEngine.bootstrap_distribution -> Sharpe block-boot CI
  - HRP correlation-distance + scipy linkage (the convention in
        engines/engine_c_portfolio/optimizers/hrp.py)

Substrate (zero new compute — existing config-consistent trade logs):
  - PRIMARY: 5 single-year ENSEMBLE runs 2021-2025 (snapshot 2026-05-22 campaign,
    $100k start, same engine versions), each with the full ~17-18 edge bloated
    set trading. Stitched into a multi-regime per-edge daily-return panel.
  - ROBUSTNESS: one 12-yr (2014-2025) 15-edge ensemble run for deep-window Sharpe.

Per-edge return convention matches tier_classifier / factor_alpha_gate:
  daily realized PnL (net of costs) summed by closure date / INITIAL_CAPITAL.

Usage:
  PYTHONHASHSEED=0 python -m scripts.edge_compression_t117
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.factor_decomposition import load_factor_data  # noqa: E402
from core.metrics_engine import MetricsEngine  # noqa: E402
from scripts.factor_decomp_substrate_honest import (  # noqa: E402
    FACTOR_COLS,
    INITIAL_CAPITAL,
    regress_with_hac,
)
from engines.engine_f_governance.factor_alpha_gate import (  # noqa: E402
    compute_alpha_tstat_with_bootstrap_ci,
)
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram  # noqa: E402
from scipy.spatial.distance import squareform  # noqa: E402

TRADE_LOGS = ROOT / "data" / "trade_logs"
OUT_DIR = ROOT / "data" / "measurements" / "edge_compression_t117_2026_06_06"
OUT_JSON = OUT_DIR / "edge_compression_results.json"

# PRIMARY substrate: 5 single-year ENSEMBLE runs (full bloated edge set),
# 2026-05-22 campaign, rep with highest trade count per year. Config-verified
# identical (engine versions A0.3.0/B0.1.0/C0.2.0, $100k start, wash_sale off).
PANEL_RUN_STUBS = {
    2021: "5039870e",
    2022: "8c577ca4",
    2023: "61394c4c",
    2024: "157e5d58",
    2025: "6b7bf3f8",
}

# ROBUSTNESS substrate: 12-yr (2014-2025) 15-edge ensemble run (3 reps
# bitwise-identical; determinism PASS). Momentum-family + low_vol + volume +
# gap trade densely here; value/quality/accruals do NOT appear on this run.
DEEP_RUN_STUB = "0dcae34c"

# Edges too sparse to support a stable pairwise residual correlation get
# decomposed individually but excluded from the dendrogram. ~1 obs/3 trading
# days minimum over the 5-yr panel.
MIN_DAYS_FOR_CLUSTER = 60
MIN_OBS_FOR_HAC = 30


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def _resolve_run(stub: str) -> Path:
    matches = sorted(glob.glob(str(TRADE_LOGS / f"{stub}*")))
    dirs = [Path(m) for m in matches if (Path(m) / "trades.csv").exists()]
    if not dirs:
        raise FileNotFoundError(f"No trades.csv for run stub {stub}")
    return dirs[0]


def _load_trades(run_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(run_dir / "trades.csv", low_memory=False,
                     usecols=["timestamp", "edge_id", "pnl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce")
    return df.dropna(subset=["pnl"])


def build_panel(run_stubs: Dict[int, str]) -> Dict[str, pd.Series]:
    """Per-edge daily-return panel stitched across the yearly runs.

    Convention identical to factor_alpha_gate.daily_returns_from_closed_trades:
    sum closed-trade pnl by date per edge_id, / INITIAL_CAPITAL, days with no
    closure for an edge are absent (not zero-filled) — matches tier_classifier.
    """
    parts: Dict[str, List[pd.Series]] = {}
    for _year, stub in sorted(run_stubs.items()):
        trades = _load_trades(_resolve_run(stub))
        trades["date"] = trades["timestamp"].dt.normalize()
        for edge, sub in trades.groupby("edge_id"):
            if not isinstance(edge, str) or edge in ("Unknown", "nan"):
                continue
            daily = sub.groupby("date")["pnl"].sum() / INITIAL_CAPITAL
            parts.setdefault(edge, []).append(daily)
    out: Dict[str, pd.Series] = {}
    for edge, segs in parts.items():
        s = pd.concat(segs).sort_index()
        s = s[~s.index.duplicated(keep="first")]
        s.name = edge
        out[edge] = s
    return out


# --------------------------------------------------------------------------- #
# Factor orthogonalization (reuse regress_with_hac; derive residual stream
# from the SAME excess/FACTOR_COLS convention)
# --------------------------------------------------------------------------- #

def factor_residual_stream(edge_returns: pd.Series,
                           factors: pd.DataFrame) -> Optional[pd.Series]:
    """Date-indexed FF5+Mom residual (idiosyncratic) return stream.

    Mirrors the aligned-lstsq core of regress_with_hac /
    compute_alpha_tstat_with_bootstrap_ci: residual = excess - X_design @ coefs,
    on the inner-join of the edge's trading days and the factor panel.
    """
    aligned = pd.concat([edge_returns.rename("edge"), factors],
                        axis=1, join="inner").dropna()
    if len(aligned) < MIN_OBS_FOR_HAC:
        return None
    excess = (aligned["edge"] - aligned["RF"]).values
    X = aligned[FACTOR_COLS].values
    X_design = np.hstack([np.ones((len(excess), 1)), X])
    coefs, _, _, _ = np.linalg.lstsq(X_design, excess, rcond=None)
    resid = excess - X_design @ coefs
    return pd.Series(resid, index=aligned.index, name=edge_returns.name)


def factor_information_ratio(alpha_daily: float, residual: pd.Series) -> float:
    """Annualized factor-adjusted (cost-adjusted, since PnL is net) IR =
    alpha_daily / residual_std_daily * sqrt(252).

    NOTE: the OLS residual is mean-zero BY CONSTRUCTION (the intercept absorbs
    the mean), so mean(resid)/std(resid) ~ 0 for every edge and is useless for
    ranking. The information ratio uses the *intercept* (alpha) over the
    idiosyncratic vol. All edges here are factor-NEGATIVE, so this IR is
    negative; the per-cluster representative is the LEAST-negative (best) edge."""
    r = residual.dropna()
    if len(r) < 2:
        return 0.0
    sd = float(r.std())
    if sd < 1e-12:
        return 0.0
    return float(alpha_daily / sd * np.sqrt(252))


# --------------------------------------------------------------------------- #
# Clustering (HRP correlation-distance + scipy linkage)
# --------------------------------------------------------------------------- #

def cluster_residuals(resid_df: pd.DataFrame):
    """Hierarchical clustering on residual-return correlation distance.

    Distance d_ij = sqrt(0.5 * (1 - corr_ij)) (López de Prado / hrp.py).
    Returns (corr, linkage_matrix, labels_by_threshold dict, leaf_order).
    """
    corr = resid_df.corr(method="pearson", min_periods=30)
    # Fill any unestimable pairs (too little overlap) with 0 corr (orthogonal).
    corr = corr.fillna(0.0)
    corr_arr = corr.to_numpy(copy=True)
    np.fill_diagonal(corr_arr, 1.0)
    corr = pd.DataFrame(corr_arr, index=corr.index, columns=corr.columns)
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr_arr), 0.0, None))
    np.fill_diagonal(dist, 0.0)
    dist = (dist + dist.T) / 2.0  # enforce symmetry
    link = linkage(squareform(dist, checks=False), method="average")
    leaf_order = [resid_df.columns[i] for i in dendrogram(link, no_plot=True)["leaves"]]
    labels = {}
    for k in (3, 4, 5):
        labels[k] = dict(zip(resid_df.columns,
                             fcluster(link, t=k, criterion="maxclust")))
    return corr, link, labels, leaf_order


# --------------------------------------------------------------------------- #
# Joint factor-alpha + Sharpe with block-bootstrap CI
# --------------------------------------------------------------------------- #

def combined_stream(streams: Dict[str, pd.Series], edges: List[str],
                    weights: Optional[Dict[str, float]] = None,
                    calendar: Optional[pd.Index] = None) -> pd.Series:
    """Equal- or custom-weighted sum of per-edge daily return streams.

    A day with no realized closure for an edge contributes 0 (realized-PnL
    attribution convention — same as tier_classifier / T-036). When `calendar`
    is given, the result is reindexed onto it (zero-filled) so subsets of
    different active-day coverage are compared on the SAME grid — otherwise a
    sparse subset is silently measured only on its own active days, mismatching
    the bloated set's calendar and inflating its Sharpe."""
    if not edges:
        return pd.Series(dtype=float)
    w = weights or {e: 1.0 for e in edges}
    frame = pd.concat({e: streams[e] for e in edges if e in streams},
                      axis=1, sort=True)
    frame = frame.fillna(0.0)
    for e in frame.columns:
        frame[e] = frame[e] * w.get(e, 1.0)
    combined = frame.sum(axis=1).sort_index()
    if calendar is not None:
        combined = combined.reindex(calendar).fillna(0.0)
    return combined


def joint_alpha(stream: pd.Series, factors: pd.DataFrame) -> Dict:
    """HAC FF5+Mom alpha t-stat with residual moving-block bootstrap CI
    (reuse the Engine F retirement-gate function — the project canon)."""
    res = compute_alpha_tstat_with_bootstrap_ci(stream, factors,
                                                 min_obs=MIN_OBS_FOR_HAC,
                                                 n_iter=1000, seed=0)
    # Also the full annualized-alpha decomp for context.
    hac = regress_with_hac(stream, factors, "combined")
    return {
        "n_obs": res.n_obs,
        "alpha_tstat_point": res.alpha_tstat_point,
        "alpha_tstat_ci_low": res.alpha_tstat_ci_low,
        "alpha_tstat_ci_high": res.alpha_tstat_ci_high,
        "alpha_annual_pct": (hac.get("alpha_annualized", 0.0) * 100.0
                             if hac.get("ok") else None),
        "alpha_annual_ci_low_pct": (hac.get("alpha_ci_low_bootstrap") * 100.0
                                    if hac.get("ok") else None),
        "p_alpha_above_zero": (hac.get("alpha_p_above_zero_bootstrap")
                               if hac.get("ok") else None),
        "clears_t2_point": res.alpha_tstat_point > 2.0,
        "clears_t2_strict_ci": res.alpha_tstat_ci_low > 2.0,
    }


def sharpe_with_ci(stream: pd.Series) -> Dict:
    """Block-bootstrap Sharpe CI of a combined attribution stream.

    CAVEAT: this is an ATTRIBUTION-CONTRIBUTION Sharpe (sum of per-edge
    net-PnL/capital), NOT a deployable portfolio Sharpe. For a SPARSE subset
    (few active days) the union-of-days stream is mostly zeros, so std is tiny
    and Sharpe is inflated — idle capital is invisible. `frac_active_days`
    quantifies the sparsity; compare only across similar-density sets. A clean
    portfolio Sharpe needs an isolation re-run of the subset (gated follow-up)."""
    r = stream.dropna()
    bd = MetricsEngine.bootstrap_distribution(
        r, MetricsEngine.sharpe_ratio, n_iterations=1000, seed=0)
    frac_active = float((r != 0).mean()) if len(r) else 0.0
    return {
        "n_obs": int(len(r)),
        "frac_active_days": frac_active,
        "sharpe_point": bd["point_estimate"],
        "sharpe_ci_low": bd["ci_low"],
        "sharpe_ci_high": bd["ci_high"],
        "p_above_zero": bd["p_above_zero"],
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    print(f"[T117] factors: {factors.shape[0]} days "
          f"{factors.index.min().date()}..{factors.index.max().date()}")

    # ---- Build 5-yr dense panel ----
    streams = build_panel(PANEL_RUN_STUBS)
    panel_meta = []
    for e, s in sorted(streams.items(), key=lambda kv: -len(kv[1])):
        panel_meta.append({"edge": e, "n_days": int(len(s)),
                           "first": str(s.index.min().date()),
                           "last": str(s.index.max().date())})
    print(f"[T117] panel: {len(streams)} edges trade across 2021-2025")
    for m in panel_meta:
        print(f"    {m['edge']:32s} {m['n_days']:5d} days")

    # ---- Per-edge factor decomp (reproduce/extend T-036 to the bloated set) ----
    per_edge = {}
    resid_streams = {}
    for e, s in streams.items():
        hac = regress_with_hac(s, factors, e)
        if not hac.get("ok"):
            per_edge[e] = {"ok": False, "n_obs": hac.get("n_obs", 0),
                           "reason": hac.get("reason", "?")}
            continue
        resid = factor_residual_stream(s, factors)
        factor_ir = (factor_information_ratio(hac["alpha_daily"], resid)
                     if resid is not None else 0.0)
        per_edge[e] = {
            "ok": True,
            "n_obs": hac["n_obs"],
            "alpha_annual_pct": hac["alpha_annualized"] * 100.0,
            "alpha_tstat": hac["alpha_tstat_hac"],
            "alpha_boot_ci_low_pct": hac["alpha_ci_low_bootstrap"] * 100.0,
            "alpha_boot_ci_high_pct": hac["alpha_ci_high_bootstrap"] * 100.0,
            "p_alpha_above_zero": hac["alpha_p_above_zero_bootstrap"],
            "r_squared": hac["r_squared"],
            "raw_sharpe": (float(s.mean() / s.std() * np.sqrt(252))
                          if s.std() > 1e-12 else 0.0),
            "factor_ir_annual": factor_ir,
            "n_resid_days": int(len(resid)) if resid is not None else 0,
        }
        if resid is not None and len(resid) >= MIN_DAYS_FOR_CLUSTER:
            resid_streams[e] = resid

    # ---- Cluster the clusterable edges on residual correlation ----
    resid_df = pd.DataFrame(resid_streams)
    corr, link, labels, leaf_order = cluster_residuals(resid_df)
    print(f"[T117] clustering {resid_df.shape[1]} edges "
          f"(>= {MIN_DAYS_FOR_CLUSTER} resid days)")
    # Choose k=4 sleeves per brief target (3-4); report k=3,5 too.
    k = 4
    cluster_map = labels[k]
    clusters: Dict[int, List[str]] = {}
    for e, c in cluster_map.items():
        clusters.setdefault(int(c), []).append(e)

    # ---- Pick representative per cluster by factor IR (least-negative wins) ----
    representatives = {}
    for c, members in sorted(clusters.items()):
        best = max(members, key=lambda e: per_edge[e]["factor_ir_annual"])
        representatives[c] = {
            "representative": best,
            "members": members,
            "rep_factor_ir": per_edge[best]["factor_ir_annual"],
            "member_irs": {e: per_edge[e]["factor_ir_annual"] for e in members},
        }
    compressed_set = [v["representative"] for v in representatives.values()]
    bloated_set = list(streams.keys())
    clusterable_set = list(resid_streams.keys())
    # Common calendar (union of ALL panel edge-days) so every subset is scored
    # on the same grid — removes the active-day-coverage mismatch.
    master_cal = combined_stream(streams, bloated_set).index
    print(f"[T117] compressed set (k={k}): {compressed_set}")

    # ---- Joint factor-alpha: compressed vs bloated vs clusterable ----
    joint = {
        "bloated_all": joint_alpha(
            combined_stream(streams, bloated_set, calendar=master_cal), factors),
        "clusterable_only": joint_alpha(
            combined_stream(streams, clusterable_set, calendar=master_cal), factors),
        "compressed_representatives": joint_alpha(
            combined_stream(streams, compressed_set, calendar=master_cal), factors),
    }
    for name, j in joint.items():
        print(f"[T117] joint-alpha {name:28s} "
              f"t={j['alpha_tstat_point']:+.2f} "
              f"ci[{j['alpha_tstat_ci_low']:+.2f},{j['alpha_tstat_ci_high']:+.2f}] "
              f"clears_t2_point={j['clears_t2_point']}")

    # ---- Portfolio Sharpe: compressed vs bloated (5-yr panel, common grid) ----
    sharpe = {
        "bloated_all": sharpe_with_ci(
            combined_stream(streams, bloated_set, calendar=master_cal)),
        "clusterable_only": sharpe_with_ci(
            combined_stream(streams, clusterable_set, calendar=master_cal)),
        "compressed_representatives": sharpe_with_ci(
            combined_stream(streams, compressed_set, calendar=master_cal)),
    }
    for name, sh in sharpe.items():
        print(f"[T117] sharpe {name:28s} "
              f"S={sh['sharpe_point']:+.3f} "
              f"ci[{sh['sharpe_ci_low']:+.3f},{sh['sharpe_ci_high']:+.3f}]")

    # ---- 12-yr robustness on the deep run ----
    deep_streams = build_panel({2014: DEEP_RUN_STUB})  # single 12-yr run
    deep_compressed = [e for e in compressed_set if e in deep_streams]
    deep_cal = combined_stream(deep_streams, list(deep_streams.keys())).index
    deep = {
        "available_edges": {e: int(len(s)) for e, s in
                            sorted(deep_streams.items(), key=lambda kv: -len(kv[1]))},
        "compressed_in_deep": deep_compressed,
        "sharpe_bloated_all": sharpe_with_ci(
            combined_stream(deep_streams, list(deep_streams.keys()), calendar=deep_cal)),
        "sharpe_compressed": (sharpe_with_ci(
            combined_stream(deep_streams, deep_compressed, calendar=deep_cal))
            if deep_compressed else None),
        "joint_alpha_bloated_all": joint_alpha(
            combined_stream(deep_streams, list(deep_streams.keys()), calendar=deep_cal),
            factors),
        "joint_alpha_compressed": (joint_alpha(
            combined_stream(deep_streams, deep_compressed, calendar=deep_cal), factors)
            if deep_compressed else None),
    }
    print(f"[T117] DEEP 12-yr bloated sharpe "
          f"{deep['sharpe_bloated_all']['sharpe_point']:+.3f} "
          f"joint-alpha t={deep['joint_alpha_bloated_all']['alpha_tstat_point']:+.2f}")

    # ---- Persist ----
    results = {
        "task": "T-2026-06-06-117",
        "panel_run_stubs": PANEL_RUN_STUBS,
        "deep_run_stub": DEEP_RUN_STUB,
        "panel_meta": panel_meta,
        "per_edge_factor_decomp": per_edge,
        "clusters_k4": {str(c): m for c, m in clusters.items()},
        "clusters_k3": {e: int(labels[3][e]) for e in labels[3]},
        "clusters_k5": {e: int(labels[5][e]) for e in labels[5]},
        "leaf_order": leaf_order,
        "residual_corr": json.loads(corr.round(3).to_json()),
        "representatives": {str(c): v for c, v in representatives.items()},
        "compressed_set": compressed_set,
        "bloated_set": bloated_set,
        "clusterable_set": clusterable_set,
        "joint_alpha": joint,
        "portfolio_sharpe": sharpe,
        "deep_12yr": deep,
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T117] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
