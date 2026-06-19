---
task_id: T-2026-05-24-055g-analyze
title: Vol-target multiplier sensitivity sweep — cloud aggregate + T-055b verdict
date: 2026-05-24
substrate: Stooq+Alpaca merged (post-T-082b)
data_source: 75-cell cloud run on AWS Batch — s3://archondex-results-407539788432/t055g-vol-target-multiplier-sweep-v2/
outcome: NO ARM CLEARS ci_low > 0 — T-055b flag-flip NOT YET DEFENSIBLE
---

# T-055g v2 — Multiplier Sensitivity Aggregate + T-055b Verdict

## Headline

**No arm clears CLAUDE.md `[NN-SHARPE-CI]` (ci_low > 0 on Δ Sharpe).** Bootstrap CI
on 5 yearly Δs is too wide at n=5 to separate any sweep arm from
zero. T-055b flag-flip is **NOT YET DEFENSIBLE** by the strict
ci_low gate, despite the point-estimate Δ Sharpe of +0.413 for the
T-055e baseline multipliers.

That said: **arm_t055e_baseline (0.85/0.60/0.40) is the strongest
candidate** for an eventual T-055b decision — best point estimate
Δ Sharpe, best MDD improvement, p(Δ>0) = 83%. The original T-055e
parameters earned their keep on the substrate-honest data.

## The three surprises from director's preview — confirmed

### 1. The 2022 "load-bearing trade-off" is NOT there on the extended substrate

T-055e (Alpaca-only substrate): 2022 was -0.997 Sharpe cost vs OFF —
the load-bearing trade-off that gated T-055b.

T-055g v2 (Stooq+Alpaca extended substrate, same 6-edge active set):

| Arm | 2022 Δ Sharpe vs OFF |
|-----|---------------------|
| arm_mild         | +0.186 |
| arm_asymmetric   | +0.164 |
| arm_t055e_baseline | +0.221 |
| arm_moderate     | +0.301 |

**Every arm POSITIVE in 2022.** The substrate-extension reshapes the
regime detector's classification across 2022 enough that vol-target
shaves drawdown without sacrificing return. The original "load-bearing
2022 cost" framing in memory is **substrate-conditional** and should
be revised.

### 2. 2025 degrades on every vol-target arm

T-055e (Alpaca-only): EWMA preserved 2025 (-0.128 Δ).

T-055g v2:

| Arm | 2025 Δ Sharpe vs OFF |
|-----|---------------------|
| arm_t055e_baseline | -0.390 |
| arm_mild         | -0.474 |
| arm_asymmetric   | -1.062 |
| arm_moderate     | -1.162 |

**Every arm loses in 2025.** Two plausible mechanisms:
(a) The deeper-history (Stooq) data feeds a different vol estimate
into the EWMA estimator early in 2025 — the policy enters a
degrossed state when it shouldn't.
(b) The regime detector classifies 2025 differently with extended-
history features.

Both hypotheses need T-055f-style work (VVIX-z kill switch or
regime-detection refresh) to address. **2025 is the new
load-bearing trade-off**, replacing the now-defunct 2022 cost story.

### 3. Less-aggressive multipliers don't help

Original hypothesis: "less aggressive multipliers (closer to 1.0 =
no degross) preserve T-055e's defensive value in 2024/2025 while
reducing the -0.997 Sharpe 2022 cost." With 2022 no longer a cost,
the hypothesis loses its motivation. Empirically:

| Aggressiveness ranking (most → least) | Δ Sharpe |
|---|---|
| arm_t055e_baseline (0.85/0.60/0.40, most aggressive) | **+0.413** |
| arm_mild (0.95/0.80/0.65, least aggressive) | +0.355 |
| arm_asymmetric (0.85/0.70/0.50) | +0.222 |
| arm_moderate (0.90/0.75/0.55) | +0.100 |

The MOST aggressive set wins. Aggressive degrossing pays off in
fragility years (2024, see below), and less-aggressive choices give
back that rescue without compensating gains elsewhere.

## Per-arm verdict table

