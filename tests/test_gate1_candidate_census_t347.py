"""T-2026-08-26-347 — the Gate-1 CANDIDATE census.

T-197 made a baseline edge's silence VISIBLE (crash vs genuine no-signal are no
longer indistinguishable). It did not make the CANDIDATE's silence FAIL — and
the candidate is the one whose silence produces a published verdict. T-346
established that an exactly +0.000 Gate-1 contribution has three causes and only
one of them is a refutation; these tests lock the two the harness can now name.
"""
from __future__ import annotations

import pandas as pd
import pytest

from core.census import assert_census
from engines.engine_d_discovery.gate1_signal_cache import (
    CandidateSignalCensus,
    DiscoveryCandidateCensusError,
    _emitted_nonzero,
)


class _SilentEdge:
    """Runs cleanly, emits nothing — the cause-C candidate."""
    def compute_signals(self, data_map, now):
        return {"AAPL": 0.0, "MSFT": 0.0}


class _SpeakingEdge:
    def __init__(self):
        self.n = 0

    def compute_signals(self, data_map, now):
        self.n += 1
        return {"AAPL": 0.42, "MSFT": 0.0}

    def unrelated(self):
        return "passthrough"


class _CrashEdge:
    def compute_signals(self, data_map, now):
        raise ValueError("boom")


def _census_block(cand_id, census, n_trades):
    """The block `validate_candidate` builds — kept in one place so the tests
    lock the CONTRACT with assert_census, not a private copy of it."""
    return {
        "census": {
            "edges_blind": ([cand_id] if census.nonzero_calls == 0 else []),
            "edges_errored": ({cand_id: {"crash_bars": census.errors}}
                              if census.errors else {}),
            "n_trades": n_trades,
        },
        "bootstrap_ci_skip_reason": "gate1_contribution_run",
    }


# --------------------------------------------------------------------------- #
# the proxy must be behaviourally invisible
# --------------------------------------------------------------------------- #
def test_proxy_is_behaviourally_transparent_t347():
    """It counts and does nothing else: same values, NO memoization (the
    delegate is invoked every call), and unrelated attributes pass through."""
    edge = _SpeakingEdge()
    proxy = CandidateSignalCensus(edge, "cand_v1")
    a = proxy.compute_signals({}, "2020-01-02")
    b = proxy.compute_signals({}, "2020-01-02")     # SAME `now` — must NOT memoize
    assert a == b == {"AAPL": 0.42, "MSFT": 0.0}
    assert edge.n == 2, "proxy memoized — it must delegate on every call"
    assert proxy.unrelated() == "passthrough"


def test_proxy_never_swallows_a_crash_t347():
    proxy = CandidateSignalCensus(_CrashEdge(), "cand_v1")
    with pytest.raises(ValueError):
        proxy.compute_signals({}, "2020-01-02")
    assert proxy.errors == 1
    assert "ValueError" in (proxy.last_error or "")


def test_counts_distinguish_never_called_from_called_and_silent_t347():
    """calls==0 (never invoked) and nonzero==0 (invoked, silent) are different
    diagnoses and must stay separable — T-346 §1 is exactly the cost of not."""
    never = CandidateSignalCensus(_SilentEdge(), "cand_v1")
    assert never.calls == 0 and never.nonzero_calls == 0

    silent = CandidateSignalCensus(_SilentEdge(), "cand_v1")
    for _ in range(5):
        silent.compute_signals({}, "2020-01-02")
    assert silent.calls == 5 and silent.nonzero_calls == 0


# --------------------------------------------------------------------------- #
# the census contract
# --------------------------------------------------------------------------- #
def test_blind_candidate_is_non_canonical_t347():
    """THE NAMED REGRESSION. A candidate that runs cleanly and emits nothing
    must NOT yield a publishable +0.000 refutation."""
    census = CandidateSignalCensus(_SilentEdge(), "cand_v1")
    for _ in range(10):
        census.compute_signals({}, "2020-01-02")

    verdict = assert_census(_census_block("cand_v1", census, n_trades=250))
    assert not verdict.canonical
    assert any("edges_blind" in f for f in verdict.failures), verdict.failures


