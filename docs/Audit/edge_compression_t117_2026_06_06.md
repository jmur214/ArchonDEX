---
task_id: T-2026-06-06-117
title: Edge compression to orthogonal sleeves — MEASURE + retirement PROPOSAL
date: 2026-06-06
author: Agent D (alpha/edge lane)
outcome: COMPRESSION-AS-ALPHA-RESCUE REFUTED. Redundancy premise CONFIRMED; on
  the recent 2021-2025 substrate all 13 dense edges are factor-NEGATIVE (12/13
  α-t < -2, p(α>0)≈0), so no orthogonal recombination clears joint t>2.
  Compression makes joint α MORE negative (-1.74 → -5.35). Proposal = tiered,
  NOT executed.
status: CURRENT
substrate_caveat: 2021-2025 dense ensemble panel (forward-relevant). 12-yr
  2014-2025 window shows POSITIVE joint α (t=+3.00) but is pre-2021-momentum-
  driven and substrate-conditional — see §6.
reproduce: PYTHONHASHSEED=0 python -m scripts.edge_compression_t117   (determinism PASS, bit-identical x2)
---

# T-117 — Edge compression to 3-4 orthogonal sleeves

## TL;DR — the compression thesis is REFUTED (cleanly, as the brief anticipated)

The brief's hypothesis (Daniel-Hirshleifer-Sun 2020, Anton-Polk 2014): redundant
edge variants SPLIT one signal and inflate the multiple-testing penalty without
adding independent information, so a COMPRESSED 3-4 orthogonal-sleeve set MIGHT
clear joint factor-α t>2 where the bloated set did not.

**Measured answer: NO.** On the forward-relevant 2021-2025 substrate:

1. **The redundancy premise is CONFIRMED.** 9 of the 12 clusterable edges collapse
   into a single residual-return cluster; pairwise residual ρ runs up to +0.56.
   The inventory is genuinely ~4 distinct residual sleeves, not 12.
2. **But every edge is factor-NEGATIVE.** All 13 edges with ≥60 trading days have
   negative point FF5+Mom α; 12/13 have α t-stat < -2 with p(α>0) ≈ 0.00 (the
   sole exception is `volume_anomaly_v1`, α t -1.59, "merely" negative). This
   EXTENDS T-036/T-043's "7-of-11 negative" to the momentum + low-vol edges those
   never decomposed — and they are negative too.
3. **You cannot recombine negative-α streams into positive joint α** (α is linear
   in long-only weights). Measured joint α t-stats (HAC + 1000-iter block
   bootstrap on the t-stat):

   | Set | edges | joint α (ann) | α t | α t 95% CI | clears t>2? |
   |---|---|---|---|---|---|
   | Bloated (all clusterable) | 12 | −2.7% | **−1.74** | [−4.09, +0.20] | NO |
   | Clusterable-only | 12 | −2.8% | −1.77 | [−4.11, +0.16] | NO |
   | **Compressed representatives** | **4** | −2.3% | **−5.35** | [−8.51, −3.39] | **NO (worse)** |

   Compression makes the joint α t-stat **more** negative, not less. The thesis
   fails in the wrong direction.

**This is the clean NEGATIVE the brief's honest-framing paragraph called for:**
the active inventory genuinely lacks factor-orthogonal alpha. The lever is NEW
orthogonal edges (microcap / futures-trend / options-vol / event-driven), exactly
as the Phase-0 pairwise diagnostic and the external research concluded —
**recombination is exhausted.**

---

## 1. Brief-vs-reality reconciliation (read this first)

The brief describes "~39 edges, 11 active … max pairwise ρ ≈ 0.62." The literal
"11 active" does not map cleanly to the current registry — there are **three
different "active" sets** in the repo and the brief's named list matches none of
them exactly:

| Source | "active" set | count |
|---|---|---|
| `data/governor/edges.yml` status==active | gap_fill, volume_anomaly, value_earnings_yield, value_book_to_market, accruals_inv_sloan, accruals_inv_asset_growth | **6** |
| `data/governor/edge_weights.json` (governor-weighted) | gap_fill, herding, low_vol_factor, macro_dollar_regime, momentum_edge, panic, volume_anomaly | **7** (different) |
| Brief's literature list (momentum×5, value/quality×6, PEAD×3, accruals×2, macro×5) | mostly **paused / candidate / never-registered** | — |

