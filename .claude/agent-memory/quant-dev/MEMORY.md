# Quant-Dev Memory Index

- [Backtest pipeline stages & the 30h dominator](project_backtest_pipeline_wall_time.md) — where time goes (signal stage), what's cheap (allocator/risk), and why execution-only replay is not separable.
- [No per-bar target-weight artifact is persisted](project_no_persisted_target_weights.md) — runs persist fills + snapshots only; weights live in-memory and are overwritten each bar.
- [T-165 in-process harness deadlock lives in the per-bar loop](project_t165_deadlock_per_bar_loop.md) — threaded logger-flush machinery; any path that drives BacktestController.run hits it.
- [Deployable-account leverage originates downstream of allocator weights](project_deployable_borrow_is_downstream.md) — Engine-B per-name sizing with no cash budget, not the allocator. Fix is propose-first.
- [T-237 EDGAR Lazy-Prices ingest: built + cost numbers + doc-format gotchas](project_t237_edgar_lazy_prices_ingest_2026_06_26.md) — PIT key=acceptanceDateTime, SGML-wrapped old .htm, full-universe ~3-4h cold / offline re-run, NN-FAIL-CLOSED verified.
