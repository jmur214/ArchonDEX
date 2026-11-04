#!/usr/bin/env python3
"""Cutover step 1 (the user's OPTION (a) ruling, 2026-10-22): drive the total-return writer over a
COPY of the processed cache, read the stale/holed-files guard and the convention label on it, and
stage a root for the candidate manifest. NEVER the canonical cache: every subcommand refuses a target
that resolves to any repo's `data/processed`, and only a path under `Dev/_substrate_candidates/` is
accepted as a copy. The real-cache write is cutover day, a separate approved act.

    python -m scripts.cutover_step1_pass fresh-copy --to <copy>        # from the canonical cache; refuses an existing <to>
    python -m scripts.cutover_step1_pass pass --copy <copy> [--only A,B] [--today YYYY-MM-DD] [--sleep 0.4]
    python -m scripts.cutover_step1_pass guard --cache <dir> --start 2000-01-03 --end 2025-12-31 [--out x.json]
    python -m scripts.cutover_step1_pass label --cache <dir> [--out x.json]
    python -m scripts.cutover_step1_pass stage --copy <copy> --root <staging_root>   # then gen_substrate_manifest.py --root

`pass` is RESUMABLE (one jsonl row per file; a file with a terminal row is skipped), writes the
writer's own log (`write_log.jsonl`, the per-file records) and the PROVIDER's output UNFILTERED
(`provider.log`: everything yfinance printed or logged, per file, with the file's name as a header).
A provider exception (not a writer refusal) is retried 3 times with 10/20/30 s backoff and every
attempt's reason is kept. Every row carries the writer source's sha256 and the worktree HEAD.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from engines.data_manager import tr_writer as w  # noqa: E402

CANDIDATES_ROOT = Path("/Users/jacksonmurphy/Dev/_substrate_candidates")
MAIN_CANONICAL = Path("/Users/jacksonmurphy/Dev/trading_machine-2/data/processed")
TOP_LEVEL_EXTRA = ("_merge_meta.json", "earnings_dates_pinned.parquet", "fundamentals_simfin.parquet")


# ── safety ────────────────────────────────────────────────────────────────────────

def assert_is_a_copy(path: Path) -> Path:
    """Refuse anything that is, or could be, the canonical cache."""
    p = Path(path).resolve()
    for canon in (w.CANONICAL_CACHE_DIR, MAIN_CANONICAL):
        try:
            if p == canon.resolve():
                raise SystemExit(f"REFUSED: {p} IS the canonical cache")
        except FileNotFoundError:
            pass
    if "data" in p.parts and "processed" in p.parts:
        raise SystemExit(f"REFUSED: {p} looks like a repo's data/processed — a copy lives under {CANDIDATES_ROOT}")
    if CANDIDATES_ROOT.resolve() not in p.parents:
        raise SystemExit(f"REFUSED: {p} is not under {CANDIDATES_ROOT}")
    return p


def _head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"unknown ({e!r})"


def _writer_sha() -> str:
    return hashlib.sha256((REPO / "engines" / "data_manager" / "tr_writer.py").read_bytes()).hexdigest()


# ── fresh-copy ────────────────────────────────────────────────────────────────────

def cmd_fresh_copy(args) -> int:
    src = MAIN_CANONICAL.resolve()
    dst = Path(args.to)
    if dst.exists():
        raise SystemExit(f"REFUSED: {dst} exists — a copy is never overwritten; rename it aside first")
    assert_is_a_copy(dst)
    print(f"[fresh-copy] {src} -> {dst}")
    shutil.copytree(src, dst, symlinks=False)
    n = sum(1 for p in dst.rglob("*") if p.is_file())
    print(f"[fresh-copy] done: {n} files")
    return 0


# ── the pass ──────────────────────────────────────────────────────────────────────

class _Tee(io.TextIOBase):
    def __init__(self, *sinks):
        self.sinks = sinks

    def write(self, s):
        for k in self.sinks:
            k.write(s)
        return len(s)

    def flush(self):
        for k in self.sinks:
            k.flush()


@contextlib.contextmanager
def capture_provider_output(log: io.TextIOBase, ticker: str):
    """Everything the provider prints or logs during one file, UNFILTERED, under the file's name."""
    log.write(f"\n===== {ticker} {datetime.now(timezone.utc).isoformat(timespec='seconds')} =====\n")
    log.flush()
    handler = logging.StreamHandler(log)
    handler.setLevel(logging.DEBUG)
    yf_logger = logging.getLogger("yfinance")
    prev_level = yf_logger.level
    yf_logger.addHandler(handler)
    tee_out, tee_err = _Tee(sys.stdout, log), _Tee(sys.stderr, log)
    with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
        try:
            yield
        finally:
            yf_logger.removeHandler(handler)
            yf_logger.setLevel(prev_level)
            log.flush()


