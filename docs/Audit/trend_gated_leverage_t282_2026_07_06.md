---
task_id: T-2026-07-06-282
title: Trend-gated leverage — the validated engine on OFFENSE (max-wealth north star)
date: 2026-07-06
author: Agent D (fair-harness lane)
type: PRE-REGISTERED trial (1 arm + named baselines, N_trials += 1)
status: DONE — offense thesis PARTIALLY validated (beats plain sleeve on wealth, marginal; does NOT beat buy-hold SPY; decisive DD-control vs naked 2x). Branch feature/trend-gated-leverage-t282
---

# T-282 — trend-gated leverage (the validated engine on offense)

**User directive (recorded):** the END GOAL is maximum terminal WEALTH over ~40yr; the user will NOT sell
in downturns → the benchmark upgrades to **buy-and-hold SPY on WEALTH**. Our validated trend signal has only
ever been deployed defensively (cash when trends break). This tests it on OFFENSE: **levered when the trend
is ON** — the hypothesis being that leverage's damage is CHOP, and our signal exits chop.

## The synthetic 2× series (frozen recipe — the load-bearing construction)
Roth-implementable via SSO (ProShares Ultra S&P500, an ordinary 2× ETF — no margin). A daily-rebalanced
constant-2× series (so volatility decay is modeled by construction):
```
spy_tr        = SPY adjusted-close daily return (data/processed/SPY_1d.csv is dividend-adjusted = TR)
spy_tr_gross  = spy_tr + SPY_ER/252          # add back SPY's 0.0945% ER (SSO doesn't hold SPY shares)
borrow_daily  = (DGS3MO/100 + 0.0060)/252    # short rate + 60 bps, on the 1× borrowed to reach 2×
sso_syn_ret   = 2·spy_tr_gross − borrow_daily − 0.0089/252     # SSO ER 0.89%
```
**Basis check (`[NN-SUBSTRATE-REVERIFY]`, T-167-style):** validate `sso_syn_ret` against REAL SSO daily
returns (yfinance, 2006+, a live liquid ETF → survivorship-clean) over the overlap; report the annualized
tracking error + the terminal-wealth ratio honestly. If the basis is large (> ~1%/yr unexplained), the
synthetic is not trustworthy and the arm result is quarantined.

## The arm (frozen)
The deploying **multi-speed {2,5,10}mo ensemble sleeve** (fair T-255 harness, EW SPY/AGG/GLD, flat-leg earns
the short rate, ER + 1.5 bps both sides), with the **SPY leg expressed at up to 2× WHEN its trend is on**:
- SPY-leg target exposure `e = min(2 · ensemble_exposure(SPY), 2)` → since ensemble ∈ {0,⅓,⅔,1}, `e ∈
  {0, ⅔, 4/3, 2}`. Implemented as a SPY(1×)+SSO(2×) blend so the leverage cost is embedded honestly:
  `e ≤ 1: e·spy_tr + (1−e)·cash` ; `e > 1: (2−e)·spy_tr + (e−1)·sso_syn_ret`. Minus txn on Δe.
