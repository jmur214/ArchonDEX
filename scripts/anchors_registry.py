"""The canon-anchor REGISTRY — `config/anchors.json`, D's half of the campaign submit gate (2026-11-05).

Ruled 2026-10-15 (docs/State/health_check.md, the HIGH row "The campaign submit gate checks only
that the anchor KEYS exist"): there was NO machine-readable anchor registry — the four anchors
lived in docs/Audit prose, and a spec's `anchor` block records nothing about WHICH substrate the
anchor was measured on. This file is that registry and this script is its ONLY writer: `add` is
the explicit step the ruling requires, never called by a submit. The gate
(`scripts/submit_arms_campaign.py:enforce_substrate_gate`) only READS it.

THE FILE. `config/anchors.json`, committed (never a runtime artifact):

    {"schema": "anchors/v1",
     "anchors": [{"anchor_id": "t215-gfc",
                  "canon_md5": "67784c1ba70ce75a5ed62056f81d2ba1", "canon_md5_is_prefix": false,
                  "window": {"start": "2008-01-01", "end": "2009-12-31", "label": "2008-2009-gfc"},
                  "image": "sha-3863ef8",
                  "substrate_manifest_digest": "<sha256 of the COMMITTED config/substrate_manifest.sha256 the anchor ran under>",
                  "source": "<the doc path + line that states it>",
                  "measured_on": "2026-06-19", "recorded_on": "2026-11-05", "recorded_by": "...",
                  "status": "history | current", ...optional: substrate_manifest_md5,
                  substrate_manifest_digest_source, job_definition, metrics, notes}]}

Per entry the gate needs three facts: the canon (`canon_md5`; `canon_md5_is_prefix` is true when
only a prefix was ever recorded — the three T-167 anchors), the image the anchor was produced on
(`image`, the `sha-<short>` tag; a full ECR reference reduces to its tag at compare time), and the
SUBSTRATE it was measured under (`substrate_manifest_digest`, by
`core.substrate_stamp.manifest_digest` — the ONE identity function, the key the verify stamp uses).
A new substrate means new canons: the gate REFUSES an anchor whose digest is not the current pinned
manifest's, naming both; cutover day re-runs the anchors and `add`s NEW entries, the old kept as
`history` — never edited, never removed (`[NN-ARCHIVE]`). `status` is a human label; the gate
decides by digest, never by status.

THE MATCH RULE (locked in tests/test_submit_gate_d_half_2026_11_05.py): a spec's `canon_md5`
matches an entry when the SHORTER of the two lowercase hex strings is a prefix of the longer, both
at least 8 hex. So a spec prefix "158fe678" matches the prefix-only entry "158fe678" (and would
match a full entry starting with it); a spec's full md5 matches a prefix-only entry it starts
with. `verify` enforces flag <=> length < 32, so a prefix can never pose as a full md5.

CLI (exit codes: 0 ok · 2 usage · 3 the registry is DEFECTIVE (`verify`) · 4 REFUSED (`add`)):
    python scripts/anchors_registry.py verify [--anchors PATH]
    python scripts/anchors_registry.py add --anchor-id t215-gfc-repin2 --canon-md5 <32 hex> \
        --window-start 2008-01-01 --window-end 2009-12-31 --label 2008-2009-gfc \
        --image sha-abc1234 --source "<doc path:line>" --measured-on 2026-11-20 [--status current]
`add` computes `substrate_manifest_digest` from the CURRENT committed manifest (P2: the on-disk
`config/substrate_manifest.sha256` must equal `git show HEAD:config/substrate_manifest.sha256`; an
uncommitted manifest is not a pin, exit 4; a tree that is not a checkout or whose HEAD has no
manifest refuses the same way), appends to an EXISTING registry only (an absent `--anchors` path is
exit 4, "restore config/anchors.json from git" — the bootstrap was this unit's hand transcription and
is over; review F4), refuses an existing id (exit 4), writes atomically (an unwritable directory is
exit 4 with the message, never a traceback), and never touches another entry. Nothing here hashes
the data: the digest is the MANIFEST file's. The same committed-ness discipline guards the registry
itself at the gate (`check_file_committed`, review F3): a submit honours only the COMMITTED
`config/anchors.json`, so an on-disk edit — however plausible its digest — is not a pin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core import substrate_stamp as st  # noqa: E402  (manifest_digest: the ONE identity function)

SCHEMA = "anchors/v1"
ANCHORS_REL = "config/anchors.json"
MANIFEST_REL = "config/substrate_manifest.sha256"
STATUSES = ("history", "current")
TOP_KEYS = ("schema", "about", "anchors")
REQUIRED_KEYS = ("anchor_id", "canon_md5", "canon_md5_is_prefix", "window", "image",
                 "substrate_manifest_digest", "source", "measured_on", "recorded_on",
                 "recorded_by", "status")
OPTIONAL_KEYS = ("substrate_manifest_md5", "substrate_manifest_digest_source", "job_definition",
                 "metrics", "notes")
WINDOW_KEYS = ("start", "end", "label")
MIN_PREFIX = 8
MD5_LEN = 32

EXIT_DEFECT = 3
EXIT_REFUSED = 4

_HEX = re.compile(r"^[0-9a-f]+$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class AnchorsDefect(ValueError):
    """`config/anchors.json` cannot be trusted (unparseable, wrong schema, a malformed entry).
    The gate refuses on it; the fix is `anchors_registry.py verify` and a deliberate edit."""


class NotCommitted(RuntimeError):
    """A tracked file in the tree is not a pin — uncommitted (staged or not), absent at HEAD,
    absent on disk, or the tree is not a checkout. The message names which, and both sha256s
    when they differ."""


class ManifestNotCommitted(NotCommitted):
    """P2: the tree's manifest is not a pin — uncommitted, absent at HEAD, or not a checkout."""


