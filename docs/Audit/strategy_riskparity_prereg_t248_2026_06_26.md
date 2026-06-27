# T-248 — strategy-level risk-parity composition: PRE-REGISTRATION (locked BEFORE measuring)

**Date:** 2026-06-26 · **Agent:** C · Branch `feature/strategy-riskparity-t248`
Pre-registered per `[NN-MBL]` / `[NN-SHARPE-CI]` — method + win-condition + N_trials declared before any result is read.

## The question
Does allocating risk budget ACROSS SLEEVES (base, trend, …) via HRP — instead of naive equal-weight — improve the composed frontier (higher Sortino at equal-or-lower MaxDD)? This is the #2 free avenue: a CONSTRUCTION multiplier on existing sleeves, **not** a new alpha.

## Method (ONE — pre-registered, no sweeping)
`StrategyRiskParityComposer.risk_budget_weights`: **HRP** (Ledoit-Wolf shrinkage cov, single-linkage, recursive bisection — the existing `HRPOptimizer`, reused asset-agnostically) over the SLEEVE return matrix {base, trend}. Static full-sample risk-budget weights, long-only, sum 1.0. Compared against the **naive equal-weight** baseline (the default-OFF behavior). Default-OFF; the equity-book canon is untouched (this composer is above the per-ticker path).
**Sweeping construction methods = multiple testing → N_trial inflation. I pre-register HRP only.** A second method (e.g. min-variance, ERC) would be a new trial.

## Win condition (pre-registered)
**Frontier improvement**, net-of-cost / after-tax, vs both robos:
- HRP composition has **higher Sortino at equal-or-lower MaxDD** than the naive equal-weight composition, AND
- the composition beats **both** robos (60/40 + schwab_like) on the Sortino/MaxDD frontier.
Report Sortino + block-bootstrap `ci_low`, MaxDD, CAGR, up/down-capture for naive vs HRP vs both robos.

## Honest framing (the result is bounded by the sleeves)
Better construction **cannot manufacture alpha that isn't there.** If the sleeves are H0 / downside-only (the base book is H0 per T-215; the trend sleeve is a downside-shaped risk-return TRADE per T-236/238), the BEST this does is **tidy the frontier** — a modest Sortino/MaxDD improvement, not a robo-beat on wealth. **Its real value is as the MULTIPLIER on CARRY** once that sleeve lands (A/T-247, Wave 2) — a third, differently-correlated sleeve is where cross-sleeve risk-parity earns its keep. A null/marginal result on {base, trend} alone is expected and is reported as such.

## N_trials
ONE method (HRP, static full-sample, {base, trend}). **N_trials += 1.**

## Measurement substrate
- base sleeve: the 5-yr base equity run (15afff62, 2019–2023 — COVID crash + 2021 bull + 2022 bear + 2023 recovery; census-canonical) `portfolio_snapshots.csv` → daily returns.
- trend sleeve: analytic `core.trend_overlay.sleeve_returns` over the same window.
- robos + metrics: the cached-data gauntlet (`tail_rescore_t234` functions). No new backtest. Window = the intersection.
- Canon proof first: 2022 `trades_canon_md5` == `80b501a8…` (the new module does not touch the book path).
- `factor_neutralize` toggle is built but **FAIL-CLOSED / Engine-B-gated** (FactorRiskModel is a B component) — not exercised here; propose-first to B.