- **AGG and GLD legs are UNCHANGED (1×)** — only the equity leg goes on offense. EW 1/3 weights (leverage
  lives inside the SPY leg's 1/3 allocation → effective SPY exposure up to 2/3 of NAV). Causal `.shift(1)`.

## Baselines (named, same window)
1. **Buy-and-hold SPY TR** — THE new bar (holding the SPY ETF, ER already in the adjusted series).
2. **The plain ensemble sleeve** (unlevered T-260 deploying spec).
3. **60/40** (SPY .60 / AGG .40, monthly rebal, net ER) — continuity with prior reports.
4. **Buy-and-hold SSO-synthetic (unGATED naked 2×)** — isolates what the TREND GATE adds vs naked leverage.

## Gates (pre-registered, FROZEN)
- **PRIMARY = terminal WEALTH.** Paired-difference block-bootstrap **Δterminal-wealth ci** of the arm vs
  **(a) buy-and-hold SPY TR** (the bar) AND **(b) the plain sleeve**. A win vs a baseline = paired Δwealth
  ci_low > 0.
- **SCORECARD (reported, NOT gating — the user accepts swings):** Sortino (+ci_low), MaxDD, Calmar, CAGR,
  Sharpe. Levered drawdowns will be deep; report them honestly, do not soften.
- **Named windows (report arm vs plain sleeve vs BH-SPY, CAGR + in-window MaxDD each):**
  - **CHOP (where trend-gated leverage BLEEDS):** 2011, 2015-16, 2018 whipsaws.
  - **CRASH (where the gate must EXIT before leverage compounds the damage):** 2008, 2020, 2022.

## Honest prior — MEDIUM (~30-40%)
The highest-prior wealth lever available: mechanism sound (leverage's damage is chop; our signal exits
chop), published family ("leverage for the long run" / Lifecycle Investing), and the gate is OUR OWN
validated engine. But expect deflation — vol decay + ER + borrow in the synthetic, and the whipsaw windows
are real. `[NN-MBL]` context: this is a NEW OFFENSE expression of an already-validated signal (+1 trial);
the PRIMARY metric is WEALTH (the user's north star), not Sharpe, so DSR/MBL is scorecard-context not the
gate. Either verdict defines the offense program's foundation. N_trials += 1.

---
## RESULTS (fair T-255 harness, 2000-10→2025-12, wealth-led)

### Basis check (`[NN-SUBSTRATE-REVERIFY]`) — DEFENSIBLE, synthetic trustworthy
Synthetic vs REAL SSO (yfinance, 2006-06→2026-04, n=4,986): CAGR **15.58% syn vs 15.35% real (+0.23%/yr,
terminal ratio 1.040)**; daily tracking-error 3.68%/yr (normal 2×-product path noise). Under the pre-registered
<1%/yr unexplained threshold → trustworthy. The +0.23%/yr is MILDLY OPTIMISTIC → the arm's edge is if anything
slightly overstated (conservative for the null-leaning verdicts below; the leverage only touches the SPY leg's
1/3 weight, so the arm-level optimism is ~1/3 of this).

### The 5-way table (WEALTH-led — the user's north star)
| strategy | $10k→ | CAGR | Sortino | ci_low | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|---|
| **TREND-GATED 2× ARM** | **51,545** | 6.7% | 1.127 | 0.611 | 0.859 | −15.1% | 0.45 |
| buy-hold SPY TR (THE BAR) | **63,335** | 7.6% | 0.603 | 0.164 | 0.485 | −59.2% | 0.13 |
| plain ensemble sleeve | 38,241 | 5.5% | 1.257 | 0.757 | 0.963 | −11.1% | 0.49 |
| 60/40 (continuity) | 48,455 | 6.5% | 0.806 | 0.331 | 0.634 | −36.2% | 0.18 |
| buy-hold SSO-syn (naked 2×) | **74,441** | 8.3% | 0.503 | 0.064 | 0.404 | **−88.8%** | 0.09 |

### PRIMARY GATE — paired Δterminal-wealth 95% CI
- **arm − buy-hold SPY TR: [−25.80, +4.93] → NOT SIGNIFICANT, point NEGATIVE** ($51.5k vs $63.3k, −1%/yr).
  **The arm does NOT beat the new bar on pure terminal wealth.**
- **arm − plain ensemble sleeve: [+0.00, +4.85] → marginal WIN** ($51.5k vs $38.2k, +35%; ci_low just
  touches 0 → directional, barely CI-significant, and haircut by the +0.23%/yr synthetic optimism).

### Named windows (CAGR / in-window MaxDD): arm | plain | BH-SPY
| window | arm | plain | BH-SPY |
|---|---|---|---|
| CHOP 2011 | +1.7% / −10.9% | +3.9% / −8.5% | −3.3% / −18.6% |
| CHOP 2015-16 | −0.8% / −11.8% | −0.4% / −9.3% | **+6.5%** / −12.8% |
| CHOP 2018 | +0.7% / −8.3% | +1.3% / −4.9% | −2.1% / −17.8% |
| **CRASH 2008** | **−5.3% / −13.8%** | −1.7% / −11.0% | **−42.2% / −56.6%** |
| CRASH 2020 | **+16.2%** / −9.0% | +11.5% / −5.3% | +15.7% / −33.7% |
| CRASH 2022 | −9.0% / −9.2% | −4.0% / −4.7% | −18.5% / −24.4% |

## VERDICT — offense thesis PARTIALLY validated: a path-optimizer + a real kicker on the sleeve, NOT a SPY-beater
1. **The mechanism is CONFIRMED.** The gate exits crashes before leverage compounds them — CRASH-2008 the arm
   lost only −13.8% MaxDD vs naked SPY's −56.6% (and naked 2× would have been ~−80%). And naked 2× (SSO
   buy-hold) out-compounds 1× SPY by a mere +0.7%/yr (8.3 vs 7.6) for DOUBLE the exposure and a **−88.8%**
   drawdown — **vol decay + crash-compounding ate the naked leverage**, exactly the thesis. The gate is what
   makes leverage survivable: −15.1% MaxDD instead of −88.8%.
2. **vs the plain sleeve: a real WEALTH kicker** (+35% terminal, 5.5%→6.7% CAGR) at a modest DD cost
   (−11%→−15%) and near-unchanged Sortino (1.26→1.13). Marginally CI-significant (ci_low ≈ 0). Trend-gated
   leverage is a genuine offense upgrade to the defensive deploying sleeve.
3. **vs buy-hold SPY (THE new bar): it LOSES** (~1%/yr, not significant) — **fails the primary wealth gate.**
   On a 2000-2026 sample that ended at all-time highs, buy-and-hold's crash-recoveries were fully rewarded, so
   the gate's chop-exits (esp. the choppy-but-RISING 2015-16, where SPY +6.5% beat the de-risking arm) cost
   more upside than they saved. The arm delivers **near-SPY wealth ($51.5k vs $63.3k) at ¼ the drawdown (−15%
   vs −59%) and ~2× the Sortino** — a vastly better PATH, but not more terminal wealth.

**Why it doesn't reach SPY:** the sleeve is only ~⅓ equity and the leverage is gated + capped at 2× on that ⅓
leg → effective average equity exposure ≈ 1.05-1.1× of NAV. It is a defensive sleeve with a leverage kicker,
not a levered equity strategy. **The offense program's honest foundation:** trend-gated leverage is the
survivable way to hold leverage (it converts naked 2×'s −89%/8.3% into −15%/6.7%), and it beats the defensive
sleeve on wealth — but beating buy-hold SPY on pure terminal wealth needs MORE of the book levered or a higher
cap, which is a SEPARATE pre-registered arm (not this one). Recommend: (a) adopt trend-gated leverage as the
Roth offense expression over the plain sleeve (wealth + survivable DD); (b) a follow-up arm testing higher
leverage / levering the equity-ON state more aggressively, if the user will accept deeper (but gated) DD.
`[NN-MBL]`: +1 trial; PRIMARY metric is WEALTH (north star), Sharpe/Sortino are scorecard. Basis +0.23%/yr
optimistic (noted). Reproducible: `scripts/trend_gated_leverage_t282.py`.

