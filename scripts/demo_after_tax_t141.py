#!/usr/bin/env python
# scripts/demo_after_tax_t141.py
"""T-141 demonstration — pre-tax vs after-tax (taxable-IL) on a real book.

Reads a backtest's trades.csv + portfolio_snapshots.csv (default: the
flat data/trade_logs/ pair — the canonical 2024 6-edge book), runs the
report-only after-tax pipeline, and prints pre-tax vs after-tax Sharpe
WITH block-bootstrap 95% CIs (house standard: 500 iter, seed 0) plus the
tax accounting detail.

REPORT-ONLY: no backtest is run, no trades change, no N_trials are
consumed. Rates come from config/backtest_settings.json
`tax_drag_model` (federal + IL state). Caveats printed below the table —
notably the conservative wash-sale disallowance (overstates drag) and
the single-year measurement shape (the whole annual tax bill lands as
one year-end return observation; CAGR drag is the robust number, the
Sharpe delta is shape-sensitive on 1-year windows).

Run:  python -m scripts.demo_after_tax_t141 [run_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from backtester.after_tax_metrics import compute_after_tax_report
from backtester.tax_drag_model import TaxDragConfig, TaxDragModel
from core.metrics_engine import MetricsEngine

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "trade_logs"
    trades = pd.read_csv(run_dir / "trades.csv")
    snaps = pd.read_csv(run_dir / "portfolio_snapshots.csv")
    snaps["timestamp"] = pd.to_datetime(snaps["timestamp"])
    equity = pd.Series(
        pd.to_numeric(snaps["equity"], errors="coerce").values,
        index=snaps["timestamp"],
    ).dropna()

    tax_cfg = json.load(open(ROOT / "config" / "backtest_settings.json"))["tax_drag_model"]
    report = compute_after_tax_report(trades, equity, tax_cfg)

    # After-tax equity curve for the bootstrap (same local-enabled copy
    # the report uses).
    cfg = TaxDragConfig(
        enabled=True,
        short_term_rate=float(tax_cfg.get("short_term_rate", 0.30)),
        long_term_rate=float(tax_cfg.get("long_term_rate", 0.15)),
        state_st_rate=float(tax_cfg.get("state_st_rate", 0.0)),
        state_lt_rate=float(tax_cfg.get("state_lt_rate", 0.0)),
        long_term_min_days=int(tax_cfg.get("long_term_min_days", 365)),
        wash_sale_window_days=int(tax_cfg.get("wash_sale_window_days", 30)),
    )
    after_equity = TaxDragModel(cfg).compute(trades, equity)["after_tax_equity"]

    def boot(eq: pd.Series) -> dict:
        rets = eq.pct_change().dropna()
        if len(rets) < 32:
            return {}
        return MetricsEngine.bootstrap_distribution(
            rets, MetricsEngine.sharpe_ratio, n_iterations=500, seed=0
        )

    pre_b, post_b = boot(equity), boot(after_equity)

    def ci(b: dict) -> str:
        lo, hi = b.get("ci_low"), b.get("ci_high")
        if lo is None:
            return "[n/a]"
        return f"[{lo:+.3f}, {hi:+.3f}]"

    print(f"T-141 after-tax demonstration — {run_dir}")
    print(f"  window: {equity.index[0].date()} → {equity.index[-1].date()}, "
          f"{report['n_realized_lots']} realized lots, "
          f"{report['pct_lots_short_term']:.0f}% short-term")
    print(f"  effective rates: ST {report['effective_st_rate']:.2%} / "
          f"LT {report['effective_lt_rate']:.2%} (federal + IL 4.95%)\n")
    print(f"  {'':24} {'Sharpe':>8}  {'95% block-bootstrap CI':>24}  {'CAGR %':>8}")
    print(f"  {'pre-tax (= Roth)':24} {report['sharpe_roth']:>8.3f}  {ci(pre_b):>24}  "
          f"{report['cagr_roth_pct']:>8.2f}")
    print(f"  {'after-tax (taxable-IL)':24} {report['after_tax_sharpe_taxable']:>8.3f}  "
          f"{ci(post_b):>24}  {report['after_tax_cagr_taxable_pct']:>8.2f}")
    print(f"\n  tax_drag_pct (share of pre-tax CAGR consumed): {report['tax_drag_pct']:.1f}%")
    print(f"  total tax: ${report['total_tax_usd']:,.2f} on "
          f"${report['st_taxable_gain_usd']:,.2f} ST taxable gains "
          f"(wash-sale disallowed losses: ${report['wash_sale_disallowed_loss_usd']:,.2f})")
    print("\n  caveats: conservative wash-sale disallowance (overstates drag); "
          "single-year window puts the whole tax bill in one year-end return "
          "(CAGR drag robust, Sharpe delta shape-sensitive); rates are "
          "planning estimates, not tax advice.")
    print("  report-only — no backtest run, no N_trials consumed.")


if __name__ == "__main__":
    main()
