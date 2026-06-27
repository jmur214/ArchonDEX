# T-248 — strategy-level risk-parity composition: VERDICT

**Date:** 2026-06-26 · **Agent:** C · Branch `feature/strategy-riskparity-t248`
Pre-registration: `strategy_riskparity_prereg_t248_2026_06_26.md` (locked before measuring).

## TL;DR — built (default-OFF, canon-safe). On {base, trend} HRP does **NOT improve the frontier** over naive — it shifts to a more defensive point. **Exactly as pre-registered: the value awaits a third sleeve (carry, Wave 2).**

## Build
`engines/engine_c_portfolio/strategy_composer.py` — `StrategyRiskParityComposer`:
- `risk_budget_weights(sleeve_returns)` — equal-weight when OFF (naive baseline), HRP (reuse `HRPOptimizer`: Ledoit-Wolf, single-linkage) over the sleeve covariance when ON. Long-only, sum 1.0.
- `compose_returns` — blends sleeve return series to the weights, renormalizing per-bar over present sleeves.
- `factor_neutralize` toggle: **FAIL-CLOSED + Engine-B-gated** — `FactorRiskModel` is an `engine_b_risk` component; enabling the toggle raises `NotImplementedError` (propose-first, do not make the cross-sleeve risk decision unilaterally). `[NN-FAIL-CLOSED]` / `[NN-ENGINE-BOUNDARIES]`.
- Default-OFF; NOT wired into the per-ticker book path → equity canon untouched.
- 7 unit tests + 76 engine_c portfolio/composer/contract tests green; doc_lint green.

## Frontier — naive vs HRP over {base, trend}, 2019–2023 (5.0y multi-regime)
Sleeve weights — naive {base 0.50, trend 0.50} | HRP {base **0.385**, trend **0.615**} (HRP tilts to the lower-vol trend sleeve).

| series | Sortino | ci_low | MaxDD | CAGR | upCap | dnCap |
|---|--:|--:|--:|--:|--:|--:|
| 60_40 robo | 0.888 | −0.122 | −21.7% | 9.5% | 1.00 | 1.00 |
| schwab_like robo | 0.935 | −0.104 | −16.7% | 7.7% | 0.76 | 0.75 |
| base sleeve | 2.231 | 1.005 | −21.7% | 21.2% | 0.73 | 0.53 |
| trend sleeve | 1.014 | 0.006 | −7.5% | 5.3% | 0.33 | 0.30 |
| **NAIVE comp (50/50)** | **2.227** | 0.951 | −13.7% | 13.2% | 0.53 | 0.42 |
| **HRP comp** | **2.102** | 0.867 | −11.8% | 11.3% | 0.48 | 0.39 |

**FRONTIER VERDICT:** HRP Sortino **2.102 < 2.227** naive (NOT higher) at MaxDD **−11.8% vs −13.7%** (lower). HRP does **not dominate** naive — it trades ~0.13 Sortino for ~1.9pts less MaxDD by overweighting the defensive trend sleeve. That is a **frontier MOVE (more defensive), not a frontier IMPROVEMENT**, so the pre-registered win condition ("higher Sortino at equal-or-lower MaxDD") is **NOT met**.

## Why (the pre-registered honest framing held)
With only TWO sleeves — one high-return/high-vol (base) + one defensive/low-vol (trend) — HRP has nothing to exploit beyond inverse-vol tilting, which just slides along the existing frontier. **Construction cannot manufacture alpha that isn't in the sleeves.** Cross-sleeve risk-parity earns its keep only with a THIRD, differently-correlated sleeve — **carry (A/T-247, Wave 2)** — where diversifying the risk budget across three low-correlation return streams can lift Sortino without giving back DD. The composer is built and ready for that.

## Don't over-read the robo "beat"
Both compositions clear both robos on Sortino (2.1–2.2 vs ~0.9) and CAGR (11–13% vs 8–10%) — but that is the **base sleeve carrying it**, and the base is **H0 + un-executable** (T-215: leans on shorts a cash Roth can't do; 2019–2023 is a bull-heavy window flattering it). This is NOT a deployable robo-beat; it is the construction layer faithfully passing through the base's (un-real) edge. The honest deployable read stays: base is H0, trend is a downside-shaped TRADE (T-236/238), and construction over the two does not change that.

## N_trials += 1 (HRP, static full-sample, {base, trend}). No sweep.
A second construction method (min-variance, ERC) would be a new trial — not run, per the pre-registration's no-multiple-testing clause.
