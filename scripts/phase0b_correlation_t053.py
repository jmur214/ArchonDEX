"""scripts/phase0b_correlation_t053.py
========================================
T-053 Phase 0b: pairwise raw-signal correlation diagnostic on the
fresh per-ticker score capture (current 6 actives).

Mirrors the methodology in
`docs/Audit/pairwise_signal_correlation_phase0_2026_05_12.md`:
- Per-day cross-sectional mean approach (mean signal across tickers
  per (date, edge); correlate the resulting (date × edge) frame)
- Per-(ticker, date) panel Spearman (rank-based; robust to
  non-stationary scale)

Comparison: previous panel had avg|ρ|=0.156/max|ρ|=0.947 (per-day)
and avg|ρ|=0.098/max|ρ|=0.622 (per-panel). The strong prior is that
the current 6 actives — 4 of which are V/Q/A SimFin-derived — will
cluster ρ > 0.7 by construction.

Output: writes a JSON summary + appends "Phase 0b" section to the
existing audit doc.

Usage:
  PYTHONHASHSEED=0 python -m scripts.phase0b_correlation_t053 [run_uuid]

If `run_uuid` is omitted, the script picks the newest parquet in
`data/research/per_ticker_scores/`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PARQUET_DIR = ROOT / "data" / "research" / "per_ticker_scores"
OUT_JSON = ROOT / "docs" / "Audit" / "pairwise_signal_correlation_phase0b_2026_05_22.json"
PHASE0_AUDIT = ROOT / "docs" / "Audit" / "pairwise_signal_correlation_phase0_2026_05_12.md"

# Phase 0 reference numbers (from existing audit doc)
PHASE0_REFERENCE = {
    "per_day_avg_abs_rho": 0.156,
    "per_day_max_abs_rho": 0.947,
    "per_panel_avg_abs_rho": 0.098,
    "per_panel_max_abs_rho": 0.622,
}


def _pick_newest_parquet(uuid_arg: Optional[str]) -> Path:
    if uuid_arg:
        p = PARQUET_DIR / f"{uuid_arg}.parquet"
        if not p.exists():
            raise FileNotFoundError(p)
        return p
    candidates = sorted(
        PARQUET_DIR.glob("*.parquet"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"no parquets in {PARQUET_DIR}")
    return candidates[0]


def _build_per_day_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional mean per (date, edge_id). Returns date-indexed
    frame with columns = edge_ids. Days where a given edge didn't
    fire on any ticker get NaN, which the correlation step ignores
    pairwise."""
    g = df.groupby(["timestamp", "edge_id"])["raw_score"].mean().unstack("edge_id")
    return g


def _build_panel_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Per-(ticker, date) wide frame: rows = (ticker, date), cols =
    edge_ids, values = raw_score. NaN where edge didn't emit."""
    g = (
        df.pivot_table(
            index=["ticker", "timestamp"],
            columns="edge_id",
            values="raw_score",
            aggfunc="mean",
        )
    )
    return g


def _abs_corr_stats(corr: pd.DataFrame) -> dict:
    """Return avg|ρ|, max|ρ|, top-5 pairs from a correlation matrix.
    Diagonal excluded; lower-triangle scanned."""
    n = corr.shape[0]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            v = corr.iat[i, j]
            if np.isnan(v):
                continue
            pairs.append((
                corr.index[i], corr.columns[j], float(v),
            ))
    if not pairs:
        return {
            "n_edges": n,
            "n_pairs": 0,
            "avg_abs_rho": 0.0,
            "max_abs_rho": 0.0,
            "top_5_pairs": [],
        }
    abs_vals = [abs(v) for _, _, v in pairs]
    avg_abs = sum(abs_vals) / len(abs_vals)
    max_idx = max(range(len(pairs)), key=lambda i: abs_vals[i])
    sorted_pairs = sorted(pairs, key=lambda p: abs(p[2]), reverse=True)
    return {
        "n_edges": n,
        "n_pairs": len(pairs),
        "avg_abs_rho": round(avg_abs, 4),
        "max_abs_rho": round(abs(pairs[max_idx][2]), 4),
        "top_5_pairs": [
            {"a": a, "b": b, "rho": round(v, 4)}
            for a, b, v in sorted_pairs[:5]
        ],
    }


def main() -> int:
    uuid_arg = sys.argv[1] if len(sys.argv) > 1 else None
    parquet_path = _pick_newest_parquet(uuid_arg)
    print(f"[T-053-Phase-0b] reading {parquet_path}", flush=True)
    df = pd.read_parquet(parquet_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    print(f"[T-053-Phase-0b] rows: {len(df):,}  unique edges: "
          f"{df['edge_id'].nunique()}  unique tickers: "
          f"{df['ticker'].nunique()}", flush=True)
    print(f"[T-053-Phase-0b] edges: {sorted(df['edge_id'].unique())}",
          flush=True)

    # Approach 1: per-day cross-sectional mean
    per_day_wide = _build_per_day_frame(df)
    per_day_pearson = per_day_wide.corr(method="pearson")
    per_day_spearman = per_day_wide.corr(method="spearman")
    per_day_pearson_stats = _abs_corr_stats(per_day_pearson)
    per_day_spearman_stats = _abs_corr_stats(per_day_spearman)

    # Approach 2: per-(ticker, date) panel
    panel_wide = _build_panel_frame(df)
    panel_pearson = panel_wide.corr(method="pearson")
    panel_spearman = panel_wide.corr(method="spearman")
    panel_pearson_stats = _abs_corr_stats(panel_pearson)
    panel_spearman_stats = _abs_corr_stats(panel_spearman)

    out = {
        "task_id": "T-2026-05-22-053",
        "phase": "Phase 0b — fresh capture",
        "input_parquet": str(parquet_path.relative_to(ROOT)),
        "n_rows": int(len(df)),
        "n_unique_edges": int(df["edge_id"].nunique()),
        "n_unique_tickers": int(df["ticker"].nunique()),
        "edges": sorted(df["edge_id"].unique().tolist()),
        "approach_1_per_day_cross_sectional_mean": {
            "pearson": per_day_pearson_stats,
            "spearman": per_day_spearman_stats,
        },
        "approach_2_per_ticker_date_panel": {
            "pearson": panel_pearson_stats,
            "spearman": panel_spearman_stats,
        },
        "phase_0_reference": PHASE0_REFERENCE,
        "gate_decision": {
            "threshold_avg_abs_rho": 0.3,
            "threshold_max_abs_rho": 0.5,
            "fires_on_avg": (
                per_day_spearman_stats["avg_abs_rho"] > 0.3
                or panel_spearman_stats["avg_abs_rho"] > 0.3
            ),
            "fires_on_max": (
                per_day_spearman_stats["max_abs_rho"] > 0.5
                or panel_spearman_stats["max_abs_rho"] > 0.5
            ),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"[T-053-Phase-0b] wrote {OUT_JSON}", flush=True)
    print("[T-053-Phase-0b] approach 1 (per-day, Spearman):",
          f"avg|ρ|={per_day_spearman_stats['avg_abs_rho']}",
          f"max|ρ|={per_day_spearman_stats['max_abs_rho']}", flush=True)
    print("[T-053-Phase-0b] approach 2 (per-panel, Spearman):",
          f"avg|ρ|={panel_spearman_stats['avg_abs_rho']}",
          f"max|ρ|={panel_spearman_stats['max_abs_rho']}", flush=True)
    print(
        "[T-053-Phase-0b] gate decision: fires_on_max="
        f"{out['gate_decision']['fires_on_max']}, fires_on_avg="
        f"{out['gate_decision']['fires_on_avg']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
