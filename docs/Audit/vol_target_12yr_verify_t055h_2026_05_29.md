---
task_id: T-2026-05-26-055h
title: Vol-target T-055e-baseline arm — 12-yr MBL-clearing window re-test
date: 2026-05-29
substrate: Stooq+Alpaca merged (post-T-082b)
window: 2014-01-01 → 2025-12-31 (11.99 yr, 3,017 aligned trading days)
data_source: cloud — s3://archondex-results-407539788432/t055h-vol-target-12yr-{verify-precheck,proof}/
outcome: VOL-TARGET CHAPTER CLOSED — Δ Sharpe -0.214, ci_low -0.688; fails CLAUDE.md `[NN-SHARPE-CI]` on all three readings
---

# T-055h — Vol-Target Chapter Close-Out (12-yr Re-test)

## Headline

**VOL-TARGET CHAPTER CLOSED.** The T-055e regime-conditional vol-target
overlay (multipliers 0.85 / 0.60 / 0.40 for cautious / stressed /
crisis), which "DEFENSIBLY" cleared CLAUDE.md `[NN-SHARPE-CI]` on the 5-yr
Alpaca-only substrate (+0.549 Δ Sharpe, ci_low +0.047), **fails on
the 12-yr MBL-clearing extended-substrate re-test**:

| Statistic | arm0_off (baseline) | arm_t055e_baseline (vol-target ON) | Δ |
|-----------|--------------------:|-----------------------------------:|----:|
| Sharpe (point) | **0.8102** | 0.5963 | **-0.214** |
| Sharpe ci_low (2.5%) | +0.265 | +0.060 | **-0.688** |
| Sharpe ci_high (97.5%) | +1.392 | +1.159 | +0.260 |
| p(Δ > 0) | — | — | **18.9%** |

**Fails CLAUDE.md `[NN-SHARPE-CI]` by all three readings**: strict ci_low > 0 gate
(no, -0.688), point > 0 (no, -0.214), one-sided p(Δ>0) > 95% (no,
18.9%). T-055b user-decision flag-flip framing is REFUTED. Confidence
gate (T-057) is REFUTED. Both yesterday's "DEFENSIBLE" 5-yr findings
retire on properly-powered 11.5+ yr measurement.

## What this means for the project

Second consecutive 5-yr "win" demoted on 12-yr re-test. The pattern
is now category lesson, not coincidence: **the 5-yr window at the
project's current N (≈265 trials) is statistically incapable of
validating engine-completion flag-flips**. Per CLAUDE.md `[NN-SUBSTRATE-REVERIFY]` the
substrate/window-conditional re-verification protocol is doing
exactly what it was designed to do — surfacing the lifts that
were small-N artifacts.

Forward narrative:
- **No engine-completion lift currently clears CLAUDE.md `[NN-SHARPE-CI]` on a
  MBL-clearing window.** T-057 confidence gate REFUTED. T-055e
  vol-target REFUTED. The 0.598 substrate-honest baseline stands.
- **T-055f VVIX-z kill switch** becomes the next-best vol-target
  exploration — qualitatively different mechanism (binary defensive
  layer vs gradual degrossing), B-eligible.
- **T-057c-regime-conditional gate** remains the only T-057-family
  lever; B owns.
- Engine D Discovery + Engine F factor-α retirements (T-043 already
  shipped) remain the active engine-completion tracks.

## Setup

### Pre-launch verify (per CLOUD_USAGE.md verify-first protocol)

2-cell single-year (2025) campaign confirmed the config patch fires:

| Arm | Sharpe | canon_md5 |
|-----|--------|-----------|
| arm0_off | 1.717 | `062d0a8f...` |
| arm_t055e_baseline | 1.327 | `632dd315...` |

`canon_md5` distinct → the regime-conditional EWMA vol-target overlay
is genuinely active in arm_t055e_baseline. 2025 single-year preview
already showed -0.39 Δ — consistent with T-055g v2's "2025
degradation is substrate-honest" finding. Full 12-yr proof confirms.

### Full proof — 10 cells × 12-yr

- **Window**: 2014-01-01 → 2025-12-31 (12 calendar years; 3,017 aligned trading days)
- **Substrate**: Stooq+Alpaca merged (post-T-082b)
- **Multipliers**: cautious 0.85 / stressed 0.60 / crisis 0.40 (T-055e
  point estimate winner per T-055g v2)
