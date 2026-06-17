---
task_id: T-2026-06-16-177
title: Engine-D gene-encoding extension — DESIGN (scoping the Discovery gating constraint)
date: 2026-06-16
author: Agent D (alpha/edge + Discovery lane)
type: design / scoping (NO code changes shipped — propose-first build)
headline: THE GENE ENCODING IS NOT THE BLOCKER. T-022 (2026-05-11) already made
  Foundry features first-class genes — the GA factory emits foundry_feature genes
  ~19% of the time, they resolve to real cross-sectional values, and a properly
  instantiated CompositeEdge produces correct signals end-to-end. The reason
  "vocabulary expansion delivers 0" is a ONE-LINE WIRING BUG: CompositeEdge binds
  self.genes once in __init__, but the Discovery instantiation path is
  `cls_()` THEN `set_params(params)`, and set_params never refreshes self.genes —
  so EVERY GA-evolved composite/foundry genome is instantiated with genes=[],
  produces 0 signals, scores 0 fitness, and is selected out. Recommendation: fix
  the wire (propose-first, ~3 lines + a regression test), RE-MEASURE whether
  foundry-driven Discovery now produces surviving candidates, and only THEN decide
  whether a deeper encoding extension is worth the overfitting cost. Do not build a
  new encoding system on top of a dead wire.
status: CURRENT
---

# T-177 — gene-encoding extension design

The brief (and the standing finding `project_engine_d_gene_encoding_blocker`,
dated 2026-05-11) say Engine D's GA "emits only rsi_bounce_v1 mutations — the
Foundry feature library is INVISIBLE to the gene encoding." Per the
repoint-over-rebuild discipline (`feedback_prefer_repoint_over_rebuild`) I ran the
cheap disambiguating diagnostics BEFORE designing a new capability. **The premise
is stale.** What follows is the measured current state, the actual blocker, and
the minimal path — with the deeper extension scoped as optional, gated on a
re-measurement the fix unblocks.

## 1. Current encoding's limits — what's ACTUALLY true (measured, code-cited)

### 1a. The gene/genome representation already supports Foundry features
- A **gene** is a plain dict; a **genome** is `{edge_id, genes:[...], direction}`
  (`genetic_algorithm.py:125-130`). Genes are DATA, not code — so new gene types
  cost nothing structurally.
- The gene factory `DiscoveryEngine._create_random_gene` (`discovery.py:405-658`)
  has a **`foundry_feature` bucket at ~20% weight**, added by **T-022
  (`discovery.py:428-434`, 563-612)**. Measured factory output over 2000 samples
  (seed 0): `foundry_feature` **381 (19.0%)**, technical 302, macro 218,
  fundamental 214, intermarket 206, microstructure 200, calendar 185, earnings
  105, regime 103, behavioral 86. A sampled gene:
  `{type:'foundry_feature', feature_id:'correlation_average_60d',
  operator:'bottom_percentile', threshold:10}`. **So the GA emits foundry genes
  today** — the "single-archetype rsi_bounce_v1" claim is false at the encoding
  layer.
- Mutation (`genetic_algorithm.py:233-296`) mutates threshold (Gaussian 10%),
  window (±5), flips operators (5%), and does structural add/delete/direction —
  all gene-type-agnostic, so foundry genes mutate like any other. Crossover
  (`191-227`) is single-point on the gene list. Nothing pins the GA to one edge.

### 1b. The Foundry registry populates and features evaluate to real values
- 35 tier-A/B features self-register on `import core.feature_foundry.features`
  (`features/__init__.py` imports every submodule). FOUR runtime call sites
  trigger this import — `composite_edge.py:203`, `discovery.py:577`,
  `feature_engineering.py:193`, `bayesian_optimizer.py:81` — so the registry is
  populated wherever a foundry gene is evaluated. (Caveat: bare
  `get_feature_registry()` WITHOUT that import returns 0 features; every product
  call site does import, so this is fine in practice but is a footgun for tests.)