# ── the pin's identity (P2), for the manifest AND the registry ──────────────────

def committed_file_sha256(tree: Path, rel: str) -> str:
    """sha256 of `git show HEAD:<rel>` in `tree` — HEAD's bytes of one tracked file.

    Raises `NotCommitted` when the tree is not a git checkout, HEAD has no copy of the file, or
    git cannot run — a "committed" that cannot be resolved is not a pin (fail closed)."""
    try:
        r = subprocess.run(["git", "-C", str(tree), "show", f"HEAD:{rel}"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise NotCommitted(f"git could not run in {tree}: {exc}") from exc
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace").strip()
        low = err.lower()
        if "not a git repository" in low:
            why = "not a git checkout"
        elif ("does not exist in" in low or "exists on disk, but not in" in low
              or "invalid object name" in low):
            why = f"HEAD has no {rel}"
        else:
            why = "git show failed"
        raise NotCommitted(f"{why} ({tree}): {err or f'git exit {r.returncode}'}")
    return hashlib.sha256(r.stdout).hexdigest()


def check_file_committed(tree: Path, rel: str) -> str:
    """The on-disk file's sha256 (`core.substrate_stamp.manifest_digest`, the one identity
    function), REQUIRED equal to HEAD's. Returns it. Raises `NotCommitted` naming both sha256s
    when they differ (staged-not-committed differs too), or why HEAD's / the disk copy could not
    be read."""
    committed = committed_file_sha256(tree, rel)
    on_disk = Path(tree) / rel
    try:
        digest = st.manifest_digest(on_disk)
    except FileNotFoundError as exc:
        raise NotCommitted(f"{rel} is absent on disk in {tree} (HEAD has it)") from exc
    except OSError as exc:
        raise NotCommitted(f"{rel} cannot be read ({on_disk}): {exc}") from exc
    if digest != committed:
        raise NotCommitted(f"uncommitted {rel}: on-disk sha256 {digest} != HEAD's {committed}")
    return digest


def committed_manifest_digest(tree: Path) -> str:
    """sha256 of `git show HEAD:config/substrate_manifest.sha256` in `tree` (`ManifestNotCommitted`
    when it cannot be resolved)."""
    try:
        return committed_file_sha256(tree, MANIFEST_REL)
    except NotCommitted as exc:
        raise ManifestNotCommitted(str(exc)) from exc


def check_manifest_committed(tree: Path) -> str:
    """P2 as the gate and `add` apply it: the on-disk manifest's digest, REQUIRED equal to HEAD's.
    Returns the digest; raises `ManifestNotCommitted` naming both when they differ."""
    try:
        return check_file_committed(tree, MANIFEST_REL)
    except NotCommitted as exc:
        raise ManifestNotCommitted(str(exc)) from exc


# ── images and canons ───────────────────────────────────────────────────────────

def image_tag(image: Any) -> str:
    """The tag of an image reference, lowercase: `sha-3863ef8`, `archondex-backtest:sha-3863ef8`
    and `407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-3863ef8` all reduce
    to `sha-3863ef8`. A digest reference keeps everything after its `@`. Empty stays empty."""
    s = str(image or "").strip()
    if "@" in s:
        return s.rsplit("@", 1)[-1].lower()
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    if ":" in s:
        s = s.rsplit(":", 1)[-1]
    return s.lower()


def normalize_canon(value: Any) -> str:
    """A spec's or an entry's canon md5 as lowercase hex of 8..32 chars; ValueError otherwise."""
    s = str(value or "").strip().lower()
    if not (MIN_PREFIX <= len(s) <= MD5_LEN and _HEX.match(s)):
        raise ValueError(f"canon_md5 must be {MIN_PREFIX}..{MD5_LEN} lowercase hex, got {value!r}")
    return s


def canon_matches(spec_md5: str, entry_md5: str) -> bool:
    """THE MATCH RULE: the shorter is a prefix of the longer (both already normalized)."""
    return spec_md5.startswith(entry_md5) or entry_md5.startswith(spec_md5)


def find_anchors(doc: Dict[str, Any], canon_md5: Any) -> List[Dict[str, Any]]:
    """Every entry whose canon matches `canon_md5` under the match rule, in file order.
    Raises ValueError for a malformed spec value (the gate names that)."""
    s = normalize_canon(canon_md5)
    return [e for e in doc["anchors"] if canon_matches(s, e["canon_md5"])]


# ── schema ──────────────────────────────────────────────────────────────────────

def _is_date(v: Any) -> bool:
    if not (isinstance(v, str) and _DATE.match(v)):
        return False
    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _entry_defects(i: int, e: Any) -> List[str]:
    where = f"anchors[{i}]"
    if not isinstance(e, dict):
        return [f"{where}: entry is {type(e).__name__}, not an object"]
    aid = e.get("anchor_id")
    where = f"anchors[{i}] ({aid!r})"
    out: List[str] = []
    unknown = sorted(set(e) - set(REQUIRED_KEYS) - set(OPTIONAL_KEYS))
    if unknown:
        out.append(f"{where}: unknown keys {unknown}")
    missing = [k for k in REQUIRED_KEYS if k not in e]
    if missing:
        out.append(f"{where}: lacks {missing}")
        return out
    if not (isinstance(aid, str) and _ID.match(aid)):
        out.append(f"{where}: anchor_id must match {_ID.pattern}")
    canon, flag = e["canon_md5"], e["canon_md5_is_prefix"]
    if not isinstance(flag, bool):
        out.append(f"{where}: canon_md5_is_prefix must be true/false")
    try:
        c = normalize_canon(canon)
        if c != canon:
            out.append(f"{where}: canon_md5 must be stored lowercase, got {canon!r}")
        if isinstance(flag, bool) and flag != (len(c) < MD5_LEN):
            out.append(f"{where}: canon_md5_is_prefix={flag} but canon_md5 has {len(c)} hex "
                       f"(a prefix is < {MD5_LEN}; a full md5 is exactly {MD5_LEN})")
    except ValueError as exc:
        out.append(f"{where}: {exc}")
    w = e["window"]
    if not (isinstance(w, dict) and sorted(w) == sorted(WINDOW_KEYS)):
        out.append(f"{where}: window must carry exactly {WINDOW_KEYS}")
    else:
        if not (_is_date(w["start"]) and _is_date(w["end"])):
            out.append(f"{where}: window start/end must be YYYY-MM-DD")
        elif w["start"] > w["end"]:
            out.append(f"{where}: window start {w['start']} is after end {w['end']}")
        if not (isinstance(w["label"], str) and w["label"].strip()):
            out.append(f"{where}: window label must be a non-empty string")
    if not (isinstance(e["image"], str) and image_tag(e["image"])):
        out.append(f"{where}: image must be a non-empty image reference (a `sha-<short>` tag)")
    d = e["substrate_manifest_digest"]
    if not (isinstance(d, str) and len(d) == 64 and _HEX.match(d)):
        out.append(f"{where}: substrate_manifest_digest must be 64 lowercase hex (sha256), got {d!r}")
    for k in ("source", "recorded_by"):
        if not (isinstance(e[k], str) and e[k].strip()):
            out.append(f"{where}: {k} must be a non-empty string")
    for k in ("measured_on", "recorded_on"):
        if not _is_date(e[k]):
            out.append(f"{where}: {k} must be YYYY-MM-DD")
    if e["status"] not in STATUSES:
        out.append(f"{where}: status {e['status']!r} not in {STATUSES}")
    m = e.get("substrate_manifest_md5")
    if m is not None and not (isinstance(m, str) and len(m) == MD5_LEN and _HEX.match(m)):
        out.append(f"{where}: substrate_manifest_md5 must be 32 lowercase hex")
    for k in ("substrate_manifest_digest_source", "job_definition", "notes"):
        if k in e and not (isinstance(e[k], str) and e[k].strip()):
            out.append(f"{where}: {k} must be a non-empty string when present")
    met = e.get("metrics")
    if met is not None and not (isinstance(met, dict) and all(
            isinstance(k, str) and (v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)))
            for k, v in met.items())):
        out.append(f"{where}: metrics must be an object of numbers (or null)")
    return out


