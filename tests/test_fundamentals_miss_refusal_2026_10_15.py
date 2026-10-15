"""The fundamentals miss-refusal (re-pin #1's decision; R's and the director's rulings, 2026-10-15).

The per-ticker fundamentals cache is a PINNED measurement input whose one runtime write path was a
cache MISS fetched from the network into the pinned scope (B-1's four files arrived that way, inside
a measurement). Locks, each driving the real code on planted inputs:
  * under the canonical switch (the SAME one as the price fallback) a miss is REFUSED — recorded,
    never fetched, never written — through both entry points (prefetch and the direct fetch);
  * without the switch a miss that reaches the network is recorded WITH ITS SOURCE, is written, says
    so in a WARN, and the census gate fails the run: an unpinned input entered mid-run (A);
  * refused or blocked names count into fundamentals_blind only when a per-ticker consumer is
    LOADED, read from the edge class's declared attribute, through proxies (B);
  * Gate 1: a planted blind candidate reads NOT_EVALUATED with the reason, never "contributing";
  * the prefetch docstring is true: an OLD cached file is never re-fetched;
  * a run starts with an empty miss log.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.census import assert_census
from engines.data_manager import data_manager as dmmod


@pytest.fixture(autouse=True)
def _clean_log(monkeypatch):
    dmmod.reset_fundamentals_log()
    monkeypatch.delenv(dmmod.REFUSE_YFINANCE_ENV, raising=False)
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "0")
    yield
    dmmod.reset_fundamentals_log()


def _dm(tmp_path) -> dmmod.DataManager:
    dm = dmmod.DataManager.__new__(dmmod.DataManager)
    dm.cache_dir = Path(tmp_path) / "processed"
    (dm.cache_dir / "parquet").mkdir(parents=True, exist_ok=True)
    dm.api_key = dm.secret_key = dm.base_url = None
    return dm


def _no_network(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("the network was touched")
    monkeypatch.setattr(dmmod.yf, "Ticker", _boom)


class _FakeTicker:
    """Enough of yfinance for the deep fetch to build a non-empty frame."""
    def __init__(self, *_a, **_k):
        q = pd.to_datetime(["2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31",
                            "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"])
        self.quarterly_income_stmt = pd.DataFrame(
            {d: {"Total Revenue": 1e9, "Net Income": 1e8, "Basic Average Shares": 1e7} for d in q})
        self.quarterly_balance_sheet = pd.DataFrame(
            {d: {"Stockholders Equity": 5e8, "Total Debt": 2e8} for d in q})
        self.quarterly_cashflow = pd.DataFrame(
            {d: {"Operating Cash Flow": 2e8, "Capital Expenditure": -5e7} for d in q})

    def history(self, start=None, end=None, **_k):
        idx = pd.bdate_range("2023-01-02", pd.Timestamp.now().normalize())
        return pd.DataFrame({"Close": np.linspace(50, 80, len(idx))}, index=idx)


# ---------------------------------------------------------------- the refusal ---------------------

def test_under_the_canonical_switch_a_miss_is_REFUSED_never_fetched_never_written(tmp_path, monkeypatch):
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    out = dm.fetch_historical_fundamentals("MISS1")
    assert isinstance(out, pd.DataFrame) and out.empty
    assert not dm._fundamentals_cache_path("MISS1").exists()
    s = dmmod.fundamentals_miss_summary()
    assert s["refused"] == ["MISS1"] and s["fetched"] == [] and s["sources"] == {}


def test_the_PREFETCH_under_the_switch_refuses_every_miss_and_writes_nothing(tmp_path, monkeypatch):
    """prefetch_fundamentals runs for every ticker on every backtest (mode_controller), whatever
    edges are active — the write path B-1's four files came through."""
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    dm.prefetch_fundamentals(["MISS1", "MISS2", "SPY"])          # SPY: skipped as an ETF
    assert dmmod.fundamentals_miss_summary()["refused"] == ["MISS1", "MISS2"]
    assert list((dm.cache_dir / "parquet").glob("*_fundamentals.parquet")) == []


def test_a_CACHED_file_is_read_and_records_no_miss_under_the_switch(tmp_path, monkeypatch):
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    pd.DataFrame({"PE_Ratio": [10.0]}, index=pd.DatetimeIndex(["2024-01-02"])).to_parquet(
        dm._fundamentals_cache_path("HAVE"))
    assert not dm.fetch_historical_fundamentals("HAVE").empty
    assert dmmod.fundamentals_miss_summary()["refused"] == []


