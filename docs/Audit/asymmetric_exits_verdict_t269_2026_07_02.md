---
task_id: T-2026-07-02-269
title: Asymmetric exits (the "when to sell" skill) — VERDICT (H0)
date: 2026-07-02
worker: Agent B
branch: feature/asymmetric-exits-t269
status: DONE — ONE frozen trial (N_trials += 1). VERDICT: H0. The sell-discipline manufactures skew but is momentum BETA.
---

# T-269 — asymmetric exits: VERDICT (H0)

Ran the FROZEN pre-registration (`asymmetric_exits_prereg_t269...md`) — no
re-tuning. 701 PIT S&P 500 members (survivorship-free) ∩ OHLC, 2000-2026, 16,090
trades, 3bps/side, cash @ short rate.

## Result
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|
| **ASYM_EXITS** | **0.486** | **0.011** | **0.371** | 4.0% | **−30.6%** |
| trend_sleeve (fair) | 1.091 | 0.557 | 0.847 | 5.2% | −11.8% |
| 60_40 (fair) | 0.820 | 0.309 | 0.634 | 6.4% | −36.7% |
| schwab_like (fair) | 0.928 | 0.425 | 0.722 | 5.6% | −27.8% |

**Skew:** per-trade **+4.68** (win-rate 41.8%, avg winner +9.1% vs avg loser
−4.9%, best +303%, worst −35%); **daily portfolio skew −0.63**.
**Kill-test (`is_it_beta_or_edge`, FF5+Mom HAC):** **BETA** — market β 0.52,
momentum β 0.21, R² 0.54, alpha **−2.78%/yr (t_HAC −1.78** — negative, NOT
significant). **Paired vs the sleeve:** ΔSortino 95% CI [−0.80, +0.01],
**P(exits > sleeve) = 3%**. **MBL (26yr, N_eff 16):** Sharpe bar 0.459; exits
Sharpe **0.371 → fails**.

## Verdict — H0 (as the ~15-20% prior predicted), but a rich one
The exit structure **did exactly what it claims mechanically**: it manufactures
**strongly positive per-trade skew (+4.68)** — cut losers at ~−5%, let winners run
to +9% average / +303% best. The sell-discipline works *per trade*. **But it is
not a deployable edge:**
1. **It is momentum/market BETA, not alpha.** The kill-test decomposes the returns
   to market β 0.52 + momentum β 0.21 with a NEGATIVE, insignificant HAC alpha
   (−2.78%/yr, t −1.78). Trailing-stop trend-riding IS time-series momentum —
   exactly the family already found H0 (T-196). No orthogonal "sell skill" alpha.
3. **It loses to every robo and the sleeve** on Sortino/Sharpe (worst of the four),
   with a deep −30.6% MaxDD, and beats the sleeve only 3% of the time. It fails MBL.
2. **The positive per-trade skew does NOT survive to the portfolio** (daily skew
   −0.63). Why: the book is long-only correlated momentum names, so in a market
   selloff MANY trailing stops trigger together — the losses CLUSTER into deep,
   negatively-skewed portfolio drawdowns. "Let winners run, cut losers" cannot
   rescue a long-only momentum book from correlated stop-outs.

## What this closes (the user's standing question)
The system had never tested "choosing when to SELL" as a skill. Tested honestly on
one frozen, survivorship-free spec: **the asymmetric exit is a real mechanical
effect (it manufactures per-trade positive skew) but not a source of edge — it
delivers momentum beta with no alpha, worse risk-adjusted return than the robos
and the sleeve, and clustered-stop drawdowns that flip the portfolio skew
negative.** The "when to sell" question is answered with EVIDENCE: exit structure
alone does not beat the robo. Consistent with the whole-program H0 on in-house
equity alpha; the realized win remains the trend sleeve. Measurement only; nothing
built into any live path.