def verify_anchors(doc: Any) -> List[str]:
    """Every defect in a parsed registry document; [] when it is sound."""
    if not isinstance(doc, dict):
        return [f"top level is {type(doc).__name__}, not an object"]
    out: List[str] = []
    if doc.get("schema") != SCHEMA:
        out.append(f"schema {doc.get('schema')!r} is not {SCHEMA!r} — this reader refuses what it does not know")
    unknown = sorted(set(doc) - set(TOP_KEYS))
    if unknown:
        out.append(f"unknown top-level keys {unknown}")
    anchors = doc.get("anchors")
    if not isinstance(anchors, list):
        return out + ["'anchors' is not a list"]
    ids: Dict[str, int] = {}
    for i, e in enumerate(anchors):
        out.extend(_entry_defects(i, e))
        if isinstance(e, dict) and isinstance(e.get("anchor_id"), str):
            if e["anchor_id"] in ids:
                out.append(f"anchors[{i}]: duplicate anchor_id {e['anchor_id']!r} "
                           f"(first at anchors[{ids[e['anchor_id']]}])")
            else:
                ids[e["anchor_id"]] = i
    return out


# ── read / write ────────────────────────────────────────────────────────────────

def load_anchors(path: Path) -> Dict[str, Any]:
    """The registry, validated. FileNotFoundError when absent; `AnchorsDefect` when untrustworthy."""
    p = Path(path)
    raw = p.read_bytes()                      # FileNotFoundError propagates: the caller names it
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise AnchorsDefect(f"{p}: unparseable ({exc})") from exc
    defects = verify_anchors(doc)
    if defects:
        raise AnchorsDefect(f"{p}: {len(defects)} defect(s): " + "; ".join(defects))
    return doc


