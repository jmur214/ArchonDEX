# Merge record — 2026-10-15 (director): the ticker-kind exclusion unit and the B-1 exposure re-score

> Why this file exists: two merge commits carry the suite result as "passed, 0 failed" with the number
> missing — the director's merge script substituted the count with a `sed` regex (`.*?`) that BSD sed
> rejects, so the substitution produced an empty string. The counts are recorded here, beside the
> commits, never by rewriting them. Same form as `2026-10-14-merge-rr2-record.md`.

## 1. `0435de7` — merge(data): the ticker-kind exclusion for the four ÷10 files (B's `4c57d4c`)

- **R's APPROVE:** `review/agent-r-ticker-exclusion @ fd262e0` (`docs/Audit/ticker_exclusion_unit_review_agent_r_2026_10_15.md`), at the FINAL hash `4c57d4c` (a24bc20 + the SLE addition + the per-ticker reason/ratio/evidence shape).
- **Director's check:** the full suite on the staged merge in the main tree — **4,309 passed, 0 failed**, 22 skipped, 5 deselected, 11 xfailed, 178.26 s. Ancestry confirmed (`git merge-base --is-ancestor 4c57d4c main`).
- **What it is:** a second exclusion KIND (`ticker`, beside `bars`) applied at universe resolution on every `resolve_universe` path and in `clip_membership`; AZO, MTD, NVR, SLE under census key `scale_defect_div10`, reason / declared_ratio / evidence PER TICKER; written by both census producers; `CENSUS_PROVENANCE_KEYS` carries it; the allow-list untouched (invariant 2 holds at 0); `lift_verified()` the re-pin #2 lock; a declaration-matches-today's-cache tripwire.
- **Follow-ons assigned (not blocking):** SLE re-kinded to class (i) with NO lift (the code at 4c57d4c would lift SLE on a ×10 write of the wrong entity — R's condition (4)); re-pin #2 calls `lift_verified()` per name (AZO, MTD, NVR) and flips the declaration test in the same commit (cutover §6); the direct-glob gap → a LOW contract test (B).

## 2. The B-1 coverage figures in `27c47b8`'s merge message are OVERSTATED (A's §14.3, 2026-10-15)

The verdict's merge message (and the first ledger row) quoted "PIT coverage 54% in 2000; 49.0% of months under 80%". The B-1 census's `coverage_pct` counted FILE EXISTENCE, not a bar at the month-end. True panel coverage: **38.4% in 2000-01** (not 52.7%); **207 of 312 months below 80%** (not 153); the last sub-80% month **2017-03** (not 2012-09); member-weighted **70.2%** (not 79.8%). The frozen 2012 window's ">80% coverage" premise does not hold on the rows actually formed; it stays a sensitivity row. The verdict's §14.3 carries the correction; the ledger row and CURRENT_STATE are corrected in the commit that adds this file.

## 3. `f1f50fc` — merge(b-1): the post-hoc EXPOSURE re-score at A's `8a0081f`

- **R's APPROVE:** `review/agent-r-b1-exposure @ bb1b40a` (ca62fa6) and the re-approve BY DIFF at `b665bba` §7 (ca62fa6..8a0081f: forbid_network() first in main(); the exact 'load_local_env: offline by design' literal; both new locks fail when reverted; R's re-run cmp-identical to rescore_05828515e998.json).
- **Director's check:** the first staging at `ca62fa6` was RED on `tests/test_env_entries_2026_10_15.py::test_every_entry_that_reaches_the_data_layer_calls_the_helper` (1 failed / 4,294 passed) and was backed out; the staging at `8a0081f`: the full suite on the staged merge — **4314 passed, 22 skipped, 5 deselected, 11 xfailed, 312 warnings in 215.55s (0:03:35)**. Ancestry confirmed.
- **Result:** both value signals still FAIL after BH with AZO/MTD/NVR removed (earnings yield BH p 0.9987 → 0.9776; the wealth leg clears neither benchmark; book-to-market likewise); NO CHANGE to the verdict; H1 NOT MET stands; N_trials 4 → 6.

## 4. Merged in the same pass (docs only, the docs-only guard + doc_lint)

- `5aa5242` — A's §14 (c723bd6; R-APPROVED at a50e397 §8): 180 stale member-months, 158 selected by momentum_12_1_v1 then lost; a weaker null, not a flipped one.
- `6a99c8c` — B's 9162706: the band SHOWN by replay, the 114 holed files (81 fixed by the pass, 33 unfillable → declared data_gaps), option (a) corrected (post-seam rewritten under (a) too), SLE/POM to class (i), §6 calls lift_verified() per name.
