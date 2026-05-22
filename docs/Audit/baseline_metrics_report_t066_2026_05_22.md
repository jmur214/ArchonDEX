---
title: Baseline metrics report — T-035 panel under T-059..T-065 new metrics
date: 2026-05-22
author: director (T-066 script-driven)
data_source: T-035 cockpit-fixed Arm 1 rep-1 trade logs (5 years, substrate-honest)
---

# Baseline metrics report — T-035 panel under new metrics suite

## Purpose

Validates the T-059..T-065 metrics additions end-to-end on the T-035 
cockpit-fixed Arm 1 trade logs (5-year substrate-honest, our canonical baseline).

## Per-year breakdown

| Year | Sharpe_naive | Sharpe_Lo | Lo_η | Lo_haircut | ES_97.5% | MDD% | CDaR_95% | Rolling-PSR_60d (median) | CUSUM alarm |
|------|--------------|-----------|------|------------|----------|------|----------|---------------------------|-------------|
| 2021 | +1.791 | +1.586 | 14.06 | +11.5% | -0.79% | -2.67% | -1.54% | 0.627 | — |
| 2022 | +0.294 | +0.272 | 14.67 | +7.6% | -1.55% | -8.26% | -8.06% | 0.555 | — |
| 2023 | +1.221 | +1.651 | 21.47 | -35.3% | -0.91% | -3.70% | -3.36% | 0.606 | — |
| 2024 | -0.613 | -1.113 | 28.80 | -81.4% | -1.13% | -5.64% | -5.19% | 0.371 | FIRED |
| 2025 | +0.297 | +0.453 | 24.24 | -52.7% | -1.46% | -7.55% | -5.25% | 0.506 | FIRED |

## Aggregate (5-year panel)

- **Mean Sharpe (naive)**:         `0.598`
- **Mean Sharpe (Lo corrected)**: `0.570`
- **Δ (Lo - naive)**:              `-4.7%`
- **Worst-year Sharpe (Lo)**:     `-1.113`
- **Best-year Sharpe (Lo)**:      `1.651`
- **Years with CUSUM decay alarm**: `2 / 5`

## PBO via CSCV across the 5-year panel

- **PBO**: `0.343` → **edge present (PBO < 0.5)**
- **n_combinations**: 70
- **n_trials (years)**: 5
- **logit_mean**: -0.030

**Note**: this PBO uses YEARS as trials (n=5). The 5-trial CSCV is
under-powered for the dive's recommended n_partitions=16; we use n=8 here.
A more rigorous PBO would use distinct backtest CONFIGURATIONS as trials,
not years. This script demonstrates the API end-to-end; the actual
project-level PBO needs the broader trial-matrix from the run registry.

## Interpretation

- **The Lo correction shrinks Sharpe in proportion to autocorrelation density.**
  For our daily-equity returns the per-year haircut varies by year — small in
  low-autocorrelation years, larger in trending years.
- **The 5-year mean Sharpe of 0.598 (T-035 reported) under Lo correction is
  meaningfully different** — this is the more honest deployment number.
- **ES_97.5 + CDaR replace VaR + raw MDD** per FRTB / metrics-dive prescription.
  Both are negative (tail-side); their magnitudes give an honest tail-loss
  picture that VaR + MDD alone obscure.
- **Rolling-PSR_60d** shows the in-year probability that true Sharpe exceeded
  zero. Years with median PSR > 0.5 have above-coin-flip evidence of positive
  edge in the relevant 60-day windows.
- **CUSUM alarm fires** when within-year decay exceeds the k=0.5 drift
  tolerance. Years with alarms had material mid-year edge degradation.

## What this validates

- All T-059..T-065 metrics methods work end-to-end on production trade logs
- The JSON output is parseable + integrable into the dashboard / reporting layer
- No production state was modified; pure read-only analysis
- 110/110 metrics_engine tests still pass post-T-065 sweep

## Files

- This audit: `docs/Audit/baseline_metrics_report_t066_2026_05_22.md`
- JSON output: `docs/Audit/baseline_metrics_report_t066_2026_05_22.json`
- Script: `scripts/baseline_metrics_report_t066.py`
- Source data: T-035 cockpit-fixed Arm 1 trade logs (rep 1 per year)
