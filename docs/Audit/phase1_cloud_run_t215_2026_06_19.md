---
task_id: T-2026-06-18-215
title: Phase-1 canonical cloud run — the first honest beat-the-robo verdict (matched A/B, PIT × realistic-cost, full-cycle)
date: 2026-06-19
author: Agent D (substrate + cloud lane)
type: cloud measurement — build + pre-registration + execution
status: RUNNING — image built (CI), pre-flight VALIDATED (N=3 determinism), canonical A/B LIVE on Batch (verdict pending ~9-18h)
outcome: >
  The matched A/B (base vs Phase-1 composition) is fully prepared and pre-registered;
  D owns build + pre-flight + submit. Image built off main @ 9bec2f7 (carries T-211
  composition, T-207 PIT, T-210 realistic-cost, T-219 PIT-accurate cap cache, simfin/
  macro/membership baked). Found + fixed a SECOND fail-open of the same class as the
  T-215 prep one: the realistic-cost cap join (market_cap_tiers.json) was added to the
  manifest + Dockerfile COPY but the build STAGING (build_backtest_image.sh) never
  mirrored it → manifest verify FAILED at build time. Without the fix the only way past
  the verify would be to drop the file → empty cap cache → realistic_retail_costs
  silently inert (the prep fail-open, one layer down).
---

# T-215 — Phase-1 canonical cloud run

## 1. What this run is
The first honest, full-cycle, decision-grade **beat-the-robo** measurement on the
**live lever** (the Phase-1 composition C/T-211 built). A MATCHED A/B, BOTH arms FRESH
and concurrent, SAME substrate / window / seed / cost:

- **arm0_base** — `phase1_composition_enabled=false`, allocator `mean_variance`.
- **arm1_composition** — `phase1_composition_enabled=true`, `phase1_trend_lookback_days=105`
  (EW SPY/AGG/GLD 5-mo long/flat, E/T-204), `phase1_quality_haircut=0.5` (defensive
  tilt + high-IVOL exclusion, A/T-205), `position_buffering_enabled=true` (T-148 lower
  turnover), allocator `mean_variance`. **Vol-target EXCLUDED** (Engine B, separate lever).

Both arms run on **PIT survivor-bias-free universe (T-207/T-180-v2) × realistic-retail
cost (T-210, with the T-219 PIT-accurate cap cache)**, after-tax **Roth**, over the
**full cycle 2000-01-01 → 2025-12-31** (crisis-inclusive: dotcom + GFC + COVID + 2022 —
so the overlay's bull-market chop pays for its crisis protection; the recent window
flatters a defensive overlay, this is the real test). **N≥3 reps/arm** (cross-task
bitwise determinism — the composition multiply adds FP ops, T-057c).

## 2. Image provenance — built off main @ 9bec2f7
`scripts/build_backtest_image.sh 9bec2f7` (registry-direct, ARM64). Carries:
- **T-211** `engines/engine_c_portfolio/phase1_composition.py` (verified present on the branch).
- **T-207** PIT universe hook + **T-180-v2** membership panel (baked, manifest-pinned).
- **T-210** `realistic_retail_costs` + **T-219** PIT-accurate cap cache
  (`market_cap_tiers.json`, 458 entries / 438 resolved incl. 138 delist-shares PIT caps).
- simfin (T-180), macro VIX/FRED (T-164), full SPY (T-167) baked; measured-mode
  (`ARCHONDEX_MEASURED=1`) loader-HALT (T-189/T-194); census (T-181); cov-pin (T-140-fu3);
  BLAS threads pinned to 1 (OMP/OPENBLAS/MKL) for FP determinism.

## 3. Two fail-opens of the same class — both closed
The recurring "missing required input → silently degrade to a plausible-but-wrong path"
disease (CLAUDE.md `[NN-FAIL-CLOSED]`), caught twice on the realistic-cost cap join:
1. **T-215 prep (cloud-time):** `market_cap_tiers.json` was not baked/pinned → empty cap
   cache on the cloud → every ticker ADV-falls-back → `realistic_retail_costs` INERT.
   Closed by baking + manifest-pinning.
2. **T-215 run (build-time, THIS task):** the file was in the manifest + Dockerfile COPY
   but `build_backtest_image.sh` staging never mirrored it → manifest verify FAILED
   (`MISSING data/universe/market_cap_tiers.json`), blocking the build. The only "fix"
   that gets past verify without staging the file is to drop it from the manifest →
   back to fail-open #1. Closed by adding the staging rsync (commit on this branch). The
   staging set MUST match `SUBSTRATE_FILES` + the Dockerfile COPYs.

## 4. PRE-REGISTRATION (written before the run; N_trials += 1)
- **Hypothesis H1:** the Phase-1 composition clears `evaluate_deploy_readiness`
  (account='roth', after-tax, w_dbmf=0) vs BOTH robo proxies (60/40 + schwab_like) —
  `ci_low(Sharpe_comp) > ci_low(Sharpe_robo)` OR **≥20% shallower full-cycle MaxDD**
  (crisis-verified, referenced to the FULL-CYCLE base MDD, not a window-flattered one) —
  where the base (arm0) does not. **H0:** it does not clear ("money stays in the robo" —
  a legitimate, publishable outcome; report the matched A/B either way, don't round to
  the thesis).
