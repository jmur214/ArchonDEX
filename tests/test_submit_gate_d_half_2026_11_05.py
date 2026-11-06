"""D's half of the campaign submit gate — the locks (2026-11-05).

The agreed interface is §7 of `docs/Sources/proposal_substrate_verify_stamp_janitor_2026-10-15.md`
(P2 the committed-manifest check, P3 the refusal order, P5 D's locks) and the ruled design in
`docs/State/health_check.md` (the HIGH row "The campaign submit gate checks only that the anchor
KEYS exist": `config/anchors.json`, the gate's order, both digests named on a mismatch). Every lock
DRIVES THE REAL `scripts.submit_arms_campaign.enforce_substrate_gate` (or `main()` under
`--dry-run`, or the real `anchors_registry.py` CLI) on a PLANTED tree: a tmp git repo with a
committed `config/substrate_manifest.sha256`, a stamp planted through the real `write_stamp`, a
`config/anchors.json` COMMITTED in that repo (review F3: a submit honours only a committed
registry). No text assertion stands in for execution. Each lock was proven by REVERSION
(the step monkeypatched out in-process, the lock run red) — the reversion list is in the unit's
report.

NOTHING HERE MAY TOUCH THE REAL STAMP OR THE REAL REGISTRY. `core.substrate_stamp.canonical_root`
is monkeypatched to REFUSE for every test and to resolve ONLY the planted tree when one exists;
the real stamp's stat triple (size, mtime_ns, ctime_ns) is snapshotted before this module and
asserted identical after it — a stat, never a read of its content. The `add` arms run against a
tmp registry only. No AWS call is possible: `aws` is monkeypatched to raise wherever `main()` runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core import substrate_stamp as st
from scripts import anchors_registry as ar
from scripts import submit_arms_campaign as sac

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
REGISTRY_CLI = REPO / "scripts" / "anchors_registry.py"
NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
ZERO = {"pinned": 3, "host": 3, "missing": 0, "extra": 0, "changed": 0}
OTHER = "f" * 64                                  # a digest no manifest will ever have
GFC = "67784c1ba70ce75a5ed62056f81d2ba1"          # the T-215 pre-flight canon (full md5 as recorded)
ECR = "407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-3863ef8"

#: The four transcribed anchors and the substrate digest PROVEN for each from its image's own
#: commit: sha256 of `git show 4c0fc16:config/substrate_manifest.sha256` (the T-167 manifest,
#: md5 be219d7f — docs/Audit/simfin_reconcile_t175_2026_06_16.md:34) for the three T-167 anchors;
#: sha256 of `git show 3863ef8:…` (== the manifest at 1d116c5; md5 9fe5c27e —
#: docs/Audit/phase1_cloud_run_t215_2026_06_19.md:99) for the T-215 GFC anchor.
T167_DIGEST = "a4767e20497c3b9e0056b8ca7cc5b39a52bb7cfd5e639b88969edec7f257e86c"
T219_DIGEST = "4b34ea8206e7e4191b13d4053b6f44e34c56a3fb1fd7a5c24d4413a684395b53"
EXPECTED_ANCHORS = {
    "t167-2022": ("eb48742e", True, "sha-4c0fc16", ("2022-01-01", "2022-12-31", "2022"), T167_DIGEST),
    "t167-16yr": ("3e9ea427", True, "sha-4c0fc16", ("2010-01-01", "2025-12-31", "16yr"), T167_DIGEST),
    "t167-26yr": ("158fe678", True, "sha-4c0fc16", ("2000-01-01", "2025-12-31", "26yr"), T167_DIGEST),
    "t215-gfc": (GFC, False, "sha-3863ef8", ("2008-01-01", "2009-12-31", "2008-2009-gfc"), T219_DIGEST),
}

_REAL_CANONICAL_ROOT = st.canonical_root


# ── never the real stamp, never the real registry ───────────────────────────────

def _real_stamp_stat():
    """A stat triple of the real stamp (never its content), or None when unresolvable/absent."""
    try:
        p = _REAL_CANONICAL_ROOT() / st.STAMP_REL
    except st.CanonicalRootUnresolved:
        return None
    if not p.exists():
        return None
    s = p.stat()
    return (s.st_size, s.st_mtime_ns, s.st_ctime_ns)


@pytest.fixture(scope="module", autouse=True)
def _the_real_stamp_and_registry_are_untouched_by_this_module():
    before = _real_stamp_stat()
    reg = (REPO / ar.ANCHORS_REL).read_bytes()
    yield
    assert _real_stamp_stat() == before, "this test module CHANGED the real stamp file"
    assert (REPO / ar.ANCHORS_REL).read_bytes() == reg, "this test module CHANGED config/anchors.json"


@pytest.fixture(autouse=True)
def _never_the_real_stamp(monkeypatch):
    def _refuse(start=None):
        raise AssertionError("a test resolved the REAL stamp path — use the `planted` tree")
    monkeypatch.setattr(st, "canonical_root", _refuse)
    monkeypatch.setattr(sac, "aws", lambda *a: (_ for _ in ()).throw(
        AssertionError(f"AWS was called: aws {a}")))


def _resolve_only(monkeypatch, tree: Path) -> None:
    """`canonical_root` resolves the planted tree and NOTHING else (the gate must pass `tree`)."""
    def _only(start=None):
        if start is not None and Path(start).resolve() == tree.resolve():
            return tree
        raise AssertionError(f"canonical_root({start!r}) — only the planted tree may resolve")
    monkeypatch.setattr(st, "canonical_root", _only)


# ── a planted tree ──────────────────────────────────────────────────────────────

_GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "lock", "GIT_AUTHOR_EMAIL": "lock@test",
            "GIT_COMMITTER_NAME": "lock", "GIT_COMMITTER_EMAIL": "lock@test"}


def _git(tree: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(tree), "-c", "commit.gpgsign=false", *args],
                          check=True, capture_output=True, text=True, env=_GIT_ENV, timeout=60)


MANIFEST_TEXT = ("a" * 64 + "  data/processed/AAA_1d.csv\n" + "b" * 64 + "  data/raw/r.txt\n"
                 + "c" * 64 + "  data/macro/VIX.parquet\n")


def _plant_tree(base: Path, *, git: bool = True, commit: str = "manifest") -> Path:
    """A tmp checkout: `config/substrate_manifest.sha256` on disk and (commit="manifest")
    committed; commit="readme" commits only a README so HEAD lacks the manifest; git=False
    plants no repository at all. `data/state` exists, empty, for the stamp."""
    tree = base / "tree"
    (tree / "config").mkdir(parents=True)
    (tree / "data" / "state").mkdir(parents=True)
    (tree / ar.MANIFEST_REL).write_text(MANIFEST_TEXT)
    if git:
        _git(tree, "init", "-q")
        if commit == "manifest":
            _git(tree, "add", ar.MANIFEST_REL)
        else:
            (tree / "README").write_text("no manifest at HEAD\n")
            _git(tree, "add", "README")
        _git(tree, "commit", "-q", "-m", "pin")
    return tree


@pytest.fixture
def planted(tmp_path, monkeypatch) -> Path:
    tree = _plant_tree(tmp_path)
    _resolve_only(monkeypatch, tree)
    return tree


def _digest(tree: Path) -> str:
    return st.manifest_digest(tree / ar.MANIFEST_REL)


def _stamp(tree: Path, digest: str, *, result: str = "PASS", writer: str = "repin",
           at: datetime = NOW - timedelta(hours=1), counts=ZERO, first_paths=(), error=None) -> Path:
    """The real writer, into the planted tree only."""
    rec = st.make_record(result, writer, "0" * 40, hashlib.md5(b"m").hexdigest(),
                         None if counts is None else dict(counts), list(first_paths),
                         error=error, verified_at=st.utc_now_iso(at))
    return st.write_stamp(digest, rec, root=tree)


def _entry(digest: str, *, anchor_id: str = "t215-gfc", canon: str = GFC, image: str = "sha-3863ef8",
           **over) -> dict:
    e = {"anchor_id": anchor_id, "canon_md5": canon, "canon_md5_is_prefix": len(canon) < 32,
         "window": {"start": "2008-01-01", "end": "2009-12-31", "label": "2008-2009-gfc"},
         "image": image, "substrate_manifest_digest": digest, "source": "planted", "measured_on": "2026-06-19",
         "recorded_on": "2026-11-05", "recorded_by": "lock", "status": "history"}
    e.update(over)
    return e


def _registry_file(where: Path, *entries: dict) -> Path:
    """A registry file OUTSIDE any checkout — for the CLI arms (verify / add) only."""
    p = where / "anchors.json"
    p.write_text(json.dumps({"schema": ar.SCHEMA, "anchors": list(entries)}, indent=1))
    return p


def _anchors(tree: Path, *entries: dict, commit: bool = True, rel: str = ar.ANCHORS_REL) -> Path:
    """The planted tree's registry at `rel`, COMMITTED (F3: a submit honours only a committed
    registry). commit=False leaves the on-disk edit uncommitted (the F3 locks, a tree without git)."""
    p = tree / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema": ar.SCHEMA, "anchors": list(entries)}, indent=1))
    if commit:
        _git(tree, "add", rel)
        staged = subprocess.run(["git", "-C", str(tree), "diff", "--cached", "--quiet"], env=_GIT_ENV).returncode
        if staged != 0:
            _git(tree, "commit", "-q", "-m", "registry")
    return p


def _spec(anchor="default", *, baseline: bool = False) -> dict:
    """A multi-arm spec: two PATCHED arms (no baseline, so the T-140 rule needs the anchor),
    with an `anchor` block naming the GFC canon on the FULL ECR ref. anchor=None → no block."""
    arms = {"arm1_a": {"config_patch": {"config/x.json": {"k": 1}}},
            "arm2_b": {"config_patch": {"config/x.json": {"k": 2}}}}
    if baseline:
        arms["arm0_off"] = {"config_patch": {}}
    spec = {"campaign_id": "lock", "windows": [{"start": "2022-01-01", "end": "2022-12-31"}],
            "reps": 1, "arms": arms}
    if anchor == "default":
        spec["anchor"] = {"canon_md5": GFC, "source": "lock", "image": ECR}
    elif anchor is not None:
        spec["anchor"] = anchor
    return spec


def _gate(spec: dict, tree: Path, anchors: Path, now: datetime = NOW) -> dict:
    return sac.enforce_substrate_gate(spec, tree=tree, now=now, anchors_path=anchors)


def _refused(spec: dict, tree: Path, anchors: Path, *words: str, now: datetime = NOW) -> str:
    with pytest.raises(SystemExit) as ei:
        _gate(spec, tree, anchors, now)
    msg = str(ei.value)
    assert msg.startswith(sac.GATE), msg
    for w in words:
        assert w in msg, (w, msg)
    return msg


def _tree_bytes(tree: Path, anchors: Path):
    sp = tree / st.STAMP_REL
    return (sp.read_bytes() if sp.exists() else None, anchors.read_bytes() if anchors.exists() else None,
            sorted(p.name for p in (tree / "data" / "state").iterdir()))


# ── P5 D: the stamp steps (b)-(d) ───────────────────────────────────────────────

def test_LOCK_absent_stamp_refuses_at_b_naming_the_fix(planted, tmp_path):
    a = _anchors(planted, _entry(_digest(planted)))
    msg = _refused(_spec(), planted, a, "(b: stamp present)", "ABSENT", "no stamp file",
                   "run the nightly", "re-pin", _digest(planted))
    assert "FIX:" in msg


def test_LOCK_FAIL_stamp_refuses_at_c_naming_result_writer_and_counts(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, result="FAIL", writer="janitor_nightly",
           counts={"pinned": 3, "host": 4, "missing": 0, "extra": 1, "changed": 5},
           first_paths=["CHANGED data/macro/VIX.parquet"])
    a = _anchors(planted, _entry(d))
    _refused(_spec(), planted, a, "(c: stamp PASS)", "FAIL", "janitor_nightly", "'changed': 5",
             "CHANGED data/macro/VIX.parquet", "re-pin")


def test_LOCK_ERROR_stamp_refuses_at_c_and_is_never_a_PASS(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, result="ERROR", writer="janitor_nightly", counts=None,
           error="build_manifest raised: boom")
    a = _anchors(planted, _entry(d))
    _refused(_spec(), planted, a, "(c: stamp PASS)", "ERROR", "boom", "never a PASS")


def test_LOCK_stale_stamp_refuses_at_d_with_the_relay_gap_wording(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, at=NOW - timedelta(hours=49))
    a = _anchors(planted, _entry(d))
    _refused(_spec(), planted, a, "(d: stamp fresh)",
             "stamp expired; is the re-pin pushed? (the relay_gap row)", "49.0 h old", "push")


def test_a_stamp_just_inside_FRESHNESS_is_still_fresh(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, at=NOW - st.FRESHNESS + timedelta(minutes=1))
    a = _anchors(planted, _entry(d))
    assert _gate(_spec(), planted, a)["manifest_digest"] == d


def test_LOCK_future_dated_stamp_refuses_at_d(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, at=NOW + timedelta(minutes=6))
    a = _anchors(planted, _entry(d))
    _refused(_spec(), planted, a, "(d: stamp fresh)", "future-dated", "clock")
    _stamp(planted, d, at=NOW + timedelta(minutes=4))         # inside FUTURE_SKEW: allowed
    assert _gate(_spec(), planted, a)["stamp"]["result"] == "PASS"


def test_LOCK_other_digest_only_refuses_at_b_naming_what_the_file_carries(planted, tmp_path):
    _stamp(planted, OTHER)                                     # a fresh PASS — for ANOTHER manifest
    a = _anchors(planted, _entry(_digest(planted)))
    _refused(_spec(), planted, a, "(b: stamp present)", "ABSENT", OTHER[:12] + "…",
             "a stamp for another manifest is not a verdict on this one")


def test_LOCK_unknown_schema_refuses_at_b_naming_StampSchemaUnknown(planted, tmp_path):
    (planted / st.STAMP_REL).write_text(json.dumps({"schema": "substrate_verify_stamp/v2", "stamps": {}}))
    a = _anchors(planted, _entry(_digest(planted)))
    _refused(_spec(), planted, a, "(b: stamp present)", "StampSchemaUnknown", "substrate_verify_stamp/v2")


def test_LOCK_unreadable_torn_file_refuses_at_b_naming_StampUnreadable(planted, tmp_path):
    d = _digest(planted)
    p = _stamp(planted, d)
    raw = p.read_bytes()
    p.write_bytes(raw[: len(raw) // 2])                        # torn mid-write
    a = _anchors(planted, _entry(d))
    _refused(_spec(), planted, a, "(b: stamp present)", "StampUnreadable", "torn write")


# ── P2: the committed-manifest step (a) ─────────────────────────────────────────

def test_LOCK_uncommitted_manifest_refuses_at_a_naming_both_digests(planted, tmp_path):
    committed = _digest(planted)
    _stamp(planted, committed)                                 # a fresh PASS exists — for the PIN
    (planted / ar.MANIFEST_REL).write_text(MANIFEST_TEXT + "d" * 64 + "  data/processed/NEW_1d.csv\n")
    on_disk = _digest(planted)
    a = _anchors(planted, _entry(committed))
    _refused(_spec(), planted, a, "(a: manifest committed)", "uncommitted", on_disk, committed,
             "not a pin", "commit the re-pin")


def test_LOCK_manifest_absent_at_HEAD_refuses_at_a(tmp_path, monkeypatch):
    tree = _plant_tree(tmp_path, commit="readme")
    _resolve_only(monkeypatch, tree)
    _stamp(tree, _digest(tree))
    a = _anchors(tree, _entry(_digest(tree)))
    _refused(_spec(), tree, a, "(a: manifest committed)", f"HEAD has no {ar.MANIFEST_REL}", "not a pin")


def test_LOCK_not_a_git_checkout_refuses_at_a(tmp_path, monkeypatch):
    tree = _plant_tree(tmp_path, git=False)
    _resolve_only(monkeypatch, tree)
    _stamp(tree, _digest(tree))
    a = _anchors(tree, _entry(_digest(tree)), commit=False)
    _refused(_spec(), tree, a, "(a: manifest committed)", "not a git checkout", "not a pin")


# ── the anchor step (e) ─────────────────────────────────────────────────────────

def test_LOCK_anchor_absent_refuses_at_e_naming_the_canon_and_the_registered_ids(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(d, anchor_id="t999-other", canon="deadbeef" * 4))
    _refused(_spec(), planted, a, "(e: anchor registered)", GFC, "not in", "t999-other",
             "anchors_registry.py add")


def test_LOCK_anchor_image_mismatch_refuses_at_e_naming_both(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(d, image="sha-aaaaaaa"))
    _refused(_spec(), planted, a, "(e: anchor image)", "sha-aaaaaaa", "sha-3863ef8", ECR, "t215-gfc")


def test_LOCK_anchor_digest_mismatch_refuses_at_e_naming_the_anchor_and_BOTH_digests(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(OTHER))                      # measured under ANOTHER substrate
    _refused(_spec(), planted, a, "(e: anchor substrate)", "t215-gfc → " + OTHER, d,
             "re-run the anchor on this substrate", "NEW entry", "history")


def test_history_and_current_entries_with_the_SAME_canon_coexist_and_the_current_one_is_chosen(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(OTHER, anchor_id="t215-gfc"),
                 _entry(d, anchor_id="t215-gfc-repin", status="current"))
    rec = _gate(_spec(), planted, a)
    assert rec["anchor"]["anchor_id"] == "t215-gfc-repin"


def test_LOCK_the_prefix_rule(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(d, anchor_id="t167-26yr", canon="158fe678", image="sha-4c0fc16"),
                 _entry(d, anchor_id="t215-gfc"))
    def block(md5, image=ECR):
        return {"canon_md5": md5, "source": "lock", "image": image}
    # a spec prefix matches the prefix-only entry; a full md5 starting with it matches too
    assert _gate(_spec(block("158fe678", "sha-4c0fc16")), planted, a)["anchor"]["anchor_id"] == "t167-26yr"
    assert _gate(_spec(block("158fe678" + "0" * 24, "sha-4c0fc16")), planted, a)["anchor"]["anchor_id"] == "t167-26yr"
    # a spec prefix matches a FULL entry it is a prefix of (8 and 12 hex)
    assert _gate(_spec(block(GFC[:8])), planted, a)["anchor"]["anchor_id"] == "t215-gfc"
    assert _gate(_spec(block(GFC[:12])), planted, a)["anchor"]["anchor_id"] == "t215-gfc"
    assert _gate(_spec(block(GFC.upper())), planted, a)["anchor"]["anchor_id"] == "t215-gfc"
    # one hex off is ABSENT; a 7-hex value is malformed
    _refused(_spec(block("158fe679")), planted, a, "(e: anchor registered)", "158fe679", "not in")
    _refused(_spec(block("158fe67")), planted, a, "(e: anchor registered)", "8..32")
    assert ar.canon_matches("158fe678", "158fe678" + "ab") and not ar.canon_matches("158fe678", "158fe679")


def test_LOCK_the_registry_verify_refuses_a_prefix_posing_as_full_a_full_flagged_prefix_and_a_duplicate_id(tmp_path):
    good = _entry(OTHER)
    assert ar.verify_anchors({"schema": ar.SCHEMA, "anchors": [good]}) == []
    posing = dict(good, canon_md5="158fe678", canon_md5_is_prefix=False)
    flagged = dict(good, canon_md5_is_prefix=True)
    dup = [good, dict(good, image="sha-other")]
    for doc, word in ((posing, "canon_md5_is_prefix=False"), (flagged, "canon_md5_is_prefix=True")):
        defects = ar.verify_anchors({"schema": ar.SCHEMA, "anchors": [doc]})
        assert defects and word in defects[0], defects
    assert any("duplicate anchor_id" in x for x in ar.verify_anchors({"schema": ar.SCHEMA, "anchors": dup}))
    assert any("schema" in x for x in ar.verify_anchors({"schema": "anchors/v2", "anchors": []}))
    assert any("unknown keys" in x for x in ar.verify_anchors(
        {"schema": ar.SCHEMA, "anchors": [dict(good, substrate_manifest_digets=OTHER)]}))
    # the CLI: exit 3 on a defect, 0 on a sound file
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": ar.SCHEMA, "anchors": dup}))
    r = subprocess.run([PY, str(REGISTRY_CLI), "verify", "--anchors", str(bad)], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == ar.EXIT_DEFECT and "duplicate anchor_id" in r.stderr, r
    r = subprocess.run([PY, str(REGISTRY_CLI), "verify", "--anchors", str(_registry_file(tmp_path, good))],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0 and "OK:" in r.stdout, r


def test_a_defective_or_absent_registry_refuses_at_e(planted):
    d = _digest(planted)
    _stamp(planted, d)
    a = planted / ar.ANCHORS_REL                               # absent on disk AND at HEAD
    _refused(_spec(), planted, a, "(e: anchor registry committed)", f"HEAD has no {ar.ANCHORS_REL}",
             "restore config/anchors.json from git")
    a.write_text("{not json")                                  # committed, so (e: registry committed) passes
    _git(planted, "add", ar.ANCHORS_REL)
    _git(planted, "commit", "-q", "-m", "bad")
    _refused(_spec(), planted, a, "(e: anchor registered)", "defective", "anchors_registry.py verify")


# ── the positive control, the record, the T-140 interplay ───────────────────────

def test_POSITIVE_CONTROL_a_fresh_PASS_and_a_matching_anchor_allow_the_submit_and_the_record_carries_both(
        planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d, at=NOW - timedelta(hours=1))
    a = _anchors(planted, _entry(d))                          # short tag in the entry, full ECR ref in the spec
    before = _tree_bytes(planted, a)
    rec = _gate(_spec(), planted, a)
    assert rec["manifest_digest"] == d
    assert rec["anchor"]["anchor_id"] == "t215-gfc" and rec["anchor"]["substrate_manifest_digest"] == d
    assert rec["stamp"] == {"result": "PASS", "writer": "repin", "verified_at": st.utc_now_iso(NOW - timedelta(hours=1)),
                            "counts": ZERO, "tree_head": "0" * 40}
    assert rec["manifest_s3_prefix_md5"] == hashlib.md5(MANIFEST_TEXT.encode()).hexdigest()
    assert len(rec["tree_head"]) == 40 and rec["anchors_path"] == str(a)
    assert _tree_bytes(planted, a) == before, "the gate WROTE something"
    # the same through load_spec: the record lands on the spec, the T-140 gate is satisfied by the anchor
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(_spec()))
    spec = sac.load_spec(sp, tree=planted, now=NOW, anchors_path=a)
    assert spec["_substrate_gate"]["anchor"]["anchor_id"] == "t215-gfc"


def test_LOCK_no_anchor_block_still_passes_a_to_d_and_e_is_the_T140_baseline_rule(planted, tmp_path):
    a = _anchors(planted, _entry(_digest(planted)))
    _refused(_spec(None, baseline=True), planted, a, "(b: stamp present)", "ABSENT")   # (a)-(d) apply
    _stamp(planted, _digest(planted))
    rec = _gate(_spec(None, baseline=True), planted, a)
    assert rec["anchor"] is None and rec["manifest_digest"] == _digest(planted)
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(_spec(None, baseline=True)))
    assert sac.load_spec(sp, tree=planted, now=NOW, anchors_path=a)["_substrate_gate"]["anchor"] is None


def test_LOCK_the_substrate_gate_runs_BEFORE_the_T140_gate(planted, tmp_path):
    """A multi-arm spec with NO baseline and NO anchor: T-140 would refuse it — but the
    substrate gate refuses FIRST, so the refusal names (b), not CANON-ANCHOR GATE."""
    a = _anchors(planted, _entry(_digest(planted)))
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(_spec(None)))
    with pytest.raises(SystemExit) as ei:
        sac.load_spec(sp, tree=planted, now=NOW, anchors_path=a)
    assert "(b: stamp present)" in str(ei.value) and "CANON-ANCHOR GATE" not in str(ei.value)
    _stamp(planted, _digest(planted))
    with pytest.raises(SystemExit, match="CANON-ANCHOR GATE"):                 # then T-140 has its say
        sac.load_spec(sp, tree=planted, now=NOW, anchors_path=a)


def test_LOCK_dry_run_still_refuses_and_never_calls_aws(planted, tmp_path, monkeypatch, capsys):
    d = _digest(planted)
    _stamp(planted, d, at=NOW - timedelta(hours=49))
    _anchors(planted, _entry(d))                               # main() reads <tree>/config/anchors.json, committed
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(_spec()))
    monkeypatch.setattr(sac, "REPO", planted)
    monkeypatch.setattr(sys, "argv", ["submit_arms_campaign.py", "--spec", str(sp), "--dry-run"])
    monkeypatch.setattr(sac, "datetime", _FrozenDatetime)
    with pytest.raises(SystemExit) as ei:
        sac.main()
    assert "(d: stamp fresh)" in str(ei.value) and "relay_gap" in str(ei.value)
    assert "DRY RUN" not in capsys.readouterr().out


class _FrozenDatetime(datetime):
    """`sac.main()` stamps launch_ts with datetime.now(); the gate takes `now` from load_spec's
    default (None → real now) — so the planted stamps here are dated relative to the REAL clock."""
    @classmethod
    def now(cls, tz=None):
        return NOW if tz is None else NOW.astimezone(tz)


def test_dry_run_positive_control_prints_the_gate_record_and_returns_0_without_aws(
        planted, tmp_path, monkeypatch, capsys):
    d = _digest(planted)
    real_now = datetime.now(timezone.utc)
    _stamp(planted, d, at=real_now - timedelta(minutes=10))   # main() has no `now`: the real clock judges
    _anchors(planted, _entry(d))
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(_spec()))
    monkeypatch.setattr(sac, "REPO", planted)
    monkeypatch.setattr(sys, "argv", ["submit_arms_campaign.py", "--spec", str(sp), "--dry-run"])
    assert sac.main() == 0
    out = capsys.readouterr().out
    assert f"[gate] substrate manifest {d}" in out and "stamp PASS by repin" in out
    assert "anchor t215-gfc" in out and "DRY RUN" in out
    assert not list((planted / "data").rglob("cloud_runs")), "a dry run must write no summary"


def test_write_summary_carries_the_gate_record(tmp_path, monkeypatch):
    monkeypatch.setattr(sac, "REPO", tmp_path)                 # data/cloud_runs under tmp, never the repo
    record = {"manifest_digest": OTHER, "stamp": {"result": "PASS"}, "anchor": {"anchor_id": "x"}}
    sac.write_summary([], "camp", "20261105T000000Z", substrate_gate=record)
    doc = json.loads((tmp_path / "data/cloud_runs/camp_20261105T000000Z.json").read_text())
    assert doc["substrate_gate"] == record


# ── the committed registry, and `add` ───────────────────────────────────────────

def test_the_committed_registry_verifies_and_records_the_four_anchors_with_their_PROVEN_digests():
    r = subprocess.run([PY, str(REGISTRY_CLI), "verify"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    doc = ar.load_anchors(REPO / ar.ANCHORS_REL)
    got = {e["anchor_id"]: (e["canon_md5"], e["canon_md5_is_prefix"], ar.image_tag(e["image"]),
                            (e["window"]["start"], e["window"]["end"], e["window"]["label"]),
                            e["substrate_manifest_digest"]) for e in doc["anchors"]}
    for aid, want in EXPECTED_ANCHORS.items():
        assert got[aid] == want, (aid, got[aid], want)
    for e in doc["anchors"]:
        if e["anchor_id"] in EXPECTED_ANCHORS:
            assert e["status"] == "history" and e["recorded_on"] == "2026-11-05"
            assert "reproduced by the reviewer" in e["recorded_by"]
            assert e["substrate_manifest_md5"] == ("be219d7f2b57854d867b15b57bde7995" if e["image"] == "sha-4c0fc16"
                                                   else "9fe5c27e09b0c6aec045262926010df7")
    # none of the four is current for THIS tree's committed manifest: every submit citing one refuses at (e)
    try:
        current = ar.committed_manifest_digest(REPO)
    except ar.ManifestNotCommitted:
        current = None
    assert current not in {T167_DIGEST, T219_DIGEST}


def test_LOCK_add_refuses_an_uncommitted_manifest_and_an_existing_id_and_appends_without_touching_others(
        planted, tmp_path):
    a = _registry_file(tmp_path, _entry(OTHER, anchor_id="t215-gfc"))
    before = a.read_bytes()
    base = [PY, str(REGISTRY_CLI), "add", "--anchors", str(a), "--tree", str(planted),
            "--canon-md5", "abcdef0123456789abcdef0123456789", "--window-start", "2008-01-01",
            "--window-end", "2009-12-31", "--label", "2008-2009-gfc", "--image", ECR,
            "--source", "lock", "--measured-on", "2026-11-05"]
    # (1) uncommitted manifest → exit 4, nothing written
    (planted / ar.MANIFEST_REL).write_text(MANIFEST_TEXT + "e" * 64 + "  data/raw/new\n")
    r = subprocess.run(base + ["--anchor-id", "t215-gfc-repin2"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == ar.EXIT_REFUSED and "uncommitted" in r.stderr and "not a pin" in r.stderr, r
    assert a.read_bytes() == before
    (planted / ar.MANIFEST_REL).write_text(MANIFEST_TEXT)       # restored to the committed bytes
    # (2) an existing id → exit 4, nothing written
    r = subprocess.run(base + ["--anchor-id", "t215-gfc"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == ar.EXIT_REFUSED and "already exists" in r.stderr, r
    assert a.read_bytes() == before
    # (3) a prefix without the flag → exit 4
    r = subprocess.run([x if x != "abcdef0123456789abcdef0123456789" else "abcdef01" for x in base]
                       + ["--anchor-id", "t215-gfc-repin2"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == ar.EXIT_REFUSED and "--canon-md5-is-prefix" in r.stderr, r
    # (4) the committed manifest → appended with ITS digest; the old entry byte-identical; verify green
    r = subprocess.run(base + ["--anchor-id", "t215-gfc-repin2"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0 and "ADDED t215-gfc-repin2" in r.stdout, r
    doc = ar.load_anchors(a)
    assert [e["anchor_id"] for e in doc["anchors"]] == ["t215-gfc", "t215-gfc-repin2"]
    assert doc["anchors"][0] == json.loads(before)["anchors"][0]
    new = doc["anchors"][1]
    assert new["substrate_manifest_digest"] == _digest(planted) == ar.committed_manifest_digest(planted)
    assert new["image"] == ECR and new["status"] == "current" and new["canon_md5_is_prefix"] is False
    assert "HEAD" in new["substrate_manifest_digest_source"]
    assert not list(tmp_path.glob("anchors.json.*.tmp"))
    r = subprocess.run([PY, str(REGISTRY_CLI), "verify", "--anchors", str(a)], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r
    # and, once COMMITTED into the checkout (F3), the gate admits the new anchor on this substrate
    _stamp(planted, _digest(planted))
    committed = _anchors(planted, *doc["anchors"])
    rec = _gate(_spec({"canon_md5": "abcdef0123456789abcdef0123456789", "source": "l", "image": "sha-3863ef8"}),
                planted, committed)
    assert rec["anchor"]["anchor_id"] == "t215-gfc-repin2"


# ── the review's four hardenings (F1–F4) and the NOTE ──────────────────────────

def test_LOCK_F1_an_AMBIGUOUS_match_refuses_naming_every_candidate_and_a_longer_canon_resolves_it(planted):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(d, anchor_id="anchor-a", canon="158fe678" + "a" * 24, image="sha-4c0fc16"),
                 _entry(d, anchor_id="anchor-b", canon="158fe678" + "b" * 24, image="sha-4c0fc16"))
    def block(md5):
        return {"canon_md5": md5, "source": "lock", "image": "sha-4c0fc16"}
    _refused(_spec(block("158fe678")), planted, a, "(e: anchor ambiguous)", "anchor-a", "anchor-b",
             "cite a longer canon_md5 or the full value")
    assert _gate(_spec(block("158fe678aaaa")), planted, a)["anchor"]["anchor_id"] == "anchor-a"
    assert _gate(_spec(block("158fe678" + "b" * 24)), planted, a)["anchor"]["anchor_id"] == "anchor-b"


def test_LOCK_F2_no_current_candidate_names_EVERY_same_image_entry_with_its_digest(planted):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry("1" * 64, anchor_id="gfc-one"), _entry("2" * 64, anchor_id="gfc-two"))
    _refused(_spec(), planted, a, "(e: anchor substrate)", "gfc-one → " + "1" * 64, "gfc-two → " + "2" * 64,
             f"current pinned manifest's digest {d}", "2 candidate(s)")


def test_LOCK_F3_an_uncommitted_registry_refuses_at_e_registry_committed_naming_both_sha256s(planted, tmp_path):
    d = _digest(planted)
    _stamp(planted, d)
    a = _anchors(planted, _entry(OTHER))                       # committed: a history entry only
    _refused(_spec(), planted, a, "(e: anchor substrate)")
    committed_sha = hashlib.sha256(a.read_bytes()).hexdigest()
    # the reviewer's forgery: the digest flipped to the current one ON DISK, never committed → REFUSED
    _anchors(planted, _entry(d), commit=False)
    forged_sha = hashlib.sha256(a.read_bytes()).hexdigest()
    _refused(_spec(), planted, a, "(e: anchor registry committed)", f"uncommitted {ar.ANCHORS_REL}",
             forged_sha, committed_sha, "not a pin", "commit the registry", "a submit never does")
    _git(planted, "add", ar.ANCHORS_REL)                       # staged, not committed → still refused
    _refused(_spec(), planted, a, "(e: anchor registry committed)", f"uncommitted {ar.ANCHORS_REL}", forged_sha)
    _git(planted, "commit", "-q", "-m", "registry2")            # committed → allowed
    assert _gate(_spec(), planted, a)["anchor"]["anchor_id"] == "t215-gfc"
    aside = tmp_path / "set_aside.json"                        # absent on disk while HEAD has it → refused
    os.replace(a, aside)
    _refused(_spec(), planted, a, "(e: anchor registry committed)", "absent on disk", "HEAD has it")
    os.replace(aside, a)
    assert _gate(_spec(), planted, a)["anchor"]["anchor_id"] == "t215-gfc"


def test_LOCK_F3_absent_at_HEAD_refuses_and_the_path_rule_inside_by_relative_path_outside_not_a_pin(
        tmp_path, monkeypatch):
    tree = _plant_tree(tmp_path)
    _resolve_only(monkeypatch, tree)
    d = _digest(tree)
    _stamp(tree, d)
    a = _anchors(tree, _entry(d), commit=False)                # on disk, never committed: HEAD lacks it
    _refused(_spec(), tree, a, "(e: anchor registry committed)", f"HEAD has no {ar.ANCHORS_REL}",
             "restore config/anchors.json from git")
    # THE RULE: a registry INSIDE the checkout is checked by its path relative to the tree …
    alt = _anchors(tree, _entry(d), rel="alt/anchors.json")
    assert _gate(_spec(), tree, alt)["anchor"]["anchor_id"] == "t215-gfc"
    _anchors(tree, _entry(d, anchor_id="forged"), commit=False, rel="alt/anchors.json")
    _refused(_spec(), tree, alt, "(e: anchor registry committed)", "uncommitted alt/anchors.json")
    # … and one OUTSIDE the checkout is not a pin, however sound its content
    outside = _registry_file(tmp_path, _entry(d))
    _refused(_spec(), tree, outside, "(e: anchor registry committed)", "outside the checkout", "not a pin")


_ADD_TAIL = ["--anchor-id", "t215-gfc-repin2", "--canon-md5", "abcdef0123456789abcdef0123456789",
             "--window-start", "2008-01-01", "--window-end", "2009-12-31", "--label", "2008-2009-gfc",
             "--image", "sha-aaaaaaa", "--source", "lock", "--measured-on", "2026-11-05"]


def test_LOCK_F4_add_refuses_an_absent_registry_with_exit_4_and_creates_nothing(planted, tmp_path, capsys):
    absent = tmp_path / "nowhere" / "anchors.json"
    argv = ["add", "--anchors", str(absent), "--tree", str(planted)] + _ADD_TAIL
    assert ar.main(argv) == ar.EXIT_REFUSED                    # the real entrypoint, in-process
    err = capsys.readouterr().err
    assert "REFUSED" in err and "restore config/anchors.json from git" in err and "nothing written" in err
    assert not absent.exists() and not absent.parent.exists()
    r = subprocess.run([PY, str(REGISTRY_CLI)] + argv, capture_output=True, text=True, cwd=REPO)   # and the process
    assert r.returncode == ar.EXIT_REFUSED and not absent.exists(), r


def test_LOCK_NOTE_add_into_an_unwritable_directory_exits_4_with_the_contracts_message_not_a_traceback(
        planted, tmp_path, capsys):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory modes")
    ro = tmp_path / "ro"
    ro.mkdir()
    a = _registry_file(ro, _entry(OTHER))
    before = a.read_bytes()
    ro.chmod(0o500)
    try:
        rc = ar.main(["add", "--anchors", str(a), "--tree", str(planted)] + _ADD_TAIL)
        err = capsys.readouterr().err
    finally:
        ro.chmod(0o700)
    assert rc == ar.EXIT_REFUSED, err
    assert "REFUSED: cannot write" in err and "nothing written" in err and "Traceback" not in err
    assert a.read_bytes() == before and not list(ro.glob("*.tmp"))
