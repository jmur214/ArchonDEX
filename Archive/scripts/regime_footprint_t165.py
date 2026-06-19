"""
scripts/regime_footprint_t165.py
================================
T-2026-06-13-165 — regime-footprint LOCAL diagnostic (subprocess version).

Does regime-blindness (the cloud condition: regime → unknown, no HMM, no
advisory) change production numbers, or is it benign? Mechanism
instrumentation (an existing layer's causal effect) — NOT strategy
selection; zero N_trials.

4 cells = {regime-live, regime-blind} × {adaptive, mean_variance} on 2022
(a real crisis/bear year that produces trades in the current substrate;
the COVID 2019-2020 sub-window produces 0 trades here, a separate gap).

Each cell is a FRESH subprocess of run_isolated (the reliable CLI path —
in-process multi-run is fragile). Force-blind = env flag
ARCHONDEX_FORCE_REGIME_BLIND=1 → RegimeDetector.detect_regime returns the
exact cloud-unknown dict (diagnostic hook in regime_detector.py, default
OFF, reverted after). Allocator axis (T-158): mean_variance = the Apr-23
allocation_recommendations.json artifact DISPLACED (copy-preserved);
adaptive = artifact present. data/macro is NEVER touched.

Usage: PYTHONHASHSEED=0 python -m scripts.regime_footprint_t165
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "data" / "research" / "allocation_recommendations.json"
TRADES_DIR = ROOT / "data" / "trade_logs"
OUT = ROOT / "data" / "research" / "t165" / "footprint.json"
YEAR = "2022"


def _md5(p: Path):
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None


def _run_cell(blind: bool) -> dict:
    before = {p.name for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"}
    env = dict(os.environ, PYTHONHASHSEED="0")
    if blind:
        env["ARCHONDEX_FORCE_REGIME_BLIND"] = "1"
    else:
        env.pop("ARCHONDEX_FORCE_REGIME_BLIND", None)
    r = subprocess.run(
        [sys.executable, "-m", "scripts.run_isolated", "--task", "q1", "--year", YEAR],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )
    out = r.stdout
    canon = (re.search(r"trades_canon_md5:\s*([0-9a-f]+)", out) or [None, None])[1]
    sharpe = (re.search(r"Sharpe:\s*([-0-9.]+)", out) or [None, None])[1]
    run_id = (re.search(r"run_id:\s*([0-9a-f-]+)", out) or [None, None])[1]
    # regime-symptom census from stdout
    unknown = out.count("'regime': 'unknown'")
    hmm_lines = out.count("hmm_regime")
    # metrics from the run dir
    new = {p.name for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"} - before
    rd = TRADES_DIR / (run_id if run_id else (next(iter(new)) if new else "?"))
    trades = mdd = gross_mean = gross_max = None
    perf = rd / "performance_summary.json"
    if perf.exists():
        p = json.loads(perf.read_text())
        trades = p.get("Total Trades"); mdd = p.get("Max Drawdown (%)")
    snap = rd / "portfolio_snapshots.csv"
    if snap.exists():
        df = pd.read_csv(snap)
        if {"gross_notional", "equity"} <= set(df.columns):
            gf = (df["gross_notional"] / df["equity"].replace(0, pd.NA)).dropna()
            if len(gf):
                gross_mean = round(float(gf.mean()), 4); gross_max = round(float(gf.max()), 4)
    return {"canon": canon, "sharpe": float(sharpe) if sharpe else None,
            "mdd_pct": mdd, "trades": trades,
            "gross_frac_mean": gross_mean, "gross_frac_max": gross_max,
            "regime_unknown_lines": unknown, "hmm_regime_lines": hmm_lines,
            "rc": r.returncode}


def main() -> int:
    md5_pre = _md5(ARTIFACT)
    cells = {}
    held = None
    try:
        for alloc in ("adaptive", "mean_variance"):
            if alloc == "mean_variance" and ARTIFACT.exists():
                held = ARTIFACT.with_suffix(".json.t165_held"); ARTIFACT.replace(held)
            for regime in ("live", "blind"):
                key = f"{alloc}/{regime}"
                m = _run_cell(blind=(regime == "blind"))
                cells[key] = m
                print(f"{key}: canon={str(m['canon'])[:8]} S={m['sharpe']} MDD={m['mdd_pct']} "
                      f"trades={m['trades']} gross(μ/max)={m['gross_frac_mean']}/{m['gross_frac_max']} "
                      f"regime_unknown_lines={m['regime_unknown_lines']} hmm_lines={m['hmm_regime_lines']}",
                      flush=True)
    finally:
        if held is not None and held.exists():
            held.replace(ARTIFACT)
    md5_post = _md5(ARTIFACT)

    res = {"window": YEAR, "cells": cells,
           "artifact_md5_pre": md5_pre, "artifact_md5_post": md5_post,
           "artifact_restored_ok": md5_pre == md5_post}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str))
    print("\n===== FOOTPRINT (live vs blind, per allocator) =====")
    for alloc in ("adaptive", "mean_variance"):
        lv, bl = cells.get(f"{alloc}/live", {}), cells.get(f"{alloc}/blind", {})
        same = lv.get("canon") == bl.get("canon")
        dS = (None if lv.get("sharpe") is None or bl.get("sharpe") is None
              else round(bl["sharpe"] - lv["sharpe"], 4))
        print(f"{alloc}: canon {'IDENTICAL' if same else 'DIFFERS'} | "
              f"ΔSharpe(blind-live)={dS} | live S={lv.get('sharpe')} trades={lv.get('trades')} "
              f"grossμ={lv.get('gross_frac_mean')} | blind S={bl.get('sharpe')} trades={bl.get('trades')} "
              f"grossμ={bl.get('gross_frac_mean')}")
    print(f"\nartifact restored OK: {res['artifact_restored_ok']} ({md5_pre} == {md5_post})")
    print(f"[T165] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
