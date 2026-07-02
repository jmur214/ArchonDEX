---
name: project-backtest-pipeline-wall-time
description: Backtest pipeline stages, which dominates wall-time (signal computation), and why an execution-only replay on cached weights is NOT separable from the expensive stage.
metadata:
  type: project
---

Pipeline: `cloud_entrypoint.sh` → `scripts/run_isolated.py` → `ModeController.run_backtest` (`orchestration/mode_controller.py:702`) → `BacktestController.run` (`backtester/backtest_controller.py:1442`, the per-bar loop).

Per-bar loop order: `_detect_regime` (E) → `_generate_signals` (A edges + signal gate) → `_prepare_orders` (C `compute_target_allocations` + B `prepare_order`) → `_execute_fills`/`_evaluate_stops`/`_log_snapshot`.

**Wall-time dominator = Engine-A signal/feature computation per bar** (the ~30h on a full-cycle 26yr PIT cell is almost all here). Two in-repo confirmations: T-211 audit ("defensive screens recompute cross-sectional vol across the whole universe every rebalance bar; quality_tilt_longs fetches fundamentals per bar → dominate per-bar cost, ~3-5× run time"); `docs/State/health_check.md:323` (RuleBasedEdge feature recompute = "minutes per backtest" uncached). Engine-C `allocate()` (`policy.py:188`) + Engine-B `prepare_order` sizing are trivial per bar by comparison.

**Why:** the signal stage is deterministic + unchanged by an execution-only fix — but you can't isolate execution from it, because stops/regime/exit signals are ALL recomputed per bar from the same slice (not just the target weights). See [[project_no_persisted_target_weights]].

`run_backtest_pure` (`orchestration/run_backtest_pure.py`) is the closest decoupled harness (reuses the real `BacktestController`, no reimplementation) but STILL builds a real `AlphaEngine` and regenerates signals inside the loop — no weight-injection seam to skip Engine A.