- Measured, hermetic, on real cached data (20 large-caps, 2024-06-03): the
  ticker-dependent features return real, varied cross-sections — e.g. `mom_12_1`
  = {AAPL 0.017, MSFT 0.22, KO 0.049, JPM 0.39, XOM 0.13, GILD −0.14}. The
  `top_percentile`/`bottom_percentile` evaluation in
  `composite_edge.py:124-141` is correct (cutoff = `np.percentile(all_vals,
  threshold)`; manual replay: 6/20 pass at threshold 70).

### 1c. THE ACTUAL BLOCKER — a one-line wiring bug makes every composite genome inert
`CompositeEdge.__init__` binds the working attributes ONCE, at construction
(`composite_edge.py:51-56`):
```python
def __init__(self, params=None):
    super().__init__()
    self.set_params(params)
    ...
    self.genes = self.params.get("genes", [])       # bound HERE, once
    self.direction = self.params.get("direction", "long")
```
But `set_params` is the base no-op refresher (`edge_base.py:19-20`):
```python
def set_params(self, params): self.params = params or {}   # updates params ONLY
```
and Discovery instantiates candidates via **construct-then-set_params**
(`discovery.py:858-867`, used by `validate_candidate` at `discovery.py:1188`):
```python
edge = cls_()                              # params=None -> self.genes = []
if candidate_spec["params"]:
    edge.set_params(candidate_spec["params"])   # sets self.params, NOT self.genes
return edge
```
**Result (measured, exact production replay):** `edge.genes == []` while
`edge.params["genes"]` has the gene. The CompositeEdge is inert → `compute_signals`
returns all-zero → attribution stream is flat → Gate-1 contribution ≤ 0 → the
candidate dies. Every GA-evolved composite genome (foundry OR any multi-gene
combination) is dead-on-arrival. The only edges that ever produce signal are the
hand-written standalone edges (rsi_bounce_v1 et al.), which do NOT go through this
path — hence the *appearance* that "the GA only does rsi_bounce_v1."

**Proof the machinery is otherwise whole:** instantiated via the CONSTRUCTOR
(`CompositeEdge(params)`, genes wired), the same foundry gene yields 6/20 signals
(MSFT/JPM/CAT/DIS/IBM/GE — the high-momentum names); a 2-gene composite
(high-mom AND low-vol) yields 3 (MSFT/WMT/T). The encoding, the registry, the
feature evals, and the boolean/percentile tree all work. Only the
discovery-path instantiation drops the genes.

### 1d. Secondary (real, but downstream of 1c) — a feature-class / operator mismatch
~half the Foundry library is **ticker-independent** (calendar: fomc_drift,
pre_holiday, sell_in_may…; macro: vix_change_5d, dxy_change_20d…). These return
the SAME value for every ticker on a given date. The gene factory can pair them
with the **cross-sectional** operators `top_percentile`/`bottom_percentile`,
which are DEGENERATE on a constant cross-section (no ticker is "top 30%" when all
are equal → 0 signals, always). Measured: every calendar feature under
`top_percentile` → 0 signals on a non-event date. So even after 1c is fixed, a
chunk of the foundry vocabulary is wired to operators that can't express it. This
is the part that is genuinely an *encoding* refinement (see §2b).

## 2. Proposed extension

### 2a. PHASE 0 (the unblock — minimal, propose-first, ~3 lines + test) — REQUIRED FIRST
Make `CompositeEdge` re-derive its working attributes whenever params change.
Smallest correct fix — override `set_params` in `composite_edge.py`:
```python
def set_params(self, params):
    super().set_params(params)              # self.params = params or {}
    self.genes = self.params.get("genes", [])
    self.direction = self.params.get("direction", "long")
```
(Equivalently: have `_instantiate_candidate` use the constructor
`cls_(candidate_spec["params"])` — but fixing `set_params` is safer because it
repairs EVERY construct-then-set_params caller, not just Discovery.) This is an
Engine-A edge fix; it is behaviour-preserving for the constructor path and
un-breaks the discovery path. **It is the entire difference between "vocabulary
delivers 0" and "the GA can actually explore the Foundry."** It must land and be
re-measured before any larger build is scoped.

