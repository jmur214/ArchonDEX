# Data Manager Engine
**Purpose:** Single point of truth for fetching, caching, and serving financial data to the entire system.
**Architectural Role:** Abstracts Alpaca, YFinance, and FRED APIs. Caches aggressively to speed up backtests.

**Known Issues & Quirks:**
- *The Monolith Problem:* `DataManager.py` is an intertwined 700+ line class. It manually scrapes fundamentals, normalizes them, computes trailing-twelve-month (TTM) figures, and handles generic OHLCV storage simultaneously.
- *Duplication:* Dual-writes everything to both `.csv` and `.parquet`.

## Modules

| File | Purpose |
|------|---------|
| `data_manager.py` | OHLCV + fundamentals fetch/cache (Alpaca primary, yfinance fallback). |
| `macro_data.py` | FRED macro series fetch/cache. Cache at `data/macro/<SERIES_ID>.parquet`. Env: `FRED_API_KEY`. See "Macro data pipeline" below. |
| `earnings_data.py` | Finnhub earnings calendar + EPS/revenue surprise fetch/cache. Cache at `data/earnings/<SYMBOL>_calendar.parquet`. Env: `FINNHUB_API_KEY`. See "Earnings data pipeline" below. |
| `universe.py` | Survivorship-bias-aware S&P 500 historical membership loader (Wikipedia scrape). Cache at `data/universe/sp500_membership.parquet`. No API key required. See "Universe membership pipeline" below. |
| `universe_resolver.py` | Backtest-time universe resolution. Bridges the membership loader and the orchestration layer's static-list contract via `resolve_universe(...)`. Cache-only, never hits the network. |
| `fundamentals/loader.py` | Fundamentals loader helpers. |

## Macro data pipeline (`macro_data.py`)

