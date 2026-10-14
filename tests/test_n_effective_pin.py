"""RR-3 §9.3 (2026-10-13) — the honest-N gate's ρ̄ input is PINNED, not "newest wins".

Before this, `mbl_gate.latest_n_effective_artifact()` took the newest `n_effective_*.json` by
filename, so any re-run of `scripts/rr3_empirical_rho.py`, by anyone, silently replaced the live
gate's input with no review. The Option B pass that night avoided it only by naming its output
differently — a convention, not a control. These tests DRIVE the gate's real entry points, and the
first regression below fails if "newest wins" is restored.
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


def _pin(pin: Path, art: Path) -> Path:
    pin.write_text(json.dumps({"artifact": art.name, "sha256": sha256_file(art)}))
    return pin


# ----------------------------------------------------------------------------- the defect
def test_a_NEWER_artifact_does_not_replace_the_pinned_one(tmp_path):
    """THE REGRESSION for §9.3. A re-run drops a newer file beside the pinned one; the gate must
    keep reading what was pinned. Under 'newest wins' this returns the 2099 file and fails."""
    reg = _registry(tmp_path / "r.sqlite", 231)
    pinned = _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    _artifact(tmp_path, "n_effective_2099-12-31.json", rho=0.95, comp=0.01)   # would loosen the gate
    pin = _pin(tmp_path / "pin.json", pinned)

    assert pinned_n_effective_artifact(pin, tmp_path) == pinned
    n = compute_n_effective_correlated(reg, artifact_dir=tmp_path, pin_path=pin)
    assert n == max(mbl.n_eff_equicorrelated(231, 0.43), 231 * 0.16), "gate read the newer, unpinned file"


def test_an_artifact_edited_in_place_after_pinning_is_REFUSED(tmp_path):
    art = _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    pin = _pin(tmp_path / "pin.json", art)
    _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.90, comp=0.02)   # same name, new bytes
    with pytest.raises(HonestNUnavailableError, match="does not match its pin"):
        pinned_n_effective_artifact(pin, tmp_path)


# ----------------------------------------------------------------------------- fails closed
def test_an_absent_pin_is_REFUSED_not_guessed(tmp_path):
    _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        pinned_n_effective_artifact(tmp_path / "no_pin.json", tmp_path)


def test_a_malformed_pin_is_REFUSED(tmp_path):
    pin = tmp_path / "pin.json"
    pin.write_text('{"artifact": "n_effective_2026-09-30.json"}')          # no sha256
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        pinned_n_effective_artifact(pin, tmp_path)


def test_a_pin_naming_a_PATH_is_REFUSED(tmp_path):
    """The pin names a file in the artifact dir, never a path — so it cannot be pointed elsewhere."""
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"artifact": "../elsewhere/n_effective_x.json", "sha256": "0" * 64}))
    with pytest.raises(HonestNUnavailableError, match="names a path"):
        pinned_n_effective_artifact(pin, tmp_path)


def test_an_absent_pinned_artifact_is_REFUSED(tmp_path):
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"artifact": "n_effective_2026-09-30.json", "sha256": "0" * 64}))
    with pytest.raises(HonestNUnavailableError, match="is absent"):
        pinned_n_effective_artifact(pin, tmp_path)


def test_the_production_default_path_goes_through_the_pin(tmp_path, monkeypatch):
    """Discovery's Gate 8 and check_mbl_gate call compute_n_effective_correlated() with NO artifact
    argument. With the default pin pointed at nothing, that call must raise — the pin is on the
    production path, not only on the path tests use."""
    reg = _registry(tmp_path / "r.sqlite", 50)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", reg)
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", tmp_path / "absent_pin.json")
    _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)   # present but unpinned
    with pytest.raises(HonestNUnavailableError, match="absent or malformed"):
        compute_n_effective_correlated()


# ----------------------------------------------------------------------------- re-pinning
def test_write_pin_records_the_sha_and_refuses_an_unreadable_artifact(tmp_path):
    art = _artifact(tmp_path, "n_effective_2026-10-13.json", rho=0.43, comp=0.14)
    pin = tmp_path / "pin.json"
    rec = write_pin(art.name, artifact_dir=tmp_path, pin_path=pin, note="test")
    assert rec["sha256"] == sha256_file(art) and json.loads(pin.read_text())["artifact"] == art.name
    (tmp_path / "n_effective_bad.json").write_text(json.dumps({"rho_bar": 0.5}))
    with pytest.raises(HonestNUnavailableError, match="gate_inputs"):
        write_pin("n_effective_bad.json", artifact_dir=tmp_path, pin_path=tmp_path / "pin2.json")


def test_the_verify_command_exits_nonzero_on_a_bad_pin(tmp_path, monkeypatch, capsys):
    art = _artifact(tmp_path, "n_effective_2026-09-30.json", rho=0.43, comp=0.16)
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", _pin(tmp_path / "pin.json", art))
    assert mbl.main(["--verify"]) == 0
    art.write_text(art.read_text().replace("0.43", "0.44"))
    assert mbl.main(["--verify"]) == 3
    assert "PIN INVALID" in capsys.readouterr().out


def test_an_explicit_artifact_path_is_a_deliberate_choice_and_still_validated(tmp_path):
    """Tools and tests may name an artifact outright (like an explicit n_trials_for_dsr); it is
    still validated. No production caller passes one."""
    art = _artifact(tmp_path, "anything.json", rho=0.43, comp=0.16)
    assert load_n_effective_artifact(path=art)["gate_inputs"]["rho_bar"] == 0.43


# ----------------------------------------------------------------------------- the committed pin
def test_the_committed_pin_is_well_formed():
    """Hermetic: the repo's pin names an n_effective_* file (not a path) and carries a full
    sha256. Whether it MATCHES the artifact is checked by `python -m scripts.n_effective_pin
    --verify` where the artifact exists — the gate itself refuses a mismatch either way."""
    pin = json.loads((ROOT / "config" / "n_effective_pin.json").read_text())
    assert pin["schema"] == "n_effective_pin/v1"
    assert re.fullmatch(r"n_effective_\d{4}-\d{2}-\d{2}\.json", pin["artifact"])
    assert re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
    assert "latest_n_effective_artifact" not in dir(mbl), "the newest-wins selector is back"
