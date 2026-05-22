---
title: Metrics report — 5 run(s) under T-059..T-065 suite
date: 2026-05-22
author: scripts/metrics_report.py (T-2026-05-22-069)
---

# Metrics report — 5 run(s) under T-059..T-065 suite

## Per-run breakdown

| Label | Sharpe_naive | Sharpe_Lo | Lo_η | Lo_haircut | ES_97.5% | MDD% | CDaR_95% | Rolling-PSR | CUSUM alarm |
|-------|--------------|-----------|------|------------|----------|------|----------|-------------|-------------|
| e5e95c32 | +1.791 | +1.586 | 14.06 | +11.5% | -0.79% | -2.67% | -1.54% | 0.627 | — |
| 48d8fb51 | +0.294 | +0.272 | 14.67 | +7.6% | -1.55% | -8.26% | -8.06% | 0.555 | — |
| c9a5dbd0 | +1.221 | +1.651 | 21.47 | -35.3% | -0.91% | -3.70% | -3.36% | 0.606 | — |
| 66bbaecc | -0.613 | -1.113 | 28.80 | -81.4% | -1.13% | -5.64% | -5.19% | 0.371 | FIRED |
| 01f06c0a | +0.297 | +0.453 | 24.24 | -52.7% | -1.46% | -7.55% | -5.25% | 0.506 | FIRED |

## Aggregate

- **n_valid_runs**: 5
- **Mean Sharpe (naive)**: `0.598`
- **Mean Sharpe (Lo corrected)**: `0.570`
- **Worst Sharpe (Lo)**: `-1.113`
- **Best Sharpe (Lo)**: `1.651`
- **Runs with CUSUM alarm**: 2 / 5

## PBO via CSCV

- **PBO**: `0.343` → **edge present (PBO < 0.5)**
- **n_combinations**: 70
- **n_partitions**: 8
- **n_trials (runs)**: 5
- **logit_mean**: -0.030

## Metric definitions

- **Sharpe_naive**: standard `mean/std × √252` annualization
- **Sharpe_Lo**: T-059 Lo η(q) autocorrelation correction; deflates naive Sharpe under positive autocorrelation, amplifies under negative
- **ES_97.5%**: T-062 Expected Shortfall (mean of worst 2.5% of returns); Basel III FRTB standard, coherent unlike VaR
- **CDaR_95%**: T-062 Conditional Drawdown at Risk (mean of worst 5% of drawdowns); LP-tractable + convex (unlike raw MDD)
- **Rolling-PSR**: T-063 Probability that true Sharpe > 0 over a 60-bar trailing window; live-monitoring signal for decay
- **CUSUM alarm**: T-063 sequential analysis detector; fires when within-run drift exceeds k=0.5σ tolerance for sustained periods
- **PBO via CSCV**: T-060 Probability of Backtest Overfitting; Bailey-Borwein-López de Prado-Zhu (2017). PBO < 0.5 = edge; > 0.5 = overfit.
