"""T-389 (cutover pre-condition P6, option A) — the pairs edge's input pinned by name and verified.

`engines/engine_a_alpha/edges/pairs_trading_v1.py` registers its pair edges at import FROM
`data/research/cointegrated_pairs_2026_05_09.json`. Without the file it registers nothing, and the
image's registry check (`scripts/sync_edge_registry.py --check`) then cannot see the anchor's pairs
rows at all. These locks drive the real code: the pin's `main()` / `verify()` / `write_pin()` and the
real `sync()` on planted trees under tmp_path (cwd moved there, so the module's cwd-relative
MANIFEST_PATH resolves into the plant). Nothing here writes under the repo's data/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from scripts import pairs_manifest_pin as pmp
from tests._canonical_inputs import CANON_PAIRS_MANIFEST, requires_canonical

REPO = Path(__file__).resolve().parent.parent
PIN = REPO / "config" / "pairs_manifest_pin.json"
PAIRS_MODULE = "engines.engine_a_alpha.edges.pairs_trading_v1"


# ───────────────────────────────────────────────────────────────────────────────
# planted screens
# ───────────────────────────────────────────────────────────────────────────────

def _screen(survivors: List[Dict[str, Any]], *, losers: int = 1) -> Dict[str, Any]:
    cands = [dict(s, survives=True) for s in survivors]
    cands += [{"ticker_x": f"L{i}", "ticker_y": f"M{i}", "survives": False, "beta": 1.0} for i in range(losers)]
    ids = [f"pairs_trading_{s['ticker_x']}_{s['ticker_y']}_v1" for s in survivors]
    return {"task_id": "T-2026-05-09-017", "candidates": cands, "survivor_pair_ids": ids}


AAA_BBB = {"ticker_x": "AAA", "ticker_y": "BBB", "beta": 0.75}
REL = "data/research/cointegrated_pairs_2026_05_09.json"


def _plant_screen(root: Path, payload: Dict[str, Any], rel: str = REL) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2))
    return p


def _plant_byte(p: Path) -> None:
    b = bytearray(p.read_bytes())
    b[len(b) // 2] ^= 0x01
    p.write_bytes(bytes(b))


def _aside(p: Path) -> Path:
    """Make `p` absent without deleting anything: rename it beside itself."""
    target = p.with_name(p.name + ".aside")
    p.rename(target)
    return target


# ═══════════════════════════════════════════════════════════════════════════════
# The pin script: verify / pin, by execution on planted trees
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_passes_on_the_pinned_file_and_fails_on_one_byte_absence_and_no_pin(tmp_path, capsys, monkeypatch):
    root, pin = tmp_path / "tree", tmp_path / "pin.json"
    f = _plant_screen(root, _screen([AAA_BBB]))
    written = pmp.write_pin(REL, root=root, pin_path=pin, note="t")
    assert written["survivor_edge_ids"] == ["pairs_trading_AAA_BBB_v1"]
    assert pmp.verify(root=root, pin_path=pin)["sha256"] == pmp.sha256_file(f)

    monkeypatch.setattr(pmp, "ROOT", root)                 # main() resolves both defaults at call time
    monkeypatch.setattr(pmp, "DEFAULT_PIN_PATH", pin)
    assert pmp.main(["--verify"]) == 0 and "PIN OK" in capsys.readouterr().out

    good = f.read_bytes()
    _plant_byte(f)
    assert pmp.main(["--verify"]) == 3
    assert "PIN INVALID" in (out := capsys.readouterr().out) and "sha256" in out
    f.write_bytes(good)

    aside = _aside(f)
    assert pmp.main(["--verify"]) == 3
    assert "ABSENT" in capsys.readouterr().out
    aside.rename(f)
    assert pmp.main(["--verify"]) == 0

    _aside(pin)
    assert pmp.main(["--verify"]) == 3
    assert "unpinned" in capsys.readouterr().out


@pytest.mark.parametrize("payload, needle", [
    (_screen([]), "zero surviving pairs"),
    ({**_screen([AAA_BBB]), "survivor_pair_ids": ["pairs_trading_XXX_YYY_v1"]}, "disagrees"),
    ({"no_candidates": True}, "no `candidates` list"),
    (_screen([{"ticker_x": "AAA", "ticker_y": "", "beta": 1.0}]), "lack ticker_x/ticker_y/beta"),
])
def test_pin_REFUSES_a_screen_the_verify_could_not_stand_behind(tmp_path, payload, needle):
    root = tmp_path / "tree"
    _plant_screen(root, payload)
    with pytest.raises(pmp.PairsPinInvalid, match=needle):
        pmp.write_pin(REL, root=root, pin_path=tmp_path / "pin.json")
    assert not (tmp_path / "pin.json").exists()


def test_pin_never_overwrites_silently_and_replace_is_explicit(tmp_path, monkeypatch, capsys):
    root, pin = tmp_path / "tree", tmp_path / "pin.json"
    _plant_screen(root, _screen([AAA_BBB]))
    first = pmp.write_pin(REL, root=root, pin_path=pin)
    _plant_screen(root, _screen([AAA_BBB, {"ticker_x": "CCC", "ticker_y": "DDD", "beta": 1.1}]))
    with pytest.raises(pmp.PinExistsError):
        pmp.write_pin(REL, root=root, pin_path=pin)
    assert json.loads(pin.read_text())["sha256"] == first["sha256"]
    monkeypatch.setattr(pmp, "ROOT", root)
    monkeypatch.setattr(pmp, "DEFAULT_PIN_PATH", pin)
    assert pmp.main(["--pin", REL]) == 4 and "REFUSED" in capsys.readouterr().err
    with pytest.raises(pmp.PairsPinInvalid, match="sha256"):  # the file moved under its pin
        pmp.verify(root=root, pin_path=pin)
    second = pmp.write_pin(REL, root=root, pin_path=pin, replace=True)
    assert second["survivor_edge_ids"] == ["pairs_trading_AAA_BBB_v1", "pairs_trading_CCC_DDD_v1"]
    assert pmp.verify(root=root, pin_path=pin)["sha256"] == second["sha256"]


@pytest.mark.parametrize("bad", ["/abs/x.json", "../outside.json"])
def test_the_pin_is_repo_relative_only(tmp_path, bad):
    with pytest.raises(pmp.PairsPinInvalid, match="repo-relative"):
        pmp.write_pin(bad, root=tmp_path, pin_path=tmp_path / "pin.json")
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"schema": pmp.SCHEMA, "file": bad, "sha256": "0" * 64,
                               "survivor_edge_ids": ["x"]}))
    with pytest.raises(pmp.PairsPinInvalid, match="repo-relative"):
        pmp.verify(root=tmp_path, pin_path=pin)


def test_the_pins_survivor_ids_are_the_ids_the_edge_module_builds():
    """The pin derives `pairs_trading_<X>_<Y>_v1` itself (no engine import at image build); it must
    equal what `pairs_trading_v1._build_pair_spec` registers."""
    from engines.engine_a_alpha.edges.pairs_trading_v1 import _build_pair_spec
    ids = pmp.survivor_edge_ids(_screen([AAA_BBB]), source="t")
    assert ids == [_build_pair_spec(dict(AAA_BBB, survives=True))[1].edge_id]


# ═══════════════════════════════════════════════════════════════════════════════
# The committed pin against the real tree
# ═══════════════════════════════════════════════════════════════════════════════

def test_LOCK_the_committed_pin_names_the_file_the_pairs_edge_reads():
    """A rename of the edge's input (MANIFEST_PATH) must force a pin edit in the same act."""
    from engines.engine_a_alpha.edges.pairs_trading_v1 import MANIFEST_PATH
    pin = pmp.load_pin(PIN)
    assert pin["file"] == MANIFEST_PATH.as_posix() == CANON_PAIRS_MANIFEST
    assert pin["schema"] == pmp.SCHEMA and len(pin["sha256"]) == 64


