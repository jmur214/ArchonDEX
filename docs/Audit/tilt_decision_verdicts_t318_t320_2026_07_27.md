# T-318 + T-320 — the TILT DECISION verdicts (frozen pre-regs, run together)

**Date:** 2026-07-27 · **Agent:** C · Branch `feature/tilt-decision-runs-t318-t320` · **N_trials += 2** (one per family)
Both frozen families run on ONE engine so the value and aggressive halves are directly comparable (the director's benchmark ruling: **FF market TR primary + T-306 deep-SPY cross-check, applied to both**). **Decision-support, NOT alpha claims.** Regret leads every table. Reproducer: `scripts/tilt_decision_measure_t318_t320.py`.

## Two measurement defects caught and fixed before reporting (disclosed, per the silent-wrongness doctrine)
1. **Month-stamp mismatch:** FF stamps month-START, yfinance month-END → the raw join produced **zero overlap**, which printed a blank Nasdaq arm that would have read as "measured, found nothing." Fixed by normalizing every leg (`_mnorm`) and adding a **fail-loud guard** — `blend()` now RAISES on an empty overlap rather than reporting one.
2. **Price-vs-total-return bias AGAINST growth:** `^IXIC` is a PRICE index; comparing it to a TR benchmark silently penalizes growth by its dividend yield (~1%/yr ≈ +48% over 40yr). Fixed by adding the **FF total-return growth leg** (same library/construction as the benchmark) as the apples-to-apples measurement, with `^IXIC` retained as the *popular tech-concentration* version, caveat printed inline. **Both agree on direction** — the correction did not rescue growth.

---

# T-318 — SMALL-VALUE TILT: nominal win, no significance, brutal post-publication decay
| arm | regret (worst 15yr rel DD) | $/10k | recover | win40y | N | log-wealth 95% CI |
|---|--:|--:|--:|--:|--:|---|
| 80/20 SPY/small-value | −14.7% | $1,467 | 6.0y | 100% | 720 | [−0.066, +0.735] **straddles 0** |
| 70/30 SPY/small-value | −21.1% | $2,113 | 6.0y | 100% | 720 | [−0.088, +1.105] **straddles 0** |
| **80/20 DECAYED (post-1993)** | **−25.1%** | **$2,512** | **NEVER (≥42.2y)** | **65%** | 720 | [−0.440, +0.361] straddles 0 |

**The decay is the finding: the measured SV premium fell from +7.07%/yr (pre-1993) to +2.36%/yr (post-publication) — a −4.71%/yr haircut, i.e. ~⅔ of the premium gone.** On the decayed premium the tilt wins only 65% of windows, its worst 15-yr relative drawdown deepens to −25%, and it **never recovers the relative high**.

**Verdict vs the frozen prior (~50-55% nominal, ~15-20% CI-excludes-zero):** the prior **understated the nominal win rate** (100% of overlapping full-sample windows) and was **right about significance** (CI straddles zero at both weights). Honest reading: **a real historical premium, decayed by two-thirds since publication, with no statistically significant edge and a 6-year (undecayed) to never (decayed) regret horizon.** A "small permanent satellite, eyes open" — exactly as framed, with eyes open to the decay.

---

# T-320 — AGGRESSIVE TILTS: momentum is the only significant arm; growth is refuted; quality has the smallest regret
| arm | regret | $/10k | recover | win40y | N | log-wealth 95% CI |
|---|--:|--:|--:|--:|--:|---|
| **80/20 SPY/momentum (long-only)** | **−5.7%** | **$568** | 6.1y | 100% | 714 | **[+0.139, +0.565] CI EXCLUDES 0** |
| **70/30 SPY/momentum (long-only)** | −8.3% | $834 | 6.1y | 100% | 714 | **[+0.226, +0.861] CI EXCLUDES 0** |
| *[MOM long-SHORT factor + rf]* | *−37.6%* | *$3,756* | *NEVER (≥17.3y)* | *87%* | *714* | *straddles 0 — **academic upper bound, NOT investable*** |
| 80/20 SPY/growth (FF, TR) | −13.1% | $1,311 | **NEVER (≥80.0y)** | **7%** | 720 | [−0.214, +0.107] straddles 0 |
| 70/30 SPY/growth (FF, TR) | −18.5% | $1,850 | **NEVER (≥80.0y)** | 10% | 720 | straddles 0 |
| 80/20 SPY/Nasdaq (price idx) | −14.8% | $1,482 | NEVER (≥54.1y) | **0%** | 184 | straddles 0 *(price-index caveat)* |
| 80/20 SPY/quality (high-OP) | **−4.1%** | **$414** | 25.1y | 100% | 276 | [−0.024, +0.136] straddles 0 |
| 70/30 SPY/quality (high-OP) | −5.8% | $577 | 23.6y | 100% | 276 | [−0.017, +0.222] straddles 0 |
| **80/20 momentum DECAYED** | −12.3% | $1,227 | NEVER (≥20.3y) | 88% | 714 | [−0.118, +0.307] **straddles 0** |
| 80/20 quality DECAYED | −3.6% | $357 | 18.2y | 100% | 276 | [+0.003, +0.163] CI excludes 0 *(barely)* |

### The four findings
1. **Momentum is the only arm whose full-sample CI excludes zero — at BOTH weights — and it carries the SMALLEST regret of the aggressive menu (−5.7%, $568 per $10k, recovered in 6.1y).** That **beats its ~40-50% prior.**
2. **But the decay kills the significance:** the measured momentum premium halved post-1993 (+6.25% → +3.02%/yr) and on the decayed premium **the CI straddles zero, 12% of windows lose, and the relative high never recovers.** Momentum's significance rests on pre-publication data — the honest caveat that must travel with the result.
3. **Reporting momentum both ways was load-bearing.** The deployable long-only leg has a −5.7% regret; the academic long-short factor has **−37.6% and never recovers**. The factor's famous crash profile (−64.5% in 1932, −52.9% in 2009) lives mostly in the SHORT leg — a long-only holder does not experience it. Quoting the factor as if investable would have been badly wrong in *both* directions (overstating the crash, overstating the premium).
4. **Growth/tech is REFUTED, as the prior predicted (~15-25%):** the TR growth leg wins **7-10%** of 40yr windows, the price-index Nasdaq version **0%**, and *neither ever recovers its relative high* (≥54-80 years). Combined with the pre-registered adversary measurement — **QQQ −81.1% drawdown, 14.6 years underwater, −68.5% relative drawdown never regained since Feb-2000** — the popular reach for "aggressive" buys concentration risk, not a premium. **This is the arm where measurement most clearly beats vibe.**

### Quality × leverage — HISTORICAL CONTEXT ONLY (T-315's static-leverage door is CLOSED)
Per the director's framing, this is *"what leverage would have needed,"* **not a live proposal**: T-315 found no static-leverage arm CI-beats at any L (the 1.25× arm significantly loses). Quality's standalone edge is the smallest of the menu (measured premium +1.15%/yr pre-2013 → +1.49%/yr post — the one leg that did **not** decay), so a levered quality book would have needed the leverage to add more than its financing + path cost on a ~1.2-1.5%/yr base. Given T-315's result that leverage does not clear its own cost, **quality's robustness does not rescue leverage, and leverage does not amplify quality into significance.** Recorded so the pairing is not re-proposed as though untested.

### Deployable cross-check (T-306 deep SPY, 1993-2026 — the wrapper era)
regret: quality **−1.3%** ($135) < momentum −5.0% ($497) < small-value −13.3% ($1,332) < growth −15.4% ($1,544). The window is too short for 40yr windows (win40y = n/a — stated, not fabricated), but the **regret ordering matches the deep result exactly**: quality and momentum are the low-regret tilts; growth is the highest-regret.

---

## What these results do NOT license (pre-stated, honored)
No in-house-edge claim (external, replicated, published factors). No timing/sizing rule on any tilt. **No change to the deploying sleeve — it is untouched by every outcome.** No stacking arms on a positive CI. The 100% win rates are on **heavily overlapping** windows (~100yr ⇒ only ~2.5 independent 40yr windows) — **the block-bootstrap CI is the honest significance test, and it is the number to read.**

## Honest bottom line for the user's decision
- **Momentum (long-only)** is the best-evidenced aggressive tilt: significant full-sample, smallest regret, 6-year worst regret horizon — **but half its premium has already decayed and the decayed variant is not significant.**
- **Quality** is the *gentlest* tilt (smallest regret at $414/$10k) and the only premium that did not decay, but its standalone edge is small and its history shortest.
- **Small-value** is a real historical premium two-thirds decayed; nominal-win-everywhere, significant-nowhere.
- **Growth/tech is the one to avoid** — it loses in 90-100% of long windows and its regret has never been repaid in 26 years.

**T-318 + T-320 done.** N_trials += 2.
