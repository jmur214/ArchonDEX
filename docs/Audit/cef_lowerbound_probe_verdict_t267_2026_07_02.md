# T-267 — CEF discount-capture SURVIVOR-ONLY LOWER-BOUND probe: VERDICT

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/cef-lowerbound-probe-t267` · **N_trials += 1**
Ran the frozen T-264 pre-registration (`cef_data_audit_t264_2026_07_02.md`). Survivor-only free NAV panel (yfinance `X<TKR>X`), 25 liquid CEFs, monthly long-only cheapest-quintile by own-trailing-12mo discount z-score, TR returns, CEF txn 20bps r/t. Robos on the T-255 FAIR conventions (DGS3MO cash path, ER+txn both sides, schwab below-market sweep −125bps). **Lower-bound framing: PASS = real & bias-defeating; FAIL = INCONCLUSIVE, not a refutation.**

## TL;DR — the academic alpha REPLICATES bias-defeatingly full-sample (t_HAC 2.31 even survivor-only), but it is NOT a deployable robo-beater (leveraged-CEF beta → −42.7% MaxDD, fails Sortino-vs-robo), and forward (post-2011) persistence is INCONCLUSIVE on free data (the wins are in the delisted tail).

## Results
| window | Sortino (ci_low) | Sharpe | MaxDD | CAGR | ΔSortino vs 60_40 [ci] | ΔSortino vs schwab [ci] | **residual α t_HAC** | corr-sleeve |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **FULL** 2004-2026 (262mo) | 1.28 (0.55) | 0.87 | **−42.7%** | 14.1% | +0.12 [−0.48] | +0.00 [−0.67] | **+2.31 → EDGE** | +0.41 |
| **POST-2011** (187mo, decay) | 1.20 (0.51) | 0.84 | −25.5% | 11.3% | −0.29 [−0.92] | −0.40 [−1.04] | +0.90 → not-sig | +0.46 |

`is_it_beta_or_edge` (monthly, Newey-West 6 lags, netting equity SPY + credit HYG-LQD + **the CEF-universe-average return**): FULL residual α **+0.43%/mo, t_HAC +2.31** (β_spy −0.20, β_cefuniv **1.30**); POST-2011 α +0.11%/mo, t_HAC +0.90.

## What this means — three distinct findings, kept separate
1. **The discount-reversion alpha is REAL and bias-defeating, full-sample.** After stripping equity, credit AND the CEF-universe beta, a **significant residual remains (t_HAC 2.31)** — and on a survivor-only lower-bound panel (which DROPS the biggest wins — the terminated wide-discount funds), finding significance is strong evidence the effect is real. **The academic finding (Pontiff / Patro-Piccotti-Wu) replicates.** This is a genuine PASS on the *existence* question.
2. **It is NOT a deployable robo-beating sleeve.** The tradeable strategy fails the beat-robo gauntlet in BOTH windows (ΔSortino ci_low < 0 vs both robos) and has a **−42.7% MaxDD** — because the quintile carries 1.30× the CEF-universe beta and leveraged CEFs get *destroyed* when discounts WIDEN in crises (2008: discounts blow out + NAV leverage collapses — discount *momentum*, the opposite of reversion, dominates the tail). The small reversion alpha (~5%/yr gross) cannot overcome that beta/leverage drawdown to beat a 60/40. **As a standalone sleeve or composer leg it does not clear the bar** (corr-to-sleeve +0.41/+0.46 — not a clean diversifier either).
3. **Forward persistence (post-2011) is INCONCLUSIVE on free data — NOT a confirmed decay.** The post-2011 residual (t_HAC 0.90) looks like McLean-Pontiff decay, BUT this is exactly where the lower-bound bias bites hardest: post-2011 activist campaigns (Saba et al.) TERMINATED wide-discount funds at an accelerating rate — those terminations-at-NAV are the strategy's biggest post-pub wins, and they are precisely the funds survivor-only DROPS. So the post-2011 number is a lower bound; the true forward alpha could be materially higher. **Per the pre-registered framing this is inconclusive, not a refutation.**

## Verdict & recommendation
- **Existence: PASS** (bias-defeating full-sample). CEF discount-reversion is a real premium — the one genuinely-new retail alpha the gap audit surfaced is not a mirage.
- **Deployability as a robo-beating sleeve: NO.** Leveraged-CEF beta + discount-widening-in-crisis (−42.7% MaxDD) swamp the small alpha; it fails Sortino-vs-robo both windows. This does not depend on survivorship (the beta/drawdown is measured on the surviving winners themselves).
- **Forward persistence: UNRESOLVED on free data.** The only clean way to answer "is the discount-reversion alpha still alive post-2011 net of the activist-terminated wins" is the **survivorship-complete paid tier (CRSP/WRDS)** — the free lower-bound proved the alpha EXISTED but structurally cannot resolve its current magnitude (the recent wins are the delisted funds).

**Bottom line:** the probe did its job — it confirmed the alpha is real (bias-defeating) AND showed the tradeable wrapper (leveraged CEFs) is too crisis-fragile to beat the robo. **Do not deploy CEF discount-capture as a sleeve.** If the forward-alpha question is worth resolving (it is the one open thread), it now has a clear, bounded price: CRSP survivorship-complete CEF data — not another free variation. N_trials += 1.

**T-267 done.**
