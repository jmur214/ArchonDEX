#!/usr/bin/env python3
"""T-2026-06-11-155 — one-time pin of earnings dates into the substrate.

T-142 found `earnings_vol_edge` fetching LIVE Yahoo earnings dates into
trades on every run (in-memory cache only) — the last live-network input
to the measurement path. This script performs the SANCTIONED one-time
fetch over the full canonical universe and lands a vintage-stamped
parquet that both local and cloud runs read thereafter.

Refresh procedure (deliberate, manifest-regenerating — the anchor-update
pattern): re-run this script → review the diff in coverage/dates →
`python3 scripts/gen_substrate_manifest.py generate` → commit parquet +
manifest together with the reason for the refresh.

Output: data/earnings/earnings_dates_pinned.parquet
  columns: ticker (str), earnings_date (datetime64, tz-naive normalized),
           vintage (str, fetch date YYYY-MM-DD)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "earnings" / "earnings_dates_pinned.parquet"


def main() -> int:
    import yfinance as yf

    tickers = json.loads((REPO / "config" / "backtest_settings.json").read_text())["tickers"]
    vintage = date.today().isoformat()
    rows, misses = [], []
    for i, t in enumerate(tickers, 1):
        try:
            ed = yf.Ticker(t).earnings_dates
            if ed is None or ed.empty:
                misses.append(t)
                continue
            idx = ed.index
            if getattr(idx, "tz", None) is not None:
                idx = idx.tz_localize(None)
            for d in pd.DatetimeIndex(idx).normalize().unique():
                rows.append({"ticker": t, "earnings_date": d, "vintage": vintage})
        except Exception as e:
            print(f"  MISS {t}: {e}", file=sys.stderr)
            misses.append(t)
        if i % 20 == 0:
            print(f"  {i}/{len(tickers)} fetched…")
        time.sleep(0.4)  # be polite; avoid rate-limit gaps in the pin

    df = pd.DataFrame(rows).sort_values(["ticker", "earnings_date"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(df)} rows, {df['ticker'].nunique()}/{len(tickers)} tickers, vintage {vintage}")
    if misses:
        print(f"NO-DATA tickers ({len(misses)}): {misses}")
        print("(yfinance has no earnings calendar for these — typically ETFs/"
              "recent listings; the edge scores them 0 exactly as the live "
              "fetch's empty result did.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
