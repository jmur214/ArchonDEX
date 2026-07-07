---
task_id: T-2026-07-06-283c
title: Accumulation race on D's canonical T-284 curves + drift reconciliation
date: 2026-07-06
worker: Agent B
branch: feature/accumulation-model-t283c
status: DONE — 0 new N_trials. Verdict preserved; the T-283b→T-284 drift is ENTIRELY dividends.
---

> ⚠️ **SUPERSEDED (T-287, 2026-07-07):** this doc's reconciliation was DIRECTIONALLY BACKWARDS.
> It blamed D's curves for being "price-only"; the truth is the OPPOSITE — D's curves are
> total-return, and MY T-283/283b runs DOUBLE-COUNTED dividends. D's canonical numbers here
> (buy-hold $929K, gated primary $1.12M, ×1.20) are CORRECT and are the surviving table; the
> "add dividends back ~1.5-1.7×" recommendation is WRONG (retracted). See
> `docs/Audit/dividend_reconcile_verdict_t287_2026_07_07.md`.

# T-283c — accumulation on D's canonical T-284 curves (one construction) + reconcile

Swapped my T-283b self-built gated-leverage construction for D's canonical,
basis-checked curves (`data/research/t284/daily_curves.parquet`: primary /
secondary / t282_arm / plain / bh_spy / bh_2x). Same $7K/yr annual DCA race.

## Result — $7K/yr DCA, 2000-2026 (~25yr), D's curves
| config | terminal | × contrib | worst $ DD | % underwater |
|---|---|---|---|---|
| naked 2× SPY (D, no gate) | $1,962,286 | 10.78× | −$613,170 | 34.9% |
| **GATED 2× 100% SPY (D primary)** | **$1,118,057** | 6.14× | −$232,440 | 23.8% |
| buy-hold SPY (D) | $929,498 | 5.11× | −$157,610 | 21.4% |
| **GATED 2× 3-leg all (D secondary, EXPL)** | **$759,654** | 4.17× | **−$51,672** | 7.4% |
| 60_40 (context) | $712,769 | 3.77× | −$96,201 | 10.7% |
| GATED 2× sleeve (T-282, 1-leg) | $580,526 | 3.19× | −$32,593 | 8.9% |
| plain ensemble sleeve | $441,150 | 2.42× | −$15,063 | 4.0% |

**Start-date sensitivity:** D-primary wins vs buy-hold at EVERY start (2000 → 6.14×
vs 5.11×; 2012 → 3.86× vs 3.16×).

## Drift reconciliation — it is ENTIRELY dividends (not "little", but fully explained)
The task expected small drift; it was large (buy-hold −36%, primary −42% vs T-283b).
**Cause: dividends.** D's curves are PRICE-ONLY; T-283/T-283b added +1.8%/yr SPY
dividends (2× in the levered arm). The arithmetic is exact:
- buy-hold: $1,457,567 (T-283b) / $929,498 (D) = **1.568 ≈ 1.018^25 = 1.562** — 25
  years of 1.8%/yr dividends.
- primary: $1,940,602 / $1,118,057 = **1.736 ≈ ~2× the dividend factor** (the 2×
  LETF earns 2× the total return, incl. 2× dividends).
- t282_arm −13%, plain −15% (less SPY exposure → smaller dividend gap). All
  consistent with the dividend explanation; no other drift.

**The RELATIVE verdict is preserved in both constructions:** gated 2× 100% SPY
BEATS buy-hold (D ×1.20 price-only; T-283b ×1.33 dividend-inclusive), wins at every
start, and the gate keeps 2× survivable (worst DD −$232K vs the NAKED 2×'s −$613K).

**⚠ Flag for D / the advisor (materiality):** citing D's price-only curves
UNDERSTATES every config's real terminal wealth by ~1.5–1.7× (a real Roth investor
earns dividends and reinvests them). For USER-FACING wealth figures the
dividend-inclusive numbers are correct (buy-hold ~$1.46M, primary ~$1.94M); D's
curves are the right CONSTRUCTION for the basis-checked relative/leverage verdict.
Recommend the advisor scales D's absolute wealth up for dividends, or D adds the
dividend to the SPY leg of the canonical curves.

## The SECONDARY is the risk-adjusted sweet spot (EXPLORATORY)
D's SECONDARY = the WHOLE 3-asset sleeve levered 2× (SPY+BOND+GOLD all-2×-when-on)
— NOT T-282's single-leg "diluted" arm. It captures **$760K terminal at only −$52K
worst drawdown / 7.4% underwater** — a far better wealth-per-drawdown than buy-hold
($929K / −$158K) or the primary ($1.12M / −$232K). Levering the DIVERSIFIED sleeve
(rather than concentrating in 100% SPY) preserves the diversification at 2×, giving
a much smoother contributing path while still ~2× the plain sleeve's wealth.
**EXPLORATORY:** its bond/gold 2× synthetics are un-basis-checked (only the
SPY/SSO leg was validated vs real SSO); a real 2× bond/gold ETF path could differ.

## The advisor's accumulation column (reconciled, D's construction)
| investor | max config | terminal (D, +div in parens) | worst $DD |
|---|---|---|---|
| won't-sell, **max-wealth**, high risk-tolerance | **GATED 2× 100% SPY (primary)** | $1.12M (~$1.94M w/ div) | −$232K |
| won't-sell, **best risk-adjusted** wealth | **GATED 2× 3-leg (secondary, EXPL)** | $760K (higher w/ div) | **−$52K** |
| won't-sell, moderate | buy-hold SPY | $929K (~$1.46M w/ div) | −$158K |
| would-panic / near-decumulation | plain sleeve | $441K | −$15K |

**T-283c done.** One construction (D's, basis-checked) now cited; the T-283b drift
is fully reconciled as the dividend treatment (relative verdict unchanged); the
secondary added as the risk-adjusted sweet spot (EXPLORATORY). Measurement only.
