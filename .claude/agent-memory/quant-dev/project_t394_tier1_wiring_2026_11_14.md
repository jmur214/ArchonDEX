---
name: t394-tier1-wiring
description: T-394 (2026-11-14) wired the 11 pinned Tier-1 Stooq corrections into the cutover writer (era_tr.build_file(changes=), stooq_tier1.py pins); byte-identical to T-390's render 575/575 incl. the real driver on a copy; how bit-identity across two code paths was kept
metadata:
  type: project
---

Branch `feat/era-tr-tier1-corrections-t394` from main (not merged at writing). Proposal
`docs/Sources/proposal_era_tr_tier1_wiring_t394_2026-11-14.md`; runbook §7 appended.

**What exists:** `engines/data_manager/stooq_tier1.py` (sha256 PIN constants for
`config/stooq_corrections_tier1.json` — 11 rows — and `config/stooq_corrections_unverified.json` — the Tier-2
label, 1,579 rows / 374 files + 3 known omissions); `era_tr.build_file(changes=)`, `correction_factor`, audits
take `changes`; `tr_writer.era_tr_rewrite(stooq_corrections=)`; `cutover_step1_pass era-tr` loads the pinned
table by default (`--stooq-corrections none` = v5, recorded); census keys `n_stooq_tier1_applied/rows`,
`n_unverified_stooq_corrections`, `n_stooq_label_not_recorded`. Target bytes:
`config/era_tr_tier1_bytes_t394.json`. Measure: `scripts/era_tr_tier1_measure_t394.py export-table|run|manifest`.
Writer check copy: `~/Dev/_substrate_candidates/t394_writer_check_2026-11-14/` (818 MB, 575 written, all equal).

**Lessons:**
- **Bit identity across two code paths needs the same multiplication ORDER.** T-390 rendered v5 text, read it
  back, × correction. The writer must do `vals*factor` then `*corr` as two steps; `vals*(factor*corr)` changes
  last bits and breaks the md5 (reversion-proven). to_csv/read_csv(round_trip) is lossless, so "read back" =
  the in-memory float.
- A constant back-adjustment changes earlier years' log returns by ~1e-13 pp: `DataFrame.equals` against the
  base run is False for rows that did not "move". Compare with a tolerance and say so.
- Export the target bytes from the SOURCE branch before switching (a worktree holds one branch): I saved
  T-390's render md5s + texts to its candidates dir first, then declared them as the target before measuring.
- The driver only writes under `CANDIDATES_ROOT`; a driver-level test must monkeypatch `cs.CANDIDATES_ROOT`.
- Pin a data table by a sha256 CONSTANT IN CODE (not a sibling .sha256 file): tampering then needs a code diff.

**How to apply:** re-run `era_tr_tier1_measure_t394.py run` after any change to era_tr/tr_writer; identity is
575/575 or it is a regression. See [[t390-stooq-corrections]], [[t393-era-tr-distribution-guard]],
[[t387-cutover-era-tr-writer]].
