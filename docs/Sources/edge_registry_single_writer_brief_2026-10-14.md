---
task_id: edges.yml single writer (R's F1 on the registry unit; health_check HIGH 2026-10-14)
title: edges.yml — pure imports, one explicit atomic writer, consumers fail closed (Engines A, D, F)
date: 2026-10-14
author: Agent D
type: DESIGN BRIEF — no code. Spans Engines A, D and F, so it needs the USER's go-ahead (CLAUDE.md, "changes
  spanning 3+ engines"); R's design read; the build starts after the registry unit (a3ac70c) merges.
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
  `live_trader/` never write edges.yml. The build re-verifies that none of them imports an edge module.

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
  - **ONE serialiser** for every writer. Row canonicalisation stays per engine; the bytes on disk follow one policy.

  It is called from explicit steps only: the governor's own save path, `scripts/sync_edge_registry.py` (which
  imports the edge modules and persists what they registered), and the explicit writers below. Never from import.
- **(c) Consumers fail closed at the point of consumption, naming which case:**
  - `_build_production_edges` refuses an UNREADABLE registry, and an EMPTY tradeable set from a readable one: a
    Gate-1 baseline of zero edges is not a measurement;
  - **ruled 2026-10-14:** `mode_controller._load_edges_via_registry` refuses too. Today an empty or absent
    registry lets `AlphaEngine.__init__` fall back to default edges (`rsi_bounce` + `xsec_momentum`), silently.
    That is the "measured the wrong edge" failure `scripts/run_per_edge_isolation.py`'s docstring records.

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

## Who relies on import-time persistence today

Found by grep. The build confirms the set by running it under pure imports.
- **`scripts/run_per_edge_isolation.py`**, explicitly, twice:
  - `_preimport_targets` imports the target modules so edges.yml holds them before `isolated()` takes its
    snapshot;
  - `_populate_registry_inside_isolated` re-imports them INSIDE `isolated()`, because restoring the anchor drops
    them.

  Both become sync calls. The docstring already names the failure they prevent, which makes this the first
  artifact showing the design is honest.
- **Tests likely to depend on `ensure()` persisting to disk:**
  - `tests/test_edge_registry.py` (21 `ensure` calls, with re-instantiation and file reads);
  - `tests/test_tier_classifier.py` ("ensure must not stomp tier", read back from the file);
  - `tests/test_pairs_trading_edges.py`;
  - `tests/test_fundamentals_edges.py` (`ensure` raising at import).

  Each gets the sync, or an explicit register + save, in its setup, so the claim it tests is unchanged.
- **Explicit writers that already write on purpose** keep writing, now atomically through the one writer:
  - `tier_classifier.py:270` (`_save`);
  - `scripts/journal_apply.py:216`;
  - `scripts/migrate_edge_graveyard_tags.py`;
  - `scripts/optimize.py`;
  - `scripts/run_per_edge_isolation.py:169` (`set_status`).
- **Before building, classify each remaining script-side edges.yml toucher in one line:** the snapshot and
  restore copies in `run_substrate_arms.py`, `run_oos_validation.py`, `sweep_cap_recalibration.py`,
  `verify_gate1_cache_determinism.py`, `per_edge_per_year_attribution.py`, `gen_substrate_manifest.py`, and
  `reset_base_edges.py`.

## Locks

Each lock is proven by reverting only its fix.
- **Engine A:**
  - importing a REAL edge module against a planted corrupt registry leaves the bytes untouched, AND the import
    succeeds (it is pure);
  - a clean import writes nothing (sha and mtime unchanged).
- **Consumers:**
  - `_build_production_edges` refuses a corrupt registry, naming "unreadable";
  - it refuses a readable registry with zero tradeable edges, naming "empty";
  - `_load_edges_via_registry` refuses both cases, and never falls back to default edges.
- **One serialiser:** every writer's healthy save of the same registry produces IDENTICAL bytes.
- **Fresh checkout:** with no registry, consumers refuse until the sync runs, and then succeed. The sync is
  atomic, keeps permissions, and reports what it persisted and which fields drifted.
- **Engine F:**
  - a planted dump error leaves the bytes untouched and raises;
  - no history row is appended after a failed save;
  - `post_run_failure` lands in the summary, and the census says NON-CANONICAL;
  - `run_backtest` writes the summary, THEN raises.

## Sequencing

The user's go-ahead and R's design read come first. Then the registry unit (`a3ac70c`) merges, the no-promotion
constraint lifts, and this unit is built propose-first, with R reviewing and the director merging.
