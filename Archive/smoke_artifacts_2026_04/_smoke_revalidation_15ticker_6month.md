# Gauntlet Re-validation — Phase 2.10b Q3 (2026-04-29T17:42:49)

Re-running the full 6-gate `DiscoveryEngine.validate_candidate` pipeline against the two edges that the in-sample factor-decomposition flagged as `tier=alpha`: `volume_anomaly_v1` (intercept t = +4.36, α = +6.1%) and `herding_v1` (intercept t = +4.49, α = +10.1%). The factor-decomp ran under the legacy fixed-cost model. The question this run answers: **do these edges still clear all six gates under the realistic Almgren-Chriss + ADV-bucketed spread cost model?**

- Window: `2024-01-01 → 2024-06-30`
- Universe: 15 of 15 production tickers (≥100 bars in window)
- Slippage model: `realistic` (base 10.0 bps + impact_coefficient 0.5)
- Significance threshold: `0.05` (uncorrected — two edges, BH-FDR is a near-no-op at this batch size)

## Headline

- **volume_anomaly_v1**: FAIL  (Sharpe=1.23, PBO=0%, deg=0.00, p=1.000, univ_b=nan, α_t=nan)
- **herding_v1**: FAIL  (Sharpe=2.15, PBO=0%, deg=0.00, p=1.000, univ_b=nan, α_t=nan)

## Per-edge gate detail

### volume_anomaly_v1

| Gate | Metric | Value | Pass? |
| --- | --- | --- | --- |
| 1. Quick backtest (benchmark-relative) | Sharpe (threshold ≈ 2.68) | 1.225 | FAIL |
| 2. PBO robustness | survival (≥ 0.70) | 0.00% | FAIL |
| 3. WFO degradation | IS=nan, OOS=nan, deg=0.00 (≤ 0.40) | 0.000 | PASS |
| 4. Statistical significance | p (< 0.05) | 1.0000 | FAIL |
| 5. Universe-B transfer | Sharpe (0 tickers, > 0) | nan | SKIP |
| 6. Factor-decomp alpha | annualized α=nan%, t=nan, R²=nan | t > 2 & α > 2% | FAIL |

- factor_alpha_reason: `n/a`
- passed_all_gates (per validate_candidate): **False**

### herding_v1

| Gate | Metric | Value | Pass? |
| --- | --- | --- | --- |
| 1. Quick backtest (benchmark-relative) | Sharpe (threshold ≈ 2.68) | 2.153 | FAIL |
| 2. PBO robustness | survival (≥ 0.70) | 0.00% | FAIL |
| 3. WFO degradation | IS=nan, OOS=nan, deg=0.00 (≤ 0.40) | 0.000 | PASS |
| 4. Statistical significance | p (< 0.05) | 1.0000 | FAIL |
| 5. Universe-B transfer | Sharpe (0 tickers, > 0) | nan | SKIP |
| 6. Factor-decomp alpha | annualized α=nan%, t=nan, R²=nan | t > 2 & α > 2% | FAIL |

- factor_alpha_reason: `n/a`
- passed_all_gates (per validate_candidate): **False**

## Run artifacts

- volume_anomaly_v1 → `/tmp/discovery_validation/980e7bcd-6a46-41a5-93b3-7090ae12769b` (most recent gate-1 trade log)
- herding_v1 → `/tmp/discovery_validation/4b9e8f57-a728-4a7a-96f0-5871b3475669` (most recent gate-1 trade log)

## Timings

- volume_anomaly_v1: 0.1 min
- herding_v1: 0.1 min

## Raw `validate_candidate` output

```json
{
  "volume_anomaly_v1": {
    "sharpe": 1.2252105635309867,
    "sortino": 1.2084417572552293,
    "robustness_survival": 0.0,
    "wfo_degradation": 0.0,
    "significance_p": 1.0,
    "passed_all_gates": false,
    "benchmark_threshold": 2.676155163133235
  },
  "herding_v1": {
    "sharpe": 2.1528113379004683,
    "sortino": 1.2435237534507846,
    "robustness_survival": 0.0,
    "wfo_degradation": 0.0,
    "significance_p": 1.0,
    "passed_all_gates": false,
    "benchmark_threshold": 2.676155163133235
  }
}
```
