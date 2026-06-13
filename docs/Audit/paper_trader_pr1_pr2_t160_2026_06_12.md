---
task_id: T-2026-06-12-160
title: Paper-trading loop PR-1 (order-state machine + ledger + client) + PR-2 (reconciliation + dry-run scheduler)
date: 2026-06-12
substrate: n/a (pure-new package; no backtest; no existing file touched)
scope: NEW paper_trader/ package + its tests ONLY — zero edits to live_trader/, engines/, backtester/, orchestration/, configs (diff-stat proof below)
outcome: **Delivered, both PRs, verified against the LIVE paper account.** PR-1: the order-state machine T-159 named as the codebase's biggest gap — STAGED→SUBMITTED→ACKED→(FILLED|PARTIAL|REJECTED|EXPIRED|CANCELED), append-only journal, deterministic idempotent client_order_id, OPG/CLS TIF, LedgerStore (belief-only accounting), paper-pinned Alpaca client. **Real paper-API OPG smoke ran end-to-end: staged→acked→canceled.** PR-2: ReconciliationEngine (three-way diff, 7-class taxonomy, pre-registered responses, only cash/position drift halt) + DRY-RUN scheduler walking the §1.1 clock submitting NOTHING. **Real dry-run day against the live paper account: clock fully walked, reconcile 3/3 clean, submitted=0.** 35 cassette/fixture tests green (+1 smoke that runs with creds). One design-vs-reality finding: the existing `brokers/alpaca_broker.py` reads a credential name (`ALPACA_API_SECRET`) that does not exist in `.env` (`ALPACA_SECRET_KEY`) — it would fail to authenticate; this client uses the correct name.
---

# T-160 — Paper loop PR-1 + PR-2

## Scope proof — zero existing files touched

```
 paper_trader/__init__.py                    |  59 ++  (new)
 paper_trader/_jsonl.py                      |  55 ++  (new)
 paper_trader/ledger_store.py                | 135 ++  (new)
 paper_trader/order_manager.py               | 233 ++  (new)
 paper_trader/paper_client.py                | 204 ++  (new)
 paper_trader/reconciliation.py              | 204 ++  (new)
 paper_trader/scheduler.py                   | 140 ++  (new)
 tests/test_paper_trader_pr1_t160.py         | 242 ++  (new)
 tests/test_paper_reconciliation_pr2_t160.py | 241 ++  (new)
 9 files changed, 1513 insertions(+)
```
`git diff --name-only origin/main HEAD | grep -v paper_trader/ | grep -v test_paper` → **NONE**. Pure-new per the hard constraint. No engine import anywhere in the package (the order-construction wiring is PR-3, propose-first). No live-money endpoint in code or tests — `AlpacaPaperClient` is pinned `paper=True` and raises if asked otherwise.

## PR-1 — the order-state machine the codebase lacked