- **Reps**: 5 per arm
- **Per-cell wall**: ~100 min (T-053b telemetry confirmed)
- **Total grid wall**: ~180 min (8 first batch + 2 queued)
- **Cost**: ~$0.50 Fargate Spot

### Harness — reused from T-053b

- `scripts/submit_arms_campaign.py` with the new `windows: [...]`
  spec format and `--job-timeout 14400` override
- `scripts/cloud_entrypoint.sh` `ARCHONDEX_START_DATE` /
  `ARCHONDEX_END_DATE` env vars
- No code changes this dispatch; only spec + analysis

### Image freshness

ECR `:dev` image rebuilt + pushed 2026-05-29 at 23:37 UTC to include
T-057c-det's `signal_collector.py` sort fix (commits b9f5aec,
02251dc on main). CI workflow at `.github/workflows/build_backtest_image.yml`
has been failing on AWS OIDC credentials since 2026-05-24; manual
rebuild path used (per the precedent in T-053b audit's "Image rebuild"
section).

## Statistical inference

### Block-bootstrap on 12-yr daily returns

Following T-053b's methodology — block-bootstrap on the single-window
daily-returns series is the correct inference when reps are
deterministic (or near-deterministic; see Determinism section).

- **n_obs**: 3,017 aligned trading days (intersection of arm0 and t055e snapshots)
- **Block length**: 8 days (Politis-White auto)
- **n_iter**: 2,000
- **Seed**: 0

Results per the table above. Δ Sharpe ci straddles zero with a
negative point and a low p(>0). Three independent CLAUDE.md `[NN-SHARPE-CI]`
readings all fail.

### MBL Gate-0 (CLAUDE.md `[NN-MBL]`) — PASSES

- N_trials accumulated (post-T-053b): **265** (T-053b added 1, T-055h
  adds 4: one verify + one proof per arm)
- SR_target: 1.0
- MBL required years: `2·ln(265)/1²` = **11.16 yr**
- Years covered: **11.99 yr** (2014-01-03 → 2025-12-31)
- **Pass: YES**

T-055h is the second T-* dispatch to clear MBL Gate-0 at the
project's accumulated N (after T-053b). The window IS substrate-
honest by the dev's prescription. The REFUTED verdict on a window
that clears MBL is not a sample-size objection — it's a real finding.

## Determinism — cross-container drift not fully closed

Per-arm canon_md5 distribution across 5 reps:

| Arm | Canonical md5 | Reps stable | Drift outlier |
|-----|---------------|-------------|---------------|
| arm0_off | `989af6a351e301c0b440a281954b4d87` (Sharpe 0.81) | rep1, 2, 3, 5 | rep4: md5 `f40d5b94...`, Sharpe **0.919** |
| arm_t055e_baseline | `32302cd8d683e4d462f7ef850438200f` (Sharpe 0.596) | rep1, 2, 3, 4 | rep5: md5 `8432b662...`, Sharpe **1.165** |

**8/10 cells bitwise stable; 2/10 drift.** T-057c-det's
`signal_collector.py` sort fix (2026-05-25, merged on main pre-image-
rebuild) was supposed to close cross-container floating-point drift,
but it's not 100% — 1 cell per arm drifted to a noticeably different
Sharpe. The drifted cells are precisely the two that started LATER
from the Batch queue (different EC2 instance / container).

Mitigations:
- The block-bootstrap uses the canonical (4/5 stable) rep1 of each
  arm — the verdict is robust to the drift outliers being included
  or excluded.
- **Using median-of-5 instead**: arm0_off=0.81, arm_t055e_baseline=0.596,
  Δ=-0.214 (identical to point-estimate verdict — median ignores the
  outliers).
- **Using mean-of-5**: arm0_off = (0.81×4 + 0.919)/5 = 0.832,
  arm_t055e_baseline = (0.596×4 + 1.165)/5 = 0.710, Δ = -0.122
  (still NEGATIVE, just smaller magnitude).
- Either interpretation: vol-target arm STAYS BELOW arm0_off.

