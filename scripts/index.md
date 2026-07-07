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

### `_xlsx_min.py`
**Module Docstring:** scripts/_xlsx_min.py — minimal stdlib .xlsx reader (T-136).
- **Function `read_xlsx_first_sheet()`**: No docstring
- **Function `excel_serial_to_datetime()`**: No docstring

### `accumulation_model_t283.py`
**Module Docstring:** scripts/accumulation_model_t283.py
- **Function `spy_buyhold()`**: No docstring
- **Function `sleeve()`**: No docstring
- **Function `robo()`**: No docstring
- **Function `accumulate()`**: DCA: contribute `contrib` each Jan (first trading day of the year); compound
- **Function `main()`**: No docstring

### `accumulation_model_t283b.py`
**Module Docstring:** scripts/accumulation_model_t283b.py
- **Function `gated_2x_spy()`**: (e) 100% SPY, 2× when the ensemble trend is on, cash (short rate) when off.
- **Function `gated_2x_sleeve()`**: (f) T-282 3-asset arm: SPY leg 2×-when-on (SPY+SSO blend), BOND/GOLD 1×.
- **Function `main()`**: No docstring

### `accumulation_model_t283c.py`
**Module Docstring:** scripts/accumulation_model_t283c.py
- **Function `main()`**: No docstring

### `analyze_13f_crowding_t145.py`
**Module Docstring:** scripts/analyze_13f_crowding_t145.py
- **Function `load_prices()`**: No docstring
- **Function `build_strategy()`**: Quarterly-rebalanced low-minus-high-crowding long-short.
- **Function `factor_report()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_8k_events_t137.py`
**Module Docstring:** scripts/analyze_8k_events_t137.py
- **Function `build_close_returns()`**: No docstring
- **Function `anchor_events()`**: Map acceptance datetime (UTC) -> anchor trading-day close index pos.
- **Function `calendar_time_series()`**: Daily mean abnormal return over events within (anchor, anchor+horizon].
- **Function `factor_gate()`**: No docstring
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

### `analyze_engine_e_hmm_ab.py`
**Module Docstring:** scripts/analyze_engine_e_hmm_ab.py
- **Function `main()`**: No docstring

### `analyze_form4_clusters_t144.py`
**Module Docstring:** scripts/analyze_form4_clusters_t144.py
- **Function `load_buys()`**: No docstring
- **Function `cluster_events()`**: Cluster-buy events: >=k distinct insiders, >=MIN_VALUE total, within a
- **Function `anchor()`**: No docstring
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

### `analyze_t118r.py`
**Module Docstring:** scripts/analyze_t118r.py
- **Function `analyze_cell()`**: No docstring
- **Function `main()`**: No docstring

### `analyze_vrp_factor_t122.py`
**Module Docstring:** scripts/analyze_vrp_factor_t122.py
- **Function `build_market_return()`**: Equal-weight daily return of the processed universe — the market proxy
- **Function `vrp_signal_series()`**: Daily VRP scale ∈[0,1] using the SAME VIX−RV formula as the edge
- **Function `vrp_return_stream()`**: Vol-managed market return: scale_{t-1} * market_return_t, minus cost on
- **Function `factor_report()`**: No docstring
- **Function `book_correlation()`**: Correlation of VRP return to the existing 6-active-edge book + to the
- **Function `main()`**: No docstring

### `archive_altdata_t136.py`
**Module Docstring:** scripts/archive_altdata_t136.py
- **Function `pull_gpr()`**: No docstring
- **Function `pull_epu()`**: No docstring
- **Function `pull_gdelt_timelines()`**: No docstring
- **Function `snapshot_polymarket()`**: No docstring
- **Function `snapshot_kalshi()`**: No docstring
- **Function `snapshot_kxfed()`**: Daily snapshot of the FULL KXFED (Fed funds rate) bucket distribution —
- **Function `pull_fred_rate_path()`**: The FRED resolution series (DFEDTARL/U + EFFR) — what the KXFED markets
- **Function `main()`**: No docstring

### `archive_positioning_t136.py`
**Module Docstring:** scripts/archive_positioning_t136.py
- **Function `pull_regsho_short_volume()`**: No docstring
- **Function `pull_sec_ftd()`**: No docstring
- **Function `pull_naaim()`**: No docstring
- **Function `pull_finra_margin()`**: No docstring
- **Function `pull_finra_short_interest()`**: No docstring
- **Function `main()`**: No docstring

### `assess_vol_collapse_t153.py`
**Module Docstring:** scripts/assess_vol_collapse_t153.py
- **Function `portfolio_sweep()`**: No docstring
- **Function `per_name_sweep()`**: No docstring
- **Function `main()`**: No docstring

### `asymmetric_exits_gauntlet_t269.py`
**Module Docstring:** scripts/asymmetric_exits_gauntlet_t269.py
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

### `barbell_gauntlet_t251.py`
**Module Docstring:** T-251 barbell gauntlet — inverse-vol SAFE CORE + convex trend SATELLITE vs both robos.
- **Function `load_close()`**: No docstring
- **Function `net_asset_rets()`**: Per-asset daily returns net of expense ratio.
- **Function `robo()`**: No docstring
- **Function `satellite_with_cost()`**: Trend overlay sleeve net of turnover trading cost (the active leg).
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `metric_ci()`**: No docstring
- **Function `updown()`**: No docstring
- **Function `main()`**: No docstring

