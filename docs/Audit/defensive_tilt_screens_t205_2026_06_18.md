---
task_id: T-2026-06-18-205
title: Defensive-tilt signals — quality/profitability tilt + high-IVOL/lottery exclusion (Phase 1 beta-engineering)
date: 2026-06-18
scope: cross-sectional SIGNALS/SCREENS only (OFF-default, NOT wired into Engine-B admission — that is propose-first); standalone validation only; NO beat-the-robo measurement (post-gate, after C's T-203)
status: PRE-REGISTRATION committed BEFORE any backtest; results appended after
references: docs/State/re_architecture_plan_2026_06_18.md (Phase 1); research brief Tier-1 #3 / Q7 (Novy-Marx)
---

# T-205 — Defensive-Tilt Signals (Quality + High-IVOL Exclusion)

## 1. PRE-REGISTRATION (committed before any backtest)

### 1.1 What + why (repoint, not rebuild)

Two robust, low-turnover, evidence-backed defensive tilts (research brief
Tier-1 #3, Novy-Marx):
- **Quality/profitability tilt** — gross profitability (Novy-Marx 2013:
  GP/assets "subsumes the quality space") + ROIC (Asness-Frazzini-Pedersen
  "Quality Minus Junk"). We already have `quality_gross_profitability_v1`
  + `quality_roic_v1` (dormant). **Repoint** their exact PIT formulas into
  one composable cross-sectional QUALITY SCORE (continuous rank), not a
  new factor.
- **High-IVOL / lottery EXCLUSION** — Novy-Marx: this is a HIGH-vol
  anomaly (the edge is *avoiding* the terrible high-vol/lottery names), a
  simple exclusion of the top-IVOL quantile. Honest: this is a defensive
  UNDER-participation tilt — it will sit out high-vol rally names
  (2009/2020); accepted consciously and reported per sub-period.

### 1.2 Deliverable scope (fixed)

SIGNALS/SCREENS ONLY, OFF-default, NOT wired into Engine-B admission or
sizing (that application is **propose-first**, flagged for later). Produce:
(a) a composable quality-tilt signal, (b) a high-IVOL exclusion screen,
(c) a STANDALONE validation harness (composition + bull/bear
under-participation). **DO NOT run the beat-the-robo measurement** — that
is the post-gate composition step after C's T-203.

### 1.3 The grid (fixed, pre-registered)

- **quality top-quantile** ∈ {0.15, 0.20, 0.25} (fraction of scored
  universe that gets the quality tilt).
- **IVOL exclusion cutoff** ∈ {0.60, 0.75, 0.90} (exclude names whose
  trailing-30d realized vol is above this cross-sectional percentile).
- 3 × 3 = **9 arms.** Every arm counts toward N_trials. **N is consumed at
  the eventual beat-the-robo gate measurement (post-C-T-203), NOT here** —
  this task's standalone validation is DESCRIPTIVE (composition,
  coverage, under-participation), not a gated Sharpe/ci_low test, so it
  does not itself constitute the trial. The grid is registered now so the
  eventual gate cannot quietly expand it.

### 1.4 Quality score (fixed construction)

For each ticker with both metrics present as-of T:
- `gp_assets = TTM_gross_profit / latest total_assets` (Novy-Marx, exact
  reuse of `quality_gross_profitability_v1`).
- `roic = (TTM_operating_income · (1−0.21)) / (latest total_equity +
  latest long_term_debt)` (exact reuse of `quality_roic_v1`; LTD None→0).
- `quality_score = mean( pctrank(gp_assets), pctrank(roic) )` across the
  present-data cross-section (0-1, higher = higher quality). A name needs
  BOTH metrics to be scored (else abstain). `min_universe = 30` floor.
- The tilt basket = top `quality_quantile` of `quality_score`.

### 1.5 High-IVOL exclusion (fixed construction)

- `ivol = stdev(daily log returns, trailing 30 trading days) · √252` per
  ticker as-of T (idiosyncratic-vol PROXY = total realized vol; honest
  label — we are not market-residualizing this round).
- Exclude tickers whose `ivol` is above the `ivol_cutoff` cross-sectional
  percentile. Output = the EXCLUDED set (and its complement, the retained
  set). `min_universe = 30` floor.

### 1.6 Standalone validation read (fixed; NOT the gate)

- Quality: scored-universe coverage, basket size per quantile, and a
  sanity check that top-score names carry higher gp/roic.
- IVOL: % excluded per cutoff, AND — the honest part — **bull vs bear
  sub-period forward-return of the excluded vs retained baskets** (e.g.
  2009 + 2020 rallies = bull; 2008 + 2022 = bear), to show explicitly the
  rally under-participation we are accepting.
- Census: confirm `fundamentals_blind = 0` (quality needs the panel fed).

### 1.7 Hard invariants (fixed)

- OFF-default: the signals are standalone functions, NOT called by the
  production backtest path → prod canon-md5 UNCHANGED (verified on a cell).
- Engine-B admission/sizing application = propose-first (NOT wired here).
- Unit tests on both signals (deterministic, fixture-fed).
- No edge_weights.json edit, no promotion.

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
