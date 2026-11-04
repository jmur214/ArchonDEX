# Session Summary: 2026-10-22 — the edges.yml single-writer unit (brief v4) and the archive of three refuted edges

> Worker session in an isolated harness worktree (`worktree-agent-af68d33f8731414c3`), building the
> user-approved design `docs/Sources/edge_registry_single_writer_brief_2026-10-14.md` (R: BUILD IT).
> Propose-first: nothing merged here; the director merges after R's review.

## What was worked on

- **The archive (first commit):** `betting_against_beta_edge`, `overnight_intraday_edge`,
  `volatility_risk_premium_edge` (REFUTED: T-123/T-129, T-135 with T-157, T-122/T-174; never in the
  registry) `git mv`'d into `Archive/engines/engine_a_alpha/edges_refuted_2026_10/` with a README, and
  their only importers (`run_bab_gauntlet_t123`, `run_vrp_gauntlet_t122`, `analyze_vrp_factor_t122`)
  into `Archive/scripts/edges_refuted_2026_10/`. The frozen B-1 inventory
  (`scripts/build_signal_panel_b1.py`, prereg §4/§5.2) resolves its two archived entries from the
  archive path (the one edit in the archived modules: an absolute `edge_base` import).
  `tests/test_edge_classes_registered_or_archived.py` pins the contract.
- **The single writer:** `core/edge_registry_io.py` — the ONE fail-closed reader, ONE row
  canonicaliser, ONE serialiser, ONE atomic writer (serialise first, temp file, fsync, mode kept,
  `os.replace`; `RegistryWriteError` with the bytes untouched). Engine A (`EdgeRegistry`), Engine D
  (`save_candidates`) and Engine F (`lifecycle_manager`, `evolution_controller`) all write through it.
- **Pure imports:** `EdgeRegistry.ensure()` records an in-memory registration and never writes;
  `scripts/sync_edge_registry.py` is the ONE explicit step that persists registrations (key-wise params
  merge, four report classes, `--check`, `--registry`, network dead-ended by construction);
  `Dockerfile.backtest` runs `--check`. The first sync on the real 218-row registry is a byte-identical
  null diff (locked against a frozen fixture, `tests/fixtures/edges_registry_snapshot_2026_10_22.yml`).
- **Consumers fail closed:** `_load_edges_via_registry` refuses an empty/absent registry in default mode
  (`EdgeLoadRefusal`, naming the sync; never the default-edge fallback) and a missing id in isolation
  mode; `_build_production_edges` refuses an unreadable registry (hard) and `validate_candidate` renders
  a readable empty book as Gate 1 NOT_EVALUATED(empty baseline) — the labelled `bootstrap_book` config
  mode seeds on purpose, recorded in the census by BOTH producers, never canonical for a backtest.
- **Engine F / post-run (R §4.3):** a registry save failure RAISES (no history row after a failed save);
  `ModeController._post_run` HOLDS a governor registry failure or a Discovery cycle failure, writes both
  `performance_summary.json` copies with `post_run_failure: {stage, error_type, message}`,
  `assert_census` says NON-CANONICAL (invariant 10), THEN re-raises. `run_paper` and the
  `analytics.edge_feedback` CLI let the failure through.
- **Locks:** 27 in `tests/test_edge_registry_single_writer.py` (every brief/R §6 lock, each driving the
  real entrypoint — two in subprocesses) + 3 archive-contract tests; reversion proof
  `scripts/registry_single_writer_reversion_proof.py` (17 cases). Existing tests migrated to tmp
  registries + the sync (the brief's list, plus R §2's two env-dependent ones); the gauntlet tests'
  empty-baseline stubs made faithful (one baseline edge) rather than relaxing the new guard.

## What was decided

- **`--check` fails only on what a sync would CHANGE** (additions, drift, type changes). The brief's
  "exits non-zero on any of them" read literally would include "registry-only keys preserved", which
  the real registry carries permanently (`validation_note`, Discovery's verdict fields) — `--check`
  would then never pass and could not gate the image build. R §6 says "additions, updates and drifted
  fields"; built that way, registry-only keys reported but not failed.
- **Bootstrap on a candidate census is a record, not a failure;** on a BACKTEST census it is
  NON-CANONICAL. Failing the candidate census on it would make the labelled bootstrap unable to promote
  — the deadlock the mode exists to break.
- **Six fundamentals modules' narrow import-time wrappers** (`except (FileNotFoundError,
  PermissionError, OSError)`) now also swallow `RegistryUnreadableError`: ruling (d) keeps the wrappers
  and R §5 says a refused read is swallowed at import and caught at the consumer; without it a corrupt
  registry failed those six IMPORTS. Programmer errors still propagate (their existing lock holds).
- **The sync EXECUTES each module's registration (reload when already imported)** rather than
  remembering one from an import it did not control — found when in-process syncs in the test session
  saw nothing after a module had been imported under another cwd.
- **The three gauntlet scripts were archived, not repointed:** running them would re-propose a refuted
  edge (the brief's "or refuse").
- **Discovery is skipped when the governor's registry save failed** in the same post-run: the registry
  was never updated and the run is already failed; compounding it with candidate writes is wrong.

## What was learned

- Importing the 30 edge modules against a copy of the real registry CHANGED it (sha `edf1ff…` →
  `cc5e59…`) in this worktree before the unit — the live defect, reproduced on the way in; after the
  unit the same import leaves bytes and mtime untouched (lock 1, measured in a subprocess).
- `tests.test_discovery_gates_7_8._wire_validate_candidate_happy_path` stubbed the production baseline
  as an EMPTY book, so 24 gauntlet tests only passed because an empty baseline was silently measured
  against — R's F3 exactly. The stub is now one faithful edge.
- A harness worktree carries no `data/`; `scripts/setup_agent_worktree.sh`'s layout (symlinked bulk
  dirs, a per-worktree COPY of `data/governor/`) was reproduced by hand so the suite count compares.

## Pick up next time

- R's review of this branch, then the director's merge; after the merge, run
  `python scripts/sync_edge_registry.py --check` in the main tree (expected: in sync, exit 0) and
  rebuild the backtest image (its build now runs the check) — the first artifact.
- A later hygiene unit: narrow the remaining `except Exception: pass` import-time wrappers (ruling (d)).
- `scripts/per_edge_per_year_attribution.py:65` and `cockpit/dashboard_v2/utils/capital_allocation_loader.py`
  read edges.yml with raw `yaml.safe_load` (read-only, outside the measurement path) — classify-only here.

## Files touched

See the branch's commits (`git log --stat cce5d5e..HEAD`).

## Subagents invoked

- None (a single worker; the sibling suite run on this machine was another worker's).
