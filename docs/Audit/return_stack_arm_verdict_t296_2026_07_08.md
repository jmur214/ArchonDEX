# T-296 RUN — return-stack (synthetic-RSST) composition arm: VERDICT

**Date:** 2026-07-08 · **Agent:** C · Branch `feature/return-stack-run-t296` · **N_trials += 1**
Ran the frozen pre-reg (`return_stack_scope_prereg_t296_2026_07_08.md`, DIRECTOR FREEZE section). MF proxy = AQR TSMOM (frozen #1, construction-audit passed), scaled to DBMF vol; fair T-255 harness, monthly.

## TL;DR — H0 / FAIL the gates. The MF-stack-under-our-gate is REDUNDANT: RSST's internal trend + our trend gate INTERFERE, not compound. ΔSortino straddles 0; the Δwealth "win" is entirely the hypothetical MF factor's +5.3%/yr over-capture (deflates to ~0 at live-fund reality). → consequence rule = **close the return-stack-under-sleeve door**; the parked CTA question is untouched.

## Proxy audit + faithfulness basis (frozen requirement)
- **AQR TSMOM construction audit: PASSED** — the Moskowitz-Ooi-Pedersen diversified time-series-momentum factor, 1985+ monthly, across equities/FI/commodities/FX, hypothetical research portfolio, excess-over-cash. The right *nature* to test "more-assets-under-trend" (far better than our 3-asset long/flat overlay, which was the fallback).
- **Faithfulness basis: +5.3%/yr** (synth `SPY_TR + AQR_scaled` vs real RSST, 31mo overlap, corr 0.875) — ABOVE the ±4-5% band the freeze assumed. The hypothetical frictionless factor **over-captures ~+5%/yr vs the live fund** (DBMF/real MF industry realized far less). **The WEALTH gate is therefore basis-inflated and untrustworthy — the verdict rests on ΔSortino + the double-trend shape.**

## Gauntlet — 2001-2025 (294mo, monthly, EXPLORATORY)
| strategy | Sortino (ci_low) | MaxDD | CAGR | $10k → |
|---|--:|--:|--:|--:|
| PLAIN sleeve (SPY/BOND/GOLD) | 2.096 (1.174) | −8.6% | 6.2% | $43,824 |
| **ARM: synth-RSST equity leg** | **2.082 (1.293)** | −8.8% | 7.6% | $59,417 |
| T-284 offense (2× SPY) | 1.886 (1.088) | −14.8% | 8.3% | $69,686 |

**Pre-registered gates — paired Δ(ARM − baseline) 95% CI:**
- vs plain sleeve: **ΔSortino [−0.25, +0.32] → straddles 0**; Δwealth [+0.05, +4.15] **(basis-inflated — the +5.3%/yr AQR over-capture ≈ the entire 6.2→7.6% CAGR gap; deflates to ~0 at live capture)**.
- vs T-284 offense: ΔSortino [−0.25, +0.44] → straddles 0; Δwealth [−4.82, +1.44] → straddles 0.

**No significant gate pass on either axis that survives the basis.**

## The double-trend interaction (the mechanism — the actual finding)
| window (in-window MaxDD) | PLAIN | ARM | offense |
|---|--:|--:|--:|
| 2008 GFC | −2.3% | −2.3% | −2.3% |
| 2015-16 chop | −5.1% | **−4.2%** | −7.6% |
| 2022 | **−5.2%** | −7.5% | −8.5% |

- **2015-16 chop: the MF stack HELPS weakly** — ARM −4.2% vs plain −5.1% MaxDD, chop total return −0.4% vs −1.2% (+0.8pp). The evidenced "more-assets-under-trend fixes trend's chop weakness" shows up — but small.
- **2022: the MF stack HURTS** — ARM −7.5% vs plain −5.2%. This is the double-trend INTERFERENCE: our long/flat gate reads the *combined* synth-RSST price (SPY + MF), and in 2022 the MF up-trend MASKED SPY's decline → the gate stayed "on" and protected LESS than it did for the plain SPY leg. Stacking a fund that already has an internal trend/MF overlay UNDER our trend gate is **redundant and muddling** — the two trend layers don't compound; our gate can't cleanly protect the equity when the MF component hides the equity trend.
- (Monthly resolution shows COVID as 0.0% for all — an honest limitation of the monthly frequency the AQR factor forced.)

## Verdict & consequence
**FAIL the pre-registered gates (H0).** ΔSortino straddles 0 vs both baselines; the Δwealth advantage is an artifact of the hypothetical MF factor over-capturing ~+5%/yr vs the live fund; and the double-trend interaction INTERFERES (weak chop help, offset by reduced crisis protection in 2022) rather than compounds. Per the frozen **consequence rule → FAIL branch: close the return-stack-under-sleeve door** — RSST held as the equity leg under our trend gate is a null. **The parked micro-futures CTA question is UNTOUCHED** (different evidence — the arm tested RSST *under our gate*; it could not cleanly test the standalone MF diversifier, both because of the gate interference and because a faithful level-replica isn't freely buildable — the ±5%/yr hypothetical basis).

**Honest scope of the kill:** this closes "return-stack fund as the gated equity leg of our sleeve." It does NOT test (and so does not kill) RSST as a *standalone, un-gated* defensive-equity holding — but that config abandons the whole premise (combining with our validated sleeve), and its level can't be validated free anyway. N_trials += 1.

**T-296 run done.**
