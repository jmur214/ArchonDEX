"""tests/test_edge_registry_single_writer.py — the edges.yml single-writer unit's locks.

The brief: docs/Sources/edge_registry_single_writer_brief_2026-10-14.md (v4, user-approved 2026-10-22,
R: BUILD IT). Every lock DRIVES the real entrypoint — a subprocess that imports the real modules, the
real `validate_candidate`, the real `_load_edges_via_registry`, the real `_post_run`, the real
`LifecycleManager.evaluate`, the real sync — never a text assertion. Each is reversion-proven
(scripts/registry_single_writer_reversion_proof.py): revert only the line it guards and it fails.

Locks, in the brief's numbering:
  1. pure imports, measured — sha256 AND mtime unchanged on a planted corrupt registry and on a healthy
     COPY of the real one; the import succeeds; the modules are ENUMERATED (27 since the archive);
  2. the key-wise params merge — a registry-only key survives, drift takes the code value, a type
     change is its own class;
  3. byte identity across the three writers (Discovery, Engine F, the sync / Engine A), including a
     row Discovery wrote first, and the real registry's 218 rows (the migration is a null diff);
  4. the empty book renders (Gate 1 NOT_EVALUATED), bootstrap promotes and the census carries it, an
     UNREADABLE registry is a hard refusal;
  5. isolation mode refuses a missing id, naming the sync;
  6. the first-sync report's distinct classes; `--check` exits 1 and writes nothing; a no-op sync
     leaves bytes AND mtime untouched;
  7. the fleet never imports an edge module (executed, not grepped).
Also: default mode refuses an empty registry and never falls back to default edges; a fresh checkout
refuses until the sync runs, then succeeds; Engine F — a planted dump error leaves the bytes untouched
and raises, no history row after a failed save, `post_run_failure` lands in the summary and the census
says NON-CANONICAL, `run_backtest` writes the summary THEN raises; Discovery's cycle failure takes the
same shape (R §4.3).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from core.edge_registry_io import (
    RegistryUnreadableError,
    RegistryWriteError,
    read_registry,
    serialise,
    write_registry_atomic,
    write_registry_if_changed,
)
from engines.engine_a_alpha.edge_registry import EdgeRegistry, EdgeSpec

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "tests" / "fixtures" / "edges_registry_snapshot_2026_10_22.yml"
SNAPSHOT_SHA = "edf1ffaf3b6f97e9f05def5c8505558d16b5bddf58648ce2551bcc441cd14380"
DRIVER_IMPORT = REPO / "tests" / "_drivers" / "import_edge_modules.py"
DRIVER_FLEET = REPO / "tests" / "_drivers" / "import_fleet.py"

#: The modules the sync imports and lock 1 proves pure — ENUMERATED (R §5: the brief's 30 vs R's 29;
#: 27 since betting_against_beta / overnight_intraday / volatility_risk_premium were archived).
AUTO_REGISTERING_2026_10_22 = [
    "accruals_inv_asset_growth_edge", "accruals_inv_sloan_edge", "calendar_anomaly_edge",
    "cot_positioning_edge", "dividend_initiation_drift_v1", "insider_cluster_edge",
    "leaps_catalyst_edge", "low_vol_factor_edge", "macro_credit_spread_edge",
    "macro_dollar_regime_edge", "macro_real_rate_edge", "macro_unemployment_momentum_edge",
    "macro_yield_curve_edge", "momentum_12_1_v1", "momentum_6_1_v1", "momentum_edge",
    "momentum_factor_edge", "pairs_trading_v1", "pead_edge", "pead_predrift_edge", "pead_short_edge",
    "quality_gross_profitability_edge", "quality_roic_edge", "short_term_reversal_v1",
    "spinoff_reversion_v1", "value_book_to_market_edge", "value_earnings_yield_edge",
]
CORRUPT = "edges:\n  - {edge_id: momentum_edge_v1, status: active\n  - {edge_id: x\n"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _plant(root: Path, text: str) -> Path:
    reg = root / "data" / "governor" / "edges.yml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(text)
    return reg


def _run(driver: Path, cwd: Path, *args: str) -> dict:
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    r = subprocess.run([sys.executable, str(driver), *args], cwd=str(cwd), env=env,
                       capture_output=True, text=True, timeout=600)
    last = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        out = json.loads(last)
    except json.JSONDecodeError:
        pytest.fail(f"driver {driver.name} printed no JSON (rc={r.returncode}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    out["rc"] = r.returncode
    out["stderr"] = r.stderr[-2000:]
    return out


# =========================================================================== #
# The enumeration (settles R's 29 vs the brief's 30)
# =========================================================================== #
def test_the_auto_registering_modules_are_exactly_the_enumerated_27():
    from scripts.sync_edge_registry import auto_registering_modules
    assert auto_registering_modules() == AUTO_REGISTERING_2026_10_22


# =========================================================================== #
# Lock 1 — pure imports, measured
# =========================================================================== #
@pytest.mark.parametrize("case", ["corrupt", "healthy_copy_of_the_real_registry"])
def test_LOCK1_importing_every_auto_registering_module_never_touches_the_registry(tmp_path, case):
    """Revert `ensure()` to register-and-save → the corrupt case is rewritten to the registered subset
    (bytes change) and the healthy copy's mtime moves."""
    reg = _plant(tmp_path, CORRUPT if case == "corrupt" else SNAPSHOT.read_text())
    sha, mtime = _sha(reg), reg.stat().st_mtime_ns
    out = _run(DRIVER_IMPORT, tmp_path, *AUTO_REGISTERING_2026_10_22)
    assert out["rc"] == 0 and not out["failures"], f"an import FAILED: {out['failures']}\n{out['stderr']}"
    assert set(out["per_module"]) == set(AUTO_REGISTERING_2026_10_22)
    assert _sha(reg) == sha, "importing the edge modules CHANGED the registry's bytes"
    assert reg.stat().st_mtime_ns == mtime, "importing the edge modules touched the registry's mtime"
    if case == "corrupt":
        # the fail-closed read refused inside every module's import-time try; nothing registered,
        # nothing written — the consumer refuses, never a one-edge file
        assert out["registered"] == []
    else:
        registered_by = {m for m, ids in out["per_module"].items() if ids}
        assert registered_by >= set(AUTO_REGISTERING_2026_10_22) - {"pairs_trading_v1"}, \
            set(AUTO_REGISTERING_2026_10_22) - registered_by
        assert out["unpersisted"] == [], f"the healthy registry lacks: {out['unpersisted']}"
        assert out["drifted"] == [], f"code-owned drift against the real registry: {out['drifted']}"


