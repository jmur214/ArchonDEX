---
task_id: T-2026-07-06-283
title: The 40-year accumulation model — which config maxes terminal wealth for a contributing, won't-sell investor
date: 2026-07-06
worker: Agent B
branch: feature/accumulation-model-t283
status: DONE — 0 new N_trials (re-analysis of validated configs under a contribution schedule). VERDICT: buy-and-hold wins the accumulation race; DCA WIDENS its edge.
---

> ⚠️ **SUPERSEDED (T-287, 2026-07-07):** the dollar figures below DOUBLE-COUNTED dividends
> (added +1.8%/yr on already-total-return processed SPY). Buy-hold ~$1.45M → **corrected $929K**;
> all absolute wealth inflated ~1.57×. The **relative verdict is unchanged** (buy-hold wins the
> accumulation race; DCA widens the equity edge). Canonical TR table:
> `docs/Audit/dividend_reconcile_verdict_t287_2026_07_07.md`.

# T-283 — accumulation model: the advisor's accumulation column

USER PROFILE (recorded): a CONTRIBUTING accumulator — ~$7K/yr Roth for decades,
~40yr horizon, **won't sell in downturns**. Lump-sum backtests miss this: during
accumulation, drawdowns are PURCHASES (DCA buys the dip). Re-analyzed the validated
fair-harness configs under a frozen $7K/yr annual contribution.

Window: 2000-2026 (~26yr, the longest honest fair-harness window — a conservative
proxy for 40yr; a true 40yr only WIDENS the equity edge via more compounding). SPY
TR = price + a frozen 1.8%/yr dividend applied CONSISTENTLY to all SPY exposure.
(D/T-282's trend-gated-2× arm to be added when it lands.)

## Result — $7K/yr DCA, 2000-2026 (~$182K contributed)
| config | terminal wealth | × contributions | worst $ drawdown | % time underwater |
|---|---|---|---|---|
| **SPY buy-hold TR** | **$1,451,589** | **7.68×** | −$223,670 | 16.0% |
| 60_40 | $711,375 | 3.76× | −$96,003 | 12.1% |
| schwab_like | $563,929 | 3.10× | −$59,709 | 10.8% |
| trend_sleeve | $519,094 | 2.75× | **−$16,063** | 5.4% |

**Start-date sensitivity (BH/sleeve terminal ratio):** 2000 → 2.80×, 2003 → 2.77×,
2006 → 2.55×, 2009 → 2.43×, 2012 → 1.95×. **Buy-hold wins by 1.95–2.80× at EVERY
start** — the verdict does not hinge on 2000's crash timing.

**Lump-sum vs DCA:** BH/sleeve = **2.59× lump-sum → 2.80× DCA** ⇒ **accumulation
WIDENS buy-hold's edge.**

## The honest answers
1. **Does buy-and-hold's edge WIDEN or NARROW under accumulation? — WIDEN.** The
   user's hypothesis is confirmed: DCA into the volatile high-return asset amplifies
   its advantage (2.80× vs 2.59× lump-sum). Contributions made during and after
   crashes buy cheap SPY that compounds through the recovery; the sleeve sits in
   cash/bonds in downturns and buys FEWER dip-shares of the asset that recovers.
2. **Does any defensive config win the 40yr contributing race? — NO.** The trend
   sleeve is the WORST on terminal wealth ($519K, 2.75× — below both robos). Defense
   is strictly a decumulation / lump-sum / will-panic-sell tool; for a won't-sell
   accumulator it is pure wealth destruction (~$930K, 2.8×, forgone vs buy-hold).
3. **Sequence-of-returns:** earlier crashes (more recovery + compounding years ahead)
   favor the volatile asset MOST — the 2000-start (2008 at year-8) gives BH 7.68×,
   the 2012-start (no deep crash until 2020/22) only 3.79×. The sleeve's protection
   matters LEAST exactly when a crash is early, which is when the accumulator most
   wants to be all-equity.
4. **The sleeve's only edge is the path** (worst $DD −$16K vs BH −$224K; 5.4% vs 16%
   underwater) — which is **worthless to a WON'T-SELL investor**: the −$224K buy-hold
   drawdown is a paper loss ridden through to $1.45M. The smooth ride buys emotional
   comfort at a cost of ~$930K.

## The advisor's accumulation column
**(contributing, horizon 40yr, won't-sell) → buy-and-hold SPY (the most
equity-heavy config), NOT the defensive sleeve.** The deployed defensive sleeve is
the RIGHT answer for its validated objective (risk-adjusted / tail, decumulation,
behavioral-panic protection) but the WRONG answer for a won't-sell accumulator's
contributions — a max-equity config maxes terminal wealth by ~2.8×.

**Premise dependency (stated honestly):** this rests entirely on "won't sell." If
the investor WOULD panic-sell in a −55% SPY crash, the sleeve's −12% MaxDD prevents
the behavioral disaster (realizing the bottom) and could win via behavior. The
verdict is: *conditional on genuinely never selling*, max equity; the sleeve is the
hedge against one's own future panic, not a wealth-maximizer. Measurement only;
nothing enabled. Directly informs whether the deployed sleeve or a max-wealth config
should receive future contributions.
