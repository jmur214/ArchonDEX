#!/usr/bin/env python3
"""Generate (or verify) the pinned data-substrate manifest — and STAMP the verdict.

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
  part of the reviewed source tree. It then runs its OWN second full pass
  over the data and stamps the new manifest's digest PASS (writer ``repin``)
  in the verify stamp — the re-pin step of the campaign submit gate (§7 R2 of
  ``docs/Sources/proposal_substrate_verify_stamp_janitor_2026-10-15.md``).
* ``verify`` recomputes and diffs against the committed manifest, failing
  loudly with the exact paths that drifted. ``scripts/build_backtest_image.sh``
  runs this before every build — a build on drifted data CANNOT succeed
  silently anymore. With ``--stamp-writer janitor_nightly`` (the nightly
  janitor's invocation, and ONLY its) the verdict is stamped too; a bare
  ``verify`` never writes the stamp — exactly two writers exist.

The stamp (``core/substrate_stamp.py``) lives at the MAIN tree's
``data/state/substrate_verify_stamp.json`` by default; ``--stamp-root``
points a scratch run elsewhere. PASS only on missing = extra = changed = 0
from a COMPLETE ``build_manifest()``; FAIL with the true counts; ERROR —
never PASS — when the verify could not run (exit 3).

When the substrate legitimately changes (new data vintage, governor seed
update), regenerate + commit the manifest in the same PR — that turns a
silent drift into a reviewed, deliberate act.

Junk files (.DS_Store, __pycache__, *.pyc) are excluded from hashing so
host clutter neither lands in the manifest nor fails verification.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import substrate_stamp as stamp                      # noqa: E402

SUBSTRATE_DIRS = [
    "data/processed", "data/raw", "data/governor", "data/macro",
    # Re-pin #1 (2026-11-05, T-375 C1): the frozen 26-yr arm0 base curve
    # (t118r_v1_26yr_arm0_3b403882.csv) read by T-171/T-178/T-174 — a controller
    # product that had ZERO manifest lines (director's ruling 2026-10-15). NOT
    # regenerated at re-pin #2. `full_verify` requires every dir here to EXIST under
    # --root, so scripts/build_backtest_image.sh stages it too (verify only; the
    # Dockerfile does not COPY it — no in-image reader).
    "data/external/base_curve",
]
# T-2026-06-13-164: curated individual files pinned WITHOUT walking their whole
# parent dir. sp500_membership.parquet drives the resolved universe and is
# gitignored — its silent regeneration (T-154) broke historical-universe runs
# repo-wide. Pinning it makes any future drift a LOUD manifest-verify failure
# (the T-131 discipline). We pin the file only, NOT data/universe/ — that dir
# also holds the bulky Wikipedia/Clenow scrape cache (raw_membership_sources/)
# which is rebuildable and must NOT bloat the image.
# Re-pin #1 (2026-11-05, T-375 C1; the record's §0 second blocker): the honest-N gate's
# two inputs (`core/measurement/mbl_gate.py` DEFAULT_ARTIFACT_DIR / DEFAULT_PIN_PATH),
# pinned BY NAME — never data/observability/, which also holds run logs and S3 mirrors.
# The names MUST equal `config/honest_n_pin.json`'s (locked in
# tests/test_repin1_code_2026_11_05.py; the lock fails naming both files), so a future
# `honest_n_pin --pin --replace` forces a manifest edit in the same reviewed act. The
# image COPYs exactly these two and verifies the pin at build (Dockerfile.backtest), and
# the CI's S3 sync carries them under the content-addressed prefix because they are here.
HONEST_N_FILES = (
    "data/observability/n_effective_2026-09-30.json",
    "data/observability/run_registry.sqlite",
)
SUBSTRATE_FILES = [
    "data/universe/sp500_membership.parquet",
    # T-2026-06-18-210/215: the realistic-retail cap-tier join. Baked +
    # pinned so realistic_retail_costs=true is not silently inert on the cloud.
    "data/universe/market_cap_tiers.json",
    # Re-pin #1 (T-375 C1): the T-219 shares histories fetched ONCE
    # (`scripts/build_pit_cap_history_t219.py --write-snapshot`), so re-pin #2's cohort
    # recompute is deterministic and never fetches. ABSENT until the data half writes it:
    # `iter_substrate_files` WARNs and skips an absent curated file, so before `generate`
    # it simply has no manifest line; once pinned, an absent file is MISSING at verify.
    "data/universe/delist_shares_snapshot.parquet",
    *HONEST_N_FILES,
]
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


class SubstrateIncomplete(RuntimeError):
    """The verify cannot run COMPLETELY against this root (a substrate dir missing or
    unreadable). The stamp records ERROR, never a FAIL made of the files it could see."""


def _walk_error(exc: OSError) -> None:
    """`os.walk` swallows unreadable directories by default, which would turn an
    unreadable dir into MISSING counts — a FAIL that looks like drift. Raise instead."""
    raise SubstrateIncomplete(f"cannot walk {exc.filename}: {exc.strerror}") from exc


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
        for dirpath, _dirnames, filenames in os.walk(base, followlinks=True, onerror=_walk_error):
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


# ── the verify, as a value (the stamp's counts come from HERE, never the printed footer) ──

@dataclass
class VerifyResult:
    pinned: int
    host: int
    missing: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)
    changed: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.extra or self.changed)

    @property
    def counts(self) -> Dict[str, int]:
        return {"pinned": self.pinned, "host": self.host, "missing": len(self.missing),
                "extra": len(self.extra), "changed": len(self.changed)}

    def first_paths(self, n: int = 10) -> List[str]:
        """MISSING, then CHANGED, then EXTRA — the order a reader needs: a pinned file gone
        or altered matters more than an unpinned addition, and 134 extras must not hide
        five changed macro files (today's exact case)."""
        out = [f"MISSING {p}" for p in self.missing] + [f"CHANGED {p}" for p in self.changed] \
            + [f"EXTRA {p}" for p in self.extra]
        return out[:n]


def diff_manifest(expected: List[str], actual: List[str]) -> VerifyResult:
    exp_map = dict(reversed(l.split("  ", 1)) for l in expected if "  " in l)
    act_map = dict(reversed(l.split("  ", 1)) for l in actual if "  " in l)
    return VerifyResult(
        pinned=len(exp_map), host=len(act_map),
        missing=sorted(set(exp_map) - set(act_map)),
        extra=sorted(set(act_map) - set(exp_map)),
        changed=sorted(k for k in set(exp_map) & set(act_map) if exp_map[k] != act_map[k]))


def full_verify(root: Path, manifest_path: Path) -> VerifyResult:
    """The COMPLETE verify: every substrate dir must exist and walk, every file must hash.
    Raises (`SubstrateIncomplete`, `OSError`, ...) rather than returning a partial count."""
    absent = [d for d in SUBSTRATE_DIRS if not (root / d).is_dir()]
    if absent:
        raise SubstrateIncomplete(f"substrate dir(s) missing under {root}: {', '.join(absent)}")
    expected = manifest_path.read_text().splitlines()
    return diff_manifest(expected, build_manifest(root))


def _stamp(digest: str, manifest_path: Path, writer: str, stamp_root: Optional[Path],
           res: Optional[VerifyResult], error: Optional[str] = None) -> Path:
    rec = stamp.make_record(
        result="ERROR" if res is None else ("PASS" if res.ok else "FAIL"), writer=writer,
        tree_head=stamp.git_head(manifest_path.parent),
        s3_prefix_md5=stamp.manifest_s3_prefix_md5(manifest_path),
        counts=None if res is None else res.counts,
        first_paths=[] if res is None else res.first_paths(), error=error)
    p = stamp.write_stamp(digest, rec, root=stamp_root)
    print(f"stamped {rec['result']} for manifest {digest[:12]} by {writer} at {p}")
    return p


#: Paths printed per drift class before the footer counts the rest.
DRIFT_SHOWN_PER_CLASS = 20


def drift_hidden(res: VerifyResult) -> int:
    """The footer's number: total − shown, shown = Σ min(20, len(class)) over the three classes.
    Re-pin #1 C2 (2026-11-05): the footer used to subtract a flat 60, so today's 0 / 134 / 5
    printed "… and 79 more" while 114 paths were hidden (RR-7 D3; R confirmed)."""
    classes = (res.missing, res.extra, res.changed)
    shown = sum(min(DRIFT_SHOWN_PER_CLASS, len(c)) for c in classes)
    return sum(len(c) for c in classes) - shown


def _print_drift(res: VerifyResult) -> None:
    print("FAIL: substrate has DRIFTED from the committed manifest:", file=sys.stderr)
    for p in res.missing[:DRIFT_SHOWN_PER_CLASS]:
        print(f"  MISSING : {p}", file=sys.stderr)
    for p in res.extra[:DRIFT_SHOWN_PER_CLASS]:
        print(f"  EXTRA   : {p}", file=sys.stderr)
    for p in res.changed[:DRIFT_SHOWN_PER_CLASS]:
        print(f"  CHANGED : {p}", file=sys.stderr)
    hidden = drift_hidden(res)
    if hidden > 0:
        print(f"  … and {hidden} more", file=sys.stderr)
    print(
        "Either restore the canonical substrate, or — if the change is deliberate — "
        "regenerate + COMMIT the manifest in the same PR.",
        file=sys.stderr,
    )


def generate(root: Path, manifest_path: Path, stamp_root: Optional[Path]) -> int:
    """R2, the re-pin step: build, write the manifest to a TEMP path beside the target, run
    the re-pin's OWN second complete pass over the data against THAT file (not the lines in
    memory, so a file that changed during the walk — the runtime fundamentals cache, T-175 —
    cannot be stamped PASS), and rename onto the target ONLY on PASS. A truncated or
    unverified manifest never sits at the target: with a substrate dir absent the first
    version of this step left one there before exiting 3 (the reviewer's 5g probe,
    2026-10-22). On FAIL/ERROR the previous pin and its stamp stay exactly as they were;
    the verdict for the content that WAS built is still stamped — true, and inert at the
    gate, which looks up the COMMITTED manifest's digest."""
    lines = build_manifest(root)
    body = "\n".join(lines) + "\n"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_name(f"{manifest_path.name}.tmp.{os.getpid()}")
    tmp.write_text(body)
    digest = stamp.manifest_digest(tmp)
    try:
        try:
            res = full_verify(root, tmp)
        except Exception as exc:
            _stamp(digest, tmp, "repin", stamp_root, None, error=f"{type(exc).__name__}: {exc}")
            print(f"ERROR: the re-pin's own verify could not run: {type(exc).__name__}: {exc}; "
                  f"{manifest_path} was NOT written", file=sys.stderr)
            return 3
        if not res.ok:
            _stamp(digest, tmp, "repin", stamp_root, res)
            _print_drift(res)
            print(f"The data moved between the two passes — {manifest_path} was NOT written; "
                  f"re-run generate.", file=sys.stderr)
            return 1
        os.replace(tmp, manifest_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    _stamp(digest, manifest_path, "repin", stamp_root, res)
    print(f"wrote {manifest_path} ({res.pinned} files; manifest-md5 "
          f"{stamp.manifest_s3_prefix_md5(manifest_path)})")
    print(f"OK: re-pin verified ({res.pinned} files; manifest-sha256 {digest})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["generate", "verify"])
    ap.add_argument("--root", default=".", help="repo root holding data/ (symlinked subdirs are followed)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help=f"manifest path, relative to --root or absolute (default {DEFAULT_MANIFEST})")
    ap.add_argument("--stamp-writer", choices=["janitor_nightly"], default=None,
                    help="verify only: ALSO stamp the verdict as this writer. Reserved for the "
                         "nightly janitor; a bare verify never writes the stamp")
    ap.add_argument("--stamp-root", default=None,
                    help="where the stamp file lives (default: the MAIN tree, via the git "
                         "common dir). Point a scratch generate/verify here so it never "
                         "touches the real stamp")
    args = ap.parse_args()

    root = Path(args.root)
    manifest_path = root / args.manifest
    stamp_root = Path(args.stamp_root) if args.stamp_root else None

    if args.mode == "generate":
        return generate(root, manifest_path, stamp_root)

    # verify
    if not manifest_path.exists():
        print(f"FAIL: manifest {manifest_path} does not exist — run `generate` and commit it", file=sys.stderr)
        return 2
    digest = stamp.manifest_digest(manifest_path)
    try:
        res = full_verify(root, manifest_path)
    except Exception as exc:
        # ERROR, never PASS and never a FAIL made of partial counts (`[NN-FAIL-CLOSED]`).
        if args.stamp_writer:
            _stamp(digest, manifest_path, args.stamp_writer, stamp_root, None,
                   error=f"{type(exc).__name__}: {exc}")
        print(f"ERROR: verify could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    if args.stamp_writer:
        _stamp(digest, manifest_path, args.stamp_writer, stamp_root, res)
    if res.ok:
        print(f"OK: substrate matches manifest ({res.pinned} files; manifest-sha256 {digest}; "
              f"manifest-md5 {stamp.manifest_s3_prefix_md5(manifest_path)})")
        return 0
    _print_drift(res)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