### 2b. PHASE 1 (encoding refinement, gated on Phase-0 re-measurement)
Only if Phase-0 re-measurement shows foundry genes explore but mis-fire on the
ticker-independent half: introduce a **feature-class tag** on the gene so the
factory pairs each feature with operators it can actually express.
- The `Feature` dataclass already carries `ticker_independent: bool`
  (`feature.py`) and `_classify_feature_ticker_independence` exists in
  `feature_engineering.py`. Reuse it: when `_create_random_gene` samples a
  `foundry_feature`, branch on the feature's class:
  - **cross-sectional** (ticker-dependent, e.g. mom_12_1, realized_vol_60d):
    keep `top_percentile`/`bottom_percentile` (stock-selection semantics).
  - **timing / regime-level** (ticker-independent, e.g. calendar/macro): use
    absolute `greater`/`less` against a threshold, i.e. a date-level ON/OFF
    filter applied to the whole book — NOT a cross-sectional rank.
- No new gene TYPE is needed (foundry_feature already exists); this is a
  constraint on operator selection inside the existing bucket — keeps the
  search space from emitting meaningless genes (which also reduces wasted
  N_trials, see §5).

### 2c. PHASE 2 (optional, only if Phases 0-1 prove foundry edges survive the gauntlet)
Richer composition, each a SEPARATE propose-first increment with its own A/B:
- OR / NOT gene-group operators (today the tree is pure AND —
  `composite_edge.py:149`), to express "high momentum OR oversold."
- feature-substitution mutation (swap one `feature_id` for a correlated sibling)
  to make the GA walk the feature manifold rather than only tune thresholds.
- multi-objective fitness (Sharpe + Sortino + turnover) vs the current single
  attribution-Sharpe (`discovery.py:373-403`).
These are real extensions but premature until Phase-0 proves the pipeline
produces a single surviving foundry candidate. **Build order is the point: wire,
measure, then extend.**

## 3. Integration points (what changes, minimally)
- **Phase 0:** `engines/engine_a_alpha/edges/composite_edge.py` only (override
  `set_params`). No change to discovery.py, the GA, or the gauntlet. The existing
  path `validate_candidate` → `_instantiate_candidate` (`discovery.py:1188, 866`)
  → `CompositeEdge` then "just works."
- **Phase 1:** `discovery.py:_create_random_gene` foundry branch (operator choice
  by feature class) + read `Feature.ticker_independent`. No gauntlet change.
- **Phase 2:** `composite_edge.py` (OR/NOT eval), `genetic_algorithm.py`
  (substitution mutation), `discovery.py` (fitness) — each independent.
- The genome→spec→registry path (`genetic_algorithm.py:375-399`
  `to_candidate_specs` → `save_candidates` `discovery.py:674-709`, status
  `candidate`) and the 8-gate gauntlet are UNCHANGED throughout.

