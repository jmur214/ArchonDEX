"""Re-pin #1's CODE half (T-375, 2026-11-05) — the locks the record's §5 names.

The record: `docs/Sources/proposal_repin_1_drip_substrate_2026-11-05.md` §2 (C1–C7) and §5 (what
must FAIL under reversion). Every lock here drives the real code — the generator's own
`build_manifest()` / `main()`, the T-219 script's `main()`, the pin's `--verify` — on a planted
tree under tmp_path; a text check appears only where the subject IS text (a Dockerfile line, a
`.dockerignore` pattern, a shell staging line) and is labelled as such.

NOTHING HERE MAY TOUCH THE REAL STAMP OR THE REAL DATA: `canonical_root` is monkeypatched for every
test (the stamp tests' guard, reused), the real stamp's bytes are asserted identical across the
module, and every write goes to tmp_path (the conftest data/ guard fails the session otherwise).
A planted file is made ABSENT by renaming it aside, never by deleting it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import substrate_stamp as st
from scripts import gen_substrate_manifest as gm

REPO = Path(__file__).resolve().parent.parent
PIN = REPO / "config" / "honest_n_pin.json"

_REAL_CANONICAL_ROOT = st.canonical_root


def _real_stamp_bytes():
    try:
        p = _REAL_CANONICAL_ROOT() / st.STAMP_REL
    except st.CanonicalRootUnresolved:
        return None
    return p.read_bytes() if p.exists() else None


@pytest.fixture(scope="module", autouse=True)
def _the_real_stamp_is_byte_identical_across_this_module():
    before = _real_stamp_bytes()
    yield
    assert _real_stamp_bytes() == before, "this test module CHANGED the real stamp file"


@pytest.fixture(autouse=True)
def _no_resolution_of_the_real_stamp(monkeypatch):
    def _refuse(start=None):
        raise AssertionError("a test resolved the REAL stamp path — monkeypatch canonical_root to a tmp root")
    monkeypatch.setattr(st, "canonical_root", _refuse)


def _plant(root: Path) -> None:
    """A COMPLETE substrate under `root`: one file per substrate dir, every curated file."""
    for d in gm.SUBSTRATE_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "data/processed/AAA_1d.csv").write_text("a,b\n1,2\n")
    (root / "data/raw/r.txt").write_text("raw")
    (root / "data/governor/seed.yml").write_text("g: 1\n")
    (root / "data/macro/VIX.parquet").write_bytes(b"vix")
    (root / "data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv").write_text("d,v\n1,2\n")
    for f in gm.SUBSTRATE_FILES:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"x")


def _aside(p: Path) -> Path:
    """Make `p` absent without deleting anything: rename it beside itself."""
    target = p.with_name(p.name + ".aside")
    p.rename(target)
    return target


# ═══════════════════════════════════════════════════════════════════════════════
# C1 — the scope: base_curve dir, the snapshot, the two honest-N files BY NAME
# ═══════════════════════════════════════════════════════════════════════════════

def honest_n_name_mismatch(pin_path: Path, manifest_names=gm.HONEST_N_FILES) -> list:
    """The C1 name lock as a value: [] when the manifest's two honest-N names equal the pin's,
    else one line per file NAMING BOTH sides (the record §2 C1: a future `--pin --replace` must
    force a manifest edit, and the failure must say which file disagrees)."""
    pin = json.loads(Path(pin_path).read_text())
    expected = {"artifact": f"data/observability/{pin['artifact']['file']}",
                "registry": f"data/observability/{pin['registry']['file']}"}
    have = set(manifest_names)
    bad = []
    for role, path in expected.items():
        if path not in have:
            bad.append(f"the pin's {role} {path} is not in gen_substrate_manifest.HONEST_N_FILES "
                       f"{sorted(have)} — a `honest_n_pin --pin --replace` must edit the manifest "
                       f"scope in the same act")
    for path in sorted(have - set(expected.values())):
        bad.append(f"HONEST_N_FILES pins {path}, which config/honest_n_pin.json does not name "
                   f"(it names {sorted(expected.values())})")
    return bad


def test_LOCK_C1_the_two_honest_N_names_equal_the_committed_pin():
    assert honest_n_name_mismatch(PIN) == []
    assert len(gm.HONEST_N_FILES) == 2
    for f in gm.HONEST_N_FILES:
        assert f in gm.SUBSTRATE_FILES
        assert f.startswith("data/observability/") and not f.endswith("/")
    assert "data/observability" not in gm.SUBSTRATE_DIRS, "pinned by NAME, never the directory"


def test_POSITIVE_CONTROL_the_name_lock_fails_on_a_planted_pin_mismatch_naming_both_files(tmp_path):
    planted = tmp_path / "pin.json"
    planted.write_text(json.dumps({"artifact": {"file": "n_effective_2099-01-01.json", "sha256": "0" * 64},
                                   "registry": {"file": "run_registry.sqlite", "sha256": "0" * 64}}))
    bad = honest_n_name_mismatch(planted)
    assert len(bad) == 2, bad
    assert any("n_effective_2099-01-01.json" in b and "artifact" in b for b in bad)
    assert any("data/observability/n_effective_2026-09-30.json" in b and "does not name" in b for b in bad)
    assert honest_n_name_mismatch(planted, manifest_names=(
        "data/observability/n_effective_2099-01-01.json", "data/observability/run_registry.sqlite")) == []


def test_LOCK_C1_the_scope_names_base_curve_the_snapshot_and_the_two_files():
    assert "data/external/base_curve" in gm.SUBSTRATE_DIRS
    assert "data/universe/delist_shares_snapshot.parquet" in gm.SUBSTRATE_FILES
    assert len(gm.SUBSTRATE_FILES) == len(set(gm.SUBSTRATE_FILES))


def test_LOCK_C1_a_file_under_base_curve_appears_in_build_manifest(tmp_path):
    _plant(tmp_path)
    (tmp_path / "data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv").write_text("curve")
    paths = [l.split("  ", 1)[1] for l in gm.build_manifest(tmp_path)]
    assert "data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv" in paths
    for f in gm.SUBSTRATE_FILES:
        assert f in paths


def test_C1_an_absent_curated_file_is_WARNED_and_skipped_before_generate_and_MISSING_after(tmp_path, capsys):
    """What `iter_substrate_files` does with a SUBSTRATE_FILES entry the host lacks (the snapshot
    does not exist until the data half runs): a WARN on stderr and no line — never an error, never
    a line for nothing. Once a manifest pins it, its absence is MISSING at verify."""
    _plant(tmp_path)
    snap = tmp_path / "data/universe/delist_shares_snapshot.parquet"
    aside = _aside(snap)
    before = gm.build_manifest(tmp_path)
    assert "WARN: curated substrate file missing" in capsys.readouterr().err
    assert not any("delist_shares_snapshot.parquet" in l for l in before)
    aside.rename(snap)
    m = tmp_path / "config/substrate_manifest.sha256"
    m.parent.mkdir(exist_ok=True)
    m.write_text("\n".join(gm.build_manifest(tmp_path)) + "\n")
    assert gm.full_verify(tmp_path, m).ok
    _aside(snap)
    res = gm.full_verify(tmp_path, m)
    assert res.missing == ["data/universe/delist_shares_snapshot.parquet"] and not res.extra and not res.changed


# ═══════════════════════════════════════════════════════════════════════════════
# C2 — the drift footer: hidden = total − shown, shown = Σ min(20, len(class))
# ═══════════════════════════════════════════════════════════════════════════════

def _drift(n_missing: int, n_extra: int, n_changed: int) -> gm.VerifyResult:
    return gm.VerifyResult(pinned=14120, host=14254,
                           missing=[f"data/raw/m{i}" for i in range(n_missing)],
                           extra=[f"data/processed/e{i}" for i in range(n_extra)],
                           changed=[f"data/macro/c{i}" for i in range(n_changed)])


def test_LOCK_C2_todays_drift_0_134_5_prints_and_114_more(capsys):
    """shown = 0 + 20 + 5 = 25; hidden = 139 − 25 = 114. The flat "− 60" footer said 79."""
    gm._print_drift(_drift(0, 134, 5))
    err = capsys.readouterr().err
    assert "  … and 114 more" in err, err
    assert "79 more" not in err
    assert err.count("  EXTRA   : ") == 20 and err.count("  CHANGED : ") == 5 and "MISSING" not in err.replace(
        "FAIL: substrate has DRIFTED", "")
    assert gm.drift_hidden(_drift(0, 134, 5)) == 114


@pytest.mark.parametrize("m, e, c, hidden", [
    (0, 25, 0, 5),        # total 25 ≤ 60: the old footer printed NOTHING while 5 were hidden
    (20, 20, 20, 0),      # every path shown: no footer
    (21, 0, 0, 1),
    (0, 0, 0, 0),
    (100, 100, 100, 240),
])
def test_LOCK_C2_the_footer_is_exactly_the_hidden_count(capsys, m, e, c, hidden):
    gm._print_drift(_drift(m, e, c))
    err = capsys.readouterr().err
    assert gm.drift_hidden(_drift(m, e, c)) == hidden
    if hidden:
        assert f"  … and {hidden} more" in err
    else:
        assert "more" not in err.split("Either restore")[0]
