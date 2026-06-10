---
task_id: T-2026-06-10-132
title: Alpha-Frontier Map + non-linear interaction go/no-go diagnostic
date: 2026-06-10
author: Agent D (alpha/edge lane)
outcome: Part A — frontier map shipped, 16 materially-untested categories (4 free-now,
  8 free-with-build, 4 fork-gated); the T-117→129 closure covered ONE cell of the
  (data × resolution × form × instrument × universe) grid. Part B — pre-registered
  interaction diagnostic returns METALEARNER GO (marginal): 1 of 28 de-correlated
  edge pairs (bollinger_reversion × pead_short) shows Friedman-Popescu H²=0.137
  exceeding its block-bootstrap null p97.5=0.096 with H=0.371>0.10; MI 2/8 above
  null. GO is per the pre-registered rule but carries a stated multiplicity caveat —
  treat as weak-prior GO; the training dispatch must pre-register its own kill bar.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.interaction_diagnostic_t132   (seed 0; determinism ×2 — see §4)
---

# T-132 — Alpha-Frontier Map + the first untested-category test

## Part A — the Alpha-Frontier Map (the breadth answer)

Shipped to `docs/Core/Ideas_Pipeline/alpha_frontier_map_t132_2026_06_10.md` (a
living Ideas-Pipeline doc, not a frozen audit). Summary:

- **What T-117→T-129 actually closed:** {13 artisanal edges + equity-proxy VRP +
  BAB-class low-beta} on {daily bars × S&P-survivor large/mid × cross-sectional
  harness} — one cell of the grid. The FF5-span circularity means
  characteristic factors could never clear the t>2 gate by construction; BAB was
  the designated exception and failed empirically. Alpha that CAN clear lives in
  different data / resolution / functional form / instruments / universes.
