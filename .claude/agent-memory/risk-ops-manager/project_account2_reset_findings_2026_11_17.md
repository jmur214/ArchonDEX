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
- **Mirror display defect.** The fleet mirror passes the BASE cap, not the contributed cap (run_paper_cloud_day.py:1592), so total_change includes contributions.

**Why:** these decide whether a paper record can be restarted cleanly and what a real-money path inherits.

**How to apply:** for any paper reset or re-tier, liquidate in place through the account's jobdef. Archive with a byte-verified copy before `mv` (bucket versioning is not available). Disable the schedule by the GET → State-only → cli-input-json pattern. Expect exit 70 on day 1. See [[live-paper-path-audit-2026-09-17]].
