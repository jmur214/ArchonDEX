# T-165 — regime-footprint local diagnostic: the re-anchor premise needs revisiting

**Date:** 2026-06-13
**Agent:** C (branch `feature/regime-footprint-t165`, off origin/main `21caeef`)
**Status:** DONE — with an honest scope correction. The clean 4-cell footprint table the dispatch asked for was **not fully achievable** (two substrate-side blockers below), but the diagnostic produced a **decision-relevant correction**: the cloud regime failure is **not** caused by `data/macro` alone, so D's T-164 (baking macro) is likely **insufficient** to restore the cloud regime. Mechanism instrumentation only — zero N_trials; `data/macro` never touched; the diagnostic env-hook was reverted.

---

## 0. Bottom line (3 lines)
1. **The "data/macro never baked → regime: unknown" hypothesis (mine, T-118fc) is REFUTED as the sole cause.** Emptying `data/macro` locally starves the macro/HMM/forward-stress features (panel macro columns go fully NaN) **but the price-based 5-axis regime survives** (regime stays *known* — trend/vol/corr/breadth run off `data/processed`). The cloud shows **full** `regime: unknown` (trend/vol unknown too), so the cloud is missing **more** than `data/macro`.
2. **Footprint where measurable (adaptive path):** removing `data/macro` shifts the 2022 book **Sharpe 0.464 → 0.369** (Δ −0.095), trades 1690 → 1661, gross 0.523 → 0.530. So the macro/HMM/forward-stress layer is **modestly material, NOT a no-op** — on the adaptive path.
3. **Benign-or-material for the cloud anchors: NOT cleanly determinable yet** — because (a) the mean_variance allocator produces **0 trades** on 2022 in the current substrate (the footprint can't be measured on the cloud's allocator), and (b) the cloud's *full* regime-unknown condition is not reproducible by the obvious local contrafactuals. **Reproduce a real cloud cell before the re-anchor spend** (the T-118fc follow-up).

---

## 1. What was measurable: the macro-feature footprint on the adaptive path
Contrafactual pair, identical except `data/macro`, 2022, adaptive allocator (artifact present), both cells fully executed (250 regime calls each):

| | canon | Sharpe | MDD% | trades | gross μ/max |
|---|---|---|---|---|---|
| regime-LIVE (full macro) | `0145c03a` | 0.464 | −10.86 | 1690 | 0.523 / 1.102 |
| macro-BLIND (empty `data/macro`) | `34ee6b33` | 0.369 | −11.34 | 1661 | 0.530 / 1.160 |

**Δ −0.095 Sharpe, −29 trades, slightly higher gross & worse MDD.** The macro/HMM/forward-stress features DO move the adaptive book — modestly. So regime is not zero-footprint; the strong "benign" prior (T-100/T-101 HMM-on-dead-Path-B; T-158 mean_variance overlays unreachable) is partially right but not total — the *advisory* path (Engine-B `suggested_exposure_cap`/`max_positions`, T-100/T-116 live on Path A) and the alpha-side macro features carry a real ~0.1-Sharpe effect.

## 2. The two blockers (why the clean 4-cell table failed)
- **mean_variance → 0 trades on 2022 (current substrate).** Direct test: artifact displaced (→ mean_variance), `run_isolated --year 2022` → canon `d41d8cd9` (empty), 0 trades. (T-162 got trades on the *same* setup yesterday — the governor/substrate shifted since.) A footprint cannot be measured on 0 trades, so the cloud's own allocator path is unmeasurable here.
- **A hard "force regime unknown" → 0 trades.** An env-gated hook returning the cloud's minimal `{regime:unknown,…}` dict produced 0 trades — yet the **cloud trades with `regime: unknown`** (8279 trades on 26-yr). So the cloud's "unknown" is NOT a hard short-circuit; trade generation locally depends on a more-populated `regime_meta` than the cloud's logged minimal dict. The faithful cloud condition is therefore not reproducible by a simple forced-unknown.

## 3. The definitive mechanism check (clean, no backtest)
`build_feature_panel(start=2021-06-01, end=2022-12-31)`, live vs empty-`data/macro`:

| | panel rows | vix_level non-NaN | yield_curve non-NaN | credit non-NaN | dollar non-NaN |
|---|---|---|---|---|---|
| LIVE macro | 401 | 401 | 401 | 401 | 338 |
| EMPTY macro | 401 | **0** | **0** | **0** | **0** |

Empty `data/macro` → all macro columns fully NaN, **but the panel still builds (401 rows)** from the price-derived columns (spy_ret/spy_vol/tlt_ret off `data/processed`). The HMM `predict_proba_at` then dropna's the all-NaN macro columns out of its window and falls back; the **5-axis price regime stays fully known.** So locally, macro-starvation degrades the macro/HMM/forward-stress part **only** — it does not blank the whole regime. **The cloud's full `regime: unknown` (price axes too) implies the benchmark/price data is *also* not reaching the cloud regime detector** — a bigger gap than `data/macro`.

## 4. Implication for the re-anchor + the allocator decision
- **D's T-164 (bake `data/macro`) is likely necessary-but-INSUFFICIENT.** It will restore the macro/HMM/forward-stress features, but the cloud's *full* regime-unknown points to the price-axis benchmark data also failing in the container. Baking macro alone may leave the cloud regime still (partly) dead. **Recommend: reproduce one cloud cell and trace the regime detector's data load — confirm whether SPY/benchmark reaches the 5-axis detector — before committing the re-anchor.** (This is the same follow-up T-118fc recommended; T-165 sharpens *why* it's needed: macro is not the whole story.)
- **For the allocator-identity decision:** the footprint that IS measurable lives on the **adaptive** path (the local artifact's allocator), ~0.1 Sharpe. The cloud's **mean_variance** path couldn't be measured (0 trades on 2022). So whether the cloud anchors are regime-blind-BENIGN vs MATERIAL **remains open** and is gated on reproducing the true cloud condition — it should not be assumed benign.

## 5. Honest verdict
Regime-blindness is **not demonstrably benign** (it's worth ~0.1 Sharpe on the one path I could measure), and the cloud's specific failure is **deeper than `data/macro`**. The cleanest path to the benign/material answer is a faithful cloud-cell reproduction, not more local contrafactuals — the local ones can't reproduce the cloud's tradeable-full-unknown state.

## 6. Provenance / hygiene
- `data/macro` **never touched** (24 parquet intact) — blinding was an in-process `DEFAULT_CACHE_DIR` pointer swap to an empty temp dir (panel check) and a per-cell empty-dir, both reverting on process exit.
- The Apr-23 artifact displaced (copy-preserved) for the mean_variance cells; **restored, md5 `bfa539466599066c35dc985c667848dd` pre==post.**
- The `ARCHONDEX_FORCE_REGIME_BLIND` diagnostic hook in `regime_detector.py` was **reverted** (git-clean; 0 refs). Engine code untouched at HEAD.
- **NEW:** `scripts/regime_footprint_t165.py` (the harness), this audit, `data/research/t165/` (gitignored). One leftover gitignored backup `data/research/allocation_recommendations.json.t165_held` (same md5; `rm` deny-listed — harmless).
