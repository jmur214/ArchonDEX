# PRE-REGISTRATION T-379 — CEF discount reversion on the WIDE survivor universe with a one-day execution skip

**Date frozen:** 2026-11-10 (committed before any return, signal, or portfolio statistic was computed).
**Owner:** director. **Track:** exploratory research, standalone harness, no controller, no live integration.
**N_trials consumed: 2** (the gated config and its no-skip decomposition arm; same family as T-267).
**Substrate:** yfinance daily Close / Adj Close / Volume and `X<TKR>X` NAV tickers. Survivor-only.

## Why this test exists
T-267 (2026-07-02) is the only t_HAC > 2 residual alpha in project history (+0.43%/mo, t 2.31, 25 funds,
cheapest quintile = 5 funds). Two things about it were never tested:
1. **Execution timing.** T-267 formed the signal from the month-end close and the month-end NAV and
   measured the return from that same close. The NAV for day s is published after the close of s, and a
   close that printed at the bid makes a fund look cheap and bounce on s+1. Both inflate a monthly
   reversal alpha. Neither was controlled.
2. **Breadth.** A 5-fund portfolio is a weak instrument for the post-2011 question (t 0.90,
   "inconclusive"). The same NAV-ticker path covers 276 of the 361 funds in the archived CEFConnect
   roster (133 with history before 2005).

Data validation done BEFORE this freeze (the only computation performed): yfinance NAV on date D equals
the archived CEFConnect NAV stamped D+1 within 0.05% for 95.5% of 14,352 same-fund pairs (2026-08-06 →
2026-10-19). The archive stamps the fetch date; the NAV is the prior business day's. No price return,
discount z-score, or portfolio number has been computed on the wide universe.

## Frozen construction (identical to T-267 unless stated)
- **Roster:** the 361 tickers in `cef_daily.parquet` (CEFConnect archive, last snapshot 2026-10-19) that
  return a non-empty `X<TKR>X` history. Survivor-only: the central caveat.
- **Signal (unchanged):** at each month-end trading day s, discount = raw Close(s) / NAV(s) − 1;
  z = (discount − own trailing 12-month-end mean) / own trailing 12-month-end std, min 12 observations.
- **Eligibility at s (new, point-in-time):** z defined; trailing-63-day median dollar volume ≥ $500,000;
  NAV changed at least once in the last 5 trading days (not stale); discount within [−60%, +100%]
  (outside = data error, fund skipped that month).
- **Portfolio (unchanged):** long the cheapest 20% by z, equal weight, min 10 eligible names, monthly.
- **Execution — the gated arm (SKIP):** enter at the close of s+1 (the next trading day), exit at the
  close of s'+1 where s' is the next month-end. Return = Adj Close ratio between those closes.
- **Decomposition arm (NO-SKIP, reported, not gated):** enter at the close of s, as T-267 did.
- **Cost:** 15 bps per side on turnover (T-267 used 10; the wide universe is less liquid).
- **Data-error rule (frozen):** a fund-month whose holding-period return is > +100% or < −70% while its
  NAV moved less than 25% over the same dates is dropped from that month's portfolio and universe.
- **Controls:** SPY TR and HYG−LQD TR from `data/processed/tr_reconciled/` over the SAME entry/exit dates;
  the CEF-universe return = equal-weight mean of all eligible funds over the same dates.
- **Statistic:** OLS of portfolio excess-of-nothing monthly return on [SPY, credit, CEF-universe],
  Newey-West 6 lags (T-267's function, unchanged). Windows: FULL (all months with a regression sample)
  and POST-2011 (entry ≥ 2011-01-01).

## Hypotheses and thresholds (SKIP arm only)
- **H1 existence, timing-robust:** FULL residual alpha t_HAC ≥ 2.0 with alpha > 0.
- **H2 persistence:** POST-2011 residual alpha t_HAC ≥ 2.0 with alpha > 0.
- **H3 wealth satellite (reported with its bias named; NOT deployment evidence):** 85% SPY + 15% CEF
  quintile, rebalanced monthly, versus 100% SPY: paired block-bootstrap (block 6 months, 2,000 draws,
  seed 0) ci_low of the difference in annualized log wealth > 0, FULL and POST-2011. The LEVEL of a
  survivor-only CEF return is biased upward; only H1/H2 are bias-conservative.
- Sharpe and Sortino of the quintile are reported with block-bootstrap ci_low per `[NN-SHARPE-CI]`.

## Pre-stated readings
- H1 fails on SKIP while NO-SKIP clears t ≥ 2 → T-267's 2.31 is attributed to execution timing
  (same-close NAV and bid-ask bounce). The CEF thread closes on free data; the T-267 "first significant
  alpha" line is demoted with a pointer here.
- H1 passes, H2 fails → real historically, decayed or unresolved post-2011 on survivors; stays parked.
- H1 and H2 pass → the alpha survives honest timing on a 10× wider book. Next steps (each its own
  proposal, none automatic): a forward shadow book rebuilt on NAV tickers (the CEFConnect feed has been
  bot-blocked since 2026-10-20), and a survivorship-complete check before any satellite proposal.
- **Predictions, recorded to be scored:** NO-SKIP FULL t ≥ 2 (replicates T-267 on the wide book, 70%);
  SKIP FULL alpha is at least one third smaller than NO-SKIP (65%); H1 passes (45%); H2 passes (20%).

## MBL / honest N
`[NN-MBL]`: at N_eff ≈ 37 a ~19-year regression window (HYG/LQD begin 2007) needs SR ≈ 0.5 to have any
chance; this is an EXPLORATORY measurement whatever it shows and cannot be quoted as deployment evidence.
The smoke covers the FIRST twelve signal months only and prints counts, never returns.
