---
name: project-b8-execution-timing-2026-11-11
description: B-8 (T-386) execution timing CLOSED WITHOUT RUNNING by director ruling 2026-11-11 (N_trials 0) — power analysis settled it; durable census facts: fleet journal has NO open/close fills, deploy candidate is a daily band-checker with no MOC path
metadata:
  type: project
---

B-8 (T-386) was **closed without running** on 2026-11-11, with N_trials 0.
- **Record:** the prereg `docs/Sources/prereg_b8_execution_timing_2026-11-11.md`. The draft is at `54d0104`; the director-ruling section was appended in the follow-up commit.
- **Verdict:** "execution timing is noise at this turnover — closed by power analysis, not by measurement".
- **Nothing ran:** no price was fetched and no return was computed.

**Why it closed.** Pre-data arithmetic settled it:
- the MDE is ≈ 0.9 bps/yr after Holm, against a plausible effect of ≤ 0.3 bps/yr;
- a perfect-hindsight ceiling is ≈ 2–5 bps/yr at ≈ 6.4%/yr turnover.

The director ruled that spending an honest-N trial on an arithmetic-settled question raises the bar for every later test.

**Durable facts (read from the artifacts):**
- **The fleet journal has no open or close fills.** Account 2's journal at `s3://archondex-results-407539788432/paper_state_offense_sso/data/{paper_state/orders.jsonl, state/exec_cost_ledger.jsonl}` holds 12 fills, all market DAY at ≈ 09:51 ET. The 10 fills ≤ 2026-11-04 cost 1.33 bps notional-weighted and 0.61 bps simple mean.
- **VOO and MTUM never traded after the 2026-09-15 arrival.** The bands did not bind in 36 sessions.
- **The deploy candidate is a daily band check at 09:50 ET**, not a monthly rebalancer. The driver accepts TIF day|opg only, so there is no MOC path. Contributions land on the 11th.
- **Local Stooq raw** (`data/raw/stooq/daily/us/nyse etfs/`) is usable as an Open-field validator (the intraday ratio), never as a return source.

**How to apply:**
- Do not re-propose execution or turn-of-month timing for this book.
- Re-open only if (a) an MOC/LOC order path exists, in which case measure its realized cost first, or (b) turnover rises roughly 10× (≳ 60% of the book per year). Re-run the turnover arithmetic first.
- **Lesson:** when the pre-data MDE arithmetic settles a question, propose closure without running. That keeps the honest-N count down.

See [[feedback-held-book-timing-trap]].
