"""tests/test_rr6a_gate_verdicts.py — RR-6a: gate verdicts that can be trusted.

One lock per defect, each DRIVING the real entrypoint (`validate_candidate`,
`_run_discovery_cycle`, `AutonomousEvolution.run_cycle`, the T-195 harness's
`foundry_record`) — never a text assertion (2026-09-14: 53 green tests passed on a
broken line because none executed it). Each lock fails when only its fix is reverted;
the reversion record is in the RR-6a proposal.

The defect class: gate results were two-valued booleans with DEFAULTS, so a gate that
never ran read as a verdict — as a PASS to the promotion decision (Gate 7/8), as a FAIL
to the foundry harness (Gate 3). Every lock below that asserts a REFUSAL is paired with
a positive control in which the same candidate, with that one gate evaluated, PASSES —
otherwise "refused" could be satisfied by some other gate refusing (Gate 0 with no
window would refuse everything), and the lock would hold vacuously on the buggy code.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import tests.test_discovery_gates_7_8 as g78
from core.factor_decomposition import gate_factor_alpha as _REAL_GATE_FACTOR_ALPHA
from core.factor_decomposition import regress_returns_on_factors as _REAL_REGRESS
from engines.engine_d_discovery import gate_verdicts as gv


# --------------------------------------------------------------------------- #
# A candidate that passes EVERY required gate when all of them are evaluated.
# --------------------------------------------------------------------------- #
def _strong_streams(idx, seed: int = 3):
    rng = np.random.default_rng(seed)
    base = pd.Series(rng.normal(0.0005, 0.01, len(idx) - 1), index=idx[1:])
    spread = pd.Series(rng.normal(0.002, 0.002, len(idx) - 1), index=idx[1:])
    return base, base + spread


def _run_passer(monkeypatch, *, substrate_b: bool = True, n_trials: int = 2,
                window: bool = True, **kw):
    data_map, idx = g78._make_synthetic_dfs()
    base, with_ = _strong_streams(idx)
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,       # drift 0.1 <= 0.5
                   "daily_returns_with": with_, "daily_returns_baseline": base},
    )
    args = dict(significance_threshold=0.05, alpha_config={}, n_trials_for_dsr=n_trials,
                data_map_substrate_b=({"SUBSTRATEB": data_map["AAA"]} if substrate_b else None))
    if window:
        args.update(start_date=idx[0].isoformat(), end_date=idx[-1].isoformat())
    args.update(kw)
    return g78._make_disc().validate_candidate(g78._make_cand_spec(), data_map, **args)


def test_POSITIVE_CONTROL_every_required_gate_evaluated_and_passed(monkeypatch):
    """Without this, every refusal below could hold vacuously."""
    r = _run_passer(monkeypatch)
    assert r["passed_all_gates"] is True, r["promotion_refusals"]
    assert r["promotion_refusals"] == []
    for g in r["required_gates"]:
        assert r["gate_verdicts"][g]["verdict"] == gv.PASSED, (g, r["gate_verdicts"][g])
    assert gv.first_failed_gate(r) is None


# --------------------------------------------------------------------------- #
# absent = PASS (the promotion decision) — Gate 7, Gate 8, Gate 0
# --------------------------------------------------------------------------- #
def test_a_skipped_gate_7_REFUSES_it_never_defaults_to_a_pass(monkeypatch):
    """Revert → `gate_7_passed` defaults True and the final check reads it → passes."""
    r = _run_passer(monkeypatch, substrate_b=False)
    assert r["gate_verdicts"]["gate_7"] == {"verdict": gv.NOT_EVALUATED,
                                            "reason": "no substrate-B data_map provided"}
    assert r["promotion_refusals"] == ["gate_7: not_evaluated — no substrate-B data_map provided"]
    assert r["passed_all_gates"] is False


def test_an_explicit_N_of_1_leaves_gate_8_NOT_EVALUATED_and_refuses(monkeypatch):
    """Revert → `gate_8_passed` defaults True when N ≤ 1 → passes."""
    r = _run_passer(monkeypatch, n_trials=1)
    assert r["gate_verdicts"]["gate_8"]["verdict"] == gv.NOT_EVALUATED
    assert [x.split(":")[0] for x in r["promotion_refusals"]] == ["gate_8"]
    assert r["passed_all_gates"] is False


def test_no_validation_window_leaves_gate_0_NOT_EVALUATED_and_refuses(monkeypatch):
    """[NN-MBL]: Gate 0 used to be SILENTLY skipped without a window. Revert → passes."""
    r = _run_passer(monkeypatch, window=False)
    assert r["gate_verdicts"]["gate_0"]["verdict"] == gv.NOT_EVALUATED
    assert [x.split(":")[0] for x in r["promotion_refusals"]] == ["gate_0"]
    assert r["passed_all_gates"] is False


# --------------------------------------------------------------------------- #
# absent = FAIL (kill attribution) — the diagnostic row and the foundry harness
# --------------------------------------------------------------------------- #
def _diag_row(path):
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_diagnostic_never_names_a_gate_that_rendered_no_verdict(monkeypatch, tmp_path):
    """Gates 1–6 pass, Gate 7 never ran. The old `gate_pass_order` (derived flags, Gate 7
    False) named 'gate_7' the killer of a candidate no gate FAILED. Revert → 'gate_7'."""
    log = tmp_path / "diag.jsonl"
    _run_passer(monkeypatch, substrate_b=False, diagnostic_log_path=str(log))
    row = _diag_row(log)
    assert row["first_failed_gate"] is None
    assert row["promotion_refusals"] == ["gate_7: not_evaluated — no substrate-B data_map provided"]
    assert row["gate_verdicts"]["gate_7"]["verdict"] == gv.NOT_EVALUATED


def test_a_gate_4_kill_is_attributed_to_gate_4_never_to_the_criterionless_gate_3(monkeypatch, tmp_path):
    """The T-196 shape: Gates 1–2 pass, Gate 3 (WFO) is computed, Gate 4 FAILS. Two
    T-196 records name Gate 3. Both the diagnostic row and the foundry harness record
    must name gate_4, and the harness must carry the tri-state per gate — revert the
    harness's `gates` to `gate_{g}_passed` and g3/g7/g8 read as booleans again."""
    from scripts.run_foundry_eval_t195 import foundry_record

    log = tmp_path / "diag.jsonl"
    data_map, idx = g78._make_synthetic_dfs()
    base, with_ = _strong_streams(idx)
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base},
    )
    monkeypatch.setattr("engines.engine_d_discovery.significance.monte_carlo_permutation_test",
                        lambda values, **kw: {"p_value": 0.9})
    r = g78._make_disc().validate_candidate(
        g78._make_cand_spec(), data_map, significance_threshold=0.05, alpha_config={},
        n_trials_for_dsr=2, diagnostic_log_path=str(log))

    assert r["gate_verdicts"]["gate_3"]["verdict"] == gv.NOT_EVALUATED
    assert "consistency" in r["gate_verdicts"]["gate_3"]["reason"], "precondition: WFO must have run"
    assert r["gate_verdicts"]["gate_4"]["verdict"] == gv.FAILED
    assert gv.first_failed_gate(r) == "gate_4"
    assert _diag_row(log)["first_failed_gate"] == "gate_4"
    rec = foundry_record("feat_x", True, r, 1.0)
    assert rec["first_failed_gate"] == "gate_4"
    assert rec["gates"]["g3"] == "not_evaluated"
    assert rec["gates"]["g7"] == "not_evaluated"          # no substrate B: never a `true`
    assert rec["gates"]["g4"] == "failed"