def test_the_prefetch_NEVER_refetches_an_old_cached_file__the_docstring_is_true(tmp_path, monkeypatch):
    """The old docstring claimed a 7-day refresh; the code never re-fetched a cached file."""
    import os
    import time
    _no_network(monkeypatch)                                    # switch OFF: the network is allowed
    dm = _dm(tmp_path)
    p = dm._fundamentals_cache_path("OLD")
    pd.DataFrame({"PE_Ratio": [10.0]}, index=pd.DatetimeIndex(["2024-01-02"])).to_parquet(p)
    old = time.time() - 90 * 86400
    os.utime(p, (old, old))
    dm.prefetch_fundamentals(["OLD"], max_age_days=7)
    dm.prefetch_fundamentals(["OLD"], force=True)
    assert dmmod.fundamentals_miss_summary()["fetched"] == []


# ---------------------------------------------------------------- A: a fetched miss fails ---------

def test_without_the_switch_a_FETCHED_miss_is_recorded_with_its_SOURCE_written_and_WARNED(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dmmod.yf, "Ticker", _FakeTicker)
    dm = _dm(tmp_path)
    out = dm.fetch_historical_fundamentals("NEWT")
    assert not out.empty and dm._fundamentals_cache_path("NEWT").exists()
    s = dmmod.fundamentals_miss_summary()
    assert s["fetched"] == ["NEWT"] and s["sources"] == {"NEWT": "yfinance"}
    assert "WRITTEN into the pinned scope" in capsys.readouterr().out
    v = assert_census({"census": {"fundamentals_misses": s}, "bootstrap_ci_skip_reason": "t"})
    msg = [f for f in v.failures if f.startswith("fundamentals_misses")]
    assert msg and "unpinned input(s) entered mid-run" in msg[0] and "NEWT (yfinance)" in msg[0]


def test_a_REFUSED_miss_alone_is_not_an_unpinned_input():
    s = {"refused": ["X"], "blocked": [], "fetched": [], "empty": [], "sources": {}}
    v = assert_census({"census": {"fundamentals_misses": s}, "bootstrap_ci_skip_reason": "t"})
    assert not [f for f in v.failures if f.startswith("fundamentals_misses")]


def test_an_ERRORED_miss_record_fails_the_gate():
    v = assert_census({"census": {"fundamentals_misses": {"error": "boom"}},
                       "bootstrap_ci_skip_reason": "t"})
    assert any("fundamentals_misses record errored" in f for f in v.failures)