### `breadth_tilt_t273.py`
**Module Docstring:** T-273 — market-breadth sizing tilt on the SPY leg of the multi-speed ensemble sleeve (fair T-255 harness).
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `build_breadth()`**: No docstring
- **Function `sleeve_tilted()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `ddwin()`**: No docstring
- **Function `cagrwin()`**: No docstring
- **Function `paired()`**: No docstring

### `btc_arm_t272.py`
**Module Docstring:** T-272 — the BTC 4th-asset ARM (completeness-critic hole #8; the last uncovered asset).
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `btc_close()`**: No docstring
- **Function `dgs3_cash()`**: No docstring
- **Function `multi_expo()`**: No docstring
- **Function `sleeve()`**: weighted multi-speed long/flat sleeve; flat earns cash; ER when exposed; txn on Δexpo.
- **Function `stats()`**: No docstring
- **Function `ddwin()`**: No docstring
- **Function `paired()`**: No docstring
- **Function `main()`**: No docstring

### `build_13f_panel_t145.py`
**Module Docstring:** scripts/build_13f_panel_t145.py
- **Function `zip_urls()`**: No docstring
- **Function `cusip_lookup()`**: No docstring
- **Function `process_quarter()`**: No docstring
- **Function `main()`**: No docstring

### `build_fair_inputs_t255.py`
**Module Docstring:** T-2026-07-02-255: build the T-236 gauntlet inputs as COMMITTED, reproducible artifacts
- **Function `build_bond_synth()`**: No docstring
- **Function `build_gold()`**: No docstring

### `build_market_cap_tiers_t210.py`
**Module Docstring:** T-2026-06-18-210 — build the market-cap snapshot join for the realistic-retail
- **Function `main()`**: No docstring

### `build_membership_panel_t136.py`
**Module Docstring:** scripts/build_membership_panel_t136.py
- **Function `build_intervals()`**: No docstring
- **Function `internal_consistency_check()`**: Cross-check the intervals against the repo's own date-stamped
- **Function `wikipedia_cross_check()`**: Second source: Wikipedia current constituents vs the panel TODAY.
- **Function `main()`**: No docstring

### `build_news_panel_t289.py`
**Module Docstring:** T-289b — resumable PIT news-panel backfill. Writes data/intel/news_panel/news_YYYYMM.parquet per month,
- **Function `full_universe()`**: No docstring
- **Function `months()`**: No docstring
- **Function `run_month()`**: No docstring

### `build_ohlc_features_t150.py`
**Module Docstring:** scripts/build_ohlc_features_t150.py
- **Function `load_ohlc_features()`**: Loader for the Part-A feature panel (long format).
- **Function `main()`**: No docstring

### `build_pit_cap_history_t219.py`
**Module Docstring:** T-2026-06-18-219 — close the T-210/T-215 cap-join under-count: give the DELISTED
- **Function `main()`**: No docstring

### `build_rate_path_history_t295.py`
**Module Docstring:** scripts/build_rate_path_history_t295.py
- **Function `build_frontcont_path()`**: ZQ=F front-continuous → implied_effr = 100 − price. Validated vs FRED
- **Function `build_meeting_probs()`**: For every FOMC meeting with an available Yahoo contract (active window
- **Function `ingest_minneapolis()`**: Minneapolis Fed Market-Based Probabilities (option-implied MPDs). The
- **Function `ingest_atlanta()`**: Atlanta Fed Market Probability Tracker — BEST-EFFORT (the task: if the
- **Function `main()`**: No docstring

### `c1_concentration_gauntlet_t241.py`
**Module Docstring:** T-241 C1 concentration gauntlet — base vs C1 vs robos on a cached-equity window.
- **Function `load_close()`**: No docstring
- **Function `etf_rets()`**: No docstring
- **Function `robo_returns()`**: No docstring
- **Function `equity_returns()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `updown()`**: No docstring
- **Function `mskew()`**: No docstring
- **Function `main()`**: No docstring

### `calendar_flow_probe_t250.py`
**Module Docstring:** T-250 calendar/flow probe: FOMC even-week + turn-of-month on SPY. Pre-registered, no sweep.
- **Function `even_week()`**: No docstring
- **Function `measure()`**: No docstring
- **Function `tilt()`**: No docstring

### `calibrate_divergence_monitors_t152.py`
**Module Docstring:** T-152 calibration — false-alarm grid + injected-divergence power.
- **Function `main()`**: No docstring

### `capital_tier_gauntlet_t278.py`
**Module Docstring:** scripts/capital_tier_gauntlet_t278.py
- **Function `main()`**: No docstring

