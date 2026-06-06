---
task_id: T-2026-06-06-122
title: VRP literature edge — implement + gauntlet + factor-α test (candidate only)
date: 2026-06-06
author: Agent D (alpha/edge lane)
outcome: VRP does NOT clear factor-α t>2. The equity proxy (vol-managed market
  overlay) has ZERO clean factor-α (t=-0.36, ci[-2.25,+1.58]); its Sharpe ~1.0
  is market beta, not alpha — the same closet-beta pattern as T-117's 13 edges.
  TWO structural findings: (1) the cross-sectional ensemble harness WASHES OUT a
  uniform market-timing signal (gauntlet Gate-1 contribution = +0.000), so the
  engine never even computes Gate 6; (2) VRP's "structurally non-factor" property
  holds only for the OPTIONS/variance implementation — the equity proxy collapses
  to beta-timing spanned by MktRF. Candidate only; NOT promoted.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.run_vrp_gauntlet_t122 --start 2014-01-01 --end 2025-12-31
  PYTHONHASHSEED=0 python -m scripts.analyze_vrp_factor_t122   (determinism PASS, bit-identical)
---

# T-122 — Volatility Risk Premium literature edge

## TL;DR

The first literature edge after T-117 proved the existing book has no
factor-orthogonal alpha. VRP was picked as the "structurally non-factor"
candidate with "a real shot." Result: **it does not clear the bar either, and the
reason is illuminating.**

- **Phase 0 (data):** VIX is cleanly available — `VIXCLS.parquet` 2000-2026 (26y,
  covers 2008 + COVID + 2022). VRP is GO; no BAB fallback needed.
- **Edge:** implemented as a proper `EdgeBase` candidate, smoke-tested with
  correct economics (calm 2021 → full long 1.0; bear 2022 → scaled 0.22; COVID
  crash → flat 0.0). Registered `status='candidate'` (NOT promoted).
- **Gauntlet (12-yr, 2014-2025, MBL-clearing):** passed Gate-0 (MBL) but **failed
  Gate-1 with contribution = +0.000** — and the gauntlet short-circuits, so Gate-6
  (factor-α) was never computed. A uniform market-timing signal is washed out by
  the cross-sectional rank-and-normalize ensemble constructor.
- **Rigorous factor-α (the standalone object VRP represents — vol-managed market,
  Moreira-Muir 2017), HAC + 1000-iter block-bootstrap CI:** clean cap-weighted
  timing **α = −0.21%, t = −0.36, ci[−2.25, +1.58], p(α>0)=0.37 → ZERO factor-α**.
  Does not clear t>2. Sharpe ~1.0 (ci_low 0.76) is the market's own Sharpe via
  beta (MktRF loading), not alpha.

**Verdict: another miss — but for a structural reason, not a tuning one.** The
equity proxy of VRP is beta-timing, which FF5+Mom spans. Genuinely-orthogonal VRP
needs options/variance instruments (a different sleeve + data), which the brief
correctly scoped as a follow-up.

---

## 1. The edge (implemented, candidate-only)

`engines/engine_a_alpha/edges/volatility_risk_premium_edge.py` — mirrors
`low_vol_factor_edge.py` (structure) + `macro_yield_curve_edge.py` (PIT external-data
load). Signal:

```
implied_vol  = VIXCLS.asof(as_of) / 100                  # forward-looking, FRED cache
realized_vol = ann. std of equal-weight market return over 21d   # from data_map
vrp_spread   = implied_vol − realized_vol
scale        = clip((vrp_spread − threshold)/0.05, 0, 1) if spread>threshold else 0
signal[t]    = scale  (uniform across the universe)
```

Smoke test (correct economics):

| date | regime | implied | realized | spread | signal |
|---|---|---|---|---|---|
| 2021-11-15 | calm bull | 0.165 | 0.095 | +0.070 | **1.00** (full long) |
| 2022-06-13 | bear | 0.340 | 0.329 | +0.011 | 0.22 (scaled down) |
| 2020-03-20 | COVID crash | 0.660 | 0.820 | −0.160 | **0.00** (flat — premium inverted) |