def test_LOCK1b_ensure_records_a_registration_and_never_mutates_the_loaded_specs(tmp_path):
    """In-process: `ensure()` of a NEW id is invisible to `get()` and to the file; of an EXISTING id it
    leaves status/tier/params untouched in memory and on disk, and records the drift it would apply."""
    reg_path = tmp_path / "edges.yml"
    reg = EdgeRegistry(store_path=reg_path)
    reg.register(EdgeSpec(edge_id="kept_v1", category="technical", module="m", params={"k": 1, "note": "x"},
                          status="paused", tier="alpha"))
    sha = _sha(reg_path)
    EdgeRegistry.clear_import_registrations()
    reg.ensure(EdgeSpec(edge_id="new_v1", category="technical", module="m", status="active"))
    reg.ensure(EdgeSpec(edge_id="kept_v1", category="technical", module="m", params={"k": 2}, status="active"))
    assert reg.get("new_v1") is None                       # invisible until the sync persists it
    assert reg.get("kept_v1").status == "paused" and reg.get("kept_v1").tier == "alpha"
    assert reg.get("kept_v1").params == {"k": 1, "note": "x"}
    assert _sha(reg_path) == sha                           # never written
    regs = EdgeRegistry.import_registrations()
    assert not regs["new_v1"].persisted and regs["new_v1"].report.never_registered
    assert regs["kept_v1"].persisted
    assert regs["kept_v1"].report.drift_applied == {"params.k": (1, 2)}
    assert regs["kept_v1"].report.registry_only_keys == ["params.note"]


