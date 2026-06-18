---
task_id: T-2026-06-17-195
title: Discovery eval-harness fix (the two T-193 blockers) + the valid-foundry-test cloud trigger
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
outcome: HARNESS FIXED + root-caused; VALID TEST is cloud-bound. The two T-193
  blockers are both real measurement bugs and both now have a fix: (1) MBL Gate-0
  ran on the 24-month quick-filter window (T_years=2 < 9.66) → killed every
  candidate before any alpha gate → fix = validate on the FULL MBL-clearing
  window; (2) the baseline was degenerate (Sharpe 0) from TWO causes — a polluted
  governor (2 active vs the canonical 6) AND the Gate1SignalCache wrapper
  SWALLOWING baseline-edge exceptions (gate1_signal_cache.py:147-152) → empty
  signals → silent 0-trade baseline → fix = clean governor anchor +
  use_signal_cache=False (PureBacktestCache still memoizes the baseline result, so
  the cross-candidate speedup is preserved). Confirmed qualitatively: with the fix
  the baseline TRADES (real fills) vs the prior 4s/Sharpe-0. The corrected driver
  is scripts/run_foundry_eval_t195.py. BUT the full repeatable LOCAL run is
  intractable (≈3-5 min/candidate over the 13yr MBL window × 35 features × 3
  determinism runs = many hours, AND the recurring fundamentals-fetch stall) —
  exactly the brief's trigger to build the pre-authorized cloud-discover path.
status: HARNESS FIXED; valid verdict needs the cloud-discover path (compute trigger hit)
---

# T-195 — discovery eval-harness fix

## Bug A (Fix 1) — MBL Gate-0 on the wrong window
`_run_discovery_cycle` validates each candidate on a 24-month quick-filter window
(`mode_controller.py:1301`, `DISCOVERY_VALIDATION_MONTHS=24`). `validate_candidate`
computes MBL Gate-0 `T_years` from that same window → `T_years=2.00 < MBL_min≈9.66`
(N_eff≈125) → `killed_by_gate=gate_0_mbl` BEFORE any alpha gate (Gate-0 is
fail-fast). The quick-filter is a cheap PRE-SCREEN; MBL/DSR belong on the full
evaluation window. **Fix:** validate on the full MBL-clearing window (the corrected
driver uses 2012-2024 = 13yr → `T_years=13 > 9.66`, Gate-0 clears, alpha gates run).

## Bug B (Fix 2) — degenerate baseline (Sharpe 0 → meaningless contribution)
Two independent causes, both real:
1. **Polluted governor.** My iterative T-193 runs (`--reset-governor` + 60+ added
   candidates) left `edges.yml` at **2 active** edges vs the canonical **6**
   (anchor). A 2-edge book barely trades. **Fix:** restore the clean governor
   anchor (`_isolated_anchor/{edges.yml,edge_weights.json,…}`) → the real 6-edge
   production book (gap_fill, volume_anomaly, 4 value/accruals) — verified it
   TRADES standalone (continuous MVO allocations + fills over 2010-2024).
2. **The Gate1SignalCache wrapper swallows baseline-edge exceptions.** With
   `use_signal_cache=True` (the production default), `CachedEdgeWrapper.
   compute_signals` (`gate1_signal_cache.py:147-152`) catches any non-programmer
   exception and returns `{}` (empty signals). If a baseline edge raises, the
   baseline silently degrades to 0 trades → `baseline_sharpe=0` in ~4s (no real
   backtest). This is a **measurement-integrity bug of the T-189 class** (a
   missing input degrades to a plausible-looking 0 instead of failing loud).
   **Fix:** `use_signal_cache=False` in the eval — `PureBacktestCache` still
   memoizes the baseline *result* across candidates, so the cross-candidate
   speedup is preserved. Verified: with cache off + clean governor, the baseline
   runs the real backtest and TRADES (vs 4s/0 with it on).

So `contribution = Sharpe(book + candidate) − Sharpe(book)` is now a TRUE marginal.

## Bonus perf fix (needed to run the eval at all)
`backtest_controller.py:786` printed `[DEBUG_BACKTEST_FILL_CREATED]` for EVERY
fill, UNCONDITIONALLY (mislabeled DEBUG, ungated). Over a 13yr/109-ticker backtest
that is tens of thousands of prints → a major wall-time + log-bloat drag. Gated it
behind `is_controller_debug()` (prints don't enter the trade canon → canon-safe).

## The corrected harness — `scripts/run_foundry_eval_t195.py`
Full MBL-clearing window + restore clean governor anchor + `use_signal_cache=False`
+ one single-gene long composite per tier-A/B feature (cross-sectional →
percentile; ticker-independent → absolute, T-177). DSR `n_trials=#features`.

## PRE-REGISTRATION (corrected eval — written before the verdict)
- **Window:** 2012-2024 (13yr) — clears MBL Gate-0 at N≈125.
- **Baseline source:** the CLEAN governor anchor (the canonical 6-edge production
  book), `use_signal_cache=False` (real baseline, not the cache-degenerate one).
- **Gate (UNCHANGED):** Gate-1 contribution_sharpe>0.10, Gate-2 PBO≥0.60, Gate-4
  perm p<0.05 (BH-FDR), Gate-5 universe-B>0, Gate-6 FF5+Mom t>2 & α>2%, Gate-7
  substrate-B drift≤0.5, **Gate-8 DSR p>0.95 honest-N** (n_trials=#features).
- **Census:** `fundamentals_blind=0` (simfin loads offline, verified T-193).
- **H1:** ≥1 foundry feature clears with a real positive contribution + DSR.
  **H0:** explored, nothing clears (honest null).
- **Determinism:** `--runs 3` on the corrected eval (deterministic given clean
  governor + seeded RNG).

## Why the LOCAL verdict didn't complete (the cloud trigger)
With the harness fixed, each candidate is a real baseline+with-candidate backtest
over the 13yr MBL window (109 tickers) ≈ **3-5 min/candidate** even with the
fill-print gated (the value edges' per-ticker fundamentals path is the residual
cost), AND the run STALLED on a fundamentals fetch (`LMT … Fetching fundamentals`
— the recurring no-timeout-fetch flakiness, T-161 class). A full **35-feature × 3
determinism** repeatable local run is many hours + flaky. **Per the brief, this is
the trigger to build the pre-authorized cloud-discover path** (the canonical venue
for the MBL-clearing per-candidate gauntlet at scale). The harness is correct; the
LOCAL substrate just can't run it repeatably.

## Proposed production-code fixes (for the director — measurement-correctness)
1. `mode_controller._run_discovery_cycle`: compute MBL Gate-0 / DSR on the full
   evaluation extent, not the 24-month quick-filter (or load long-history data for
   the validation step). Today the local cycle structurally can't promote.
2. `gate1_signal_cache.CachedEdgeWrapper`: do NOT swallow baseline-edge exceptions
   to `{}` — propagate (programmer-error class) or set an explicit `degraded`
   flag the census treats as FAIL (T-189 class). A silent empty baseline is the
   exact fail-open the measurement-integrity work targets.
3. `backtest_controller.py:786` fill-print — gated here (perf).

## State / hygiene
Governor restored to the clean 6-active anchor; `ga_population.yml` legacy preserved
in Archive (gitignored, worktree-local). No edges promoted; no `edge_weights.json`
edits. The fill-print gate is the only behavior change to committed code (canon-safe).
