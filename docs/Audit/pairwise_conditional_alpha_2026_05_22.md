---
title: Pair-wise conditional alpha matrix — extends Phase 0 + N-of-K
date: 2026-05-22 (director-side analysis during A/B chains)
author: director
data_source: data/research/per_ticker_scores/695b0b21-...parquet (10-edge 2024-era snapshot)
status: director-side analysis (read-only); third cheap diagnostic from the 2026-05-16 multi-strat dive
gate_decision: CONFIRMS the N-of-K finding — no robust idiosyncratic α at pair-wise level either
---

# Pair-wise conditional alpha matrix

## TL;DR — confirms N-of-K finding: no robust idiosyncratic α

Same data + same approach as Phase 0 (signal correlation) + N-of-K (agreement count), but at the per-pair granularity the 2026-05-16 multi-strategy research dive prescribed as the cheapest direct test of compound alpha.

**Method**: for each pair (A, B) of fired edges in the panel:
- Partition (Date, ticker) bars into 4 cells: only-A-fires, only-B-fires, both-agree-direction, both-disagree-direction
- Per cell: hit rate + mean return + Sharpe of the trade (1-day forward hold in dominant direction, no costs)
- Compare AGREE-cell Sharpe vs marginal-cell Sharpes
- For top compound-lift candidates: bootstrap CI on Sharpe + FF5+Mom factor decomp on daily-aggregated return stream

**Top 6 candidate pairs by raw AGREE-cell Sharpe:**

| Pair | n | Sharpe | CI_low | CI_high | α%/yr | α_t | Verdict |
|---|---|---|---|---|---|---|---|
| low_vol_factor_v1 + panic_v1 | **40** | 5.885 | +2.729 | 10.552 | +159% | **+2.066** | **CLEARS t>2 but n=40** |
| low_vol_factor_v1 + volume_anomaly_v1 | 542 | 2.068 | +0.307 | 3.794 | +41.69% | +1.609 | fails t>2 |
| pead_predrift_v1 + volume_anomaly_v1 | 138 | 1.626 | -0.914 | 4.430 | +111.29% | +1.654 | fails t>2 |
| pead_v1 + volume_anomaly_v1 | 221 | 1.560 | -0.764 | 3.306 | +123.82% | +1.202 | fails t>2 |
| gap_fill_v1 + pead_v1 | 84 | 1.767 | -2.632 | 6.554 | +63.20% | +0.642 | fails t>2 |
| gap_fill_v1 + panic_v1 | 141 | 2.108 | -0.652 | 4.248 | +46.10% | +0.631 | fails t>2 |

## Interpretation

### One apparent t > 2 hit, but small-sample + multiple-testing penalty

`low_vol_factor_v1 + panic_v1` clears t > 2 (α t-stat +2.066, α annualized +159%) with bootstrap CI low of +2.729. **At face value this is a positive finding.** Under closer scrutiny it falls apart:

1. **n = 40 is below the "stable" sample threshold** for HAC factor regression (6 factors + intercept = 7 parameters; rule-of-thumb needs >> 7 observations for stability). The HAC SE on the α t-stat is fragile.

2. **Multiple-testing penalty.** We tested 28 pairs in this sweep. Under the H₀ "no pair has α", expecting ~1-2 to clear t > 2 by chance (5% Type-I × 28 tests ≈ 1.4 expected false positives). Bonferroni at α=0.05 / 28 = 0.0018 → required t-stat ≈ 3.13. Our +2.066 doesn't clear it. BHY/FDR is less conservative but still penalizes substantially.

3. **DSR adjustment.** The 28-pair sweep adds 28 trials to the project's honest N (which was already ~75 per `docs/Audit/honest_n_mbl_computation_2026_05_12.md`). DSR with N=100+ on a 5-year window requires SR ≈ 1.55 to clear (per the metrics dive's MBL math). The +2.066 doesn't deflate cleanly to clearance.

