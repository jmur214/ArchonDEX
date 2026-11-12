---
name: project-b8-execution-timing-2026-11-11
description: B-8 (T-386) execution-timing prereg 54d0104 — Phase 1 STOP awaiting 7 rulings; the fleet journal has NO open/close fills (all ~09:51 ET market DAY); deployed system is a daily band-checker, not monthly
metadata:
  type: project
---

B-8 (T-386) prereg `docs/Sources/prereg_b8_execution_timing_2026-11-11.md` was committed at `54d0104` on `research/execution-timing-b8`, 2026-11-11. It is a DRAFT. Seven rulings were requested (§18), and no returns have been computed. Prior P(H1) ≈ 4%; prediction: REFUTED.

**Durable facts found by reading the artifacts:**
- **Account 2's journal is the only fill record, and it has no open or close fill.** It lives at `s3://archondex-results-407539788432/paper_state_offense_sso/data/{paper_state/orders.jsonl, state/exec_cost_ledger.jsonl}`. All 12 fills are market DAY orders at ≈ 09:51 ET. So realized open-vs-close slippage can never come from the fleet as it is configured.
- **Pre-void costs:** 10 fills ≤ 2026-11-04 (VOO 1.65 bps, MTUM 0.00, SGOV 0–0.99 bps). Notional-weighted 1.33 bps.
- **VOO and MTUM never traded after the 2026-09-15 arrival.** The bands did not bind in 36 sessions.
- **The deploy candidate is not a monthly rebalancer.** It is a DAILY band check at 09:50 ET (`cron(50 9 ...)`). The driver accepts TIF day|opg only, so no MOC path exists. Contributions land on the 11th.
- **Local Stooq raw** (`data/raw/stooq/daily/us/nyse etfs/`) has SPY 2005+, VOO 2010+, MTUM 2013+ and SGOV 2020+, all back-adjusted. It is usable as an Open-field validator (the intraday ratio), not as a return source.

**Why:** the user's go-ahead for the frontier program. B-8 is the cheap Route-J closure.

**How to apply:** check the director's rulings (an amendment appended to the prereg) before Phase 2. If REFUTED, do not re-propose execution timing for this book unless flows grow by roughly 100× relative to the book. See [[feedback-held-book-timing-trap]].
