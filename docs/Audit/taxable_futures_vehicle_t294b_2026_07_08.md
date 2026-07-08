---
task_id: T-2026-07-08-294b
title: Taxable-margin vehicle — does gated-2× via micro futures beat Roth-SSO AFTER TAX?
date: 2026-07-08
author: Agent D (fair-harness lane)
type: PRE-REGISTERED after-tax arm (N_trials += 1)
status: DONE — FAILS the frozen gate at BOTH brackets. §1256's annual mark-to-market exactly consumes the vehicle+slippage advantage; deferral beats the 60/40 rate. Branch feature/taxable-futures-vehicle-t294b
---

# T-294b — the taxable-futures arm

**User directive (scoped):** a strategy may live in the Roth OR a taxable brokerage with margin; if the taxable
implementation wins after tax, it wins the row. T-294's "no **Roth** vehicle recovers the +0.86%/yr" stands, but
V4 (ideal futures) is **not hypothetical in the taxable column** — micro E-mini (MES) futures implement it.

## Sequencing note (binding)
The dispatch says use the better-turnover config **"if T-297 passes."** **T-297 did NOT pass** — both damped arms
failed the frozen crash-exit gate (Arm1 225d, Arm2 34d). Therefore this arm uses the **undamped T-284 PRIMARY
exposure path** (`e2 = min(2·ensemble_frac, 2)`), the same path as the Roth-SSO benchmark. Also: this runs on the
**corrected full SPY trading calendar** (T-297 found T-294's index was holed by the bond synth; no bond series
enters here, so the calendar is clean by construction).

## ⚠️ The mechanism that decides this (stated before running)
**§1256 futures are marked-to-market EVERY year** — tax is paid annually on unrealized gains, regardless of
turnover. **Both benchmarks defer:** the Roth pays **zero, ever**; taxable buy-and-hold SPY pays only dividend tax
until a sale, and the user's recorded directive is that they **will not sell** (step-up at death). So §1256's
60/40 blended rate must beat not just "ordinary income" but **deferral itself**. That is the real race, and the
honest prior should reflect it.

## The arm (FROZEN): gated 2× SPY via MES futures, in a taxable account
Collateral = 100% of NAV in T-bills (earning `rf`, taxed annually as ordinary income). Exposure `e` obtained via
futures notional; **notional is reset only when the gate changes** → no daily reset, so LETF chop-decay is avoided
by construction.
```
pnl_t      = notional · (spy_gross − rf − FUT_SPREAD/252)   # futures excess return; basis financing ≈ rf+30bps
interest_t = nav · rf                                        # collateral, ordinary income
frictions  = roll (8 bps/yr of notional, 4 quarterly rolls @2bps)
           + 0.5 bps per side on |Δnotional| (MES: ~0.25 index-pt spread = $1.25 on $36,045 ≈ 0.35bp,
             + ~$1.24 round-turn commission ≈ 0.35bp → ~1bp round-trip; MES is TIGHTER than SSO's ≥5bps)
```
**Tax (T-191 machinery):** at each calendar year end, the year's **futures P&L** is marked and taxed at the
**§1256 blended rate** `0.60·LT + 0.40·ST`, with losses carried forward. Collateral interest taxed at the ST rate.
Two brackets reported so bracket-sensitivity is visible:
- **Base:** ST 24% / LT 15% → blended **18.6%**; qualified dividends 15%.
- **High:** ST 37% / LT 20% → blended **26.8%**; qualified dividends 20%. _(NIIT 3.8% not added; noted.)_

**Wash-sale:** §1256 contracts are **exempt from wash-sale mechanics** — a genuine advantage of this column, stated.
The advisor-spec §9a cross-account guard still applies to the ETF legs elsewhere.

