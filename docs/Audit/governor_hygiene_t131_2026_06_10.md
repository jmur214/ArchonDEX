# T-2026-06-10-131 — Governor hygiene: the "isolation leak" was non-propagation, not a leak; live state proven canon-irrelevant; manifest policy fixed

**Date:** 2026-06-10
**Branch:** `feature/governor-hygiene-t131`
**Worker:** Agent B
**Predecessors:** T-127 (manifest guard that surfaced the drift), T-099 (run_isolated determinism floor)
**Status:** DONE — Part A diagnosed (no anchor-write bug exists; two real-but-different problems found + fixed/hardened), Part B proven + shipped (Option 1 with evidence).

## TL;DR

1. **Nothing ever wrote INTO the director's anchor.** The "anchor mutation + missing file" was an inverted reading: the director's `_isolated_anchor/` was the **stale pre-May-12 original** (last written May 7, mtime-verified). The canonical anchor moved FORWARD in the agent-b worktree on May 12 (T-037-era edges-archive cleanup + `--save-anchor` refresh: `edges.yml` slimmed 86,674→56,373 bytes, GA edges archived into the new `edges_archive_pre_t037.yml`). **`data/governor` is gitignored → that update never propagated to the director.** "Drift" = 29 days of silent cross-worktree divergence of canon-relevant, git-invisible state.
2. **The live-file drift decomposes into two writer classes:** (a) Discovery-era GA artifacts (24 `composite_gen1_*` edges with `status: error` in `edges.yml`; `ga_population.yml`, Apr-28 mtime — predates `ga_population`'s addition to the isolation scope on May 11); (b) **unscoped observability appends** — `edge_metrics.json` (write-only via `governor._save_metrics`, never read back) and `decision_diary.jsonl` (append-only, no engine readers) are NOT in `ISOLATED_FILES`, so even perfectly-isolated runs mutate them. That is BY DESIGN for observability logs — but under T-127's original manifest policy it meant **any local run blocked all image builds**.
3. **`isolated()` has no restore bug** — entry-restore + exit-restore already wrapped in `try/finally`; the only anchor writer is operator-invoked `--save-anchor`. Bonus live demonstration: my first proof-run crashed because `restore_anchor` correctly tried to DELETE a stray `ga_population.yml` (absent from anchor) and hit my read-only docker bind-mount — the deletion-on-restore hygiene working exactly as documented.
4. **PROVEN: baked/live governor state is canon-irrelevant when the anchor is canonical.** Controlled local pair on the clean-pipeline image: Run N (canonical live) vs Run X (the **entire June-10 drifted live set** — GA-laden `edges.yml` + `ga_population.yml` + drifted metrics + diary — copied into the container) → **bitwise-identical 2022 canon `0a62b7541d3d…`, Sharpe 1.6 both**. Mechanism: `isolated()` restores every scoped file from the anchor ON ENTRY, before the engine reads anything. Corroborating 26-yr evidence already existed accidentally: T-127's Cell B (director's stale GA-laden governor baked) ≡ Cell C (canonical governor baked) ≡ `529e5520…`.
5. **Shipped (Option 1 + hardening):** live mutable governor files excluded from the substrate manifest (`LIVE_MUTABLE_GOVERNOR`, 9 files; manifest regenerated → 14,026 files, md5 `147e9d0e781ca79eecd716b116f52d10`, verify green); **anchors stay pinned** (they ARE the reproducibility-relevant input). `save_anchor` now write-protects anchor files (0o444) + prints the manifest-regen reminder; `restore_anchor` made perms-safe (`copyfile` + pre-chmod). **The "local run blocks builds" trap is closed.**

## Part A — forensics

### Specimen characterization (`Archive/governor_drift_2026_06_10/`)

| Specimen | mtime | vs canonical | Content of the delta |
|---|---|---|---|
| `edges.yml` (live) | May 31 02:06 | +1,429 diff lines | 24 `composite_gen1_*` GA edges (`status: error`, `tier: feature`) the May-12 cleanup archived out; plus lifecycle counter/status accretion |
| `_isolated_anchor_edges.yml` | **May 7 01:49** | +1,306 diff lines | same GA edges — this is the **pre-cleanup anchor**, frozen since May 7 |
| `edge_metrics.json` | May 10 01:28 | 74 diff lines | per-edge diagnostics rewritten by `governor._save_metrics` (write-only) |
| `decision_diary.jsonl` | May 10 01:28 | 205 diff lines | append-only decision log entries |
| `ga_population.yml` | Apr 28 | (absent from canonical) | Discovery GA population from before the file entered isolation scope (added 2026-05-11, T-026) |

The mtimes tell the story: **every specimen predates June** — none of this was new mutation from the June saga; it was accumulated divergence that T-127's manifest made visible for the first time.

### Timeline (reconstructed, mtime-anchored)