# =========================================================================== #
# Lock 2 — the key-wise params merge (R §4.1)
# =========================================================================== #
def test_LOCK2_the_sync_merges_params_key_wise_and_reports_four_distinct_classes(tmp_path):
    """Plant a row for a REAL module with a registry-only key, a drifted code-owned value and a
    code-owned key of the wrong type. Revert to the wholesale `s.params = spec.params or s.params`
    → `validation_note` is gone and nothing is reported."""
    from engines.engine_a_alpha.edges.momentum_12_1_v1 import Momentum12_1Edge
    from scripts.sync_edge_registry import sync
    code = dict(Momentum12_1Edge.DEFAULT_PARAMS)
    numeric = [k for k in sorted(code) if isinstance(code[k], (int, float)) and not isinstance(code[k], bool)]
    drift_key = numeric[0]
    type_key = next(k for k in sorted(code) if k != drift_key and not isinstance(code[k], str))
    planted = dict(code)
    planted[drift_key] = code[drift_key] + 1            # same TYPE, different value → drift
    planted[type_key] = str(code[type_key])             # same value, wrong TYPE → a type change
    planted["validation_note"] = "keep me — Discovery wrote this"
    reg_path = tmp_path / "edges.yml"
    write_registry_atomic(reg_path, {"edges": [{
        "edge_id": "momentum_12_1_v1", "category": Momentum12_1Edge.CATEGORY,
        "module": "engines.engine_a_alpha.edges.momentum_12_1_v1", "version": "1.0.0",
        "params": planted, "status": "paused", "tier": "alpha", "tier_last_updated": "2026-01-01T00:00:00+00:00",
    }]})
    report = sync(reg_path, modules=["momentum_12_1_v1"])
    assert report.additions == []
    assert report.drift_applied == {"momentum_12_1_v1": {f"params.{drift_key}": [planted[drift_key], code[drift_key]]}}
    assert report.type_changes == {"momentum_12_1_v1": {f"params.{type_key}": ["str", type(code[type_key]).__name__]}}
    assert report.registry_only_keys == {"momentum_12_1_v1": ["params.validation_note"]}
    assert report.wrote is True
    row = read_registry(reg_path)["edges"][0]
    assert row["params"]["validation_note"] == "keep me — Discovery wrote this"
    assert row["params"][drift_key] == code[drift_key] and row["params"][type_key] == code[type_key]
    assert row["status"] == "paused" and row["tier"] == "alpha"          # registry-owned, untouched
    assert row["tier_last_updated"] == "2026-01-01T00:00:00+00:00"
    # idempotent: the second sync changes nothing and touches nothing
    mtime = reg_path.stat().st_mtime_ns
    again = sync(reg_path, modules=["momentum_12_1_v1"])
    assert not again.changes_file and again.wrote is False and reg_path.stat().st_mtime_ns == mtime


# =========================================================================== #
# Lock 3 — byte identity across the three writers, and the migration null diff
# =========================================================================== #
def _discovery_write(path: Path, registry: dict) -> None:
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    eng = DiscoveryEngine.__new__(DiscoveryEngine)
    eng.registry_path = path
    eng._write_registry(registry)


def _lifecycle_write(path: Path, registry: dict) -> None:
    from engines.engine_f_governance.lifecycle_manager import LifecycleManager
    lcm = LifecycleManager.__new__(LifecycleManager)
    lcm.registry_path = path
    lcm._registry_extra = {k: v for k, v in registry.items() if k != "edges"}
    lcm._save_registry(list(registry["edges"]))


def _engine_a_write(path: Path, registry: dict) -> None:
    src = path.with_name("src.yml")
    write_registry_atomic(src, registry)
    reg = EdgeRegistry(store_path=src)
    reg.path = path
    reg.save()


def _sync_write(path: Path, registry: dict) -> None:
    write_registry_if_changed(path, registry)


WRITERS = {"discovery": _discovery_write, "engine_f": _lifecycle_write, "engine_a": _engine_a_write, "sync": _sync_write}


def test_LOCK3_the_same_registry_saved_through_every_writer_is_one_sha256(tmp_path):
    """Including a row Discovery wrote FIRST, in Discovery's own key order (edge_id, module, class,
    category, params, status, version, origin). Revert Discovery's writer to raw `yaml.dump` → two
    hashes."""
    discovery_first = {"edge_id": "cand_mut_1", "module": "engines.engine_a_alpha.edges.gap_edge",
                       "class": "GapEdge", "category": "mean_reversion", "params": {"atr_mult": 1.5},
                       "status": "candidate", "version": "1.0.0-mut", "origin": "ga"}
    engine_a_row = {"edge_id": "rsi_bounce_v1", "category": "technical", "module": "rsi_bounce",
                    "version": "1.0.0", "params": {}, "status": "paused", "tier": "feature"}
    registry = {"edges": [engine_a_row, discovery_first]}
    hashes = {}
    for name, write in WRITERS.items():
        p = tmp_path / name / "edges.yml"
        p.parent.mkdir()
        write(p, registry)
        hashes[name] = _sha(p)
    assert len(set(hashes.values())) == 1, hashes
    # and the row Discovery wrote first comes back in the ONE canonical order from every writer
    row = read_registry(tmp_path / "discovery" / "edges.yml")["edges"][1]
    assert list(row) == ["edge_id", "category", "module", "version", "params", "status", "tier", "class", "origin"]