- **Decision instruments:** `core.combined_candidate_scorecard.evaluate_deploy_readiness`
  + `FactorRiskModel.is_it_beta_or_edge` (a "beta" verdict does NOT reject — the thesis
  is better-shaped tail-protected beta).
- **Gates (all mandatory, per CLAUDE.md):** census `[NN-CENSUS]` (fundamentals_blind=0 —
  the quality tilt reads fundamentals; edges_blind empty; n_in_panel ≥ n_resolved −
  allowlist; n_trades>0; trades_canon_md5 ≠ empty; macro_panel_complete; costs actually
  applied); fail-closed `[NN-FAIL-CLOSED]`; block-bootstrap ci_low `[NN-SHARPE-CI]`
  (Politis-White/Künsch, 1000 iter); N≥3 bitwise determinism IN-CONTAINER.
- **E/T-221 regime-sanity checklist** (`docs/Audit/regime_ground_truth_deepwindow_t221_2026_06_19.md`):
  the composition's overlay must de-gross EARLY and sit ~73-82% flat through each
  historical crisis (dotcom/GFC/COVID/2022). If the defensive arm doesn't show this, it
  isn't exercising the tail protection → treat the cell as a FAIL, not a pass.

## 5. Execution path (campaign launcher, no fork)
`scripts/submit_arms_campaign.py` (the existing per-arm A/B launcher) applies the per-cell
config patch (`ARCHONDEX_CONFIG_PATCH_B64`) + window (`ARCHONDEX_START_DATE/END_DATE`) via
`cloud_entrypoint.sh`. Specs: `/tmp/t215_preflight_spec.json` (single-arm PIT×rc,
2008-2009-GFC, 3-rep — census + determinism PRE-FLIGHT, gate-exempt as single-arm) and
`/tmp/t215_ab_spec.json` (the matched A/B, full-cycle, 6 cells + canary, anchor block
citing the pre-flight canon for the T-140 canon-anchor gate). Job-def: clone of
`archondex-backtest-t155-anchor` (entrypoint command + ARM64 + 1vCPU/4GB, the proven
determinism config) repointed to this image, with an extended attemptDurationSeconds for
the 26-yr cell (~9h, B/T-180 reference).

## 6b. Execution UPDATE (2026-06-19) — UNBLOCKED via remote CI build; A/B is LIVE
The local-disk blocker (§6, below) was routed around per the director's guidance:
- **Substrate to S3 without the 2-hour slow uplink:** the manifest md5 changed from the
  T-175 prefix (`6e36e42d…`) ONLY by the added `market_cap_tiers.json`. Server-side-copied
  the 14119-object T-175 prefix → my prefix (`9fe5c27e…`) with `--copy-props none` (the CI
  user lacks `s3:GetObjectTagging`), then uploaded the one 33 KB cap json → **14120 objects
  = my manifest**. Minutes, not hours.
- **Remote CI build** (`.github/workflows/build_backtest_image.yml`) on my pushed branch →
  **image `:sha-3863ef8` in ECR** (1.366 GB). The CI run reports `failure` but the image
  + manifest landed (describe-images confirms): the CI role `archondex-github-ci-role`
  lacks `ecr:BatchGetImage`, which denied a POST-push read AFTER all layers pushed. **This
  is a real-but-non-blocking CI defect to fix** (add `ecr:BatchGetImage` to the CI role so
  the workflow goes green + is reliable). The build's manifest-verify passed (it reached
  the push), so the baked substrate matches the committed manifest incl. the cap cache.
- **Job-def `archondex-backtest-t215`** repointed at `:sha-3863ef8` (rev 2), then rev 3
  adds the justified `CENSUS_EXPECTED_DORMANT=news_sentiment_edge`.

### Pre-flight (single-arm PIT×rc, 2008-2009-GFC, N=3) — VALIDATED with one census caveat
- **Image healthy** (Fargate ARM64), **config patch applies** (PIT + realistic_retail_costs
  set, entrypoint-logged), **fund_blind=0**, **regime_unknown=0.0**, **trades=998>0**.
