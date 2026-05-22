"""scripts/run_per_ticker_capture_t053.py
==========================================
T-053: fresh per-ticker score capture on current 6 actives.

The original Phase 0 pairwise correlation diagnostic (commit e91f913)
ran on a 2024-era 10-edge panel. The current 6 actives include 4
V/Q/A fundamental edges NOT in that panel. Prior: those 4 cluster
ρ > 0.7 by construction (all SimFin-derived). T-053 measures it
directly on a fresh capture.

This script runs ONE backtest, 2024-01-01 → 2024-12-31, on the
substrate-honest universe, with `log_per_ticker_scores=True`. The
output parquet at `data/research/per_ticker_scores/<run_uuid>.parquet`
contains per-(timestamp, ticker, edge_id) raw_score for the current
6 actives.

Determinism: 1-rep is fine for logger output; this is NOT a Sharpe
measurement.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-m", "scripts.run_per_ticker_capture_t053",
             *sys.argv[1:]],
        )


def main() -> int:
    _reexec_if_hashseed_unset()
    from orchestration.mode_controller import ModeController
    mc = ModeController(ROOT, env="prod")
    summary = mc.run_backtest(
        mode="prod",
        fresh=False,
        no_governor=False,
        reset_governor=True,
        alpha_debug=False,
        override_start="2024-01-01",
        override_end="2024-12-31",
        use_historical_universe=True,
        apply_journal_at_end=True,
        discover=False,
        log_per_ticker_scores=True,
    )
    print("\n[T-053] Backtest complete")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
