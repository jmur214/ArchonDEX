#!/usr/bin/env python3
"""T-2026-06-13-167 GAP 4 — prove the PRICE-axis regime is LIVE across the FULL
window once SPY depth is restored (GAP 3) + the median*3 clip is fixed.

Mechanism (C's T-165): the trend & volatility axes read ONLY the benchmark (SPY)
DataFrame; corr & breadth read the full data_map. On the cloud SPY was truncated
to 2020+ (and the median*3 clip re-truncated even a restored SPY at 2020-06), so
for every bar before SPY's first row trend/vol returned "unknown". This drives the
real RegimeDetector over sampled dates 2002->2025 on local-CSV data (no network):

  POSITIVE arm (restored substrate): trend & vol non-"unknown" across the full span.
  NEGATIVE arm (SPY truncated to 2020+, the OLD cloud condition): trend & vol
  "unknown" at every pre-2020 date — isolating SPY depth as the sole cause.

No backtest, no network; deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.data_manager.data_manager import DataManager
from engines.engine_e_regime.regime_detector import RegimeDetector

SAMPLE_DATES = [
    "2002-07-01", "2004-01-02", "2006-06-01", "2008-10-01", "2010-03-01",
    "2012-06-01", "2014-09-02", "2016-11-01", "2018-03-01", "2020-03-16",
    "2021-06-01", "2023-01-03", "2025-02-03",
]
# A representative slice of the universe (benchmark + breadth/corr names)
TICKERS = ["SPY", "KO", "JPM", "XOM", "AAPL", "IBM", "GE", "MCD", "PG", "JNJ",
           "CVX", "HD", "DIS", "BA", "CAT", "MMM", "WMT", "T", "INTC", "MSFT"]


def build_data_map(truncate_spy_to=None):
    dm = DataManager()
    out = {}
    for t in TICKERS:
        df = dm.load_cached(t, "1d")
        if df is None or df.empty:
            continue
        if t == "SPY" and truncate_spy_to is not None:
            df = df[df.index >= pd.Timestamp(truncate_spy_to)]
        out[t] = df
    return out


def run_arm(label, truncate_spy_to=None):
    data_map = build_data_map(truncate_spy_to)
    det = RegimeDetector()
    spy_min = data_map["SPY"].index.min().date()
    print(f"\n=== {label}  (SPY starts {spy_min}) ===")
    print(f"{'date':<12}{'trend':<12}{'volatility':<12}{'correlation':<12}{'breadth':<12}")
    n_trend_live = n_vol_live = n_pre2020 = n_pre2020_live = 0
    for d in SAMPLE_DATES:
        ts = pd.Timestamp(d)
        slice_map = {t: df[df.index <= ts] for t, df in data_map.items()}
        bm = slice_map.get("SPY")
        if bm is None or bm.empty:
            states = {"trend": "NO-SPY", "volatility": "NO-SPY",
                      "correlation": "?", "breadth": "?"}
        else:
            r = det.detect_regime(bm, data_map=slice_map, now=str(ts))
            states = {
                "trend": r.get("trend"),
                "volatility": r.get("volatility"),
                "correlation": (r.get("correlation_regime") or {}).get("state"),
                "breadth": (r.get("breadth_regime") or {}).get("state"),
            }
        tr, vo = states.get("trend"), states.get("volatility")
        print(f"{d:<12}{str(tr):<12}{str(vo):<12}"
              f"{str(states.get('correlation')):<12}{str(states.get('breadth')):<12}")
        if tr not in (None, "unknown", "NO-SPY"):
            n_trend_live += 1
        if vo not in (None, "unknown", "NO-SPY"):
            n_vol_live += 1
        if ts < pd.Timestamp("2020-01-01"):
            n_pre2020 += 1
            if tr not in (None, "unknown", "NO-SPY") and vo not in (None, "unknown", "NO-SPY"):
                n_pre2020_live += 1
    print(f"  trend live {n_trend_live}/{len(SAMPLE_DATES)} | vol live "
          f"{n_vol_live}/{len(SAMPLE_DATES)} | PRE-2020 both-live "
          f"{n_pre2020_live}/{n_pre2020}")
    return n_pre2020_live, n_pre2020


def main() -> int:
    pos_live, pos_n = run_arm("POSITIVE — restored full SPY + normalize fix")
    neg_live, neg_n = run_arm("NEGATIVE — SPY truncated to 2020+ (OLD cloud condition)",
                              truncate_spy_to="2020-04-09")
    print("\n--- VERDICT ---")
    ok = (pos_live == pos_n and pos_n > 0) and (neg_live == 0)
    print(f"POSITIVE pre-2020 both-live: {pos_live}/{pos_n} (want all)")
    print(f"NEGATIVE pre-2020 both-live: {neg_live}/{neg_n} (want 0 — proves SPY depth is the cause)")
    print("RESULT:", "PASS — regime price axes LIVE across full window iff SPY depth restored"
          if ok else "INCONCLUSIVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