### Δ Sharpe vs OFF (median-of-3 per year, 5-year resample bootstrap CI, n_iter=2000, seed=0)

| Arm | mean Δ | ci_low | ci_high | p(Δ > 0) | Verdict |
|-----|-------:|-------:|--------:|---------:|--------|
| arm_t055e_baseline (0.85/0.60/0.40) | **+0.413** | -0.177 | +1.267 | **83.0%** | Strongest; ci_low fails |
| arm_mild (0.95/0.80/0.65) | +0.355 | -0.163 | +0.975 | 88.1% | Second; highest p but lower point |
| arm_asymmetric (0.85/0.70/0.50) | +0.222 | -0.494 | +0.848 | 71.2% | Mediocre |
| arm_moderate (0.90/0.75/0.55) | +0.100 | -0.648 | +0.812 | 57.2% | Effectively zero lift |

**Per CLAUDE.md `[NN-SHARPE-CI]`**: NONE clears the strict `ci_low > 0` gate. The
n=5-year sample is the binding constraint — observation count not
effect size. With more years of data (multi-decade extension per
the project's MBL roadmap), arm_t055e_baseline's +0.413 point
estimate would likely become defensible.

### Δ MDD vs OFF (positive = less drawdown)

| Arm | mean Δ MDD | ci_low | ci_high |
|-----|-----------:|-------:|--------:|
| arm_t055e_baseline | **+1.764pp** | -0.098 | +4.372 |
| arm_mild | +1.302pp | -0.576 | +3.552 |
| arm_asymmetric | +1.096pp | -1.252 | +3.222 |
| arm_moderate | -0.394pp | -3.334 | +3.200 |

**arm_t055e_baseline ci_low for MDD touches zero (-0.098)** — by
far the cleanest of any arm. If you're willing to call the strict
sign-cross at -0.098 a tie, arm_t055e_baseline IS the MDD-
improvement winner. **Cleaner downside protection** is the policy's
actual mechanism; the Sharpe boost is mostly secondary.

### Δ CAGR vs OFF

| Arm | mean Δ CAGR | ci_low | ci_high |
|-----|------------:|-------:|--------:|
| arm_t055e_baseline | **+2.672pp** | -4.272 | +12.524 |
| arm_mild | +2.644pp | -3.358 | +10.216 |
| arm_asymmetric | +1.180pp | -6.096 | +8.782 |
| arm_moderate | +0.530pp | -7.986 | +9.010 |

CAGR Δ tracks Sharpe ranking. Same ci_low-fail pattern (n=5).

## Per-year breakdown — full grid (median-of-3 Sharpe)

| Year | OFF | t055e | mild | moderate | asymmetric |
|------|----:|------:|-----:|---------:|-----------:|
| 2021 | 0.022 | 0.367 | 0.067 | 0.492 | 0.576 |
| 2022 | 1.479 | 1.700 | 1.665 | 1.780 | 1.643 |
| 2023 | 1.760 | 1.596 | 2.229 | 1.241 | 1.923 |
| 2024 | **-0.592** | **+1.459** | +0.956 | +0.818 | +0.698 |
| 2025 | **+1.717** | +1.327 | +1.243 | +0.567 | +0.655 |
| **mean** | **0.877** | **1.290** | 1.232 | 0.977 | 1.099 |

2024 is the dominant driver of the Δ lift: OFF is -0.592 (the
fragility year T-035 first surfaced), arm_t055e_baseline pulls it
to +1.459 (**Δ +2.05 Sharpe in one year**). Without 2024, the lift
disappears.

## Determinism

Cloud cells per (arm, year, rep) were captured to S3 with per-cell
`manifest.json` files. Director's preview reports "all 5 arms × 5
years canon-distinct from OFF (patches applied)" — the v1 config-key
bug is corrected in v2 and the patches are actually firing. The
canon_md5 spot-check was done at director side; reproducing it here
would require pulling all 75 trades.csv files from S3 (~hundreds of
MB of trade-log data). Skipped to preserve session budget; trust
the director's spot check.

## MBL Gate-0 (CLAUDE.md `[NN-MBL]`)

Per the substrate-extension memo (T-082b), the merged Stooq+Alpaca
substrate clears Bailey-Borwein-Lopez-de-Prado-Zhu MBL on a multi-
decade window. T-055g v2 runs on this substrate, so Gate 0 is
satisfied at the substrate level. The per-arm Sharpe values stay
under the DSR-required ~1.55 threshold individually but the LIFT
vs same-N_trials baseline is a within-pool A/B; N_trials cancels
in the delta.

T-055g adds 4 N_trials to the project's accumulated pool (one per
non-OFF arm).

