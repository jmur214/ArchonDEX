"""T-2026-06-16-179 — regression guard for the Discovery gene-wiring bug.

CompositeEdge bound self.genes/self.direction ONCE in __init__, but the base
set_params (edge_base.py) only updates self.params. Discovery instantiates
candidates via `cls_()` THEN `set_params(spec_params)` (discovery.py
_instantiate_candidate), so every GA-evolved composite/foundry genome reached
compute_signals with genes=[] -> 0 signals -> 0 fitness -> selected out. That
silently neutered the entire Foundry vocabulary (the "rsi-only / 0 promotions"
history, T-021). Fix = override set_params to re-derive self.genes/self.direction
on EVERY set. These tests instantiate via the EXACT production path; the first
two FAIL on the pre-fix code and PASS on the fix.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pandas as pd
import pytest

import core.feature_foundry.features  # noqa: F401  populate the registry

ROOT = Path(__file__).resolve().parents[1]

# Fixed 20-large-cap panel + date so signal counts are deterministic.
TICKERS = ["AAPL", "MSFT", "KO", "JPM", "XOM", "GILD", "CVX", "HD", "PG", "JNJ",
           "BA", "CAT", "MCD", "DIS", "INTC", "WMT", "T", "NKE", "IBM", "GE"]
AS_OF = pd.Timestamp("2024-06-03")


def _data_map():
    from engines.data_manager.data_manager import DataManager
    dm = DataManager()
    out = {}
    for t in TICKERS:
        df = dm.load_cached(t, "1d")
        if df is not None and not df.empty:
            out[t] = df
    return out


def _instantiate_like_discovery(spec):
    """Replicate discovery._instantiate_candidate EXACTLY: cls_() then set_params."""
    mod = import_module(spec["module"])
    cls_ = getattr(mod, spec["class"])
    edge = cls_()
    if spec.get("params"):
        edge.set_params(spec["params"])
    return edge


def test_production_path_wires_genes_and_fires():
    """The load-bearing test: instantiate as Discovery does and assert genes
    populate AND compute_signals fires. FAILS on pre-fix code (genes==[])."""
    spec = {
        "module": "engines.engine_a_alpha.edges.composite_edge",
        "class": "CompositeEdge",
        "params": {"genes": [{"type": "foundry_feature", "feature_id": "mom_12_1",
                              "operator": "top_percentile", "threshold": 70}],
                   "direction": "long"},
    }
    edge = _instantiate_like_discovery(spec)
    assert len(edge.genes) == 1, "set_params did not re-bind self.genes (the bug)"
    assert edge.direction == "long"
    sig = edge.compute_signals(_data_map(), AS_OF)
    nz = sum(1 for v in sig.values() if v != 0)
    assert nz > 0, "wired foundry gene produced 0 signals"


def test_two_gene_composite_fires_via_production_path():
    """A 2-gene composite (high-momentum AND low-vol) must combine and fire."""
    spec = {
        "module": "engines.engine_a_alpha.edges.composite_edge",
        "class": "CompositeEdge",
        "params": {"genes": [
            {"type": "foundry_feature", "feature_id": "mom_12_1",
             "operator": "top_percentile", "threshold": 60},
            {"type": "foundry_feature", "feature_id": "realized_vol_60d",
             "operator": "bottom_percentile", "threshold": 50}],
            "direction": "long"},
    }
    edge = _instantiate_like_discovery(spec)
    assert len(edge.genes) == 2
    sig = edge.compute_signals(_data_map(), AS_OF)
    nz = sum(1 for v in sig.values() if v != 0)
    assert nz > 0, "2-gene composite produced 0 signals"
    # AND-logic: composite winners must be a subset of the momentum-only winners
    mom_only = _instantiate_like_discovery({
        "module": "engines.engine_a_alpha.edges.composite_edge", "class": "CompositeEdge",
        "params": {"genes": [spec["params"]["genes"][0]], "direction": "long"}})
    mom_win = {k for k, v in mom_only.compute_signals(_data_map(), AS_OF).items() if v != 0}
    comp_win = {k for k, v in sig.items() if v != 0}
    assert comp_win <= mom_win, "AND-composite winners must be a subset of gene-0 winners"


def test_set_params_refresh_is_idempotent_and_updatable():
    """Calling set_params again must REPLACE the working state (not append)."""
    from engines.engine_a_alpha.edges.composite_edge import CompositeEdge
    e = CompositeEdge()
    assert e.genes == []
    e.set_params({"genes": [{"type": "foundry_feature", "feature_id": "mom_12_1",
                            "operator": "top_percentile", "threshold": 70}], "direction": "long"})
    assert len(e.genes) == 1 and e.direction == "long"
    e.set_params({"genes": [], "direction": "short"})
    assert e.genes == [] and e.direction == "short"


def test_autogen_siblings_refresh_direction():
    """The sibling set-once bug class: autogen edges refresh direction via set_params."""
    from engines.engine_a_alpha.edges.autogen_phase3_long import AutogenPhase3Long
    e = AutogenPhase3Long()
    e.set_params({"direction": "short"})
    assert e.direction == "short", "autogen direction did not refresh via set_params"


def test_rsi_bounce_v1_non_regression():
    """The standalone hand-written edge must still construct + compute (it never
    used the composite path; this guards against collateral damage)."""
    from engines.engine_a_alpha.edges.rsi_bounce import RSIBounceEdge
    e = RSIBounceEdge()
    sig = e.compute_signals(_data_map(), AS_OF)
    assert isinstance(sig, dict)  # produces a signal map without error


def test_instantiate_candidate_constructor_form_hydrates_genes():
    """Belt-and-suspenders (T-179): the ACTUAL Discovery helper
    _instantiate_candidate now uses the params-constructor, so genes hydrate
    even if a future edge forgets the set_params override."""
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    spec = {"module": "engines.engine_a_alpha.edges.composite_edge",
            "class": "CompositeEdge",
            "params": {"genes": [{"type": "foundry_feature", "feature_id": "mom_12_1",
                                 "operator": "top_percentile", "threshold": 70}],
                       "direction": "long"}}
    edge = DiscoveryEngine._instantiate_candidate(spec)
    assert len(edge.genes) == 1 and edge.direction == "long"
    sig = edge.compute_signals(_data_map(), AS_OF)
    assert sum(1 for v in sig.values() if v != 0) > 0


def test_instantiate_candidate_typeerror_fallback_for_no_params_edge():
    """Edges whose __init__ does not accept params= (e.g. RSIBounceEdge) must
    still instantiate via the construct-then-set_params fallback, with params set."""
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    spec = {"module": "engines.engine_a_alpha.edges.rsi_bounce",
            "class": "RSIBounceEdge", "params": {"rsi_period": 14}}
    edge = DiscoveryEngine._instantiate_candidate(spec)
    assert type(edge).__name__ == "RSIBounceEdge"
    assert edge.params.get("rsi_period") == 14  # fallback applied set_params


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
