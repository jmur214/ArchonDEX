# CUTOVER-DAY RUNBOOK — DRAFT for the user's review (director, 2026-11-05; propose-first)

**Status:** PROPOSED. Nothing here runs until the user says so; cutover day is a separate approved act
(the step-1 record §13). The candidate exists and is verified; this document is the ORDER of the day, each
step with its command of record, its artifact, its refusal, and what it waits on. Sources: the cutover proposal
(`docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md` §3.2, §5, §6), the step-1 record
(`docs/Audit/cutover_step1_record_2026_10_22.md`), the guard proposal's writer inventory
(`docs/Sources/proposal_price_cache_convention_guard_2026_10_15.md` §4), the re-pin #1 record
(`docs/Sources/proposal_repin_1_drip_substrate_2026-11-05.md`), the user's ruling of 2026-10-22 (option (a)).

## 0. What the day changes, and what it does not

- CHANGES: the canonical price cache `data/processed/` (the exact-TR copy replaces the drip cache in ONE
  step, every rewritten file carrying `close_unadj`); every pin the cutover moves (§3); the anchor
  (`_isolated_anchor/`, a canon change — T-376); `config/substrate_manifest.sha256` (re-pin #2); the S3 prefix;
  the backtest image; the four anchors in `config/anchors.json` (new entries added, the old kept as history).
- DOES NOT CHANGE: any live trading input (cutover proposal §3.1: the paper fleet reads Alpaca at run time
  and bakes no file the cutover rewrites; `tr_reconciled/` is outside it). No redeploy. No real-money path.

## 1. Pre-conditions — every one holds, or the day does not start

| # | condition | how it is proven |
|---|---|---|
| P1 | T-377 (D's half of the submit gate) and T-378 (the T-219 selection rule) MERGED on main | the ledger rows read `done`; `anchors_registry.py verify` exit 0 |
| P2 | The candidate is still the fixed object the step-1 record pinned | `gen_substrate_manifest.py verify --root <staging_root> --manifest ../<candidate>.sha256 --stamp-root <staging_root>` → 0/0/0 (14,902 files) |
| P3 | The candidate's guard and label readings reproduce | `cutover_step1_pass guard --cache <copy> --start 2000-01-03 --end 2025-12-31` → holed 1 (SLE, declared); `label --cache <copy>` → 0 unlabelled |
| P4 | The canonical is untouched since re-pin #1 | `gen_substrate_manifest.py verify` → OK on main; the latest janitor row `substrate_verify PASS` |
| P5 | The guard switch-on commit (S3) is BUILT and REVIEWED BY EXECUTION on a branch against the copy, not yet merged | the review's APPROVE in the merge message; nothing on main yet |
| P6 | The pairs-manifest decision is made and locked (S5) | one of: `data/research/cointegrated_pairs_2026_05_09.json` pinned by name + baked; or the in-image check proven to tolerate a registry-only row |
| P7 | Disk ≥ 15 GB free; no suite, no agent, no campaign running | `df`; `pgrep -f "pytest tests[/]"` empty; `aws batch list-jobs` shows nothing RUNNABLE/RUNNING on the backtest queue |
| P8 | The user's go, with the date | this document's status flipped to APPROVED by the user |

## 2. The day, in order — a refusal at any step HALTS the day (abort = §4)

- **S1 Freeze.** No suites, no agents, no fleet touch for the duration. The janitor's next night run is the
  post-day verifier; the fleet is unaffected by design (§0).
- **S2 The one-step replacement, never a delete.** The canonical `data/processed/` is QUARANTINED BY RENAME to
  `/Users/jacksonmurphy/Dev/_substrate_candidates/canonical_pre_cutover_<date>/` (outside the repo; [NN-ARCHIVE]);
  the copy's `data/processed/` moves into place (one `mv`). Artifact: the quarantine's file count equals the
  pre-move count; the new `data/processed/` md5 listing equals the candidate manifest's lines for that tree.
- **S3 The guard switch-on commit (merged on the day; built and reviewed before — P5).** Every writer in the
  guard's §4 inventory routes through the convention writer or REFUSES in canonical runs — above all
  `DataManager.save_cache`'s live path for an uncached ticker (R's O-3: `full_refetch` or refuse); the
  `backfill_t052` and `fetch_missing_delisted` writers routed or refused; `lift_verified()` called per declared
  name (AZO, MTD, NVR; NEVER SLE) with each declaration test flipped to the restored level IN THE SAME COMMIT;
  the write log quoting the five LEGACY-W residuals (CAT +0.0019, ZTS +0.0043, LOW +0.0048, PG +0.0075,
  CVS +0.0087). Artifact: the full suite green on the staged merge with the NEW cache in place.
- **S4 The dependent pins, re-pinned together (cutover proposal §3.2).** `tests/test_golden_master.py`'s golden
  regenerated; `PRE_RR1_GOLDEN` RETIRED with the reason in the test and RR-1's §4 (the number stays in the
  record); the DAL declaration re-declared with the ruling; the T-219 recompute from the pinned snapshot INTO
  the real file — `build_pit_cap_history_t219.py --from-snapshot data/universe/delist_shares_snapshot.parquet
  --out data/universe/market_cap_tiers.json` with the selection rule in force (T-378). **Its whole-file diff on the
  step-1 copy is EMPTY by construction** (the T-219 reviewer's measurement, 2026-11-05, locked: the writer wrote only
  what the provider served, so every cohort name it wrote ends at the bulk and is kept, and every one it did not
  write is June's input, rewritten identically) — the EMPTY diff is the correct artifact; a non-empty one is a
  finding. The DECLARED-list guard (names the pass refused as `span`/`convention`/class (i) must never be written
  as "delisted by the cache") is owed before any RE-FETCHED snapshot is ever used, not for this step. The T-306 SPY
  leg and `ohlc_features_t150` re-labelled per §3.2. B-1's "must
  reproduce" md5s are re-recorded by B-1's own re-run (§5 — after the day, not on it).
- **S5 The RE-ANCHOR (T-376).** `sync_edge_registry.py --check` exit 0 on the live registry first; then
  `python -m scripts.run_isolated --save-anchor` (writes + chmods the anchor 0o444) — the anchor now carries the
  nine edges the May anchor lacked; then `sync_edge_registry.py --check --registry
  data/governor/_isolated_anchor/edges.yml` exit 0 — the image's own check, run locally BEFORE the push
  (P6 decides the pairs edge). Artifact: the anchor files' new sha256s; the check's exit 0.
- **S6 Re-pin #2.** `python3 scripts/gen_substrate_manifest.py generate` in the MAIN tree (the committed default,
  no `--stamp-root`; anything else refuses) → the stamp PASS by writer `repin`; the manifest diff reviewed CLASS
  BY CLASS (every rewritten price file; the anchor files; the tiers file; nothing else) and committed with this
  runbook's record section. Artifact: `verify` → OK; the diff's class counts equal the candidate's written set.