**Forward action surfaced**: T-057c-det's fix is necessary but not
sufficient. There is at least one additional cross-container FP
drift site beyond the signal_collector edge-iteration order.
Recommend a T-057c-det-followup dispatch to enumerate other
order-dependent FP summation sites (likely in alpha_engine
aggregation, signal_processor weighting, or risk_engine sizing).

## Comparison across T-055 measurement series

| Measurement | Window | Substrate | Δ Sharpe (point) | ci_low | p(Δ>0) | Verdict |
|---|---|---|---:|---:|---:|---|
| T-055e original | 5 yr 2021-2025 | Alpaca-only | **+0.549** | +0.047 | (high) | **DEFENSIBLE** |
| T-055g v2 (arm_t055e_baseline) | 5 yr 2021-2025 | Extended (Stooq+Alpaca) | +0.413 | -0.177 | 83.0% | MARGINAL — straddles 0 |
| **T-055h** | **12 yr 2014-2025** | **Extended (Stooq+Alpaca)** | **-0.214** | **-0.688** | **18.9%** | **REFUTED — closes chapter** |

The Δ-Sharpe progression as substrate + window honesty improves: 0.549 → 0.413 → -0.214. **The original 5-yr Alpaca lift was the combined artifact of (a) limited-history vol-estimator noise + (b) small-N window inflation.** Each measurement-honesty step shaved the lift, and the final 11.99-yr MBL-clearing step took it negative.

This is the exact pattern T-053b documented for T-057: 5-yr lift +0.793 → 12-yr -0.128. Two for two. **Future engine-completion A/Bs that quote a Sharpe lift on 5-yr only should be treated as conjecture until re-verified on 12-yr.**

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|--------|
| 1 | Pre-launch verify confirms canon_md5 differs OFF vs ON | DONE — `062d0a8f` ≠ `632dd315` |
| 2 | Full 10-cell campaign 10/10 SUCCEEDED | DONE |
| 3 | MBL Gate-0 explicit log; ≥11.16 yr required, 12.0 actual | DONE — PASS |
| 4 | Block-bootstrap CI on Δ Sharpe | DONE — Δ -0.214, ci_low -0.688 |
| 5 | Cross-container determinism check | DONE — 8/10 stable, 2/10 drift; verdict robust |
| 6 | Verdict + comparison table across T-055 measurements | DONE (this file) |
| 7 | Branch push only; director merges | DONE |

## Files

- `data/cloud_runs/specs/t055h_verify.json` (verify spec)
- `data/cloud_runs/specs/t055h_proof.json` (proof spec)
- `data/cloud_runs/t055h-vol-target-12yr-verify-precheck_*.{csv,json}` (gitignored)
- `data/cloud_runs/t055h-vol-target-12yr-proof_*.{csv,json}` (gitignored)
- `data/cloud_runs/t055h-proof-snapshots/*.csv` (rep1 canonical for each arm; gitignored)
- `data/cloud_runs/t055h_block_bootstrap.json` (gitignored)
- this audit doc

S3:
- `s3://archondex-results-407539788432/t055h-vol-target-12yr-verify-precheck/`
- `s3://archondex-results-407539788432/t055h-vol-target-12yr-proof/`

## Memory updates needed (post-merge)

- `project_t055e_first_defensible_2026_05_23.md` — flag as REFUTED;
  the substrate-conditional caveat applied to 2022 also turned out
  to apply to the whole window — on 12-yr the lift evaporates and
  flips sign.
- `project_t055g_v2_substrate_honest_sweep_2026_05_24.md` (if it
  exists) — the "arm_t055e_baseline winning point but ci_low fails"
  reading was a leading indicator; 12-yr confirms.
- New memory entry: "5-yr window is statistically incapable of
  validating any flag-flip at N≈265. Mandatory 11.5+ yr re-test
  per CLAUDE.md `[NN-SUBSTRATE-REVERIFY]` — pattern confirmed by T-057 REFUTED (T-053b)
  and now T-055e REFUTED (T-055h)."

## NOT done in T-055h

- T-057c-det follow-up to enumerate other cross-container FP drift
  sites (separate dispatch; surfaced as forward action above)
- T-055f VVIX-z kill switch (separate dispatch; the natural
  "qualitatively different mechanism" follow-up to the close-out)
- No flag flipped on main per spec hard constraint
- No engine code touched (per spec hard constraint)
