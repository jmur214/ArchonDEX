#!/usr/bin/env python3
"""Cutover step 1 (the user's OPTION (a) ruling, 2026-10-22): drive the total-return writer over a
COPY of the processed cache, read the stale/holed-files guard and the convention label on it, and
stage a root for the candidate manifest. The WRITING subcommands (fresh-copy, pass, stage) refuse a
target that resolves to any repo's `data/processed`, and only a path under `Dev/_substrate_candidates/`
is accepted as a copy; guard and label are READ-ONLY on any --cache, including the canonical one,
which label exists to lock. The real-cache write is cutover day, a separate approved act.

    python -m scripts.cutover_step1_pass fresh-copy --to <copy> [--from <copy>]   # from the canonical cache (or a copy); refuses an existing <to>
    python -m scripts.cutover_step1_pass pass --copy <copy> [--only A,B] [--today YYYY-MM-DD] [--sleep 0.4]
    python -m scripts.cutover_step1_pass era-tr --copy <copy> [--yf-dir D] [--raw-stooq D] [--only A,B] [--dry-run]   # option (a′), offline
    python -m scripts.cutover_step1_pass guard --cache <dir> --start 2000-01-03 --end 2025-12-31 [--out x.json]
    python -m scripts.cutover_step1_pass label --cache <dir> [--out x.json]
    python -m scripts.cutover_step1_pass stage --copy <copy> --root <staging_root>   # then gen_substrate_manifest.py generate --root <staging_root> --manifest ../<candidate>.sha256 --stamp-root <staging_root> (a bare --root REFUSES since re-pin #1)

`pass` is RESUMABLE (one jsonl row per file; a file with a terminal row is skipped), writes the
writer's own log (`write_log.jsonl`, the per-file records) and the PROVIDER's output UNFILTERED
(`provider.log`: everything yfinance printed or logged, per file, with the file's name as a header).
A provider exception (not a writer refusal) is retried 3 times with 10/20/30 s backoff and every
attempt's reason is kept. Every row carries the writer source's sha256 and the worktree HEAD.

`era-tr` (option (a′), USER RULING 2026-11-12, T-387) rewrites the PRE-seam span of every merged
file with pre-seam bars (the merge record's `both` files with `n_stooq_pre_seam > 0`) from the drip
to `era_tr`, through `tr_writer.era_tr_rewrite` — OFFLINE: raw Stooq from `--raw-stooq`, the
yfinance reference from the cached `--yf-dir` (refused without its `_fetch_log.jsonl`, and unless the
cache equals its pinned per-file manifest `--yf-manifest`, default
`config/era_tr_reference_yf_manifest.sha256`). It is
RESUMABLE (`era_tr_<tag>.jsonl`, one row per file). Post-seam it leaves every Date/OHLCV field, and
`close_unadj` on every row, byte-identical; ATR on the first 14 post-seam rows and PrevClose on the seam
row change by construction (functions of pre-seam bars). Run it on a DUPLICATE (`fresh-copy --from <step-1 copy>`), never on the
pinned step-1 copy itself. Exit 0 = every target written; 2 = a refusal; 3 = below --min-free-gb.
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
    # --from (T-387): a COPY of a copy — the (a′) rewrite runs on a duplicate, so the pinned step-1
    # candidate stays the object its manifest names ([NN-ARCHIVE]); the default is the canonical.
    src = MAIN_CANONICAL.resolve() if args.src is None else assert_is_a_copy(Path(args.src))
    if not src.is_dir():
        raise SystemExit(f"REFUSED: the source {src} is not a directory")
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
    # ticker-exclusions: bypassed — the pass reads EVERY file of the COPY by design (a WRITING
    # subcommand: assert_is_a_copy above refuses a repo's data/processed) and resolves no universe
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


# ── option (a′): the era-aware pre-seam rewrite (USER RULING 2026-11-12, T-387) ────

DEFAULT_YF_DIR = CANDIDATES_ROOT / "drip_fix_a_prime_2026_11_11" / "yf"
DEFAULT_RAW_STOOQ = MAIN_CANONICAL.parents[1] / "data" / "raw" / "stooq" / "daily" / "us"
#: The per-file sha256 manifest of the reference cache the (a′) bytes depend on (T-387 review MINOR-4):
#: every price and dividend parquet plus the fetch log, committed so the input is pinned in git. The
#: driver REFUSES a cache that does not equal it (`--yf-manifest none` skips, and the rows say so).
DEFAULT_YF_MANIFEST = REPO / "config" / "era_tr_reference_yf_manifest.sha256"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def yf_cache_manifest(yf_dir: Path) -> str:
    """`<sha256>  <relative path>` for EVERY regular file under the reference cache, sorted — the
    manifest the (a′) build's inputs are pinned by (the prices and dividends, not only the log)."""
    root = Path(yf_dir)
    files = sorted(q for q in root.rglob("*") if q.is_file())
    return "".join(f"{_sha256_file(q)}  {q.relative_to(root).as_posix()}\n" for q in files)


