# Session Summary: 2026-11-04 — the cutover follow-ups on `dd64793` (branch `cutover-followups`)

## What was worked on

- The six follow-ups the 10-23 execution review of cutover step 1 asked for, each its own commit on
  top of `dd64793`: three dated prose corrections to `docs/Audit/cutover_step1_record_2026_10_22.md`
  (`9a26f7b`); the R9 lock and fix (`9d10dc9`); the kept drip's pre-seam holes as the declared,
  counted `pre_seam_drip_gap` class (`3ef4034`); the MEDIUM PIT-membership identity row
  (`67be1f5`); the record's counts, status line and §9a reversions (this commit's sibling);
  `sync_docs` after the engine edits.
- READ-ONLY on the canonical cache and the cutover copy throughout; the worktree carried the
  mandated per-file `data/` layout (a REAL `data/processed/` of csv symlinks, a copied
  `_merge_meta.json`, an EMPTY real `parquet/`, an EMPTY real `raw/simfin/download/`). No full
  suite (another agent's suites on the shared Mac); targeted runs only.

## What was decided

- **R9 — "an explicit `unmeasured` record", not a halt:** a merge-record convention label with no
  frame to witness it (no `data_map`, or the name absent from it) is UNLABELLED with the reason
  "UNWITNESSED … unmeasured"; the block carries `witness` ("frames" | "unmeasured") and
  `n_unwitnessed`; the gate fails under the existing invariant 10. The write record and a declared
  override need no witness (they describe the file itself). A cache-wide label (the pass driver's
  `label`, the canonical data lock) is witnessed against each file's FIRST bar — what a run loads.
- **The drip class is keyed to the LABEL and witnessed against the FILE:** a hole is excused only
  when the label carries a drip pre-seam span (the label's own resolver), the day is strictly before
  the seam, the file's bars before the seam number exactly the kept count its record carries
  (563/563 on the copy, 575/575 on the canonical — measured first), and the file lacks the day too.
  Counted per name and in total; the reason the rest was not excused travels with the record and
  into the gate's HOLED line. Without `cache_dir` the class is OFF (fail closed). Both producers AND
  the measured-run admission pass the canonical cache (a third call site the brief did not name).
- **Item 1(b)'s one computation:** the guard's own rule — majority-calendar days inside the
  PIT-required spans, strictly before the seam — 384 over 218 drip names, of which AVB 1, BBBY 1,
  LEG 2 already declared, so 380 over 215 undeclared: the guard's count, the class's count, the lock.
- **Item 1(c):** the three stale names are a membership defect in BOTH tables — `sp500_membership.
  parquet` carries the PIT names as current (`included_until = NaT`) and the PIT intervals omit them
  — not a declaration gap (none carries `ends_at_delisting`; DLPH has no declaration at all).

## What was learned

- The record's "11 now served" was arithmetic, not observation: 10 class (i) + 7 relisted + FRC =
  18 = 75 − 57, and 632 → 648 = +13 seams + DAL + 4 defects − SLE − POM. Reconcile a delta name by
  name before writing a cause for it.
- Three different "pre-seam hole" counts (380 / 388 / 393) were three different calendars and spans.
  State the rule before the number.
- A `data_map=None` default is a fail-open in disguise: a witness that is skipped when its input is
  absent passes every lock that never withholds the input. The lock must withhold it.
- The copy's parquet files make the real-copy guard lock 14 s, not 50 s (csv).

## Pick up next time

- The hygiene reviewer's gate, then the merge order (hygiene → stamp → Engine B → registry →
  `fa26a7b` + `dd64793` + this branch), each through the full suite, then push.
- Declared acts still open: the membership-table correction for CCR/DLPH/FSR (the MEDIUM row); SLE's
  class (i) withholding in a cache-wide read; the real-cache write and re-pin #2 (cutover day).

## Files touched

```
backtester/backtest_controller.py
core/census.py
docs/Audit/cutover_step1_record_2026_10_22.md
docs/Sessions/2026-11/2026-11-04_session_cutover_followups.md
docs/State/health_check.md
engines/data_manager/convention.py
engines/data_manager/coverage.py
engines/data_manager/index.md
engines/engine_d_discovery/discovery.py
orchestration/mode_controller.py
scripts/cutover_step1_pass.py
tests/test_contracts.py
tests/test_pre_seam_drip_gaps_2026_11_04.py
tests/test_substrate_convention_census_2026_10_22.py
```

## Subagents invoked

- None (this session was itself a worktree subagent of the director).