- **S7 Publish the prefix BEFORE the push.** `_director_tools/repin1_s3_publish.sh stage` (hardlinks exactly the
  committed manifest's files; verifies the stage 0/0/0) → `upload` (refuses a non-empty prefix; object count ==
  manifest lines; every changed/new path + a 25-file sample sha256-equal; the registry companion after
  `--check` exit 0). Artifact: the proof lines in the log.
- **S8 Push, then the image.** The delegated pre-push checks; `git push origin main`; the CI build fires
  (`engines/**`, `Dockerfile.backtest` paths) and syncs the new prefix. Expect GREEN through the registry step
  (S5); the trailing `ecr:BatchGetImage` denial may still fail the STEP until the user's IAM allow — the
  `sha-<short>` image in ECR (`aws ecr describe-images --image-ids imageTag=sha-<short>`) is the artifact, with
  the label `org.archondex.substrate-manifest-md5` = the new md5.
- **S9 The canon campaign on the new image.** A campaign job definition REGISTERED AGAINST THE SHA TAG (never
  `:dev`); `run_isolated` N=5 bitwise-unanimous per window (26-yr, 16-yr, 2022, the GFC 2008–2009) through the
  canary; each new canon added with `scripts/anchors_registry.py add …` (computes the digest from the committed
  manifest), the June entries kept as history. Artifact: the submit gate's positive control passes on the new
  digest with a new anchor; the old anchors refuse by digest, as designed.
- **S10 The provenance cell.** `_director_tools/repin1_provenance_cell.sh <sha-short>`: the in-image manifest
  verify, `honest_n_pin --verify` PIN OK, `resolve_cycle_n_trials` provenance printed; the jobdef deregistered.
  (NOT a discovery cycle — the RR-3B ruling stands until Option B is the pinned input.)
- **S11 The first artifacts, read before anything is quoted.** The next canonical run's census reports the
  convention label (`exact_tr` post-seam / `drip` pre-seam per file) and `share_price_basis = close_unadj`; the
  night's janitor row `substrate_verify PASS` by `janitor_nightly` on the NEW digest; `relay_gap` 0.

