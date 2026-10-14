"""RR-3 §9.3 (2026-10-13) — BOTH honest-N inputs are PINNED: the ρ̄ artifact and the run registry.

Before this, `mbl_gate.latest_n_effective_artifact()` took the newest `n_effective_*.json` by
filename, so any re-run of `scripts/rr3_empirical_rho.py`, by anyone, silently replaced the live
gate's input with no review. R's addition: pin the registry too, which closes T-356b's
rebuild-after-loss case — a registry rebuilt from whatever is on disk would otherwise hand the gate
a SMALLER N without complaint. These tests DRIVE the gate's real entry points; the first and the
rebuild-after-loss test fail if the corresponding protection is reverted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import core.measurement.mbl_gate as mbl
from core.measurement.mbl_gate import (
    HonestNUnavailableError,
    compute_n_effective_correlated,
    load_n_effective_artifact,
    pinned_n_effective_artifact,
    sha256_file,
    verify_pinned_registry,
    write_pin,
)

ROOT = Path(__file__).resolve().parents[1]


def _registry(path: Path, n: int = 100) -> Path:
    import sqlite3
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY)")
    c.executemany("INSERT INTO runs VALUES (?)", [(f"r{i}",) for i in range(n)])
    c.commit(); c.close()
    return path


def _artifact(d: Path, name: str, rho: float, comp: float) -> Path:
    p = d / name
    p.write_text(json.dumps({"rho_bar": rho, "onc_compression": comp,
                             "gate_inputs": {"rho_bar": rho, "onc_compression": comp}}))
    return p


@pytest.fixture
def pinned(tmp_path):
    """A correctly pinned pair: registry (231 rows) + artifact (ρ̄ 0.43, compression 0.16)."""
    reg = _registry(tmp_path / "run_registry.sqlite", 231)
    art = _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    pin = tmp_path / "honest_n_pin.json"
    write_pin(art.name, artifact_dir=tmp_path, db_path=reg, pin_path=pin)
    return tmp_path, reg, art, pin


def _gate(d, reg, pin):
    return compute_n_effective_correlated(reg, artifact_dir=d, pin_path=pin)


def _expected(n):
    return max(mbl.n_eff_equicorrelated(n, 0.43), n * 0.16)


def test_the_pinned_pair_gates_normally(pinned):
    d, reg, _, pin = pinned
    assert _gate(d, reg, pin) == _expected(231)


# ----------------------------------------------------------------------------- the ρ̄ artifact
def test_a_NEWER_artifact_does_not_replace_the_pinned_one(pinned):
    """THE REGRESSION for §9.3: a re-run drops a newer file beside the pinned one; the gate keeps
    reading what was pinned. Under 'newest wins' this reads the 2099 file and fails."""
    d, reg, art, pin = pinned
    _artifact(d, "n_effective_2099-12-31.json", rho=0.95, comp=0.01)        # would loosen the gate
    assert pinned_n_effective_artifact(pin, d) == art
    assert _gate(d, reg, pin) == _expected(231)


def test_an_artifact_edited_in_place_after_pinning_is_REFUSED(pinned):
    d, reg, _, pin = pinned
    _artifact(d, "n_effective_2026-09-30.json", rho=0.90, comp=0.02)        # same name, new bytes
    with pytest.raises(HonestNUnavailableError, match="artifact .* does not match its pin"):
        _gate(d, reg, pin)


# ----------------------------------------------------------------------------- the registry (R2)
def test_a_registry_REBUILT_AFTER_LOSS_is_refused_not_trusted(pinned):
    """T-356b's case, closed: the registry is lost and rebuilt from what is on disk that day —
    fewer rows. Without the registry pin the gate would silently read a smaller N and LOOSEN.
    Reverting the registry pin makes this return a smaller N instead of raising."""
    d, reg, _, pin = pinned
    reg.unlink()
    _registry(reg, 106)                                                   # rebuilt: ledger rows only
    with pytest.raises(HonestNUnavailableError, match="run registry .* does not match its pin"):
        _gate(d, reg, pin)


def test_a_backfill_after_pinning_is_refused_until_re_pinned(pinned):
    """Legitimate growth (a backfill, Option B's rebuild) also changes the bytes. That is the point:
    changing what N is computed from is a reviewed re-pin, not a side effect."""
    d, reg, art, pin = pinned
    import sqlite3
    c = sqlite3.connect(reg); c.execute("INSERT INTO runs VALUES ('new')"); c.commit(); c.close()
    with pytest.raises(HonestNUnavailableError, match="run registry"):
        _gate(d, reg, pin)
    write_pin(art.name, artifact_dir=d, db_path=reg, pin_path=pin)         # the reviewed re-pin
    assert _gate(d, reg, pin) == _expected(232)


def test_a_registry_with_a_different_name_is_refused(pinned):
    d, _, _, pin = pinned
    other = _registry(d / "other_registry.sqlite", 231)
    with pytest.raises(HonestNUnavailableError, match="pin names 'run_registry.sqlite'"):
        verify_pinned_registry(other, pin)


def test_the_gate_never_changes_the_registry_it_pins(pinned):
    """The registry is read read-only, so reading it cannot alter the bytes the pin protects."""
    d, reg, _, pin = pinned
    before = sha256_file(reg)
    for _ in range(3):
        _gate(d, reg, pin)
    assert sha256_file(reg) == before


# ----------------------------------------------------------------------------- the pin itself
def test_an_absent_pin_is_REFUSED_not_guessed(tmp_path):
    reg = _registry(tmp_path / "run_registry.sqlite")
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        _gate(tmp_path, reg, tmp_path / "no_pin.json")


@pytest.mark.parametrize("bad", [
    {"artifact": {"file": "n_effective_2026-09-30.json", "sha256": "0" * 64}},              # no registry
    {"artifact": {"file": "n_effective_2026-09-30.json"},
     "registry": {"file": "run_registry.sqlite", "sha256": "0" * 64}},                    # no artifact sha
    {"artifact": "n_effective_2026-09-30.json",
     "registry": {"file": "run_registry.sqlite", "sha256": "0" * 64}},                    # the v0 shape
])
def test_a_malformed_pin_is_REFUSED(tmp_path, bad):
    reg = _registry(tmp_path / "run_registry.sqlite")
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps(bad))
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        _gate(tmp_path, reg, pin)


def test_a_pin_naming_a_PATH_is_REFUSED(tmp_path):
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"artifact": {"file": "../x/n_effective_x.json", "sha256": "0" * 64},
                               "registry": {"file": "run_registry.sqlite", "sha256": "0" * 64}}))
    with pytest.raises(HonestNUnavailableError, match="names a path"):
        pinned_n_effective_artifact(pin, tmp_path)


def test_the_production_default_path_goes_through_the_pin(tmp_path, monkeypatch):
    """Discovery's Gate 8 and check_mbl_gate call compute_n_effective_correlated() with NO arguments.
    With the default pin pointed at nothing, that call must raise."""
    reg = _registry(tmp_path / "run_registry.sqlite", 50)
    _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", tmp_path / "absent_pin.json")
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        compute_n_effective_correlated()


def test_write_pin_refuses_what_the_gate_could_not_read(tmp_path):
    reg = _registry(tmp_path / "run_registry.sqlite")
    (tmp_path / "n_effective_bad.json").write_text(json.dumps({"rho_bar": 0.5}))
    with pytest.raises(HonestNUnavailableError, match="gate_inputs"):
        write_pin("n_effective_bad.json", artifact_dir=tmp_path, db_path=reg, pin_path=tmp_path / "p.json")
    art = _artifact(tmp_path, "n_effective_ok.json", rho=0.4, comp=0.1)
    empty = tmp_path / "empty.sqlite"
    import sqlite3
    c = sqlite3.connect(empty); c.execute("CREATE TABLE runs (run_id TEXT)"); c.commit(); c.close()
    with pytest.raises(HonestNUnavailableError, match="0 rows"):
        write_pin(art.name, artifact_dir=tmp_path, db_path=empty, pin_path=tmp_path / "p.json")


def test_the_verify_command_checks_BOTH_files(pinned, monkeypatch, capsys):
    d, reg, _, pin = pinned
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", d)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", pin)
    assert mbl.main(["--verify"]) == 0
    import sqlite3
    c = sqlite3.connect(reg); c.execute("INSERT INTO runs VALUES ('x')"); c.commit(); c.close()
    assert mbl.main(["--verify"]) == 3
    assert "run registry" in capsys.readouterr().out


def test_an_explicit_artifact_path_is_a_deliberate_bypass(tmp_path):
    """Tools and tests may name an artifact outright; it is still validated, and no production
    caller passes one."""
    art = _artifact(tmp_path, "anything.json", rho=0.43, comp=0.16)
    assert load_n_effective_artifact(path=art)["gate_inputs"]["rho_bar"] == 0.43


def test_the_committed_pin_is_well_formed():
    """Hermetic: the repo's pin covers both inputs with full sha256s. Whether they MATCH the files is
    `python -m scripts.honest_n_pin --verify` where the files exist — the gate refuses a mismatch."""
    pin = json.loads((ROOT / "config" / "honest_n_pin.json").read_text())
    assert pin["schema"] == "honest_n_pin/v1"
    assert re.fullmatch(r"n_effective_\d{4}-\d{2}-\d{2}\.json", pin["artifact"]["file"])
    assert pin["registry"]["file"] == "run_registry.sqlite"
    for k in ("artifact", "registry"):
        assert re.fullmatch(r"[0-9a-f]{64}", pin[k]["sha256"])
    assert "latest_n_effective_artifact" not in dir(mbl), "the newest-wins selector is back"
