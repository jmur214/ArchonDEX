---
task_id: T-2026-06-18-206 (Task 1)
title: DESIGN — homegrown Barra-lite factor risk model (diagnostic + sizing spec)
date: 2026-06-18
worker: Agent B
branch: feature/risk-model-voltarget-design-t206
status: DESIGN / PROPOSE-FIRST (Engine B — director reviews; no autonomous risk change)
---

# Factor risk model — design (T-206 Task 1)

## 0. Problem (the audit's #2 gap)
`engines/engine_b_risk/factor_analysis.py::FactorRiskModel` exists but is a **stub** (3 crude per-asset loadings: SPY-beta, 12-1 momentum, log(price·volume) "size") and is **never imported by `risk_engine.py`**. There is no book-level factor decomposition, no factor-neutrality, no VaR/ES. Separately, `core/factor_decomposition.py` already regresses returns on **Fama-French 5 + Momentum** (MktRF, SMB, HML, RMW, CMA, Mom) with cached Ken-French factor data — but it is used only by Discovery's Gate-6 (per-edge alpha screen) and carries the **OLS→HAC t-stat defect** (`:200-213`, no Newey-West → inflated t-stats). The book is, by every prior instrument (T-117: 12/13 dense edges factor-negative; 3 flow edges ~94% of PnL, all factor-negative), **closet beta**. The risk model should say that honestly and then size against it.

## 1. Scope of THIS design (propose-first)
Two deliverables, in dependency order:
- **(a) DIAGNOSTIC (measurement — runnable now):** decompose the **book's** realized returns into factor exposures → answer "how much of the Sharpe is beta vs genuine, factor-orthogonal edge?" This directly serves the resolved goal (know honestly what we hold).
- **(b) SIZING SPEC (design only — a later, separate propose-first build):** how the same factor model WOULD feed risk sizing (factor-exposure caps, factor-neutrality constraints, factor-covariance VaR/ES). NO sizing code ships here.

## 2. The model (homegrown Barra-lite)
Six systematic factors, reusing the cached Ken-French series already wired in `core/factor_decomposition.py` + one added low-vol factor:

| Factor | Source (reuse) | Retail-replicable proxy (the "cheap to hold" test) |
|---|---|---|
| Market (MktRF) | FF cache | SPY |
| Size (SMB) | FF cache | IWM |
| Value (HML) | FF cache | VLUE |
| Quality (RMW) | FF cache | QUAL |
| Investment (CMA) | FF cache | (diagnostic only) |
| Momentum (Mom) | FF cache | MTUM |
| Low-vol (BAB) | **NEW** — betting-against-beta (long low-β / short high-β), computed from the universe β ranks, OR USMV-return proxy | USMV |

