# T-327 Act 1 — drill-week ops-verification record

**One row per drill: injected-how / expected artifact / observed artifact /
restored-how.** Bar: [NN-FIRST-ARTIFACT] per drill. A silent alarm is a
finding; so is a drill that won't restore cleanly.

## Day 0 — 2026-08-28 (rev30 first scheduled firing, verified)

Pre-stated expectations vs observed:

| expectation | observed |
|---|---|
| census's 5 ordering false-wolves gone | **4 of 5 cleared** (`news_month_pushed`, `stage2_clock_ticked`, `llm_shadow_book_rolled`, `exec_ledger_on_fill_days`). The 5th (`analyst_note_written`) was never an ordering miss: the clock globbed `startswith(<date>)` but notes are `note_<date>.json` — **matched nothing ever written** (T-346 filename class). Fixed + regression-locked same day. |
| census/news tail blocks in S3 same-day | **CONFIRMED** — `news` + `altdata` blocks present in the day's S3 heartbeat for the first time (the T-329d3 tail re-sync live). |
| acct-3 short adjusts −6 → −5 | **CONFIRMED** — BUY 1 AGG @ 97.83 on the scheduled principal; the truncation fix's live confirm. |
| no DIGEST line (step unmerged at build) | **CONFIRMED absent, as pre-stated.** C's new `digest_written_weekly` clock (aboard rev30 under that name) correctly MISSes it — the clock watching a caller that isn't deployed yet is the system working. |