def test_the_harness_records_an_errored_candidate_without_inventing_a_verdict():
    from scripts.run_foundry_eval_t195 import foundry_record
    rec = foundry_record("feat_x", False, {"error": "RuntimeError('boom')"}, 2.0)
    assert rec["first_failed_gate"] is None and rec["gates"] is None
    assert rec["passed_all_gates"] is False and rec["error"] == "RuntimeError('boom')"


# --------------------------------------------------------------------------- #
# Gate 3's dead parameter
# --------------------------------------------------------------------------- #
def test_gate_3_threshold_is_not_a_silent_parameter(monkeypatch):
    """`gate3_consistency_threshold` was declared and never compared. Passing it now
    raises instead of silently doing nothing. Revert (parameter restored) → the full,
    stubbed gauntlet runs to completion and nothing raises. (Driven through the
    positive-control passer so that, reverted, the call SUCCEEDS — it must not fail for
    an unrelated reason such as an unimportable candidate module.)"""
    with pytest.raises(TypeError, match="gate3_consistency_threshold"):
        _run_passer(monkeypatch, gate3_consistency_threshold=0.9)


# --------------------------------------------------------------------------- #
# Gate 6 RF — at the CALL SITE, through validate_candidate
# --------------------------------------------------------------------------- #
def test_gate_6_recovers_a_spreads_alpha_without_subtracting_RF(monkeypatch):
    """A factor-neutral +2.5%/yr attribution spread, RF 5%/yr in the factor frame. Gate 6
    must report ≈ +2.5%. Revert `already_excess=True` at the call → ≈ −2.5%."""
    n = 1500
    idx = pd.bdate_range("2019-01-01", periods=n)
    df = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0,
                       "Volume": 1_000_000, "ATR": 1.0, "PrevClose": 100.0}, index=idx)
    rng = np.random.default_rng(0)
    factors = pd.DataFrame({c: rng.normal(0, 0.01, n) for c in
                            ["MktRF", "SMB", "HML", "RMW", "CMA", "Mom"]}, index=idx)
    factors["RF"] = 0.05 / 252
    base = pd.Series(rng.normal(0.0004, 0.01, n - 1), index=idx[1:])
    spread = pd.Series(0.025 / 252 + rng.normal(0, 0.002, n - 1), index=idx[1:])
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": base + spread, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,
                   "daily_returns_with": base + spread, "daily_returns_baseline": base},
    )
    monkeypatch.setattr("core.factor_decomposition.regress_returns_on_factors", _REAL_REGRESS)
    monkeypatch.setattr("core.factor_decomposition.gate_factor_alpha", _REAL_GATE_FACTOR_ALPHA)
    monkeypatch.setattr("core.factor_decomposition.load_factor_data",
                        lambda auto_download=False: factors)
    r = g78._make_disc().validate_candidate(
        # SPY as in production: the Gate-1 census proves the calendar against it (the guard, 10-15)
        g78._make_cand_spec(), {"AAA": df, "SPY": df}, significance_threshold=0.05, alpha_config={},
        n_trials_for_dsr=2)
    assert r["gate_verdicts"]["gate_6"]["verdict"] in (gv.PASSED, gv.FAILED), "precondition: Gate 6 ran"
    assert abs(r["factor_alpha_annualized"] - 0.025) < 0.015, r["factor_alpha_annualized"]


