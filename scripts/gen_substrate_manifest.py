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
# T-2026-06-13-164: curated individual files pinned WITHOUT walking their whole
# parent dir. sp500_membership.parquet drives the resolved universe and is
# gitignored — its silent regeneration (T-154) broke historical-universe runs
# repo-wide. Pinning it makes any future drift a LOUD manifest-verify failure
# (the T-131 discipline). We pin the file only, NOT data/universe/ — that dir
# also holds the bulky Wikipedia/Clenow scrape cache (raw_membership_sources/)
# which is rebuildable and must NOT bloat the image.
SUBSTRATE_FILES = ["data/universe/sp500_membership.parquet"]
JUNK_NAMES = {".DS_Store"}
JUNK_SUFFIXES = {".pyc"}
JUNK_DIRS = {"__pycache__"}
DEFAULT_MANIFEST = "config/substrate_manifest.sha256"

# T-2026-06-10-131: LIVE mutable governor state is excluded from the
# manifest. Rationale (proven, see docs/Audit/governor_hygiene_t131_*):
#   * The in-container harness (scripts/run_isolated.py `isolated()`)
#     restores every ISOLATED_FILES entry from `_isolated_anchor/` ON
#     ENTRY — the baked live value is overwritten before the engine
#     reads it, so it cannot affect the trade canon. Proven empirically:
#     a run with the ENTIRE June-10 drifted live set mounted produced a
#     bitwise-identical canon to the canonical run.
#   * edge_metrics.json / decision_diary.jsonl are write-only
#     observability outputs (governor._save_metrics is never read back;
#     the diary has no engine readers) — append/rewrite by design.
#   * Pinning them caused the operational trap this exclusion fixes:
#     ANY local run mutated live files -> manifest verify FAILED -> all
#     image builds blocked on a hand-restore.
# The ANCHORS (`_isolated_anchor/`, `_cap_recal_anchor/`) remain PINNED
# — they are the state the run actually executes from, i.e. the
# reproducibility-relevant input. Changing an anchor is a deliberate
# act: re-run --save-anchor, regenerate this manifest, commit both in
# the same PR.
LIVE_MUTABLE_GOVERNOR = {
    # ISOLATED_FILES (run_isolated.py) — restored from anchor on entry:
    "data/governor/edges.yml",
    "data/governor/edge_weights.json",
    "data/governor/regime_edge_performance.json",
    "data/governor/lifecycle_history.csv",
    "data/governor/ga_population.yml",
    # journal-mode scope:
    "data/governor/lifecycle_journal.jsonl",
    "data/governor/.journal_apply_mark",
    # write-only observability (no engine readers):
    "data/governor/edge_metrics.json",
    "data/governor/decision_diary.jsonl",
}


def iter_substrate_files(root: Path):
    import os
    for d in SUBSTRATE_DIRS:
        base = (root / d).resolve()
        if not base.is_dir():
            print(f"WARN: substrate dir missing: {root / d}", file=sys.stderr)
            continue
        # T-155 fix: walk with followlinks=True. Since T-133 the anchor
        # dirs are SYMLINKS in agent worktrees; pathlib.rglob does not
        # descend symlinked dirs, so a manifest generated in a worktree
        # silently DROPPED the anchors — while the build's `rsync -aL`
        # dereferences them, making every build fail verify with
        # "EXTRA: _isolated_anchor/...". The generator must dereference
        # exactly like the build stages.
        paths = []
        for dirpath, _dirnames, filenames in os.walk(base, followlinks=True):
            for fn in filenames:
                paths.append(Path(dirpath) / fn)
        for p in sorted(paths):
            if not p.is_file():
                continue
            if p.name in JUNK_NAMES or p.suffix in JUNK_SUFFIXES:
                continue
            if any(part in JUNK_DIRS for part in p.parts):
                continue
            rel = Path(d) / p.relative_to(base)
            if rel.as_posix() in LIVE_MUTABLE_GOVERNOR:
                continue
            yield rel
    # curated individual files (T-164)
    for f in SUBSTRATE_FILES:
        if (root / f).resolve().is_file():
            yield Path(f)
        else:
            print(f"WARN: curated substrate file missing: {root / f}", file=sys.stderr)


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
