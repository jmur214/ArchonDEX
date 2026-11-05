# Re-pin #1 — the drip substrate PINNED, `verify` green, the honest-N inputs shipped, the image rebuilt (director, 2026-11-05)

**Kind:** propose-first record of a deliberate substrate act. **Authority:** the director's ruling of 2026-10-15
(TWO re-pins, each with its reason; #1 NOW), the user's standing lead of 2026-10-22, and the cutover ruling of
2026-10-22 (option (a); re-pin #2 on cutover day). **Nothing in the canonical price cache is rewritten.** The only
writes under `data/` are two NEW files (the T-219 shares snapshot; nothing else) and, at the end, the committed
manifest plus its PASS stamp. The cutover's write pass stays on the copy.

## 0. Why now

`config/substrate_manifest.sha256` has failed `verify` since 2026-06-18. Measured today with the generator's own
`build_manifest()`, read-only, identical to the janitor's 2026-11-05 stamp:

| pinned | host | MISSING | EXTRA | CHANGED |
|---|---|---|---|---|
| 14,120 | 14,254 | 0 | 134 | 5 |

While it is red: the backtest image cannot be rebuilt (`build_backtest_image.sh` exits 65 on a failed verify), every
campaign submit refuses at the stamp once D's half of the gate lands, and RR-3's cloud `--discover` cannot run (the
B-7 blocker, RR-7 D3). The janitor's `substrate_verify` row is the one red check on an otherwise green night.

**A second blocker, found today, that the re-pin alone would not lift:** the honest-N gate reads its two pinned inputs
from `data/observability/` (`core/measurement/mbl_gate.py`: `DEFAULT_ARTIFACT_DIR`, `DEFAULT_PIN_PATH` →
`config/honest_n_pin.json`). `Dockerfile.backtest` creates `/app/data/observability` EMPTY and the CI build syncs only
the manifest-pinned prefix. On the cloud, Discovery's Gate 0 therefore raises `HonestNUnavailableError` by design —
the right fail-closed answer, and the reason the halt would survive a green manifest. The two files are pinned
(`PIN OK` today: `n_effective_2026-09-30.json`, `run_registry.sqlite`, 13 KB + 80 KB, both static by the 9.3 ruling —
a changed registry makes the gate refuse until re-pinned). They join the substrate manifest's scope here, so the
content-addressed prefix carries them and the image copies them.

## 0b. Found at dispatch: the CI image build has FAILED on every main push, and two distinct defects explain it

`gh run list` for "Build & push backtest image": no successful run in the retained history; the workflow's own
guard text says "failing on every main push since 2026-05-24". Read from the logs, not inferred:

- **Through 2026-10-22 — a trailing IAM denial AFTER the push.** The 10-22 run built the image, pushed every
  layer, then failed: `ecr:BatchGetImage` on `repository/archondex-backtest` is not allowed to
  `archondex-github-ci-role` ("no identity-based policy allows"). The `sha-f9c5e9d` image IS in ECR, pushed
  2026-10-22 14:31 local, by that run — so the sha tag lands and only the step's exit (and the `:dev` retag) fails.
  Every campaign since has used images by sha tag; `:dev` is stale. Fix: one IAM action on the CI role — the user's
  account, proposed in §4, not done here.
- **Since 2026-11-04 — the build fails EARLIER, correctly.** The registry single-writer unit added
  `RUN python scripts/sync_edge_registry.py --check` to the Dockerfile; in CI it reads
  `data/governor/edges.yml (0 rows)` and fails with 26 never-registered edges. `data/governor/edges.yml` is
  gitignored (`.gitignore:28 data/`) and manifest-EXCLUDED by design (`LIVE_MUTABLE_GOVERNOR`, T-131), so the CI
  runner, which has only the git checkout plus the S3 substrate prefix, has NO registry. The check is right: an image
  without its registry must not ship. Before the check existed, every CI image shipped registry-less and the (then
  import-writing) code re-registered edges from defaults at runtime — the exact class the single-writer unit closed.
  Locally `--check` exits 0 (the main tree's file, 2,414 lines).

**Consequence for this unit:** D4 publishes `data/governor/edges.yml` into the new prefix as a NON-pinned COMPANION
beside the manifest's files ("the image carries the last SYNCED state of the building machine" — here, the
publishing machine's, verified by `--check` exit 0 at publish time). The generator excludes it, so `verify` stays
green on the runner. D5 is the CI dispatch; its sha-tag image is checked in ECR by `describe-images` whether or not
the trailing denial still fails the step. A local Docker build is the fallback only (the daemon is off; the desktop
VM was the largest process in the 10-18 memory-pressure kills).

## 1. The diff as a statement of canonicity — what `generate` will pin

| class | files | origin | decision |
|---|---|---|---|
| CHANGED, `data/macro` | VIX, VIX3M, VIX6M, VIX9D `.parquet`, `_meta.json` (5) | `scripts/fetch_vix_term_structure.py`, 2026-07-02 03:09 (T-256/T-274 day); a PURE EXTENSION of the June files — every June row present and bit-identical against the S3 June copies (B's read, 2026-10-15) | PIN |
| EXTRA, `data/macro` | SKEW.csv, SKEW.parquet, VVIX.parquet, shiller_ie_data.csv (4) | T-274 | PIN |
| EXTRA, `data/processed/parquet` | CVNA, KG, SII, S `_fundamentals.parquet` (4) | B-1's cache misses, 2026-10-14 02:45–03:06 | PIN — B's delegated decision (2026-10-15): never exclude the fundamentals pattern (585 already pinned; the canonical-run miss is REFUSED since `a4c6f89`) |
| EXTRA, `data/processed/stooq_us_daily` | 39 csv + 39 parquet + `_ingest_meta.json` (79) | T-256 ingest | PIN |
| EXTRA, `data/processed/tr_reconciled` | 39 csv + `_tr_manifest.json` (40) | T-256 reconcile; read by `core/benchmark.py`, `engine_e_regime/macro_features.py`, two foundry features; baked into the paper image UNPINNED today | PIN |
| EXTRA, `data/raw/cboe` | 6 `_cdn.csv` + the wayback `.xls` (7) | T-256/T-274 | PIN |
| NEW SCOPE | `data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv` (1) | the frozen 26-yr arm0 curve read by T-171/T-178/T-174; a controller product with zero manifest lines | PIN — director's ruling 2026-10-15; NOT regenerated at re-pin #2 |
| NEW FILES | `data/universe/delist_shares_snapshot.parquet` + `delist_shares_snapshot.meta.json` (2) | the T-219 shares histories fetched ONCE (§3 D1) and the per-name fetched/empty/failed record of that fetch (reviewer F2: the snapshot's provenance, pinned beside it by name) | PIN — so re-pin #2's cohort recompute is deterministic and never fetches |
| NEW SCOPE | `data/observability/n_effective_2026-09-30.json`, `data/observability/run_registry.sqlite` (2) | the honest-N gate's two inputs, already pinned by `config/honest_n_pin.json` | PIN by name (never the directory) — §0's second blocker |
| ABSENT, recorded | DFII10 | no file anywhere under `data/` (RR-7 D3); `macro_real_rate_v1` is paused; `real_rate_level` is an AUX column the production 7-feature HMM does not read | NOT fetched. A new macro series pulled at pin time would be an unreviewed input entering the substrate in the act that certifies it. Fetch it as its own declared act when a consumer is live. The edge docstring's "now feeds Engine E's HMM" is corrected to the fact |

Expected after the code half: `verify` → MISSING 0 / EXTRA 138 / CHANGED 5 (134 + base_curve 1 + snapshot 1 + the
two honest-N files); after `generate`: 0 / 0 / 0, pinned 14,258... the exact count is the generate's own output and is
recorded in the commit, never predicted here.

## 2. The CODE half — a builder in a worktree, a fresh-context reviewer by execution, the merge gate

C1. `scripts/gen_substrate_manifest.py`: `SUBSTRATE_DIRS` += `data/external/base_curve`; `SUBSTRATE_FILES` += the
snapshot path and the two honest-N files BY NAME. Lock: the two names equal `config/honest_n_pin.json`'s names, so a
future `honest_n_pin --pin --replace` forces a manifest edit (the lock fails on a mismatch, naming both files).

C2. The drift footer (`_print_drift`): hidden = total − shown, shown = Σ min(20, class). Today's drift would print
"… and 79 more" with 114 hidden (RR-7 D3; R confirmed). Lock on a `VerifyResult` of 0/134/5 → "… and 114 more".

C3. `generate` REFUSES a `--manifest` other than the committed default when `--stamp-root` is absent — before any
write, naming the flag and the hazard (a candidate's PASS stamp landing in the real stamp file; recorded 2026-11-04).
Lock: refused → non-zero, no manifest written, the real stamp byte-untouched; with `--stamp-root` on a temp root → proceeds.

C4. `scripts/build_pit_cap_history_t219.py` gets two EXPLICIT modes; the bare live-fetch `main()` is retired:
- `--write-snapshot <path>` (network): for every delisted-cohort name with a price file, `get_shares_full` once; the
  series stored; an empty or failed fetch RECORDED per name with its reason in the snapshot's meta (counts
  `{fetched, empty, failed}`), never swallowed to None.
- `--from-snapshot <path> [--out <path>]` (re-pin #2's recompute): caps from the snapshot + the price cache; NEVER
  imports or calls yfinance on this path. Lock: a stub that raises if invoked; the recompute runs with it installed.
  The tier arithmetic is unchanged (`_tier`, late-period median of close × shares).
- `--out` defaults to a SCRATCH path, never `data/universe/market_cap_tiers.json`; writing the real file is an
  explicit `--out` (re-pin #2's act).

C5. `engines/engine_a_alpha/edges/macro_real_rate_edge.py` docstring: DFII10 is ABSENT from the substrate; the AUX
column is not read by the production HMM. Docs only. (`MacroDataManager.load_cached` returning an empty frame
silently for an absent series is the always-empty-channel class — its own row, §4.)

C6. `Dockerfile.backtest`: COPY exactly the two pinned honest-N files (by name) into `/app/data/observability/`, then
`RUN python -m scripts.honest_n_pin --verify` (exit 3 fails the build). The image cannot ship an N its pin disagrees with.

C7. Tests for C1–C4 and C6's build step where a test can reach it; `execution_manual.md` blocks for the re-pin (the
new scope), the T-219 modes, and the image's honest-N verify; `doc_lint` + `sync_docs --check` + the FULL suite in
the worktree before posting.

## 3. The DATA half — the director, in the main tree, after the code merges

D1. `--write-snapshot data/universe/delist_shares_snapshot.parquet` (network). Then `--from-snapshot` into a scratch
path and DIFF THE WHOLE recomputed file against the current one — the recompute's FIRST ARTIFACT (reviewer F1: the
recompute writes every snapshot name with a positive cap, so it would also replace the 55 cohort names that carry a
current-snapshot cap today, not only the 138 `delist_shares` entries; `cap_at_delist` keys its window on the price
file's LAST BAR, so for a still-trading name it is the current cap). Equal caps on the 138 prove the snapshot
reproduces June's live fetch; every difference and every would-be replacement is LISTED, never hidden.
`market_cap_tiers.json` is NOT rewritten at re-pin #1; it is pinned as-is.

D2. `gen_substrate_manifest.py verify` (expect §1's counts) → `generate` (stamps PASS, writer `repin`, in the MAIN
tree: no `--stamp-root`) → the manifest diff reviewed class by class against §1 → commit the manifest with this
record and the ledger row.

D3. Push under the delegated checks (ls-remote unchanged, secrets scan, no blobs over 5 MB, fast-forward).
**ORDER CORRECTED at execution (2026-11-05): D4 runs BEFORE D3.** The push fires the CI image build, whose first
step syncs the prefix keyed by the committed manifest's md5 — if the prefix is published after the push, that
build fails at the sync with nothing to fetch; published first, the push's own build is D5's artifact.

D4. S3: `_director_tools/repin1_s3_publish.sh stage` hardlinks EXACTLY the manifest's files outside the repo and verifies
the stage with the generator (0/0/0); `upload` syncs it to `substrate/<new md5>/data/` (refusing a non-empty prefix),
then proves it: object count == manifest lines, every CHANGED/NEW path and a 25-file sample sha256-equal. Plus the
registry COMPANION `data/governor/edges.yml` (§0b; not pinned; `--check` exit 0 at publish). ~2.7 GB.

D5. `gh workflow run` "Build & push backtest image" at the pushed commit. First artifact: the `sha-<short>` image in ECR
(`aws ecr describe-images`) whose label `org.archondex.substrate-manifest-md5` = the new md5; the registry check and
`honest_n_pin --verify` both run inside the build. The step may still exit 1 on the trailing `ecr:BatchGetImage` denial
(§0b) — that is recorded, not a failure of this unit; the IAM fix is the user's.

**D5 OUTCOME (2026-11-05 16:01):** the CI run fired by the push `2e65544` is the first since May to reach the
registry step with the right substrate: `substrate manifest md5: 44d3be53b1f59377abfae9ed66840116` synced; in-image
`honest_n_pin --verify` → `PIN OK` (C6's first artifact); then `sync_edge_registry.py --check` → `data/governor/edges.yml
(0 rows)`, exit 1. The live registry is not baked by design (T-133) and `run_isolated` restores the governor set from
`_isolated_anchor/` on entry — the default-path check certified an absent file. Re-targeted to the anchor's registry
(branch `repin-1-anchor-check`, reviewed by diff, merged behind this record), and against the anchor a sync WOULD
CHANGE it: 9 code-registered edges absent — so the build fails for the REAL reason until the anchor is re-saved and
re-pinned, a canon change scheduled with cutover day's re-anchor (health_check MEDIUM row, 2026-11-05). No
`sha-2e65544` image exists in ECR; **D7's provenance cell is DEFERRED to the first image that builds.** The
registry companion in the prefix is moot for the image (not baked) and harmless.

D6. Tonight's janitor row: `substrate_verify PASS` with the stamp written by `janitor_nightly` — the stamp's first
artifact from its second writer.

D7. ~~The first `--discover` cell on the new image~~ — **WITHDRAWN at execution (2026-11-05), by the director's own
RR-3B ruling of 2026-10-13:** "Cloud `--discover` stays halted until Option B's rebuilt registry exists … shipping
Option A's registry into the image would end the halt by feeding the cloud a count that structurally omits its own
runs." C6 ships exactly those files, so the brake that was ACCIDENTAL (absent files → `HonestNUnavailableError`)
is gone from the image and the halt is now a RULING with no mechanism behind it. Today no cloud launcher runs
`--discover` (`cloud_entrypoint.sh` runs `run_isolated --task q1` only), so nothing runs loosened; but the
mechanism is owed — PROPOSED (referee code, never autonomously modifiable): the discovery path refuses on a cloud
cell (`ARCHONDEX_CELL_ID` set) while the pinned artifact is not the Option B population. **D7 as executed:** a
one-off PROVENANCE cell on the new image — `gen_substrate_manifest.py verify` inside the container (the baked
substrate against the committed manifest), `honest_n_pin --verify`, and `resolve_cycle_n_trials` printing its
source and N — the observability step-5 artifact without a cycle. A registered-then-deregistered job definition
pinned to the `sha-` tag, as the 10-22 image audit did.

D8. **Found at D7 (2026-11-05): the default Batch job definition `archondex-backtest` (rev 3, the one
`submit_substrate_run.py` picks) points at `archondex-backtest:dev`, and `:dev` is the image pushed 2026-06-10
(tag `t118-3953085`)** — CI never retags it (§0b). Every MEASURED campaign used a campaign jobdef pinned to a
`sha-` tag (t215, foundry-t196, the re-anchors), so no quoted verdict ran on it; but the default is a June image
and `docs/Cloud/CLOUD_USAGE.md`'s `imageTag=dev` line points at it. The re-run campaign MUST register its jobdef
revision against the `sha-` tag of the commit it measures, never `:dev`; the doc line is corrected in this unit.

## 4. Not in this unit (recorded so nothing reads as forgotten)

- RR-3 Option B's 9.1 build (persisting candidate attribution streams; N_eff 267 without borrowed credit) — D's
  unit. The pinned 09-30 artifact stays the gate's input until that lands and is re-pinned with `--replace`.
- `load_cached`'s silent empty frame for an absent series — a LOW row of its own.
- The paper image re-bake (`tr_reconciled/` baked unpinned) — the fleet checklist, the user's gate.
- 23 stale `.claude/worktrees/agent-*` checkouts from 2026-11-04 (branches all merged) — removal is a deletion; proposed, not done.
- The CI role's missing `ecr:BatchGetImage` (and the `:dev` retag) — PROPOSED to the user: one allow on
  `archondex-github-ci-role` for `repository/archondex-backtest` (§0b). Not an action the director takes on the account.
- Whether `data/governor/edges.yml` should instead be TRACKED (the build-time check then certifies the committed
  state; Engine D's promotion writes would churn git) — a decision for the registry's owner, not this unit.
- OWED before re-pin #2 (reviewer F1, MINOR): the recompute's SELECTION rule — June's `main()` skipped names already
  carrying a cap; `--from-snapshot` overwrites them. Rule to build and lock: write cap-at-delist only for names whose
  price file ENDS before the recompute date (truly delisted); leave a still-trading name's current-snapshot cap. The
  D1 whole-file diff is the evidence that sizes it.
- EXPECTED after this merge (reviewer F6): the CI image build fires on the push (`engines/**`, `Dockerfile.backtest`
  are trigger paths) and fails at STAGING — the runner's data is the still-committed June prefix, which has no
  `data/external/base_curve` and no observability files — until D2–D4 publish the new manifest and prefix. Not this
  unit's defect; recorded so the first red run is read correctly.
- Re-pin #2 and everything on cutover day.

## 5. What the reviewer must see FAIL under reversion

C1's scope reverted → the base_curve lock fails; the name lock fails on a planted pin mismatch. C2 reverted → the
footer lock fails. C3 reverted → generate with a foreign `--manifest` and no `--stamp-root` writes a stamp into the
temp real-stamp path the test gives it. C4: the yfinance stub RAISES on the `--from-snapshot` path when the
retired live call is restored; an empty fetch recorded as `empty`, a raising fetch as `failed`, never a silent None.
C6: a planted byte change in the copied artifact fails `--verify` at build (exit 3) where a test can drive the step
without Docker (the script's exit code under a planted file is enough).

## 6. Ledger

T-375 — re-pin #1 (dispatched 2026-11-05; the code half's review, the data half's artifacts D1–D7 each recorded here).