I did NOT silently substitute one for another. I defined the working set
**empirically**: the edges that actually *trade* in the deployed ensemble.
On the dense 2021-2025 ensemble panel, **21 edge_ids trade and 12 clear the
60-trading-day threshold** for a stable residual correlation. That 12-edge dense
set (momentum×3, value×2, accruals×2, low_vol, short_term_reversal, volume, gap,
earnings_vol) is the closest faithful realization of the brief's "bloated-11" and
is what I clustered. The 9 sparser edges (insider 31d, herding 20d, panic 10d,
pead×3 ≤3d, dividend 4d, news 3d, growth_sales 1d) are too sparse to cluster and
are reported individually where decomposable.

**Why the discrepancy matters:** the brief's momentum/value/quality "redundant
variants" are largely *paused and inert* in the current `edges.yml` (the 12-yr
run trades only momentum_edge densely; the others <80 days/12yr). They trade
densely only in the 2021-2025 full-universe campaign runs — which is the
substrate I used. Flagging this so the director's mental model of "11 co-equal
active edges" is corrected to "6 active + soft-paused tail; ~12 trade densely
when the full inventory is loaded."

---

## 2. Substrate (zero new compute — reused existing config-consistent trade logs)

**PRIMARY — 2021-2025 dense ensemble panel (1,087 trading days, multi-regime).**
Five single-year ensemble runs from the 2026-05-22 campaign, one rep/year, each
with the full ~17-18 edge inventory trading. Config-verified identical (engine
versions A0.3.0/B0.1.0/C0.2.0, $100k start, wash-sale off, same cost layer):

| year | run_id (stub) | per-year ensemble Sharpe |
|---|---|---|
| 2021 | 5039870e | 1.196 |
| 2022 | 8c577ca4 | 0.367 |
| 2023 | 61394c4c | 1.285 |
| 2024 | 157e5d58 | 0.035 |
| 2025 | 6b7bf3f8 | 0.476 |

Stitched into a per-edge daily-return panel (sum closed-trade pnl by date per
`edge_id` / $100k — the `tier_classifier` / T-036 / `factor_alpha_gate`
convention).

**ROBUSTNESS — 2014-2025 deep run (0dcae34c, 15 edges, 3 reps bit-identical,
determinism PASS; perf-summary Sharpe 1.081, MDD −15.99%).** Momentum-family +
low_vol + volume + gap trade densely here; value/quality/accruals do NOT appear.

## 2a. Method (reuse, no reimplementation of the factor model)

- FF5+Mom+RF panel: `core.factor_decomposition.load_factor_data` (cached on
  disk; no network).
- Per-edge HAC α + bootstrap CI: `scripts.factor_decomp_substrate_honest.regress_with_hac`
  (Newey-West, Politis-White auto-lag, 1000-iter residual moving-block bootstrap, seed 0).
- Joint-α t-stat with block-bootstrap CI on the **t-stat itself**:
  `engines.engine_f_governance.factor_alpha_gate.compute_alpha_tstat_with_bootstrap_ci`
  (the project-canonical function used by the Engine F retirement gate).
- Residual streams: derived from the SAME aligned-lstsq coefficients
  (`residual = excess − X·β̂`).
- Clustering: residual-corr → distance `sqrt(0.5·(1−ρ))` → `scipy` average linkage
  (the HRP convention in `engine_c_portfolio/optimizers/hrp.py`).
- Sharpe CI: `core.metrics_engine.MetricsEngine.bootstrap_distribution` (stationary
  block bootstrap, seed 0).