1. **Apr 28** — Discovery run writes `ga_population.yml` (file not yet isolation-scoped; scoped May 11).
2. **May 7 01:49** — director's anchor last refreshed (`--save-anchor`), GA edges still in `edges.yml`.
3. **May 8 18:06** — agent worktrees created; each gets a private COPY of `data/governor` (everything else in `data/` symlinks back to the director).
4. **May 12 12:03** — in the agent-b worktree: T-037-era cleanup archives GA edges (`edges.yml` 86,674→56,373; `edges_archive_pre_t037.yml` created) + anchor re-saved. **Gitignored → never reaches the director.**
5. **May 10–31** — director-side processes mutate the director's live files (observability appends; `edges.yml` accretion to 89,545 by May 31 02:06 — T-092-era runs).
6. **June 6–10** — every director-built image bakes the director's stale governor. **Canon impact: zero** (proven below) — the GA edges are `status: error` (load-inert) and `isolated()` restores from the anchor anyway.
7. **June 10** — T-127's manifest (generated from agent-b = the post-cleanup state) becomes the pin → director's governor fails verify → director restores from agent-b + archives the specimens → this task.

### The writer map (who can mutate `data/governor/**`)

Engine writers (all run inside backtests; rolled back for SCOPED files when under `isolated()`): `governor.py` (8 write-ops, incl. `_save_metrics` → `edge_metrics.json` — UNSCOPED), `lifecycle_manager.py` (3), `journal.py` (5), `discovery.py` (4) + `genetic_algorithm.py` (2) (→ `ga_population.yml`, scoped since May-11), `edge_registry.py` (1), `decision_diary.py` (2 — UNSCOPED), `factor_alpha_gate.py` (1). Direct scripts that bypass `isolated()` entirely: `run_oos_validation.py`, `prune_strategies.py`, `reset_base_edges.py`, `journal_apply.py`, `inter_edge_correlation_regime.py`.

So isolation coverage has exactly two structural gaps: (a) the two observability files are unscoped **on purpose** (append-logs should persist; deleting the decision diary as a run side-effect would be observability data loss); (b) the direct scripts are sanctioned mutators (e.g. `reset_base_edges`). Neither is a bug; both were trapped by the old manifest policy, which is what actually needed fixing.

### Fixes shipped (harness-scope, autonomous per dispatch)

- **`save_anchor()` write-protects the anchor** — files chmod 0o444 after snapshot, with a printed reminder that a deliberate anchor update = `--save-anchor` + manifest regen + commit in one PR. Any rogue write into the anchor now fails loudly instead of silently re-seeding every future measurement.
- **`restore_anchor()` perms-safe** — `copyfile` (content only, no perm propagation) + pre-chmod of a read-only dst; without this the 0o444 anchors would break the next restore.
- **`isolated()` needed no fix** — already `try/finally`-restored on both entry and exit.

## Part B — the proof + the policy

### The question

Does BAKED live governor state affect the canon at all, given `run_isolated` restores from the anchor?

### The proof (Run N vs Run X — controlled, local, zero cloud spend)

Image: the clean-pipeline `:dev` (provenance-labeled commit `3953085`, substrate `a40d5483`). Window: 2022 single-year, `--runs 1 --task q1`.

| Run | Live governor state | canon_md5 | Sharpe |
|---|---|---|---|
| N | canonical (as baked) | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |
| X | **entire drifted June-10 set copied in** (GA-laden `edges.yml` 89,545B + `ga_population.yml` + drifted `edge_metrics.json` + `decision_diary.jsonl`) | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |

**Bitwise identical.** The restore-on-entry mechanism makes scoped live files irrelevant; the unscoped observability files are write-only. (First Run-X attempt crashed on a docker artifact — `restore_anchor` correctly tried to unlink the stray `ga_population.yml`, which was a read-only bind mount; re-run with copy-in semantics. The crash itself is a live demonstration of the delete-strays-on-restore hygiene.)

Corroboration at 26-yr depth (accidental but controlled): T-127 Cell B baked the director's **stale GA-laden governor + stale May-7 anchor**; Cell C baked the canonical agent-b governor + May-12 anchor — identical canon `529e5520…`. (The anchor delta there was GA edges with `status: error` = load-inert, so even the anchor difference happened to be benign — luck, not structure, which is why anchors STAY pinned.)

### The policy (Option 1, shipped in this branch)

