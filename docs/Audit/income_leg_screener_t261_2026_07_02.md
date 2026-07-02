# T-261 — income-leg SCREENER: results & recommendation ($0, screening only)

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/income-screener-t261`
Screening only — **no gauntlet, no N_trials consumed, nothing built.** Picks WHICH single income candidate earns the one pre-registered 50/50-with-sleeve test (Wave 2.1). Substrate: the T-256 unlock (`data/raw/cboe/` + `data/processed/tr_reconciled/`). Trend sleeve on the TR-reconciled SPY/AGG/GLD.

## Full-window screen (each candidate's own history)
| candidate | start | Sortino (ci) | Sharpe | MaxDD | CAGR | skew | Calmar | COVID-20 | 2022 | corr-sleeve | gap-day ret |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| CBOE PUT (put-write) | 1986 | 0.71 (0.41) | 0.78 | −37.1% | 9.6% | −2.9 | 0.26 | **−18.3%** | −7.7% | 0.22 | −47bps |
| CBOE BXMD (buywrite) | 1986 | 0.79 (0.45) | 0.72 | −46.9% | 10.6% | −1.1 | 0.23 | −17.5% | −16.1% | 0.28 | −72bps |
| PFF (preferreds) | 2007 | 0.29 (−0.11) | 0.29 | **−65.5%** | 3.8% | −0.2 | 0.06 | −8.5% | −18.2% | 0.13 | −33bps |
| PGX (preferreds) | 2008 | 0.24 (−0.12) | 0.24 | **−66.4%** | 2.8% | 0.6 | 0.04 | −5.2% | −21.2% | 0.07 | −16bps |
| **JEPI (cov-call)** | 2020 | **1.32** (0.25) | 1.03 | **−13.7%** | 11.0% | 0.0 | **0.80** | 0.0%* | −3.5% | 0.36 | −65bps |
| PCEF (CEF income) | 2010 | 0.59 (0.03) | 0.60 | −38.6% | 6.7% | −2.9 | 0.17 | **−19.1%** | −18.7% | 0.32 | −70bps |
| **MUB (muni)** | 2007 | 0.64 (0.09) | 0.59 | −13.7% | 3.1% | −1.6 | 0.22 | −3.5% | −7.3% | **0.13** | **−9bps** |
| SCHD (div-growth) | 2011 | 1.14 (0.46) | 0.89 | −33.4% | 13.2% | −0.3 | 0.40 | −12.5% | −3.3% | 0.36 | −97bps |
| AGG TR (baseline) | 2005 | 0.72 (0.26) | 0.60 | −18.4% | 3.0% | −1.9 | 0.16 | **+2.8%** | −13.0% | 0.23 | −15bps |

*JEPI started 2020-05, AFTER the COVID crash — its "0.0%" is non-participation, not resilience. `gap-day ret` = mean candidate return on the sleeve's worst-5% days (the fast-gap regime). PUT skew −2.9 matches the audit's −2.94 (a first-pass sparse-CDN splice glitch was found + fixed: use the dense Wayback xls 1986-2019, level-match CDN only after).

## Common window (2020-05+, JEPI-limited — fair cross-comparison)
Benign window (post-COVID-crash + 2020-21 rally + 2022 + recovery) → flatters long-biased candidates. JEPI Sortino 1.32 / Calmar 0.80, SCHD 1.50 / CAGR 15.7% (equity beta), PUT 1.20, AGG **0.04** (bonds dead in the rate-hike era). Correlation-to-sleeve is 0.29–0.41 for ALL — none is a real hedge on the common window.

## The decisive findings
1. **No income leg hedges the sleeve's fast gaps.** Every candidate has a NEGATIVE gap-day return — they are all long-risk and co-fall when the sleeve (caught long) gaps down. An income leg is a **CARRY addition, not a gap hedge**; the only fast-gap hedge here is high-quality duration (AGG +2.8% in COVID — but 2022 broke it, −13%).
2. **Put-write / buywrite (the audit's lean) is REFUTED as a sleeve diversifier.** PUT/BXMD are negative-skew tail-sellers that crash in exactly the sleeve's failure mode (COVID −17 to −18%), with −37/−47% MaxDD and the audit-confirmed decayed post-2013 edge. rSlv 0.22/0.28. They co-crash with the sleeve, not diversify it.
3. **Preferreds (PFF/PGX) and PCEF are crisis AMPLIFIERS** — −38 to −66% MaxDD, deeply negative COVID/2022. Reject. (NB: PCEF = naive CEF *beta*; this does NOT refute the audit's separate **CEF-discount-CAPTURE** long-quintile strategy, which is a different, still-open idea.)
4. **The two screen criteria CONFLICT.** "Most CAGR per MaxDD" → JEPI (Calmar 0.80). "Least correlated with the sleeve's failures" → MUB (rSlv 0.13, gap-day −9bps). No candidate wins both — the high-carry end co-crashes more; the true diversifier (MUB) adds too little return.

## Recommendation — the ONE for the pre-registered gauntlet
**Primary: JEPI**, tested with **BXMD (1986+) as the mandatory long-history structural proxy** (JEPI's 2020+ window cannot clear MBL and never saw a fast gap or GFC; BXMD shows the covered-call family's true crisis behavior). Wrapper-transfer check mandatory (JEPI methodology vs BXMD index; and JEPI itself is a 2020 wrapper). It is the ONLY candidate combining meaningful carry (11% CAGR) with low DD, and covered-call income is conceptually complementary to trend (premium in the range-bound chop where long/flat trend whipsaws).

**But the honest prior is LOW (~25-30%), below the audit's ~40%**, and the screen argues the income-leg slot is a **weak use of the single gauntlet**: the carry candidates (JEPI/PUT/BXMD) do not diversify the sleeve's fast-gap failure, and the one genuine diversifier (MUB) can't beat the robo on wealth. Expect the T-251 base rate (points-win / CI-fail).

**Alternative (if the composer wants pure diversification, not a standalone wealth-beat): MUB** — the honest lowest-correlation, lowest-gap-damage carry stream for the T-248 HRP composer, accepting it adds little return.

**Reject for the gauntlet:** PUT, PFF, PGX, PCEF, SCHD (SCHD is equity beta, not an income leg). If the director wants the single slot's highest EV, the screen suggests spending it elsewhere (the off-leg CTA upgrade, or CEF-discount-capture) rather than the income-leg family.

**T-261 done.** $0, screening only, 0 N_trials.
