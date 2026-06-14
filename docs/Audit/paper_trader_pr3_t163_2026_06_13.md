---
task_id: T-2026-06-13-163
title: Paper-loop PR-3 — close the 5 review criteria, wire production order-construction, ARM the paper submit
date: 2026-06-13
substrate: n/a (paper_trader/ package + read-only engine imports; no live-money path; PAPER endpoint only)
scope: paper_trader/ + its tests + one driver script. NO edits to live_trader/, Engine B logic, or backtest configs. Engine imports are READ-ONLY (no engine-logic change). dyn-opt ON is in the PAPER config only.
outcome: **Delivered — the loop is armed and proven on the live PAPER account.** Part A closed all 5 T-160-review entry criteria, each with a test (+ the two durability tests the review flagged missing: torn-journal replay + zero-broker-POST-across-restart). Part B wired the production A→C→B order-construction read-only with the allocator made EXPLICIT and logged (T-158), and the T-152/T-141/T-151 shadow layer + the paper-only telemetry (auction-slippage-vs-T146, reject map, divergence null). Part C armed the submit and ran ONE end-to-end armed day on the live paper account: staged → submit_opg ARMED (real POST, broker `accepted`, broker_id set) → ack sweep → 3/3 reconcile cycles clean vs real broker truth → eod-expire (an unfilled OPG on a non-trading Saturday is correctly canceled at the broker; account left FLAT). 72 paper tests green. **Go-live (the 60-day clock) is NOT started — gated on the director's allocator-identity decision (T-158) + the book/fork decision; kill ACTIONS stay SHADOW.**
---

# T-163 — Paper loop PR-3 (arm the submit)

## Part A — the 5 review entry criteria, closed + tested

| # | Defect (T-160 review) | Fix | Test |
|---|---|---|---|
| 1 | submit POSTs then journals → crash window leaves STAGED for an accepted order → restart blind-resubmits | `submit()` journals the SUBMITTED **intent fsync'd BEFORE the POST**; replay then routes through reconcile-vs-broker | `TestCrit1` (raises on POST, asserts the intent already on disk) |
| 2 | `_replay_from_journal` trusts the journal alone | `reconcile_with_broker()` on `__init__`: every replayed non-terminal order gets a broker GET — adopt if live, revert SUBMITTED→STAGED if the broker never saw it; a duplicate-coid reject = "already live, adopt" NOT REJECTED | `TestCrit2` ×3 (adopt-if-live, revert-if-absent, dup-coid-adopt) |
| 3 | SUBMITTED-but-never-acked invisible to reconciliation + uncancellable | `expire_unfilled()` (window EXPIRE); missed_fill now covers SUBMITTED; `cancel()` falls back to a client_order_id lookup | `TestCrit3` ×3 |
| 4 | computed halt was cosmetic | a cash/position-drift halt now **BLOCKS the submit step** | `TestCrit4` (preflight halt → submit BLOCKED, submitted_count 0) |
| 5 | split/qty-morph on a held name misclassified as position_drift (halt) | clean small-integer qty ratio on a held name → corporate_action (manual); + an explicit corporate-action feed; sign-flip stays position_drift | `TestCrit5` ×4 |

**The two durability tests the review flagged as missing:**
- `test_torn_journal_final_line_is_ignored_on_replay` — a crash mid-append leaves a torn final JSON line; replay skips it and recovers everything before it.
- `test_zero_broker_post_across_restart` — submit, restart with a new client+manager, retry submit → **ZERO new POSTs**; total POSTs across both processes = exactly one. The core durability primitive, now proven.

18 new criterion tests; 35 prior PR-1/PR-2 tests updated for the changed lifecycle (intent-before-post renamed the journal event; the A5 ratio detector reclassified a 2:1 fixture; the live-mode guard is now the arm gate). All green.

## Part B — production order-construction (read-only) + shadow + telemetry

`PaperOrderConstructor` mirrors `BacktestController._prepare_orders`
exactly: Engine A `generate_signals` → `{ticker: signed-score}` (strength
× side; `none` dropped) → `compute_target_allocations` (dyn-opt ON — the
whole-share integer book auction orders require) → `prepare_order(
target_weights=…)` per signal → `OrderSpec` (side long/cover→buy,
short/exit→sell; TIF entries→OPG, exits→CLS under moo_moc). **Engines are
INJECTED** — the adapter only CALLS them (read-only contract literal),
unit-tested against fakes proving the A→C→B sequence.