def verify_yf_manifest(yf_dir: Path, manifest_path: Path) -> str:
    """The cache's manifest must EQUAL the pinned one, line for line — or REFUSE (SystemExit) with
    the first differences. Returns the sha256 of the verified manifest text."""
    want_p = Path(manifest_path)
    if not want_p.exists():
        raise SystemExit(f"REFUSED: the reference-cache manifest {want_p} is absent — the (a′) inputs are "
                         f"unpinned; pass --yf-manifest none to run unverified (recorded in every row)")
    got, want = yf_cache_manifest(yf_dir), want_p.read_text()
    if got != want:
        g, w_ = set(got.splitlines()), set(want.splitlines())
        diff = sorted(g ^ w_)[:6]
        raise SystemExit(f"REFUSED: the reference cache {yf_dir} does not equal its pinned manifest {want_p} "
                         f"({len(g - w_)} lines differ/extra, {len(w_ - g)} missing); first: {diff}")
    return hashlib.sha256(got.encode()).hexdigest()


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def yf_fetch_state(yf_dir: Path) -> Dict[str, dict]:
    """The reference cache's own fetch log, last row per ticker. The log is what makes an ABSENT
    price file mean "fetched, the provider had none" rather than "never fetched" — so a cache
    without one is refused (a wrong --yf-dir would otherwise read as 575 no-reference names)."""
    log = Path(yf_dir) / "_fetch_log.jsonl"
    if not log.exists():
        raise SystemExit(f"REFUSED: {log} is absent — the reference cache's fetch state is unknown "
                         f"(an absent price file could mean 'never fetched'); not running")
    state: Dict[str, dict] = {}
    for line in log.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            state[r["ticker"]] = r
    return state


def reference_for(t: str, yf_dir: Path, state: Dict[str, dict]):
    """(px, divs, status) for one name from the cached reference — refusing a name the fetch log
    never saw, or one it says was fetched whose file is missing (never read as "no reference")."""
    from engines.data_manager import era_tr as et
    row = state.get(t)
    if row is None:
        return None, None, f"refused: {t} has no row in the reference fetch log (never fetched)"
    px, dv = et.read_yf(t, yf_dir)
    if row.get("prices") == "ok" and px is None:
        return None, None, f"refused: the fetch log says {t}'s prices were fetched but the file is missing"
    return px, dv, ("reference_files" if px is not None else f"no_reference ({row.get('prices')})")


