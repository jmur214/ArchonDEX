"""Every `edge_weights` key must be a name the ENGINE looks weights up by (RR-7).

The defect class: a config key the engine never looks up. The lookup is
`edge_weights.get(edge_name, 1.0)` (`signal_processor.py:657`), keyed by the names
in `AlphaEngine.edges` — so a key outside that set is not an error, it is a weight
that silently describes nothing, and the edge it was meant for runs at 1.0.

WHICH NAMES THE ENGINE USES — asked of the engine, not read off the source tree.
`AlphaEngine.edges` is built from two places:
  * the registry: production (`mode_controller._load_edges_via_registry`) passes
    the edges.yml specs keyed by `edge_id` — including PARAMETRISED instances such
    as `growth_sales_v1` / `value_deep_v1`, which have no class EDGE_ID at all;
  * the engine's own always-active registrations (`alpha_engine.py:350`): the news
    edge, under the dict key `news_sentiment_edge` — NOT its class EDGE_ID.
The first version of this test (2026-09-30) used class EDGE_IDs ∪ registry ids. It
read the source, so it rejected the key the engine actually uses and endorsed a
rename that would have doubled the news edge's weight (Agent R, 2026-10-08). The
registry-invisibility defect itself is NEW-8 in test_referee_repairs_proposed.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PROD_CFG = REPO / "config/alpha_settings.prod.json"
# EdgeRegistry's own default (`data/governor/edges.yml`), resolved against the repo
# root rather than the CWD. Constructed only when present: EdgeRegistry mkdirs its
# parent and loads a missing file as an EMPTY registry, which would fail every key.
REGISTRY = REPO / "data/governor/edges.yml"


def _registry_edge_ids() -> set:
    if not REGISTRY.exists():
        # Without the registry, a parametrised edge cannot be told from a typo. A
        # verdict produced on half the evidence would be a confident wrong answer.
        pytest.skip("data/governor/edges.yml is not on disk in this environment — "
                    "cannot evaluate the registry half of the rule honestly")
    from engines.engine_a_alpha.edge_registry import EdgeRegistry
    return {s.edge_id for s in EdgeRegistry(REGISTRY).get_all_specs()}


def _engine_self_registered(monkeypatch) -> set:
    """The names AlphaEngine adds on its own, given production's non-empty edge set."""
    monkeypatch.delenv("ALPHA_INCLUDE_EXTRAS", raising=False)   # production default
    from engines.engine_a_alpha.alpha_engine import AlphaEngine
    probe = "__registry_edges_stand_in__"
    engine = AlphaEngine(edges={probe: object()}, debug=False)
    return set(engine.edges) - {probe}


def test_every_prod_edge_weight_key_is_a_name_the_engine_uses(monkeypatch):
    names = _registry_edge_ids() | _engine_self_registered(monkeypatch)
    keys = json.loads(PROD_CFG.read_text()).get("edge_weights", {})
    bad = sorted(k for k in keys if k not in names)
    assert not bad, (f"edge_weights keys the engine never looks up (neither a registry "
                     f"edge_id nor a name AlphaEngine registers itself): {bad} — each is "
                     f"a weight that describes nothing; the edge it meant runs at 1.0")


def test_the_engine_keys_the_always_active_news_edge_by_its_DICT_name(monkeypatch):
    """What makes today's config key correct, and a lone rename wrong."""
    assert "news_sentiment_edge" in _engine_self_registered(monkeypatch)


def test_the_rule_must_accept_PARAMETRISED_registry_edges():
    """Registry-only edges: instances of the generic fundamental_ratio module, with no
    class EDGE_ID anywhere — a check against class attributes would flag them."""
    registry = _registry_edge_ids()
    for pid in ("growth_sales_v1", "value_deep_v1"):
        assert pid in registry
