# Engine D: Discovery & Evolution
**Purpose:** Autonomously discover new trading edges, evolve existing ones through genetic algorithms, and validate all candidates through a rigorous multi-gate pipeline before promoting them to active status.

**Architectural Role:** Engine D is an **offline engine** — it operates on historical data during the post-backtest discovery cycle and does not participate in the live trading loop. It writes candidate edge specs to `edges.yml` for Governance (F) to manage. Triggered via `python -m scripts.run_backtest --discover`.

**Key Design Decisions:**
- *Two-Stage ML:* LightGBM screens features by importance, then a shallow decision tree extracts interpretable rules. This avoids the opacity of pure ML while leveraging its feature selection power.
- *GA Evolution:* CompositeEdge genomes are evolved via tournament selection, crossover, and mutation. The GA vocabulary spans 7 gene types, allowing cross-category combinations (e.g., "RSI < 30 AND overnight gap down AND gold rising").
- *Vol-Adjusted Labels:* Target thresholds scale by rolling ATR%, preventing regime-dependent labeling (5% in TSLA vs. 5% in KO).
- *4-Gate Validation:* No candidate reaches `active` without passing backtest, PBO robustness, WFO degradation, and Monte Carlo significance tests.
- *Inter-Market Features:* Gracefully degrade when TLT/GLD are not in the backtest universe.

**Pipeline Flow (per `--discover` cycle):**
1. **REGIME** — Get regime context from Engine E (passed to feature engineering)
2. **FEATURES** — Compute 40+ features across 7 categories per ticker, then cross-sectional ranks
3. **HUNT** — LightGBM screening -> decision tree rule extraction -> RuleBasedEdge candidates
4. **EVOLVE** — Template mutations + GA cycle (select -> crossover -> mutate -> save population)
5. **VALIDATE** — 4-gate pipeline: backtest (Sharpe>0) -> PBO (50 paths) -> WFO -> significance (p<0.05)
6. **PROMOTE** — Winners to `active` in `edges.yml`; validation Sharpe stored for GA fitness

<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->

## Auto-Generated Code Reference

*This section is automatically built by `scripts/sync_docs.py`. Do not edit manually.*

### `attribution.py`
**Module Docstring:** engines/engine_d_discovery/attribution.py
- **Function `treatment_effect_returns()`**: Daily attribution stream = with_candidate - baseline.
- **Function `per_edge_realized_pnl_returns()`**: Daily realized PnL for one edge, normalized to per-day return.
- **Function `stream_sharpe()`**: Annualized Sharpe of a per-day return stream.
- **Function `attribution_diagnostics()`**: Summary stats for the attribution stream — for audit logging.

### `bayesian_optimizer.py`
**Module Docstring:** engines/engine_d_discovery/bayesian_optimizer.py
- **Class `BayesianOptimizer`**: Bayesian-optimization-guided candidate search for Engine D.
  - `def __init__()`
  - `def warm_start()`: Register `(gene, score)` pairs from a prior cycle's
  - `def suggest_candidates()`: Suggest N candidate gene-specs ready for downstream gauntlet
  - `def n_observations()`: How many points has the surrogate seen (warm-start + tells).
- **Function `cumulative_gate_margin()`**: Compute the spec's Option-B objective: sum of (metric - threshold)/

### `discovery.py`
- **Class `DiscoveryEngine`**: Engine D (Discovery): The Evolutionary Lab.
  - `def __init__()`
  - `def clear_gate1_signal_cache()`: Drop all cached baseline-edge wrappers. Call between cycles
  - `def hunt()`: Phase 2 Core: The "Hunter".
  - `def generate_candidates()`: Produce candidate specs via two paths:
  - `def get_queued_candidates()`: Retrieve candidates from registry that are ready for validation.
  - `def save_candidates()`: Append candidates to the active edges.yml (or a separate staging registry).
  - `def validate_candidate()`: Production-equivalent multi-gate validation (architectural-fix v2).

### `discovery_logger.py`
**Module Docstring:** Discovery activity logger.
- **Class `DiscoveryLogger`**: Append-only JSONL logger for discovery cycle events.
  - `def __init__()`
  - `def log_hunt()`
  - `def log_ga_generation()`
  - `def log_validation()`
  - `def log_cycle_summary()`

### `feature_engineering.py`
- **Class `FeatureEngineer`**: Tier 1 Research Feature Factory.
  - `def __init__()`
  - `def compute_all_features()`: Master factory method. Computes all feature blocks and returns a unified DataFrame.
  - `def compute_cross_sectional_features()`: Compute cross-sectional rank features across the universe.

