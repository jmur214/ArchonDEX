---
task_id: B-1
title: "B-1 raw-signal decile re-evaluation — VERDICT"
date: 2026-10-14
author: Agent A
outcome: "H1 NOT MET — 0 of 13 main signals clear the IC bar and none meets the wealth leg against both benchmarks; short window 0 of 6; calendar 0 of 7. Scoped refutation (§6 'Nothing meets H1')."
status: FINAL — R-approved at 7266caa (first read, 1,190 cells vs the artifacts, 0 mismatches) and the wording fixup bfe8055 (re-checked by hash); merged 2026-10-14. What travels (R-3): the prereg's own words only.
reproduce: "§12 below; the panel md5 d9d449d17f8f102614b34079e8f1bd60 and the results md5 5de36b89e0ade6eac008667e035d2d03 must reproduce"
---

# B-1 — VERDICT: on the literature's construction, the cross-sectional price vocabulary clears nothing

Pre-registration: `docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md`, FROZEN 2026-10-13
(`469fa69` on the branch; `2af10ad` the director's merge to main, identical text), with three post-freeze, pre-data amendments (§3 below). Branch
`research/raw-signal-decile-b1`. The harness's open choices were fixed in prereg §11.4 and
committed (`bae38e5`, revised `6c6200a` / `cc8a24e`) before the harness produced any output.
**N_trials +4.**

## 0. The answer

- **H1 as ruled is NOT MET.** No non-calendar, cross-sectional signal has a BH-adjusted IC
  p < 0.05, and none has a 25%-satellite Δ log wealth `ci_low > 0` against **both** 100% SPY and
  the 25% equal-weight-universe sleeve. The main family: **0 of 13** clear the IC bar. The lowest
  BH-adjusted p is 0.107, shared by four signals. **0 of 13** clear the wealth leg against both
  benchmarks.
- The short-window family: **0 of 6.** The calendar family: **0 of 7.** The definition-sensitivity
  rows are reported and sit in no BH count, as frozen; none would change the reading.
- **This is §6's "Nothing meets H1" row, a scoped refutation:** the cross-sectional price
  vocabulary, on the literature's construction, clears nothing, even with survivorship bias
  helping it. Under the §3.6 pre-commitment, **the refutation is conservative and stands.**
- Two signals land in §6's "EW tilt, not signal" row on the wealth leg: `skew_60d` and
  `vol_regime_5_60`. Neither clears the IC bar.
- The pre-data prior for H1 as ruled was ≈ 12% (§9). Nothing goes to RR-6's Gate 1′.
- The pre-named 2012 window (§7 of this doc) agrees: 0 of 13, 0 of 7.

## 1. The frozen text is intact

```bash
F=docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md
for sec in "## 4. Signal inventory" "## 8. Predictions"; do
  awk -v h="$sec" 'index($0,h)==1{f=1} f&&/^## /&&index($0,h)!=1{exit} f' "$F" | shasum -a 256 | cut -c1-12
done   # → ba6cc7bff764, cb9f4c3e185b
```

These are the 09-30 values. They were re-checked at every launch gate and again at this
document's commit. §4 (signs) and §8 (predictions) are byte-identical to the draft, and every
inventory change lives in the amendment sections, never in §4 itself.

## 2. The record

| artifact | identity | where / how |
|---|---|---|
| panel (attempt 2), run A | canonical md5 **`d9d449d17f8f102614b34079e8f1bd60`** | `full_2a/`, builder at `dc8eeb5`, 807.8 s (census `wall_seconds`; 809 s by `/usr/bin/time`, incl. start-up), peak RSS 1.02 GB |
| panel (attempt 2), run B | **the same md5** | `full_2b/`, at `6c6200a` (builder, `core/`, `engines/` byte-identical), 770.7 s (772 s by `/usr/bin/time`), 954 MB. The two censuses differ only in `wall_seconds` |
| harness run 1 | canonical md5 **`5de36b89e0ade6eac008667e035d2d03`** | `run1/`, at `cc8a24e`, 20.5 s (`meta.wall_seconds`; 22 s by `/usr/bin/time`, incl. start-up), 524 MB |
| harness run 2 | **the same md5** | `run2/`, 21.1 s (23 s by `/usr/bin/time`), 496 MB. The JSON files differ only in `meta.wall_seconds` |
| 2012 window | `bbf88ffc9f23bde015e03b5361b09dd4` | `run_2012/`, 17.0 s (19 s by `/usr/bin/time`), 488 MB |
| attempt 1 (kept as the first attempt) | census `f47aa0d6f705…`, **HALT**, no panel | `full_a/`, at `e595ae5`: four SimFin edges blank at the old window start |

- **Gates passed outright at every launch**, with no waiver: one heavy job, disk ≥ 5 GB, swap
  ≥ 1 GB, clean tree, frozen hashes, code provenance in the agent-a worktree, `run_isolated`'s
  env pins (refused, never re-exec'd).
- **Smokes were run before every full run**, covering each window's first twelve months
  (§11.1, binding since the second amendment).
- **The harness census:** every main and sensitivity signal has an IC in 312/312 months, and the
  short window in 54/54. There are 0 Arm L fallback months and 0 missing LS months. The
  calendar runs 6,519 days, with 2001–2025 judged and 2000 a partial year.
- **Independent check, outside the harness:** the monthly IC for `mom_12_1`, `reversal_1m`,
  `realized_vol_60d` and `moving_avg_distance_50d` was recomputed with `scipy.stats.spearmanr`
  directly from the panel. It matches to 4 decimals.
- **Alignment probe:** the raw `reversal_1m` (last-21-day return) against the forward return
  gives a mean IC of −0.0175. If the forward return were the current month, this would be near
  +1.
- `january_effect`'s near-zero slope was verified as a difference of means: +5.75 bps of
  next-day EW return on flagged days against +5.75 bps on the rest, a difference of 0.003 bps.

## 3. The inventory as tested — three amendments and one pre-ruling, beside the comparison

| family | frozen (§4/§5) | as tested | change | basis (all pre-data) |
|---|---|---|---|---|
| main | 15 | **13** | `herding_v1` excluded; `volume_anomaly_v1` auto-excluded | 1st amendment (a daily event edge is silent at month-end). Pre-ruling: it tripped the 10% bar, unusable in 29.8% of months, applied automatically |
| sensitivity | 5 | 5 | — | reported, in no BH count |
| short window | 7 on 2020-04 → 2025-12 | **6 on 2021-07 → 2025-12** (54 months) | `earnings_proximity_5d` excluded; window start moved | 1st amendment; **2nd amendment**: 2020-04 came from the excluded edge's earnings calendar, while SimFin FREE filings start at publish 2020-07 and TTM needs four quarters |
| calendar | 10 | **7** | `fomc_drift`, `pre_fomc_reduce`, `pre_holiday` excluded | **3rd amendment**: `FOMC_DATES` / `US_MARKET_HOLIDAYS` start 2018, so these are constant 0.0 for 2000–2017 |

**UNTESTED by B-1, by name:**
- Excluded by the amendments and the pre-ruling: `herding_v1`, `earnings_proximity_5d`,
  `volume_anomaly_v1`, `fomc_drift`, `pre_fomc_reduce`, `pre_holiday`.
- Excluded at the freeze: `pair_zscore_60d`, the 11 macro-timing features (ruled OUT
  2026-10-01) and the 17 market-wide features (§3.1).

**The survivorship pre-commitment (§3.6), restated verbatim beside the comparison:**
> - **A refutation (nothing clears) is CONSERVATIVE and stands** — nothing cleared even with the
>   bias helping it.
> - **A survivor is NOT evidence.** It is "cleared on a survivor-biased substrate" and requires
>   re-verification on survivorship-complete data (a paid CRSP-class source) before it counts.

**Coverage:**
- 153 of 312 months (**49.0%**) sit below 80% point-in-time coverage; the last such month is
  2012-09.
- Coverage is 52.7% in 2000-01, 99.4% in 2025-12, and 79.8% weighted by members.

## 4. §8's predictions, line by line — compared as written against the amended inventory (13 / 6 / 7)

| line | prediction (verbatim) | outcome | |
|---|---|---|---|
| (a) | "Main family, IC clearing BH at q = 0.05: **3** (plausible range 1–5)." | **0 of 13**; the lowest BH p is 0.107 | **MISS**, below the stated range |
| (b) | "The three strongest by IC t in the declared sign: 1. `beta_252d` (−), 2. `realized_vol_60d` (−), 3. `dist_52w_high` (+) … 12-1 momentum, which I rank fourth" | Actual order: 1. `reversal_1m` t +2.14, 2. `vol_regime_5_60` +1.74, 3. `skew_60d` +1.28, 4. `mom_12_1` +0.08. The predicted three rank **7th (−0.52), 8th (−0.54) and 10th (−1.17)**, all in the wrong direction and none significant | **MISS.** The one placement that is right (momentum 4th) carries a t of 0.08 |
| (c) | "the two low-risk signals clear the IC bar but **fail the wealth leg** … `dist_52w_high` is the single most likely to clear **both** bars." | Low-risk: **neither clears the IC bar** (t −0.54, −0.52), and **both fail the wealth leg**: vs SPY `ci_low` −0.135 / −0.158, vs EW −0.348 / −0.375. `dist_52w_high` clears **neither**, and its Δ log wealth vs the EW sleeve is **negative with a CI that excludes zero**: −0.334 [−0.612, −0.110] | **MISS.** The wealth-leg failure was predicted, but the IC clear it was paired with did not happen, and the "most likely to clear both" call was wrong in the strongest way |
| calendar | "**Calendar family:** 0 clear" | **0 of 7** (the three blind features excluded, untested) | **HIT** |
| short window | "**Short-window family:** 0 clear." | **0 of 6** | **HIT** |

**Score: 2 of 5.** Both hits are predictions that nothing would clear; every prediction that
something would clear failed. The low-risk pair's Arm L Sharpes, 0.92 [0.56, 1.34] and 0.85
[0.49, 1.34], are among the family's best (the 0.92 is tied with `high_minus_low_60d`). Neither
signal ranks next month's return, which is what the IC tests, and both ICs ran against their
declared sign. Comparing those Sharpes with SPY's 0.60 [0.17, 1.06] carries the EW tilt that
the wealth ruling closed: the EW sleeve's Sharpe is not in the record.

## 5. The pre-named outcomes (§6, verbatim) — and which apply

> | Outcome | What it means | What it does NOT mean |
> |---|---|---|
> | **H1 met** (vs BOTH benchmarks) by a non-calendar signal | Cleared **on a survivor-biased substrate** (§3.6). Goes to survivorship-complete re-verification and RR-6 Gate 1′. | Not evidence yet. Not deployable. |
> | **Clears vs SPY but NOT vs the EW universe** (§3.7) | "EW tilt, not signal." **Does NOT meet H1** (ruling 2). Reported as such. | Not a signal discovery. |
> | **IC clears BH, wealth leg fails** | A real ranking signal that does not pay as a long-only satellite at this weight (the expected shape for low-risk signals — §8). | Not a refutation of the anomaly; not a deployable satellite. |
> | **Nothing meets H1** | **Refutation, scoped:** the cross-sectional price vocabulary, on the literature's construction, clears nothing even with survivorship bias helping it. Conservative, and it stands. | **Not** a verdict on macro timing (§3.1), fundamentals over a long window (§5.2), or calendar effects beyond §5.3. |
> | **A signal clears with the WRONG sign** | Reported as not clearing, with the opposite-sign statistic shown. | Never flipped (§2.1). |

**Which apply:**
- **"Nothing meets H1" — APPLIES.** It is a scoped refutation, conservative, and it stands
  (§3.6).
- **"Clears vs SPY but NOT vs the EW universe" — APPLIES to two signals, on the wealth leg
  only:**
  - `skew_60d`: Δ log wealth vs SPY +0.247 [+0.011, +0.544], vs EW +0.015 [−0.136, +0.200].
  - `vol_regime_5_60`: +0.308 [+0.077, +0.495] vs SPY, +0.076 [−0.094, +0.203] vs EW.

  Neither clears the IC bar. This is "EW tilt, not signal": the EW sleeve itself beats SPY by
  +0.232 [+0.052, +0.422] on this window (§8, property 2).
- **"IC clears BH, wealth leg fails" — does not arise.** No IC clears.
- **"A signal clears with the WRONG sign" — does not arise.** No BH rejection in either
  direction. Reported, never flipped:
  - Three signals have a 95% HAC CI entirely below zero in their declared direction:
    `moving_avg_distance_50d` −0.0225 [−0.0403, −0.0048], `drawdown_60d` −0.0234 [−0.0441,
    −0.0027] and `overnight_intraday_v1` −0.0117 [−0.0224, −0.0009]. All three have BH p 0.107.
  - `reversal_1m` is nominally significant in the declared direction, +0.0175 [+0.0015,
    +0.0335], also with BH p 0.107.
  - *Observation, not a finding (post hoc):* the three wrong-direction signals all reward recent
    strength, which is consistent with the same one-month reversal that `reversal_1m` measures.

## 6. Results — the headline window, 2000-01 → 2025-12

- Arm L = top decile by declared sign, equal weight, monthly rebalance, 10 bps round trip.
- Δ log W = (75% SPY + 25% Arm L) against 100% SPY, and against (75% SPY + 25% EW sleeve).
- Every Sharpe, Sortino and Δ log W CI is the 2.5th–97.5th percentile of the project-standard
  Künsch moving-block bootstrap: 1000 iterations, 6-month blocks, seed 0, paired across arms,
  benchmarks and signals within the window.
- IC CIs are HAC normal intervals (Bartlett, 6 lags): mean ± 1.96·|mean/t|, identical to the
  statsmodels `conf_int` of the fit.
- Calendar slopes use Newey-West with automatic lags.
- Arm LS is diagnostic only; a Roth cannot short.

#### Benchmarks
| window | months | SPY ann. | SPY Sharpe [CI] | SPY MaxDD | EW ann. | EW MaxDD | EW cost (bps/yr) | 25% EW sleeve ΔlogW vs SPY [CI] |
|---|--:|--:|---|--:|--:|--:|--:|---|
| main (from 2000-01) | 312 | 9.1% | +0.60 [+0.17, +1.06] | -50.8% | 12.8% | -52.1% | 3.9 | +0.232 [+0.052, +0.422] |
| short_window (from 2021-07) | 54 | 12.8% | +0.82 [-0.01, +1.81] | -23.9% | 9.0% | -20.3% | 4.9 | -0.041 [-0.107, +0.017] |

#### Main family — IC (13 BH members)
| signal | sign | sparse | IC mean [95% HAC CI] | NW t | p | BH p | clears IC |
|---|:-:|:-:|---|--:|--:|--:|:-:|
| `mom_12_1` | + |  | +0.0008 [-0.0203, +0.0219] | +0.08 | 0.9387 | 0.9387 | no |
| `mom_6_1` | + |  | -0.0042 [-0.0201, +0.0117] | -0.52 | 0.6056 | 0.7158 | no |
| `reversal_1m` | − |  | +0.0175 [+0.0015, +0.0335] | +2.14 | 0.0320 | 0.1068 | no |
| `dist_52w_high` | + |  | -0.0142 [-0.0379, +0.0096] | -1.17 | 0.2423 | 0.4500 | no |
| `realized_vol_60d` | − |  | -0.0071 [-0.0325, +0.0184] | -0.54 | 0.5875 | 0.7158 | no |
| `beta_252d` | − |  | -0.0075 [-0.0357, +0.0208] | -0.52 | 0.6037 | 0.7158 | no |
| `skew_60d` | − |  | +0.0074 [-0.0040, +0.0189] | +1.28 | 0.2021 | 0.4378 | no |
| `high_minus_low_60d` | − |  | -0.0037 [-0.0228, +0.0153] | -0.38 | 0.7010 | 0.7594 | no |
| `drawdown_60d` | + |  | -0.0234 [-0.0441, -0.0027] | -2.21 | 0.0269 | 0.1068 | no |
| `ma_cross_50_200` | + |  | -0.0048 [-0.0213, +0.0117] | -0.57 | 0.5689 | 0.7158 | no |
| `moving_avg_distance_50d` | + |  | -0.0225 [-0.0403, -0.0048] | -2.49 | 0.0129 | 0.1068 | no |
| `vol_regime_5_60` | − |  | +0.0084 [-0.0011, +0.0178] | +1.74 | 0.0823 | 0.2139 | no |
| `overnight_intraday_v1` | + |  | -0.0117 [-0.0224, -0.0009] | -2.13 | 0.0329 | 0.1068 | no |

#### Main family — wealth leg (Arm L, 25% satellite)
| signal | Arm L ann. | Sharpe [95% CI] | Sortino ci_low | MaxDD | ΔlogW vs SPY [CI] | ΔlogW vs EW [CI] | both > 0 | H1 |
|---|--:|---|--:|--:|---|---|:-:|:-:|
| `mom_12_1` | 12.1% | +0.65 [+0.19, +1.00] | +0.25 | -56.5% | +0.194 [-0.104, +0.397] | -0.038 [-0.359, +0.159] | no | no |
| `mom_6_1` | 13.8% | +0.70 [+0.23, +1.10] | +0.30 | -59.5% | +0.292 [-0.050, +0.523] | +0.060 [-0.226, +0.225] | no | no |
| `reversal_1m` | 12.9% | +0.51 [+0.13, +0.91] | +0.17 | -68.2% | +0.167 [-0.174, +0.536] | -0.066 [-0.312, +0.176] | no | no |
| `dist_52w_high` | 6.8% | +0.54 [+0.09, +0.99] | +0.12 | -49.5% | -0.102 [-0.335, +0.112] | -0.334 [-0.612, -0.110] | no | no |
| `realized_vol_60d` | 10.6% | +0.92 [+0.56, +1.34] | +0.74 | -31.7% | +0.163 [-0.135, +0.483] | -0.070 [-0.348, +0.249] | no | no |
| `beta_252d` | 10.3% | +0.85 [+0.49, +1.34] | +0.68 | -34.9% | +0.148 [-0.158, +0.503] | -0.084 [-0.375, +0.238] | no | no |
| `skew_60d` | 13.1% | +0.74 [+0.32, +1.17] | +0.44 | -48.0% | +0.247 [+0.011, +0.544] | +0.015 [-0.136, +0.200] | no | no |
| `high_minus_low_60d` | 11.4% | +0.92 [+0.50, +1.40] | +0.65 | -39.0% | +0.192 [-0.033, +0.461] | -0.040 [-0.236, +0.190] | no | no |
| `drawdown_60d` | 5.3% | +0.40 [-0.00, +0.86] | -0.00 | -55.0% | -0.213 [-0.405, +0.026] | -0.446 [-0.700, -0.201] | no | no |
| `ma_cross_50_200` | 13.1% | +0.73 [+0.27, +1.12] | +0.37 | -56.6% | +0.262 [-0.030, +0.434] | +0.030 [-0.255, +0.168] | no | no |
| `moving_avg_distance_50d` | 10.1% | +0.55 [+0.09, +0.96] | +0.12 | -60.5% | +0.057 [-0.197, +0.239] | -0.175 [-0.447, +0.021] | no | no |
| `vol_regime_5_60` | 14.0% | +0.81 [+0.36, +1.22] | +0.47 | -44.4% | +0.308 [+0.077, +0.495] | +0.076 [-0.094, +0.203] | no | no |
| `overnight_intraday_v1` | 9.2% | +0.69 [+0.28, +1.15] | +0.34 | -42.0% | +0.042 [-0.151, +0.276] | -0.191 [-0.369, +0.010] | no | no |

#### Main family — turnover, costs, counts, LS (diagnostic)
| signal | turnover (1-way/yr) | cost drag (bps/yr) | L fallback months | oversized top | IC months | LS ann. | LS Sharpe [CI] | LS missing |
|---|--:|--:|--:|--:|--:|--:|---|--:|
| `mom_12_1` | 3.87 | 38.7 | 0 | 0 | 312/312 | -6.8% | -0.24 [-0.61, +0.09] | 0 |
| `mom_6_1` | 5.47 | 54.7 | 0 | 0 | 312/312 | -3.7% | -0.14 [-0.48, +0.12] | 0 |
| `reversal_1m` | 10.44 | 104.4 | 0 | 0 | 312/312 | 0.4% | +0.02 [-0.29, +0.36] | 0 |
| `dist_52w_high` | 8.43 | 84.3 | 0 | 19 | 312/312 | -12.9% | -0.44 [-0.76, -0.08] | 0 |
| `realized_vol_60d` | 3.67 | 36.7 | 0 | 0 | 312/312 | -8.7% | -0.29 [-0.61, +0.12] | 0 |
| `beta_252d` | 1.50 | 15.0 | 0 | 0 | 312/312 | -7.3% | -0.23 [-0.59, +0.15] | 0 |
| `skew_60d` | 5.47 | 54.7 | 0 | 0 | 312/312 | -1.2% | -0.12 [-0.46, +0.31] | 0 |
| `high_minus_low_60d` | 6.49 | 64.9 | 0 | 0 | 312/312 | -9.5% | -0.36 [-0.64, +0.05] | 0 |
| `drawdown_60d` | 9.77 | 97.7 | 0 | 56 | 312/312 | -12.9% | -0.52 [-0.86, -0.13] | 0 |
| `ma_cross_50_200` | 3.49 | 34.9 | 0 | 0 | 312/312 | -4.0% | -0.14 [-0.47, +0.13] | 0 |
| `moving_avg_distance_50d` | 8.60 | 86.0 | 0 | 0 | 312/312 | -8.9% | -0.43 [-0.81, -0.09] | 0 |
| `vol_regime_5_60` | 10.47 | 104.7 | 0 | 0 | 312/312 | 0.8% | +0.07 [-0.30, +0.34] | 0 |
| `overnight_intraday_v1` | 9.78 | 97.8 | 0 | 0 | 312/312 | -4.4% | -0.54 [-0.93, -0.23] | 0 |

#### Definition-sensitivity rows (NOT in any BH count)
| signal | sign | sparse | IC mean [95% HAC CI] | NW t | p | BH p | clears IC |
|---|:-:|:-:|---|--:|--:|--:|:-:|
| `momentum_12_1_v1` | + | y | -0.0078 [-0.0228, +0.0072] | -1.02 | 0.3065 | — | — |
| `momentum_6_1_v1` | + | y | -0.0026 [-0.0146, +0.0094] | -0.43 | 0.6675 | — | — |
| `short_term_reversal_v1` | + | y | +0.0093 [-0.0025, +0.0212] | +1.54 | 0.1227 | — | — |
| `low_vol_factor_v1` | + | y | -0.0096 [-0.0290, +0.0097] | -0.97 | 0.3299 | — | — |
| `betting_against_beta_v1` | + |  | -0.0110 [-0.0383, +0.0163] | -0.79 | 0.4288 | — | — |

| signal | Arm L ann. | Sharpe [95% CI] | Sortino ci_low | MaxDD | ΔlogW vs SPY [CI] | ΔlogW vs EW [CI] | both > 0 | H1 |
|---|--:|---|--:|--:|---|---|:-:|:-:|
| `momentum_12_1_v1` | 10.4% | +0.64 [+0.17, +1.06] | +0.22 | -53.0% | +0.091 [-0.138, +0.269] | -0.142 [-0.401, +0.032] | no | — |
| `momentum_6_1_v1` | 12.3% | +0.74 [+0.29, +1.14] | +0.39 | -52.3% | +0.211 [-0.022, +0.394] | -0.021 [-0.215, +0.104] | no | — |
| `short_term_reversal_v1` | 12.9% | +0.51 [+0.13, +0.91] | +0.17 | -68.4% | +0.165 [-0.173, +0.534] | -0.067 [-0.313, +0.172] | no | — |
| `low_vol_factor_v1` | 10.0% | +0.85 [+0.46, +1.31] | +0.56 | -36.1% | +0.109 [-0.138, +0.386] | -0.124 [-0.349, +0.134] | no | — |
| `betting_against_beta_v1` | 10.0% | +0.85 [+0.51, +1.33] | +0.67 | -32.9% | +0.130 [-0.155, +0.472] | -0.102 [-0.384, +0.221] | no | — |

#### Short-window family (2021-07 → 2025-12; nominate only)
| signal | sign | sparse | IC mean [95% HAC CI] | NW t | p | BH p | clears IC |
|---|:-:|:-:|---|--:|--:|--:|:-:|
| `value_book_to_market_v1` | + | y | -0.0000 [-0.0244, +0.0243] | -0.00 | 0.9987 | 0.9987 | no |
| `value_earnings_yield_v1` | + | y | -0.0103 [-0.0324, +0.0118] | -0.92 | 0.3600 | 0.9987 | no |
| `quality_gross_profitability_v1` | + | y | +0.0022 [-0.0149, +0.0192] | +0.25 | 0.8009 | 0.9987 | no |
| `quality_roic_v1` | + | y | +0.0055 [-0.0150, +0.0260] | +0.52 | 0.6004 | 0.9987 | no |
| `accruals_inv_sloan_v1` | + | y | +0.0018 [-0.0109, +0.0144] | +0.27 | 0.7864 | 0.9987 | no |
| `accruals_inv_asset_growth_v1` | + | y | -0.0002 [-0.0177, +0.0172] | -0.03 | 0.9776 | 0.9987 | no |

| signal | Arm L ann. | Sharpe [95% CI] | Sortino ci_low | MaxDD | ΔlogW vs SPY [CI] | ΔlogW vs EW [CI] | both > 0 | H1 |
|---|--:|---|--:|--:|---|---|:-:|:-:|
| `value_book_to_market_v1` | 10.2% | +0.55 [-0.16, +1.12] | -0.24 | -22.0% | -0.030 [-0.138, +0.072] | +0.012 [-0.063, +0.077] | no | no |
| `value_earnings_yield_v1` | 8.0% | +0.42 [-0.19, +1.01] | -0.32 | -22.7% | -0.055 [-0.131, +0.031] | -0.014 [-0.059, +0.040] | no | no |
| `quality_gross_profitability_v1` | 9.5% | +0.53 [-0.17, +1.20] | -0.28 | -26.0% | -0.039 [-0.106, +0.024] | +0.002 [-0.053, +0.060] | no | no |
| `quality_roic_v1` | 10.3% | +0.57 [-0.13, +1.23] | -0.22 | -26.9% | -0.031 [-0.094, +0.024] | +0.011 [-0.046, +0.066] | no | no |
| `accruals_inv_sloan_v1` | 10.1% | +0.58 [-0.07, +1.19] | -0.14 | -20.3% | -0.031 [-0.094, +0.036] | +0.010 [-0.016, +0.042] | no | no |
| `accruals_inv_asset_growth_v1` | 9.8% | +0.57 [-0.10, +1.13] | -0.16 | -19.2% | -0.034 [-0.113, +0.052] | +0.008 [-0.038, +0.053] | no | no |

| signal | turnover (1-way/yr) | cost drag (bps/yr) | L fallback months | oversized top | IC months | LS ann. | LS Sharpe [CI] | LS missing |
|---|--:|--:|--:|--:|--:|--:|---|--:|
| `value_book_to_market_v1` | 1.27 | 12.7 | 0 | 0 | 54/54 | 0.8% | +0.11 [-1.01, +0.96] | 0 |
| `value_earnings_yield_v1` | 1.43 | 14.3 | 0 | 0 | 54/54 | -1.7% | -0.26 [-1.12, +0.57] | 0 |
| `quality_gross_profitability_v1` | 0.82 | 8.2 | 0 | 0 | 54/54 | -0.1% | -0.01 [-0.75, +0.95] | 0 |
| `quality_roic_v1` | 0.87 | 8.7 | 0 | 0 | 54/54 | 0.9% | +0.13 [-0.66, +1.08] | 0 |
| `accruals_inv_sloan_v1` | 3.12 | 31.2 | 0 | 0 | 54/54 | 0.6% | +0.13 [-0.43, +0.91] | 0 |
| `accruals_inv_asset_growth_v1` | 1.83 | 18.3 | 0 | 0 | 54/54 | 0.3% | +0.07 [-0.91, +1.10] | 0 |

#### Calendar family (daily dummy regression)
| feature | days | NW lags | slope, bps/day per unit [95% HAC CI] | NW t | p | BH p | clears |
|---|--:|--:|---|--:|--:|--:|:-:|
| `sell_in_may_halloween` | 6519 | 10 | +4.97 [-0.73, +10.67] | +1.71 | 0.0874 | 0.4211 | no |
| `january_effect` | 6519 | 10 | +0.00 [-19.78, +19.79] | +0.00 | 0.9998 | 0.9998 | no |
| `triple_witching_premium` | 6519 | 10 | -14.13 [-43.79, +15.54] | -0.93 | 0.3506 | 0.5720 | no |
| `tax_loss_season` | 6519 | 10 | +7.21 [-2.74, +17.16] | +1.42 | 0.1557 | 0.4211 | no |
| `month_of_year_dummy` | 6519 | 10 | +0.35 [-0.49, +1.19] | +0.83 | 0.4085 | 0.5720 | no |
| `weekday_dummy` | 6519 | 10 | -1.64 [-4.04, +0.76] | -1.34 | 0.1805 | 0.4211 | no |
| `days_to_quarter_end` | 6519 | 10 | +0.04 [-0.08, +0.15] | +0.63 | 0.5309 | 0.6193 | no |

**H1:** {"met": false, "signals_meeting": [], "ew_tilt_not_signal": ["skew_60d", "vol_regime_5_60"], "n_trials_consumed": 4}  
**families:** {"main": {"m": 13, "n_clear_ic": 0}, "short_window": {"m": 6, "n_clear_ic": 0}, "calendar": {"m": 7, "n_clear": 0}}  
**canonical md5:** `5de36b89e0ade6eac008667e035d2d03`

## 7. The pre-named sensitivity window: 2012-01 → 2025-12 (beside the headline, never instead)

Coverage exceeds 80% for this whole window. **0 of 13 main signals clear; 0 of 7 calendar.**
- The EW sleeve no longer beats SPY: −0.024 [−0.129, +0.074]. The 2000–2025 EW tilt is a
  pre-2012 effect, of survivorship and the EW premium together; the two are not separable on
  this substrate.
- Three signals are **significantly worse than SPY**: `dist_52w_high` −0.121 [−0.265, −0.006],
  `drawdown_60d` −0.121 [−0.243, −0.008] and `overnight_intraday_v1` −0.130 [−0.254, −0.016].
- The short-window rows are identical to §6's, because the window is the same 54 months.

#### Benchmarks
| window | months | SPY ann. | SPY Sharpe [CI] | SPY MaxDD | EW ann. | EW MaxDD | EW cost (bps/yr) | 25% EW sleeve ΔlogW vs SPY [CI] |
|---|--:|--:|---|--:|--:|--:|--:|---|
| main (from 2012-01) | 168 | 14.7% | +1.06 [+0.59, +1.61] | -23.9% | 14.1% | -27.1% | 3.8 | -0.024 [-0.129, +0.074] |
| short_window (from 2021-07) | 54 | 12.8% | +0.82 [-0.01, +1.81] | -23.9% | 9.0% | -20.3% | 4.9 | -0.041 [-0.107, +0.017] |

#### Main family — IC (13 BH members)
| signal | sign | sparse | IC mean [95% HAC CI] | NW t | p | BH p | clears IC |
|---|:-:|:-:|---|--:|--:|--:|:-:|
| `mom_12_1` | + |  | +0.0039 [-0.0222, +0.0300] | +0.29 | 0.7703 | 0.9195 | no |
| `mom_6_1` | + |  | +0.0022 [-0.0174, +0.0218] | +0.22 | 0.8259 | 0.9195 | no |
| `reversal_1m` | − |  | +0.0089 [-0.0113, +0.0291] | +0.87 | 0.3865 | 0.9195 | no |
| `dist_52w_high` | + |  | -0.0031 [-0.0305, +0.0242] | -0.22 | 0.8220 | 0.9195 | no |
| `realized_vol_60d` | − |  | -0.0014 [-0.0332, +0.0304] | -0.09 | 0.9319 | 0.9319 | no |
| `beta_252d` | − |  | -0.0157 [-0.0532, +0.0218] | -0.82 | 0.4126 | 0.9195 | no |
| `skew_60d` | − |  | +0.0016 [-0.0146, +0.0178] | +0.19 | 0.8487 | 0.9195 | no |
| `high_minus_low_60d` | − |  | -0.0028 [-0.0268, +0.0211] | -0.23 | 0.8163 | 0.9195 | no |
| `drawdown_60d` | + |  | -0.0092 [-0.0321, +0.0137] | -0.79 | 0.4320 | 0.9195 | no |
| `ma_cross_50_200` | + |  | -0.0029 [-0.0234, +0.0177] | -0.27 | 0.7849 | 0.9195 | no |
| `moving_avg_distance_50d` | + |  | -0.0076 [-0.0283, +0.0131] | -0.72 | 0.4716 | 0.9195 | no |
| `vol_regime_5_60` | − |  | +0.0058 [-0.0060, +0.0175] | +0.96 | 0.3366 | 0.9195 | no |
| `overnight_intraday_v1` | + |  | -0.0144 [-0.0303, +0.0015] | -1.77 | 0.0759 | 0.9195 | no |

#### Main family — wealth leg (Arm L, 25% satellite)
| signal | Arm L ann. | Sharpe [95% CI] | Sortino ci_low | MaxDD | ΔlogW vs SPY [CI] | ΔlogW vs EW [CI] | both > 0 | H1 |
|---|--:|---|--:|--:|---|---|:-:|:-:|
| `mom_12_1` | 15.0% | +0.95 [+0.53, +1.38] | +0.74 | -20.6% | +0.009 [-0.138, +0.109] | +0.033 [-0.104, +0.138] | no | no |
| `mom_6_1` | 15.9% | +0.92 [+0.48, +1.38] | +0.62 | -27.1% | +0.036 [-0.121, +0.196] | +0.060 [-0.052, +0.173] | no | no |
| `reversal_1m` | 12.7% | +0.57 [+0.19, +1.05] | +0.26 | -39.6% | -0.101 [-0.276, +0.107] | -0.077 [-0.207, +0.077] | no | no |
| `dist_52w_high` | 10.7% | +0.88 [+0.46, +1.34] | +0.63 | -19.7% | -0.121 [-0.265, -0.006] | -0.097 [-0.243, +0.031] | no | no |
| `realized_vol_60d` | 13.5% | +1.17 [+0.76, +1.63] | +1.06 | -18.4% | -0.020 [-0.189, +0.135] | +0.004 [-0.165, +0.169] | no | no |
| `beta_252d` | 11.3% | +0.96 [+0.53, +1.41] | +0.82 | -17.8% | -0.087 [-0.306, +0.102] | -0.063 [-0.276, +0.126] | no | no |
| `skew_60d` | 12.6% | +0.79 [+0.40, +1.27] | +0.59 | -27.0% | -0.074 [-0.209, +0.065] | -0.050 [-0.141, +0.056] | no | no |
| `high_minus_low_60d` | 13.8% | +1.14 [+0.73, +1.61] | +1.11 | -17.5% | -0.013 [-0.151, +0.119] | +0.011 [-0.113, +0.127] | no | no |
| `drawdown_60d` | 10.8% | +0.88 [+0.39, +1.39] | +0.59 | -21.0% | -0.121 [-0.243, -0.008] | -0.097 [-0.227, +0.022] | no | no |
| `ma_cross_50_200` | 15.4% | +1.00 [+0.56, +1.44] | +0.86 | -20.3% | +0.027 [-0.127, +0.151] | +0.051 [-0.074, +0.155] | no | no |
| `moving_avg_distance_50d` | 13.8% | +0.94 [+0.45, +1.47] | +0.62 | -26.6% | -0.025 [-0.164, +0.095] | -0.001 [-0.137, +0.131] | no | no |
| `vol_regime_5_60` | 13.9% | +0.85 [+0.43, +1.41] | +0.58 | -27.6% | -0.031 [-0.172, +0.118] | -0.008 [-0.082, +0.076] | no | no |
| `overnight_intraday_v1` | 10.6% | +0.82 [+0.42, +1.35] | +0.58 | -21.2% | -0.130 [-0.254, -0.016] | -0.106 [-0.227, +0.009] | no | no |

#### Calendar family (daily dummy regression)
| feature | days | NW lags | slope, bps/day per unit [95% HAC CI] | NW t | p | BH p | clears |
|---|--:|--:|---|--:|--:|--:|:-:|
| `sell_in_may_halloween` | 3519 | 8 | +2.00 [-4.82, +8.83] | +0.58 | 0.5652 | 0.7568 | no |
| `january_effect` | 3519 | 8 | +6.28 [-20.73, +33.28] | +0.46 | 0.6487 | 0.7568 | no |
| `triple_witching_premium` | 3519 | 8 | -9.64 [-37.55, +18.26] | -0.68 | 0.4981 | 0.7568 | no |
| `tax_loss_season` | 3519 | 8 | +12.66 [-0.98, +26.30] | +1.82 | 0.0688 | 0.4819 | no |
| `month_of_year_dummy` | 3519 | 8 | +0.16 [-0.84, +1.16] | +0.31 | 0.7592 | 0.7592 | no |
| `weekday_dummy` | 3519 | 8 | -1.02 [-3.83, +1.79] | -0.71 | 0.4781 | 0.7568 | no |
| `days_to_quarter_end` | 3519 | 8 | +0.09 [-0.05, +0.23] | +1.31 | 0.1901 | 0.6654 | no |

**H1:** {"met": false, "signals_meeting": [], "ew_tilt_not_signal": [], "n_trials_consumed": 4}  
**families:** {"main": {"m": 13, "n_clear_ic": 0}, "short_window": {"m": 6, "n_clear_ic": 0}, "calendar": {"m": 7, "n_clear": 0}}  
**canonical md5:** `bbf88ffc9f23bde015e03b5361b09dd4`

**H1:** {"met": false, "signals_meeting": [], "ew_tilt_not_signal": [], "n_trials_consumed": 4}  
**families:** {"main": {"m": 13, "n_clear_ic": 0}, "short_window": {"m": 6, "n_clear_ic": 0}, "calendar": {"m": 7, "n_clear": 0}}  
**canonical md5:** `bbf88ffc9f23bde015e03b5361b09dd4`

## 8. Properties of the measurement (stated; no action taken)

1. **Substrate: total return on both legs, not price-only as §7 says.** The `data/processed`
   closes are dividend-adjusted: SPY 1993-01-29 is 24.18 against a ~43.9 nominal close. **The
   §7 TR-reconciled SPY twin coincides with the main leg:** across 250 months, 2005-03 →
   2025-12, `processed` and `tr_reconciled` SPY monthly returns correlate at 1.000000 with a mean
   difference of 0.0 bps/yr. `tr_reconciled` starts in 2005-02, so it could not cover 2000–2004
   anyway.
2. **Survivorship and the EW premium.** The EW sleeve beats SPY over 2000–2025 (+0.232 [+0.052,
   +0.422]) but not over 2012–2025 (−0.024 [−0.129, +0.074]). Ruling 2 (clear BOTH benchmarks)
   is what keeps that tilt from reading as signal.
3. **The SimFin edges emit a basket-transition shape:** 1.0 on entry, 0.3 while held, 0
   otherwise. Arm L is the whole top-quintile basket. Spearman IC also ranks entries above held
   names, so the IC is partly an entry-versus-hold measure. The state starts empty at 2021-07,
   so the first month emits the whole basket as entries.
4. **SimFin FREE filings thin out after publish 2025-Q2.** Late-2025 fundamentals are up to two
   quarters stale. This introduces no look-ahead.
5. **Before 2018, `january_effect` counts Jan 1 as a trading day**, so it flags 4 trading days
   instead of 5. Its slope is verified at ≈ 0 (§2).
6. **Tie groups:** under the tie-preserving decile rule (§11.4 item 4), the top leg exceeded 15%
   of names in 56 months for `drawdown_60d` and 19 months for `dist_52w_high`. The first-cut
   average-rank rule would have emptied the top decile in some of those months and silently
   substituted the EW sleeve.
7. **Missing values:** 361 + 7 forward returns are NaN (0.34%). They are reported and never
   filled. 112 names exit at a delisting proxy.
8. **Costs:** main-family Arm L costs between 15 bps/yr (`beta_252d`) and ≈ 105 bps/yr
   (`vol_regime_5_60`, `reversal_1m`); the short-window edges cost 8–31 bps/yr. The 75/25 satellite rebalance is costless on both sides of every comparison.

> **Record qualification, 2026-10-15 (director, from R's cache-guard design read `docs/Audit/price_cache_convention_guard_design_read_agent_r_2026_10_15.md` §3.4):** "total return on both legs" is exact only AFTER each file's merge seam (2018-01-02 for most names, 2020-04-09 for 108); pre-seam history is price-only plus T-082b's smooth constant-yield drip (`apply_dividend_strip`, `exp(a + b·t)`), approximately total return in level. Both legs, both benchmarks and the EW sleeve read the same files, and within-month ex-date timing is second-order for a monthly construction, so the outcome is unaffected. No number in this document changes.

> **Record note, 2026-10-15 (director, from B's item-(d) measurement):** one name in the PIT universe, DAL, is two securities stitched under one ticker — the old Delta (equity cancelled in the 2005–07 bankruptcy) and the new Delta (listed 2007-05) — with 6,034 pre-2005 bars above 1,000 that the loader's `÷10` auto-scale half-masked on every load. **Correction, same day (B's membership check): this panel NEVER carried pre-2007 DAL.** The PIT membership (`data/universe/sp500_membership_pit.parquet`) lists DAL only from 2013-09-11, when the new Delta joined the S&P 500; the panel masks membership per month-end, and from 2013-09 its lookbacks reach only post-2007 bars, which are clean. The outcome is UNAFFECTED — not 'unaffected materially'. The corrupt bars can reach a measurement only through a consumer that loads full histories without the per-date mask (a PIT-mask fallback, a cache-wide universe from `discover_cached_tickers`, research scripts reading data/processed directly); the declared bar-level exclusion at the loader closes all three. No number in this document changes.


## 9. Honest N and minimum backtest length

- **N_trials +4 consumed** (main L, main LS, short window, calendar), as ruled 2026-10-01.
  Recording it in the run registry is the director's call: the harness writes nothing there.
- A refutation needs no MBL clearance. A positive on the short window (4.5 years) could only have
  nominated (§5.2). At N_eff ≈ 37, a 26-year window needs SR ≥ 0.42 (`[NN-MBL]`); no signal
  reached the IC bar that a wealth claim would have needed first.

## 10. What this does NOT mean (§6, verbatim, plus the inventory)

> **Not** a verdict on macro timing (§3.1), fundamentals over a long window (§5.2), or calendar
> effects beyond §5.3.

It also says nothing about the signals that are UNTESTED by B-1 (§3). It is not a statement
that these anomalies are absent from the market: it covers this universe (PIT S&P 500 members
with a local price file), this construction (deciles, equal weight, monthly, long-only Arm L at
25%), these costs and this period. The substrate is survivor-biased upward, so the bias could
only have helped a signal clear.

## 11. What follows (facts, for the director; nothing is decided here)

- The alpha-frontier review (2026-09-30) demoted T-196's "0/35 cleared" to UNTESTED, because it
  ran under the RR-1 sizing defect with a Gate 4 that had no power, and named B-1 the decisive
  re-test. **On the literature's construction, outside `BacktestController`, the cross-sectional
  price vocabulary clears nothing.**
- Nothing is deployed and nothing goes to Gate 1′.
- Queued separately, not B-1's: extending the foundry's calendar tables to 2000 (propose-first;
  that would make the three excluded features testable), and the separate macro-timing brief.

## 12. Reproduce

```bash
cd <agent-a worktree>   # the builder and harness refuse any other cwd (exit 5)
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE
# the panel (×2; canonical md5 d9d449d17f8f102614b34079e8f1bd60 both times)
python -m scripts.build_signal_panel_b1 --start 2000-01 --end 2025-12 --out data/research/b1/full_2a/
python -m scripts.build_signal_panel_b1 --start 2000-01 --end 2025-12 --out data/research/b1/full_2b/
# the harness (×2; canonical md5 5de36b89e0ade6eac008667e035d2d03), then the 2012 window
P=data/research/b1/full_2a/signal_panel_d9d449d17f8f.parquet
python -m scripts.raw_signal_decile_b1 --panel $P --out data/research/b1/run1/ --seed 0 --boot-iter 1000 --boot-block-months 6
python -m scripts.raw_signal_decile_b1 --panel $P --out data/research/b1/run2/ --seed 0 --boot-iter 1000 --boot-block-months 6
python -m scripts.raw_signal_decile_b1 --panel $P --out data/research/b1/run_2012/ --start 2012-01
python -m pytest tests/test_build_signal_panel_b1.py tests/test_raw_signal_decile_b1.py -q   # 46 pass
```

The data under `data/research/b1/` is gitignored, so the tables above are the durable copy.
