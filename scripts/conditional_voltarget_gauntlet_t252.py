"""
scripts/conditional_voltarget_gauntlet_t252.py
==============================================
T-2026-06-26-252 — CONDITIONAL vol-targeting on the EQUITY sleeve (SPY) gauntlet.

Pre-registered (NO sweep — the brief's corrected methodology: Sortino/MaxDD are a
SCORECARD, not an optimization target). Compares, on full-cycle SPY (1993-2026,
incl. dotcom/GFC/COVID/2022), net of liquid-ETF turnover cost:

  ARM 0  baseline        SPY buy-and-hold
  ARM 1  continuous_lever  daily clip(0.15/rv, 0.5, 1.5) — the FAJ-2020-critiqued
                           lever-in-calm variant
  ARM 2  continuous_capped daily clip(0.15/rv, 0.5, 1.0) — de-gross always, no lever
  ARM 3  conditional       clip(0.15/rv, 0.5, 1.0) ONLY when realized vol > its own
                           expanding P80, else 1.0 — the brief's robust variant

Question (the brief): does CONDITIONAL vol-targeting cut the TAIL (MaxDD) without
killing return — and does CONTINUOUS (lever) INCREASE drawdown (FAJ 2020)?
Reports Sortino (+ block-bootstrap ci_low), MaxDD, Sharpe, skew, tail_ratio.

Deterministic (seeded bootstrap). Output: data/research/t252/gauntlet.json + table.
Usage: python -m scripts.conditional_voltarget_gauntlet_t252
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_b_risk.sleeve_vol_target import (  # noqa: E402
    SleeveVolTargetConfig, apply_sleeve_vol_target,
)
from engines.engine_d_discovery.sleeve_gauntlet import compute_sleeve_metrics  # noqa: E402

SPY = ROOT / "data" / "processed" / "SPY_1d.csv"
OUT = ROOT / "data" / "research" / "t252" / "gauntlet.json"
BOOT = 1000


def _arms():
    base = dict(enabled=True, target_vol=0.15, vol_window=20, floor=0.5,
                extreme_percentile=0.80, min_history=252, cost_bps=5.0)
    return {
        "continuous_lever":  SleeveVolTargetConfig(conditional=False, ceiling=1.5, **base),
        "continuous_capped": SleeveVolTargetConfig(conditional=False, ceiling=1.0, **base),
        "conditional":       SleeveVolTargetConfig(conditional=True,  ceiling=1.0, **base),
    }


def main() -> int:
    if not SPY.exists():
        print(f"[T252] FATAL: SPY data absent at {SPY}")
        return 2
    spy = pd.read_csv(SPY, index_col=0, parse_dates=True)["Close"].astype(float)
    bh = spy.pct_change().dropna()

    arms = _arms()
    streams = {"baseline": bh}
    scales = {}
    for name, cfg in arms.items():
        net, scale, _ = apply_sleeve_vol_target(bh, cfg)
        streams[name] = net
        scales[name] = scale

    # Align ALL arms to a common index (the conditional's valid range is the most
    # restrictive — expanding-P80 needs min_history) for an apples-to-apples read.
    common = None
    for s in streams.values():
        common = s.index if common is None else common.intersection(s.index)
    common = common.sort_values()
    bh_aligned = bh.reindex(common).dropna()

    report = {"task": "T-2026-06-26-252 conditional vol-target gauntlet (SPY)",
              "window": [str(common.min().date()), str(common.max().date())],
              "n_obs": int(len(common)), "n_trials_preregistered": len(arms),
              "config": {"target_vol": 0.15, "vol_window": 20, "floor": 0.5,
                         "extreme_percentile": 0.80, "cost_bps": 5.0},
              "arms": {}}
    for name, s in streams.items():
        r = s.reindex(common).dropna()
        m = compute_sleeve_metrics(r, benchmark_returns=bh_aligned, bootstrap_iterations=BOOT)
        ann_ret = float((1.0 + r).prod() ** (252.0 / max(len(r), 1)) - 1.0)
        avg_scale = float(scales[name].reindex(common).mean()) if name in scales else 1.0
        report["arms"][name] = {
            "sortino": round(m.sortino, 4),
            "sortino_ci_low": round(m.bootstrap_sortino["ci_low"], 4) if m.bootstrap_sortino else None,
            "max_drawdown_pct": round(m.max_drawdown * 100.0, 2),
            "sharpe": round(m.sharpe, 4),
            "skewness": round(m.skewness, 4),
            "tail_ratio": round(m.tail_ratio, 4),
            "cagr_pct": round(ann_ret * 100.0, 2),
            "avg_exposure": round(avg_scale, 4),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    # headline table
    cols = ["sortino", "sortino_ci_low", "max_drawdown_pct", "sharpe", "cagr_pct", "skewness", "tail_ratio", "avg_exposure"]
    print(f"\nT-252 conditional vol-target gauntlet — SPY {report['window'][0]}..{report['window'][1]} "
          f"({report['n_obs']} bars), net of {report['config']['cost_bps']}bps")
    print(f"{'arm':18s} " + " ".join(f"{c:>14s}" for c in cols))
    for name in ["baseline", "continuous_lever", "continuous_capped", "conditional"]:
        a = report["arms"][name]
        print(f"{name:18s} " + " ".join(f"{str(a[c]):>14s}" for c in cols))

    # verdict
    base, cond = report["arms"]["baseline"], report["arms"]["conditional"]
    clev = report["arms"]["continuous_lever"]
    cut_tail = cond["max_drawdown_pct"] > base["max_drawdown_pct"]  # MDD less negative = better (values are negative)
    kept_ret = cond["sortino"] >= base["sortino"] - 0.05
    faj = clev["max_drawdown_pct"] < base["max_drawdown_pct"]       # continuous-lever DEEPER MDD than baseline
    print(f"\n[T252] conditional cuts the tail (MaxDD better than buy-hold): {cut_tail} "
          f"({base['max_drawdown_pct']} -> {cond['max_drawdown_pct']})")
    print(f"[T252] conditional keeps return (Sortino >= baseline-0.05): {kept_ret} "
          f"({base['sortino']} -> {cond['sortino']})")
    print(f"[T252] continuous-LEVER increases drawdown vs buy-hold (FAJ 2020): {faj} "
          f"({base['max_drawdown_pct']} -> {clev['max_drawdown_pct']})")
    print(f"[T252] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