> Note on "HAC OLS": the brief and `core/factor_decomposition.py` (Discovery's
> Gate-6 entry) label the model "HAC" but that path actually uses **homoskedastic
> OLS** standard errors, which *inflate* t-stats on serially-correlated daily
> returns. I used the **genuinely-HAC** path (`factor_decomp_substrate_honest` /
> `factor_alpha_gate`) plus a block-bootstrap CI, so my t-stats are if anything
> *more* conservative than the "0/11" baseline the brief cites. Worth a follow-up
> to reconcile the Gate-6 entry path to true HAC (separate, propose-first — it's
> Engine D machinery).

---

## 3. Per-edge factor-α (FF5+Mom HAC, 2021-2025) — the core evidence

| edge | n_days | α ann % | α t-stat | α 95% CI low % | p(α>0) | raw Sharpe |
|---|---|---|---|---|---|---|
| momentum_edge_v1 | 794 | −5.2 | **−7.10** | −6.6 | 0.00 | −1.71 |
| value_earnings_yield_v1 | 583 | −3.4 | **−8.84** | −4.2 | 0.00 | 0.05 |
| value_book_to_market_v1 | 533 | −3.0 | **−8.59** | −3.7 | 0.00 | 0.67 |
| accruals_inv_sloan_v1 | 521 | −2.8 | **−6.15** | −3.7 | 0.00 | 0.80 |
| momentum_12_1_v1 | 497 | −2.6 | **−3.82** | −3.9 | 0.00 | 0.58 |
| low_vol_factor_v1 | 435 | −2.4 | **−3.71** | −3.7 | 0.00 | 0.61 |
| accruals_inv_asset_growth_v1 | 384 | −3.8 | **−11.15** | −4.4 | 0.00 | −0.13 |
| momentum_6_1_v1 | 361 | −3.0 | **−5.62** | −4.0 | 0.00 | 0.49 |
| short_term_reversal_v1 | 343 | −1.4 | **−2.87** | −2.4 | 0.00 | 4.48 |
| volume_anomaly_v1 | 254 | −0.9 | −1.59 | −2.0 | 0.06 | 5.63 |
| gap_fill_v1 | 206 | −2.7 | **−5.14** | −3.8 | 0.00 | 3.21 |
| earnings_vol_v1 | 65 | −4.2 | **−3.25** | −7.2 | 0.00 | −0.87 |
| insider_cluster_v1 (sparse, 31d) | 31 | −3.1 | −3.63 | −4.7 | 0.00 | 2.93 |

**The closet-beta tell.** `volume_anomaly` (raw Sharpe **5.63**), `short_term_reversal`
(**4.48**), `gap_fill` (**3.21**) look like the system's best edges on raw Sharpe — yet
their factor-α is negative. Their returns are **cheap-to-replicate factor beta**
(market / momentum / size exposure), not alpha. You are paying spread + commission
to manufacture something MTUM / VTV / USMV deliver for ~15 bps. This is precisely
what the factor decomp is for.

---

## 4. Clustering — the redundancy is real (but it's redundancy among losers)

Residual-return hierarchical cluster (k=4):

- **C1 — the factor-loser mega-cluster (9 edges):** accruals_inv_asset_growth,
  accruals_inv_sloan, low_vol_factor, momentum_12_1, momentum_6_1, momentum_edge,
  short_term_reversal, value_book_to_market, value_earnings_yield.
  Representative (highest, i.e. least-negative, factor IR): **momentum_12_1_v1** (IR −3.57).
- **C2 — gap_fill_v1** (singleton). IR −6.55.
- **C3 — volume_anomaly_v1** (singleton; the sole non-significantly-negative edge). IR −1.81.
- **C4 — earnings_vol_v1** (singleton). IR −7.87.

Representative high residual-ρ pairs inside C1 (confirming the split-signal premise):

| pair | residual ρ |
|---|---|
| accruals_inv_asset_growth ↔ value_earnings_yield | +0.56 |
| low_vol_factor ↔ momentum_edge | +0.53 |
| momentum_12_1 ↔ value_earnings_yield | +0.51 |
| low_vol_factor ↔ momentum_12_1 | +0.50 |
| momentum_12_1 ↔ momentum_edge | +0.49 |
| momentum_6_1 ↔ value_book_to_market | +0.49 |
| value_book_to_market ↔ value_earnings_yield | +0.48 |
| momentum_12_1 ↔ momentum_6_1 | +0.48 |
| accruals_inv_asset_growth ↔ accruals_inv_sloan | +0.45 |

