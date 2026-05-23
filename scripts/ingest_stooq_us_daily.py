"""scripts/ingest_stooq_us_daily.py
=====================================
T-2026-05-23-081: ingest Stooq US daily bundle → project's processed schema.

Purpose
-------
Extend historical daily-bar coverage for SPX members beyond what Alpaca
retains. Stooq bundles go back to 1962 for some tickers (IBM, GE) and
1970+ for most blue chips — vs Alpaca's effective ~2010 floor.

Per the 2026-05-16 dev review, the multi-decade backtest extension is
the **precondition** for any deployment decision. This script delivers
the surviving-universe half of that extension. (Delisted-ticker coverage
remains a separate concern; Stooq scrubs delisted history the same way
Yahoo does — 0/124 hit rate on our missing SPX delisted members.)

Inputs
------
- `data/raw/stooq/daily/us/{nasdaq,nyse,nysemkt}{ stocks,etfs}/<bucket>/<ticker>.us.txt`
  Format: `<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>`
  DATE is YYYYMMDD; PER is "D" for daily; OPENINT is unused for stocks.

- `data/universe/sp500_membership.parquet`
  The scope filter: only ingest tickers that were S&P 500 members at any
  point during the configured window (default: 2010-2026 ∪ all-time).

Outputs (to a SEPARATE dir to avoid clobbering existing Alpaca data)
-------------------------------------------------------------------
- `data/processed/stooq_us_daily/<TICKER>_1d.csv`
- `data/processed/stooq_us_daily/parquet/<TICKER>_1d.parquet`
- `data/processed/stooq_us_daily/_ingest_meta.json` (provenance manifest)

Schema (matches existing `data/processed/<TICKER>_1d.csv` convention)
--------------------------------------------------------------------
- Columns: `Date,Open,High,Low,Close,Volume,ATR,PrevClose`
- ATR: 14-day rolling mean of True Range (project convention from
  engines/data_manager/data_manager.py:495-503).
- PrevClose: `Close.shift(1)`.

A follow-up task (T-082, separately briefed) will handle the MERGE into
the canonical `data/processed/` namespace — joining Stooq's deep history
with Alpaca's recent bars per-ticker. This script's output is the
upstream input for that merge.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

STOOQ_ROOT = REPO / "data/raw/stooq/daily/us"
OUT_ROOT = REPO / "data/processed/stooq_us_daily"
SPX_MEMBERSHIP = REPO / "data/universe/sp500_membership.parquet"


# =============================================================================
# Ticker normalization
# =============================================================================

def normalize_ticker_for_stooq(ticker: str) -> str:
    """Convert project-shape ticker to Stooq-shape filename stem.

    Examples:
      "AAPL"   -> "aapl"
      "BRK.B"  -> "brk-b"   (Stooq uses hyphen for class separator)
      "BF.B"   -> "bf-b"
    """
    return ticker.lower().replace(".", "-")


# =============================================================================
# Index Stooq archive (one-shot scan)
# =============================================================================

def build_stooq_index(stooq_root: Path) -> Dict[str, Path]:
    """Walk the Stooq tree and build {ticker_lower: path} index.

    Stooq tickers are stored as `<symbol>.us.txt` across multiple
    exchange/type/bucket subdirs.
    """
    index: Dict[str, Path] = {}
    for path in stooq_root.rglob("*.us.txt"):
        stem = path.name.replace(".us.txt", "")
        # First-write-wins (extremely rare for two paths to hold same ticker)
        index.setdefault(stem, path)
    return index


# =============================================================================
# Parse one Stooq file into our schema
# =============================================================================

def parse_stooq_file(path: Path) -> Optional[pd.DataFrame]:
    """Parse a Stooq .us.txt file → DataFrame in project schema.

    Returns None if the file is empty / malformed / has no usable bars.
    """
    try:
        df = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return None

    if df.empty:
        return None

    # Strip <> from header names: <TICKER> -> TICKER
    df.columns = [c.strip("<>").upper() for c in df.columns]

    required = {"DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOL"}
    if not required.issubset(df.columns):
        return None

    # Convert DATE (YYYYMMDD int or str) to datetime
    df["Date"] = pd.to_datetime(df["DATE"].astype(str), format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    if df.empty:
        return None

    out = pd.DataFrame({
        "Date":   df["Date"].values,
        "Open":   pd.to_numeric(df["OPEN"],   errors="coerce"),
        "High":   pd.to_numeric(df["HIGH"],   errors="coerce"),
        "Low":    pd.to_numeric(df["LOW"],    errors="coerce"),
        "Close":  pd.to_numeric(df["CLOSE"],  errors="coerce"),
        "Volume": pd.to_numeric(df["VOL"],    errors="coerce"),
    })
    out = out.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    if out.empty:
        return None

    out = out.sort_values("Date").reset_index(drop=True)

    # ATR (project convention: 14-day rolling MEAN of True Range, min 14 bars)
    tr_components = pd.concat([
        (out["High"] - out["Low"]).abs(),
        (out["High"] - out["Close"].shift()).abs(),
        (out["Low"]  - out["Close"].shift()).abs(),
    ], axis=1)
    tr = tr_components.max(axis=1)
    out["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    out["PrevClose"] = out["Close"].shift(1)

    # Hygiene: drop any all-zero / non-positive-close rows (artifacts)
    out = out[(out["Close"] > 0) & (out["Volume"] >= 0)].copy()
    if out.empty:
        return None

    return out


# =============================================================================
# Write to project format
# =============================================================================

def write_processed(df: pd.DataFrame, ticker: str, out_root: Path) -> Tuple[Path, Path]:
    csv_path = out_root / f"{ticker}_1d.csv"
    pq_path = out_root / "parquet" / f"{ticker}_1d.parquet"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    pq_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(csv_path, index=False, date_format="%Y-%m-%d")
    df.set_index("Date").to_parquet(pq_path)
    return csv_path, pq_path


# =============================================================================
# Scope: SPX historical members
# =============================================================================

def get_target_tickers(
    membership_path: Path,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> List[str]:
    df = pd.read_parquet(membership_path)
    df["from"]  = pd.to_datetime(df["included_from"])
    df["until"] = pd.to_datetime(df["included_until"])
    in_window = (
        (df["until"].isna() | (df["until"] >= window_start)) &
        (df["from"].isna()  | (df["from"]  <= window_end))
    )
    return sorted(df.loc[in_window, "ticker"].unique().tolist())


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-start", default="2010-01-01",
                   help="Earliest membership date to include (default 2010-01-01)")
    p.add_argument("--window-end", default="2026-12-31",
                   help="Latest membership date to include (default 2026-12-31)")
    p.add_argument("--limit", type=int, default=None,
                   help="Only ingest first N tickers (smoke-test path)")
    p.add_argument("--all-stooq", action="store_true",
                   help="Ignore SPX scope; ingest every ticker Stooq has (~12k)")
    p.add_argument("--out", default=str(OUT_ROOT),
                   help=f"Output dir (default {OUT_ROOT.relative_to(REPO)})")
    args = p.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[ingest] Building Stooq index from {STOOQ_ROOT}...")
    stooq_idx = build_stooq_index(STOOQ_ROOT)
    print(f"[ingest]   {len(stooq_idx):,} Stooq US tickers indexed")

    if args.all_stooq:
        targets = sorted(stooq_idx.keys())
    else:
        ws = pd.Timestamp(args.window_start)
        we = pd.Timestamp(args.window_end)
        targets = get_target_tickers(SPX_MEMBERSHIP, ws, we)
        print(f"[ingest]   {len(targets)} SPX historical members in [{ws.date()}..{we.date()}]")

    if args.limit:
        targets = targets[:args.limit]
        print(f"[ingest]   limited to first {len(targets)} for smoke test")

    manifest = {
        "task_id": "T-2026-05-23-081",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stooq_index_size": len(stooq_idx),
        "n_targets": len(targets),
        "window": {"start": args.window_start, "end": args.window_end},
        "scope": "all_stooq" if args.all_stooq else "spx_historical_members",
        "per_ticker": {},
    }

    n_hit = 0
    n_miss = 0
    n_parsed_empty = 0
    for tkr in targets:
        stem = normalize_ticker_for_stooq(tkr)
        path = stooq_idx.get(stem)
        if path is None:
            n_miss += 1
            manifest["per_ticker"][tkr] = {"status": "miss"}
            continue
        df = parse_stooq_file(path)
        if df is None or df.empty:
            n_parsed_empty += 1
            manifest["per_ticker"][tkr] = {"status": "parsed_empty", "source": str(path.relative_to(REPO))}
            continue
        csv_path, pq_path = write_processed(df, tkr, out_root)
        n_hit += 1
        manifest["per_ticker"][tkr] = {
            "status": "ok",
            "source": str(path.relative_to(REPO)),
            "n_bars": int(len(df)),
            "first_date": df["Date"].iloc[0].strftime("%Y-%m-%d"),
            "last_date":  df["Date"].iloc[-1].strftime("%Y-%m-%d"),
        }

    manifest["summary"] = {
        "n_hit": n_hit,
        "n_miss": n_miss,
        "n_parsed_empty": n_parsed_empty,
        "hit_rate_pct": round(100 * n_hit / max(1, len(targets)), 1),
    }

    meta_path = out_root / "_ingest_meta.json"
    with open(meta_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    def _display(p: Path) -> str:
        try:
            return str(p.relative_to(REPO))
        except ValueError:
            return str(p)

    print()
    print(f"[ingest] Done. {n_hit} ok / {n_miss} miss / {n_parsed_empty} parsed-empty")
    print(f"[ingest] Hit rate: {manifest['summary']['hit_rate_pct']}%")
    print(f"[ingest] Manifest: {_display(meta_path)}")
    print(f"[ingest] Files at: {_display(out_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
