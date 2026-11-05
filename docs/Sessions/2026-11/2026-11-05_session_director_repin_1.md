# Session Summary: 2026-11-05 — director: RE-PIN #1 landed; the image path's three defects found by its first artifacts

## What was worked on

- **Re-pin #1** (ledger T-375; record `docs/Sources/proposal_repin_1_drip_substrate_2026-11-05.md`): the drip substrate PINNED. The code half (an in-session builder; a fresh reviewer by execution; the merge gate) merged at `4bf0ec1` (4,651 / 0); the data half by the director in the main tree — the T-219 shares snapshot fetched ONCE (219 names with a price file; 199 fetched, 20 empty with reasons, 0 failed) and pinned with its meta; `generate` in the main tree (`1bb6764`: 14,259 files; `verify` exits 0 on main for the first time since 2026-06-18; the stamp PASS by writer `repin`); the content-addressed prefix `substrate/44d3be53b1f59377abfae9ed66840116/data/` published and proven (14,259 objects, 144 explicit + 25 sampled sha256-equal, the registry companion beside them); pushed (`2e65544`).
- **The image's build-time registry check re-targeted** to the ANCHOR registry a cell executes from (`e8ebd59`, 4,652 / 0; reviewed by execution) after the push's CI run — the first since May to reach that step with the right substrate — read an absent live file.
- Status for the user (their morning question); the fleet digest unchanged (10-30 weekly; next due 11-06).

## What was decided

- **The diff as a statement of canonicity** (record §1): the 5 VIX-term files a pure July extension — pinned; the T-256/T-274 additions incl. `tr_reconciled/` — pinned; B-1's four fundamentals reads — pinned (B's 10-15 ruling: never exclude the cache pattern); `data/external/base_curve` joins SUBSTRATE_DIRS; the T-219 snapshot + meta and the honest-N gate's two inputs join SUBSTRATE_FILES BY NAME; DFII10 recorded ABSENT, not fetched (a new series at pin time would be an unreviewed input entering the substrate in the act that certifies it). Nothing in the price cache or `market_cap_tiers.json` rewritten.
- **D7 (the first cloud `--discover` cell) WITHDRAWN** by the director's own RR-3B ruling of 2026-10-13: cloud discovery stays halted until Option B's registry is the pinned input. Shipping the pinned honest-N files into the image (C6) removed the ACCIDENTAL brake (absent files → `HonestNUnavailableError`); the halt is now a ruling with no mechanism — a referee-side refusal on a cloud cell is PROPOSED (the referee and the gates are never autonomously modifiable). D7 becomes a one-off PROVENANCE cell (`_director_tools/repin1_provenance_cell.sh`), deferred to the first image that builds.
- **The T-219 recompute's selection rule is OWED before re-pin #2** (reviewer F1): `--from-snapshot` as written would replace the 55 cohort names carrying a current-snapshot cap (for a still-trading name `cap_at_delist` keys on the price file's last bar — a trailing median, not a cap at leaving the index). Rule: write cap-at-delist only for names whose price file ends before the recompute date. Sized by the D1 artifact `docs/Measurements/2026-11/repin1_d1_shares_snapshot_recompute_diff_2026-11-05.md` (130 of 138 exact; 8 still-trading names ≤1.5%; the 55 listed).
- **The re-anchor is a canon change scheduled WITH cutover day** (health_check MEDIUM, 2026-11-05): the May anchor registry (209 rows) is 9 code-registered edges behind the code (all nine `paused` live — no active set changes); the CI image build fails at the retargeted check for the real reason until `run_isolated --save-anchor` + re-pin, with the N=5 bitwise campaign. The check is never loosened.
- **D4 before D3**: publish the prefix BEFORE the push, because the push fires the CI build whose first step syncs the prefix.
- **Pushes under the delegation**, two today (2e65544, then the close), each after ls-remote unchanged, a secrets scan of the range (0), no blobs over 5 MB, fast-forward.

## What was learned

