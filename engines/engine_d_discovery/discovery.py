from __future__ import annotations
import os
import random
import stat
import yaml
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Type

# Import Template Interface from Engine A
from engines.engine_a_alpha.edge_template import EdgeTemplate
from engines.engine_a_alpha.edges.rsi_bounce import RSIBounceEdge
from engines.engine_a_alpha.edges.fundamental_value import ValueTrapEdge
from engines.engine_a_alpha.edges.fundamental_ratio import FundamentalRatioEdge
from engines.engine_a_alpha.edges.rule_based_edge import RuleBasedEdge
from engines.engine_a_alpha.edges.seasonality_edge import SeasonalityEdge
from engines.engine_a_alpha.edges.gap_edge import GapEdge
from engines.engine_a_alpha.edges.volume_anomaly_edge import VolumeAnomalyEdge
from engines.engine_a_alpha.edges.panic_edge import PanicEdge
from engines.engine_a_alpha.edges.herding_edge import HerdingEdge
from engines.engine_a_alpha.edges.earnings_vol_edge import EarningsVolEdge

# Research Modules
from core.census import assert_census
from engines.engine_d_discovery import gate_verdicts as gv
from engines.engine_d_discovery.gate1_signal_cache import (
    CandidateSignalCensus,
    DiscoveryCandidateCensusError,
)
from engines.engine_d_discovery.tree_scanner import DecisionTreeScanner
from engines.engine_d_discovery.feature_engineering import FeatureEngineer


class RegistryUnreadableError(RuntimeError):
    """edges.yml exists but cannot be read as an edge registry. Discovery REFUSES — it never
    rewrites a registry it could not read (that is how a parse failure wiped every edge)."""


# T-2026-05-12-052 targeted seed list — one Gen-0 single-gene long
# candidate per new regime-ensemble feature. Without this, the
# 20%-foundry × 4/35 sampling probability gives each specific feature
# <2% expected coverage across 5-random-seed runs. Targeted seeds
# guarantee at least one validation pass per new feature in cycle 0.
_T052_TARGET_FEATURE_IDS: Tuple[str, ...] = (
    "vix_term_structure_slope",
    "hy_oas_change_20d",
    "anfci_z_60d",
    "faber_multi_asset_trend_above_10mo_sma",
)


class RegimeContextUnavailable(RuntimeError):
    """RR-6a fixup: the Discovery cycle REFUSES when it cannot establish regime context.

    The cycle's regime step used to swallow every exception — and a missing SPY — and run
    the hunt with `regime_meta=None`: a context-free hunt is a different experiment under
    the same label. There is no labelled 'no regime context' mode, so the cycle refuses."""


def candidate_census_block(cand_id: str, cand_census, n_trades: int) -> dict:
    """The Gate-1 candidate's census block, routed through the SAME `assert_census` the
    measurement path uses. It carries the SAME provenance fields the measurement path's census
    writes — a census provenance field exists only when BOTH producers write it (Agent R found
    the gap twice: data_feed, then data_exclusions):
      * data_feed (ruling C-2): a candidate validated on yfinance-fed data fails closed here;
      * data_exclusions (item d): a candidate validated where a declared exclusion was applied
        (e.g. dal_pre2007_excluded) carries the record — the exclusion itself is applied to the
        candidate's data at load either way; this is the record of it."""
    from engines.data_manager.data_manager import data_feed_summary
    block = {
        # A candidate census, declared: the gate does not ask a Gate-1 candidate for the BACKTEST
        # run-shape counters (n_resolved, regime_total_bars) — and treats an UNdeclared census as a
        # backtest, which must carry them (no silent zero, 2026-10-15).
        "census_kind": "candidate",
        "edges_blind": ([cand_id] if cand_census.nonzero_calls == 0 else []),
        "edges_errored": ({cand_id: {"crash_bars": cand_census.errors}}
                          if cand_census.errors else {}),
        "n_trades": n_trades,
        "data_feed": data_feed_summary(),
    }
    try:
        from engines.data_manager.exclusions import exclusions_applied
        block["data_exclusions"] = exclusions_applied()
    except Exception as e:   # recorded, never omitted
        block["data_exclusions"] = {"error": repr(e)}
    return block


