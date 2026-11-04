"""Observe an edge module's IMPORT-TIME self-registration against a tmp registry (2026-10-22).

Every edge module does `EdgeRegistry().ensure(EdgeSpec(...))` at import, into the live
data/governor/edges.yml. A test that then READ that file depended on the import-time writer (a
separate unit retires it) and on the tree holding the pinned file — in a clean worktree the file
is whatever collection regenerated. This re-executes the module with `EdgeRegistry` bound to a
tmp store, so the spec the module registers is observed where it is written, and nothing under
data/ is touched.
"""
from __future__ import annotations

import functools
import importlib
from pathlib import Path
from types import ModuleType

from engines.engine_a_alpha import edge_registry as _er


def registry_from_reimport(monkeypatch, tmp_path: Path, *modules: ModuleType) -> _er.EdgeRegistry:
    """Re-import `modules` with `EdgeRegistry()` pointed at <tmp_path>/edges.yml; return that
    registry, holding exactly what the modules registered."""
    store = tmp_path / "edges.yml"
    monkeypatch.setattr(_er, "EdgeRegistry",
                        functools.partial(_er.EdgeRegistry, store_path=store))
    for module in modules:
        importlib.reload(module)
    return _er.EdgeRegistry(store_path=store)
