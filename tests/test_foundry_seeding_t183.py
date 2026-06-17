"""T-2026-06-17-183 — fair Foundry representation in the Gen-0 GA seed.

T-179 unblocked the GA but the population seeds from the legacy technical-heavy
ga_population.yml, so the first --discover cycle off it under-tests the Foundry
vocabulary (1/32 foundry genes). This adds a config-gated `foundry_seed_fraction`
that allocates a fair fraction of the FRESH Gen-0 population to single-gene
foundry genomes with feature_ids drawn UNIFORMLY AT RANDOM across the tier-A/B
registry (no hand-picking). Seed diversity ONLY — the gauntlet/DSR gates are
unchanged. These tests lock: the fraction is respected, it's deterministic, OFF
(0.0) is inert, and features are sampled (not hand-picked to one).
"""
from __future__ import annotations

import json
import os
import random
import tempfile

import pytest

import core.feature_foundry.features  # noqa: F401  populate the registry


def _fresh_seed(fraction, seed=0):
    """Build a FRESH Gen-0 population at the given foundry_seed_fraction and
    return its genomes (reads the just-written ga_population.yml)."""
    import yaml
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    random.seed(seed)
    d = tempfile.mkdtemp()
    eng = DiscoveryEngine(registry_path=os.path.join(d, "edges.yml"))
    eng.foundry_seed_fraction = float(fraction)  # bypass config for the test
    eng._run_ga_evolution(n_random_seed=5)
    pop = yaml.safe_load(open(os.path.join(d, "ga_population.yml")))
    return pop if isinstance(pop, list) else pop.get("population", pop)


def _count_fair_foundry(genomes):
    return sum(1 for g in genomes
              if str(g.get("edge_id", "")).startswith("composite_foundryseed_"))


def test_fraction_respected():
    """~half the population is fair-foundry-seeded at fraction 0.5 (pop=20)."""
    genomes = _fresh_seed(0.5)
    n = len(genomes)
    fair = _count_fair_foundry(genomes)
    assert n == 20
    assert fair == 10, f"expected 10 fair-foundry genomes at 0.5×20, got {fair}"


def test_off_is_inert():
    """fraction 0.0 → no fair-foundry genomes (default-safe / prior behavior)."""
    genomes = _fresh_seed(0.0)
    assert _count_fair_foundry(genomes) == 0


def test_deterministic_across_builds():
    """Same seed → identical population (the seed change must be deterministic)."""
    a = json.dumps(_fresh_seed(0.5, seed=0), sort_keys=True, default=str)
    b = json.dumps(_fresh_seed(0.5, seed=0), sort_keys=True, default=str)
    assert a == b


def test_features_are_sampled_not_handpicked():
    """The fair-foundry genes reference MULTIPLE distinct registry features
    (uniform random), not a single hand-picked feature."""
    genomes = _fresh_seed(0.5)
    feats = {ge["feature_id"]
             for g in genomes for ge in g.get("genes", [])
             if ge.get("type") == "foundry_feature"}
    assert len(feats) >= 5, f"foundry features too concentrated: {feats}"
    # and they must be real registered tier-A/B features
    from core.feature_foundry import get_feature_registry
    reg = get_feature_registry()
    valid = {f.feature_id for f in reg.list_features() if f.tier in ("A", "B")}
    assert feats <= valid, f"seeded non-registry features: {feats - valid}"


def test_make_random_foundry_gene_shape():
    """The factored generator returns a well-formed foundry gene."""
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    eng = DiscoveryEngine.__new__(DiscoveryEngine)
    random.seed(0)
    g = eng._make_random_foundry_gene()
    assert g is not None
    assert g["type"] == "foundry_feature" and "feature_id" in g
    assert g["operator"] in ("top_percentile", "bottom_percentile", "greater", "less")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