### `carry_sleeve_gauntlet_t247.py`
**Module Docstring:** scripts/carry_sleeve_gauntlet_t247.py
- **Function `macro_series()`**: No docstring
- **Function `etf_close()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `sharpe_ci()`**: No docstring
- **Function `updown()`**: No docstring
- **Function `crisis_dd()`**: No docstring
- **Function `beta_or_edge()`**: PRIME KILL-TEST: regress the sleeve on FF5+Mom + a bond-DURATION factor.
- **Function `report()`**: No docstring
- **Function `main()`**: No docstring

### `cef_data_probe_t264.py`
**Module Docstring:** T-264 CEF-discount data-feasibility probe (reproduces the audit's load-bearing checks).
- **Function `main()`**: No docstring

### `cef_lowerbound_probe_t267.py`
**Module Docstring:** T-267 — CEF discount-capture SURVIVOR-ONLY LOWER-BOUND probe (pre-registered, N_trials+=1).
- **Function `tr_close()`**: No docstring
- **Function `dgs3_cash()`**: No docstring
- **Function `build_panel()`**: price(raw), tr(adj close), nav per CEF → cached. discount = raw price / nav - 1.
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `paired_dci()`**: No docstring
- **Function `newey_west_t()`**: No docstring
- **Function `monthly()`**: No docstring
- **Function `main()`**: No docstring

### `ci_coverage_audit_t257.py`
**Module Docstring:** scripts/ci_coverage_audit_t257.py
- **Function `simulate_garch_t()`**: GARCH(1,1) with standardized Student-t innovations.
- **Function `main()`**: No docstring

### `cloud_pipeline_smoke.py`
**Module Docstring:** scripts/cloud_pipeline_smoke.py — MANDATORY both-paths pre-flight before any
- **Class `SmokeCell`**: No docstring
  - `def cell_id()`
  - `def submit()`
- **Function `aws()`**: No docstring
- **Function `build_cells()`**: No docstring
- **Function `poll()`**: No docstring
- **Function `check_uploads()`**: No docstring
- **Function `main()`**: No docstring

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

### `compose_voltarget_t262.py`
**Module Docstring:** scripts/compose_voltarget_t262.py
- **Function `sleeve_fair()`**: D's fair sleeve; when voltarget=True, the SPY leg's long exposure is
- **Function `main()`**: No docstring

### `conditional_voltarget_gauntlet_t252.py`
**Module Docstring:** scripts/conditional_voltarget_gauntlet_t252.py
- **Function `main()`**: No docstring

### `crisis_replay_t118b.py`
**Module Docstring:** T-143 — Crisis-replay harness implementing the LOCKED T-118b
- **Class `Episode`**: No docstring
- **Class `EpisodeResult`**: No docstring
- **Class `Criterion`**: No docstring
- **Class `CrisisReplayResult`**: No docstring
  - `def verdict_line()`
- **Function `derive_episodes_mechanical()`**: Mechanically derive ≥threshold peak-to-trough drawdown episodes.
- **Function `pin_locked_episodes()`**: Pin the LOCKED episode set's exact trading dates from the TR
- **Function `check_mechanical_derivation()`**: The honest-derivation check the T-143 brief requires: does the
- **Function `evaluate_crisis_replay()`**: Run the locked T-118b evaluation on one config's artifact pair.
- **Function `format_report()`**: No docstring
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

### `defensive_tilt_screens_t205.py`
**Module Docstring:** T-205 standalone validation harness for the defensive-tilt signals.
- **Function `main()`**: No docstring

### `demo_after_tax_t141.py`
**Module Docstring:** T-141 demonstration — pre-tax vs after-tax (taxable-IL) on a real book.
- **Function `main()`**: No docstring

### `demo_auction_execution_t146.py`
**Module Docstring:** T-146 demonstration — what auction execution is WORTH at our turnover.
- **Function `main()`**: No docstring

### `demo_dynamic_optimization_t139.py`
**Module Docstring:** T-139 payoff demonstration — frozen-fixture comparison, NOT a backtest.
- **Function `build_fixture()`**: No docstring
- **Function `annualized_te()`**: No docstring
- **Function `main()`**: No docstring

### `demo_position_buffering_t148.py`
**Module Docstring:** T-148 demonstration — what buffering is worth, COUPLED through costs
- **Function `main()`**: No docstring

### `demo_safef_car25_t151.py`
**Module Docstring:** T-151 demonstration — safe-f / CAR25 on a real book, per account.
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

### `dividend_reconcile_t287.py`
**Module Docstring:** scripts/dividend_reconcile_t287.py
- **Function `robo_clean()`**: 60/40-style robo, NO dividend double-count — processed SPY is already TR.
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
- **Function `check_no_numbered_nonneg_refs()`**: No docstring
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

### `event_interaction_t291.py`
**Module Docstring:** T-291 Deliverable 2 — even_week x is_fomc_week interaction (frozen pre-reg, N_trials+=1).
- **Function `spy_returns()`**: No docstring
- **Function `even_week()`**: No docstring
- **Function `is_fomc_week()`**: dt is in the same ISO calendar week as an FOMC decision (cycle week 0).
- **Function `block_ci()`**: 95% CI of (mean(a) - mean(b)) via independent block bootstrap of each group.
- **Function `run()`**: No docstring
- **Function `main()`**: No docstring

### `evenweek_sleeve_t268.py`
**Module Docstring:** T-268 — FOMC even-week tilt on the SPY leg of the multi-speed ensemble sleeve (fair T-255 harness).
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `even_week()`**: No docstring
- **Function `sleeve_tilted()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `ddwin()`**: No docstring
- **Function `cagrwin()`**: No docstring
- **Function `paired()`**: No docstring

### `factor_decomp_book_t206.py`
**Module Docstring:** T-206 Task 1 diagnostic — book-level factor decomposition (HAC).
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

### `factor_momentum_t254.py`
**Module Docstring:** T-254 factor momentum (Ehsani-Linnainmaa): do factors' own returns predict their next? Pre-registered.
- **Function `parse_ff()`**: Ken French daily CSV: skip metadata, read the YYYYMMDD data block.
- **Function `stats()`**: No docstring
- **Function `hac_alpha()`**: No docstring

