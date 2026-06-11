# CLI Scripts Directory
**Purpose:** Command-line wrappers to invoke specific workflows or execute tests without burying the user in Python imports.
**Architectural Role:** The user-facing execution layer.

**Key Categories:**
- *One-Button Orchestrators:* `run_autonomous_cycle.py` (Full ML Loop).
- *Execution:* `run_backtest.py`, `run_paper_loop.py`.
- *Diagnostics:* `run_healthcheck.py` (true math test), `system_validity_check.py`.
- *Documentation:* `sync_docs.py` (AST markdown generator).

*Note: Over 10 legacy proof-of-concept scripts were purged to `Archive/scripts/` during the Phase 6 Code Audit. See `docs/Audit/codebase_findings.md` for historical mapping.*

<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->

## Auto-Generated Code Reference

*This section is automatically built by `scripts/sync_docs.py`. Do not edit manually.*

### `_hmm_causal_proba.py`
**Module Docstring:** T-2026-05-31-089 — canonical CAUSAL HMM posterior helper for validators.
- **Function `causal_proba_sequence()`**: Compute CAUSAL (filtered) HMM posteriors over a panel.

### `ab_engine_c_hrp.py`
**Module Docstring:** A/B harness: weighted_sum vs HRP under run_isolated.
- **Function `main()`**: No docstring

