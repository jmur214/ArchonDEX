"""tests/test_engine_d_registry_write_fail_closed.py — Discovery never wipes edges.yml.

`DiscoveryEngine.save_candidates` read the registry inside `except Exception: existing =
{"edges": []}`, then wrote back ONLY the merged candidates — so a registry it could not read
(a merge-conflict marker, a half-written file, a stray tab) was REPLACED by the handful of
candidates being saved, wiping every other edge from the sole edge-status authority. It also
opened the file with `open("w")` BEFORE serialising, so a dump error truncated it.

Each lock drives the real `save_candidates` / `get_queued_candidates` against a planted file
in a temp dir, and asserts the file's BYTES afterwards — the defect is a property of the file
on disk, not of anything the method returns.
"""
from __future__ import annotations

import hashlib

import pytest
import yaml

from engines.engine_d_discovery.discovery import DiscoveryEngine, RegistryUnreadableError

GOOD = {"edges": [
    {"edge_id": "momentum_edge_v1", "status": "active", "params": {"lookback": 20}},
    {"edge_id": "rsi_bounce_v1", "status": "paused", "params": {}},
    {"edge_id": "cand_old", "status": "candidate", "params": {}},
]}
NEW = {"edge_id": "cand_new", "status": "candidate", "params": {"genes": []}}


def _engine(path):
    eng = DiscoveryEngine.__new__(DiscoveryEngine)
    eng.registry_path = path
    return eng


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("planted", [
    pytest.param("edges:\n  - {edge_id: momentum_edge_v1, status: active\n  - {edge_id: x\n", id="unparseable-yaml"),
    pytest.param("<<<<<<< HEAD\nedges: []\n=======\nedges:\n  - {edge_id: a}\n>>>>>>> other\n", id="merge-conflict-markers"),
    pytest.param("", id="empty-file"),
    pytest.param("just a string\n", id="scalar-root"),
    pytest.param("version: 2\nedgez: []\n", id="dict-without-edges"),
    pytest.param("edges: {momentum_edge_v1: active}\n", id="edges-not-a-list"),
])
def test_an_unreadable_registry_is_REFUSED_and_left_byte_untouched(tmp_path, planted):
    """Revert to the old read → it falls back to an empty registry and rewrites the file
    with only `cand_new`: the bytes change (every other edge gone)."""
    reg = tmp_path / "edges.yml"
    reg.write_text(planted)
    before = _sha(reg)
    with pytest.raises(RegistryUnreadableError, match="refusing — the file is untouched"):
        _engine(reg).save_candidates([NEW])
    assert _sha(reg) == before, "save_candidates changed a registry it could not read"


def test_get_queued_candidates_refuses_an_unreadable_registry_never_reads_it_as_empty(tmp_path):
    """It returned [] on any read error — a cycle that silently found 'nothing queued'.
    Revert → returns []."""
    reg = tmp_path / "edges.yml"
    reg.write_text("edges:\n  - {edge_id: x\n")
    with pytest.raises(RegistryUnreadableError):
        _engine(reg).get_queued_candidates("candidate")


def test_an_absent_registry_is_an_empty_one(tmp_path):
    """The one legitimate empty: no file yet. First save creates it."""
    reg = tmp_path / "edges.yml"
    eng = _engine(reg)
    assert eng.get_queued_candidates("candidate") == []
    eng.save_candidates([NEW])
    assert yaml.safe_load(reg.read_text()) == {"edges": [NEW]}


def test_a_serialisation_failure_never_truncates_the_registry(tmp_path, monkeypatch):
    """The old code opened edges.yml with open("w") — truncating it — BEFORE yaml.dump ran,
    so a dump error left an EMPTY registry. Serialising first means the file is never
    touched. Revert → the file is empty after the error."""
    import engines.engine_d_discovery.discovery as dmod
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.dump(GOOD, sort_keys=False))
    before = _sha(reg)

    def _boom(*a, **kw):
        raise yaml.representer.RepresenterError("cannot represent an object")
    monkeypatch.setattr(dmod.yaml, "dump", _boom)
    with pytest.raises(yaml.representer.RepresenterError):
        _engine(reg).save_candidates([NEW])
    assert _sha(reg) == before


def test_a_failed_rename_leaves_the_registry_untouched(tmp_path, monkeypatch):
    """Atomicity at the last step: if the rename fails, edges.yml is the old file, whole."""
    import engines.engine_d_discovery.discovery as dmod
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.dump(GOOD, sort_keys=False))
    before = _sha(reg)

    def _no_rename(src, dst):
        raise OSError("disk full")
    monkeypatch.setattr(dmod.os, "replace", _no_rename)
    with pytest.raises(OSError, match="disk full"):
        _engine(reg).save_candidates([NEW])
    assert _sha(reg) == before


def test_POSITIVE_CONTROL_a_healthy_save_merges_and_is_byte_identical_to_the_old_format(tmp_path):
    """The fix must not change a healthy write: same merge (new appended, existing kept,
    duplicate id replaced), same bytes as the old `yaml.dump({"edges": ...}, sort_keys=False)`,
    and no temp file left behind."""
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.dump(GOOD, sort_keys=False))
    updated = dict(GOOD["edges"][2], status="failed")
    _engine(reg).save_candidates([NEW, updated])
    expected = {"edges": [GOOD["edges"][0], GOOD["edges"][1], updated, NEW]}
    assert reg.read_text() == yaml.dump(expected, sort_keys=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["edges.yml"]


def test_the_legacy_list_root_is_still_read(tmp_path):
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.dump(GOOD["edges"], sort_keys=False))
    assert [e["edge_id"] for e in _engine(reg).get_queued_candidates("candidate")] == ["cand_old"]


# --------------------------------------------------------------------------- #
# R's three notes on the review (fixup)
# --------------------------------------------------------------------------- #
def test_the_atomic_replace_keeps_the_registrys_permissions(tmp_path):
    """The temp file is created with the umask default, so a 600 registry became 644 after
    one save. Revert the chmod → 0o644 (under the usual 022 umask)."""
    import os
    import stat
    reg = tmp_path / "edges.yml"
    reg.write_text(yaml.dump(GOOD, sort_keys=False))
    os.chmod(reg, 0o600)
    _engine(reg).save_candidates([NEW])
    assert stat.S_IMODE(reg.stat().st_mode) == 0o600


def test_the_GA_fitness_seed_refuses_an_unreadable_registry(tmp_path):
    """R's F2: `_load_fitness_from_registry` swallowed a read failure (`except: pass`) and
    seeded the GA with no fitness history. Revert → returns {} silently."""
    reg = tmp_path / "edges.yml"
    reg.write_text("edges:\n  - {edge_id: x\n")
    with pytest.raises(RegistryUnreadableError):
        _engine(reg)._load_fitness_from_registry()


def test_a_refused_queue_read_is_labelled_by_its_own_stage(monkeypatch, tmp_path):
    """R's note: the cycle's first registry READ (the queue) failed under the label of the
    previous stage, 'save new candidates'. Revert → that label."""
    from tests.test_rr6a_gate_verdicts import _drive_cycle
    seen = {}
    with pytest.raises(RegistryUnreadableError):
        _drive_cycle(monkeypatch, tmp_path, seen=seen,
                     queued_raises=RegistryUnreadableError("edges.yml is not parseable YAML"))
    assert seen["failures"][0][0] == "load queue"
