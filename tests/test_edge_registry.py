"""
tests/test_edge_registry.py
============================
Enforce the `edges.yml` Write Contract documented in
`docs/Core/PROJECT_CONTEXT.md`:

> D writes: New entries (candidate specs, params, metadata, source info)
> F writes: `status` field changes (candidate → active → paused → retired)
> Neither engine deletes the other's fields.

These tests exist because of the 2026-04-25 registry-status-stomp bug:
`EdgeRegistry.ensure()` was silently overriding `status` on every import,
which let auto-register-on-import code (e.g. `momentum_edge.py:64`)
revert lifecycle pause/retire decisions on every backtest startup. The
contract was documented but not enforced. The bug was invisible for
weeks. This file is the executable enforcement.

Since the edges.yml single-writer unit (2026-10-22) `ensure()` NEVER writes:
it records the module's registration in memory, and the code-owned merge it
used to apply at import is applied only by `scripts/sync_edge_registry.py`
through `merge_code_owned` — KEY-WISE, with status, tier and every
registry-owned field write-protected by construction. The claims below are
unchanged; the persistence they exercise is the explicit `register()` /
`set_status()` and the merge the sync applies (R §4.1).

Methodology: documented contracts decay into folklore unless tests assert
them. See `docs/State/lessons_learned.md` 2026-04-25 entry.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.engine_a_alpha.edge_registry import (  # noqa: E402
    ABSENT,
    EdgeRegistry,
    EdgeSpec,
    merge_code_owned,
    spec_to_row,
)


@pytest.fixture
def tmp_registry(tmp_path: Path) -> EdgeRegistry:
    """Fresh empty registry on a temp file. Isolated from real data."""
    store = tmp_path / "edges.yml"
    return EdgeRegistry(store_path=store)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "<absent>"


def _spec(edge_id: str, **kw) -> EdgeSpec:
    base = dict(category="technical", module="m", version="1.0.0", status="active")
    base.update(kw)
    return EdgeSpec(edge_id=edge_id, **base)


# ---------------------------------------------------------------------------
# Core Write Contract: the merge the sync applies does NOT touch status.
# ---------------------------------------------------------------------------

def test_a_new_registration_merges_to_its_own_row_with_the_provided_status():
    """A NEW edge_id: the row the sync would ADD carries the module's declared status."""
    row, report = merge_code_owned(None, _spec("new_edge", status="candidate"))
    assert report.never_registered and report.changes_file
    assert row["status"] == "candidate" and row["edge_id"] == "new_edge"


@pytest.mark.parametrize("registry_status", ["paused", "retired", "failed"])
def test_the_merge_does_not_overwrite_a_lifecycle_status(registry_status):
    """The 2026-04-25 bug: ensure() reverted paused→active on import. The merge the sync applies to
    an EXISTING row never reads status from the module's spec — paused/retired/failed survive a
    re-registration declaring `active`."""
    existing = spec_to_row(_spec("edge", status=registry_status))
    row, report = merge_code_owned(existing, _spec("edge", status="active"))
    assert row["status"] == registry_status, (
        "status was reverted by re-registration — the registry-stomp bug is back. "
        "See docs/State/lessons_learned.md 2026-04-25.")
    assert not report.changes_file


def test_ensure_never_writes_and_never_revives_in_memory(tmp_registry, tmp_path):
    """End to end on a file: register active → the lifecycle pauses it (Engine F's explicit write) →
    the module's import-time `ensure(active)` → the file AND the loaded spec still say paused, and
    the registration is recorded as persisted with no status drift."""
    tmp_registry.register(_spec("momentum_edge_v1", module="engines.engine_a_alpha.edges.momentum_edge"))
    tmp_registry.set_status("momentum_edge_v1", "paused")
    sha = _sha(tmp_path / "edges.yml")
    EdgeRegistry.clear_import_registrations()
    tmp_registry.ensure(_spec("momentum_edge_v1", module="engines.engine_a_alpha.edges.momentum_edge",
                              status="active"))
    assert tmp_registry.get("momentum_edge_v1").status == "paused"
    assert EdgeRegistry(store_path=tmp_path / "edges.yml").get("momentum_edge_v1").status == "paused"
    assert _sha(tmp_path / "edges.yml") == sha, "ensure() wrote the registry"
    reg = EdgeRegistry.import_registrations()["momentum_edge_v1"]
    assert reg.persisted and not reg.report.changes_file