**Allocator visibility (T-158):** `PaperConfig.allocator` is an explicit,
validated field (`adaptive | mean_variance | parrondo_fixed`), surfaced
in `log_dict()` and logged EVERY cycle (the live driver prints it). The
allocator-IDENTITY decision stays director-held (go-live gate) — this
config makes it visible and configurable, not decided.

**Shadow kill layer + telemetry** (all read-only over shipped engines):
- `DivergenceShadow` — T-152 CUSUM/PH monitors at the calibrated
  operating points (k=1/h=5 mean, k=2/h=12 var, δ=0.05/λ=20 PH),
  consuming `(realized − backtest-expected)/σ`. **SHADOW: logs alarms,
  takes NO action** (arming reduce/flatten is a later step).
- `PromotionReport` — captures the 2026-06-13 paper-only agenda from day
  one: realized **auction slippage vs the T-146 model** (signed adverse;
  the number that re-opens T-157 LPS), the **rejection-rate map**, the
  **divergence null distribution** (paper − backtest-expected), + §5
  promotion-criteria status (operational; alpha is NOT paper-learnable).
- `RouterShadow` — T-141 `CrossAccountWashSaleChecker` in shadow.
- `SafefWeeklyJob` — T-151 safe-f/CAR25 scaffold (fires past 126 obs).

19 Part-B tests green.

## Part C — armed, and proven on the live paper account

Arming is gated twice: a module constant `PR3_ENTRY_CRITERIA_CLOSED`
(the link to "the criteria that gate it" — flip it False and the loop
instantly reverts to no-submit) AND an explicit `armed=True`; it never
arms in dry-run.

`scripts/run_paper_day_t163.py` transcript (live PAPER account, creds
redacted; **2026-06-13 is a Saturday — market closed, next open Mon**):

```
=== T-163 armed paper day | market open=False | account=ACTIVE ===
allocator-visibility (logged every cycle): {account: roth, allocator: adaptive,
  dyn_opt: True, buffering: False, auction_execution: moo_moc, config_hash: 71e321a5db64}
scheduler armed=True (criteria gate + explicit opt-in)

1. STAGED   archondex-2026-06-15-SPY-1def59526eed82db -> staged
   16:05 pull_close_bars
   17:00 compute_signals_targets     staged 1 orders (1 OPG / 0 CLS)
   08:30 preflight                   reconcile_clean=True  CLEAN — proceed
   09:00 submit_opg          submit=1 ARMED(paper): submitted 1/1 OPG
   09:35 ack_sweep
   10:00 reconcile_1                 reconcile_clean=True
   15:40 submit_cls                  ARMED(paper): submitted 0/0 CLS
   16:10 eod_reconcile_snapshot      reconcile_clean=True
2. SUBMITTED(real POST) -> expired | broker_status=accepted | broker_id=set
3. POLLED   -> expired | filled_qty=0
4. FILLED(SIMULATED T+1 @ Mon open, market closed Sat) -> ledger SPY=1 | slippage_vs_t146=1.0bps
5. RECONCILED post-fill -> clean=True halt=False
RESULT: armed paper day complete | real chain reached 'expired' on the live
  paper account | fill leg = simulated_t1 | post-fill reconcile clean=True
```

**What is REAL vs simulated, stated plainly:** the submit→ack→reconcile
chain is REAL against the live paper broker — a real OPG POST returned
`accepted` with a broker order id, and all three reconcile cycles diffed
real broker truth and were clean. The order then EXPIRED at the eod step
because the loop correctly cancels an unfilled OPG at end-of-day — on a
non-trading Saturday there is no open for it to fill at (on a real
trading day the OPG fills at the 09:30 open, before eod). That eod
cancel hit the real broker — **the account was verified FLAT afterward**
(0 positions, 0 open orders), which is a real-account proof of crit-3's
expire/cancel path. The fill→ledger→reconcile leg is a CLEARLY-LABELLED
T+1 simulation (market closed); the deterministic fill path is also
proven by the cassette test `test_stage_submit_ack_fill`.

**Did a real paper order fill?** No — not synchronously possible on a
Saturday (OPG fills at the next open). The real order acked, queued, and
was expired/canceled clean by the loop. A real FILL will land the first
time this runs on a trading day (the natural next step before the
60-day clock).

## Go-live prerequisites (NOT started here)