def test_gate_6_with_no_factor_cache_is_NOT_EVALUATED_not_a_pass(monkeypatch):
    """It used to read `factor_alpha_passed=True, 'skipped: factor cache missing'`."""
    def _missing(auto_download=False):
        raise FileNotFoundError("no factor cache")
    data_map, idx = g78._make_synthetic_dfs()
    base, with_ = _strong_streams(idx)
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base})
    monkeypatch.setattr("core.factor_decomposition.load_factor_data", _missing)
    r = g78._make_disc().validate_candidate(g78._make_cand_spec(), data_map,
                                            significance_threshold=0.05, alpha_config={},
                                            n_trials_for_dsr=2)
    assert r["gate_verdicts"]["gate_6"]["verdict"] == gv.NOT_EVALUATED
    assert r["factor_alpha_passed"] is False


# --------------------------------------------------------------------------- #
# Gate 5/7 cache contamination
# --------------------------------------------------------------------------- #
class _BaselineEdge:
    """Emits on EVERY ticker of the data_map it is given — so a signal naming a ticker
    absent from that data_map can only have come from somewhere else (the cache)."""
    def compute_signals(self, data_map, now):
        return {t: 1.0 for t in data_map}


class _CandidateEdge:
    def compute_signals(self, data_map, now):
        return {next(iter(data_map)): 0.5}