# ---------------------------------------------------------------------------
# The merge updates code-owned fields (allowed by contract), KEY-WISE on params.
# ---------------------------------------------------------------------------

def test_the_merge_updates_the_module_field():
    existing = spec_to_row(_spec("merge_test", module="old_module", status="paused"))
    row, report = merge_code_owned(existing, _spec("merge_test", module="new_module"))
    assert row["module"] == "new_module"        # code-owned field updated
    assert row["status"] == "paused"            # status preserved
    assert report.drift_applied == {"module": ("old_module", "new_module")}


def test_the_merge_updates_code_owned_params_and_version():
    existing = spec_to_row(_spec("params_test", params={"lookback": 10}, status="paused"))
    row, report = merge_code_owned(existing, _spec("params_test", version="1.0.1", params={"lookback": 20}))
    assert row["params"] == {"lookback": 20}
    assert row["version"] == "1.0.1"
    assert row["status"] == "paused"
    assert report.drift_applied == {"version": ("1.0.0", "1.0.1"), "params.lookback": (10, 20)}


def test_the_merge_does_not_clobber_params_with_empty():
    """A re-register with `params={}` owns no key: every existing key is preserved (registry-only)."""
    existing = spec_to_row(_spec("params_keep", params={"lookback": 14, "threshold": 3.0}))
    row, report = merge_code_owned(existing, _spec("params_keep", params={}))
    assert row["params"] == {"lookback": 14, "threshold": 3.0}
    assert report.registry_only_keys == ["params.lookback", "params.threshold"]
    assert not report.changes_file


def test_the_merge_is_key_wise_registry_only_keys_survive_and_a_type_change_is_its_own_class():
    """R §4.1: `validation_note` / `validation_sharpe` (Discovery's write-back) survive; a code-owned
    key absent from the registry is added; a type change is reported apart from drift."""
    existing = spec_to_row(_spec("kw", params={"lookback": "14", "validation_note": "keep", "validation_sharpe": 0.3}))
    row, report = merge_code_owned(existing, _spec("kw", params={"lookback": 14, "window": 60}))
    assert row["params"] == {"lookback": 14, "validation_note": "keep", "validation_sharpe": 0.3, "window": 60}
    assert report.type_changes == {"params.lookback": ("str", "int")}
    assert report.drift_applied == {"params.window": (ABSENT, 60)}
    assert report.registry_only_keys == ["params.validation_note", "params.validation_sharpe"]


def test_the_merge_never_touches_tier_or_the_registry_owned_fields():
    existing = spec_to_row(_spec("t", tier="alpha", combination_role="standalone",
                                 tier_last_updated="2026-04-28T12:00:00+00:00", status="paused",
                                 regime_gate={"crisis": 0.0}, extra={"reclassified_to": "regime_input"}))
    row, _ = merge_code_owned(existing, _spec("t", tier="feature"))
    assert row["tier"] == "alpha" and row["combination_role"] == "standalone"
    assert row["tier_last_updated"] == "2026-04-28T12:00:00+00:00" and row["status"] == "paused"
    assert row["regime_gate"] == {"crisis": 0.0} and row["reclassified_to"] == "regime_input"


# ---------------------------------------------------------------------------
# set_status() is the explicit owned API for status changes (F/lifecycle).
# ---------------------------------------------------------------------------

