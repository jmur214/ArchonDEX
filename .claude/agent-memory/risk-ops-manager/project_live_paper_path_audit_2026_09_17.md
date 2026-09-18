---
name: live-paper-path-audit-2026-09-17
description: Near-misses found in the daily cloud paper path (order_manager/reconciliation/wash guard/halt) on 2026-09-17 — what is real enforcement vs claim, before any real-money move
metadata:
  type: project
---

Audit of the EventBridge→Batch→run_paper_cloud_day.py path (accts 1/2/3), 2026-09-17, read-only.

Near-misses (risk engine claims protection it does not have):
- Cross-account wash guard is UNFED: `tax_lots.jsonl` lives under each account's OWN S3 prefix (DURABLE_PATHS), acct-1 runs `wash_guard=None` so it never calls `ledger.record_fill`, and there is no cross-prefix pull of lots. The driver comment "a VOO buy CAN be refused because of an account-1 SPY loss" is false in code. Same class as T-342 channel liveness.
- CASH_DRIFT halt is neutralized whenever positions are held: `adopt_explained_broker_truth` adopts broker cash every run if positions are explained+non-empty, so a standalone cash mystery only halts on a FLAT account.
- PRICE_DRIFT / MISSED_FILL(window) never fire on the cloud path: `inputs_fn` passes no `expected_prices` and `window_closed=False` always.
- Journal durability is container-exit granularity (S3 push at end), not per-write: a hard kill after the broker POST loses the intent record → next run sees an unexplained position → HALT with no operator adopt tool.
- Halt is per-account (3 S3 objects), not one fleet object. Calendar fallback holiday set is 2026-only; client has no `get_clock`, so a broker-calendar outage on a holiday would rest DAY market orders to the next open.

**Why:** the user intends to move real Roth money onto this exact path; these are the items that make "the guard is on" a false statement.
**How to apply:** before any real-money proposal, require (1) a fed cross-account lot ledger with a liveness check, (2) cash-drift detection independent of adoption, (3) per-write journal durability or a pre-submit S3 checkpoint, (4) limit/collared orders, (5) a live client that is NOT `AlpacaPaperClient` (paper pin is a feature — keep it).
