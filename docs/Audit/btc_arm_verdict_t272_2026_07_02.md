# T-272 — the BTC 4th-asset ARM: VERDICT (EXPLORATORY)

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/btc-arm-t272` · **N_trials += 1**
Completeness-critic hole #8 — bitcoin, the one liquid new asset class added to the investable universe since the sleeve was designed, never examined. Pre-registration FROZEN before running: 5% BTC leg (risk-sensible — at ~70% vol, 5% ≈ half the portfolio risk), same multi-speed {42,105,210}d long/flat rule, base scaled to 95%, fair T-255 harness (DGS3MO flat-leg, ER, txn; BTC 7.5bps/flip + IBIT 0.25% ER). BTC on the weekday calendar (≈ IBIT capture).

## TL;DR — the STRONGEST composition result of the arc: a 5% trend-ruled BTC leg SIGNIFICANTLY lifts Sortino AND wealth (paired CIs above 0), DD-neutral, and the trend rule caps BTC's −75/−81% winters to ~−6/−7%. BUT it is EXPLORATORY and CANNOT be deployment evidence — 11yr is ONE BTC bull era, the wealth rides that secular bull, and the Roth-clean wrapper (IBIT) is only 2.5yr old.

## A/B — 2015-04 → 2025-12 (10.7y, EXPLORATORY, < MBL bar)
| sleeve | Sortino (ci_low) | MaxDD | CAGR | $10k → |
|---|--:|--:|--:|--:|
| **A: base ensemble (no BTC)** | 1.590 (0.876) | −6.5% | 6.8% | $20,248 |
| **B: + 5% BTC leg** | **2.205 (1.427)** | −7.5% | **10.1%** | **$28,059** |

**Paired Δ(B − A), block-bootstrap 95% CI:**
- **ΔSortino [+0.146, +0.700] → SIGNIFICANT+** (entirely above 0)
- **Δwealth-multiple [+0.299, +1.524] → SIGNIFICANT+** (entirely above 0)
- ΔMaxDD [−2.2%, +2.5%] → straddles 0 (DD-neutral)

This is categorically different from every prior composition addition (barbell T-251, income legs T-261, concentration T-241, HRP-over-sleeves T-248 — all straddled 0 or were refuted). BTC is the first leg whose paired improvement clears 0 on BOTH risk-adjusted and wealth terms.

## Winter windows — does the long/flat trend rule exit in time? YES
| window | A (no BTC) | B (+5% BTC) | BTC-USD buy&hold |
|---|--:|--:|--:|
| 2018 crypto winter | −4.9% | −5.5% | **−81.4%** |
| 2022 crypto winter | −5.6% | −7.3% | **−75.7%** |
| COVID-2020 | −5.0% | −5.5% | **−48.7%** |

The multi-speed long/flat discipline caps BTC's catastrophic bears exactly as designed — a −75/−81% raw drawdown becomes a +0.6-to-1.7pp add to the sleeve's own drawdown, because the trend rule goes flat (BTC leg → cash) before the worst of each winter. The sleeve's discipline works on BTC's tail the same way it caps everything else.

## Why this is EXPLORATORY, not deployment evidence (the honesty gate)
1. **11yr = ONE BTC bull era.** BTC ran from ~$200 (2015) to ~$60k+ — a ~300× secular bull. The +3.3pp/yr CAGR and the significant Δwealth are *earned on that bull*. Per `[NN-MBL]`, an 11yr window on a single-regime, single-bull-era asset cannot clear the DSR bar — this is the textbook unrepeatable sample. The result says "BTC-as-trend-ruled-satellite trended beautifully in the one era we have," which is exactly what the dispatch's honest prior warned.
2. **Upside is not guaranteed to repeat; the trend rule's winter-exits are IN-sample.** The rule was validated on this same era; its OOS winter behavior (does it exit the NEXT bear in time?) is unknown. The downside cap is encouraging but in-sample.
3. **Wrapper / `[NN-SUBSTRATE-REVERIFY]`:** the cleanly-Roth-holdable instrument (IBIT) launched Jan-2024 — only ~2.5yr. The 11yr backtest uses 24/7 spot BTC that a Roth couldn't cleanly access pre-2024 (GBTC traded at large premiums/discounts — a wrapper-basis problem). BTC-USD daily returns correlate only 0.82 to IBIT (24/7-vs-market-hours timing, not a tracking failure) — the monthly-signal sleeve is robust to it, but real fills differ.

## Verdict & recommendation
- **The exploratory arm PASSES decisively** — significant ΔSortino + Δwealth, DD-neutral, winters survived. BTC's convex/high-vol/low-correlation profile is precisely the satellite shape the composition work kept hunting for, and T-214's breadth-dilution verdict does not cover it.
- **But it is EXPLORATORY** — the single-bull-era sample cannot be deployment evidence. This EARNS a real forward look, not a flag-flip.
- **Recommended next step (a decision for the director/user, not taken here):** treat BTC-as-5%-trend-satellite as a **paper-track / forward-validation candidate** alongside the deploying sleeve — the honest test is whether the trend rule exits the NEXT winter OOS and whether the lift survives a non-bull BTC regime. Pre-register that forward test; do NOT integrate into the deploying sleeve on this sample.

**The last uncovered asset closes with evidence: BTC is the most promising composition addition found — and the most sample-fragile. Both are true.** N_trials += 1.

**T-272 done.**