@requires_canonical(CANON_PAIRS_MANIFEST)
def test_the_REAL_pin_verifies_the_REAL_file_copied_as_the_image_copies_it_and_a_planted_byte_fails(tmp_path):
    pin = pmp.load_pin(PIN)
    image = tmp_path / "image"
    (image / pin["file"]).parent.mkdir(parents=True)
    shutil.copyfile(REPO / pin["file"], image / pin["file"])           # the Dockerfile's COPY, by name
    assert pmp.verify(root=image, pin_path=PIN)["survivor_edge_ids"] == ["pairs_trading_MA_V_v1"]
    _plant_byte(image / pin["file"])
    with pytest.raises(pmp.PairsPinInvalid, match="sha256"):
        pmp.verify(root=image, pin_path=PIN)


@requires_canonical(CANON_PAIRS_MANIFEST)
def test_the_exact_build_command_runs_on_this_tree():
    """`python -m scripts.pairs_manifest_pin --verify` as the Dockerfile runs it (subprocess, real defaults)."""
    r = subprocess.run([sys.executable, "-m", "scripts.pairs_manifest_pin", "--verify"], cwd=REPO,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "PIN OK" in r.stdout, r.stdout + r.stderr


# ═══════════════════════════════════════════════════════════════════════════════
# Why the bake matters — the real registry check, image-shaped, with and without the file
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def _pairs_registrations_restored():
    """sync() reloads the pairs module with cwd in tmp_path; drop what it recorded afterwards."""
    from engines.engine_a_alpha.edge_registry import EdgeRegistry
    yield
    for eid, r in list(EdgeRegistry.import_registrations().items()):
        if str(r.spec.module) == PAIRS_MODULE:
            EdgeRegistry._import_registrations.pop(eid, None)


def _image_tree(tmp_path: Path, monkeypatch, *, with_file: bool) -> Path:
    """cwd = an /app-shaped tree: the anchor registry written by the REAL sync from a planted screen
    (the re-anchor), no live data/governor/edges.yml (T-133), and the screen present or not."""
    from scripts.sync_edge_registry import sync
    image = tmp_path / "app"
    _plant_screen(image, _screen([AAA_BBB]))
    monkeypatch.chdir(image)
    anchor = Path("data/governor/_isolated_anchor/edges.yml")
    anchor.parent.mkdir(parents=True)
    sync(anchor, modules=["pairs_trading_v1"])                          # the re-anchor carries the row
    assert "pairs_trading_AAA_BBB_v1" in anchor.read_text()
    if not with_file:
        _aside(image / REL)
    return image


def _drift(anchor: Path, key: str, value: Any) -> None:
    d = yaml.safe_load(anchor.read_text())
    for row in d["edges"]:
        if row["edge_id"] == "pairs_trading_AAA_BBB_v1":
            row["params"][key] = value
    anchor.write_text(yaml.safe_dump(d, sort_keys=False))


@pytest.mark.usefixtures("_pairs_registrations_restored")
def test_WITH_the_baked_file_the_image_check_verifies_the_anchors_pairs_row(tmp_path, monkeypatch):
    from scripts.sync_edge_registry import sync
    _image_tree(tmp_path, monkeypatch, with_file=True)
    anchor = Path("data/governor/_isolated_anchor/edges.yml")
    rep = sync(anchor, modules=["pairs_trading_v1"], check=True)
    assert rep.registrations_per_module == {"pairs_trading_v1": 1} and not rep.changes_file
    _drift(anchor, "beta", 0.5)
    rep = sync(anchor, modules=["pairs_trading_v1"], check=True)
    assert rep.changes_file and rep.drift_applied["pairs_trading_AAA_BBB_v1"]["params.beta"] == [0.5, 0.75]


@pytest.mark.usefixtures("_pairs_registrations_restored")
def test_EVIDENCE_WITHOUT_the_file_the_image_check_cannot_see_the_pairs_row_at_all(tmp_path, monkeypatch):
    """The option-B blind spot (T-389, 2026-11-12), by execution: with the screen absent the module
    registers nothing and the check exits clean on a drifted beta AND a nonsensical z_entry. If the
    check is ever hardened to refuse unverifiable rows, this test is expected to flip — update it then."""
    from scripts.sync_edge_registry import sync
    _image_tree(tmp_path, monkeypatch, with_file=False)
    anchor = Path("data/governor/_isolated_anchor/edges.yml")
    _drift(anchor, "beta", 0.5)
    _drift(anchor, "z_entry", 9.0)
    rep = sync(anchor, modules=["pairs_trading_v1"], check=True)
    assert rep.registrations_per_module == {"pairs_trading_v1": 0}
    assert not rep.changes_file, "the check saw the drift — the blind spot is closed; revisit option B"
