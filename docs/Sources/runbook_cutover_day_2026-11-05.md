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
  --out data/universe/market_cap_tiers.json` with the selection rule in force (T-378), its whole-file diff
  recorded as the artifact; the T-306 SPY leg and `ohlc_features_t150` re-labelled per §3.2. B-1's "must
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
