# Proposal: wire the 11 Tier-1 Stooq corrections into the cutover writer (T-394)

**For:** the director, then **the USER** (a change to what the cutover writes; `[NN-SUBSTRATE-REVERIFY]`).
**Status:** §1 PRE-DECLARED, committed alone before any code. **N_trials: 0** (wiring; no new measurement
of any strategy, and no new rule).

**What this wires:** T-390's corrections table, rebuilt on v5 and reviewed SOUND for Tier 1 only
(`docs/Sources/proposal_stooq_repair_t390_2026-11-13.md` §10–§11, branch `research/stooq-repair-t390` @
`c1610fb`). Tier 1 is the 11 applied rows that T-265 covers and agrees with. Nothing here re-derives a
row or changes a rule.

---

## §1. What the writer does, and the acceptance — PRE-DECLARED

### 1.1 Exactly eleven rows are applied

They are read from a committed table, `config/stooq_corrections_tier1.json`. Each row carries its file,
kind, date (and end date for a block), log amount, T-265's own measurement of the same event, and the
8-K filings on or near the date where the EDGAR panel has one.

| file | kind | date | log amount (yfinance) | T-265 |
|---|---|---|---|---|
| APD | spin-off step | 2016-10-03 | −0.0778 | −0.0779 |
| CAG | spin-off step | 2016-11-10 | −0.2507 | −0.2508 |
| DOC | spin-off step | 2016-11-01 | −0.0935 | −0.0938 |
| HLT | spin-off step | 2017-01-04 | −0.0298 | −0.0298 |
| HON | spin-off step | 2018-10-29 | −0.0312 | −0.0313 |
| HPE | spin-off step | 2017-04-03 | −0.2888 | −0.2897 |
| HPE | spin-off step | 2017-09-01 | −0.2538 | −0.2538 |
| IBM | block (one bar) | 2019-08-12 → 08-13 | +0.0033 | +0.0032 |
| MRK | block (one bar) | 2019-08-12 → 08-13 | +0.0083 | +0.0083 |
| TJX | block (one bar) | 2019-08-12 → 08-13 | +0.0035 | +0.0034 |
| KG | block (one bar) | 2018-02-12 → 02-13 | −0.0072 | −0.0073 |

- **A step** of log amount s at date e multiplies every bar before e by exp(s).
- **A block** of offset δ over [a, b) multiplies the bars a … b−1 by exp(−δ).
- Both are one profile, exp(Corr(t) − Corr(seam)), as T-390 §1.2 R4 declared.
- The amounts are the exact floats of T-390's table, not the rounded figures above.

### 1.2 The pin

- The table's sha256 is a constant in the code (`engines/data_manager/stooq_tier1.py`). A table that does
  not hash to it is REFUSED before any file is read. A test asserts the shipped file matches the constant.
- The Tier-2 label file (1.4) is pinned the same way.
- Each rewritten file's write record carries the table's sha256 and every row applied to it.

### 1.3 How it is applied — and why the bytes must equal T-390's

- `era_tr.build_file` gains an optional `changes` argument (date → change of the daily log return).
- The pre-seam OHLC is first multiplied by v5's own factor, then by the correction profile, as two
  multiplications. T-390 rendered v5's text, read it back and multiplied; the two-step order reproduces
  the same floats, so the bytes can be compared.
- The write-time rails absorb the changes: the step audit expects each change on its bar; the splice
  audit expects a change that lands on the seam bar.
- With no `changes`, `build_file` is v5, byte for byte.
- The cutover driver (`cutover_step1_pass era-tr`) loads the pinned table by default. Running without it
  (`--stooq-corrections none`) is allowed, writes v5, and is recorded in every row and write record.

### 1.4 Tier 2 is NOT applied; it is carried as a label

- 1,579 rows on 374 files (38 steps, 1,541 block re-levels) are yfinance-derived and unverified.
- They ride in a second committed, pinned file, `config/stooq_corrections_unverified.json`: per file, the
  step dates, the block spans and the counts.
- The writer copies a file's entry into its write record as `unverified_stooq_corrections`. The
  convention census reads it back: how many names carry such a label, and each name's counts.
- A record written without the table says so (`unverified_stooq_corrections: null`), and the census
  counts it as "not recorded". It is never read as "nothing unverified".

### 1.5 The writer REFUSES

1. a table (or label file) whose sha256 is not the pinned one;
2. a row whose file is not a merged file with pre-seam bars in the copy's merge record (checked for the
   whole table before the first file is written);
3. a row whose date, or a block's end date, is not a bar of that file;
4. a row dated on or after the seam, or a block that ends after the seam (it would land outside the
   pre-seam span);