def test_gates_5_and_7_with_arms_never_replay_universe_A_signals(monkeypatch):
    """The Gate-1 signal cache keys on the bar timestamp alone. The Gate-5 and Gate-7
    with-arms reused the WRAPPED baseline edges, so on Universe B / substrate B they
    replayed Universe A's cached signals for every shared date. Each with-arm must see
    only signals for ITS OWN data_map. Revert `alt_with_edges` → the B runs carry 'AAA'."""
    from engines.engine_d_discovery.discovery import DiscoveryEngine

    idx = pd.date_range("2024-01-02", periods=200, freq="B")
    df = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0,
                       "Volume": 1_000_000, "ATR": 1.0, "PrevClose": 100.0}, index=idx)
    seen = []          # (tickers in the run's data_map, tickers the baseline edge signalled)

    def fake_run_backtest_pure(**kw):
        dm, edges = kw["data_map"], kw["edges"]
        rets = []
        for now in next(iter(dm.values())).index:
            total = 0.0
            for eid, edge in edges.items():
                sig = edge.compute_signals(dm, now)
                if eid == "base_edge":
                    seen.append((frozenset(dm), frozenset(sig)))
                total += sum(sig.values())
            rets.append(total)
        noise = np.random.default_rng(len(dm)).normal(0, 1e-3, len(rets))
        daily = pd.Series(np.array(rets) * 1e-4 + noise, index=next(iter(dm.values())).index)
        return SimpleNamespace(metrics={"Sharpe Ratio": 1.5 if "candidate_v0" in edges else 1.0,
                                        "Sortino": 1.0},
                               trade_log=pd.DataFrame({"pnl": [1.0, -0.5, 2.0]}),
                               equity_curve=(1.0 + daily).cumprod() * 100_000.0,
                               daily_returns=daily, attributed_pnl_per_edge={}, fingerprint="x")

    monkeypatch.setattr("orchestration.run_backtest_pure.run_backtest_pure", fake_run_backtest_pure)
    monkeypatch.setattr(DiscoveryEngine, "_build_production_edges",
                        lambda self, **kw: ({"base_edge": _BaselineEdge()}, {"base_edge": 1.0}))
    monkeypatch.setattr(DiscoveryEngine, "_instantiate_candidate",
                        staticmethod(lambda spec: _CandidateEdge()))
    monkeypatch.setattr(DiscoveryEngine, "_load_universe_b", lambda self, **kw: {"BBB": df})
    monkeypatch.setattr(
        "engines.engine_d_discovery.robustness.RobustnessTester.calculate_pbo_returns_stream",
        lambda self, *a, **kw: {"survival_rate": 1.0, "actual_sharpe": 1.0, "avg_synthetic_sharpe": 0.5})
    monkeypatch.setattr("engines.engine_d_discovery.significance.monte_carlo_permutation_test",
                        lambda values, **kw: {"p_value": 0.001})

    def _no_factors(auto_download=False):
        raise FileNotFoundError("not needed")
    monkeypatch.setattr("core.factor_decomposition.load_factor_data", _no_factors)

    r = g78._make_disc().validate_candidate(
        # SPY as in production: the Gate-1 census proves the calendar against it (the guard, 10-15)
        g78._make_cand_spec(), {"AAA": df, "SPY": df}, significance_threshold=0.05, alpha_config={},
        n_trials_for_dsr=1, data_map_substrate_b={"SUBB": df})   # use_signal_cache defaults True

    assert r["gate_verdicts"]["gate_5"]["verdict"] != gv.NOT_EVALUATED, "precondition: Gate 5 ran"
    assert r["gate_verdicts"]["gate_7"]["verdict"] != gv.NOT_EVALUATED, "precondition: Gate 7 ran"
    runs_on = {dm for dm, _ in seen}
    assert {frozenset({"BBB"}), frozenset({"SUBB"})} <= runs_on, "precondition: both B runs happened"
    leaks = sorted({(tuple(dm), tuple(sig)) for dm, sig in seen if not sig <= dm})
    assert not leaks, f"a with-arm on another data_map replayed signals for other tickers: {leaks}"


