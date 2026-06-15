"""
scripts/analyze_t118r.py
========================
T-2026-06-14 — recompute Sharpe + block-bootstrap ci_low + MaxDD for T-118
re-run cells, from each cell's portfolio_snapshots.csv (the project standard:
recompute from equity, never trust rounded perf_summary fields — T-090).

Usage: python -m scripts.analyze_t118r <campaign_id> <arm> <window>
  e.g. python -m scripts.analyze_t118r t118r-decisive arm0_v1 26yr
Or import analyze_cell() / cmp pairs.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.metrics_engine import MetricsEngine  # noqa: E402

BUCKET = "archondex-results-407539788432"


def _s3_text(key: str) -> str:
    r = subprocess.run(["aws", "s3", "cp", f"s3://{BUCKET}/{key}", "-", "--profile", "archondex"],
                       capture_output=True, text=True)
    return r.stdout


def _s3_ls(prefix: str) -> str:
    r = subprocess.run(["aws", "s3", "ls", f"s3://{BUCKET}/{prefix}", "--recursive", "--profile", "archondex"],
                       capture_output=True, text=True)
    return r.stdout


def analyze_cell(campaign: str, arm: str, window: str, rep: str = "rep1") -> dict:
    pre = f"{campaign}/{arm}/{window}/{rep}/"
    ls = _s3_ls(pre)
    snap_key = next((l.split()[-1] for l in ls.splitlines()
                     if l.rstrip().endswith("portfolio_snapshots.csv")
                     and "_" not in l.split("/")[-1].replace("portfolio_snapshots.csv", "")), None)
    man_key = next((l.split()[-1] for l in ls.splitlines() if l.endswith("manifest.json")), None)
    if snap_key is None:
        return {"arm": arm, "window": window, "status": "no_snapshots"}
    df = pd.read_csv(io.StringIO(_s3_text(snap_key)), parse_dates=["timestamp"])
    eq = df.groupby(df["timestamp"].dt.date)["equity"].last()
    eq = eq[np.isfinite(eq.values) & (eq.values > 0)]
    eq_curve = pd.Series(eq.values, index=pd.to_datetime(eq.index))
    rets = eq_curve.pct_change().dropna()
    sharpe = MetricsEngine.sharpe_ratio(rets)
    boot = MetricsEngine.bootstrap_distribution(rets, MetricsEngine.sharpe_ratio,
                                                n_iterations=1000, seed=0)
    mdd = MetricsEngine.max_drawdown(eq_curve)
    canon = None
    if man_key:
        try:
            canon = json.loads(_s3_text(man_key)).get("canon_md5")
        except Exception:
            pass
    return {"arm": arm, "window": window, "status": "ok",
            "canon": canon, "n_days": len(rets),
            "sharpe": round(float(sharpe), 4),
            "ci_low": round(float(boot["ci_low"]), 4),
            "ci_high": round(float(boot["ci_high"]), 4),
            "maxdd_pct": round(float(mdd) * 100, 2),
            "cagr_pct": round((eq_curve.iloc[-1] / eq_curve.iloc[0]) ** (252.0 / len(rets)) * 100 - 100, 3),
            "terminal_equity": round(float(eq_curve.iloc[-1]), 2)}


def main() -> int:
    if len(sys.argv) >= 4:
        r = analyze_cell(sys.argv[1], sys.argv[2], sys.argv[3],
                         sys.argv[4] if len(sys.argv) > 4 else "rep1")
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
