---
task_id: T-2026-07-02-268
title: FOMC even-week × trend-sleeve tilt (T-250 step-2 — the queued ingredient arm)
date: 2026-07-02
author: Agent D (measurement lane)
type: PRE-REGISTERED trial (1, N_trials += 1)
status: DONE — H0/NULL (fails gate); shelf entry #6 closed. Branch feature/evenweek-sleeve-t268
---

# T-268 — FOMC even-week × the multi-speed trend sleeve

My T-250 measurement confirmed the Cieslak-Morse-Vissing-Jorgensen (JF 2019) FOMC even-week effect is
REAL and orthogonal in our data (+5.44 bps/day, even vs odd FOMC-cycle weeks on SPY), but
standalone-marginal on pure SPY. The queued step-2 (shelf entry #6's activation test): does the even-week
signal add value as an **ingredient tilt on the diversified deploying sleeve**, rather than as a
standalone strategy?

## Hypothesis (H1)
Scaling the trend sleeve's **SPY (equity) leg** exposure UP in FOMC even-weeks and DOWN in odd-weeks
concentrates equity exposure into the higher-return even weeks, improving the sleeve's risk-adjusted
return (Sortino) without a material terminal-wealth cost, net of the added turnover.

## Frozen mapping (fixed BEFORE any result — no sweep)
- **Substrate:** the fair T-255 harness (`scripts/multispeed_robustness_t260.py` machinery — flat leg earns
  the DGS3MO short rate, ER + 1.5bps both sides), **spec = the multi-speed {2,5,10}mo ensemble** (the T-260
  deploying spec). Common 2000-08→2026 window.
- **Tilt:** SPY-leg daily exposure = `ensemble_exposure(SPY) × m(day)`, where **m = 1.0 in FOMC even-weeks,
  0.5 in odd-weeks** (the CMVJ premium accrues in even cycle-weeks). AGG and GLD legs **unchanged**.
- **Long-only, no leverage:** m ≤ 1.0 (the tilt only ever REDUCES SPY exposure in odd weeks; it never
  levers up). This is the inbox's suggested mapping; frozen as the single pre-registered arm.
- **Continuous tilt, NOT a gate (T-220 lesson):** the 0.5 floor keeps the SPY leg always partly invested,
  and AGG/GLD are always on — the diversified sleeve never fully de-risks. FOMC dates are pre-scheduled
  (known ~1yr ahead), and `m(day)` uses the most-recent PAST meeting → causal, no look-ahead. The
  multiplier is applied AFTER the causal `.shift(1)` on the price signal.
- **Cost:** the multiplier flips ~weekly → adds SPY-leg turnover; charged at the same 1.5bps/side
  (× 1/3 leg weight) as the base harness. No separate cost model — the added flips are charged honestly.
- **FOMC calendar:** the T-250 hand-compiled meeting list (1994-2025, 8/yr) + `even_week()` (weeks since
  the most-recent meeting; even = premium).

## Gates (pre-registered)
- **Primary:** paired-difference block-bootstrap **ΔSortino** and **Δterminal-wealth** CI (21-day blocks,
  1000 iter) of the tilted sleeve vs the **unconditioned multi-speed ensemble sleeve** (the T-260 spec).
  A win requires the paired ΔSortino ci_low > 0 OR Δwealth ci_low > 0 (`[NN-SHARPE-CI]`) — a directional
  point improvement that straddles zero is NOT a pass (the T-260/T-255 discipline).
- **Named windows:** report in-window behavior for the 2015-2018 bull (where halving odd-week beta should
  cost the most) and a crisis (2020/2022) for completeness.

## Honest prior — LOW (~15-20%)
The even-week premium is real but small (+5.44 bps/day), and the mapping HALVES SPY exposure ~half the
time (odd weeks) → it gives up bull-market upside and adds turnover. For the tilt to win, the even-week
concentration must beat the wealth given up by de-risking odd weeks. Most likely outcome: a small Sortino
change that does not clear ci_low, and a terminal-wealth give-up — i.e. a null that **closes shelf entry
#6 honestly**. Report whatever it is. N_trials += 1.

---
## RESULTS (fair T-255 ensemble harness, 2000-10→2025, even-week share = 53% of days)

| sleeve | Sortino | ci_low | MaxDD | CAGR | $10k→ |
|---|---|---|---|---|---|
| **unconditioned ensemble (T-260 deploying spec)** | **1.257** | **0.757** | −11.1% | 5.5% | **38,250** |
| even-week-tilted SPY leg (1.0 even / 0.5 odd) | 1.185 | 0.698 | −10.1% | 5.0% | 33,771 |

**Paired-difference block-bootstrap (tilt − base):**
- **ΔSortino 95% CI [−0.116, +0.039]** — straddles zero, POINT is **negative** (1.257→1.185). Not an
  improvement; a directional loss.
- **Δwealth (×start) 95% CI [−1.168, −0.050]** — **entirely below zero** → the tilt costs terminal wealth
  *significantly* (−$4,479 on $10k, −11.7%).

**Named windows (CAGR / MaxDD):**
| window | base | tilt |
|---|---|---|
| 2015-2018 bull | +1.8% / −9.3% | **+0.9%** / −7.8% |
| COVID-2020 | +11.0% / −5.3% | +10.0% / −4.7% |
| 2022 bear | −3.6% / −4.7% | −2.1% / −4.2% |

## VERDICT — H0 / NULL: fails the pre-registered gate. Shelf entry #6 CLOSED.
The tilt does the opposite of add alpha: it **modestly reduces MaxDD (−11.1%→−10.1%) but at a significant
terminal-wealth cost (Δwealth CI entirely negative) and a directional Sortino LOSS (ΔSortino ci_low
−0.116, point negative).** Neither primary gate is met (both ci_low < 0). The mechanism is exactly the
pre-registered concern, visible in the 2015-2018 bull (CAGR halved, +1.8%→+0.9%): halving odd-week SPY beta
gives up bull-market upside, and the real-but-small even-week premium (+5.44 bps/day, T-250) does not
compensate. Concentrating equity into even weeks lowers *total* equity exposure, so return falls more (in
Sortino terms) than downside-vol does.

**Why it's redundant:** the sleeve ALREADY de-risks via the trend overlay; layering a calendar de-risk on
top just gives up more upside for a defensive property the sleeve already has — the same "defensive trade,
not a return-add" pattern as the barbell (T-251) and the sleeve itself. The even-week effect is real
(T-250) but **not additive as a sleeve ingredient.** A milder mapping (e.g. 1.0/0.75) only shrinks toward
the base — it cannot flip the already-zero/negative Sortino Δ; no mapping in this long-only family clears
the gate. Not a harness artifact: the tilt is causal, and its DD-improvement confirms it fires as intended;
it simply loses the wealth/Sortino trade.

**Shelf entry #6 (even-week × sleeve) closes honestly at H0.** This was the cleanest remaining calendar
"ingredient" arm; its null further tightens the "comprehensive H0" (T-250 calendar, T-254 factor-momentum,
T-265 small-cap PEAD). N_trials += 1. Reproducible: `scripts/evenweek_sleeve_t268.py` (reuses the T-260
harness + T-250 FOMC calendar).

