---
task_id: T-2026-06-17-193
title: Phase-0b honest --discover cycle — BLOCKED on image provenance + cloud-discover path
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
type: blocker report + execution recipe (the load-bearing alpha test must run CORRECT)
outcome: BLOCKED — verified, before burning cloud spend on a misleading result. The
  brief says run on B's image `sha-fc5a69e`, but that image was built BEFORE T-183
  merged, so it lacks the fair foundry seed — running on it produces the
  legacy-technical-heavy near-rerun (exactly the unfair test T-183 was built to
  avoid). The only other recent image (`sha-561c488`, the T-183 merge) predates
  T-180-v2, so it is simfin-BLIND (census would FAIL on fundamentals_blind>0). NO
  built image has BOTH the fair seed (T-183) AND simfin-live (T-180-v2). Only
  current main HEAD (`8cbdd50`) has both. Recommendation: build an image off main
  HEAD (with ga_population.yml archived from the substrate so Gen-0 seeds fresh),
  census-pre-flight it, then run the pre-registered cycle. Plus: no turnkey cloud
  --discover entrypoint exists — clarify the execution model.
status: BLOCKED — awaiting an image off main HEAD (B's lane) + cloud-discover-path decision
---

# T-193 — Phase-0b honest --discover: why it can't run yet (and the fix)

This is THE alpha test (does the Foundry vocabulary contain harvestable alpha,
honestly explored for the first time?). It MUST run on a correct substrate or the
result is worthless. Before submitting, I verified the preconditions — two are
unmet.

## BLOCKER 1 — no built image has BOTH the fair seed AND simfin-live
The honest cycle needs all of: T-179 (genes non-inert), T-181 (census), **T-183
(fair foundry Gen-0 seed)**, **T-180-v2 (simfin-live loader fix)**. The candidate
images:

| Image | T-179 | census | T-183 fair seed | T-180-v2 simfin-live | verdict |
|---|---|---|---|---|---|
| `sha-fc5a69e` (B's, the brief's) | ✓ | ✓ | **✗** (0 `foundry_seed_fraction`; config absent) | ✓ | **unfair seed** → legacy-technical near-rerun |
| `sha-561c488` (the T-183 merge) | ✓ | ✓ | ✓ | **✗** (`cceede0` not an ancestor) | **simfin-blind** → census FAILs `fundamentals_blind>0` |
| build off **main HEAD `8cbdd50`** | ✓ | ✓ | ✓ (`2900492` ancestor; config 2 lines) | ✓ (`cceede0` ancestor; simfin offline-read present) | **CORRECT — but not built** |

Evidence (verified): `git merge-base --is-ancestor 2900492 fc5a69e` → NO;
`git show fc5a69e:engines/engine_d_discovery/discovery.py | grep -c
foundry_seed_fraction` → 0; `git merge-base --is-ancestor cceede0 561c488` → NO.
`fc5a69e` was pushed 09:49, T-183 merged later; `561c488` (17:21) predates the
T-180-v2 merge. So the brief's premise ("B's image is simfin-live + census-
canonical [and] T-183 made the seed fairly foundry-weighted") is true of two
DIFFERENT images, not one. **Running on `fc5a69e` would burn the load-bearing
cloud spend on the exact unfair, legacy-seeded test T-183 exists to prevent, and
report a misleading H0.**

## BLOCKER 2 — no turnkey cloud --discover entrypoint
The discovery cycle is LOCAL orchestration: `python -m scripts.run_backtest
--discover` (execution_manual:199) or `scripts/run_discovery_diagnostic_*.py`.
The cloud infra (`scripts/submit_substrate_run.py` → `cloud_entrypoint.sh`) runs
`run_isolated` BACKTEST cells, not a discovery cycle. So "run the multi-generation
--discover cycle on the image" has no existing turnkey path. Options (decision
needed):
- (a) one long Batch job on the image with the command overridden to
  `python -m scripts.run_backtest --discover` (single Fargate task, large timeout);
- (b) run the cycle locally on the correct image's substrate (but the per-candidate
  MBL-clearing gauntlet over a multi-decade window is the slow part — local is
  flaky at that scale, cf. T-179);
- (c) a discover-mode `cloud_entrypoint.sh` variant (small infra build).
The per-candidate gauntlet backtests are the cost driver either way; "cell count"
≈ candidates × (baseline cached once + with-candidate + universe-B + substrate-B).

## What IS verified / done (so the correct run is one build away)
- Fair seed + genes fix + census are ALL on current main HEAD `8cbdd50`
  (foundry_seed_fraction in config; simfin offline-read in simfin_adapter).
- T-183's fair Gen-0 seed is proven (T-183 audit: fresh Gen-0 → 17/20 foundry-
  containing, 12 features, deterministic). It only fires on a FRESH seed.
- The local legacy `ga_population.yml` (20 genomes, 10% foundry) was inspected and
  left as-found; the REAL run must archive it IN THE IMAGE SUBSTRATE (the
  `data/governor/_isolated_anchor/ga_population.yml` the run restores from) so
  Gen-0 builds fair — else the GA evolves the legacy technical-heavy population.

## Pre-registration (restated from T-179, unchanged — to run on the correct image)
- **H1:** ≥1 GA-evolved composite/foundry candidate clears the UNCHANGED 8-gate
  gauntlet incl. Gate-6 (FF5+Mom t>2) and Gate-8 (honest-N DSR), on the
  simfin-live + census-canonical substrate over an MBL-clearing window.
- **H0 (now HONEST):** the vocabulary explores but nothing clears — the Foundry
  feature space genuinely lacks harvestable alpha in our form. (The prior null was
  a bug artifact, T-177/T-179.)
- **Census-gate:** the run must be census-canonical (`fundamentals_blind=0`,
  `regime_unknown_frac~0`, `n_trades>floor`) or it is non-canonical and void.
- **Honest-N:** log the N_trials this cycle consumes; `n_trials_for_dsr` = the
  per-cycle candidate count; DSR vs the max-of-N null.
- No hand promotion / no `edge_weights.json` edit (Engine-F + the `--discover`
  gate own promotion).

## Recommendation (the unblock path)
1. **B (image lane):** build an image off main HEAD `8cbdd50` via
   `scripts/build_backtest_image.sh 8cbdd50 sha-8cbdd50` (the sanctioned clean-ref
   path), with `data/governor/_isolated_anchor/ga_population.yml` ARCHIVED from the
   staged substrate so Gen-0 seeds fresh (fair). Census-pre-flight one cell:
   confirm `fundamentals_blind=0`, `n_trades>floor`, AND
   `foundry_seed_fraction=0.5` is in the baked config + a fresh fair Gen-0 is
   generated.
2. **Director:** decide the cloud-discover execution model (a/b/c above).
3. **D (me):** run the pre-registered cycle on that image the moment it exists +
   the path is decided; report H1/H0, per-candidate DSR, N_trials, cell count.

## NOT done (deliberately)
Did NOT submit the cycle on `fc5a69e` (would be the unfair legacy-seeded test) or
`561c488` (simfin-blind). Did NOT autonomously build an image + invent a cloud
--discover entrypoint + spend hours/dollars on the load-bearing test — that needs
the image-lane build (B) + the execution-model decision (director). No edges
promoted; no gates touched. Shared local state left as-found.
