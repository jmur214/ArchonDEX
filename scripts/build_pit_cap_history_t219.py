#!/usr/bin/env python3
"""T-2026-06-18-219 — close the T-210/T-215 cap-join under-count: give the DELISTED
PIT cohort a real cap (cap-AT-DELISTING) instead of the current-snapshot's null →
ADV-15bps fallback. yfinance get_shares_full carries shares history up to a name's
delisting/acquisition (back to ~2015), so cap_at_delist = late-period median(close ×
shares). Names delisted BEFORE ~2015 (no shares data) are the FREE-DATA WALL — left
null (honest), still ADV fallback. Merges into data/universe/market_cap_tiers.json:
{ticker: {marketCap, tier, asof}} so the existing slippage cap-cache tiers them
correctly with NO model change. Additive; run with network (NOT hermetic).
"""
from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/universe/market_cap_tiers.json"
TIERS = [(200e9, "mega"), (10e9, "large"), (2e9, "mid"), (300e6, "small")]


def _tier(cap: float) -> str:
    for floor, label in TIERS:
        if cap >= floor:
            return label
    return "micro"


def _delisted_cohort():
    m = pd.read_parquet(ROOT / "data/universe/sp500_membership.parquet")
    left = m[m["included_until"].notna()].copy()
    left["iu"] = pd.to_datetime(left["included_until"])
    return dict(zip(left["ticker"], left["iu"]))


def main() -> int:
    import yfinance as yf
    cache = json.loads(OUT.read_text()) if OUT.exists() else {}
    cohort = _delisted_cohort()
    have_price = {os.path.basename(p).replace("_1d.csv", "")
                  for p in glob.glob(str(ROOT / "data/processed/*_1d.csv"))}
    # only the delisted names that (a) have price data and (b) aren't already resolved
    todo = [t for t, iu in cohort.items()
            if t in have_price and not (cache.get(t, {}) or {}).get("marketCap")]
    print(f"[PITCAP] delisted cohort with price + unresolved cap: {len(todo)}")

    ok = wall = 0
    for i, t in enumerate(sorted(todo), 1):
        iu = cohort[t]
        cap = None
        try:
            sh = yf.Ticker(t).get_shares_full(start="2010-01-01")
        except Exception:
            sh = None
        if sh is not None and len(sh):
            try:
                px = pd.read_csv(ROOT / f"data/processed/{t}_1d.csv", parse_dates=["Date"]).set_index("Date")
                # align shares to price dates near delisting (last 12mo of overlap)
                sh = sh[~sh.index.duplicated(keep="last")].sort_index()
                sh.index = pd.to_datetime(sh.index).tz_localize(None)
                end = min(px.index.max(), sh.index.max())
                win = px[(px.index >= end - pd.DateOffset(months=12)) & (px.index <= end)]
                if len(win):
                    shares_ff = sh.reindex(win.index, method="ffill")
                    cap_series = (win["Close"] * shares_ff).dropna()
                    if len(cap_series):
                        cap = float(cap_series.median())
            except Exception:
                cap = None
        if cap and cap > 0:
            cache[t] = {"marketCap": cap, "tier": _tier(cap),
                        "asof": str(end.date()), "source": "delist_shares"}
            ok += 1
        else:
            wall += 1  # pre-2015 / no shares: the free-data wall (left null)
        if i % 25 == 0:
            print(f"[PITCAP] {i}/{len(todo)} (ok={ok} wall={wall})", flush=True)
            OUT.write_text(json.dumps(cache, indent=0))
        time.sleep(0.05)

    OUT.write_text(json.dumps(cache, indent=0))
    from collections import Counter
    delist = {t: cache[t] for t in cohort if t in cache and cache[t].get("source") == "delist_shares"}
    dist = Counter(v["tier"] for v in delist.values())
    print(f"[PITCAP] delisted cohort resolved={ok} free-data-wall={wall}")
    print(f"[PITCAP] delisted-cohort cap-at-delist tier distribution: {dict(dist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
