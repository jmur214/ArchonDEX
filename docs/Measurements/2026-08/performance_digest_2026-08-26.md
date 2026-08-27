# Performance digest — 2026-08-26

*Auto-generated weekly. Informational only — this digest reports what the
machine did; it does not recommend, schedule, or prompt any decision.*

> **Sleeve rows answer:** what does the drawdown insurance COST, live? — NOT 'is the sleeve winning?'
> **Can evidence:** the live, realized PRICE of the sleeve's drawdown protection: its return give-up vs the twin alongside the drawdown it actually avoided, at measured costs.
> **Cannot evidence:** that the sleeve 'beats' its twin on return. T-333 measured the timing component as significantly VALUE-DESTROYING net of cash in the modern era (−5.16pp/yr, CI excludes 0); the sleeve is a drawdown instrument bought WITH return. A live record showing the sleeve behind its twin is the EXPECTED shape, not a failure — and one showing it ahead over a short window is not a refutation of T-333.
> *(source: T-333 excess-of-cash attribution (2026-07-28))*

**8 streams tracked** as of 2026-08-26.
**Nothing is decidable yet** — all 8 streams are still inside the 60-day minimum record.
Largest gap vs benchmark: **btc 5% shadow (exploratory)** at **+$39 per $10K** (27 days).

---

## Per-stream

| stream | vs benchmark (per $10K) | current drawdown | days | read |
|---|---|---|---|---|
| account-1 trend sleeve (paper) | −$89 | -0.1% | 26 | too early to say (26 days) |
| book: damped_offense_t298 | — | — | 21 | too early to say (21 days) |
| book: quality_satellite | −$28 | -1.9% | 21 | too early to say (21 days) |
| book: sleeve_tier_50k | +$25 | -0.4% | 21 | too early to say (21 days) |
| book: spy_null | +$0 | -2.0% | 21 | too early to say (21 days) |
| btc 5% shadow (exploratory) | +$39 | -0.1% | 27 | too early to say (27 days) |
| dbmf shadow (3rd-stream clock) | +$0 | — | 22 | too early to say (22 days) |
| llm analyst shadow book | −$240 | — | 22 | too early to say (22 days) |

*"Too early to say" is applied to any stream with fewer than 60 days of record, no matter how good or bad its numbers look. Gaps under $50 per $10K read as "roughly matching" — inside the noise.*

### Sleeve ahead of its twin — read this before concluding anything

- **book: sleeve_tier_50k** is ahead by +$25 per $10K over 21 days.
  - *that the sleeve 'beats' its twin on return. T-333 measured the timing component as significantly VALUE-DESTROYING net of cash in the modern era (−5.16pp/yr, CI excludes 0); the sleeve is a drawdown instrument bought WITH return. A live record showing the sleeve behind its twin is the EXPECTED shape, not a failure — and one showing it ahead over a short window is not a refutation of T-333.*

### Cash-drag annotation (secondary — not the record)

- **book: quality_satellite** — raw: **−$28** per $10K (the record) · cash-adjusted: −$28 per $10K · 1 day(s) missing a rate
  - *ANNOTATION ONLY — the raw NAV above is the record. Live paper cash earns 0%; the backtest spec credits the short rate, so this shows what that gap is worth. Never a restatement. INCOMPLETE: 1 day(s) had no rate and accrued NOTHING (fail-closed, never assumed 0%).*
- **book: sleeve_tier_50k** — raw: **+$25** per $10K (the record) · cash-adjusted: +$26 per $10K · 1 day(s) missing a rate
  - *ANNOTATION ONLY — the raw NAV above is the record. Live paper cash earns 0%; the backtest spec credits the short rate, so this shows what that gap is worth. Never a restatement. INCOMPLETE: 1 day(s) had no rate and accrued NOTHING (fail-closed, never assumed 0%).*
- **book: spy_null** — raw: **+$0** per $10K (the record) · cash-adjusted: +$0 per $10K · 1 day(s) missing a rate
  - *ANNOTATION ONLY — the raw NAV above is the record. Live paper cash earns 0%; the backtest spec credits the short rate, so this shows what that gap is worth. Never a restatement. INCOMPLETE: 1 day(s) had no rate and accrued NOTHING (fail-closed, never assumed 0%).*

*The verdicts above are computed from the RAW record only; the cash-adjusted figures never change a read.*

## Not reporting

- **book: damped_offense_t298** — no data this period (investigate; a stream that stops reporting is itself a finding).

## Notes

- FIRST PRODUCTION RENDER. The generator was built 2026-07-28 (T-329) and extended through v1.3, but had NO production caller — the committed digest sat frozen at 2026-07-28 for a month. Wiring it into the Friday pulse + registering it as a census clock is the accompanying task; this render is the first-artifact proof it works on today's real inputs.
- The `llm analyst shadow book` shows book 1.000 vs twin 1.024 because it sat 100% CASH: the daily/v2 prompt told the analyst its actions were never executed and it complied (0 actions in 19 notes). daily/v3 opened that channel on 2026-08-18, so this row is a record of the OLD prompt cohort — a fair read of v3 starts from its own forward window.
- `book: damped_offense_t298` is not reporting a NAV pair yet and is listed under Not reporting rather than dropped.
- Deltas are computed from each book's own NORMALIZED growth ratio, never raw dollar NAVs — the books run different notionals (sleeve_tier_50k is $50k book vs a $10k twin), so differencing raw NAVs would print a spectacular and entirely false number.
