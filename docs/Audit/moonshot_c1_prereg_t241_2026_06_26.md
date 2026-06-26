# T-241 — moonshot probe C1 (concentration): PRE-REGISTRATION (locked BEFORE measuring)

**Date:** 2026-06-26
**Agent:** C. Pre-registered per `[NN-MBL]` / `[NN-SHARPE-CI]` — hypothesis + K + gate + N_trials declared before any result is read.

## The question (the decisive probe)
Does CONCENTRATION surface the alpha that diversification CANCELS (the ensemble-alpha paradox, `project_ensemble_alpha_paradox_2026_04_30`), or does it just amplify H0 noise (the single-gene book is H0 per T-196) / concentrated beta? **Either result is decisive.**

## Mechanism (pre-registered, default-OFF)
`PortfolioPolicy._apply_concentration`: keep the **top-K = 10** names by **conviction = |combined signal score|**, **conviction-weighted** (weight ∝ conviction), **GROSS PRESERVED** (reallocate the same gross into fewer names — a cash Roth has no margin; amplify the right tail via ASSET SELECTION, not leverage). Deterministic ranking (conviction desc, |weight| desc, ticker asc). Composes before the T-230 deployable cone.

## Hypotheses
- **H1:** concentration surfaces an upside half. Operationally, the PRIZE: **C1 PAIRED with the trend sleeve (T-236) beats BOTH robos (60/40 + schwab_like) on BOTH terminal wealth (CAGR) AND drawdown (MaxDD)**, with Sortino `ci_low > 0` (block-bootstrap), AND `is_it_beta_or_edge` shows real alpha (HAC alpha t ≥ 2.0) rather than concentrated beta.
- **H0 (a legitimate, publishable deliverable):** concentration does NOT beat the robos on both axes AND/OR `is_it_beta_or_edge == "beta"` with alpha t < 2.0 → the equity book has **no extractable upside half**; the honest ceiling becomes "trend sleeve + the robo's own return," and the moonshot frontier moves to NEW DATA (C4) or is conceded. **A clean H0 is reported AS the result.**

## Decision rule (locked)
Report ALL of, for C1 alone AND C1+trend-sleeve, vs both robos:
- **Sortino + block-bootstrap `ci_low`** (`[NN-SHARPE-CI]`), up/down-capture, skew, Calmar, MaxDD, CAGR.
- **`is_it_beta_or_edge`** (HAC alpha t net of FF5+Mom) — the key alpha-vs-beta/noise test.
- **MBL at honest-N** (`[NN-MBL]`): the window must satisfy `T_years ≥ 2·ln(N_eff)/SR_target²`. Pre-registered SR bar at the accumulated N.
- **THE PRIZE:** C1+trend-sleeve vs BOTH robos on BOTH terminal wealth AND MaxDD.
H1 accepted ONLY if the PRIZE holds (both robos, both axes) AND alpha is not pure beta/noise. Anything less → H0.

## N_trials accounting
This pre-registers **ONE** configuration (**K=10**, conviction-weighted, gross-preserved). **N_trials += 1.** A different K (or equal-weight, or a different conviction definition) is a NEW pre-registration / a new trial, not a re-read of this one. The prior is **medium-LOW** (the book is single-gene H0 + closet-beta diversified) — this is a CHEAP, HIGH-INFO probe, not an open-ended moonshot program.

## Measurement plan (compute-honest)
The book equity for C1 requires per-bar (conviction × forward returns). The full backtest **deadlocks locally** (T-165 harness fragility) and a 30h cloud cell is being avoided, so C1 is measured by a **WEIGHT-REPLAY**: take a BASE run's per-bar target weights (conviction = weight magnitude / the logged signal), form (a) the diversified book and (b) the top-K concentrated book from the SAME per-bar weights × the universe forward returns → two equity curves over the same window → fed to the established cached-data gauntlet (`tail_rescore_t234` + `trend_sleeve_gauntlet_t236`) vs the robos + the analytic trend sleeve. The replay isolates the concentration effect (same conviction, different weighting). Window = the longest crisis-inclusive base run obtainable locally; if only short windows complete, the verdict is reported on that window with the limitation stated, and the full-cycle confirmation flagged as cloud-bound. Canon-unchanged (mode OFF) proven first.