PR-3 proves the loop CAN submit + reconcile a real paper day. The
sustained **60-day paper run (go-live) is a separate step**, gated on:
1. **The director's allocator-identity decision (T-158)** — the paper
   config exposes `allocator` explicitly and logs it; which allocator
   actually deploys is director-held. This is a hard go-live gate.
2. **The book / fork decision** — which strategy book paper trades.
3. Kill ACTIONS armed (reduce/flatten) — they stay SHADOW in PR-3.
4. A first real-trading-day run that produces an actual fill (trivial;
   just run the driver on a weekday).

## What the adversarial review should scrutinize

- **Crit-1/2 ordering**: is the intent truly journaled (fsync'd) before
  the POST, and does `reconcile_with_broker` correctly distinguish
  "broker has it" (adopt) from "broker never saw it" (revert→STAGED)?
  The `test_zero_broker_post_across_restart` is the load-bearing proof.
- **The arm gate**: `armed = armed AND not dry_run AND
  PR3_ENTRY_CRITERIA_CLOSED` — three conditions; confirm none can be
  bypassed and that dry-run can never submit.
- **Halt actually gates** (crit-4): the submit step checks
  `summary.halted` set by a PRIOR reconcile in the same day — confirm
  the preflight reconcile runs before submit_opg in the clock order.
- **Corporate-action ratio heuristic** (crit-5): is the 2..20 integer-
  ratio window the right split detector, and does the explicit feed
  override correctly? A genuine drift that happens to be a clean ratio
  would be mis-soothed to manual — the explicit feed is the safety.
- **The fill leg is simulated** — the review should confirm the real
  fill→reconcile only needs a weekday run, and that nothing in the
  ledger/reconcile path is faked beyond the labelled T+1 price.

## Files

- `paper_trader/{order_manager,reconciliation,scheduler}.py` — Part A criteria
- `paper_trader/{paper_config,order_construction,paper_telemetry}.py` — NEW, Part B
- `tests/test_paper_pr3_criteria_t163.py`, `tests/test_paper_pr3_partB_t163.py` — NEW
- `tests/test_paper_trader_pr1_t160.py`, `tests/test_paper_reconciliation_pr2_t160.py` — updated for the new lifecycle
- `scripts/run_paper_day_t163.py` — NEW, the armed-day driver
- this audit

## NOT done (later, gated)

- The 60-day paper run (go-live; gated above).
- Arming kill ACTIONS (reduce/flatten) — SHADOW only here.
- PR-4 (hard-gated): archive `live_trader/` + `storage/state_manager.py`
  + `brokers/alpaca_broker.py`; move the deployment boundary.
- A real weekday fill transcript (one driver run on a trading day).

---

# ADDENDUM — T-163-fix (2026-06-13): adversarial-review blockers + majors closed

The 17-agent adversarial review returned **block** on two dimensions —
all findings in the real-Alpaca-broker-vs-test-stub gap (the
silent-failure class). The architecture was affirmed ("the core design
is the right shape"); the holes were in error handling. All seven are
now closed, each with a test that fails-before / passes-after. 91 paper
tests green; re-verified on the live paper account.

| ID | Defect | Fix | Test |
|---|---|---|---|
| **B1** | `get_order`/`cancel_order` swallowed ALL exceptions → None/False; consumers reverted-to-STAGED / marked-flat on a transient failure (double-submit / believe-flat-while-live) | `get_order` is TRI-STATE (dict / `ORDER_ABSENT` 404 / `ORDER_UNKNOWN`); `cancel_order` True only on confirmed-or-provably-absent. `reconcile_with_broker` reverts SUBMITTED→STAGED ONLY on definitive ABSENT; `cancel`/`expire_unfilled` terminalize ONLY on a confirmed cancel or provable absence — UNKNOWN leaves the order OPEN | `TestB1TransientVsAbsent` ×5 |
| **B2** | `_is_duplicate_coid` required `client_order_id` (underscores); Alpaca's real body is `{"code":42210000,"message":"client order id must be unique."}` (spaces) → adopt-on-duplicate was DEAD | detect by structured `code==42210000` + message fallback matching the REAL text | `TestB2RealApiError` ×4 (constructs the real `APIError`) |
| **M1** | armed batch-submit/expire had no per-order handling + no try/finally → one raise aborted the day mid-batch (partially-submitted, unreconciled book) | per-order try/except (record + continue) + a try/finally guaranteeing the EOD reconcile/snapshot always runs | `TestM1ErrorHandling` ×2 |
| **M2** | preflight logged "BLOCKED" on `not clean` but the gate fires on `halt` → non-halt findings printed BLOCKED while submission PROCEEDED | the log now matches the gate: only HALT → BLOCKED; non-halt findings → PROCEEDS | `TestM2TruthfulPreflightLog` ×2 |
| **M3** | a clean integer qty-ratio on a held name was soothed to corporate_action (manual, no halt) — same shape as a double-counted fill | a ratio ALONE no longer downgrades; held-name morph is corporate_action ONLY with the explicit feed; ratio-without-feed still HALTS | `TestCrit5*` (updated) |
| **M4** | allocator had a silent `"adaptive"` default + was never a gate → paper would silently run the local machine (the T-158 trap) | `PaperConfig.allocator` is REQUIRED (bare `PaperConfig()` raises); arming is a HARD interlock that FAILS LOUD unless paper allocator == director-designated | `TestM4AllocatorInterlock` ×4 |
| **M5** | halt-gates-submit was tested only in dry-run (vacuously true) | a test with `armed=True, dry_run=False` + a halt asserts ZERO broker POSTs | `TestM5ArmedHaltZeroPosts` |

Minors folded: the paper client refuses any non-paper `url_override`;
the driver requires `--confirm` to arm.

**The false positives the review's refutation pass cleared were NOT
chased** (transient-GET-as-standalone — subsumed by B1+B2;
crit-2-untested — already covered; done_for_day — auction orders are
single-session; not-armed-untested — already covered).

**Re-verification on the live paper account** (armed, `--confirm`):
real chain staged → submit_opg ARMED (real POST, `accepted`, broker_id)
→ 3/3 reconcile clean → eod confirmed-cancel; account left FLAT;
preflight log now reads "CLEAN — proceed". The allocator interlock and
the `--confirm` refusal both fired as designed.

**Scope:** `paper_trader/` + its tests + the driver only (diff-stat
above). No live_trader/Engine B/config edits; engine imports read-only.
Ready for director re-review.

---

# ADDENDUM 2 — T-163-fix2 (2026-06-13): the fix round's 3 new same-class blockers, fixed STRUCTURALLY

The 14-agent re-review confirmed the original 2 blockers + 5 majors are
CLOSED, but my point-fixes (commit 90df30f) introduced 3 new defects —
all in **two small surfaces** (the broker-error classifier and the
journal-write path). The re-review's key insight: point-fixes caused
this; fix the surfaces ONCE, hardened, and lock them with
contract/property tests. Done.

## SURFACE 1 — one hardened broker-error classifier

`classify_broker_error(exc) → absent | duplicate | unknown`, **never
raises**, applied by BOTH `_is_definitive_absent` and
`_is_duplicate_coid`. Two new blockers killed:

- **NEW-BLOCKER-1**: `APIError.message`/`.code` are `@property`s that
  `json.loads` the body and RAISE on a non-JSON 502/timeout body;
  `getattr`'s default does NOT catch an exception thrown inside the
  getter → `get_order` raised instead of returning `ORDER_UNKNOWN`,
  crashing restart-reconcile. Fix: `_safe_code`/`_safe_message` read
  through `try/except → ""/None`.
- **NEW-BLOCKER-3** (the worst — a real believe-flat): the
  `"not found" in msg` substring fallback misclassified
  `ConnectionError("Name or service not found")` as ABSENT → reverted /
  flattened a LIVE order (re-opening B1). Fix: **absence is
  structured-signal ONLY** (`code==40410000` or `status_code==404`); the
  message-substring absence fallback is DELETED. Everything not provably
  absent/duplicate → UNKNOWN.

Also: `reconcile_with_broker` in `__init__` is wrapped so a restart
broker outage degrades gracefully (orders stay as the journal left
them). **CONTRACT/PROPERTY TEST** (`TestErrorClassifierContract`) sweeps
the error SPACE — APIError(JSON 40410000)→absent, (JSON 42210000)→
duplicate, non-JSON 502→unknown, ConnectionError("...not found")→unknown,
TimeoutError→unknown, status 404→absent — and asserts the classifier
never raises on any shape.

## SURFACE 2 — schema-complete journal writes + defensive replay

- **NEW-BLOCKER-2**: M1's armed submit-error guard appended a raw partial
  dict (`{client_order_id, event, error}`) bypassing `to_journal`; on
  restart `_replay_from_journal` did `OrderRecord(**payload)` with the
  5 required fields missing → TypeError → bricked restart. Fix (two
  layers): (1) the submit-error path now journals via the
  schema-complete `note_event`/`_record`; (2) `_replay_from_journal` is
  DEFENSIVE — a malformed line is QUARANTINED (`self.quarantined`) and
  skipped, never crashing construction (this also hardens the torn-
  journal path). **CONTRACT TEST** (`TestJournalReplayDefensive`) writes
  a schema-incomplete line and asserts construction survives + the
  submit-error record is replay-safe.

## SURFACE 3 — M4 interlock de-tautologized

The driver fed BOTH `PaperConfig(allocator=args.allocator)` AND
`designated_allocator=args.allocator` → designated == runtime by
construction → the mismatch branch was unreachable. Fix:
`designated_allocator` now comes from an INDEPENDENT committed source
(`config/paper_designated_allocator.json`, director-owned, placeholder
`"adaptive"` pending the T-158 decision); `--allocator` is required (no
silent default). **Verified live**: `--allocator mean_variance` →
`ARM REFUSED: paper allocator 'mean_variance' != director-designated
'adaptive'`; `--allocator adaptive` → armed day runs, account left flat.

## Minors folded

Sentinels are falsy (`_Sentinel.__bool__`); the driver checks the actual
broker state after cleanup and WARNs if not flat; `submitted_count`
excludes idempotent no-ops; `done_for_day→CANCELED` confirmed safe for
auction orders (fills adopted separately).

## Status

31 new fix2 tests (incl. the two required contract/property tests);
**122 paper tests green**; original 7 fixes intact (their tests still
pass). Live re-verification: armed day + mismatch refusal both fire as
designed; account flat. Scope: `paper_trader/` + tests + driver + one
config file. Ready for the third re-review.

---

# ADDENDUM 3 — T-163-fix3 (2026-06-13): the final persistence-recovery majors, FINAL round

The 3rd adversarial review CONFIRMED fix2 closed all 3 new blockers + the
M4 tautology with NO new blockers — the structural approach converged
(3 → 0). Classifier + M4 dimensions = `merge`. The journal dimension =
`merge-with-followups`: 2 refutation-confirmed majors, both in the
persistence-RECOVERY path, both the SAME class as NEW-BLOCKER-2. Closed
by extending the existing hardening to the sibling path — no new schemes.

## MAJOR-1 — LedgerStore read-back is now defensive (sibling of the order-journal fix)

`LedgerStore.__init__` used `existing[-1]` + `float(last["cash"])`
directly → a malformed/invalid last ledger line (a crash mid-ledger-
write — the exact recovery scenario) bricked construction. Fixed with
the IDENTICAL pattern as `_replay_from_journal`: walk all snapshots,
adopt the LAST VALID one, quarantine bad lines (`self.quarantined`).
`_parse_ledger_state` validates by VALUE (finite cash/pnl, int seq,
positions a dict of int-qty). Tests: malformed last line → constructs
(prior good line adopted), invalid-positions-shape → quarantined, torn
last line → recovers prior.

## MAJOR-2 — defensive replay validates VALUES, not just shape

A schema-complete but wrong-typed / invalid-enum record passed
`OrderRecord(**payload)` (a dataclass doesn't validate) and replayed
into bad state. `_validate_order_values` now rejects an invalid
state/side/tif enum, non-positive/wrong-type qty, negative filled_qty,
or non-finite price → quarantined like a malformed line. Tests
parametrize the bad-value space (6 cases) + assert a valid record still
replays.

## The 3 minors

- **Journal minor**: a line missing `client_order_id` is now QUARANTINED
  with an explicit `"missing_client_order_id"` error (was silently
  dropped — no observability).
- **Classifier minor A**: the contract sweep gains the PRODUCTION 404
  shape — `APIError(non-JSON body, http_error.response.status_code=404)`
  → ERR_ABSENT (the structured signal even when the body isn't JSON).
- **Classifier minor B**: `_safe_status_code` int-coerces (a stringy
  `"404"` still matches) — mirrors the code-path's `int()`.
- **Nit**: `reconcile_with_broker`'s restart-outage swallow now RECORDS
  the error (`self.reconcile_start_error`) instead of a silent
  except-pass — a non-outage logic bug is observable.

## Status

No new raw-dict writes, no message-substring inferences (the two
patterns that caused the prior rounds). 16 new tests extend the existing
contract tests; **138 paper tests green**; contract suite + broader repo
unaffected. The persistence/recovery layer (order journal + ledger +
reconcile log) is now uniformly defensive. Ready for the director's
TARGETED verification → merge.
