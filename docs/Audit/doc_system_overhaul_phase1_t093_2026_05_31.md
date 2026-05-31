# T-2026-05-31-093 — Documentation-system overhaul, Phase 1

**Date:** 2026-05-31
**Branch:** `feature/doc-system-overhaul-phase1-t093` (off origin/main; main has T-088 + T-089 + T-090 + T-091 merged)
**Worker:** Agent B

## Verdict — 4 new files + README edits shipped; doc_lint baseline = 3 WARN / 0 FAIL / exit 0

The collision-free subset of the dev-reviewed doc-system overhaul is in. `.claude/settings.json` and `CLAUDE.md` are explicitly DEFERRED to Phase 2 pending coordination with the parallel statistical-discipline-hooks workstream — the whole reason for the phase split.

## What shipped

### 1. `docs/State/CURRENT_STATE.md` (NEW)

The at-a-glance dashboard. Hard caps per section (≤5 each section, exactly 1 next-decision, ≤5 standing constraints). Reconciled against MEMORY.md + the current task state — NOT blind-pasted from the dev's skeleton. Key reconciliations from the skeleton:

- **Validated** = none yet (correct as of 2026-05-31; no substrate-robust + factor-adjusted + MBL-clearing positive finding).
- **In flight** = T-092 only (Agent A's deep-substrate baseline). The skeleton's old "Next decision: run multi-decade-window backtest" was moved into "In flight" because T-092 IS that backtest, currently running.
- **Next decision** is now **conditional on T-092's verdict** (not "go run T-092" since T-092 is already in flight).
- **Standing constraints** use **run_registry shows 125 rows** per user correction (skeleton said 188; the user's late-stage correction was applied). Stated both honestly: "125; effective ~260+ incl. cloud cells not all back-synced."
- **Refuted/superseded** = updated to 5 most-recent-and-relevant per MEMORY: T-057 12-yr refuted (T-053b), T-055 vol-target chapter closed 12-yr (T-055h), T-088 dead-knob, T-002 baseline 0.270 superseded by T-035 0.598, 2026-05-06 Engine E refutation reversed by T-087/T-089.
- **Last reconciled stamp** at the top per dispatch refinement #6: "If >3 days old, read source docs before quoting state."

### 2. `docs/State/TASK_LEDGER.md` (NEW)

Hand-maintained for now (per dev refinement #5; auto-gen from frontmatter is the future once the parallel workstream's `result_emit` schema lands). Backfilled T-035 onward with the columns the dev refined: `T-ID | date | title | status | cells_attempted | cells_succeeded | outcome | audit doc`. 29 rows; all complete.

Status values: `done` / `refuted` / `superseded` / `in-flight` / `blocked`. Cells columns are `—` for local/non-campaign tasks (~75% of the rows); populated for cloud campaigns where the audit doc cites a cell count (T-053b: 13/13, T-055g: 75/75, T-057b: 50/50).

### 3. `scripts/doc_lint.py` (NEW) + `.pre-commit-config.yaml` wire-up

7 checks per dispatch acceptance. Runs in <1 s; same model as the existing feature-foundry hook. Hooks fire on changes to `docs/`, `scripts/`, or `.pre-commit-config.yaml`.

**Current baseline (clean on main + T-093 files):**

| # | Check | Severity | Outcome |
|---|---|---|---|
| 1 | MEMORY.md byte count | **WARN** | 23,467 / 24,985 bytes (93.9% of 24.4 KB cap) — within 20% of cap, plan archival |
| 2 | CURRENT_STATE.md freshness | PASS | mtime 0.0 days ago (limit 3) |
| 3 | MEMORY supersession markers resolve | PASS | all 4 markers resolve |
| 4 | MEMORY audit-doc refs exist on disk | PASS | no audit refs in MEMORY (memory cites memory slugs) |
| 5 | MEMORY entries have a date in header | **WARN** | 10 of 87 undated — all legacy archived hooks that pre-date the dating convention (`feedback_no_manual_tuning`, `project_phantom_stops_fix`, etc.); backfill follow-up |
| 6 | TASK_LEDGER rows complete | PASS | all 29 rows complete with valid status |
| 7 | scripts/*.py covered in execution_manual | **WARN** | 23/133 scripts documented (110 missing) — WARN-only per dispatch (110 is too many to backfill in this task; promote to FAIL after a separate execution_manual coverage dispatch) |

**Exit code: 0** (no FAILs; WARNs do not block).

**Check refinements applied during the build:**

- **Check 3 (supersession markers)** initially fired FAIL on `C-collapses-1` because my check only looked for filename-slug-match or T-ID-match. The reference is actually a tag-style label (the memory file `project_substrate_audit_2_edge_overfit_2026_05_09.md` carries that label in its title). Relaxed the check to also resolve tag-style refs by searching memory file bodies. This is a real bug fix in the lint, not a corpus issue.
- **Check 5 (undated entries)** kept as WARN, not FAIL. The 10 undated entries are real archived hooks that pre-date the dating convention. Inventing dates retroactively would be worse than the WARN. The check was tagged FAIL-promotion-ready after the corpus is cleaned.

### 4. `docs/Audit/README.md` (NEW)

Topic-grouped index of `docs/Audit/`. Columns: `topic | audit doc | date | verdict`. Backfilled all major audits across the topic groups:

- Baseline + measurement infrastructure (4)
- Engine A — Alpha / signal contracts (3)
- Engine B — Risk / vol-targeting (7, the full T-055 arc + T-088)
- Engine A → B/C confidence-gated execution (6, the T-057 arc + 12-yr re-verify)
- Engine E — Regime detection (2, T-087 + T-089)
- Substrate (T-081, T-082)
- Code quality / silent-mismatch family (4, T-054 + audit + T-090 + T-091)
- Discovery / Engine D / Engine F lifecycle (5)
- Documentation system (1, this dispatch's audit)
- In-flight (T-092 + Phase 2 doc-system)

Plus an explicit "Conventions" section explaining REFUTED vs SUPERSEDED, multi-doc T-ID handling, and chapter-closer rows.

### 5. `docs/README.md` edits

- **Quick-links table** — added CURRENT_STATE.md (top), TASK_LEDGER.md, Audit/README.md. Added a sentence explaining the CURRENT_STATE-vs-forward_plan relationship and the 3-day staleness fall-back.
- **`State/` table** — added CURRENT_STATE.md + TASK_LEDGER.md as new rows.
- **NEW section: `Audit/` vs `Measurements/`** (dispatch item F) — the most-confused distinction in the doc tree. Side-by-side comparison: Audit holds analysis-with-verdict (one per T-ID/question), Measurements holds raw cell-level results. Audits CITE measurements; measurements are SOURCE DATA. Quick rule: "does it have a verdict? Yes → Audit. No → Measurements."
- **`Measurements/` section** retitled "raw point-in-time results" to disambiguate from audits.
- **NEW `Audit/` section** — with pointer to `Audit/README.md` topic index.
- **"I want to..." cheat-sheet** — added 3 new rows (at-a-glance status, T-ID lookup, audit topic search).

## What is DEFERRED to Phase 2

Per dispatch hard constraint, the following were NOT touched in this task:

- **Any edit to `.claude/settings.json`** — collision with the parallel statistical-discipline-hooks workstream.
- **Any edit to `CLAUDE.md`** — possible collision + needs coordination.
- The SessionStart-prepend logic (dev refinement #3) — settings.json.
- The Stop-hook BLOCK on stale CURRENT_STATE (dev refinement #7) — settings.json.
- The forward_plan-vs-CURRENT_STATE rule in CLAUDE.md (dev refinement #8).
- The NON_NEGOTIABLES.md split out of CLAUDE.md.
- The reading-order entry in CLAUDE.md adding CURRENT_STATE to the "always loaded" set.
- Quarterly archive sweep (dev item G), plan-mode artifact ownership (item I), bidirectional MEMORY↔audit linking ENFORCEMENT in doc_lint (item E — the WARN currently exists; full FAIL-level enforcement is Phase 2).

Document trail: this audit doc is the parking-place for the Phase 2 list. Phase 2 lands after the director coordinates settings.json ownership with the other workstream.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | CURRENT_STATE.md created, reconciled (not blind-pasted), hard caps respected, last-reconciled stamp | DONE |
| 2 | TASK_LEDGER.md created + backfilled T-035 onward with cells columns | DONE (29 rows) |
| 3 | doc_lint.py created + 7 checks + wired to .pre-commit-config.yaml; run + report findings | DONE — 3 WARN / 0 FAIL / exit 0 |
| 4 | docs/Audit/README.md topic index created + backfilled | DONE |
| 5 | docs/README.md updated (nav rows + audit/measurements distinction + audit-index pointer) | DONE |
| 6 | NO edits to .claude/settings.json or CLAUDE.md | DONE (verified diff) |
| 7 | audit doc + branch push | DONE (this; pushed at close) |

## Hard constraints — confirmed met

- [x] No edits to `.claude/settings.json`.
- [x] No edits to `CLAUDE.md`.
- [x] `doc_lint.py` runnable standalone (`python scripts/doc_lint.py`) AND as pre-commit hook.
- [x] Exit non-zero on FAIL, zero on WARN-only (verified: `exit: 1` synthetic case validated; current `exit: 0` is the real baseline).
- [x] CURRENT_STATE reconciled against MEMORY + live state (T-092 in flight, run_registry 125 per user correction).
- [x] Memory dir is correctly identified as `~/.claude/projects/.../memory/` — NOT in this repo's git.

## Forward-look — Phase 2 (after director coordinates settings.json ownership)

Per dispatch, Phase 2 picks up:

1. `.claude/settings.json` SessionStart-prepend (loads CURRENT_STATE into every session prelude).
2. `.claude/settings.json` Stop hook — BLOCK session end if `CURRENT_STATE` last-reconciled is stale beyond N days.
3. `CLAUDE.md` reading-order — add CURRENT_STATE to the always-loaded set.
4. `CLAUDE.md` supersession sentence — explicit rule that older verdicts in audits/measurements are superseded automatically when TASK_LEDGER `status` flips.
5. `CLAUDE.md` `forward_plan`-vs-CURRENT_STATE rule (which to edit when).
6. `NON_NEGOTIABLES.md` split — extract CLAUDE.md non-negotiables to their own file (dev item G).
7. End-to-end hook test (dev item B): simulate session lifecycle, verify SessionStart-prepend + Stop-BLOCK fire correctly.
8. Quarterly archive sweep policy (dev item G).
9. Plan-mode artifact ownership rule (dev item I).
10. doc_lint bidirectional MEMORY↔audit linking promoted from WARN to FAIL (dev item E).

The director will brief Phase 2 once the shared-file ownership is agreed with the other workstream.

## Surprises

1. **`run_registry` row count: 125, not 188.** User flagged this on dispatch hand-off. Caught the dev's skeleton stating 188; CURRENT_STATE's Standing-constraints uses 125. Effective ~260+ including cloud cells not all back-synced into the registry. The discrepancy is interesting in its own right — there's a cloud→registry sync gap that's a real ops surface (not in scope for T-093, but flagged here for the director).

2. **Check 3 had a real bug, not a corpus issue.** My initial `_SUPERSEDED_RE` resolver looked only for filename slugs or T-IDs. The MEMORY entry `(SUPERSEDED by C-collapses-1)` failed both checks because `C-collapses-1` is a tag-style label embedded in another memory's title prefix (`project_substrate_audit_2_edge_overfit_2026_05_09.md` carries that tag). Relaxed the check to also resolve tag-style refs by searching memory bodies. **The corpus was already correct; the lint was wrong.** Good reminder: when a lint fires on a single legacy case, suspect the lint before suspecting the corpus.

3. **MEMORY.md is at 93.9% of cap.** Two more sizeable entries would push it over 100% and trigger FAIL. The 2026-05-07 trim archived 8 hooks; a similar pass is overdue. Not in scope here, but flagged: a "memory archive sweep" follow-up is the cheapest way to give headroom.

4. **110 of 133 scripts are NOT documented in execution_manual.** The doc system has a quietly massive gap. WARN-only is correct for now — backfilling 110 entries in this task would balloon scope — but a separate dispatch to backfill execution_manual is the right path. Promote check 7 to FAIL once that's done.

5. **The dev's "Recently refuted" skeleton had stale items.** "F6 surviving-6 Sharpe 0.9154" was in the skeleton but not in current MEMORY; replaced with the more recent + load-bearing 2026-05-06 Engine E refutation reversal (T-087/T-089). Honored the dispatch's "verify against MEMORY.md" instruction.

## Files

- **NEW** `docs/State/CURRENT_STATE.md` — at-a-glance dashboard, hard caps, last-reconciled stamp
- **NEW** `docs/State/TASK_LEDGER.md` — 29-row T-035-onward backfill
- **NEW** `scripts/doc_lint.py` — 7 checks, <1s, standalone + pre-commit
- **NEW** `docs/Audit/README.md` — topic-grouped audit index
- **NEW** `docs/Audit/doc_system_overhaul_phase1_t093_2026_05_31.md` (this)
- **MOD** `docs/README.md` — quick-links + State table + Audit/Measurements distinction + cheat-sheet
- **MOD** `.pre-commit-config.yaml` — doc-lint hook wired

## CI runtime

`scripts/doc_lint.py` end-to-end: <1 s. Pre-commit hook trigger paths: `docs/.*`, `scripts/.*\.py`, `.pre-commit-config.yaml`. Cheap permanent gate.

## Phase 2 trigger

Phase 2 unblocks the moment the director resolves shared-file ownership with the parallel statistical-discipline-hooks workstream. This audit doc is the parking-place for the Phase 2 backlog; reference it when the next dispatch lands.
