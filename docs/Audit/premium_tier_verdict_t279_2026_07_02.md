# T-279 — the $65-70K+ TIER test (direct premium harvesting): VERDICT

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/premium-tier-t279` · **N_trials += 1** (tier-labeled)
Capital-adaptive revival: the income gauntlet was skipped at $5-15K on IMPLEMENTABILITY (the WTPI wrapper divergence, T-261). At $65K+ a real XSP cash-secured put IS the CBOE PUT-index mechanic → the wrapper objection disappears, so the test earns its slot FOR THIS TIER. Pre-registered (frozen): 70% deploying trend sleeve + 30% CBOE PUT index, monthly-rebalanced, fair T-255 harness, PUT roll cost 7.5bps/mo.

## TL;DR — even where it's implementable, direct premium harvesting FAILS as an addition: it strictly DEGRADES the sleeve (worse Sortino AND worse MaxDD), crashes 2-3× harder than the sleeve in the exact gap windows the sleeve defends, and beats no benchmark significantly. The wrapper was never the real problem — the carry-not-hedge science (T-261) is, and it stands at every tier.

## Gauntlet — 2000-2026 (25.2y; fair conventions)
| strategy | Sortino (ci_low) | MaxDD | CAGR | $10k → |
|---|--:|--:|--:|--:|
| **trend sleeve alone** | **1.257 (0.757)** | **−11.1%** | 5.5% | $38,250 |
| CBOE PUT alone (net roll) | 0.466 (0.130) | −37.6% | 5.6% | $39,202 |
| 60_40 robo | 0.811 (0.375) | −36.7% | 6.4% | $47,202 |
| schwab_like robo | 0.925 (0.425) | −27.9% | 5.6% | $39,171 |
| **COMBO 70/30 (the arm)** | 1.146 (0.644) | −18.5% | 5.5% | $38,157 |

## Pre-registered gates — paired Δ(COMBO − X) 95% CI
| vs | ΔSortino | ΔMaxDD | Δwealth | verdict |
|---|--:|--:|--:|---|
| **sleeve alone** | [−0.33, +0.20] | [−11.9%, +4.5%] | [−1.68, +1.42] | straddle-0 — but points WORSE (the PUT drags the sleeve down) |
| 60_40 | [−0.00, +0.48] | [+5.3%, +26.4%] | [−6.13, +1.24] | straddle-0 (DD better, but that's the sleeve) |
| schwab_like | [−0.07, +0.38] | [+0.4%, +15.1%] | [−2.46, +1.31] | straddle-0 |

**No significant beat of anything.** And vs the correct decision baseline — the sleeve you'd hold *instead* — the combo's point estimates go the WRONG way on both Sortino (1.257→1.146) and MaxDD (−11.1%→−18.5%). Adding the premium leg is dominated by not adding it.

## Named gap windows — the combo crashes 2-3× harder than the sleeve
| window | sleeve | COMBO | 60_40 | schwab | PUT-alone |
|---|--:|--:|--:|--:|--:|
| 1987 crash | n/a* | n/a* | n/a* | n/a* | **−29.7%** |
| 2008 GFC | **−5.3%** | −14.9% | −32.1% | −24.2% | −35.8% |
| COVID-2020 | **−5.0%** | −11.8% | −19.1% | −14.6% | −29.0% |

*sleeve/combo/robos cannot reach 1987 (the fair gold series starts 2000); PUT-alone −29.7% is the archetypal put-write crash — it sells tail into exactly the gap the sleeve exists to dodge.
The combo DOES survive 2008/COVID better than both robos (the dispatch's literal gate) — **but only because 70% is the sleeve.** The 30% PUT roughly TRIPLES the sleeve's GFC drawdown (−5.3%→−14.9%) and more than doubles its COVID drawdown (−5.0%→−11.8%). Put-write adds crash risk precisely where the sleeve's whole edge is crash defense — the T-261 carry-not-hedge finding, confirmed at this tier.

## Contract granularity (the honest tier discretization)
1 XSP CSP ≈ SPX/10 × 100 collateral. Today (SPX ~6000) that is **~$60,000 per contract**, so:
- **$65-70K holds ~1 contract = PREMIUM-DOMINANT (~90%), NOT a 70/30 blend** — and premium-dominant ≈ the PUT alone (Sortino 0.466, MaxDD −37.6%), the worst option on the board.
- A clean 70/30 (30% ≥ 1 contract) needs **~$200K**; 30% in 2 contracts (smoother) ~$400K.
- Granularity is TIME-VARYING: at SPX~1500 (2000) 1 XSP ≈ $15K, so $65K then held ~4 contracts (finer). The high current index level makes retail granularity WORSE now than historically.
So the "$65-70K tier" barely enables premium harvesting at all, and the size at which the pre-registered 70/30 is even implementable (~$200K) is a much higher tier — at which the verdict (negative addition) is unchanged.

## Verdict — the $65K+ advisor-map row
**Direct premium harvesting is IMPLEMENTABLE at $65K+ (wrapper objection gone) but is a NEGATIVE addition — hold the sleeve alone.** The combo beats the robos only because the sleeve carries it; the PUT strictly degrades the sleeve and amplifies exactly the drawdowns the sleeve is built to avoid. The capital-adaptive test did its job: it revived the strategy at the tier where the ONLY open objection (implementability) is resolved — and refuted it on the science, which never depended on the wrapper. Prior was LOW-MEDIUM (~25-30%); the result lands at the low end. N_trials += 1.

**T-279 done.**