`OrderManager` (`paper_trader/order_manager.py`): the lifecycle every
prior path skipped —
`STAGED → SUBMITTED → ACKED → (FILLED | PARTIAL | REJECTED | EXPIRED |
CANCELED)`. Every transition is journaled append-only (fsync'd) BEFORE
the next action, so `replay` rebuilds in-memory state after a crash.
Broker statuses normalize through `_BROKER_STATE_MAP` (transient
`pending_*` → no transition). OPG/CLS TIF only (the T-146 convention).

**Idempotency / restart safety:** `client_order_id =
sha1(trade_date|ticker|side|qty|config_hash)[:16]` — a stable hash, NOT
Python's per-process-salted `hash()`. A crash-and-retry produces the
same id, which collides with the already-submitted order at the broker;
`submit()` on a non-STAGED record is a no-op (tested: exactly one POST
across three submit calls, and idempotency survives a journal-replay
restart). This is the mechanism behind the T-146 live one-pager's
"never blind-resubmit past the 9:28 OPG cutoff."

`LedgerStore` (`ledger_store.py`): positions/cash AS WE BELIEVE,
append-only, updated only on OBSERVED fills — never on intended orders
(the exact conflation T-159 flagged in `mode_controller`'s adapter,
which fabricates fills at intended prices). Weighted-avg accounting
mirrors `PortfolioEngine.apply_fill`'s identity without importing it.

`AlpacaPaperClient` / `FakePaperClient` (`paper_client.py`): the minimal
`PaperClient` interface; the real one wraps alpaca-py `TradingClient`
pinned to paper; the fake is a scripted cassette for no-network tests.

### Real paper-API OPG smoke (transcript)

Run with `.env` creds against `paper-api.alpaca.markets` (values
redacted; the script prints only states):

```
creds present: True
paper account status: AccountStatus.ACTIVE | equity present: True
1. staged: staged | coid: archondex-2026-06-15-SPY-61c37c6068198e55
2. submitted-> acked | broker_status: accepted | broker_id set: True
3. polled  -> acked | broker_status: accepted
4. canceled-> canceled
RESULT: lifecycle reached canceled | terminal: True
```

The full submit → ack → cancel lifecycle is proven against the real
paper broker; the deterministic coid is visible in the prefix.

## PR-2 — reconciliation + dry-run scheduler

`ReconciliationEngine` (`reconciliation.py`): the three-way diff —
(a) ledger belief, (b) broker truth, (c) journal expectation — into the
seven pre-registered classes, each with its response chosen NOW:

| class | trigger | response | halt | manual |
|---|---|---|---|---|
| missed_fill | acked, 0 fills, window closed | cancel; log; no chase | – | – |
| partial_fill | 0 < filled < qty, order done/window-closed | adopt broker truth; cancel remainder | – | – |
| reject | state REJECTED | sub-classify {fractional, after_cutoff, buying_power, other}; skip for day | – | – |
| price_drift | \|fill − expected\| > safety+5bps | accept fill; feed slippage-error series | – | – |
| cash_drift | \|ledger − broker cash\| > $1 | HALT new submissions | ✅ | – |
| position_drift | known-ticker qty mismatch, no open order | HALT; adopt only after journal explains | ✅ | – |
| corporate_action | unknown symbol at broker | halt ticker; manual review | – | ✅ |

A cycle is `clean` iff zero findings; the engine never mutates state
(the caller applies adoption/halt). Only cash/position drift halt; only
corporate action is manual — exactly as designed.

`PaperScheduler` (`scheduler.py`): the §1.1 daily clock as ordered
steps, DRY-RUN by default — stages+logs, runs reconcile at
preflight/reconcile_1/eod, appends the per-cycle `clean` bool to the
append-only `reconcile_log` (promotion criterion §5.3 input), and
SUBMITS NOTHING. The live submit step raises `NotImplementedError`
until PR-3 arms it (tested).

### Real dry-run day against the live paper account (transcript)

Broker truth pulled from the live paper account; scheduler submits
nothing:

```
broker truth: status=AccountStatus.ACTIVE cash present=True positions=0
  16:05 pull_close_bars            [data]
  17:00 compute_signals_targets    [compute]
  08:30 preflight                  [preflight] reconcile_clean=True
  09:00 submit_opg                 [submit_opg] would_submit=1
  09:35 ack_sweep                  [ack]
  10:00 reconcile_1                [reconcile] reconcile_clean=True
  15:40 submit_cls                 [submit_cls] would_submit=1
  16:10 eod_reconcile_snapshot     [eod] reconcile_clean=True
RESULT: submitted=0 (MUST be 0) | reconcile 3/3 clean | halted=False
```

The clock walks; OPG and CLS batches are COUNTED (`would_submit=1`
each) but never sent; all three reconcile cycles against real broker
truth are clean.

## Tests

- PR-1 (16 + 1 smoke): deterministic-id (field-sensitive, sha1 not
  salted-hash), full lifecycle (ack→fill, partial→fill, reject,
  cancel, CLS routing), double-submit-noop, restart-replay-recovery,
  append-only journal timeline, ledger PnL/commission/weighted-avg/
  persistence/broker-adoption. Smoke skips cleanly without creds.
- PR-2 (19): the all-agree clean case; a fixture per divergence class
  asserting its pre-registered response + halt/manual flags;
  within-threshold clean cases (price drift, cash, open-order-explains-
  gap); halt aggregation; a logged dry-run day (zero submissions, full
  clock); a dirty-cycle reconcile_log; the live-mode guard.
- 35 passed + 1 skipped; contract suite unaffected (no producer change).

## The implementation-vs-design catch (the standing pattern)

The design (and the inbox) named the secret env var `ALPACA_SECRET_KEY`;
implementation confirmed `.env` indeed uses `ALPACA_API_KEY` /
`ALPACA_SECRET_KEY`. But the EXISTING `brokers/alpaca_broker.py:35`
reads `ALPACA_API_SECRET` — a name absent from `.env` — so that stub
raises "Missing Alpaca API credentials" and could never have
authenticated. The design was right; a pre-existing file was wrong.
PR-4 archives that stub anyway; flagged here so the audit trail records
it. (No fix applied — pure-new constraint; this is a finding, not a
PR-1/2 change.)

Nothing else in the design was contradicted by implementation: OPG/CLS
TIF exist in alpaca-py 0.43.2 (`['day','gtc','opg','cls','ioc','fok']`);
the lifecycle, journal, and reconciliation taxonomy built exactly as
specified.

## Files

- `paper_trader/{__init__,_jsonl,order_manager,ledger_store,paper_client,reconciliation,scheduler}.py` — NEW
- `tests/test_paper_trader_pr1_t160.py`, `tests/test_paper_reconciliation_pr2_t160.py` — NEW
- this audit

## NOT done (later PRs, per the design)

- PR-3 (propose-first): wire production order construction (Engine
  A→C→B) into the scheduler + arm the submit step + T-152 feed adapter
  + T-141 shadow checks + T-151 weekly job.
- PR-4 (hard-gated): archive `live_trader/` + `storage/state_manager.py`
  + `brokers/alpaca_broker.py`; remove the synthetic-fill adapter path;
  move the deployment boundary.
- No order construction, no engine imports, no live submission here.
