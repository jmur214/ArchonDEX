---
task_id: T-2026-07-07-287
title: Dividend double-count reconciliation — the CORRECTED CANONICAL accumulation table
date: 2026-07-07
worker: Agent B
branch: feature/dividend-reconcile-t287
status: DONE — double-count CONFIRMED; T-283/283b/283c dollar figures RETRACTED; corrected canonical issued. Relative verdict survives.
---

# T-287 — dividend reconciliation: I double-counted; D was right

D/T-286 verified the canonical curves are already TOTAL-RETURN. That contradicted
my T-283c premise ("D's curves are price-only; I added +1.8%/yr dividends"). The
audit settles it against me — cleanly, caught before any decision consumed it.

## The evidence (my own inputs audited)
1. **`data/processed/SPY_1d.csv` is TOTAL-RETURN.** 2005-01-03 close = **81.38** =
   the TR-adjusted value (≈81.4), NOT the raw price (≈120.3). Bare price-series
   CAGR over the window = **8.44%** — the TR range, not price-only (~5.5%).
2. **My pipeline added a spurious dividend uplift** on top of that already-TR
   series, at FIVE sites:
   - `accumulation_model_t283.py:67` `_spy_tr_ret = SPY.pct_change() + DIV_D`
   - `:79` sleeve SPY leg `ar = ar + DIV_D`  ·  `:92` robo SPY leg `(a + DIV_D)`
   - `accumulation_model_t283b.py:49` `SSO_SYN = 2*(_aret + DIV_D) − …` (2× the spurious div)
   - `:71` sleeve SPY leg `aret = aret + DIV_D`
3. **D's `bh_spy` CAGR = 7.61%** (clean TR from the same processed series, no manual
   div) — the correct baseline.

**The 1.568 = 1.018^25 identity was direction-blind, as D noted. The direction is:
I ADDED a second dividend (double count), NOT D missing one.** My published figures
were inflated ~1.57× (buy-hold, 1× SPY) / ~1.74× (the 2× arm, which double-counted
2× the dividend).

## RETRACTION
The following T-283 / T-283b / T-283c figures are **WRONG (double-counted) and are
retracted**: buy-hold ~$1.45–1.46M, gated 2× 100% SPY ~$1.94M, and every
dividend-inflated dollar figure in those docs. The T-283c "reconciliation" that
blamed D's curves for missing dividends was **directionally backwards** and is
superseded by this document.

## THE CORRECTED CANONICAL TABLE (all TOTAL-RETURN, no double-count)
$7K/yr annual DCA, 2000-2026 (~25yr). D's TR curves + cleanly-recomputed (no-div)
robos:
| config | terminal | × contrib | worst $ DD |
|---|---|---|---|
| naked 2× SPY (no gate) | $1,962,286 | 10.78× | −$613,170 |
| **GATED 2× 100% SPY (primary)** | **$1,118,057** | 6.14× | −$232,440 |
| buy-hold SPY TR | $929,498 | 5.11× | −$157,610 |
| **GATED 2× 3-leg all (secondary, EXPL)** | **$759,654** | 4.17× | **−$51,672** |
| 60_40 | $594,554 | 3.15× | −$86,042 |
| GATED 2× sleeve (T-282, 1-leg) | $580,526 | 3.19× | −$32,593 |
| schwab_like | $494,701 | 2.72× | −$55,604 |
| plain ensemble sleeve | $441,150 | 2.42× | −$15,063 |

## THE RELATIVE VERDICT SURVIVES THE CORRECTION
- **Gated 2× 100% SPY beats buy-hold: $1.12M vs $929K = ×1.20, at EVERY staggered
  start** (2000→6.14× vs 5.11×; 2012→3.86× vs 3.16×). Confirmed programmatically.
- The gate keeps 2× survivable (worst DD −$232K vs the naked-2×'s −$613K).
- The SECONDARY (3-leg all-2×) remains the risk-adjusted sweet spot: $760K at only
  −$52K worst DD (EXPLORATORY — bond/gold 2× synthetics un-basis-checked).
- **The double-count inflated ABSOLUTE wealth but never changed the RANKING or the
  verdict** — every prior qualitative conclusion (gated > buy-hold > robos > sleeve
  on wealth; sleeve smoothest; secondary best risk-adjusted) holds on the corrected
  TR numbers.

## Corrected advisor accumulation column (canonical, TR)
| investor | config | terminal (TR) | worst $DD |
|---|---|---|---|
| won't-sell, max-wealth, high risk | GATED 2× 100% SPY | $1.12M | −$232K |
| won't-sell, best risk-adjusted | GATED 2× 3-leg (secondary, EXPL) | $760K | −$52K |
| won't-sell, moderate | buy-hold SPY TR | $929K | −$158K |
| would-panic / near-decumulation | plain sleeve | $441K | −$15K |

**T-287 done.** ONE canonical table survives (this one, TR-labeled); the
double-counted T-283/283b/283c figures are superseded. The apparatus caught my
error before any decision used it. Corrected canonical:
`data/research/t283/accumulation_CANONICAL_t287.json`.
