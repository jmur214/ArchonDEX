# T-241 — moonshot probe C1 (concentration): VERDICT

**Date:** 2026-06-26 · **Agent:** C · Branch `feature/moonshot-c1-concentration-t241`
Pre-registration: `moonshot_c1_prereg_t241_2026_06_26.md` (locked before any result was read).

## TL;DR — **H0. Concentration does NOT surface an upside half; it amplifies beta/noise and HURTS.**
Concentrating the edge book into the top-K=10 highest-conviction names (conviction-weighted, gross-preserved) does **not** extract the alpha the diversified book might cancel. On every window measured, C1 is **worse** than the diversified base, its idiosyncratic alpha is **negative and statistically insignificant**, and its residual exposure is concentrated **market beta**. This is the pre-registered clean-H0 deliverable: **the equity book has no extractable upside half via concentration.** The honest ceiling stays "trend sleeve (T-236) + the robo's own return"; the moonshot frontier moves to NEW DATA (C4) or is conceded.

## Build (default-OFF, canon-safe — the probe is shipped, just OFF)
`PortfolioPolicy._apply_concentration` (policy.py): top-K by conviction = |combined signal score| over the WHOLE book, conviction-weighted, gross preserved (no leverage — selection, not gross), OVERRIDES the allocator. Gated `concentration_enabled` (default False).
- **OFF canon byte-identical:** 2022 `trades_canon_md5 = 80b501a8…` == baseline.
- **ON fires + differs:** `71d06e39…`; logs `concentrated 108→10 conviction names (gross 1.000 preserved)` on all 250 bars.
- 10 unit tests + 60 engine_c portfolio/contract tests green; doc_lint green.
- **Finding:** the prod `mean_variance` allocator already concentrates to ~5 names per bar — so a top-K-of-the-allocator-output subset is a no-op for K≥5. C1 therefore ranks the FULL ~108-name conviction set and overrides the allocator. (This also means the "diversification that cancels alpha" the paradox warns of lives in the ADAPTIVE/inverse-vol path, not the already-concentrated prod MVO.)

## Gauntlet — 2022 (single bear year, 0.99y)
| series | Sortino | ci_low | MaxDD | CAGR | upCap | dnCap | mSkew |
|---|--:|--:|--:|--:|--:|--:|--:|
| 60_40 robo | −1.749 | −4.868 | −20.9% | −16.7% | 1.00 | 1.00 | 0.45 |
| schwab_like robo | −1.697 | −4.798 | −16.4% | −12.6% | 0.76 | 0.75 | 0.42 |
| **BASE (diversified-MVO)** | **+1.016** | −2.099 | −25.8% | **+10.8%** | 1.02 | 0.73 | 1.27 |
| **C1 (top-K concentration)** | **−0.375** | −3.659 | −23.5% | **−6.7%** | 0.71 | 0.64 | 0.18 |
| C1 + trend sleeve (PAIR) | −0.767 | −4.061 | −14.7% | −5.8% | 0.39 | 0.38 | 0.41 |

**Concentration HURT:** C1 Sortino +1.016 → −0.375, CAGR +10.8% → −6.7% vs the base. The PRIZE table shows C1+sleeve "winning" both robos on terminal wealth AND MaxDD — but that is a **bear-year cushion artifact** of the TREND SLEEVE de-grossing (everyone lost in 2022; C1+sleeve lost less), NOT a concentration win — **C1 alone lost.**

## beta-or-edge (HAC factor decomposition, FF5+Mom) — the key alpha-vs-noise test
| book | alpha_ann | t_HAC | verdict | MktRF β (t) |
|---|--:|--:|---|--:|
| BASE | +19.54% | **1.02** (p=0.31) | insignificant (closet beta) | +0.687 (9.46) |
| **C1** | **−2.91%** | **−0.19** (p=0.85) | **negative + insignificant — pure beta/noise** | +0.547 (6.91) |

C1's idiosyncratic alpha is **negative** and **nowhere near** the t≥2.0 H1 bar. Its surviving exposure is concentrated **market beta**. Concentration didn't surface alpha — it removed the diversification that was muting the base's beta-noise and made the book strictly worse.

## Multi-regime window — 2019–2023 (COVID crash + 2021 bull + 2022 bear + 2023 recovery)
**In flight at write-time** (5-yr base+C1 local runs, ~20–25 min each; the full 26yr cycle deadlocks per T-165). This is a robustness confirmation, NOT a gate-changer: the 2022 + factor-decomposition evidence already establishes a **negative, insignificant** idiosyncratic alpha (t = −0.19) — a multi-regime window cannot convert a negative-alpha, lower-Sortino concentrated book into a t≥2.0 edge. If/when it lands it is appended here; the H0 verdict stands on the evidence above regardless.

## Verdict against the pre-registered gate
- PRIZE (C1+sleeve beats BOTH robos on BOTH terminal wealth AND MaxDD, full-cycle): the only "win" seen is a single-bear-year sleeve artifact; **not a concentration win**, and not on the full cycle.
- alpha t ≥ 2.0: **FAILED** decisively (t = −0.19, negative).
- ⇒ **H0 accepted.** Concentration is not the upside half. **N_trials += 1** (K=10, conviction-weighted).

## Honest limitations
- Windows are 2022 (+ 2019–2023); the full 26yr cycle deadlocks locally (T-165) and a 30h cloud cell is being avoided. The 2022 base leans on SHORTS (un-executable in a cash Roth per T-230) — but C1 is *worse* than that already-generous base, so the H0 direction is robust to it. A full-cycle cloud confirmation would tighten the CI but is very unlikely to overturn a negative-alpha, lower-Sortino result. **Reported as H0 per the pre-registration's clean-H0 clause.**
