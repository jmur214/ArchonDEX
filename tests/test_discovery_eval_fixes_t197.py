"""T-2026-06-17-197 — production discovery eval-fix regressions.

FIX 2 (the structural one): the Gate1SignalCache wrapper used to SWALLOW a
crashing edge's compute_signals to {} — indistinguishable from a legitimate
"edge produced no signal" → a silent degenerate baseline → a fake Sharpe-0
(T-189-class fail-open behind T-195's degenerate baseline). Now a swallowed crash
is RECORDED structurally; a SYSTEMATIC crash (most bars) FAILS LOUD via
DiscoveryBaselineError; a transient gap is surfaced (eval_error_report) but does
NOT raise; a genuine no-signal is never flagged. (FIX 1 — the 24-month MBL window
in _run_discovery_cycle → full extent — is discovery-path-only and covered by the
OFF-byte-identical construction; see the audit.)
"""
from __future__ import annotations

import pandas as pd
import pytest

from engines.engine_d_discovery.gate1_signal_cache import (
    Gate1SignalCache, DiscoveryBaselineError,
)


class _CrashEdge:
    EDGE_ID = "crash_v1"
    def compute_signals(self, data_map, now):
        raise ValueError("boom")


class _HealthyEdge:
    EDGE_ID = "ok_v1"
    def compute_signals(self, data_map, now):
        return {"AAA": 1.0}


class _NoSignalEdge:
    EDGE_ID = "quiet_v1"
    def compute_signals(self, data_map, now):
        return {}


class _TransientEdge:
    """Raises on exactly one bar (a legitimate per-bar gap), fine otherwise."""
    EDGE_ID = "transient_v1"
    def __init__(self):
        self.n = 0
    def compute_signals(self, data_map, now):
        self.n += 1
        if self.n == 3:
            raise KeyError("one-bar gap")
        return {"AAA": 1.0}


def _drive(edge, n_bars=10):
    c = Gate1SignalCache()
    w = c.wrap_edges({edge.EDGE_ID: edge})[edge.EDGE_ID]
    for i in range(n_bars):
        w.compute_signals({}, pd.Timestamp("2020-01-01") + pd.Timedelta(days=i))
    return c


def test_systematic_crash_fails_loud():
    """A baseline edge that crashes on most bars must raise DiscoveryBaselineError
    (named, with the rate + last error) — not a silent fake Sharpe-0."""
    c = _drive(_CrashEdge())
    rep = c.eval_error_report()
    assert rep["crash_v1"]["rate"] == 1.0 and rep["crash_v1"]["errors"] == 10
    with pytest.raises(DiscoveryBaselineError) as ei:
        c.assert_baseline_healthy()
    assert "crash_v1" in str(ei.value) and "boom" in str(ei.value)


def test_healthy_baseline_does_not_raise():
    c = _drive(_HealthyEdge())
    assert c.eval_error_report() == {}
    c.assert_baseline_healthy()  # no raise


def test_genuine_no_signal_not_flagged_as_crash():
    """An edge that legitimately returns {} must NOT appear as a crash (the
    distinguish-no-signal-from-swallowed-crash requirement)."""
    c = _drive(_NoSignalEdge())
    assert c.eval_error_report() == {}      # errors==0 → not a crash
    c.assert_baseline_healthy()             # no raise


def test_transient_gap_surfaced_but_not_raised():
    """A single-bar gap is surfaced structurally (eval_error_report) but is NOT
    systematic → does NOT fail loud (preserves the legitimate narrow-catch)."""
    c = _drive(_TransientEdge(), n_bars=10)
    rep = c.eval_error_report()
    assert rep["transient_v1"]["errors"] == 1 and rep["transient_v1"]["rate"] == 0.1
    c.assert_baseline_healthy()  # 0.1 < 0.5 systematic threshold → no raise


def test_signals_still_correct_for_healthy_edge():
    """The wrapper still memoizes + returns the real signals unchanged."""
    e = _HealthyEdge()
    c = Gate1SignalCache()
    w = c.wrap_edges({e.EDGE_ID: e})[e.EDGE_ID]
    s1 = w.compute_signals({}, pd.Timestamp("2020-01-01"))
    s2 = w.compute_signals({}, pd.Timestamp("2020-01-01"))  # cache hit
    assert s1 == {"AAA": 1.0} and s2 == {"AAA": 1.0}
    assert w.hits == 1 and w.misses == 1 and w.eval_errors == 0


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