def write_anchors(path: Path, doc: Dict[str, Any]) -> None:
    """Atomic: a temp file in the same directory, fsync, `os.replace`. Validates first. On any
    failure the temp file is discarded and the previous file is untouched."""
    defects = verify_anchors(doc)
    if defects:
        raise AnchorsDefect("refusing to write a defective registry: " + "; ".join(defects))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)                    # only this call's own temp file, never the registry
        except FileNotFoundError:
            pass
        raise


def add_anchor(doc: Dict[str, Any], entry: Dict[str, Any]) -> Dict[str, Any]:
    """A new document with `entry` appended; every existing entry is the same object, untouched.
    Raises `AnchorsDefect` on an existing id or a malformed entry."""
    existing = {e["anchor_id"] for e in doc["anchors"]}
    if entry.get("anchor_id") in existing:
        raise AnchorsDefect(f"anchor_id {entry['anchor_id']!r} already exists — a re-run is a NEW id; "
                            f"the old entry stays as history")
    new = {k: doc[k] for k in doc}
    new["anchors"] = list(doc["anchors"]) + [entry]
    defects = verify_anchors(new)
    if defects:
        raise AnchorsDefect("; ".join(defects))
    return new


# ── CLI ─────────────────────────────────────────────────────────────────────────

def _cmd_verify(args: argparse.Namespace) -> int:
    p = Path(args.anchors)
    try:
        doc = load_anchors(p)
    except FileNotFoundError:
        print(f"DEFECT: {p} is absent", file=sys.stderr)
        return EXIT_DEFECT
    except AnchorsDefect as exc:
        print(f"DEFECT: {exc}", file=sys.stderr)
        return EXIT_DEFECT
    for e in doc["anchors"]:
        print(f"  {e['anchor_id']:<16} canon {e['canon_md5']}{'…(prefix)' if e['canon_md5_is_prefix'] else ''} "
              f"image {image_tag(e['image'])} window {e['window']['label']} "
              f"substrate {e['substrate_manifest_digest'][:12]}… {e['status']}")
    print(f"OK: {p} — {len(doc['anchors'])} anchor(s), schema {SCHEMA}")
    return 0


def _require_registry(p: Path) -> Optional[str]:
    """F4: `add` appends to an EXISTING registry only — the bootstrap (this unit's hand
    transcription) is over. The refusal message, or None when the file is there."""
    if p.is_file():
        return None
    return (f"REFUSED: {p} is absent — `add` appends to an existing registry, never creates one; "
            f"nothing written\n  FIX: restore config/anchors.json from git")