# --------------------------------------------------------------------------- #
# Gate 7 in production: the substrate-B build (the swallowed NameError)
# --------------------------------------------------------------------------- #
def _drive_cycle(monkeypatch, tmp_path, *, cached_tickers=lambda: ["AAA", "SB1", "SB2"],
                 validate_raises=None, hunt_raises=None, seen=None, with_spy=True, regime_raises=None,
                 queued_raises=None):
    """The REAL `_run_discovery_cycle` with only upstream work stubbed (R's F2 pattern),
    plus a resolvable historical universe so the substrate-B build has data. `seen` is
    filled as the cycle runs, so a test can inspect it even when the cycle raises."""
    import orchestration.mode_controller as mcmod
    from engines.engine_d_discovery import discovery as dmod
    from engines.engine_d_discovery import discovery_logger as dlog
    from engines.data_manager import universe_resolver as ur
    from tests.test_referee_repairs_proposed import _honest_n_fixture

    seen = seen if seen is not None else {}
    seen.update({"substrate_b": [], "timeframes": [], "saved": [], "logged": [], "failures": [],
                 "hunted": False})
    monkeypatch.setattr(dmod.DiscoveryEngine, "__init__", lambda self, **kw: None)

    def _hunt(self, *a, **kw):
        seen["hunted"] = True
        if hunt_raises is not None:
            raise hunt_raises
        return []
    monkeypatch.setattr(dmod.DiscoveryEngine, "hunt", _hunt)
    monkeypatch.setattr(dmod.DiscoveryEngine, "generate_candidates", lambda self, **kw: [])
    def _queued(self, status="candidate"):
        if queued_raises is not None:
            raise queued_raises
        return [{"edge_id": "cand_0", "status": "candidate", "params": {}}]
    monkeypatch.setattr(dmod.DiscoveryEngine, "get_queued_candidates", _queued)
    monkeypatch.setattr(dmod.DiscoveryEngine, "save_candidates",
                        lambda self, cands: seen["saved"].extend((c["edge_id"], c["status"]) for c in cands))

    def _validate(self, cand, *a, **kw):
        seen["substrate_b"].append(kw.get("data_map_substrate_b"))
        if validate_raises is not None:
            raise validate_raises
        return {"passed_all_gates": False, "sharpe": 0.0, "significance_p": 1.0}
    monkeypatch.setattr(dmod.DiscoveryEngine, "validate_candidate", _validate)
    monkeypatch.setattr(dlog.DiscoveryLogger, "__init__", lambda self, **kw: None)
    monkeypatch.setattr(dlog.DiscoveryLogger, "log_validation",
                        lambda self, cid, result, promoted: seen["logged"].append((cid, result)))
    monkeypatch.setattr(dlog.DiscoveryLogger, "log_cycle_summary", lambda self, *a, **kw: None)
    monkeypatch.setattr(dlog.DiscoveryLogger, "log_cycle_failure",
                        lambda self, stage, error, notes=None: seen["failures"].append((stage, error)))

    def _cached(cache_dir, timeframe="1d", **kw):
        seen["timeframes"].append(timeframe)
        return cached_tickers()
    monkeypatch.setattr(ur, "discover_cached_tickers", _cached)
    monkeypatch.setattr(ur, "resolve_universe",
                        lambda **kw: (["AAA", "SB1", "SB2"], {"mode": "historical"}))

    idx = pd.date_range("2024-01-02", periods=50, freq="B")
    df = pd.DataFrame({"Close": 100.0}, index=idx)

    def _ensure_data(tickers, start, end, timeframe):
        seen["timeframes"].append(timeframe)
        return {t: df for t in tickers}

    fake_self = SimpleNamespace(root=tmp_path, timeframe="1d",
                                cfg_bt={"start_date": "2024-01-02", "end_date": "2024-03-08",
                                        "tickers": ["AAA"]},
                                dm=SimpleNamespace(ensure_data=_ensure_data))
    def _detect(benchmark_df, data_map=None):
        if regime_raises is not None:
            raise regime_raises
        return {"regime_summary": "fixture"}

    _honest_n_fixture(tmp_path)
    data_map = {"AAA": df, **({"SPY": df} if with_spy else {})}
    mcmod.ModeController._run_discovery_cycle(fake_self, data_map, SimpleNamespace(detect_regime=_detect))
    return seen