5. a row within three bars of an ex-date that v5's guard refused or repaired in that file (the guard and
   the table must never both act on one event). No such row exists today; the refusal is locked by a
   planted case;
6. two rows for one file and date.

A refusal writes nothing for that file. The rewrite still never runs twice: a file whose pre-seam span is
already `era_tr` is refused as before.

### 1.6 Known omissions — recorded as labels, NOT applied

The reviewer named three defects that Tier 1 leaves in v5. They go into the label file as
`known_unapplied` on their files, and are candidates for a later pre-registered row:

| file, date | what is known | why it is not a row |
|---|---|---|
| GE 2019-02-26 (Wabtec) | Stooq is 3.93 % below yfinance and 3.98 % below T-265 on the day; GE 2019 fails test (i) at −3.95 pp | T-390's market gate refused it (Stooq's own three-day move against the Stooq market was +6.9 %) |
| HON 2018-10-01 (Garrett) | Stooq is 1.11 % below both references; HON 2018 fails (i) at −1.14 pp after the Resideo row | the same gate refused it (+0.4 %) |
| APD 2016-09-29 | a separate dividend-sized Stooq offset (+0.57 %) two bars before the Versum step; APD 2016 fails (i) at +0.59 pp after the Versum row | not a corporate-action step; below T-390's 1 % floor |

### 1.7 The acceptance

1. **Byte identity, 10 files.** The writer's output for APD, CAG, DOC, HLT, HON, HPE, IBM, KG, MRK and
   TJX equals T-390's own v5 + Tier 1 render (exported from `c1610fb` to
   `~/Dev/_substrate_candidates/stooq_repair_t390_v5/tier1_render/render_md5.json`).
2. **Byte identity, 565 files.** Every other file equals v5 (v4's `MANIFEST.md5`, or
   `config/era_tr_v5_delta_t393.json` for DHR, ETN, XRX).
3. **T-384 §1, unchanged, in memory:** (i) 54 failing name-years; (ii), (iii) and (iv) exactly as v5; the
   step audit with 0 unexpected steps. Every acceptance CSV equals T-390's Tier-1 run row for row.
4. **The real writer, end to end.** `cutover_step1_pass era-tr` on a fresh copy of the canonical inputs
   writes files with the same md5s as (1) and (2), and each of the 10 records names its rows and the
   table's sha256.

If any of these fails, it is reported as a failure.

### 1.8 What this is not

- It adds no row beyond the 11 and changes no T-390 rule.
- It does not touch the canonical cache. The cutover itself is a separate, approved act.
- Its evidence is in-sample, as T-390 §10.0 states. Tier 1 is defined by T-265, so "(i) = 54" restates
  that definition; the per-row agreement is the evidence.

---

## §2. What was built

- **The tables.** `config/stooq_corrections_tier1.json` (the 11 rows; each with T-265's measurement and the
  8-K filings within five business days) and `config/stooq_corrections_unverified.json` (the Tier-2 label:
  1,579 rows on 374 files, plus the three known omissions). Both are pinned by sha256 constants in
  `engines/data_manager/stooq_tier1.py` (`fa53978c…` and `60902ac0…`).
- **The build.** `era_tr.build_file(changes=…)` and `era_tr.correction_factor`. The correction is a second
  multiplication after the (a′) factor. `era_tr.step_audit` and `era_tr.splice_audit` take the same
  `changes`.
- **The writer.** `tr_writer.era_tr_rewrite(stooq_corrections=…)` validates the file's rows
  (`stooq_tier1.changes_for_file`) or refuses, then records `stooq_corrections` (table sha256, tier, each
  applied row) and `unverified_stooq_corrections` in the `era_tr` block.
- **The driver.** `cutover_step1_pass era-tr` loads the pinned table by default and checks that every row
  names a merged file of the copy before the first write. `--stooq-corrections none` writes v5 and says so.
- **The census.** `convention.substrate_convention_record` reports `n_stooq_tier1_applied`,
  `n_stooq_tier1_rows`, `n_unverified_stooq_corrections`, `n_stooq_label_not_recorded` and the per-name
  `stooq_corrections`.
- **The target bytes.** `config/era_tr_tier1_bytes_t394.json` holds the md5s of T-390's own render for the
  10 files. It was written from T-390's export before the wired path was measured.

## §3. The result against §1.7