def _write_or_refuse(p: Path, doc: Dict[str, Any]) -> Optional[str]:
    """The atomic write, or the contract's refusal message on an OSError (an unwritable
    directory, a full disk) — never a traceback. Nothing is written on a refusal."""
    try:
        write_anchors(p, doc)
    except OSError as exc:
        return (f"REFUSED: cannot write {p} ({type(exc).__name__}: {exc}); nothing written\n"
                f"  FIX: make the registry's directory writable, then re-run `add`")
    return None


def _cmd_add(args: argparse.Namespace) -> int:
    tree = Path(args.tree)
    p = Path(args.anchors)
    try:
        digest = check_manifest_committed(tree)
    except ManifestNotCommitted as exc:
        print(f"REFUSED (P2: the manifest is not a pin): {exc}\n"
              f"  FIX: commit the re-pin (`gen_substrate_manifest.py generate`, committed in the same "
              f"PR) and run `add` from that checkout; nothing written", file=sys.stderr)
        return EXIT_REFUSED
    absent = _require_registry(p)
    if absent:
        print(absent, file=sys.stderr)
        return EXIT_REFUSED
    try:
        doc = load_anchors(p)
    except AnchorsDefect as exc:
        print(f"REFUSED: the registry is defective, fix it first (`verify`): {exc}", file=sys.stderr)
        return EXIT_REFUSED
    try:
        canon = normalize_canon(args.canon_md5)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    is_prefix = len(canon) < MD5_LEN
    if is_prefix and not args.canon_md5_is_prefix:
        print(f"REFUSED: {canon!r} is {len(canon)} hex — pass --canon-md5-is-prefix to record a prefix "
              f"deliberately, or give the full 32-hex md5", file=sys.stderr)
        return EXIT_REFUSED
    head = st.git_head(tree)
    entry: Dict[str, Any] = {
        "anchor_id": args.anchor_id,
        "canon_md5": canon,
        "canon_md5_is_prefix": is_prefix,
        "window": {"start": args.window_start, "end": args.window_end, "label": args.label},
        "image": args.image,
        "substrate_manifest_digest": digest,
        "substrate_manifest_md5": st.manifest_s3_prefix_md5(tree / MANIFEST_REL),
        "substrate_manifest_digest_source": (
            f"anchors_registry.py add: sha256 of `git show HEAD:{MANIFEST_REL}` at HEAD {head} "
            f"(P2-checked equal to the on-disk file)"),
        "source": args.source,
        "measured_on": args.measured_on,
        "recorded_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "recorded_by": args.recorded_by,
        "status": args.status,
    }
    if args.job_definition:
        entry["job_definition"] = args.job_definition
    if args.notes:
        entry["notes"] = args.notes
    try:
        new = add_anchor(doc, entry)
    except AnchorsDefect as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    unwritable = _write_or_refuse(p, new)
    if unwritable:
        print(unwritable, file=sys.stderr)
        return EXIT_REFUSED
    print(f"ADDED {entry['anchor_id']} → {p}: canon {canon}{' (prefix)' if is_prefix else ''}, image "
          f"{image_tag(args.image)}, window {args.label}, substrate {digest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="The canon-anchor registry (config/anchors.json): verify | add")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="schema + every digest hex + no duplicate ids; exit 3 on a defect")
    v.add_argument("--anchors", default=str(REPO / ANCHORS_REL))
    a = sub.add_parser("add", help="append ONE entry whose substrate digest is the CURRENT committed manifest's")
    a.add_argument("--anchors", default=str(REPO / ANCHORS_REL))
    a.add_argument("--tree", default=str(REPO), help="the checkout whose committed manifest is the pin")
    a.add_argument("--anchor-id", required=True)
    a.add_argument("--canon-md5", required=True, help="the arm0 canon md5 (32 hex; a prefix needs --canon-md5-is-prefix)")
    a.add_argument("--canon-md5-is-prefix", action="store_true")
    a.add_argument("--window-start", required=True)
    a.add_argument("--window-end", required=True)
    a.add_argument("--label", required=True)
    a.add_argument("--image", required=True, help="the image the anchor was produced on (sha-<short> or a full ref)")
    a.add_argument("--source", required=True, help="the doc path + line that states the canon")
    a.add_argument("--measured-on", required=True, help="YYYY-MM-DD")
    a.add_argument("--status", default="current", choices=STATUSES)
    a.add_argument("--recorded-by", default="anchors_registry.py add")
    a.add_argument("--job-definition", default=None)
    a.add_argument("--notes", default=None)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return _cmd_verify(args) if args.cmd == "verify" else _cmd_add(args)


if __name__ == "__main__":
    sys.exit(main())
