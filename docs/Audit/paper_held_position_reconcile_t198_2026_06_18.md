# Held-position reconciliation fix (T-198)

**Date:** 2026-06-18 · **Branch:** `feature/paper-held-position-reconcile-t198` ·
**Agent:** E · **Endpoint:** Alpaca **PAPER** only.

## The blocker (adversarial pre-flight; director-verified)

The cloud daily pulse (`run_paper_cloud_day.py`) was a **flat-account
heartbeat**: it built a fresh empty ledger each run and never converged it
to broker truth (the caller never called `LedgerStore.adopt_broker_truth`).
The moment the first real fill (SPY OPG `4dcffc7c`, filling at the 6/18
open) is HELD, the three-way reconcile would have:

- empty `known_tickers` → mislabel the held SPY a `CORPORATE_ACTION`
  ("suspected ticker change");
- ledger cash (unchanged) vs broker cash (reduced) → `CASH_DRIFT` → HALT;
- `account_flat=False` → the `heartbeat.py` canonical gate forces
  `canonical=False` → exit 70 → Batch FAILED → **the non-canonical alarm
  fires every single day the position is held.**

The dead-man's-switch would invert into a daily cry-wolf storm + a halted
loop. The prior 74 paper tests all passed because the held-position tests
pre-seeded the ledger to MATCH the broker — the real operating shape
(broker holds, ledger empty → adopt) was untested.

## The fix — the loop correctly TRACKS held positions (it does NOT trade)

- **`paper_trader/held_reconcile.py`** (new, pure/testable):
  - `journal_net_positions(orders)` — net of OBSERVED fills (belief updates
    only on a fill, per the LedgerStore contract).
  - `explain_broker_positions(broker, orders)` — STRICT: every held broker
    position must be attributable to known fills, and vice-versa. A mystery
    position (ticker never ordered) OR a quantity our fills don't account
    for → UNEXPLAINED.
  - `adopt_explained_broker_truth(ledger, broker_pos, broker_cash, orders)`
    — converge the ledger (positions + the cash that moved *because* of
    those fills) to broker truth IFF explained. A genuine unexplained
    position is **NOT** adopted (FAIL-SAFE: assume nothing) → it stays
    non-canonical / HALTs.
  - `known_tickers_for(orders, ledger_pos)` — every ticker ordered or held,
    so a legitimately-held name is never mislabeled a ticker change.
- **`run_paper_cloud_day.py`**: BEFORE the reconcile cycles — poll
  non-terminal orders (so the journal reflects fills), adopt the explained
  part, populate `known_tickers`, pass `account_explained`. `main()` now
  accepts injectable `now`/`client`/`cloud` for tests.
- **Canonical gate** (`heartbeat.py` + `scheduler.py`): `account_flat` →
  `account_explained`. Canonical = reconcile-clean + not-halted + account
  **EXPLAINED** (not "account empty") + census-clean. Only a genuine
  unexplained position forces non-canonical.

## Verification

- **`tests/test_paper_held_position_t198.py` — 12 passed**: the journal-net
  / explain helpers; adoption (explained adopts ledger+cash, unexplained
  does NOT); **held-fill cycle → reconcile clean → CANONICAL** (the real
  operating shape); known-ticker qty-mismatch → POSITION_DRIFT **HALT** +
  non-canonical; unknown symbol → non-canonical; and the **Juneteenth
  driver end-to-end** (`main()` → `happened=True`/`canonical=True`/`rc=0`),
  which the pre-flight flagged as previously inspection-only.
- Full paper + reconcile + heartbeat + ledger + scheduler suite: **221
  passed / 1 skipped / 1 xfailed** — the `account_flat→account_explained`
  rename is clean, no regressions.
- **Lean image rebuilt** with the fix: `archondex-backtest:paper-sha-6aa1fe5`
  (sanctioned git-archive build). Job def **rev 4** points at it; schedule
  stays **DISABLED**.
- **Flat re-verify (Fargate `3c50e6e3`) PASSED**: pulled the (now-seeded)
  S3 journal, account flat (the OPG still queued pre-open) → explained →
  reconcile 3/3 clean → canonical → exit 0.
- **Dead-man's-switch re-confirmed (Fargate `f66ec5f5`)**: mismatched
  allocator → exit 66 → Batch FAILED (the `PaperRunCanonical=0` + FAILED
  fault signal still fires on the new image; the alarm→SNS wiring is
  unchanged from T-186-exec).
- **S3 durable journal SEEDED** with the first-fill order
  (`s3://…/paper_state/data/paper_state/orders.jsonl`) — the manual first
  fill ran off-cloud, so its journal wasn't in S3; without it the cloud
  loop would see the held SPY as unexplained. Now seeded, the loop will
  adopt the held SPY once it fills.

## Pending (physically gated on market hours)

- **Held-position LIVE Fargate re-verify** fires after the **6/18 09:30 ET
  open** (when `4dcffc7c` fills → the paper account genuinely holds SPY).
  Command: `aws batch submit-job --job-name paper-t198-held-verify
  --job-queue archondex-backtest-queue --job-definition
  archondex-paper-cloud-day` → expect: pull seeded journal → poll order
  FILLED → adopt SPY → reconcile clean → canonical → exit 0. The held-position
  LOGIC is already proven deterministically by the 12 unit tests; this is
  the live integration confirmation, and the director re-verifies before
  enabling the schedule regardless.

## Image recipe now on this branch (for main)

`Dockerfile.paper` + `scripts/build_paper_image.sh` + the deploy
`_comment`-strip fixes were merged from the provision branch onto the T-198
line, so once the director merges T-198 to main, main can rebuild the
verified image. Nothing AWS-live is changed by the merge.

## Design note — reconcile-only vs wiring the trading layer (my read)

**Keep it reconcile-only for now; do NOT wire autonomous order generation
yet.** Rationale: (1) the base has no validated edge (T-180-v2: nothing
strictly clears), so autonomous orders would trade an unvalidated signal;
(2) the paper run's job is to validate the MACHINE (lifecycle /
reconciliation / dead-man's-switch) — which reconcile-only + occasional
manual fills already does — while the EDGE is judged separately vs the
Schwab robo; (3) wiring trading needs the in-container data pipeline
(signal generation), but the lean paper image deliberately bakes NO data
substrate — wiring it would either re-bloat the image or add a data-fetch
path (a real architecture decision). Right sequence: validate the machine
→ measure base-vs-robo historically (A's lane) → THEN decide whether to
wire paper trading once there's something worth trading. This is a
director+user call, raised for that decision.
