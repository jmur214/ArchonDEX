"""Declared skips for data-depth tests (2026-10-22).

A test that READS the pinned cache (data/processed, data/macro, data/raw/stooq, data/governor,
data/observability, data/research, data/earnings) says so and SKIPS when its input is absent in
this tree. It never fails on the missing file, never passes silently, and never constructs a
DataManager / MacroDataManager / EarningsDataManager / EdgeRegistry first: their constructors
mkdir their cache dirs, and the data/ write guard in tests/conftest.py would then name the test.
The number of these skips is part of every clean-tree run's report.

Kept out of conftest.py on purpose: a test imports this module, and importing conftest.py again
would re-run the guard's module state.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# One marker file per pinned surface: present in a tree that holds the canonical data, absent
# in a clean worktree. The file is the real input where a test reads one file; otherwise it is
# the surface's most stable member.
CANON_SPY = "data/processed/parquet/SPY_1d.parquet"
CANON_AAPL = "data/processed/parquet/AAPL_1d.parquet"
CANON_SIMFIN_PANEL = "data/processed/fundamentals_simfin.parquet"
CANON_MACRO_VIX = "data/macro/VIX.parquet"
CANON_MACRO_HY_OAS = "data/macro/BAMLH0A0HYM2.parquet"
CANON_EARNINGS_AAPL = "data/earnings/AAPL_calendar.parquet"
CANON_GOVERNOR = "data/governor/edge_weights.json"          # the pinned governor dir, not the
                                                            # import-time-regenerated edges.yml
CANON_RUN_REGISTRY = "data/observability/run_registry.sqlite"
CANON_PAIRS_MANIFEST = "data/research/cointegrated_pairs_2026_05_09.json"
CANON_STOOQ_SPY = "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt"
CANON_STOOQ_DBMF = "data/raw/stooq/daily/us/nyse etfs/1/dbmf.us.txt"


def canonical_missing(*rel_paths: str) -> list[str]:
    return [p for p in rel_paths if not (REPO / p).exists()]


def _reason(missing: list[str]) -> str:
    return (f"declared skip: data-depth test reads the pinned cache; absent in this tree: "
            f"{missing}")


def requires_canonical(*rel_paths: str):
    """Decorator form: `@requires_canonical(CANON_SPY, CANON_STOOQ_DBMF)`."""
    missing = canonical_missing(*rel_paths)
    return pytest.mark.skipif(bool(missing), reason=_reason(missing))


def skip_unless_canonical(*rel_paths: str) -> None:
    """Imperative form for fixtures and helpers: skip NOW unless every input is on disk."""
    missing = canonical_missing(*rel_paths)
    if missing:
        pytest.skip(_reason(missing))


# --------------------------------------------------------------------------------------------
# Data-layer redirects for tests whose code under test CONSTRUCTS a manager with its default
# cache dir (the constructor mkdirs it). Each points the class at the pinned dir when this tree
# holds it (nothing is created: exist_ok) and at tmp_path otherwise. Both the submodule class
# and the package's PEP 562 re-export are patched: `from engines.data_manager import X` caches
# X on the package after the first access, so a submodule-only patch is bypassed.
# --------------------------------------------------------------------------------------------
def _pinned_or_tmp(marker: str, name: str, tmp_path: Path) -> Path:
    return (REPO / "data" / name) if (REPO / marker).exists() else tmp_path / name


def redirect_macro_manager(monkeypatch, tmp_path: Path) -> Path:
    import functools
    import engines.data_manager as pkg
    from engines.data_manager import macro_data
    cache = _pinned_or_tmp(CANON_MACRO_VIX, "macro", tmp_path)
    cls = functools.partial(macro_data.MacroDataManager, cache_dir=cache)
    monkeypatch.setattr(macro_data, "MacroDataManager", cls)
    monkeypatch.setattr(pkg, "MacroDataManager", cls, raising=False)
    return cache


def redirect_earnings_manager(monkeypatch, tmp_path: Path) -> Path:
    import functools
    import engines.data_manager as pkg
    from engines.data_manager import earnings_data
    cache = _pinned_or_tmp(CANON_EARNINGS_AAPL, "earnings", tmp_path)
    cls = functools.partial(earnings_data.EarningsDataManager, cache_dir=cache)
    monkeypatch.setattr(earnings_data, "EarningsDataManager", cls)
    monkeypatch.setattr(pkg, "EarningsDataManager", cls, raising=False)
    return cache