### `ab_path_a_tax_efficient_core.py`
**Module Docstring:** A/B/C/D harness — Path A tax-efficient core (HRP slice 2 + turnover
- **Function `main()`**: No docstring

### `aggregate_t055c.py`
**Module Docstring:** T-2026-05-22-055c aggregation — read per-arm incremental JSON,
- **Function `main()`**: No docstring

### `aggregate_t055d.py`
**Module Docstring:** T-2026-05-22-055d aggregation — read per-arm incremental JSON,
- **Function `main()`**: No docstring

### `aggregate_t055e.py`
**Module Docstring:** T-2026-05-23-055e aggregation — read per-arm incremental JSON,
- **Function `main()`**: No docstring

### `aggregate_t057b.py`
**Module Docstring:** T-2026-05-23-057b aggregation — bootstrap CI on the 2-arm × 5-yr ×
- **Function `main()`**: No docstring

### `aggregate_t057b_cloud.py`
**Module Docstring:** T-2026-05-23-057b-analyze cloud-results aggregator.
- **Function `main()`**: No docstring

### `analyze_bab_deep_t129.py`
**Module Docstring:** scripts/analyze_bab_deep_t129.py
- **Function `build_returns_panel()`**: No docstring
- **Function `build_bab_streams()`**: Monthly-rebalanced FP BAB — identical to T-123 except the window and the
- **Function `factor_report()`**: No docstring
- **Function `book_correlation()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_bab_factor_t123.py`
**Module Docstring:** scripts/analyze_bab_factor_t123.py
- **Function `build_returns_panel()`**: No docstring
- **Function `build_bab_streams()`**: Monthly-rebalanced BAB. Returns (longshort_daily, longonly_daily).
- **Function `factor_report()`**: No docstring
- **Function `book_correlation()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_discovery_diagnostic.py`
**Module Docstring:** scripts/analyze_discovery_diagnostic.py
- **Function `load_records()`**: No docstring
- **Function `fmt_pct()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_edges.py`
*No public classes or functions found.*

### `analyze_engine_e_hmm_ab.py`
**Module Docstring:** scripts/analyze_engine_e_hmm_ab.py
- **Function `main()`**: No docstring

### `analyze_oos_2025.py`
**Module Docstring:** scripts/analyze_oos_2025.py
- **Function `load_trades()`**: No docstring
- **Function `pivot_pnl()`**: No docstring
- **Function `pivot_fills()`**: No docstring
- **Function `regime_pnl_crosstab()`**: No docstring
- **Function `regime_fill_crosstab()`**: No docstring
- **Function `regime_by_month()`**: No docstring
- **Function `cumulative_top_bottom()`**: No docstring
- **Function `spy_monthly_return()`**: No docstring
- **Function `rivalry_probe()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_overnight_intraday_t135.py`
**Module Docstring:** scripts/analyze_overnight_intraday_t135.py
- **Function `build_panels()`**: Return (total, overnight, intraday) daily log-return panels.
- **Function `build_strategy()`**: Monthly-rebalanced LPS overnight-persistence long-short.
- **Function `persistence_check()`**: LPS structure diagnostic: Spearman corr of past-21d mean r_on rank vs
- **Function `factor_report()`**: No docstring
- **Function `book_correlation()`**: No docstring
- **Function `ann_stats()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_per_edge_isolation.py`
**Module Docstring:** scripts/analyze_per_edge_isolation.py
- **Function `load_grid()`**: No docstring
- **Function `cross_year_sharpe_ci()`**: Cross-year bootstrap CI on mean Sharpe.
- **Function `build_edge_daily_returns()`**: Aggregate the per-edge daily PnL stream across all yearly isolated
- **Function `trade_count_per_edge()`**: Count closed trades across all yearly isolated runs for one edge.
- **Function `per_edge_verdict()`**: Assign verdict per spec line:
- **Function `render_markdown()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_vrp_factor_t122.py`
**Module Docstring:** scripts/analyze_vrp_factor_t122.py
- **Function `build_market_return()`**: Equal-weight daily return of the processed universe — the market proxy
- **Function `vrp_signal_series()`**: Daily VRP scale ∈[0,1] using the SAME VIX−RV formula as the edge
- **Function `vrp_return_stream()`**: Vol-managed market return: scale_{t-1} * market_return_t, minus cost on
- **Function `factor_report()`**: No docstring
- **Function `book_correlation()`**: Correlation of VRP return to the existing 6-active-edge book + to the
- **Function `main()`**: No docstring

### `audit_data_gaps.py`
- **Function `audit_file()`**: No docstring
- **Function `main()`**: No docstring

### `audit_feature_archive.py`
**Module Docstring:** 90-day archive enforcement for the Feature Foundry.
- **Class `AuditDecision`**: No docstring
- **Function `evaluate_card()`**: Decide whether `card` should be flagged review_pending.
- **Function `apply_decision()`**: Mutate the card in-place and write it back when the action is
- **Function `reset_pending()`**: Optional: clear all `review_pending` flags before re-running.
- **Function `run_audit()`**: Iterate over every card in `root`, evaluate, and (unless
- **Function `main()`**: No docstring

### `audit_per_edge_substrate.py`
**Module Docstring:** scripts/audit_per_edge_substrate.py
- **Function `main()`**: No docstring

### `audit_six_names_isolation.py`
**Module Docstring:** scripts/audit_six_names_isolation.py
- **Function `main()`**: No docstring

### `audit_surviving_edges_multi_year.py`
**Module Docstring:** scripts/audit_surviving_edges_multi_year.py
- **Function `main()`**: No docstring

### `backfill_decision_diary.py`
**Module Docstring:** One-shot backfill of decision diary with this week's load-bearing decisions.
- **Function `main()`**: No docstring

### `backfill_t052_macro_data.py`
**Module Docstring:** T-2026-05-12-052 macro/ETF data backfill.
- **Function `fetch_anfci()`**: No docstring
- **Function `fetch_etf()`**: No docstring

### `backtest_transition_warning.py`
**Module Docstring:** scripts/backtest_transition_warning.py
- **Function `build_extended_panel()`**: Build an extended daily feature panel covering `start` → `end`.
- **Function `detect_real_transitions()`**: Identify durable argmax-state transitions in a posterior sequence.
- **Function `evaluate_anchor_events()`**: For each anchor event, find lead time of the first warning fire.
- **Function `main()`**: No docstring

### `baseline_metrics_report_t066.py`
**Module Docstring:** scripts/baseline_metrics_report_t066.py
- **Function `load_equity_curve()`**: Load equity from a run's portfolio_snapshots.csv (cockpit-fixed schema).
- **Function `compute_per_year_metrics()`**: Apply the full T-059..T-063 metric suite to a single year's equity.
- **Function `compute_full_panel_metrics()`**: Aggregate metrics computed on the per-year cells.
- **Function `compute_pbo_across_years()`**: Run PBO via CSCV across the 5-year panel. Each year is one "trial";
- **Function `main()`**: No docstring
- **Function `generate_audit_md()`**: Generate the markdown audit doc.

### `cointegration_pair_screen.py`
**Module Docstring:** scripts/cointegration_pair_screen.py
- **Function `load_close_series()`**: Load adjusted closes from data/processed/<ticker>_1d.csv as a
- **Function `aligned_log_prices()`**: Restrict both series to [start, end], align on common dates,
- **Function `estimate_beta_ols()`**: OLS: log_y = α + β·log_x + ε. Returns (alpha, beta) via
- **Function `half_life_ar1()`**: Estimate half-life of mean reversion via AR(1) on Δspread vs
- **Function `beta_stability()`**: Compute β per yearly subsample. Returns (per_year_betas, instability_pct)
- **Function `screen_pair()`**: Run the full screen on one pair. Returns a dict with diagnostics
- **Function `main()`**: No docstring

### `cointegration_pair_screen_t031.py`
**Module Docstring:** scripts/cointegration_pair_screen_t031.py
- **Function `main()`**: No docstring

### `compare_leaky_vs_causal_t089.py`
**Module Docstring:** T-2026-05-31-089 — quantify leaky-vs-causal AUC inflation.
- **Function `main()`**: No docstring

### `dbmf_kmlm_phase0_t110.py`
**Module Docstring:** T-110 Phase 0 — DBMF + KMLM managed-futures ETFs diagnostic.
- **Function `load_stooq_etf()`**: No docstring
- **Function `daily_returns()`**: No docstring
- **Function `sharpe_ratio()`**: No docstring
- **Function `sortino_ratio()`**: No docstring
- **Function `max_drawdown()`**: No docstring
- **Function `politis_white_block()`**: No docstring
- **Function `block_bootstrap_ci()`**: No docstring
- **Function `analyze()`**: No docstring
- **Function `verdict_for()`**: Map ETF result to PROCEED-INTEGRATE / MIXED / DEAD.
- **Function `main()`**: No docstring

### `demo_dynamic_optimization_t139.py`
**Module Docstring:** T-139 payoff demonstration — frozen-fixture comparison, NOT a backtest.
- **Function `build_fixture()`**: No docstring
- **Function `annualized_te()`**: No docstring
- **Function `main()`**: No docstring

### `det_d1_repro.py`
**Module Docstring:** scripts/det_d1_repro.py
- **Function `md5()`**: No docstring
- **Function `hash_governor_state()`**: No docstring
- **Function `file_size()`**: No docstring
- **Function `gov_sizes()`**: No docstring
- **Function `find_run_id()`**: No docstring
- **Function `trades_canon_md5()`**: MD5 of trades.csv with run_id+meta columns dropped (mirrors
- **Function `run_one()`**: Single 2025 OOS Q1-style run with --reset-governor.
- **Function `main()`**: No docstring

### `det_d2_bisect.py`
**Module Docstring:** scripts/det_d2_bisect.py
- **Function `md5()`**: No docstring
- **Function `snapshot_drifted()`**: Capture the current live governor state as the 'drifted' anchor.
- **Function `restore_from_drifted()`**: Restore the four candidate files from the drifted snapshot.
- **Function `override_one_from_clean()`**: After restore_from_drifted(), copy `file_to_override` from CLEAN
- **Function `find_run_id()`**: No docstring
- **Function `trades_canon_md5()`**: No docstring
- **Function `run_one()`**: Single 2025 OOS Q1 run. Caller is responsible for governor-state
- **Function `main()`**: No docstring

### `diagnose_crisis_path_t100.py`
**Module Docstring:** T-2026-06-04-100 — diagnose the existing HMM crisis-de-gross path.
- **Function `install_advisory_monkeypatch()`**: Wrap AdvisoryEngine.generate so every per-bar call records its
- **Function `install_detect_regime_monkeypatch()`**: Wrap RegimeDetector.detect_regime so it stamps the timestamp onto
- **Function `run_backtest()`**: Run a 26-yr arm0_off backtest. Returns the run_id.
- **Function `read_snapshot_gross()`**: Load portfolio_snapshots.csv → DataFrame with per-bar
- **Function `compute_offline_hmm_p_crisis()`**: Build the HMM feature panel + drive HMMRegimeClassifier.predict_proba_at
- **Function `analyze()`**: Cross-join + summary stats per year + crisis-bar / benign-bar
- **Function `main()`**: No docstring

### `diagnose_realistic_slippage.py`
**Module Docstring:** scripts/diagnose_realistic_slippage.py
- **Function `find_latest_trade_log()`**: Locate the most recently-written trades.csv under data/trade_logs/.
- **Function `load_bar_data()`**: Load the daily parquet for a ticker; None if missing.
- **Function `trailing_window()`**: Return up to n_days of bar data ending at-or-before `as_of` (no look-ahead).
- **Function `main()`**: No docstring

### `discovery_diag_analytics.py`
**Module Docstring:** scripts/discovery_diag_analytics.py
- **Function `load_jsonl()`**: No docstring
- **Function `first_failed_histogram()`**: Count of candidates by first_failed_gate label.
- **Function `per_gate_pass_rate()`**: For each gate, count (n_evaluated, n_passed). A gate is
- **Function `wall_time_stats()`**: Per-candidate wall-time distribution.
- **Function `candidate_origin_distribution()`**: Distribution of candidate archetypes — informs GA vocabulary diagnostic.
- **Function `gene_type_distribution()`**: What gene primitives is the GA composing candidates from?
- **Function `bootstrap_survival_ci()`**: Bootstrap 95% CI on the binary survive-the-gauntlet rate.
- **Function `summarize()`**: No docstring
- **Function `main()`**: No docstring

### `doc_lint.py`
**Module Docstring:** doc_lint — anti-rot guard for the documentation system.
- **Class `CheckResult`**: No docstring
- **Function `check_memory_size()`**: No docstring
- **Function `check_current_state_freshness()`**: No docstring
- **Function `check_memory_supersession_markers()`**: No docstring
- **Function `check_memory_audit_doc_refs()`**: No docstring
- **Function `check_memory_entries_have_dates()`**: No docstring
- **Function `check_task_ledger_columns()`**: No docstring
- **Function `check_scripts_in_execution_manual()`**: No docstring
- **Function `main()`**: No docstring

### `edge_compression_t117.py`
**Module Docstring:** scripts/edge_compression_t117.py
- **Function `build_panel()`**: Per-edge daily-return panel stitched across the yearly runs.
- **Function `factor_residual_stream()`**: Date-indexed FF5+Mom residual (idiosyncratic) return stream.
- **Function `factor_information_ratio()`**: Annualized factor-adjusted (cost-adjusted, since PnL is net) IR =
- **Function `cluster_residuals()`**: Hierarchical clustering on residual-return correlation distance.
- **Function `combined_stream()`**: Equal- or custom-weighted sum of per-edge daily return streams.
- **Function `joint_alpha()`**: HAC FF5+Mom alpha t-stat with residual moving-block bootstrap CI
- **Function `sharpe_with_ci()`**: Block-bootstrap Sharpe CI of a combined attribution stream.
- **Function `main()`**: No docstring

### `factor_decomp_per_regime.py`
**Module Docstring:** scripts/factor_decomp_per_regime.py
- **Function `load_closed_trades_for_edge()`**: Concatenate closed-trade rows for this edge across the provided
- **Function `build_daily_returns_per_regime()`**: Group closed-trade PnL by (date, regime_label) and build a
- **Function `regress_hac_with_bootstrap()`**: OLS + Newey-West HAC + residual bootstrap CI on α (annualized).
- **Function `classify_edge()`**: Apply the spec's 5-bucket verdict per edge across its regimes.
- **Function `analyze_edge()`**: Full per-regime decomp for one edge.
- **Function `render_markdown()`**: Produce the audit-doc markdown.
- **Function `build()`**: No docstring
- **Function `main()`**: No docstring

### `factor_decomp_per_regime_t036.py`
**Module Docstring:** scripts/factor_decomp_per_regime_t036.py
- **Function `main()`**: No docstring

### `factor_decomp_substrate_honest.py`
**Module Docstring:** scripts/factor_decomp_substrate_honest.py
- **Function `newey_west_lag()`**: Politis-style automatic lag: floor(4 * (T/100)^(2/9)).
- **Function `newey_west_cov()`**: Hand-rolled Newey-West (Bartlett-kernel) HAC covariance.
- **Function `load_arm1_attribution()`**: Build per-edge daily-PnL-as-return series from the 5 Arm 1 yearly runs.
- **Function `regress_with_hac()`**: OLS with Newey-West HAC SE; returns alpha + t-stats + betas + R².
- **Function `verdict_bucket()`**: Apply the spec's verdict framing to volume_anomaly_v1's result.
- **Function `render_markdown()`**: No docstring
- **Function `build()`**: No docstring
- **Function `main()`**: No docstring

### `factor_decomposition_baseline.py`
**Module Docstring:** scripts/factor_decomposition_baseline.py
- **Function `find_latest_trade_log()`**: No docstring
- **Function `edge_daily_returns()`**: Group trades by edge_id and compute a daily return stream per edge.
- **Function `regress_edge_on_factors()`**: OLS: edge_excess_return ~ alpha + sum(beta_i * factor_i).
- **Function `write_report()`**: No docstring
- **Function `main()`**: No docstring

### `feature_foundry_gate.py`
**Module Docstring:** Feature Foundry CI gate.
- **Class `FeatureCheck`**: No docstring
- **Function `load_margin()`**: Resolve the adversarial margin: env var > YAML config > default.
- **Function `run_pytest()`**: Run the Feature Foundry test module. Returns the pytest exit code.
- **Function `import_feature_modules()`**: Import each changed feature file so its `@feature` decorator runs.
- **Function `validate_model_cards()`**: Run the existing card validator scoped to changed features.
- **Function `adversarial_check()`**: Real-vs-twin lift comparison.
- **Function `resolve_changed_paths()`**: Decide which feature files to gate.
- **Function `main()`**: No docstring

### `fetch_all.py`
- **Function `main()`**: No docstring

### `fetch_data.py`
- **Function `main()`**: No docstring

### `fetch_leading_indicators.py`
**Module Docstring:** fetch_leading_indicators — cache copper, gold, XLP, XLY closes to data/macro/.
- **Function `fetch_one()`**: No docstring
- **Function `main()`**: No docstring

### `fetch_missing_delisted.py`
**Module Docstring:** scripts/fetch_missing_delisted.py
- **Class `FetchResult`**: No docstring
  - `def as_record()`
- **Function `fetch_via_yfinance()`**: Returns (DataFrame, yahoo_symbol_used). Empty DataFrame on failure.
- **Function `fetch_via_alpaca()`**: Pull daily bars from Alpaca Market Data v2.
- **Function `fetch_via_stooq()`**: Stooq returns full history as CSV; we slice to [start, end] post-fetch.
- **Function `save_ticker()`**: Persist OHLCV; returns the row count after truncation/cleaning.
- **Function `load_provenance()`**: No docstring
- **Function `save_provenance()`**: No docstring
- **Function `fetch_one()`**: No docstring
- **Function `discover_missing_tickers()`**: No docstring
- **Function `parse_args()`**: No docstring
- **Function `run()`**: No docstring
- **Function `main()`**: No docstring

### `fetch_universe.py`
**Module Docstring:** scripts/fetch_universe.py
- **Class `FetchSummary`**: No docstring
  - `def report()`
- **Function `parse_args()`**: No docstring
- **Function `load_ticker_list()`**: Resolve --source into a deduped, sorted ticker list.
- **Function `split_cached_vs_missing()`**: Partition the universe into already-cached vs. missing tickers.
- **Function `credentials_available()`**: True if DataManager will be able to talk to Alpaca.
- **Function `fetch_one()`**: Fetch a single ticker and return (success, message).
- **Function `run()`**: No docstring
- **Function `main()`**: No docstring

### `fetch_vix_term_structure.py`
**Module Docstring:** fetch_vix_term_structure — cache CBOE VIX-family closes to data/macro/.
- **Function `fetch_one()`**: No docstring
- **Function `main()`**: No docstring

### `gen_substrate_manifest.py`
**Module Docstring:** Generate (or verify) the pinned data-substrate manifest.
- **Function `iter_substrate_files()`**: No docstring
- **Function `hash_file()`**: No docstring
- **Function `build_manifest()`**: No docstring
- **Function `main()`**: No docstring

### `gen_t118_campaign_spec.py`
**Module Docstring:** scripts/gen_t118_campaign_spec.py
- **Function `build_arms()`**: No docstring
- **Function `main()`**: No docstring

### `harvest_data.py`
- **Function `harvest()`**: Run a simulation to collect (Features, Label) pairs for ML training.

### `hrp_slice_3_redistribution_histogram.py`
**Module Docstring:** Sanity histogram for HRP slice 3's redistribution behaviour.
- **Function `build_data_map()`**: Two-cluster synthetic returns with mild within-cluster noise.
- **Function `collect_optimizer_weights()`**: No docstring
- **Function `histogram()`**: Bucket optimizer_weights into [0, 0.25), [0.25, 0.5), ... up to
- **Function `render_md_block()`**: No docstring
- **Function `main()`**: No docstring

### `ingest_stooq_us_daily.py`
**Module Docstring:** scripts/ingest_stooq_us_daily.py
- **Function `normalize_ticker_for_stooq()`**: Convert project-shape ticker to Stooq-shape filename stem.
- **Function `build_stooq_index()`**: Walk the Stooq tree and build {ticker_lower: path} index.
- **Function `parse_stooq_file()`**: Parse a Stooq .us.txt file → DataFrame in project schema.
- **Function `write_processed()`**: No docstring
- **Function `get_target_tickers()`**: No docstring
- **Function `main()`**: No docstring

### `inter_edge_correlation.py`
**Module Docstring:** Inter-edge correlation matrix on the 6 active edges + recent paused (0.25x) edges.
- **Function `load_trades()`**: No docstring
- **Function `daily_pnl_by_edge()`**: Aggregate realized PnL per edge per day. Open trades have empty pnl; we keep
- **Function `compute_correlations()`**: Daily-PnL Pearson correlation among the requested edges.
- **Function `render_report()`**: No docstring
- **Function `main()`**: No docstring

### `inter_edge_correlation_regime.py`
**Module Docstring:** Regime-conditional inter-edge correlation matrix.
- **Function `load_trades()`**: No docstring
- **Function `daily_pnl_by_edge()`**: No docstring
- **Function `daily_regime_per_date()`**: Return the dominant (mode) regime label per trading day. When a
- **Function `bucket_regimes()`**: Map per-day regime labels into {benign, adverse, other}.
- **Function `correlation_for_bucket()`**: No docstring
- **Function `render_md_table()`**: No docstring
- **Function `render_report()`**: No docstring
- **Function `main()`**: No docstring

### `interaction_diagnostic_t132.py`
**Module Docstring:** scripts/interaction_diagnostic_t132.py
- **Function `assemble_panel()`**: No docstring
- **Function `decorrelate()`**: No docstring
- **Function `make_shifted_targets()`**: Yield y vectors where the (date×ticker) forward-return matrix is rolled
- **Function `h2_pair()`**: No docstring
- **Function `fit_gbm()`**: No docstring
- **Function `main()`**: No docstring

### `journal_apply.py`
**Module Docstring:** journal_apply — apply LifecycleJournal entries to data/governor/edges.yml.
- **Class `ApplyResult`**: No docstring
  - `def to_dict()`
- **Function `read_mark()`**: No docstring
- **Function `write_mark()`**: No docstring
- **Function `apply()`**: Apply pending journal entries to edges.yml.
- **Function `main()`**: No docstring

### `lifecycle_factor_alpha_reeval_t043.py`
**Module Docstring:** scripts/lifecycle_factor_alpha_reeval_t043.py
- **Function `main()`**: No docstring

### `managed_futures_sleeve_phase1_t112.py`
**Module Docstring:** T-112 Phase 1 — managed-futures crisis-diversifier sleeve A/B.
- **Function `crisis_mask()`**: True where index falls inside ANY crisis window.
- **Function `load_base_returns()`**: Load T-092 arm0_off equity curve, return daily returns.
- **Function `load_etf_returns()`**: DBMF / KMLM daily returns from Stooq mirror.
- **Function `load_spot_basket_returns()`**: Reuse T-108's exact harness to compute spot 8-ETF basket daily returns.
- **Function `sharpe_ratio()`**: No docstring
- **Function `max_drawdown_from_returns()`**: Block-bootstrap-friendly MDD: works on a daily-returns array directly.
- **Function `calmar_from_returns()`**: No docstring
- **Function `politis_white_block()`**: No docstring
- **Function `block_bootstrap_ci()`**: No docstring
- **Function `crisis_period_return()`**: No docstring
- **Function `analyze_sleeve()`**: No docstring
- **Function `evaluate_arm()`**: No docstring
- **Function `main()`**: No docstring

### `managed_futures_trend_t108.py`
**Module Docstring:** T-108 Phase 0 — managed-futures / diversified-ETF trend sleeve on
- **Function `load_stooq_etf()`**: No docstring
- **Function `build_data_map()`**: No docstring
- **Function `sharpe_ratio()`**: No docstring
- **Function `sortino_ratio()`**: No docstring
- **Function `max_drawdown()`**: No docstring
- **Function `equity_curve()`**: No docstring
- **Function `politis_white_block()`**: No docstring
- **Function `block_bootstrap_ci()`**: No docstring
- **Function `run_phase0()`**: No docstring
- **Function `main()`**: No docstring

### `merge_stooq_alpaca_substrate.py`
**Module Docstring:** scripts/merge_stooq_alpaca_substrate.py
- **Function `fit_ratio_loglinear()`**: Fit log(alpaca_close / stooq_close) ~ a + b*days_from_epoch on overlap.
- **Function `apply_dividend_strip()`**: Apply ratio(t) = exp(a + b*(t - epoch)) to Stooq's OHLC.
- **Function `apply_constant_rescale()`**: Fallback when overlap is too short: scale by a single constant.
- **Function `merge_ticker()`**: Merge one ticker. Returns provenance record (no IO of the result).
- **Function `main()`**: No docstring

### `metrics_report.py`
**Module Docstring:** scripts/metrics_report.py
- **Function `load_equity_curve()`**: Load equity from a run's portfolio_snapshots.csv (cockpit-fixed schema).
- **Function `compute_metrics_for_run()`**: Apply T-059..T-065 metrics to a single run's equity curve.
- **Function `compute_aggregate()`**: Cross-run summary stats.
- **Function `compute_pbo_across_runs()`**: Run PBO via CSCV using runs as trials, common-bar-count as time.
- **Function `resolve_run_ids()`**: Return list of (run_id, label) tuples per CLI args.
- **Function `render_per_run_table()`**: ASCII table of per-run metrics for terminal output.
- **Function `render_markdown()`**: Generate the audit-doc Markdown.
- **Function `main()`**: No docstring

### `migrate_edge_graveyard_tags.py`
**Module Docstring:** One-time migration: tag failed edges with structured graveyard metadata.
- **Function `migrate()`**: Apply graveyard tags. Returns map of edge_id -> action taken.
- **Function `main()`**: No docstring

### `operational_pattern_audit.py`
**Module Docstring:** scripts/operational_pattern_audit.py
- **Function `audit_edge_population()`**: Edge-curation pattern audit.
- **Function `audit_oos_lock_status()`**: Is the F8 frozen-code OOS window declared and active?
- **Function `audit_discovery_cycle_activity()`**: When did Engine D last promote a candidate?
- **Function `audit_metalearner_status()`**: Is the autonomous portfolio meta-learner enabled in production?
- **Function `audit_recent_param_sweeps()`**: Scan recent measurement docs for parameter-sweep activity.
- **Function `render_markdown_report()`**: No docstring
- **Function `render_summary()`**: One-paragraph stdout summary.
- **Function `main()`**: No docstring

### `optimize.py`
- **Function `main()`**: No docstring

### `path1_revalidation_grid.py`
**Module Docstring:** scripts/path1_revalidation_grid.py
- **Function `run_cell()`**: No docstring
- **Function `main()`**: No docstring

### `path_c_overlays.py`
**Module Docstring:** Path C overlays — standalone risk-overlay helpers for the compounder backtest.
- **Class `VolOverlayDiagnostics`**: Per-rebalance overlay diagnostics — used for clip-frequency analysis.
  - `def clip_state()`: Categorize the overlay action this rebalance.
- **Function `estimate_portfolio_vol()`**: Estimate annualized portfolio volatility from a wide price panel.
- **Function `apply_vol_target()`**: Scale weights to hit `target_vol`, clipped to [clip_low, clip_high].
- **Function `apply_exposure_cap()`**: Hard-cap gross exposure at `cap`.
- **Function `summarize_overlay_diagnostics()`**: Aggregate per-rebalance diagnostics into clip-frequency summary stats.

### `path_c_synthetic_compounder.py`
**Module Docstring:** Path C — compounder sleeve feasibility backtest.
- **Class `RebalanceEvent`**: No docstring
- **Class `BacktestResult`**: No docstring
- **Function `build_universe()`**: S&P 500 current-constituents ∩ ex-financials ∩ SimFin coverage.
- **Function `fetch_prices()`**: Fetch adjusted close prices via yfinance, with parquet caching.
- **Function `compute_composite_score_synthetic()`**: SYNTHETIC (price-derived) composite — preserved as Cell C baseline.
- **Function `apply_defensive_prescreen()`**: Keep the ``top_n`` lowest-trailing-vol names from ``universe`` as-of ``as_of``.
- **Function `compute_composite_score_real()`**: REAL-fundamentals composite — 6 V/Q/A factors via SimFin panel.
- **Function `get_first_trading_day_of_january()`**: Find the first available trading day in January of `year`.
- **Function `run_compounder_backtest()`**: Long-only annual-rebalance equal-weighted top-quintile compounder.
- **Function `run_spy_buy_and_hold()`**: Pure buy-and-hold of SPY. Tax applies only at terminal sale (LT).
- **Function `run_60_40_benchmark()`**: No docstring
- **Function `main()`**: Run the 5-cell harness comparing real-fundamentals vs synthetic vs vol-overlay.

### `per_edge_contribution.py`
**Module Docstring:** Per-edge contribution analysis on the 6 active edges.
- **Function `load_trades()`**: No docstring
- **Function `per_edge_year_stats()`**: Per-edge stats for one year. Returns {edge_id: {pnl, n_trades, ...}}.
- **Function `render_report()`**: No docstring
- **Function `main()`**: No docstring

### `per_edge_per_year_attribution.py`
**Module Docstring:** Phase 2.10c diagnostic: per-edge per-year PnL attribution across the
- **Function `main()`**: No docstring

### `profile_seed_from_foundry.py`
**Module Docstring:** T-2026-05-12-038-CONT profile: identify the hot path inside
- **Function `profile_substrate()`**: No docstring

### `prune_strategies.py`
- **Class `StrategyPruner`**: The 'Reaper' of the Trading Machine.
  - `def __init__()`
  - `def prune()`
  - `def clean_logs()`: Removes old backtest log folders from data/trade_logs.

### `replay_fill_share_cap_2025.py`
**Module Docstring:** scripts/replay_fill_share_cap_2025.py
- **Function `main()`**: No docstring

### `reset_base_edges.py`
**Module Docstring:** scripts/reset_base_edges.py
- **Function `load_edges()`**: No docstring
- **Function `save_edges()`**: No docstring
- **Function `preview()`**: Return edge_ids that would be demoted.
- **Function `demote()`**: Mutate in place: active → candidate. Returns count.
- **Function `main()`**: No docstring

### `retrain_edges.py`
*No public classes or functions found.*

### `revalidate_alphas.py`
**Module Docstring:** Re-validate the two factor-decomp-identified real alphas
- **Function `main()`**: No docstring

### `run.py`
*No public classes or functions found.*

### `run_autonomous_cycle.py`
- **Function `is_market_open()`**: Simple check: Mon-Fri, 9:30 AM - 4:00 PM EST.
- **Function `run_cycle()`**: No docstring

### `run_bab_gauntlet_t123.py`
**Module Docstring:** scripts/run_bab_gauntlet_t123.py
- **Function `main()`**: No docstring

### `run_backtest.py`
**Module Docstring:** scripts/run_backtest.py
- **Function `run_backtest_logic()`**: Backward-compatible programmatic entry point for running a backtest.
- **Function `main()`**: No docstring

### `run_benchmark.py`
**Module Docstring:** Performance Benchmark
- **Function `profit_factor()`**: Gross profit / gross loss.
- **Function `max_consecutive()`**: Longest streak of consecutive winning (or losing) trades.
- **Function `avg_trade_duration()`**: Average holding period in bars (approximate from trade timestamps).
- **Function `per_edge_metrics()`**: Compute per-edge performance from trade log.
- **Function `spy_benchmark()`**: Compute SPY buy-and-hold metrics over the same period.
- **Function `print_scorecard()`**: Print a formatted performance scorecard.
- **Function `run_benchmark()`**: Run benchmark and return full report dict.
- **Function `main()`**: No docstring

### `run_c2_walkforward.py`
**Module Docstring:** scripts/run_c2_walkforward.py
- **Function `find_run_id()`**: No docstring
- **Function `build_filtered_run()`**: Copy the source run's trades + snapshots, filter out test_year rows,
- **Function `retrain_metalearner()`**: Invoke train_metalearner.py on the filtered run. Returns the
- **Function `backtest_year()`**: Backtest single-year window with the currently-loaded metalearner.
- **Function `attach_benchmarks()`**: No docstring
- **Function `main()`**: No docstring

### `run_confidence_gated_ab_t057.py`
**Module Docstring:** scripts/run_confidence_gated_ab_t057.py
- **Function `confidence_gate_patch()`**: Temporarily set the `confidence_gate` block in alpha_settings.prod.json.
- **Function `main()`**: No docstring

### `run_confidence_gated_t057b.py`
**Module Docstring:** scripts/run_confidence_gated_t057b.py
- **Function `confidence_gate_patch()`**: Patch the `confidence_gate` block in alpha_settings.prod.json,
- **Function `main()`**: No docstring

### `run_deterministic.py`
**Module Docstring:** scripts/run_deterministic.py
- **Function `md5()`**: No docstring
- **Function `canonical_md5()`**: MD5 of the CSV with per-run identifier columns (run_id, meta) excluded.
- **Function `save_anchor()`**: No docstring
- **Function `restore_anchor()`**: No docstring
- **Function `run_once()`**: No docstring
- **Function `main()`**: No docstring

### `run_diagnostics.py`
- **Function `run()`**: No docstring
- **Function `check_file()`**: No docstring

### `run_discovery_diagnostic.py`
**Module Docstring:** scripts/run_discovery_diagnostic.py
- **Function `main()`**: No docstring

### `run_discovery_diagnostic_standalone.py`
**Module Docstring:** scripts/run_discovery_diagnostic_standalone.py
- **Function `load_data_map()`**: Load slim ticker set from data/processed/*_1d.csv.
- **Function `emit_timeout()`**: No docstring
- **Function `main()`**: No docstring

### `run_diversified_futures_trend.py`
**Module Docstring:** Run the trend Phase-0 verdict on R2's 8-ETF diversified-futures basket
- **Function `run_sleeve_with_history()`**: Same as scripts.sleeve_phase0_verdict.run_sleeve, but also returns
- **Function `asset_class_contribution()`**: Sum of per-bar weighted returns, grouped by asset class.
- **Function `main()`**: No docstring

### `run_engine_e_hmm_ab.py`
**Module Docstring:** scripts/run_engine_e_hmm_ab.py
- **Function `hmm_patch()`**: Patch config/regime_settings.json's `hmm` block to enable Variant
- **Function `run_smoke()`**: Smoke gate: 2024 Cell A single rep. Kill on zero-trade md5.
- **Function `run_full()`**: Run both cells end-to-end. Smoke gate first by default.
- **Function `main()`**: No docstring

### `run_evaluator.py`
- **Function `main()`**: No docstring

### `run_evolution_cycle.py`
- **Class `AutonomousEvolution`**: The Master Learning Loop.
  - `def __init__()`
  - `def run_cycle()`

### `run_falsifiable_spec.py`
**Module Docstring:** Capture falsifiable-spec results for the gauntlet architectural fix.
- **Function `build_candidate_spec()`**: No docstring
- **Function `load_data_map()`**: No docstring
- **Function `main()`**: No docstring

### `run_healthcheck.py`
**Module Docstring:** Trading Machine - Unified Healthcheck Script
- **Function `run_cmd()`**: Run a shell command, stream output, and return success boolean.
- **Function `run_pytests()`**: Run only the high‑signal tests that verify portfolio math + controller logic.
- **Function `run_dev_backtest()`**: Run the small/fast dev backtest. User may later customize flags.
- **Function `run_invariants()`**: Perform core snapshot/trade invariants.
- **Function `main()`**: No docstring

### `run_isolated.py`
**Module Docstring:** scripts/run_isolated.py
- **Function `reset_module_globals()`**: Reset all registered cross-run-contaminating module globals.
- **Function `save_anchor()`**: Snapshot `data/governor/<file>` for every name in ISOLATED_FILES.
- **Function `restore_anchor()`**: Restore the full set of governor files from the anchor.
- **Function `isolated()`**: Context manager: restore anchor on entry, restore again on exit.
- **Function `main()`**: No docstring

### `run_live.py`
*No public classes or functions found.*

### `run_multi_year.py`
**Module Docstring:** scripts/run_multi_year.py
- **Function `main()`**: No docstring

### `run_oos_validation.py`
**Module Docstring:** scripts/run_oos_validation.py
- **Function `sample_universe_b()`**: Mirror engines/engine_d_discovery/discovery.py::_load_universe_b
- **Function `find_run_id()`**: No docstring
- **Function `run_q1()`**: 2025 OOS on prod universe. Same costs, shifted window, reset governor.
- **Function `run_q2()`**: Universe-B (50 held-out tickers, seed=42) on same in-sample window.
- **Function `run_q3()`**: 2021-2024 IS on prod universe with production-equivalent ensemble.
- **Function `attach_benchmarks()`**: Add SPY / QQQ / 60-40 metrics over the same window.
- **Function `main()`**: No docstring

### `run_paper_loop.py`
- **Function `main()`**: No docstring

### `run_path2_revalidation.py`
**Module Docstring:** scripts/run_path2_revalidation.py
- **Function `write_config()`**: Edit alpha_settings.prod.json in place: set metalearner.enabled
- **Function `find_run_id()`**: No docstring
- **Function `trades_canon_md5()`**: No docstring
- **Function `attach_benchmarks()`**: No docstring
- **Function `run_q2_under_harness()`**: Single Universe-B (q2) backtest under isolated() context.
- **Function `run_single_year_under_harness()`**: Single-year prod-109 backtest under isolated() context.
- **Function `cell_runs()`**: No docstring
- **Function `task_c1()`**: No docstring
- **Function `build_filtered_run()`**: No docstring
- **Function `retrain_metalearner_on_fold()`**: No docstring
- **Function `task_c2()`**: No docstring
- **Function `main()`**: No docstring

### `run_path2_ub.py`
**Module Docstring:** Path-2 Universe-B driver — runs Q2 with optional metalearner override.
- **Function `sample_universe_b()`**: No docstring
- **Function `find_run_id()`**: No docstring
- **Function `run_q2_with_metalearner()`**: No docstring
- **Function `attach_benchmarks()`**: No docstring
- **Function `main()`**: No docstring

### `run_per_edge_isolation.py`
**Module Docstring:** scripts/run_per_edge_isolation.py
- **Function `main()`**: No docstring

### `run_per_ticker_oos.py`
**Module Docstring:** scripts/run_per_ticker_oos.py
- **Function `main()`**: No docstring

### `run_shadow_paper.py`
- **Function `load_candidates()`**: Load 'Candidate' edges from the registry.
- **Function `run_shadow_session()`**: No docstring

### `run_short_term_reversal_3rep.py`
**Module Docstring:** scripts/run_short_term_reversal_3rep.py
- **Function `main()`**: No docstring

### `run_spinoff_gauntlet_t041b.py`
**Module Docstring:** scripts/run_spinoff_gauntlet_t041b.py
- **Function `main()`**: No docstring

### `run_str_3rep_t036.py`
**Module Docstring:** scripts/run_str_3rep_t036.py
- **Function `main()`**: No docstring

### `run_substrate_arms.py`
**Module Docstring:** scripts/run_substrate_arms.py
- **Function `hmm_patch()`**: Patch config/regime_settings.json to enable HMM Variant C, restore on exit.
- **Function `run_smoke()`**: Run 2021 Arm 1 single rep and check zero-trade kill condition.
- **Function `run_full()`**: Run both arms end-to-end. Optionally do smoke gate first.
- **Function `main()`**: No docstring

### `run_trend_wider_universe.py`
**Module Docstring:** Run the trend Phase-0 verdict on the wider universe (all 722 tickers
- **Function `main()`**: No docstring

### `run_vol_target_arms_ewma_t055d.py`
**Module Docstring:** scripts/run_vol_target_arms_ewma_t055d.py
- **Function `vol_target_ewma_patch()`**: No docstring
- **Function `main()`**: No docstring

### `run_vol_target_arms_full.py`
**Module Docstring:** scripts/run_vol_target_arms_full.py
- **Function `vol_target_patch()`**: Patch risk_settings.json to enable/disable vol-targeting, restore on exit.
- **Function `run_full()`**: No docstring
- **Function `main()`**: No docstring

### `run_vol_target_arms_multiplier_sweep_t055g.py`
**Module Docstring:** scripts/run_vol_target_arms_multiplier_sweep_t055g.py
- **Function `vol_target_arm_patch()`**: Patch config/risk_settings.prod.json with the arm's multiplier
- **Function `main()`**: No docstring

### `run_vol_target_arms_regime_t055e.py`
**Module Docstring:** scripts/run_vol_target_arms_regime_t055e.py
- **Function `vol_target_regime_patch()`**: No docstring
- **Function `main()`**: No docstring

### `run_vrp_gauntlet_t122.py`
**Module Docstring:** scripts/run_vrp_gauntlet_t122.py
- **Function `main()`**: No docstring

### `sleeve_phase0_verdict.py`
**Module Docstring:** Sleeve Phase-0 verdict harness — drives a Sleeve through a measurement-
- **Function `run_sleeve()`**: Run the sleeve through a sequence of rebalance dates. Returns
- **Function `run_trend_verdict()`**: No docstring
- **Function `run_moonshot_verdict()`**: No docstring
- **Function `main()`**: No docstring

### `smoke_per_ticker_logger.py`
**Module Docstring:** scripts/smoke_per_ticker_logger.py
- **Function `main()`**: No docstring

### `spot_basket_extended_sweep_t115.py`
**Module Docstring:** T-115 — extend the T-112 spot-basket sweep to {25%, 30%} on the deep
- **Function `main()`**: No docstring

### `spot_sleeve_cloud_ab_spec_t121.py`
**Module Docstring:** T-121 cloud A/B spec for the spot sleeve integration — full 16/26-yr.
- **Function `write_spec_json()`**: No docstring
- **Function `verify_locally()`**: Pre-flight check: confirm both arms produce different canon md5s
- **Function `launch_to_cloud()`**: NOT IMPLEMENTED in this branch — cloud submit holds for T-109 image.
- **Function `main()`**: No docstring

### `start_stack.py`
- **Function `run_background()`**: No docstring
- **Function `main()`**: No docstring

### `submit_arms_campaign.py`
**Module Docstring:** scripts/submit_arms_campaign.py
- **Class `Cell`**: No docstring
  - `def cell_id()`
  - `def s3_prefix()`
  - `def year_int_for_legacy()`: Return integer year iff the window is a single calendar year
  - `def submit()`: Submit one Batch job for this cell. Returns the AWS job ID.
- **Function `aws()`**: Run an AWS CLI command via the `archondex` profile + `us-east-1`.
- **Function `load_spec()`**: Load + validate the campaign spec JSON.
- **Function `build_cells()`**: Build the list of cells from spec. Desugars `years` to single-year
- **Function `submit_all()`**: Submit cells in parallel (Batch handles N concurrent submits fine).
- **Function `poll_until_terminal()`**: Poll Batch describe-jobs until all cells reach SUCCEEDED or FAILED.
- **Function `fetch_manifests()`**: Pull per-cell manifest.json from S3 for cells that SUCCEEDED.
- **Function `write_summary()`**: No docstring
- **Function `main()`**: No docstring

### `submit_substrate_run.py`
**Module Docstring:** scripts/submit_substrate_run.py
- **Class `Cell`**: No docstring
- **Function `aws()`**: Run an AWS CLI command via the `archondex` profile in `us-east-1`.
- **Function `submit()`**: Submit one Batch job for this cell.
- **Function `poll_once()`**: Update status on every non-terminal cell with one describe-jobs call.
- **Function `fetch_manifest()`**: Pull the entrypoint-written manifest from S3 to populate canon_md5 etc.
- **Function `main()`**: No docstring

### `substrate_arms_analytics.py`
**Module Docstring:** scripts/substrate_arms_analytics.py
- **Function `load_records()`**: No docstring
- **Function `daily_returns_for_run()`**: No docstring
- **Function `concat_arm_returns()`**: Concatenate daily returns from rep 1 of each year for an arm.
- **Function `per_arm_headline()`**: No docstring
- **Function `bootstrap_arm()`**: No docstring
- **Function `per_edge_attribution()`**: Per-arm per-edge realized PnL aggregated across years (rep 1 only,
- **Function `correlation_matrix()`**: Daily-PnL Pearson correlation matrix using rep-1 of each year, concatenated.
- **Function `verdict_bucket()`**: Apply spec verdict framing to (Arm 1, Arm 2) headline Sharpes.
- **Function `render_markdown()`**: No docstring
- **Function `build()`**: No docstring
- **Function `main()`**: No docstring

### `sweep_cap_recalibration.py`
**Module Docstring:** scripts/sweep_cap_recalibration.py
- **Function `snapshot_lifecycle_state()`**: Copy lifecycle/governor files into _cap_recal_anchor/. Idempotent.
- **Function `restore_lifecycle_state()`**: Restore lifecycle/governor files from _cap_recal_anchor/.
- **Function `patched_configs()`**: Patch alpha_settings.prod.json + regime_settings.json with the
- **Function `find_run_id()`**: No docstring
- **Function `run_one()`**: Run a single 2025 Q1 OOS under the given preset.
- **Function `main()`**: No docstring

### `sync_docs.py`
- **Function `parse_file()`**: No docstring
- **Function `sync_directory()`**: No docstring

### `system_validity_check.py`
- **Function `run_system_check()`**: No docstring

### `t139_fixture_data.py`
**Module Docstring:** Frozen T-139 fixture — REAL closes from data/processed/<T>_1d.csv,

### `train_gate.py`
- **Function `train_gate_model()`**: Train the SignalGate model using harvested data.

### `train_hmm_crisis_t103.py`
**Module Docstring:** T-103 — Retrain Engine E's HMM on a crisis-inclusive span.
- **Function `load_fred()`**: No docstring
- **Function `build_crisis_panel()`**: Build the 7-feature HMM panel from Stooq SPY/TLT + FRED.
- **Function `main()`**: No docstring

### `train_hmm_regime.py`
**Module Docstring:** scripts/train_hmm_regime.py
- **Function `main()`**: No docstring

### `train_hmm_vix_term.py`
**Module Docstring:** train_hmm_vix_term — train a 3-state HMM on the rebuilt feature panel
- **Function `main()`**: No docstring

### `train_metalearner.py`
**Module Docstring:** scripts/train_metalearner.py
- **Function `find_latest_run()`**: Locate the run directory whose trades.csv + portfolio_snapshots.csv
- **Function `load_per_edge_daily_raw_scores()`**: Build a (date × edge) matrix of MEAN RAW SCORES from the trade
- **Function `load_per_edge_daily_pnl()`**: Aggregate trade-level fills into a (date × edge) daily PnL matrix.
- **Function `load_portfolio_returns()`**: Daily portfolio return series from portfolio_snapshots.csv.
- **Function `build_features_from_raw_scores()`**: Build per-bar features from a (date × edge) raw-score matrix.
- **Function `build_features()`**: Build a (date × feature) DataFrame from per-edge daily PnL.
- **Function `build_profile_aware_target()`**: Build the training target: profile-aware fitness over the next
- **Function `walk_forward_train()`**: Train the meta-learner via walk-forward folds and report per-fold
- **Function `write_validation_report()`**: No docstring
- **Function `main()`**: No docstring

### `train_minimal_hmm.py`
**Module Docstring:** train_minimal_hmm — train a 3-state HMM on the leading-feature subset.
- **Function `train_one()`**: No docstring
- **Function `main()`**: No docstring

### `train_multires_hmm.py`
**Module Docstring:** scripts/train_multires_hmm.py
- **Function `main()`**: No docstring

### `train_per_ticker_metalearner.py`
**Module Docstring:** scripts/train_per_ticker_metalearner.py
- **Function `find_latest_per_ticker_parquet()`**: No docstring
- **Function `load_per_ticker_scores()`**: No docstring
- **Function `assert_no_leakage()`**: Refuse to train if the corpus contains any rows >= cutoff. Returns
- **Function `per_ticker_features()`**: Pivot per-ticker rows to (date × edge_id) of raw_score.
- **Function `per_ticker_forward_return()`**: Forward H-day return on the ticker's CLOSE series.
- **Function `walk_forward_train_ticker()`**: Walk-forward training for ONE ticker.
- **Function `main()`**: No docstring

### `train_signal_gate.py`
- **Function `train_gate()`**: No docstring

### `update_data.py`
- **Function `update_all_data()`**: Programmatic entry point for data updating.
- **Function `main()`**: No docstring

### `validate_active_edges.py`
- **Function `main()`**: No docstring

### `validate_complementary_discovery.py`
- **Function `validate_discovery_vocabulary()`**: No docstring

### `validate_hmm_crisis_t103.py`
**Module Docstring:** T-103 — Validate the crisis-trained HMM on HELD-OUT crisis events.
- **Function `compute_causal_posteriors()`**: For each t, run predict_proba on Z[max(0,t-window+1):t+1] and
- **Function `forward_drawdown()`**: No docstring
- **Function `auc_score()`**: No docstring
- **Function `auc_block_bootstrap_ci()`**: No docstring
- **Function `per_event_fire()`**: No docstring
- **Function `main()`**: No docstring

### `validate_hmm_window_t105.py`
**Module Docstring:** T-105 — Re-validate T-103's crisis-HMM at the LIVE 60-bar inference window
- **Function `compute_causal_posteriors()`**: For each t, run predict_proba on the trailing `window` bars
- **Function `forward_drawdown()`**: No docstring
- **Function `auc_score()`**: No docstring
- **Function `auc_block_bootstrap_ci()`**: No docstring
- **Function `per_event_fire()`**: No docstring
- **Function `run_length_stats()`**: Median + p90 run-length above `threshold`, plus days-above-trigger
- **Function `main()`**: No docstring

### `validate_lifecycle_triggers.py`
**Module Docstring:** Phase 2.10d Task A validation driver.
- **Function `main()`**: No docstring

### `validate_minimal_hmm.py`
**Module Docstring:** validate_minimal_hmm — read-only validation of E-rebuild phase-1 variants.
- **Function `auc_score()`**: No docstring
- **Function `forward_drawdown()`**: No docstring
- **Function `forward_return()`**: No docstring
- **Function `trailing_return()`**: No docstring
- **Function `load_spy()`**: No docstring
- **Function `load_states()`**: No docstring
- **Function `per_state_dd_breakdown()`**: No docstring
- **Function `evaluate_variant()`**: No docstring
- **Function `main()`**: No docstring

### `validate_phase2_math.py`
- **Function `test_phase2_math()`**: No docstring

### `validate_regime_signals.py`
**Module Docstring:** validate_regime_signals — read-only validation of HMM + WS-C signals.
- **Function `load_spy()`**: No docstring
- **Function `load_fred()`**: No docstring
- **Function `compute_hyg_lqd_z()`**: 60-business-day z-score of (BAMLH0A0HYM2 - BAMLC0A0CM).
- **Function `compute_dxy_change_20d()`**: No docstring
- **Function `compute_vvix_proxy()`**: No docstring
- **Function `forward_drawdown()`**: For each t, the worst forward drawdown over (t, t+horizon].
- **Function `forward_return()`**: Forward arithmetic return over `horizon` bars.
- **Function `auc_score()`**: ROC AUC from scratch (avoids sklearn dependency).
- **Function `hit_rate_and_fpr()`**: Hit rate (TPR) and false-positive rate.
- **Function `cond_mean_dd()`**: Mean forward drawdown conditional on a boolean mask.
- **Function `lead_time_stats()`**: For each forward window with drawdown ≤ threshold, find the lead
- **Function `main()`**: No docstring

### `validate_regime_signals_cheap.py`
**Module Docstring:** validate_regime_signals_cheap — feature-level cheap-input validation.
- **Function `load_spy()`**: No docstring
- **Function `load_macro_series()`**: No docstring
- **Function `forward_drawdown()`**: No docstring
- **Function `forward_return()`**: No docstring
- **Function `auc_score()`**: No docstring
- **Function `build_vix_term_features()`**: Compute VIX term-structure slopes on the daily index.
- **Function `build_pc_ratio_features()`**: Attempt to load CBOE total P/C ratio from data/macro/cboe_pc_ratio.parquet.
- **Function `conditional_top_decile()`**: No docstring
- **Function `coincident_leading_test()`**: No docstring
- **Function `main()`**: No docstring

### `validate_regime_signals_t087.py`
**Module Docstring:** T-087 — Engine E regime re-diagnosis on 12-yr extended substrate.
- **Function `load_spy_extended()`**: Load SPY close from Stooq (covers 2005+). Returns tz-naive daily series.
- **Function `load_tlt_extended()`**: Load TLT close from Stooq (covers 2005+). Returns tz-naive daily series.
- **Function `load_fred()`**: No docstring
- **Function `compute_vvix_proxy()`**: 30d rolling annualized std of log(VIX) — same as production script.
- **Function `vvix_z_score()`**: Trailing z-score of VVIX-proxy over `window` business days.
- **Function `build_extended_panel()`**: Build the HMM feature panel using extended-substrate SPY.
- **Function `forward_drawdown()`**: No docstring
- **Function `auc_score()`**: No docstring
- **Function `auc_block_bootstrap_ci()`**: Block-bootstrap CI for AUC. Block respects serial correlation
- **Function `lead_vs_lag_corr()`**: For each lag k:
- **Function `per_event_tpr()`**: Did `signal >= threshold` fire at any point in (trough - lookback, trough]?
- **Function `main()`**: No docstring

### `validate_regime_signals_vix_term.py`
**Module Docstring:** validate_regime_signals_vix_term — slice-1 panel-rebuild validation.
- **Function `load_spy()`**: No docstring
- **Function `load_fred()`**: No docstring
- **Function `forward_drawdown()`**: No docstring
- **Function `forward_return()`**: No docstring
- **Function `auc_score()`**: No docstring
- **Function `hit_rate_and_fpr()`**: No docstring
- **Function `cond_mean_dd()`**: No docstring
- **Function `lead_time_stats()`**: No docstring
- **Function `main()`**: No docstring

### `verify_gate1_cache_determinism.py`
**Module Docstring:** scripts/verify_gate1_cache_determinism.py
- **Function `load_data_map()`**: No docstring
- **Function `build_candidate_spec()`**: No docstring
- **Function `main()`**: No docstring

### `walk_forward_affinity.py`
**Module Docstring:** scripts/walk_forward_affinity.py
- **Function `backup()`**: No docstring
- **Function `restore()`**: No docstring
- **Function `write_gov_config()`**: No docstring
- **Function `latest_run_summary()`**: No docstring
- **Function `phase_train()`**: No docstring
- **Function `phase_eval()`**: No docstring
- **Function `main()`**: No docstring

### `walk_forward_factor_edge.py`
**Module Docstring:** scripts/walk_forward_factor_edge.py
- **Function `backup()`**: No docstring
- **Function `restore()`**: No docstring
- **Function `set_edge_weight()`**: No docstring
- **Function `latest_run_summary()`**: No docstring
- **Function `run_eval()`**: No docstring
- **Function `main()`**: No docstring

### `walk_forward_phase210.py`
**Module Docstring:** scripts/walk_forward_phase210.py
- **Function `main()`**: No docstring

### `walk_forward_regime.py`
**Module Docstring:** scripts/walk_forward_regime.py
- **Function `backup()`**: No docstring
- **Function `restore()`**: No docstring
- **Function `write_gov_config()`**: Write governor_settings.json with overrides.
- **Function `latest_run_summary()`**: Read performance_summary.json from the most-recently-modified run dir.
- **Function `phase_train()`**: Phase 1: clean slate, run 2021-2022 with governor on → save OOS-anchor.
- **Function `phase_eval()`**: Phase 2/3: restore OOS anchor, run 2023-2024 --no-governor with given policy.
- **Function `main()`**: No docstring

### `walk_forward_risk_advisory.py`
**Module Docstring:** scripts/walk_forward_risk_advisory.py
- **Function `backup()`**: No docstring
- **Function `restore()`**: No docstring
- **Function `write_cfg()`**: No docstring
- **Function `latest_run_summary()`**: No docstring
- **Function `phase_train()`**: No docstring
- **Function `phase_eval()`**: No docstring
- **Function `main()`**: No docstring

### `wash_sale_multi_year.py`
**Module Docstring:** scripts/wash_sale_multi_year.py
- **Function `main()`**: No docstring

### `watch_coordination.py`
**Module Docstring:** Coordination outbox watcher — notify the director when any agent finishes.
- **Function `main()`**: No docstring
