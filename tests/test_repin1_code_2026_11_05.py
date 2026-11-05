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


# ═══════════════════════════════════════════════════════════════════════════════
# C3 — generate REFUSES a foreign --manifest without --stamp-root, before any write
# ═══════════════════════════════════════════════════════════════════════════════

def _fake_main(tmp_path: Path, monkeypatch) -> Path:
    """A planted MAIN tree: a complete substrate, the committed default manifest, and a stamp file
    with KNOWN bytes. `canonical_root` resolves here for the test, so a stamp written "to the main
    tree" lands in this file — exactly where the reversion of C3 would write."""
    main = tmp_path / "main"
    _plant(main)
    m = main / gm.DEFAULT_MANIFEST
    m.parent.mkdir(exist_ok=True)
    m.write_text("\n".join(gm.build_manifest(main)) + "\n")
    rec = st.make_record("PASS", "repin", None, "0" * 32,
                         {"pinned": 1, "host": 1, "missing": 0, "extra": 0, "changed": 0}, [])
    st.write_stamp("f" * 64, rec, root=main)
    monkeypatch.setattr(st, "canonical_root", lambda start=None: main)
    return main


def test_LOCK_C3_a_foreign_manifest_without_stamp_root_is_REFUSED_before_any_write(tmp_path, monkeypatch, capsys):
    main = _fake_main(tmp_path, monkeypatch)
    stamp_file = main / st.STAMP_REL
    stamp_before = stamp_file.read_bytes()
    scratch = tmp_path / "scratch"
    _plant(scratch)
    cand = tmp_path / "candidate.sha256"
    rc = gm.main(["generate", "--root", str(scratch), "--manifest", str(cand)])
    err = capsys.readouterr().err
    assert rc == 4, err
    assert err.startswith("REFUSED") and "--stamp-root" in err and "real" in err and st.STAMP_REL in err
    assert "2026-11-04" in err                                     # the hazard, named
    assert not cand.exists() and not list(tmp_path.glob("*.tmp.*")) and not list(scratch.rglob("*.tmp.*"))
    assert stamp_file.read_bytes() == stamp_before, "the real stamp file was WRITTEN"
    assert not (scratch / st.STAMP_REL).exists()
    # a worktree's OWN config/ default is foreign too: only the main tree's committed file passes
    rc = gm.main(["generate", "--root", str(scratch)])
    assert rc == 4 and "REFUSED" in capsys.readouterr().err
    assert not (scratch / gm.DEFAULT_MANIFEST).exists()
    assert stamp_file.read_bytes() == stamp_before