Registered `status='candidate'` via the standard auto-register-on-import. **Not
promoted; no `edge_weights.json`/governor edits.** (`edges.yml` is gitignored — the
candidate entry stays local; the committed edge module auto-registers wherever
imported.)

---

## 2. Gauntlet — VRP washes out of the cross-sectional ensemble (structural finding)

`scripts/run_vrp_gauntlet_t122.py` (mirrors the T-041b precedent),
`DiscoveryEngine.validate_candidate`, 2014-2025 (655 tickers, historical S&P).

- **5-yr window (2021-2025) → killed by Gate-0 (MBL):** T_years=5.0 < MBL_min=9.66
  (N_effective=125, SR_target=1.0). The project's MBL non-negotiable working as
  designed; re-ran on 12-yr.
- **12-yr window (2014-2025) → passed Gate-0, FAILED Gate-1:**
  `volatility_risk_premium_v1 failed Gate 1 (contribution=+0.000 <= 0.1)`,
  `attribution_sharpe = 0.0`. The with-candidate and baseline ensembles were
  **identical**. Gate-6 (factor-α) is short-circuited and never computed.

**Why +0.000 exactly:** VRP emits the *same* score for every ticker (a market-
exposure dial). The ensemble's portfolio constructor ranks and normalizes
cross-sectionally, so a uniform additive tilt does not change the relative
ranking → the selected portfolio is unchanged → zero contribution. This is the
**same structural limitation that makes the `macro_*` timing edges inert** —
`macro_yield_curve_edge.py:180` likewise returns `{ticker: tilt for ticker in
data_map}`, a uniform tilt. **The cross-sectional equity edge interface cannot
express a market-timing / gross-exposure signal.** This is an architectural
finding that applies to ALL timing-style edges, not just VRP.

---

## 3. Rigorous factor-α (the vol-managed-market object VRP represents)

Because the harness can't express the timing signal, the faithful standalone
object is the **volatility-managed market overlay** (Moreira-Muir 2017): hold the
market scaled by VRP's `scale`, flat when it inverts. `scripts/analyze_vrp_factor_t122.py`
reproduces the edge's REAL VIX−RV signal (vectorized, PIT) and runs the resulting
return stream through the SAME machinery T-117 used on the existing 13 edges
(`regress_with_hac` + `compute_alpha_tstat_with_bootstrap_ci`, HAC + block
bootstrap, seed 0). 2014-2025, scale active 77% of days.

| stream | α ann | α t | α t 95% CI | clears t>2 | MktRF β | Sharpe (ci_low) |
|---|---|---|---|---|---|---|
| **VRP cap-weighted timing (clean Moreira-Muir)** | **−0.21%** | **−0.36** | [−2.25, +1.58] | **NO** | 0.13 | +1.00 (0.76) |
| VRP net (equal-weight underlying) | −5.07% | −2.23 | [−4.32, −0.22] | NO | 0.50 | +0.20 (−0.25) |
| VRP gross (equal-weight underlying) | −3.82% | −1.67 | [−3.73, +0.31] | NO | 0.49 | +0.30 (−0.15) |
| _ref: equal-weight market buy-hold_ | −3.60% | −2.98 | [−4.86, −1.40] | NO | 0.99 | +0.49 |

**Reading the table:**
- The **cap-weighted timing** row is the clean test (removes the equal-weight
  proxy's own −3.60% artifact — equal-weight underperformed the cap-weighted FF
  factors in the mega-cap decade, a known non-VRP effect). VRP's vol-timing α is
  **−0.21%, t −0.36 — statistically indistinguishable from zero.** The timing adds
  nothing.
- The equal-weight rows are pessimistic because they inherit the −3.60% proxy
  artifact; the timing component (VRP − buy-hold) is −1.47%/yr net, −0.22%/yr
  gross — i.e. ~0 gross, slightly negative net after de-risking costs + missed
  rallies in a bull decade.
- **Sharpe ~1.0 with α ≈ 0 is the T-117 closet-beta signature again:** the
  vol-managed market has a decent Sharpe because the *market* did (2014-2025), not
  because VRP adds alpha. Correlation to the existing 6-edge book = +0.22.

