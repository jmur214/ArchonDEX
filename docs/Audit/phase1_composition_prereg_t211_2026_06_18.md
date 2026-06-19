# T-211 — Phase-1 composition: PRE-REGISTRATION (lock BEFORE the run)

**Date:** 2026-06-18
**Agent:** C. Pre-registered BEFORE any measurement, per CLAUDE.md (MBL/DSR discipline — hypothesis + threshold + N_trials declared up front; no goalpost-fishing).

## The question
Does ENGINEERING THE SHAPE of the (closet-beta) base book — cut the drawdown + the turnover cost — beat the Schwab robo on **risk-adjusted / tail / after-tax** terms, even though both diagnostics this week say the honest base does NOT beat the robo on raw return? The whole Phase-1 bet.

## Hypotheses
- **H1 (the bet):** the Phase-1 composition clears the robo deploy gate (`evaluate_deploy_readiness`, T-203) — **Roth-primary, after-tax, crisis-tested** — on `ci_low(Sharpe) > ci_low(Sharpe_robo)` OR a **≥20% shallower MaxDD**, vs BOTH robo proxies (60/40 + schwab_like), with `full_cycle_tail_verified=True` (the window must include dotcom/GFC/COVID/2022 — not a bull window).
- **H0 (a valid outcome):** it does not clear the gate → the honest, evidence-based **"the money stays in the robo."** Promote nothing; this is a measurement. H0 is a legitimate result, not a failure.

## Pre-registered configuration (ONE cell — the E-best composition)
`phase1_composition_enabled=True` with: `phase1_trend_lookback_days=105` (EW SPY/AGG/GLD 5-month long/flat — E/T-204 best), `phase1_quality_haircut=0.5` (defensive quality tilt + high-IVOL exclusion, A/T-205), `position_buffering_enabled=True` (T-148 lower-turnover). Allocator `mean_variance` (the designated prod allocator). **Vol-target EXCLUDED** (Engine B, propose-first, B/T-212 — the v2 increment).

## Substrate (the honest, apples-to-apples bar)
- **PIT universe** `use_historical_universe=True` (survivorship-corrected, D/T-207).
- **Realistic retail costs** `slippage_extra.realistic_retail_costs=True` (cap-tier spreads, D/T-210).
- **Full-cycle, crisis-inclusive** window (target 2000–2025; the gate REQUIRES the tail be crisis-tested — a bull window auto-fails `full_cycle_tail_verified`).
- **Block-bootstrap ci_low** (Politis-White, the project standard). Both `base` AND `composition` run on the IDENTICAL substrate (apples-to-apples).

## Decision rule (locked)
Run `base` and `composition` → feed each equity curve to `evaluate_deploy_readiness(account="roth")` (+ `account="taxable"` as the secondary diagnostic) AND `FactorRiskModel.is_it_beta_or_edge()`. **H1 accepted iff** the composition's verdict is `DEPLOY` (Roth, passed=True, full_cycle_tail_verified=True). We EXPECT `is_it_beta_or_edge() == "beta"` — that is FINE; the thesis is *better-shaped beta*, not orthogonal alpha. A "beta" verdict does NOT reject H1.

## N_trials accounting
This pre-registers **N_trials += 1** against the PIT × realistic-cost substrate (one composition configuration, declared before unblinding). The local first-cut (a tractable crisis window, for signal/plumbing) is EXPLORATORY — it does NOT count as a deployment trial and no deploy claim rests on it. If the cell fails and a different composition config is tried, that is a NEW pre-registration (a new N_trial), not a re-read of this one.

## Compute plan
Local first-cut on a tractable crisis-inclusive window (signal + plumbing verification), then the canonical full-cycle PIT × realistic-cost run as a **cloud cell** (compute-bound). Canon-unchanged proof (mode OFF) precedes everything.
