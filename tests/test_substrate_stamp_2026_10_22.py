"""The substrate VERIFY STAMP — B's half of the campaign submit gate (2026-10-22).

The agreed interface is §7 of `docs/Sources/proposal_substrate_verify_stamp_janitor_2026-10-15.md`;
these are P5's locks on B's side — drift, clean, fail-closed (with a positive control),
isolation, atomicity, unknown-schema and unreadable reads — plus the two-writer rule, the
freshness rule the gate shares, and the janitor wiring. Every lock DRIVES THE REAL ENTRYPOINT:
`janitor_nightly.check_substrate_verify()` running the real `gen_substrate_manifest.py` CLI in a
subprocess against a planted, COMPLETE substrate; `write_stamp` / `read_stamp` on a real file.
No text assertion stands in for execution (the 2026-09-14 lesson). Each lock was proven by
REVERSION — the guarded line removed, the test run red, the file restored — and the record of
each reversion is in the unit's session report.

Nothing here touches the real stamp: every run points `--stamp-root` (via `jn.CANON`) at a
tmp root, and the janitor's `MANIFEST` is the planted one.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core import substrate_stamp as st
from scripts import gen_substrate_manifest as gm
from scripts import janitor_nightly as jn

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
CLI = REPO / "scripts" / "gen_substrate_manifest.py"
OTHER = "f" * 64                               # a digest no manifest will ever have


# ── a planted, COMPLETE substrate ───────────────────────────────────────────────

def _plant(root: Path) -> Path:
    """All four substrate dirs and both curated files, so `full_verify` can run COMPLETELY,
    and the manifest the generator's own `build_manifest()` writes for them."""
    for d in gm.SUBSTRATE_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "data/universe").mkdir(parents=True, exist_ok=True)
    (root / "data/processed/AAA_1d.csv").write_text("a,b\n1,2\n")
    (root / "data/raw/r.txt").write_text("raw")
    (root / "data/governor/seed.yml").write_text("g: 1\n")
    (root / "data/macro/VIX.parquet").write_bytes(b"vix")
    for f in gm.SUBSTRATE_FILES:
        (root / f).write_bytes(b"x")
    m = root / "config/substrate_manifest.sha256"
    m.parent.mkdir(exist_ok=True)
    m.write_text("\n".join(gm.build_manifest(root)) + "\n")
    return m


def _janitor_on(monkeypatch, root: Path, manifest: Path) -> None:
    """Point the REAL check at the planted tree: data + stamp under `root`, manifest `manifest`."""
    monkeypatch.setattr(jn, "CANON", root)
    monkeypatch.setattr(jn, "MANIFEST", manifest)


