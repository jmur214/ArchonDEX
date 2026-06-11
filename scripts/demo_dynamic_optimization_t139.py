#!/usr/bin/env python
# scripts/demo_dynamic_optimization_t139.py
"""T-139 payoff demonstration — frozen-fixture comparison, NOT a backtest.

On one frozen rebalance bar (real closes, 8 liquid names, pinned
2024-05-10 — see scripts/t139_fixture_data.py) compare, at $5K and $50K
capital:

    naive rounding (production Engine B truncation)
    vs Carver dynamic optimization (this branch, Engine C post-processor)
    vs the unrounded ideal book,

on annualized tracking error and trade counts. The headline number is how
much of the rounding-induced tracking error a $5K account recovers.

THIS IS AN ENGINEERING VERIFICATION ON A FIXTURE, NOT A PERFORMANCE
CLAIM. No backtest is run, no Sharpe is quoted, and NO N_trials are
consumed (CLAUDE.md MBL accounting). The production flag stays OFF.

Construction mirrors the production stack: target weights from the
PortfolioPolicy adaptive formula (inverse-vol, max_weight 0.30 cap,
20-bar vol), covariance from HRPOptimizer._estimate_cov (Ledoit-Wolf,
60-bar lookback) — the same estimator the Engine C wiring reuses.

Run:  python scripts/demo_dynamic_optimization_t139.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engines.engine_c_portfolio.dynamic_optimizer import (
    DynamicOptimizationConfig,
    naive_rounded_positions,
    optimize_integer_positions,
    tracking_error_std,
)
from engines.engine_c_portfolio.optimizers.hrp import HRPConfig, HRPOptimizer
from scripts.t139_fixture_data import CLOSES, PINNED_DATE, TICKERS

VOL_LOOKBACK = 20      # PortfolioPolicyConfig.vol_lookback default
MAX_WEIGHT = 0.30      # production portfolio_settings.json max_weight
COV_LOOKBACK = 60      # HRPConfig / dynopt default
CAPITALS = (5_000.0, 50_000.0)


def build_fixture():
    closes = pd.DataFrame({t: CLOSES[t] for t in TICKERS})
    returns = closes.pct_change().dropna()
    prices = {t: float(closes[t].iloc[-1]) for t in TICKERS}

    # Production adaptive formula: weight ∝ |signal| / vol, signal=1.0,
    # clipped at max_weight (policy.allocate, mode="adaptive").
    vols = returns.tail(VOL_LOOKBACK).std() * np.sqrt(252)
    inv_vol = 1.0 / vols
    weights = (inv_vol / inv_vol.sum()).clip(upper=MAX_WEIGHT)
    target_weights = {t: float(weights[t]) for t in TICKERS}

    hrp = HRPOptimizer(HRPConfig(cov_lookback=COV_LOOKBACK))
    covariance = hrp._estimate_cov(returns.tail(COV_LOOKBACK))
    return target_weights, prices, covariance


def annualized_te(positions: dict, target_weights: dict, prices: dict,
                  equity: float, covariance: pd.DataFrame) -> float:
    tickers = sorted(target_weights)
    w_star = np.array([target_weights[t] for t in tickers])
    w = np.array([positions.get(t, 0) * prices[t] / equity for t in tickers])
    sigma = covariance.loc[tickers, tickers].to_numpy() * 252.0
    return tracking_error_std(w, w_star, sigma)


def main() -> None:
    target_weights, prices, covariance = build_fixture()
    gross = sum(target_weights.values())

    print(f"T-139 fixture: {len(TICKERS)} names, pinned {PINNED_DATE}, "
          f"gross target {gross:.3f}")
    print(f"{'ticker':>7} {'price':>9} {'w*':>7}")
    for t in TICKERS:
        print(f"{t:>7} {prices[t]:>9.2f} {target_weights[t]:>7.4f}")
    print()

    rows = []
    for equity in CAPITALS:
        tickers = sorted(target_weights)
        w_star = np.array([target_weights[t] for t in tickers])
        px = np.array([prices[t] for t in tickers])
        cur = np.zeros(len(tickers), dtype=np.int64)

        n_naive = naive_rounded_positions(w_star, px, cur, equity)
        naive_pos = dict(zip(tickers, (int(x) for x in n_naive)))

        # buffer=0: this is a from-flat construction comparison — the
        # speed control (default 0.02) is a live-trading trade-pacing
        # feature, not part of the expressibility question.
        res = optimize_integer_positions(
            target_weights, prices, {t: 0 for t in tickers}, equity, covariance,
            cfg=DynamicOptimizationConfig(tracking_error_buffer=0.0),
        )

        te_naive = annualized_te(naive_pos, target_weights, prices, equity, covariance)
        te_opt = res.tracking_error_optimized
        recovery = 100.0 * (te_naive - te_opt) / te_naive if te_naive > 0 else 0.0

        naive_trades = int(np.sum(np.abs(n_naive)))
        opt_trades = sum(abs(v) for v in res.trades.values())
        naive_gross = float(np.sum(np.abs(n_naive) * px)) / equity
        opt_gross = sum(abs(n) * prices[t] for t, n in res.positions.items()) / equity

        rows.append((equity, te_naive, te_opt, recovery,
                     naive_trades, opt_trades, naive_gross, opt_gross))

        print(f"=== capital ${equity:,.0f} ===")
        print(f"{'ticker':>7} {'ideal':>8} {'naive':>6} {'dynopt':>7}")
        for i, t in enumerate(tickers):
            ideal = target_weights[t] * equity / prices[t]
            print(f"{t:>7} {ideal:>8.2f} {n_naive[i]:>6d} {res.positions[t]:>7d}")
        print(f"  TE naive   : {te_naive:.4%} annualized")
        print(f"  TE dynopt  : {te_opt:.4%} annualized")
        print(f"  TE unrounded ideal: 0.0000% (definitionally)")
        print(f"  >>> tracking-error recovery vs naive: {recovery:.1f}%")
        print(f"  shares traded: naive {naive_trades}, dynopt {opt_trades}")
        print(f"  gross deployed: naive {naive_gross:.1%}, dynopt {opt_gross:.1%}")
        print()

    print("| capital | TE naive | TE dyn-opt | TE recovered | trades naive | trades dyn-opt |")
    print("|---|---|---|---|---|---|")
    for (eq, tn, to, rec, ntr, otr, _, _) in rows:
        print(f"| ${eq:,.0f} | {tn:.4%} | {to:.4%} | **{rec:.1f}%** | {ntr} | {otr} |")
    print("\nEngineering fixture verification — no backtest run, no N_trials consumed.")


if __name__ == "__main__":
    main()
