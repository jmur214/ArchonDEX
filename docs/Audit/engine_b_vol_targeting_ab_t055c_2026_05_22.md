# T-2026-05-22-055c — Engine B vol-targeting A/B lift verification

**Date:** 2026-05-22
**Branch:** `feature/engine-b-vol-targeting-ab-t055c`
**Worker:** Agent B
**Spec:** `docs/Measurements/2026-05/spec_engine_b_vol_targeting_2026_05_12.md`
(Acceptance §4-5, deferred from T-055 ship).

## Verdict — MARGINAL

Point estimate **clears** the Moreira-Muir +0.20 upper bound
(+0.256 Sharpe lift, mean over 5 years × 3 reps). Bootstrap ci_low
**crosses zero** (-0.140). Per CLAUDE.md non-negotiable #6 ("kill
thresholds and gating decisions follow ci_low, not point"), this is
the MARGINAL bucket from the dispatch's verdict ladder.

**T-055b flag-flip is NOT yet recommended.** The lift exists in the
point estimate but is dominated by per-year variance — vol-targeting
helps massively in 2 of 5 years (2021 bull +0.915, 2024 fragility
+1.303) and hurts in 2 of 5 (2022 bear -0.129, 2025 vol-shock -0.942).
The wide CI reflects this regime dependency, not noise.

**Recommended follow-up before T-055b**:
- EWMA λ=0.94 estimator (faster vol-up detection) — addresses the
  2025 vol-shock failure mode.
- Regime-conditional target (lower target in ANFCI-stressed or
  HMM-crisis state) — addresses the late-cycle vol-shock trap.
- Both are spec'd in T-055c's "forward look" section.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | 30/30 backtests complete | **PASS** |
| 2 | 3-rep canon md5 invariance within each (year × arm) cell | **PASS** (10/10 cells canon_set_size=1) |
| 3 | Headline table + per-year breakdown | **PASS** — see below |
| 4 | Audit doc with bootstrap CI per cell | **PASS** (this doc + `engine_b_vol_targeting_ab_t055c_2026_05_22.json`) |
| 5 | No production state changes | **PASS** — `risk_settings.prod.json` reverted after each arm |
| 6 | Branch push only; director merges | **PASS** |

## Headline table (5-year × 3-rep mean, bootstrap CI)

| Metric | Arm 0 (OFF) | Arm 1 (ON) | Δ point | Δ ci_low | Δ ci_high |
|---|---|---|---|---|---|
| **Mean Sharpe** | 0.598 [0.192, 1.042] | **0.854 [0.335, 1.449]** | **+0.256** | **-0.140** | **+0.631** |
| Mean CAGR % | 3.14 [1.30, 5.18] | 5.21 [1.29, 9.50] | +2.07 | -0.97 | +5.16 |
| Mean MDD % | -5.56 [-6.53, -4.48] | -6.19 [-7.67, -4.87] | -0.62 | -1.81 | +0.38 |
| n_backtests | 15 | 15 | — | — | — |

Bootstrap: iid resampling of per-(year, rep) means, n=1000 iterations,
2.5%/97.5% quantiles. Smaller-N panel (15 obs/arm) makes block-
bootstrap less informative than iid here; per the project's
MetricsEngine convention, switch to block-bootstrap once the panel
grows.

## Per-year breakdown

| Year | Regime | Arm0 Sharpe | Arm1 Sharpe | Δ Sharpe | Arm0 MDD% | Arm1 MDD% | Δ MDD pp |
|---|---|---|---|---|---|---|---|
| 2021 | bull / calm | 1.791 | **2.706** | **+0.915** | -2.67 | -3.19 | -0.52 |
| 2022 | bear | 0.294 | 0.165 | -0.129 | -8.26 | **-7.00** | **+1.26** |
| 2023 | chop | 1.221 | 1.352 | +0.131 | -3.70 | -6.05 | -2.35 |
| 2024 | fragility | -0.613 | **0.690** | **+1.303** | -5.64 | **-3.40** | **+2.24** |
| 2025 | vol-shock | 0.297 | **-0.645** | **-0.942** | -7.55 | **-11.29** | **-3.74** |
| **Mean** | | **0.598** | **0.854** | **+0.256** | **-5.56** | **-6.19** | **-0.62** |

### Per-year interpretation

- **2021 (bull, calm)**: vol-target levered up (realized vol 5–7 % vs
  target 10 % → scalar pinned near ceiling 2.0). Result: +0.915
  Sharpe lift, but slightly worse drawdown (the leverage amplifies
  small dips into MDD). Classic Moreira-Muir lever-up benefit.