**Conclusion on this specific pair**: low_vol + panic SHOWING compound signal at n=40 may or may not be real. We cannot tell from this data; need either (a) more data (multi-decade extension; T-050 deferred) or (b) out-of-sample test on different substrate. Filing as "suggestive but not confirmed."

### Larger-sample pairs (n ≥ 138) all fail t > 2

The four larger-sample pairs all have α t-stat in the +0.6 to +1.7 range — directionally positive but well below the gate. Per the standard pattern of every project measurement: per-bar signal real (bootstrap CI on per-bar Sharpe clears 0 in 4 of 6 pairs), but factor-decomposed daily-aggregate α fails t > 2. Same trap as N-of-K aggregate finding.

The most-trustworthy candidate is `low_vol_factor_v1 + volume_anomaly_v1`:
- n = 542 (large enough for robust factor regression)
- Per-bar bootstrap CI low = +0.307 (clears 0)
- α t-stat = +1.609 (directionally positive but fails t > 2)
- α annualized = +41.69% (large magnitude)

This pair has the BEST honest case among the candidates. Per CLAUDE.md it still fails the gate. Could be worth retesting on cockpit-fixed current-actives data (T-053 pending) and/or different substrate (T-056 microcap deferred).

### What does NOT change

The N-of-K + Phase 0 verdict stands:
- Signal-diversity gate fires (max ρ > 0.5 between raw signals on 2024-era panel)
- Compound signal exists at high agreement counts at the per-bar level
- Idiosyncratic α at t > 2 does NOT survive factor decomposition at the daily-portfolio level

Pair-wise drilling adds one nuance: a few specific pairs have stronger per-bar signal than the N-of-K aggregate would suggest, but factor decomp still wipes it out except in small-sample cases that don't survive multiple-testing.

## What this means for T-057 and the dispatch queue

**No change to T-057's revised framing.** The pair-wise analysis confirms what the N-of-K correction said: confidence-gated execution is a Sharpe-RESTRUCTURER (turnover + cost reduction + better factor exposure delivery), NOT an alpha-FINDER.

**One additional spec candidate surfaced (T-XX, NOT urgent):**
> T-058 candidate (deferred): re-run pair-wise conditional analysis post-T-053 on the CURRENT 6 actives. The 2024-era 10-edge panel here doesn't include the 4 V/Q/A fundamentals. If those edges produce different pair-wise patterns (e.g., 2-of-4 V/Q/A agreeing produces compound α at t > 2), that's the next-level diagnostic. Lower priority than T-057 + T-055c. Defer.

**The low_vol + panic finding is interesting enough to note** but NOT actionable without confirmation. Document as "suggestive small-sample observation; not action-grade." If future Discovery cycles produce a candidate that combines low-vol + panic-style features (regime-conditional sizing on volatility spikes), it inherits this finding as supporting context.

## Cross-research-dive consistency check

All four research dives + Phase 0 + N-of-K + pair-wise now CONVERGE on the same conclusion:
- The S&P 500 substrate is the empty quadrant of retail alpha space
- Classical retail-quant strategies on liquid US equities don't produce idiosyncratic α at t > 2
- Engine completion (T-055 vol-target, T-057 confidence-gating, T-043 lifecycle factor-α) delivers Sharpe-restructuring not alpha-discovery
- The path to actual α requires substrate change (microcap T-056 / multi-decade T-050) — both deferred per user 2026-05-12 data-spend gate

## Files

- Input: `data/research/per_ticker_scores/695b0b21-...parquet` (10-edge 2024-era snapshot)
- This audit: `docs/Audit/pairwise_conditional_alpha_2026_05_22.md`
- Companion (Phase 0): `docs/Audit/pairwise_signal_correlation_phase0_2026_05_12.md`
- Companion (N-of-K): `docs/Audit/n_of_k_agreement_diagnostic_2026_05_12.md`
- Companion (MBL): `docs/Audit/honest_n_mbl_computation_2026_05_12.md`
- Cited research: `docs/Sources/Alpha/Retail-algo-alpha_follow-up_multi-strat.md` §7 (Methodology for testing interaction effects)
