#!/usr/bin/env python3
"""T-2026-06-13-167 GAP 3 — regenerate data/processed/SPY_1d.csv with FULL history.

WHY
---
`data/processed/SPY_1d.csv` was truncated to 1513 rows (2020-04-09 -> 2026-04-17,
~6 yr) while every stock (KO/JPM/XOM) carries the full 1970-> Stooq+Alpaca merged
depth. SPY is the benchmark AND the source the regime detector's price axes
(trend/vol) read (engines/engine_e_regime/detectors/{trend,volatility}_detector.py).
On the cloud the substrate runs the long windows (16yr/26yr -> back to 2010/2000);
for every bar BEFORE 2020-04-09 `slice_map.get('SPY')` was empty -> trend & vol
regime axes returned "unknown" across the whole pre-2020 span (corr/breadth read the
full data_map and stayed live). That is C's T-165 "cloud price-axis regime dead".
Restoring SPY depth makes the price-axis regime LIVE across the full window. The
backtest CALENDAR is the UNION of all tickers (backtest_controller.py:202-203), so
the truncation NEVER shortened the window — it only degraded the benchmark+regime.

BASIS (proven, not assumed)
---------------------------
The existing 2020+ rows are EXACTLY yfinance total-return (Adj Close) basis:
    alpaca_close / yf_adjclose over the full 1513-day overlap = 1.000000 (std 0.0).
So extending with the SAME yfinance total-return basis is a zero-convention-change,
zero-seam-discontinuity splice. SPY has no splits 1993-2026, so the dividend
back-adjustment (Adj Close) is the only adjustment in play and it matches the file.

METHOD
------
* Deep portion (1993-01-29 -> 2020-04-08): yfinance SPY, auto_adjust=False; build
  total-return OHLC = O/H/L * (AdjClose/Close), Close = AdjClose, Volume raw.
  ATR (14d rolling-mean True Range, the project convention) + PrevClose computed.
* Recent portion (2020-04-09 -> 2026-04-17): the ORIGINAL file's lines kept
  BYTE-IDENTICAL (appended verbatim) so the recent canon every prior anchor used is
  unchanged. The single derived imperfection (recent row-0 PrevClose stays blank
  rather than pointing at the deep 2020-04-08 close) is preserved deliberately to
  guarantee byte-identity; PrevClose of the benchmark does not enter the prod canon.
* Parquet sibling (data/processed/parquet/SPY_1d.parquet) regenerated to match
  (load_cached reads parquet first); recent OHLCV read back from the ORIGINAL
  parquet so its float64 bits are identical.

VINTAGE
-------
Pass --asof YYYY-MM-DD to stamp the pull date (no wall-clock in the file). The
script prints row count + a content hash for the audit + manifest re-pin.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/processed/SPY_1d.csv"
PQ = ROOT / "data/processed/parquet/SPY_1d.parquet"
SEAM = pd.Timestamp("2020-04-09")  # first row of the existing (recent) file


def fetch_deep_tr() -> pd.DataFrame:
    """yfinance SPY on total-return basis (matches the existing file)."""
    import yfinance as yf

    raw = yf.download(
        "SPY", start="1993-01-01", end="2026-04-18", interval="1d",
        progress=False, auto_adjust=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.index = pd.to_datetime(raw.index)
    fac = raw["Adj Close"] / raw["Close"]
    tr = pd.DataFrame({
        "Open": raw["Open"] * fac,
        "High": raw["High"] * fac,
        "Low": raw["Low"] * fac,
        "Close": raw["Adj Close"],
        "Volume": raw["Volume"].astype(float),
    })
    return tr[tr.index < SEAM]


def compute_atr_prevclose(df: pd.DataFrame) -> pd.DataFrame:
    """Project convention: ATR = 14d rolling MEAN of True Range (min 14)."""
    out = df.copy()
    tr = pd.concat([
        (out["High"] - out["Low"]).abs(),
        (out["High"] - out["Close"].shift()).abs(),
        (out["Low"] - out["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    out["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    out["PrevClose"] = out["Close"].shift(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asof", required=True, help="vintage stamp YYYY-MM-DD (the pull date)")
    ap.add_argument("--dry-run", action="store_true", help="build + verify, do not write")
    args = ap.parse_args()

    if not CSV.exists():
        print(f"FAIL: {CSV} missing", file=sys.stderr)
        return 2

    orig_lines = CSV.read_text().splitlines()
    header = orig_lines[0]
    assert header == "Date,Open,High,Low,Close,Volume,ATR,PrevClose", header
    recent_lines = orig_lines[1:]  # verbatim recent rows (2020-04-09 ->)
    first_recent_date = recent_lines[0].split(",", 1)[0]
    assert first_recent_date == "2020-04-09", first_recent_date

    deep = compute_atr_prevclose(fetch_deep_tr())
    cols = ["Open", "High", "Low", "Close", "Volume", "ATR", "PrevClose"]
    deep = deep[cols]

    # --- CSV: deep rows (pandas-formatted) + recent lines verbatim ---
    deep_csv = deep.copy()
    deep_csv.index.name = "Date"
    deep_csv_body = deep_csv.reset_index()
    deep_csv_body["Date"] = deep_csv_body["Date"].dt.strftime("%Y-%m-%d")
    deep_text = deep_csv_body.to_csv(index=False, header=False).rstrip("\n")
    full_text = header + "\n" + deep_text + "\n" + "\n".join(recent_lines) + "\n"

    # --- Parquet: deep frame + ORIGINAL parquet recent rows (bit-identical) ---
    orig_pq = pd.read_parquet(PQ)  # Date index
    orig_pq.index = pd.to_datetime(orig_pq.index)
    recent_pq = orig_pq[orig_pq.index >= SEAM]
    deep_pq = deep.copy()
    deep_pq.index.name = recent_pq.index.name
    full_pq = pd.concat([deep_pq[recent_pq.columns.tolist()], recent_pq])

    # --- verify recent OHLCV byte-identity (CSV) ---
    new_lines = full_text.splitlines()
    seam_pos = new_lines.index(recent_lines[0])
    assert new_lines[seam_pos:] == recent_lines, "recent CSV rows NOT byte-identical!"
    # --- verify parquet recent OHLCV bit-identity ---
    rb = full_pq[full_pq.index >= SEAM][["Open", "High", "Low", "Close", "Volume"]]
    ob = recent_pq[["Open", "High", "Low", "Close", "Volume"]]
    assert rb.equals(ob), "recent parquet OHLCV NOT bit-identical!"

    h = hashlib.sha256(full_text.encode()).hexdigest()
    n_total = len(new_lines) - 1
    n_deep = len(deep)
    print(f"[regen] asof={args.asof} rows={n_total} (deep={n_deep} + recent={len(recent_lines)})")
    print(f"[regen] range {deep.index[0].date()} -> {recent_lines[-1].split(',',1)[0]}")
    print(f"[regen] recent OHLCV byte-identical: CSV ✓  parquet ✓")
    print(f"[regen] csv-sha256 {h}")

    if args.dry_run:
        print("[regen] dry-run: nothing written")
        return 0

    CSV.write_text(full_text)
    full_pq.to_parquet(PQ)
    print(f"[regen] wrote {CSV} ({CSV.stat().st_size} bytes)")
    print(f"[regen] wrote {PQ} ({PQ.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
