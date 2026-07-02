#!/usr/bin/env python3
"""T-2026-07-02-255: build the T-236 gauntlet inputs as COMMITTED, reproducible artifacts
(the flagship number's inputs were deleted from /tmp — a census-class irreproducibility).

- bond_synth: synthetic constant-maturity 10yr-Treasury TOTAL-RETURN index from FRED DGS10
  (committed at data/macro/DGS10.parquet). Formula (documented in the T-236 audit):
  daily TR = carry(y_{t-1}/252) − D·Δy,  D≈7 (10yr treasury modified duration proxy).
- gold: GC=F continuous gold futures (auto-adjusted ~spot proxy) via yfinance (network).

Writes to data/research/ (archived) so the fair re-run (scripts/fair_t236_rerun_t255.py) is
re-runnable by anyone from the repo. Deterministic from DGS10; gold needs a one-time network fetch.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research"
DUR = 7.0  # 10yr-treasury modified-duration proxy (documented in the T-236 audit)

def build_bond_synth() -> pd.Series:
    y = pd.read_parquet(ROOT / "data/macro/DGS10.parquet")["value"].astype(float) / 100.0
    y.index = pd.to_datetime(y.index); y = y.dropna().sort_index()
    dy = y.diff(); carry = y.shift(1) / 252.0
    tr = (carry - DUR * dy).dropna()
    idx = (1 + tr).cumprod().rename("bond_tr")
    idx.to_csv(OUT / "bond_synth_dgs10_t255.csv")
    print(f"[bond] DGS10 TR index {idx.index.min().date()}..{idx.index.max().date()} "
          f"({len(idx)}); CAGR {((idx.iloc[-1]/idx.iloc[0])**(252/len(idx))-1)*100:.2f}%")
    return idx

def build_gold() -> pd.Series:
    import yfinance as yf, warnings; warnings.filterwarnings("ignore")
    g = yf.download("GC=F", start="2000-01-01", end="2026-01-01", progress=False, auto_adjust=True)
    gc = g["Close"].squeeze(); gc.index = pd.to_datetime(gc.index).tz_localize(None)
    gc = gc.rename("gold_close"); gc.to_csv(OUT / "gold_gcf_t255.csv")
    print(f"[gold] GC=F {gc.index.min().date()}..{gc.index.max().date()} ({len(gc)})")
    return gc

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_bond_synth()
    build_gold()
    print("[done] inputs written to data/research/ (bond_synth_dgs10_t255.csv, gold_gcf_t255.csv)")