def test_LOCK3b_the_migration_is_a_null_diff_on_the_real_registry(tmp_path):
    """The real 218-row registry (frozen fixture) reproduced BYTE FOR BYTE by the one serialiser and by
    every writer, and a full sync of all 27 modules against it changes nothing — bytes AND mtime."""
    from scripts.sync_edge_registry import sync
    assert _sha(SNAPSHOT) == SNAPSHOT_SHA, "the fixture is not the registry as frozen on 2026-10-22"
    registry = read_registry(SNAPSHOT)
    assert len(registry["edges"]) == 218
    assert hashlib.sha256(serialise(registry).encode()).hexdigest() == SNAPSHOT_SHA
    for name, write in WRITERS.items():
        p = tmp_path / name / "edges.yml"
        p.parent.mkdir()
        write(p, registry)
        assert _sha(p) == SNAPSHOT_SHA, f"{name} changed the real registry's bytes"
    live = tmp_path / "live" / "data" / "governor" / "edges.yml"
    live.parent.mkdir(parents=True)
    shutil.copyfile(SNAPSHOT, live)
    os.chmod(live, 0o600)
    mtime = live.stat().st_mtime_ns
    report = sync(live, modules=AUTO_REGISTERING_2026_10_22)
    assert not report.changes_file, report.lines()
    assert report.additions == [] and report.drift_applied == {} and report.type_changes == {}
    assert report.wrote is False and _sha(live) == SNAPSHOT_SHA and live.stat().st_mtime_ns == mtime
    assert oct(live.stat().st_mode & 0o777) == "0o600"


# =========================================================================== #
# Lock 4 — the empty book renders; bootstrap promotes; unreadable is a hard refusal
# =========================================================================== #
def _real_gauntlet(monkeypatch, registry_text: str, tmp_path: Path, *, bootstrap: bool = False):
    """The REAL validate_candidate with its upstream stubbed (the RR-6a passer) EXCEPT the baseline
    builder, which is the REAL one over a planted registry."""
    import tests.test_discovery_gates_7_8 as g78
    import tests.test_rr6a_gate_verdicts as rr6a
    from engines.engine_d_discovery import discovery as dmod
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    real_build = DiscoveryEngine.__dict__["_build_production_edges"]
    data_map, idx = g78._make_synthetic_dfs()
    base, with_ = rr6a._strong_streams(idx)
    # Under bootstrap the book is EMPTY on every substrate, so the fake's substrate-B baseline is
    # the zero the real run_backtest_pure gives an empty edge set (the static baseline is skipped
    # by declaration); Gate 7's drift then compares 1.5 − 0 against 1.4 − 0.
    base_b = 0.0 if bootstrap else 1.0
    g78._wire_validate_candidate_happy_path(
        monkeypatch,
        results_a={"with_sharpe": 1.5, "baseline_sharpe": 1.0, "daily_returns_with": with_, "daily_returns_baseline": base},
        results_b={"with_sharpe": 1.4, "baseline_sharpe": base_b, "daily_returns_with": with_, "daily_returns_baseline": base},
    )
    monkeypatch.setattr(DiscoveryEngine, "_build_production_edges", real_build)
    monkeypatch.setattr(dmod, "bootstrap_book_declared", lambda *a, **k: bootstrap)
    reg = tmp_path / "edges.yml"
    reg.write_text(registry_text)
    disc = g78._make_disc()
    disc.registry_path = reg
    return disc.validate_candidate(
        g78._make_cand_spec(), data_map, significance_threshold=0.05, alpha_config={}, n_trials_for_dsr=2,
        data_map_substrate_b={"SUBSTRATEB": data_map["AAA"]},
        start_date=idx[0].isoformat(), end_date=idx[-1].isoformat())


ZERO_TRADEABLE = yaml.safe_dump({"edges": [
    {"edge_id": "dead_v1", "category": "technical", "module": "rsi_bounce", "version": "1.0.0",
     "params": {}, "status": "failed", "tier": "feature"}]}, sort_keys=False)


def test_LOCK4_a_readable_registry_with_zero_tradeable_edges_renders_gate_1_NOT_EVALUATED(monkeypatch, tmp_path):
    """Promotion refused by required_gates, the cycle completes (returns, no raise), the record says
    why. Revert to measuring against the empty book → Gate 1 PASSED (contribution 1.5 vs nothing)."""
    r = _real_gauntlet(monkeypatch, ZERO_TRADEABLE, tmp_path)
    g1 = r["gate_verdicts"]["gate_1"]
    assert g1["verdict"] == "not_evaluated" and "empty baseline" in g1["reason"], g1
    assert "0 tradeable edge(s)" in g1["reason"]
    assert r["passed_all_gates"] is False and r["bootstrap_book"] is False
    assert any(ref.startswith("gate_1: not_evaluated") for ref in r["promotion_refusals"]), r["promotion_refusals"]


