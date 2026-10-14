"""RR-3 (proposal) — fail-closed honest-N, exact E[max], correlation-aware N_eff.

The brief's three xfails (tests/test_referee_repairs_proposed.py) check the leaf
function. These check the INTEGRATION, because the defect was never one line: a
missing registry was absorbed by FOUR successive layers —

  1. mbl_gate.compute_n_effective         `return 1`
  2. discovery Gate 0                      `except (ValueError, FileNotFoundError): log + proceed`
  3. discovery Gate 8 + validate_candidate `except Exception: n = 1`, then "candidate failed"
  4. mode_controller._run_discovery_cycle  `except Exception: print WARN`

— so fixing layer 1 alone turns the xfail green and changes nothing in production.
Every test below DRIVES a real entrypoint (the 2026-09-14 lesson: a text assertion
cannot catch what only execution can), and each would fail if its layer were reverted.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import core.measurement.mbl_gate as mbl
from core.measurement.mbl_gate import (
    HonestNUnavailableError,
    compute_mbl_min,
    compute_n_effective,
    compute_n_effective_correlated,
    expected_max_normal,
    n_eff_equicorrelated,
)


# ----------------------------------------------------------------------------- fixtures
def _registry(path: Path, n: int) -> Path:
    import sqlite3
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, snapshot_at TEXT)")
    c.executemany("INSERT INTO runs VALUES (?, ?)", [(f"r{i}", "2026-01-01") for i in range(n)])
    c.commit(); c.close()
    return path


def _artifact(d: Path, rho: float = 0.43, comp: float = 0.16, name="n_effective_2026-09-30.json") -> Path:
    p = d / name
    p.write_text(json.dumps({"rho_bar": 0.6, "onc_compression": 0.06,
                             "gate_inputs": {"rho_bar": rho, "onc_compression": comp}}))
    return p


@pytest.fixture
def no_registry(tmp_path, monkeypatch):
    """Every N source pointed at nothing — the state of every cloud container."""
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", tmp_path / "absent.sqlite")
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", tmp_path)
    return tmp_path


# ----------------------------------------------------------------------------- the maths
def test_the_error_is_a_FileNotFoundError_as_the_brief_specifies():
    assert issubclass(HonestNUnavailableError, FileNotFoundError)


@pytest.mark.parametrize("n", [75, 231, 260, 500])
def test_expected_max_is_within_2pct_of_exact_integration(n):
    from scipy import integrate, stats
    f = lambda x: x * n * stats.norm.pdf(x) * stats.norm.cdf(x) ** (n - 1)
    exact, _ = integrate.quad(f, -10, 10, limit=200)
    assert abs(expected_max_normal(n) - exact) / exact < 0.02


def test_gate0_and_gate8_share_one_euler_gamma():
    """Gate 0 (MinBTL) and Gate 8 (DSR) must use the SAME E[max] — one constant."""
    from core import metrics_engine
    assert mbl._EULER_GAMMA is metrics_engine._EULER_GAMMA


def test_exact_form_is_below_the_bound_and_bound_reproduces_2lnN():
    for n in (10, 100, 260, 1000):
        assert compute_mbl_min(n) < compute_mbl_min(n, upper_bound=True)
        assert math.isclose(compute_mbl_min(n, upper_bound=True), 2 * math.log(n))
    # the probe's headline: ~38.7% overstatement at N=260
    over = compute_mbl_min(260, upper_bound=True) / compute_mbl_min(260) - 1
    assert 0.33 < over < 0.40


def test_equicorrelated_identity_limits_and_monotonicity():
    assert n_eff_equicorrelated(231, 0.0) == 231
    assert n_eff_equicorrelated(231, -0.2) == 231, "negative ρ̄ must not license MORE trials"
    assert n_eff_equicorrelated(231, 1.0) == mbl.N_EFF_FLOOR
    vals = [n_eff_equicorrelated(231, r) for r in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert vals == sorted(vals, reverse=True)
    # the identity itself: E[max_Neff] == sqrt(1-ρ)·E[max_N]
    ne = n_eff_equicorrelated(231, 0.43)
    assert math.isclose(expected_max_normal(ne), math.sqrt(0.57) * expected_max_normal(231), rel_tol=1e-4)


def test_a_correlation_estimate_can_never_erase_the_correction():
    """N_eff = 1 would make MinBTL 0 — defect 1's door, reached by another route."""
    for r in (0.95, 0.99, 0.999999):
        assert n_eff_equicorrelated(231, r) >= mbl.N_EFF_FLOOR > 1
        assert compute_mbl_min(n_eff_equicorrelated(231, r)) > 0


# ----------------------------------------------------------------------------- layer 1
def test_layer1_absent_empty_and_zero_byte_registries_all_raise(tmp_path):
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(tmp_path / "absent.sqlite")
    import sqlite3
    e = tmp_path / "empty.sqlite"; c = sqlite3.connect(e); c.execute("CREATE TABLE runs (run_id TEXT)"); c.commit(); c.close()
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(e)
    z = tmp_path / "zero.db"; z.write_bytes(b"")
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(z)


