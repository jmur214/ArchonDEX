"""Every edge class reachable by import is either REGISTERED in edges.yml or ARCHIVED.

The defect class (R, 2026-10-14; archived 2026-10-22): three edge modules existed in code, carried
edge ids the registry had never held, and were REFUTED in the ledger — `betting_against_beta_v1`,
`overnight_intraday_v1`, `volatility_risk_premium_v1`. Under the old import-time writer they
appeared in `edges.yml` whenever a script imported them; under pure imports they would have been
silently invisible. Neither is a state the registry (the SOLE edge authority, `[NN-NO-MANUAL-EDGES]`)
should be in: an edge class under `engines/engine_a_alpha/edges/` is registered, or it is archived.

"Registered" means the registry holds the class's `EDGE_ID`, or holds at least one row whose
`module` names the class's module (templates such as `fundamental_ratio` and `rule_based_edge` are
instantiated by Discovery under generated ids; the module reference is their registration).

The exceptions are EXPLICIT and PINNED by set equality: a new unregistered class fails this test,
and a fixed one must be removed from the list. Each carries its reason.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EDGES_DIR = REPO / "engines" / "engine_a_alpha" / "edges"
ARCHIVE_DIR = REPO / "Archive" / "engines" / "engine_a_alpha" / "edges_refuted_2026_10"
REGISTRY = REPO / "data" / "governor" / "edges.yml"

ARCHIVED_2026_10 = ("betting_against_beta_edge", "overnight_intraday_edge", "volatility_risk_premium_edge")

#: module -> reason. Classes under engines/engine_a_alpha/edges/ that are neither registered nor archived,
#: each with the reason it is tolerated. PINNED: the test asserts set EQUALITY, so this list never grows
#: silently and never keeps a fixed entry.
KNOWN_UNREGISTERED = {
    "news_sentiment_edge": "EDGE_ID news_sentiment_v2 vs the config key news_sentiment_edge — the registry-"
                           "invisibility defect, health_check anchor (11) (RR-7 D1 returned); its own "
                           "propose-first Engine-A unit",
    "xsec_momentum": "no EDGE_ID; AlphaEngine's legacy default-edge fallback (alpha_engine.py:279), which the "
                     "single-writer unit made unreachable from the registry path",
    "composite_edge": "Discovery's GA template, instantiated under generated ids; no composite row in the "
                      "registry today",
    "autogen_phase2_complex_test": "GA-generated specimen (Phase 2); used by no registry row",
    "autogen_phase2_rank_test": "GA-generated specimen (Phase 2); used by no registry row",
    "autogen_phase3_long": "GA-generated specimen (Phase 3); tests/test_composite_genes_wiring_t179.py imports it",
    "autogen_phase3_short": "GA-generated specimen (Phase 3); used by no registry row",
}


def _registry_ids_and_modules():
    """(edge ids, module names both bare and dotted) from the live registry, through the ONE reader."""
    if not REGISTRY.exists():
        pytest.skip(f"no registry at {REGISTRY} — a fresh checkout refuses until "
                    f"`python scripts/sync_edge_registry.py` has run once")
    import yaml
    rows = yaml.safe_load(REGISTRY.read_text())["edges"]
    ids = {r["edge_id"] for r in rows}
    mods = set()
    for r in rows:
        m = str(r.get("module", ""))
        if m:
            mods.add(m)
            mods.add(m.rsplit(".", 1)[-1])
    return ids, mods


def _edge_classes():
    """{module name: [(class name, EDGE_ID)]} for every EdgeBase subclass DEFINED in a module under edges/."""
    from engines.engine_a_alpha.edge_base import EdgeBase
    import engines.engine_a_alpha.edges as pkg
    out = {}
    for m in pkgutil.iter_modules(pkg.__path__):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{pkg.__name__}.{m.name}")
        classes = [(name, getattr(cls, "EDGE_ID", None))
                   for name, cls in inspect.getmembers(mod, inspect.isclass)
                   if cls.__module__ == mod.__name__ and issubclass(cls, EdgeBase)]
        if classes:
            out[m.name] = classes
    return out


def test_every_edge_class_reachable_by_import_is_registered_or_a_pinned_exception():
    ids, mods = _registry_ids_and_modules()
    unregistered = {}
    for module, classes in _edge_classes().items():
        if module in mods:
            continue
        if any(eid in ids for _, eid in classes if eid):
            continue
        unregistered[module] = classes
    assert set(unregistered) == set(KNOWN_UNREGISTERED), (
        f"edge classes neither registered in edges.yml nor archived, outside the pinned exception list:\n"
        f"  new: { {m: unregistered[m] for m in set(unregistered) - set(KNOWN_UNREGISTERED)} }\n"
        f"  fixed (remove from KNOWN_UNREGISTERED): {sorted(set(KNOWN_UNREGISTERED) - set(unregistered))}\n"
        f"register it (scripts/sync_edge_registry.py) or archive it (Archive/, never delete)")


def test_the_three_refuted_edges_are_archived_and_nothing_imports_their_old_path():
    """The 2026-10-22 archive: the modules are gone from the package, present under Archive/, and no
    module under engines/, scripts/, core/ or orchestration/ imports them from the old path (AST, not grep:
    an `import` / `from … import` of the old dotted name)."""
    for name in ARCHIVED_2026_10:
        assert not (EDGES_DIR / f"{name}.py").exists(), f"{name} is still under engines/engine_a_alpha/edges/"
        assert (ARCHIVE_DIR / f"{name}.py").exists(), f"{name} is not under {ARCHIVE_DIR}"
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"engines.engine_a_alpha.edges.{name}")
    assert (ARCHIVE_DIR / "README.md").exists()

    old = {f"engines.engine_a_alpha.edges.{n}" for n in ARCHIVED_2026_10}
    offenders = []
    for top in ("engines", "scripts", "core", "orchestration"):
        for p in (REPO / top).rglob("*.py"):
            try:
                tree = ast.parse(p.read_text())
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module in old:
                    offenders.append(f"{p.relative_to(REPO)}:{n.lineno}")
                elif isinstance(n, ast.Import) and any(a.name in old for a in n.names):
                    offenders.append(f"{p.relative_to(REPO)}:{n.lineno}")
    assert not offenders, f"imports of the archived modules' old path: {offenders}"


def test_the_frozen_b1_inventory_resolves_the_archived_edges_from_the_archive():
    """scripts/build_signal_panel_b1.py's inventory is a frozen pre-registration naming two archived
    edges; its loader resolves them from the archive path and every other entry from the package."""
    from scripts import build_signal_panel_b1 as b1
    edges = b1.make_edges({"overnight_intraday_v1": b1.MAIN_EDGES["overnight_intraday_v1"],
                           "betting_against_beta_v1": b1.SENSITIVITY_EDGES["betting_against_beta_v1"],
                           "momentum_12_1_v1": b1.SENSITIVITY_EDGES["momentum_12_1_v1"]})
    assert type(edges["overnight_intraday_v1"]).__module__.startswith("Archive.")
    assert type(edges["betting_against_beta_v1"]).__module__.startswith("Archive.")
    assert type(edges["momentum_12_1_v1"]).__module__ == "engines.engine_a_alpha.edges.momentum_12_1_v1"