def test_speaking_candidate_with_trades_is_canonical_t347():
    """The guard must not break the ordinary path: a candidate that speaks and
    a with-arm that trades is CANONICAL and proceeds to Gate-1 normally."""
    census = CandidateSignalCensus(_SpeakingEdge(), "cand_v1")
    for _ in range(10):
        census.compute_signals({}, "2020-01-02")

    verdict = assert_census(_census_block("cand_v1", census, n_trades=250))
    assert verdict.canonical, verdict.failures
    assert not verdict.warnings, "skip_reason declared → no spurious CI warning"


def test_crashing_candidate_is_non_canonical_t347():
    census = CandidateSignalCensus(_CrashEdge(), "cand_v1")
    for _ in range(3):
        with pytest.raises(ValueError):
            census.compute_signals({}, "2020-01-02")

    verdict = assert_census(_census_block("cand_v1", census, n_trades=250))
    assert not verdict.canonical
    assert any("edges_errored" in f for f in verdict.failures), verdict.failures


def test_zero_trade_with_arm_is_non_canonical_t347():
    """A with-arm that placed no trades cannot measure a contribution either."""
    census = CandidateSignalCensus(_SpeakingEdge(), "cand_v1")
    census.compute_signals({}, "2020-01-02")

    verdict = assert_census(_census_block("cand_v1", census, n_trades=0))
    assert not verdict.canonical
    assert any("zero-trade" in f for f in verdict.failures), verdict.failures


# --------------------------------------------------------------------------- #
# the ABSORBED branch (cause A) — kept DISTINCT from blindness
# --------------------------------------------------------------------------- #
def _absorbed(census, attribution):
    """Mirrors the predicate in validate_candidate."""
    return (census.nonzero_calls > 0 and len(attribution) > 0
            and not (attribution != 0.0).any())


def test_absorbed_is_detected_only_when_the_candidate_SPOKE_t347():
    spoke = CandidateSignalCensus(_SpeakingEdge(), "cand_v1")
    spoke.compute_signals({}, "2020-01-02")
    silent = CandidateSignalCensus(_SilentEdge(), "cand_v1")
    silent.compute_signals({}, "2020-01-02")

    identical = pd.Series([0.0] * 50)
    assert _absorbed(spoke, identical), "spoke + bit-identical stream = ABSORBED"
    assert not _absorbed(silent, identical), "silent candidate is BLIND, not absorbed"


def test_absorbed_does_not_fire_on_a_real_contribution_t347():
    spoke = CandidateSignalCensus(_SpeakingEdge(), "cand_v1")
    spoke.compute_signals({}, "2020-01-02")
    real = pd.Series([0.0] * 49 + [1e-9])
    assert not _absorbed(spoke, real), "a single non-zero bar is a real effect"


def test_absorbed_fails_safe_on_nan_t347():
    """NaN != 0.0 is True, so a NaN-bearing stream never falsely raises."""
    spoke = CandidateSignalCensus(_SpeakingEdge(), "cand_v1")
    spoke.compute_signals({}, "2020-01-02")
    assert not _absorbed(spoke, pd.Series([float("nan")] * 10))
    assert not _absorbed(spoke, pd.Series(dtype=float))     # empty → no verdict


# --------------------------------------------------------------------------- #
# the non-zero predicate across the shapes edges actually return
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value,expected", [
    ({"A": 0.0, "B": 0.3}, True),
    ({"A": 0.0, "B": 0.0}, False),
    ({}, False),
    (None, False),
    ({"A": float("nan")}, False),           # NaN is not a signal
    ({"A": float("inf")}, False),           # nor is inf
    ({"A": None, "B": "x"}, False),         # junk is not a signal
    ([0.0, 0.0], False),
    ([0.0, -0.7], True),                    # SHORT signals count
    (pd.Series([0.0, 0.0]), False),
    (pd.Series([0.0, 1.0]), True),
])
def test_emitted_nonzero_shapes_t347(value, expected):
    assert _emitted_nonzero(value) is expected
