---
name: t387-cutover-era-tr-writer
description: T-387 (2026-11-12) put option (a′) into the cutover writer as label era_tr; byte-identical to v4 (2cee41ef…); what was proven, what parquet/derived-column choices made identity hold, and the traps (label inheritance, k≈1 hides a splice rail, disk at 11 GB)
metadata:
  type: project
---

USER RULING 2026-11-12: the cutover adopts T-384 (a′) v4. T-387 built it on branch
`feat/cutover-a-prime-writer-t387` (commit ec5a1d7; propose-only, not merged at writing).

**What exists:** `engines/data_manager/era_tr.py` = the ONE (a′) implementation (the T-384 script imports
it); `tr_writer.era_tr_rewrite` = offline pre-seam rewrite drip → `era_tr` with write-time step + splice
audits; CLI `cutover_step1_pass era-tr` (+ `fresh-copy --from`). Acceptance check dir:
`~/Dev/_substrate_candidates/t387_writer_check_2026-11-12/` (575 rewritten files + era_tr_*.jsonl rows).

**Byte identity held because (keep these if the writer is touched):**
- parquet = parsed FROM the csv text, Date index `datetime64[us]` — canonical, the step-1 copy and v4 all
  share that layout (pandas 3.0.1 / pyarrow 23.0.1). Writing to a tmp path then `os.replace` gives identical
  bytes (no filename in the file).
- `tr_writer.with_derived_columns` (via set_index/reset_index) is byte-equal to the merge's
  `_recompute_derived` — proven by the 1,150-file identity, so the engine never loads a script by path.
- the copy's 9th column (`close_unadj`) is carried as TEXT tails per line, never re-rendered.

**Traps found:**
- A label constant swap would mislabel: the pre-cutover cache IS drip; a post-cutover `full_refetch` must
  inherit the KEPT span's label from the file's record (`kept_pre_seam_convention`), not the seam spec.
- A splice rail whose tolerance comes from rule-1's 1e-9 proportionality (1e-8) does NOT fire when k≈1
  (planted merge: k−1 ≈ 5e-9). Proving the rail needs a planted post-seam Stooq block (T-384's k lock).
- Step-1 copy facts: 563 of 575 seam files carry drip records; 12 (AVB BBBY CTRA EA EQR HOLX LEG POM PSKY
  QRVO SATS SLE) have NO record (refused in step 1) — the rewrite must create one or the merge-meta
  fallback would still label them drip. Copy's `_merge_meta.json` md5 = canonical's.
- On the real copy (dry run) (a′) pre-seam = v4 × ONE constant per file (copy seam close ÷ canonical's) to 8.9e-16.

**Why:** cutover day needs a writer, not a script; re-pin #2 grows by the 575 pre-seam rewrites.
**How to apply:** any change to era_tr/tr_writer → re-run the byte-identity check (copy the 575 canonical
seam files + meta, `era-tr`, compare to v4 MANIFEST `grep "  processed/"`). Related: [[drip-double-count-stooq-eras]].
