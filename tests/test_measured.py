"""T-2026-06-17-194 — loader HALT-semantics (D's T-189 design).

Proves the contract: measured AND load_bearing AND active ⇒ HALT; else degrade.
Two guarded sites: fundamentals (get_panel) and universe_resolver (membership).
"""
import os
import importlib
from pathlib import Path

import pytest

import core.measured as measured
from core.measured import MeasurementHalt, Degraded, halt_or_degrade


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # default OFF unless a test sets it
    monkeypatch.delenv("ARCHONDEX_MEASURED", raising=False)
    monkeypatch.delenv("ARCHONDEX_HERMETIC", raising=False)
    yield


# ---------------------------------------------------------------- predicate ---
def test_is_measured_default_off():
    assert measured.is_measured() is False


def test_is_measured_explicit_on(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    assert measured.is_measured() is True


def test_is_measured_hermetic_strict_on(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "strict")
    assert measured.is_measured() is True


def test_is_measured_explicit_off_overrides_hermetic(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "strict")
    monkeypatch.setenv("ARCHONDEX_MEASURED", "0")
    assert measured.is_measured() is False


def test_hermetic_warn_is_not_measured(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_HERMETIC", "warn")
    assert measured.is_measured() is False


# ------------------------------------------------------------------- helper ---
def test_halt_or_degrade_halts_when_measured_loadbearing_active(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    with pytest.raises(MeasurementHalt):
        halt_or_degrade("s", load_bearing=True, active=True, reason="r")


def test_halt_or_degrade_degrades_when_not_measured(monkeypatch):
    d = halt_or_degrade("s", load_bearing=True, active=True, reason="r")
    assert isinstance(d, Degraded) and d.site == "s"


def test_halt_or_degrade_degrades_when_not_loadbearing(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    assert isinstance(halt_or_degrade("s", load_bearing=False, active=True, reason="r"), Degraded)


def test_halt_or_degrade_degrades_when_not_active(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    assert isinstance(halt_or_degrade("s", load_bearing=True, active=False, reason="r"), Degraded)


# ------------------------------------------------- fundamentals site (G/H) ---
def _force_panel_load_failure(monkeypatch):
    import engines.engine_a_alpha.edges._fundamentals_helpers as fh
    fh.reset_panel_cache()
    # make the underlying loader raise (simulates absent/unbaked simfin panel)
    import engines.data_manager.fundamentals.simfin_adapter as sa
    monkeypatch.setattr(sa, "load_panel", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("panel absent")))
    return fh


def test_fundamentals_measured_halts(monkeypatch):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    fh = _force_panel_load_failure(monkeypatch)
    with pytest.raises(MeasurementHalt):
        fh.get_panel()


def test_fundamentals_offline_degrades_to_none(monkeypatch):
    fh = _force_panel_load_failure(monkeypatch)
    assert fh.get_panel() is None  # exact pre-existing degrade behavior


# ------------------------------------------------ universe_resolver site (M) ---
def test_universe_measured_halts_on_missing_membership(monkeypatch, tmp_path):
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    from engines.data_manager.universe_resolver import resolve_universe
    # tmp_path has no universe/sp500_membership.parquet → membership absent
    with pytest.raises(MeasurementHalt):
        resolve_universe(
            static_tickers=["SPY", "AAPL"], start="2020-01-01", end="2021-01-01",
            use_historical=True, cache_dir=tmp_path,
        )


def test_universe_offline_degrades_to_static(monkeypatch, tmp_path):
    from engines.data_manager.universe_resolver import resolve_universe
    tickers, info = resolve_universe(
        static_tickers=["SPY", "AAPL"], start="2020-01-01", end="2021-01-01",
        use_historical=True, cache_dir=tmp_path,
    )
    assert info["mode"] == "fallback_to_static"
    assert tickers == ["SPY", "AAPL"]  # exact pre-existing degrade behavior
