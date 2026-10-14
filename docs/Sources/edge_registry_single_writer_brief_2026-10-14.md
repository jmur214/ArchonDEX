---
task_id: edges.yml single writer (R's F1 on the registry unit; health_check HIGH 2026-10-14)
title: edges.yml — pure imports, one explicit atomic writer, consumers fail closed (Engines A, D, F)
date: 2026-10-14
author: Agent D
type: DESIGN BRIEF v4 — no code. Spans Engines A, D and F, so the BUILD waits on the USER's go-ahead (CLAUDE.md,
  "changes spanning 3+ engines"). R's design read is done (verdict BUILD IT; its three corrections are absorbed as
  rulings below); the registry unit (a3ac70c) is on main.
reviewed_by: Agent R — docs/Audit/edge_registry_single_writer_design_read_agent_r_2026_10_14.md (review/agent-r-registry-design)
n_trials: 0
---

# edges.yml — pure imports, one explicit atomic writer, consumers fail closed

## In plain words

`data/governor/edges.yml` holds every edge's status, and three parts of the system write it. Each can leave it
empty, half-written, or cut down to one edge, and none of them reports the damage. The worst is Engine A: merely
**importing** an edge module rewrites the file, about 30 times every time a program starts. If the file is ever
unreadable (a merge-conflict marker, a half-finished write, two runs writing at once), the next import rewrites it
holding **one** edge.

After this change:
- **importing code never writes the file**;
- **exactly one explicit step writes it, all-or-nothing:** the governor's own save, or a new
  `scripts/sync_edge_registry.py`;
- **everything that reads it refuses an unreadable or empty registry**, instead of carrying on with "no edges" or
  quietly substituting default edges.

**What you would notice:**
- **A new edge, or a changed default parameter in code, trades only after the sync runs.** This is intended: the
  file is the one authority on which edges exist, and code no longer edits it as a side effect.
- **A fresh local checkout refuses to run a backtest until the sync has run once.** This is also intended. The
  cloud image ships its own copy, so cloud runs are unaffected.
- **The live cloud paper fleet is not affected.** `scripts/run_paper_cloud_day.py`, `paper_trader/` and
  `live_trader/` never write edges.yml, and a lock proves that none of them imports an edge module.
- **Your decision before the first sync: three edges have never been in the registry.** Their modules
  (`betting_against_beta_v1`, `overnight_intraday_v1`, `volatility_risk_premium_v1`, from the T-122/T-123
  experiments) declare themselves "candidate". The first sync would add them, and Discovery would then queue 23
  candidates instead of 20. **Archive or register?** The director recommends archiving.

## The defect, verified on the code

- **Engine A**, `engines/engine_a_alpha/edge_registry.py`. R's F1, proven by R on planted files and re-read here:
  - `_load` ends in `except Exception: self._specs = {}` (`:128`);
  - `_save` is a non-atomic `path.write_text(yaml.safe_dump(…))` (`:166`);
  - `ensure()` calls `_save()` **unconditionally**, even when nothing changed (`:310`);
  - **30 modules** under `engines/engine_a_alpha/edges/` call `EdgeRegistry().ensure(…)` at module level, inside
    a `try`.

  So on an unreadable registry, the first import writes a ONE-edge file; and every import rewrites the file
  non-atomically, where concurrent processes on one worktree can interleave. That is the likeliest origin of a
  half-written registry, which the next import then "repairs" into one edge.
- **Engine D.** The registry unit (`a3ac70c`, in review) already made Discovery's own read refuse and its write
  atomic. **R's F3 remains:** `_build_production_edges` builds the Gate-1 baseline from
  `EdgeRegistry(…).list_tradeable()` (`discovery.py:909/914`). On an unreadable registry that baseline is an
  **empty book**, so a direct `validate_candidate` caller measures contribution against nothing, without saying so.