- **2022 (bear)**: vol-target degrossed correctly (realized vol up to
  ~11 % → scalar dropped below 1.0). MDD improved by +1.26pp, but
  Sharpe slipped -0.13 because the policy also clipped some of the
  partial-recovery upside. Net: defensive value > Sharpe cost. This
  matches Harvey et al. 2018's kurtosis-cut + MDD-trim claim.

- **2023 (chop)**: vol-target produced an in-band +0.131 Sharpe lift
  but a -2.35pp MDD deterioration. Vol-target's scalar shifted
  sizing slightly enough that the choppy-year drawdown was widened
  by holding too long through reversals. This is a known failure
  mode in chop regimes.

- **2024 (fragility)**: **the biggest single-year win.** 2024 was
  the documented substrate-fragility year (T-035 corrected -0.613).
  Vol-target rescued it: Sharpe -0.613 → +0.690 = +1.303 lift, AND
  MDD improved by +2.24pp. CAGR flipped from -2.68 % to +3.70 %.
  This is the canonical "vol-target rescues bad year" pattern.

- **2025 (vol-shock)**: **the biggest single-year loss.** Sharpe
  +0.297 → -0.645 (-0.942), MDD -7.55 → -11.29 (-3.74pp WORSE).
  Vol-target was leveraged-up entering a vol expansion event, and
  the 60-day rolling estimator was too slow to degross before
  losses accumulated. This is the EXACT failure mode documented in
  Harvey et al. 2018 § "vol expansion regime" and explains why
  fast-response EWMA estimators are recommended for systems exposed
  to crisis-onset regimes.

### Asymmetric kurtosis observation (qualitative — full kurtosis test deferred)

The strict Harvey-et-al-2018 kurtosis cut from 4.6 → 1.8 was NOT
verified in this campaign because the cockpit metrics pipeline does
not emit per-arm daily-return kurtosis as a first-class number.
Qualitative: the per-year Sharpe distribution for arm1 has
HIGHER spread (range -0.645 to 2.706 = 3.35 wide) than arm0 (range
-0.613 to 1.791 = 2.40 wide). That's NOT the "stabilization" Harvey
et al. predict — actually the opposite. Possible cause: our
6-active-edges substrate is too small (vs the 100-stock factor
portfolios Harvey tested) for the per-year MDD-trim effect to
dominate over the lever-up-then-trap effect.

## Determinism evidence

| Cell (year × arm) | Reps run | Canon md5 unique count | Status |
|---|---|---|---|
| 2021 × Arm 0 | 3 | 1 (`bd9ca4e4…`) | PASS |
| 2022 × Arm 0 | 3 | 1 (`77e6aa5c…`) | PASS |
| 2023 × Arm 0 | 3 | 1 (`b799c652…`) | PASS |
| 2024 × Arm 0 | 3 | 1 (`cfc02811…`) | PASS |
| 2025 × Arm 0 | 3 | 1 (`f566269b…`) | PASS |
| 2021 × Arm 1 | 3 | 1 (`178aad45…`) | PASS |
| 2022 × Arm 1 | 3 | 1 (`e56db542…`) | PASS |
| 2023 × Arm 1 | 3 | 1 (`6016d0cd…`) | PASS |
| 2024 × Arm 1 | 3 | 1 (`34d00b8e…`) | PASS |
| 2025 × Arm 1 | 3 | 1 (`95ac6178…`) | PASS |

10/10 cells pass determinism. **All 5 across-arm canon md5s differ**
(vol-target IS changing orders) — confirms the prod-patch fix
documented below.

## Harness bug discovered + fixed mid-campaign

**Critical**: the initial T-055c campaign run silently failed
because the harness was patching `config/risk_settings.json` while
`orchestration/mode_controller.py:522` actually loads
`config/risk_settings.{env}.json` (here `risk_settings.prod.json`).
The wrong file got patched → ARM_ON ran with vol-target DEFAULT
(disabled) → canon md5 bitwise identical to ARM_OFF for the first
attempt's 4 completed runs.

Caught when the simulator script
`scripts/aggregate_t055c.py` was test-applied against arm0/2022's
portfolio snapshots and computed that the vol-target scalar would
have moved on 191/191 eligible days (range 0.86–2.00, median 1.23)
— meaning the scalar SHOULD have differed materially but didn't.
That inconsistency forced the diagnosis.

Fix: `scripts/run_vol_target_arms_full.py` updated to patch
`config/risk_settings.prod.json` (the env-resolved file). Arm 0 was
retained because arm 0's intent is "vol-target OFF" and both files'
defaults match that. Arm 1 was re-run; this audit reflects the
corrected arm1 results.

The invalid pre-fix arm1 results are archived at
`data/measurements/vol_target_t055c_2026_05_22/arm1_results.invalid-pre-prod-patch-fix.json`
for reference.

**Process lesson**: any future harness that toggles `config/risk_settings.*`
or any other env-suffixed file must patch the env-resolved variant,
not the unsuffixed default. Worth adding to lessons_learned.