## 4. Test plan
- **Phase-0 regression (the load-bearing test):** instantiate via the EXACT
  production path — `cls_()` then `set_params(spec["params"])` — and assert
  `edge.genes` is populated AND `compute_signals` returns ≥1 non-zero on a fixed
  20-ticker/2024-06-03 hermetic data_map. This test FAILS on today's code and
  PASSES after the fix (I have the harness from this scoping; it's ~15 lines).
  Add a twin asserting the constructor path is unchanged (no regression).
- **rsi_bounce_v1 non-regression:** a standalone-edge candidate still validates
  identically (it never used the composite path; canon-md5 unchanged).
- **Pipeline probe:** run one `--discover` cycle with `n_trials_for_dsr` set and
  confirm ≥1 foundry-gene candidate now produces a non-flat attribution stream
  (reaches Gate 1 with non-zero contribution) — vs today's universal flat-line.
- **Determinism:** GA uses stdlib `random` seeded by `PYTHONHASHSEED`
  (`bayesian_optimizer.py:39-47` pattern; GA has no explicit seed). Verify a
  fixed-seed cycle is bit-reproducible across runs (`--runs 3`); the fix changes
  only attribute wiring, not the RNG call order, so determinism holds. Recommend
  adding an explicit `seed` param to `GeneticAlgorithm.__init__` as hardening.
- **Phase-1:** assert calendar/macro foundry genes get absolute operators and
  produce book-level ON/OFF signals (non-degenerate) on an event date.

## 5. Risks
- **Overfitting / honest-N (the biggest):** Phase 0 turns a dead search branch
  LIVE. The instant foundry genomes can score, the GA will mint many distinct
  candidate configurations — each is a trial against the same substrate, so
  `N_effective` climbs and MBL Gate-0 (`T_years ≥ 2·ln(N)/SR²`, CLAUDE.md #6)
  tightens and Gate-8 DSR (`discovery.py:898-905`, default `n_trials_for_dsr=1`)
  MUST be turned on with an honest trial count. Pre-register the re-measurement
  (hypothesis + threshold + N_trials consumed) BEFORE running, per CLAUDE.md.
  Recommendation: set `n_trials_for_dsr` to the per-cycle candidate count so the
  DSR gate is honest from day one.
- **Gauntlet load:** cost is O(N_candidates) with-candidate backtests (baseline
  cached per cycle, `discovery.py:1199-1220`); Gates 5/7 add per-candidate
  universe-B/substrate-B backtests. A live foundry branch could 3-5× candidates
  per cycle → default to cloud (CLAUDE.md parallel-campaign rule) and/or cap
  candidates/cycle. Phase 1's operator-by-class constraint REDUCES wasted trials
  (no more degenerate calendar×percentile genes).
- **False confidence from the prior "0 promotions":** the historical
  substrate-honest 0/3 promotion finding (T-021) and "GA only rsi_bounce_v1" were
  measured WITH this wiring bug live — they cannot be read as evidence that the
  Foundry vocabulary lacks alpha. They must be re-measured post-fix before any
  conclusion about feature quality.
- **Scope creep:** the temptation is to build Phases 1-2 now. Resist — the
  honest, cheap move is Phase 0 + re-measure. If post-fix foundry candidates
  still don't survive the gauntlet on the canonical substrate, THAT result (not a
  speculative encoding system) tells us where the next dollar goes.

## Recommendation — is the build worth it?
**Yes, but it is a ~3-line fix, not a project.** The "highest-leverage Discovery
work" framing is correct about the *leverage* and wrong about the *cost*: the
gene encoding was already extended (T-022); a single un-refreshed attribute
(`CompositeEdge.set_params` not re-deriving `self.genes`) silently neutered the
entire foundry-gene capability, which is why six weeks of "vocabulary expansion
delivers 0." Ship Phase 0 (propose-first, with the production-path regression
test), re-run one pre-registered `--discover` cycle with DSR on, and let the
measured survival rate decide whether Phases 1-2 are warranted. Designing a large
new encoding system before fixing the wire would be building on a dead path —
exactly the rebuild-over-repoint trap this codebase keeps hitting.

## Evidence appendix (commands run for this scoping — read-only, no code shipped)
- gene-factory distribution: 2000-sample `_create_random_gene` → 19% foundry.
- registry: `import core.feature_foundry.features` → 35 tier-A/B features.
- feature evals (hermetic, 20 large-caps, 2024-06-03): mom_12_1 etc. return real
  cross-sections; calendar features return 0 off-event (ticker-independent).
- production-path replay (`cls_()` then `set_params`): `edge.genes == []`
  (inert); constructor path: genes wired → 6/20 (single gene), 3/20 (2-gene
  composite). Citations: composite_edge.py:51-56,124-141,203; edge_base.py:19-20;
  discovery.py:405-658,858-867,1188; genetic_algorithm.py:125-130,233-296,375-399;
  feature.py (Feature dataclass); features/__init__.py.
