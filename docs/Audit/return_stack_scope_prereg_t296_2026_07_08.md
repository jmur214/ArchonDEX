# T-296 — return-stacked funds (RSST/RSBT): SCOPE + DATA-REALITY AUDIT + PRE-REG DRAFT

**Date:** 2026-07-08 · **Agent:** C · Branch `feature/return-stack-scope-t296` · **0 N_trials** (scope only — the director freezes the pre-reg before any run)
The external research run ranked return-stacked funds the #1 untested idea: RSST (100% stocks + 100% managed-futures trend) / RSBT (bonds + trend) deliver the MF diversifier AND capital efficiency in one Roth-holdable ticker — potentially answering the parked micro-futures CTA (if RSST works, DIY micro-futures stays parked permanently). This is the T-264-style data-reality audit that gates the arm.

## Part 1 — DATA-REALITY AUDIT (measured, yfinance, 2026-07-08)
**Real funds are too short for a standalone gauntlet:** RSST inception **2023-09** (~2.8yr), RSBT **2023-02** (~3.4yr), RSSB 2023-12. All fail MBL alone (same shape as the T-272 BTC / T-284 SSO problem — a synthetic is required for full-cycle, validated on the live overlap).

**The synthetic construction has a load-bearing subtlety (measured):** the return-stack is NOT `SPY_ret + MF_ETF_ret`. An MF ETF (DBMF, KMLM) holds T-bills as collateral, so its return already INCLUDES the ~cash yield; but in RSST the **SPY is the collateral** (earning the equity return), so the MF leg must enter as its **EXCESS return over cash**:
> `synthetic_RSST = SPY_TR + (MF_leg_TR − cash_yield)`

Validated on the RSST live overlap (2023-09 → 2026-07, 709 days, DBMF as the MF proxy):

| synthetic | corr to real RSST | ann tracking-diff | synth ann-ret (real 19.7%) |
|---|--:|--:|--:|
| naive `SPY + DBMF` | 0.919 | **+9.10%/yr** | 31.9% |
| corrected `SPY + (DBMF − Tbill)` | 0.919 | **+4.50%/yr** | 26.0% |

**Findings:**
- The naive synthetic overstates RSST by **+9.1%/yr**; ~4.6pp of that is the **double-counted T-bill collateral yield** (~5% in the 2023-25 rate regime) — the excess-return construction is mandatory, and any future return-stack synthetic (RSBT, SSO in T-284, etc.) must subtract the collateral yield.
- **Even corrected, a +4.5%/yr residual basis remains** — DBMF's specific MF program ≠ RSST's proprietary trend program, plus RSST's ~1% fee + implementation frictions. Correlation is good (0.92 — the SHAPE tracks) but the **LEVEL is unreliable to ~±4-5%/yr.**
- **The fund's actual trend program is proprietary and CANNOT be validated** (the T-264 discipline: state what can't be checked). Any free MF-trend proxy carries this basis; it just changes which proxy's basis you inherit.

**Deep-history MF-trend leg options for a full-cycle (2000+) backtest — each with its own basis:**
| proxy | window | nature | basis risk |
|---|---|---|---|
| DBMF (validated above) | 2019+ | live MF-replication ETF | measured +4.5%/yr vs RSST; too short for full-cycle |
| AQR Time-Series-Momentum factor | 1985+ (free, aqr.com) | HYPOTHETICAL, net-of-cost academic series | construction-audit required (like the ReSolve SG-Trend series the dispatch names); hypothetical ≠ live |
| our own multi-asset long/flat overlay | 2000+ | long/FLAT, 3 assets | UNDERSTATES MF crisis-alpha (real MF goes SHORT across commodities/FX/rates — the very source of the 2022/crisis diversification) |

**Data-reality verdict:** a faithful *level*-replica of RSST is **NOT freely buildable** — the MF program is proprietary and every free proxy carries material (~±4-5%/yr) basis. The arm can only be a **DIRECTIONAL scoping read with the basis explicitly bounded**, NOT deployment-grade evidence. This is the honest finding to carry into the pre-reg.

## Part 2 — PRE-REGISTRATION DRAFT (director freezes before any run; N_trials += 1 when frozen)
**The arm (ONE, pre-registered):** the deploying ensemble sleeve with its **SPY leg replaced by synthetic-RSST** (`SPY_TR + (MF_excess)`), under the SAME multi-speed {42,105,210} long/flat gate — i.e. the sleeve holds {synthetic-RSST, AGG, GLD} EW-trend-ruled. Compared vs (a) the **plain deploying sleeve**, and (b) the **T-284 offense arm** (trend-gated SSO leverage). Fair T-255 harness (DGS3MO cash, ER incl RSST's ~1% + the MF-leg cost, txn), full-cycle.
- **MF-trend proxy (pre-register ONE, no sweep):** primary = AQR TSMOM (if the construction audit passes) OR our long/flat overlay as the fallback; validate the chosen proxy against DBMF on 2019+ and against real RSST on 2023+, and **report the measured basis as a pre-registered caveat** (the ±4-5%/yr band bounds the verdict).
- **The double-trend question (the key mechanism):** RSST stacks its OWN MF-trend, and our sleeve applies a long/flat gate on top → does the double-trend HELP (more assets under trend fixes trend's equity-chop weakness — the evidenced mitigation) or CANCEL (our gate flattens exactly when the MF overlay would carry)? Report the interaction explicitly.
- **Gates:** paired ΔSortino + Δwealth 95% CI vs BOTH baselines (plain sleeve, T-284 offense). **Named windows:** the sleeve's known fast-crash gaps (COVID-2020, 2008 where reachable) + **2015-16 chop** (trend's documented weakness — does the MF stack rescue it?) + **2022** (MF's crisis-alpha showcase).
- **Honest prior: MEDIUM-LOW (~25-35%)** — the stack adds the one diversifier with real crisis-alpha evidence, but (i) the hypothetical-replication basis (±4-5%/yr) may swamp the signal, and (ii) the double-trend interaction may cancel. **Exploratory-labeled** (real RSST 2.8yr can't clear MBL; the deep leg is hypothetical) — a scoping read, not deployment evidence, per the T-272 discipline.

## Part 3 — ON THE RECORD: buffered / defined-outcome ETFs are REJECTED (closes the door, no trial burned)
Buffered / defined-outcome ETFs (Innovator BUFR/BALT, FT Cboe Vest, etc.) are **REJECTED for this investor profile** and should never consume a trial:
- They **CAP the upside** (~9-18% annual caps) to fund a downside buffer — but this investor is a **max-terminal-wealth, won't-sell-in-downturns accumulator** ([[feedback_max_wealth_north_star_2026_07_06]]): selling the upside is selling exactly what the strategy exists to keep, and the downside buffer protects against a drawdown the holder has pre-committed to ride through.
- **~0.79-0.88% fees** for a payoff structure replicable with options at a fraction of the cost.
- Protection is only from the **period-start reference level** and resets annually — mid-period entrants get an asymmetric (often unfavorable) payoff, and the buffer is worthless once the index is already below the buffer floor.
Net: buffered ETFs sacrifice the equity risk premium a long-horizon holder should harvest, for insurance they've pre-declared they don't want. Door closed.

**T-296 done (scope + draft).** Director freezes the pre-reg → then I run (N_trials += 1). Nothing run here.
