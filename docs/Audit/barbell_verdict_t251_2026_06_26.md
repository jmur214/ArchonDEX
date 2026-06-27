# T-251 — barbell composer (convexity-per-carry): VERDICT

**Date:** 2026-06-26 · **Agent:** C · Branch `feature/barbell-composer-t251`
Pre-registration: `barbell_prereg_t251_2026_06_26.md` (locked before measuring).

## TL;DR — BUILT (default-OFF, canon-safe). The barbell shape-dominates both robos on POINT estimates and is a large, real **drawdown/tail** improvement — but the risk-adjusted edge is **NOT significant** (paired ΔSharpe ci_low < 0 vs both robos) and it **gives back ~1.6%/yr of wealth.** It's a better DEFENSIVE portfolio on the asymmetric objective — the SAME trade as the trend sleeve — not a robust robo-beat. **This confirms the brief: "achievable on drawdown/tail terms: yes; on return terms: low prior."**

## Build
`BarbellComposer` (extends T-248 `StrategyRiskParityComposer`, `engines/engine_c_portfolio/strategy_composer.py`):
- **SAFE CORE:** plain inverse-vol over {SPY, AGG, GLD} (60-bar rolling vol, causal). NOT HRP (brief: HRP buys nothing with 3-4 sleeves; confirms T-248).
- **CONVEX SATELLITE:** trend overlay sleeve (105-bar), weight **0.15** (pre-registered midpoint of 10-20%, no sweep).
- `equity_vol_target` toggle: **FAIL-CLOSED / Engine-B-gated** (T-252 conditional vol-targeting — propose-first; raises if enabled).
- Default-OFF; not wired into the per-ticker book path → equity canon untouched. 5 unit + 81 engine_c tests green; doc_lint green.

## Gauntlet — liquid-ETF, 2005–2026 (20.8y), net ER + 1.5bps turnover, robo cash @ RF=4%
| strategy | Sortino | so_ci | Sharpe | sh_ci | MaxDD | CAGR | Calmar | up | dn |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 60_40 robo | 0.768 | 0.269 | 0.627 | 0.220 | −38.6% | 6.8% | 0.18 | 1.00 | 1.00 |
| schwab_like robo | 0.958 | 0.436 | 0.778 | 0.368 | −28.9% | 6.6% | 0.23 | 0.81 | 0.71 |
| inverse-vol CORE only | 1.025 | 0.459 | 0.812 | 0.392 | −18.2% | 4.9% | 0.27 | 0.48 | 0.32 |
| trend SATELLITE only | 1.076 | 0.553 | 0.881 | 0.457 | −10.8% | 5.7% | 0.53 | 0.52 | 0.31 |
| **BARBELL (85c+15s)** | **1.107** | 0.538 | **0.867** | 0.448 | **−17.0%** | **5.1%** | 0.30 | 0.49 | 0.32 |

## The pre-registered gate is met on POINTS — but fails the CI-aware test (`[NN-SHARPE-CI]`)
Point-estimate shape-domination: barbell > both robos on Sortino AND Sharpe at lower MaxDD → the pre-registered gate (criterion 2) reads PASS. **But `[NN-SHARPE-CI]` requires CI-aware, not point.** The paired block-bootstrap on the DIFFERENCE (barbell − robo, same blocks resampled across both, 1000×, block=20):

| vs | ΔSharpe [ci_low] | ΔSortino [ci_low] | significant? |
|---|--:|--:|---|
| 60_40 | +0.240 [**−0.078**] | +0.339 [−0.076] | NO (barely straddles 0) |
| schwab_like | +0.089 [**−0.201**] | +0.149 [−0.243] | NO (clearly within noise) |

**The risk-adjusted edge over the robos is NOT statistically significant** — decisively so vs the harder schwab_like benchmark (which already holds gold + cash). On a CI-aware reading the barbell does NOT beat the robo on risk-adjusted terms.

## What IS real, and what isn't
- **REAL + large: the drawdown/tail improvement.** MaxDD −17.0% vs −28.9%/−38.6%; down-capture 0.32 vs 0.71/1.00. Over 21y through GFC + COVID + 2022 that is structural, not luck. On the user's chosen ASYMMETRIC (Sortino/tail) objective, the barbell is a genuine improvement.
- **REAL: the wealth give-back.** CAGR 5.1% vs 6.6–6.8% → ~1.6%/yr less terminal wealth. The classic defensive trade (same as the trend sleeve T-236/238).
- **NOT proven: a risk-adjusted or wealth robo-beat.** The Sortino/Sharpe edge is within noise; wealth loses outright.
- **The core does the heavy lifting; the satellite is modestly additive.** Inverse-vol core alone already beats both robos on risk-adjusted+DD; adding the 15% trend satellite moves Sortino 1.025→1.107, MaxDD −18.2%→−17.0%, CAGR 4.9%→5.1% (the convex satellite buys back a little DD AND a little return — correct direction, small size).
- **Caveat — bond-bull tailwind:** inverse-vol overweights the lowest-vol asset (AGG), and 2005–2021 was a structural bond bull. The core's risk-adjusted edge is partly that tailwind (now over); the forward edge is weaker than the backtest.

## MBL
At point Sharpe 0.87 over 20.8y the window clears MBL; at the ci_low (~0.45) it is borderline at full accumulated-N. The barbell is ONE structural, pre-registered config (low effective-N — it does not share the price-machine's search), which is the mitigant per the corrected effective-N methodology. N_trials += 1.

## Honest bottom line
The barbell is a clean, deployable **defensive** structure that does exactly what the brief predicted: it wins on drawdown/tail (already-achievable territory) but its risk-adjusted edge over the robo is within noise and it gives back wealth. **It does NOT unlock the upside half** — same conclusion as the trend sleeve, concentration (T-241), and HRP-over-sleeves (T-248). The asymmetric-objective win is real and worth deploying as a defensive sleeve; a *return*-beat is not here. Consistent with the brief's path: deploy the defensive sleeve, spend remaining budget on the orthogonal free probes (calendar/flow T-250, EDGAR text), not another price/construction variation.