**Real event surfaced by the fixed clock's investigation**: 2026-08-27's
constrained note was VOIDED — the model wrapped its JSON in a ```json fence
(explicitly forbidden by the prompt); the fail-loud gate produced NO note;
the constructor fell back to the 08-26 note inside the staleness bound.
Correct behavior end-to-end, but operationally invisible until today.
**Banked as evidence for the queued bounded-repair unit.**

**Standing findings logged Day 0:**
1. `HALT_GATED_STRATEGIES = {"llm_analyst"}` — the trading kill switch is
   consulted ONLY by account-3's strategy. Accounts 1/2 have no kill-switch
   surface at all. Scopes drill 8; design question for Act 2's constructor.
2. `archondex-paper-offense-sso-silent-stop` has been in **ALARM since
   2026-07-12** — the born-in-ALARM trap on a deliberately-dark account: six
   weeks of standing noise nobody can re-alert through. Feeds drill 3.
3. acct-3 heartbeat `fills: 3` vs `submitted: 1` today — the fills counter
   appears to include reconcile-adopted prior-day fills; exec ledger shows
   exactly 1 real fill today. Minor; watch.

---

## Drill 1 — scheduler-break → DLQ (group A) — 2026-08-28

| step | detail |
|---|---|
| injected | removed `archondex-paper-offense-sso:*` from the scheduler role's `submit-paper-job` policy (union-edit, readback-verified absent) |
| assertion A | `diff_live_paper_infra.py` → **DRIFT: 1 finding, exit 1**, naming `archondex-paper-offense-sso-daily`'s uncovered target — the mechanical gate catches the T-329d class BEFORE any firing ✅ |
| assertion B | one-shot self-deleting schedule (`at(+3min)`, retry 1/120s, same role, revision-pinned :12 target) → expected: zero Batch jobs, DLQ 2→3 |
| observed | **PASSED both halves**: zero Batch jobs named `drill-t327-scheduler-break` (the submit never reached Batch — exactly the invisible-outside-the-DLQ shape); DLQ `ApproximateNumberOfMessages` 2→**3** within ~4 min of the firing |
| restored | grant re-added (union, readback verified, 5 resources); drift gate **"No drift"** exit 0; the one-shot schedule confirmed self-deleted (`ResourceNotFoundException`). One fault in flight throughout. |

**Drill 1 verdict: PASS.** The T-329d failure class now has a proven detection
pair: the drift gate catches it BEFORE a firing; the DLQ catches it AFTER.

---

## Drill 3 — new-alarm fresh-transition proof (group A) — 2026-08-28

Target: `archondex-paper-offense-sso-silent-stop`, in standing ALARM since
2026-07-12 (the born-in-ALARM trap — six weeks of noise no re-alert can
penetrate). Method: a metric-only Batch job on the acct-2 jobdef (command
override → `emit_metrics(happened=True, canonical=True)` via the container's
job role, dimension from the jobdef's own env). Expected: ALARM→**OK** fresh
transition (+ SNS notify on ok-actions); then the next missing 24h window
flips it back ALARM — both directions proven by one datapoint.

| step | detail |
|---|---|
| injected | Batch job `drill-t327-alarm-transition` on the acct-2 jobdef, command override → `emit_metrics(happened=True, canonical=True)`; log line `DRILL3 METRIC EMITTED account=offense-sso` |
| observed | `archondex-paper-offense-sso-silent-stop`: **ALARM → OK** within ~2 min of the datapoint — the alarm's FIRST state change since 2026-07-12, proving it can transition and firing the ok-actions SNS notify |
| pending | the reverse transition (OK → ALARM when the next 24h window has no datapoint) completes over the weekend — verify Monday; that flip is the ALARM-direction proof AND returns the alarm to its (noisy-by-design) dormant-account state |
| restored | nothing to restore — the injected artifact was one legitimate datapoint; the account remains DISABLED/dark |

**Drill 3 verdict: PASS (first half); second half self-completes — verify Monday.**
**Finding attached**: a dormant account's dead-man alarm sits in standing ALARM
for weeks (offense-sso since 07-12) — noise that blunts the channel. Proposal
for the director: dormant-account alarms should be disabled-with-reason (or
actions-suppressed) until the account arms, then proven by exactly this drill.

---

## Rulings applied — 2026-08-28 evening (both built + live same night)

**Ruling 1 — dormant alarms suppressed-with-reason (LIVE).** offense-sso ×2 +
btc-sleeve ×2 re-put with `--no-actions-enabled` and the reason stamped in the
description; provisioner renders the same from the FLEET `dormant` key (so a
re-run preserves it — template==live); the drift gate gained
`check_alarm_suppression` (a reasonless disabled alarm = drift) and reads
green: 4 armed / 4 suppressed-with-reason. Arming protocol documented in the
execution manual (remove `dormant` → re-provision → prove ALARM→OK→ALARM,
the drill-3 pattern).

**Drill-3 second-half adjustment (honest note):** with offense-sso's actions
now suppressed by the ruling, the weekend OK→ALARM flip is a STATE-TRANSITION
receipt only (evaluation continues; notify correctly silent — that silence is
now the ruling working, not a dead channel). The notify path was already
proven on the ALARM→OK leg while actions were enabled.

**Ruling 2 — kill switch = fleet property (BUILT, rides next rev).**
`om_halt` is unconditional in the runner: every strategy's OrderManager now
consults `check_trading_halt` pre-submission (halt-new NEVER liquidate,
unchanged; no-halt path behaviorally identical for accounts 1/2). Deploys
with the next rev — drill 8 then exercises it fleet-wide, per-surface.

---

## Drill 3 — CLOSED (second half receipt) — 2026-09-01

`archondex-paper-offense-sso-silent-stop`: **OK → ALARM at 2026-08-31 13:58 CDT**
(StateUpdatedTimestamp), `ActionsEnabled: false` — the full ALARM→OK→ALARM
cycle is proven, and the reverse leg's notify was CORRECTLY silent under the
suppression ruling (pre-stated 08-28). **Drill 3 verdict: PASS, closed.**
This exact cycle is now the mandatory arming protocol for any account going live.

---

## Drill 5 — frozen-clock → census names it (group B) — 2026-09-01

| step | detail |
|---|---|
| mechanics (local A/B against REAL state) | copied the live `llm_shadow_book.json` into a scratch root; census `as_of=2026-09-01` → `llm_shadow_book_rolled` **ADVANCED**; froze `points[-1].date` to 08-31 → **MISS: "last=2026-08-31 != as_of=2026-09-01 (did not roll)"** — the census names exactly the frozen clock with the stale date |
| live receipt | the in-cloud census names non-advancing artifacts daily in production (`digest_written_weekly` naming its absent artifact since 08-28) — the naming chain is proven on the scheduled principal, not only locally |
| notify leg | CONSOLIDATED INTO DRILL 15: `PAPER_NOTIFY_WEBHOOK` is set nowhere, so every census miss is heartbeat-visible but push-silent today — the drill-15 wiring is what closes the last link |
| restored | nothing live was touched (scratch-root exercise) |

**Drill 5 verdict: PASS (naming mechanics + live receipt); notify leg deferred to drill 15 by design.**

---

## Drill 6 — append-failure → loud push (group B) — INJECTED 2026-09-01, ACTIVE overnight

| step | detail |
|---|---|
| injected | `news_panel/*` PUT revoked from the job role's `PaperStateRW` (readback verified). ⚠ FAULT ACTIVE until the 2026-09-02 ~10:05 observation |
| assertion A (pre-observation) | drift gate → **DRIFT: job-role/PaperStateRW** — the gate flags the revocation before any run ✅ |
| expected tomorrow | both 9:45/9:55 runs: local append succeeds, `push_news_month` AccessDenied → `pushed=False` → `s3_push_failed` degraded reason in the news block — AND that block reaches the SAME-DAY S3 heartbeat (the T-329d3 tail re-sync under deliberate fault). Runs stay canonical (news is report-only). |
| restore plan | re-grant (readback) + drift gate green + **backfill the one-day tape hole** via the resumable Alpaca builder + verify row counts — the deliberate data cost of this drill, and its repair exercises the backfill machinery |

**Sequencing note:** rev31 (fleet kill switch + digest step + T-348 + A's
agentic_v2 when drafted) deliberately NOT built tonight — one fault in flight;
tomorrow's observation stays on the known rev30 baseline. rev31 = tomorrow
evening, post-restore.
