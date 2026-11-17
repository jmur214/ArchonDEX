"""T-392a: the static fundamentals path is REFUSED except under an explicit test flag.

`data/fundamentals_static.csv` (7 hand-made rows: AAPL PE 12.0, a flat market cap, SYNTH-A) was read
IMPLICITLY whenever it sat beside the cache and served as real fundamentals BEFORE the canonical
refusal, recorded by nothing. Locks, each driving the real `fetch_historical_fundamentals` on a
fixture this file PLANTS (never the on-disk toy):
  * no flag: a fixture at the old implicit location is never read — the name takes the ordinary miss
    path (canonical: refused and logged; hermetic: blocked; local: the network stub is reached);
  * the flag NAMES its file; every served row is labelled `fundamentals_source == "fixture"`, the
    name is logged "fixture", and the census gate FAILS the run on it (7c);
  * the flag is REFUSED (raised, before any read) in a canonical or hermetic run, through both
    entry points — prefetch does not swallow it — and a flag naming a missing file is refused.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.census import assert_census
from engines.data_manager import data_manager as dmmod

_TOY = ("Ticker,Date,PE_Ratio,Market_Cap,EPS_TTM\n"
        "AAPL,2023-01-01,12.0,2000000000000,6.0\n"
        "AAPL,2024-01-01,11.8,2200000000000,6.5\n"
        "SYNTH-A,2023-01-01,12.0,50000000000,2.0\n")


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    dmmod.reset_fundamentals_log()
    monkeypatch.delenv(dmmod.REFUSE_YFINANCE_ENV, raising=False)
    monkeypatch.delenv(dmmod.FUNDAMENTALS_FIXTURE_ENV, raising=False)
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "0")
    yield
    dmmod.reset_fundamentals_log()


def _dm(tmp_path: Path) -> dmmod.DataManager:
    dm = dmmod.DataManager.__new__(dmmod.DataManager)
    dm.cache_dir = Path(tmp_path) / "processed"
    (dm.cache_dir / "parquet").mkdir(parents=True, exist_ok=True)
    dm.api_key = dm.secret_key = dm.base_url = None
    return dm


def _plant_implicit_toy(tmp_path: Path) -> Path:
    """The toy at the location the old code read implicitly: `<cache_dir>/../fundamentals_static.csv`."""
    p = Path(tmp_path) / "fundamentals_static.csv"
    p.write_text(_TOY)
    return p


def _plant_fixture(tmp_path: Path, monkeypatch) -> Path:
    p = Path(tmp_path) / "planted_fixture.csv"
    p.write_text(_TOY)
    monkeypatch.setenv(dmmod.FUNDAMENTALS_FIXTURE_ENV, str(p))
    return p


def _record_network(monkeypatch) -> list:
    calls: list = []

    def _rec(tk, *a, **k):
        calls.append(tk)
        raise RuntimeError("simulated no-network")       # swallowed by the deep fetch -> empty
    monkeypatch.setattr(dmmod.yf, "Ticker", _rec)
    return calls


def _no_network(monkeypatch):
    monkeypatch.setattr(dmmod.yf, "Ticker",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("the network was touched")))


# ------------------------------------------------------------- no flag: the static path is closed --

def test_no_flag_CANONICAL_an_implicit_toy_is_never_served__the_name_is_REFUSED(tmp_path, monkeypatch):
    _plant_implicit_toy(tmp_path)
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    out = _dm(tmp_path).fetch_historical_fundamentals("AAPL")
    assert isinstance(out, pd.DataFrame) and out.empty, "toy rows served under the canonical switch"
    s = dmmod.fundamentals_miss_summary()
    assert s["refused"] == ["AAPL"] and s["fixture"] == []


def test_no_flag_HERMETIC_an_implicit_toy_is_never_served__the_name_is_BLOCKED(tmp_path, monkeypatch):
    _plant_implicit_toy(tmp_path)
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    _no_network(monkeypatch)
    out = _dm(tmp_path).fetch_historical_fundamentals("AAPL")
    assert out.empty and dmmod.fundamentals_miss_summary()["blocked"] == ["AAPL"]


def test_no_flag_LOCAL_an_implicit_toy_is_never_served__the_ordinary_miss_path_runs(tmp_path, monkeypatch):
    _plant_implicit_toy(tmp_path)
    calls = _record_network(monkeypatch)
    out = _dm(tmp_path).fetch_historical_fundamentals("AAPL")
    assert out.empty and calls == ["AAPL"], "the toy answered instead of the miss path"
    assert dmmod.fundamentals_miss_summary()["fixture"] == []


def test_the_summary_always_carries_a_fixture_list():
    assert dmmod.fundamentals_miss_summary()["fixture"] == []


# ------------------------------------------------------------- the flag: explicit, labelled, failed --

def test_flag_LOCAL_serves_the_planted_fixture_LABELLED_on_every_row(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    _no_network(monkeypatch)
    out = _dm(tmp_path).fetch_historical_fundamentals("AAPL")
    assert len(out) > 300 and out.index[0] == pd.Timestamp("2023-01-01")
    assert (out[dmmod.FIXTURE_SOURCE_COLUMN] == dmmod.FIXTURE_SOURCE_VALUE).all()
    assert out.loc[pd.Timestamp("2023-06-01"), "PE_Ratio"] == 12.0      # forward-filled from Jan
    assert dmmod.fundamentals_miss_summary()["fixture"] == ["AAPL"]


def test_flag_LOCAL_a_name_the_fixture_lacks_takes_the_ordinary_miss_path(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    calls = _record_network(monkeypatch)
    out = _dm(tmp_path).fetch_historical_fundamentals("MSFT")
    assert out.empty and calls == ["MSFT"]
    assert dmmod.fundamentals_miss_summary()["fixture"] == []


def test_a_fixture_served_name_FAILS_the_census_gate(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    _no_network(monkeypatch)
    _dm(tmp_path).fetch_historical_fundamentals("AAPL")
    s = dmmod.fundamentals_miss_summary()
    v = assert_census({"census": {"fundamentals_misses": s}, "bootstrap_ci_skip_reason": "t"})
    msg = [f for f in v.failures if "TEST FIXTURE" in f]
    assert msg and "AAPL" in msg[0] and not v.canonical


def test_an_empty_fixture_list_does_not_fail_the_gate():
    s = {"refused": [], "blocked": [], "fetched": [], "empty": [], "fixture": [], "sources": {}}
    v = assert_census({"census": {"fundamentals_misses": s}, "bootstrap_ci_skip_reason": "t"})
    assert not [f for f in v.failures if "TEST FIXTURE" in f]


# ------------------------------------------------------------- the flag is refused where it may not run --

def test_flag_under_the_CANONICAL_switch_is_REFUSED_before_any_read(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    with pytest.raises(dmmod.FundamentalsFixtureRefused, match="canonical"):
        dm.fetch_historical_fundamentals("AAPL")
    assert getattr(dm, "_fixture_cache", None) is None, "the fixture was read"
    s = dmmod.fundamentals_miss_summary()
    assert s["fixture"] == [] and s["refused"] == [] and s["fixture_refused"] == ["AAPL"]
    v = assert_census({"census": {"fundamentals_misses": s}, "bootstrap_ci_skip_reason": "t"})
    assert any("TEST FIXTURE flag" in f for f in v.failures) and not v.canonical


@pytest.mark.parametrize("switch", ["canonical", "hermetic"])
def test_RUN_START_refuses_the_flag_even_when_no_name_would_reach_the_static_path(tmp_path, monkeypatch, switch):
    """The lazy refusal never fires when every name is cached; ModeController.run_backtest must
    refuse before it reads anything (the first statement after the log resets)."""
    from orchestration.mode_controller import ModeController
    _plant_fixture(tmp_path, monkeypatch)
    if switch == "canonical":
        monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    else:
        monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    mc = ModeController.__new__(ModeController)          # no config/data read: the refusal comes first
    with pytest.raises(dmmod.FundamentalsFixtureRefused):
        mc.run_backtest()


def test_RUN_START_check_is_silent_without_the_flag_and_outside_measured_runs(tmp_path, monkeypatch):
    dmmod.refuse_fixture_flag_in_measured_run()                       # no flag
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    dmmod.refuse_fixture_flag_in_measured_run()                       # canonical, no flag
    monkeypatch.delenv(dmmod.REFUSE_YFINANCE_ENV)
    _plant_fixture(tmp_path, monkeypatch)
    dmmod.refuse_fixture_flag_in_measured_run()                       # flag, local run


def test_the_REBAKE_refuses_the_flag_before_any_read_or_write(tmp_path, monkeypatch):
    """With the flag set the rebake recorded fixture rows as `source: yfinance` (review, 2026-11-13)."""
    from scripts import rebake_fundamentals as rb
    _plant_fixture(tmp_path, monkeypatch)
    _no_network(monkeypatch)
    cache = Path(tmp_path) / "processed"
    with pytest.raises(rb.RebakeRefused, match=dmmod.FUNDAMENTALS_FIXTURE_ENV):
        rb.rebake(["AAPL"], cache_dir=cache)
    assert not cache.exists(), "the rebake created or wrote under the cache before refusing"
    assert dmmod.fundamentals_miss_summary()["fixture"] == []


def test_flag_under_HERMETIC_is_REFUSED_before_any_read(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "1")
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    with pytest.raises(dmmod.FundamentalsFixtureRefused, match="hermetic"):
        dm.fetch_historical_fundamentals("AAPL")
    assert getattr(dm, "_fixture_cache", None) is None
    assert dmmod.fundamentals_miss_summary()["fixture"] == []


def test_the_PREFETCH_does_not_swallow_the_refusal(tmp_path, monkeypatch):
    """prefetch_fundamentals runs on every backtest and catches per-ticker errors; the refusal is a
    misconfigured run, not a per-ticker hiccup, so it must escape."""
    _plant_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv(dmmod.REFUSE_YFINANCE_ENV, "1")
    _no_network(monkeypatch)
    with pytest.raises(dmmod.FundamentalsFixtureRefused):
        _dm(tmp_path).prefetch_fundamentals(["AAPL"])


def test_a_flag_naming_a_MISSING_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv(dmmod.FUNDAMENTALS_FIXTURE_ENV, str(Path(tmp_path) / "nope.csv"))
    _no_network(monkeypatch)
    with pytest.raises(dmmod.FundamentalsFixtureRefused, match="not a file"):
        _dm(tmp_path).fetch_historical_fundamentals("AAPL")


def test_a_CACHED_name_is_served_from_its_parquet_and_never_reaches_the_fixture(tmp_path, monkeypatch):
    _plant_fixture(tmp_path, monkeypatch)
    _no_network(monkeypatch)
    dm = _dm(tmp_path)
    pd.DataFrame({"PE_Ratio": [20.0]}, index=pd.DatetimeIndex(["2024-01-02"])).to_parquet(
        dm._fundamentals_cache_path("AAPL"))
    out = dm.fetch_historical_fundamentals("AAPL")
    assert list(out["PE_Ratio"]) == [20.0] and dmmod.fundamentals_miss_summary()["fixture"] == []