## 3. After the day (not on it)

The re-run campaign on sha-pinned jobdefs — every 2024–25 verdict per the cutover proposal's §5 classes;
B-1 as a NEW pre-registered run; T-146; the (c) pricing decision; the dollar-ADV / slippage / borrow readers'
switch to `close_unadj` (its own unit; the column exists on every written file); the paper image re-bake with
the pinned `tr_reconciled/` (the fleet checklist, the user's gate).

## 4. Abort — any refusal, at any step, in any order

The quarantine is reversed by rename (S2 backwards: the copy out, the canonical back); the manifest is restored
by a NEW commit that re-adds the re-pin #1 bytes (never a reset, never an amend) and `verify` is run green; the
anchor is restored from the quarantined copy's `_isolated_anchor/` only if S5 ran; nothing published to S3 is
deleted (a prefix is content-addressed; an unused one is harmless). The day is then re-planned from the step
that refused, with its reason recorded here.

## 5. Decisions the user owns before the day

1. **The date**, and the go (P8).
2. **The pairs edge's data file** (P6): pin `data/research/cointegrated_pairs_2026_05_09.json` by name and bake it
   (the same discipline as the honest-N files — my recommendation), or prove the in-image check tolerates a
   registry-only row.
3. **The IAM allow** (`ecr:BatchGetImage` on `archondex-backtest` for `archondex-github-ci-role`) — optional for
   the day (the sha image still lands), required for a green CI step and a live `:dev` tag.
4. **Disk headroom**: removing the 23 stale `.claude/worktrees/agent-*` checkouts (a deletion) before the day,
   or not.
5. Whether the dollar-ADV readers' `close_unadj` switch rides WITH the day (bigger diff, one re-qualification)
   or after it (two). My recommendation: after, as its own reviewed unit.

## 6. Amendment, 2026-11-12 (T-387): the USER ruled option (a′) — the pre-seam rewrite before S2

**Appended; §0–§5 above are kept as written.** The USER ruled on 2026-11-12 that the cutover adopts the
T-384 option-(a′) v4 drip fix, amending the 2026-10-22 option (a) (`docs/Sources/proposal_drip_fix_a_prime_2026-11-11.md`).
Where §0–§5 say the copy's pre-seam span is "drip", read this section. **Status:** the writer is BUILT on branch
`feat/cutover-a-prime-writer-t387`, NOT merged; nothing here has run on a cutover copy except the read-only dry
run below. The step joins the day only after the branch's review and merge (a new pre-condition, P9).

**What the writer does.** `tr_writer.era_tr_rewrite` (the (a′) logic in ONE module, `engines/data_manager/era_tr.py`,
shared with `scripts/drip_fix_candidate_t384.py`) rewrites the PRE-seam span of a merged file from the drip to
`era_tr`, OFFLINE: raw Stooq from the bundle, the missed dividends from the cached yfinance reference (v3's `yf/`,
read-only; refused without its `_fetch_log.jsonl`), no-reference spans kept raw Stooq and LABELLED UNVERIFIED, ONE
constant at the seam. Every post-seam byte and the `close_unadj` column stay as the step-1 pass wrote them. It
refuses (fail closed) a span that is not the drip (so it never runs twice), a file the step-1 pass wrote WHOLE, a
kept-bar count that disagrees with the merge record, and any write-time rail failure (the step audit: pre-seam
daily returns differ from raw Stooq's only at the restored ex-dates, by exactly −log(1 − D/P); the splice audit:
the seam-day return is Stooq's own). The refusal behaviour of option (a)'s seam write (the mid-span step,
`cache_convention_defects`) is unchanged.

**Acceptance (T-387, 2026-11-12).** On a COPY of the canonical inputs (the 575 merged files with pre-seam bars +
`_merge_meta.json`, at `Dev/_substrate_candidates/t387_writer_check_2026-11-12/`), the writer path's output equals
v4's `processed/` FILE FOR FILE: 1,150 of 1,150 identical, aggregate md5 `2cee41ef7d2e0bd8fa858d500f99dda2`.
A `--dry-run` on the real step-1 copy (read-only; no file in it changed): 575 would be written, 0 refused; the built
pre-seam span equals v4's × ONE constant per file (the copy's seam close ÷ the canonical's) to 8.9e-16; post-seam
text and `close_unadj` identical on all 575 (563 carry `close_unadj`).

**P9 (new pre-condition).** The T-387 branch merged on main after independent review by execution.

**S1b — the (a′) build, NEW, between S1 and S2.**
1. P2 is read on the step-1 copy FIRST, exactly as §1 says: it must still be the object the step-1 record pinned.
2. Duplicate it — the step-1 copy stays the pinned record ([NN-ARCHIVE]): `python -m scripts.cutover_step1_pass
   fresh-copy --from /Users/jacksonmurphy/Dev/_substrate_candidates/cutover_copy_2026_10_22 --to
   /Users/jacksonmurphy/Dev/_substrate_candidates/cutover_copy_a_prime_<date>`. The step-1 copy measured 1.0 GB
   on 2026-11-12; P7's 15 GB floor applies AFTER the duplicate.
3. `python -m scripts.cutover_step1_pass era-tr --copy /Users/jacksonmurphy/Dev/_substrate_candidates/cutover_copy_a_prime_<date>
   --tag a_prime_<date>`. Artifact: `era_tr_a_prime_<date>.jsonl` beside the copy — 575 rows, 0 refused, exit 0 —
   and `era_tr_write_log_a_prime_<date>.jsonl`. Refusal: any non-zero exit halts the day (§4).
4. P3 re-read on the (a′) copy. EXPECTED — by construction, NOT yet read on an (a′) copy (no duplicate was made
   on 2026-11-12; disk): `guard` → holed 1 (SLE, declared), as on the step-1 copy ((a′) moves no pre-seam DATE and
   keeps every kept-bar count, and the `pre_seam_drip_gap` class now also covers an `era_tr` span, so the same 380
   days on 215 names are excused); `label` → 0 unlabelled, `n_pre_seam_era_tr` 575, `n_pre_seam_drip` 0,
   `n_unverified_missed_era` 12 (AVB, BBBY, CTRA, DAL, ELV, EQR, HOLX, LEG, PLD, POM, PSKY, SATS),
   `n_unverified_pre2003` 54 (the label counts were READ on the T-387 check copy's 575 files). A different reading
   is a finding, not a tolerance.
5. P2 replaced by a NEW candidate manifest for the (a′) copy: `stage --copy <(a′) copy> --root <root>`, then
   `gen_substrate_manifest.py generate --root <root> --manifest ../cutover_a_prime_candidate_manifest_<date>.sha256
   --stamp-root <root>`, then `verify` 0/0/0. Its diff against the step-1 candidate manifest must be exactly the
   575 × (csv + parquet) price files and 575 write records (563 modified, 12 new) — nothing else.
6. S2 then moves the (a′) copy — not the step-1 copy — into place.

**S6 re-pin #2 grows.** The class-by-class review gains one class: the 575 pre-seam rewrites. Against the canonical,
563 of the 575 were already rewritten by option (a) (post-seam exact) and now ALSO carry `era_tr` pre-seam bars; 12
(AVB, BBBY, CTRA, EA, EQR, HOLX, LEG, POM, PSKY, QRVO, SATS, SLE — refused by the step-1 pass, so canonical bytes in
the copy) change ONLY in their pre-seam span and gain a write record. The tests that lock today's canonical as
drip flip in the same commit (`test_the_canonical_cache_is_labelled_whole_with_575_pre_seam_drip_files` → 575
`era_tr`).

**S11.** The census reports `era_tr<seam|exact_tr` for the 575 files (not drip), with each file's UNVERIFIED spans
(`unverified`), and `exact_tr` elsewhere.

**After the day (§3, added).** The re-run campaign runs on the (a′) substrate (the proposal's §7 list). (a′) does
NOT repair Stooq's corporate actions or its transient blocks, the 12 no-reference missed-era spans, or the 54
pre-2003 spans; the second unit (the spin-off / transient-block repair, held to the same §1 test) is owed.

**Decisions the user owns (added to §5).**
6. Whether the (a′) build rides on cutover day (S1b above) or runs as its own approved act before it, with its
   own candidate manifest reviewed separately (my recommendation: before, as its own act, so the day itself is
   unchanged in length).
7. The reference cache as an input: the (a′) bytes depend on v3's `yf/` snapshot (fetch-log md5
   `1763a95fe86a44f0d42085767acb545e`, 95 MB), which no manifest pins. Every write record names it; my
   recommendation is to keep it read-only beside the candidates and quote its md5 in the re-pin #2 commit.
8. Keep the step-1 copy after the day (my recommendation: yes, as the pinned record of option (a)).