def _record_block(text: str, digest: str) -> str:
    """The raw lines of one digest's record as written (indent=1 → records sit at two spaces)."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(f'  "{digest}": {{'))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("  }"))
    return "\n".join(lines[start:end + 1]).rstrip(",")


# ── P5 B-1: clean ───────────────────────────────────────────────────────────────

def test_LOCK_clean_an_exact_match_stamps_PASS_and_the_check_is_GREEN(tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    digest = st.manifest_digest(m)
    c = jn.check_substrate_verify()
    assert c.name == "substrate_verify" and c.ok and c.status == "PASS", c.detail
    assert digest[:12] in c.detail and "janitor_nightly" in c.detail
    rec = st.read_stamp(digest, root=tmp_path)
    assert rec["result"] == "PASS" and rec["writer"] == "janitor_nightly"
    assert rec["counts"] == {"pinned": 6, "host": 6, "missing": 0, "extra": 0, "changed": 0}
    assert rec["first_paths"] == [] and rec["error"] is None
    assert rec["s3_prefix_md5"] == hashlib.md5(m.read_bytes()).hexdigest()
    assert rec["tree_head"] is None                  # a scratch tree is no checkout: stated, not invented
    assert st.freshness_verdict(rec) is None


# ── P5 B-2: drift ───────────────────────────────────────────────────────────────

def test_LOCK_drift_stamps_FAIL_with_the_TRUE_counts_and_the_row_names_the_fix(tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    (tmp_path / "data/processed/AAA_1d.csv").write_text("a,b\n1,3\n")      # one byte changed
    (tmp_path / "data/macro/NEW.parquet").write_bytes(b"new")               # one extra
    (tmp_path / "data/raw/r.txt").unlink()                                  # one missing
    digest = st.manifest_digest(m)
    c = jn.check_substrate_verify()
    assert not c.ok and c.status == "FAIL" and c.mechanical is False, c.detail
    assert "MISSING 1 · EXTRA 1 · CHANGED 1" in c.detail
    assert "MISSING data/raw/r.txt" in c.detail and "CHANGED data/processed/AAA_1d.csv" in c.detail
    assert "re-pin" in c.detail and "`scripts/gen_substrate_manifest.py generate`" in c.detail
    assert "every campaign submit refuses" in c.detail
    assert "B-7" not in c.detail                     # not the June-18 manifest: not that blocker
    rec = st.read_stamp(digest, root=tmp_path)
    assert rec["result"] == "FAIL"
    assert rec["counts"] == {"pinned": 6, "host": 6, "missing": 1, "extra": 1, "changed": 1}
    assert rec["first_paths"] == ["MISSING data/raw/r.txt", "CHANGED data/processed/AAA_1d.csv",
                                  "EXTRA data/macro/NEW.parquet"]


def test_the_B7_blocker_sentence_is_said_ONLY_for_the_June_18_manifest(tmp_path, monkeypatch):
    """The first nightly's RED is the known B-7 blocker, and the row must say so — but only
    while the manifest it fails on IS that pin. Later drift is new drift."""
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    (tmp_path / "data/processed/AAA_1d.csv").write_text("drifted")
    assert jn.PRE_REPIN1_MANIFEST_SHA256 == \
        "4b34ea8206e7e4191b13d4053b6f44e34c56a3fb1fd7a5c24d4413a684395b53"
    monkeypatch.setattr(jn, "PRE_REPIN1_MANIFEST_SHA256", st.manifest_digest(m))
    c = jn.check_substrate_verify()
    assert c.status == "FAIL" and "KNOWN B-7 blocker: re-pin #1" in c.detail


# ── P5 B-3: fail-closed, with a positive control FIRST ──────────────────────────

@pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 directories")
def test_LOCK_fail_closed_an_unreadable_dir_is_ERROR_never_PASS_never_a_FAIL_of_partial_counts(
        tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    digest = st.manifest_digest(m)
    assert jn.check_substrate_verify().status == "PASS"            # positive control: it CAN pass
    raw = tmp_path / "data/raw"
    raw.chmod(0)
    try:
        c = jn.check_substrate_verify()
    finally:
        raw.chmod(0o755)
    assert c.status == "FAIL" and c.detail.startswith("ERROR"), c.detail
    assert "could not run" in c.detail and "every campaign submit refuses" in c.detail
    rec = st.read_stamp(digest, root=tmp_path)
    assert rec["result"] == "ERROR" and rec["counts"] is None
    assert "cannot walk" in rec["error"] and "data/raw" in rec["error"]
    assert "MISSING" not in c.detail                # an unreadable dir is NOT "1 missing"


def test_LOCK_fail_closed_a_missing_substrate_dir_is_ERROR(tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    os.rename(tmp_path / "data/macro", tmp_path / "data/macro_gone")
    c = jn.check_substrate_verify()
    rec = st.read_stamp(st.manifest_digest(m), root=tmp_path)
    assert c.status == "FAIL" and c.detail.startswith("ERROR")
    assert rec["result"] == "ERROR" and "data/macro" in rec["error"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 directories")
def test_LOCK_fail_closed_the_CLI_itself_stamps_ERROR_and_exits_3(tmp_path):
    """The CLI's own guard, separately from the janitor's fallback: a crash inside the verify
    becomes an ERROR stamp written BY THE VERIFY, exit 3 — not a traceback and exit 1."""
    m = _plant(tmp_path)
    raw = tmp_path / "data/raw"
    raw.chmod(0)
    try:
        r = subprocess.run([PY, str(CLI), "verify", "--root", str(tmp_path), "--manifest", str(m),
                            "--stamp-writer", "janitor_nightly", "--stamp-root", str(tmp_path)],
                           capture_output=True, text=True, timeout=120)
    finally:
        raw.chmod(0o755)
    assert r.returncode == 3, r.stderr
    assert "Traceback" not in r.stderr and "ERROR: verify could not run" in r.stderr
    rec = st.read_stamp(st.manifest_digest(m), root=tmp_path)
    assert rec["result"] == "ERROR" and rec["writer"] == "janitor_nightly"


def test_LOCK_fail_closed_a_verify_that_DIES_without_stamping_gets_an_ERROR_stamp_from_the_janitor(
        tmp_path, monkeypatch):
    """A last PASS left standing after a crashed nightly is the dead-clock class the stamp
    exists to close: the janitor overwrites it with ERROR when the verify wrote nothing."""
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    digest = st.manifest_digest(m)
    old = st.make_record("PASS", "janitor_nightly", None, "0" * 32,
                         {"pinned": 6, "host": 6, "missing": 0, "extra": 0, "changed": 0}, [],
                         verified_at=st.utc_now_iso(datetime.now(timezone.utc) - timedelta(hours=1)))
    st.write_stamp(digest, old, root=tmp_path)
    monkeypatch.setattr(jn, "_run", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 1, "", "Traceback (most recent call last):\n  ...\nMemoryError: boom\n"))
    c = jn.check_substrate_verify()
    assert c.status == "FAIL" and "ERROR — the verify exited 1 without writing a stamp" in c.detail
    assert "MemoryError: boom" in c.detail and "stamp ERROR written by the janitor" in c.detail
    rec = st.read_stamp(digest, root=tmp_path)
    assert rec["result"] == "ERROR" and rec["counts"] is None and "MemoryError" in rec["error"]


def test_LOCK_fail_closed_a_TIMEOUT_is_an_ERROR_stamp(tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)

    def _hang(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setattr(jn, "_run", _hang)
    c = jn.check_substrate_verify()
    assert c.status == "FAIL" and "timed out" in c.detail
    rec = st.read_stamp(st.manifest_digest(m), root=tmp_path)
    assert rec["result"] == "ERROR" and "timed out" in rec["error"]


def test_no_manifest_is_ERROR_with_nothing_stamped(tmp_path, monkeypatch):
    _janitor_on(monkeypatch, tmp_path, tmp_path / "config/substrate_manifest.sha256")
    c = jn.check_substrate_verify()
    assert c.status == "FAIL" and c.detail.startswith("ERROR — no manifest")
    assert not (tmp_path / st.STAMP_REL).exists()


# ── P5 B-4: isolation ───────────────────────────────────────────────────────────

def test_LOCK_isolation_another_digests_entry_survives_BYTE_IDENTICAL(tmp_path, monkeypatch):
    m = _plant(tmp_path)
    _janitor_on(monkeypatch, tmp_path, m)
    other = st.make_record("PASS", "repin", "a" * 40, "b" * 32,
                           {"pinned": 3, "host": 3, "missing": 0, "extra": 0, "changed": 0}, [])
    p = st.write_stamp(OTHER, other, root=tmp_path)
    before = p.read_text()
    (tmp_path / "data/processed/AAA_1d.csv").write_text("drifted")
    assert jn.check_substrate_verify().status == "FAIL"           # a FAIL stamped for THIS digest
    after = p.read_text()
    assert _record_block(after, OTHER) == _record_block(before, OTHER)
    assert st.read_stamp(OTHER, root=tmp_path) == other
    assert st.read_stamp(st.manifest_digest(m), root=tmp_path)["result"] == "FAIL"


# ── P5 B-5: atomicity ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("fault", ["fsync", "replace"])
def test_LOCK_atomicity_a_torn_write_leaves_the_previous_stamp_readable_and_no_temp_file(
        tmp_path, monkeypatch, fault):
    good = st.make_record("PASS", "repin", None, "0" * 32,
                          {"pinned": 1, "host": 1, "missing": 0, "extra": 0, "changed": 0}, [])
    p = st.write_stamp(OTHER, good, root=tmp_path)
    before = p.read_bytes()

    def _boom(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(st.os, fault, _boom)
    with pytest.raises(OSError):
        st.write_stamp("e" * 64, good, root=tmp_path)
    monkeypatch.undo()
    assert p.read_bytes() == before
    assert sorted(x.name for x in p.parent.iterdir()) == [p.name]       # no temp file left
    assert st.read_stamp(OTHER, root=tmp_path) == good
    assert st.read_stamp("e" * 64, root=tmp_path) is None


# ── P5 B-6/7: unknown-schema and unreadable reads ───────────────────────────────

def test_LOCK_unknown_schema_is_REFUSED_as_StampSchemaUnknown_a_StampUnreadable(tmp_path):
    p = tmp_path / st.STAMP_REL
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"schema": "substrate_verify_stamp/v2", "stamps": {}}))
    with pytest.raises(st.StampSchemaUnknown) as e:
        st.read_stamp(OTHER, root=tmp_path)
    assert isinstance(e.value, st.StampUnreadable) and "v2" in str(e.value)
    p.write_text(json.dumps({"schema": 1, "stamps": {}}))                  # the §1 draft form
    with pytest.raises(st.StampSchemaUnknown):
        st.read_stamp(OTHER, root=tmp_path)


@pytest.mark.parametrize("payload, why", [
    (b"\x00\xffnot json", "unparseable bytes"),
    (b"[]", "top level not an object"),
    (json.dumps({"schema": st.SCHEMA, "stamps": []}).encode(), "stamps not an object"),
    (json.dumps({"schema": st.SCHEMA, "stamps": {"short": {}}}).encode(), "a non-digest key"),
    (json.dumps({"schema": st.SCHEMA, "stamps": {OTHER: {
        "result": "PASS", "verified_at": "2026-10-22T00:00:00Z", "writer": "janitor_nightly",
        "tree_head": None, "s3_prefix_md5": None, "error": None, "first_paths": [],
        "counts": {"pinned": 2, "host": 2, "missing": 0, "extra": 0, "changed": 1}}}}).encode(),
     "PASS contradicting its own counts"),
    (json.dumps({"schema": st.SCHEMA, "stamps": {OTHER: {
        "result": "ERROR", "verified_at": "2026-10-22T00:00:00Z", "writer": "janitor_nightly",
        "tree_head": None, "s3_prefix_md5": None, "error": "x", "first_paths": [],
        "counts": {"pinned": 0, "host": 0, "missing": 0, "extra": 0, "changed": 0}}}}).encode(),
     "ERROR carrying fabricated zero counts"),
    (json.dumps({"schema": st.SCHEMA, "stamps": {OTHER: {
        "result": "PASS", "verified_at": "2026-10-22T00:00:00Z", "writer": "submit",
        "tree_head": None, "s3_prefix_md5": None, "error": None, "first_paths": [],
        "counts": {"pinned": 2, "host": 2, "missing": 0, "extra": 0, "changed": 0}}}}).encode(),
     "a writer that is not one of the two"),
    (json.dumps({"schema": st.SCHEMA, "stamps": {OTHER: {
        "result": "PASS", "verified_at": "2026-10-22 00:00", "writer": "repin",
        "tree_head": None, "s3_prefix_md5": None, "error": None, "first_paths": [],
        "counts": {"pinned": 2, "host": 2, "missing": 0, "extra": 0, "changed": 0}}}}).encode(),
     "an unparseable verified_at"),
])
def test_LOCK_unreadable_is_a_TYPED_error_never_absent_and_fine(tmp_path, payload, why):
    p = tmp_path / st.STAMP_REL
    p.parent.mkdir(parents=True)
    p.write_bytes(payload)
    with pytest.raises(st.StampUnreadable):
        st.read_stamp(OTHER, root=tmp_path)


def test_absent_is_None_for_no_file_and_for_another_digest_only(tmp_path):
    assert st.read_stamp(OTHER, root=tmp_path) is None
    good = st.make_record("FAIL", "repin", None, None,
                          {"pinned": 2, "host": 2, "missing": 0, "extra": 0, "changed": 1},
                          ["CHANGED data/x"])
    st.write_stamp("e" * 64, good, root=tmp_path)
    assert st.read_stamp(OTHER, root=tmp_path) is None
    assert st.read_stamp("e" * 64, root=tmp_path) == good


def test_a_writer_cannot_build_a_self_contradicting_record_either():
    zero = {"pinned": 1, "host": 1, "missing": 0, "extra": 0, "changed": 0}
    with pytest.raises(st.StampUnreadable):
        st.make_record("PASS", "repin", None, None, {**zero, "extra": 2}, [])
    with pytest.raises(st.StampUnreadable):
        st.make_record("FAIL", "repin", None, None, zero, [])
    with pytest.raises(st.StampUnreadable):
        st.make_record("ERROR", "repin", None, None, zero, [], error="x")
    with pytest.raises(st.StampUnreadable):
        st.make_record("ERROR", "repin", None, None, None, [])            # ERROR must say what
    with pytest.raises(st.StampUnreadable):
        st.make_record("PASS", "submit", None, None, zero, [])
    assert st.WRITERS == ("janitor_nightly", "repin")


def test_an_unreadable_existing_file_is_set_aside_never_deleted_and_the_writer_recovers(tmp_path, capsys):
    p = tmp_path / st.STAMP_REL
    p.parent.mkdir(parents=True)
    p.write_bytes(b"{torn")
    good = st.make_record("PASS", "repin", None, None,
                          {"pinned": 1, "host": 1, "missing": 0, "extra": 0, "changed": 0}, [])
    st.write_stamp(OTHER, good, root=tmp_path)
    aside = [x for x in p.parent.iterdir() if ".unreadable." in x.name]
    assert len(aside) == 1 and aside[0].read_bytes() == b"{torn"
    assert st.read_stamp(OTHER, root=tmp_path) == good
    assert "set aside" in capsys.readouterr().err


# ── P3 (d), shared: freshness ───────────────────────────────────────────────────

def test_freshness_is_48h_stale_and_FUTURE_DATED_are_refused_naming_which():
    assert st.FRESHNESS == timedelta(hours=48)
    now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    counts = {"pinned": 1, "host": 1, "missing": 0, "extra": 0, "changed": 0}

    def rec(delta):
        return st.make_record("PASS", "repin", None, None, counts, [],
                              verified_at=st.utc_now_iso(now + delta))
    assert st.freshness_verdict(rec(timedelta(hours=-47)), now) is None
    assert st.freshness_verdict(rec(timedelta(minutes=2)), now) is None       # within skew
    stale = st.freshness_verdict(rec(timedelta(hours=-49)), now)
    assert stale.startswith("stale") and "relay_gap" in stale and "49.0 h" in stale
    future = st.freshness_verdict(rec(timedelta(minutes=10)), now)
    assert future.startswith("future-dated") and "extend its own freshness" in future
    assert st.freshness_verdict(rec(timedelta(0)), now) is None


def test_verified_at_is_UTC_Z_and_non_UTC_input_is_refused():
    assert st.utc_now_iso(datetime(2026, 10, 23, 8, 5, 12, tzinfo=timezone.utc)) == "2026-10-23T08:05:12Z"
    assert st.parse_verified_at("2026-10-23T08:05:12Z") == st.parse_verified_at("2026-10-23T08:05:12+00:00")
    for bad in ("2026-10-23T08:05:12", "2026-10-23T08:05:12+02:00", "", None):
        with pytest.raises(ValueError):
            st.parse_verified_at(bad)


# ── P1: where and identity ──────────────────────────────────────────────────────

def test_canonical_root_resolves_the_MAIN_tree_from_any_worktree_and_FAILS_CLOSED_otherwise(
        tmp_path, monkeypatch):
    main = st.canonical_root()
    assert (main / "data").is_dir() and (main / ".git").exists()
    assert st.stamp_path() == main / "data/state/substrate_verify_stamp.json"
    with pytest.raises(st.CanonicalRootUnresolved):
        st.canonical_root(tmp_path)                      # not a checkout: no invented location
    monkeypatch.setattr(st.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("no git")))
    with pytest.raises(st.CanonicalRootUnresolved):     # never "degrade to ROOT" (unlike the ledger)
        st.canonical_root()


def test_manifest_digest_is_sha256_of_the_bytes_and_the_md5_is_recorded_beside_it_never_the_key(tmp_path):
    m = _plant(tmp_path)
    assert st.manifest_digest(m) == hashlib.sha256(m.read_bytes()).hexdigest()
    assert st.manifest_s3_prefix_md5(m) == hashlib.md5(m.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        st.read_stamp(st.manifest_s3_prefix_md5(m), root=tmp_path)       # an md5 is not a key
    with pytest.raises(OSError):
        st.manifest_digest(tmp_path / "absent")                         # never a digest of nothing


# ── R2: the re-pin step, and the two-writer rule ────────────────────────────────

def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(CLI), *args], capture_output=True, text=True, timeout=120)


def test_LOCK_generate_stamps_PASS_as_repin_after_its_OWN_full_verify(tmp_path):
    _plant(tmp_path)
    m = tmp_path / "config/substrate_manifest.sha256"
    m.unlink()
    r = _cli("generate", "--root", str(tmp_path), "--stamp-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert "stamped PASS" in r.stdout and "by repin" in r.stdout and "OK: re-pin verified" in r.stdout
    digest = st.manifest_digest(m)
    doc = json.loads((tmp_path / st.STAMP_REL).read_text())
    assert doc["schema"] == st.SCHEMA and list(doc["stamps"]) == [digest]
    rec = st.read_stamp(digest, root=tmp_path)
    assert rec["result"] == "PASS" and rec["writer"] == "repin"
    assert rec["counts"] == {"pinned": 6, "host": 6, "missing": 0, "extra": 0, "changed": 0}
    assert rec["s3_prefix_md5"] == hashlib.md5(m.read_bytes()).hexdigest()


def test_a_bare_verify_NEVER_writes_the_stamp_and_repin_is_not_a_verify_writer(tmp_path):
    m = _plant(tmp_path)
    r = _cli("verify", "--root", str(tmp_path), "--manifest", str(m), "--stamp-root", str(tmp_path))
    assert r.returncode == 0 and "OK: substrate matches" in r.stdout
    assert not (tmp_path / st.STAMP_REL).exists()
    r = _cli("verify", "--root", str(tmp_path), "--manifest", str(m), "--stamp-writer", "repin")
    assert r.returncode == 2 and "invalid choice" in r.stderr


def test_verify_exit_codes_are_0_clean_1_drift_2_no_manifest(tmp_path):
    m = _plant(tmp_path)
    assert _cli("verify", "--root", str(tmp_path), "--manifest", str(m)).returncode == 0
    (tmp_path / "data/macro/VIX.parquet").write_bytes(b"moved")
    r = _cli("verify", "--root", str(tmp_path), "--manifest", str(m))
    assert r.returncode == 1 and "CHANGED : data/macro/VIX.parquet" in r.stderr
    assert _cli("verify", "--root", str(tmp_path), "--manifest", "nope.sha256").returncode == 2


# ── the janitor wiring ──────────────────────────────────────────────────────────

def test_the_janitor_runs_the_check_and_it_is_never_mechanical(monkeypatch):
    assert "check_substrate_verify()" in inspect.getsource(jn.run_checks)
    for name in [n for n in dir(jn) if n.startswith("check_")]:
        label = name[len("check_"):]
        monkeypatch.setattr(jn, name, lambda label=label: jn.Check(label, True, "stub"))
    assert "substrate_verify" in [c.name for c in jn.run_checks()]
    assert "mechanical=True" not in inspect.getsource(jn.check_substrate_verify)


def test_the_stamp_is_registered_in_BOTH_censuses_with_a_reason():
    from core.durability_census import REGISTRY, assert_durability
    from paper_trader.clock_census import EXEMPT
    rec = next(r for r in REGISTRY if r.path == st.STAMP_REL)
    assert rec.writer == "core/substrate_stamp.py" and rec.venue == "local" and len(rec.reason) > 100
    assert assert_durability().ok
    assert "FRESHNESS" in EXEMPT[st.STAMP_REL] and "48 h" in EXEMPT[st.STAMP_REL]