- **Engine F.** `lifecycle_manager.py:1108` `_save_registry`, and `evolution_controller.py:97` `save_edges` (no
  caller outside tests). Both write non-atomically inside an `except Exception: log`, so a dump error or crash
  mid-write truncates the registry, and nobody is told.
- **Format flip.** Discovery writes raw dicts with `yaml.dump`; EdgeRegistry writes canonicalised rows (fixed key
  order, `tier` always emitted) with `safe_dump`. The file's format depends on which writer touched it last.

## The ruling (director, 2026-10-14)

- **(a) Imports are pure.** `ensure()` at import NEVER writes. It registers the spec in memory, and marks it
  *unpersisted* when the file lacks it, or holds different code-owned fields. This also ends the
  30-rewrites-per-process churn and the format flip, at the root.
- **(b) ONE explicit, atomic writer:** `core/edge_registry_io.py`, which is neutral, so neither engine imports
  another. It holds:
  - the fail-closed read (`RegistryUnreadableError`; an absent file is the only empty registry);
  - the atomic write: serialise first, temp file, fsync, `chmod` to keep the mode, `os.replace`;
  - **ONE row canonicaliser and ONE serialiser for every writer** (ruled from R §4.2; "row canonicalisation stays
    per engine" is withdrawn). Rows use Engine A's key order, extras are appended in their original order, and
    `tier`/`category`/`version` are materialised exactly as Engine A does today. The real 218 rows already
    round-trip byte-identically through both writers, so adopting this is a null diff. Serialisation is
    `yaml.safe_dump(sort_keys=False)`, with numpy/pandas scalars coerced to Python types; anything else
    unrepresentable RAISES. No value validation (`error` and `archived` are live statuses). Every writer passes
    rows through it, Discovery included.

  It is called from explicit steps only: the governor's own save path, `scripts/sync_edge_registry.py` (which
  imports the edge modules and persists what they registered), and the explicit writers below. Never from import.
- **(c) Consumers fail closed at the point of consumption, naming which case:**
  - `_build_production_edges` refuses an UNREADABLE registry (a hard refusal). An EMPTY tradeable set from a
    readable registry renders instead as **Gate 1 NOT_EVALUATED(empty baseline)**, through RR-6a's tri-state
    (ruled from R §3.1). `required_gates` then refuses promotion, the cycle completes, and the record says why. A
    hard refusal there would deadlock Discovery on an empty book forever (6 active + 24 paused today). One
    explicit, labelled **bootstrap mode** (a config key, recorded in the census as `bootstrap_book: true`, never
    canonical for a performance claim) lets a standalone gauntlet seed an empty book on purpose;
  - **ruled 2026-10-14:** `mode_controller._load_edges_via_registry` refuses too. Today an empty or absent
    registry lets `AlphaEngine.__init__` fall back to default edges (`rsi_bounce` + `xsec_momentum`), silently.
    That is the "measured the wrong edge" failure `scripts/run_per_edge_isolation.py`'s docstring records;
  - **isolation mode** (`exact_edge_ids`) has its own rule (R §3.2): every requested id resolves, or the run
    refuses with a message naming the sync. Today a missing id prints `not found` and continues with fewer edges
    (`mode_controller.py:622`).

  Where genuine graceful degradation is required (the offline/paper sandbox), the run degrades ONLY with an
  explicit `degraded` flag that the census treats as a FAIL, per `[NN-FAIL-CLOSED]`.
- **(d) The 30 import-time `try:` wrappers stay.** They no longer hide a write. Narrowing them is a later hygiene
  unit.
- **Engine F (brief v2 rulings).** A failed registry save RAISES, after the run's own artifacts are written:
  - `performance_summary.json` carries `post_run_failure: {stage, error_type, message}`;
  - `assert_census` marks the run NON-CANONICAL on that field, and the key joins
    `tests/test_contracts.py::KNOWN_DOWNSTREAM_AUGMENT_KEYS` with a justification line;
  - `run_backtest` holds the failure across the summary write, then re-raises;
  - `lifecycle_history.csv` is appended only after the registry save succeeded.

  Affected paths: `run_backtest`'s post-run, the local simulated paper loop, and the `analytics.edge_feedback`
  CLI.
