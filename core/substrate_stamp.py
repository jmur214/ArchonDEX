"""The substrate VERIFY STAMP — the janitor-side half of the campaign submit gate (B, 2026-10-22).

Agreed interface: `docs/Sources/proposal_substrate_verify_stamp_janitor_2026-10-15.md` §7
(P1–P5, the director's rulings R1–R3, D's three additions). This module is P1, OWNED BY B;
D's gate (`scripts/submit_arms_campaign.py` + `config/anchors.json`) imports the reader and
the two shared facts — `manifest_digest()` and `FRESHNESS` — and builds nothing of its own.

WHY A STAMP. The gate must not hash ~14,250 files per submit, and a stamp is only as true
as whatever writes it. So exactly TWO writers run the FULL data-hashing verify
(`scripts/gen_substrate_manifest.py`'s own `build_manifest()`, never its printed footer):

  * `janitor_nightly` — `scripts/janitor_nightly.py:check_substrate_verify`, every night,
    against the canonical data, for the manifest committed in the runner's tree;
  * `repin`          — `scripts/gen_substrate_manifest.py generate`, after its OWN second
    full pass over the data it just pinned.

A submit never writes the stamp. A verify of manifest X never touches the entry for Y.

THE FILE. `<main tree>/data/state/substrate_verify_stamp.json`, beside the autonomy ledger —
a runtime artifact in the gitignored canonical tree, never committed. `data/state` is a REAL
per-worktree directory in agent worktrees, so the location is resolved through the git
COMMON dir (`canonical_root()`), the way the janitor resolves its ledger: one stamp file
exists no matter which worktree wrote it. Keyed by the sha256 of the COMMITTED
`config/substrate_manifest.sha256` (R1); the S3 prefix's md5 is RECORDED beside it, never
used as the key.

    {"schema": "substrate_verify_stamp/v1",
     "stamps": {"<sha256 of the manifest file>": {
         "result": "PASS | FAIL | ERROR", "verified_at": "2026-10-23T08:05:12Z",
         "writer": "janitor_nightly | repin", "tree_head": "<commit whose manifest was verified>",
         "s3_prefix_md5": "<md5 of the same manifest bytes>",
         "counts": {"pinned": 14120, "host": 14254, "missing": 0, "extra": 134, "changed": 5},
         "first_paths": ["CHANGED data/macro/VIX.parquet", "..."], "error": null}}}

THE VERDICTS. PASS only on an exact, COMPLETE match — missing = extra = changed = 0 from a
finished `build_manifest()`. FAIL on any drift, with the true counts. ERROR when the verify
could not run (a crash, an unreadable file or directory, a missing substrate dir, a timeout):
`counts` is null, never fabricated zeros, and ERROR is never PASS — a verify that did not
finish says nothing about the substrate (`[NN-FAIL-CLOSED]`). A record that contradicts
itself (PASS with a non-zero count, an unknown writer, an unparseable date) is refused by
the reader, so a writer bug cannot be honoured as a verdict.

READING. `read_stamp(digest)` returns None when the stamp is ABSENT (no file, or no entry for
this digest; fix: run the nightly or re-pin) and raises the typed `StampUnreadable` when the
file exists but cannot be trusted (unparseable, wrong shape, a malformed record; fix:
investigate a writer bug or a torn write). `StampSchemaUnknown` is the subclass for a schema
this reader does not know (P4). Both refuse at the gate; the gate names which.
`freshness_verdict()` is the shared age rule (P3 d): a stamp older than `FRESHNESS` (48 h —
two nightlies, so one missed night does not block a submit and two do) is stale, and a
stamp dated in the FUTURE beyond `FUTURE_SKEW` is refused, because it would extend its own
freshness.

WRITING. `write_stamp()` is atomic — a temp file in the same directory, fsync, `os.replace` —
so a torn write leaves the previous stamp readable and no temp file behind. It updates only
the one digest it was given. An existing stamp file that is UNREADABLE is set aside under a
dated `.unreadable.<ts>` name (kept, never deleted: `[NN-ARCHIVE]`) before a fresh file is
written, so the nightly can recover from a torn file without destroying the evidence.

KNOWN, STATED FOR WHOEVER READS A REFUSAL (§7):
  (1) Every submit refuses until re-pin #1 (the honest-N re-bake) lands, because `verify`
      exits 1 today: pinned 14,120 · host 14,254 · MISSING 0 · EXTRA 134 · CHANGED 5 — the
      known B-7 blocker (health_check's MEDIUM manifest row). That is the honest state.
  (2) A LOCAL, unpushed re-pin's PASS stands only until the 48 h bound; after that every
      submit refuses until the push lands and a nightly (which certifies origin/main)
      verifies the new manifest. Ruled a FEATURE, not a cost (R3): an unpushed re-pin must
      not license cloud submits for long; the refusal names relay_gap.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

#: P4 (D's addition): the reader REFUSES any other value.
SCHEMA = "substrate_verify_stamp/v1"
#: ONE literal of the path, and `_write_atomic` serialises through the json module's dump
#: call on a file handle — the two things the T-356 durability census's text scan matches
#: (`core/durability_census.py`: `_DATA_PATH` and `_WRITE_IDIOM`), so the census SEES this
#: module as the stamp's writer by construction instead of carrying it by declaration only.
#: Locked in `tests/test_substrate_stamp_2026_10_22.py` against the scan AND by AST (the
#: call must be in CODE: a comment spelling the idiom satisfied the text scan once, which
#: is the "we said it" trap, 2026-10-22). The reviewer caught the first comment here
#: claiming this of a `f.write(...)` the scan cannot see.
STAMP_REL = "data/state/substrate_verify_stamp.json"
#: P1 (D's addition): the ONE freshness bound, shared by the gate and any census check (R3).
FRESHNESS = timedelta(hours=48)
#: P3 (D's addition): a stamp dated further ahead than this is refused as future-dated.
FUTURE_SKEW = timedelta(minutes=5)

RESULTS = ("PASS", "FAIL", "ERROR")
WRITERS = ("janitor_nightly", "repin")
COUNT_KEYS = ("pinned", "host", "missing", "extra", "changed")
RECORD_KEYS = ("result", "verified_at", "writer", "tree_head", "s3_prefix_md5",
               "counts", "first_paths", "error")
_HEX64 = frozenset("0123456789abcdef")


class StampUnreadable(RuntimeError):
    """The stamp file exists but cannot be trusted. Fix: investigate a writer bug or a torn
    write. Distinct from ABSENT (`read_stamp` returns None), whose fix is to run a writer."""


class StampSchemaUnknown(StampUnreadable):
    """The file declares a schema this reader does not know (P4: refuse, never guess)."""


class CanonicalRootUnresolved(RuntimeError):
    """The main tree could not be resolved — the stamp has no location. Fail closed: a
    stamp invented under some other root would be a verdict nobody else can read."""


# ── where ───────────────────────────────────────────────────────────────────────

def canonical_root(start: Optional[Path] = None) -> Path:
    """The MAIN worktree, from wherever this runs — the janitor's resolution (P1).

    `git rev-parse --git-common-dir` points at the main worktree's `.git` from ANY
    worktree, so one stamp file exists no matter where a writer or reader is invoked.
    Unlike the janitor's ledger resolver this does NOT degrade to the local checkout:
    a stamp written under a worktree's private `data/state` is one the gate never reads
    (or worse, one it reads while the nightly writes elsewhere), so an unresolvable
    root raises `CanonicalRootUnresolved`.
    """
    base = Path(start) if start is not None else ROOT
    try:
        out = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise CanonicalRootUnresolved(f"cannot resolve the main tree from {base}: {exc}") from exc
    if not out:
        raise CanonicalRootUnresolved(f"git gave no common dir for {base}")
    common = Path(out)
    main = common.parent if common.name == ".git" else common
    if not (main / "data").is_dir():
        raise CanonicalRootUnresolved(
            f"{main} resolved as the main tree but has no data/ — refusing to invent a "
            f"stamp location")
    return main


def stamp_path(root: Optional[Path] = None) -> Path:
    """`<root>/data/state/substrate_verify_stamp.json`; `root` defaults to the main tree."""
    return Path(root if root is not None else canonical_root()) / STAMP_REL


# ── identity ────────────────────────────────────────────────────────────────────

def manifest_digest(path: Path) -> str:
    """THE ONE identity function (P1, D's addition): sha256 hex of the manifest file's bytes.

    The stamp key, and the `substrate_manifest_digest` D's `config/anchors.json` records
    per anchor. Raises `OSError` when the file cannot be read — never a digest of nothing."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_s3_prefix_md5(path: Path) -> str:
    """md5 hex of the same bytes — the content-addressed S3 snapshot prefix and the image
    label (`scripts/build_backtest_image.sh`). RECORDED beside the digest, never the key (R1)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(tree: Path) -> Optional[str]:
    """The full HEAD sha of the checkout holding `tree`, or None when it is not one (a
    scratch manifest has no tree; its stamp can never match a committed digest anyway)."""
    try:
        r = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    out = r.stdout.strip()
    return out if r.returncode == 0 and len(out) == 40 else None


# ── time ────────────────────────────────────────────────────────────────────────

def utc_now_iso(now: Optional[datetime] = None) -> str:
    """UTC ISO-8601 with a trailing Z, second precision (P4: `verified_at`)."""
    now = now if now is not None else datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_verified_at(text: str) -> datetime:
    """Parse a `verified_at`; naive or non-UTC input is refused (a stamp's clock is UTC)."""
    if not isinstance(text, str) or not text:
        raise ValueError(f"verified_at must be a non-empty string, got {text!r}")
    s = text[:-1] + "+00:00" if text.endswith("Z") else text
    at = datetime.fromisoformat(s)
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise ValueError(f"verified_at must be UTC, got {text!r}")
    return at


def freshness_verdict(record: Dict[str, Any], now: Optional[datetime] = None) -> Optional[str]:
    """P3 (d), shared: None when the stamp is fresh, else the refusal naming which and the fix.

    Future-dated (beyond `FUTURE_SKEW`) is checked FIRST — such a stamp would extend its
    own freshness, so it is refused rather than trusted as young."""
    now = now if now is not None else datetime.now(timezone.utc)
    at = parse_verified_at(record["verified_at"])
    if at > now + FUTURE_SKEW:
        ahead = at - now
        return (f"future-dated: verified_at {record['verified_at']} is {ahead} ahead of now "
                f"(> {FUTURE_SKEW} skew) — a stamp cannot extend its own freshness; fix: "
                f"check the writer host's clock, then run the nightly or re-pin")
    age = now - at
    if age > FRESHNESS:
        hours = age.total_seconds() / 3600
        return (f"stale: verified_at {record['verified_at']} is {hours:.1f} h old "
                f"(> {FRESHNESS.total_seconds() / 3600:.0f} h) — is the re-pin pushed? (the "
                f"relay_gap row: the nightly certifies origin/main); fix: push, or run the "
                f"nightly, or re-pin")
    return None


# ── the record ──────────────────────────────────────────────────────────────────

def _check_digest(digest: str) -> str:
    if not (isinstance(digest, str) and len(digest) == 64 and set(digest) <= _HEX64):
        raise ValueError(f"a stamp digest is a 64-hex sha256, got {digest!r}")
    return digest


def _validate_record(rec: Any, where: str) -> Dict[str, Any]:
    """Every field P4 names, with the type it names. A self-contradicting record is a
    writer bug and is refused (`StampUnreadable`), never honoured."""
    def bad(msg: str) -> StampUnreadable:
        return StampUnreadable(f"{where}: {msg}")

    if not isinstance(rec, dict):
        raise bad(f"record is {type(rec).__name__}, not an object")
    missing = [k for k in RECORD_KEYS if k not in rec]
    if missing:
        raise bad(f"record lacks {missing}")
    if rec["result"] not in RESULTS:
        raise bad(f"result {rec['result']!r} not in {RESULTS}")
    if rec["writer"] not in WRITERS:
        raise bad(f"writer {rec['writer']!r} not in {WRITERS}")
    try:
        parse_verified_at(rec["verified_at"])
    except ValueError as exc:
        raise bad(f"verified_at: {exc}") from exc
    for k in ("tree_head", "s3_prefix_md5", "error"):
        if rec[k] is not None and not isinstance(rec[k], str):
            raise bad(f"{k} must be a string or null")
    if not isinstance(rec["first_paths"], list) or not all(isinstance(p, str) for p in rec["first_paths"]):
        raise bad("first_paths must be a list of strings")
    counts = rec["counts"]
    if rec["result"] == "ERROR":
        if counts is not None:
            raise bad("an ERROR record carries no counts (null, never fabricated numbers)")
        if not (isinstance(rec["error"], str) and rec["error"].strip()):
            raise bad("an ERROR record must say what failed")
        return rec
    if not isinstance(counts, dict) or sorted(counts) != sorted(COUNT_KEYS):
        raise bad(f"counts must carry exactly {COUNT_KEYS}")
    for k in COUNT_KEYS:
        v = counts[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise bad(f"counts.{k} must be a non-negative integer, got {v!r}")
    drift = counts["missing"] + counts["extra"] + counts["changed"]
    if rec["result"] == "PASS" and drift:
        raise bad(f"PASS with drift counts {counts} — a writer bug; a PASS is only an exact match")
    if rec["result"] == "FAIL" and not drift:
        raise bad(f"FAIL with zero drift {counts} — a writer bug")
    return rec


def make_record(result: str, writer: str, tree_head: Optional[str], s3_prefix_md5: Optional[str],
                counts: Optional[Dict[str, int]], first_paths: List[str],
                error: Optional[str] = None, verified_at: Optional[str] = None) -> Dict[str, Any]:
    """Build and validate one P4 record. PASS requires missing = extra = changed = 0; ERROR
    requires `counts is None` and a non-empty `error`. Validation happens here AND on read."""
    rec = {"result": result, "verified_at": verified_at or utc_now_iso(), "writer": writer,
           "tree_head": tree_head, "s3_prefix_md5": s3_prefix_md5,
           "counts": None if counts is None else {k: int(counts[k]) for k in COUNT_KEYS},
           "first_paths": list(first_paths), "error": error}
    return _validate_record(rec, where=f"make_record({result}, {writer})")


# ── read / write ────────────────────────────────────────────────────────────────

def _load_doc(p: Path) -> Optional[Dict[str, Any]]:
    """The whole validated document, or None when the file is absent."""
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_bytes())
    except Exception as exc:                       # unparseable bytes of any kind
        raise StampUnreadable(f"{p}: unparseable ({type(exc).__name__}: {exc})") from exc
    if not isinstance(doc, dict):
        raise StampUnreadable(f"{p}: top level is {type(doc).__name__}, not an object")
    if doc.get("schema") != SCHEMA:
        raise StampSchemaUnknown(f"{p}: schema {doc.get('schema')!r} is not {SCHEMA!r} — "
                                 f"this reader refuses what it does not know")
    stamps = doc.get("stamps")
    if not isinstance(stamps, dict):
        raise StampUnreadable(f"{p}: 'stamps' is not an object")
    for key, rec in stamps.items():
        try:
            _check_digest(key)
        except ValueError as exc:
            raise StampUnreadable(f"{p}: {exc}") from exc
        _validate_record(rec, where=f"{p}[{key[:12]}]")
    return doc


def read_stamp(digest: str, root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """The record for `digest`, or None when ABSENT. Raises `StampUnreadable` (or its
    subclass `StampSchemaUnknown`) when the file exists but cannot be trusted (P4)."""
    _check_digest(digest)
    doc = _load_doc(stamp_path(root))
    if doc is None:
        return None
    rec = doc["stamps"].get(digest)
    return None if rec is None else dict(rec)


def _write_atomic(p: Path, doc: Dict[str, Any]) -> None:
    """Temp file in the same directory, `json.dump`, fsync, `os.replace`; on ANY failure
    the temp file is removed and the previous file is untouched."""
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    try:                                            # best effort: make the rename durable
        dfd = os.open(str(p.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


def write_stamp(digest: str, record: Dict[str, Any], root: Optional[Path] = None) -> Path:
    """Record the verdict for ONE digest, atomically, leaving every other digest's entry
    byte-identical. Returns the stamp path. An unreadable existing file is set aside
    (never deleted) and a fresh file written, so a writer can always recover."""
    _check_digest(digest)
    rec = _validate_record(dict(record), where=f"write_stamp({digest[:12]})")
    p = stamp_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc = _load_doc(p)
    except StampUnreadable as exc:
        aside = p.with_name(p.name + ".unreadable." + utc_now_iso().replace(":", ""))
        os.replace(p, aside)
        print(f"[substrate_stamp] existing stamp was UNREADABLE and is set aside at {aside}: "
              f"{exc}", file=sys.stderr)
        doc = None
    if doc is None:
        doc = {"schema": SCHEMA, "stamps": {}}
    doc["stamps"][digest] = rec
    _write_atomic(p, doc)
    return p
