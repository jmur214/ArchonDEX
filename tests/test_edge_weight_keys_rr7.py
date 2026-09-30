"""Every `edge_weights` key must name a real edge (RR-7, 2026-09-30).

The defect class: a config key that matches no edge. The lookup is
`edge_weights.get(edge_name, 1.0)`, so a mismatched key is not an error — it is a
weight that silently describes nothing, and the edge (if it ever loads) runs at 1.0.

WHAT "A REAL EDGE" MEANS, and why the definition had to be widened. Edges get their
identity two ways:
  * a class attribute `EDGE_ID = "..."` on a concrete edge class, and
  * a REGISTRY entry in edges.yml for PARAMETRISED classes — `growth_sales_v1` and
    `value_deep_v1` are both instances of the generic `fundamental_ratio` module and
    have no hardcoded EDGE_ID anywhere.
A check against class attributes alone falsely flags the parametrised two; a check
against the registry alone falsely flags `news_sentiment_v2`, which is declared but
unregistered. Only the union is correct — found by running both before writing this.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PROD_CFG = REPO / "config/alpha_settings.prod.json"
EDGES_DIR = REPO / "engines/engine_a_alpha/edges"
REGISTRY_CANDIDATES = [REPO / "data/governor/edges.yml",
                       REPO.parent / "trading_machine-2/data/governor/edges.yml"]


def _declared_edge_ids() -> set:
    ids = set()
    for f in EDGES_DIR.rglob("*.py"):
        for m in re.finditer(r'^\s+EDGE_ID\s*=\s*["\']([^"\']+)["\']', f.read_text(), re.M):
            ids.add(m.group(1))
    return ids


def _registry_edge_ids():
    for p in REGISTRY_CANDIDATES:
        if p.exists():
            return set(re.findall(r"edge_id:\s*(\S+)", p.read_text()))
    return None


def test_every_prod_edge_weight_key_names_a_real_edge():
    registry = _registry_edge_ids()
    if registry is None:
        # Without the registry, the parametrised edges cannot be told from typos. A
        # verdict produced on half the evidence would be a confident wrong answer.
        pytest.skip("edges.yml not on disk in this environment — cannot evaluate the "
                    "registry half of the rule honestly")
    valid = _declared_edge_ids() | registry
    keys = json.loads(PROD_CFG.read_text()).get("edge_weights", {})
    bad = sorted(k for k in keys if k not in valid)
    assert not bad, (f"edge_weights keys that match NO edge (neither a class EDGE_ID nor a "
                     f"registry edge_id): {bad} — each is a weight that describes nothing")


def test_the_rule_must_accept_PARAMETRISED_registry_edges():
    """The two a class-attribute-only check would falsely flag."""
    registry = _registry_edge_ids()
    if registry is None:
        pytest.skip("edges.yml not on disk")
    for pid in ("growth_sales_v1", "value_deep_v1"):
        assert pid not in _declared_edge_ids(), f"{pid} is parametrised, not class-declared"
        assert pid in registry


def test_the_rule_must_accept_DECLARED_but_unregistered_edges():
    """The one a registry-only check would falsely flag."""
    assert "news_sentiment_v2" in _declared_edge_ids()


def test_the_stale_key_is_gone_and_the_correct_one_is_present():
    keys = json.loads(PROD_CFG.read_text()).get("edge_weights", {})
    assert "news_sentiment_edge" not in keys
    assert keys.get("news_sentiment_v2") == 0.5, "the intended weight is preserved, only renamed"
