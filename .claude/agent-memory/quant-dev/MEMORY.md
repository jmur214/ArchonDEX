# Quant-Dev Memory Index

- [Backtest pipeline stages & the 30h dominator](project_backtest_pipeline_wall_time.md) — where time goes (signal stage), what's cheap (allocator/risk), and why execution-only replay is not separable.
- [No per-bar target-weight artifact is persisted](project_no_persisted_target_weights.md) — runs persist fills + snapshots only; weights live in-memory and are overwritten each bar.
- [T-165 in-process harness deadlock lives in the per-bar loop](project_t165_deadlock_per_bar_loop.md) — threaded logger-flush machinery; any path that drives BacktestController.run hits it.
- [Deployable-account leverage originates downstream of allocator weights](project_deployable_borrow_is_downstream.md) — Engine-B per-name sizing with no cash budget, not the allocator. Fix is propose-first.
- [T-237 EDGAR Lazy-Prices ingest: built + cost numbers + doc-format gotchas](project_t237_edgar_lazy_prices_ingest_2026_06_26.md) — PIT key=acceptanceDateTime, SGML-wrapped old .htm, full-universe ~3-4h cold / offline re-run, NN-FAIL-CLOSED verified.
- [T-321 agentic-analyst reader store map](project_t321_agentic_reader_stores.md) — exact paths/schemas for the 6 read-only tool readers; 4 of 6 stores don't exist on disk yet (fail-closed to []); data/processed is a symlink to tm-2.
- [Drip double count: Stooq dividend eras + T-082b slope](project_drip_double_count_stooq_eras_2026_11_11.md) — exact edges, PER-NAME pre-2003 eras; T-384 (a′) v4 after review: fails strict test on non-dividend Stooq defects; never approximate without payer status; build-reference ≠ validation.
- [T-387 cutover era_tr writer](project_t387_cutover_era_tr_writer_2026_11_12.md) — (a′) in tr_writer, byte-identical to v4 (2cee41ef…); parquet-from-text [us]; label inheritance; k≈1 hides the splice rail.
- [Report a check at its actual scope](feedback_report_the_checks_actual_scope_2026_11_12.md) — "post-seam identical" overclaimed a from-seam+14 check; record digest recipes or cite the committed manifest.
- [Reversion harness + worktree bash refusals](feedback_reversion_harness_and_worktree_bash_2026_11_12.md) — mutate-run-restore, print the first E-line; split git calls; Python via scratchpad files.
- [T-391 honest-N: what the 231/267 contain + standalone gap](project_t391_honest_n_standalone_trials_2026_11_12.md) — 267 is an N_eff; S=53 outside; branch unmerged, R2 89.92 gated / R3 324.28 reported.
- [Stooq transient blocks + yfinance quirks](reference_stooq_transient_blocks_and_yf_quirks.md) — 4,517 one-dividend reverting blocks fool ex-date probes; widening the window backfired; yf empty dividends for delisted; processed-read lock marker.