- **The CI image build has FAILED on every main push since 2026-05-24** (`gh run list`: no success in the retained history): through 10-22 a trailing `ecr:BatchGetImage` denial to `archondex-github-ci-role` AFTER the sha-tag image landed (`sha-f9c5e9d` is in ECR; `:dev` STALE since 2026-06-10); since 11-04 the registry check fails earlier. Nothing had read the run list — `[NN-FIRST-ARTIFACT]` again. The IAM allow is the USER's (one statement); proposed, not done.
- **The honest-N gate's inputs never reached the image** (`/app/data/observability` created EMPTY): Gate 0 raised `HonestNUnavailableError` on every cloud run; the re-pin alone would not have lifted RR-3's halt. Now the two files are substrate-pinned by name, COPYd by name, and `honest_n_pin --verify` runs at build — its first artifact: `PIN OK` inside the CI build at 22:00:41Z.
- **The default Batch job definition `archondex-backtest` points at `:dev` = the 2026-06-10 image.** Every measured campaign used a sha-pinned campaign jobdef; the re-run campaign must too (`docs/Cloud/CLOUD_USAGE.md` corrected: freshness is checked by the sha tag, never `:dev`).
- **The isolated harness executes from the ANCHOR's registry** (run_isolated restores `data/governor/` from `_isolated_anchor/` on entry; the live `edges.yml` is not baked by T-133). Since the single-writer unit, imports no longer re-register in-container, so the May anchor's row set is what every isolated run — local and cloud — starts from. The registry companion in the S3 prefix is moot for the image and harmless.
- **A reviewer's NOT READY on my own follow-up**: pinning the snapshot's meta without staging it would have made every image build MISSING it after the pin — invisible to a literal lock; the staging lock is now derived from SUBSTRATE_FILES. The by-diff re-check of a director follow-up is not optional.
- **Script hygiene**: a manifest path with a space (`stooq/daily/us/nasdaq stocks/…`) broke an `awk '{print $2}'` proof loop; parse the `<sha256><two spaces><path>` line by its separator. A `COUNT_PLACEHOLDER passed, 0 failed` message doubled the gate's substitution — the gate substitutes the whole phrase. A `timeout` wrapper does not exist on macOS. One commit on the branch went out with a failing new test (an undefined name) and was corrected on top — run the targeted file before the commit, every time.
- The seventeen `ops/approvals/*` records the scheduled director pass writes into the main tree are now committed as records (every one withdrawn).

## Pick up next time

- **Tonight's janitor row (11-06 03:00): `substrate_verify PASS` by writer `janitor_nightly`** — the stamp's second writer and the gate's first artifact; the manifest health row flips to RESOLVED on it; `relay_gap` reads 0 after the close push.
- **The CI run fired by the close push**: expect a red step at the RETARGETED registry line (`_isolated_anchor/edges.yml`, 9 additions) — the retarget's first artifact; anything else is a new finding.
- **D's half of the submit gate** (`config/anchors.json`; the gate reading `core/substrate_stamp.py`; the agreed interface §7) — now buildable.
- **The cutover-day RUNBOOK** (propose-first) carrying: re-pin #2; the RE-ANCHOR (`run_isolated --save-anchor` → `generate` → commit; N=5 bitwise per window on the new image; the arm-0 canon md5s re-recorded); the T-219 selection rule + the recompute into the real tiers file; the image build (CI, by sha tag) and the provenance cell; the campaign jobdef pinned to the sha tag.
- Proposals for the user: the IAM allow (`ecr:BatchGetImage` on `archondex-backtest` for the CI role); 23 stale `.claude/worktrees/agent-*` checkouts (a deletion); the orphaned simulator image; the parked data-source decision; the paper journals' sizing field.
- Owed, small: the referee-side cloud-discover refusal (propose-first); `load_cached`'s silent empty frame (LOW); the T-219 stats counter (191 vs 193); `generate`'s docstring in `cutover_step1_pass.py` is fixed, the one in the cutover record not re-read.

## Files touched

```
.dockerignore
Dockerfile.backtest
config/substrate_manifest.sha256
docs/Cloud/CLOUD_USAGE.md
docs/Core/execution_manual.md
docs/Measurements/2026-11/repin1_d1_shares_snapshot_recompute_diff_2026-11-05.md
docs/Sessions/2026-11/2026-11-05_session_director_repin_1.md
docs/Sources/proposal_repin_1_drip_substrate_2026-11-05.md
docs/State/CURRENT_STATE.md
docs/State/TASK_LEDGER.md
docs/State/health_check.md
engines/engine_a_alpha/edges/macro_real_rate_edge.py
ops/approvals/* (17 records)
scripts/build_backtest_image.sh
scripts/build_pit_cap_history_t219.py
scripts/cutover_step1_pass.py
scripts/gen_substrate_manifest.py
scripts/index.md
tests/test_repin1_code_2026_11_05.py
tests/test_substrate_stamp_2026_10_22.py
data/universe/delist_shares_snapshot.parquet + .meta.json (NEW, pinned; untracked data)
data/state/substrate_verify_stamp.json (the repin PASS; untracked)
```

## Subagents invoked

- A general-purpose BUILDER in a scratch worktree with the safe data layout (`_director_tools/wt_data_layout.sh`): C1–C7 in seven commits (dde8ecd … 346b973), the full suite 4,616 / 1 environmental.
- A general-purpose fresh-context REVIEWER by execution in its own worktree: APPROVE 346b973 (every lock reverted in-process); NOT READY on the director's follow-up 7725c14 (the meta pinned, not staged); APPROVE 2102a52; APPROVE 7235202 (the anchor-check unit) — four reports in the fixed format, the worktree byte-untouched throughout.