def test_under_HERMETIC_a_miss_is_recorded_BLOCKED(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    _no_network(monkeypatch)
    _dm(tmp_path).fetch_historical_fundamentals("HERM")
    assert dmmod.fundamentals_miss_summary()["blocked"] == ["HERM"]


# ---------------------------------------------------------------- B: blind names, by declaration --

class _Consumer:
    READS_TICKER_FUNDAMENTALS = True


class _NotAConsumer:
    pass


class _Proxy:                                  # the Gate-1 cache / counting proxy shape
    def __init__(self, inner):
        self._wrapped = inner


def test_blind_names_count_ONLY_when_a_declared_consumer_is_loaded_even_behind_a_proxy():
    dmmod._FUNDAMENTALS_LOG.update({"A": "refused", "B": "blocked", "C": "fetched"})
    none = dmmod.ticker_fundamentals_blind({"momentum_v1": _NotAConsumer()})
    assert none == {"consumers": [], "blind_names": []}
    some = dmmod.ticker_fundamentals_blind({"fundamental_ratio_v1_mut_x": _Proxy(_Proxy(_Consumer())),
                                            "momentum_v1": _NotAConsumer()})
    assert some == {"consumers": ["fundamental_ratio_v1_mut_x"], "blind_names": ["A", "B"]}


def test_the_REAL_consumer_classes_declare_the_attribute():
    from engines.engine_a_alpha.edges.composite_edge import CompositeEdge
    from engines.engine_a_alpha.edges.fundamental_ratio import FundamentalRatioEdge
    from engines.engine_a_alpha.edges.fundamental_value import ValueTrapEdge
    assert all(getattr(c, "READS_TICKER_FUNDAMENTALS", False) is True
               for c in (CompositeEdge, FundamentalRatioEdge, ValueTrapEdge))


def test_the_BACKTEST_census_counts_blind_names_for_a_loaded_consumer_and_its_gate_names_them(tmp_path):
    from backtester.backtest_controller import BacktestController

    class _Alpha:
        class collector:
            _signal_counts, _bars_collected, _edge_errors, _edge_error_samples = {"c": 3}, 40, {}, {}

        class processor:
            paused_edge_ids: set = set()

    dmmod._FUNDAMENTALS_LOG.update({"NAME1": "refused", "NAME2": "refused"})
    idx = pd.bdate_range("2025-01-02", periods=20)
    ctrl = object.__new__(BacktestController)
    ctrl.alpha, ctrl.regime_detector = _Alpha(), object()
    ctrl.alpha.edges = {"fundamental_ratio_v1_mut_x": _Consumer()}
    ctrl.data_map = {t: pd.DataFrame({"Close": 1.0}, index=idx) for t in ("SPY", "AAA")}
    ctrl._census_n_resolved, ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 2, 40, 3
    ctrl._membership_intervals, ctrl._census_universe = None, ["SPY", "AAA"]
    ctrl._census_window = (str(idx[0].date()), str(idx[-1].date()))
    p = tmp_path / "trades.csv"
    pd.DataFrame({"ticker": ["AAA"], "pnl": [1.0]}).to_csv(p, index=False)
    census = ctrl._build_census(str(p))
    assert census["fundamentals_blind_names"] == ["NAME1", "NAME2"]
    assert census["fundamentals_ticker_consumers"] == ["fundamental_ratio_v1_mut_x"]
    assert census["fundamentals_blind"] == 2 and census["fundamentals_misses"]["refused"] == ["NAME1", "NAME2"]
    v = assert_census({"census": census, "bootstrap_ci_skip_reason": "t"})
    assert any(f.startswith("fundamentals_blind") and "NAME1" in f for f in v.failures), v.failures
    # the same misses with NO consumer loaded: nothing is blind
    ctrl.alpha.edges = {"momentum_v1": _NotAConsumer()}
    assert ctrl._build_census(str(p))["fundamentals_blind"] == 0


# ---------------------------------------------------------------- Gate 1 --------------------------

def _validate(monkeypatch, cand_edge):
    import tests.test_discovery_gates_7_8 as g78
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    data_map, idx = g78._make_synthetic_dfs()
    rets = pd.Series(0.001, index=idx[1:])
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": rets + 0.0005, "daily_returns_baseline": rets},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,
                   "daily_returns_with": rets + 0.0005, "daily_returns_baseline": rets})
    monkeypatch.setattr(DiscoveryEngine, "_instantiate_candidate", staticmethod(lambda spec: cand_edge))
    return g78._make_disc().validate_candidate(g78._make_cand_spec(), data_map,
                                               significance_threshold=0.05, alpha_config={},
                                               n_trials_for_dsr=2)


class _BlindRatioCandidate:
    """A fundamental_ratio-shaped candidate: a declared consumer that emits signals."""
    READS_TICKER_FUNDAMENTALS = True
    EDGE_ID = "fundamental_ratio_v1_mut_blind"

    def compute_signals(self, data_map, now):
        return {t: 0.5 for t in data_map}


class _PlainCandidate(_BlindRatioCandidate):
    READS_TICKER_FUNDAMENTALS = False


def test_GATE_1_refuses_a_BLIND_per_ticker_consumer_candidate_NOT_EVALUATED_with_the_reason(monkeypatch):
    dmmod._FUNDAMENTALS_LOG.update({"AAA": "refused"})
    r = _validate(monkeypatch, _BlindRatioCandidate())
    g1 = r["gate_verdicts"]["gate_1"]
    assert g1["verdict"] == "not_evaluated" and "fundamentals_blind" in g1["reason"], g1
    assert r["passed_all_gates"] is False


def test_GATE_1_positive_control_the_same_misses_with_a_NON_consumer_candidate_are_not_blind(monkeypatch):
    dmmod._FUNDAMENTALS_LOG.update({"AAA": "refused"})
    r = _validate(monkeypatch, _PlainCandidate())
    assert r["gate_verdicts"]["gate_1"]["verdict"] != "not_evaluated", r["gate_verdicts"]["gate_1"]


# ---------------------------------------------------------------- the run starts clean ------------

def test_run_backtest_RESETS_the_miss_log_at_run_start(tmp_path, monkeypatch):
    import tests.test_stale_holed_guard_2026_10_15 as g
    dmmod._FUNDAMENTALS_LOG.update({"STALE_FROM_AN_EARLIER_RUN": "fetched"})
    mc = g._mode_controller(tmp_path, g._clean_map(), monkeypatch)
    with pytest.raises(g._Reached):
        mc.run_backtest()
    assert dmmod.fundamentals_miss_summary()["fetched"] == []