Self-contained FRED ingestion layer. **Not yet wired into any engine** —
this is plumbing for upcoming work on macro features, regime
classification, and yield-curve / credit-spread edges (see
`docs/Sessions/2026-04-24_strategic_pivot.md` item #4).

**Public API:**
- `MacroDataManager(api_key=None, cache_dir="data/macro")` — pulls
  `FRED_API_KEY` from `.env` if `api_key` is None. With no key the
  manager runs in cache-only mode.
- `mgr.fetch_series(series_id, start=..., end=..., force=False, max_age_hours=24)`
  → `DataFrame[date → value]`. Cache-first: returns parquet cache if
  fresher than `max_age_hours`. On network failure falls back to
  cache; raises `MacroDataError` only when there is no cache to fall
  back to.
- `mgr.fetch_panel(series_ids=None, ffill=True)` → wide DataFrame
  joining all curated series, forward-filled to a daily index by
  default.
- `mgr.cache_status()` → DataFrame describing the on-disk cache.

**Curated registry** (`MACRO_SERIES`): 18 series across yield curve,
credit, policy, inflation, labor, growth, FX, vol, and liquidity. See
the docstring in `macro_data.py` for the full list and rationale.

**Derived features:** `yoy_change`, `credit_quality_slope` (HY-IG OAS),
`real_fed_funds` (DFF − T10YIE). More-bespoke transforms belong in
the consuming edge / regime detector, not here.

**Tests:** `tests/test_macro_data.py` — 23 offline tests (HTTP layer
mocked) plus one live integration test gated behind `FRED_API_KEY`.

## Earnings data pipeline (`earnings_data.py`)

Self-contained Finnhub ingestion layer for earnings calendar +
surprise data. **Not yet wired into any engine** — this is plumbing
for the upcoming PEAD (post-earnings announcement drift) edge work
called out in `docs/Sessions/2026-04-24_strategic_pivot.md`
as the strongest single-factor alpha in the academic literature.

**Public API:**
- `EarningsDataManager(api_key=None, cache_dir="data/earnings", rate_limit_s=1.1)`
  — pulls `FINNHUB_API_KEY` from `.env` if `api_key` is None. With
  no key the manager runs in cache-only mode. The 1.1s default
  rate-limit keeps us under Finnhub's 60 req/min free-tier ceiling;
  set to 0 in tests.
- `mgr.fetch_calendar(symbol, start="2020-01-01", end=None, force=False, max_age_hours=24)`
  → `DataFrame[announcement_date → event row]`. Cache-first:
  returns the parquet cache if fresher than `max_age_hours`. On
  network failure falls back to cache; raises `EarningsDataError`
  only when there is no cache to fall back to.
- `mgr.fetch_universe(symbols, ...)` → long-form events DataFrame
  concatenating all symbols, sorted by announcement date. Per-symbol
  failures are skipped with a warning; the run only raises if every
  symbol fails.
- `mgr.cache_status()` → DataFrame describing every parquet on disk
  (universe is open-ended, so this walks the cache dir rather than
  iterating a registry like the FRED variant).

**Schema** (`EVENT_COLUMNS`): index `announcement_date`, columns
`symbol`, `eps_actual`, `eps_estimate`, `eps_surprise`,
`eps_surprise_pct`, `revenue_actual`, `revenue_estimate`,
`revenue_surprise`, `revenue_surprise_pct`, `hour` (`bmo`/`amc`),
`quarter` (`Int64`), `year` (`Int64`). Surprise percentages use
`(actual − estimate) / |estimate|` so misses on negative-consensus
loss companies get the right sign. NaN whenever estimate is zero
or either side is missing.

**Helpers:** `surprise_pct(actual, estimate)` exposed for ad-hoc
use. More-bespoke transforms (rolling z-scores, drift windows,
event-aligned price panels) belong in the consuming edge, not here.

**Tests:** `tests/test_earnings_data.py` — 29 offline tests (HTTP
layer mocked) plus one live integration test gated behind
`FINNHUB_API_KEY`.

## Universe membership pipeline (`universe.py`)

Self-contained Wikipedia scraper for S&P 500 historical membership.
**Wired into ModeController via `universe_resolver.resolve_universe`
(2026-05-09).** The wiring is opt-in: default behavior remains the
legacy static ticker list in `config/backtest_settings.json`. Setting
`use_historical_universe: true` in that config (or passing
`--use-historical-universe` to `scripts/run_multi_year`) swaps in the
survivorship-aware annual-anchor union of constituents over the backtest
window. No API key required.

**Public API:**
- `SP500MembershipLoader(cache_dir="data/universe")` — fetch + cache
  the membership table.
- `loader.fetch_membership(force=False, max_age_hours=168)` →
  long-format `DataFrame[ticker, name, sector, included_from,
  included_until]`. Cache-first: returns the parquet cache if fresher
  than `max_age_hours` (default 7 days; membership changes are rare,
  no need to thrash Wikipedia). On network failure falls back to
  cache; raises `UniverseError` only when there is no cache to fall
  back to.
- `loader.current_constituents()` → tickers whose `included_until` is
  NaT (the open spell).
- `loader.historical_constituents(as_of)` → survivorship-bias-aware
  snapshot of which tickers were in the index on a given date.
- `loader.cache_status()` → dict describing the on-disk cache.

**Pure helpers** (no I/O — useful in tests or for consumers that want
to manipulate membership frames):
- `parse_membership_html(html)` — Wikipedia HTML → membership frame.
- `current_tickers(df)` / `active_at(df, as_of)` — query a frame
  directly.
- `normalize_ticker(t)` — strip footnotes, uppercase, etc.

**Schema** (`MEMBERSHIP_COLUMNS`): `ticker` (str), `name` (object),
`sector` (object), `included_from` (datetime64, NaT if pre-changelog),
`included_until` (datetime64, NaT if currently active). One row per
(ticker, spell-of-membership); a ticker that's been added and removed
multiple times has multiple rows.

**Limitations:** the Wikipedia "changes" table only goes back ~30
years and is volunteer-maintained. For tickers currently in the index
with no entry in the change log, `included_from` falls back to the
"Date added" column of the current table; if that's also missing, it's
NaT.

**CLI companion:** `scripts/fetch_universe.py` — explicit
user-driven tool that uses the membership list to populate
`data/processed/` via the existing `DataManager` pipeline. See
`docs/Core/execution_manual.md` for usage.

**Tests:** `tests/test_universe.py` — 40 offline tests (HTTP layer
mocked, parser exercised against fixture HTML) plus one live
integration test gated behind `UNIVERSE_LIVE_TEST=1`.

<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->

## Auto-Generated Code Reference

*This section is automatically built by `scripts/sync_docs.py`. Do not edit manually.*

### `convention.py`
**Module Docstring:** The UNIVERSAL convention label (option (a), the user's cutover ruling, 2026-10-22).
- **Function `derive_drip_witness_text()`**: THE recipe of `config/drip_cache_witness_repin1.json`, as text (its exact bytes): from re-pin #1's
- **Function `load_drip_witness()`**: The frozen witness's per-name hashes, or None when the file is absent (then NOTHING is labelled
- **Function `is_drip_witnessed()`**: None when the file under `cache_dir` IS the drip the witness pinned (csv always; parquet where
- **Function `era_tr_records_present()`**: The cache is post-(a′): at least one pinned write record labels a pre-seam span era_tr.
- **Function `label_of()`**: One string per name: `exact_tr` (whole), or `drip<2018-01-02|exact_tr` (pre-seam, seam date,
- **Function `cache_first_bar_frames()`**: One-row frames at each file's FIRST bar, read from the cache's own `<T>_1d.csv` files — the
- **Function `substrate_convention_record()`**: The `substrate_convention` census block over `run_names` (the panel; every name in the merge
- **Function `pre_seam_spans()`**: Per name, for the guard's `pre_seam_drip_gap` class: `{"seam_date", "n_pre_seam_kept",

### `coverage.py`
**Module Docstring:** The stale/holed-files guard (adopted 2026-10-15; docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md).
- **Function `load_data_gaps()`**: The declared data gaps, validated. An absent file means no declarations; a malformed one
- **Function `majority_calendar()`**: Trading days in [start, end]: dates on which at least `share` of the names ACTIVE that day
- **Function `formation_coverage()`**: Rows FORMED on each formation date over EVERY member on that date — never over the names that
- **Function `stale_files_record()`**: The `stale_files` census block. Per name: first/last bar, the REQUIRED end (the earlier of

### `data_manager.py`
- **Class `CacheUnreadableError`**: A cache file could not be read. It was QUARANTINED (renamed), never deleted.
  - `def __init__()`
- **Class `FundamentalsFixtureRefused`**: The explicit fundamentals test fixture was named where it may not be read.
- **Class `DataManager`**: No docstring
  - `def __init__()`
  - `def prefetch_fundamentals()`: Fetch fundamentals for every ticker that has NO cached file. Call during data loading.
  - `def fetch_historical_fundamentals()`: Reconstructs DEEP historical fundamental time-series.
  - `def fetch_fundamentals()`: Fetch fundamental data (P/E, EPS, etc.) for a ticker.
  - `def cache_path()`
  - `def parquet_cache_path()`
  - `def load_cached()`: The cached bars, with DECLARED exclusions withheld (item d, 2026-10-15).
  - `def save_cache()`
  - `def load_or_fetch()`: Try to load from Parquet cache, then CSV, then use fetch_func if provided.
  - `def ensure_data()`
- **Function `is_info_enabled()`**: No docstring
- **Function `data_feed_summary()`**: What the network fed this process: counts by source and the yfinance-fed tickers.
- **Function `reset_feed_log()`**: Forget the recorded fetches (tests, or a fresh run in a long-lived process).
- **Function `fundamentals_miss_summary()`**: Every fundamentals cache miss this process: sorted ticker lists by outcome, and the
- **Function `ticker_fundamentals_blind()`**: The per-ticker fundamentals blind count for a set of LOADED edges. `consumers` are the
- **Function `reset_fundamentals_log()`**: Forget the recorded misses (tests, or a fresh run in a long-lived process).
- **Function `fundamentals_fixture_path()`**: The explicitly named fixture file, or None when no fixture is named (the default: the

### `earnings_data.py`
**Module Docstring:** yfinance-backed earnings calendar + surprise data pipeline.
- **Class `EarningsDataError`**: Raised for non-recoverable failures in the earnings pipeline.
- **Class `EarningsEvent`**: Lightweight value type for a single earnings announcement.
- **Class `EarningsDataManager`**: Fetch + cache yfinance earnings calendar entries per ticker.
  - `def __init__()`
  - `def load_cached()`: Read a cached calendar without touching the network.
  - `def fetch_calendar()`: Fetch one ticker's earnings calendar, with cache.
  - `def fetch_universe()`: Fetch a list of tickers and concatenate into a long events frame.
  - `def cache_status()`: Return a DataFrame describing the on-disk cache state.
- **Function `surprise_pct()`**: Standard surprise-magnitude transform.

### `era_tr.py`
**Module Docstring:** OPTION (a′) — the ERA-AWARE pre-seam convention (`era_tr`): the ONE shared implementation.
- **Class `EraTrRefusal`**: The (a′) build will not produce this file: a load-bearing check failed (fail closed).
- **Class `NameReference`**: What the yfinance reference says about one name's Stooq series.
  - `def covered()`: Bars whose year has a valid same-security reference — plus (amendment A3) a stub of at
- **Class `BuildResult`**: No docstring
- **Function `global_missed()`**: Boolean mask: the date lies in a universe-wide missed era (fallback rule).
- **Function `global_block()`**: No docstring
- **Function `align_reference()`**: Stooq close + yfinance (adj_close, close) on their common, strictly positive dates.
- **Function `year_identity()`**: Per calendar year: is the reference the SAME security as the Stooq series?
- **Function `transient_offsets()`**: Bars that sit inside a TRANSIENT level offset of Stooq against the reference (amendment A1).
- **Function `probe_exdates()`**: The fraction of each dividend Stooq MISSED, measured against the reference (amendment A1:
- **Function `label_exdates()`**: missed / captured per ex-date. MEASURED where confident; otherwise the confident neighbours
- **Function `missed_log_factor()`**: Back-adjustment for the missed dividends: logM(t) = Σ_{e > t} log(1 − D_e/P_e,prev), on the
- **Function `empty_labels()`**: The labelled-ex-date frame of a name with no usable reference (no ex-date labelled).
- **Function `analyse_reference()`**: Probe every reference ex-date up to `until` (the seam) and label it.
- **Function `era_runs()`**: Contiguous runs of MISSED ex-dates (the name's measured missed eras), for the record.
- **Function `mask_runs()`**: Contiguous runs of True in `mask`, as [first date, last date] pairs (for the record).
- **Function `raw_stooq_index()`**: Ticker -> path of the raw Stooq daily file under `raw_dir` (`<raw_dir>/*/*/<t>.us.txt`). A
- **Function `read_raw_stooq()`**: No docstring
- **Function `read_yf()`**: Cached yfinance (adj_close, close) and dividends. (None, None) when prices are absent:
- **Function `read_cache_text()`**: A cached CSV as (header, data lines) — text, so post-seam rows can be copied verbatim.
- **Function `read_cache_frame()`**: No docstring
- **Function `frame_from_text()`**: The parquet twin of a written csv: parsed FROM the text (round trip), Date index at
- **Function `recompute_derived()`**: ATR(14) + PrevClose on a Date-column frame — the writer's `with_derived_columns`, the
- **Function `carried_columns()`**: The trailing columns past the cache's eight that the build carries verbatim: none (the
- **Function `check_text_bytes()`**: The write-time byte rule on the cache's eight fields: every post-seam row's Date/OHLCV text
- **Function `build_file()`**: Option (a′) for one merged file. Pure: every input is passed in; nothing is read or written.
- **Function `step_audit()`**: R3 at write time: the pre-seam daily log returns may differ from raw Stooq's ONLY at the
- **Function `splice_audit()`**: The ONE constant at the seam, at write time. The written seam-day log return must be Stooq's
- **Function `carried_text_identical()`**: Every carried column's text is the cache's own, on every row (the build copies it).

### `exclusions.py`
**Module Docstring:** Declared data exclusions: bars the loader WITHHOLDS, by name, with a reason, and records.
- **Class `ExclusionMismatchError`**: A declared exclusion no longer matches the data it was declared for.
- **Function `truncate_declared()`**: STEP (a), on the RAW frame BEFORE normalization: drop the declared-excluded bars and record
- **Function `check_declared()`**: STEP (b), on the SERVED frame, outside any read error handling: fail closed if a bar that
- **Function `withhold_excluded_bars()`**: Both steps on an already-normalized frame (the network-fetch serve point).
- **Function `clip_membership()`**: Apply the declarations to PIT membership intervals (`ticker`, `start`, `end`): an interval
- **Function `withhold_declared_tickers()`**: The ticker kind at a UNIVERSE: remove every declared name and record where it was withheld.
- **Function `lift_verified()`**: The re-pin #2 lift lock: a ticker-kind declaration may be lifted only when the WRITTEN level
- **Function `ticker_exclusions_applied()`**: The census block for the ticker kind: every declared name withheld in this run (at
- **Function `exclusions_applied()`**: The census block: every declaration applied in this run, keyed by its census key.
- **Function `reset_exclusion_log()`**: Start a run's bar and resolution records (membership is applied once per process and kept).

### `insider_data.py`
**Module Docstring:** OpenInsider Form 4 scraping pipeline.
- **Class `InsiderDataError`**: Raised for non-recoverable failures in the insider data pipeline.
- **Class `InsiderTxn`**: Lightweight value type for a single insider transaction.
- **Class `InsiderDataManager`**: Fetch + cache OpenInsider Form 4 transactions per ticker.
  - `def __init__()`
  - `def load_cached()`: Read a cached transactions frame without touching the network.
  - `def fetch_filings()`: Fetch one ticker's insider transactions, with cache.
  - `def fetch_universe()`: Fetch a list of tickers and concatenate into one long frame.
  - `def cache_status()`: Return a DataFrame describing the on-disk cache state.
- **Function `parse_insider_table()`**: Parse an OpenInsider screener HTML response.

### `macro_calendar.py`
**Module Docstring:** Macro event calendar — FOMC decision dates (T-2026-07-07-290, deliverable 3).
- **Function `load_fomc_dates()`**: Sorted FOMC decision dates (normalized to midnight). Cached per path.
- **Function `is_fomc_week()`**: True if `date` falls in the same Mon-Sun week as an FOMC decision date
- **Function `days_to_next_decision()`**: Calendar days from `date` to the NEXT FOMC decision on/after it (0 if

### `macro_data.py`
**Module Docstring:** FRED macro data pipeline.
- **Class `MacroDataError`**: Raised for non-recoverable failures in the macro pipeline.
- **Class `MacroSeries`**: Metadata describing a single FRED series we care about.
- **Class `MacroDataManager`**: Fetch + cache FRED macro series.
  - `def __init__()`
  - `def load_cached()`: Read a cached series without touching the network.
  - `def fetch_series()`: Fetch a single FRED series, with cache.
  - `def fetch_panel()`: Fetch a wide panel of macro series.
  - `def cache_status()`: Return a DataFrame describing the on-disk cache state.
- **Function `list_series()`**: Return the curated series registry, optionally filtered by category.
- **Function `yoy_change()`**: Year-over-year change (default monthly cadence: 12 periods).
- **Function `credit_quality_slope()`**: HY OAS minus IG OAS — widens before risk-off events.
- **Function `real_fed_funds()`**: DFF minus 10y breakeven inflation. Rough real-policy-rate proxy.

### `membership.py`
**Module Docstring:** engines/data_manager/membership.py
- **Function `load_membership()`**: Membership intervals. `end` is NaT for current members.
- **Function `members_on()`**: No docstring
- **Function `in_index()`**: Boolean (date x ticker) membership mask, vectorized over intervals.

### `tr_writer.py`
**Module Docstring:** The TOTAL-RETURN writer for the processed price cache (data/processed/<TICKER>_1d.{csv,parquet}).
- **Class `WriterRefusal`**: The writer will not write: the evidence for a safe replacement is missing.
  - `def __init__()`
- **Class `WriteRecord`**: No docstring
- **Function `covers_span()`**: A whole-file replacement must cover everything the cached file holds.
- **Function `measure_basis()`**: Two-mode measurement (R's C-4). Total-return back-adjustment makes adjusted/unadjusted RISE
- **Function `classify_overlap()`**: The guard's test on an overlap window (R §3.1): the same convention reads ratio 1 at the
- **Function `seam_return_ok()`**: R's C-3 rail: an UNADJUSTED provider after a split matches the pre-split overlap and would
- **Function `with_derived_columns()`**: ATR + PrevClose per project convention (scripts/merge_stooq_alpaca_substrate.py).
- **Function `write_pair_atomically()`**: Both temp files are written first; only then are both swapped in. A failure while writing
- **Function `write_text_pair_atomically()`**: The TEXT-preserving twin of `write_pair_atomically` (option (a′)): the csv is `text` VERBATIM
- **Function `load_level_declarations()`**: The hand-set facts the identity cannot establish: per name, `kind` (`scale_defect` — a level
- **Function `level_identity()`**: The cache's last bar against the level the provider says it SHOULD hold. The cache was
- **Function `substrate_level_declarations()`**: The census block (`level_declarations`): every file in this substrate whose CURRENT version
- **Function `load_convention_declarations()`**: `config/convention_declarations.json`: `seams` (per name: `seam_date`, `pre_seam`,
- **Function `load_merge_meta()`**: The T-082b merge record's `per_ticker` map under this cache, or None when the cache has
- **Function `seam_for()`**: Where this file's seam is, and who says so. A DECLARED seam (classes (iii)/(iv)) wins, and
- **Function `kept_pre_seam_convention()`**: What the KEPT pre-seam bars ARE (option (a′), T-387). `seam_spec`'s `pre_seam` (a declaration,
- **Function `seam_ratio()`**: The provider/cache ratio AT the seam: the first bar on or after the seam both series hold.
- **Function `verify_split_only_cache()`**: The declared check for a SPLIT-ONLY cache (the backfill_t052 trio): the cached tail must
- **Function `verify_mixed_convention()`**: The declared check for a MIXED cache (AMCR: total return, then two missed ex-dates): the
- **Function `full_refetch()`**: Replace `<ticker>_1d` with a total-return re-fetch from THE universe provider — or refuse.
- **Function `era_tr_rewrite()`**: Rewrite the PRE-seam span of `<ticker>_1d` under `cache_dir` from the T-082b drip to `era_tr`
- **Function `yfinance_provider()`**: yfinance: auto_adjust=True -> total return; False -> split-adjusted Close.
- **Function `yfinance_actions()`**: yfinance's corporate-actions record (dividends and split factors), tz-naive.

### `universe.py`
**Module Docstring:** Survivorship-bias-aware S&P 500 historical membership pipeline.
- **Class `UniverseError`**: Raised for non-recoverable failures in the universe pipeline.
- **Class `SP500MembershipLoader`**: Fetch + cache the Wikipedia S&P 500 membership history.
  - `def __init__()`
  - `def load_cached()`: Read the cached membership parquet without touching the network.
  - `def fetch_membership()`: Fetch the S&P 500 membership history, with cache.
  - `def current_constituents()`: Return the list of tickers currently in the index.
  - `def historical_constituents()`: Tickers active on a given date — the survivorship-bias-aware view.
  - `def cache_status()`: Return a dict describing the on-disk cache state.
- **Function `parse_membership_html()`**: Convert raw Wikipedia HTML into the canonical membership frame.
- **Function `current_tickers()`**: Tickers whose most recent spell is still open (included_until NaT).
- **Function `active_at()`**: Tickers active on ``as_of``.
- **Function `annual_anchor_dates()`**: Return one anchor per calendar year in ``[start, end]``, on Jan 1.
- **Function `union_active_over_window()`**: Union of ``active_at`` results over a list of anchor dates.
- **Function `normalize_ticker()`**: Trim, uppercase, and strip Wikipedia footnote markers like '[1]'.

### `universe_resolver.py`
**Module Docstring:** engines/data_manager/universe_resolver.py
- **Function `resolve_universe()`**: The single entry point (see `_resolve_universe_unfiltered` for the parameters).
- **Function `discover_cached_tickers()`**: Return the set of tickers with a USABLE cached price CSV under

### `yahoo_symbols.py`
**Module Docstring:** ONE Yahoo symbol table for the processed cache's tickers (director ruling, 2026-10-15).
- **Function `yahoo_symbol()`**: (the Yahoo symbol to fetch, the kind of mapping: None, SHARE_CLASS or RENAME).
