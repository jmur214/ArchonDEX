# T-327 Act 1 — THE FIRE-DRILL WEEK (the consolidated runbook)

**Status: RUNBOOK (drills not yet executed). This doc is Act-1 deliverable 1.**
Owner: E. Gate: Act 1 **BLOCKS Act 2** (the deploy-candidate record) by program
rule. Scope: account-2 (`offense-sso`, DISABLED — the drill sandbox) plus
deliberately-injected faults against the live acct-1/acct-3 *alarm* surfaces
where stated. **The free window closes forever once account-2's Act-2 record
starts** — that is why the week exists.

## The bar (uniform, non-negotiable)

Every drill is an **expected-alarm-fires assertion**, not a code review:
inject the fault → observe the alarm/refusal/degraded-flag ARTIFACT end-to-end
([NN-FIRST-ARTIFACT]) → restore → log the receipt in the ops-verification
record (`docs/Measurements/2026-08/drill_week_t327_record.md`, one row per
drill: injected-how, expected artifact, observed artifact, restored-how).
A drill whose alarm does NOT fire is a FINDING, not a failed drill — it found
a dead alarm, which is the point.

## Deploy dependency — rev30 is the drill-week rev

rev30 (built from merged main, standard discipline) carries, all merged or
merge-ready: the census-tail reorder + tail heartbeat re-sync + short-rounding
fix (T-329d3, `aef1d6e`); A's digest-as-Friday-pulse-step; C's registry fixes
(news_month_pushed flat-path, digest clock, similarity exempt-note). Deploy
rev30 BEFORE the census/liveness drills (they exercise the fixed ordering) and
verify its first scheduled firing before any drill that reads the census.

## The drills

Legend: [M] needs market hours · [U] needs the user · [30] needs rev30 first.

### A. Scheduler / submission integrity
1. **Scheduler-break → DLQ** — remove (then restore) the acct-2 jobdef ARN
   from the scheduler role's submit policy; fire the DISABLED schedule via a
   one-shot enable on acct-2. EXPECT: zero Batch jobs, +1 DLQ message, and
   `diff_live_paper_infra.py` reporting the coverage gap (the T-329d ignition
   miss, now a drill). Assert the drift gate catches it BEFORE the firing too.
2. **Missed-day catch-up (coalesced)** — leave acct-2's schedule dark a day,
   then run the catch-up path. EXPECT: exactly ONE catch-up run (the July
   recovery's rule, now written down: a catch-up fires once; it NEVER replays
   every missed invocation).
