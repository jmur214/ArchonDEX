"""ValueTrapEdge: a technical trigger (RSI) gated by a per-ticker fundamentals frame.

2026-10-22: this test built a REAL `DataManager()` and let `compute_signals` call
`fetch_historical_fundamentals("AAPL")`, which on a cache miss fetched from yfinance and WROTE
parquet/AAPL_fundamentals.parquet into the pinned cache (through a worktree's data/processed
symlink — the manifest's EXTRA count moved 134 -> 135). The data layer is stubbed here: a
tmp_path cache root in place of data/processed and a synthetic fundamentals frame in place of
the provider. What is tested is the edge's logic: the trigger fires, the fundamentals are
fetched once and cached on the edge.
"""
from __future__ import annotations

import pandas as pd
import pytest

from engines.data_manager.data_manager import DataManager
from engines.engine_a_alpha.edges import fundamental_value as fv


@pytest.fixture
def stubbed_data_layer(tmp_path, monkeypatch):
    """`DataManager()` inside the edge -> a tmp cache root; the provider -> a synthetic frame."""
    monkeypatch.setattr(fv, "DataManager",
                        lambda *a, **k: DataManager(cache_dir=tmp_path / "processed"))
    dates = pd.date_range("2023-01-01", periods=100)
    fundamentals = pd.DataFrame({"PE_Ratio": 15.0, "Market_Cap": 2.5e12, "EPS_TTM": 6.0},
                                index=dates)
    fetched: list[str] = []

    def fake_fetch(self, ticker):
        fetched.append(ticker)
        return fundamentals
    monkeypatch.setattr(DataManager, "fetch_historical_fundamentals", fake_fetch)
    return fetched


def test_value_edge(stubbed_data_layer, tmp_path):
    edge = fv.ValueTrapEdge({"max_pe": 100.0, "max_rsi": 100.0})   # generous gates: must trigger
    assert edge.dm.cache_dir == tmp_path / "processed", "the edge's DataManager is the stub"

    dates = pd.date_range("2023-01-01", periods=100)
    prices = [100.0] * 80 + [100.0 * (0.95 ** i) for i in range(20)]   # a sharp drop -> RSI < 30
    df = pd.DataFrame({"Close": prices, "Volume": [1000] * 100}, index=dates)

    signals = edge.compute_signals({"AAPL": df}, df.index[-1])

    assert "AAPL" in signals
    assert "AAPL" in edge.fundamental_cache
    assert stubbed_data_layer == ["AAPL"], "fundamentals fetched exactly once, from the stub"
    assert not (tmp_path / "processed" / "parquet" / "AAPL_fundamentals.parquet").exists()
