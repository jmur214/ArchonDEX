---
task_id: T-2026-06-17-183
title: Fair Foundry representation in the GA Gen-0 seed (so Phase-0b is an honest vocabulary test)
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
type: implementation + pre-registration (seed diversity only; gauntlet/DSR gates UNCHANGED)
outcome: DONE. T-179 unblocked the GA, but the population evolves from the legacy
  technical-heavy ga_population.yml, so the first --discover cycle off it is a
  near-rerun of the technical edges (1/32 foundry genes), NOT a test of whether the
  Foundry vocabulary has alpha — which is the open question (the "no-alpha" history
  was a bug artifact). Added a config-gated `foundry_seed_fraction` (pre-registered
  0.5) that allocates half the FRESH Gen-0 population to single-gene foundry genomes
  with feature_ids drawn UNIFORMLY AT RANDOM across the whole tier-A/B registry —
  no hand-picking; the GA + the unchanged gates decide what survives. Fresh Gen-0
  now: 17/20 genomes contain a foundry gene, 12 distinct features (was 1/32).
  Deterministic (md5 identical ×3); OFF (0.0) bit-identical to prior; gene factory
  bit-identical (seed-0 2000-gene md5 unchanged after refactor).
status: CURRENT
reproduce: |
  pytest tests/test_foundry_seeding_t183.py -q                 # 5 pass
  # fresh seed at fraction 0.5 → 10 fair-foundry genomes, deterministic
---

# T-183 — fair Foundry seeding

## 1. Diagnosis — why 1/32 foundry in T-179's batch
`DiscoveryEngine._run_ga_evolution` (discovery.py:~295):
- **If `ga_population.yml` EXISTS** (the normal case — it's baked/restored from
  the governor anchor): the GA EVOLVES from the persisted population. That
  population is legacy technical-heavy (built before T-022 added the foundry
  bucket and before T-179 made composites non-inert). New genes enter only via
  mutation (~10%/gen add a random gene, ~19% of which is foundry). So foundry
  representation trickles in over generations — the first cycle is technical.
  **This is why T-179's batch was 1/32 foundry.**
- **If FRESH (no ga_population.yml):** seeds from (a) `seed_from_registry` (legacy
  active/candidate edges → technical genes), (b) a HAND-PICKED `_T052_TARGET_FEATURE_IDS`
  subset (one genome each), (c) random fill via `_create_random_gene` (~19%
  foundry/gene). Even fresh, foundry is a minority and (b) is hand-picked.

Either way, the first honest `--discover` cycle would under-test the vocabulary.

## 2. The fix — fair, non-hand-picked foundry fraction in the Gen-0 seed
- New config key `foundry_seed_fraction` (config/discovery_settings.json),
  read in `DiscoveryEngine.__init__`; default **0.0** (prior behavior preserved).
- In the FRESH-seed path, before the random fill, allocate
  `round(foundry_seed_fraction × population_size)` single-gene foundry genomes
  via the new `_make_random_foundry_gene()` — feature_id drawn UNIFORMLY AT
  RANDOM from the live tier-A/B registry (NO hand-picking), with the T-022
  operator/threshold distribution. Each is a long-direction single-gene genome;
  the GA combines/mutates them over generations.
- `_make_random_foundry_gene()` was factored out of `_create_random_gene`'s
  foundry branch with the IDENTICAL RNG call sequence → the gene factory is
  bit-identical (verified: seed-0 2000-gene md5 `139b42b3…` unchanged).
- **Gates UNTOUCHED.** No change to the gauntlet, Gate-6 (FF5+Mom t>2), or
  Gate-8 (honest-N DSR). Only seed diversity changes.

## 3. PRE-REGISTRATION (written before the Phase-0b cycle)
- **Fraction:** `foundry_seed_fraction = 0.5`. At population_size 20 → 10
  single-gene foundry genomes (uniform-random features) + the other 10 from
  registry-seed/T-052/random fill. Measured fresh Gen-0: **17/20 genomes contain
  ≥1 foundry gene across 12 distinct features.**
- **Why 0.5 (not 1.0):** a fair test needs foundry on EQUAL footing with the
  legacy/mixed vocabulary, while keeping (a) composites that MIX foundry with
  technical/regime genes (via the other half + mutation) and (b) a technical
  comparison baseline in the same cycle. 1.0 would be foundry-only — itself a
  biased test and no mixing substrate. 0.5 is "meaningful share, not token" while
  not hand-tuning toward any specific feature.
- **No hand-picking:** feature_ids are uniform-random over the WHOLE tier-A/B
  registry; ~12 of 35 features appear at Gen-0, the rest enter via mutation across
  generations. The GA + the unchanged gates decide which survive.
- **Honest-N implication:** population SIZE is unchanged (20), so the per-cycle
  candidate count — and thus the N_trials added to honest-N and the MBL/DSR
  pressure — is ~NEUTRAL. The change redistributes WHAT is explored, not HOW MANY
  candidates are minted per cycle. (Over many generations the GA explores a wider
  genome space, but each cycle's gauntlet load is bounded by population_size as
  before.) DSR Gate-8 still uses the honest accumulated N.
- **Determinism:** seeding uses stdlib `random` (PYTHONHASHSEED). Verified: fresh
  Gen-0 at fraction 0.5 is identical across 3 builds (md5 `546b8cea…` ×3). OFF
  (0.0) consumes no extra RNG → bit-identical to prior behavior.

## 4. Phase-0b execution note (coordinate with B)
The fair seeding applies on the FRESH-seed path. For Phase-0b to use it, the cycle
must START FRESH — the legacy `ga_population.yml` (baked/anchor-restored) must be
ARCHIVED/absent so the fair Gen-0 is built (otherwise the GA evolves the legacy
technical-heavy population and the fraction never applies). **Action for the
Phase-0b run on B's T-180 simfin-live image:** archive `data/governor/
ga_population.yml` (and its anchor copy) before the `--discover` cycle so the fair
Gen-0 seed is generated. (Archive-never-delete; it's a regenerable GA artifact.)
This is the only operational step beyond merging T-183.

## 5. Tests
`tests/test_foundry_seeding_t183.py` (5): fraction respected (10@0.5×20),
OFF inert (0.0→0), deterministic across builds, features sampled not hand-picked
(≥5 distinct, all registry-valid), `_make_random_foundry_gene` shape. + 122
discovery/composite/wfo tests pass, 0 regressions; gene-factory md5 unchanged.

## Files
- `engines/engine_d_discovery/discovery.py` — `_make_random_foundry_gene` (factored,
  bit-identical), `foundry_seed_fraction` config read, fair-foundry Gen-0 block
- `config/discovery_settings.json` — `foundry_seed_fraction: 0.5` (pre-registered)
- `tests/test_foundry_seeding_t183.py` — 5 tests

## NOT included
No gate/gauntlet/DSR change (seed only). No hand-picked features. No edge promoted
by hand. The legacy ga_population.yml archival is an operational step for the
Phase-0b run (noted above), not done here. Branch only; director merges.
