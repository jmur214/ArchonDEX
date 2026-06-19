# T-211 — Phase-1 composition: the build + the FIRST honest beat-the-robo first-cut

**Date:** 2026-06-18/19
**Agent:** C. THE CONVERGENCE. Pre-registration: `docs/Audit/phase1_composition_prereg_t211_2026_06_18.md` (locked before the run).

---

## 1. The build (Engine C, OFF-default, canon-safe)
`engines/engine_c_portfolio/phase1_composition.py` — an OFF-default post-processor (same contract as dyn-opt/buffering) that shapes the target book when `phase1_composition_enabled=True`:
- **Defensive tilt** (A/T-205): zero the high-IVOL/lottery exclusions + haircut non-quality longs toward the quality set, renormalized (a RELATIVE shift, not a covert de-gross). Engine-C construction tilt — NOT an Engine-B gate.
- **Trend overlay** (E/T-204): scale gross by the EW SPY/AGG/GLD 5-month long/flat exposure scalar (cash when flat) — the drawdown lever; no-lookahead (signal `shift(1)`'d). Verified: exposure **0.0 during the 2008 GFC and 2020 COVID crash**, 0.67 in the 2021 bull.
- Vol-target (Engine B) EXCLUDED (propose-first, B/T-212). Position buffering (T-148, lower-turnover) = the separate Engine-C flag, toggled in the run config.

**Canon-safe OFF:** `phase1_composition_enabled=False` default → branch skipped, module never imported → 2022 `trades_canon_md5 = 80b501a8` == origin/main (bitwise). Layer-1 contract green.

The gate also gained a `w_dbmf=0` self-contained-candidate path: the composition carries its OWN crisis diversifier (the trend overlay), so it is judged DIRECTLY vs robo over its full crisis window, not bolted to a 2019+ DBMF sleeve.

## 2. The first-cut measurement (2007–2012 GFC window, local) — a POSITIVE signal for H1
The canonical full-cycle PIT × realistic run is cloud-bound (§4); the local first-cut is a tractable crisis window for signal + plumbing. All on the standard universe/costs (the PIT × realistic substrate is the cloud cell).

| metric (2007–2012) | base book | **composition** | 60/40 robo |
|---|---|---|---|
| MaxDD | **−39.7%** | **−21.5%** | −36.5% |
| Sharpe | (neg) | 0.243 / gate −0.20 | −0.01 |

- **The trend overlay roughly HALVED the GFC drawdown** (−21.5% vs the un-overlaid −39.7%) and is **41% shallower than the 60/40 robo** (−21.5% vs −36.5%).
- **Through the deploy gate (Roth, after-tax, vs 60/40): DEPLOY** — NOT on Sharpe ci_low (both negative through a crisis window; cand ci_low −1.04 < robo −0.58) but on the **≥20% MaxDD criterion (41% shallower)**, with the tail crisis-VERIFIED (the window is the GFC → `full_cycle_tail_verified=True`).
- **`is_it_beta_or_edge()` = "beta"** (alpha −0.57%/yr, t_HAC −0.18, **market beta 0.22** — low, because the overlay sits out crises in cash). EXACTLY the thesis: **better-shaped (low-beta, tail-protected) beta, not orthogonal alpha** — and that's fine; the win is the shape.

**Read:** the Phase-1 thesis shows up exactly as predicted on the crisis window — the composition wins on the TAIL (cut the drawdown ~half), not the headline (both lose money through the GFC). It clears the gate on the tail criterion.

## 3. Honest H1/H0 — NOT YET the final verdict
This is a **favorable single window** (a sustained crisis is where a trend overlay shines). The CANONICAL H1/H0 is the **full-cycle (2000–2025) PIT × realistic-cost** run, where the overlay's **bull-market chop/whipsaw drag** must be weighed against the crisis protection, and the turnover cost is realistic. The first-cut **supports H1** (the tail-cut works + clears the gate on a crisis), but the full-cycle verdict is pending §4. No deploy claim rests on this exploratory window (per the pre-reg N_trials rule).

## 4. The canonical run = cloud cell (with a REQUIRED optimization first)
- **Local heavy runs DEADLOCK** (the T-165 in-process harness fragility — the 6yr composition run + base re-runs hung at 0% CPU; one base run was killed mid-backtest). The full-cycle 26yr × PIT × realistic is not locally tractable → **cloud cell** (as the dispatch anticipated).
- **REQUIRED before the cloud submit:** the defensive screens (`high_ivol_exclusion` recomputes cross-sectional vol across the whole universe every rebalance bar; `quality_tilt_longs` fetches fundamentals per bar) dominate the per-bar cost and ~3–5× the run time. They MUST be cached/down-sampled (compute the IVOL-exclusion + quality sets monthly, not per bar — the screens are slow-moving) before a 26yr × full-PIT-universe cell, or the cell will be intractably slow. This is the next concrete step.
- Cloud cell config (pre-registered §config): `phase1_composition_enabled=True`, `position_buffering_enabled=True`, `use_historical_universe=True`, `slippage_extra.realistic_retail_costs=True`, `mean_variance`, 2000–2025, block-bootstrap ci_low. Run base + composition cells; feed both equity curves to `evaluate_deploy_readiness` (Roth + taxable) + `is_it_beta_or_edge`.

## 5. Files
`engines/engine_c_portfolio/phase1_composition.py` (new), `portfolio_engine.py` (OFF-default branch + wrapper), `policy.py` (config fields), `config/portfolio_settings.json` (flags), `core/combined_candidate_scorecard.py` (w_dbmf=0 path). Commits: build+prereg `c93a0f2`, gate path `4469df3`. No Engine-B/live_trader touch; OFF-default canon `80b501a8` bitwise. Branch push; director reviews the integration + result.