**Two distinct objects (the stub conflated them):**
1. **Exposure model** (extend `FactorRiskModel.compute_exposures`): per-asset factor loadings → portfolio-level exposure = position-weighted sum. Used by sizing (b).
2. **Return decomposition** (reuse `core/factor_decomposition.py`): regress the **book daily excess return** `r_book − RF` on the 6+1 factors. β vector = systematic exposure; intercept = α (the only thing that's NOT cheaply replicable); R² = fraction of variance explained by factors. Used by the diagnostic (a).

## 3. Diagnostic (a) — method + the honesty fix
- **Input:** the book equity curve from the canonical re-anchor run (26yr `reanchor-mv/26yr/rep1/…/portfolio_snapshots.csv` in S3; also 16yr for the bull-window contrast). Daily returns − RF.
- **Regression:** `r_book − RF ~ α + Σ βᵢ·factorᵢ`. Report βᵢ (with sign/size), **R²** (the headline beta share), and α_annualized.
- **HONESTY FIX (un-inflate the ruler):** compute the intercept t-stat with **Newey-West/HAC SEs** (`statsmodels OLS(...).fit(cov_type="HAC", cov_kwds={"maxlags": int(T**0.25)})`), NOT the homoskedastic `σ²(X'X)⁻¹` of `factor_decomposition.py:200-213`. Daily returns are autocorrelated → OLS SEs understate → α looks more significant than it is. This is the same defect Phase-0 fixes for Gate-6; the diagnostic uses the honest path so "is there alpha?" is answered with an un-biased t-stat.
- **Verdict rule:** high R² (factors explain most variance) + α t-stat (HAC) not significant ⇒ **the book is beta** (confirms T-117 at the book level). A significant positive α would be the surprise (prior: there isn't one).
- **Robustness:** report βᵢ stability across the 16yr (bull) vs 26yr (full-cycle) windows — the 16yr→26yr Sharpe gap (1.105→0.751) is expected to show up as a market/size/momentum β that pays in the bull window and doesn't across the cycle.

## 4. Sizing spec (b) — design only (separate build, propose-first)
Once the exposure model is trusted, wire `FactorRiskModel` into `risk_engine.py` (the missing call) as a **risk overlay**, NOT an alpha source:
- **Factor-exposure caps:** cap the portfolio's |βᵢ| per factor (e.g., market β ∈ [0.6, 1.1], |size/value/mom β| ≤ X). When a target book breaches a cap, scale the offending exposures down (a constraint in the Engine-C MVO or a post-allocation projection).
- **Factor-neutrality (optional, regime-gated):** in a flagged crisis (the validated HMM p_crisis — the audit's "the one validated signal isn't wired to sizing"), tighten caps / neutralize the highest-β factor.
- **VaR/ES:** from the factor covariance Σ_f and exposures β: portfolio σ = √(βᵀ Σ_f β + idio), report 1-day 95%/99% VaR + ES. A VaR limit is a sizing ceiling (compose with vol-target, Task 2).
- **Boundary:** this is Engine B risk LOGIC → each of these is a separate propose-first build with canon-md5-across-the-toggle (default-OFF byte-identical), census/MBL/DSR rigor, and director sign-off. The factor-orthogonality is **diagnostic-only** (demoted from the deploy gate per Phase-0); the gate is the robo-relative after-tax bar.

## 5. Reuse + non-duplication
- Return decomposition + FF loader: `core/factor_decomposition.py` (add the BAB factor + the HAC SE path; don't re-download — use `FF5_CACHE`/`MOM_CACHE`).
- Per-asset exposures: extend `FactorRiskModel.compute_exposures` (add value/quality/low-vol; today only β/mom/size).
- Diagnostic harness: extend `scripts/factor_decomposition_baseline.py` (already takes `--run-id`) to point at the re-anchor book curve + emit the book-level β/R²/α-HAC table.
- Metrics: Sharpe/CI via `core/metrics_engine.py` (block-bootstrap), not a private reimpl.

## 6. DIAGNOSTIC RESULT (run — the 26yr book on FF5+Mom, HAC)
Ran §3 on the canonical 26yr book (`reanchor-mv/26yr/rep1` equity curve, 6538 daily obs 2000-2025), cached Ken-French FF5+Mom, **Newey-West HAC** SEs (the honest path):

| | value | read |
|---|---|---|
| **R²** | **0.357** | FF5+Mom explain ~36% of book variance |
| **Market β (MktRF)** | **+0.332** (t=14.2) | dominant systematic exposure — a **low-β (0.33) long book** (risk-managed, not 1.0 market) |
| RMW (quality) β | +0.092 (t=3.6) | real quality tilt |
| CMA (conservative inv.) β | +0.134 (t=4.3) | real conservative-investment tilt |
| SMB (size) β | −0.052 (t=−2.9) | slight large-cap tilt |
| HML (value) β | +0.012 (t=0.6) | none |
| Mom β | +0.015 (t=1.1) | none |
| **α (annualized)** | **+2.26%** | positive point estimate… |
| **α t-stat (HAC)** | **1.31** (p=0.19) | **…NOT statistically significant** |

**Verdict: at the book level, the Sharpe is market-β (0.33) + quality/conservative-investment tilts + idiosyncratic (the ~64% non-factor variance = single-name selection + the 3 flow edges + risk-management timing). There is NO statistically-significant factor-orthogonal alpha (HAC t=1.31).** This refines T-117 (per-edge factor-negative) to the book level and confirms "closet beta, no validated alpha" — honestly, with an un-inflated ruler. (Caveat: only FF5+Mom here; adding a low-vol/BAB factor — §2 — would likely raise R² and further shrink α; the headline insignificance is robust. The +2.26% point α is within noise, NOT a deploy signal.)

**Implication for Phase 1:** the −33% MDD (not the return) is what loses to the robo, and the book is a 0.33-β long carry — so **engineering the SIZE/SHAPE of this beta (vol-target Task 2, trend/tail overlays) is the right lever; hunting orthogonal alpha is not.** The factor model's forward role is the diagnostic above + the §4 sizing overlay (caps/VaR), NOT an alpha gate.

Script: `scripts/factor_decomp_book_t206.py` (book curve + cached FF + HAC); reproducible offline.