3. **New-alarm fresh-transition proof** (from T-329d2's finding) — for any
   alarm created during the week: prove it can TRANSITION (OK→ALARM or
   ALARM→OK) on a real datapoint, not merely sit in a state. An alarm born
   into ALARM before its first datapoint never re-alerts on the real miss.

### B. State / measurement integrity
4. **S3 push-fail → canonical=False** — deny (then restore) the job role's
   put on the acct-2 state prefix. EXPECT: `pushed-to-s3=False` → FATAL →
   non-zero exit → Batch FAILED → dead-man fires. Never a cheerful config echo.
5. **[30] Frozen-clock → census names it** — freeze a book's state date (C's
   method: hold a `days[].date` back). EXPECT: `clock_census.missed[].clock`
   names exactly that clock, same-day, in the S3 heartbeat (the tail re-sync
   is part of what's under test).
6. **[30] Append-failure → loud push** — deny the news_panel/ put. EXPECT:
   step 8 sets `s3_push_failed` degraded → heartbeat news block degrades →
   notify fires — and the block actually REACHES S3 same-day (the T-329d3
   blind-spot fix is part of what's under test).
7. **Stalled-feed → cadence alarm** — deliberately stall one archiver feed.
   EXPECT: B's T-335 cadence gate degrades loudly (exercise the merged gate,
   don't rebuild it). Route the `archive_feeds_in_budget` container-scoping
   question (13 feeds invisible in-cloud) to B in the same pass.

### C. Order-path safety (acct-2's path; wash guard wired for the drill)
8. **kill_switch flip → reconcile-only** — trip all three surfaces one at a
   time (S3 `TRADING_HALT` object; jobdef env; config flag) AND `llm.kill_switch`
   (the spend switch) on acct-3's path. EXPECT: BUYS and SELLS both refused
   with typed reasons, journaled REJECTED, run canonical, reconcile-only.
   NB the spend switch still trades one more day (constructor eats yesterday's
   note) — assert that documented latency, don't be surprised by it.
9. **WASH-GUARD refusal end-to-end** — wire `wash_guard=` on acct-2's path
   (acct-1 stays byte-neutral, its gate-d record pristine) and drive a real
   equivalence-class violation (SPY≈VOO≈IVV) inside the 61-day window.
   EXPECT: a REAL `WashSaleRefusal` — journaled REJECTED, typed reason, order
   never reaches the broker. D's bar: a real refusal observed, not a unit test.
10. **Forced broker rejection** — submit a deliberately-rejectable order
    (e.g. malformed qty via a test-only path). EXPECT: terminal REJECTED with
    broker reason adopted, run continues, no blind re-POST.
11. **[M] ONE marketable-LIMIT order** — the first non-market order in program
    history, on acct-2. EXPECT: clean fill + exec-ledger row. Also settles the
    empirical check: are FRACTIONAL orders market-only? (Try one fractional
    limit; record the broker's answer.)

### D. Corporate actions / calendar
12. **Forced-split reconcile** — `corporate_action_tickers` is NEVER populated
    in prod (verified: `reconciliation.py:207` reads an input no caller feeds)
    — the next index-ETF split HALTS the laboratory on position_drift. Wire the
    feed, then inject a synthetic 2:1 split. EXPECT: reconcile explains the
    ratio via the CA feed instead of halting; without the wire, assert it DOES
    halt (both sides of the gate observed).
13. **Synthetic dividend / cash-drift injection** — through reconcile. EXPECT:
    recognized, explained, ledger row. Settles the empirical check: does
    Alpaca PAPER credit dividends at all (check account activities on a held
    ex-div name)? If not, the synthetic path is the ONLY coverage — which is
    why it must fire in a drill at least once.
14. **2027 calendar** — `market_calendar.py` falls back to a 2026-ONLY holiday
    set (`_FALLBACK_HOLIDAYS_2026`); in Jan 2027 the fallback would silently
    trade holidays. Fix: add 2027 + FAIL-LOUD on fallback-year mismatch.
    EXPECT (drill): simulate a 2027 date offline → loud failure, not a trade.

### E. Notification / secrets
15. **[U] PAPER_NOTIFY_WEBHOOK** — set nowhere today, so every `_notify()` is
    a cloud no-op (`heartbeat.py:323` reads the env; no jobdef sets it). Wire
    it + a DLQ alarm; then the **SMS second channel**: coordinate with the
    user's `archondex-paper-alerts` SMS subscription — EXPECT a real message
    to land on a drill-fired alarm (the unread-email lesson's fix, proven).
16. **Secrets-missing clean-skip** — remove (then restore) the ANTHROPIC
    binding on acct-2's jobdef only. EXPECT: the pulse clean-skips with an
    honest "no adapter" record — never a fabricated note, never a crash.
17. **Exec-IAM shared-role-overwrite** (flagged-open since July) — the fleet
    shares one exec role; a blind PUT from any provisioner rewrites everyone's
    grants. The union+readback pattern now guards both known policies; the
    drill: deliberately render a would-revoke document and assert the
    provisioner REFUSES (the `assert not dropped` path fires).

## Sequencing sketch

Day 0 (any evening): rev30 deploy + verify its scheduled firing next morning.
Days 1-2: B-group (state/measurement) + A-group — no market dependency except
observing next-day firings. Days 3-4: C-group [M] + D-group. Day 5: E-group
[U] + the record write-up + the ops-verification report to the director.
Order within a day is flexible; NEVER run two fault injections that share an
alarm surface concurrently (an alarm proven by drill A must not be mid-drill
from B — one fault in flight per surface).

## Out of scope (explicitly)

Act 2 (the deploy-candidate constructor + ARRIVAL EVENT + Rule-B contribution
record) — blocked on this week. The bounded-repair unit and further input
evolutions — queued post-drill-week. The agentic-arm actions channel (still
NEVER_ALIVE — its prompt never got the v3-style opening) — A's lane, flagged.
