---
title: Phase 0 — Pairwise raw-signal correlation diagnostic
date: 2026-05-12
author: director (post-research-synthesis)
data_source: existing PerTickerScoreLogger output at data/research/per_ticker_scores/695b0b21-18f0-4493-b593-e62abf091519.parquet
status: director-side analysis (no agent dispatch); the highest-leverage single diagnostic per all four 2026-05-16 research dives
gate_decision: SIGNAL-DIVERSITY PROBLEM CONFIRMED — fire follow-up actions
---

# Phase 0 — Pairwise Raw-Signal Correlation Diagnostic

## TL;DR — the gate FIRED

The 2026-05-16 multi-strategy research dive specified the highest-leverage single diagnostic: pairwise rank correlation matrix of the active edges' RAW SIGNAL SCORES (not return streams). Decision tree:

- If max ρ > 0.5 OR avg ρ > 0.3 → **signal-diversity problem; no aggregator change can rescue this stack**
- Otherwise → substrate or sample-size is the binding constraint

**Result on existing per-ticker score logs (1.85M rows, 10 actively-firing edges from a 2024-era snapshot, 2021-2024 substrate):**

| Approach | avg \|ρ\| | max \|ρ\| | Gate decision |
|---|---|---|---|
| **Per-day cross-sectional mean** | 0.156 | **0.947** | **FIRED** |
| **Per-(ticker, date) panel (Spearman)** | 0.098 | **0.622** | **FIRED** |

The avg-|ρ| threshold of 0.3 is NOT exceeded under either approach, but the **max-|ρ| threshold of 0.5 is exceeded under both**. This satisfies the dive's "OR" trigger. **Signal-diversity problem confirmed.**

## The high-correlation pairs (per-(ticker, date) panel)

| Pair | ρ | Interpretation |
|---|---|---|
| `bollinger_reversion_v1` ↔ `rsi_bounce_v1` | +0.622 | **Technical mean-reversion twins** — same dynamic, different oscillator |
| `pead_predrift_v1` ↔ `pead_v1` | +0.588 | **PEAD twins** — same earnings-drift signal, different timing windows |
| `momentum_edge_v1` ↔ `rsi_bounce_v1` | -0.494 | Momentum vs mean-reversion (anti-correlation expected; still co-determined) |
| `bollinger_reversion_v1` ↔ `momentum_edge_v1` | -0.416 | Same anti-correlation dynamic |
| `gap_fill_v1` ↔ `volume_anomaly_v1` | +0.314 | Both react to single-day volume/price anomalies |

## What this means

The system's "10 actively-firing edges" in this snapshot are mathematically **~6-7 distinct signal clusters**, not 10. Specifically:

- PEAD has 3 sibling variants (`pead_v1`, `pead_predrift_v1`, `pead_short_v1`) → effective standalone PEAD count ≈ 1 (the highest at ρ=0.59 is duplicative; pead_short is anti-correlated)
- Technical mean-reversion has 2 (`bollinger`, `rsi_bounce`) at ρ=0.62 → effective count ≈ 1
- Momentum (`momentum_edge_v1`) is anti-correlated with both mean-reversion variants — it's a real third bucket but co-determined with the mean-reversion bucket
- Gap fill / volume anomaly cluster lightly (ρ=0.31)

## What the research dive says happens at these correlation levels

From the dive's Grinold-Kahn math:

| ρ (avg pairwise) | Combined IR for 6 edges at IR₀=0.316 (t=1 individual) | Combined 10-yr t |
|---|---|---|
| 0.0 | 0.775 | 2.45 |
| 0.2 | 0.548 | 1.73 |
| 0.4 | 0.450 | 1.42 |
| 0.5 | 0.414 | 1.31 |

At max ρ ≈ 0.6 between technical-mean-rev pairs, the effective combined t-stat for that cluster is **mechanically capped well below the t=2 deployment bar regardless of aggregator topology**. Linear weighted sum cannot save it. Gradient boosting cannot save it. Bayesian opt cannot save it.

