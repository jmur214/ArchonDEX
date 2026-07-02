---
name: project-no-persisted-target-weights
description: Backtest runs do NOT persist per-bar target-weight vectors — only fills + snapshots. Disqualifies any "replay execution on cached weights" plan.
metadata:
  type: project
---

A backtest run dir (`data/trade_logs/<run_id>/`) persists: `trades.csv` (fills), `portfolio_snapshots.csv` (per-bar `cash`/`market_value`/`gross_notional`/`equity`), `performance_summary.json`, `regime_history.csv`, `engine_versions.json`.

**Per-bar target weights are NOT persisted anywhere.** They live only in memory at `engines/engine_c_portfolio/portfolio_engine.py:443` (`self.current_target_weights = weights`), overwritten each bar, never logged. Nothing in `cockpit/` writes them.

T-230's "250 per-bar mean_variance target-weight vectors" were captured by re-instrumenting a live OFF run on the local 2022 cell (250 = 2022 trading-day count), NOT read from a cached artifact. `git show e84cb10` (the T-230 commit) ships only `policy.py` + config + test + audit — no weight-extraction script.

**Consequence:** there is no cached-weight artifact to replay against, and reconstructing one still requires re-running the expensive signal stage ([[project_backtest_pipeline_wall_time]]). A weights-only replay would also be non-canonical (no census — `_build_census` @ `backtest_controller.py:1255` is assembled from live `AlphaEngine` state: `edge_signal_counts`, `edges_blind`, `fundamentals_blind`), violating `[NN-CENSUS]`/`[NN-FAIL-CLOSED]`.

Cheapest defensible alternative to a 30h full re-run: a reduced-cell cloud re-run (cov-pin proves determinism → N=1/arm instead of N=3, carry the arm0 anchor gate) ≈ 1/3 the cells, ~9h elapsed on Batch.
