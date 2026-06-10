# T-2026-06-10-133 — Governor-hygiene follow-ups: shared anchors, live-file bake-exclusion, procedure docs

**Date:** 2026-06-10
**Branch:** `feature/governor-hygiene-followups-t133`
**Worker:** Agent B
**Predecessors:** T-131 (the three propose-first items this implements), T-127 (build pipeline), T-109 (timeout lesson)
**Status:** DONE — all 3 approved follow-ups shipped + verified. The anchor-divergence class is closed end-to-end.

## TL;DR

1. **Shared anchors (#1):** `setup_agent_worktree.sh` now symlinks `_isolated_anchor/` + `_cap_recal_anchor/` to the director's (single source of truth) instead of copying; live governor files remain per-agent copies. The 4 existing worktrees were converted in place (by the director, during this task); old anchors archived under `Archive/anchor_divergence_t133/agent_{a,b,c,d}/`. **Conversion forensics: agents A and D had DIVERGED anchors** (stale pre-May-12, no `edges_archive_pre_t037.yml` — the same class T-131 found in the director); B and C were identical to canonical. A/D's local-run behavior changes (to canonical) from now on — flagged below.
2. **Bake-exclusion (#2):** `build_backtest_image.sh` no longer bakes the 9 `LIVE_MUTABLE_GOVERNOR` files (T-131 proved them canon-irrelevant). Anchors keep being baked. Pattern subtlety that mattered: rsync excludes are basename-matched at any depth, so the patterns are ANCHORED (`/governor/edges.yml`) — a bare `edges.yml` would have stripped `_isolated_anchor/edges.yml`, the very file the container restores from. **Verified:** fresh build passes the manifest gate (`147e9d0e…`); image contains anchors (incl. via the new worktree symlink) and zero live files; 2022 sanity cell reproduces the reference canon **`0a62b7541d3d…` / Sharpe 1.6 bitwise** (valid reference: engine code unchanged since `9374871`).
3. **Docs (#3):** `CLOUD_USAGE.md` — script-only builds (raw `docker build .` deprecated, with the one-paragraph saga rationale), the substrate-manifest policy, the anchor-update procedure, and a `--job-timeout` table (26-yr = 21600s, never 14400). `execution_manual.md` — new CLI section (build script, manifest generate/verify, save-anchor 3-step). `Coordination/PROTOCOL.md` — stale "auto-rebuilt on every push" claim corrected (CI blocked on `AWS_ROLE_TO_ASSUME`, T-109).

## #1 — shared anchors

### Setup-script change

After the existing per-agent `cp -r data/governor`, the two anchor dirs are replaced with symlinks to the director's. Rationale comment in-script: the anchor is the canon-relevant seed, pinned by the manifest, updated only via the deliberate 3-step procedure; live files keep per-agent isolation (they mutate per-run and are manifest-excluded since T-131).

### In-place conversion of the 4 existing worktrees

Performed by the director mid-task (I had archived all 8 anchor dirs first; my conversion command was superseded). Verified post-conversion: all 8 paths are symlinks → `/Users/jacksonmurphy/Dev/trading_machine-2/data/governor/_{isolated,cap_recal}_anchor`.

### Divergence found during archiving (flag for the director)

| Agent | `_isolated_anchor` vs canonical | `edges_archive_pre_t037.yml` | Implication |
|---|---|---|---|
| a | **DIVERGED** (`edges.yml` md5 `8da9ce85…`) | missing | pre-May-12-class stale anchor; local isolated runs in A's worktree were seeded from a NON-canonical state until today |
| b | identical | present | (canonical source — the director restored from it in T-131) |
| c | identical | present | no behavior change |
| d | **DIVERGED** (`edges.yml` md5 `818330dc…`) | missing | same as A |

A and D's local gauntlet/diagnostic results that depended on the anchor seed are not directly comparable across the conversion boundary. Cloud results are unaffected (images bake the build-worktree's anchor — built from director or agent-b, both canonical-class since June 10). The archived anchors preserve the exact pre-conversion states for any retro-comparison.

## #2 — bake-exclusion

- `build_backtest_image.sh` stages `data/governor` with 9 anchored excludes mirroring `LIVE_MUTABLE_GOVERNOR` (cross-referenced in comments both ways).
- **Why anchored patterns:** rsync `--exclude='edges.yml'` matches the basename at ANY depth → would also exclude `_isolated_anchor/edges.yml` → broken images (restore_anchor would fail / silently seed nothing). `--exclude='/governor/edges.yml'` anchors at the transfer root. Caught at design time, worth recording as a gotcha.
- **Effect:** images of the same commit are byte-identical regardless of local run activity — the last image-content surface that varied with worktree state is gone (T-127 closed code/pycache/junk; this closes live governor).

### Verification (per dispatch constraint)

1. Fresh `build_backtest_image.sh HEAD` build (commit `9496fe9`): manifest gate **green** (`147e9d0e…`, 14,026 files), provenance labels set.
2. Image inspection: `/app/data/governor/` contains anchors + inert legacy clutter only — **zero live files**; `/app/data/governor/_isolated_anchor/` fully populated (the worktree's anchor SYMLINK was followed by `rsync -aL` as designed).
3. 2022 sanity cell in the container: canon **`0a62b7541d3dfe697905d279b3eb1431`**, Sharpe 1.6 — **bitwise-identical** to the T-131 Run-N/Run-X reference (reference validity confirmed: `git diff 9374871..HEAD` over engine dirs = empty; only the manifest content-neutral delta + `run_isolated`'s behavior-identical `copyfile` hardening).

## #3 — docs

- **`docs/Cloud/CLOUD_USAGE.md`:** "Refreshing the image" rewritten — `build_backtest_image.sh` is the only sanctioned path; raw `docker build .` deprecated with the stale-bytecode rationale; substrate-manifest policy paragraph (pinned vs excluded, "local runs can NOT block builds"); anchor-update 3-step procedure; CI status corrected (blocked on `AWS_ROLE_TO_ASSUME`); new `--job-timeout` table (single-year 1h / 12-yr 3h / 16-yr 4h / **26-yr 6h, never 14400**) with the T-109 SIGKILL-during-upload story.
- **`docs/Core/execution_manual.md`:** new "REPRODUCIBLE IMAGE BUILDS + SUBSTRATE PIN" section (per the CLAUDE.md new-CLI rule) — build script, manifest verify/generate, save-anchor procedure, shared-anchor note, timeout pointer.
- **`docs/Coordination/PROTOCOL.md`:** line 195's stale "auto-rebuilt on every main push" claim replaced with script-only builds + CI-blocked status.

## Acceptance vs dispatch

| # | Criterion | Status |
|---|---|---|
| 1 | Setup script + 4 worktrees on shared write-protected anchor; old anchors archived | DONE — script updated; conversion done in-place (director); 8 anchor dirs archived under `Archive/anchor_divergence_t133/`; all 8 paths verified symlinks; 0o444 protection carried (T-131) |
| 2 | Live files excluded from bake; build + canon sanity pass | DONE — anchored rsync excludes; manifest gate green; image content verified; 2022 canon `0a62b754…` bitwise vs reference |
| 3 | Docs updated | DONE — CLOUD_USAGE + execution_manual + PROTOCOL |
| 4 | Audit + proposed ledger row in outbox | DONE |
| 5 | Branch pushed NOT merged | DONE |

## Hard constraints — confirmed

- [x] Old anchors archived (never deleted) before conversion; agents' LIVE governor copies untouched.
- [x] Compute: 1 local container cell (2022) — zero cloud spend.
- [x] No TASK_LEDGER write; no `cockpit/dashboard/`; branch push only.

## Surprises

1. **Agents A and D had silently diverged anchors** — the T-131 divergence class wasn't just the director-vs-agent-b pair; it was 3-of-5 worktrees (director, A, D). Every local isolated run A and D made was seeded from a stale anchor. The symlink conversion ends the class structurally; the archived anchors allow retro-comparison if any of their local findings look anomalous.
2. **The rsync basename-matching gotcha** — a naive exclusion list would have silently produced images with EMPTY anchors (the harness's seed state). Worth remembering whenever excluding by filename: anchor the pattern.
3. The dispatch's sanity fallback ("cite C's running campaign arm0 if it matches `529e5520`") wasn't needed — the local 2022 cell was cheaper and bitwise-conclusive.

## Files

- **MOD** `scripts/setup_agent_worktree.sh` — anchor symlinks for future worktrees.
- **MOD** `scripts/build_backtest_image.sh` — anchored live-file bake-excludes.
- **MOD** `docs/Cloud/CLOUD_USAGE.md`, `docs/Core/execution_manual.md`, `docs/Coordination/PROTOCOL.md`.
- **NEW** `docs/Audit/governor_hygiene_followups_t133_2026_06_10.md` (this).
- (Filesystem, not in-branch: `Archive/anchor_divergence_t133/agent_{a,b,c,d}/` — 8 archived anchor dirs; 8 symlinks across 4 worktrees.)

## Forward-look

1. When the CI workflow is revived (post-`AWS_ROLE_TO_ASSUME`), migrate it to call `scripts/build_backtest_image.sh` (noted in CLOUD_USAGE).
2. Optional: fresh S3 substrate snapshot under `147e9d0e…` (carried from T-131; still pending, cheap).
3. A/D anomaly check: if any A/D local-measurement finding from May 12–June 10 becomes load-bearing, re-verify it against the canonical anchor (their archived anchors enable an exact A/B).
