"""Survival for RR-3's honest-N inputs (T-356b) — the run registry and the ρ̄ artifacts.

The hazard is not loss alone. D's census: `rebuild()` after a loss re-reads whatever sits
in local trade_logs, and 125 run rows' directories exist nowhere — so the rebuilt N is
SMALLER and the gate LOOSER, with no alarm. A naive mirror would then publish that smaller
N over the good copy. These tests pin the rule that refuses it, against a fake S3.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts import janitor_nightly as jn
from scripts import ledger_backup as lb


def _registry(path: Path, rows: dict) -> Path:
    """A minimal run registry: {run_id: sharpe}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, sharpe REAL)")
    con.executemany("INSERT INTO runs VALUES (?, ?)", list(rows.items()))
    con.commit()
    con.close()
    return path


@pytest.fixture
def s3(monkeypatch):
    """A dict standing in for the bucket; records every PUT."""
    store: dict = {}
    puts: list = []

    def read_remote(key=lb.KEY_CANON):
        return (store[key], "ok") if key in store else (None, "absent")

    def put(local: Path, key: str):
        store[key] = Path(local).read_bytes()
        puts.append(key)
        return None

    monkeypatch.setattr(lb, "read_remote", read_remote)
    monkeypatch.setattr(lb, "_put", put)
    monkeypatch.setattr(lb, "NET_BACKOFF_S", 0)
    return store, puts


@pytest.fixture
def obs(tmp_path):
    d = tmp_path / "data/observability"
    _registry(d / lb.OBS_REGISTRY, {f"r{i}": 0.1 * i for i in range(5)})
    (d / "n_effective_2026-09-30.json").write_text('{"gate_inputs": {"rho_bar": 0.46}}')
    return d


# ── the pure rules ────────────────────────────────────────────────────────────

def test_registry_rule():
    a, ab = {"r1"}, {"r1", "r2"}
    assert lb.classify_registry(set(), None, False).status == lb.REFUSE
    assert lb.classify_registry(ab, None, False).status == lb.OK_FIRST
    assert lb.classify_registry(ab, ab, True).status == lb.OK_SAME
    assert lb.classify_registry(ab, a, False).status == lb.OK_EXTEND
    v = lb.classify_registry(a, ab, False)
    assert v.status == lb.REFUSE and "SMALLER N" in v.detail
    same_ids = lb.classify_registry(ab, ab, False)
    assert same_ids.status == lb.OK_EXTEND and "N unchanged" in same_ids.detail


def test_artifact_rule():
    assert lb.classify_artifact("x", b"", None).status == lb.REFUSE
    assert lb.classify_artifact("x", b"1", None).status == lb.OK_FIRST
    assert lb.classify_artifact("x", b"1", b"1").status == lb.OK_SAME
    assert lb.classify_artifact("x", b"2", b"1").status == lb.REFUSE


def test_the_backup_never_writes_the_gates_input(obs):
    db = obs / lb.OBS_REGISTRY
    before = db.read_bytes()
    lb._registry_ids(db)
    lb._content_digest(db)
    lb._snapshot(db, obs / "snap.sqlite")
    assert db.read_bytes() == before


def test_content_digest_tracks_rows_not_bytes(obs, tmp_path):
    db = obs / lb.OBS_REGISTRY
    lb._snapshot(db, tmp_path / "a.sqlite")
    assert lb._content_digest(tmp_path / "a.sqlite") == lb._content_digest(db)
    _registry(tmp_path / "b.sqlite", {"r0": 9.9})
    assert lb._content_digest(tmp_path / "b.sqlite") != lb._content_digest(db)


# ── the drill: first push, quiet night, LOSS, extension ─────────────────────

def test_the_loss_drill(obs, s3):
    store, puts = s3
    db = obs / lb.OBS_REGISTRY

    v = lb.sync_observability(obs, as_of="2026-10-14")
    assert v.status == lb.OK_FIRST, v.detail
    assert lb.KEY_REGISTRY in store and "ops/observability/daily/run_registry_2026-10-14.sqlite" in store
    assert "ops/observability/n_effective_2026-09-30.json" in store

    n = len(puts)
    v = lb.sync_observability(obs, as_of="2026-10-15")
    assert v.status == lb.OK_SAME and len(puts) == n, "an unchanged night pushes nothing"

    good = store[lb.KEY_REGISTRY]
    _registry(db, {"r0": 0.0, "r1": 0.1})          # rebuilt after loss: 2 of 5 runs
    v = lb.sync_observability(obs, as_of="2026-10-16")
    assert v.status == lb.REFUSE and not v.ok and "SMALLER N" in v.detail
    assert store[lb.KEY_REGISTRY] == good, "the good remote copy must survive the refusal"

    _registry(db, {f"r{i}": 0.1 * i for i in range(6)})   # all 5 + one new run
    v = lb.sync_observability(obs, as_of="2026-10-17")
    assert v.status == lb.OK_EXTEND, v.detail
    assert lb._read_blob(store[lb.KEY_REGISTRY])[0] == {f"r{i}" for i in range(6)}