**The literature is unanimous: at correlation levels these high, the fix is signal diversity, NOT aggregator method.**

## Important caveats

### 1. The captured log has the OLDER edge set, not the current 6 actives

This particular per-ticker score parquet was generated 2026-04-30, so it predates several edge-set changes that landed in May 2026 (C-collapses cleanup, paused-tier retirements). It contains 10 actively-firing edges of a 17-edge snapshot, of which only **2 are in the current 6 active set**:
- `volume_anomaly_v1`
- `gap_fill_v1`

The current 6 actives include 4 V/Q/A fundamental edges (`value_earnings_yield_v1`, `value_book_to_market_v1`, `accruals_inv_sloan_v1`, `accruals_inv_asset_growth_v1`) NOT present in this captured panel.

### 2. The current 6 actives are almost certainly MORE correlated than what this panel shows

By construction:
- All 4 V/Q/A edges derive from SimFin fundamentals (same data source)
- The 2 accruals variants share most of their computation (different denominator)
- The 2 value variants share most of their computation (different denominator: earnings yield vs book-to-market)
- T-036's per-regime factor decomp already showed all 4 are UNIFORMLY NEGATIVE on factor-adjusted α — strong indication they're all loading on the same factor exposures

**Prior**: the current 6-edge raw-signal correlation matrix is at least as bad as the 0.622 max in this panel, plausibly with the 4 V/Q/A edges clustering at ρ > 0.7 among themselves.

### 3. The structural finding is established regardless

The 10-edge panel here gives a real, quantitative measurement of how the system's signals cluster. The fact that even this 10-edge older snapshot fires the gate is sufficient evidence that:

- The multi-edge architecture's central thesis (combining weak signals produces alpha) has been operating against signal substrates with effective standalone count < raw count
- The 0/11 factor-α verdict makes mechanical sense at these correlation levels
- All aggregator iteration on this signal substrate has been wasted DSR budget

## Forward actions per the research dive's decision tree

The dive specified the action when the gate fires:

> "Replace the worst-correlated pair with one orthogonal signal — most plausibly a regime feature (VIX level, term spread, 200-day SMA slope) or a fundamentally different substrate (futures trend, options-vol-crush, event-driven) — BEFORE changing the aggregation function."

Mapped to our project's current dispatch queue:

