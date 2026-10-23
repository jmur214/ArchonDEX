# Session Summary: 2026-10-22 (Agent B — cutover step 1 on a copy, option (a))

## What was worked on

- Cutover step 1 under the user's OPTION (a) ruling: the writer's SEAM-preserving write (the cached
  pre-seam drip kept, scaled by the measured seam ratio; the post-seam span exact from the provider;
  the provider need only cover the post-seam span), the seam-ratio rail, the declared cache-convention
  defects (the split-only trio, the mixed AMCR), the 13 declared seams, the ten class (i) declarations,
  BK → BNY, `close_unadj` on every written file, and the UNIVERSAL convention label as a census field
  from both producers (fail-closed on an unlabelled name).
- Two full passes over fresh copies of the canonical cache outside the repo (pass 1 before
  `close_unadj` existed; pass 2 = the candidate), the guard and label readings on the candidate, the
  candidate manifest beside the copy. Record: `docs/Audit/cutover_step1_record_2026_10_22.md`.

## What was decided

- The 10-15 copy is the option (b) form (whole-file exact, no write records) and is a record, not the
  candidate; the candidate was built fresh from the canonical by the option (a) writer.
- The kept pre-seam bars are scaled by the ratio AT the seam bar (the seam-day return unchanged; the
  file at the provider's level); a seam ratio that is not the tail's rescale is an undeclared mid-span
  convention change and is refused.
- A candidate census name the substrate cannot label is refused as unlabelled (the discovery-gate
  harness's synthetic name became one the substrate records).

## What was learned

- A test-suite run through a plain `data/processed` symlink WRITES into the canonical cache (a
  non-canonical fundamentals cache miss is fetched and written; a sibling's run did it twice tonight,
  and a SimFin panel rebuild replaced `fundamentals_simfin.parquet` at 23:49). The worktree now holds a
  real `data/processed` of per-file csv symlinks with an EMPTY real `parquet/`. The canonical PRICE
  files are proven untouched (730 csv + 730 parquet, identical before and after).
- Option (a) keeps the drip's own holes: the guard over 2000 → 2025 reads 216 holed on the candidate
  (215 pre-seam only, 388 days; SLE the exception) while 2018 → 2025 is green but for the three
  declared delistings and SLE. The proposal's "one ruling from green" was the option (b) form's.
- Seven symbols the proposal called delisted are now relisted later entities (AVB, EA, EQR, LEG, QRVO,
  SATS, WBD): the span rail refuses them; they need class (i) declarations.

## Pick up next time

- The director's rulings on: the 388 pre-seam holes (declare vs hole-fill); class (i) declarations for
  the seven relisted symbols; the fundamentals miss-branch refusal outside a deliberate refresh (the
  HIGH row); the merge record's retirement at cutover day.
- The full suite was NOT run (halted by the coordinator); run it on a tree whose data layout cannot
  reach the canonical cache, then the cutover-day act: the candidate replaces the canonical, re-pin #2,
  `lift_verified()` per name, the guard switch-on.

## Files touched

```
engines/data_manager/tr_writer.py  engines/data_manager/convention.py  engines/data_manager/yahoo_symbols.py
engines/engine_d_discovery/discovery.py  backtester/backtest_controller.py  core/census.py
config/convention_declarations.json  config/level_declarations.json
scripts/cutover_step1_pass.py  docs/Core/execution_manual.md  docs/State/health_check.md
tests/test_cutover_step1_writer_2026_10_22.py  tests/test_substrate_convention_census_2026_10_22.py
tests/test_contracts.py  tests/test_census.py  tests/test_discovery_gates_7_8.py  tests/test_level_rail_2026_10_15.py
tests/test_tr_writer_2026_10_15.py  engines/data_manager/index.md  scripts/index.md
docs/Audit/cutover_step1_record_2026_10_22.md
```

## Subagents invoked

None (the unit was executed directly in the worktree).