## Open questions raised by the result

1. **Why is the Sharpe lift so much larger than Moreira-Muir's
   +0.10-0.20?** Two reasons:
   - Our substrate has only 6 active edges; per-bar realized vol
     ranges from 4 % to 11 % — much wider than Moreira-Muir's
     ~12-15 % factor-portfolio range. The clip to [0.5, 2.0]
     produces aggressive lever-up in the calm tail, which
     dominates the gains.
   - 2024 fragility-year rescue is single-event-driven (+1.303 of
     +0.256 mean lift = 5.1× of the mean signal).

2. **Why does MDD get WORSE on average (-0.62pp)?** Vol-target's
   defensive behavior shows up in 2022 (+1.26pp) and 2024 (+2.24pp).
   But 2021 (-0.52), 2023 (-2.35), and 2025 (-3.74) all show worse
   MDD. The net is -0.62pp. The 2025 vol-shock outlier dominates.

3. **Is the 2025 vol-shock representative?** This is the critical
   question for production deployment. A single year of -3.74pp MDD
   deterioration is uncomfortable. The dispatch's open question §3
   addresses this: a regime-conditional target (lower target in
   stress) is the principled fix.

4. **Should we ship T-055b anyway given the +0.256 point lift?** Per
   CLAUDE.md #6 strict reading: no. The ci_low overlaps 0, so the
   lift is not statistically distinguishable from zero at 95 %.
   Pre-Moreira-Muir-claim follow-ups (EWMA, regime-conditional) are
   the disciplined path.

## Hard constraints — confirmed met

- [x] Vol_target.py + risk_engine.py unchanged. Pure measurement.
- [x] Vol-targeting NOT enabled on main (default `enabled=False`
  preserved; the `risk_settings.prod.json` patch is restored after
  each arm via `vol_target_patch`'s finally clause).
- [x] Engine A / C / D / E / F untouched.
- [x] Bootstrap CI on every Sharpe per CLAUDE.md #6.
- [x] Determinism: 10/10 cells canon-stable across 3 reps.

## Files

- **NEW** `scripts/run_vol_target_arms_full.py` — 30-run harness (with
  the harness-bug fix documented above).
- **NEW** `scripts/aggregate_t055c.py` — headline + per-year + bootstrap
  CI aggregator.
- **NEW** `data/measurements/vol_target_t055c_2026_05_22/arm0_results.json`
  — 15 control-arm results.
- **NEW** `data/measurements/vol_target_t055c_2026_05_22/arm1_results.json`
  — 15 treatment-arm results (after harness-bug fix).
- **ARCHIVED** `data/measurements/vol_target_t055c_2026_05_22/arm1_results.invalid-pre-prod-patch-fix.json`
  — 4 partial runs from the pre-fix run, preserved for traceability.
- **NEW** `docs/Audit/engine_b_vol_targeting_ab_t055c_2026_05_22.json`
  — full aggregation output.
- **NEW** `docs/Audit/engine_b_vol_targeting_ab_t055c_2026_05_22.md`
  (this doc).

## Forward-look — recommended T-055 follow-ups

Per the dispatch's verdict-bucket "MARGINAL" branch:

1. **T-055d**: EWMA λ=0.94 estimator alternative. Faster vol-up
   response should help the 2025 vol-shock failure mode. Same A/B
   harness; new pure-function `compute_realized_vol_ewma` in
   `vol_target.py`. ~3 hr code + 6 hr A/B.

2. **T-055e**: regime-conditional vol target. Lower target (e.g.,
   6 %) when HMM crisis state ≥ 0.6 OR ANFCI z-score > 1.0; default
   10 % otherwise. Couples vol-target to Engine E. ~6 hr code + 6 hr
   A/B.

3. **T-055f**: vol-of-vol kill switch (VVIX z > 3 → flatten). Per
   dispatch open-question §3 forward-look. Binary defensive layer,
   not a sizing knob.

If T-055d (EWMA) confirms a tighter CI with `ci_low > 0`, that's
the canonical Moreira-Muir result and T-055b becomes defensible.

## T-055b flag-flip recommendation

**DO NOT DISPATCH T-055b YET.** Per CLAUDE.md #6: the ci_low(Δ
Sharpe) = -0.140 does NOT clear the 0 threshold required to
distinguish the lift from noise at 95 % confidence. The +0.256
point estimate is encouraging but per-year variance dominates.

Director should review this audit + decide between:
- (a) dispatch T-055d (EWMA) to test whether a faster estimator
  tightens the CI and clears ci_low > 0, OR
- (b) accept marginal evidence + T-055b ship anyway (user-level
  decision per Engine B propose-first discipline; not for me to
  recommend).
