"""tests/test_edge_registry_single_writer_r2.py — the reviewer's eight test-only gaps (R's execution of ae9bd15).

Each refusal below existed in code but nothing locked it: under the reviewer's own single-line
reversion every test stayed green. Each lock here DRIVES the real entrypoint and is proven FAILING
under its own reversion (scripts/registry_single_writer_reversion_proof.py, the R-cases).

  R5  — `_load_edges_via_registry`: a tradeable set whose modules ALL fail to import returns {} → the
        default-edge measurement this unit exists to stop (the heart of the unit);
  R7  — `StrategyGovernor.evaluate_tiers` lets a registry read/save failure through;
  R8  — the sync refuses an unreadable DEFAULT registry before importing, when the target is another file;
  R9  — `bootstrap_book_declared` fails closed on a missing or non-bool key;
  R10 — `EvolutionController.load_edges` refuses an unreadable registry;
  R11 — `row_to_spec` refuses a row with no module as RegistryUnreadableError (never a KeyError);
  R12 — the journal-apply path (apply_journal_at_end=True) re-raises a registry failure into the hold;
  R13 — census invariant 10 holds with NO census block at all.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from core.edge_registry_io import RegistryUnreadableError, RegistryWriteError, read_registry
from engines.engine_a_alpha.edge_registry import EdgeRegistry

CORRUPT = "edges:\n  - {edge_id: momentum_edge_v1, status: active\n  - {edge_id: x\n"
HEALTHY_ONE = yaml.safe_dump({"edges": [
    {"edge_id": "rsi_bounce_v1", "category": "technical", "module": "rsi_bounce", "version": "1.0.0",
     "params": {}, "status": "paused", "tier": "feature"}]}, sort_keys=False)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _plant(root: Path, text: str) -> Path:
    reg = root / "data" / "governor" / "edges.yml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(text)
    return reg


# --------------------------------------------------------------------------- #
# R5 — the heart: every tradeable edge failing to import is a refusal, never {}
# --------------------------------------------------------------------------- #
def test_R5_a_tradeable_set_whose_modules_all_fail_to_import_REFUSES_never_returns_empty(monkeypatch, tmp_path):
    """Revert ONLY `if not loaded_edges: raise` → {} comes back, and AlphaEngine.__init__ turns {}
    into rsi_bounce + xsec_momentum: the wrong-edge measurement."""
    from orchestration.mode_controller import EdgeLoadRefusal, ModeController
    _plant(tmp_path, yaml.safe_dump({"edges": [
        {"edge_id": "ghost_v1", "category": "technical", "module": "no_such_module_xyz", "version": "1.0.0",
         "params": {}, "status": "active", "tier": "feature"}]}, sort_keys=False))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(EdgeLoadRefusal, match=r"none of the 1 edge\(s\) to load could be imported.*ghost_v1"):
        ModeController._load_edges_via_registry(SimpleNamespace())
    # positive control: an importable tradeable edge loads
    _plant(tmp_path, HEALTHY_ONE)
    assert list(ModeController._load_edges_via_registry(SimpleNamespace())) == ["rsi_bounce_v1"]


# --------------------------------------------------------------------------- #
# R7 — evaluate_tiers lets a registry failure through, swallows the rest
# --------------------------------------------------------------------------- #
def test_R7_evaluate_tiers_lets_a_registry_failure_through_and_swallows_an_ordinary_one(monkeypatch, tmp_path):
    from engines.engine_f_governance import governor as gmod
    gov_dir = tmp_path / "data" / "governor"
    gov_dir.mkdir(parents=True)
    trades = tmp_path / "trades.csv"
    trades.write_text("timestamp,edge,pnl\n2024-01-02,e,1.0\n")
    gov = SimpleNamespace(cfg=SimpleNamespace(tier_reclassification_enabled=True),
                          state_path=gov_dir / "edge_weights.json")
    (gov_dir / "edges.yml").write_text(CORRUPT)
    with pytest.raises(RegistryUnreadableError):
        gmod.StrategyGovernor.evaluate_tiers(gov, trades_path=trades)
    # positive control: an ordinary classifier failure is logged and swallowed, as before
    (gov_dir / "edges.yml").write_text(HEALTHY_ONE)
    from engines.engine_a_alpha.tier_classifier import TierClassifier

    def _boom(self, *a, **k):
        raise ValueError("an ordinary tier failure")
    monkeypatch.setattr(TierClassifier, "classify_from_trades", _boom)
    assert gmod.StrategyGovernor.evaluate_tiers(gov, trades_path=trades) == []


# --------------------------------------------------------------------------- #
# R8 — the sync refuses an unreadable DEFAULT registry before importing anything
# --------------------------------------------------------------------------- #
def test_R8_the_sync_refuses_an_unreadable_default_registry_when_the_target_is_another_file(monkeypatch, tmp_path):
    """The modules read the DEFAULT path at import; a refused read there records nothing, which the
    sync must never mistake for "registers nothing". Revert the default-path read → the sync runs,
    reports 0 registrations and raises nothing."""
    from scripts.sync_edge_registry import sync
    _plant(tmp_path, CORRUPT)                       # the DEFAULT registry (cwd-relative), unreadable
    target = tmp_path / "other.yml"
    target.write_text(HEALTHY_ONE)
    sha = _sha(target)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RegistryUnreadableError):
        sync(target, modules=["momentum_12_1_v1"])
    assert _sha(target) == sha


# --------------------------------------------------------------------------- #
# R9 — bootstrap_book_declared fails closed
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("planted", [{}, {"bootstrap_book": "false"}, {"bootstrap_book": 0}, {"bootstrap_book": None}])
def test_R9_bootstrap_book_declared_fails_closed_on_a_missing_or_non_bool_key(tmp_path, planted):
    """Revert to `.get("bootstrap_book", False)` → every one of these reads as False, silently."""
    from engines.engine_d_discovery.thresholds import bootstrap_book_declared
    p = tmp_path / "discovery_settings.json"
    p.write_text(json.dumps(planted))
    with pytest.raises(ValueError, match="bootstrap_book must be a bool"):
        bootstrap_book_declared(p)
    p.write_text(json.dumps({"bootstrap_book": True}))
    assert bootstrap_book_declared(p) is True
    p.write_text(json.dumps({"bootstrap_book": False}))
    assert bootstrap_book_declared(p) is False


# --------------------------------------------------------------------------- #
# R10 — EvolutionController.load_edges refuses
# --------------------------------------------------------------------------- #
def test_R10_evolution_controller_load_edges_refuses_an_unreadable_registry(tmp_path):
    """Revert to the old `except: log; return []` → a cycle that silently found no candidates."""
    from engines.engine_f_governance.evolution_controller import EvolutionController
    (tmp_path / "data" / "governor").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    reg = tmp_path / "data" / "governor" / "edges.yml"
    reg.write_text(CORRUPT)
    ctrl = EvolutionController(project_root=str(tmp_path))
    with pytest.raises(RegistryUnreadableError):
        ctrl.load_edges()
    reg.write_text(HEALTHY_ONE)
    assert [e["edge_id"] for e in ctrl.load_edges()] == ["rsi_bounce_v1"]


# --------------------------------------------------------------------------- #
# R11 — a row with no module refuses by name, never a KeyError
# --------------------------------------------------------------------------- #
def test_R11_a_row_without_a_module_refuses_as_RegistryUnreadableError_naming_the_row(tmp_path):
    """Revert the check → `row["module"]` raises a bare KeyError (the pre-unit shape, which the old
    `_load` then turned into an EMPTY registry)."""
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.safe_dump({"edges": [{"edge_id": "nomod_v1", "status": "active", "params": {}}]},
                                  sort_keys=False))
    assert read_registry(reg)["edges"][0]["edge_id"] == "nomod_v1"   # the shared reader accepts it (F needs no module)
    with pytest.raises(RegistryUnreadableError, match="nomod_v1.*has no module"):
        EdgeRegistry(store_path=reg)


# --------------------------------------------------------------------------- #
# R12 — the journal-apply path re-raises a registry failure into the hold
# --------------------------------------------------------------------------- #
def test_R12_a_registry_failure_in_the_journal_apply_is_held_recorded_then_raised(monkeypatch, tmp_path):
    """apply_journal_at_end=True: the journal apply IS the registry save. Revert its re-raise → the
    generic `[JOURNAL][APPLY][WARN]` swallows it: no post_run_failure, no raise."""
    import orchestration.mode_controller as mcmod
    from engines.engine_f_governance import journal as jmod
    from tests.test_contracts import _CANONICAL_CENSUS
    run_id = "run-journal"
    perf = tmp_path / "data" / "trade_logs" / run_id / "performance_summary.json"
    perf.parent.mkdir(parents=True)
    perf.write_text(json.dumps({"Sharpe Ratio": 1.0, "census": dict(_CANONICAL_CENSUS),
                                "bootstrap_ci_skip_reason": "contract"}))
    monkeypatch.setattr(mcmod, "PerformanceMetrics", lambda **kw: SimpleNamespace(
        summary_dict={"Sharpe Ratio": 1.0}, trades=pd.DataFrame(), snapshots=pd.DataFrame()))

    class _Journal:                       # one pending entry, so the apply runs
        def __len__(self):
            return 1
    monkeypatch.setattr(jmod, "LifecycleJournal", _Journal)

    def _apply_boom(**kw):
        raise RegistryWriteError("planted: the journal apply could not write edges.yml")
    monkeypatch.setattr("scripts.journal_apply.apply", _apply_boom)
    governor = SimpleNamespace(update_from_trades=lambda *a, **k: None, save_weights=lambda: None,
                               evaluate_lifecycle=lambda *a, **k: None, evaluate_tiers=lambda *a, **k: [])
    fake_self = SimpleNamespace(root=tmp_path, _run_discovery_cycle=lambda *a, **k: None)
    fake_self._record_post_run_failure = lambda c, p: mcmod.ModeController._record_post_run_failure(fake_self, c, p)
    with pytest.raises(RegistryWriteError, match="journal apply could not write"):
        mcmod.ModeController._post_run(
            fake_self, mode="prod", start="2024-01-02", end="2024-03-08", tickers=["AAA"],
            loaded_edges={"e": object()}, governor=governor, no_governor=False, apply_journal_at_end=True,
            cockpit=SimpleNamespace(run_id=run_id), discover=False, data_map={}, regime_detector=None)
    for p in (perf, tmp_path / "data" / "research" / "performance_summary.json"):
        doc = json.loads(p.read_text())
        assert doc["post_run_failure"]["stage"] == "governor" and "journal apply" in doc["post_run_failure"]["message"], p


# --------------------------------------------------------------------------- #
# R13 — invariant 10 with no census block at all
# --------------------------------------------------------------------------- #
def test_R13_post_run_failure_fails_the_gate_even_when_the_summary_has_no_census_block():
    """Revert the early return to its old shape → a summary with no census and a post-run failure
    reports only "census block missing", and with require_census=False it reads ok=True."""
    from core.census import assert_census
    summary = {"post_run_failure": {"stage": "discovery", "error_type": "RuntimeError", "message": "boom"}}
    v = assert_census(summary)
    assert not v.canonical and not v.ok
    assert any("post_run_failure at stage 'discovery'" in f for f in v.failures), v.failures
    assert any("census block missing" in f for f in v.failures)
    v2 = assert_census(summary, require_census=False)
    assert not v2.ok and not v2.canonical
    assert any("post_run_failure" in f for f in v2.failures), v2.failures