def test_a_changed_artifact_is_refused_and_an_explicit_rewrite_is_labelled(obs, s3):
    store, _ = s3
    lb.sync_observability(obs)
    art = obs / "n_effective_2026-09-30.json"
    art.write_text('{"gate_inputs": {"rho_bar": 0.10}}')
    v = lb.sync_observability(obs)
    assert v.status == lb.REFUSE and "immutable by name" in v.detail
    assert b"0.46" in store["ops/observability/n_effective_2026-09-30.json"]
    v = lb.sync_observability(obs, allow_rewrite=True)
    assert v.ok and "REWRITE ALLOWED" in v.detail
    assert b"0.10" in store["ops/observability/n_effective_2026-09-30.json"]


def test_an_unreadable_remote_registry_is_not_overwritten(obs, s3):
    store, puts = s3
    store[lb.KEY_REGISTRY] = b"not a database"
    v = lb.sync_observability(obs)
    assert v.status == lb.REFUSE and "unreadable" in v.detail
    assert store[lb.KEY_REGISTRY] == b"not a database" and lb.KEY_REGISTRY not in puts


def test_missing_local_inputs_are_refused(tmp_path, s3):
    d = tmp_path / "obs"
    d.mkdir()
    v = lb.sync_observability(d)
    assert v.status == lb.REFUSE
    assert "no local run registry" in v.detail and "n_effective" in v.detail


def test_an_unreachable_network_DEFERS_and_pushes_nothing(obs, s3, monkeypatch):
    _, puts = s3
    monkeypatch.setattr(lb, "read_remote", lambda key=None: (None, "unreachable: no route"))
    v = lb.sync_observability(obs)
    assert v.status == lb.DEFERRED and v.ok and puts == []


def test_verify_states_single_copy_then_current_then_loss(obs, s3):
    assert not lb.verify_observability(obs).ok, "no remote copy = single copy = not ok"
    lb.sync_observability(obs)
    v = lb.verify_observability(obs)
    assert v.ok and v.status == lb.OK_SAME, v.detail
    _registry(obs / lb.OBS_REGISTRY, {"r0": 0.0})
    v = lb.verify_observability(obs)
    assert not v.ok and "N would shrink" in v.detail


# ── the janitor: driven by execution ─────────────────────────────────────────

def test_the_janitor_runs_the_observability_check(monkeypatch):
    for name in [n for n in dir(jn) if n.startswith("check_")]:
        label = name[len("check_"):]
        monkeypatch.setattr(jn, name, lambda label=label: jn.Check(label, True, "stub"))
    assert "observability_backup" in [c.name for c in jn.run_checks()]


def test_a_corrupt_registry_is_reported_not_fatal(monkeypatch):
    def boom(_):
        raise sqlite3.DatabaseError("file is not a database")
    monkeypatch.setattr(lb, "verify_observability", boom)
    c = jn.check_observability_backup()
    assert not c.ok and "DatabaseError" in c.detail


def test_survival_syncs_push_both_and_one_failure_does_not_cost_the_other(monkeypatch):
    calls = []

    def ledger_sync(path, allow_rewrite=False, as_of=None):
        raise RuntimeError("s3 hiccup")

    def obs_sync(path, allow_rewrite=False, as_of=None):
        calls.append(allow_rewrite)
        return lb.PushVerdict(lb.OK_SAME, "current")

    monkeypatch.setattr(lb, "sync", ledger_sync)
    monkeypatch.setattr(lb, "sync_observability", obs_sync)
    out = dict(jn.survival_syncs("2026-10-14"))
    assert out["ledger_sync"].status == lb.REFUSE and "RuntimeError" in out["ledger_sync"].detail
    assert out["observability_sync"].ok and calls == [False], "never allow_rewrite at night"