### `fair_t236_rerun_t255.py`
**Module Docstring:** T-255 FAIR T-236 re-run — corrects the biases the 2026-07-02 gap audit verified (all AGAINST the sleeve):
- **Function `spy_close()`**: No docstring
- **Function `csv_ser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `sleeve_returns_fair()`**: EW SPY/BOND/GOLD long-flat; FLAT leg earns the short rate; ER when long; txn cost on flips.
- **Function `robo_fair()`**: monthly-rebal; ETF legs net of ER; _cash earns cash_rate (a daily Series); 1.5bps rebal cost.
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `so()`**: No docstring
- **Function `so_ci()`**: No docstring
- **Function `paired()`**: No docstring

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

### `fetch_8k_edgar_t137.py`
**Module Docstring:** scripts/fetch_8k_edgar_t137.py
- **Function `panel_tickers()`**: No docstring
- **Function `ticker_cik_map()`**: No docstring
- **Function `fetch_company()`**: No docstring
- **Function `main()`**: No docstring

### `fetch_all.py`
- **Function `main()`**: No docstring

### `fetch_alpaca_minute_t150.py`
**Module Docstring:** scripts/fetch_alpaca_minute_t150.py
- **Function `fetch_symbol()`**: No docstring
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

### `fetch_shiller_ie_data.py`
**Module Docstring:** fetch_shiller_ie_data — download Robert Shiller's `ie_data` workbook and cache
- **Function `parse_data_sheet()`**: No docstring
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

### `firing_curve_sweep_t118fc.py`
**Module Docstring:** scripts/firing_curve_sweep_t118fc.py
- **Function `main()`**: No docstring

### `first_real_fill_t186.py`
**Module Docstring:** T-186 — put the FIRST REAL paper fill on the board.
- **Function `main()`**: No docstring

### `fullequity_gated_leverage_t284.py`
**Module Docstring:** T-284 — trend-gated leverage on a FULL-EQUITY base. PRIMARY = 100% SPY 2x-when-trend-on;
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `ens_frac()`**: No docstring
- **Function `leg_ret()`**: return series of a strategy that is `weight` in the k-leg, gated at up to `lev`x when trend on, cash off.
- **Function `combine()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `paired()`**: No docstring
- **Function `win()`**: No docstring

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

### `income_leg_screener_t261.py`
**Module Docstring:** T-261 income-leg SCREENER ($0, screening only — NO gauntlet, NO N_trials consumed).
- **Function `tr_close()`**: No docstring
- **Function `cboe_cdn()`**: No docstring
- **Function `cboe_xls()`**: No docstring
- **Function `splice_returns()`**: Chain two index levels by RETURNS, level-matched at the seam (NOT raw levels).
- **Function `put_returns()`**: No docstring
- **Function `bxmd_returns()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `win()`**: No docstring
- **Function `main()`**: No docstring

### `index_deletion_t271.py`
**Module Docstring:** T-271 — S&P 500 deletion-reversal event study. Reuses the T-265 SIP path + event machinery.
- **Function `fetch_prices()`**: No docstring
- **Function `load()`**: No docstring
- **Function `build()`**: No docstring
- **Function `table()`**: No docstring

### `industry_momentum_t213.py`
**Module Docstring:** T-213 standalone validation for sector-neutral industry momentum.
- **Function `main()`**: No docstring

### `ingest_stooq_us_daily.py`
**Module Docstring:** scripts/ingest_stooq_us_daily.py
- **Function `normalize_ticker_for_stooq()`**: Convert project-shape ticker to Stooq-shape filename stem.
- **Function `build_stooq_index()`**: Walk the Stooq tree and build {ticker_lower: path} index.
- **Function `parse_stooq_file()`**: Parse a Stooq .us.txt file → DataFrame in project schema.
- **Function `write_processed()`**: No docstring
- **Function `get_target_tickers()`**: No docstring
- **Function `main()`**: No docstring

### `integer_share_sleeve_t257.py`
**Module Docstring:** scripts/integer_share_sleeve_t257.py
- **Function `main()`**: No docstring

### `inter_edge_correlation.py`
**Module Docstring:** Inter-edge correlation matrix on the 6 active edges + recent paused (0.25x) edges.
- **Function `load_trades()`**: No docstring
- **Function `daily_pnl_by_edge()`**: Aggregate realized PnL per edge per day. Open trades have empty pnl; we keep
- **Function `compute_correlations()`**: Daily-PnL Pearson correlation among the requested edges.
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

### `intraday_probe_t270.py`
**Module Docstring:** scripts/intraday_probe_t270.py — the ONE intraday probe (FROZEN pre-reg T-270).
- **Function `fetch_daily()`**: No docstring
- **Function `cross_check()`**: Sanity-bound the SIP first-30min extremes vs Stooq daily H/L on a sample.
- **Function `cash_on()`**: No docstring
- **Function `trend_sleeve()`**: No docstring
- **Function `robo()`**: No docstring
- **Function `realized()`**: Frozen frictions: active day → 0.5·(gross−cost) + 0.5·cash; flat day → cash.
- **Function `stats()`**: No docstring
- **Function `main()`**: No docstring

### `journal_apply.py`
**Module Docstring:** journal_apply — apply LifecycleJournal entries to data/governor/edges.yml.
- **Class `ApplyResult`**: No docstring
  - `def to_dict()`
- **Function `read_mark()`**: No docstring
- **Function `write_mark()`**: No docstring
- **Function `apply()`**: Apply pending journal entries to edges.yml.
- **Function `main()`**: No docstring

### `land_held_position_t201.py`
**Module Docstring:** T-201 — land a REAL held position the cloud loop can explain.
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

### `measure_pit_strategy_t154.py`
**Module Docstring:** scripts/measure_pit_strategy_t154.py
- **Class `_ArmTimeout`**: No docstring
- **Function `build_data_map()`**: LOCAL-ONLY data_map: resolve the historical universe (pure, reads the
- **Function `arm0_edges()`**: No docstring
- **Function `membership_mask()`**: No docstring
- **Function `canon_md5()`**: No docstring
- **Function `run_arm()`**: No docstring
- **Function `trade_filter_estimate()`**: ROBUST per-strategy survivor-inflation via membership-filtering the
- **Function `main()`**: No docstring

### `measure_survivor_inflation_t136.py`
**Module Docstring:** scripts/measure_survivor_inflation_t136.py
- **Function `load_price_panel()`**: No docstring
- **Function `exchange_map()`**: SEC company_tickers_exchange.json → ticker -> exchange (best-effort).
- **Function `classify_exits()`**: One row per membership exit inside the window, with classification.
- **Function `ew_series()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `main()`**: No docstring

