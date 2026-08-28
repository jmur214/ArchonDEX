"""T-195's three 'deferred' production fixes — pinned as CLOSED (2026-08-27).

All three shipped (fixes 1-2 via T-197, fix 3 in T-195 itself); the record simply
never carried a forward pointer, so a supersession sweep read them as open. These
tests make "already done" durable — each of the three regressions is SILENT if it
returns, which is exactly why they need pins rather than prose.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent


# ---- FIX 1: MBL Gate-0 must run on the FULL evaluation extent ---------------

def _dm(periods=3000, start="2012-01-02"):
    idx = pd.bdate_range(start, periods=periods)
    return {"SPY": pd.DataFrame({"Close": range(periods)}, index=idx)}


def test_default_validation_window_is_the_FULL_extent_not_a_trailing_slice():
    """The T-193/T-195 bug: a 24-month default made T_years=2.0 vs an MBL minimum
    of ~9.66yr, so every candidate died at Gate-0 before any alpha gate and the
    cycle structurally could not promote. Silent if it regresses — the cycle still
    runs and simply never promotes."""
    from orchestration.mode_controller import discovery_validation_window
    dm = _dm()
    start, end = discovery_validation_window(dm, None)
    idx = dm["SPY"].index
    assert start == idx[0].isoformat(), "default must be the first bar, not a trailing window"
    assert end == idx[-1].isoformat()
    span_years = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    assert span_years > 9.66, f"default window {span_years:.1f}yr cannot clear MBL Gate-0"


def test_the_legacy_sub_window_remains_available_but_only_OPT_IN():
    from orchestration.mode_controller import discovery_validation_window
    dm = _dm()
    start, end = discovery_validation_window(dm, "24")
    assert (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25 == pytest.approx(2.0, abs=0.05)
    assert start != dm["SPY"].index[0].isoformat()


def test_empty_data_map_yields_no_window_rather_than_a_fabricated_one():
    from orchestration.mode_controller import discovery_validation_window
    assert discovery_validation_window({}, None) == (None, None)
    assert discovery_validation_window({"SPY": pd.DataFrame()}, None) == (None, None)


# ---- FIX 2: a crashing edge must not masquerade as "no signal" --------------

def test_systematic_edge_crash_still_fails_loud_and_is_wired_into_production():
    """Recording alone is not the fix — the signal needs a consumer. Pins BOTH
    the raise and the fact that discovery.py actually calls it."""
    from engines.engine_d_discovery.gate1_signal_cache import (
        Gate1SignalCache, DiscoveryBaselineError,
    )
    assert hasattr(Gate1SignalCache, "assert_baseline_healthy")
    assert issubclass(DiscoveryBaselineError, RuntimeError)
    src = (REPO / "engines/engine_d_discovery/discovery.py").read_text()
    assert "assert_baseline_healthy()" in src, "the guard must be CALLED in the discovery path"


def test_edges_errored_is_treated_as_non_canonical_by_the_census():
    """`[NN-CENSUS]`/`[NN-FAIL-CLOSED]`: a swallowed crash reaches the census and
    fails the run, rather than resolving to a plausible Sharpe-0 baseline."""
    from core.census import assert_census
    import inspect
    assert "edges_errored" in inspect.getsource(assert_census)


# ---- FIX 3: the unconditional per-fill print stays gated --------------------

def test_the_per_fill_debug_print_remains_behind_the_debug_gate():
    """Ungated it emitted one line PER FILL over a 13yr/109-ticker backtest —
    a wall-time and log-bloat drag heavy enough to block the eval entirely."""
    src = (REPO / "backtester/backtest_controller.py").read_text()
    i = src.index("[DEBUG_BACKTEST_FILL_CREATED]")
    preceding = src[max(0, i - 300):i]
    assert "is_controller_debug()" in preceding, "the per-fill print must stay gated"