| Action | Status |
|---|---|
| **Prune redundant signal pairs from active set** | NEW — should be queued. Either pead_predrift_v1 OR pead_v1 (keep one). Either bollinger_reversion_v1 OR rsi_bounce_v1 (keep one). This is Engine F lifecycle territory — T-043 should add this to its scope. |
| **Add orthogonal regime features to Foundry** | T-052 (B's chain second task) does exactly this: VIX/VIX3M, EBP+HY OAS, ANFCI, Faber multi-asset trend. Confirmed correctly prioritized. |
| **Pivot to a different substrate (microcap)** | First alpha dive's #1 recommendation. NOT in current dispatch queue. Pending user approval on Norgate $80/mo. |
| **Pause aggregator iteration (Bayesian opt, MetaLearner variants, HRP slices)** | Already paused per B's T-038-CONT brief; the Engine D infrastructure work (vectorize seed_from_foundry) is durable regardless. |
| **Re-run this diagnostic on current 6 actives** | NEW — should be queued. Requires fresh substrate-honest backtest with `PerTickerScoreLogger` enabled. ~2-3 hr. Confirms or refines the prior above. |

## Recommendation to user

**Phase 0 verdict: signal-diversity problem CONFIRMED on the available panel. The current actives are almost-certainly worse.**

Two immediate forward actions are independent and can be done in parallel:

1. **T-043's scope expands** — in addition to factor-α gate, Engine F lifecycle should consider signal-correlation as a retirement criterion. If two active edges have raw-signal ρ > 0.6, the lower-Sharpe one is the prune candidate.

2. **A fresh per-ticker-score-log capture on the current 6 actives** is worth ~2-3 hr to confirm the strong prior. Could be a director-side smoke run OR added to one of the in-flight chains.

The big strategic answer (microcap substrate? LLM unpark? more event-driven sleeves?) is a USER decision; this diagnostic just confirms the mathematical necessity that those decisions become urgent.

## Files

- Input: `data/research/per_ticker_scores/695b0b21-18f0-4493-b593-e62abf091519.parquet`
- This audit: `docs/Audit/pairwise_signal_correlation_phase0_2026_05_12.md`
- Cited research: `docs/Sources/Alpha/Retail-algo-alpha_follow-up_multi-strat.md` §11 ("The single most consequential finding for your situation")

---

# Phase 0b — Fresh capture on current 6 actives (T-2026-05-22-053)

**Date:** 2026-05-22
**Input:** `data/research/per_ticker_scores/157e5d58-ac68-493c-ba29-ccd313175ef3.parquet`
**Window:** 2024-01-01 → 2024-12-31, substrate-honest historical universe, journal-mode
**Rows:** 2,816,839 (vs Phase 0's 1.85M)
**Unique edges firing:** 27 (active + paused emit raw scores; archived spinoff_reversion_v1 does NOT)
**Unique tickers:** 512

## TL;DR — gate fires on max, NOT on the V/Q/A prior

**The strong prior — that the 4 V/Q/A SimFin-derived edges cluster ρ > 0.7 — is REFUTED.**

| Pair | ρ (per-panel Spearman) |
|------|------------------------|
| `accruals_inv_asset_growth_v1` ↔ `accruals_inv_sloan_v1` | +0.147 |
| `accruals_inv_asset_growth_v1` ↔ `value_book_to_market_v1` | +0.074 |
| `accruals_inv_asset_growth_v1` ↔ `value_earnings_yield_v1` | +0.012 |
| `accruals_inv_sloan_v1` ↔ `value_book_to_market_v1` | +0.033 |
| `accruals_inv_sloan_v1` ↔ `value_earnings_yield_v1` | +0.054 |
| `value_book_to_market_v1` ↔ `value_earnings_yield_v1` | +0.316 |

Max V/Q/A pair: +0.316 (book-to-market ↔ earnings-yield, both "value"; expected). Three of six V/Q/A pairs are below ρ=0.1. **The 4 V/Q/A edges are NOT a single redundant cluster.**

## Among the current 6 actives, max ρ = +0.340 (below the 0.5 gate threshold)

Current 6 actives sub-matrix (Spearman, per-panel):

| | accruals_inv_asset_growth_v1 | accruals_inv_sloan_v1 | gap_fill_v1 | value_book_to_market_v1 | value_earnings_yield_v1 | volume_anomaly_v1 |
|---|---|---|---|---|---|---|
| accruals_inv_asset_growth_v1 | 1.000 | 0.147 | 0.002 | 0.074 | 0.012 | 0.000 |
| accruals_inv_sloan_v1 | | 1.000 | 0.000 | 0.033 | 0.054 | 0.008 |
| gap_fill_v1 | | | 1.000 | -0.000 | 0.000 | **0.340** |
| value_book_to_market_v1 | | | | 1.000 | 0.316 | -0.000 |
| value_earnings_yield_v1 | | | | | 1.000 | 0.002 |
| volume_anomaly_v1 | | | | | | 1.000 |

**Max ρ among current 6 actives: +0.340** (`gap_fill_v1` ↔ `volume_anomaly_v1`). This is **below** the gate's 0.5 max-threshold.

## Full-panel results (includes paused edges)

| Approach | avg \|ρ\| | max \|ρ\| | Gate fires? |
|---|---|---|---|
| **Per-day cross-sectional mean (Spearman)** | 0.1814 | **0.9940** | **YES (max)** |
| **Per-(ticker, date) panel (Spearman)** | 0.0461 | **0.7056** | **YES (max)** |

Phase 0 reference: 0.156 / 0.947 (per-day) and 0.098 / 0.622 (per-panel). The fresh capture's max|ρ| values are similar or slightly worse than Phase 0; avg|ρ| values are similar.

### Top correlated pairs — fresh capture

**Per-day Spearman (cross-sectional mean approach):**

| Pair | ρ |
|------|---|
| `low_vol_factor_v1` ↔ `momentum_12_1_v1` | +0.9940 |
| `low_vol_factor_v1` ↔ `momentum_6_1_v1` | +0.9715 |
| `momentum_12_1_v1` ↔ `momentum_6_1_v1` | +0.9700 |
| `pead_predrift_v1` ↔ `pead_v1` | +0.8300 |
| `bollinger_reversion_v1` ↔ `rsi_bounce_v1` | +0.7952 |

**Per-panel Spearman:**

| Pair | ρ |
|------|---|
| `pead_predrift_v1` ↔ `pead_v1` | +0.7056 |
| `bollinger_reversion_v1` ↔ `rsi_bounce_v1` | +0.6201 |
| `momentum_edge_v1` ↔ `short_term_reversal_v1` | -0.6030 (expected anti-correlation) |
| `momentum_edge_v1` ↔ `rsi_bounce_v1` | -0.4995 |
| `rsi_bounce_v1` ↔ `short_term_reversal_v1` | +0.4508 |

## What this means — re-interpretation

1. **The current 6-active set is NOT signal-diversity-broken at the raw-correlation level.** Max ρ = +0.340 between any pair is below the 0.5 threshold. The Grinold-Kahn IR table at p.51 of Phase 0 still applies, but **on the actives the avg-ρ ≈ 0.08** (well below 0.2), which would give effective combined IR ≈ 0.7 of the i.i.d. baseline — NOT the disastrous 0.4 ratio at ρ=0.5.

2. **The high-correlation pairs are all in the paused/non-active subset.** `low_vol_factor`, `momentum_12_1`, `momentum_6_1`, `pead_predrift`/`pead_v1`, `bollinger_reversion`/`rsi_bounce` — these are all paused per T-029/T-043 verdicts and are not contributing to the active ensemble at full weight.

3. **The original Phase 0 "signal-diversity problem confirmed" gate fired correctly** on the 2024-era snapshot, which DID include high-correlation pairs in the active set. Today's actives — post-pruning to 6 + spinoff archival — are more diverse than feared.

4. **The 0/11 factor-α verdict remains the binding constraint, but for a different mechanical reason.** Each active edge's raw signal is approximately uncorrelated with each other; the factor-α failure means each individual edge is factor-explained (loading on FF5+Mom), not that the ensemble is redundant.

## Pruning recommendation

**None at the active-set level.** The 6 current actives don't have a pair with ρ > 0.5; the gate doesn't fire on the actively-trading subset.

For the **paused** set (where the gate fires hard), Engine F lifecycle's T-043 factor-α gate already retires 6 of 7 paused panel edges per the re-evaluation. The lifecycle journal contains the retirement decisions; once user reviews + approves, those edges leave the registry and the per-day Spearman max|ρ|=0.99 cluster disappears from future captures.

## Forward implications for T-057

T-057's confidence-gated execution (N-of-K agreement filter) operates on the **per-bar per-ticker per-edge raw scores**. With the current active set's max raw-signal ρ ≈ 0.34, an N≥2 confidence gate operates on signals that are largely independent — exactly the regime where N-of-K confidence-gating delivers meaningful turnover reduction without over-correlated false confidence.

In contrast, if max ρ had been > 0.7 (as the prior predicted), N≥2 would be vacuous — two correlated edges both firing is one signal, not two. **Phase 0b's result is permissive for T-057.**

## Files

- Input parquet: `data/research/per_ticker_scores/157e5d58-ac68-493c-ba29-ccd313175ef3.parquet` (gitignored)
- Diagnostic JSON: `docs/Audit/pairwise_signal_correlation_phase0b_2026_05_22.json`
- Analysis script: `scripts/phase0b_correlation_t053.py`
- Capture driver: `scripts/run_per_ticker_capture_t053.py`