def test_the_cycle_BUILDS_substrate_B_and_hands_it_to_the_gauntlet(monkeypatch, tmp_path):
    """Revert to the bare `timeframe` → NameError in the build (before RR-6a: swallowed as
    'gate skipped' and Gate 7 passed; now the cycle FAILS on it — ruling (c))."""
    seen = _drive_cycle(monkeypatch, tmp_path)
    assert len(seen["substrate_b"]) == 1, seen
    assert seen["substrate_b"][0] is not None and set(seen["substrate_b"][0]) == {"SB1", "SB2"}
    assert seen["timeframes"] == ["1d", "1d"], "self.timeframe reaches both the cache scan and ensure_data"


def test_a_programmer_error_in_the_substrate_B_build_is_never_a_skipped_gate(monkeypatch, tmp_path):
    """The block may degrade on DATA unavailability; it may never absorb a NameError.
    Revert the catch-all → the NameError reads as 'gate skipped', nothing raises, and the
    candidate is validated with no substrate B (pre-RR-6a: a free Gate 7)."""
    def _broken():
        raise NameError("name 'timeframe' is not defined")
    seen = {}
    with pytest.raises(NameError):
        _drive_cycle(monkeypatch, tmp_path, cached_tickers=_broken, seen=seen)
    assert seen["substrate_b"] == [], "a candidate was validated after a programmer error in the build"
    assert seen["saved"] == []
    assert seen["failures"] and seen["failures"][0][0] == "substrate-B build (Gate 7)"


# --------------------------------------------------------------------------- #
# RR-6a fixup — the director's rulings (b) and (c): the cycle's handlers
# --------------------------------------------------------------------------- #
def test_a_programmer_error_inside_validation_FAILS_the_cycle_never_a_failed_candidate(monkeypatch, tmp_path):
    """Ruling (b). The per-candidate handler caught EVERYTHING and recorded the candidate
    'failed' — so a NameError inside the gauntlet would fail every candidate, a plausible
    'promotes nothing'. Revert the catch-all → no raise, and cand_0 is written 'failed'."""
    seen = {}
    with pytest.raises(NameError) as ei:
        _drive_cycle(monkeypatch, tmp_path, validate_raises=NameError("name 'x' is not defined"), seen=seen)
    assert seen["saved"] == [], f"a programmer error was recorded as a candidate verdict: {seen['saved']}"
    assert seen["failures"] == [("validate cand_0", "NameError: name 'x' is not defined")]
    assert "[_run_discovery_cycle] failed at stage 'validate cand_0'" in getattr(ei.value, "__notes__", [])


def test_the_diagnostic_TIMEOUT_is_the_one_expected_class_and_renders_NOT_EVALUATED(monkeypatch, tmp_path):
    """Positive control for ruling (b): the typed, expected failure is still handled — the
    candidate is refused with every gate NOT_EVALUATED and the reason, and the cycle goes on.
    (It used to record a bare dict with no verdicts at all.)"""
    seen = _drive_cycle(monkeypatch, tmp_path, validate_raises=TimeoutError("validate_candidate exceeded 5s"))
    assert seen["saved"] == [("cand_0", "failed")]
    (cid, result), = seen["logged"]
    assert result["passed_all_gates"] is False
    assert {v["verdict"] for v in result["gate_verdicts"].values()} == {gv.NOT_EVALUATED}
    assert all("timeout" in r for r in result["promotion_refusals"])


def test_a_failure_outside_validation_FAILS_the_cycle_loudly_and_is_logged(monkeypatch, tmp_path):
    """Ruling (c). The outer handler re-raised only HonestNUnavailableError; anything else
    ended the cycle as one WARN line — a cycle that 'found nothing'. Revert → no raise."""
    seen = {}
    with pytest.raises(RuntimeError, match="feature store unreadable"):
        _drive_cycle(monkeypatch, tmp_path, hunt_raises=RuntimeError("feature store unreadable"), seen=seen)
    assert seen["failures"] == [("hunt", "RuntimeError: feature store unreadable")]
    assert seen["substrate_b"] == [] and seen["saved"] == []


def test_no_regime_context_REFUSES_the_cycle_it_never_hunts_context_free(monkeypatch, tmp_path):
    """The director's ruling on §5.6. With no SPY the regime step used to leave
    regime_meta=None and run the hunt anyway — a different experiment under the same
    label. Revert → the hunt runs and nothing raises."""
    from engines.engine_d_discovery.discovery import RegimeContextUnavailable
    seen = {}
    with pytest.raises(RegimeContextUnavailable, match="no SPY bars"):
        _drive_cycle(monkeypatch, tmp_path, with_spy=False, seen=seen)
    assert seen["hunted"] is False
    assert seen["failures"][0][0] == "regime context"