This is consistent with the post-publication literature (e.g. Cederburg, O'Doherty,
Wang & Yan 2020): volatility-managed portfolios do not reliably beat buy-and-hold
out-of-sample. The Moreira-Muir alpha is fragile / sample-dependent.

---

## 4. The key insight — "structurally non-factor" was true of the wrong thing

The brief's thesis was that VRP is structurally non-FF5/Mom and therefore has a
shot the existing characteristic edges don't. That is true of the **options /
variance-swap** VRP harvest (selling insurance is genuinely orthogonal to equity
factors). It is **NOT** true of the **equity proxy** I could build with available
data: a vol-managed market overlay is, by construction, market beta times a timing
weight — and market beta is exactly the MktRF factor. So the equity proxy collapses
into the factor space and shows ~0 α, just like every characteristic edge in T-117.

There is no equity-only expression of VRP that escapes the factor space, because
the premium being harvested lives in the *options* surface, not the *stock* cross-
section. This sharpens T-117's conclusion: the binding constraint is the
**instrument/architecture** (equity-cross-sectional only), not the specific signal.

---

## 5. RETIREMENT/PROMOTION POSTURE (candidate only — nothing executed)

- VRP stays `status='candidate'`. It does NOT clear Gate-6 (factor-α ~0) and does
  NOT clear Gate-1 (zero ensemble contribution). **No promotion.** No `edges.yml` /
  `edge_weights.json` / governor edits were made or committed.
- The edge module is retained (committed) as a documented candidate + as the
  substrate for a future options-based v2.

## 6. Forward (proposals for the director — not executed)

1. **The genuinely-orthogonal VRP needs options/variance instruments** (sell SPY
   puts / short variance when IV≫RV) + a NON-cross-sectional sleeve that can hold
   a gross-exposure/timing position. That is an architecture extension (new data +
   a sleeve outside the cross-sectional edge interface) → propose-first, user-gated.
2. **The cross-sectional-harness-can't-express-timing finding is reusable:** any
   future macro/timing/regime edge will wash out the same way. Timing belongs in a
   gross-exposure overlay (Engine B/regime), not the cross-sectional edge bus.
3. **If the next literature edge should clear the existing harness, pick a
   CROSS-SECTIONAL one** — BAB (betting-against-beta, Frazzini-Pedersen) expressed
   as long low-β / short high-β IS cross-sectional and would express through the
   framework (the brief's own fallback). It is the cleaner next test of "can any
   literature edge clear t>2 here."

---

## 7. Reproduce + determinism

```
PYTHONHASHSEED=0 python -m scripts.run_vrp_gauntlet_t122 --start 2014-01-01 --end 2025-12-31
PYTHONHASHSEED=0 python -m scripts.analyze_vrp_factor_t122
```
`vrp_factor_analysis.json` is bit-identical across two runs (md5 f116863c…); all
bootstraps seed=0.

## 8. Files

- `engines/engine_a_alpha/edges/volatility_risk_premium_edge.py` (NEW — candidate edge)
- `scripts/run_vrp_gauntlet_t122.py` (NEW — gauntlet runner, mirrors T-041b)
- `scripts/analyze_vrp_factor_t122.py` (NEW — rigorous factor-α analysis)
- `data/measurements/vrp_gauntlet_t122/{result.json,vrp_factor_analysis.json}` (NEW, gitignored)
- This audit: `docs/Audit/vrp_literature_edge_t122_2026_06_06.md`
- Reused: `core/factor_decomposition.py`, `scripts/factor_decomp_substrate_honest.py`,
  `engines/engine_f_governance/factor_alpha_gate.py`, `core/metrics_engine.py`,
  `engines/engine_d_discovery/discovery.py` (gauntlet), `engines/data_manager/macro_data.py` (VIX)
- Builds on: `docs/Audit/edge_compression_t117_2026_06_06.md` (T-117)

## 9. NOT included (hard boundaries honored)

- No promotion; VRP stays candidate. No `edges.yml` / `edge_weights.json` / governor edits committed.
- No `docs/State/TASK_LEDGER.md` write (protocol T-114 — proposed row in outbox).
- No new sleeve / options data / architecture change (proposed only, §6).
- No `cockpit/dashboard/` edits. Branch only; director merges.