def test_LOCK_C3_with_stamp_root_a_candidate_manifest_PROCEEDS_and_the_real_stamp_is_untouched(
        tmp_path, monkeypatch, capsys):
    main = _fake_main(tmp_path, monkeypatch)
    stamp_before = (main / st.STAMP_REL).read_bytes()
    scratch = tmp_path / "scratch"
    _plant(scratch)
    cand = tmp_path / "candidate.sha256"
    rc = gm.main(["generate", "--root", str(scratch), "--manifest", str(cand), "--stamp-root", str(scratch)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert cand.exists() and "stamped PASS" in out.out and "by repin" in out.out
    assert st.read_stamp(st.manifest_digest(cand), root=scratch)["result"] == "PASS"
    assert (main / st.STAMP_REL).read_bytes() == stamp_before


def test_C3_the_committed_default_under_the_main_tree_still_generates_without_stamp_root(
        tmp_path, monkeypatch, capsys):
    """The director's D2 invocation (`generate` in the MAIN tree, no --stamp-root) is exactly the
    one case the refusal lets through — and it stamps the main tree's file, as before."""
    main = _fake_main(tmp_path, monkeypatch)
    rc = gm.main(["generate", "--root", str(main)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    digest = st.manifest_digest(main / gm.DEFAULT_MANIFEST)
    assert st.read_stamp(digest, root=main)["result"] == "PASS"
    assert st.read_stamp("f" * 64, root=main)["result"] == "PASS"          # the other entry survives


def test_C3_an_unresolvable_main_tree_is_a_refusal_not_a_pass(tmp_path, monkeypatch, capsys):
    def _unresolved(start=None):
        raise st.CanonicalRootUnresolved("no git here")
    monkeypatch.setattr(st, "canonical_root", _unresolved)
    scratch = tmp_path / "scratch"
    _plant(scratch)
    cand = tmp_path / "candidate.sha256"
    assert gm.main(["generate", "--root", str(scratch), "--manifest", str(cand)]) == 4
    err = capsys.readouterr().err
    assert "could not resolve the MAIN tree" in err and "--stamp-root" in err
    assert not cand.exists()


def test_C3_verify_is_not_gated_by_the_refusal(tmp_path, monkeypatch):
    """The refusal is generate's: the janitor and the build script run verify on absolute,
    non-default manifests without --stamp-root's writer (they pass --stamp-root or stamp nothing)."""
    main = _fake_main(tmp_path, monkeypatch)
    scratch = tmp_path / "scratch"
    _plant(scratch)
    cand = tmp_path / "candidate.sha256"
    cand.write_text("\n".join(gm.build_manifest(scratch)) + "\n")
    assert gm.main(["verify", "--root", str(scratch), "--manifest", str(cand), "--stamp-root", str(scratch)]) == 0
    assert gm.main(["verify", "--root", str(scratch), "--manifest", str(cand)]) == 0   # a bare verify never stamps
    assert not (scratch / st.STAMP_REL).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# C4 — build_pit_cap_history_t219.py: --write-snapshot (network, recorded) / --from-snapshot (hermetic)
# ═══════════════════════════════════════════════════════════════════════════════

import ast
import sys
import types

import pandas as pd

from scripts import build_pit_cap_history_t219 as t219

_BDAYS = pd.bdate_range("2019-01-01", "2020-12-31")


def _t219_root(tmp_path: Path) -> Path:
    """A synthetic checkout: a membership panel (AAA, BBB, CCC, DDD delisted; EEE live), price csvs
    for AAA/BBB/CCC (Close 10.0 through 2019, 20.0 through 2020), and a tiers file with one
    current-snapshot entry (ZZZ) that the recompute must leave alone."""
    root = tmp_path / "root"
    (root / "data/universe").mkdir(parents=True)
    (root / "data/processed").mkdir(parents=True)
    pd.DataFrame({"ticker": ["AAA", "BBB", "CCC", "DDD", "EEE"], "name": ["a", "b", "c", "d", "e"],
                  "sector": ["x"] * 5,
                  "included_from": pd.to_datetime(["2010-01-01"] * 5),
                  "included_until": pd.to_datetime(["2020-12-31", "2020-12-31", "2020-06-30", "2012-01-01", None]),
                  }).to_parquet(root / t219.MEMBERSHIP_REL, index=False)
    close = [10.0 if d.year == 2019 else 20.0 for d in _BDAYS]
    for t in ("AAA", "BBB", "CCC"):
        pd.DataFrame({"Date": _BDAYS, "Open": close, "Close": close, "Volume": 1}).to_csv(
            root / f"data/processed/{t}_1d.csv", index=False)
    (root / t219.TIERS_REL).write_text(json.dumps(
        {"ZZZ": {"marketCap": 5e9, "tier": "mid", "asof": "2026-06-18", "source": "fast_info"}}, indent=0))
    return root


def _install_yfinance_stub(monkeypatch, behaviour):
    """`behaviour` maps ticker -> a Series, an empty Series, or an Exception to raise; None means
    the Ticker must never be constructed (the --from-snapshot lock)."""
    stub = types.ModuleType("yfinance")
    calls = []

    class Ticker:
        def __init__(self, t):
            if behaviour is None:
                raise AssertionError(f"yfinance.Ticker({t!r}) constructed on a path that must NEVER fetch")
            self.t = t

        def get_shares_full(self, start=None):
            calls.append((self.t, start))
            r = behaviour[self.t]
            if isinstance(r, Exception):
                raise r
            return r
    stub.Ticker = Ticker
    monkeypatch.setitem(sys.modules, "yfinance", stub)
    return calls


def test_LOCK_C4_write_snapshot_records_fetched_empty_and_failed_never_a_silent_None(tmp_path, monkeypatch, capsys):
    root = _t219_root(tmp_path)
    series = pd.Series([1e9, 1e9], index=pd.DatetimeIndex(["2019-01-02", "2020-12-31"]).tz_localize("America/New_York"))
    calls = _install_yfinance_stub(monkeypatch, {"AAA": series, "BBB": pd.Series(dtype="float64"),
                                                 "CCC": RuntimeError("boom")})
    snap = tmp_path / "out" / "delist_shares_snapshot.parquet"
    rc = t219.main(["--write-snapshot", str(snap), "--root", str(root)])
    assert rc == 0, capsys.readouterr()
    assert sorted(calls) == [("AAA", "2010-01-01"), ("BBB", "2010-01-01"), ("CCC", "2010-01-01")]   # ONCE each; DDD has no price file
    long = pd.read_parquet(snap)
    assert list(long.columns) == ["ticker", "date", "shares"]
    assert long["ticker"].tolist() == ["AAA", "AAA"] and long["shares"].tolist() == [1e9, 1e9]
    assert long["date"].dt.tz is None and str(long["date"].iloc[0].date()) == "2019-01-02"
    meta = json.loads(t219.snapshot_meta_path(snap).read_text())
    assert meta["counts"] == {"fetched": 1, "empty": 1, "failed": 1}
    assert meta["cohort_delisted"] == 4 and meta["cohort_with_price"] == 3 and meta["rows"] == 2
    assert meta["written_on"] and meta["shares_start"] == "2010-01-01"
    by = {s["ticker"]: s for s in meta["statuses"]}
    assert by["AAA"]["status"] == "fetched" and by["AAA"]["rows"] == 2
    assert by["BBB"] == {"ticker": "BBB", "status": "empty", "reason": "get_shares_full returned an empty series"}
    assert by["CCC"] == {"ticker": "CCC", "status": "failed", "reason": "RuntimeError: boom"}
    assert "DDD" not in by
    assert (root / t219.TIERS_REL).read_text().startswith('{\n"ZZZ"')          # the tiers file is not touched


def test_C4_a_snapshot_with_nothing_fetched_is_written_WITH_its_reasons_and_exits_1(tmp_path, monkeypatch, capsys):
    root = _t219_root(tmp_path)
    _install_yfinance_stub(monkeypatch, {"AAA": None, "BBB": pd.Series(dtype="float64"), "CCC": OSError("down")})
    snap = tmp_path / "s.parquet"
    assert t219.main(["--write-snapshot", str(snap), "--root", str(root)]) == 1
    assert "nothing fetched" in capsys.readouterr().err
    meta = json.loads(t219.snapshot_meta_path(snap).read_text())
    assert meta["counts"] == {"fetched": 0, "empty": 2, "failed": 1}
    assert {s["ticker"]: s["reason"] for s in meta["statuses"]}["AAA"] == "get_shares_full returned None"
    assert pd.read_parquet(snap).empty


def _plant_snapshot(path: Path) -> None:
    """AAA: 1e9 shares across the whole price span; BBB: 4e8; CCC: a single point in 2012, before
    any price bar — no overlap, the wall."""
    pd.DataFrame({"ticker": ["AAA", "AAA", "BBB", "BBB", "CCC"],
                  "date": pd.to_datetime(["2019-01-02", "2020-12-31", "2019-01-02", "2020-12-31", "2012-01-01"]),
                  "shares": [1e9, 1e9, 4e8, 4e8, 7e7]}).to_parquet(path, index=False)


def test_LOCK_C4_from_snapshot_NEVER_imports_yfinance_and_reproduces_the_cap_arithmetic(tmp_path, monkeypatch, capsys):
    """The stub's Ticker RAISES if constructed; the recompute runs with it installed. The window is
    the last 12 months of overlap ending 2020-12-31 — one 2019-12-31 bar at Close 10 and every 2020
    bar at Close 20 — so the median of Close × shares is 20 × shares exactly."""
    root = _t219_root(tmp_path)
    _install_yfinance_stub(monkeypatch, None)
    snap = tmp_path / "delist_shares_snapshot.parquet"
    _plant_snapshot(snap)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(t219.tempfile, "gettempdir", lambda: str(scratch))
    tiers_before = (root / t219.TIERS_REL).read_bytes()
    rc = t219.main(["--from-snapshot", str(snap), "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0, out
    written = [p for p in scratch.iterdir()]
    assert len(written) == 1 and written[0].name.startswith("market_cap_tiers_from_snapshot_"), written
    assert str(written[0]) in out and "SCRATCH default" in out
    new = json.loads(written[0].read_text())
    assert new["AAA"] == {"marketCap": 2e10, "tier": "large", "asof": "2020-12-31", "source": "delist_shares"}
    assert new["BBB"] == {"marketCap": 8e9, "tier": "mid", "asof": "2020-12-31", "source": "delist_shares"}
    assert "CCC" not in new                                                  # the wall: no overlap, left null
    assert new["ZZZ"] == {"marketCap": 5e9, "tier": "mid", "asof": "2026-06-18", "source": "fast_info"}
    assert (root / t219.TIERS_REL).read_bytes() == tiers_before, "the real tiers file was written"
    assert "'resolved': 2" in out and "'wall': 1" in out and "'new_vs_current': 2" in out
    # --out names the target explicitly
    explicit = tmp_path / "explicit.json"
    assert t219.main(["--from-snapshot", str(snap), "--root", str(root), "--out", str(explicit)]) == 0
    assert json.loads(explicit.read_text())["AAA"]["marketCap"] == 2e10
    assert (root / t219.TIERS_REL).read_bytes() == tiers_before


def test_LOCK_C4_the_only_yfinance_import_is_inside_the_fetch_and_the_bare_call_is_retired(monkeypatch, capsys):
    tree = ast.parse(Path(t219.__file__).read_text())
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
               and any("yfinance" in (a.name if isinstance(n, ast.Import) else (n.module or "")) for a in n.names)]
    owners = []
    for n in imports:
        owner = next(f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
                     and f.lineno <= n.lineno <= f.end_lineno)
        owners.append(owner)
    assert owners == ["fetch_shares_snapshot"], owners
    assert "yf" not in vars(t219) and "yfinance" not in vars(t219)
    _install_yfinance_stub(monkeypatch, None)
    with pytest.raises(SystemExit) as e:                                      # no mode = usage error, no fetch
        t219.main([])
    assert e.value.code == 2
    with pytest.raises(SystemExit):
        t219.main(["--write-snapshot", "x", "--from-snapshot", "y"])
    assert not hasattr(t219, "OUT")                                           # the in-place real-file writer is gone


def test_C4_the_tier_arithmetic_is_unchanged_and_the_meta_sits_beside_the_parquet():
    assert t219.TIERS == [(200e9, "mega"), (10e9, "large"), (2e9, "mid"), (300e6, "small")]
    assert [t219._tier(c) for c in (200e9, 199e9, 10e9, 9e9, 2e9, 1e9, 300e6, 1.0)] == \
        ["mega", "large", "large", "mid", "mid", "small", "small", "micro"]
    assert t219.snapshot_meta_path(Path("x/delist_shares_snapshot.parquet")) == Path("x/delist_shares_snapshot.meta.json")
    assert t219.SHARES_START == "2010-01-01"
    # the arithmetic on a hand-checkable case: a single shares point ends the window at that point
    px = pd.DataFrame({"Close": [1.0, 2.0, 3.0, 4.0]}, index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]))
    sh = pd.Series([100.0, 100.0], index=pd.DatetimeIndex(["2020-01-02", "2020-01-02"]))   # a duplicated date
    cap, end = t219.cap_at_delist(px, sh)
    assert cap == 200.0 and str(end.date()) == "2020-01-02"                   # only 2020-01-02 has shares: 2 × 100
    assert t219.cap_at_delist(px, pd.Series([5.0], index=pd.DatetimeIndex(["2019-01-01"]))) is None   # no overlap


# ═══════════════════════════════════════════════════════════════════════════════
# C6 — the image carries the two pinned honest-N files and verifies the pin at build
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import subprocess

import core.measurement.mbl_gate as mbl
from scripts.honest_n_pin import main as pin_main, write_pin

DOCKERFILE = REPO / "Dockerfile.backtest"
DOCKERIGNORE = REPO / ".dockerignore"
BUILD_SH = REPO / "scripts" / "build_backtest_image.sh"
REAL_OBS = REPO / "data" / "observability"


def _pin_names() -> dict:
    pin = json.loads(PIN.read_text())
    return {"artifact": pin["artifact"]["file"], "registry": pin["registry"]["file"]}


def _synthetic_pair(d: Path):
    """A pinned pair the gate accepts (the honest_n tests' shape): a 231-row registry and a ρ̄ artifact."""
    import sqlite3
    reg = d / "run_registry.sqlite"
    c = sqlite3.connect(reg)
    c.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY)")
    c.executemany("INSERT INTO runs VALUES (?)", [(f"r{i}",) for i in range(231)])
    c.commit(); c.close()
    art = d / "n_effective_2026-09-30.json"
    art.write_text(json.dumps({"rho_bar": 0.43, "onc_compression": 0.16,
                               "gate_inputs": {"rho_bar": 0.43, "onc_compression": 0.16}}))
    pin = d / "honest_n_pin.json"
    write_pin(art.name, artifact_dir=d, db_path=reg, pin_path=pin)
    return reg, art, pin


def _image_like(src_dir: Path, names: dict, image: Path) -> Path:
    """What the Dockerfile's two COPY lines produce: exactly the two files under
    <image>/data/observability/, nothing else from the source directory."""
    obs = image / "data" / "observability"
    obs.mkdir(parents=True)
    for n in names.values():
        shutil.copyfile(src_dir / n, obs / n)
    return obs


def _verify_at(obs: Path, names: dict, pin: Path, monkeypatch) -> int:
    """`python -m scripts.honest_n_pin --verify` against `obs`: the real main(), its three
    defaults redirected the way tests/test_honest_n_pin.py redirects them."""
    monkeypatch.setattr(mbl, "DEFAULT_ARTIFACT_DIR", obs)
    monkeypatch.setattr(mbl, "DEFAULT_DB_PATH", obs / names["registry"])
    monkeypatch.setattr(mbl, "DEFAULT_PIN_PATH", pin)
    return pin_main(["--verify"])


def _plant_byte(p: Path) -> None:
    b = bytearray(p.read_bytes())
    b[len(b) // 2] ^= 0x01
    p.write_bytes(bytes(b))


def test_LOCK_C6_verify_passes_on_the_copied_pair_and_exits_3_after_one_planted_byte(tmp_path, monkeypatch, capsys):
    src = tmp_path / "host"
    src.mkdir()
    _, _, pin = _synthetic_pair(src)
    names = {"artifact": "n_effective_2026-09-30.json", "registry": "run_registry.sqlite"}
    obs = _image_like(src, names, tmp_path / "image")
    assert sorted(x.name for x in obs.iterdir()) == sorted(names.values())
    assert _verify_at(obs, names, pin, monkeypatch) == 0 and "PIN OK" in capsys.readouterr().out
    for role in ("artifact", "registry"):                      # one byte in either file fails the build step
        good = (obs / names[role]).read_bytes()
        _plant_byte(obs / names[role])
        assert _verify_at(obs, names, pin, monkeypatch) == 3, role
        assert "PIN INVALID" in capsys.readouterr().out
        (obs / names[role]).write_bytes(good)
    assert _verify_at(obs, names, pin, monkeypatch) == 0


def test_C6_the_REAL_pin_verifies_the_REAL_files_copied_as_the_image_copies_them_and_a_planted_byte_fails(
        tmp_path, monkeypatch, capsys):
    """The build step's own inputs: the committed pin against copies of the two real files. Skipped
    where the files are not on the host (a bare CI checkout has no data/)."""
    names = _pin_names()
    missing = [n for n in names.values() if not (REAL_OBS / n).is_file()]
    if missing:
        pytest.skip(f"the pinned honest-N files are not on this host: {missing}")
    obs = _image_like(REAL_OBS, names, tmp_path / "image")
    assert _verify_at(obs, names, PIN, monkeypatch) == 0, capsys.readouterr().out
    _plant_byte(obs / names["registry"])
    assert _verify_at(obs, names, PIN, monkeypatch) == 3
    assert "run registry" in capsys.readouterr().out


def test_C6_the_exact_build_command_runs_on_this_tree():
    """`python -m scripts.honest_n_pin --verify` as the Dockerfile runs it (a subprocess, the real
    defaults): PIN OK where the two files are on the host; skipped otherwise."""
    names = _pin_names()
    if any(not (REAL_OBS / n).is_file() for n in names.values()):
        pytest.skip("the pinned honest-N files are not on this host")
    r = subprocess.run([sys.executable, "-m", "scripts.honest_n_pin", "--verify"], cwd=REPO,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "PIN OK" in r.stdout, r.stdout + r.stderr


def test_LOCK_C6_TEXT_the_image_copies_exactly_the_pins_two_files_by_name_and_verifies_before_the_registry_check():
    """A text check, labelled as such: the subject IS the Dockerfile. The two COPY lines name the
    pin's files (so a `--pin --replace` must edit the Dockerfile too), sit after the governor COPY
    and before the sync_edge_registry check, the verify RUN follows them, and the later mkdir -p
    cannot clobber them. The directory is never COPYd."""
    df = DOCKERFILE.read_text()
    names = _pin_names()
    copies = [f"COPY --chown=archondex:archondex data/observability/{n} ./data/observability/{n}" for n in names.values()]
    for line in copies:
        assert df.count(line) == 1, line
    verify = "RUN python -m scripts.honest_n_pin --verify"
    assert df.count(verify) == 1
    governor = "COPY --chown=archondex:archondex data/governor/ ./data/governor/"
    registry_check = "RUN python scripts/sync_edge_registry.py --check"
    mkdir = "RUN mkdir -p /app/data/trade_logs /app/data/observability"
    order = [df.index(governor), min(df.index(c) for c in copies), max(df.index(c) for c in copies),
             df.index(verify), df.index(registry_check), df.index(mkdir)]
    assert order == sorted(order), order
    assert "data/observability/ ./data/observability/" not in df            # by name, never the directory
    assert "substrate-pinned" in df or "SUBSTRATE_FILES" in df                # the comment says why the S3 sync carries them


def test_LOCK_C6_TEXT_dockerignore_re_includes_exactly_the_two_files_and_the_build_script_stages_the_new_scope():
    names = _pin_names()
    di = DOCKERIGNORE.read_text().splitlines()
    assert "data/observability/" in di
    excl = di.index("data/observability/")
    bangs = [l for l in di if l.startswith("!data/observability/")]
    assert sorted(bangs) == sorted(f"!data/observability/{n}" for n in names.values()), bangs
    assert all(di.index(b) > excl for b in bangs)                             # the exception follows the exclusion
    sh = BUILD_SH.read_text()
    for n in names.values():
        assert f"data/observability/{n}" in sh, n
    assert '"data/external/base_curve" "$STAGE/data/external/"' in sh
    for f in gm.SUBSTRATE_FILES:                                               # every curated file is staged — derived
        assert f in sh, f                                                      # from the scope (reviewer F1, 2026-11-05)
    for d in gm.SUBSTRATE_DIRS:                                                # every substrate dir is staged
        assert d.split("/", 1)[1].split("/")[0] in sh or d in sh, d


def test_LOCK_D5_TEXT_the_image_registry_check_targets_the_ANCHOR_registry_the_cell_executes_from():
    """2026-11-05: run_isolated restores data/governor/ from _isolated_anchor/ on entry, and the live
    edges.yml is not baked (T-133), so the build-time check must read the anchor's registry — the one
    the container runs with — or it certifies an absent file."""
    df = DOCKERFILE.read_text()
    lines = [l for l in df.splitlines() if l.startswith("RUN python scripts/sync_edge_registry.py")]
    assert lines == ["RUN python scripts/sync_edge_registry.py --check --registry data/governor/_isolated_anchor/edges.yml"], lines
    sh = BUILD_SH.read_text()
    assert "--exclude='/governor/edges.yml'" in sh                                # T-133 still excludes the live file
    assert "data/governor/_isolated_anchor/edges.yml" in (ROOT / "config/substrate_manifest.sha256").read_text()  # the anchor is pinned
