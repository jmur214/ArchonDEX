"""T-2026-06-13-164 (P0): fetch_historical_fundamentals must be hermetic-safe.

The live yfinance fall-through was the one network path T-155 left unguarded;
under hermetic it aborted the whole cloud run (zero trades). These tests prove
the guard fires (uncovered ticker → empty, no network) while the cached path is
untouched. Fast, deterministic, no real network."""
from __future__ import annotations

import pandas as pd
import pytest

from engines.data_manager import data_manager as dmmod


def _dm():
    from pathlib import Path
    dm = dmmod.DataManager.__new__(dmmod.DataManager)
    dm.cache_dir = Path("data/processed")
    dm.api_key = dm.secret_key = dm.base_url = None
    return dm


def test_uncovered_ticker_hermetic_returns_empty_no_network(monkeypatch, capsys):
    """Under hermetic, an uncovered ticker returns empty via the guard and
    NEVER reaches yfinance (monkeypatched to explode if touched)."""
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")   # warn/block mode (= cloud)
    monkeypatch.setattr(dmmod.yf, "Ticker",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("network touched")))
    out = _dm().fetch_historical_fundamentals("ZZZZ_NOT_A_REAL_TICKER")
    assert isinstance(out, pd.DataFrame) and out.empty
    assert "[HERMETIC] BLOCKED" in capsys.readouterr().out


def test_without_guard_uncovered_reaches_yfinance(monkeypatch):
    """Demonstrates the BUG class: with hermetic OFF (local), an uncovered
    ticker DOES reach the live yfinance call — the very call that, on the
    no-network cloud, HANGS (the try/except swallows errors but cannot rescue a
    no-timeout blocking read → zero cloud trades). The hermetic guard is what
    prevents reaching it on cloud. Here we record that yf.Ticker is called."""
    monkeypatch.delenv("ARCHONDEX_HERMETIC", raising=False)
    calls = []

    def _record(tk, *a, **k):
        calls.append(tk)
        raise RuntimeError("simulated no-network")   # swallowed by the path's except
    monkeypatch.setattr(dmmod.yf, "Ticker", _record)
    out = _dm().fetch_historical_fundamentals("ZZZZ_NOT_A_REAL_TICKER")
    assert calls == ["ZZZZ_NOT_A_REAL_TICKER"]       # the dangerous call WAS reached
    assert out.empty                                  # except swallows -> empty (local)


def test_cached_ticker_unaffected_by_guard(monkeypatch):
    """A covered ticker (baked parquet) returns its cache regardless of
    hermetic — the guard sits AFTER the cache/static checks, so behavior on the
    common path is byte-unchanged."""
    from pathlib import Path
    pq = Path("data/processed/parquet")
    covered = next((f.name.replace("_fundamentals.parquet", "")
                    for f in pq.glob("*_fundamentals.parquet")
                    if not pd.read_parquet(f).empty), None)
    if covered is None:
        pytest.skip("no non-empty fundamentals parquet on disk")
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    monkeypatch.setattr(dmmod.yf, "Ticker",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not fetch")))
    out = _dm().fetch_historical_fundamentals(covered)
    assert not out.empty   # served from the baked parquet, no network


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
