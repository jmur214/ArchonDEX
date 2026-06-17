---
task_id: T-2026-06-16-179
title: Phase-0 Discovery gene-wiring fix + the first honest Foundry-vocabulary exploration
date: 2026-06-16
author: Agent D (alpha/edge + Discovery lane)
outcome: FIXED + PROVEN. Two latent bugs neutered the entire GA composite/foundry
  path. (1) CompositeEdge bound self.genes/self.direction ONCE in __init__ but the
  base set_params only updates self.params, so Discovery's cls_()+set_params
  instantiation left every GA-evolved genome with genes=[] -> inert -> 0 fitness
  -> selected out (the "rsi-only / 0 promotions" history is this bug). (2) Exposed
  by fixing (1): residual_momentum technical genes crashed on a never-set
  self.regime_cache. Both fixed (Engine-A edge, default-safe). Proven on the EXACT
  Discovery instantiation path: 32 GA composite candidates now run, 0 errors,
  20 live / 12 legitimate-abstain (was: 100% inert). The Foundry feature space is
  now actually testable for the first time. Phase-0b gated cycle pre-registered;
  canonical multi-generation run handed to B's T-180 panel-baked (simfin-live)
  cloud image.
status: CURRENT
---

# T-179 — the Discovery alpha-reopener

## What was broken (both verified)

### Bug 1 (gating) — composite genomes instantiated INERT
`CompositeEdge.__init__` bound `self.genes`/`self.direction` once
(`composite_edge.py`), but `set_params` (`edge_base.py:19-20`) only updates
`self.params`. Discovery instantiates candidates via `cls_()` THEN
`set_params(spec_params)` (`discovery._instantiate_candidate`, used by
`validate_candidate`), so every GA-evolved composite/foundry genome reached
`compute_signals` with `genes=[]` → all-zero signals → flat attribution → Gate-1
contribution ≤ 0 → dead. The only edges that ever produced signal were the
hand-written standalone ones (rsi_bounce_v1…) that skip this path — hence the
six-week illusion "the GA only does rsi_bounce_v1 / the Foundry vocabulary has no
alpha." **The vocabulary was never actually tested.** (Found in T-177,
director-verified.)

**Fix:** override `set_params` in `CompositeEdge` to re-derive
`self.genes`/`self.direction` after the base call — refreshes on ANY
instantiation path. Same set-once-in-`__init__` bug class fixed in the two
sibling `autogen_phase3_{long,short}` edges (direction only; latent/harmless there
since the default matched the hardcoded direction). `RuleBasedEdge`/`xsec_momentum`
already override `set_params` correctly (the template).

**Belt-and-suspenders (per `measurement_integrity_audit_2026_06_16.md`):** the two
construction sites that used `cls_(); set_params(params)` —
`discovery._instantiate_candidate` (~discovery.py:864) and
`wfo._quick_backtest` (~wfo.py:244) — now use the params-CONSTRUCTOR
`cls_(params=params)` (mirroring the production loader at ~discovery.py:835, with
its `TypeError` fallback for edges whose `__init__` doesn't accept `params=`, e.g.
the template-mutation edges). So genes hydrate in `__init__` even if a future
evolutionary edge forgets the `set_params` override — two independent guarantees.
Verified: composite via `_instantiate_candidate` → genes=1 + fires; `RSIBounceEdge`
(no `params` kwarg) → TypeError fallback instantiates + applies set_params; empty
spec → genes=[] safe.

### Bug 2 (exposed by fixing Bug 1) — residual_momentum crash
Once composite genomes actually RUN, any genome with a `residual_momentum`
technical gene crashed at `composite_edge.py` — `self.regime_cache.get(...)`
referenced an attribute NOTHING ever sets → `AttributeError` (a propagating
programmer-error). Dormant while composites were inert. **Fix:** read the
benchmark (SPY) from the live `self._current_data_map` (already set in
`compute_signals`); abstain when absent — preserving the original intent.

## Proof of unblock (production-path, hermetic, deterministic)
Instantiated EXACTLY as Discovery does (`cls_()` then `set_params`):
- single foundry gene (`mom_12_1` top-30%): 6/20 large-caps fire (the
  high-momentum names) — was 0.
- 2-gene composite (high-mom AND low-vol): 3/20 fire (AND-subset of gene-0).
- full GA batch (`generate_candidates(n_mutations=8)`, seed 0): **32 GA composite
  candidates, 0 errors, 20 LIVE / 12 legitimate-abstain** — was 100% inert.

Regression test `tests/test_composite_genes_wiring_t179.py` (5 tests) instantiates
via the production path and FAILS on pre-fix code (genes==[]), PASSES on the fix;
plus 2-gene AND-subset, set_params-idempotency, autogen-direction-refresh, and
rsi_bounce_v1 non-regression. 494 edge/discovery tests pass (3 pre-existing
failures unrelated, fail identically on main).

