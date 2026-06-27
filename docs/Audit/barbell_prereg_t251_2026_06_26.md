# T-251 — barbell composer (convexity-per-carry): PRE-REGISTRATION (locked BEFORE measuring)

**Date:** 2026-06-26 · **Agent:** C · Branch `feature/barbell-composer-t251`
Pre-registered per `[NN-MBL]` / `[NN-SHARPE-CI]` and the CORRECTED methodology (fresh-eyes brief, 2026-06-26 / memory `feedback_measurement_methodology_corrections_2026_06_26`). Method + win-condition + N_trials declared before any result is read.

## The question
Does re-framing to a BARBELL — a near-zero-cost SAFE CORE + a small CONVEX SATELLITE — beat the robo on the ASYMMETRIC objective (convexity per unit carry, net of the robo's cash-drag), on BOTH wealth and drawdown, or at least a *dominating* shape improvement (not just a defensive slide)? It's the brief's #1 (~35-45% prior) — highest-conviction because it's STRUCTURAL (shape), not an alpha bet, and exploits the Roth's two real edges (zero tax-drag, free liquid-ETF turnover).

## Method (ONE config — pre-registered, NO sweep)
`BarbellComposer` (extends the T-248 `StrategyRiskParityComposer`):
- **SAFE CORE:** plain **inverse-vol** over {SPY, AGG, GLD}, 60-bar rolling vol, causal (yesterday's weights). PLAIN inverse-vol, **not HRP** — the brief's defensible default (with 3-4 sleeves HRP buys nothing; confirms T-248).
- **CONVEX SATELLITE:** the trend overlay sleeve (`core/trend_overlay.sleeve_returns`, 105-bar lookback — the T-204/T-236 sleeve), weight **0.15** (the midpoint of the brief's 10-20% band — pre-registered, single value, no sweep).
- **equity vol-target:** OFF (Engine-B's conditional vol-targeting is T-252, not landed; the toggle is FAIL-CLOSED / B-gated here).
- barbell = 0.85 × inverse-vol core + 0.15 × trend satellite.

## Costs / substrate (liquid-ETF, NOT institutional)
- Expense-ratio drag on EVERY ETF holding (SPY 0.0945%, AGG 0.03%, GLD 0.40% annual), applied identically to barbell, core, AND both robos.
- Trading cost **1.5 bps** one-way on the trend satellite's signal turnover (the active leg) + monthly-rebalance turnover.
- Robo cash earns **RF = 4%** (fair — the "cash-drag" is the opportunity cost of the 20% idle allocation, NOT a zero-return strawman; net of that real drag).
- Substrate: stooq SPY/AGG/GLD daily, **2005–2026 (~21y, multi-regime: GFC / 2011 / 2018 / COVID / 2022)**. Fully analytic over return series; no new backtest.

## Win condition (pre-registered) — Sortino is a SCORECARD, not an optimization target
Report **both** bootstrap-CI **Sortino** AND **Sharpe** (block-bootstrap ci_low, 1000 iter, seed 0), MaxDD, CAGR, Calmar, up/down-capture, vs both robos (60/40 + schwab_like). The barbell PASSES iff EITHER:
1. it beats **both** robos on **both** wealth (CAGR) AND drawdown (MaxDD), net of all costs + cash-drag; **OR**
2. a **dominating shape improvement** — higher Sortino AND higher Sharpe at equal-or-lower MaxDD than both robos (not merely a lower-return/lower-DD defensive slide).
A defensive slide (lower DD bought with lower return, no Sortino+Sharpe domination) is a NULL by this gate.

## MBL / N_trials
ONE config (no satellite-weight or vol-rule sweep — sweeping = multiple testing → N_trial inflation). **N_trials += 1.** MBL checked at effective-N on the ~21y window.

## Honest framing
It's a SHAPE bet; the ~35-45% prior is the best we have BECAUSE it's structural, not alpha. Construction/shape cannot manufacture alpha that isn't there — but unlike T-241 (concentration) and T-248 (HRP-over-2-sleeves), the barbell changes the RETURN DISTRIBUTION (convex satellite + diversified low-carry core), which is exactly what the asymmetric objective rewards. A clean result either way is the deliverable.
