"""RR-1 RE-SCORE — the pre-registered paired test on one before/after pair.

A descriptor of an existing RE-SCORE pair (N_trials 0): no threshold, no gate on the
answer. It exists because two per-arm CIs that overlap say nothing about the DIFFERENCE;
only a paired resample does. Pre-registration:
docs/Measurements/2026-09/rr1_rescore/PAIRED_TEST_PREREG.md.

Method: moving-block bootstrap (Künsch) with the SAME resampled block starts applied to
every series of the pair, block 19, 1,000 iterations, seed 0. Sharpe = mean/std·√252 and
Sortino = mean/std(negative days)·√252 — the definitions of orchestration/run_backtest_pure.py
and core/metrics_engine.py.

SANITY GATE FIRST: every series must reproduce its RECORDED Sharpe to 4 decimals, or the
script exits 2 and prints no Δ — a series that is not the harness's own measures nothing.

Usage:
  python scripts/rr1_paired_delta.py anchor --records docs/Measurements/2026-09/rr1_rescore \
      --cell anchor26 --trade-logs data/trade_logs
  python scripts/rr1_paired_delta.py feature --records docs/Measurements/2026-09/rr1_rescore \
      --cell t196_mom_12_1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BLOCK = 19
N_ITER = 1000
SEED = 0
TOL = 5e-5          # "reproduces to 4 decimals"


def sharpe(x: np.ndarray) -> float:
    sd = np.std(x, ddof=1)
    if sd is None or sd < 1e-12 or not np.isfinite(sd):
        return float("nan")
    return float(np.mean(x) / sd * np.sqrt(252))


def sortino(x: np.ndarray) -> float:
    neg = x[x < 0]
    sd = np.std(neg, ddof=1) if len(neg) > 1 else float("nan")
    if sd is None or sd < 1e-12 or not np.isfinite(sd):
        return float("nan")
    return float(np.mean(x) / sd * np.sqrt(252))


def _equity_returns(snapshots: Path) -> pd.Series:
    s = pd.read_csv(snapshots, usecols=["timestamp", "equity"], parse_dates=["timestamp"])
    s = s.drop_duplicates("timestamp", keep="last").set_index("timestamp")["equity"]
    return s.pct_change().dropna()


def _block_index(n: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, n - BLOCK + 1, int(np.ceil(n / BLOCK)))
    return (starts[:, None] + np.arange(BLOCK)).ravel()[:n]


def paired(series: dict[str, np.ndarray], deltas: dict[str, callable]) -> dict:
    """Every Δ is computed on the SAME resampled indices — that is what makes it paired."""
    n = len(next(iter(series.values())))
    rng = np.random.default_rng(SEED)
    draws: dict[str, list] = {k: [] for k in deltas}
    for _ in range(N_ITER):
        ix = _block_index(n, rng)
        sample = {k: v[ix] for k, v in series.items()}
        for k, f in deltas.items():
            draws[k].append(f(sample))
    out = {}
    for k, f in deltas.items():
        d = np.array(draws[k])
        lo, hi = np.percentile(d, [2.5, 97.5])
        out[k] = {"point": f(series), "ci95": [float(lo), float(hi)],
                  "share_le_0": float(np.mean(d <= 0))}
    return out


def _gate(checks: list[tuple[str, float, float]]) -> list[dict]:
    rows = [{"series": name, "recomputed": got, "recorded": want,
             "ok": bool(np.isfinite(got) and abs(got - want) < TOL)} for name, got, want in checks]
    for r in rows:
        print(f"  gate {r['series']:<22} recomputed {r['recomputed']:.6f} "
              f"recorded {r['recorded']:.6f}  {'OK' if r['ok'] else 'FAIL'}")
    return rows


def anchor(rec_dir: Path, cell: str, trade_logs: Path) -> dict:
    rec = {a: json.loads((rec_dir / f"{cell}_{a}.json").read_text()) for a in ("before", "after")}
    ret = {a: _equity_returns(trade_logs / rec[a]["run_id"] / "portfolio_snapshots.csv")
           for a in rec}
    idx = ret["before"].index.intersection(ret["after"].index)
    s = {a: ret[a].loc[idx].to_numpy() for a in ret}
    gate = _gate([(f"{a} sharpe", sharpe(s[a]), rec[a]["sharpe"]) for a in s] +
                 [(f"{a} sortino", sortino(s[a]), rec[a]["sortino"]) for a in s])
    res = {"cell": cell, "kind": "baseline", "n_days": len(idx), "gate": gate}
    if all(g["ok"] for g in gate if "sharpe" in g["series"]):
        sortino_ok = all(g["ok"] for g in gate if "sortino" in g["series"])
        deltas = {"d_sharpe": lambda x: sharpe(x["after"]) - sharpe(x["before"])}
        if sortino_ok:
            deltas["d_sortino"] = lambda x: sortino(x["after"]) - sortino(x["before"])
        res["deltas"] = paired(s, deltas)
        res["sortino_note"] = None if sortino_ok else "Sortino did not reproduce — Δ withheld"
    return res


def feature(rec_dir: Path, cell: str) -> dict:
    rec = {a: json.loads((rec_dir / f"{cell}_{a}.json").read_text()) for a in ("before", "after")}
    raw = {a: pd.read_csv(rec_dir / rec[a]["series_file"], index_col="date", parse_dates=True)
           for a in rec}
    # Each column is a daily_returns series as the harness built it; align all four on
    # their common dates (the attribution stream itself aligns on the intersection).
    cols = {f"{c}_{a}": raw[a][c].dropna() for a in raw for c in ("with_candidate", "baseline")}
    idx = None
    for v in cols.values():
        idx = v.index if idx is None else idx.intersection(v.index)
    s = {k: v.loc[idx].to_numpy() for k, v in cols.items()}
    row = {a: rec[a]["harness_rows"][0] for a in rec}
    # The gate reads the series AS CAPTURED (own dates), the way the harness scored them.
    gate = _gate([(f"{c}_{a}", sharpe(cols[f"{c}_{a}"].to_numpy()), row[a][f"{c}_sharpe"])
                  for a in rec for c in ("with_candidate", "baseline")])
    res = {"cell": cell, "kind": "feature", "feature": rec["after"].get("feature"),
           "n_days": len(idx), "gate": gate}
    if all(g["ok"] for g in gate):
        contrib = lambda x, a: sharpe(x[f"with_candidate_{a}"]) - sharpe(x[f"baseline_{a}"])
        res["deltas"] = paired(s, {
            "d_with_candidate_sharpe": lambda x: sharpe(x["with_candidate_after"]) - sharpe(x["with_candidate_before"]),
            "d_baseline_sharpe": lambda x: sharpe(x["baseline_after"]) - sharpe(x["baseline_before"]),
            "d_contribution_sharpe": lambda x: contrib(x, "after") - contrib(x, "before"),
        })
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["anchor", "feature"])
    ap.add_argument("--records", required=True, type=Path)
    ap.add_argument("--cell", required=True)
    ap.add_argument("--trade-logs", type=Path, help="anchor only: the run_isolated trades dir")
    a = ap.parse_args()
    res = (anchor(a.records, a.cell, a.trade_logs) if a.kind == "anchor"
           else feature(a.records, a.cell))
    res.update({"method": f"paired moving-block bootstrap, block {BLOCK}, {N_ITER} iter, "
                          f"seed {SEED}, same block starts for every series",
                "n_trials": 0, "prereg": "PAIRED_TEST_PREREG.md"})
    out = a.records / f"{a.cell}_paired_delta.json"
    out.write_text(json.dumps(res, indent=1))
    if "deltas" not in res:
        print(f"SANITY GATE FAILED — no Δ reported. Record: {out}")
        return 2
    for k, d in res["deltas"].items():
        print(f"  {k:<26} {d['point']:+.3f}  95% CI [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]"
              f"  share Δ≤0 {d['share_le_0']:.3f}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