def test_an_engine_E_error_in_the_regime_step_propagates_never_skipped(monkeypatch, tmp_path):
    """Same ruling: only the typed unavailability refuses; anything Engine E raises propagates.
    Revert the catch-all → "Regime detection skipped" and a context-free hunt."""
    seen = {}
    with pytest.raises(NameError):
        _drive_cycle(monkeypatch, tmp_path, regime_raises=NameError("name 'vix' is not defined"), seen=seen)
    assert seen["hunted"] is False
    assert seen["failures"] == [("regime context", "NameError: name 'vix' is not defined")]


def test_validate_candidate_names_the_candidate_and_last_gate_on_a_programmer_error(monkeypatch):
    """Ruling (c), the 'which gate' half: an error re-raised out of the gauntlet carries
    the candidate and the last gate it completed. Revert the note → absent."""
    def _pbo_broken(self, *a, **kw):
        raise NameError("name 'pbo' is not defined")
    data_map, idx = g78._make_synthetic_dfs()
    base, with_ = _strong_streams(idx)
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": 1.0,
                   "daily_returns_with": with_, "daily_returns_baseline": base})
    monkeypatch.setattr(
        "engines.engine_d_discovery.robustness.RobustnessTester.calculate_pbo_returns_stream", _pbo_broken)
    with pytest.raises(NameError) as ei:
        g78._make_disc().validate_candidate(g78._make_cand_spec(), data_map,
                                            significance_threshold=0.05, alpha_config={}, n_trials_for_dsr=2)
    assert "[validate_candidate] candidate=candidate_v0 last_gate_completed=gate_1" in getattr(
        ei.value, "__notes__", [])


