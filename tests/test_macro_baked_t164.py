"""T-2026-06-13-164 GAP 2: the macro panel must be present for a live regime.

Cloud ran regime-blind ("unknown x438") because data/macro was never baked
(Dockerfile copied only processed/raw/governor). These tests prove the causal
chain — macro present → the regime detector's VIX input loads; macro absent →
it does not (→ regime degrades to unknown) — and that the panel is now pinned
in the substrate manifest. Fast, deterministic, no backtest."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_vix_input_loads_when_macro_present():
    """The regime detector's actual input (VIX family) loads non-empty from the
    on-disk panel — i.e. a live regime is computable when macro is baked."""
    from engines.data_manager import MacroDataManager
    mgr = MacroDataManager()
    for series in ("VIX", "VIXCLS", "VIX3M"):
        df = mgr.load_cached(series)
        assert df is not None and not df.empty, f"{series} should load non-empty"


def test_vix_input_empty_when_macro_absent(tmp_path):
    """Pointing the loader at an empty dir (the cloud pre-fix condition) yields
    empty → the regime feature is unavailable → regime degrades to unknown.
    This is the causal mechanism the Dockerfile bake fixes."""
    from engines.data_manager import MacroDataManager
    mgr = MacroDataManager(cache_dir=tmp_path)   # no VIX parquets here
    assert mgr.load_cached("VIX").empty


def test_macro_panel_pinned_in_manifest():
    """The fix: the macro panel is now in the substrate manifest (was 0 lines),
    so it is baked + drift-protected."""
    mani = (ROOT / "config" / "substrate_manifest.sha256").read_text()
    for f in ("data/macro/VIX.parquet", "data/macro/VIXCLS.parquet",
              "data/macro/VIX3M.parquet", "data/macro/VIX9D.parquet",
              "data/macro/VIX6M.parquet"):
        assert f in mani, f"{f} must be pinned in the manifest"


def test_macro_baked_in_dockerfile():
    df = (ROOT / "Dockerfile.backtest").read_text()
    assert "COPY" in df and "data/macro/" in df, "data/macro must be COPYd"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