### `gate1_signal_cache.py`
**Module Docstring:** engines/engine_d_discovery/gate1_signal_cache.py
- **Class `CachedEdgeWrapper`**: Memoizing wrapper around an EdgeBase-shaped object.
  - `def __init__()`
  - `def edge_id()`
  - `def hits()`
  - `def misses()`
  - `def compute_signals()`: Delegated + memoized version of the wrapped edge's
  - `def cache_stats()`
- **Class `Gate1SignalCache`**: Per-cycle registry of `CachedEdgeWrapper`s keyed by edge_id.
  - `def __init__()`
  - `def wrap_edges()`: Return wrapped versions of the supplied edges.
  - `def clear()`
  - `def stats()`

### `genetic_algorithm.py`
**Module Docstring:** Genetic Algorithm engine for CompositeEdge genome evolution.
- **Class `GeneticAlgorithm`**: Manages a persistent population of CompositeEdge genomes and evolves
  - `def __init__()`
  - `def load_population()`: Load population from YAML. Returns True if loaded, False if empty/new.
  - `def save_population()`: Persist population to YAML.
  - `def seed_from_registry()`: Seed Gen 0 from existing composite edges in the registry, then
  - `def tournament_select()`: Tournament selection: pick k random individuals, return the one
  - `def crossover()`: Single-point crossover: take a prefix of genes from parent_a and
  - `def mutate()`: Mutate a genome with several possible operations:
  - `def evolve()`: Run one generation of evolution.
  - `def get_unevaluated()`: Return genomes that don't have fitness scores yet.
  - `def to_candidate_specs()`: Convert genomes to EdgeRegistry-compatible candidate specs

### `robustness.py`
- **Class `RobustnessTester`**: Tier 1 Research Tool: Robustness & Overfitting Check.
  - `def generate_bootstrap_paths()`: Generate N synthetic price histories using Circular Block Bootstrap.
  - `def generate_cross_section_bootstrap()`: Synchronized cross-section block bootstrap.
  - `def bootstrap_returns_stream()`: Circular-block bootstrap of a 1-D returns stream.
  - `def calculate_pbo()`: Probability of Backtest Overfitting (PBO).
  - `def calculate_pbo_returns_stream()`: PBO survival on a per-day attribution stream (post-fix gauntlet).

### `significance.py`
**Module Docstring:** Statistical significance testing for edge discovery validation.
- **Function `monte_carlo_permutation_test()`**: Test whether the strategy's Sharpe ratio is statistically significant
- **Function `apply_bh_fdr()`**: Benjamini-Hochberg false-discovery-rate correction for a batch of p-values.
- **Function `minimum_track_record_length()`**: Minimum Track Record Length (MinTRL) per Bailey & Lopez de Prado (2012).

### `sleeve_gauntlet.py`
**Module Docstring:** Sleeve-level gauntlet — different fitness criteria from the core gauntlet.
- **Class `SleeveCriteria`**: Pre-committed success and kill thresholds for a sleeve.
- **Class `SleeveMetrics`**: Computed metrics for one sleeve's return stream.
  - `def to_dict()`
- **Class `SleeveVerdict`**: Outcome of evaluating a SleeveMetrics against SleeveCriteria.
  - `def to_dict()`
- **Function `upside_capture()`**: Strategy return / benchmark return on days when benchmark > 0.
- **Function `per_trade_stats()`**: Hit rate, avg winner / loser, ≥3x bet flag.
- **Function `compute_sleeve_metrics()`**: Compute the sleeve gauntlet metric pack from a sleeve's daily
- **Function `evaluate_sleeve_gauntlet()`**: Bucket a SleeveMetrics into SUCCESS / PARTIAL / FAIL / INDETERMINATE.

### `synthetic_market.py`
- **Class `SyntheticMarketGenerator`**: Generates realistic synthetic market data using Regime-Switching Geometric Brownian Motion.
  - `def __init__()`
  - `def generate_price_history()`: Generates OHLCV Data.
  - `def generate_fundamentals()`: Generates consistent P/E, P/S data for the simulated price.

### `tree_scanner.py`
- **Class `DecisionTreeScanner`**: Tier 2 Research: The Hunter.
  - `def __init__()`
  - `def generate_targets()`: Generate multi-class targets based on future returns.
  - `def scan()`: Two-stage scanning pipeline:

### `wfo.py`
- **Class `WalkForwardOptimizer`**: Tier 1 Research Feature: Walk-Forward Optimization (WFO).
  - `def __init__()`
  - `def run_optimization()`: optimize parameters over rolling windows.