**1 and 2 — byte identity, in memory** (`python scripts/era_tr_tier1_measure_t394.py run`):
- the 10 Tier-1 files: **10 of 10 equal T-390's v5 + Tier 1 render**;
- the other 565: **565 of 565 equal v5** (and T-390's render of them);
- the write-time step and splice audits pass on all 575.

**3 — T-384 §1, unchanged, in memory:**

| test | v5 | v5 + Tier 1 (wired) |
|---|---|---|
| (i) failing name-years (strict passes) | 57 (1,743) | **54 (1,746)** |
| (ii) years passing | 15 of 16 | 15 of 16; the largest change in any of 6,423 rows is 9e-14 pp |
| (iii)(a) / (b) / (c) | 110 of 110 / 6 names fail / 14 of 14 | identical |
| (iv) bytes | 575 of 575 | 575 of 575 |
| step audit: steps, unexpected | 11,094, 0 | 11,109, 0 |
| verdict | FAIL | FAIL |

Every acceptance CSV equals T-390's Tier-1 run row for row (`DataFrame.equals`, all eight files).

**4 — the real writer, end to end.** A fresh copy of the 575 canonical seam files and the merge record
(`~/Dev/_substrate_candidates/t394_writer_check_2026-11-14/`, 818 MB), then
`python -m scripts.cutover_step1_pass era-tr --copy … --tag t394_check`:
- 575 written, 0 refused;
- **575 of 575 written csv files equal T-390's render** (10 Tier-1, 565 v5);
- the 10 changed parquet twins parse to their csv;
- the records name 11 applied rows in total, each file's rows equal the table's, and every record carries
  the table's sha256;
- the records carry 1,579 Tier-2 labels on 374 files (GE: 5 blocks and its known omission);
- the census on the written copy: 575 `era_tr`, 0 unlabelled, 10 files with Tier-1 rows (11 rows), 374
  with an unverified label, 0 not recorded.

**The full suite** on this branch: 4,888 passed, 1 failed, 56 skipped, 11 xfailed. The one failure is the
`edges.yml` capability-ledger contract, which needs a gitignored file this worktree does not have.

**Tests:** `tests/test_era_tr_tier1_t394.py`, 15 locks. 15 reversion runs, every one failing. Three fail
through a different rail than the one named, and are reported as such:
- with the duplicate check off, the row-count check refuses instead;
- with the "already era_tr" check off, the build's proportionality rail refuses a second rewrite (two
  rails stand between a file and a double rewrite);
- with the record's label removed, the test fails reading the missing label.

## §4. What changes on cutover day

`docs/Sources/runbook_cutover_day_2026-11-05.md` §7 (appended) states S1b as it now stands. In short:
- one command, unchanged: `cutover_step1_pass era-tr`. It now writes v5 + Tier 1;
- the acceptance line becomes "565 files equal v5; 10 equal `config/era_tr_tier1_bytes_t394.json`";
- re-pin #2's class of 575 pre-seam rewrites is the same class; 13 of its files differ from v4 (3 by the
  guard, 10 by Tier 1).

## §5. Still open, for the user

- **Tier 2 stays unapplied.** 374 files carry the label. Whether any part is ever wired is a later,
  pre-registered decision (T-390 §11.4).
- **The three known omissions** (§1.6) remain in v5 + Tier 1: GE 2019 (−3.95 pp), HON 2018 (−1.14 pp),
  APD 2016 (+0.59 pp) in test (i).
- **The verdict on T-384's unchanged test is still FAIL.**

## §6. Review follow-up (2026-11-14) — appended; the review's verdict was APPROVE with two LOW findings

1. **The duplicate check is now tested where it alone can catch the defect.** A 12-row table that repeats
   APD's row has 11 distinct (file, date) keys, so the row-count check is satisfied; only the duplicate check
   stands between it and APD's step applied twice (0.1556 instead of 0.0778). The new lock plants exactly
   that table. Reverted, the table loads. The earlier 11-row case could not show this, and is now a separate
   lock on the row count.
2. **A copy written without the table now fails closed where it matters.**
   `--stooq-corrections none` stays available for scratch runs, and the driver prints a SCRATCH MODE line
   when it is used. A copy written that way is refused in three places:
   - **the run census** (`core/census.assert_census`): a panel with `n_stooq_label_not_recorded > 0` is a
     FAILURE, naming the files — the same pattern as an unlabelled name;
   - **`cutover_step1_pass label`** exits 5 and names the files;
   - **`cutover_step1_pass stage`** refuses to stage the copy for a candidate manifest.
   The scan behind the two driver checks reads the write records alone
   (`convention.era_tr_files_without_stooq_label`).
   On the real check copy (`t394_writer_check_2026-11-14/`) `label` reports 575 `era_tr`, 10 files with
   Tier-1 rows, 11 rows, 374 with the unverified label and 0 not recorded. (That command exits 3 there for
   an unrelated reason: the check copy holds only the 575 seam files of the merge record's 730 names.)
3. **Tests:** 19 locks in `tests/test_era_tr_tier1_t394.py` (4 new); 7 further reversion runs, each failing for
   the intended reason.
