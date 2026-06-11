#!/usr/bin/env python
# scripts/demo_safef_car25_t151.py
"""T-151 demonstration — safe-f / CAR25 on a real book, per account.

Computes Bandy's sizing-health metrics for a run's PRE-TAX record
(= the Roth account: no drag) and for the TAXABLE-IL record (T-141's
tax model applied to the same artifacts), answering: is the current
implicit sizing over or under the Bandy-safe fraction, and does the
answer differ by account?

REPORTING ONLY — nothing sizes off these numbers; zero N_trials.

LOUD CAVEAT (printed below): safe_f is a function of the RECORD it is
fed. A single benign year (2024: no 20%+ episodes) yields a generous
safe_f; the 26-yr record (MDD −59%) would bind FAR lower. The number
that should ever gate sizing is the deep-window one — re-run this
script on a multi-decade run dir when one is on disk.

Run:  python -m scripts.demo_safef_car25_t151 [run_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from backtester.safef_car25 import SafeFConfig, compute_safef_car25
from backtester.tax_drag_model import TaxDragConfig, TaxDragModel

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "trade_logs"
    trades = pd.read_csv(run_dir / "trades.csv", engine="python", on_bad_lines="skip")
    snaps = pd.read_csv(run_dir / "portfolio_snapshots.csv")
    snaps["timestamp"] = pd.to_datetime(snaps["timestamp"])
    equity = pd.Series(
        pd.to_numeric(snaps["equity"], errors="coerce").values,
        index=snaps["timestamp"],
    ).dropna()

    bt_cfg = json.load(open(ROOT / "config" / "backtest_settings.json"))
    sf_block = bt_cfg.get("safef_car25") or {}
    sf_cfg = SafeFConfig(**{k: v for k, v in sf_block.items()
                            if k in SafeFConfig.__annotations__})
    tax_cfg_d = bt_cfg["tax_drag_model"]

    # Roth = the pre-tax record (no drag).
    pre = compute_safef_car25(equity.pct_change().dropna(), sf_cfg)

    # Taxable-IL = the T-141 tax model applied to the same artifacts.
    tax_model = TaxDragModel(TaxDragConfig(
        enabled=True,
        short_term_rate=float(tax_cfg_d.get("short_term_rate", 0.30)),
        long_term_rate=float(tax_cfg_d.get("long_term_rate", 0.15)),
        state_st_rate=float(tax_cfg_d.get("state_st_rate", 0.0)),
        state_lt_rate=float(tax_cfg_d.get("state_lt_rate", 0.0)),
        long_term_min_days=int(tax_cfg_d.get("long_term_min_days", 365)),
        wash_sale_window_days=int(tax_cfg_d.get("wash_sale_window_days", 30)),
    ))
    trades["timestamp"] = pd.to_datetime(trades["timestamp"])
    after_equity = tax_model.compute(trades, equity)["after_tax_equity"]
    post = compute_safef_car25(after_equity.pct_change().dropna(), sf_cfg)

    def line(label, r):
        sf = r["safe_f"]
        verdict = ("UNDER-sized (headroom +{:.0%})".format(r["headroom"])
                   if sf is not None and sf >= 1.0
                   else "OVERSIZED (excess {:.0%})".format(-r["headroom"])
                   if sf is not None else f"skip: {r['skip_reason']}")
        print(f"  {label:22} safe_f={sf}  CAR25={r['car25_pct']}%/yr  "
              f"P(DD>{r['config']['dd_tolerance']:.0%})@f1={r['prob_dd_at_f1']}  "
              f"mdd95@f1={r['mdd95_at_f1_pct']}%  → {verdict}")

    print(f"T-151 safe-f / CAR25 — {run_dir}")
    print(f"  record: {equity.index[0].date()} → {equity.index[-1].date()} "
          f"({pre['n_obs']} daily obs); config: P(DD>"
          f"{sf_cfg.dd_tolerance:.0%} over {sf_cfg.horizon_days}td) ≤ "
          f"{sf_cfg.dd_probability:.0%}, {sf_cfg.n_paths} paths, "
          f"{sf_cfg.block_days}d blocks, seed {sf_cfg.seed}\n")
    line("Roth (pre-tax)", pre)
    line("taxable-IL (after-tax)", post)
    print("\n  CAVEAT 1: safe_f is record-dependent. This record contains no "
          "20%+ episode, so the\n  tolerance binds loosely pre-tax; the 26-yr "
          "record (MDD −59%) would bind FAR lower.\n  Any sizing decision uses "
          "the deep-window number — re-run on a multi-decade run dir.")
    print("  CAVEAT 2: the taxable number leans OVERSTATED in magnitude — "
          "T-141's tax model debits\n  the whole year's tax as ONE synthetic "
          "year-end day, and block resampling replicates\n  that lump across "
          "paths. The DIRECTION (taxable fails Bandy sizing at this turnover)\n"
          "  is the honest read, consistent with T-141's tax-exceeds-profit "
          "finding.")
    print("  reporting only — nothing sizes off these numbers; zero N_trials.")


if __name__ == "__main__":
    main()