**Honest nuance:** the GA SEEDS from the existing `ga_population.yml`, which is
legacy technical-heavy (1/32 of this batch references a foundry feature). Foundry
exploration GROWS as the GA evolves — new random genes are ~19% foundry (measured
factory distribution) and structural mutation adds them ~10%/gen. The first cycle
off the legacy population is technical-dominated; the foundry vocabulary is
explored over generations. The fix makes composite/foundry genomes SURVIVABLE for
the first time; it does not instantly make the population foundry-heavy.

## Phase 0b — PRE-REGISTRATION (written before any gate result)
Per CLAUDE.md #7. The canonical run is the multi-generation gated cycle on B's
T-180 panel-baked (simfin-live) image (B's coordination note: "share the image
tag so D doesn't re-run blind"). Locally simfin IS present (T-175,
`fundamentals_simfin.parquet` 9.9 MB) so a local cycle is not simfin-blind, but
the per-candidate MBL-clearing backtest is a cloud-scale cost — the canonical
verdict runs there.

- **Hypothesis (H1):** with composite genomes no longer inert, ≥1 GA-evolved
  composite/foundry candidate clears the full 8-gate gauntlet (incl. Gate-6
  FF5+Mom α t>2 and Gate-8 DSR) on the canonical substrate over an MBL-clearing
  window. **Null (H0):** the vocabulary explores but nothing clears (now an HONEST
  null — the prior null was a bug artifact).
- **Promotion gate (unchanged, no loosening):** the existing gauntlet —
  Gate-1 contribution > 0.10, Gate-2 PBO survival ≥ 0.60, Gate-4 perm p < 0.05,
  Gate-5 universe-B contribution > 0, Gate-6 FF5+Mom α t > 2 & α_ann > 2%,
  Gate-7 substrate-B drift ≤ 0.5, **Gate-8 DSR p > 0.95 with honest N**.
- **N_trials consumed:** `n_trials_for_dsr` = the per-cycle candidate count
  (template mutations + GA composites), added to the accumulated honest-N; DSR
  computed against the max-of-N null. Window must satisfy MBL Gate-0
  (`T_years ≥ 2·ln(N)/SR²`) — multi-decade given accumulated N.
- **Decision rule:** clears → a real candidate edge (Engine-F `--discover` gate
  promotes, never by hand); doesn't clear → "explored, nothing clears" is itself
  decision-grade (first honest read of the Foundry vocabulary).
- **Determinism:** GA uses stdlib `random` seeded by PYTHONHASHSEED; the fix
  changes only attribute wiring (no RNG/call-order change). Recommend an explicit
  `seed` param on `GeneticAlgorithm.__init__` as hardening.

## Phase 0b — local cycle execution + the canonical-run handoff
A local `ARCHONDEX_HERMETIC=1 python -m scripts.run_backtest --discover` cycle was
launched on the simfin-present local substrate (NOT simfin-blind). It ran the full
backtest phase clean post-fix (no `genes=[]` / `regime_cache` crashes — the bugs
that the unblock would otherwise have surfaced). The `--discover` cycle's per-
candidate gauntlet over an MBL-clearing window is a cloud-scale cost (T-021:
~thousands of sec/candidate even with the Gate-1 signal cache, T-023); the
**canonical multi-generation gated verdict runs on B's T-180 panel-baked
(simfin-live) image** — per B's coordination note ("share the image tag so D
doesn't re-run blind"), and because that is the substrate the re-anchor + the
honest-N DSR gate are defined on.

**What is decision-grade NOW (does not need the gated run):** the unblock is
PROVEN end-to-end — composite/foundry genomes that were 100% inert (0 signals → 0
fitness → Gate-1 death) now run and produce live attribution (20/32 GA composites
live, 0 errors). So the prior "0 promotions / rsi-only / vocabulary-has-no-alpha"
verdicts are bug artifacts and MUST be re-measured. **What the gated cycle decides
(deferred to the cloud, pre-registered above):** whether any surviving composite/
foundry candidate clears the unchanged 8-gate gauntlet — H1 (≥1 clears) vs the now-
honest H0 (explores, nothing clears). Both are decision-grade; the prior null was
not (it was the bug).

## Files
- `engines/engine_a_alpha/edges/composite_edge.py` — set_params override (Bug 1) +
  residual_momentum benchmark-from-data_map (Bug 2)
- `engines/engine_a_alpha/edges/autogen_phase3_{long,short}.py` — sibling set_params
- `engines/engine_d_discovery/discovery.py` — `_instantiate_candidate` → params-constructor (belt-and-suspenders)
- `engines/engine_d_discovery/wfo.py` — `_quick_backtest` → params-constructor (belt-and-suspenders)
- `tests/test_composite_genes_wiring_t179.py` — 7 regression tests (fail-on-old + constructor-form + TypeError fallback)
- `docs/Audit/gene_encoding_extension_design_t177_2026_06_16.md` — the T-177 design

## NOT included
No edge promoted by hand / no `edge_weights.json` edit (Engine F + `--discover`
gate own promotion). No Engine B / live_trader. The canonical gated cycle runs on
B's T-180 simfin-live image. Branch only; director merges.
