---
task_id: T-2026-06-18-205
title: Defensive-tilt signals — quality/profitability tilt + high-IVOL/lottery exclusion (Phase 1 beta-engineering)
date: 2026-06-18
scope: cross-sectional SIGNALS/SCREENS only (OFF-default, NOT wired into Engine-B admission — that is propose-first); standalone validation only; NO beat-the-robo measurement (post-gate, after C's T-203)
status: CURRENT (pre-registration committed before any backtest — see git history; results appended after)
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

(Appended after the pre-registration commit — verify §1 predates these in git history. Reproducible: `scripts/defensive_tilt_screens_t205.py`; tests `tests/test_defensive_tilt_screens_t205.py`.)

### 2.0 Fundamentals fed + canon-unchanged (the invariants)

- **`fundamentals_blind = False`** (panel loads, 51,133 rows; gross_profit
  / operating_income / total_assets / total_equity / long_term_debt all
  present) — the quality signal is fed, not starved.
- **Prod canon UNCHANGED — by construction.** This task is ADDITIVE-ONLY:
  `git diff --name-only HEAD` is empty; the only changes are new files
  (`engines/engine_a_alpha/screens/`, the harness, the test). Nothing on
  the production backtest path was modified, and a contract test
  (`test_signals_are_pure_not_wired`) asserts `backtest_controller` does
  not import the screens. The Engine-B admission/sizing application is
  propose-first and NOT wired here.

### 2.1 What shipped (repoint, not rebuild)

- `engines/engine_a_alpha/screens/defensive_tilt.py`:
  - `quality_score(data_map, now)` — composite cross-sectional quality
    score = mean(pctrank(gp/assets), pctrank(roic)); REUSES the exact PIT
    formulas of `quality_gross_profitability_v1` + `quality_roic_v1` (both
    metrics required; distressed equity≤0 dropped; min_universe=30 abstain).
  - `quality_tilt_longs(..., quality_quantile)` — top-quantile tilt basket.
  - `high_ivol_exclusion(..., ivol_cutoff, lookback=30)` — returns the
    EXCLUDED set (trailing-30d annualized realized vol above the
    cross-sectional cutoff percentile; idiosyncratic-vol PROXY, honestly
    labeled — not market-residualized this round).
- 6 unit tests (fixture-fed, deterministic) — all pass.

### 2.2 Quality tilt — standalone composition (as-of 2026-05-21)

102 of 200 processed tickers scorable (≈51% — matches SimFin FREE
fundamentals coverage). Basket sizes per pre-registered quantile:

| quality_quantile | basket size |
|---|---|
| 0.15 | 16 names |
| 0.20 | 21 names |
| 0.25 | 27 names |

### 2.3 High-IVOL exclusion — the HONEST bull/bear under-participation

Excluded (= high-vol names we sit out) vs retained, mean forward return
per sub-period. **This is the conscious cost, surfaced explicitly:**

| cutoff | bull_2009 (R−E) | bull_2020 (R−E) | bear_2008 (R−E) | bear_2022 (R−E) |
|---|---|---|---|---|
| 0.60 | −97.4pp | −95.5pp | +12.0pp | +20.0pp |
| 0.75 | −110.4pp | −120.3pp | +8.2pp | +21.9pp |
| 0.90 | −138.4pp | −146.0pp | +0.5pp | +22.1pp |

(R−E = retained mean − excluded mean.) The high-vol/lottery names
**rip in the 2009/2020 recovery rallies** (excluded basket +160% to +228%
vs retained +61% to +88%) — so the screen GIVES UP large rally upside —
and **fall harder in 2008/2022 bears** — so the screen cushions
drawdowns. Textbook high-vol-anomaly tradeoff: a beta/vol-reduction,
defensive UNDER-participation tilt. Net Sharpe/tail value is for the
post-gate beat-robo measurement to decide; this task only surfaces the
tradeoff honestly, which it does starkly (the rally cost is enormous —
the higher the cutoff, the more extreme-only the exclusion and the
larger the per-name rally give-up).

### 2.4 Verdict (scope-appropriate)

Both signals are built, composable, OFF-by-construction, fed, tested, and
standalone-validated; the grid is pre-registered (9 arms, N consumed at
the eventual gate). The quality tilt selects a coherent high-profitability
basket; the IVOL exclusion is a real defensive cushion with an
honestly-quantified rally-under-participation cost. **No beat-the-robo
measurement run** (deferred to the post-gate composition after C's T-203).
Wiring either into Engine-B admission/sizing is propose-first.
