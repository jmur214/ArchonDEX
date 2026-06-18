---
task_id: T-2026-06-17-197
title: Production discovery eval fixes — MBL-window + the signal-cache fail-open (ported from T-195)
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
type: measurement-correctness bug fixes (Engine D, autonomous-OK)
outcome: SHIPPED to production. The two T-193/T-195 blockers — which the T-195
  merge only fixed inside the standalone harness — are now closed in the
  production discovery code. (1) `_run_discovery_cycle` computed MBL Gate-0 on a
  24-month quick-filter window (T_years=2.0 < MBL_min~9.66) → every candidate
  died at Gate-0 before any alpha gate; now validates on the FULL MBL-clearing
  extent by default. (2) the `Gate1SignalCache` wrapper SWALLOWED a crashing
  edge's compute_signals to {} (indistinguishable from a legitimate no-signal) →
  silent degenerate baseline → fake Sharpe-0; now a swallowed crash is recorded
  structurally and a SYSTEMATIC crash FAILS LOUD (`DiscoveryBaselineError`). Both
  changes are discovery-(--discover)-path-only → the production backtest canon is
  byte-identical by construction (OFF-identical). 5 regression tests green.
status: CURRENT
---

# T-197 — port the two discovery eval fixes to production

## Fix 1 — MBL Gate-0 on the full window (not the 24-month quick-filter)
`orchestration/mode_controller.py::_run_discovery_cycle` set the validation
window to the last 24 months (`DISCOVERY_VALIDATION_MONTHS`, default 24).
`validate_candidate` computes MBL Gate-0 `T_years` from that window → `2.0 <
MBL_min≈9.66` (N≈125) → `killed_by_gate=gate_0_mbl` BEFORE any alpha gate (Gate-0
is fail-fast). The quick-filter is a PRE-SCREEN, not the validation extent.

**Fix:** the validation window now DEFAULTS to the FULL data_map extent (so
MBL/DSR are computed on the real evaluation window); an explicit
`DISCOVERY_VALIDATION_MONTHS` still selects a legacy sub-window for anyone who
deliberately wants the cheap screen (Gate-0 then correctly fails unless that
window clears MBL). Gate-3 (WFO) still does proper multi-window OOS internally.
Gate-0 now clears iff the cycle runs on an MBL-clearing (≥~10yr) backtest — which
is the correct condition. (Ported from the T-195 harness, where it was proven.)

## Fix 2 — the signal-cache exception-swallow (T-189-class fail-open) — STRUCTURAL
`engines/engine_d_discovery/gate1_signal_cache.py::CachedEdgeWrapper.
compute_signals` caught any non-programmer exception from the wrapped edge and
returned `{}` (empty signals) with only a debug-level warning. An empty `{}` from
a swallowed CRASH is byte-identical to an empty `{}` from a legitimate
"edge produced no signal" — so a systematically-crashing baseline edge degraded
to a 0-trade baseline silently (Sharpe 0 in ~4s, the T-195 degenerate baseline).
This is the session's recurring disease (T-088/T-167/T-175/T-189): a missing/
broken input degrades to a plausible number instead of failing loud.

**Fix (structural, not a point-patch):**
- The wrapper RECORDS each swallowed crash: `_eval_calls`, `_eval_errors`,
  `_last_error` + an `eval_error_rate` property. It still returns `{}` for that
  one bar (so a single bad bar doesn't abort the whole backtest mid-loop — the
  controller swallows raises there anyway), but the crash is no longer SILENT.
- `Gate1SignalCache.eval_error_report()` → `{edge_id: {errors, calls, rate,
  last_error}}` for any edge that swallowed ≥1 crash. A genuine no-signal NEVER
  appears here (errors==0) → **a swallowed crash is now distinguishable from a
  legitimate no-signal.**
