---
task_id: T-2026-07-02-273
title: Market-breadth sizing tilt on the trend sleeve (the #1-ranked conditioning input)
date: 2026-07-02
author: Agent D (measurement lane)
type: PRE-REGISTERED trial (1 arm, N_trials += 1)
status: DONE — H0/NULL (causal); apparent edge was a look-ahead bug, caught + fixed. Branch feature/breadth-tilt-t273
---

# T-273 — market-breadth sizing tilt on the multi-speed trend sleeve

The audit's #1-ranked conditioning input: **market breadth** (% of index members above their 200-day SMA),
computed from OUR OWN PIT panel — zero external-data risk, full 26yr history, survivorship-aware via the
membership panel. A `BreadthDetector` (`engines/engine_e_regime/detectors/breadth_detector.py`) already
computes `pct_above_sma200` but was never tested as a sleeve input.

## Hypothesis (H1)
The trend overlay sees only SPY's OWN price. Breadth sees **cross-sectional participation** — the number of
names carrying the index. The specific value is the **divergence case**: index up (trend overlay long) but
breadth NARROW (few names participating), a documented pre-top signature (1999, 2007, late-2021) the price
trend cannot see. Scaling the sleeve's SPY-leg exposure DOWN when breadth is weak should reduce drawdown
BEFORE the trend rolls over — adding something orthogonal to the trend.

## The bar is TWO nulls (the load-bearing constraint)
1. **vs the unconditioned ensemble sleeve** (the T-260 deploying spec): paired ΔSortino + Δwealth ci.
2. **vs the T-268 graveyard:** even-week was a de-risking tilt that LOST (cost wealth for a marginal DD gain,
   because the trend overlay ALREADY de-risks). Breadth must do BETTER than that — its de-risking must be
   BETTER-TIMED than the trend's own (reduce specifically before drawdowns the price trend misses), not just
   repeat a wealth-costing de-risk. A breadth tilt that merely tracks the trend adds nothing.

## Frozen spec (fixed BEFORE any result — no sweep)
- **Breadth series (PIT, survivorship-aware):** at each date, `breadth = % of S&P-500 members (per the
  membership panel) that have a price and ≥200d history AND close > their own 200-day SMA`. Reuses the
  `BreadthDetector` definition (`pct_above_sma200`, sma_long=200), vectorized to a daily series (the
  detector is a stateful online classifier; a vectorized series is the right tool for a backtest input).
- **Multiplier:** `m(t) = 0.5 + 0.5 · P252(t)`, where `P252` is the **causal trailing-252-day percentile
  rank** of `breadth(t)` (breadth low vs its own recent range → low percentile → reduce). Continuous, band
  **[0.5, 1.0]**, applied to the **SPY leg only** (AGG/GLD unchanged), long-only/no-leverage. Applied AFTER
  the causal `.shift(1)` on the price signal; breadth uses data through t-1 → causal, no look-ahead.
- **Substrate:** the fair T-255 harness, multi-speed {2,5,10}mo ensemble spec (the deploying spec); added
  SPY-leg turnover charged at 1.5bps/side (same as T-268).

## Gates (pre-registered)
- **Primary:** paired-difference block-bootstrap **ΔSortino** and **Δwealth** ci (21-day blocks, 1000 iter)
  vs the unconditioned ensemble sleeve. A win needs ΔSortino ci_low > 0 OR Δwealth ci_low > 0
  (`[NN-SHARPE-CI]`; a point improvement that straddles zero is NOT a pass — the T-268/T-255 discipline).
- **Two-nulls check:** report vs the T-268 even-week result — did breadth BEAT the graveyard (add
  orthogonal value), or just repeat the wealth-costing de-risk?
- **Named windows:** the divergence tops — the 2007 narrow-breadth top and the late-2021 narrowing — where
  breadth SHOULD add value the trend misses; plus the 2015-2018 bull (where de-risking costs the most).

## Honest prior — LOW (~10-15%)
T-268 just showed the sleeve's own trend rule already does the de-risking, and any redundant de-risk costs
wealth. For breadth to win it must time the reduction BETTER than the price trend — capture participation
divergence the trend can't see. Plausible in principle (the divergence signature is real) but the trend
overlay is a strong de-risker already, and breadth is highly correlated with price trend in most regimes. A
null closes the conditioning family's #1 candidate. N_trials += 1.

---
## RESULTS (fair T-255 ensemble harness, 2000-10→2025)

### ⚠️ Measurement-integrity catch FIRST (the headline)
The first run showed the tilt improving EVERYTHING — Sortino 1.257→1.487, CAGR 5.5→6.2%, MaxDD −11.1→−10.2%,
$10k→$45,767, with paired ΔSortino CI **[+0.119,+0.246]** and Δwealth CI **[+0.365,+1.343]** (both entirely
positive). **That was a look-ahead bug, not an edge.** A causal de-risking tilt (multiplier ≤ 1.0, mean
0.743) that *increases* CAGR is near-impossible unless it peeks: `breadth[t]` is computed from **close[t]**
(price vs its 200d SMA using today's close), so `mult[t]` embeds day-t information — but it was applied to
`aret[t]` (the return *into* close[t]). The trend leg is correctly `.shift(1)`'d; the multiplier was not.
**Fix:** lag the multiplier one trading day (use `mult[t-1]`, breadth through t-1) — consistent with the
trend's own lag. Caught by the "too-good result → hunt the look-ahead" discipline ([NN-FAIL-CLOSED]).

### Causal result (multiplier lagged one trading day)
| sleeve | Sortino | ci_low | MaxDD | CAGR | $10k→ |
|---|---|---|---|---|---|
| **unconditioned ensemble (T-260 deploying spec)** | **1.257** | **0.757** | −11.1% | 5.5% | **38,250** |
| breadth-tilted SPY leg (causal) | 1.231 | 0.742 | −10.6% | 5.1% | 35,391 |

**Paired-difference block-bootstrap (tilt − base):**
- **ΔSortino 95% CI [−0.059, +0.051]** — straddles zero, POINT negative. Not an improvement.
- **Δwealth (×start) 95% CI [−0.792, +0.024]** — straddles zero, POINT negative (−7.5% terminal wealth).

**Named windows (CAGR / MaxDD) — the divergence tops where breadth SHOULD add value:**
| window | base | tilt |
|---|---|---|
| 2007-08 top | +3.0% / −11.0% | +4.7% / −10.6% |
| late-2021 narrow | −3.7% / −5.8% | −2.7% / −4.4% |
| 2015-2018 bull | +1.8% / −9.3% | +1.2% / −8.6% |
| COVID-2020 | +11.0% / −5.3% | +9.8% / −5.1% |

### Breadth series (PIT, survivorship-aware)
680 S&P-member tickers with prices; series 1999-10→2026-04 (6,470 days); median 349 members/bar; breadth
mean 0.64. Multiplier mean 0.743 (17% at the 0.5 floor, 15% at the 1.0 cap) — a genuine, varying tilt.

## VERDICT — H0 / NULL (both gates fail). Conditioning family's #1 candidate closes.
Once causal, the breadth tilt is the **same defensive trade as T-268's even-week**: it shaves MaxDD
marginally (−11.1→−10.6%) but costs terminal wealth (−7.5%) and does not improve Sortino — both paired
ci_low < 0. **It fails the TWO nulls:** (1) it does not beat the unconditioned sleeve (paired CIs straddle
zero, points negative); (2) it does NOT beat the T-268 graveyard — it repeats the same wealth-costing
de-risk, adding nothing orthogonal to the trend. The divergence windows (2007, late-2021) show only a
marginal DD improvement bought with lost upside (2015-18 bull CAGR +1.8→+1.2%) — the trend overlay already
does this de-risking, and breadth is too correlated with the price trend to time it better.

**The apparent edge was entirely the one-day look-ahead** — a clean demonstration of why conditioning
signals derived from `close[t]` must be lagged exactly like the price signal. Breadth-as-a-single-input
sizing tilt is dead; this closes the audit's #1-ranked conditioning candidate, further tightening the
comprehensive H0 (T-250/T-254/T-265/T-268/T-271). N_trials += 1. Reproducible:
`scripts/breadth_tilt_t273.py`.

