"""ARCHIVED 2026-11-04 at the merge of the edges.yml single-writer unit (3a3edf4) onto main.

This helper observed an edge module's IMPORT-TIME write by re-importing it with `EdgeRegistry`
bound to a tmp store. Since the single-writer unit `ensure()` records in memory and never writes,
so the re-import leaves the tmp store absent (witnessed at the merge: store.exists() == False,
the registration only in `EdgeRegistry.import_registrations()`). Its three consumers
(tests/test_buyback_dividend_drift_edges.py, tests/test_cross_sectional_momentum_edges.py,
tests/test_fundamentals_edges.py) observe registration through the explicit sync on a tmp
registry (`scripts.sync_edge_registry.sync(tmp, modules=[...])`) instead. Kept, never deleted
([NN-ARCHIVE]). The original module follows.

--- the original module docstring ---

Observe an edge module's IMPORT-TIME self-registration against a tmp registry (2026-10-22).

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
