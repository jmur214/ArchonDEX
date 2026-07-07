---
task_id: T-2026-07-06-283b
title: Accumulation race + trend-gated leverage — does the gated 2× config beat buy-hold's $1.45M?
date: 2026-07-06
worker: Agent B
branch: feature/accumulation-model-t283b
status: DONE — 0 new N_trials (re-analysis of the T-282-validated leverage arms under the $7K/yr contribution schedule).
---

> ⚠️ **SUPERSEDED (T-287, 2026-07-07):** the dollar figures below DOUBLE-COUNTED dividends
> (added +1.8%/yr, 2× in the levered arm, on already-total-return inputs). Gated 2× 100% SPY
> ~$1.94M → **corrected $1.12M**; buy-hold ~$1.46M → **$929K**. The **relative verdict is
> unchanged**: gated 2× 100% SPY BEATS buy-hold — **×1.20 (corrected TR)**, every start; the
> diluted arm still loses. Canonical: `docs/Audit/dividend_reconcile_verdict_t287_2026_07_07.md`.

# T-283b — accumulation race + trend-gated leverage

Extends the T-283 accumulation model with D/T-282's VALIDATED trend-gated-leverage
arms. Reuses the T-283 machinery ($7K/yr DCA, SPY TR + 1.8% div) + T-282's
SSO-synthetic (2× SPY TR − borrow[cash+0.60%] − SSO_ER 0.89%) and ensemble trend
[42,105,210]. Dividends added CONSISTENTLY (2× in the SSO portion) so the levered
arms compare apples-to-apples vs the div-inclusive buy-hold (T-282 itself was
price-only — this is the honest, slightly more favorable-to-leverage version).

## Result — $7K/yr DCA, 2000-2026 (~26yr, ~$182K contributed)
| config | terminal wealth | × contributions | worst $ drawdown | % underwater |
|---|---|---|---|---|
| **GATED 2× — 100% SPY** | **$1,940,602** | **10.27×** | **−$320,061** | 15.9% |
| SPY buy-hold TR (the bar) | $1,457,567 | 7.71× | −$224,596 | 14.9% |
| 60_40 | $712,769 | 3.77× | −$96,201 | 10.7% |
| GATED 2× sleeve (T-282, diluted) | $667,833 | 3.67× | −$35,450 | 8.7% |
| schwab_like | $564,741 | 3.10× | −$59,800 | 9.7% |
| trend_sleeve | $519,224 | 2.75× | −$16,067 | 4.5% |

**Start-date sensitivity (terminal × contributions):** GATED-2×-100%SPY wins at
EVERY start — 2000 → 10.27× (vs BH 7.71×), 2003 → 9.37×, 2006 → 8.13×, 2009 →
6.92×, 2012 → 5.21× (vs BH 3.79×). The verdict does not hinge on start timing.

## The answers
1. **Does the GATED levered config beat buy-hold's $1.45M? — YES, but ONLY the
   UNDILUTED (100% SPY) version.** Gated 2× on 100% SPY → **$1.94M, ×1.33 the
   buy-hold bar.** The GATE is what makes 2× survivable: the trend rule exits to
   cash before the deep crashes, so the worst contributing-path drawdown is
   **−$320K** (a ~30% paper loss), not the −70/−80% a NAKED daily-2× SPY would
   inflict. That is the price of the extra ~$480K.
2. **The DILUTED 3-asset arm (SPY leg 2×, BOND/GOLD 1×) does NOT beat buy-hold —
   it reaches only $668K**, below even 60_40. The bond/gold diversification +
   the sleeve's cash-sitting DILUTE the leverage's wealth kick. This confirms
   D/T-282's headline ("the diluted arm doesn't reach buy-hold SPY") and extends
   it to the accumulation frame: **diversification is the enemy of terminal wealth
   for a won't-sell accumulator; the leverage only pays when concentrated in the
   high-return asset.**
3. **The path cost is real:** worst contributing-path drawdown −$320K (100% SPY 2×)
   vs −$225K (buy-hold) vs −$16K (plain sleeve). For a genuinely won't-sell 40yr
   accumulator this is a paper loss ridden to $1.94M; for anyone who might panic
   it is a wealth-destroying bailout point.

## The advisor's accumulation column (updated)
| investor | max-wealth config | why |
|---|---|---|
| contributing, 40yr, **genuinely won't-sell, high risk-tolerance** | **GATED 2× 100% SPY** | $1.94M (1.33× buy-hold); the gate makes the 2× survivable (−$320K worst DD vs naked-2× ruin) |
| contributing, 40yr, won't-sell, moderate | buy-hold SPY TR | $1.46M; no leverage financing/decay risk, shallower −$225K DD |
| contributing, would-panic-sell OR near decumulation | trend sleeve | the −$16K DD is the behavioral hedge — worth ~$1.4M of forgone wealth ONLY if it prevents a bottom-sale |

## Honest caveats
- **Leverage costs are in** (SSO_ER 0.89% + 0.60% financing spread); the 2× gross
  return + the gate overcome them, but they are a real ~1.5%/yr drag on the levered
  portion. **Daily-2× volatility decay** is real in chop — T-282 basis-checked the
  synthetic vs REAL SSO (small tracking error), so the synthetic is honest, but the
  decay is why the diluted/lower-conviction arm underperforms.
- **26yr window** (fair data), a conservative proxy for 40yr — more compounding
  years only WIDEN the concentrated-leverage edge (and deepen the dollar DD).
- **N_trials:** 0 new — this re-analyzes T-282's validated leverage construction. D/T-284's
  formal full-equity validation is the system of record; if its exact arm specs
  differ, swap them in — the accumulation machinery is ready.

Measurement only; nothing enabled. This directly answers the user's "does gated
leverage beat $1.45M" question: **yes, concentrated + gated, at the cost of a
−$320K path you must not sell into.**