`scripts/gen_substrate_manifest.py` now excludes `LIVE_MUTABLE_GOVERNOR` (9 files: the 5 `ISOLATED_FILES`, the 2 journal-mode files, the 2 write-only observability files) from generate AND verify. **Anchors (`_isolated_anchor/`, `_cap_recal_anchor/`) + all other governor content stay pinned.** Manifest regenerated + committed: **14,026 files, manifest-md5 `147e9d0e781ca79eecd716b116f52d10`** (was 14,032 / `a40d5483…`; delta = 6 live files present at generate-time — `ga_population.yml`, absent, was never in it; verify green post-change; exercised `--save-anchor` and re-verified green, confirming anchor re-saves with identical content don't trip the manifest).

Why not Option 2/3 (read-only live files / chmod guards): the live files are SUPPOSED to mutate (lifecycle, observability) — write-protecting them breaks sanctioned behavior; the anchor write-protection (shipped) covers the part of Option 2/3 that's actually load-bearing. The manifest now guards exactly the canon-relevant surface: anchors + processed + raw.

### Operational outcome

- Local runs (isolated or not) can no longer block image builds — the trap is closed.
- Anchor changes are loud, deliberate, 3-step, and manifest-tracked.
- S3 snapshot note for the director: the existing snapshot at `substrate/a40d5483…/` includes the old live files; the new manifest hash (`147e9d0e…`) defines the new canonical set — recommend a fresh snapshot prefix on next campaign (or treat live-file objects in the old prefix as ignorable; the anchors there were corrected by the director on June 10).

## Acceptance vs dispatch

| # | Criterion | Status |
|---|---|---|
| 1 | Leak characterized + fix proposed/shipped | DONE — no anchor-write leak exists (stale-divergence via gitignored non-propagation + sanctioned unscoped observability writers); `save_anchor` 0o444 + perms-safe restore shipped (harness-scope) |
| 2 | Anchor-vs-live canon question PROVEN | DONE — Run N ≡ Run X bitwise (`0a62b754…`) with the ENTIRE drifted live set injected; corroborated at 26-yr by Cell B ≡ Cell C (`529e5520…`) |
| 3 | Manifest-policy recommendation + regenerated manifest committed | DONE — Option 1 shipped with evidence; manifest `147e9d0e…` (14,026 files) committed atomically with the policy |
| 4 | Audit + proposed ledger row in outbox | DONE |
| 5 | Branch pushed NOT merged | DONE |

## Hard constraints — confirmed

- [x] No manual edits to `data/governor/*` content (forensics read-only on Archive specimens; the only governor write was the sanctioned `--save-anchor` exercise in MY worktree, byte-identical content, manifest-verified green).
- [x] No `cockpit/dashboard/`. No TASK_LEDGER write (row proposed in outbox).
- [x] Compute: ZERO cloud cells — the proof pair ran locally on the existing clean image (2 × 2022 container runs).
- [x] Branch push only.

## Surprises

1. **The dispatch's "anchor mutated" framing was inverted** — the director's anchor never moved; the WORLD moved around it (agent-b's May-12 refresh + gitignored non-propagation). The right mental model: `data/governor` is canon-relevant state with NO propagation mechanism between worktrees — until T-127's manifest accidentally became one. Now it's the official one.
2. **The first proof-run crash WAS the isolation working** — `restore_anchor`'s delete-strays path fired on the bind-mounted `ga_population.yml`. Accidental positive test of the hygiene the harness promises.
3. **`edge_metrics.json` is write-only** (`governor._save_metrics`, "for dashboards/analytics", never read back) — its presence in the original manifest pin was pure friction with zero reproducibility value.
4. **2022 clean-image canon = `0a62b754…` — identical to the June-6 TAINTED images' 2022 canon** (T-125 det-gate 3/3). More evidence the pyc taint's behavioral divergence (T-127) was conditional on multi-year paths: 2008 and 2022 single-year canons were identical across tainted/clean images; only deep windows diverged.
5. **The May-12 anchor refresh itself was never propagated to the director for 29 days** and nothing noticed until a build guard existed. Silent-divergence-until-guard is the recurring theme of this whole arc (T-088 silent-mismatch family → T-127 substrate pin → this).

## Files

- **MOD** `scripts/gen_substrate_manifest.py` — `LIVE_MUTABLE_GOVERNOR` exclusion (generate + verify) with full rationale comment.
- **MOD** `config/substrate_manifest.sha256` — regenerated under the new policy (14,026 files, md5 `147e9d0e…`).
- **MOD** `scripts/run_isolated.py` — `save_anchor` write-protection (0o444 + reminder); `restore_anchor` perms-safe `copyfile`.
- **NEW** `docs/Audit/governor_hygiene_t131_2026_06_10.md` (this).

## Forward-look (director gates)

1. **Adopt the anchor-update procedure** into SESSION_PROCEDURES/CLOUD_USAGE: `--save-anchor` → regenerate manifest → commit both in one PR.
2. **Fresh S3 substrate snapshot prefix** under the new manifest hash on the next campaign (cheap; or document the old prefix's live-file objects as non-canonical).
3. **Optional:** worktree-setup script could symlink `data/governor/_isolated_anchor` to the director's (single source of truth) — propose-first; changes the worktree contract.
4. **Optional bake-exclusion:** stop baking the 9 live files into images entirely (restore/lazy-create covers the cloud path) — would restore full byte-identity of images across days; left unshipped because canon-reproducibility (the contract that matters) is already proven and the runtime file-presence change deserves its own verify cell.
