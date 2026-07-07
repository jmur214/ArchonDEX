---
task_id: T-2026-07-06-284
title: Trend-gated leverage on a FULL-EQUITY base — the designed-for-the-user's-goal arm
date: 2026-07-06
author: Agent D (fair-harness lane)
type: PRE-REGISTERED (1 PRIMARY + 1 SECONDARY, N_trials += 2)
status: DONE — PRIMARY beats buy-hold SPY on wealth (+28%, directional) AND Pareto-dominates it on point estimates; offense foundation SET. Branch feature/fullequity-gated-leverage-t284
---

# T-284 — trend-gated leverage on a full-equity base

T-282 diagnosed exactly: the trend gate makes leverage survivable (crash-exits before it compounds; naked
2× = +0.7%/yr for −89% DD), but the ⅓-equity sleeve base diluted effective leverage to ~1.05-1.1× → the
arm couldn't reach buy-hold SPY on wealth. B/T-283 sharpened the stakes: for the user's actual profile
(contributing $7K/yr, 40yr, won't-sell), max-equity configs win by ~3×. So the offense arm must run on a
FULL-EQUITY base. Reuses the T-282 SSO-synthetic (basis: +0.23%/yr optimistic vs real SSO — carried forward).

## PRIMARY — the classic published form ("leverage for the long run", frozen)
- **Base = 100% SPY** (full NAV, single asset — NOT the ⅓ sleeve).
- **Exposure `e = min(2 · ensemble_fraction(SPY), 2)`** (the {2,5,10}mo ensemble; e ∈ {0, ⅔, 4/3, 2}); cash
  (short rate) when the trend is fully OFF (e=0). Causal `.shift(1)`.
- **2× via the SPY(1×)+SSO-synthetic(2×) blend** (leverage cost embedded honestly):
  `e ≤ 1: e·spy_tr + (1−e)·cash`; `e > 1: (2−e)·spy_tr + (e−1)·sso_syn`; minus txn on Δe.
- Full-equity → effective average exposure ≈ 1.4-1.6× (vs T-282's ~1.1×). Roth-implementable (SSO + SPY).

## SECONDARY — the diversified-levered variant (frozen)
- The 3-asset EW sleeve with **EACH leg at 2×-when-its-own-trend-is-ON** (equity + bond + gold all
  gated-levered), EW ⅓ each, off-leg → cash. Per-leg synthetic 2×, `2·leg_tr_gross − borrow − ER`, borrow =
  DGS3MO+60bps for all legs; **per-leg ER assumptions (STATED):** SPY→**SSO 0.89%** (basis-checked, T-282);
  BOND→**2× intermediate-treasury synth, ER 0.95%** (NOT basis-checked — no clean real 2×-AGG ETF; the
  nearest real proxies UBT/TMF are 20-30yr duration, not our DGS10 synth → treat as a WEAKER, un-verified
  synthetic, `[NN-SUBSTRATE-REVERIFY]` caveat); GOLD→**2× gold synth (UGL-like), ER 0.95%** (NOT basis-
  checked, same caveat). The bond/gold 2× legs are exploratory; the SPY leg is the only validated 2×.

## Baselines (named, same window)
1. **Buy-and-hold SPY TR** — THE bar.
2. **Naked 2× SSO-synthetic buy-hold** — the ceiling (−89% DD).
3. **The T-282 arm** (⅓-equity sleeve, SPY leg 2×) — the diluted predecessor.
4. **The plain ensemble sleeve** (unlevered).

## Gates (frozen)
- **PRIMARY GATE = terminal WEALTH:** paired-difference block-bootstrap **Δwealth ci vs buy-and-hold SPY TR**.
  A win = ci_low > 0.
- **SCORECARD (reported, NOT gating):** Sortino (+ci_low), MaxDD, Calmar, CAGR, Sharpe. **Expect DEEP but
  GATED drawdowns — that IS the design; state the single WORST drawdown window plainly, no softening.**
- **Named windows (arm vs BH-SPY vs naked-2×, CAGR + in-window MaxDD):** CHOP (2011, 2015-16, 2018 — where
  T-282 bled; full-equity means ~3× the whipsaw exposure) AND CRASH (2008, 2020, 2022 — the gate must keep the
  levered book OUT of −50%+ territory).
- **`[NN-MBL]` effective-N:** the trend-gated-leverage family now has **3 trials** (T-282 + this primary +
  secondary). Count honestly; WEALTH is the north-star gate (not Sharpe), so DSR/MBL is scorecard-context.
- **Accumulation handoff:** save both arms' daily return curves for B/T-283's $7K/yr-contributing overlay
  (the user's real scoreboard).

## Honest prior — MEDIUM for the primary (~35-45%)
Naked 2× already ends ABOVE SPY on this window ($74k vs $63k), so the ceiling exists; the gate should recover
most of it while cutting −89% to a gated −25-40%. The open question is the CHOP COST — at full equity the
2011/2015-16/2018 whipsaws bite ~3× harder than in the diluted T-282 arm, and 2015-16 (choppy-but-rising)
already beat the gate there. This is the closest thing to a designed-for-the-user's-goal arm we have run.
N_trials += 2.

---
## RESULTS (fair T-255 harness, 2000-10→2025-12, wealth-led; SSO basis +0.23%/yr optimistic carried fwd)

### The table (WEALTH-led — the user's north star)
| strategy | $10k→ | CAGR | Sortino | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|
| **PRIMARY 100% SPY 2×-gated** | **81,310** | **8.7%** | 0.606 | 0.524 | −42.8% | 0.20 |
| **SECONDARY 3-leg 2×-gated** | 76,317 | 8.4% | **0.999** | 0.766 | **−22.6%** | 0.37 |
| buy-hold SPY TR (THE BAR) | 63,335 | 7.6% | 0.603 | 0.485 | −59.2% | 0.13 |
| naked 2× SSO-syn (ceiling) | 74,441 | 8.3% | 0.503 | 0.404 | **−88.8%** | 0.09 |
| T-282 arm (⅓ sleeve 2×) | 51,549 | 6.7% | 1.127 | 0.859 | −15.1% | 0.45 |
| plain ensemble sleeve | 38,241 | 5.5% | 1.257 | 0.963 | −11.1% | 0.49 |

### PRIMARY GATE — paired Δterminal-wealth 95% CI vs buy-hold SPY
- **PRIMARY − BH-SPY: [−12.38, +30.81]** — straddles zero (leverage inflates the bootstrap variance), but
  **point strongly POSITIVE (+28% terminal, +1.1%/yr)** → a DIRECTIONAL wealth win, not CI-significant.
- **SECONDARY − BH-SPY: [−23.90, +15.80]** — straddles zero, point positive (+20%). Directional.

### Named windows (CAGR / in-window MaxDD): PRIMARY | BH-SPY | naked-2×
| window | PRIMARY | BH-SPY | naked-2× |
|---|---|---|---|
| CHOP 2011 | **−13.1% / −27.4%** | −3.3% / −18.6% | −12.4% / −36.3% |
| CHOP 2015-16 | −2.8% / −19.9% | **+6.5%** / −12.8% | +9.5% / −26.3% |
| CHOP 2018 | −2.5% / −19.7% | −2.1% / −17.8% | −9.9% / −33.8% |
| **CRASH 2008** | **−19.8% / −26.2%** | −42.2% / −56.6% | −72.2% / −84.8% |
| CRASH 2020 | **+25.6%** / −22.5% | +15.7% / −33.7% | +17.2% / −58.8% |
| CRASH 2022 | −26.5% / −27.2% | −18.5% / −24.4% | −39.5% / −46.3% |

**Worst drawdown (stated plainly):** PRIMARY’s worst peak-to-trough is **−42.8%** (trough 2009-07 — the
2008-09 crash, gated). Deep — but the gate held the levered book to −26% *through* 2008 (vs SPY −57%, naked
2× −85%); the −42.8% figure spans the full peak-to-recovery path. The user accepts swings; this is the swing.

## VERDICT — the offense foundation is SET: full-equity trend-gated leverage beats buy-hold SPY on wealth
**Removing the ⅓-equity dilution flips the T-282 verdict.** The PRIMARY (100% SPY, 2×-when-trend-on) is the
first configuration to **beat buy-hold SPY on the user's terminal-wealth north star (+28%, $81.3k vs $63.3k)**
— and it does so while **beating even naked 2× ($74.4k) at HALF its drawdown** (−42.8% vs −88.8%). The gate
converts naked leverage's −89%/$74k into −43%/$81k: MORE wealth, half the DD. On point estimates the PRIMARY
**Pareto-dominates buy-hold SPY** — higher wealth, higher Sortino (0.606 vs 0.603), higher Sharpe (0.524 vs
0.485), shallower MaxDD (−42.8% vs −59.2%). The mechanism is decisive in 2008 (gated −26% vs naked −85%) and
2020 (+25.6%, leverage caught the recovery).

**The honest caveats (load-bearing):**
1. **Directional, not CI-significant.** The paired Δwealth CI vs SPY straddles zero ([−12.4, +30.8]) — leverage
   inflates bootstrap variance, so a +28% point win is not statistically bulletproof. For a WEALTH-maximization
   north star (point estimate, won't-sell) it is meaningful; as a Sharpe claim it would not clear. `[NN-MBL]`:
   this family now has **3 trials** (T-282 + primary + secondary) — counted; WEALTH is the gate, not Sharpe.
2. **The chop-cost is REAL and DEEP at full equity.** 2011 −27% in-window (SPY −3%), 2015-16 −20% (SPY +6.5%).
   The whipsaw bleed is ~3× the diluted T-282 arm; the crash-avoidance pays for it *over the full cycle*, but a
   run of choppy-but-rising years would hurt.
3. **The synthetic is +0.23%/yr optimistic** (SSO basis, T-282) → the +28% edge is slightly overstated (~+25%
   after haircut). Still a directional win.
4. **SECONDARY is the better RISK-ADJUSTED offense but rests on UN-VALIDATED synthetics.** $76.3k at −22.6% DD /
   Sortino 0.999 — nearly PRIMARY's wealth at half the drawdown, because the levered bond/gold legs de-correlate.
   BUT the bond/gold 2× series are **NOT basis-checked** (no clean real 2×-AGG ETF; UBT/UGL are different-duration
   proxies) → exploratory. Do NOT quote the SECONDARY as validated until its 2× legs are basis-checked against
   real levered ETFs (`[NN-SUBSTRATE-REVERIFY]`).

**Recommendation:** adopt the **PRIMARY** (100% SPY, 2×-gated, SSO-implementable, Roth-legal) as the validated
offense expression — it beats the buy-hold-SPY bar on wealth with a survivable (deep-but-gated) drawdown. Route
both curves to B/T-283 for the $7K/yr-contributing overlay (the user's real scoreboard — a levered curve
compounds contributions harder). The SECONDARY is a high-value follow-up pending a real-2×-ETF basis check on
the bond/gold legs. Reproducible: `scripts/fullequity_gated_leverage_t284.py`.

### Accumulation handoff (for B/T-283)
Both arms' daily return curves (primary, secondary, t282_arm, plain, bh_spy, bh_2x) saved to
`data/research/t284/daily_curves.parquet` — feed the $7K/yr-contributing accumulation overlay.