def test_correlated_n_fails_closed_on_missing_or_malformed_artifact(tmp_path):
    """RR-3 §9.3: the artifact is now selected by a PIN, so 'missing' means a missing pin or a
    missing pinned file — and a malformed artifact still fails even when correctly pinned."""
    reg = _registry(tmp_path / "r.sqlite", 100)
    pin = tmp_path / "pin.json"
    with pytest.raises(HonestNUnavailableError, match="pin"):
        compute_n_effective_correlated(reg, artifact_dir=tmp_path, pin_path=pin)
    bad = tmp_path / "n_effective_2026-01-01.json"
    bad.write_text(json.dumps({"rho_bar": 0.5}))
    pin.write_text(json.dumps({"artifact": {"file": bad.name, "sha256": mbl.sha256_file(bad)},
                               "registry": {"file": reg.name, "sha256": mbl.sha256_file(reg)}}))
    with pytest.raises(HonestNUnavailableError, match="gate_inputs"):
        compute_n_effective_correlated(reg, artifact_dir=tmp_path, pin_path=pin)


def test_conservative_method_takes_the_larger_estimate(tmp_path):
    reg = _registry(tmp_path / "r.sqlite", 231)
    art = _artifact(tmp_path, rho=0.43, comp=0.16)
    onc = compute_n_effective_correlated(reg, method="onc", artifact_path=art)
    eq = compute_n_effective_correlated(reg, method="equicorr", artifact_path=art)
    cons = compute_n_effective_correlated(reg, artifact_path=art)
    assert cons == max(onc, eq)
    assert math.isclose(onc, 231 * 0.16)


def test_gate_reads_the_CONSERVATIVE_bounds_not_the_point_estimates(tmp_path):
    """The artifact carries point ρ̄=0.6 / compression 0.06 AND gate inputs 0.43 / 0.16.
    The gate must read the latter — the bounds that make N_eff larger."""
    reg = _registry(tmp_path / "r.sqlite", 231)
    art = _artifact(tmp_path, rho=0.43, comp=0.16)
    eq = compute_n_effective_correlated(reg, method="equicorr", artifact_path=art)
    assert math.isclose(eq, n_eff_equicorrelated(231, 0.43))
    assert eq > n_eff_equicorrelated(231, 0.6)


# ----------------------------------------------------------------------------- layer 2
def _bare_engine():
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    return DiscoveryEngine.__new__(DiscoveryEngine)


def _spec():
    return {"edge_id": "rr3_probe_v0", "module": "x", "class": "X", "category": "technical",
            "params": {}, "status": "candidate", "version": 1, "origin": "test"}


def test_layer2_gate0_PROPAGATES_an_unavailable_N_out_of_validate_candidate(no_registry):
    """Pre-RR-3: 'log + proceed' → N=1 → MinBTL 0 → PASS, then the gauntlet ran.
    Now the harness failure leaves validate_candidate before any backtest."""
    with pytest.raises(HonestNUnavailableError):
        _bare_engine().validate_candidate(_spec(), {}, start_date="2010-01-01", end_date="2024-12-31")


def test_layer2_explicit_N_is_honoured_and_recorded(no_registry):
    """The escape hatch: an explicit count needs no registry, and it is the N reported."""
    r = _bare_engine().validate_candidate(_spec(), {}, start_date="2024-01-01", end_date="2024-06-30",
                                          n_trials_for_dsr=37)
    assert r["killed_by_gate"] == "gate_0_mbl"
    assert r["gate_0_n_effective"] == 37
    assert r["gate_0_n_effective_source"] == "explicit"


def test_layer2_an_unparseable_window_FAILS_gate0_instead_of_skipping_it(no_registry):
    r = _bare_engine().validate_candidate(_spec(), {}, start_date="not-a-date", end_date="2024-12-31",
                                          n_trials_for_dsr=37)
    assert r["passed_all_gates"] is False
    assert r["killed_by_gate"] == "gate_0_unevaluable"


# ----------------------------------------------------------------------------- layer 3
def test_layer3_gate8_PROPAGATES_through_validate_candidates_outer_handler(no_registry, monkeypatch):
    """Gate 0 off (no dates) so the N is first needed at Gate 8. Pre-RR-3: `except
    Exception: n = 1` → Gate 8 SKIPPED with its default gate_8_passed=True. Even with that
    swallow removed, the outer per-candidate handler would have converted the raise into
    'candidate failed' — the T-177 'Discovery promotes nothing' shape."""
    from tests.test_discovery_gates_7_8 import (
        _make_cand_spec,
        _make_disc,
        _make_synthetic_dfs,
        _wire_validate_candidate_happy_path,
    )
    data_map, idx = _make_synthetic_dfs()
    rets = pd.Series(0.001, index=idx[1:])
    _wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": rets + 0.0005, "daily_returns_baseline": rets},
        results_b={"with_sharpe": 1.5, "baseline_sharpe": 1.0,
                   "daily_returns_with": rets + 0.0005, "daily_returns_baseline": rets},
    )
    with pytest.raises(HonestNUnavailableError):
        _make_disc().validate_candidate(
            _make_cand_spec(), data_map, significance_threshold=0.05,
            gate1_contribution_threshold=-1e6, gate2_survival_threshold=0.0,
            candidate_default_weight=1.0, alpha_config={})