def test_set_status_transitions_through_lifecycle(tmp_registry):
    """The full candidate → active → paused → retired path."""
    tmp_registry.register(_spec("lifecycle", status="candidate"))
    assert tmp_registry.get("lifecycle").status == "candidate"

    tmp_registry.set_status("lifecycle", "active")
    assert tmp_registry.get("lifecycle").status == "active"

    tmp_registry.set_status("lifecycle", "paused")
    assert tmp_registry.get("lifecycle").status == "paused"

    tmp_registry.set_status("lifecycle", "active")  # revival
    assert tmp_registry.get("lifecycle").status == "active"

    tmp_registry.set_status("lifecycle", "retired")
    assert tmp_registry.get("lifecycle").status == "retired"


def test_set_status_persists_to_disk(tmp_registry, tmp_path):
    tmp_registry.register(_spec("persist"))
    tmp_registry.set_status("persist", "paused")

    # Re-load from disk in a fresh registry instance
    reloaded = EdgeRegistry(store_path=tmp_path / "edges.yml")
    assert reloaded.get("persist").status == "paused"


def test_construction_never_writes_or_creates_directories(tmp_path):
    """Pure: constructing a registry on an absent path leaves the filesystem as it was."""
    store = tmp_path / "nested" / "edges.yml"
    reg = EdgeRegistry(store_path=store)
    assert reg.get_all_specs() == [] and not store.parent.exists()


# ---------------------------------------------------------------------------
# list / list_modules / list_tradeable filters.
# ---------------------------------------------------------------------------

def test_list_tradeable_includes_active_and_paused_only(tmp_registry):
    """Soft-pause: paused edges trade at reduced weight, so list_tradeable
    must include them. Failed/retired/candidate should NOT trade."""
    for eid, status in [
        ("active_e", "active"),
        ("paused_e", "paused"),
        ("retired_e", "retired"),
        ("failed_e", "failed"),
        ("candidate_e", "candidate"),
        ("archived_e", "archived"),
    ]:
        tmp_registry.register(_spec(eid, status=status))

    tradeable_ids = {s.edge_id for s in tmp_registry.list_tradeable()}
    assert tradeable_ids == {"active_e", "paused_e"}


def test_list_with_statuses_multi_filter(tmp_registry):
    """The `statuses=` argument allows multi-match filtering."""
    for eid, status in [
        ("a1", "active"), ("a2", "active"),
        ("p1", "paused"),
        ("r1", "retired"),
    ]:
        tmp_registry.register(_spec(eid, status=status))

    got = {s.edge_id for s in tmp_registry.list(statuses=["active", "retired"])}
    assert got == {"a1", "a2", "r1"}


# ---------------------------------------------------------------------------
# Real-world repro: the actual import-time scenario, end to end through the sync
# ---------------------------------------------------------------------------

def test_repro_momentum_edge_import_does_not_revive_paused(tmp_path):
    """End-to-end repro of the 2026-04-25 bug, on the REAL module through the REAL sync.

    1. momentum_edge_v1 is synced into a fresh registry (status `active`, as the module declares)
    2. Lifecycle pauses it (Engine F write)
    3. The next startup imports momentum_edge.py (pure) and the next sync persists registrations
    4. Subsequent reads of edges.yml must show `paused`, not `active`.
    """
    from scripts.sync_edge_registry import sync
    reg_path = tmp_path / "edges.yml"
    first = sync(reg_path, modules=["momentum_edge"])
    assert first.additions == ["momentum_edge_v1"]
    reg = EdgeRegistry(store_path=reg_path)
    assert reg.get("momentum_edge_v1").status == "active"

    reg.set_status("momentum_edge_v1", "paused")           # 2. Engine F's explicit write
    second = sync(reg_path, modules=["momentum_edge"])     # 3. the re-registration, persisted
    assert not second.changes_file
    assert EdgeRegistry(store_path=reg_path).get("momentum_edge_v1").status == "paused", (
        "Status was reverted by re-registration — the registry-stomp bug is back. "
        "See docs/State/lessons_learned.md 2026-04-25."
    )