- **Design points confirmed as intended:**
  - (1) unpersisted in-memory registrations are INVISIBLE to consumers, because the file is the sole authority;
  - (2) code-owned field drift (category, module, version, params, today re-merged on every import) is merged
    only at the sync, which REPORTS each drifted field it writes; status and tier stay write-protected as now;
  - (4) a fresh checkout refuses until the sync runs.
- **The params merge is KEY-WISE, never wholesale** (ruled from R §4.1). Code-owned keys are the module's
  `DEFAULT_PARAMS` keys. Where code and registry values differ, **CODE wins**, reported as "drift applied". Every
  other params key is preserved verbatim and reported as its own class. Today's `edge_registry.py:306`
  (`s.params = spec.params or s.params`) is a wholesale replacement: measured, `momentum_factor_v1` lost its
  `params.validation_note` on one import. Kept as written, a sync would drop `validation_note` /
  `validation_sharpe` / `fitness_score` on every run. A TYPE change is reported separately. A key the code no
  longer reads is reported for a human and never deleted: the sync cannot tell a stale key from Discovery's
  metadata. Hand-tuned module params that must persist would need an explicit marker (e.g. `params_locked:
  [key]`), out of scope here.
- **The sync's specification:**
  - idempotent;
  - network-dead-ended by construction (importing edge modules must not fetch);
  - keeps the file's mode;
  - reports four DISTINCT classes: *never registered* (additions), *drift applied* (code-owned values changed),
    *registry-only keys preserved*, and *type changes*;
  - `--check` writes nothing and exits non-zero on any of them;
  - `--registry PATH` (`run_per_edge_isolation`'s second call writes the ISOLATED registry, not the default).
- **Not yet ruled — R §4.3, flagged:**
  - Discovery's cycle failure (RR-6a) raises BEFORE `performance_summary.json` is written, while Engine F's
    raises AFTER it, carrying `post_run_failure`. R suggests the Discovery failure use the same field (`stage:
    "discovery"`), so one census rule covers both;
  - "successful save" needs defining per path for the history rule: on the journal path the save IS the journal
    append.

## Who relies on import-time persistence today

Found by grep. The build confirms the set by running it under pure imports.
- **`scripts/run_per_edge_isolation.py`**, explicitly, twice:
  - `_preimport_targets` imports the target modules so edges.yml holds them before `isolated()` takes its
    snapshot;
  - `_populate_registry_inside_isolated` re-imports them INSIDE `isolated()`, because restoring the anchor drops
    them.

  Both become sync calls. The docstring already names the failure they prevent, which makes this the first
  artifact showing the design is honest.
- **The T-122/T-123 gauntlet scripts** (added from R §2): `scripts/run_bab_gauntlet_t123.py`,
  `scripts/run_vrp_gauntlet_t122.py` and `scripts/analyze_vrp_factor_t122.py`. They are the ONLY importers of
  `betting_against_beta_edge` and `volatility_risk_premium_edge`, whose ids exist in the file only while such a
  script runs. Under pure imports those edges never appear, so the scripts call the sync with `--registry` (or
  refuse), depending on the user's archive-or-register decision.
- **Tests that depend on `ensure()` persisting to disk:**
  - `tests/test_edge_registry.py` (21 `ensure` calls, with re-instantiation and file reads);
  - `tests/test_tier_classifier.py` ("ensure must not stomp tier", read back from the file);
  - `tests/test_pairs_trading_edges.py`;
  - `tests/test_fundamentals_edges.py` (`ensure` raising at import);
  - `tests/test_cross_sectional_momentum_edges.py:68` and `tests/test_buyback_dividend_drift_edges.py:55`, added
    from R §2. They construct `EdgeRegistry()` on the REAL, CWD-relative file, are environment-dependent today,
    and MUTATE the real registry as a side effect.

  Each moves to a tmp registry with an explicit register + save, or the sync, so the claim it tests is unchanged.
- **The cloud image** (added from R §2): `Dockerfile.backtest:153` COPYs the building machine's local
  `data/governor/`. The image build runs `sync_edge_registry.py --check`, so an image cannot ship a registry its
  own code disagrees with. The nightly verifier can run the same check.
- **A fresh checkout:** `data/governor/edges.yml` is untracked. The execution manual's first-run path, and the
  README, name the sync as step one.
- **Explicit writers that already write on purpose** keep writing, now atomically through the one writer:
  - `tier_classifier.py:270` (`_save`);
  - `scripts/journal_apply.py:216`;
  - `scripts/migrate_edge_graveyard_tags.py`;
  - `scripts/optimize.py`;
  - `scripts/run_per_edge_isolation.py:169` (`set_status`).
- **Before building, classify each remaining script-side edges.yml toucher in one line:** the snapshot and
  restore copies in `run_substrate_arms.py`, `run_oos_validation.py`, `sweep_cap_recalibration.py`,
  `verify_gate1_cache_determinism.py`, `per_edge_per_year_attribution.py`, `gen_substrate_manifest.py`,
  `reset_base_edges.py`, and `run_foundry_eval_t195.py:48-57` (`restore_clean_governor`). That last one writes by
  `shutil.copyfile` of a known-good anchor and bypasses the one writer, which is acceptable for a copy, but the
  brief says so.

## Locks

Each lock is proven by reverting only its fix. R's seven (§6) are included in full.
1. **Pure imports, measured:** import every auto-registering edge module against (a) a planted corrupt registry
   and (b) a healthy COPY of the real registry. sha256 AND mtime are unchanged in both, and the import succeeds.
   The lock ENUMERATES the modules it proves pure, which settles R's 29 against the brief's 30.
2. **Key-wise params merge:** a planted registry-only params key survives a sync. A code-owned key whose value
   differs takes the code value and is reported as "drift applied". A type change is reported as its own class.
3. **Byte identity across three writers:** the same registry, saved through Discovery, Engine F and the sync,
   produces ONE sha256, including a row that Discovery wrote first.
4. **The empty-book path renders, not crashes:** a readable registry with zero tradeable edges gives Gate 1
   NOT_EVALUATED(empty baseline), promotion refused by `required_gates`, and the cycle completes. Bootstrap mode
   promotes, and the census carries `bootstrap_book: true`. An UNREADABLE registry is a hard refusal.
5. **Isolation mode refuses a missing id**, naming the sync.
6. **First-sync report:** additions ("never registered"), drift applied, registry-only keys preserved and type
   changes are distinct classes. `--check` exits non-zero on any of them and writes nothing. A sync with nothing
   to change leaves the bytes identical AND the mtime untouched.
7. **The fleet never imports an edge module:** a lock over `paper_trader/`, `live_trader/` and
   `scripts/run_paper_cloud_day.py`, not a grep.

Also kept:
- `_load_edges_via_registry` refuses an unreadable or empty registry in default mode and never falls back to
  default edges;
- a fresh checkout refuses until the sync runs, then succeeds;
- **Engine F:** a planted dump error leaves the bytes untouched and raises; no history row is appended after a
  failed save; `post_run_failure` lands in the summary and the census says NON-CANONICAL; `run_backtest` writes
  the summary, THEN raises.

## Sequencing

R's design read is DONE: build it, with its §4 absorbed above as rulings. The registry unit (`a3ac70c`) is on
main, and the no-promotion constraint is lifted for the local path. Two steps remain before code:
1. **The USER's go-ahead** on this three-engine design;
2. **The USER's decision** on the three never-registered edges (archive or register), which must come before the
   first sync against the real file.

The build is then propose-first, with R reviewing and the director merging.
