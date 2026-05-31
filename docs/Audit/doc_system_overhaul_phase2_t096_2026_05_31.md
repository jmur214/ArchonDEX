# Doc-system overhaul — Phase 2 (T-096): hooks + CLAUDE.md restructure + NON_NEGOTIABLES split

**Date:** 2026-05-31
**Owner:** Director (implemented in main thread; design+verify via background workflow)
**Branch:** `feature/doc-system-overhaul-phase2`
**Status:** SHIPPED (branch; awaiting user review → merge)
**Depends on:** Phase 1 (T-093, merged 6410259) — CURRENT_STATE.md + TASK_LEDGER.md must exist first.

## What & why

Phase 2 makes the Phase-1 current-truth files *self-enforcing* and splits the
non-negotiables into an expanded canonical home — the documentation-erosion
remedy. Per CLAUDE.md "changes to the documentation system itself" is a
propose-first area, so this was designed + adversarially verified BEFORE touching
the always-firing hooks, then applied by hand. The outside dev's refinements
were used as the spec; the director implemented.

### Design + verify protocol (why a workflow ran first)

A background Workflow (8 agents, ~390K tok) did: (Understand) read the live
settings.json + CLAUDE.md + Phase-2 backlog and **verified the actual Claude Code
hook/@import semantics from official docs** rather than guessing; (Design)
produced apply-ready artifacts; (Verify) 3 adversarial reviewers tried to prove
the design bricks session-end or drops a safety rule. Verdict: `apply_ready:
false`, 2 NEEDS_FIX — all fixes folded in below. **The workflow earned its keep:**
it surfaced two traps a naive edit would have hit.

## The two traps the verification caught

1. **Stop-hook brick risk.** Verified Claude Code semantics: a Stop hook
   returning `decision:"block"` (or exiting 2) BLOCKS session end and **returns
   control to Claude, NOT the user — there is no user force-end of a blocked
   stop.** A dense inline `bash -c '...'` one-liner with a future typo → bash
   exit 2 → bricks every session-end, and the trailing `exit 0` never runs
   (bash aborts at parse time). **Fix:** externalized both hooks to
   version-controlled, `bash -n`-checkable scripts; Stop logic runs in a
   swallowed subshell (`( ... ) || true`) with a final standalone `exit 0`; the
   settings.json wrapper ALSO appends `; exit 0` as a second backstop. The hook
   is ADVISORY (stderr WARN), never `decision:block`.
2. **@import is NOT a safe relocation mechanism.** Verified: `@path` imports ARE
   auto-loaded at launch, BUT the official docs explicitly name the
   separate-NON_NEGOTIABLES case as the wrong tool. So the split uses
   **duplicate-pointer**, NOT move+import: all 15 hard rules stay VERBATIM in
   CLAUDE.md (the only guaranteed-always-loaded file); NON_NEGOTIABLES.md is the
   expanded copy. Zero always-loaded coverage lost — verified by grepping each
   rule still appears in CLAUDE.md.

A third verifier mis-reported settings.json as a "9-byte stub" with
settings.local.json being live; **director ground-truth check refuted this** —
settings.json is the live 1856-byte file with all 3 hooks; settings.local.json
holds only a PreToolUse deletion-guard + 159 allow entries (untouched).

## Shipped

| Item | File | Note |
|---|---|---|
| SessionStart hook → external script | `.claude/hooks/sessionstart_context.sh` (NEW) | Prepends CURRENT_STATE.md to the prelude; preserves LAST-3-SESSION-SUMMARIES + git + health-check. |
| Stop hook → external script | `.claude/hooks/stop_freshness.sh` (NEW) | Advisory stale-CURRENT_STATE WARN (7-day threshold); fail-open by construction; preserves session-summary reminder. |
| settings.json rewire | `.claude/settings.json` (MOD) | Both hooks now call the external scripts via `bash -c '... ; exit 0'`. PostToolUse sync_docs hook untouched. Valid JSON confirmed. |
| Non-negotiables expanded copy | `docs/Core/NON_NEGOTIABLES.md` (NEW) | All 16 hard rules with full rationale + named regression tests + audit cross-refs; stable title cross-refs (no positional `rule #N`). |
| CLAUDE.md reading order | `CLAUDE.md` (MOD) | CURRENT_STATE.md added as #2 current-truth file. |
| CLAUDE.md supersession rule | `CLAUDE.md` (MOD) | SUPERSEDED tag / TASK_LEDGER status-flip → no longer current truth. |
| CLAUDE.md forward_plan-vs-CURRENT_STATE | `CLAUDE.md` (MOD) | Which file to edit when. |
| CLAUDE.md NON_NEGOTIABLES pointer | `CLAUDE.md` (MOD) | Callout at top of non-negotiables block; rules kept in place (duplicate-pointer). |

## Verification performed (all green)

- settings.json parses as valid JSON after edit; SessionStart/Stop rewired; PostToolUse preserved.
- Both hook scripts pass `bash -n`.
- SessionStart emits CURRENT STATE + all 4 original sections.
- Stop: fresh stamp → no WARN, exit 0; stale → WARN, exit 0; missing file → fail-open, exit 0; garbled stamp → fail-open, exit 0.
- Brick-resistance: injected `$(( 5 / 0 ))` → exit 0; syntax-broken script under the `; exit 0` wrapper → exit 0.
- All 15 CLAUDE.md hard rules still present verbatim (grep count = 1 each).
- NON_NEGOTIABLES.md: 16 headings, 0 positional cross-refs.
- doc_lint: exit 0 (WARN-only); MEMORY 90.2% of cap, all 78 entries dated.
- **Self-test caveat:** an early functional test corrupted the live CURRENT_STATE.md (tested against the real file); restored from git. LESSON: never functional-test a hook against the live file it reads — use a temp copy.

## Deferred to follow-ups (not in this phase)

- Quarterly archive-sweep policy (dev item G) — recurring policy, own dispatch.
- Plan-mode artifact ownership rule (dev item I) — doc-system process change, own dispatch.
- doc_lint WARN→FAIL promotions (item E bidirectional MEMORY↔audit; check 5 dated [now passes]; check 7 execution_manual 110-script gap) — batch after corpus cleanup.
- **Optional drift-guard:** a doc_lint check asserting each CLAUDE.md non-negotiable heading appears in NON_NEGOTIABLES.md (mitigates duplicate-pointer drift). Recommended next.

## End-to-end hook test (dev item B) — director to run live

The script-level tests above cover the logic. The one remaining check that needs
a real session: start a fresh Claude Code session in-repo and confirm the
session prelude contains the CURRENT_STATE dashboard (proves SessionStart
injection works end-to-end, not just the script in isolation). Stop-hook live
behavior with a stale stamp: confirm the session still ends (WARN appears, no
block) — proving the advisory-not-block choice avoids the brick.
