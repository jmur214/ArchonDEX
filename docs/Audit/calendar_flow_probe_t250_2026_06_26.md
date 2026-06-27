---
task_id: T-2026-06-26-250
title: Calendar/FLOW probe — FOMC even-week + turn-of-month (the "is our H0 a coverage gap?" test)
date: 2026-06-26
author: Agent D
type: pre-registered probe (free, daily, orthogonal to the price vocabulary)
status: PRE-REGISTERED (results below the line)
---

# T-250 — calendar/flow probe (FOMC even-week + turn-of-month)

## PRE-REGISTRATION (written BEFORE the verdict — `[NN-MBL]`)

**Why:** the fresh-eyes brief found a real coverage gap — the 35-signal PRICE-vocabulary sweep
(T-196/Foundry) STRUCTURALLY could not find FLOW/CALENDAR effects (they aren't price signals). These
two are free, daily-testable, peer-reviewed, and orthogonal to everything we've tested. **A clean H0
here is high-value: it's the test of whether "comprehensive H0" is real or a coverage gap.**

**The two effects (rules FIXED by the papers — ZERO parameter sweep, ZERO researcher DOF):**
1. **FOMC even-week cycle** (Cieslak-Morse-Vissing-Jorgensen, JF 2019): since 1994 the equity premium
   concentrates in EVEN weeks of FOMC-cycle time (week 0 = FOMC week, then weeks 2/4/6). Rule: SPY
   long in even cycle-weeks, cash@rf in odd. (FOMC meeting calendar hand-compiled; weekly resolution
   is robust to ±1-2 day date error.)
2. **Turn-of-month** (McConnell-Xu, FAJ 2008): the equity premium concentrates in the 4-day TOM window
   (last trading day of month + first 3 of next). Rule: SPY long in the TOM window, cash@rf otherwise.
   (Pure calendar — EXACT, no external data.)
   (Pre-FOMC drift SKIPPED — decayed post-2015 per the brief.)

**CORRECTED METHODOLOGY (load-bearing, from the brief):**
- **Sortino/MaxDD = a CI-bounded SCORECARD, not an optimization target.** The rules above are
  pre-registered verbatim from the papers; NO sweep. Report Sharpe too (Sortino's CI is wider →
  `[NN-SHARPE-CI]` binds MORE strictly).
- **Liquid-ETF cost: 1.5 bps/side** (SPY tilts) — an institutional/small-cap cost model is a
  false-negative generator here.
- **MBL at EFFECTIVE-N:** these 2 effects are genuinely orthogonal to the price vocabulary (they
  count near-fully, NOT against the ~295 equity-book trials) — effective-N ≈ 2-3.
- **McLean-Pontiff decay haircut (~50%):** both are PUBLISHED → apply a 50% haircut to the in-sample
  edge for the honest forward estimate.
- **Honest robo bar:** beat both robos (60_40, schwab_like) risk-adjusted, net of the robo's cash-drag.

**Hypothesis H1:** the even-week and/or TOM tilt beats the robo on Sortino ci_low (and Sharpe), net of
liquid-ETF cost AND the 50% decay haircut. **H0:** the effect is present in-sample but does NOT clear
the corrected apparatus (haircut + cost + the give-up-of-out-of-window-return) → confirms comprehensive H0.

**Decision rule:** clears (haircut + cost, ci_low > robo) → a real orthogonal lever, escalate. Doesn't
clear → clean H0, the coverage gap is closed (we DID test flow/calendar, they don't survive honest gates).

---
## RESULTS (SPY 1994-2026)

### Raw effect — BOTH ARE PRESENT (the coverage gap was REAL)
| effect | in-window | out-of-window | diff | n(in) |
|---|---|---|---|---|
| **FOMC even-week** | **7.31 bps/day** | 1.87 bps/day | **+5.44 bps/day** | 4,318 |
| **Turn-of-month (4-day)** | **7.84 bps/day** | 4.03 bps/day | **+3.81 bps/day** | 1,552 |

Both effects are clearly present in our data — the 35-signal price sweep genuinely COULD NOT have
found them. The even-week magnitude (~4× the out-of-window rate) matches CMV-J and **validates the
hand-compiled FOMC calendar** (a wrong meeting cadence would wash the effect out).

### Deployable tilt (long SPY in-window / cash@rf out; 1.5bps/side cost) vs robos
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD | time-in-mkt |
|---|---|---|---|---|---|---|
| FOMC even-week tilt (net cost) | 0.750 | 0.408 | 0.795 | 10.5% | −29.6% | 53% |
| FOMC even-week tilt (net + 50% haircut) | 0.972 | 0.604 | 1.032 | 7.1% | −13.1% | 53%* |
| TOM tilt (net cost) | 0.464 | 0.263 | 0.831 | 6.5% | −17.1% | 19% |
| TOM tilt (net + 50% haircut) | 0.717 | 0.509 | 1.286 | 5.2% | −8.2% | 19%* |
| SPY buy-hold | 0.816 | — | 0.638 | 10.8% | −55.2% | 100% |
| (robo bars, T-236) | 60_40 0.807 / schwab_like 1.008 | | | | | |

*the haircut shrinks the in-window EXCESS by 50% → effectively half-invested in-window → its higher
Sortino is a LOWER-EXPOSURE artifact, not a better edge; read the net-cost row for the honest standalone verdict.

### Verdict — the coverage gap was REAL, but neither survives as a STANDALONE robo-beater
- **NOT a clean H0:** the effects exist (even-week is large + robust). "Comprehensive H0" genuinely had
  a flow/calendar coverage gap — now tested and CLOSED.
- **NOT a clean robo-beater either (standalone):** as deployable SPY tilts net of the corrected
  apparatus, **TOM FAILS** (Sortino 0.464 — gives up too much return at 19% time-in-market), and
  **FOMC even-week is MARGINAL** — its net-cost Sortino (0.750) is BELOW both robos and ≈ SPY buy-hold,
  even though it's a genuinely better-SHAPED equity exposure (~buy-hold's 10.5% CAGR at HALF the time
  in market and HALF the drawdown, −29.6% vs −55%). Standalone pure-SPY, it can't beat the diversified
  robo on risk-adjusted terms.
- **The even-week effect is the real find** — large, orthogonal, robust, and it produces a
  half-drawdown equity exposure. Its limitation is concentration (pure SPY); the natural low-prior
  Step-2 is **combining the even-week TIMING with the trend sleeve / a diversified base** (timing ×
  diversification), where it could add value the standalone version can't — NOT a standalone deploy.

**Net:** the coverage gap was real and is now closed honestly — flow/calendar effects EXIST in our
data (so "comprehensive H0" was incomplete), but as standalone deployable tilts net of cost + the 50%
McLean-Pontiff haircut they do NOT clear the robo bar (TOM fails; even-week is a better-shaped-but-not-
robo-beating pure-equity exposure). The deployable conclusion ("nothing standalone beats the robo")
SURVIVES — for the more honest reason that the effects are real but standalone-marginal. The one
forward thread worth a low-prior Step-2: even-week timing × the trend sleeve.

