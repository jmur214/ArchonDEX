"""tests/test_evolution_cycle_verdict_rr2.py — the SECOND verdict overwrite, locked by EXECUTION.

RR-2's brief named mode_controller's overwrite. A second copy lived in
scripts/run_evolution_cycle.py (reachable from the dashboard command runner and
run_autonomous_cycle.py). It used the variable `m`, not `result`, so the brief's text
assertion (`'result["passed_all_gates"] = (' not in src`) could never have seen it —
and its Pass 2 promoted straight to status "active" without ever reading the gauntlet's
verdict, on its own rule with a third survival literal (0.4).

These tests drive the REAL `AutonomousEvolution.run_cycle`; only I/O is stubbed.
"""
import pandas as pd
import pytest

run_evo = pytest.importorskip("scripts.run_evolution_cycle")


class _Disc:
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.queued = [{"edge_id": f"cand_{i}", "status": "candidate", "params": {}}
                       for i in range(len(verdicts))]
        self.saved = None
        self.thresholds = []

    def get_queued_candidates(self, status="candidate"):
        return self.queued

    def generate_candidates(self, **kw):
        return []

    def validate_candidate(self, cand, data_map, **kw):
        # RECORD, don't assert: an assertion here would fire first on the unfixed code
        # and make the reversion proof fail for the wrong reason.
        self.thresholds.append(kw.get("significance_threshold"))
        return dict(self.verdicts.pop(0))

    def save_candidates(self, cands):
        self.saved = {c["edge_id"]: c["status"] for c in cands}


class _Log:
    def log_validation(self, *a, **k):
        pass


class _WFO:
    def run_optimization(self, cand, **kw):
        return {"degradation": 0.95}          # WFO always passes: isolate the gauntlet


def _drive(monkeypatch, verdicts):
    import core.benchmark as bm
    monkeypatch.setattr(bm, "compute_benchmark_metrics",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    evo = object.__new__(run_evo.AutonomousEvolution)
    evo.discovery = _Disc(verdicts)
    evo.discovery_logger = _Log()
    evo.data_map = {"SPY": pd.DataFrame({"Close": range(800)},
                                        index=pd.bdate_range("2020-01-01", periods=800))}
    evo.wfo = _WFO()
    promoted = []
    evo._promote_winners = lambda winners: promoted.extend(w["edge_id"] for w in winners)
    evo.run_cycle()
    _drive.last = evo.discovery
    return evo.discovery.saved, promoted


# Everything the OLD Pass 2 checked is satisfied: sharpe above any benchmark fallback,
# Sortino >= 0.8, survival >= 0.4, a p that BH rejects, universe-B > 0. Only the
# gauntlet's own verdict says no. The old code promoted it; the fixed code must not.
_FAILED_BUT_PLAUSIBLE = {"passed_all_gates": False, "sharpe": 5.0, "sortino": 3.0,
                         "robustness_survival": 0.9, "significance_p": 0.0001,
                         "universe_b_sharpe": 1.0, "universe_b_n_tickers": 20}


def test_a_gauntlet_FAILURE_is_never_promoted_by_the_evolution_cycle(monkeypatch):
    saved, promoted = _drive(monkeypatch, [_FAILED_BUT_PLAUSIBLE])
    assert saved is not None, "the cycle never reached its registry write"
    assert promoted == [], f"a gauntlet failure was promoted: {promoted}"
    assert saved["cand_0"] == "failed"


def test_a_clean_gauntlet_passer_IS_promoted(monkeypatch):
    """Positive control: without it, 'nothing promoted' is also satisfied by a cycle
    that cannot promote anything."""
    clean = dict(_FAILED_BUT_PLAUSIBLE, passed_all_gates=True)
    saved, promoted = _drive(monkeypatch, [clean])
    assert promoted == ["cand_0"] and saved["cand_0"] == "active"


def test_BH_can_remove_a_passer_but_the_reason_says_so(monkeypatch):
    """Two candidates so BH has a family: a passer with a hopeless p is REMOVED."""
    passer_bad_p = dict(_FAILED_BUT_PLAUSIBLE, passed_all_gates=True, significance_p=0.9)
    saved, promoted = _drive(monkeypatch, [passer_bad_p, dict(passer_bad_p)])
    assert promoted == [] and set(saved.values()) == {"failed"}


def test_validate_candidate_receives_the_CONFIGURED_threshold_not_None(monkeypatch):
    _drive(monkeypatch, [dict(_FAILED_BUT_PLAUSIBLE)])
    assert _drive.last.thresholds == [0.05], _drive.last.thresholds
