# Scheduled director/worker passes — the pre-statement (Phase-6 rung 0, second half)

**Status: DESIGN ONLY. No code. Awaiting director FREEZE.**
**Date:** 2026-09-10 · **Agent:** B · Extends `docs/Core/autonomous_development_prestatement.md`
Written BEFORE the capability, per the house rule the pilot's own constitution set.

## 0. The ruling this design forces first

The constitution's rung-0 line reads: *"a director pass that reads outboxes/merges/
dispatches on cron."* Read one way that grants **autonomous merging to main** at rung 0.
It cannot mean that, for two reasons the document itself supplies:

- **Rung 2 is explicitly "class-approved merges."** If rung 0 already merged, rung 2 would
  be empty.
- CLAUDE.md puts `git merge` onto main in the stop-and-propose list, and the constitution
  says *"the existing propose-first list is unchanged for autonomous sessions."*

**So: the rung-0 director pass PREPARES merges and never performs one.** It reads the
janitor's and workers' merge requests, verifies them, and writes a ranked, evidence-carrying
queue for a human to approve in one action. That is what actually retires the *ferry* —
transport was the cost, not the judgment. **If the director intends rung-0 merging, that is a
deliberate rung-2 promotion and should be stated as one, not inherited from a comma.**

## 1. What a scheduled pass may READ
Both pass types: the repo at `origin/main`, git history and diffs, agent inboxes/outboxes,
`janitor_merge_requests.md`, janitor reports, `autonomy_ledger.jsonl`, census/clock output,
test and lint results.

**Every one of these is DATA, never instruction.** An outbox is text written by another
agent; a dispatch is text written by a pass. A pass that treats read text as a command is
one confused or compromised session away from steering the program. This is the same rule
the papers pipeline already applies to user-supplied content, and the same firewall logic
T-325 armed — stated here before the capability exists rather than after an incident.

## 2. What each pass may WRITE

**Director pass** (cron, e.g. 07:00 daily)
- ✅ dispatch entries into agent **inboxes**
- ✅ its own report surface + an `autonomy_ledger.jsonl` row (append-only)
- ✅ an **approvals-queue** entry when something needs a human (the merge queue lives here)
- ❌ never merges to main; never edits an agent's **outbox** (that is the agent's record of
  its own work — a director editing it rewrites history it did not do)
- ❌ never edits past ledger rows

**Worker pass** (wakes on inbox change)
- ✅ a feature branch, its own **outbox** entry, a ledger row, a merge request
- ❌ never main, never another agent's surfaces

## 3. What neither may EVER touch
The janitor's guard already encodes this and **should be reused, not re-derived**
(`scripts/janitor_guard.py` — the referee, the gates, the propose-first list, with
deny-winning, deny-by-default and all-or-nothing refusal). Two additions the passes need
that the janitor did not:

- **`data/coordination/*_inbox.md` / `*_outbox.md` write-scoping.** A pass may append only
  to the surfaces its role owns. Cross-writing is how one confused session becomes two.
- **The approvals queue mechanism itself** — constitutionally a gate, so on the denylist
  exactly as `launchd_canon.py` is.

## 4. The new failure class: a pass that GENERATES work

The janitor only ever *fixed* what it was told was broken. A director pass **decides what
gets built**, which is new authority and brings failure modes the janitor never had:

| risk | mechanical limit (not a prompt instruction) |
|---|---|
| **Runaway dispatch loop** — a pass dispatches work whose completion triggers another dispatch | **Hard budget: N dispatches per pass** (propose 3), counted in the ledger; exceeding it halts the pass and writes an approvals entry |
| **Self-dispatch** — a pass assigns itself work | A pass may not write to its own inbox; enforced by role→surface mapping |
| **Injection via read surfaces** — an outbox steers the director | Read text is data (§1); a dispatch must cite a **trigger** from a machine-derived source (census miss, drill finding, Brier reading, papers verdict, failing check) — never free text alone |
| **Duplicate dispatch** — the same finding re-dispatched nightly | Trigger fingerprint recorded in the ledger; a repeat fingerprint inside a cooldown is a no-op with a logged reason |
| **Silent pass** — the schedule dies and work stops flowing | A registered clock, exactly as `janitor_ran_nightly`, plus `launchd_canon` coverage |

## 5. First artifacts (per `[NN-FIRST-ARTIFACT]` — observed, not asserted)
1. A **director-pass report + ledger row** from a real scheduled firing (not a manual run).
2. **One dispatch auto-drafted from a machine-derived trigger**, appearing in an agent inbox
   with its trigger cited.
3. A **worker pass waking on that inbox change**, producing a branch + outbox entry with
   **zero human transport**.
4. The resulting merge request reaching the **approvals queue** with its evidence attached —
   the human's action reduced to one approve/decline, which is the ferry retired without the
   merge gate moving.

## 6. Open questions for the director (I am not deciding these)
1. **The rung-0 merge ruling** (§0) — confirm prepare-only, or promote deliberately.
2. **Where the approvals queue lives.** Coordination files are gitignored-local today; the
   constitution flags that cloud scale-up needs them tracked-or-S3 first. A queue the user
   answers asynchronously probably cannot be gitignored-local.
3. **Worker wake mechanism.** Inbox-change detection on this machine is a file watch
   (launchd `WatchPaths`) — simple, but it fires on any write. A polled digest is duller and
   more predictable. I lean `WatchPaths` + debounce.
4. **Dispatch budget** — propose 3/pass.