- **N=3 cross-task in-container determinism CONFIRMED** — all three reps =
  `67784c1ba70ce75a5ed62056f81d2ba1` (the T-057c FP-summation risk is resolved on this
  image; satisfies the N≥3 requirement's hardest part).
- **Census NON-CANONICAL on the 2yr window (expected, window-length):** `edges_blind=5`
  = `news_sentiment_edge` (STRUCTURALLY dormant historically — a stray edge not in the
  governor's `edges.yml`, needs `data/intel` news history that isn't baked / doesn't exist
  pre-~2020) + the 4 value/accruals edges (T-180-v2 measured them firing on the 26yr
  window → window-length, not structural). `panel 396/398` (2 names resolved-not-built;
  minor). The 2yr GFC window is simply too short for the slow fundamental edges.

### Census handling for the canonical run (conservative, gate-respecting)
- `CENSUS_EXPECTED_DORMANT=news_sentiment_edge` ONLY — objectively justified (no historical
  news data baked; verified). **NOT** allowlisting value/accruals (they must fire on the
  26yr window — if blind there, that is a REAL finding and census SHOULD fail) and **NOT**
  pre-setting a panel allowlist (let the full-window census honestly report any shrink).
  This avoids the "force-a-pass" anti-pattern `[NN-CENSUS]` warns against.

### Canonical A/B — LIVE
6 cells submitted on `archondex-backtest-t215:3`: `arm0_base`×3 + `arm1_composition`×3,
window 2000-2025, anchor = the pre-flight canon (same image, N=3-verified). Each 26yr PIT
cell ≈ 9-18h; running in parallel; launcher `submit_arms_campaign.py` polls + writes a
summary. **Verdict pending completion.** On completion: per-arm N=3 determinism, census
(value/accruals fire? panel?), then `evaluate_deploy_readiness(roth, after-tax, w_dbmf=0)`
vs 60/40 + schwab_like + `is_it_beta_or_edge` + the E/T-221 regime-sanity checklist.

## 6. (historical) Execution status — BLOCKED on local image build (honest hard blocker)
D's side is fully prepared; the ONE gating artifact — the canonical image — **cannot be
built on this Mac**. This is the known local-disk hazard (CLAUDE.md build-script
T-107/T-126/containerd lineage), now definitively characterized:

- The image bakes a **~2 GB data substrate** (`data/processed` + `data/raw` + macro +
  governor). Multi-stage buildx loads/extracts that context for the builder AND runtime
  stages, and the python scientific deps add ~1.5 GB → **peak disk demand > 12 GB**.
- From a fully-pruned clean slate (**12 GB free**), the build **craters to 1 GB while
  still at builder stage 2/5 (apt)** — before the 2 GB data-COPY layer and pip even run.
  The first attempt actually hit 0 → containerd I/O errors → **Docker Desktop crashed**
  (recovered via full restart + prune).
- I **cannot free host disk**: `rm`/`git clean` are deny-listed (correctly), and a
  killed build leaves an orphaned ~2.7 GB staging dir in `$TMPDIR` that only `rm` (or OS
  tmp-reaping) clears.
- **`data/raw` is runtime-load-bearing** (fundamentals loader + the composition's own
  trend overlay reads SPY/AGG/GLD from `data/raw/stooq`), so the context can NOT be
  shrunk by dropping it — that's not a valid unblock.

**Two fail-opens were genuinely found + fixed this task** (the build-script staging
fail-open §3, committed), and all non-build prep is done. But the measurement itself is
gated on an image artifact this machine's disk cannot produce.

### Unblock options for the director (the run fires the moment the image lands)
1. **Free substantial host disk** (~20 GB+ free to build safely), then I retry the build
   + run — fastest if disk can be freed.
2. **Remote / larger-disk build** (CodeBuild / an EC2 builder / a machine with disk):
   `scripts/build_backtest_image.sh 9bec2f7 <ecr-ref>` off the SAME commit, push
   `:sha-9bec2f7`. This is the durable fix for a recurring hazard (3+ disk incidents on
   record). The job-def `archondex-backtest-t215:1` is already registered pointing at
   `:sha-9bec2f7`.
3. **Another agent/director builds** off 9bec2f7; then D runs pre-flight + A/B — everything
   downstream is ready and mechanical.

### What is DONE and locked in (nothing else blocks D's side)
- Branch off main @ 9bec2f7 (T-211 + T-207 + T-210 present); manifest matches the T-219
  enriched cap cache (verify OK, 14120 files).
- **Build-script staging fail-open fixed + committed** (`market_cap_tiers.json`).
- **Job-def `archondex-backtest-t215:1` registered** (entrypoint command + ARM64 +
  1vCPU/4GB proven-determinism config + 11h timeout for the 26-yr cell).
- **Specs pre-registered + committed** (`docs/Audit/t215_campaign_specs/`): pre-flight
  (single-arm PIT×rc, 2008-2009-GFC, 3-rep, gate-exempt) + the matched A/B (full-cycle,
  6 cells + canary, anchor block citing the pre-flight canon).
- AWS verified (sts/ECR/Batch); `submit_arms_campaign.py` is the launcher (no fork).

## Files
- `scripts/build_backtest_image.sh` — stage `market_cap_tiers.json` (build-time fail-open fix)
- `/tmp/t215_preflight_spec.json`, `/tmp/t215_ab_spec.json` — campaign specs (pre-registered)
- (no canon/config default changes — PIT + realistic-cost + composition are ON only in the
  measurement-cell config patches; prod defaults stay OFF; promote nothing)