def test_LOCK4b_bootstrap_mode_promotes_from_an_empty_book_and_the_census_carries_the_label(monkeypatch, tmp_path):
    from core.census import assert_census
    from engines.engine_d_discovery.discovery import candidate_census_block
    r = _real_gauntlet(monkeypatch, ZERO_TRADEABLE, tmp_path, bootstrap=True)
    assert r["gate_verdicts"]["gate_1"]["verdict"] == "passed", r["gate_verdicts"]["gate_1"]
    assert r["baseline_sharpe"] == 0.0 and r["bootstrap_book"] is True
    assert r["passed_all_gates"] is True, r["promotion_refusals"]
    # the candidate census carries the label (it is the record of the seeding, not failed on it);
    # the same label on a BACKTEST census is NON-CANONICAL — never a performance claim
    idx = pd.bdate_range("2025-01-02", periods=20)
    clean = {t: pd.DataFrame({"Close": 1.0}, index=idx) for t in ("SPY", "AAA")}
    block = candidate_census_block("cand_v1", SimpleNamespace(nonzero_calls=1, errors=0), n_trades=3,
                                   data_map=clean, window=(str(idx[0].date()), str(idx[-1].date())),
                                   # L4 (merged 2026-11-04): a clean candidate block supplies its sizing
                                   # counts — unsupplied is an ERRORED share_price_basis record by design
                                   share_basis_counts={"total_return": 3})
    assert block["bootstrap_book"] is True
    assert assert_census({"census": block, "bootstrap_ci_skip_reason": "t"}).canonical
    from tests.test_contracts import _CANONICAL_CENSUS
    v = assert_census({"census": {**_CANONICAL_CENSUS, "bootstrap_book": True}, "bootstrap_ci_skip_reason": "t"})
    assert not v.canonical and any("bootstrap_book" in f for f in v.failures)


def test_LOCK4c_an_unreadable_registry_is_a_HARD_refusal_of_the_gauntlet(monkeypatch, tmp_path):
    """Revert the propagate list → the candidate is quietly recorded refused and the cycle carries on."""
    with pytest.raises(RegistryUnreadableError):
        _real_gauntlet(monkeypatch, CORRUPT, tmp_path)


# =========================================================================== #
# Lock 5 — isolation mode refuses a missing id; default mode refuses an empty registry
# =========================================================================== #
HEALTHY_ONE = yaml.safe_dump({"edges": [
    {"edge_id": "rsi_bounce_v1", "category": "technical", "module": "rsi_bounce", "version": "1.0.0",
     "params": {}, "status": "paused", "tier": "feature"}]}, sort_keys=False)


def _load(monkeypatch, tmp_path, registry_text, **kw):
    from orchestration.mode_controller import ModeController
    if registry_text is not None:
        _plant(tmp_path, registry_text)
    monkeypatch.chdir(tmp_path)
    return ModeController._load_edges_via_registry(SimpleNamespace(), **kw)


def test_LOCK5_isolation_mode_refuses_a_missing_id_naming_the_sync(monkeypatch, tmp_path):
    """Revert → `not found` is printed and the run continues with fewer edges."""
    from orchestration.mode_controller import EdgeLoadRefusal
    with pytest.raises(EdgeLoadRefusal, match=r"nope_v1.*sync_edge_registry"):
        _load(monkeypatch, tmp_path, HEALTHY_ONE, exact_edge_ids=["rsi_bounce_v1", "nope_v1"])
    # positive control: every requested id resolves → loaded
    loaded = _load(monkeypatch, tmp_path, HEALTHY_ONE, exact_edge_ids=["rsi_bounce_v1"])
    assert list(loaded) == ["rsi_bounce_v1"]


def test_LOCK5b_default_mode_refuses_an_empty_registry_and_never_falls_back_to_default_edges(monkeypatch, tmp_path):
    """A readable registry with no tradeable edge, and an ABSENT one (a fresh checkout) — both refuse,
    naming the sync; an UNREADABLE one raises the reader's refusal. Revert → an empty dict, which
    AlphaEngine.__init__ turns into rsi_bounce + xsec_momentum silently."""
    from orchestration.mode_controller import EdgeLoadRefusal
    with pytest.raises(EdgeLoadRefusal, match="no tradeable"):
        _load(monkeypatch, tmp_path, ZERO_TRADEABLE)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    with pytest.raises(EdgeLoadRefusal, match="sync_edge_registry"):
        _load(monkeypatch, fresh, None)
    with pytest.raises(RegistryUnreadableError):
        _load(monkeypatch, tmp_path / "bad", CORRUPT)


