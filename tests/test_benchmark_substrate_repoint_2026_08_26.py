"""Benchmark substrate repoint (2026-08-26) — T-256 sourcing + fail-closed coverage.

The defect: `data/processed/` ETF benchmarks (QQQ, TLT, ...) were never backfilled
past 2020-04-09, so a benchmark over a deep window silently covered only the
post-COVID bull. Measured on 2005-2026: QQQ Sharpe read 0.998 instead of 0.753,
inflating the promotion gate's threshold by ~0.245.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core import benchmark as bench
from core.benchmark import BenchmarkCoverageError


def _write(dirpath: Path, ticker: str, start: str, periods: int, seed: int = 0):
    dirpath.mkdir(parents=True, exist_ok=True)
    idx = pd.bdate_range(start, periods=periods)
    px = 100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0004, 0.01, periods)))
    pd.DataFrame({"Date": idx, "Close": px}).to_csv(dirpath / f"{ticker}_1d.csv", index=False)


@pytest.fixture
def iso(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "DEFAULT_DATA_DIR", tmp_path)
    bench.compute_benchmark_metrics.cache_clear()
    bench._first_date.cache_clear()
    yield tmp_path
    bench.compute_benchmark_metrics.cache_clear()


# ---- T-256 sourcing ---------------------------------------------------------

def test_tr_reconciled_is_preferred_over_the_flat_price_only_copy(iso):
    _write(iso, "SPY", "2010-01-01", 500, seed=1)                 # flat, price-only
    _write(iso / "tr_reconciled", "SPY", "2010-01-01", 500, seed=2)  # dividend-reconciled
    assert bench._resolve_path("SPY").parent.name == "tr_reconciled"
    assert bench._source_of("SPY") == "tr_reconciled"


def test_falls_back_to_the_flat_copy_when_tr_reconciled_lacks_the_ticker(iso):
    _write(iso, "AAPL", "2010-01-01", 500)
    assert bench._resolve_path("AAPL").parent.name != "tr_reconciled"
    assert bench._source_of("AAPL") == "processed"


def test_path_resolution_honours_a_swapped_data_dir_HERMETICITY(iso):
    """The regression that bit during this fix: a module-level TR_RECONCILED_DIR
    frozen at import silently defeated DEFAULT_DATA_DIR overrides, so an isolated
    run read PRODUCTION prices. The tr dir must resolve from the EFFECTIVE base."""
    _write(iso / "tr_reconciled", "SPY", "2021-01-01", 300, seed=3)
    resolved = bench._resolve_path("SPY")
    assert str(resolved).startswith(str(iso)), f"escaped the isolated dir: {resolved}"


def test_reported_source_cannot_drift_from_the_file_actually_read(iso):
    """`_source_of` and `_load_benchmark_prices` must share one rule — they
    briefly did not, and the provenance field misreported."""
    _write(iso, "SPY", "2010-01-01", 400, seed=4)
    _write(iso / "tr_reconciled", "SPY", "2010-01-01", 400, seed=5)
    for t in ("SPY",):
        assert (bench._source_of(t) == "tr_reconciled") == \
               (bench._resolve_path(t).parent.name == "tr_reconciled")


# ---- fail-closed coverage ---------------------------------------------------

def test_the_real_defect_shape_is_caught_SPY_deep_QQQ_truncated(iso):
    """The exact production shape: SPY deep, QQQ stopping at the 2020-04 Alpaca
    boundary. Either guard is a correct catch; what matters is that no threshold
    is produced and the message names the offender."""
    _write(iso / "tr_reconciled", "SPY", "2006-01-02", 3000, seed=6)
    _write(iso / "tr_reconciled", "QQQ", "2020-04-09", 400, seed=7)   # the shallow copy
    _write(iso / "tr_reconciled", "TLT", "2006-01-02", 3000, seed=8)
    with pytest.raises(BenchmarkCoverageError) as e:
        bench.compute_multi_benchmark_metrics("2006-01-02", "2026-01-01")
    assert "QQQ" in str(e.value)


def test_unequal_coverage_RAISES_even_when_all_reach_the_requested_start(iso):
    """G2 in isolation: every benchmark covers the start, but one ENDS early —
    so the request-coverage check passes and only the cross-benchmark check can
    see that a strongest-of threshold would span different periods."""
    _write(iso / "tr_reconciled", "SPY", "2006-01-02", 3000, seed=16)
    _write(iso / "tr_reconciled", "QQQ", "2006-01-02", 1200, seed=17)   # ends years early
    _write(iso / "tr_reconciled", "TLT", "2006-01-02", 3000, seed=18)
    with pytest.raises(BenchmarkCoverageError) as e:
        bench.compute_multi_benchmark_metrics("2006-01-02", "2018-01-01")
    assert "UNEQUAL" in str(e.value) and "QQQ" in str(e.value)


def test_all_benchmarks_truncating_TOGETHER_still_raises(iso):
    """The case a cross-benchmark check alone cannot see: three benchmarks that
    agree with each other and all silently ignore the requested history."""
    for t in ("SPY", "QQQ", "TLT"):
        _write(iso / "tr_reconciled", t, "2020-04-09", 400, seed=9)
    with pytest.raises(BenchmarkCoverageError) as e:
        bench.compute_multi_benchmark_metrics("2006-01-02", "2022-01-01")
    assert "does not reach the requested start" in str(e.value)


def test_equal_full_coverage_passes_cleanly(iso):
    for i, t in enumerate(("SPY", "QQQ", "TLT")):
        _write(iso / "tr_reconciled", t, "2010-01-04", 1200, seed=20 + i)
    m = bench.compute_multi_benchmark_metrics("2010-01-04", "2014-08-01")
    assert len(m) == 3
    assert all(b.source.startswith("tr_reconciled") for b in m.values())
    assert min(b.n_obs for b in m.values()) / max(b.n_obs for b in m.values()) >= bench.COVERAGE_TOLERANCE


def test_the_escape_hatch_is_EXPLICIT_not_a_silent_default(iso):
    """`[NN-FAIL-CLOSED]`: degradation is allowed only when the caller says so."""
    _write(iso / "tr_reconciled", "SPY", "2006-01-02", 3000, seed=10)
    _write(iso / "tr_reconciled", "QQQ", "2020-04-09", 400, seed=11)
    _write(iso / "tr_reconciled", "TLT", "2006-01-02", 3000, seed=12)
    m = bench.compute_multi_benchmark_metrics("2006-01-02", "2026-01-01", allow_unequal_coverage=True)
    assert m["QQQ"].n_obs < m["SPY"].n_obs        # the mismatch is returned, not hidden
    assert m["QQQ"].first_obs and m["QQQ"].last_obs   # ...and it is inspectable


def test_the_gate_propagates_the_guard_rather_than_thresholding_on_bad_data(iso):
    _write(iso / "tr_reconciled", "SPY", "2006-01-02", 3000, seed=13)
    _write(iso / "tr_reconciled", "QQQ", "2020-04-09", 400, seed=14)
    _write(iso / "tr_reconciled", "TLT", "2006-01-02", 3000, seed=15)
    with pytest.raises(BenchmarkCoverageError):
        bench.gate_sharpe_vs_benchmark(0.6, "2006-01-02", "2026-01-01")


def test_metrics_carry_provenance_so_a_reader_can_audit_the_window(iso):
    _write(iso / "tr_reconciled", "SPY", "2015-01-01", 800, seed=16)
    b = bench.compute_benchmark_metrics("2015-01-01", "2018-01-01", ticker="SPY")
    assert b.source == "tr_reconciled"
    assert b.first_obs and b.last_obs
    assert pd.Timestamp(b.first_obs) <= pd.Timestamp(b.last_obs)