- `Gate1SignalCache.assert_baseline_healthy()` raises `DiscoveryBaselineError`
  (named, with the rate + last error) when an edge crashed on a SYSTEMATIC
  fraction of bars (≥50%, ≥4 calls) — the degenerate-baseline signature. A
  TRANSIENT per-bar gap (tiny rate) is surfaced but does NOT raise (the
  legitimate narrow-catch is preserved).
- `validate_candidate` calls `assert_baseline_healthy()` right after the baseline
  backtest (when `use_signal_cache=True`) → a degenerate baseline now FAILS LOUD
  with an actionable message instead of publishing a fake Sharpe-0 contribution.

This also EXPOSES the underlying cause: instead of a silent 0, the error names the
crashing edge + its exception, so the root crash (the one the wrapper triggered in
T-195) becomes diagnosable.

## Sibling sweep (fix the family, not the line)
- `wfo.py:118` (`if not param_space: return {}`), `wfo.py:202` (`if not
  param_history: return {}`), `discovery.py:812` (`if not candidates: return
  {}`) — these are **legitimate early-returns**, NOT exception-swallows. Left
  unchanged.
- `gate1_signal_cache.py:124` (`_key_for` except → `str(now)`) — benign key
  fallback, not a signal swallow. Unchanged.
- `engines/engine_a_alpha/signal_collector.py` HAS the same swallow class
  (`except Exception` around `compute_signals`) — but it is in the SHARED
  PRODUCTION backtest path, so touching it WOULD move the production canon (out
  of this task's OFF-byte-identical scope). **FLAGGED for the director:** it is
  the same T-189-class fail-open and should be closed via the census/HALT path
  (T-189/T-194), as a canon-moving change, separately.

## Proofs
- **OFF byte-identical (by construction).** Both changes are discovery-only:
  `gate1_signal_cache` is imported ONLY by `discovery.py` (+ the harness), and
  `_run_discovery_cycle` is called ONLY under `if discover:`
  (`mode_controller.py:1080-1081`). A normal backtest (`discover=False`, the
  default) executes NEITHER → its trade canon cannot change.
- **`--runs 3` determinism:** `PYTHONHASHSEED=0 run_isolated --runs 3 --task q1`
  → [see §result] (the normal path is unchanged → stable).
- **Fail-loud test:** `tests/test_discovery_eval_fixes_t197.py` (5) — a
  systematically-crashing edge raises `DiscoveryBaselineError` (named); a healthy
  edge, a genuine no-signal, and a transient 1-bar gap all do NOT raise (and the
  no-signal is not flagged as a crash); the wrapper still memoizes real signals.

## Harness-contract note for B (T-196 cloud-discover)
No open contract question was posted in B's outbox. For the record, the validated
single-source-of-truth eval is `scripts/run_foundry_eval_t195.py` (merged): full
MBL-clearing window + clean-governor anchor baseline + `use_signal_cache=False`
+ one single-gene composite per tier-A/B feature + DSR `n_trials=#features`.
The cloud-discover path should INVOKE that harness per-candidate (not fork it);
the census assertion is `fundamentals_blind=0` + `n_trades>floor`; the
clean-governor baseline is restored from `data/governor/_isolated_anchor/`. With
T-197 merged, the production `--discover` path is ALSO correct, so the cloud path
may use either, but the harness stays the pre-registered reference. I'm available
to answer any specific contract question B raises.

## Files
- `orchestration/mode_controller.py` — Fix 1 (validation window → full extent)
- `engines/engine_d_discovery/gate1_signal_cache.py` — Fix 2 (crash tracking +
  `eval_error_report` + `assert_baseline_healthy` + `DiscoveryBaselineError`)
- `engines/engine_d_discovery/discovery.py` — `validate_candidate` calls
  `assert_baseline_healthy()` after the baseline run
- `tests/test_discovery_eval_fixes_t197.py` — 5 regression tests

## NOT included
No promotion / no `edge_weights.json` edit. No change to the production backtest
path (OFF byte-identical). `signal_collector`'s prod-path swallow flagged, not
touched (canon-moving). Branch only; director merges.