The brief's "5 momentum / 6 value-quality split the same signal" is directionally
right: after removing common FF5+Mom exposure, the *idiosyncratic residuals* of
these 9 edges still co-move at ρ 0.45-0.56. The system has ~4 distinct residual
sleeves, not 12. **But all four sleeves are factor-negative**, so compressing to
them is multiple-testing hygiene, not an alpha gain (§5).

Compressed set (k=4 representatives): **momentum_12_1_v1, gap_fill_v1,
volume_anomaly_v1, earnings_vol_v1**.

---

## 5. Portfolio Sharpe — compressed vs bloated (2021-2025, common 1,087-day grid)

| Set | Sharpe | 95% CI | active-day fraction |
|---|---|---|---|
| Bloated (12) | +0.308 | [−1.013, +1.580] | 1.00 |
| Clusterable-only (12) | +0.294 | [−1.026, +1.568] | 1.00 |
| Compressed (4) | +1.543 | [+0.309, +2.632] | 0.61 |

**Do NOT read the compressed +1.54 as "compression improves Sharpe."** Two reasons:
(1) it is an *attribution-stream* Sharpe (realized PnL on close, not
mark-to-market), and the compressed set is flat 39% of days — its volatility is
understated; (2) more importantly, the compressed set's **factor-α t is −5.35** —
that +1.54 Sharpe is pure factor beta. A deployable compressed-portfolio Sharpe
requires an isolation re-run (see §7, gated follow-up); the attribution sum
cannot answer "does compression hold deployable Sharpe." The *alpha* question
(which the attribution stream CAN answer) already settles it: no.

---

## 6. Substrate-conditional caveat — the 12-yr window flips POSITIVE (and why it's a trap)

On the 2014-2025 deep run (0dcae34c) the **bloated joint α is POSITIVE**:
α +35.9%, t **+3.00**, CI [+1.18, +4.90]; compressed t +2.51. Taken at face value
this would say the inventory has alpha and compression roughly preserves it.

It doesn't — this is a known substrate trap (cf. `feedback_substrate_re_verify_before_recommend`,
CLAUDE.md #9, and the 16-yr "crisis-free bull flatters momentum" finding):

- The deep run is **76% momentum_edge** (9,732 / 12,832 trades; 824 dense days).
- Momentum_edge's α is **positive pre-2021** (momentum's golden decade) and
  **−5.2% / t −7.10 on 2021-2025**. The 12-yr positive α is bygone-regime
  momentum that has since decayed and reversed.
- The forward-relevant substrate is the recent one. On it, the verdict is
  uniformly negative.

So the deep-window positive α is reported for completeness but is **not** evidence
for deployment. If anything it reinforces the lesson: the only "alpha" the
inventory ever had was a momentum-regime that is gone.

---

## 7. Limitations (stated plainly)

1. **As-deployed, not standalone.** Per-edge streams are realized PnL from a
   *shared* ensemble backtest (capital-rivalry-diluted), not isolation. This is
   the correct object for the joint-α question (it's what's deployed) and is
   consistent with T-036/T-043, but a *standalone* per-edge decomp could differ.
   A per-edge isolation campaign (30 edges × multi-year ≈ a ≥4-cell cloud job)
   is the expensive follow-up — **only worth it if a result here had been
   promising. It wasn't, so I did not spend it.**
2. **Realized-PnL lumpiness.** PnL is booked on close, so a 30-day hold shows 29
   zero days + 1 lump. This understates daily vol and makes Sharpe lumpy. Same
   limitation as all prior project factor-α work; mark-to-market per-edge returns
   are not available (only ensemble-level `portfolio_snapshots`).