### `merge_stooq_alpaca_substrate.py`
**Module Docstring:** scripts/merge_stooq_alpaca_substrate.py
- **Function `fit_ratio_loglinear()`**: Fit log(alpaca_close / stooq_close) ~ a + b*days_from_epoch on overlap.
- **Function `apply_dividend_strip()`**: Apply ratio(t) = exp(a + b*(t - epoch)) to Stooq's OHLC.
- **Function `apply_constant_rescale()`**: Fallback when overlap is too short: scale by a single constant.
- **Function `merge_ticker()`**: Merge one ticker. Returns provenance record (no IO of the result).
- **Function `main()`**: No docstring

### `metalearner_falsification_t149.py`
**Module Docstring:** scripts/metalearner_falsification_t149.py
- **Function `fit_predict()`**: No docstring
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

### `mf_etf_satellite_t253.py`
**Module Docstring:** T-253 — bought MF-ETF (DBMF/KMLM) vs our trend overlay as the barbell's
- **Function `crisis_returns()`**: No docstring
- **Function `main()`**: No docstring

### `mf_sleeve_deep_crisis_t171.py`
**Module Docstring:** T-171/T-173: deep-crisis backtest of a bought managed-futures sleeve.
- **Function `load_aqr_monthly()`**: No docstring
- **Function `load_base_monthly_returns()`**: No docstring
- **Function `mdd()`**: No docstring
- **Function `cum()`**: No docstring
- **Function `main()`**: No docstring

### `migrate_edge_graveyard_tags.py`
**Module Docstring:** One-time migration: tag failed edges with structured graveyard metadata.
- **Function `migrate()`**: Apply graveyard tags. Returns map of edge_id -> action taken.
- **Function `main()`**: No docstring

### `moonshot_rescore_t239.py`
**Module Docstring:** T-239 moonshot/return-side re-score: Wide-9 + 3-asset + robos on Sortino/up-capture/skew.
- **Function `find()`**: No docstring
- **Function `load()`**: No docstring
- **Function `dr()`**: No docstring
- **Function `robo()`**: No docstring
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `updown()`**: No docstring
- **Function `mskew()`**: No docstring

### `multiasset_carry_gauntlet_t263.py`
**Module Docstring:** scripts/multiasset_carry_gauntlet_t263.py
- **Function `spy_close()`**: No docstring
- **Function `csv_ser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `tr_close()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `carry_sleeve()`**: Diversified bond/equity/gold carry, z-score long/flat, flat=cash@short-rate.
- **Function `trend_sleeve()`**: T-255 fair trend sleeve (SPY/BOND/GOLD long-flat, flat=cash) — for the corr test.
- **Function `robo_fair()`**: No docstring
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `so()`**: No docstring
- **Function `so_ci()`**: No docstring
- **Function `sortino_np()`**: No docstring

### `multispeed_robustness_t260.py`
**Module Docstring:** T-260 multi-speed ensemble + robustness scans on the FAIR T-255 harness (same corrections).
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `sleeve()`**: exposure_fn(close)->daily target exposure in [0,1]; flat portion earns cash; ER when exposed; txn on Δexposure.
- **Function `single()`**: No docstring
- **Function `multi()`**: No docstring
- **Function `monthly_offset()`**: monthly-rebal: hold the signal evaluated on the k-th trading day of each month for that month.
- **Function `stats()`**: No docstring
- **Function `ddwin()`**: No docstring
- **Function `paired()`**: No docstring

### `news_interaction_tests_t289.py`
**Module Docstring:** T-289 tests — the 4 FROZEN news-interaction tests (a1 a2 a3 b1) + amendments F1-F4.
- **Function `px()`**: No docstring
- **Function `car()`**: No docstring
- **Function `load_hist()`**: No docstring
- **Function `run_a1()`**: No docstring
- **Function `run_a2()`**: No docstring
- **Function `run_a3()`**: No docstring
- **Function `run_b1()`**: No docstring
- **Function `main()`**: No docstring