- **16 materially-untested categories**, each scored on data availability,
  lookahead risk, harness fit (XS vs overlay-that-doesn't-exist vs sleeve),
  FF5-span-by-construction risk, cost, and N-trials.
- **4 are testable for free with data already on disk:** (1) overnight/intraday
  return composition (Lou-Polk-Skouras "tug of war" — category the brief missed;
  computable TODAY from existing OHLC), (2) VIX-term/vol-of-vol as per-ticker
  conditioners (foundry features already built), (3) metalearner/meta-labeling
  (gated on Part B, below), (4) residual momentum (cheap falsification;
  span-risk flagged).
- **Ranked shortlist:** overnight/intraday composition first (free now,
  XS-native, span-L, lit-strong); then the event/data class (8-K reactions —
  EDGAR fetcher pattern already exists from T-041b; Form-4 feed repoint — the
  insider edge EXISTS but its feed dir is 0 bytes); then intraday-derived daily
  features (the user's idea — one-time precompute sidesteps the 78-390×
  intraday-backtest cost).
- **Fork-gated (honestly listed with costs):** options-class VRP, futures
  carry, micro-cap/international, LLM/news lane (plateau-before-AI).
- **Closed doors restated** so they don't get re-tested: characteristic factors
  on this universe, uniform timing tilts through the XS bus (T-122), linear
  recombination (T-117), aggregator-topology iteration (Phase-0).

## Part B — the non-linear interaction go/no-go (first untested-category test)

**Question:** is there non-linear/interaction structure between existing edges'
signals and forward returns — i.e., is training the built-but-never-trained
MetaLearner worthwhile? (T-117 closed only LINEAR recombination; research Q4.)

**Method (pre-registered in the script docstring before running):** per-ticker
signal panel `695b0b21` (1.85M rows → 108,762 (ticker,date) rows × 17 edges,
2021-2024, norm_score), features = edges with ≥1% nonzero rate (10), greedy
de-correlation at |ρ|>0.5 FIRST (Friedman-Popescu collinearity warning) →
**8 features** (dropped: rsi_bounce ρ=0.63 vs bollinger; pead_predrift ρ=0.65
vs pead — exactly the Phase-0 twins). Target: 1-day forward log return.
Subsample 30,000 rows, seed 0. **Null = circular time-shift of the (date×ticker)
forward-return matrix by random offset k∈[21,T−21], same k across tickers** —
preserves the target's autocorrelation AND cross-sectional dependence (iid
shuffles inadmissible per CLAUDE.md #6). MI (KSG kNN, k=3) vs 200 nulls;
Friedman-Popescu pairwise H² (GBM 200×depth-3, PD on 8×8 quantile grid,
cell-frequency weighted) on all 28 pairs, top-3 tested vs 60 GBM-refit nulls.
**Verdict rule (pre-registered): GO iff ≥1 pair has H² > its null p97.5 AND
H > 0.10.** N-trials consumed: **0** (diagnostic; no backtest configs).

### Results

**MI (marginal predictivity), 2/8 features exceed their block-null p97.5:**

| feature | MI | null p97.5 | exceeds |
|---|---|---|---|
| volume_anomaly_v1 | 0.0064 | 0.0030 | **YES (2.1× null)** |
| low_vol_factor_v1 | 0.0217 | 0.0206 | YES (barely) |
| momentum_edge_v1 | 0.0159 | 0.0186 | no |
| bollinger_reversion_v1 | 0.0075 | 0.0092 | no |
| pead_v1 / pead_short / herding / gap_fill | — | — | no |

**H-statistic (interaction structure), top-3 of 28 pairs vs their own nulls:**

| pair | H² obs | H obs | null p97.5 | passes |
|---|---|---|---|---|
| **bollinger_reversion × pead_short** | **0.1374** | **0.371** | 0.0961 | **YES** |
| momentum_edge × pead | 0.1343 | 0.366 | 0.2066 | no |
| momentum_edge × pead_short | 0.0170 | 0.131 | 0.2027 | no |

The pair-specific nulls did real work: momentum×pead has nearly the same
observed H² as the passing pair but fails because dense-momentum noise-fits
manufacture interaction under the null (its null p97.5 is 2.1× wider).

### VERDICT: **METALEARNER GO** (per the pre-registered rule) — with a stated caveat

**The caveat (brutal-realism):** the rule was "≥1 pair passes," and exactly 1 of
28 passed, where the top-3 were *selected* by observed H² before testing —
selection-then-test inflates pass probability, and ~0.7 false discoveries would
be expected testing 28 pairs at 2.5% each. The GO is therefore **marginal /
weak-prior**, not a strong detection. What it earns: the metalearner-training
dispatch is *justified* (the door did not close), but it must (a) pre-register
its own OOS kill criteria before training, (b) treat bollinger×pead_short as
the hypothesis to confirm, not a validated fact, and (c) count its trials.
A NO-GO would have closed the door cleanly; this is "door ajar."

Supporting context: volume_anomaly carries the cleanest marginal signal
(MI 2.1× null) — consistent with T-117 finding it the least-factor-negative
edge (α t −1.59, the only one above −2).

## §4 Determinism — PASS (with one honest wrinkle)

Three full independent runs, seed 0 (`default_rng(0)` consumed in fixed order:
subsample → MI nulls → H nulls). Runs 1-2 had identical substantive output
(every MI value, null percentile, H², and the verdict — log-diff clean) but
differing md5 because I had put `wall_seconds` INSIDE the result JSON — a
self-inflicted timestamp breaking bit-identity. Patched (wall time now
print-only), run 3 vs run-2-content: **bit-identical, md5 `aa50564f…` — PASS.**
Lesson for future diagnostics: never put wall-clock in a determinism-bearing
artifact.

## Files

- `docs/Core/Ideas_Pipeline/alpha_frontier_map_t132_2026_06_10.md` (NEW — Part A, living doc)
- `scripts/interaction_diagnostic_t132.py` (NEW — Part B, pre-registered)
- `data/measurements/alpha_frontier_t132/interaction_diagnostic.json` (gitignored)
- This audit. Builds on: T-117/T-122/T-123/T-129; Phase-0 pairwise-correlation audit.

## NOT included

- No metalearner training (that's the next dispatch, now justified).
- No governor/edges/engine edits; no promotion; no backtest configs consumed.
- No TASK_LEDGER write (T-114 — proposed row in outbox). Branch only.
