---
name: account2-reset-findings-2026-11-17
description: Account-2 reset runbook (2026-11-17) findings — Alpaca paper cannot reset in place, the tier is a cap not a balance, seeding-day stand-down, 36-vs-35 clean-session near-miss, laptop .env = account 1
metadata:
  type: project
---

Drafted `docs/Sources/runbook_account2_reset_2026-11-17.md` (branch `docs/account2-reset-runbook`, a5cf0b8) after the user ruled RESET (not basis adjustment) on 2026-11-17. Durable findings:

- **Broker reliability.** The Alpaca PAPER split processing ×4'd the 18 MTUM bought ON the ex-date at the post-split price (true 38, broker 92, about $3.5k phantom). Never trust paper broker share counts on split days. Paper also does not simulate dividends, so SGOV's cash leg earns about 0 in the record.
- **Alpaca reset is gone.** The docs (paper-trading.md, read 2026-11-17) say: create/delete paper accounts plus new keys; an existing balance cannot be changed. The user has a 3-paper-account cap (provision_paper_fleet.py:87), so a "new account" probably means deleting the old one, which is irreversible.
- **Sizing.** The tier is the notional CAP; sizing = min(broker equity, contributed cap). A windfall in broker cash is FENCED, not removed. The fence fails at tiers of roughly $100k or more on that account. The contributed cap is $10k + $583 per whole month since 2026-09-11, giving $11,166 from 2026-11-11.
- **Near-miss.** The tracker counted the 2026-11-05 defect day as clean (36). The valid count is 35 tracked sessions, 09-17 → 11-04. The tracker summary uses ALL points, including non-canonical ones.
- **Near-miss.** The laptop `.env` holds ACCOUNT 1's Alpaca keys, and AlpacaPaperClient loads `.env`. Any broker action run locally hits account 1. Always go through the account's own jobdef (Batch command override).
- **Fresh state.** A fresh prefix gives a seeding day (no marks, stand-down, exit 70); trading starts on the second run. A state-only reset with a non-flat broker gives an UNEXPLAINED halt forever.
- **Mirror display defects.** (1) It passes the BASE cap, not the contributed cap (run_paper_cloud_day.py:1592), so total_change includes contributions. (2) On arrival day it uses broker positions captured BEFORE trading (:621, :1585) with a post-fill basis, so it reads tier_equity 0 / −$10,000 until the next day. Both are tracked in T-401.
- **Silent cash adoption.** Once positions are held, a cash-only broker correction is silently ADOPTED into the ledger (held_reconcile.py:116-118). CASH_DRIFT fires only on a flat account.
- **The split feed asks about no tickers on the first two runs after a reset** (nothing is held or journaled yet). Only the price guard and a manual calendar check stand.

**My own runbook near-misses, caught by the review of revision 1:**
- An md5 gate without `pipefail` passed on two failed reads (md5 of an empty string on both sides).
- Restoring a schedule from an early capture would silently revert a mid-window redeploy. Always rebuild from a FRESH GET and assert the expected revision.
- The irreversible broker step was ordered before a possibly denied S3 move. Probe permissions first, and put reversible steps first.
- I predicted the arrival-day mirror from code reading. A simulation of the real `main()` showed otherwise. Simulate artifact expectations instead of inferring them.
- I hand-compacted two scripts when embedding them in the runbook, so the text there was not the tested file. Commit the ops scripts and their tests next to the runbook (`docs/Sources/runbook_account2_reset_ops/`), embed exact bytes, and gate the match with `check_embedded.py`. Never leave tested scripts only in the scratchpad.

**Why:** these decide whether a paper record can be restarted cleanly and what a real-money path inherits.

**How to apply:** for any paper reset or re-tier:
- Liquidate in place through the account's jobdef.
- Archive with pipefail and a three-way md5 (step-1 snapshot, live object, archive copy) before `mv`; bucket versioning is not available.
- Disable and re-enable the schedule from fresh GETs that change only State, and assert the revision pin.
- Expect exit 70 on day 1.
- Drive the real `main()` against a fake broker to set the day-1 to day-3 expectations.

See [[live-paper-path-audit-2026-09-17]].