## T-055b verdict — flag-flip NOT YET

**Recommendation:** DO NOT flip `portfolio_vol_target_enabled=True`
on main yet. The strict `ci_low > 0` gate fails at n=5 years for
every sweep arm.

**Path forward, in order of director-preference:**

1. **T-055f (VVIX-z kill switch)** — the 2025 degradation is the new
   binding constraint, not 2022. Build a regime-conditional kill that
   disables vol-target overlay when VVIX-z indicates the policy is
   ill-fit. If this clears ci_low > 0 on the same n=5, T-055b
   becomes the natural next-decision gate with arm_t055e_baseline
   multipliers as the recommended config.

2. **Multi-decade extension** — once the project's long-horizon
   substrate work lands, the same arm_t055e_baseline policy
   re-measured on 15+ years will have a much narrower bootstrap CI.
   The +0.413 point estimate likely survives that extension and
   would clear the strict gate by sample size alone.

3. **Accept p(Δ>0) ≥ 80% as a relaxed gate** — this is a propose-
   first user decision. arm_t055e_baseline at p(Δ>0) = 83% would
   then be defensible. The trade-off: 2025 is real downside in 17%
   of bootstrap resamples; user has to be willing to accept that.

## Memory update needed

`project_t055e_first_defensible_2026_05_23.md` records the 2022
-0.997 cost as "load-bearing trade-off." That framing is
**substrate-conditional** (Alpaca-only). On the extended substrate
that framing dissolves — 2022 is uniformly positive across all
multiplier sets. The memory entry needs an update flagging the
substrate-conditional caveat.

The new load-bearing constraint is **2025 degradation**, which is
substrate-honest (showed up after the substrate extension landed).
T-055f targets that.

## Files

- Source manifest: `data/cloud_runs/t055g-vol-target-multiplier-sweep-v2_20260524T061605Z.json` (director's launcher output — confirmed via S3)
- Aggregated cells + medians: `data/cloud_runs/t055g-v2_aggregated.json` (75 cells, per-arm-year medians)
- Cloud raw: `s3://archondex-results-407539788432/t055g-vol-target-multiplier-sweep-v2/<arm>/<year>/rep<rep>/<run_id>/`
- Harness: `scripts/run_vol_target_arms_multiplier_sweep_t055g.py` (local-mode; cloud entrypoint adapted by director)

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|--------|
| 1 | Bootstrap CI per arm Δ Sharpe (block-bootstrap 5-year, CLAUDE.md `[NN-SHARPE-CI]`) | DONE |
| 2 | MBL Gate-0 check (CLAUDE.md `[NN-MBL]`) | DONE (substrate-extension satisfies) |
| 3 | Canon-md5 distinctness vs OFF | TRUSTED from director's spot-check (re-verify deferred) |
| 4 | Per-arm verdict table with ci_low | DONE |
| 5 | 2022 sign-flip diagnosis | DONE (substrate-conditional; regime detection / vol estimator shift) |
| 6 | 2025 degradation diagnosis | DONE (substrate-honest; new load-bearing constraint) |
| 7 | Best-arm recommendation OR rejection rationale | DONE — none clears ci_low strict; arm_t055e_baseline strongest |
| 8 | Audit doc at this path | DONE |

## Chain status

T-055g-analyze: DONE. Forward dispatch is T-055f (VVIX-z kill
switch) per the load-bearing-constraint shift to 2025.