def cmd_era_tr(args) -> int:
    """Rewrite every merged file's PRE-seam span in the copy from the drip to era_tr — offline,
    through the writer (`tr_writer.era_tr_rewrite`), resumable. `--dry-run` measures and writes
    nothing to the copy (only the report rows)."""
    from engines.data_manager import era_tr as et
    copy = assert_is_a_copy(Path(args.copy))
    yf_dir, raw_dir = Path(args.yf_dir).resolve(), Path(args.raw_stooq).resolve()
    meta = w.load_merge_meta(copy)
    if meta is None:
        raise SystemExit(f"REFUSED: {copy} has no {w.MERGE_META_NAME} — no seam, no drip slope")
    state = yf_fetch_state(yf_dir)
    if args.yf_manifest == "none":
        yf_pin = "UNVERIFIED: --yf-manifest none"
    else:
        yf_pin = verify_yf_manifest(yf_dir, Path(args.yf_manifest))
    raw_idx = et.raw_stooq_index(raw_dir)
    targets = sorted(t for t, r in meta.items()
                     if r.get("merge_case") == "both" and int(r.get("n_stooq_pre_seam") or 0) > 0)
    # T-394: the PINNED Tier-1 Stooq corrections (11 rows) — loaded by default, refused on a sha256 mismatch,
    # and every row must name a merged file of THIS copy before the first file is written.
    from engines.data_manager import stooq_tier1 as st1
    if args.stooq_corrections == "none":
        corrections, corr_pin = None, "NOT APPLIED: --stooq-corrections none (the output is v5)"
    else:
        try:
            corrections = st1.load_tier1()
            st1.check_universe(corrections, targets)
        except st1.StooqTier1Refusal as e:
            raise SystemExit(f"REFUSED: {e}")
        corr_pin = corrections.sha256
    if args.only:
        wanted = [t.strip() for t in args.only.split(",") if t.strip()]
        missing = sorted(set(wanted) - set(targets))
        if missing:
            raise SystemExit(f"REFUSED: --only names that are not merged files with pre-seam bars: {missing}")
        targets = wanted
    out_dir = Path(args.out_dir) if args.out_dir else copy.parent
    tag = args.tag or f"{copy.name}{'_dryrun' if args.dry_run else ''}"
    rows_path = out_dir / f"era_tr_{tag}.jsonl"
    write_log = None if args.dry_run else out_dir / f"era_tr_write_log_{tag}.jsonl"
    done = _done(rows_path)
    todo = [t for t in targets if t not in done]
    provenance = {"yf_dir": str(yf_dir), "yf_fetch_log_md5": _md5(yf_dir / "_fetch_log.jsonl"),
                  "yf_manifest": (None if args.yf_manifest == "none" else str(Path(args.yf_manifest).resolve())),
                  "yf_manifest_sha256": yf_pin,
                  "raw_stooq_dir": str(raw_dir), "writer_sha256": _writer_sha(), "head": _head(),
                  "stooq_corrections_tier1_sha256": corr_pin,
                  "era_tr_sha256": hashlib.sha256((REPO / "engines" / "data_manager" / "era_tr.py").read_bytes()).hexdigest()}
    print(f"[era-tr] {len(targets)} merged files with pre-seam bars, {len(done)} done, {len(todo)} to do; "
          f"dry_run={args.dry_run}; {provenance}")
    out_dir.mkdir(parents=True, exist_ok=True)
    n_ok = n_ref = 0
    with open(rows_path, "a") as rout:
        for i, t in enumerate(todo, 1):
            if shutil.disk_usage(copy).free < args.min_free_gb * 1024 ** 3:
                print(f"[era-tr] HALT: free disk below {args.min_free_gb:.0f} GB at {t}")
                return 3
            row = {"ticker": t, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "dry_run": bool(args.dry_run), "terminal": True}
            px, dv, ref_state = reference_for(t, yf_dir, state)
            row["reference_files"] = ref_state
            try:
                if ref_state.startswith("refused"):
                    raise w.WriterRefusal(f"{t}: {ref_state}")
                stooq = et.read_raw_stooq(raw_idx[t]) if t in raw_idx else None
                rec = w.era_tr_rewrite(t, copy, stooq=stooq, reference_px=px, reference_divs=dv,
                                       write=not args.dry_run, provenance=provenance, log_path=write_log,
                                       stooq_corrections=corrections)
                b = rec["era_tr"]
                row["stooq_corrections_applied"] = len(b["stooq_corrections"]["applied"])
                row["unverified_stooq_corrections"] = (None if b["unverified_stooq_corrections"] is None else
                                                       {k: b["unverified_stooq_corrections"][k] for k in ("n_steps", "n_blocks")})
                row.update({"written": not args.dry_run, "would_write": True, "convention": rec["convention"],
                            "reference": b["reference"], "n_div_added": b["n_div_added"],
                            "splice": b["splice"], "k_splice": b["k_splice"],
                            "unverified_missed_era_spans": b["unverified_missed_era_spans"],
                            "unverified_pre2003_span": b["unverified_pre2003_span"],
                            "step_audit": b["rails"]["step_audit"], "splice_audit": b["rails"]["splice_audit"],
                            "carried_columns": b["carried_columns"]})
                n_ok += 1
            except w.WriterRefusal as e:
                row.update({"written": False, "would_write": False, "refused": str(e),
                            "detail": _json_safe(e.detail)})
                n_ref += 1
            rout.write(json.dumps(row, default=str) + "\n")
            rout.flush()
            if i % 50 == 0 or "refused" in row:
                print(f"[era-tr] {i}/{len(todo)} {t}: " + ("REFUSED — " + row["refused"][:160] if "refused" in row
                                                         else f"ok (added {row['n_div_added']})"), flush=True)
    rows = _done(rows_path)
    n_refused = sum(1 for r in rows.values() if "refused" in r)
    print(f"[era-tr] done: {len(rows)} rows ({n_ok} ok, {n_ref} refused this run; {n_refused} refused in all) -> {rows_path}")
    return 0 if n_refused == 0 else 2


