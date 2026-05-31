# Documentation-system overhaul — proposal for review

**Date:** 2026-05-31
**Status:** PROPOSAL — needs review (user + other dev) before any change to the
doc system itself (CLAUDE.md says changes to the documentation system are
propose-first, not autonomous).
**Author:** director (Claude)

## Why now — measured symptoms of erosion

The doc system worked well at ~1 measurement/session. The cloud campaigns
pushed us to ~10 campaigns in 3 days, and the **synthesis layer never scaled
with execution**. Concrete, measured failures (2026-05-31):

1. **MEMORY.md breached its load cap.** It was **37.6 KB against the ~24.4 KB
   limit** → the SessionStart loader only injected PART of the index → recent
   entries silently fell off the bottom of what loads each session. This is
   itself an instance of the silent-truncation bug class. **(FIXED 2026-05-31:
   compressed to 14.6 KB, all 84 entries + links preserved, detail intact in
   backing files.)**

2. **No single "current truth" snapshot.** `docs/State/` has 6 files
   (GOAL, ROADMAP, forward_plan, health_check, lessons_learned,
   deployment_boundary) but none is a one-screen "where are we right now."
   Reconstructing state means reading 85 memory files + 49 audit docs + 6
   state files → context rebuilt from fragments each session → drift.

3. **Task-ID sprawl, no ledger.** 38 T-IDs in memory, 49 audit docs, tangled
   numbering (T-055c/d/e/f/g/h/b; T-057b/c/c-det/c-det-followup). No map from
   T-ID → status → outcome. Real cost: user + director both recently
   half-thought "didn't we already do the Stooq deep-history work?" — we had
   (T-081/T-082) but it wasn't glanceable, AND we'd never actually run a
   backtest on the deep window we built.

4. **Reversals don't force reconciliation.** When a finding flips (Engine E
   refuted→predictive; baseline phantom→borderline-real), a new memory entry
   gets added ALONGSIDE the old one with equal weight. Nothing marks the old
   one stale at write time.

## Root-cause insight (this should shape the fix)

The resurfacing machinery already exists and works — it's the **SessionStart
hook** in `.claude/settings.json`, which auto-injects `=== LAST 3 SESSION
SUMMARIES ===` into context every session, plus the **Stop hook** that reminds
the agent to write a session summary at end. That pair is the "how will I know
in 20 days" answer: **the hook tells the agent, not the agent's memory.**

The problem: **the hook surfaces session NARRATIVES, not current TRUTH.** What
auto-loads is "here's what happened in the last 3 sessions" (a story), not a
state snapshot. The State/ files only load if the agent chooses to read them.

**Therefore the fix is NOT new free-floating files** (those rot, exactly as the
user warned). The fix is to teach the EXISTING always-firing points to surface
+ maintain a state snapshot. Every addition must plug into one of three slots:
- **SessionStart hook** → so it AUTO-loads (no agent memory required)
- **Stop hook** → so the agent is REMINDED to update it at session end
- **CLAUDE.md reading order + docs/README.md nav table** → so it's FINDABLE

## Proposed changes (concrete)

### Change 1 — `docs/State/CURRENT_STATE.md` (NEW, mutates in place)
One screen, REWRITTEN (not appended) at session end. Sections:
- **Validated:** what has cleared the bar (with the bar: ci_low > X on Y-yr window at N trials)
- **Refuted/closed:** what's dead and why (one line each)
- **In flight:** active dispatches (T-ID → agent → expected outcome)
- **Next decision:** the single most important open fork
- **Standing constraints:** the live numbers (current N, MBL requirement, substrate window, baseline Sharpe)

Wired in via:
- **SessionStart hook:** add a line that `cat`s the top ~40 lines of
  CURRENT_STATE.md alongside the existing 3 session summaries.
- **Stop hook:** add CURRENT_STATE.md to the end-of-session update reminder.
- **docs/README.md:** top row of the "current truth" table.
- **CLAUDE.md reading order:** item 2 (right after CLAUDE.md itself).

### Change 2 — `docs/State/TASK_LEDGER.md` (NEW, append-per-task table)
One markdown table: `T-ID | date | title | status | one-line outcome | audit-doc`.
status ∈ {done, refuted, superseded, in-flight, blocked}. Backfill the major
T-IDs (T-035 onward where the cloud era starts). Kills the "did we do X?" class.

Wired in via:
- **docs/README.md** "current truth" table row.
- **Stop hook** reminder ("did a task complete/change status? → add/update a TASK_LEDGER row").
- Not in SessionStart (too big to auto-load); it's the lookup table, reached on demand.

### Change 3 — Supersession discipline (process rule, ~0 code)
When a finding reverses, the OLD memory entry gets a `(SUPERSEDED by [x])`
marker in its MEMORY.md one-liner at the same time the new entry is written.
(Already done manually for T-057/T-055e/Engine-E today; this makes it a rule.)

Wired in via:
- **CLAUDE.md memory section** (always loaded): one sentence making it mandatory.
- The MEMORY.md header comment (already added in the 2026-05-31 compression)
  states the rule for whoever edits the index.

## Exact hook diffs (for review — NOT yet applied)

Current SessionStart hook (`.claude/settings.json`):
```
bash -c 'echo "=== LAST 3 SESSION SUMMARIES ==="; ls -t docs/Sessions/*/*_session*.md 2>/dev/null | head -3 | while read f; do echo "--- $f ---"; head -25 "$f"; done'
```
Proposed addition (prepend, so current-truth loads BEFORE the narratives):
```
echo "=== CURRENT STATE ==="; head -45 docs/State/CURRENT_STATE.md 2>/dev/null; echo;
```

Current Stop hook reminds to write a session summary. Proposed addition to its
reminder text:
```
...also: rewrite docs/State/CURRENT_STATE.md (validated/refuted/in-flight/next-decision),
and add/update a docs/State/TASK_LEDGER.md row for any task that changed status.
```

## Open questions for the other dev
1. Is a 45-line auto-loaded CURRENT_STATE the right size, or tighter? (token cost
   per session vs context value.)
2. Should TASK_LEDGER be auto-generated from audit-doc frontmatter + run_registry
   rather than hand-maintained? (More robust, more upfront wiring.)
3. Is there appetite for a `scripts/doc_lint.py` that fails if MEMORY.md > cap or
   a CURRENT_STATE section is stale-dated > N days? (Enforcement vs trust.)

## What is already done vs needs approval
- DONE (in-lane memory maintenance, no system change): MEMORY.md compressed
  37.6→14.6 KB.
- NEEDS APPROVAL (system change): the two NEW State files, the hook edits, the
  CLAUDE.md reading-order + memory-section edits, the README nav rows.
