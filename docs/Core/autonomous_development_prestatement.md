# Autonomous Development — the pre-statement (Phase 6 of the Gap-Closure Program)

User-approved 2026-08-28 ("lets do it"). Written BEFORE any code, per house rule: the rules
that constrain a capability must exist before the capability does.

## The decomposition (what the human loop actually contains)
1. **Transport** — ferrying inbox/outbox text between sessions. Zero judgment, real cost
   (the 3-day dead-account detection lag was a transport failure). FULLY AUTOMATABLE.
2. **Judgment gates** — approvals (dependencies, Engine B / live_trader, deploys, trial
   spends, real money). CHEAP AND LOAD-BEARING. Kept, as an asynchronous approvals queue.
3. **Work generation** — deciding what to build. PARTIALLY AUTOMATABLE: census misses,
   drill findings, Brier triggers, papers verdicts, and scheduled discovery rounds already
   generate work; the missing piece is auto-DRAFTING dispatches from those triggers.

## The constitutional exclusions (never autonomously modifiable)
- **The referee**: the measurement stack — gates, census, resolvers, honest-N accounting,
  bootstrap/DSR machinery, the clock registry's semantics. The thing being measured must
  never control the measurement. Changes here always require director + user.
- **The gates themselves**: CLAUDE.md non-negotiables, this document, the approvals-queue
  mechanism, kill switches, the firewall family (bias/seed/injection/action).
- **The existing propose-first list is unchanged** for autonomous sessions: Engine B,
  live_trader, new dependencies, new external services, deploys to live AWS state,
  anything touching real-money paths. An autonomous session that needs one of these
  WRITES TO THE APPROVALS QUEUE AND STOPS.
- **T-305 stands**: no component tunes strategy parameters against its own P&L. Evidence:
  T-314 (in-sample gains collapsed OOS, twice) + prime-agent's Factorio self-refinement
  ("optimized cheating"). Evidence-paced prompt/context evolution (pre-registered triggers,
  next-cohort validation) remains the only sanctioned learning lane.

## The autonomy ladder (authority by record, like every other stream)
- **Rung 0 (pilot): the janitor** — a scheduled nightly headless session: run the suite +
  doc_lint + census review + worktree-canon checks; fix ONLY mechanical classes (drift in
  docs, stale pointers, broken imports from merges, test flake triage) on a branch; open a
  merge request to the director pass; NEVER merges itself. Plus **scheduled wake-ups**:
  a director pass that reads outboxes/merges/dispatches on cron, and worker sessions that
  wake on inbox changes — retiring the human ferry. (Pilot mechanics: local launchd +
  headless `claude -p` on this machine where the worktrees live — the T-136 archiver
  pattern; cloud routines are the scale-up path and require moving coordination files
  from gitignored-local to tracked-or-S3 first.)
- **Rung 1: trigger→draft** — census misses, drill findings, matured Brier readings, and
  papers verdicts auto-draft dispatches into inboxes (work the machine assigns itself);
  director pass routes them; gates unchanged.
- **Rung 2: class-approved merges** — change classes with a clean record (docs sync, test
  additions, dashboard-off-path fixes) merge without per-item director review, logged.
- **Rung 3+: negotiated later, on the record only.**
- **Promotion/demotion**: the autonomy itself is a scored stream — every autonomous action
  logged (autonomy_ledger.jsonl: session, trigger, diff summary, outcome); the metric is
  clean-merges vs reverts vs findings-missed; a revert DEMOTES the class that caused it
  (symmetric, no ratchet — the brain-book rule). Rung promotions are proposed with the
  record attached; director + user confirm.
- **The census watches the watchmen**: janitor/director-pass runs are registered clocks —
  a silent janitor alarms like any dead feed.

## Human surface after the pilot
The user reads the weekly digest, answers the approvals queue, and gets alarms. Relaying
ends. Every gate they hold today, they still hold — asynchronously.

## Sequencing
After T-327 (drill week) and not blocking Act 2: B builds the pilot (janitor + scheduled
passes) in parallel with E's Act 2. First artifacts per [NN-FIRST-ARTIFACT]: the janitor's
first nightly report + first accepted mechanical fix; the first full inbox→outbox→merge
cycle completed with zero human transport; the autonomy ledger's first row. The Sept-20
program checkpoint reviews the pilot's record alongside the structural stack.