### `offleg_ab_t259.py`
**Module Docstring:** scripts/offleg_ab_t259.py — RUN the FROZEN T-258 off-leg pre-registration.
- **Function `spy_close()`**: No docstring
- **Function `csv_ser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `tr_close()`**: No docstring
- **Function `build_offleg()`**: Frozen off-leg: hold IEF iff (mom_IEF > mom_BIL AND mom_IEF > 0), else BIL.
- **Function `sleeve()`**: EW SPY/BOND/GOLD long-flat; flat leg earns offleg_ret; ER when long; txn on
- **Function `robo_fair()`**: No docstring
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `so()`**: No docstring
- **Function `so_ci()`**: No docstring
- **Function `paired()`**: block-bootstrap paired diff (a − b): ΔSortino CI, Δterminal-wealth CI, P(Δ>0).
- **Function `yr()`**: No docstring

### `offleg_rescue_t266.py`
**Module Docstring:** scripts/offleg_rescue_t266.py — RUN the FROZEN T-266 off-leg RESCUE (family N=2, FINAL).
- **Function `spy_close()`**: No docstring
- **Function `csv_ser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `tr_close()`**: No docstring
- **Function `build_offleg_rescue()`**: T-259 base selection + the RESCUE 63d IEF fast-trend eligibility gate.
- **Function `sleeve()`**: T-255 fair sleeve; flat leg earns offleg_ret; ER when long; txn on flips +
- **Function `robo_fair()`**: No docstring
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `so()`**: No docstring
- **Function `so_ci()`**: No docstring
- **Function `paired()`**: No docstring
- **Function `yr()`**: No docstring

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
- **Function `attribute_by_edge_regime()`**: Per-edge × per-regime PnL attribution with per-cell N + bootstrap CI.
- **Function `load_trades()`**: Concatenate trades.csv from one or more run dirs/UUIDs (under
- **Function `main()`**: No docstring

### `pin_earnings_dates.py`
**Module Docstring:** T-2026-06-11-155 — one-time pin of earnings dates into the substrate.
- **Function `main()`**: No docstring

### `pit_universe_dryrun_t207.py`
**Module Docstring:** T-2026-06-18-207 — DRY-RUN the PIT (survivorship-corrected) universe expansion.
- **Function `restore_clean_governor()`**: No docstring
- **Function `main()`**: No docstring

### `premium_tier_t279.py`
**Module Docstring:** T-279 — the $65-70K+ TIER test: DIRECT premium harvesting (N_trials += 1, tier-labeled).
- **Function `sleeve()`**: No docstring
- **Function `put_leg()`**: No docstring
- **Function `robo()`**: No docstring
- **Function `combine()`**: monthly-rebalanced (1-w) sleeve + w premium.
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `paired()`**: No docstring
- **Function `ddwin()`**: No docstring
- **Function `main()`**: No docstring

### `probe_engine_c_reachability_t158.py`
**Module Docstring:** scripts/probe_engine_c_reachability_t158.py
- **Function `install_probes()`**: No docstring
- **Function `cancellation_replay()`**: Offline S-vs-0.5S replays on captured real inputs, both modes.
- **Function `main()`**: No docstring

### `probe_news_depth_t289.py`
**Module Docstring:** T-289a — Alpaca News (Benzinga) depth/survivorship/breadth PROBE. Gates the whole news lane.
- **Function `fetch()`**: No docstring

### `reconcile_stooq_tr_t256.py`
**Module Docstring:** T-2026-07-02-256 Part 2 — TR reconciliation of the Stooq-ingested ETFs.
- **Function `load_stooq_close()`**: No docstring
- **Function `fetch_yf_tr()`**: yfinance total-return OHLC (T-167 basis) + split-adj Close for the basis check.
- **Function `compute_atr_prevclose()`**: No docstring
- **Function `ann_ret()`**: No docstring
- **Function `reconcile()`**: No docstring
- **Function `main()`**: No docstring

### `regen_spy_full_history_t167.py`
**Module Docstring:** T-2026-06-13-167 GAP 3 — regenerate data/processed/SPY_1d.csv with FULL history.
- **Function `fetch_deep_tr()`**: yfinance SPY on total-return basis (matches the existing file).
- **Function `compute_atr_prevclose()`**: Project convention: ATR = 14d rolling MEAN of True Range (min 14).
- **Function `main()`**: No docstring

### `regime_conditional_overlay_t220.py`
**Module Docstring:** T-220 — always-on vs regime-gated trend overlay (the SHAPE verdict for C).
- **Function `causal_p_crisis()`**: Frozen-HMM causal p_crisis: train on [start, train_end] (crisis-state =
- **Function `regime_label()`**: No docstring
- **Function `main()`**: No docstring

### `regime_ground_truth_deepwindow_t221.py`
**Module Docstring:** T-221 — regime ground-truth + defensive-behavior pre-spec for the deep-window
- **Function `main()`**: No docstring

### `regime_oos_loco_t172.py`
**Module Docstring:** T-172 — regime-detector leave-one-crisis-out OOS generalization test.
- **Function `build_deep_panel()`**: No docstring
- **Function `loco_fold()`**: No docstring
- **Function `main()`**: No docstring

### `regime_sleeve_sizer_t178.py`
**Module Docstring:** T-178 — dynamic MF-sleeve SIZER A/B vs always-on 20% (Step 2).
- **Function `main()`**: No docstring

### `reprice_lps_auction_t157.py`
**Module Docstring:** T-157: re-price T-135's LPS overnight harvest under the SHIPPED
- **Function `cost_per_day_decimal()`**: All channels in decimal daily return units (of capital).
- **Function `ann_ret_pct()`**: No docstring
- **Function `ann_vol_pct()`**: No docstring
- **Function `sharpe()`**: No docstring
- **Function `block_bootstrap_ann_ci()`**: No docstring
- **Function `account_views()`**: Roth (pre-tax) and taxable-IL (annual-netting approximation).
- **Function `main()`**: No docstring

### `reset_base_edges.py`
**Module Docstring:** scripts/reset_base_edges.py
- **Function `load_edges()`**: No docstring
- **Function `save_edges()`**: No docstring
- **Function `preview()`**: Return edge_ids that would be demoted.
- **Function `demote()`**: Mutate in place: active → candidate. Returns count.
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

### `run_combined_scorecard.py`
**Module Docstring:** scripts/run_combined_scorecard.py
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

### `run_foundry_eval_t195.py`
**Module Docstring:** T-2026-06-17-195 — CORRECTED discovery eval harness for a valid foundry test.
- **Function `restore_clean_governor()`**: FIX 2a: restore the canonical 6-edge production book from the anchor.
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

### `run_paper_cloud_day.py`
**Module Docstring:** T-186 — one paper day in the cloud (EventBridge → Fargate → here).
- **Function `main()`**: Run one cloud paper day. ``now``/``client``/``cloud`` are injectable

### `run_paper_day_t163.py`
**Module Docstring:** T-163 Part C — run ONE armed paper day end-to-end on the PAPER account.
- **Function `main()`**: No docstring

### `run_paper_day_t185.py`
**Module Docstring:** T-185 — a window-aware, calendar-aware, heartbeat-recording paper day.
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

### `run_phase0b_foundry_discover_t193.py`
**Module Docstring:** T-2026-06-17-193 Phase-0b — the first HONEST test of the Foundry vocabulary.
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

### `run_vol_target_arms_full.py`
**Module Docstring:** scripts/run_vol_target_arms_full.py
- **Function `vol_target_patch()`**: Patch risk_settings.json to enable/disable vol-targeting, restore on exit.
- **Function `run_full()`**: No docstring
- **Function `main()`**: No docstring

### `run_vrp_gauntlet_t122.py`
**Module Docstring:** scripts/run_vrp_gauntlet_t122.py
- **Function `main()`**: No docstring

### `screen_features_t150.py`
**Module Docstring:** scripts/screen_features_t150.py
- **Function `load_returns()`**: No docstring
- **Function `mi_with_nulls()`**: Pooled MI per feature vs forward return, with circular-shift nulls.
- **Function `main()`**: No docstring

### `secondary_basis_check_t285.py`
**Module Docstring:** T-285 — basis-check the SECONDARY's bond/gold 2x legs vs REAL 2x ETFs (UGL 2x gold, UBT 2x 20yr tsy),
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `yf_close()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `synth2x()`**: No docstring
- **Function `basis()`**: No docstring
- **Function `ens_frac()`**: No docstring
- **Function `leg_ret()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `combine()`**: No docstring

### `sleeve_phase0_verdict.py`
**Module Docstring:** Sleeve Phase-0 verdict harness — drives a Sleeve through a measurement-
- **Function `run_sleeve()`**: Run the sleeve through a sequence of rebalance dates. Returns
- **Function `run_trend_verdict()`**: No docstring
- **Function `run_moonshot_verdict()`**: No docstring
- **Function `main()`**: No docstring

### `smallcap_momentum_gauntlet_t249.py`
**Module Docstring:** T-249 small-cap 12-1 momentum gauntlet — gross vs HONEST small-cap cost. Survivor-biased universe (upper bound).
- **Function `load_monthly()`**: Return (month-end close Series, month-end trailing dollar-ADV Series) or None.
- **Function `run()`**: No docstring
- **Function `stats()`**: No docstring

### `smallcap_pead_pilot_t265.py`
**Module Docstring:** T-265 — survivorship-complete small-cap panel + PEAD low-coverage event-study pilot.
- **Function `stage_edgar()`**: No docstring
- **Function `stage_map()`**: No docstring
- **Function `stage_prices()`**: No docstring
- **Function `stage_study()`**: No docstring
- **Function `stage_announce()`**: No docstring

### `special_situations_monitor_t277.py`
**Module Docstring:** scripts/special_situations_monitor_t277.py
- **Function `scan()`**: No docstring
- **Function `persist()`**: No docstring
- **Function `main()`**: No docstring

### `spot_basket_extended_sweep_t115.py`
**Module Docstring:** T-115 — extend the T-112 spot-basket sweep to {25%, 30%} on the deep
- **Function `main()`**: No docstring

### `spot_sleeve_closeout_analysis_t128.py`
**Module Docstring:** T-128 spot-sleeve close-out analysis — the definitive 16/26-yr integrated A/B.
- **Function `fetch_snapshots()`**: No docstring
- **Function `daily_returns()`**: No docstring
- **Function `sharpe()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `max_drawdown()`**: No docstring
- **Function `year_return()`**: No docstring
- **Function `block_bootstrap_ci()`**: Block bootstrap on the DIFFERENCE series; returns (ci_low, ci_high)
- **Function `analyze()`**: No docstring
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

### `strategy_riskparity_frontier_t248.py`
**Module Docstring:** T-248 strategy-level risk-parity frontier — naive vs HRP over {base, trend} vs robos.
- **Function `load_close()`**: No docstring
- **Function `etf_rets()`**: No docstring
- **Function `robo_returns()`**: No docstring
- **Function `base_returns()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `updown()`**: No docstring
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
- **Function `build_canary_cells()`**: 3-rep single-year canary on the spec's first arm.
- **Function `check_canary()`**: True if all canary canons are present and identical.
- **Function `submit_all()`**: Submit cells in parallel (Batch handles N concurrent submits fine).
- **Function `poll_until_terminal()`**: Poll Batch describe-jobs until all cells reach SUCCEEDED or FAILED.
- **Function `fetch_manifests()`**: Pull per-cell manifest.json from S3 for cells that SUCCEEDED.
- **Function `write_summary()`**: No docstring
- **Function `main()`**: No docstring

### `submit_foundry_eval_t196.py`
**Module Docstring:** T-196 foundry-eval cloud submit. Runs D's BAKED run_foundry_eval_t195.py
- **Function `submit()`**: No docstring

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

### `tail_rescore_t234.py`
**Module Docstring:** T-234 tail re-score — robos (monthly-rebal) vs T-215 base/composition. No new backtest.
- **Function `load_close()`**: No docstring
- **Function `etf_daily_returns()`**: No docstring
- **Function `robo_returns()`**: monthly-rebal robo daily returns. weights: {SPY:..,AGG:..,GLD:..,_cash:..}
- **Function `equity_returns()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `updown_capture()`**: monthly up/down capture vs robo.
- **Function `win()`**: No docstring
- **Function `dd_in_window()`**: No docstring

### `train_gate.py`
- **Function `train_gate_model()`**: Train the SignalGate model using harvested data.

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

### `trend_gated_leverage_t282.py`
**Module Docstring:** T-282 — trend-gated leverage: the validated ensemble sleeve with its SPY leg at up to 2x WHEN trend on.
- **Function `spy_close()`**: No docstring
- **Function `cser()`**: No docstring
- **Function `macro()`**: No docstring
- **Function `cash_on()`**: No docstring
- **Function `real_sso()`**: No docstring
- **Function `build_sleeve()`**: No docstring
- **Function `stats()`**: No docstring
- **Function `paired()`**: No docstring
- **Function `win()`**: No docstring

### `trend_overlay_validation_t204.py`
**Module Docstring:** T-204 — standalone validation of the trend overlay (the PRE-REGISTERED
- **Function `load_close()`**: No docstring
- **Function `metrics()`**: No docstring
- **Function `crisis_mdds()`**: No docstring
- **Function `position_stats()`**: No docstring
- **Function `main()`**: No docstring

### `trend_sleeve_gauntlet_t236.py`
**Module Docstring:** T-236 trend-sleeve gauntlet — full-cycle (incl dotcom) on index substrate.
- **Function `spy_close()`**: No docstring
- **Function `csv_series()`**: No docstring
- **Function `daily_ret()`**: No docstring
- **Function `robo()`**: No docstring
- **Function `win()`**: No docstring
- **Function `maxdd()`**: No docstring
- **Function `cagr()`**: No docstring
- **Function `sortino_ci()`**: No docstring
- **Function `sharpe()`**: No docstring
- **Function `updown()`**: No docstring
- **Function `ddw()`**: No docstring

### `trend_wider_breadth_validation_t214.py`
**Module Docstring:** T-214 — does WIDER cross-asset breadth strengthen the trend sleeve's
- **Function `load_all()`**: No docstring
- **Function `common_window()`**: No docstring
- **Function `inverse_vol_sleeve()`**: Wide sleeve, each asset long/flat (cash off-leg), combined with
- **Function `equal_weight_sleeve()`**: No docstring
- **Function `buyhold_sleeve()`**: No docstring
- **Function `mean_pairwise_corr()`**: No docstring
- **Function `main()`**: No docstring

### `update_data.py`
- **Function `update_all_data()`**: Programmatic entry point for data updating.
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

### `verify_altdata_snapshot.py`
**Module Docstring:** scripts/verify_altdata_snapshot.py
- **Function `main()`**: No docstring

### `verify_gate1_cache_determinism.py`
**Module Docstring:** scripts/verify_gate1_cache_determinism.py
- **Function `load_data_map()`**: No docstring
- **Function `build_candidate_spec()`**: No docstring
- **Function `main()`**: No docstring

### `vixterm_tilt_t274.py`
**Module Docstring:** scripts/vixterm_tilt_t274.py
- **Function `sleeve()`**: Fair sleeve; SPY leg optionally tilted by mode ∈ {none, t252, vixterm}.
- **Function `main()`**: No docstring

### `vrp_edge_t174.py`
**Module Docstring:** T-174: VRP (variance risk premium) equity-implementable edge backtest.
- **Function `sharpe()`**: No docstring
- **Function `mdd()`**: No docstring
- **Function `boot_diff()`**: No docstring
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

### `wire_sec_insider_feed_t136.py`
**Module Docstring:** scripts/wire_sec_insider_feed_t136.py
- **Function `quarters()`**: No docstring
- **Function `fetch_zip()`**: No docstring
- **Function `parse_quarter()`**: No docstring
- **Function `main()`**: No docstring
