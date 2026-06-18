---
task_id: T-2026-06-18-206 (Task 2)
title: SPEC — vol-target re-enablement (sigma-floor guard FIRST) + pre-registration
date: 2026-06-18
worker: Agent B
branch: feature/risk-model-voltarget-design-t206
status: SPEC / PROPOSE-FIRST (Engine B — director reviews; NO autonomous flag-flip)
---

# Vol-target re-enablement — spec (T-206 Task 2)

## 0. Why (and the honest caveat)
Phase-1 thesis: the book is a **low-β (0.33) long carry whose −33% MDD, not its return, is what loses to the robo** (Task-1 diagnostic). Vol-targeting the **beta EXPOSURE** (Moreira-Muir / Harvey et al.: scale exposure inversely to realized vol) is the cleanest already-wired lever to cut that tail and lift risk-adjusted return (~0.40→0.50 gross). **Honest caveat — why this is NOT a repeat of the refuted T-055:** T-055 vol-targeted the *dead edge book* at the *signal* level and failed (−0.214 on 12yr). THIS targets the **whole-book beta exposure scale** (a different object, a different test). The lift is **gross**; net ~0.35-0.45 after de-gross re-entry slippage — **fragile, must be netted, not assumed.**

The flag (`portfolio_vol_target_enabled`, default `False`) and the machinery (`engines/engine_b_risk/vol_target.py`: `scale = clamp(target_vol/realized_vol, floor, ceiling)`, estimators rolling/ewma/yang_zhang, regime-aware multipliers) already exist. **This spec does NOT flip the flag** — it specs the precondition guard + the A/B for the director.

## 1. Task 2a — the sigma-floor guard FIRST (the hard precondition)
**The T-150/T-153 defect:** the realized-vol estimator emits **σ < 2% annual on ~14% of bars** (min observed **3e-06**), which sails past a naive `<= 0` guard → `target/σ` explodes → the book gets levered to the ceiling on near-zero-vol bars = a blow-up / churn machine. A bare `== 0` guard is insufficient (the FP-tolerance rule: `< 1e-12` etc.).

**Status — the guard is already BUILT but default-OFF.** `vol_target.py` carries the T-153 "Fix A" sigma-floor: `vol_floor_enabled` (default **False**), `vol_floor_annual` (0.02), `vol_floor_full_sample_frac` (0.0). When enabled, realized_vol is floored to `max(vol_floor_annual, vol_floor_full_sample_frac · full-sample σ(history))` **BEFORE** the target/σ divide.

**Spec (precondition before ANY vol-target paper run):**
1. **Mandate `vol_floor_enabled=True`** whenever `portfolio_vol_target_enabled=True` — wire an assertion/validator so vol-target cannot be enabled with the floor off (fail-loud, not silent). This is the structural fix (cf. the T-194 fail-closed discipline).
2. **Tune the floor:** pre-register the floor as `max(vol_floor_annual=0.02, vol_floor_full_sample_frac · σ_full)` with `vol_floor_full_sample_frac ∈ {0.0, 0.25, 0.50}` (a fraction-of-full-sample floor adapts to the book's own vol scale; absolute-only risks being too low/high across regimes).
3. **VALIDATION (the acceptance gate for 2a, runnable as measurement):** over the full 26yr book, assert (a) **0 bars** have post-guard effective σ below the floor; (b) the realized leverage `scale` stays within `[floor, ceiling]` with **no spike to ceiling driven by σ→0** (histogram the scale; confirm the ~14% low-σ bars no longer pin the ceiling); (c) canon-md5 of a vol-target-OFF run is **byte-identical** with the guard code present-but-OFF (default-OFF safety, the standing rule). Only after 2a passes does 2b run.

## 2. Task 2b — the A/B (pre-registered grid)
Flip `portfolio_vol_target_enabled=True` (guard ON) and sweep, vs the vol-target-OFF baseline (the canonical re-anchor book), full 26yr + walk-forward OOS, AWS Batch + block-bootstrap CI, census-gated, cov-pin:
- **estimator ∈ {rolling-60d, ewma-λ0.94, yang_zhang}** (pre-registered; `yz_vol.py` is the YZ path).
- **target_annual_vol ∈ {0.10}** (retail-fit; hold fixed unless 2a tuning says otherwise).
- **floor/ceiling ∈ {(0.5, 2.0)}** primary; sensitivity {(0.7, 1.5)}.
- **regime_aware ∈ {off, on}** (the cautious/stressed multipliers 0.85/0.60). NOTE: regime_aware consumes the regime layer — if used, it must read the **validated HMM p_crisis** (the audit: the one validated signal isn't wired to sizing), NOT the coarse 5-axis advisory that failed in April. Default this A/B arm to regime_aware=OFF to isolate the pure exposure-scaling effect first.
- **De-gross slippage (do NOT assume away):** every degross/regross is turnover → model the round-trip cost (the existing exec cost model + the T-148 finding that turnover is a TAX lever first). Report BOTH gross and **net-of-slippage-AND-after-tax** Sharpe. The ~0.40→0.50 gross lift must survive to a net ~0.35-0.45 to matter.

## 3. Task 2c — pre-registration (bound BEFORE the run)
- **H1:** vol-targeting the beta exposure (guard ON) clears `evaluate_deploy_readiness` vs ≥1 robo proxy **AFTER-TAX**, DSR/n_trials-penalized (cumulative honest-N ~260+), walk-forward OOS — i.e. a net-of-slippage-after-tax risk-adjusted improvement (Sharpe and/or MDD/tail) over the OFF baseline whose ci_low > 0.
- **H0:** the gross lift does not survive de-gross slippage + after-tax + the DSR penalty (the fragile-net prior; plausibly the outcome).
- **Primary metric:** Δ(net-after-tax Sharpe) ci_low > 0 AND/OR Δ(MDD) materially better (the −33% tail is the robo-losing axis), vs the robo bar.
- **N_trials:** the estimator×floor/ceiling×regime grid = the pre-registered cell count (each adds to honest-N — keep the grid SMALL and pre-registered, not exploratory, per the MBL discipline). Log it.
- **Window:** 26yr (MBL-clearing) + walk-forward OOS folds; block-bootstrap CI; census-gated (measured-mode, T-194); cov-pin.

## 4. Sequence + boundary
2a (guard mandate + validation) → 2b (A/B) → 2c verdict. **All Engine B → PROPOSE-FIRST:** this spec is for director review; flipping `portfolio_vol_target_enabled` / changing risk sizing is a separate director-gated act. Default-OFF stays byte-identical (canon-md5 across the toggle). Composes with the Task-1 factor-VaR overlay and the de-gross/kill-switch (vol-target is NEVER a risk override — the drawdown-halt still binds).