## Benchmarks (same exposure path, same window)
1. **After-tax taxable buy-and-hold SPY** (the advisor §9b bar for this column): SPY's dividend contribution is
   **1.92%/yr** (measured: TR 8.37% vs price 6.45%), taxed annually at the qualified rate → drag **0.29%/yr**
   (base) / **0.38%/yr** (high). **No terminal capital-gains tax** (never-sell + step-up). This makes the bar
   *stronger*, i.e. harder for the arm — the honest choice given the recorded directive.
2. **Roth SSO arm (V1)** — zero tax, on the **0/5/10 bps** slippage grid (E's measured floor is ≥5 bps).
3. **After-tax taxable SSO** (completeness): ETF gains **defer** (never sold); only the SPY-leg dividend and SSO's
   small distribution are taxed annually.

## Tier honesty (capital-adaptive directive) — measured at the current index (S&P 7,209)
MES = **$5 × index = $36,045 notional/contract**. 2× exposure needs notional `2E`, so **exactly 2× requires
E = $18,023** (one contract). Below that the arm **cannot express 2× at all** (one contract on $10k is 3.6×).
Half-contract granularity error, as a fraction of the 2× target:
| equity | contracts for 2× | granularity error |
|---|---|---|
| $10,000 | 0.55 | **90% of target — not implementable** |
| $15,000 | 0.83 | 60% |
| $25,000 | 1.39 | 36% |
| $50,000 | 2.77 | 18% |
| $100,000 | 5.55 | 9% |
The backtest models **continuous exposure**; granularity is a separate deployment constraint. The row is
**tier-gated** and I will state the minimum tier at which it is real.

## Gate (FROZEN)
The taxable-futures arm earns the offense row (at its minimum tier) **iff its after-tax terminal wealth beats
BOTH (a) after-tax taxable buy-and-hold SPY AND (b) the Roth-SSO arm at the 5 bps grid point.** Reported at both
brackets; a win must hold at the **base** bracket at minimum, with the high bracket shown.

## Honest prior — LOW-MEDIUM (~25-35%), below the dispatch's 40-50%
The arm recovers the vehicle gap (+0.86%/yr decay/ER/financing) and most of the slippage (MES ~1bp round-trip vs
SSO's ≥5bps ⇒ ~0.7%/yr saved) — call it **~1.5%/yr of pretax advantage**. But it pays **18.6-26.8% on ALL gains,
every year**, against two benchmarks that pay **~0.3%/yr (buy-hold SPY) and zero (Roth)**. On a ~8.8% pretax CAGR
that annual mark-to-market costs roughly **1.6-2.4%/yr** of compounding. **The tax drag plausibly exceeds the
vehicle advantage** — deferral, not the blended rate, is the thing §1256 fails to beat. Running it settles the
magnitude. N_trials += 1.

---
## RESULTS (2000-08-30 → 2026-04-17, corrected full SPY calendar; undamped T-284 path)

### Pretax, the futures arm is the best vehicle in the entire program
**$10k → $99,845, CAGR 9.39%** — it recovers the vehicle gap *and* the slippage. Against Roth-SSO @0bps (8.37%)
that is **+1.02%/yr** (≈ T-294's +0.86%/yr vehicle gap, on the clean calendar); against Roth-SSO @5bps (7.58%) it
is **+1.81%/yr**. The MES frictions are genuinely small (roll 8bps/yr, ~1bp round-trip vs SSO's ≥5bps). **Then the
tax lands.**

### Base bracket — §1256 blended 18.6%, qualified dividends 15%
| strategy | $10k→ | CAGR | Sortino | MaxDD |
|---|---|---|---|---|
| TAXABLE futures 2× (§1256 annual MTM) | 65,102 | 7.58% | 0.557 | −42.6% |
| **after-tax taxable buy-hold SPY (the bar)** | **68,843** | **7.82%** | 0.618 | −55.4% |
| Roth SSO @0bps | 78,534 | 8.37% | 0.587 | −43.5% |
| Roth SSO @5bps (E's floor) | 65,088 | 7.58% | 0.544 | −45.3% |
| Roth SSO @10bps | 53,940 | 6.80% | 0.500 | −48.5% |
| taxable SSO @5bps (deferred gains) | 63,507 | 7.48% | 0.538 | −45.7% |

**Gate: beats after-tax BH-SPY? NO** ($65,102 vs $68,843). Beats Roth-SSO @5bps? Technically yes — **by $14** on
$10k over 25.6 years. A dead heat. → **does NOT earn the row.**

Tax drag: pretax 9.39% → after-tax **7.58%** = **−1.81%/yr**. The §1256 mark-to-market consumes the arm's entire
**+1.81%/yr** pretax advantage, to the basis point. That coincidence is the whole story.

### High bracket — §1256 blended 26.8%, qualified dividends 20%
| strategy | $10k→ | CAGR |
|---|---|---|
| TAXABLE futures 2× | **53,158** | 6.74% |
| after-tax taxable buy-hold SPY | 67,174 | 7.71% |
| Roth SSO @5bps | 65,088 | 7.58% |

Tax drag **−2.66%/yr**. **Gate: NO on both.** → does NOT earn the row.

### Tier honesty (recorded even though the arm fails)
MES = $5 × index = **$36,045/contract** (S&P 7,209). Exactly 2× needs **E = $18,023** (one contract); **below that
the arm cannot express 2× at all** (one contract on $10k is 3.6× leverage). Half-contract granularity error as a
fraction of the 2× target: **$10k → 90% (not implementable)**, $15k → 60%, $25k → 36%, $50k → 18%, $100k → 9%.
Even on a passing verdict this row would be **tier-gated to ≈$100k+** for a clean 2× expression. §1256 contracts
are **exempt from wash-sale mechanics** — a real advantage of this column, but it does not rescue the arm.

## VERDICT — the taxable-margin column does NOT rescue the offense config
**§1256's 60/40 blended rate softens taxes versus ordinary income — but the thing it must beat is DEFERRAL, and it
cannot.** The Roth pays zero forever; taxable buy-and-hold SPY pays only 0.29%/yr of dividend tax and defers the
rest (never-sell + step-up). The futures arm pays 18.6-26.8% on **all gains, every year**. Its ~+1.8%/yr pretax
vehicle+slippage advantage is exactly consumed at the base bracket (−1.81%/yr) and buried at the high one
(−2.66%/yr). This confirms the pre-registered mechanism, and my LOW-MEDIUM prior (25-35%) over the dispatch's
40-50%.

### The bigger picture this completes (worth stating plainly)
Add the **Roth buy-and-hold SPY** reference from T-297's clean calendar — **$74,104 / 8.13%, zero tax** (not a
pre-registered benchmark here; the north-star bar):

| implementable config | $10k→ |
|---|---|
| **Roth buy-and-hold SPY** | **74,104** |
| after-tax taxable buy-hold SPY | 68,843 |
| taxable futures 2× (base bracket) | 65,102 |
| Roth SSO 2× @5bps | 65,088 |
| taxable SSO 2× @5bps | 63,507 |

**No implementable gated-2× offense configuration beats simply buying and holding SPY in the Roth**, once E's
measured slippage and honest taxes are charged. The only thing that does is the *pretax* futures arm ($99,845) —
and pretax is not a place one can invest. Combined with **T-294** (no Roth vehicle recovers the decay) and
**T-297** (turnover reduction beats SPY but fails the crash-exit gate), the honest standing of the offense program
is that **its edge is currently consumed by execution and taxes**.

**The one live lever remains T-298 asymmetric damping** (damp re-entry, never damp de-risking → exit-lag ≡ 0 by
construction). T-297 showed damping recovers far more than the slippage it saves; if a variant can capture that
*without* delaying the crash exit, it is the only identified path back to a defensible offense row. Recommend it
be pre-registered next.

N_trials += 1 (one arm; two brackets are sensitivity lines, not separate trials). Reproducible:
`scripts/taxable_futures_vehicle_t294b.py`.
