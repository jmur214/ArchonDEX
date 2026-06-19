#!/usr/bin/env python3
"""T-2026-06-18-210 — build the market-cap snapshot join for the realistic-retail
cost model. Fetches CURRENT market cap (yfinance fast_info, free) for the universe
and writes data/universe/market_cap_tiers.json: {ticker: {marketCap, tier}}.

LIMITATION (flagged): this is a CURRENT-snapshot join, NOT point-in-time. For
live names it's a good first pass; DELISTED / removed names (the PIT survivorship
cohort) have no current cap → they fall back to the ADV bucket in the slippage
model (which never UNDER-prices vs the existing realistic model). True PIT cap
tiering needs a survivorship-free cap history (Norgate/FMP) — a later increment.
Run with network available (NOT hermetic).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/universe/market_cap_tiers.json"
# tier floors (USD) + labels — must match SlippageConfig.cap_tier_thresholds_usd
TIERS = [(200e9, "mega"), (10e9, "large"), (2e9, "mid"), (300e6, "small")]


def _tier(cap: float) -> str:
    for floor, label in TIERS:
        if cap >= floor:
            return label
    return "micro"


def main() -> int:
    import yfinance as yf
    cfg = json.loads((ROOT / "config/backtest_settings.json").read_text())
    tickers = list(dict.fromkeys(cfg.get("tickers", [])))
    extra = [t for t in sys.argv[1:] if t]
    tickers = list(dict.fromkeys(tickers + extra))
    print(f"[CAP] fetching current market cap for {len(tickers)} tickers...")

    out = {}
    if OUT.exists():
        try:
            out = json.loads(OUT.read_text())
        except Exception:
            out = {}
    ok = miss = 0
    for i, t in enumerate(tickers, 1):
        if t in out and out[t].get("marketCap"):
            ok += 1
            continue
        cap = None
        try:
            fi = yf.Ticker(t).fast_info
            cap = getattr(fi, "market_cap", None) or (fi.get("market_cap") if hasattr(fi, "get") else None)
        except Exception:
            cap = None
        if not cap:
            try:
                cap = yf.Ticker(t).info.get("marketCap")
            except Exception:
                cap = None
        if cap and float(cap) > 0:
            out[t] = {"marketCap": float(cap), "tier": _tier(float(cap))}
            ok += 1
        else:
            out[t] = {"marketCap": None, "tier": None}
            miss += 1
        if i % 20 == 0:
            print(f"[CAP] {i}/{len(tickers)} (ok={ok} miss={miss})", flush=True)
            OUT.write_text(json.dumps(out, indent=0))
        time.sleep(0.05)

    OUT.write_text(json.dumps(out, indent=0))
    from collections import Counter
    dist = Counter(v.get("tier") for v in out.values())
    print(f"[CAP] wrote {OUT} | resolved={ok} missing={miss}")
    print(f"[CAP] tier distribution: {dict(dist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