# ── the guard and the label ───────────────────────────────────────────────────────

def _dates_map(cache: Path) -> Dict[str, pd.DataFrame]:
    out = {}
    # The guard and the label read EVERY file of any --cache dir by design — the COPY or the canonical
    # cache itself (which label exists to lock): a cache-wide, READ-ONLY reading of what the files hold.
    # ticker-exclusions: bypassed — a cache-wide read-only reading; nothing is resolved or served to a run
    for p in sorted(cache.glob("*_1d.csv")):
        t = p.name[:-7]
        pq = cache / "parquet" / f"{t}_1d.parquet"   # ticker-exclusions: bypassed — the file's parquet twin, the same cache-wide read
        if pq.exists():
            # ticker-exclusions: bypassed — the same cache-wide read, from the file's own parquet
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
    # cache_dir = the cache being read (2026-11-04): the kept drip's own pre-seam holes are excused
    # under the COUNTED pre_seam_drip_gap class, witnessed against this cache's own files and records.
    rec = stale_files_record(dm, args.start, args.end, intervals=intervals,
                             universe=(sorted(dm) if args.static else None), cache_dir=cache)
    defects = coverage_defects(rec)
    dg = rec["pre_seam_drip_gaps"]
    summary = {"cache": str(cache), "n_files": len(dm), "window": rec["window"], "membership": rec["membership"],
               "n_stale": rec["n_stale"], "n_holed": rec["n_holed"], "n_declared": rec["n_declared"],
               "pre_seam_drip_gaps": {"n_names": dg["n_names"], "n_days": dg["n_days"],
                                      "n_not_excused": len(dg["not_excused"])},
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
    so `gen_substrate_manifest.py generate --root <root> --manifest ../<candidate>.sha256 --stamp-root <root>`
    pins the copy (never the canonical); without --manifest/--stamp-root `generate` REFUSES (exit 4, re-pin #1 C3)."""
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
    s.add_argument("--from", dest="src", default=None,
                   help="a COPY to duplicate (T-387: the (a′) rewrite runs on a duplicate of the step-1 copy); default the canonical")
    s.set_defaults(fn=cmd_fresh_copy)
    s = sub.add_parser("pass")
    s.add_argument("--copy", required=True)
    s.add_argument("--only", default=None)
    s.add_argument("--today", default=None)
    s.add_argument("--sleep", type=float, default=0.4)
    s.add_argument("--tag", default=None)
    s.set_defaults(fn=cmd_pass)
    s = sub.add_parser("era-tr", help="option (a′): rewrite every merged file's pre-seam span to era_tr (offline)")
    s.add_argument("--copy", required=True)
    s.add_argument("--yf-dir", default=str(DEFAULT_YF_DIR))
    s.add_argument("--raw-stooq", default=str(DEFAULT_RAW_STOOQ))
    s.add_argument("--yf-manifest", default=str(DEFAULT_YF_MANIFEST),
                   help="the reference cache's pinned per-file sha256 manifest (refuses a mismatch); 'none' skips — scratch/test only, NEVER on cutover day (rows are marked UNVERIFIED)")
    s.add_argument("--only", default=None)
    s.add_argument("--tag", default=None)
    s.add_argument("--out-dir", default=None, help="where the report rows go (default: beside the copy)")
    s.add_argument("--dry-run", action="store_true", help="measure only: nothing in the copy is written")
    s.add_argument("--min-free-gb", type=float, default=11.0)
    s.add_argument("--stooq-corrections", choices=["pinned", "none"], default="pinned",
                   help="T-394: apply the 11 pinned Tier-1 rows (default); 'none' writes v5 and says so in every row")
    s.set_defaults(fn=cmd_era_tr)
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