def test_a_fresh_checkout_refuses_until_the_sync_runs_then_succeeds(monkeypatch, tmp_path):
    from orchestration.mode_controller import EdgeLoadRefusal
    from scripts.sync_edge_registry import sync
    with pytest.raises(EdgeLoadRefusal):
        _load(monkeypatch, tmp_path, None)
    report = sync(tmp_path / "data" / "governor" / "edges.yml", modules=["momentum_12_1_v1"])
    assert report.additions == ["momentum_12_1_v1"] and report.wrote
    loaded = _load(monkeypatch, tmp_path, None)
    assert list(loaded) == ["momentum_12_1_v1"]


# =========================================================================== #
# Lock 6 — the first-sync report; --check writes nothing; a no-op sync touches nothing
# =========================================================================== #
def test_LOCK6_check_exits_non_zero_on_a_change_and_writes_nothing(tmp_path):
    """`--check` on a registry a module would be ADDED to: exit 1, bytes and mtime untouched. After the
    sync: `--check` exits 0 and a second sync touches nothing."""
    reg = tmp_path / "edges.yml"
    reg.write_text(HEALTHY_ONE)
    sha, mtime = _sha(reg), reg.stat().st_mtime_ns
    cli = [sys.executable, str(REPO / "scripts" / "sync_edge_registry.py"), "--registry", str(reg)]
    env = dict(os.environ, OMP_NUM_THREADS="1")
    r = subprocess.run([*cli, "--check", "--json"], cwd=str(REPO), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 1, r.stdout + r.stderr
    rep = json.loads(r.stdout)
    assert rep["changes_file"] is True and len(rep["additions"]) >= 26 and rep["wrote"] is False
    assert _sha(reg) == sha and reg.stat().st_mtime_ns == mtime, "--check wrote or touched the registry"
    r = subprocess.run(cli, cwd=str(REPO), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "never registered (additions): 26" in r.stdout or "never registered (additions): 27" in r.stdout, r.stdout
    ids = {e["edge_id"] for e in read_registry(reg)["edges"]}
    assert {"rsi_bounce_v1", "momentum_12_1_v1", "value_earnings_yield_edge_v1"} <= ids or \
        {"rsi_bounce_v1", "momentum_12_1_v1"} <= ids
    sha2, mtime2 = _sha(reg), reg.stat().st_mtime_ns
    r = subprocess.run([*cli, "--check"], cwd=str(REPO), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "in sync" in r.stdout, r.stdout
    r = subprocess.run(cli, cwd=str(REPO), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "no change — bytes identical, file untouched" in r.stdout
    assert _sha(reg) == sha2 and reg.stat().st_mtime_ns == mtime2


def test_LOCK6b_the_sync_refuses_an_unreadable_registry_before_importing_anything(tmp_path):
    from scripts.sync_edge_registry import sync
    reg = tmp_path / "edges.yml"
    reg.write_text(CORRUPT)
    sha = _sha(reg)
    with pytest.raises(RegistryUnreadableError):
        sync(reg, modules=["momentum_12_1_v1"])
    assert _sha(reg) == sha
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "sync_edge_registry.py"), "--registry", str(reg)],
                       cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert r.returncode == 2 and "[SYNC][REFUSED]" in r.stderr


# =========================================================================== #
# Lock 7 — the fleet never imports an edge module (executed, not grepped)
# =========================================================================== #
def test_LOCK7_the_paper_fleet_imports_no_edge_module(tmp_path):
    """Every module under paper_trader/ and scripts.run_paper_cloud_day, imported in a fresh
    interpreter over a planted corrupt registry: no edge module or EdgeRegistry in sys.modules, the
    bytes untouched. live_trader/ does not exist in the tree (archived, pr4_dead_live_stub_t169).
    Positive control: the same driver asked to also import one edge module reports it."""
    reg = _plant(tmp_path, CORRUPT)
    sha = _sha(reg)
    out = _run(DRIVER_FLEET, tmp_path)
    assert out["rc"] == 0 and not out["failures"], out["failures"]
    assert len(out["imported"]) >= 30 and "scripts.run_paper_cloud_day" in out["imported"]
    assert out["edge_modules_loaded"] == [], out["edge_modules_loaded"]
    assert out["live_trader_dir_exists"] is False
    assert _sha(reg) == sha
    control = _run(DRIVER_FLEET, tmp_path, "engines.engine_a_alpha.edges.rsi_bounce")
    assert "engines.engine_a_alpha.edges.rsi_bounce" in control["edge_modules_loaded"]


# =========================================================================== #
# Engine F — a failed save raises with the bytes untouched; no history after a failed save
# =========================================================================== #
def _lifecycle(tmp_path):
    from engines.engine_f_governance.lifecycle_manager import LifecycleConfig, LifecycleManager
    from tests.test_f11_phase2_wire import _seed_registry
    reg = tmp_path / "edges.yml"
    hist = tmp_path / "lifecycle_history.csv"
    _seed_registry(reg, edge_id="losing_edge", status="active")
    cfg = LifecycleConfig(enabled=True, retirement_min_trades=100, retirement_min_days=30, retirement_margin=0.0)
    return LifecycleManager(cfg=cfg, registry_path=reg, history_path=hist), reg, hist


def test_ENGINE_F_a_planted_dump_error_leaves_the_bytes_untouched_raises_and_appends_no_history(monkeypatch, tmp_path):
    """Revert `_save_registry` to `open("w")` + `yaml.dump` inside `except: log` → the file is
    truncated/empty, nothing raises, and a history row is appended for a transition never saved."""
    import core.edge_registry_io as io_mod
    from tests.test_f11_phase2_wire import _losing_trades
    lcm, reg, hist = _lifecycle(tmp_path)
    sha = _sha(reg)

    def _boom(*a, **k):
        raise yaml.representer.RepresenterError("cannot represent an object")
    monkeypatch.setattr(io_mod.yaml, "safe_dump", _boom)
    with pytest.raises(RegistryWriteError, match="cannot represent"):
        lcm.evaluate(trades=_losing_trades(), benchmark_sharpe=0.5)
    assert _sha(reg) == sha, "a failed save changed the registry"
    assert not hist.exists(), "a history row was appended after a FAILED registry save"
    # positive control: without the fault the transition is saved and THEN the history row appended
    monkeypatch.undo()
    lcm2, reg2, hist2 = _lifecycle(tmp_path / "ok")
    events = lcm2.evaluate(trades=_losing_trades(), benchmark_sharpe=0.5)
    assert events and read_registry(reg2)["edges"][0]["status"] != "active"
    assert hist2.exists() and hist2.stat().st_size > 0


def test_ENGINE_F_the_governor_lets_a_registry_save_failure_through(monkeypatch, tmp_path):
    """`StrategyGovernor.evaluate_lifecycle` swallows every lifecycle failure except a registry
    read/save failure, which RAISES. Revert → it is logged and swallowed."""
    from engines.engine_f_governance import governor as gmod
    from engines.engine_f_governance.lifecycle_manager import LifecycleManager

    def _raise(self, *a, **k):
        raise RegistryWriteError("planted: the registry could not be written")
    monkeypatch.setattr(LifecycleManager, "evaluate", _raise)
    gov = SimpleNamespace(cfg=SimpleNamespace(lifecycle_enabled=True), state_path=tmp_path / "edge_weights.json")
    trades = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-02", "2024-03-01"], utc=True), "edge": ["e", "e"], "pnl": [1.0, -1.0]})
    with pytest.raises(RegistryWriteError, match="planted"):
        gmod.StrategyGovernor.evaluate_lifecycle(gov, trades)

    def _other(self, *a, **k):
        raise ValueError("an ordinary lifecycle failure")
    monkeypatch.setattr(LifecycleManager, "evaluate", _other)
    gmod.StrategyGovernor.evaluate_lifecycle(gov, trades)          # swallowed, as before


# =========================================================================== #
# run_backtest's post-run: hold the failure, write the summary WITH it, THEN raise (R §4.3: one shape)
# =========================================================================== #
def _post_run(monkeypatch, tmp_path, *, governor_raises=None, discovery_raises=None, discover=False):
    import orchestration.mode_controller as mcmod
    from core.census import assert_census_file
    from tests.test_contracts import _CANONICAL_CENSUS
    run_id = "run-post"
    perf = tmp_path / "data" / "trade_logs" / run_id / "performance_summary.json"
    perf.parent.mkdir(parents=True)
    perf.write_text(json.dumps({"Sharpe Ratio": 1.0, "census": dict(_CANONICAL_CENSUS),
                                "bootstrap_ci_skip_reason": "contract"}))
    assert assert_census_file(str(perf)).canonical, "precondition: the run-scoped summary is canonical"

    monkeypatch.setattr(mcmod, "PerformanceMetrics", lambda **kw: SimpleNamespace(
        summary_dict={"Sharpe Ratio": 1.0}, trades=pd.DataFrame(), snapshots=pd.DataFrame()))

    def _lifecycle(*a, **k):
        if governor_raises is not None:
            raise governor_raises
    governor = SimpleNamespace(update_from_trades=lambda *a, **k: None, save_weights=lambda: None,
                               evaluate_lifecycle=_lifecycle, evaluate_tiers=lambda *a, **k: [])

    def _cycle(data_map, regime_detector):
        if discovery_raises is not None:
            raise discovery_raises
    fake_self = SimpleNamespace(root=tmp_path, _run_discovery_cycle=_cycle)
    fake_self._record_post_run_failure = lambda c, p: mcmod.ModeController._record_post_run_failure(fake_self, c, p)
    kwargs = dict(mode="prod", start="2024-01-02", end="2024-03-08", tickers=["AAA"], loaded_edges={"e": object()},
                  governor=governor, no_governor=False, apply_journal_at_end=False,
                  cockpit=SimpleNamespace(run_id=run_id), discover=discover, data_map={}, regime_detector=None)
    return (lambda: mcmod.ModeController._post_run(fake_self, **kwargs)), perf, tmp_path / "data" / "research" / "performance_summary.json"


def test_RUN_BACKTEST_a_registry_save_failure_lands_in_both_summaries_the_census_says_NON_CANONICAL_then_it_raises(monkeypatch, tmp_path):
    """Revert the hold → the exception escapes with NO post_run_failure in either summary."""
    from core.census import assert_census_file
    run, perf, research = _post_run(monkeypatch, tmp_path, governor_raises=RegistryWriteError("planted: disk full"))
    with pytest.raises(RegistryWriteError, match="planted: disk full"):
        run()
    for p in (perf, research):
        doc = json.loads(p.read_text())
        assert doc["post_run_failure"]["stage"] == "governor", p
        assert doc["post_run_failure"]["error_type"] == "RegistryWriteError"
        assert "planted: disk full" in doc["post_run_failure"]["message"]
    v = assert_census_file(str(perf))
    assert not v.canonical and any("post_run_failure" in f for f in v.failures), v.failures


def test_RUN_BACKTEST_a_discovery_cycle_failure_takes_the_same_shape(monkeypatch, tmp_path):
    """R §4.3 (ruled): stage "discovery", the summary written, THEN the raise. Revert to
    raise-before-summary → no summary file, no record."""
    from core.census import assert_census_file
    run, perf, research = _post_run(monkeypatch, tmp_path, discover=True,
                                    discovery_raises=RuntimeError("cycle FAILED at stage 'hunt'"))
    with pytest.raises(RuntimeError, match="stage 'hunt'"):
        run()
    assert research.exists(), "the research summary was never written — the cycle raised before it"
    doc = json.loads(research.read_text())
    assert doc["post_run_failure"]["stage"] == "discovery" and doc["post_run_failure"]["error_type"] == "RuntimeError"
    assert json.loads(perf.read_text())["post_run_failure"]["stage"] == "discovery"
    assert not assert_census_file(str(perf)).canonical


def test_RUN_BACKTEST_positive_control_a_clean_post_run_writes_a_clean_summary(monkeypatch, tmp_path):
    from core.census import assert_census_file
    run, perf, research = _post_run(monkeypatch, tmp_path, discover=True)
    summary = run()
    assert "post_run_failure" not in summary and "post_run_failure" not in json.loads(research.read_text())
    assert assert_census_file(str(perf)).canonical


# =========================================================================== #
# The reader: an absent file is the only empty registry; everything else refuses
# =========================================================================== #
@pytest.mark.parametrize("planted", ["", "just a string\n", "edges: {a: b}\n", "edges:\n  - 7\n",
                                     "edges:\n  - {status: active}\n", CORRUPT])
def test_the_one_reader_refuses_everything_that_is_not_an_edge_registry(tmp_path, planted):
    reg = tmp_path / "edges.yml"
    reg.write_text(planted)
    with pytest.raises(RegistryUnreadableError, match="refusing — the file is untouched"):
        read_registry(reg)
    with pytest.raises(RegistryUnreadableError):
        EdgeRegistry(store_path=reg)
    assert read_registry(tmp_path / "absent.yml") == {"edges": []}