def _classify(msg: str) -> str:
    m = msg
    if "REUSED TICKER" in m:
        return "class_i_declared"
    if "returned no bars" in m:
        return "unfetchable"
    if "cannot replace the file" in m or "before the cached end" in m:
        return "span"
    if "mid-span step" in m:
        return "seam_ratio"
    if "LEVEL IDENTITY" in m or "declared ratio" in m or "level identity holds" in m:
        return "level"
    if "DIFFERENT_CONVENTION" in m or "re-rule it" in m or "does not match the data" in m or "SPLIT-ONLY mode too" in m:
        return "convention"
    if "INSUFFICIENT" in m:
        return "insufficient"
    if "anomalous" in m:
        return "basis_anomalous"
    return "refused_other"


def _json_safe(x):
    return json.loads(json.dumps(x, default=str))


def _done(pass_path: Path) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    if pass_path.exists():
        for line in pass_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("terminal", True):
                    rows[r["ticker"]] = r
    return rows


def cmd_pass(args) -> int:
    copy = assert_is_a_copy(Path(args.copy))
    today = pd.Timestamp(args.today) if args.today else pd.Timestamp.today().normalize()
    out_dir = copy.parent
    tag = args.tag or f"{copy.name}"
    pass_path = out_dir / f"pass_{tag}.jsonl"
    write_log = out_dir / f"write_log_{tag}.jsonl"
    provider_log_path = out_dir / f"provider_{tag}.log"
    names = sorted(p.name[:-7] for p in copy.glob("*_1d.csv"))
    if args.only:
        wanted = [t.strip() for t in args.only.split(",") if t.strip()]
        missing = sorted(set(wanted) - set(names))
        if missing:
            raise SystemExit(f"REFUSED: --only names with no file in the copy: {missing}")
        names = wanted
    done = _done(pass_path)
    todo = [t for t in names if t not in done]
    env = {"writer_sha256": _writer_sha(), "head": _head(), "today": str(today.date()),
           "copy": str(copy), "python": sys.version.split()[0]}
    try:
        import yfinance as yf
        env["yfinance"] = yf.__version__
    except Exception as e:  # noqa: BLE001
        env["yfinance"] = f"unavailable ({e!r})"
    print(f"[pass] {len(names)} names, {len(done)} done, {len(todo)} to do; {env}")
    with open(provider_log_path, "a") as plog, open(pass_path, "a") as pout:
        for i, t in enumerate(todo, 1):
            row = {"ticker": t, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), **env,
                   "attempts": []}
            for attempt in range(1, 4):
                with capture_provider_output(plog, f"{t} attempt {attempt}"):
                    try:
                        rec = w.full_refetch(t, copy, w.DEFAULT_PROVIDERS, today=today, log_path=write_log,
                                             actions=w.DEFAULT_ACTIONS)
                        row.update({
                            "written": True,
                            "class": "written:" + (rec.overlap["verdict"] if rec.overlap else "NEW"),
                            "ratio": (rec.overlap or {}).get("ratio"),
                            "basis": rec.basis, "span": [rec.span_start, rec.span_end],
                            "cached_span": rec.cached_span, "n_rows": rec.n_rows,
                            "symbol_mapped": rec.symbol_mapped, "convention": rec.convention,
                            "seam": None if rec.seam is None else {
                                "date": rec.seam["date"], "source": rec.seam["source"],
                                "n_pre_seam_bars_kept": rec.seam["n_pre_seam_bars_kept"],
                                "seam_ratio": rec.seam["seam_ratio"]["ratio"],
                                "gap": rec.seam["gap"], "tolerance": rec.seam["tolerance"],
                                "gap_explained_by_declaration": rec.seam["gap_explained_by_declaration"]},
                            "level_log_residual": None if rec.level is None else rec.level["log_residual"],
                            "level_declared": None if rec.level_declared is None else rec.level_declared.get("kind"),
                            "convention_declared": (None if rec.convention_declared is None
                                                    else rec.convention_declared.get("kind")),
                            "close_unadj": rec.close_unadj,
                            "terminal": True})
                        break
                    except w.WriterRefusal as e:
                        row.update({"written": False, "class": _classify(str(e)), "refused": str(e),
                                    "detail": _json_safe(e.detail), "terminal": True})
                        break
                    except Exception as e:  # noqa: BLE001 — the provider's own failure, kept verbatim
                        row["attempts"].append({"attempt": attempt, "error": repr(e)})
                        if attempt < 3:
                            time.sleep(10 * attempt)
                        else:
                            row.update({"written": False, "class": "provider_error", "terminal": True,
                                        "refused": f"provider error after 3 attempts: {e!r}"})
            row["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            pout.write(json.dumps(row) + "\n")
            pout.flush()
            print(f"[pass] {i}/{len(todo)} {t}: {row['class']}" + ("" if row.get("written") else
                                                                   f" — {str(row.get('refused'))[:140]}"))
            time.sleep(args.sleep)
    rows = _done(pass_path)
    from collections import Counter
    print(f"[pass] done: {len(rows)} rows; {dict(Counter(r['class'] for r in rows.values()))}")
    return 0


# ── the guard and the label ───────────────────────────────────────────────────────

def _dates_map(cache: Path) -> Dict[str, pd.DataFrame]:
    out = {}
    for p in sorted(cache.glob("*_1d.csv")):
        t = p.name[:-7]
        pq = cache / "parquet" / f"{t}_1d.parquet"
        if pq.exists():
            df = pd.read_parquet(pq, columns=["Close"])
        else:
            df = pd.read_csv(p, usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date")
        out[t] = df
    return out


def cmd_guard(args) -> int:
    from core.census import coverage_defects
    from engines.data_manager.coverage import stale_files_record
    from engines.data_manager.membership import load_membership
    cache = Path(args.cache).resolve()
    dm = _dates_map(cache)
    intervals = None if args.static else load_membership()
    rec = stale_files_record(dm, args.start, args.end, intervals=intervals,
                             universe=(sorted(dm) if args.static else None))
    defects = coverage_defects(rec)
    summary = {"cache": str(cache), "n_files": len(dm), "window": rec["window"], "membership": rec["membership"],
               "n_stale": rec["n_stale"], "n_holed": rec["n_holed"], "n_declared": rec["n_declared"],
               "calendar": {k: (v if not isinstance(v, list) else len(v)) for k, v in rec["calendar"].items()},
               "formation_coverage": rec["formation_coverage"], "defects": defects,
               "stale_names": sorted(t for t, v in rec["names"].items()
                                     if v["ends_before_required"] and not v["end_declared_as_delisting"]),
               "holed_names": sorted(t for t, v in rec["names"].items() if v["undeclared_missing_days"]),
               "head": _head(), "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    print(json.dumps(summary, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps({"summary": summary, "record": rec}, indent=1, default=str))
    return 0 if not defects else 3


def cmd_label(args) -> int:
    from engines.data_manager.convention import cache_first_bar_frames, substrate_convention_record
    cache = Path(args.cache).resolve()
    # The witness for a cache-wide label (R9, 2026-11-04): each merge-record label is checked
    # against the FILE's first bar — the file on disk is what a run would load. Unwitnessed, a
    # merge-record label is unmeasured and the name reads unlabelled.
    rec = substrate_convention_record(cache, data_map=cache_first_bar_frames(cache))
    summary = {k: rec[k] for k in ("cache_dir", "merge_meta_present", "records_dir_present", "witness",
                                   "n_unwitnessed", "n_names", "n_labelled", "n_pre_seam_drip", "labels",
                                   "seams", "sources")}
    summary["unlabelled"] = rec["unlabelled"]
    print(json.dumps(summary, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(rec, indent=1))
    return 0 if not rec["unlabelled"] else 3


# ── the manifest staging root ─────────────────────────────────────────────────────

def cmd_stage(args) -> int:
    """A root whose data/processed IS the copy and whose other substrate dirs are the main tree's,
    so `gen_substrate_manifest.py generate --root <root>` pins the copy (never the canonical)."""
    copy = assert_is_a_copy(Path(args.copy))
    root = Path(args.root)
    if root.exists():
        raise SystemExit(f"REFUSED: {root} exists")
    main = Path(args.main).resolve()
    (root / "data").mkdir(parents=True)
    os.symlink(copy, root / "data" / "processed")
    for d in ("raw", "governor", "macro", "universe"):
        os.symlink(main / "data" / d, root / "data" / d)
    print(f"[stage] {root}: data/processed -> {copy}; raw, governor, macro, universe -> {main}/data")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("fresh-copy")
    s.add_argument("--to", required=True)
    s.set_defaults(fn=cmd_fresh_copy)
    s = sub.add_parser("pass")
    s.add_argument("--copy", required=True)
    s.add_argument("--only", default=None)
    s.add_argument("--today", default=None)
    s.add_argument("--sleep", type=float, default=0.4)
    s.add_argument("--tag", default=None)
    s.set_defaults(fn=cmd_pass)
    s = sub.add_parser("guard")
    s.add_argument("--cache", required=True)
    s.add_argument("--start", default="2000-01-03")
    s.add_argument("--end", default="2025-12-31")
    s.add_argument("--static", action="store_true", help="every name live to the window end (no PIT)")
    s.add_argument("--out", default=None)
    s.set_defaults(fn=cmd_guard)
    s = sub.add_parser("label")
    s.add_argument("--cache", required=True)
    s.add_argument("--out", default=None)
    s.set_defaults(fn=cmd_label)
    s = sub.add_parser("stage")
    s.add_argument("--copy", required=True)
    s.add_argument("--root", required=True)
    s.add_argument("--main", default="/Users/jacksonmurphy/Dev/trading_machine-2")
    s.set_defaults(fn=cmd_stage)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
