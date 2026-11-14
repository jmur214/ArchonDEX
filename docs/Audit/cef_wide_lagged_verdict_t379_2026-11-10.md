# T-379 — CEF discount reversion, wide survivor universe, one-day execution skip: VERDICT

**Date:** 2026-11-10 · **Owner:** director · **N_trials consumed: 2** · exploratory, survivor-only, never deployment evidence.
**Pre-registration:** `prereg_cef_wide_lagged_t379_2026-11-10.md` (commit `9372c75`, before any return was computed).
**Script:** `scripts/cef_wide_lagged_probe_t379.py` (`7d020e2`). **Outputs:** `data/research/t379/result.json`, `result_{SKIP,NO_SKIP}.csv`.
**Independent review by execution:** REPRODUCED WITH FINDINGS — a separate implementation written from the
pre-registration text before the outputs were opened; with the script's three inherited choices switched on it
matches every monthly row to 1e-16. No blocker. The reviewer's scratch work is outside the repo.

## Result

269 usable funds of 276 (median 182 eligible, 34 held, over the regression months 2007-05 → 2026-04).

| arm | window | months | residual alpha %/mo | t_HAC | β universe | strategy CAGR | universe CAGR | SPY CAGR | Sharpe (ci_low) | Sortino (ci_low) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **SKIP (gated)** | FULL | 228 | **+0.285** | **2.97** | 1.21 | 10.9% | 7.3% | 10.7% | 0.74 (0.36) | 0.83 (0.38) |
| **SKIP (gated)** | POST-2011 | 184 | **+0.134** | **1.50** | 1.10 | 10.3% | 8.2% | 14.0% | 0.74 (0.30) | 0.86 (0.33) |
| NO-SKIP (T-267's timing) | FULL | 228 | +0.422 | 3.93 | 1.18 | 12.6% | 7.2% | 10.7% | 0.90 (0.49) | 1.12 (0.55) |
| NO-SKIP (T-267's timing) | POST-2011 | 183 | +0.240 | 2.67 | 1.06 | 11.8% | 8.2% | 13.9% | 0.89 (0.45) | 1.25 (0.55) |

Sharpe / Sortino and their block-bootstrap ci_low are on ALL months of each arm (321 from 2000 for FULL), a
different sample from the alpha's regression months; the reviewer did not reproduce those two ci_lows.
Max drawdown −49.9% (SKIP, 2008).

- **H1 (SKIP FULL t ≥ 2): PASS.** On the reviewer's literal reading +0.270%/mo, t 2.84.
- **H2 (SKIP POST-2011 t ≥ 2): FAIL.** t 1.50 (reviewer 1.31).
- **H3 (85/15 satellite vs SPY, ci_low of Δ annual log wealth > 0): FAIL both windows** (FULL +0.0011,
  ci_low −0.0066; POST-2011 −0.0045, ci_low −0.0107). The CEF universe itself trails SPY by 3.4 pp/yr
  (FULL) and 5.8 pp/yr (POST-2011); a long-only holder pays that deficit to reach the residual.
- **Pre-stated reading that applies:** "real historically, decayed or unresolved post-2011 on survivors; stays parked."

## What the test adds to T-267
1. **A third of T-267's alpha was execution timing.** Entering one day later removes 0.137%/mo (32%) of
   the full-sample alpha and 44% of the post-2011 alpha. T-267's same-close construction used a NAV
   published after the close it traded and a close that may have printed at the bid.
2. **What survives is still a days-horizon reversal** (reviewer, sensitivity): entry at s+2 gives FULL t 2.23
   and POST-2011 t 0.60; at s+3, 1.99 and 0.29; at s+5, 1.39 and −0.19.
3. **It is cost-fragile** (reviewer, sensitivity): turnover is 93% a month; at 30 bps a side FULL t is 1.54
   and POST-2011 is −0.07. The frozen 15 bps is optimistic for the less liquid half of this book.
4. **It is concentrated in 2007–2010:** those 44 months alone give +0.77%/mo; from 2009-07 on, t is 1.94.
5. **Breadth did not rescue the post-2011 question.** The 5-fund portfolio was not the reason T-267's
   post-2011 read was weak: with 34 names held it fails under honest timing.

## Verdict
The discount-reversion effect existed and replicates on a ten-times wider book. For a long-only retail
account after 2011 it is not harvestable: under one-day-honest timing it is not significant, it is gone
by the second day, it does not survive 30 bps a side, and the asset class it lives in trails SPY by more
than the residual. **The CEF thread is CLOSED on free data for the terminal-wealth goal.** T-267's
"first significant alpha in project history" stands as an existence result with this pointer: its
magnitude was inflated by execution timing, and no deployable form has been found.

The survivorship question T-267 priced (CRSP) would not change this reading: the missing terminated
funds could raise the residual, but the days-horizon decay, the cost fragility and the universe's
deficit to SPY are measured on the funds present.

## Predictions scored (as pre-registered)
NO-SKIP FULL t ≥ 2 (70%): yes. SKIP alpha at least one third smaller (65%): 32.4% on the script's
inherited rounding, 33.9% on the reviewer's — a coin-flip, scored as a miss. H1 passes (45%): yes.
H2 passes (20%): no.

## Data facts worth keeping
- yfinance `X<TKR>X` NAV stamped D is D's NAV (peak correlation with same-day SPY in every era; none
  forward-dated). The archived CEFConnect panel stamps the FETCH date: its NAV is the prior business day's.
- Seven funds (AWP, IAF, NCV, NCZ, MGF, MIN, BKT) carry a reverse-split basis mismatch between price and
  NAV for most of their history; yfinance left DHY and IGR un-back-adjusted on 2026-01-02 (+974%, +198%
  phantom returns, caught by the frozen data-error rule). Any future use of this panel needs a per-fund
  basis check, not a range filter.
- CEFConnect has refused automated requests since 2026-10-20 (a block page, not an error). The T-334
  forward panel ended 2026-10-19 with 52 days. It was not worked around.

## Deviations from the pre-registration text (neither changes a verdict)
The 63-day dollar-volume median accepts 31 observations (zero eligible fund-months affected); the
quintile count is T-267's `max(2, round(0.2·n))`. The NO-SKIP arm carries one partial-month row
(2026-10-30 entry) outside every regression. The control series end 2026-05-22, so six months of
available CEF returns are outside every hypothesis statistic.
