# ArchonDEX Execution Manual

> **AI Agent Notice:** Use the commands below as your absolute reference for interacting with ArchonDEX. Never guess arbitrary python scripts or pathways. If you are tasked with a specific operation, search this manual for the exact execution syntax. When using the command line, you must track what works, what fails, and what it does in your reasoning. If you utilize or create a NEW command that is not in this document, you MUST immediately add it here.

---

### RUNTIME FLAGS (`run_backtest.py` and related scripts)

Two orthogonal axes control which configs and which state files a run uses. They are independent — choose each based on what you're doing.

**`--env {dev, prod}`** — selects which *config file* pair to load. Parsed in `ModeController.__init__` ([mode_controller.py:522, 551](orchestration/mode_controller.py#L522)).

| env | Alpha config | Risk config | Purpose |
|-----|--------------|-------------|---------|
| `dev` | `alpha_settings.dev.json` | `risk_settings.dev.json` | Debug on, loose thresholds (enter=0.10, exit=0.03), only `rsi_mean_reversion` + `xsec_meanrev` weighted. Use for quick iteration. |
| `prod` | `alpha_settings.prod.json` | `risk_settings.prod.json` | Debug off, tight thresholds (enter=0.01, exit=0.005), full edge roster with curated weights. This is the canonical settings. |

Default: `prod`. Use `--env dev` for rapid parameter experiments without editing the prod config.

**`--mode {sandbox, prod}`** — selects where *Governor state* is read from and written to. Parsed in `ModeController.run_backtest()` ([mode_controller.py:772-774](orchestration/mode_controller.py#L772-L774)).

| mode | Governor state path | Purpose |
|------|---------------------|---------|
| `prod` | `data/governor/edge_weights.json` + `regime_edge_performance.json` | Main learned state. Every run reads from and writes to these files. |
| `sandbox` | `data/governor/sandbox/edge_weights.json` + `regime_edge_performance.json` | Isolated scratch state. Use to test changes without contaminating main governor memory. |

Default: `prod`. Use `--mode sandbox` when you want to run backtests that should not update the main governor's learned weights.

**`--no-governor`** — skips the post-run `governor.update_from_trades()` + `save_weights()` call entirely ([mode_controller.py:838-840](orchestration/mode_controller.py#L838-L840)). The backtest still *reads* current governor state at startup, but does not write. Use for deterministic A/B tests where you want identical state between runs.

**`--reset-governor`** — resets governor learned weights to neutral (1.0 for all edges) at run startup, without touching the persisted `edge_weights.json`. The governor still runs and updates weights during the run, and if `--no-governor` is not also passed, writes the newly learned weights at the end. Use for clean in-sample measurement runs where stale OOS affinity would inject forward-looking signal. Rule of thumb: `--reset-governor` for measurement, `--no-governor` for deterministic A/B anchoring, both together for a completely isolated run. See: `engines/engine_f_governance/governor.py::reset_weights`, `tests/test_governor_reset.py`.

**Note on combining flags:** `--env` and `--mode` are independent. Typical combinations:
- `--env prod --mode prod` (default): real backtest that updates learned state.
- `--env prod --mode sandbox`: test a code change against prod configs without polluting main governor.
- `--env dev --mode sandbox`: quick iteration on debug configs in isolated state.

### DETERMINISTIC A/B TESTING

Backtests are *not* naturally deterministic across runs because every run that doesn't pass `--no-governor` writes `data/governor/edge_weights.json` and `regime_edge_performance.json`. Run 2 then reads post-run-1 state and produces different results — not because the code is non-deterministic, but because its inputs are.

To get reproducible results for A/B comparisons:

```bash
# 1. Create an anchor snapshot of governor state (one-time)
cp data/governor/regime_edge_performance.json data/governor/regime_edge_performance.json.anchor
cp data/governor/edge_weights.json data/governor/edge_weights.json.anchor

# 2. Before each test run, restore the anchor
cp data/governor/regime_edge_performance.json.anchor data/governor/regime_edge_performance.json
cp data/governor/edge_weights.json.anchor data/governor/edge_weights.json

# 3. Run with --no-governor so the run does not mutate the anchor for the next test
python -m scripts.run_backtest --no-governor

# 4. Verify determinism across two runs
md5 data/trade_logs/trades.csv      # run 1 md5
# (restore anchor, run again)
md5 data/trade_logs/trades.csv      # should match run 1
```

`scripts/run_deterministic.py` (wrapper that handles anchor save/restore + md5 comparison) is the preferred entry point for this workflow.

**Determinism also requires `PYTHONHASHSEED=0`** — Python 3 randomizes string hashing per-process by default, which makes `set()` iteration order differ across invocations. `run_deterministic.py` sets this automatically via a self-reexec guard at the top of the module; no manual action needed. When running `scripts/run_backtest` directly for A/B comparisons, prefix with `PYTHONHASHSEED=0 python -m scripts.run_backtest --no-governor`.

### Regime / HMM — THE CANONICAL PATH (T-222 consolidation)

There are exactly **two** live regime-HMM paths; everything else under
`scripts/*hmm*` / `scripts/*regime*` was early exploration and is now in
`Archive/scripts/` (superseded — see the T-222 archive list). Do NOT re-derive
or re-tune the HMM; the regime science is settled (see the **"Validated regime
findings"** block in `docs/Core/engine_charters.md` → Engine E — canonical).

1. **Production regime HMM** — `engines/engine_e_regime/regime_detector.py`
   (+ `hmm_classifier.py`, `macro_features.py`). The backtest's ModeController
   calls `RegimeDetector.detect_regime()` once per bar; it trains the HMM at
   init from the macro feature panel and publishes the causal posterior at
   `regime_meta["hmm_regime"]["probabilities"]` (the lookahead-clean
   `predict_proba_at` forward filter; T-089). Consumers read **`hmm_regime`**,
   NOT the 5-axis `advisory["regime_summary"]` (which is not a validated
   predictor). This is the live, load-bearing path — do not touch its model.

2. **Canonical RESEARCH / measurement HMM** — `scripts/regime_oos_loco_t172.py`
   (`build_deep_panel()` + `_causal_filtered_posterior()`). The deep reduced
   feature panel (spy_ret_5d, spy_vol_20d, bond_ret_20d, vix_level,
   yield_curve_spread, credit_spread; sources: `data/processed/SPY_1d.csv`,
   `data/macro/{DGS10,DGS3MO,BAA10Y,AAA10Y}.parquet`,
   `data/research/vix_deep_t172.csv`), a seed-pinned GaussianHMM, and the
   causal forward filter. **Single source of truth** for offline regime
   labels; reused (not forked) by `regime_conditional_overlay_t220.py`,
   `regime_ground_truth_deepwindow_t221.py`, and `regime_sleeve_sizer_t178.py`.
   Deterministic (SEED=0). To regenerate the deep-window regime ground-truth:
   `python -m scripts.regime_ground_truth_deepwindow_t221`.

   The HMM is **regime-grade, not timing-grade**: it fires only ~20% into
   every historical drawdown. Tail protection is the always-on trend overlay
   (`core/trend_overlay.py`, T-204/T-220/T-221), NOT the regime flip.
   Regime-GATING a defensive signal net-negatives (T-178 sizer, T-220 overlay)
   — always-on is the ceiling.

A minimal-HMM variant path (`scripts/train_minimal_hmm.py` +
`validate_minimal_hmm.py`, artifacts `engines/engine_e_regime/models/hmm_minimal_*_v1.pkl`)
is retained for the `test_minimal_hmm` fixture but is not on the canonical
deploy path.

### WALK-FORWARD VALIDATION (regime-conditional governor) — the principle

Any regime-conditional mechanism (governor-per-regime weights, per-edge
kill-switches conditioned on regime stats) must pass **walk-forward** before
re-enabling. In-sample A/B hides overfitting — on 2026-04-23 an in-sample
Sharpe penalty of −0.15 revealed itself as −0.50 under walk-forward,
falsifying the per-edge-per-regime kill mechanism. Acceptance: **OOS Sharpe of
the activated variant ≥ OOS baseline Sharpe** — anything below is a no-go
regardless of in-sample result. (The original `walk_forward_regime` harness is
archived; the canonical walk-forward for the HMM regime is the LOCO design in
`regime_oos_loco_t172.py`, and the standing finding is that regime-conditional
defensive gating does NOT clear this bar — T-178/T-220.)

```bash
# Phase 2.10 year-by-year walk-forward: run all 9 Phase 2.10 edges on each
# calendar year (2021-2024) independently with --no-governor. Reports per-year
# Sharpe vs SPY delta table. Backs up + restores governor state automatically.
PYTHONHASHSEED=0 python -m scripts.walk_forward_phase210

# Run specific years only:
PYTHONHASHSEED=0 python -m scripts.walk_forward_phase210 --years 2022 2023 2024
```

---

### MULTI-YEAR FOUNDATION MEASUREMENT

```bash
# Default (legacy static-list universe):
PYTHONHASHSEED=0 python -m scripts.run_multi_year \
    --years 2021,2022,2023,2024,2025 --runs 3 \
    --output docs/Measurements/<year-month>/multi_year_foundation_measurement.md

# Survivorship-bias-aware universe (F6 wire, 2026-05-09):
# Resolves S&P 500 historical membership union over the backtest window
# instead of the 109-ticker static list in config/backtest_settings.json.
# Requires data/universe/sp500_membership.parquet (run
# `python -m scripts.fetch_universe --membership-only` first if absent).
PYTHONHASHSEED=0 python -m scripts.run_multi_year \
    --years 2021,2022,2023,2024,2025 --runs 3 \
    --use-historical-universe \
    --output docs/Measurements/<year-month>/multi_year_universe_aware.md \
    --json-output docs/Measurements/<year-month>/multi_year_universe_aware.json
```

The `--use-historical-universe` flag wires `engines/data_manager/universe_resolver.py::resolve_universe` into `ModeController.run_backtest`. Behavior is opt-in (default false) — the static path is preserved for backward-compat with prior measurement campaigns.

### AUTONOMOUS MODE (THE "ONE BUTTON")
Runs the full cycle: Data -> Hunt -> Navigate -> Trade
```bash
python scripts/run_autonomous_cycle.py
# Run in infinite loop (Master Controller)
python scripts/run_autonomous_cycle.py --loop
```

### ENVIRONMENT SETUP
```bash
python3 -m venv .venv
source .venv/bin/activate            # macOS / Linux
# .venv\Scripts\activate             # Windows
pip install -r requirements.txt
deactivate                           # Environment Management
```

### SYSTEM HEALTH & DIAGNOSTICS
```bash
# Run full system health diagnostics (edges, backtest, governor, trades)
python -m scripts.run_diagnostics

# Run diagnostics in sandbox mode (isolated governor updates)
python -m scripts.run_diagnostics --mode sandbox

# Run edge feedback update in sandbox mode (safe learning)
python -m analytics.edge_feedback --mode sandbox

# Verify recency-decay weighting behavior
python -m analytics.edge_feedback --mode sandbox --debug

# Run unified health check (pytest + backtest + invariant checks)
python -m scripts.run_healthcheck
python -m scripts.run_healthcheck --skip-tests    # Skip pytest, run backtest only
python -m scripts.run_healthcheck --skip-backtest  # Skip backtest, run pytest only
```

### CORE SYSTEM COMMANDS
```bash
# Run full backtest (Alpha → Risk → OMS → Portfolio → Governor)
python -m scripts.run_backtest

# Run with fresh logs (clears prior trades/snapshots)
python -m scripts.run_backtest --fresh

# Run AlphaEngine signal generation only (diagnostic)
python -m scripts.run_backtest --mode alpha --alpha-debug
python -m scripts.run_backtest --mode alpha --debug # (Legacy)

# Launch Cockpit dashboard V2 (Modern)
python -m cockpit.dashboard_v2.app
# Launch on custom port (default 8050)
python -m cockpit.dashboard_v2.app --port 8055
# Live mode (2s pulse refresh) — drives the Paper tab (T-182): census/health
# banner, paper run status, §5 scorecard, equity-vs-robo. Read-only.
python -m cockpit.dashboard_v2.app --live --port 8050

# Run Governor weight update from latest results
python -m analytics.edge_feedback
python -m analytics.edge_feedback --history     # show weight history
```

### RESEARCH & EDGE HARNESS
```bash
# Run parameter sweep / walk-forward for a single edge
python -m research.edge_harness \
  --edge <EDGE_NAME> \
  --param-grid config/grids/<EDGE>.json \
  --walk-forward "YYYY-MM-DD:YYYY-MM-DD" \
  --backtest-config config/backtest_settings.json \
  --risk-config config/risk_settings.json

# Run edge evaluator (rank edges by time-decay composite score)
python -m scripts.run_evaluator

# Clear old research results
rm -rf data/research/*
```

### EVOLUTION & OPTIMIZATION (DARWIN)
```bash
# FULL DISCOVERY CYCLE (Recommended — post-backtest)
# Runs: regime detection → feature hunt (LightGBM+DTree) → GA evolution →
#       4-gate validation (backtest → PBO → WFO → significance) → auto-promote
python -m scripts.run_backtest --discover
python -m scripts.run_backtest --fresh --discover    # with fresh logs

# GENERATE CANDIDATES ONLY (no validation)
# Creates template mutations + GA-evolved composite genomes
python -m engines.engine_d_discovery.discovery

# VALIDATE CANDIDATES (Evolutionary Selector)
# Runs walk-forward optimization on 'candidate' edges.
# Promotes winners to 'active' status.
python -m scripts.optimize

# ML DATA HARVEST (Experimental)
# Collects trade signals and outcomes for ML training
python -m scripts.harvest_data
```

### PHASE 2: RESEARCH & SHADOW TRADING
```bash
# Run the Shadow Loop (Hunter + Gatherer)
# - Discovers new 'Hunter' rules using Decision Trees.
# - Validates candidates in a Shadow Broker simulation.
# - Requires NO risk; uses 'Ghost Money'.
python scripts/run_shadow_paper.py
```

### DATA & MARKET INTELLIGENCE
```bash
# Update ALL Data (Intraday + Fundamentals)
# Reads tickers from config/universe.json
python scripts/update_data.py

# Fetch entire universe history (defined in config/backtest_settings.json)
python scripts/fetch_all.py

# Fetch specific normalized OHLCV data (via Alpaca or Yahoo fallback)
python scripts/fetch_data --tickers AAPL MSFT SPY \
  --start 2022-01-01 --end 2025-01-01 --timeframe 1d

# Verify DataManager integrity and source availability
python debug/verify_dm_integrity.py

# Collect and summarize latest financial news
python -m intelligence.news_collector
python -m intelligence.news_summarizer
```

### ANALYTICS & PERFORMANCE
```bash
# PERFORMANCE BENCHMARK (full scorecard)
# Runs a standardized backtest and outputs:
#   Portfolio metrics (Sharpe, Sortino, Calmar, CAGR, MDD, profit factor)
#   Per-edge breakdown (PnL, win rate, trade count)
#   SPY buy-and-hold comparison (alpha measurement)
python -m scripts.run_benchmark
python -m scripts.run_benchmark --start 2023-01-01 --end 2024-12-31
python -m scripts.run_benchmark --capital 50000
python -m scripts.run_benchmark --json     # JSON output only
# Report saved to: data/research/benchmark_report.json

# View research and backtest outputs
cat data/trade_logs/trades.csv
cat data/trade_logs/portfolio_snapshots.csv
cat data/governor/edge_weights.json

# View Parquet research results (binary format, requires Python)
python -c "import pandas as pd; print(pd.read_parquet('data/research/edge_results.parquet'))"
```

### MACRO DATA (FRED)
```bash
# The FRED macro pipeline lives at engines/data_manager/macro_data.py.
# It is a library — no CLI script. Cache in data/macro/<SERIES_ID>.parquet.
# Requires FRED_API_KEY in .env (free key: https://fredaccount.stlouisfed.org/apikeys).
# Without a key the manager runs in cache-only mode.

# Bootstrap / refresh the curated panel from a Python shell:
python -c "from engines.data_manager.macro_data import MacroDataManager; \
mgr = MacroDataManager(); panel = mgr.fetch_panel(); \
print(panel.tail()); print(mgr.cache_status())"

# Refresh a single series:
python -c "from engines.data_manager.macro_data import MacroDataManager; \
print(MacroDataManager().fetch_series('DGS10', force=True).tail())"

# Inspect the on-disk cache state without hitting the network:
python -c "from engines.data_manager.macro_data import MacroDataManager; \
print(MacroDataManager(api_key=None).cache_status().to_string())"

# E-rebuild phase-1 (added 2026-05-07): yfinance leading-indicator series
# (HG=F copper, GC=F gold, XLP, XLY) for copper-gold + defensive-cyclical
# rotation features. Cached as data/macro/{HG_F,GC_F,XLP,XLY}.parquet.
python scripts/fetch_leading_indicators.py
python scripts/fetch_leading_indicators.py --start 2010-01-01 --end 2026-05-07

# Train minimal-HMM variants (A: 4 long-history FRED features, B: A + HY-IG
# OAS, C: B + intermarket RS). All trained on shared 2023-10 → 2024-12
# window. Model artifacts at engines/engine_e_regime/models/hmm_minimal_*_v1.pkl,
# state series at data/macro/minimal_hmm_states_<variant>.parquet.
python scripts/train_minimal_hmm.py --variant all
python scripts/train_minimal_hmm.py --variant C --test-end 2026-04-17

# Validate variants vs forward SPY drawdowns at 5d/20d/60d horizons.
# Writes data/research/hmm_minimal_validation_2026_05.json + stdout summary.
python scripts/validate_minimal_hmm.py --test-end 2026-04-17
```

### EARNINGS DATA (yfinance)
```bash
# The earnings pipeline lives at engines/data_manager/earnings_data.py.
# It is a library — no CLI script. Cache in data/earnings/<SYMBOL>_calendar.parquet.
# Backend: yfinance (no API key required). Finnhub was the original
# backend but its free tier returns 0 historical earnings — see
# memory/project_finnhub_free_tier_no_historical_2026_04_25.md.
# Manager rate-limits to 1.1s/call by default to be polite to Yahoo.
# Online by default; pass offline=True for cache-only mode.

# Bootstrap the cache for a universe (loops with rate limiting):
python -c "from engines.data_manager.earnings_data import EarningsDataManager; \
mgr = EarningsDataManager(offline=False); df = mgr.fetch_universe(['AAPL','MSFT','NVDA']); \
print(df.tail()); print(mgr.cache_status())"

# Refresh a single symbol (force-bypass the 24h freshness window):
python -c "from engines.data_manager.earnings_data import EarningsDataManager; \
print(EarningsDataManager(offline=False).fetch_calendar('AAPL', force=True).tail())"

# Inspect the on-disk cache state without hitting the network:
python -c "from engines.data_manager.earnings_data import EarningsDataManager; \
print(EarningsDataManager(offline=True).cache_status().to_string())"

# Re-bootstrap the full universe (115 tickers, ~150s with default rate limit):
python -c "import json, warnings; warnings.filterwarnings('ignore'); \
from engines.data_manager.earnings_data import EarningsDataManager; \
mgr = EarningsDataManager(offline=False); \
mgr.fetch_universe(json.load(open('config/universe.json')), force=True); \
print(mgr.cache_status().to_string())"
```

### INSIDER TRANSACTIONS (OPENINSIDER)
```bash
# The OpenInsider scraper lives at engines/data_manager/insider_data.py.
# It is a library — no CLI script. Cache in data/insider/<TICKER>.parquet.
# OpenInsider is unauthenticated — no API key required.
# Be a good citizen: rate-limited to 1.5s/call by default; never spam.

# Bootstrap the cache for a universe (loops with rate limiting):
python -c "from engines.data_manager.insider_data import InsiderDataManager; \
mgr = InsiderDataManager(); df = mgr.fetch_universe(['AAPL','MSFT','NVDA']); \
print(df.tail()); print(mgr.cache_status())"

# Refresh a single ticker (force-bypass the 24h freshness window):
python -c "from engines.data_manager.insider_data import InsiderDataManager; \
print(InsiderDataManager().fetch_filings('AAPL', force=True).tail())"

# Inspect the on-disk cache state without hitting the network:
python -c "from engines.data_manager.insider_data import InsiderDataManager; \
print(InsiderDataManager().cache_status().to_string())"
```

### UNIVERSE MEMBERSHIP (S&P 500 historical)
```bash
# The membership loader lives at engines/data_manager/universe.py.
# Source: Wikipedia "List of S&P 500 companies". No API key required.
# Cache at data/universe/sp500_membership.parquet (refresh window: 7 days).

# Refresh the cached membership history (one network call):
python -c "from engines.data_manager.universe import SP500MembershipLoader; \
loader = SP500MembershipLoader(); df = loader.fetch_membership(force=True); \
print(loader.cache_status()); print('current:', len(loader.current_constituents()))"

# Survivorship-bias-aware snapshot for an arbitrary historical date:
python -c "from engines.data_manager.universe import SP500MembershipLoader; \
print(SP500MembershipLoader().historical_constituents('2018-01-01')[:10])"

# Inspect the cache state without hitting the network:
python -c "from engines.data_manager.universe import SP500MembershipLoader; \
print(SP500MembershipLoader().cache_status())"
```

The companion CLI `scripts/fetch_universe.py` uses the membership list
to populate `data/processed/` (OHLCV bars) via the existing
`DataManager` pipeline. It is **explicit user action only** — running
it for the full historical universe is a 30-60 minute job that hits
Alpaca's rate limit, so it is never invoked by tests, hooks, or
backtests.

```bash
# Preview which tickers would be fetched without touching the API:
python -m scripts.fetch_universe --source sp500_historical --dry-run

# Fetch only today's S&P 500 constituents:
python -m scripts.fetch_universe --source sp500_current --start 2018-01-01

# Fetch the full historical union (every ticker that's ever been in the index)
# — recommended for survivorship-bias-aware backtests:
python -m scripts.fetch_universe --source sp500_historical --start 2018-01-01

# Fetch from a custom newline-separated ticker file:
python -m scripts.fetch_universe --source file --file my_tickers.txt

# Cap the number of fetches per run (useful for incremental backfills):
python -m scripts.fetch_universe --source sp500_historical --max-tickers 50

# Re-fetch tickers that already have a cached parquet (forces refresh):
python -m scripts.fetch_universe --source sp500_current --refresh
```

Idempotent by default: tickers whose
`data/processed/parquet/<TICKER>_<TF>.parquet` already exists are
skipped. The script exits with code 0 on full success, 1 if any
ticker failed to fetch, 2 if Alpaca credentials are missing for a
non-empty fetch list.

#### Sourcing delisted / share-class names

`fetch_universe.py` works for active tickers. For S&P 500 names that
were delisted during the backtest window (FRC, SIVB, ATVI, TWTR, …),
yfinance now 404s on most non-trading symbols and the public Stooq
CSV endpoint requires a captcha-issued API key. Use
`scripts/fetch_missing_delisted.py` instead — it tries Alpaca v2
historical bars (which retains delisted-name history because the
broker held positions) before falling back to yfinance and Stooq.
Provenance is tracked at
`data/processed/_data_provenance_delisted.json`.

```bash
# Discover the missing 2021-2025 S&P 500 union and source from the chain:
python -m scripts.fetch_missing_delisted

# List what would be fetched without hitting any API:
python -m scripts.fetch_missing_delisted --dry-run

# Targeted retry of specific names:
python -m scripts.fetch_missing_delisted --tickers FRC SIVB ATVI

# Different membership window or backfill start:
python -m scripts.fetch_missing_delisted \
    --window-start 2018-01-01 --window-end 2025-12-31 \
    --start 2018-01-01

# Skip a particular source in the chain (for debugging):
python -m scripts.fetch_missing_delisted --skip-yfinance
```

The script applies a `HARD_DELIST_DATES` map for names whose equity
stub kept trading at penny prices post-failure (FRC, SIVB) and
truncates everything else at the membership table's `included_until +
7d` — so backtests don't see post-removal phantom data. Stray odd-lot
leading bars (Alpaca occasionally emits one isolated row months
before real coverage starts) are dropped automatically.

Coverage achieved on the 2026-05-08 run: 48/48 legitimate
delisted-S&P-500 names sourced (100%); 7 false-positive names whose
ticker changed pre-2021 (HRS, JEC, JOYG, KORS, LUK, TSO, WLP) are
documented in
`docs/Measurements/2026-05/missing_csv_closure_2026_05_08.md`.

### DEBUGGING & DIAGNOSTICS
```bash
# The 'debug/' folder contains ad-hoc verification scripts
# Verify Assets API (Alpaca)
python debug/verify_assets_api.py

# Run full system diagnostics
python -m scripts.run_diagnostics
```

### PYTEST QUICK REFERENCE
```bash
# Run all system tests (full regression)
pytest -v

# Run specific subsystem tests
pytest -v tests/test_edge_outputs_extended.py        # Edge output format
pytest -v tests/test_collector_integration.py        # SignalCollector
pytest -v tests/test_alpha_pipeline.py               # AlphaEngine pipeline
pytest -v tests/test_portfolio.py                    # Portfolio accounting
pytest -v tests/test_backtest_controller.py          # Backtest orchestration
pytest -v tests/test_golden_path.py                  # Edge cases (data gaps, crashes)

# Typical Usage:
#   After editing an edge → test_edge_outputs_extended.py
#   After modifying pipeline logic → test_alpha_pipeline.py
#   Before committing code → pytest -v
```

### UTILITY & CLEANUP
```bash
# Backup and start fresh backtest
python -m scripts.run_backtest --fresh

# Clean generated files
rm -rf data/trade_logs/*
rm -rf data/research/*
rm -rf data/governor/*
```

### OBSERVABILITY (WS-J cross-cutting)
```bash
# One-time edge-graveyard tagging migration. Idempotent — running
# twice produces the same on-disk state. Tags failed/marked-failed
# canonical edges with structured `failure_reason` per project memory.
python -m scripts.migrate_edge_graveyard_tags
python -m scripts.migrate_edge_graveyard_tags --dry-run
python -m scripts.migrate_edge_graveyard_tags \
    --registry-path data/governor/edges.yml

# Read decision diary entries (from a quick Python snippet — no
# dedicated CLI yet because the diary is small enough to grep):
python -c "from core.observability import read_entries; \
    [print(e) for e in read_entries()]"
```

---

### DEPRECATED COMMANDS
> These commands reference modules or paths that no longer exist or have been replaced. Kept for historical reference.

```bash
# V1 Dashboard (replaced by dashboard_v2)
python -m cockpit.dashboard --live

# continuous_validation (replaced by run_healthcheck)
python -m scripts.continuous_validation
python -m scripts.continuous_validation --once
python -m scripts.continuous_validation --interval 30
python -m scripts.continuous_validation --no-tests
python -m scripts.continuous_validation --debug

# DuckDB datastore (never implemented)
python -m datastore.inspect --path data/trading.duckdb
python -m datastore.migrate --mirror-csv true
duckdb data/trading.duckdb "SELECT run_id, mode, started_at FROM runs;"

# edge_db_viewer (use run_evaluator instead)
python -m research.edge_db_viewer

# performance_summary module (metrics computed inline by backtest)
python -m analytics.performance_summary

# Parquet files are binary (use Python to read, not cat)
cat data/research/edge_results.parquet

# File logging (system uses print(), no log files)
tail -f data/logs/latest.log
grep ALPHA data/logs/latest.log | tail
```

### DYNAMIC OPTIMIZATION FIXTURE DEMO (T-139, 2026-06-10)

```bash
# Frozen-fixture comparison: naive rounding vs Carver dynamic
# optimization vs unrounded ideal at $5K / $50K. Engineering
# verification only — no backtest, no N_trials consumed. Fixture data
# embedded (scripts/t139_fixture_data.py, pinned 2024-05-10).
python -m scripts.demo_dynamic_optimization_t139
```

The optimizer itself is Engine C: `dynamic_optimization_enabled` in
`config/portfolio_settings.json` (default false — OFF is canon-inert,
see docs/Audit/dynamic_optimization_t139_2026_06_10.md).

### AFTER-TAX REPORTING DEMO (T-141, 2026-06-10)

```bash
# Pre-tax vs after-tax (taxable-IL) Sharpe/CAGR with block-bootstrap CIs
# on a backtest's trade logs (default: flat data/trade_logs pair).
# Report-only — no backtest, no N_trials. Rates from
# backtest_settings.json `tax_drag_model` (federal + IL 4.95%).
python -m scripts.demo_after_tax_t141 [run_dir]
```

Every performance summary now carries `after_tax_sharpe_taxable`,
`sharpe_roth`, `tax_drag_pct` + `after_tax_detail` (report-only; the
canon-changing `tax_drag_model.enabled` flag is separate). Router
validation: `core/account_router.py::validate_routing` against
`config/account_routing.json`. See
docs/Audit/after_tax_gate_t141_2026_06_10.md.

### CRISIS-REPLAY ANALYSIS — T-118b locked gate (T-143, 2026-06-10)

```bash
# The pre-registered T-118b second-read, push-button (director runs
# post-relaunch on REAL artifacts; fixture-only until then):
python -m scripts.crisis_replay_t118b \
    --on <overlay_on.csv> --off <overlay_off.csv> \
    --spx <sp500_tr.csv> --primary-config
# artifacts: date,equity,gross_notional per bar. Verdict line shows
# every locked criterion's value. Non-primary configs: drop
# --primary-config -> SENSITIVITY (no gate; addendum v2 §4).
```

Locked criteria + episode month-pinning live in the module's constants
block (transcribed from docs/Audit/t118b_preregistration_2026_06_10.md).
NOTE: no on-disk S&P 500 TR series covers 1999→present — see
docs/Audit/crisis_replay_harness_t143_2026_06_10.md (episode-list
findings + the ^SP500TR caching decision).

### AUCTION-EXECUTION CONVENTION + COST ACCOUNTING (T-146, 2026-06-10)

```bash
# Execution-cost accounting: current realistic-model convention vs
# OPG/CLS auction fills, per-fill ADV-bucketed, on an existing book.
# Accounting only — no backtest, no N_trials.
python -m scripts.demo_auction_execution_t146 [run_dir]
```

Backtest convention flag: `auction_execution` in backtest_settings.json
(`off`|`moo`|`moc`|`moo_moc`, default off = legacy bitwise) +
`auction_safety_bps` (1.0). moo = conservative timing-identical choice.
See docs/Audit/auction_execution_t146_2026_06_10.md (incl. the live-side
OPG/CLS design one-pager: 9:28 ET cutoff, dyn-opt whole-share coupling,
router/account batching).

### POSITION-BUFFERING COUPLED ACCOUNTING (T-148, 2026-06-11)

```bash
# Turnover/cost/tax-drag deltas between an OFF and ON run pair
# (accounting only — no performance comparison, zero N_trials):
python -m scripts.demo_position_buffering_t148 <off_run_dir> <on_run_dir>
```

Flag: `position_buffering_enabled` (false) + `buffer_fraction` (0.10)
in portfolio_settings.json. Composes AFTER dynamic optimization.
POSITION-level trade-to-edge — NOT T-098's refuted weight band; see
docs/Audit/position_buffering_t148_2026_06_11.md (incl. the
pre-registered enable-A/B spec).

### SAFE-F / CAR25 SIZING HEALTH (T-151, 2026-06-11)

```bash
# Bandy sizing-health metrics per account (Roth=pre-tax vs taxable-IL
# via the T-141 tax model). Reporting only — zero N_trials.
python -m scripts.demo_safef_car25_t151 [run_dir]
```

Every performance summary now carries `safe_f` + `car25_pct` +
`safef_detail` (seed-pinned block-MC; defaults are documented
reconstructions, configurable via optional `safef_car25` block in
backtest_settings.json). Record-dependent — sizing decisions use the
deep-window number. See docs/Audit/safef_car25_t151_2026_06_11.md.

### DIVERGENCE-MONITOR CALIBRATION (T-152, 2026-06-11)

```bash
# False-alarm grids -> operating points -> injected-divergence power
# (seed-deterministic; zero N_trials). Re-run on deeper run dirs to
# refresh the calibration.
python -m scripts.calibrate_divergence_monitors_t152 [run_dir]
```

Operating points (calibrated 2026-06-11, ~<=1 FA/yr): CUSUM-mean
k=1.0/h=5.0, CUSUM-var k=2.0/h=12.0, PH delta=0.05/lambda=20 (sigma
units — research params were mis-scaled ~80x; documented). Summaries
carry `divergence_alarms` + `divergence_detail` (shadow only). See
docs/Audit/divergence_monitors_t152_2026_06_11.md.

### COORDINATION — outbox watcher (T-114, 2026-06-06)

Run in the DIRECTOR worktree to get notified when any agent finishes a task
(automates the manual "X done, see outbox" relay). Read-only; globs
`agent_*_outbox.md` so it scales to agent C / specialists with no change.

```bash
python scripts/watch_coordination.py                 # poll forever (10s)
python scripts/watch_coordination.py --interval 5    # custom interval
python scripts/watch_coordination.py --once          # one snapshot + exit
```

Protocol: agents no longer write `docs/State/TASK_LEDGER.md` (conflict source);
the director writes the ledger row at merge time from the agent's outbox
"Proposed TASK_LEDGER row" section. See `docs/Coordination/PROTOCOL.md`.

### REPRODUCIBLE IMAGE BUILDS + SUBSTRATE PIN (T-127/T-131/T-133, 2026-06-10)

The ONLY sanctioned way to build the cloud backtest image. Raw
`docker build -f Dockerfile.backtest .` is DEPRECATED — it bakes live
worktree state (host __pycache__ → stale-bytecode execution, untracked
junk, uncommitted files); the T-125→T-127 saga came from exactly that.

```bash
# Build from a COMMIT (git archive; worktree-independent), verify the
# data substrate against the committed manifest, label provenance:
scripts/build_backtest_image.sh HEAD                      # → :dev + :sha-<short>
scripts/build_backtest_image.sh <ref> archondex-backtest:<tag>

# Substrate manifest (pins data/processed + data/raw + governor ANCHORS;
# the 9 live mutable governor files are excluded — T-131 policy):
python3 scripts/gen_substrate_manifest.py verify           # check current state
python3 scripts/gen_substrate_manifest.py generate         # after a DELIBERATE change; commit in same PR

# Anchor update (deliberate, director-coordinated, 3 steps):
python -m scripts.run_isolated --save-anchor               # writes + chmods anchors 0o444
python3 scripts/gen_substrate_manifest.py generate         # re-pin
# commit the manifest in the SAME PR with the reason for the seed change
```

Anchors are SHARED across worktrees by symlink (setup_agent_worktree.sh
does this for new worktrees; the 4 existing ones were converted
2026-06-10). Cloud `--job-timeout`: 26-yr cells = 21600 (6h), never
14400 — see CLOUD_USAGE.md timeout table.

### PAPER CLOUD LOOP — build / deploy / fire the sleeve (T-186 / T-238)

The daily paper loop is a SEPARATE lean image (`Dockerfile.paper`, ~600MB,
no data substrate) built by its OWN sanctioned wrapper (git-archive
provenance, same discipline as the backtest image). ECR repo is shared
(`archondex-backtest`); paper images are tagged `paper-sha-<short>`.

```bash
# 1. ECR login (once per shell; needs the docker daemon up)
aws ecr get-login-password --profile archondex --region us-east-1 \
  | docker login --username AWS --password-stdin \
      407539788432.dkr.ecr.us-east-1.amazonaws.com

# 2. Build+push the lean paper image from a COMMIT (never the worktree)
REF=407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:paper-sha-$(git rev-parse --short HEAD)
scripts/build_paper_image.sh HEAD "$REF"

# 3. Register the jobdef rev + (re-)point the schedule DISABLED. --no-secret
#    reuses the existing Secrets Manager creds; NEVER pass --alert-email here
#    (the director owns the SNS subscription). The jobdef env carries
#    ARCHONDEX_PAPER_STRATEGY=trend_sleeve + ARCHONDEX_SLEEVE_NOTIONAL_CAP.
scripts/deploy_paper_cloud_trigger.sh --image "$REF" --no-secret --schedule-disabled

# 4. Fire ONE armed run manually (in-window: OPG submit window is 7pm-9:28am
#    ET; fills at the next 9:30 open). The jobdef env already selects the
#    sleeve + $10k cap, so no container-overrides are needed.
aws batch submit-job --profile archondex --region us-east-1 \
  --job-name paper-armed-sleeve-t238 --job-queue archondex-backtest-queue \
  --job-definition archondex-paper-cloud-day

# 5. ENABLING the schedule is USER-ONLY and gated (armed-run-clean AND T-255):
#    aws scheduler update-schedule --name archondex-paper-daily --state ENABLED ...
#    Do NOT run this from an agent — it is the go-live trigger.
```

Verify a run: `aws batch describe-jobs --jobs <id>` (SUCCEEDED = canonical
exit 0), CloudWatch log group `/aws/batch/job` stream prefix `paper-cloud`,
and the durable state under `s3://archondex-results-407539788432/paper_state/`.

### FLEET DRIFT CHECK — run BEFORE any provisioning touch (T-329b)

```bash
# READ-ONLY. Diffs the checked-in templates against the LIVE AWS resources.
# Exit 1 = drift. Non-negotiable pre-flight: a live hand-fix that was never
# written back is silently REVERTED by the next provisioner re-run, while
# every log line still reads success. Already caught three: a live
# archondex/anthropic-api grant the template didn't render (a blind PUT =
# fleet-wide LLM blackout), missing DLQ + fast-fail on the schedules, and
# each new S3 state prefix needing an explicit job-role grant.
python scripts/diff_live_paper_infra.py
```

### PRE-IGNITION FLAT-CHECK — verify a paper account from the BROKER (T-329b)

The CLI user deliberately has NO `secretsmanager:GetSecretValue`, so an
account's true state cannot be read from the laptop. Ask the container
instead: a read-only Batch job on that account's jobdef, with the command
overridden so the paper entrypoint never runs. Never trust dashboard memory
that an account is flat — check it ([NN-FIRST-ARTIFACT]).

```bash
cat > /tmp/flatcheck.py <<'PY'
import json
from paper_trader.paper_client import AlpacaPaperClient
c = AlpacaPaperClient(); a = c.get_account(); pos = c.list_positions()
TERM = {"filled","canceled","expired","rejected","done_for_day","replaced"}
op = [o for o in c.list_orders() if str(o.get("status","")).lower() not in TERM]
print("FLATCHECK " + json.dumps({"status": a.get("status"), "equity": a.get("equity"),
      "n_positions": len(pos), "n_open_orders": len(op), "positions": pos}, default=str))
print("FLAT=%s" % (not pos and not op))
PY
python -c "import json;print(json.dumps({'command':['python','-c',open('/tmp/flatcheck.py').read()]}))" > /tmp/ov.json
aws batch submit-job --profile archondex --region us-east-1 \
  --job-name preignition-flatcheck --job-queue archondex-backtest-queue \
  --job-definition archondex-paper-<acct> --container-overrides file:///tmp/ov.json
# then read the log stream from describe-jobs → container.logStreamName
```

### ACCOUNT 3 — the stage-2 AI trader (`--strategy llm_analyst`, T-329/T-329b)

```bash
# Provision (jobdef + DISABLED schedule + alarms). Run the drift check FIRST.
python scripts/provision_paper_fleet.py --image "$REF"
```

Jobdef env specific to this account: `ARCHONDEX_PAPER_STRATEGY=llm_analyst`,
`ARCHONDEX_PAPER_STATE_PREFIX=paper_state_ai_trader` (a NEW prefix — the
inherited btc-sleeve prefix stays intact as the archive),
`ARCHONDEX_NOTES_SOURCE_PREFIX=paper_state` (where it cross-reads account-1's
analyst notes read-only), `ARCHONDEX_TRADING_KILL_SWITCH=0`,
`ARCHONDEX_SLEEVE_NOTIONAL_CAP=10000` (the analyst stream's sub-budget).
Secret is the INHERITED `archondex/alpaca-paper-btc-sleeve` — aliased in
config, never renamed (a rename touches IAM ARNs and the jobdef binding).

**Tripping the trading kill switch** — three surfaces, by latency. Any one
halts; a halt STOPS NEW ORDERS and NEVER liquidates:

```bash
# 1. FASTEST — one S3 object, effective next run, no deploy at all:
echo "halted <who/why/when>" | aws s3 cp - \
  s3://archondex-results-407539788432/paper_state_ai_trader/data/state/TRADING_HALT \
  --profile archondex
#    clear it by deleting that object.
# 2. jobdef env ARCHONDEX_TRADING_KILL_SWITCH=1 (a jobdef revision, no rebuild)
# 3. config/llm_settings.json → llm.trading_kill_switch (needs an image rev).
#    NB llm.kill_switch (the SPEND switch) also halts trading: the constructor
#    consumes YESTERDAY's note, so halting spend alone still trades one more day.
```

Read the day's stream verdict from the heartbeat's `streams.llm_analyst`
block (`note_as_of`, `n_orders`, `reject_reason`, `halted`, `notes_pull_ok`)
— "0 orders" alone never says which of the four reasons applied.

## Alt-data daily archivers (Info-Layer program, Lane 2.1 Phase A — 2026-07-07)

```bash
# Run both snapshot archivers once (idempotent; dedup on (snap_date,id) /
# (date, archive_vintage)). Kalshi+Polymarket+GPR/EPU/GDELT, then FINRA
# regsho/FTD/short-interest/NAAIM/margin. Output: data/macro_data/alt/*.parquet
.venv/bin/python scripts/archive_altdata_t136.py
.venv/bin/python scripts/archive_positioning_t136.py

# The scheduled path: launchd runs the wrapper daily at 17:30 CT (= 18:30 ET).
# Wrapper logs to data/macro_data/alt/logs/archive_YYYY-MM-DD.log and prints
# ALTDATA_ARCHIVER_FAILED on any non-zero exit (grep target).
bash scripts/run_altdata_archivers.sh          # manual invocation of the wrapper

# launchd job management (plist source-of-truth: scripts/launchd/)
cp scripts/launchd/com.archondex.altdata-archive.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.archondex.altdata-archive.plist
launchctl kickstart gui/$(id -u)/com.archondex.altdata-archive   # fire now (test)
launchctl list | grep archondex                                  # confirm loaded
# Retire (when Lane 2.1 Phase B cloud-pulse integration supersedes, ~2wk overlap):
launchctl bootout gui/$(id -u)/com.archondex.altdata-archive
```

## Alt-data daily archivers (Info-Layer program, Lane 2.1 Phase A — 2026-07-07)

```bash
# Run both snapshot archivers once (idempotent; dedup on (snap_date,id) /
# (date, archive_vintage)). Kalshi+Polymarket+GPR/EPU/GDELT, then FINRA
# regsho/FTD/short-interest/NAAIM/margin. Output: data/macro_data/alt/*.parquet
.venv/bin/python scripts/archive_altdata_t136.py
.venv/bin/python scripts/archive_positioning_t136.py

# The scheduled path: launchd runs the wrapper daily at 17:30 CT (= 18:30 ET).
# Wrapper logs to data/macro_data/alt/logs/archive_YYYY-MM-DD.log and prints
# ALTDATA_ARCHIVER_FAILED on any non-zero exit (grep target).
bash scripts/run_altdata_archivers.sh          # manual invocation of the wrapper

# launchd job management (plist source-of-truth: scripts/launchd/)
cp scripts/launchd/com.archondex.altdata-archive.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.archondex.altdata-archive.plist
launchctl kickstart gui/$(id -u)/com.archondex.altdata-archive   # fire now (test)
launchctl list | grep archondex                                  # confirm loaded
# Retire (when Lane 2.1 Phase B cloud-pulse integration supersedes, ~2wk overlap):
launchctl bootout gui/$(id -u)/com.archondex.altdata-archive
```

### T-295 rate-path population — the gated Yahoo retry (transient, self-unloads)

```bash
# WHY a scheduler: Yahoo (the only free ZQ source) globally 429-throttles its
# unauthenticated chart API — confirmed from 3 IPs (dev/AWS/hotspot) 2026-07-08.
# The ban resets on contact, so patience is the fix and each attempt must spend
# AT MOST ONE Yahoo contact. The wrapper's gated protocol enforces that:
#   FRED health-gate (non-Yahoo) -> ONE no-retry Yahoo probe -> populate ONLY on 200.
# On success it writes the 2 parquets, uploads them to s3://…/altdata/…, prints
# the meeting-prob confirmation, and touches data/macro_data/alt/logs/
# t295_population.DONE (idempotent: a later firing sees DONE and no-ops).
bash scripts/run_t295_gated_population.sh        # manual invocation of the wrapper

# launchd job management (plist source-of-truth: scripts/launchd/). Fires TWICE
# daily — 22:30 + 06:30 CT — until it succeeds once.
cp scripts/launchd/com.archondex.t295-population.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.archondex.t295-population.plist
launchctl list | grep t295-population            # confirm loaded
tail -30 data/macro_data/alt/logs/t295_launchd_stdout.log   # read the last firing
# UNLOAD once T-295 closes (parquets exist + "T-295 done" ledger call made):
launchctl bootout gui/$(id -u)/com.archondex.t295-population
rm -f ~/Library/LaunchAgents/com.archondex.t295-population.plist
```

### Launchd path hardening (2026-07-08, fresh-eyes finding #1)

```bash
# Freshness verifier — did TODAY's snapshot rows actually land? (The T-136
# archivers exit 0 unconditionally; this is the real failure gate.)
# rc 0 = all 24/7 sources fresh; 1 = zero-row source(s); 2 = verifier broke.
.venv/bin/python scripts/verify_altdata_snapshot.py

# The wrapper runs it automatically after both archivers and alarms on ANY
# failure: SNS topic archondex-paper-alerts (needs sns:Publish for the
# claude-code-cli IAM user — pending grant) + local macOS notification.
# NOTE: the launchd job is PERMANENT (canonical ~EOD 18:30 ET local series);
# the cloud pulse's 09:45 ET capture is a separate pre-open series on S3.
# Do NOT retire one into the other (program-doc amendment 2026-07-08).
```