class DiscoveryEngine:
    """
    Engine D (Discovery): The Evolutionary Lab.
    
    Responsibilities:
    1. Scan for valid EdgeTemplates.
    2. Generate N candidate configurations (Mutations).
    3. Save candidates to registry for validation.
    """
    
    def __init__(
        self,
        registry_path: str = "data/governor/edges.yml",
        processed_data_dir: str = "data/processed",
    ):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._processed_data_dir = Path(processed_data_dir)
        self.templates: List[Type[EdgeTemplate]] = [
            RSIBounceEdge,
            ValueTrapEdge,
            FundamentalRatioEdge,
            SeasonalityEdge,
            GapEdge,
            VolumeAnomalyEdge,
            PanicEdge,
            HerdingEdge,
            EarningsVolEdge,
        ]

        # Gate 1 signal-collector cache (T-2026-05-11-023). Persists
        # across validate_candidate calls within a single Discovery
        # cycle so the baseline ensemble's per-(edge, bar) signals are
        # computed ONCE and reused across all N candidates. The cache
        # naturally clears when the DiscoveryEngine instance is rebuilt
        # at the next cycle. Initialized to None here so tests that
        # bypass __init__ via `DiscoveryEngine.__new__(DiscoveryEngine)`
        # don't trip an AttributeError; `_get_gate1_signal_cache()`
        # lazy-initializes on first access.
        self._gate1_signal_cache = None  # type: ignore[assignment]

        # T-2026-06-17-183: fair-foundry Gen-0 seed fraction. The legacy GA
        # population is technical-heavy, so the first --discover cycle off it
        # under-tests the Foundry vocabulary (1/32 foundry genes, T-179). This
        # fraction of the FRESH Gen-0 population is allocated to single-gene
        # foundry genomes with feature_ids drawn uniformly at random across the
        # whole tier-A/B registry (NO hand-picking — the GA + the UNCHANGED
        # gauntlet/DSR gates decide what survives). Default 0.0 preserves prior
        # behavior; read from config/discovery_settings.json. Seed diversity
        # only — gates are untouched. Pre-registered (see the T-183 audit).
        self.foundry_seed_fraction: float = 0.0
        try:
            import json as _json
            _cfg_path = (
                Path(__file__).resolve().parents[2]
                / "config" / "discovery_settings.json"
            )
            if _cfg_path.exists():
                _cfg = _json.loads(_cfg_path.read_text())
                self.foundry_seed_fraction = float(
                    _cfg.get("foundry_seed_fraction", 0.0) or 0.0
                )
        except Exception:
            self.foundry_seed_fraction = 0.0

    def _get_gate1_signal_cache(self):
        """Return the Gate 1 signal cache, lazy-initializing on first
        access. Defensive against tests that bypass __init__ via
        `DiscoveryEngine.__new__(DiscoveryEngine)`."""
        if getattr(self, "_gate1_signal_cache", None) is None:
            from engines.engine_d_discovery.gate1_signal_cache import Gate1SignalCache
            self._gate1_signal_cache = Gate1SignalCache()
        return self._gate1_signal_cache

    def clear_gate1_signal_cache(self) -> None:
        """Drop all cached baseline-edge wrappers. Call between cycles
        or whenever universe/window/active-edge set changes."""
        if getattr(self, "_gate1_signal_cache", None) is not None:
            self._gate1_signal_cache.clear()

    def hunt(
        self,
        data_map: Dict[str, pd.DataFrame],
        regime_meta: Optional[Dict[str, Any]] = None,
        fundamentals_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Phase 2 Core: The "Hunter".
        1. Calculate Features for all data (including cross-sectional, calendar,
           microstructure, inter-market, and regime context).
        2. Run TreeScanner to find patterns.
        3. Convert Rules -> RuleBasedEdge Candidates.
        """
        logger = logging.getLogger("DISCOVERY")

        # 1. Feature Prep
        fe = FeatureEngineer()
        scanner = DecisionTreeScanner(max_depth=4, min_prob=0.55)

        # Extract benchmark / cross-asset DataFrames for inter-market features
        spy_df = data_map.get("SPY")
        tlt_df = data_map.get("TLT")
        gld_df = data_map.get("GLD")

        all_dfs = []
        for ticker, df in data_map.items():
            if df.empty:
                continue

            # Get fundamentals for this ticker (if available)
            fund_df = pd.DataFrame()
            if fundamentals_map and ticker in fundamentals_map:
                fund_df = fundamentals_map[ticker]

            # Compute all features (technical + calendar + microstructure + inter-market + regime).
            # T-054: pass `ticker=` so the Foundry pass is exercised (not
            # silently skipped). Pre-T-054, the omission made every
            # foundry_feature gene (~20% of GA emissions per T-022) a
            # dead-letter — referenced columns were never computed, Gate 1
            # always failed. See docs/Audit/production_hunt_ticker_wiring_2026_05_12.md.
            f_df = fe.compute_all_features(
                df, fund_df,
                spy_df=spy_df, tlt_df=tlt_df, gld_df=gld_df,
                regime_meta=regime_meta,
                ticker=ticker,
            )

            # Add Targets
            t_df = scanner.generate_targets(f_df)
            t_df["ticker"] = ticker

            all_dfs.append(t_df)

        if not all_dfs:
            return []

        big_data = pd.concat(all_dfs).reset_index(drop=True)

        # Cross-sectional features (rank across universe per date)
        big_data = FeatureEngineer.compute_cross_sectional_features(big_data, ticker_col="ticker")

        logger.info(f"Hunting on {len(big_data)} rows of data, {len(big_data.columns)} features...")
        
        # 2. Scan
        rules = scanner.scan(big_data, target_col="Target")
        
        # 3. Convert to Candidates
        candidates = []
        
        for r in rules:
            # Hash rule string to get ID
            import hashlib
            rule_hash = hashlib.md5(r["rule_string"].encode()).hexdigest()[:8]
            cand_id = f"hunter_{rule_hash}"
            
            spec = {
                "edge_id": cand_id,
                "module": RuleBasedEdge.__module__,
                "class": RuleBasedEdge.__name__,
                "category": "discovered_rule",
                "params": {
                    "rule_string": r["rule_string"],
                    "target_class": r["target_class"],
                    "probability": r["probability"],
                    "description": f"Target {r['target_name']} ({r['probability']:.1%})"
                },
                "status": "candidate",
                "version": "1.0.0-auto",
                "origin": "tree_scanner"
            }
            candidates.append(spec)
            
        return candidates

    def generate_candidates(self, n_mutations: int = 5) -> List[Dict[str, Any]]:
        """
        Produce candidate specs via two paths:
        1. Standard template mutation (random hyperparameter sampling).
        2. Genetic algorithm evolution of CompositeEdge genomes
           (selection, crossover, mutation across generations).
        """
        candidates = []

        # 1. Standard Template Mutation
        for template in self.templates:
            if template.__name__ == "CompositeEdge":
                continue  # Handled by GA below

            base_id = getattr(template, "EDGE_ID", "unknown_edge")

            for i in range(n_mutations):
                params = template.sample_params()

                suffix = "".join(random.choices("abcdef0123456789", k=4))
                candidate_id = f"{base_id}_mut_{suffix}"

                spec = {
                    "edge_id": candidate_id,
                    "module": template.__module__,
                    "class": template.__name__,
                    "category": getattr(template, "EDGE_CATEGORY", "experimental"),
                    "params": params,
                    "status": "candidate",
                    "version": "1.0.0-mut",
                    "origin": "discovery_engine",
                }
                candidates.append(spec)

        # 2. Composite candidate search — GA or Bayesian opt per config flag.
        # T-028 (2026-05-11): the candidate-search strategy is now
        # selectable. Default is `use_bayesian_opt=False` (GA, the
        # pre-T-028 behavior). Setting True routes to BayesianOptimizer
        # which uses skopt's GP + EI acquisition over a flat per-gene
        # encoding. Backwards-compat: flag-OFF preserves bit-identical
        # GA behavior; the surrogate model never instantiates when off.
        search_candidates = self._run_search(n_mutations)
        candidates.extend(search_candidates)

        return candidates

    def _run_search(self, n_mutations: int) -> List[Dict[str, Any]]:
        """Dispatch to GA or Bayesian-opt candidate generation per config
        flag. T-028 addition; default flag is OFF so this is a no-op
        wrapper around `_run_ga_evolution` for backwards compatibility.

        Config source: reads `use_bayesian_opt` from `self.cfg` if
        present; otherwise from `config/discovery_settings.json` if
        readable; otherwise defaults to False.
        """
        use_bayesian = False
        if hasattr(self, "cfg") and isinstance(self.cfg, dict):
            use_bayesian = bool(self.cfg.get("use_bayesian_opt", False))
        else:
            try:
                import json
                from pathlib import Path
                cfg_path = (
                    Path(__file__).resolve().parents[2]
                    / "config" / "discovery_settings.json"
                )
                if cfg_path.exists():
                    cfg = json.loads(cfg_path.read_text())
                    use_bayesian = bool(cfg.get("use_bayesian_opt", False))
            except Exception:
                use_bayesian = False

        if not use_bayesian:
            return self._run_ga_evolution(n_mutations)

        # Bayesian opt path — lazy-import skopt so the flag-OFF case
        # doesn't pay the import cost.
        from engines.engine_d_discovery.bayesian_optimizer import (
            BayesianOptimizer,
        )
        opt = BayesianOptimizer(random_state=None)  # uses PYTHONHASHSEED
        # Warm-start from existing ga_population.yml fitness_cache if
        # present (matches spec section 5).
        try:
            from engines.engine_d_discovery.genetic_algorithm import (
                GeneticAlgorithm,
            )
            ga = GeneticAlgorithm(gene_factory=self._create_random_gene)
            if ga.load_population():
                entries: List[Tuple[Dict[str, Any], float]] = []
                for genome in ga.population:
                    genes = genome.get("genes", [])
                    if not genes:
                        continue
                    score = float(ga.fitness_cache.get(
                        genome.get("edge_id", ""), 0.0
                    ))
                    # T-028a single-gene per candidate; use first gene
                    entries.append((genes[0], score))
                if entries:
                    opt.warm_start(entries)
        except Exception as e:
            print(f"[BAYES] warm_start skipped: {e}")

        return opt.suggest_candidates(n_mutations)

    def _run_ga_evolution(self, n_random_seed: int = 5) -> List[Dict[str, Any]]:
        """
        Run one generation of the genetic algorithm for CompositeEdge genomes.
        On first run (no population), seeds with random genomes.
        On subsequent runs, evolves from the persisted population.
        """
        from engines.engine_d_discovery.genetic_algorithm import GeneticAlgorithm

        ga_pop_path = str(self.registry_path.parent / "ga_population.yml")
        ga = GeneticAlgorithm(
            population_path=ga_pop_path,
            population_size=max(20, n_random_seed * 4),
            gene_factory=self._create_random_gene,
        )

        if ga.load_population():
            # Subsequent run: evolve from persisted population
            # Get fitness for evaluated genomes from the registry
            fitnesses = self._load_fitness_from_registry()
            ga.fitness_cache.update(fitnesses)

            # Evolve to next generation
            ga.evolve(fitnesses)
        else:
            # First run: seed with random genomes
            # Try to seed from existing composite edges in registry
            existing = self.get_queued_candidates(status="active")
            existing += self.get_queued_candidates(status="candidate")
            ga.seed_from_registry(existing)

            # T-2026-05-12-052: targeted seeding for the 4-signal regime
            # ensemble. Guarantees at least one Gen-0 candidate per new
            # regime-Foundry feature (otherwise the 20%-foundry × N-genes
            # × N-features Bernoulli sampling has <2% chance of touching
            # each specific new feature in a 5-random-seed run). Each
            # target gets a single-gene long-direction genome.
            for fid in _T052_TARGET_FEATURE_IDS:
                suffix = "".join(random.choices("abcdef0123456789", k=6))
                gene = {
                    "type": "foundry_feature",
                    "feature_id": fid,
                    "operator": "greater",
                    "threshold": 0.0,
                }
                ga.population.append({
                    "edge_id": f"composite_t052_seed_{fid}_{suffix}",
                    "genes": [gene],
                    "direction": "long",
                })

            # T-2026-06-17-183: FAIR foundry representation in the Gen-0 seed so
            # the first honest --discover cycle actually TESTS the Foundry
            # vocabulary instead of near-rerunning the legacy technical edges.
            # Allocate `foundry_seed_fraction` of the population to single-gene
            # foundry genomes whose feature_ids are drawn UNIFORMLY AT RANDOM
            # across the whole tier-A/B registry (no hand-picking — the GA + the
            # UNCHANGED gauntlet/DSR gates decide which survive). Each is a
            # long-direction single-gene genome (the GA combines/mutates them
            # over generations). Population SIZE is unchanged, so the per-cycle
            # candidate count (and thus honest-N pressure) is ~neutral — only
            # WHAT is explored shifts. Deterministic (seeded random).
            n_foundry_target = int(round(self.foundry_seed_fraction * ga.population_size))
            n_foundry_added = 0
            while (n_foundry_added < n_foundry_target
                   and len(ga.population) < ga.population_size):
                fgene = self._make_random_foundry_gene()
                if fgene is None:
                    break  # registry unavailable — skip fair-foundry seeding
                suffix = "".join(random.choices("abcdef0123456789", k=6))
                ga.population.append({
                    "edge_id": f"composite_foundryseed_{suffix}",
                    "genes": [fgene],
                    "direction": "long",
                })
                n_foundry_added += 1

            # Fill remaining with random genomes
            while len(ga.population) < ga.population_size:
                n_genes = random.randint(1, 3)
                genes = [self._create_random_gene() for _ in range(n_genes)]

                suffix = "".join(random.choices("abcdef0123456789", k=6))
                direction = "long"
                rand = random.random()
                if rand < 0.10:
                    direction = "short"
                elif rand < 0.20:
                    direction = "market_neutral"

                genome = {
                    "edge_id": f"composite_gen0_{suffix}",
                    "genes": genes,
                    "direction": direction,
                }
                ga.population.append(genome)

            ga.generation = 0

        ga.save_population()

        # Return unevaluated genomes as candidate specs for validation
        unevaluated = ga.get_unevaluated()
        return ga.to_candidate_specs(unevaluated)

    def _load_fitness_from_registry(self) -> Dict[str, float]:
        """
        Extract fitness scores from the registry for composite edges.
        Uses the 'sharpe' field stored during validation.
        """
        fitnesses = {}
        # R's F2: this read was `except Exception: pass` — an unreadable registry seeded the GA
        # with NO fitness history, silently. It reads through the fail-closed reader now.
        all_edges = self._read_registry()["edges"]

        for edge in all_edges:
            eid = edge.get("edge_id", "")
            if "composite" not in eid and edge.get("origin") != "genetic_algorithm":
                continue
            params = edge.get("params", {})
            # Prefer composite fitness_score (OOS-weighted) over in-sample validation_sharpe.
            fitness_val = params.get("fitness_score", None)
            if fitness_val is None:
                fitness_val = params.get("validation_sharpe", None)
            if fitness_val is not None:
                fitnesses[eid] = float(fitness_val)
            # Active edges without stored fitness get a baseline so they're
            # not invisible to tournament selection.
            if edge.get("status") == "active" and eid not in fitnesses:
                fitnesses[eid] = 0.5

        return fitnesses

    def _make_random_foundry_gene(self) -> Optional[Dict[str, Any]]:
        """Build ONE random foundry-feature gene: feature_id drawn UNIFORMLY AT
        RANDOM from the live tier-A/B Foundry registry (NO hand-picking), with
        the T-022 operator/threshold distribution (70% percentile / 30%
        absolute). Returns None when the registry is unavailable in this context
        (caller falls through).

        Factored out of _create_random_gene (T-179/183) so the fair-foundry
        Gen-0 seeding reuses the SAME generator. The RNG call sequence is
        IDENTICAL to the prior inline foundry branch, so the gene factory stays
        bit-identical (verified: seed-0 2000-gene md5 unchanged).
        """
        try:
            from core.feature_foundry import get_feature_registry
            import core.feature_foundry.features  # noqa: F401  trigger register
            reg = get_feature_registry()
            eligible_ids = [
                f.feature_id for f in reg._features.values()
                if f.tier in ("A", "B")
            ]
        except Exception:
            eligible_ids = []
        if not eligible_ids:
            return None
        feature_id = random.choice(sorted(eligible_ids))
        if random.random() < 0.70:
            # Percentile operator path (cross-sectional ranking)
            operator = random.choice(["top_percentile", "bottom_percentile"])
            threshold = (
                random.choice([80, 90, 95])
                if operator == "top_percentile"
                else random.choice([5, 10, 20])
            )
        else:
            # Absolute-comparison path (return-like / score-like features)
            operator = random.choice(["greater", "less"])
            threshold = 0.0
        return {
            "type": "foundry_feature",
            "feature_id": feature_id,
            "operator": operator,
            "threshold": threshold,
        }

    def _create_random_gene(self) -> Dict[str, Any]:
        """
        Creates a random Gene (Condition) using expanded vocabulary.

        Categories (weighted selection — post-T-022 distribution):
        - Regime (5%): Bull/bear/vol context
        - Calendar (10%): Day-of-week, month, quarter-end, opex proximity
        - Microstructure (10%): Overnight gap, close location, intraday range
        - Intermarket (10%): SPY/TLT/GLD returns, SPY-TLT correlation
        - Macro (10%): Yield curve (T10Y2Y), VIX level, unemployment delta
        - Earnings (5%): EPS surprise % look-back
        - Behavioral (5%): Panic score, herding breadth
        - Fundamental (10%): PE, PS, PB, PFCF, Debt
        - **Foundry feature (20%, NEW T-022)**: any feature_id in
          `core.feature_foundry.get_feature_registry()`. Includes post-T-006
          (mom_12_1, mom_6_1, vol_regime_5_60, ma_cross_50_200, dist_52w_high,
          drawdown_60d, etc.) + post-T-014 (fomc_drift, pre_holiday,
          sell_in_may_halloween, january_effect, triple_witching_premium,
          tax_loss_season). Most numerically-valued features support
          top/bottom percentile + greater/less operators.
        - Technical (15%, reduced from 35%): RSI, Volatility, SMA Distance,
          SMA Cross, Donchian, Pivot, Momentum ROC, Residual Momentum, Vol Diff

        T-022 (2026-05-11): added `foundry_feature` bucket so Discovery's GA
        can sample the post-T-006 + post-T-014 Foundry vocabulary. Pre-T-022,
        Discovery emitted only rsi_bounce_v1 mutations on substrate-honest
        substrate (T-021 finding) regardless of how many features the Foundry
        accumulated. Determinism preserved: same `random` source, same call
        order on existing buckets up to `roll < 0.65`.
        """
        roll = random.random()

        # --- Regime (5%) ---
        if roll < 0.05:
            return {
                "type": "regime",
                "is": random.choice(["bull", "bear", "neutral_low_vol"]),
                "operator": "is",
            }

        # --- Calendar (10%) ---
        if roll < 0.15:
            indicator = random.choice([
                "day_of_week_sin", "month_sin",
                "quarter_end_proximity", "opex_proximity",
            ])
            gene = {"type": "calendar", "indicator": indicator, "operator": "less"}
            if indicator == "day_of_week_sin":
                gene["threshold"] = round(random.uniform(-1.0, 1.0), 2)
            elif indicator == "month_sin":
                gene["threshold"] = round(random.uniform(-1.0, 1.0), 2)
            elif indicator == "quarter_end_proximity":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([3, 5, 10])
            elif indicator == "opex_proximity":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([2, 5])
            return gene

        # --- Microstructure (10%) ---
        if roll < 0.25:
            indicator = random.choice([
                "overnight_gap", "close_location", "intraday_range",
            ])
            gene = {"type": "microstructure", "indicator": indicator}
            if indicator == "overnight_gap":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.choice([-0.02, -0.01, 0.01, 0.02]), 3)
            elif indicator == "close_location":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([0.2, 0.3, 0.7, 0.8])
            elif indicator == "intraday_range":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.uniform(0.01, 0.05), 3)
            return gene

        # --- Intermarket (10%) ---
        if roll < 0.35:
            indicator = random.choice([
                "spy_return_5d", "tlt_return_5d", "gld_return_5d", "spy_tlt_corr",
            ])
            gene = {"type": "intermarket", "indicator": indicator}
            if indicator in ("spy_return_5d", "tlt_return_5d", "gld_return_5d"):
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.choice([-0.03, -0.01, 0.0, 0.01, 0.03]), 3)
                gene["window"] = 5
            elif indicator == "spy_tlt_corr":
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.choice([-0.3, -0.1, 0.0, 0.2, 0.4]), 2)
            return gene

        # --- Macro (10%) — economy-wide FRED signals, all with data back to 2000+ ---
        if roll < 0.45:
            indicator = random.choice(["yield_curve", "vix_level", "unemployment_delta"])
            gene = {"type": "macro", "indicator": indicator}
            if indicator == "yield_curve":
                # T10Y2Y: inverted (<0) = stress, steep (>1.5) = expansion
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.choice([-0.5, 0.0, 0.5, 1.0, 1.5]), 2)
            elif indicator == "vix_level":
                # VIX: > 20 = elevated vol, > 30 = panic
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([15, 20, 25, 30])
            elif indicator == "unemployment_delta":
                # UNRATE month-over-month change: positive = worsening labor market
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = round(random.choice([-0.2, -0.1, 0.0, 0.1, 0.2]), 2)
            return gene

        # --- Earnings (5%) — per-ticker EPS surprise look-back ---
        if roll < 0.50:
            gene = {
                "type": "earnings",
                "indicator": "eps_surprise_pct",
                "operator": random.choice(["less", "greater"]),
                "threshold": round(random.choice([-0.10, -0.05, 0.0, 0.05, 0.10, 0.15]), 2),
                "lookback_days": random.choice([30, 60, 90]),
            }
            return gene

        # --- Behavioral (5%) ---
        if roll < 0.55:
            indicator = random.choice(["panic_score", "herding_breadth"])
            gene = {"type": "behavioral", "indicator": indicator}
            if indicator == "panic_score":
                # Panic score is composite: low RSI + high vol + low close_location
                # For now, proxy via RSI threshold (will be expanded later)
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([20, 25, 30])
            elif indicator == "herding_breadth":
                # % of universe moving same direction
                gene["operator"] = random.choice(["less", "greater"])
                gene["threshold"] = random.choice([0.7, 0.8, 0.9])
            return gene

        # --- Standard operator selection for technical/fundamental ---
        op_choices = ["less", "greater"]
        if random.random() < 0.30:
            op_choices += ["top_percentile", "bottom_percentile"]
        operator = random.choice(op_choices)

        # --- Fundamental (10%) ---
        if roll < 0.65:
            metric = random.choice([
                "PE_Ratio", "PS_Ratio", "PB_Ratio", "PFCF_Ratio", "Debt_to_Equity",
            ])
            gene = {"type": "fundamental", "metric": metric, "operator": operator}
            if "percentile" in operator:
                gene["threshold"] = 20 if "bottom" in operator else 80
            else:
                if metric == "PE_Ratio":
                    gene["threshold"] = 15
                elif metric == "PS_Ratio":
                    gene["threshold"] = 2
                else:
                    gene["threshold"] = 1.0
            return gene

        # --- Foundry feature (20%, T-022) — sample any registered Foundry
        # feature (post-T-006 + post-T-014 vocabulary). Heavily favors
        # percentile operators because Foundry feature scales vary widely
        # and percentile ranking is universally meaningful; greater/less
        # operators get a 30% share for the absolute-comparison case
        # (return-like / score-like features). Picks feature_id from the
        # tier-A + tier-B registry — adversarial-tier features are
        # excluded since they're permuted twins, not signal-bearing.
        if roll < 0.85:
            # T-2026-06-17-183: foundry-gene generation factored into
            # _make_random_foundry_gene() (identical RNG sequence — gene-factory
            # determinism preserved, verified bit-identical seed-0 2000-gene md5)
            # so the fair-foundry Gen-0 seeding can reuse the SAME generator.
            foundry_gene = self._make_random_foundry_gene()
            if foundry_gene is not None:
                return foundry_gene
            # Foundry not importable in this context — fall through to the
            # technical bucket so the gene factory always returns a gene.
            roll = 0.95  # forces technical path below

        # --- Technical (15% — remainder) ---
        indicators = [
            "rsi", "volatility", "sma_dist_pct",
            "sma_cross", "donchian_breakout", "pivot_position", "momentum_roc",
            "residual_momentum", "volatility_diff",
        ]
        indicator = random.choice(indicators)
        gene = {"type": "technical", "indicator": indicator, "operator": operator}

        if indicator == "rsi":
            gene["window"] = 14
            gene["threshold"] = random.choice([30, 70]) if "percentile" not in operator else 50
        elif indicator == "volatility":
            gene["window"] = 20
            gene["threshold"] = 0.02
        elif indicator == "sma_dist_pct":
            gene["window"] = 50
            gene["threshold"] = 0.0
        elif indicator == "sma_cross":
            gene["window_fast"] = random.choice([10, 20])
            gene["window_slow"] = random.choice([50, 200])
            gene["threshold"] = 0.0
        elif indicator == "donchian_breakout":
            gene["window"] = 20
            gene["threshold"] = 0.0
        elif indicator == "pivot_position":
            gene["threshold"] = 0.0
        elif indicator == "momentum_roc":
            gene["window"] = random.choice([20, 60, 120])
            gene["threshold"] = 0.0
        elif indicator == "residual_momentum":
            gene["window"] = 60
            gene["threshold"] = 0.0
        elif indicator == "volatility_diff":
            gene["threshold"] = 0.0

        # Adjust threshold for ranking operators
        if "percentile" in operator:
            if operator == "top_percentile":
                gene["threshold"] = random.choice([80, 90, 95])
            else:
                gene["threshold"] = random.choice([5, 10, 20])

        return gene

    def _read_registry(self) -> Dict[str, Any]:
        """The registry as a dict holding an `edges` list. An ABSENT file is an empty
        registry; a file that EXISTS but is unparseable, empty, or not an edge registry
        RAISES `RegistryUnreadableError` — it is never treated as empty.

        Treating it as empty is how `save_candidates` used to wipe edges.yml: a read
        failure fell back to `{"edges": []}` and the write-back then replaced every edge
        in the sole edge-status authority with the handful of candidates being saved."""
        if not self.registry_path.exists():
            return {"edges": []}
        try:
            data = yaml.safe_load(self.registry_path.read_text())
        except yaml.YAMLError as exc:
            raise RegistryUnreadableError(
                f"{self.registry_path} is not parseable YAML ({exc}); refusing — the file is untouched"
            ) from exc
        if isinstance(data, list):              # legacy format: a bare edge list at the root
            data = {"edges": data}
        if not isinstance(data, dict) or not isinstance(data.get("edges"), list):
            raise RegistryUnreadableError(
                f"{self.registry_path} exists but holds no edge registry "
                f"(root {type(data).__name__}{'' if not isinstance(data, dict) else ', keys ' + str(sorted(data))}); "
                f"refusing — the file is untouched")
        return data

    def _write_registry(self, registry: Dict[str, Any]) -> None:
        """ATOMIC write: serialise first, write a sibling temp file, fsync, then rename over
        edges.yml. The old `open("w")` truncated the registry BEFORE yaml.dump ran, so a dump
        error or a crash mid-write left it empty or partial. A failed attempt leaves the temp
        file in place as evidence and never touches edges.yml."""
        text = yaml.dump(registry, sort_keys=False)
        tmp = self.registry_path.with_name(f".{self.registry_path.name}.tmp-{os.getpid()}")
        with tmp.open("w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if self.registry_path.exists():
            # R's note: keep the registry's permissions across the replace (a 600 file was
            # becoming 644 — the temp file's umask default — after a single save).
            os.chmod(tmp, stat.S_IMODE(self.registry_path.stat().st_mode))
        os.replace(tmp, self.registry_path)

    def get_queued_candidates(self, status: str = "candidate") -> List[Dict[str, Any]]:
        """
        Retrieve candidates from registry that are ready for validation.
        An unreadable registry RAISES (it used to return [] — a cycle that silently
        found "nothing queued").
        """
        return [e for e in self._read_registry()["edges"] if e.get("status") == status]

    def save_candidates(self, candidates: List[Dict[str, Any]]) -> None:
        """
        Append candidates to the active edges.yml (or a separate staging registry).
        For now, we append to edges.yml but with status='candidate'.

        Fail-closed: refuses (RegistryUnreadableError) on a registry it cannot read, and
        writes atomically — edges.yml is the sole edge-status authority.
        """
        existing = self._read_registry()

        # Deduplicate by ID
        current_map = {e.get("edge_id"): e for e in existing["edges"]}

        new_count = 0
        update_count = 0
        for cand in candidates:
            cid = cand["edge_id"]
            if cid not in current_map:
                new_count += 1
            else:
                update_count += 1
            current_map[cid] = cand

        # Write back. Other top-level keys, if any, are kept (they used to be dropped).
        self._write_registry({**existing, "edges": list(current_map.values())})

        print(f"[DISCOVERY] Registry saved. New: {new_count}, Updated: {update_count}. Path: {self.registry_path}")

    def _load_universe_b(
        self,
        prod_tickers: set,
        n_sample: int = 50,
        seed: int = 42,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load a random sample of tickers NOT in the production universe.

        Reads directly from `self._processed_data_dir` (CSV fallback only —
        no Parquet, no network). Skips files shorter than 100 rows so that
        thinly-traded or delisted names don't pollute the Gate 5 result.

        Parameters
        ----------
        prod_tickers : set
            The production universe (data_map keys). Universe B = all
            cached tickers minus this set.
        n_sample : int
            Maximum number of universe-B tickers to load. 50 is enough to
            detect universe-specificity while keeping Gate 5 cost under ~50%
            of the production backtest.
        seed : int
            Reproducible random selection within a cycle.

        Returns
        -------
        dict — ticker → DataFrame, possibly empty if no universe-B data found.
        """
        import numpy as np

        all_csvs = {
            f.stem.replace("_1d", "")
            for f in self._processed_data_dir.glob("*_1d.csv")
        }
        candidates = sorted(all_csvs - prod_tickers)

        if not candidates:
            return {}

        rng = np.random.RandomState(seed)
        sampled: List[str] = rng.choice(
            candidates, size=min(n_sample, len(candidates)), replace=False,
        ).tolist()

        dm_b: Dict[str, pd.DataFrame] = {}
        for ticker in sampled:
            csv_path = self._processed_data_dir / f"{ticker}_1d.csv"
            try:
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                if not df.empty and len(df) >= 100:
                    dm_b[ticker] = df
            except Exception:
                pass

        return dm_b

    # ====================================================================
    # Production-equivalent edge ensemble construction
    # ====================================================================

    @staticmethod
    def _build_production_edges(
        *,
        registry_path: Path,
        alpha_config: Optional[Dict[str, Any]],
        exclude_edge_ids: Optional[set] = None,
    ) -> tuple[Dict[str, Any], Dict[str, float]]:
        """Construct the production-equivalent edges_dict + edge_weights.

        Mirrors `ModeController.run_backtest`'s edge-loading + soft-pause
        logic exactly:
          - Loads active + paused specs from `EdgeRegistry.list_tradeable()`.
          - Instantiates each edge from its module + class via importlib.
          - Applies config-driven `edge_weights` from alpha_settings.
          - Applies `PAUSED_WEIGHT_MULTIPLIER = 0.25` and
            `PAUSED_MAX_WEIGHT = 0.5` to status='paused' edges.

        Excludes any edge_id in `exclude_edge_ids` (used to pull the
        candidate out of the baseline before adding it back into the
        with-candidate set).

        Returns
        -------
        (edges, edge_weights) — drop-in inputs for `run_backtest_pure`.
        """
        import importlib

        from engines.engine_a_alpha.edge_registry import EdgeRegistry

        # Load registry from the same path the orchestrator uses
        registry = EdgeRegistry(store_path=str(registry_path))
        excluded = set(exclude_edge_ids or set())

        loaded_edges: Dict[str, Any] = {}
        spec_status_by_id: Dict[str, str] = {}
        for spec in registry.list_tradeable():
            if spec.edge_id in excluded:
                continue
            mod_name = spec.module
            params = (spec.params or {}).copy()
            try:
                if "." in mod_name:
                    mod = importlib.import_module(mod_name)
                else:
                    mod = importlib.import_module(
                        f"engines.engine_a_alpha.edges.{mod_name}"
                    )
                edge_class = None
                for attr in dir(mod):
                    if attr.lower().endswith("edge") and attr not in ("BaseEdge",):
                        val = getattr(mod, attr)
                        if hasattr(val, "__module__") and val.__module__ == mod.__name__:
                            edge_class = val
                            break
                if edge_class is None:
                    for attr in dir(mod):
                        if attr.lower().endswith("edge") and attr not in ("BaseEdge",):
                            edge_class = getattr(mod, attr)
                            break
                if edge_class is None:
                    continue
                try:
                    loaded_edges[spec.edge_id] = edge_class(params=params)
                except TypeError:
                    loaded_edges[spec.edge_id] = edge_class()
                spec_status_by_id[spec.edge_id] = spec.status
            except Exception as e:
                print(f"[VALIDATE] Could not import {mod_name} for {spec.edge_id}: {e}")
                continue

        # Build edge_weights from alpha config (matches mode_controller)
        config_ew = (alpha_config or {}).get("edge_weights", {}) if alpha_config else {}
        edge_weights = {
            eid: float(config_ew.get(eid, 1.0)) for eid in loaded_edges
        }
        PAUSED_WEIGHT_MULTIPLIER = 0.25
        PAUSED_MAX_WEIGHT = 0.5
        for eid in list(edge_weights.keys()):
            if spec_status_by_id.get(eid) == "paused":
                edge_weights[eid] = min(
                    edge_weights[eid] * PAUSED_WEIGHT_MULTIPLIER,
                    PAUSED_MAX_WEIGHT,
                )

        return loaded_edges, edge_weights

    @staticmethod
    def _instantiate_candidate(candidate_spec: Dict[str, Any]) -> Any:
        """Import + instantiate a candidate edge from its spec dict."""
        from importlib import import_module
        mod = import_module(candidate_spec["module"])
        cls_ = getattr(mod, candidate_spec["class"])
        params = candidate_spec.get("params") or {}
        # T-2026-06-16-179: prefer the params-CONSTRUCTOR (the form the
        # production loader at ~discovery.py:835 already uses) so params-derived
        # state (e.g. CompositeEdge.genes) hydrates in __init__ even if a future
        # edge forgets to override set_params. Belt-and-suspenders alongside the
        # CompositeEdge.set_params override (measurement_integrity_audit_2026_06_16).
        # Fall back to construct-then-set_params for any edge whose __init__ does
        # not accept params= (which now ALSO hydrates, via the set_params override).
        try:
            edge = cls_(params=params)
        except TypeError:
            edge = cls_()
            if params:
                edge.set_params(params)
        return edge

    def validate_candidate(
        self,
        candidate_spec: Dict[str, Any],
        data_map: Dict[str, pd.DataFrame],
        significance_threshold: Optional[float] = 0.05,
        exec_params: Optional[Dict[str, Any]] = None,
        diagnostic_log_path: Optional[str] = None,
        cache: Optional[Any] = None,
        gate1_contribution_threshold: float = 0.10,
        gate2_survival_threshold: float = 0.60,
        # RR-6a: `gate3_consistency_threshold` is GONE. It was declared and never compared —
        # a caller passing 0.9 changed nothing, a false statement in the interface. Gate 3 is
        # RECORDED, not a promotion condition; passing the old keyword now raises TypeError.
        # Whether Gate 3 should bind is RR-6b's question, not a default.
        candidate_default_weight: float = 1.0,
        alpha_config: Optional[Dict[str, Any]] = None,
        risk_settings: Optional[Dict[str, Any]] = None,
        portfolio_settings: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        # ---- Substrate-transfer gate (Gate 7) — added 2026-05-09 evening ----
        # If provided, Gate 7 runs the candidate on the historical-S&P 500
        # substrate and fails if its contribution does not survive substrate
        # transfer. Caller is responsible for pre-loading the substrate-B
        # data_map (typically once per Discovery cycle, reused across all
        # candidates). When None, Gate 7 is skipped (default; preserves
        # current behavior). The expected use is `Discovery cycle preloads
        # historical universe via UniverseLoader.historical_constituents
        # then passes the resulting data_map here`. See B1's wire pattern
        # at orchestration/mode_controller.py for the loader integration.
        data_map_substrate_b: Optional[Dict[str, pd.DataFrame]] = None,
        gate7_max_substrate_drift: float = 0.5,
        # ---- Multiple-testing-corrected gate (Gate 8 / DSR) ----
        # When n_trials_for_dsr > 1, the candidate's attribution Sharpe is
        # checked against the expected-max-of-N-trials null. This protects
        # against curve-fitting in cycles where the GA / Bayesian optimizer
        # generates dozens of candidates.
        #
        # T-336(b): the default is now None -> resolve to the PROJECT'S HONEST N via
        # core.measurement.mbl_gate.compute_n_effective() (the refreshed run
        # registry). Previously the default was a hardcoded 1, which SKIPPED Gate 8
        # entirely -- i.e. the multiple-testing correction the gate exists to apply
        # was silently off in every default run, against a 200+-trial history.
        # Pass an explicit int to override (1 restores the legacy no-correction
        # behaviour for a deliberately isolated test).
        n_trials_for_dsr: Optional[int] = None,
        gate8_dsr_threshold: float = 0.95,
        # ---- Gate 1 signal-collector cache (T-2026-05-11-023) ----
        # When True (default), the baseline ensemble's per-(edge, bar)
        # compute_signals outputs are memoized in `self._gate1_signal_cache`
        # so the second-through-Nth candidate's with-candidate backtest
        # skips re-computing the baseline edges. The candidate edge runs
        # fresh on every call. Determinism is preserved by construction
        # (edges are pure functions of (data_map, now, params)).
        #
        # Set False to disable caching; used by determinism cross-check
        # harnesses and by callers that need bitwise-equivalent paths.
        use_signal_cache: bool = True,
        # ---- Gate 0: MBL pre-flight (T-2026-05-24-083) ----
        # Per CLAUDE.md non-negotiable `[NN-MBL]`. The backtest window must satisfy
        # T_years >= 2 * ln(N_effective) / SR_target^2 before any backtest
        # fires. A window too short for the accumulated trial count is
        # statistically incapable of clearing DSR — running the gauntlet
        # on such a window wastes compute and produces measurements that
        # cannot inform deployment.
        #
        # Set `enable_mbl_gate=False` to skip the check (for legacy
        # bitwise-cross-checks against pre-Gate-0 runs only). Production
        # use should keep it True.
        enable_mbl_gate: bool = True,
        mbl_sr_target: float = 1.0,
    ) -> Dict[str, float]:
        """Production-equivalent multi-gate validation (architectural-fix v2).

        Per `project_gauntlet_consolidated_fix_2026_05_01.md`: invokes the
        actual production pipeline twice (baseline = active+paused minus
        candidate; with-candidate = baseline + candidate) instead of running
        a standalone single-edge backtest. The candidate's *attribution
        stream* (with_returns - baseline_returns) is then threaded through
        gates 2-6.

        This fixes the standalone-vs-ensemble geometry mismatch that drove
        Gate 1 to kill 30/30 candidates in the 2026-05-01 diagnostic
        (Audit doc `discovery_diagnostic_2026_05.md`) and was inherited
        by gates 2-6 (Audit doc `gates_2_to_6_audit_2026_05.md`).

        Gates
        -----
        - Gate 1: Sharpe(with_candidate) - Sharpe(baseline) > threshold.
        - Gate 2: PBO survival on bootstrap of attribution stream.
        - Gate 3: WFO consistency = mean rolling-window Sharpe / overall
                  Sharpe of the attribution stream. RECORDED ONLY — no pass
                  criterion, so its verdict is always NOT_EVALUATED.
        - Gate 4: Permutation-null p-value on attribution stream.
        - Gate 5: Universe-B production-equivalent contribution > 0.
        - Gate 6: FF5+Mom regression on attribution stream — t > 2 AND
                  α annualized > 2%.
        - Gate 7: substrate-B transfer; Gate 8: DSR at the honest N.

        Verdicts (RR-6a)
        ----------------
        `result["gate_verdicts"]` holds PASSED | FAILED | NOT_EVALUATED(reason) for
        every gate 0–8 (see `gate_verdicts.py`). `passed_all_gates` is True iff every
        gate in `config/discovery_settings.json` `required_gates` is PASSED; a required
        gate that rendered no verdict REFUSES, and `promotion_refusals` says which and
        why. No gate defaults to a pass, and none that did not run is ever blamed.

        Threshold rationale — see `docs/Measurements/2026-05/gauntlet_architectural_fix_2026_05.md`
        for calibration.

        Caching
        -------
        If `cache` (a `PureBacktestCache` instance) is passed, the baseline
        is fingerprinted and reused across candidates in the same Discovery
        cycle. N candidates → N+1 backtests instead of 2N.
        """
        # RR-2: a None threshold used to mean "skip Gate 4" — and a skipped gate cannot
        # pass, so it silently failed EVERY candidate (production passed None, making
        # T-196's H1 structurally unreachable). Fail LOUD instead: an un-runnable gate is
        # a configuration error to fix, never a verdict to record.
        if significance_threshold is None:
            raise ValueError(
                "validate_candidate: significance_threshold is None — Gate 4 cannot be "
                "evaluated. Pass the configured value (config/discovery_settings.json "
                "`significance_threshold`); None is no longer a silent fail.")
        import numpy as np
        import time as _time
        import math

        from orchestration.run_backtest_pure import (
            run_backtest_pure,
            PureBacktestCache,
        )
        from engines.engine_d_discovery.attribution import (
            treatment_effect_returns,
            stream_sharpe,
            attribution_diagnostics,
        )
        from engines.engine_d_discovery.robustness import RobustnessTester

        # ---- Gate 0: MBL pre-flight (T-2026-05-24-083) ----------------
        # Per CLAUDE.md non-negotiable `[NN-MBL]`. Reject backtest windows that
        # are statistically incapable of clearing DSR at the configured
        # SR_target given the accumulated honest-N. Runs BEFORE any
        # expensive backtest fires; fail-fast saves ~30 min per cell.
        #
        # RR-3 (proposal, 2026-09-30): this block used to catch
        # (ValueError, FileNotFoundError) and "log + proceed — better to run the
        # gauntlet than to crash on a precondition check". With the registry absent
        # (its normal state in every cloud container: data/observability is
        # .dockerignore'd) that meant N=1 → MBL_min=0 → PASS, for every candidate.
        # Now: an un-establishable honest N (HonestNUnavailableError) PROPAGATES —
        # a harness failure, not a candidate verdict — and an unparseable window
        # fails THIS candidate's Gate 0 instead of skipping it.
        #
        # One N per evaluation: an explicit `n_trials_for_dsr` is what Gate 0 AND
        # Gate 8 both use. Before, Gate 0 judged against the registry count while
        # Gate 8 judged against whatever the caller passed (production: the batch
        # size) — two different trial counts inside one candidate's verdict.
        # RR-6a: one tri-state verdict per gate, and the required set, established BEFORE any
        # work — a bad `required_gates` config fails here, not after an hour of backtests.
        from engines.engine_d_discovery.thresholds import required_gates
        required = required_gates()
        verdicts = gv.new_verdicts()

        def _seal(res: Dict[str, Any]) -> Dict[str, Any]:
            """The ONE place the verdict becomes a decision: the verdicts, their derived
            legacy flags, and passed_all_gates = every required gate PASSED."""
            passed, refusals = gv.promotion_decision(verdicts, required)
            res["gate_verdicts"] = verdicts
            res.update(gv.legacy_flags(verdicts))
            res["passed_all_gates"] = passed
            res["promotion_refusals"] = refusals
            res["required_gates"] = list(required)
            return res

        n_trials_source = "explicit" if n_trials_for_dsr is not None else None
        if not enable_mbl_gate:
            gv.not_evaluated(verdicts, "gate_0", "enable_mbl_gate=False (legacy bitwise cross-check bypass)")
        elif not (start_date and end_date):
            gv.not_evaluated(verdicts, "gate_0", "no validation window passed — MinBTL cannot be checked")
        else:
            from core.measurement.mbl_gate import check_mbl_gate, years_from_window
            try:
                t_years = years_from_window(start_date, end_date)
            except ValueError as exc:
                gv.not_evaluated(verdicts, "gate_0", f"bad window ({exc}) — an MBL check that cannot run is not a pass")
                gv.not_reached(verdicts, "gate_0", "the validation window is unparseable")
                return _seal({
                    "gate_0_reason": f"unevaluable: bad window ({exc}) — an MBL check "
                                     f"that cannot run is not a pass",
                    "killed_by_gate": "gate_0_unevaluable",
                })
            mbl_verdict = check_mbl_gate(
                t_years=t_years,
                n_effective=n_trials_for_dsr,
                sr_target=mbl_sr_target,
            )
            if n_trials_for_dsr is None:
                n_trials_for_dsr = mbl_verdict["n_effective"]
                n_trials_source = mbl_verdict["n_effective_source"]
            gv.render(verdicts, "gate_0", bool(mbl_verdict["passed"]), mbl_verdict["reason"])
            if not mbl_verdict["passed"]:
                gv.not_reached(verdicts, "gate_0", "the window is shorter than MinBTL")
                return _seal({
                    "gate_0_reason": mbl_verdict["reason"],
                    "gate_0_mbl_min": mbl_verdict["mbl_min"],
                    "gate_0_n_effective": mbl_verdict["n_effective"],
                    "gate_0_n_effective_source": mbl_verdict["n_effective_source"],
                    "gate_0_t_years": mbl_verdict["t_years"],
                    "killed_by_gate": "gate_0_mbl",
                })

        _diag_t_start = _time.time()
        _diag_gate_seconds: Dict[str, float] = {}
        _diag_gates_run: List[str] = []
        _diag_error: Optional[str] = None

        def _stamp(gate_name: str, t0: float) -> None:
            _diag_gate_seconds[gate_name] = round(_time.time() - t0, 3)
            _diag_gates_run.append(gate_name)

        result = {
            "sharpe": 0.0,
            "sortino": 0.0,
            "baseline_sharpe": 0.0,
            "with_candidate_sharpe": 0.0,
            "contribution_sharpe": 0.0,
            "attribution_sharpe": 0.0,
            "robustness_survival": 0.0,
            "wfo_degradation": 0.0,
            "significance_p": 1.0,
            # RR-6a: no gate flags here. They were two-valued DEFAULTS — Gate 7/8 started
            # True ("SKIPPED"), so a gate that never ran read as a pass. `_seal` writes the
            # verdicts and the flags derived from them at every exit.
            # RR-3: the trial count every multiple-testing decision in this verdict used,
            # and where it came from — recorded with the decision (discovery_log.jsonl).
            "n_trials_for_dsr": n_trials_for_dsr,
            "n_trials_source": n_trials_source,
        }

        def _emit_diag() -> None:
            if not diagnostic_log_path:
                return
            try:
                # RR-6a: the killer is the first gate whose verdict is FAILED. A gate that
                # rendered no verdict (Gate 3 always; Gate 7/8 when skipped) is never named.
                first_failed = gv.first_failed_gate(result)
                params = candidate_spec.get("params", {}) or {}
                gene_count = 0
                gene_types: List[str] = []
                if "genes" in params and isinstance(params["genes"], list):
                    gene_count = len(params["genes"])
                    for g in params["genes"]:
                        if isinstance(g, dict):
                            gene_types.append(str(g.get("type", "?")))
                rec = {
                    "candidate_id": candidate_spec.get("edge_id", "?"),
                    "module": candidate_spec.get("module", "?"),
                    "class": candidate_spec.get("class", "?"),
                    "category": candidate_spec.get("category", "?"),
                    "origin": candidate_spec.get("origin", "?"),
                    "gene_count": gene_count,
                    "gene_types": gene_types,
                    "direction": params.get("direction"),
                    "wall_seconds_total": round(_time.time() - _diag_t_start, 3),
                    "gate_seconds": _diag_gate_seconds,
                    "gates_run": _diag_gates_run,
                    "first_failed_gate": first_failed,
                    "error": _diag_error,
                    "metrics": {
                        "sharpe": float(result.get("sharpe", 0.0) or 0.0),
                        "sortino": float(result.get("sortino", 0.0) or 0.0),
                        "robustness_survival": float(result.get("robustness_survival", 0.0) or 0.0),
                        "wfo_degradation": float(result.get("wfo_degradation", 0.0) or 0.0),
                        "wfo_oos_sharpe": float(result.get("wfo_oos_sharpe", 0.0) or 0.0),
                        "wfo_is_sharpe": float(result.get("wfo_is_sharpe", 0.0) or 0.0),
                        "significance_p": float(result.get("significance_p", 1.0) or 1.0),
                        "benchmark_threshold": float(result.get("benchmark_threshold", float("nan")) or float("nan")),
                        "universe_b_sharpe": float(result.get("universe_b_sharpe", float("nan")) or float("nan")),
                        "universe_b_n_tickers": int(result.get("universe_b_n_tickers", 0) or 0),
                        "factor_alpha_annualized": float(result.get("factor_alpha_annualized", 0.0) or 0.0),
                        "factor_alpha_tstat": float(result.get("factor_alpha_tstat", 0.0) or 0.0),
                        "factor_alpha_reason": str(result.get("factor_alpha_reason", "")),
                    },
                    # Legacy shape, values DERIVED from the verdicts (never a default).
                    "gate_passed": {
                        "gate_1": result["gate_1_passed"],
                        "gate_2": result["gate_2_passed"],
                        "gate_3_evaluated": result["gate_3_evaluated"],
                        "gate_4": result["gate_4_passed"],
                        "gate_5": result["gate_5_passed"],
                        "gate_6": result["gate_6_passed"],
                        "gate_7": result["gate_7_passed"],
                        "gate_7_evaluated": result["gate_7_evaluated"],
                        "gate_8": result["gate_8_passed"],
                        "gate_8_evaluated": result["gate_8_evaluated"],
                    },
                    "gate_verdicts": result["gate_verdicts"],
                    "promotion_refusals": result["promotion_refusals"],
                    "passed_all_gates": result["passed_all_gates"],
                }
                import json as _json
                from pathlib import Path as _Path
                _p = _Path(diagnostic_log_path)
                _p.parent.mkdir(parents=True, exist_ok=True)
                with open(_p, "a") as _f:
                    _f.write(_json.dumps(rec) + "\n")
            except Exception as _emit_err:
                print(f"[DISCOVERY-DIAG] emit failed: {_emit_err}")

        def _finish() -> Dict[str, Any]:
            """Every exit: seal the verdicts into the result, emit the diagnostic row, return."""
            _seal(result)
            _emit_diag()
            return result

        try:
            # ---------------------------------------------------------------
            # Setup: build production-equivalent baseline + with-candidate
            # edge ensembles. Run pure backtests for both. Compute
            # attribution stream from the diff.
            # ---------------------------------------------------------------
            if not data_map:
                _diag_error = "empty_data_map"
                gv.not_reached(verdicts, "setup", "empty data_map")
                return _finish()

            cand_id = candidate_spec["edge_id"]
            first_ticker = list(data_map.keys())[0]
            if start_date is None:
                start_date = data_map[first_ticker].index[0].isoformat()
            if end_date is None:
                end_date = data_map[first_ticker].index[-1].isoformat()

            # Default exec_params: cheap 5bps for discovery scans; callers
            # passing realistic-cost ADV-bucketed Almgren-Chriss configs
            # override this.
            _exec_params = exec_params if exec_params is not None else {"slippage_bps": 5.0}

            # Lazy-load alpha config so soft-pause weights match production.
            if alpha_config is None:
                try:
                    from utils.config_loader import load_json
                    repo_root = Path(__file__).resolve().parents[2]
                    alpha_config = load_json(
                        str(repo_root / "config" / "alpha_settings.prod.json")
                    )
                except Exception:
                    alpha_config = {}

            # Build the baseline ensemble (production minus this candidate)
            baseline_edges, baseline_weights = self._build_production_edges(
                registry_path=self.registry_path,
                alpha_config=alpha_config,
                exclude_edge_ids={cand_id},
            )

            # Gate 1 signal-collector caching (T-2026-05-11-023).
            # Wrap baseline edges with memoizing wrappers so subsequent
            # candidates (and the with-candidate backtest within this
            # call) reuse per-(edge, bar) signals instead of recomputing.
            # The candidate edge itself is NEVER wrapped — it's new per
            # call so caching has no benefit.
            #
            # The cache key includes the window so a window change
            # between cycles auto-invalidates. (Universe change reaches
            # us via a different data_map; same window + different
            # data_map → cache hits would return stale tickers, but
            # within a Discovery cycle the data_map is constant.)
            if use_signal_cache:
                _cache_fingerprint = f"{start_date}|{end_date}|{','.join(sorted(baseline_edges.keys()))}"
                wrapped_baseline = self._get_gate1_signal_cache().wrap_edges(
                    baseline_edges, fingerprint=_cache_fingerprint,
                )
            else:
                wrapped_baseline = baseline_edges

            # Build the with-candidate ensemble (baseline + candidate at default weight)
            cand_edge = self._instantiate_candidate(candidate_spec)
            with_edges = dict(wrapped_baseline)
            # T-2026-08-26-347: the candidate rides in a COUNTING-ONLY proxy so
            # its silence is countable. Byte-identical behaviour (no memoizing,
            # no swallowing) — it only tallies non-zero emissions for the census
            # below. Applied unconditionally, NOT gated on `use_signal_cache`:
            # the guard must exist exactly where the cache is off too.
            cand_census = CandidateSignalCensus(cand_edge, cand_id)
            with_edges[cand_id] = cand_census
            with_weights = dict(baseline_weights)
            with_weights[cand_id] = float(candidate_default_weight)

            # Caching: if the orchestrator passed a cache, fingerprint and
            # reuse the baseline; the with-candidate run is candidate-
            # specific and not cacheable.
            local_cache = cache if cache is not None else PureBacktestCache()

            run_kwargs = dict(
                data_map=data_map,
                start_date=start_date,
                end_date=end_date,
                exec_params=_exec_params,
                initial_capital=100_000.0,
                alpha_config=alpha_config,
                risk_settings=risk_settings,
                portfolio_settings=portfolio_settings,
            )

            _g1_t0 = _time.time()
            baseline_result = local_cache.get_or_run(
                edges=wrapped_baseline,
                edge_weights=baseline_weights,
                **run_kwargs,
            )
            # T-2026-06-17-197: fail LOUD if the wrapped baseline ensemble is
            # structurally degenerate (a swallowed edge crash → empty signals →
            # a silent fake Sharpe-0, T-195). Only meaningful when the signal
            # cache is active (use_signal_cache=True); a degenerate baseline
            # makes every candidate's contribution meaningless, so this raises a
            # named DiscoveryBaselineError instead of publishing a fake 0.
            if use_signal_cache:
                self._get_gate1_signal_cache().assert_baseline_healthy()
            with_candidate_result = run_backtest_pure(
                edges=with_edges,
                edge_weights=with_weights,
                **run_kwargs,
            )

            # ---- T-2026-08-26-347: the Gate-1 CANDIDATE census (`[NN-CENSUS]`) ----
            # T-346 established that an exactly +0.000 contribution has three
            # causes and only one is a refutation. `assert_baseline_healthy`
            # above guards the BASELINE (and only against crashes); nothing
            # guarded the CANDIDATE, so an edge that emitted no signal was
            # published as REFUTED, indistinguishable from a genuine null.
            # A candidate that emits zero signals must get a VERDICT, not a
            # NUMBER. Routed through the SAME `assert_census` the measurement
            # path uses — never a second, drifting health standard.
            # NB: `trade_log` is a DataFrame — never test it for truthiness
            # (`df or []` raises "truth value of a DataFrame is ambiguous").
            _tl = getattr(with_candidate_result, "trade_log", None)
            n_trades_with = 0 if _tl is None else int(len(_tl))
            _census_block = candidate_census_block(cand_id, cand_census, n_trades_with)
            _cv = assert_census(
                {"census": _census_block,
                 # A Gate-1 contribution run is not a headline measurement; the
                 # CI lives on the attribution stream downstream. Declared, not
                 # silently absent, so the census emits no spurious warning.
                 "bootstrap_ci_skip_reason": "gate1_contribution_run"},
            )
            if not _cv.canonical:
                raise DiscoveryCandidateCensusError(
                    f"Gate-1 candidate census NON-CANONICAL for {cand_id!r}: "
                    f"{'; '.join(_cv.failures)} "
                    f"[signal calls={cand_census.calls}, non-zero={cand_census.nonzero_calls}, "
                    f"errors={cand_census.errors}, last_error={cand_census.last_error!r}, "
                    f"n_trades={n_trades_with}] — the contribution would measure "
                    f"the harness, not the edge, so it is not a verdict."
                )

            # Pull Sharpes
            baseline_sharpe = float(baseline_result.metrics.get("Sharpe Ratio", 0.0))
            with_candidate_sharpe = float(
                with_candidate_result.metrics.get("Sharpe Ratio", 0.0)
            )
            contribution = with_candidate_sharpe - baseline_sharpe
            result["baseline_sharpe"] = baseline_sharpe
            result["with_candidate_sharpe"] = with_candidate_sharpe
            result["contribution_sharpe"] = contribution
            # `sharpe` retained for backward-compat consumers (orchestrator
            # passed_all_gates final-check, fitness score, GA selection).
            # Now reports the with-candidate ensemble Sharpe rather than a
            # standalone single-edge Sharpe.
            result["sharpe"] = with_candidate_sharpe
            result["sortino"] = float(
                with_candidate_result.metrics.get("Sortino", 0.0)
            )

            # Attribution stream = with - baseline (treatment effect).
            attribution = treatment_effect_returns(
                with_candidate_result.daily_returns,
                baseline_result.daily_returns,
            )

            # ---- T-347: the SECOND cause, kept DISTINCT from blindness ----
            # The candidate spoke, yet the return stream is bit-identical to the
            # baseline: the allocator absorbed it exactly. That is the T-156
            # result (inverse-vol normalization is scale-invariant in signal
            # level, so a uniform signal cancels algebraically; T-158 confirmed
            # it exact at runtime). The contribution then measures the HARNESS,
            # not the edge — equally not a verdict, but a DIFFERENT diagnosis.
            # Collapsing the two is precisely how three mechanisms hid behind
            # one +0.000 for months (T-346 §1), so they never share a message.
            if cand_census.nonzero_calls > 0 and len(attribution) > 0 \
                    and not (attribution != 0.0).any():
                raise DiscoveryCandidateCensusError(
                    f"Gate-1 candidate ABSORBED for {cand_id!r}: emitted non-zero "
                    f"signals on {cand_census.nonzero_calls}/{cand_census.calls} calls, "
                    f"yet the attribution stream is identically zero over "
                    f"{len(attribution)} bars — the allocator cancelled it exactly "
                    f"(T-156/T-158 scale-invariance). The contribution measures the "
                    f"harness, not the edge; this is NOT a refutation of the edge."
                )
            attribution_sharpe = stream_sharpe(attribution)
            result["attribution_sharpe"] = attribution_sharpe
            attr_diag = attribution_diagnostics(attribution, capital=100_000.0)
            result["attribution_diagnostics"] = attr_diag

            # ---- Gate 1: Sharpe contribution ----
            # Pass criterion: with-candidate Sharpe lifts the baseline by
            # at least `gate1_contribution_threshold` (default 0.10).
            # This replaces the legacy benchmark-relative standalone gate
            # which kills 30/30 candidates that have positive ensemble
            # contribution (Audit doc discovery_diagnostic_2026_05.md).
            gate1_ok = bool(contribution > gate1_contribution_threshold)
            gv.render(verdicts, "gate_1", gate1_ok,
                      f"contribution {contribution:+.3f} {'>' if gate1_ok else '<='} {gate1_contribution_threshold}")
            result["benchmark_threshold"] = float(gate1_contribution_threshold)
            if not gate1_ok:
                print(
                    f"[DISCOVERY] {cand_id} failed Gate 1 "
                    f"(contribution={contribution:+.3f} <= {gate1_contribution_threshold})"
                )
                _stamp("gate_1", _g1_t0)
                gv.not_reached(verdicts, "gate_1", "the candidate failed gate_1")
                return _finish()
            _stamp("gate_1", _g1_t0)

            # ---- Gate 2: PBO survival on attribution stream ----
            _g2_t0 = _time.time()
            survival_rate = 0.0
            g2_error: Optional[str] = None
            try:
                tester = RobustnessTester()
                pbo = tester.calculate_pbo_returns_stream(
                    attribution, n_paths=200, block_size=20, seed=42,
                )
                survival_rate = pbo.get("survival_rate", 0.0)
                result["pbo_actual_sharpe"] = pbo.get("actual_sharpe", 0.0)
                result["pbo_avg_synthetic_sharpe"] = pbo.get("avg_synthetic_sharpe", 0.0)
            except Exception as e:
                if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                    raise
                print(f"[Gate 2] {type(e).__name__}: {e}")
                survival_rate = 0.0
                g2_error = f"{type(e).__name__}: {e}"

            result["robustness_survival"] = float(survival_rate)
            if g2_error is not None:
                gv.not_evaluated(verdicts, "gate_2", f"PBO could not run — {g2_error}")
            else:
                gv.render(verdicts, "gate_2", survival_rate >= gate2_survival_threshold,
                          f"survival {survival_rate:.3f} vs {gate2_survival_threshold}")
            _stamp("gate_2", _g2_t0)

            # ---- Gate 3: WFO consistency on attribution stream ----
            # Replaces hyperparameter-optimization WFO with a simpler
            # rolling-window Sharpe-consistency check on the attribution
            # stream (the architectural fix means the candidate's
            # contribution is the right substrate, not its standalone
            # parameters). Computes mean rolling-63d Sharpe and divides
            # by overall Sharpe. RR-6a: RECORDED, never compared — Gate 3 has no
            # pass criterion, so its verdict is NOT_EVALUATED and it can never be
            # named as a killer (two T-196 records were blamed on it).
            _g3_t0 = _time.time()
            wfo_consistency = 0.0
            try:
                if len(attribution) >= 126:  # need at least 2 windows of 63d
                    win = 63  # ~3 months of trading days
                    rolling_sharpes = []
                    for start_i in range(0, len(attribution) - win + 1, win // 2):
                        chunk = attribution.iloc[start_i : start_i + win]
                        s = stream_sharpe(chunk)
                        rolling_sharpes.append(s)
                    if rolling_sharpes and attribution_sharpe > 0:
                        mean_window_sharpe = float(np.mean(rolling_sharpes))
                        wfo_consistency = mean_window_sharpe / attribution_sharpe
                        result["wfo_oos_sharpe"] = mean_window_sharpe
                        result["wfo_is_sharpe"] = float(attribution_sharpe)
                        result["wfo_window_sharpes"] = [float(x) for x in rolling_sharpes]
            except Exception as e:
                if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                    raise
                print(f"[Gate 3] {type(e).__name__}: {e}")

            result["wfo_degradation"] = float(wfo_consistency)
            gv.not_evaluated(verdicts, "gate_3", (
                f"recorded only — no pass criterion (RR-6b decides whether Gate 3 binds); "
                + (f"consistency {wfo_consistency:.3f}" if wfo_consistency != 0.0 else
                   "consistency not computed (attribution < 126 bars, or its Sharpe <= 0)")))
            _stamp("gate_3", _g3_t0)

            # ---- Gate 4: Permutation significance on attribution stream ----
            _g4_t0 = _time.time()
            sig_p = 1.0
            g4_error: Optional[str] = None
            try:
                from engines.engine_d_discovery.significance import (
                    monte_carlo_permutation_test,
                )
                sig_result = monte_carlo_permutation_test(
                    attribution.values, n_permutations=500,
                )
                sig_p = sig_result.get("p_value", 1.0)
            except Exception as e:
                if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                    raise
                print(f"[Gate 4] {type(e).__name__}: {e}")
                sig_p = 1.0
                g4_error = f"{type(e).__name__}: {e}"

            result["significance_p"] = float(sig_p)
            # RR-2: the threshold is always a number here — validate_candidate
            # raises on None at entry, so there is no "skip" mode left to fail.
            if g4_error is not None:
                gv.not_evaluated(verdicts, "gate_4", f"permutation test could not run — {g4_error}")
            else:
                gv.render(verdicts, "gate_4", sig_p < significance_threshold,
                          f"p {sig_p:.4f} vs {significance_threshold}")
            _stamp("gate_4", _g4_t0)

            # RR-6a — the with-arm on any OTHER data_map is built from the UNWRAPPED
            # baseline edges. The Gate-1 signal cache keys on the bar timestamp alone
            # (`CachedEdgeWrapper._key_for(now)`), so a wrapped baseline edge run on
            # Universe B or substrate B replayed its Universe-A signal on every shared
            # date: the with-arm carried Universe A's baseline while the baseline arm
            # (unwrapped) carried B's, and the "contribution" measured the cache, not
            # the candidate. Gates 5 and 7 use this dict; Gate 1 keeps its cache.
            alt_with_edges = dict(baseline_edges)
            alt_with_edges[cand_id] = cand_edge

            # ---- Gate 5: Universe-B production-equivalent transfer ----
            _g5_t0 = _time.time()
            universe_b_sharpe: float = float("nan")
            universe_b_n_tickers: int = 0
            universe_b_contribution: float = float("nan")
            g5_not_evaluated: Optional[str] = None
            try:
                dm_b = self._load_universe_b(prod_tickers=set(data_map.keys()))
                universe_b_n_tickers = len(dm_b)
                if not dm_b:
                    print(f"[DISCOVERY] Gate 5 skipped: no universe-B tickers available")
                    g5_not_evaluated = "no universe-B tickers available"
                else:
                    # Production-equivalent ensemble on Universe-B too.
                    # Run baseline + with-candidate; contribution = diff.
                    ub_start = list(dm_b.values())[0].index[0].isoformat()
                    ub_end = list(dm_b.values())[0].index[-1].isoformat()
                    ub_run_kwargs = dict(
                        data_map=dm_b,
                        start_date=ub_start,
                        end_date=ub_end,
                        exec_params=_exec_params,
                        initial_capital=100_000.0,
                        alpha_config=alpha_config,
                        risk_settings=risk_settings,
                        portfolio_settings=portfolio_settings,
                    )
                    ub_baseline = run_backtest_pure(
                        edges=baseline_edges,
                        edge_weights=baseline_weights,
                        **ub_run_kwargs,
                    )
                    ub_with = run_backtest_pure(
                        edges=alt_with_edges,
                        edge_weights=with_weights,
                        **ub_run_kwargs,
                    )
                    ub_contribution = (
                        float(ub_with.metrics.get("Sharpe Ratio", 0.0))
                        - float(ub_baseline.metrics.get("Sharpe Ratio", 0.0))
                    )
                    ub_attribution = treatment_effect_returns(
                        ub_with.daily_returns, ub_baseline.daily_returns,
                    )
                    universe_b_sharpe = stream_sharpe(ub_attribution)
                    universe_b_contribution = ub_contribution
            except Exception as e:
                if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                    raise
                print(f"[Gate 5] {type(e).__name__}: {e}")
                universe_b_sharpe = float("nan")
                universe_b_contribution = float("nan")
                g5_not_evaluated = f"universe-B run failed — {type(e).__name__}: {e}"

            result["universe_b_sharpe"] = universe_b_sharpe
            result["universe_b_contribution"] = universe_b_contribution
            result["universe_b_n_tickers"] = universe_b_n_tickers
            # NaN means we couldn't measure. Previously NaN short-circuited to pass;
            # then it was recorded as a FAIL — blaming a gate that rendered nothing.
            # RR-6a: it is NOT_EVALUATED, which a required gate turns into a refusal.
            if g5_not_evaluated is None and math.isnan(universe_b_sharpe):
                g5_not_evaluated = "universe-B attribution Sharpe is NaN"
            if g5_not_evaluated is not None:
                gv.not_evaluated(verdicts, "gate_5", g5_not_evaluated)
            else:
                gv.render(verdicts, "gate_5", universe_b_sharpe > 0,
                          f"universe-B attribution Sharpe {universe_b_sharpe:+.3f} on {universe_b_n_tickers} tickers")
            _stamp("gate_5", _g5_t0)

            # ---- Gate 6: FF5+Mom factor decomposition on attribution stream ----
            _g6_t0 = _time.time()
            # Fail-closed: a candidate that cannot prove non-trivial alpha vs FF5+Mom
            # does not pass on the absence of evidence. RR-6a: nor does a candidate
            # whose regression never ran — a missing factor cache and too little
            # overlap used to read as a PASS ("skipped"); they are NOT_EVALUATED now.
            factor_alpha_passed = False
            factor_alpha_reason = "failed: not run"
            g6_not_evaluated: Optional[str] = None
            try:
                from core.factor_decomposition import (
                    load_factor_data,
                    regress_returns_on_factors,
                    gate_factor_alpha,
                )
                factors = load_factor_data(auto_download=False)
                # RR-6a (Gate 6 RF): the attribution stream is with − baseline, a
                # SPREAD — already an excess return. Subtracting RF from it again
                # shifted α by −RF (a +2.5%/yr spread read −2.5% at RF 5%).
                decomp = regress_returns_on_factors(
                    returns=attribution,
                    factors=factors,
                    edge_name=cand_id,
                    already_excess=True,
                )
                if decomp is None:
                    g6_not_evaluated = "too little attribution/factor overlap to regress"
                    factor_alpha_reason = f"not evaluated: {g6_not_evaluated}"
                else:
                    factor_alpha_passed, factor_alpha_reason = gate_factor_alpha(decomp)
                    result["factor_alpha_annualized"] = decomp.alpha_annualized
                    result["factor_alpha_tstat"] = decomp.alpha_tstat
                    result["factor_r_squared"] = decomp.r_squared
            except FileNotFoundError as e:
                g6_not_evaluated = f"factor cache missing ({e})"
                factor_alpha_reason = "not evaluated: factor cache missing"
                print(f"[DISCOVERY] Gate 6 not evaluated: {e}")
            except Exception as e:
                if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                    raise
                g6_not_evaluated = f"factor regression failed — {type(e).__name__}: {e}"
                factor_alpha_reason = f"not evaluated: {type(e).__name__}"
                print(f"[Gate 6] {type(e).__name__}: {e}")

            result["factor_alpha_passed"] = factor_alpha_passed
            result["factor_alpha_reason"] = factor_alpha_reason
            if g6_not_evaluated is not None:
                gv.not_evaluated(verdicts, "gate_6", g6_not_evaluated)
            else:
                gv.render(verdicts, "gate_6", factor_alpha_passed, factor_alpha_reason)
            _stamp("gate_6", _g6_t0)
            # T-203 Phase-0 re-aim: Gate-6 (factor-orthogonality) is DIAGNOSTIC-
            # ONLY by default (factor_gate_mode='report') — the resolved goal is
            # beat-the-robo, not academic factor-orthogonal alpha. The verdict is
            # still computed + recorded (now with the HAC-corrected t-stat) but
            # does not KILL unless mode=='kill'. The deploy-readiness check is the
            # robo scorecard gate (core.combined_candidate_scorecard).
            # RR-6a: whether Gate 6 binds is whether it is in `required_gates`, which
            # `thresholds.required_gates` has already checked against factor_gate_mode
            # in the same file — the two can no longer disagree.
            _fgm = "kill" if "gate_6" in required else "report"
            result["factor_gate_mode"] = _fgm
            if not factor_alpha_passed:
                _tag = "failed Gate 6 (KILL)" if _fgm == "kill" else "Gate 6 report-only (diagnostic, not killed)"
                print(f"[DISCOVERY] {cand_id} {_tag} ({factor_alpha_reason})")

            # ---- Gate 7: Substrate-transfer (historical-S&P 500 universe) ----
            # Added 2026-05-09 evening per F6 audit-machinery gap. Catches
            # substrate-conditional alpha BEFORE promotion. The gate runs the
            # production-equivalent ensemble on the substrate-B data_map
            # (typically the historical-S&P 500 union via
            # UniverseLoader.historical_constituents) and compares the
            # candidate's contribution Sharpe across the two substrates.
            #
            # If substrate-B contribution Sharpe < 0 → FAIL (substrate-
            # conditional drag).
            # If |substrate-A contribution - substrate-B contribution|
            #   > gate7_max_substrate_drift → FAIL (substrate-conditional
            #   alpha; survives one substrate but not the other).
            #
            # RR-6a: without a substrate-B data_map the gate is NOT_EVALUATED — it
            # used to default to PASSED, and production never built substrate B (a
            # swallowed NameError), so every production candidate got a free Gate 7.
            if data_map_substrate_b is None or len(data_map_substrate_b) == 0:
                gv.not_evaluated(verdicts, "gate_7", "no substrate-B data_map provided")
                result["gate_7_reason"] = "not evaluated: no substrate-B data_map provided"
            else:
                _g7_t0 = _time.time()
                substrate_b_contribution: float = float("nan")
                substrate_b_sharpe: float = float("nan")
                substrate_b_drift: float = float("nan")
                gate_7_reason = "not run"
                g7_not_evaluated: Optional[str] = None
                gate_7_passed = False
                try:
                    sb_start = list(data_map_substrate_b.values())[0].index[0].isoformat()
                    sb_end = list(data_map_substrate_b.values())[0].index[-1].isoformat()
                    sb_run_kwargs = dict(
                        data_map=data_map_substrate_b,
                        start_date=sb_start,
                        end_date=sb_end,
                        exec_params=_exec_params,
                        initial_capital=100_000.0,
                        alpha_config=alpha_config,
                        risk_settings=risk_settings,
                        portfolio_settings=portfolio_settings,
                    )
                    sb_baseline = run_backtest_pure(
                        edges=baseline_edges,
                        edge_weights=baseline_weights,
                        **sb_run_kwargs,
                    )
                    sb_with = run_backtest_pure(
                        edges=alt_with_edges,
                        edge_weights=with_weights,
                        **sb_run_kwargs,
                    )
                    substrate_b_contribution = (
                        float(sb_with.metrics.get("Sharpe Ratio", 0.0))
                        - float(sb_baseline.metrics.get("Sharpe Ratio", 0.0))
                    )
                    sb_attribution = treatment_effect_returns(
                        sb_with.daily_returns, sb_baseline.daily_returns,
                    )
                    substrate_b_sharpe = stream_sharpe(sb_attribution)
                    substrate_b_drift = abs(
                        contribution - substrate_b_contribution
                    )
                    # Two failure conditions: negative on substrate B, OR
                    # too much drift between substrates. A NaN is unmeasured, not failed.
                    if math.isnan(substrate_b_sharpe):
                        g7_not_evaluated = "substrate-B attribution Sharpe is NaN"
                        gate_7_reason = f"not evaluated: {g7_not_evaluated}"
                    elif substrate_b_contribution < 0:
                        gate_7_passed = False
                        gate_7_reason = (
                            f"failed: substrate-B contribution {substrate_b_contribution:+.3f} < 0"
                        )
                    elif substrate_b_drift > gate7_max_substrate_drift:
                        gate_7_passed = False
                        gate_7_reason = (
                            f"failed: substrate drift {substrate_b_drift:.3f} > "
                            f"{gate7_max_substrate_drift}"
                        )
                    else:
                        gate_7_passed = True
                        gate_7_reason = (
                            f"passed: drift {substrate_b_drift:.3f}, "
                            f"sb_contrib {substrate_b_contribution:+.3f}"
                        )
                except Exception as e:
                    if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                        raise
                    g7_not_evaluated = f"substrate-B run failed — {type(e).__name__}: {e}"
                    gate_7_reason = f"not evaluated: {type(e).__name__}: {e}"
                    print(f"[Gate 7] {type(e).__name__}: {e}")
                if g7_not_evaluated is not None:
                    gv.not_evaluated(verdicts, "gate_7", g7_not_evaluated)
                else:
                    gv.render(verdicts, "gate_7", gate_7_passed, gate_7_reason)
                result["gate_7_reason"] = gate_7_reason
                result["substrate_b_sharpe"] = substrate_b_sharpe
                result["substrate_b_contribution"] = substrate_b_contribution
                result["substrate_b_drift"] = substrate_b_drift
                _stamp("gate_7", _g7_t0)
                if not gate_7_passed:
                    print(f"[DISCOVERY] {cand_id} did not pass Gate 7 ({gate_7_reason})")

            # ---- Gate 8: DSR multiple-testing correction ----
            # Added 2026-05-09 evening per outside-reviewer recommendation.
            # When the Discovery cycle generates n_trials_for_dsr > 1
            # candidates, raw Sharpe gates are too lax — testing 50 things
            # at p<0.05 is expected to find ~2.5 false positives. DSR
            # (Bailey & Lopez de Prado 2014) corrects: PSR with the
            # benchmark set to E[max SR_i] under the null of N independent
            # trials. Default n_trials_for_dsr=1 disables (legacy behavior).
            if n_trials_for_dsr is None:
                # RR-3: this read used to be wrapped in `except Exception: n = 1`,
                # commented "fail-safe: never block on a bad read". In a measurement
                # path that inverts what safe means: N=1 skipped Gate 8 entirely and
                # its default reads gate_8_passed=True. Now the correlation-aware
                # count FAILS CLOSED and the outer handler re-raises it.
                from core.measurement.mbl_gate import compute_n_effective_correlated
                n_trials_for_dsr = compute_n_effective_correlated()
                n_trials_source = "registry_correlated"
                result["n_trials_for_dsr"] = n_trials_for_dsr
                result["n_trials_source"] = n_trials_source
            if n_trials_for_dsr <= 1:
                # RR-6a: an explicit N ≤ 1 applies no multiple-testing correction. That
                # is NOT a pass — it used to default to gate_8_passed=True.
                gv.not_evaluated(verdicts, "gate_8",
                                 f"n_trials_for_dsr={n_trials_for_dsr}: no multiple-testing correction applied")
                result["gate_8_reason"] = f"not evaluated: n_trials_for_dsr={n_trials_for_dsr}"
            else:
                _g8_t0 = _time.time()
                dsr_value: float = 0.0
                gate_8_reason = "not run"
                g8_not_evaluated: Optional[str] = None
                gate_8_passed = False
                try:
                    from core.metrics_engine import MetricsEngine
                    if attribution is not None and len(attribution) >= 4:
                        dsr_value = MetricsEngine.deflated_sharpe_ratio(
                            attribution, n_trials=n_trials_for_dsr,
                        )
                        if dsr_value >= gate8_dsr_threshold:
                            gate_8_passed = True
                            gate_8_reason = f"passed: DSR {dsr_value:.3f} ≥ {gate8_dsr_threshold}"
                        else:
                            gate_8_passed = False
                            gate_8_reason = (
                                f"failed: DSR {dsr_value:.3f} < {gate8_dsr_threshold} "
                                f"(n_trials={n_trials_for_dsr})"
                            )
                    else:
                        g8_not_evaluated = "attribution stream too short for DSR"
                        gate_8_reason = f"not evaluated: {g8_not_evaluated}"
                except Exception as e:
                    if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
                        raise
                    g8_not_evaluated = f"DSR could not run — {type(e).__name__}: {e}"
                    gate_8_reason = f"not evaluated: {type(e).__name__}: {e}"
                    print(f"[Gate 8] {type(e).__name__}: {e}")
                if g8_not_evaluated is not None:
                    gv.not_evaluated(verdicts, "gate_8", g8_not_evaluated)
                else:
                    gv.render(verdicts, "gate_8", gate_8_passed, gate_8_reason)
                result["gate_8_reason"] = gate_8_reason
                result["dsr_value"] = dsr_value
                result["n_trials_for_dsr"] = n_trials_for_dsr
                _stamp("gate_8", _g8_t0)
                if not gate_8_passed:
                    print(f"[DISCOVERY] {cand_id} did not pass Gate 8 ({gate_8_reason})")

            # ---- Final pass check ----
            # RR-6a: the decision is the verdicts — every REQUIRED gate PASSED
            # (`_seal`). It used to be rebuilt here from raw metrics, with Gate 7/8
            # read as `result.get("gate_7_passed", True)`: a skipped gate passed.
            result["significance_threshold"] = significance_threshold
            _seal(result)
            passed = result["passed_all_gates"]

            b_sharpe_str = (
                "skipped" if math.isnan(universe_b_sharpe)
                else f"{universe_b_sharpe:.2f}"
            )
            g7_str = (
                "not evaluated" if not result["gate_7_evaluated"]
                else f"drift={result['substrate_b_drift']:.2f}"
            )
            g8_str = (
                "not evaluated" if not result["gate_8_evaluated"]
                else f"DSR={result['dsr_value']:.2f}"
            )
            gate_summary = (
                f"contrib={contribution:+.3f}, "
                f"attr_sh={attribution_sharpe:.2f}, "
                f"survival={survival_rate:.0%}, "
                f"wfo_cons={wfo_consistency:.2f}, "
                f"p={sig_p:.3f}, "
                f"univ_b={b_sharpe_str}({universe_b_n_tickers}t), "
                f"alpha={factor_alpha_reason}, "
                f"substrate_xfer={g7_str}, "
                f"dsr={g8_str}"
            )
            if passed:
                print(f"[DISCOVERY] {cand_id} PASSED all gates: {gate_summary}")
            else:
                print(f"[DISCOVERY] {cand_id} did not pass: {'; '.join(result['promotion_refusals'])} "
                      f"| {gate_summary}")

            # Composite fitness score: weight the contribution Sharpe lift
            # heavily (production-relevant). Survival + WFO consistency are
            # secondary stability signals.
            result["fitness_score"] = float(
                0.5 * contribution
                + 0.3 * float(survival_rate)
                + 0.2 * float(max(0.0, min(1.0, wfo_consistency)))
            )

            return _finish()

        except Exception as e:
            # Programmer errors must propagate so they surface in CI / logs
            # instead of silently masking a candidate as "failed validation."
            # RR-3: so must an un-establishable honest N. It is a HARNESS failure;
            # absorbed here it would mark every candidate in the cycle "failed" —
            # "Discovery promotes nothing", a plausible number (the T-177 shape).
            # RR-6a: every gate the run never reached says why — e.g. a census
            # refusal leaves Gate 1 NOT_EVALUATED, never a Gate-1 FAIL.
            from core.measurement.mbl_gate import HonestNUnavailableError
            gv.not_reached(verdicts, _diag_gates_run[-1] if _diag_gates_run else "setup",
                           f"{type(e).__name__}: {e}")
            _diag_error = f"{type(e).__name__}: {e}"
            if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError,
                              HonestNUnavailableError)):
                _seal(result)
                _emit_diag()
                # RR-6a fixup (ruling (c)): the error that fails the cycle names WHICH
                # candidate and WHICH gate, so the cycle's failure record can say so.
                e.add_note(f"[validate_candidate] candidate={candidate_spec.get('edge_id', '?')} "
                           f"last_gate_completed={_diag_gates_run[-1] if _diag_gates_run else 'none (setup)'}")
                raise
            print(f"[validate_candidate] {type(e).__name__}: {e}")
            return _finish()

# No __main__ block (2026-10-15): a library module is not a process entry. The
# "generate candidates only" CLI moved to scripts/discovery_generate_candidates.py.
