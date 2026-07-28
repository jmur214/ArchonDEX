# T-328 — FOUR LIVE BOOKS: the t=0 spec + FROZEN gates (report-only)

**Date:** 2026-07-28 · **Agent:** C · Branch `feature/live-books-t328` · **0 N_trials** (infra)
The performance laboratory fills out. Per the user directive (*"as much live performance testing as possible"*), **performance testing scales through BOOKS, not accounts** — one parameterized `LiveBook` + a `BookSpec` per stream, so a new book is a config, not a module. **All report-only, zero order effect, zero new deps.**

## The universal caveat — printed with every line, by design
> **A book proves LIVE BEHAVIOR. It cannot make a straddling backtest significant on any short horizon.**
`days_accrued` is displayed on every summary line and `status()` returns a literal
`"NOT EVALUABLE — N clean days accrued; no book promotes anything on its own."`
That string exists so a 20-day record can never be quoted as a verdict — the failure mode these books would otherwise invite.

## Shared mechanics
Every book holds **SHARES + CASH** from a starting notional — *not* abstract weights — because whole-share rounding is precisely the effect book 4 exists to measure, and a weight-space book would silently hide it. Costs **1.5 bps/side** (liquid-ETF, the T-255 rate). The book-vs-twin comparison is **growth-vs-growth, never raw dollars**, because the tier book's twin deliberately starts at a *different* notional. **Fail-closed:** a missing price *or* an unavailable strategy stance **parks the day** (`degraded=true`, excluded from `days_accrued`) — never a fabricated mark or exposure.

---

## 1. `spy_null` — the explicit dollar-denominated null
Plain buy-hold SPY; **twin = itself** (excess ≡ 0 by construction).
- **Gate:** *NONE — this book IS the null.* It is never promoted or refuted; it exists so every other stream's *"vs just buying SPY"* is a **first-class measured row** in the digest rather than an implied comparison.
- **CAN evidence:** the realized dollar path of buy-hold SPY over the accrual window.
- **CANNOT evidence:** anything about any other stream — it is the yardstick, not a contender.

## 2. `damped_offense_t298` — the straddling config gets its only possible evidence
The T-298 asymmetric-damping config. Twin = SPY.
- **FROZEN gate (T-298 carried forward):** Δwealth vs SPY must be **positive at block-bootstrap CI** over the accrual **AND** realized MaxDD must stay within the backtest's **−30.6%** bound. Neither is evaluable until the record is long enough to bootstrap.
- **CAN evidence:** that the damped config **runs** live at measured slippage; its realized exposure path (~1.1× mean), turnover, and drawdown behavior.
- **CANNOT evidence:** a revival of the straddling backtest edge on a short horizon. **T-298's Δwealth CI straddled at depth; only a long forward record can move that, and this book cannot shorten the wait.** It is the *only* instrument that can ever revive or bury the config — which is exactly why it must not be over-read early.

## 3. `quality_satellite` — the one premium that never decayed
80/20 SPY/QUAL (the gentle, CI-straddling tilt from T-320). Twin = SPY.
- **FROZEN gate (T-320 carried forward):** log-wealth ratio vs SPY must exceed zero at **block-bootstrap CI**.
- **CAN evidence:** realized tracking behavior, turnover and regret path of the gentlest tilt (T-320 regret −4.1%, **$414 per $10k**) in live conditions.
- **CANNOT evidence:** that the quality premium is **significant**. **T-320's CI straddled zero over 63 YEARS — no live window of months can settle it.**

## 4. `sleeve_tier_50k` — capital-adaptive behavior, measured instead of assumed
The validated sleeve at **$50K** notional; **twin = the SAME sleeve at $10K**. Both sides in **whole shares** — *the divergence IS the tier lesson.*
- **Gate:** no promotion gate — this is a **measurement**. The reported quantity is the **$50K-vs-$10K growth divergence** (whole-share granularity drag), with days-accrued displayed.
- **CAN evidence:** how much realized performance the $10K tier loses to whole-share rounding and rebalance granularity vs the identical sleeve at $50K — the capital-adaptive lesson, **measured live instead of assumed**.
- **CANNOT evidence:** which tier is "better" *as a strategy* — **the strategy is identical by construction; only the granularity differs.**

---

## Wiring + durability
All four run in the Account-1 pulse after the thesis books. Prices fetched once for the union of book symbols; the sleeve/offense **stances are taken from this run's own `plan.signals`** (never re-derived — a second derivation could disagree with what the account actually did). All four state files added to `DURABLE_PATHS`: each compounds a NAV across sessions, so an ephemeral disk would reset every book to its notional daily and no record could ever accrue. Heartbeat: `LIVE-BOOK[<name>] days_accrued=… nav=… twin=… excess_growth=… (NOT EVALUABLE on a short record)`.

**15 unit tests; 91 green across the whole book family** (4 live + 5 shadow + D's desk suites). doc_lint clean.

**T-328: four books armed.**
