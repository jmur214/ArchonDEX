---
name: project-t416-options-snapshot-archive
description: T-416 daily options snapshot archive — current design after the 2026-11-24 review fixes (rule v2, coverage against what was EXPECTED, slots, session/calendar logic, verifier, bounds) and why; unmerged branch, first production artifact owed
metadata:
  type: project
---

Built 2026-11-20 on branch `worktree-agent-aeda84432f0d9481c`, hardened 2026-11-24 after an independent review by execution (R1–R9). Not merged as of 2026-11-24. The owner approved building our own options history (quotes + IV) since no free one exists.

**Why:** Alpaca has no historical option quotes, and IV/greeks exist only as current values. A day not captured cannot be recaptured, so a problem may cost a row or an underlying, never the day, and never quietly. See [[reference-alpaca-options-api-quirks-2026-11-20]].

**Current design** (`scripts/archive_options_snapshots.py`, `config/options_archive_universe.json`, 49 names)
- **Rule v2:** session-stamped quote; bid > 0 with both sizes > 0; bid ≤ ask ≤ no-arbitrage bound; ask ≥ intrinsic − 2 %; spread ≤ max($0.10, 175 % mid) = ask ≤ 15×bid; IV 1 %–500 % (waived for XSP). v1's "or a same-session trade" leg admitted 144 pulled XSP quotes and was dropped.
  - Real shares under v2: 11-20 16:16 ET 88.0 % (XSP 0.782, lowest ABBV 0.664); 11-24 12:45 ET 84.8 % (XSP 0.912, lowest PG 0.569). Both judge 49/49 OK.
  - Spread leg: first built at 50 % of mid, which rejected 11.7 % / 6.1 % of non-XSP two-sided rows; director ruled 1.75 on 2026-11-24 (1.2 % / 1.0 %). The $0.10 allowance is inert for bids ≥ 1 cent. The flag marks usable, not tight; it is recomputable from RULE_COLUMNS.
- **Coverage is judged against what was EXPECTED** (contract listing), not on what came back: ≥ 10 real, ≥ 30 % real, ≥ 90 % of expected listed contracts returned, ≥ 4 expiries, no one (bid, ask) on > 25 % of real rows (real max 3 %). FAILED below 90 % of names or any of SPY/QQQ/IWM/XSP. Expected counts are in the run log so `--verify` re-judges.
- **Session/slot:** eod = last session that closed, captured late after midnight/weekends (assumes Alpaca still serves closing quotes; unobserved for active contracts); between open and close eod is refused (rc 2). `slot` is in the dedup key (`near_close` exists, no job). A day is skipped only when Alpaca AND the rules say closed; `--verify` believes a closure only from a LATER run's calendar.
- **Verifier:** every session since the first file needs an eod capture; unrepaired gaps alarm daily until listed in config `acknowledged_gaps`.
- **Bounds:** 60 s total per request (daemon thread), 1500 s run budget, 2400 s perl alarm in the wrapper (rc 142).

**How to apply:** read the first production file by content, XSP first (the close is a pulled market: 164/1,940 quotes zeroed at 15:59:59 on 11-20). The 18:30 ET feed state is still unobserved.
