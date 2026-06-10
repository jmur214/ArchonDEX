#!/usr/bin/env python3
"""Generate (or verify) the pinned data-substrate manifest.

T-2026-06-09-127: the cloud image bakes ``data/processed/``, ``data/raw/``
and ``data/governor/`` from the HOST FILESYSTEM at build time. T-125 pinned
the Docker base by digest and the libs were already lock-pinned — but the
data legs were unpinned, so two builds of the same commit on different days
could (and did) bake different bytes and produce different trade canons.
T-126/T-127 forensics traced one full week of contradictory 26-yr baselines
to exactly this class.

This script closes the third leg:

* ``generate`` walks the three substrate dirs, hashes every file (sha256),
  and writes a sorted manifest. The manifest is COMMITTED to git
  (``config/substrate_manifest.sha256``), making the expected data state
  part of the reviewed source tree.
* ``verify`` recomputes and diffs against the committed manifest, failing
  loudly with the exact paths that drifted. ``scripts/build_backtest_image.sh``
  runs this before every build — a build on drifted data CANNOT succeed
  silently anymore.

When the substrate legitimately changes (new data vintage, governor seed
update), regenerate + commit the manifest in the same PR — that turns a
silent drift into a reviewed, deliberate act.

Junk files (.DS_Store, __pycache__, *.pyc) are excluded from hashing so
host clutter neither lands in the manifest nor fails verification.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

SUBSTRATE_DIRS = ["data/processed", "data/raw", "data/governor"]
JUNK_NAMES = {".DS_Store"}
JUNK_SUFFIXES = {".pyc"}
JUNK_DIRS = {"__pycache__"}
DEFAULT_MANIFEST = "config/substrate_manifest.sha256"


def iter_substrate_files(root: Path):
    for d in SUBSTRATE_DIRS:
        base = (root / d).resolve()
        if not base.is_dir():
            print(f"WARN: substrate dir missing: {root / d}", file=sys.stderr)
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if p.name in JUNK_NAMES or p.suffix in JUNK_SUFFIXES:
                continue
            if any(part in JUNK_DIRS for part in p.parts):
                continue
            yield Path(d) / p.relative_to(base)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: Path) -> list[str]:
    lines = []
    for rel in iter_substrate_files(root):
        digest = hash_file((root / rel).resolve())
        lines.append(f"{digest}  {rel.as_posix()}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["generate", "verify"])
    ap.add_argument("--root", default=".", help="repo root holding data/ (symlinked subdirs are followed)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST, help=f"manifest path (default {DEFAULT_MANIFEST})")
    args = ap.parse_args()

    root = Path(args.root)
    manifest_path = root / args.manifest

    lines = build_manifest(root)
    body = "\n".join(lines) + "\n"
    digest_of_manifest = hashlib.md5(body.encode()).hexdigest()

    if args.mode == "generate":
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(body)
        print(f"wrote {manifest_path} ({len(lines)} files; manifest-md5 {digest_of_manifest})")
        return 0

    # verify
    if not manifest_path.exists():
        print(f"FAIL: manifest {manifest_path} does not exist — run `generate` and commit it", file=sys.stderr)
        return 2
    expected = manifest_path.read_text().splitlines()
    actual = lines
    if expected == actual:
        print(f"OK: substrate matches manifest ({len(lines)} files; manifest-md5 {digest_of_manifest})")
        return 0
    exp_map = dict(reversed(l.split("  ", 1)) for l in expected if "  " in l)
    act_map = dict(reversed(l.split("  ", 1)) for l in actual if "  " in l)
    missing = sorted(set(exp_map) - set(act_map))
    extra = sorted(set(act_map) - set(exp_map))
    changed = sorted(k for k in set(exp_map) & set(act_map) if exp_map[k] != act_map[k])
    print("FAIL: substrate has DRIFTED from the committed manifest:", file=sys.stderr)
    for p in missing[:20]:
        print(f"  MISSING : {p}", file=sys.stderr)
    for p in extra[:20]:
        print(f"  EXTRA   : {p}", file=sys.stderr)
    for p in changed[:20]:
        print(f"  CHANGED : {p}", file=sys.stderr)
    total = len(missing) + len(extra) + len(changed)
    if total > 60:
        print(f"  … and {total - 60} more", file=sys.stderr)
    print(
        "Either restore the canonical substrate, or — if the change is deliberate — "
        "regenerate + COMMIT the manifest in the same PR.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
