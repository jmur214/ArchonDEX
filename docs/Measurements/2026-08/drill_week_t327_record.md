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

---

## Drill 6 — OBSERVED + RESTORED — 2026-09-02

| step | detail |
|---|---|
| observed (~13:25 CDT) | **PASS**: both 9:45/9:55 runs canonical/clean; local append fine; `pushed=False`; the news block carries `s3_push_failed: news panel did NOT persist to S3 (the forward tape cannot accrue)` — **IN the same-day S3 heartbeat on BOTH accounts** (the T-329d3 tail re-sync proven under deliberate fault; pre-fix this flag died with the container every day) |
| restored | grant re-added (readback); job-role re-put in template order (the gate's list comparison is ORDER-SENSITIVE — a false-positive class noted for a later gate improvement); drift gate **"No drift"** |
| tape repair | the one-day hole backfilled via the resumable builder: `news_202609.parquet` rebuilt (490 rows; **240 for the lost day 09-02**) and pushed to the durable S3 partition — the backfill machinery exercised as part of the restore, per the drill's stated cost |

**Drill 6 verdict: PASS.**

### ⚠ Drill-6 COLLATERAL — the scan filed on a zero-document bundle (director dispatch)

The injected fault starved the weekly scan's bundle; provenance:
`{n_documents: 0, bundle_bytes: 822, reason: 'filed'}` — `n_docs` existed only
in the post-hoc reason classification, never as a CALL GATE, so the model was
called on 822 bytes of non-news context and recited its power-buildout priors
(near-duplicate of the open m-2026-08-19 basket, conv 0.62). **The desk fails
UNSAFE on input starvation — found by an injected fault instead of a real
outage: the drill week doing exactly its job.**

| action | detail |
|---|---|
| quarantine (same day, before first book intake) | `m-2026-09-02-picks_and_shovels` EXPIRED-with-reason via the existing skip path: appended a superseding quarantine row to the append-only ledger + `expired=[tid]` + a reasoned day-row + `quarantine_notes` in the book state (both in S3). **Mechanically verified**: `_due_theses('2026-09-03')` returns `[]` against the modified state — the book cannot open it |
| the guard (rev31) | `MIN_SCAN_DOCUMENTS` evidence floor in `run_blind_scan` — refuses to CALL below the floor (clean-skip: no spend, no record_scan, scan stays due and retries when the tape returns). 2 tests incl. the ordering lock (floor before governor). Deeper spec (higher floor + duplicate detection) → D |

---

## 🔴 INCIDENT — account-3's first FAILED run (2026-09-03) — the drill week's best find, unplanned

**Not a drill. The AI's own decision produced it**, and the machinery the drill
week has been proving is what caught it.

The 09-02 note took the account to zero (`{AGG: 0.0, GLD: 0.0, SPY: 0.05}` →
sell 5 AGG, 1 GLD, 1 SPY). The fills executed at the broker; **the ledger never
learned.** Reconcile caught it on the first post-submit cycle:

```
reconcile_1  cash_drift      halt  ledger cash 98,377.56 vs broker 100,041.66 (gap 1,664.10)
             position_drift  halt  AGG ledger 5 vs broker 0
             position_drift  halt  GLD ledger 1 vs broker 0
             position_drift  halt  SPY ledger 1 vs broker 0
→ NON-CANONICAL "reconcile 1/3; halted" → exit 70 → Batch FAILED → alarm
```

The gap is exactly the three sales' proceeds. **The system failed SAFE and LOUD
— it refused to certify a day whose record it could not vouch for.**

**Root cause** (`held_reconcile.py:82`, `if explained and bpos:`): the ledger has
**no fill-application path** — `LedgerStore.apply_fill` has ZERO production
callers. It is not an independent record; it is a MIRROR kept in sync by
re-adopting broker truth. That adoption was gated on *"are there broker positions
NOW"*, so it skipped the one case that needs it most: an account our own fills
took FLAT. Six prior trading days looked clean only because each ended non-empty
— **the agreement was tautological, not evidence.**

**The wedge (why it mattered):** with the broker flat, every later run would skip
adoption too, so preflight would halt and BLOCK submission **every day, forever**.
It could not self-heal.

**The fix** (merge-ready, NOT aboard rev31): the condition the docstring actually
describes is an explained position **CHANGE**, not a non-empty position **SET** —
and going flat is a position change. Adopt when the broker holds explained
positions **or** the ledger still holds positions the strictly-equal journal says
are gone. A flat ledger with a *standalone* cash gap still adopts nothing and is
left to CASH_DRIFT — the mystery the guard exists to protect, locked by its own
test. Lock proven by reversion; pre-existing reconciliation suite green.

**Self-heal verified against the real artifacts, not predicted:** the live journal
nets to `{}`, which equals the flat broker, so `explained` is True and the ledger
is stale ⇒ the next run's start-of-run adoption converges it **through the
machine's own documented path**. No hand-editing of a forward record.

**Flagged, not fixed here:** that the ledger never applies fills at all is a
design question — it means the ledger cannot independently detect a broker-side
error, which is the thing a ledger is *for*. Scope for the director.

---

## rev31 DEPLOYED — 2026-09-03 evening

Image `paper-sha-55ef859` **from merged main** (the branch-build rule held: the
incident fix is on my branch only and is therefore deliberately NOT aboard —
stated, not hidden). In-container verified: fleet kill switch (opt-in set
retired) · digest Friday step · advisor step · census at tail · tail re-sync ·
`daily_agentic_v2` (SHA `c1a3ac1e52add266…` matching repo) · `daily_v4` ·
evidence floor **after** the firewall · floor self-explaining · artifact_paths ·
short-truncation fix · PIT parquet.

Fleet: acct-1 `:31` ENABLED · offense-sso `:13` DISABLED with **alarms SUPPRESSED
(dormant)** — the 08-28 ruling rendering correctly on its first provisioner
exercise · ai-trader `:4` ENABLED (live state preserved). IAM 0 added / 0 revoked.
**Drift gate: no drift.**

**Agentic open date stamped at deploy: 2026-09-04** ⇒ common-window start for the
paired book comparison (per A's binding condition).

### Friday 2026-09-04 — the pre-stated reads
1. **DIGEST** line fires for the first time (Friday cadence).
2. **ADVISOR** renders its second memo (artifact reads 08-27 → new month).
3. **rev31 verify** on the scheduled principal.
4. **Agentic v2's first note** — the channel opens; T-342 liveness should flip
   `hypothetical_actions/llm_shadow_book(agentic)` off NEVER_ALIVE in the days after.
5. **⚠ acct-3 will FAIL AGAIN** (wedged; fix not aboard) — *expected and explained*,
   not a new finding. It unwedges on the rev that carries the incident fix.