# ----------------------------------------------------------------------------- layer 4
def test_layer4_the_discovery_cycle_halts_BEFORE_any_side_effect(tmp_path, monkeypatch):
    """Pre-RR-3 the cycle's own `except Exception: print WARN` absorbed everything, and N
    was resolved only after hunting and after save_candidates() wrote edges.yml. Now N is
    resolved first: with no registry the cycle raises and DiscoveryEngine is never built."""
    import engines.engine_d_discovery.discovery as disc_mod
    from orchestration.mode_controller import ModeController

    constructed = []

    class _Sentinel:
        def __init__(self, *a, **k):
            constructed.append(True)
            raise AssertionError("DiscoveryEngine built before honest N was established")

    monkeypatch.setattr(disc_mod, "DiscoveryEngine", _Sentinel)
    mc = ModeController.__new__(ModeController)
    mc.root = tmp_path                       # no data/observability here
    with pytest.raises(HonestNUnavailableError):
        mc._run_discovery_cycle({}, regime_detector=None)
    assert not constructed


def test_layer4_the_cycle_resolves_N_from_ITS_OWN_root(tmp_path):
    """The cycle reads <root>/data/observability, not the module default, so a controller
    pointed at another tree cannot silently gate on this tree's registry."""
    obs = tmp_path / "data" / "observability"; obs.mkdir(parents=True)
    _registry(obs / "run_registry.sqlite", 50)
    art = _artifact(obs, rho=0.43, comp=0.16)
    (tmp_path / "config").mkdir()
    pin = tmp_path / "config" / "honest_n_pin.json"
    from scripts.honest_n_pin import write_pin
    write_pin(art.name, artifact_dir=obs, db_path=obs / "run_registry.sqlite", pin_path=pin)
    info = mbl.resolve_cycle_n_trials(10, db_path=obs / "run_registry.sqlite", artifact_dir=obs,
                                      pin_path=pin)
    assert info["source"] == "registry_correlated" and info["batch_len"] == 10
    assert info["n_trials"] == max(n_eff_equicorrelated(50, 0.43), 50 * 0.16)


# ----------------------------------------------------------------------------- the script
def _synthetic_runs(root: Path) -> None:
    """3 campaigns × 4 configs over 2 years, one determinism rep, one empty run."""
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2023-01-02", "2024-12-31")
    market = rng.normal(0.0004, 0.01, len(days))
    k = 0
    for c in range(3):
        camp = rng.normal(0, 0.006, len(days))
        for _ in range(4):
            r = 0.7 * market + 0.5 * camp + rng.normal(0, 0.004, len(days))
            eq = 100_000 * np.cumprod(1 + r)
            d = root / f"campaign{c}" / f"{k:08d}-0000-0000-0000-000000000000"
            d.mkdir(parents=True)
            pd.DataFrame({"timestamp": days, "equity": eq}).to_csv(d / "portfolio_snapshots.csv", index=False)
            k += 1
    src = root / "campaign0" / "00000000-0000-0000-0000-000000000000"
    rep = root / "campaign0" / "99999999-0000-0000-0000-000000000000"; rep.mkdir()
    (rep / "portfolio_snapshots.csv").write_text((src / "portfolio_snapshots.csv").read_text())
    empty = root / "campaign1" / "88888888-0000-0000-0000-000000000000"; empty.mkdir()
    (empty / "portfolio_snapshots.csv").write_text("timestamp,equity\n")


def test_the_empirical_script_end_to_end_feeds_the_gate(tmp_path):
    from scripts import rr3_empirical_rho as script
    mirror = tmp_path / "mirror"; _synthetic_runs(mirror)
    reg = _registry(tmp_path / "reg.sqlite", 40)
    out = tmp_path / "obs" / "n_effective_2026-09-30.json"
    art = script.run(mirror, tmp_path / "no_trade_logs", reg, out)

    assert art["funnel"] == {"discovered": 14, "valid": 13, "after_dedupe": 12}
    assert art["determinism_rep_groups"]["runs_removed_as_reps"] == 1
    assert art["rho_bar"] > 0.3, "the synthetic trials share a strong common factor"
    gi = art["gate_inputs"]
    assert gi["rho_bar"] <= min(v["rho_bar"] for v in art["rho"].values()), "gate ρ̄ is not the conservative one"
    assert gi["onc_compression"] >= art["onc_compression"], "gate compression is not the conservative one"
    assert art["n_trials_consumed"] == 0
    assert "NOT the run registry" in art["population"]
    # and the gate consumes exactly this artifact
    n = compute_n_effective_correlated(reg, artifact_path=out)
    assert n == max(n_eff_equicorrelated(40, gi["rho_bar"]), min(40.0, max(2.0, 40 * gi["onc_compression"])))