3. **Deep run lacks value/quality/accruals** (they don't trade on it), so the
   12-yr robustness covers only the momentum/low-vol/volume/gap subset.

None of these change the headline: on the recent substrate the components are
uniformly factor-negative, which no recombination can rescue.

---

## 8. RETIREMENT PROPOSAL (measurement + proposal only — NOT executed)

Per CLAUDE.md ("Never manually edit `edge_weights.json` or promote/retire edges
by hand; Engine F manages lifecycle autonomously"), nothing below is executed.
No `edges.yml`, `edge_weights.json`, or governor edits were made. This is evidence
for a director/user-gated decision.

The honest framing: **there is no "keep the good 4" story** — the 4 representatives
are the *least-bad*, all still factor-negative. The proposal is therefore tiered:

**Tier 1 — redundancy prune (multiple-testing hygiene; defensible independent of
alpha).** Within C1 the residual ρ is 0.45-0.56. Keep one representative per
*theme*, propose retiring the redundant siblings to shrink N_trials / DSR-MBL
trial-count exposure (no alpha is lost because none exists):
- Momentum: keep 1 of {momentum_edge, momentum_12_1, momentum_6_1} → retire 2.
- Value: keep 1 of {value_earnings_yield, value_book_to_market} → retire 1.
- Accruals: keep 1 of {accruals_inv_sloan, accruals_inv_asset_growth} → retire 1.

**Tier 2 — factor-α retirement (this is just the already-shipped T-043 gate).**
My decomp CONFIRMS and EXTENDS the T-043 retirement-gate verdict. T-043 found 6/7
of {gap, volume, value×2, accruals×2, STR} fire the α-ci_low<−2 gate; I add that
**momentum_edge, momentum_12_1, momentum_6_1, low_vol, earnings_vol, insider are
also factor-negative** and would fire the same gate. Enabling
`LifecycleConfig.factor_alpha_enabled=True` (currently disabled-by-default) would
autonomously retire ~12 of 13 over 2 cycles. **That empties the book — it must be
a USER decision, surfaced by the director, not an autonomous flip.** The sole
edge that does NOT fire on point estimate is `volume_anomaly_v1` (α t −1.59) —
keep/watch (matches T-043's "borderline" classing).

**Tier 3 — the real lever (out of scope here, but the actionable conclusion).**
Recombination of this inventory is exhausted. Forward alpha requires NEW
orthogonal substrate (microcap, managed-futures trend, options-vol-crush,
event-driven), per the Phase-0 diagnostic and the 2026-05-31 external research.
This is almost certainly Agent D's next task (literature edge implementation).

**Recommended sequencing for the director:** surface Tier-2 (enable the existing
T-043 gate) to the user as the headline decision; Tier-1 is subsumed by it. Do
NOT deploy any compressed sub-portfolio as an alpha vehicle.

---

## 9. Reproduce + determinism

```
PYTHONHASHSEED=0 python -m scripts.edge_compression_t117
```
Determinism: two consecutive runs produce a bit-identical
`data/measurements/edge_compression_t117_2026_06_06/edge_compression_results.json`
(md5 cc036abb…). All bootstraps seed=0.

## 10. Files

- `scripts/edge_compression_t117.py` (NEW — analysis, reuses existing machinery)
- `data/measurements/edge_compression_t117_2026_06_06/edge_compression_results.json` (NEW — full results, gitignored)
- This audit: `docs/Audit/edge_compression_t117_2026_06_06.md` (NEW)
- Reused: `core/factor_decomposition.py`, `scripts/factor_decomp_substrate_honest.py`,
  `engines/engine_f_governance/factor_alpha_gate.py`, `core/metrics_engine.py`,
  `engines/engine_c_portfolio/optimizers/hrp.py` (clustering convention)
- Prior art confirmed/extended: `docs/Audit/engine_f_lifecycle_factor_alpha_reeval_2026_05_12.md`
  (T-043), `docs/Audit/pairwise_signal_correlation_phase0_2026_05_12.md` (Phase 0)

## 11. NOT included (hard boundaries honored)

- No `edges.yml` / `edge_weights.json` / governor edits; no edge retired or paused.
- No `factor_alpha_enabled` flip.
- No `docs/State/TASK_LEDGER.md` write (protocol T-114 — proposed row is in the outbox).
- No isolation/cloud campaign spent (negative result did not warrant it).
