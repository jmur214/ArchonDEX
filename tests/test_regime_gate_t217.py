# tests/test_regime_gate_t217.py
"""T-217 — the g_regime gate: HMM-labelled regime, the Sharpe→gate map, and
(the load-bearing one) DEFAULT-OFF / canon-safe inertness.
"""
from __future__ import annotations

from engines.engine_e_regime.regime_gate import (
    CALM_MAX, CAUTIOUS_MAX, DISABLE_SR, GATE_FLOOR, MIN_TRADES,
    RegimeGate, build_gates_from_stats, gate_from_sharpe, hmm_regime_label,
)


def _meta(p_crisis):
    return {"hmm_regime": {"probabilities": {"benign": 1 - p_crisis,
                                             "crisis": p_crisis}}}


class TestHmmLabel:
    def test_thresholds(self):
        assert hmm_regime_label(_meta(0.0)) == "calm"
        assert hmm_regime_label(_meta(CALM_MAX - 0.01)) == "calm"
        assert hmm_regime_label(_meta(CALM_MAX)) == "cautious"
        assert hmm_regime_label(_meta(CAUTIOUS_MAX - 0.01)) == "cautious"
        assert hmm_regime_label(_meta(CAUTIOUS_MAX)) == "crisis"
        assert hmm_regime_label(_meta(0.95)) == "crisis"

    def test_failsafe_calm_when_hmm_absent(self):
        # missing / disabled / malformed HMM → calm (never suppress an edge)
        assert hmm_regime_label(None) == "calm"
        assert hmm_regime_label({}) == "calm"
        assert hmm_regime_label({"advisory": {"regime_summary": "crisis"}}) == "calm"
        assert hmm_regime_label({"hmm_regime": {"probabilities": {}}}) == "calm"
        assert hmm_regime_label({"hmm_regime": {"probabilities": {"crisis": "x"}}}) == "calm"

    def test_does_not_read_the_failed_advisory(self):
        # even with a 'crisis' advisory, no HMM posterior → calm (we ignore
        # the 5-axis advisory label that net-negatived the walk-forward).
        meta = {"advisory": {"regime_summary": "crisis"}, "hmm_regime": None}
        assert hmm_regime_label(meta) == "calm"


class TestSharpeMap:
    def test_insufficient_trades_no_gate(self):
        assert gate_from_sharpe(-5.0, MIN_TRADES - 1) == 1.0   # data too thin → pass

    def test_disable_below_threshold(self):
        assert gate_from_sharpe(DISABLE_SR, MIN_TRADES) == 0.0
        assert gate_from_sharpe(DISABLE_SR - 0.5, MIN_TRADES) == 0.0

    def test_in_range_monotone_and_clamped(self):
        g0 = gate_from_sharpe(0.0, 100)
        g1 = gate_from_sharpe(1.0, 100)
        g2 = gate_from_sharpe(2.0, 100)
        assert abs(g0 - GATE_FLOOR) < 1e-9
        assert abs(g1 - 1.0) < 1e-9
        assert g2 == g1 == 1.0            # clamped at the ceiling
        assert g0 < gate_from_sharpe(0.5, 100) < g1


class TestBuildGates:
    def test_builds_and_drops_unity_entries(self):
        stats = {
            "edgeA": {"crisis": {"sharpe": -1.0, "trade_count": 50},   # → 0.0
                      "calm": {"sharpe": 1.5, "trade_count": 50}},     # → 1.0 (dropped)
            "edgeB": {"cautious": {"sharpe": 0.5, "trade_count": 5}},  # thin → 1.0 (dropped)
        }
        gates = build_gates_from_stats(stats)
        assert gates == {"edgeA": {"crisis": 0.0}}    # only the non-unity gate kept


class TestRegimeGateDefaultOff:
    def test_empty_gate_is_inert_everywhere(self):
        rg = RegimeGate()                 # {} == OFF
        assert rg.enabled is False
        for p in (0.0, 0.4, 0.9):
            assert rg.gate("any_edge", _meta(p)) == 1.0
        assert rg.gate("any_edge", None) == 1.0     # the canon-safe no-op

    def test_unseen_edge_or_regime_passes(self):
        rg = RegimeGate(gates={"edgeA": {"crisis": 0.0}})
        assert rg.enabled is True
        assert rg.gate("edgeB", _meta(0.9)) == 1.0        # edge not gated
        assert rg.gate("edgeA", _meta(0.0)) == 1.0        # calm not in edgeA's gate
        assert rg.gate("edgeA", _meta(0.9)) == 0.0        # crisis → killed

    def test_persistence_roundtrip(self, tmp_path):
        rg = RegimeGate(gates={"e": {"crisis": 0.5, "cautious": 0.8}})
        p = tmp_path / "g.json"
        rg.to_file(p)
        back = RegimeGate.from_file(p)
        assert back.gates == rg.gates
        # fail-safe: a bad path → OFF, never raises
        assert RegimeGate.from_file(tmp_path / "nope.json").gates == {}