def test_run_evolution_cycle_validates_on_the_production_window(monkeypatch):
    """Ruling (a). This dashboard-reachable path passed NO window, so Gate 0 never ran — and
    under RR-6a it would be NOT_EVALUATED and refuse every candidate: a silently dead path.
    It must hand the gauntlet the same full-extent window production Discovery uses.
    Revert → start_date/end_date are absent."""
    run_evo = pytest.importorskip("scripts.run_evolution_cycle")
    import core.benchmark as bm
    from tests.test_evolution_cycle_verdict_rr2 import _Log

    seen_kw = []

    class _Disc:
        def get_queued_candidates(self, status="candidate"):
            return [{"edge_id": "cand_0", "status": "candidate", "params": {}}]

        def generate_candidates(self, **kw):
            return []

        def validate_candidate(self, cand, data_map, **kw):
            seen_kw.append(kw)
            return {"passed_all_gates": False}

        def save_candidates(self, cands):
            pass

    monkeypatch.setattr(bm, "compute_benchmark_metrics",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    evo = object.__new__(run_evo.AutonomousEvolution)
    evo.discovery, evo.discovery_logger, evo.wfo = _Disc(), _Log(), None
    idx = pd.bdate_range("2012-01-02", periods=3269)
    evo.data_map = {"SPY": pd.DataFrame({"Close": range(len(idx))}, index=idx)}
    evo._promote_winners = lambda winners: None
    evo.run_cycle()
    (kw,) = seen_kw
    assert (kw.get("start_date"), kw.get("end_date")) == (idx[0].isoformat(), idx[-1].isoformat())


def test_a_DATA_failure_in_the_substrate_B_build_degrades_to_no_substrate_B(monkeypatch, tmp_path):
    """Positive control for the narrowing: genuine data unavailability still degrades
    (Gate 7 then renders NOT_EVALUATED inside the gauntlet, which refuses)."""
    def _no_cache():
        raise OSError("cache directory unreadable")
    seen = _drive_cycle(monkeypatch, tmp_path, cached_tickers=_no_cache)
    assert seen["substrate_b"] == [None]


# --------------------------------------------------------------------------- #
# Re-queue forever (run_evolution_cycle)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wfo_result, reason_fragment", [
    ({}, "WFO returned no result"),
    ({"degradation": 0.1}, "Poor OOS consistency"),
])
def test_a_WFO_rejection_leaves_the_queue_with_its_reason(monkeypatch, wfo_result, reason_fragment):
    """Both WFO rejections used to `continue` with status 'candidate' — re-queued and
    re-run through the full gauntlet on every cycle, forever. Revert → 'candidate'."""
    run_evo = pytest.importorskip("scripts.run_evolution_cycle")
    import core.benchmark as bm
    from tests.test_evolution_cycle_verdict_rr2 import _Log

    class _Disc:
        def __init__(self):
            self.queued = [{"edge_id": "cand_0", "status": "candidate", "params": {}}]
            self.saved = None

        def get_queued_candidates(self, status="candidate"):
            return self.queued

        def generate_candidates(self, **kw):
            return []

        def validate_candidate(self, cand, data_map, **kw):
            return {"passed_all_gates": True, "sharpe": 5.0, "sortino": 3.0,
                    "robustness_survival": 0.9, "significance_p": 0.0001,
                    "universe_b_sharpe": 1.0, "universe_b_n_tickers": 20}

        def save_candidates(self, cands):
            self.saved = {c["edge_id"]: dict(c) for c in cands}

    class _WFO:
        def run_optimization(self, cand, **kw):
            return dict(wfo_result)

    monkeypatch.setattr(bm, "compute_benchmark_metrics",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    evo = object.__new__(run_evo.AutonomousEvolution)
    evo.discovery, evo.discovery_logger, evo.wfo = _Disc(), _Log(), _WFO()
    evo.data_map = {"SPY": pd.DataFrame({"Close": range(800)},
                                        index=pd.bdate_range("2020-01-01", periods=800))}
    evo._promote_winners = lambda winners: None
    evo.run_cycle()
    saved = evo.discovery.saved["cand_0"]
    assert saved["status"] == "failed", saved
    assert reason_fragment in saved["rejection_reason"]


# --------------------------------------------------------------------------- #
# The required-gates config and the verdict contract
# --------------------------------------------------------------------------- #
def test_the_committed_required_gates_are_pinned():
    """A change to which gates bind promotion is a reviewed diff, never a quiet edit."""
    from engines.engine_d_discovery.thresholds import required_gates
    assert required_gates() == ("gate_0", "gate_1", "gate_2", "gate_4", "gate_5", "gate_7", "gate_8")


@pytest.mark.parametrize("patch, match", [
    ({"required_gates": ["gate_1", "gate_3"]}, "recorded only"),
    ({"required_gates": ["gate_1", "gate_9"]}, "unknown gates"),
    ({"required_gates": []}, "non-empty"),
    ({"required_gates": ["gate_1", "gate_6"]}, "disagree about Gate 6"),          # mode is 'report'
    ({"factor_gate_mode": "kill"}, "disagree about Gate 6"),                     # gate_6 not listed
])
def test_an_incoherent_required_gates_config_is_refused(tmp_path, patch, match):
    from engines.engine_d_discovery.thresholds import SETTINGS_PATH, required_gates
    cfg = json.loads(SETTINGS_PATH.read_text())
    cfg.update(patch)
    p = tmp_path / "discovery_settings.json"
    p.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match=match):
        required_gates(p)


def test_a_missing_required_gates_key_fails_closed(tmp_path):
    from engines.engine_d_discovery.thresholds import SETTINGS_PATH, required_gates
    cfg = json.loads(SETTINGS_PATH.read_text())
    del cfg["required_gates"]
    p = tmp_path / "discovery_settings.json"
    p.write_text(json.dumps(cfg))
    with pytest.raises(KeyError):
        required_gates(p)


def test_the_verdict_contract_has_no_defaults():
    v = gv.new_verdicts()
    del v["gate_7"]
    with pytest.raises(KeyError):
        gv.promotion_decision(v, ("gate_1", "gate_7"))
    with pytest.raises(KeyError):
        gv.first_failed_gate({"passed_all_gates": False})      # no gate_verdicts: no guess
    with pytest.raises(ValueError):
        gv.promotion_decision(gv.new_verdicts(), ())
    with pytest.raises(ValueError):
        gv.render(gv.new_verdicts(), "gate_3", True, "x")       # recorded-only gate
