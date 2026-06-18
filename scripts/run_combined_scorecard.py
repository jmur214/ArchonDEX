"""
scripts/run_combined_scorecard.py
=================================
T-176 thin entrypoint for the combined-candidate scorecard (presentation
+ I/O only; all logic lives in core/combined_candidate_scorecard.py).

Callable on EITHER source the deploy-bar needs:
  (a) a backtest equity curve  — portfolio_snapshots.csv (timestamp,equity)
  (b) a paper return series     — any CSV with a date col + equity|return col

Examples
--------
  # backtest snapshot (local or S3-downloaded)
  python -m scripts.run_combined_scorecard --snapshots /tmp/base_equity.csv

  # paper series (date,equity) once the paper machine has a track record
  python -m scripts.run_combined_scorecard --series data/paper/equity.csv \
      --date-col date --value-col equity

  # JSON out for E's paper scorecard to consume
  python -m scripts.run_combined_scorecard --snapshots /tmp/base_equity.csv --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.combined_candidate_scorecard import (  # noqa: E402
    build_scorecard, format_scorecard, rows_to_dicts,
)


def _base_from_snapshots(path: Path) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df.groupby(df["timestamp"].dt.date)["equity"].last()


def _base_from_series(path: Path, date_col: str, value_col: str) -> pd.Series:
    df = pd.read_csv(path)
    s = pd.Series(df[value_col].values, index=pd.to_datetime(df[date_col]))
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="Combined-candidate scorecard (base / base+20%DBMF / robo)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--snapshots", type=Path, help="portfolio_snapshots.csv (backtest)")
    src.add_argument("--series", type=Path, help="generic date,value CSV (paper or backtest)")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--value-col", default="equity")
    ap.add_argument("--w-dbmf", type=float, default=0.20)
    ap.add_argument("--rf", type=float, default=0.04, help="annual risk-free rate (cash-drag + Sharpe)")
    ap.add_argument("--rebalance", default="monthly", choices=["daily", "monthly", "quarterly"])
    ap.add_argument("--account", default="roth", choices=["roth", "taxable"],
                    help="roth = no tax (after-tax==pre-tax); taxable = T-191 after-tax layer")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.snapshots:
        base = _base_from_snapshots(a.snapshots)
    else:
        base = _base_from_series(a.series, a.date_col, a.value_col)

    rows = build_scorecard(base, w_dbmf=a.w_dbmf, rf_annual=a.rf, rebalance=a.rebalance,
                           account=a.account)
    if a.json:
        print(json.dumps(rows_to_dicts(rows), indent=2))
    else:
        print(format_scorecard(rows, rf_annual=a.rf, account=a.account))
    return 0


if __name__ == "__main__":
    sys.exit(main())
