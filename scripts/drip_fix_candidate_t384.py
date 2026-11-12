"""T-384 — candidate fix ("option (a′)") for the era-wrong pre-seam drip in the price cache.

THE DEFECT (health_check.md HIGH, 2026-11-11). The canonical cache `data/processed/<T>_1d.csv`
merges raw Stooq (before each name's seam) with Alpaca total return (after it). The T-082b merge
(`scripts/merge_stooq_alpaca_substrate.py`) assumed Stooq is total return and multiplied every
pre-seam bar by a fitted exp(a + b·t). Raw Stooq is dividend-adjusted by ERA (≈ 0 % of each
dividend missed for ex-dates 2011-Q2 → 2022-Q4, ≈ 100 % missed 2003-Q2 → 2011-Q1 and from
2023-Q1), so b — Stooq's missed 2023+ dividends smeared over the overlap — is applied back on top
of bars that were already total return (over-count 2011-Q2 → seam) and does not replace the
dividends Stooq really missed (under-count 2003-Q2 → 2011-Q1).

THE CANDIDATE. For every merged file with pre-seam bars:
  1. undo the drip: pre-seam closes × exp(−b·(t − seam)) recovers the Stooq series the merge read
     (proven against the raw bundle: the ratio must be constant to the rounding floor);
  2. add back, in full, every dividend Stooq MISSED — per name, era edges measured from data
     (the per-ex-date fraction-missed probe against a yfinance reference), global edges only
     where no reference exists; dividends from yfinance for live names; a labelled per-era-year
     cross-sectional-median yield drift for names with no dividend source;
  3. splice to the Alpaca leg with ONE constant at the seam (the Stooq seam-day return kept);
  4. post-seam OHLCV is copied as TEXT, byte for byte.

It NEVER writes inside the repository's `data/` tree: the candidate lands under
`/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/` (outside the repo)
for the user's ruling. The canonical writer (`engines/data_manager/tr_writer.py`) and the merge
script are NOT edited. Network: yfinance only (Adj Close via `fetch_yf_tr` of
`scripts/reconcile_stooq_tr_t256.py`, loaded by path — its writer is never called; dividends via
`yfinance.Ticker(...).dividends`), cached under the candidate directory.

Proposal + pre-declared acceptance test: `docs/Sources/proposal_drip_fix_a_prime_2026-11-11.md`.

T-387 (USER RULING 2026-11-12: the cutover adopts (a′) v4): the era model, the probe, the labels,
the reference analysis and the per-file build MOVED to `engines/data_manager/era_tr.py` — the ONE
implementation the cutover writer (`tr_writer.era_tr_rewrite`) also calls. This script imports them
and keeps its own fetch / build / accept / manifest commands and the v1–v3-only helpers.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engines.data_manager import era_tr as _et  # noqa: E402  — the ONE (a′) implementation (T-387)
from engines.data_manager.era_tr import (  # noqa: E402,F401  — re-exported: the tests and records name them here
    BLIP_MAX_BARS, BLIP_MIN, BLIP_REVERT_TOL, CONFIDENT_SM, FULL_YEAR_BARS, GLOBAL_BLOCK_EDGES,
    GLOBAL_MISSED_ERAS, IDENTITY_CORR, IDENTITY_MED_ABS_D, MAX_DIV_FRACTION, MISSED_M, NOISE_WINDOW,
    OHLC, PRE_REFERENCE_STUB_DAYS, PROBE_LEVEL_BARS, SEAM_TEXT_ROWS, STEP_TOL, BuildResult,
    NameReference, align_reference, analyse_reference, build_file, era_runs, global_block,
    global_missed, label_exdates, mask_runs, missed_log_factor, probe_exdates, read_raw_stooq, read_yf,
    recompute_derived, transient_offsets, year_identity)
from engines.data_manager.era_tr import EraTrRefusal as CandidateRefusal  # noqa: E402  — the script's name for it
from engines.data_manager.tr_writer import write_text_pair_atomically  # noqa: E402

CACHE_DIR = REPO / "data" / "processed"
META_PATH = CACHE_DIR / "_merge_meta.json"
RAW_STOOQ_GLOB = str(REPO / "data" / "raw" / "stooq" / "daily" / "us" / "*" / "*" / "*.us.txt")
T265_DIR = REPO / "data" / "research" / "t265" / "prices"
V3_OUT = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11")
#: v4 (independent review, 2026-11-11) writes to a NEW directory; v3 is kept as it is.
DEFAULT_OUT = Path("/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11")
#: The yfinance cache fetched for v1–v3 (read-only from v4 on; its md5s are in v3's MANIFEST.md5).
DEFAULT_YF = V3_OUT / "yf"

FETCH_START = "1962-01-01"
FETCH_END = "2026-11-11"


# ═══════════════════════════════════════════════════════════════════════════════
# Write-location guard (fail closed: the candidate never lands in canon)
# ═══════════════════════════════════════════════════════════════════════════════

def assert_outside_canon(out_dir: Path) -> Path:
    """Refuse any output directory inside the repository's data tree or the canonical cache."""
    out = Path(os.path.realpath(out_dir))
    forbidden = [Path(os.path.realpath(REPO / "data")),
                 Path(os.path.realpath(CACHE_DIR)),
                 Path(os.path.realpath(REPO))]
    main_repo_data = Path("/Users/jacksonmurphy/Dev/trading_machine-2/data")
    forbidden.append(Path(os.path.realpath(main_repo_data)))
    for f in forbidden:
        if out == f or f in out.parents:
            raise SystemExit(f"REFUSED: output {out} is inside {f} (canonical/repo tree)")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Readers
# ═══════════════════════════════════════════════════════════════════════════════

def load_meta() -> Dict[str, dict]:
    with open(META_PATH) as fh:
        return json.load(fh)["per_ticker"]


def preseam_universe(meta: Dict[str, dict]) -> List[str]:
    """Every merged ('both') file that carries pre-seam (Stooq) bars."""
    return sorted(t for t, r in meta.items()
                  if r.get("merge_case") == "both" and int(r.get("n_stooq_pre_seam") or 0) > 0)


def raw_stooq_index() -> Dict[str, str]:
    return _et.raw_stooq_index(Path(RAW_STOOQ_GLOB).parents[2])


def read_cache_text(ticker: str, cache_dir: Path = CACHE_DIR) -> Tuple[str, List[str]]:
    """The cached CSV as (header, data lines) — text, so post-seam rows can be copied verbatim."""
    # ticker-exclusions: bypassed — data-ops: the substrate-repair candidate reads/rewrites EVERY merged file; the measurement-universe exclusion does not apply to a cache rewrite (output outside the repo)
    return _et.read_cache_text(cache_dir / f"{ticker}_1d.csv")


def read_cache_frame(ticker: str, cache_dir: Path = CACHE_DIR) -> pd.DataFrame:
    # ticker-exclusions: bypassed — data-ops: the substrate-repair candidate reads/rewrites EVERY merged file; the measurement-universe exclusion does not apply to a cache rewrite (output outside the repo)
    return _et.read_cache_frame(cache_dir / f"{ticker}_1d.csv")


def read_t265(ticker: str) -> Optional[pd.Series]:
    p = T265_DIR / f"{ticker}.parquet"
    if not p.exists():
        return None
    s = pd.read_parquet(p, columns=["close"])["close"].astype(float)
    s.index = pd.to_datetime(s.index).normalize()
    return s.sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
# yfinance fetch (cache under the candidate directory only)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_fetch_yf_tr() -> Callable:
    """`fetch_yf_tr` from scripts/reconcile_stooq_tr_t256.py, loaded by path (top level is
    imports + constants only; its writer/main is never called)."""
    spec = importlib.util.spec_from_file_location(
        "_t256_reconcile", REPO / "scripts" / "reconcile_stooq_tr_t256.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.fetch_yf_tr


def _yahoo_symbol(ticker: str) -> str:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from engines.data_manager.yahoo_symbols import yahoo_symbol  # lazy package: json/re only
    sym, _kind = yahoo_symbol(ticker)
    return sym


def fetch_dividends(symbol: str, retries: int = 3) -> Tuple[Optional[pd.Series], str]:
    """yfinance dividend history (split-adjusted per-share cash, by ex-date). Returns (series,
    status). An EMPTY series is a valid answer ("no dividends") only when the call succeeded."""
    import yfinance as yf
    last_err = ""
    for attempt in range(retries):
        try:
            s = yf.Ticker(symbol).dividends
            if s is None:
                return None, "none_returned"
            s = s.astype(float)
            idx = pd.DatetimeIndex(s.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            s.index = idx.normalize()
            s.index.name = "ex_date"
            return s.rename("dividend").sort_index(), "ok"
        except Exception as exc:  # noqa: BLE001 — provider errors are logged verbatim, retried
            last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return None, f"error: {last_err}"


def cmd_fetch(args: argparse.Namespace) -> int:
    out = assert_outside_canon(Path(args.out))
    ydir = assert_outside_canon(Path(args.yf_dir))
    ydir.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    tickers = list(args.tickers) if args.tickers else (["SPY"] + preseam_universe(meta))
    fetch_yf_tr = _load_fetch_yf_tr()
    log_path = ydir / "_fetch_log.jsonl"
    for i, t in enumerate(tickers):
        px_path = ydir / f"{t}.parquet"
        dv_path = ydir / f"{t}__div.parquet"
        if px_path.exists() and dv_path.exists() and not args.refetch:
            continue
        sym = _yahoo_symbol(t)
        rec: dict = {"ticker": t, "symbol": sym, "at": datetime.now(timezone.utc).isoformat()}
        tr, close = fetch_yf_tr(sym, FETCH_START, FETCH_END)
        if tr is None or close is None or len(tr) == 0:
            rec["prices"] = "no_data"
        else:
            px = pd.DataFrame({"adj_close": tr["Close"].astype(float),
                               "close": close.astype(float)})
            idx = pd.DatetimeIndex(px.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            px.index = idx.normalize()
            px.index.name = "Date"
            px = px[~px.index.duplicated(keep="last")].sort_index()
            px.to_parquet(px_path)
            rec.update(prices="ok", n=int(len(px)), first=str(px.index[0].date()),
                       last=str(px.index[-1].date()))
        divs, status = fetch_dividends(sym)
        rec["dividends"] = status
        if divs is not None:
            divs.to_frame().to_parquet(dv_path)
            rec["n_div"] = int(len(divs))
        with open(log_path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"[{i + 1}/{len(tickers)}] {t} ({sym}): prices={rec['prices']} div={status}"
              f" n_div={rec.get('n_div')}", flush=True)
        time.sleep(args.sleep)
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# The era model — what Stooq's dividend adjustment covers
# ═══════════════════════════════════════════════════════════════════════════════

#: The era model (GLOBAL_MISSED_ERAS, the probe and its constants, the labels, missed_log_factor)
#: lives in `engines/data_manager/era_tr.py` (T-387) and is imported above. Only the v1–v3
#: approximation stays here, so the v3 record stays reproducible.
MIN_FREE_BYTES = 15 * 1024 ** 3   # halt the write pass below 15 GB free (shared 8 GB / ~20 GB host)


def approx_log_factor(dates: pd.DatetimeIndex, mask: np.ndarray, yield_by_year: pd.Series) -> np.ndarray:
    """v1–v3 ONLY — v4's `build_file` never calls this (independent review, MAJOR-1, 2026-11-11: with
    no payer reference it ADDED ≈ 1.1 pp/yr of dividends to known non-payers HOLX/SATS/BBBY and the
    near-non-payer CTRA, and under-counted the REIT/high-yield AVB/EQR/LEG). Kept, with its test, so
    the v3 record stays reproducible. Original contract below.

    The LABELLED approximation for a span with no dividend source: inside `mask` (a missed era
    with no reference) each bar carries a drift of Y(year)/B(year), Y = the cross-sectional median
    annual log dividend yield of the reference-backed universe that year, B = the business days in
    that calendar year (amendment A2: v1 divided by the bars PRESENT, so a stub year — CHTR's
    December 2009 — received a whole year's yield in a month)."""
    yrs = dates.year
    uniq = np.unique(yrs)
    bdays = {int(y): len(pd.bdate_range(f"{y}-01-01", f"{y}-12-31")) for y in uniq}
    n_in_year = np.array([bdays[int(y)] for y in uniq])[np.searchsorted(uniq, yrs)]
    yld = yield_by_year.reindex(yrs).to_numpy()
    if mask.any() and np.isnan(yld[mask]).any():
        missing = sorted(set(yrs[mask & np.isnan(yld)]))
        raise RuntimeError(f"no cross-sectional yield for years {missing} (fail closed)")
    per_bar = np.where(mask, -np.nan_to_num(yld) / n_in_year, 0.0)
    total = per_bar.sum()
    return total - np.cumsum(per_bar)


# ═══════════════════════════════════════════════════════════════════════════════
# Per-name reference analysis (probe → labels → reference coverage)
# ═══════════════════════════════════════════════════════════════════════════════

# NameReference, analyse_reference and era_runs: `engines/data_manager/era_tr.py` (imported above).


# ═══════════════════════════════════════════════════════════════════════════════
# The per-file candidate
# ═══════════════════════════════════════════════════════════════════════════════

# CandidateRefusal (= era_tr.EraTrRefusal), recompute_derived, BuildResult, mask_runs and build_file:
# `engines/data_manager/era_tr.py` (imported above) — the cutover writer calls the same build_file.


# ═══════════════════════════════════════════════════════════════════════════════
# The build pass (two passes: every reference first — the cross-sectional yields need the
# whole universe — then one file at a time)
# ═══════════════════════════════════════════════════════════════════════════════

def _free_bytes(path: Path) -> int:
    import shutil
    return shutil.disk_usage(path).free


def xs_median_yield(refs: Dict[str, NameReference]) -> pd.Series:
    """Median annual dividend log-yield across reference-backed names (non-payers count as 0)."""
    cols = {t: r.yearly_yield for t, r in refs.items()
            if r.status == "reference" and r.yearly_yield is not None and len(r.yearly_yield)}
    if not cols:
        raise RuntimeError("no reference-backed name: the cross-sectional yield is undefined (fail closed)")
    panel = pd.DataFrame(cols)
    med = panel.median(axis=1, skipna=True)
    med.index.name = "year"
    return med.rename("xs_median_log_yield")


def write_pair(out_dir: Path, ticker: str, text: str) -> Tuple[Path, Path]:
    """csv (the text, verbatim) + parquet (parsed from that text), mirroring the cache layout —
    through the cutover writer's own atomic text pair (T-387: one writer of the (a′) bytes)."""
    # ticker-exclusions: bypassed — data-ops: the substrate-repair candidate reads/rewrites EVERY merged file; the measurement-universe exclusion does not apply to a cache rewrite (output outside the repo)
    csv_p = out_dir / f"{ticker}_1d.csv"
    pq_p = out_dir / "parquet" / f"{ticker}_1d.parquet"
    write_text_pair_atomically(text, _et.frame_from_text(text), pq_p, csv_p)
    return csv_p, pq_p


def cmd_build(args: argparse.Namespace) -> int:
    out = assert_outside_canon(Path(args.out))
    ydir, pdir = assert_outside_canon(Path(args.yf_dir)), out / "processed"
    (out / "probe" / "labels").mkdir(parents=True, exist_ok=True)
    pdir.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    raw_idx = raw_stooq_index()
    universe = preseam_universe(meta)
    targets = list(args.tickers) if args.tickers else universe

    refs: Dict[str, NameReference] = {}
    for t in targets:    # pass 1: every reference (v4: no cross-sectional median is needed)
        if t not in raw_idx:
            refs[t] = NameReference(t, "no_raw_stooq", _et.empty_labels())
            continue
        px, dv = read_yf(t, ydir)
        refs[t] = analyse_reference(t, read_raw_stooq(raw_idx[t]), px, dv, pd.Timestamp(meta[t]["seam_date"]))
        if not refs[t].labels.empty:
            refs[t].labels.drop(columns=["pos"]).to_parquet(out / "probe" / "labels" / f"{t}.parquet")
    print(f"[build] pass 1: {sum(r.status == 'reference' for r in refs.values())} reference-backed of "
          f"{len(targets)} (yf: {ydir}); statuses {pd.Series([r.status for r in refs.values()]).value_counts().to_dict()}")

    rec_path = out / "build_records.jsonl"
    n_ok = n_ref = 0
    with open(rec_path, "w") as rec_fh:
        for i, t in enumerate(targets):
            if _free_bytes(out) < args.min_free_gb * 1024 ** 3:
                print(f"[build] HALT: free disk below {args.min_free_gb:.0f} GB at {t}")
                return 3
            try:
                if t not in raw_idx:
                    raise CandidateRefusal(f"{t}: no raw Stooq file")
                header, lines = read_cache_text(t)
                res = build_file(t, meta[t], header, lines, read_cache_frame(t),
                                 read_raw_stooq(raw_idx[t]), refs[t])
                write_pair(pdir, t, res.text)
                rec = {"status": "written", **res.record}
                n_ok += 1
            except CandidateRefusal as exc:
                rec = {"status": "refused", "ticker": t, "reason": str(exc)}
                n_ref += 1
            rec_fh.write(json.dumps(rec, default=str) + "\n")
            if (i + 1) % 50 == 0:
                print(f"[build] {i + 1}/{len(targets)} written={n_ok} refused={n_ref}", flush=True)
    print(f"[build] done: written={n_ok} refused={n_ref} -> {pdir}")
    return 0 if n_ref == 0 else 2


def cmd_manifest(args: argparse.Namespace) -> int:
    out = assert_outside_canon(Path(args.out))
    lines = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.md5":
            h = hashlib.md5()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            lines.append(f"{h.hexdigest()}  {p.relative_to(out)}")
    body = "\n".join(lines) + "\n"
    (out / "MANIFEST.md5").write_text(body)
    print(f"[manifest] {len(lines)} files; aggregate md5 {hashlib.md5(body.encode()).hexdigest()}")
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Acceptance (the pre-declared test, proposal §1 — thresholds are constants, not arguments)
# ═══════════════════════════════════════════════════════════════════════════════

T265_TOL_PP = 0.05
T265_CENT = 0.005
YF_MEDIAN_PP = 0.05
YF_P95_PP = 0.30
YF_MIN_NAMES = 100
NONPAYER_TOL_PP = 1e-6
# STEP_TOL (1e-10, the v4 step audit's float floor) is the shared constant, imported above.


def yearly_periods(a: pd.Series, b: pd.Series) -> pd.DataFrame:
    """Calendar-year log returns of a and b on their common dates: from the last common date of
    year y−1 (or the first common date) to the last common date of year y. Labelled by y."""
    cols = ["year", "start", "end", "lr_a", "lr_b", "x_pp", "b_start", "b_end", "full_year"]
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    j = j[(j > 0).all(axis=1)]
    if len(j) < 2:
        return pd.DataFrame(columns=cols)
    pts = pd.concat([j.iloc[[0]], j.groupby(j.index.year).tail(1)])
    pts = pts[~pts.index.duplicated(keep="first")].sort_index()
    if len(pts) < 2:
        return pd.DataFrame(columns=cols)
    lg = np.log(pts)
    st, en = pts.index[:-1], pts.index[1:]
    lr_a = np.diff(lg["a"].to_numpy())
    lr_b = np.diff(lg["b"].to_numpy())
    is_ye = lambda d: (d.month == 12) & (d.day >= 24)   # noqa: E731
    full = is_ye(st) & is_ye(en) & (en.year - st.year == 1)
    return pd.DataFrame({"year": en.year, "start": st, "end": en, "lr_a": lr_a, "lr_b": lr_b,
                         "x_pp": 100 * (lr_a - lr_b), "b_start": pts["b"].to_numpy()[:-1],
                         "b_end": pts["b"].to_numpy()[1:], "full_year": full})


def _cand_close(out: Path, t: str) -> pd.Series:
    # ticker-exclusions: bypassed — data-ops: the substrate-repair candidate reads/rewrites EVERY merged file; the measurement-universe exclusion does not apply to a cache rewrite (output outside the repo)
    df = pd.read_csv(out / "processed" / f"{t}_1d.csv", usecols=["Date", "Close"],
                     float_precision="round_trip")
    return pd.Series(df["Close"].to_numpy(dtype=float), index=pd.to_datetime(df["Date"]), name="cand")


def _cache_close(t: str) -> pd.Series:
    # ticker-exclusions: bypassed — data-ops: the substrate-repair candidate reads/rewrites EVERY merged file; the measurement-universe exclusion does not apply to a cache rewrite (output outside the repo)
    df = pd.read_csv(CACHE_DIR / f"{t}_1d.csv", usecols=["Date", "Close"], float_precision="round_trip")
    return pd.Series(df["Close"].to_numpy(dtype=float), index=pd.to_datetime(df["Date"]), name="cache")


def check_post_seam_bytes(cand_lines: List[str], cache_lines: List[str], n_pre: int) -> List[str]:
    """Test (iv) on text. Returns the list of violations (empty = pass)."""
    bad: List[str] = []
    if len(cand_lines) != len(cache_lines):
        return [f"row count {len(cand_lines)} != {len(cache_lines)}"]
    for i, (a, c) in enumerate(zip(cand_lines, cache_lines)):
        fa, fc = a.split(","), c.split(",")
        if i < n_pre:
            if fa[0] != fc[0] or fa[5] != fc[5]:
                bad.append(f"pre-seam row {i} Date/Volume")
        else:
            if fa[:6] != fc[:6]:
                bad.append(f"post-seam row {i} OHLCV")
            if i >= n_pre + SEAM_TEXT_ROWS and fa[6] != fc[6]:
                bad.append(f"post-seam row {i} ATR")
            if i > n_pre and fa[7] != fc[7]:
                bad.append(f"post-seam row {i} PrevClose")
        if len(bad) > 5:
            break
    return bad


LARGE_DISTRIBUTION = 0.08      # D/P_prev at or above this: a spin-off / special (vendors differ)


def year_diagnostics(out: Path, ticker: str) -> Dict[int, dict]:
    """Per calendar year, from the labelled ex-dates: the witnesses the §1.2 cause classes read."""
    p = out / "probe" / "labels" / f"{ticker}.parquet"
    if not p.exists():
        return {}
    lab = pd.read_parquet(p)
    if lab.empty:
        return {}
    lab["year"] = pd.DatetimeIndex(lab["day"]).year
    lab["dp"] = lab["D"] / lab["P_prev"]
    conf = lab["confident"].astype(bool)
    lab["partial"] = conf & (lab["m"] > 0.25) & (lab["m"] < 0.75)
    lab["extreme"] = conf & ((lab["m"] < -0.25) | (lab["m"] > 1.25))
    lab["global"] = lab["label_source"] == "global"
    g = lab.groupby("year")
    d = pd.DataFrame({"n_div": g.size(), "n_added": g["missed"].sum(), "max_dp": g["dp"].max(),
                      "n_partial": g["partial"].sum(), "n_extreme": g["extreme"].sum(),
                      "n_global_label": g["global"].sum()})
    return {int(y): {k: (float(v) if k == "max_dp" else int(v)) for k, v in row.items()}
            for y, row in d.iterrows()}


def classify_failure(row: pd.Series, test: str) -> str:
    """The §1.2 cause classes, in order. A class EXPLAINS a failure; it never excuses one."""
    if test == "i" and pd.notna(row.get("x_yf_vs_t265_pp")) and \
            abs(row["x_yf_vs_t265_pp"]) > T265_TOL_PP + row.get("floor_pp", 0.0):
        return "reference_disagreement (yfinance and T-265 differ)"
    def pos(key: str) -> bool:
        v = row.get(key)
        return v is not None and pd.notna(v) and float(v) > 0
    if pos("max_dp") and float(row["max_dp"]) >= LARGE_DISTRIBUTION:
        return "reference_disagreement (large distribution / spin-off)"
    if pos("n_extreme"):
        return "reference_disagreement (ex-date m outside [-0.25, 1.25])"
    if test == "i" and pd.notna(row.get("med_abs_daily_vs_t265")) and row["med_abs_daily_vs_t265"] > IDENTITY_MED_ABS_D:
        return "identity"
    if pos("n_partial"):
        return "partial_adjustment"
    if pos("n_global_label"):
        return "unlabelled_exdate (global rule)"
    if test == "i" and bool(row.get("seam_stub", False)):
        return ("splice (a Stooq transient offset on the bar before the seam)"
                if bool(row.get("endpoint_in_offset", False)) else "splice")
    if bool(row.get("endpoint_in_offset", False)):
        return "other: a Stooq transient offset at a period endpoint (inherited from raw Stooq)"
    return "other"


def _membership_sectors() -> Dict[str, str]:
    p = REPO / "data" / "universe" / "sp500_membership.parquet"
    if not p.exists():
        return {}
    m = pd.read_parquet(p, columns=["ticker", "sector"]).dropna()
    return m.drop_duplicates("ticker").set_index("ticker")["sector"].to_dict()


def cmd_accept(args: argparse.Namespace) -> int:
    out = assert_outside_canon(Path(args.out))
    adir = out / "acceptance"
    adir.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    raw_idx = raw_stooq_index()
    recs = {}
    with open(out / "build_records.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            recs[r["ticker"]] = r
    written = sorted(t for t, r in recs.items() if r["status"] == "written")
    sectors = _membership_sectors()
    rows_i, rows_ii, rows_iii, rows_iv, rows_era, rows_b = [], [], [], [], [], []
    rows_iiic, rows_step = [], []
    era_edges = [("pre_2000", None, pd.Timestamp("2000-01-01")),
                 ("2000_to_2003Q1", pd.Timestamp("2000-01-01"), pd.Timestamp("2003-04-01")),
                 ("2003Q2_to_2011Feb", pd.Timestamp("2003-04-01"), pd.Timestamp("2011-02-21")),
                 ("2011Feb_to_seam", pd.Timestamp("2011-02-21"), None)]
    for n, t in enumerate(written):
        r = recs[t]
        seam = pd.Timestamp(r["seam"])
        cand, cache = _cand_close(out, t), _cache_close(t)
        n_pre = int(r["n_pre"])
        n_i0, n_ii0 = len(rows_i), len(rows_ii)
        # (iv) bytes, re-read from disk
        _, cache_lines = read_cache_text(t)
        _, cand_lines = read_cache_text(t, out / "processed")
        viol = check_post_seam_bytes(cand_lines, cache_lines, n_pre)
        rows_iv.append({"ticker": t, "pass": not viol, "violations": "; ".join(viol)})
        # era deltas (candidate − cache), pp per year
        log_f = np.log(cand / cache)
        for name, lo, hi in era_edges:
            sel = log_f[(log_f.index < seam) if hi is None else (log_f.index < min(hi, seam))]
            if lo is not None:
                prior = log_f[log_f.index < lo]
                sel = sel[sel.index >= lo]
                if sel.empty:
                    continue
                start_v, start_d = (prior.iloc[-1], prior.index[-1]) if len(prior) else (sel.iloc[0], sel.index[0])
            else:
                if sel.empty:
                    continue
                start_v, start_d = sel.iloc[0], sel.index[0]
            if hi is None:   # through the seam bar (log_f = 0 there): includes the splice return
                end_v, end_d = float(log_f.loc[seam]), seam
            else:
                end_v, end_d = sel.iloc[-1], sel.index[-1]
            yrs = (end_d - start_d).days / 365.25
            if yrs < 0.25:
                continue
            rows_era.append({"ticker": t, "era": name, "years": yrs,
                             "delta_pp_per_year": 100 * (end_v - start_v) / yrs, "seam": r["seam"]})
        px, dv = read_yf(t, Path(args.yf_dir))
        raw = read_raw_stooq(raw_idx[t])
        diag = year_diagnostics(out, t)
        # (i) T-265
        t265 = read_t265(t)
        if t265 is not None:
            c_i = cand[(cand.index <= seam) & (cand.index >= "2016-01-01")]
            k_i = cache[(cache.index <= seam) & (cache.index >= "2016-01-01")]
            ref_i = t265[t265.index <= seam]
            pi = yearly_periods(c_i, ref_i)
            pk = yearly_periods(k_i, ref_i)
            # the two references against each other, on the same dates (a corporate-action witness)
            yf_vs = {}
            if px is not None:
                pr = yearly_periods(px["adj_close"].reindex(c_i.index).dropna(), ref_i)
                yf_vs = {(row.start, row.end): row.x_pp for row in pr.itertuples()}
            # the candidate against T-265, day by day (an identity witness)
            jd = pd.concat([c_i.rename("c"), ref_i.rename("r")], axis=1, join="inner").dropna()
            jd = jd[(jd > 0).all(axis=1)]
            dsig = (np.log(jd).diff()["c"] - np.log(jd).diff()["r"]).fillna(0.0)
            med_d = dsig.abs().groupby(jd.index.year).median()
            off_i = pd.Series(transient_offsets(dsig.to_numpy()), index=jd.index)
            for (_, p), (_, q) in zip(pi.iterrows(), pk.iterrows()):
                if p["year"] < 2016:
                    continue
                y = int(p["year"])
                floor = 100 * (T265_CENT / p["b_start"] + T265_CENT / p["b_end"])
                ends_off = bool(off_i.get(p["start"], False)) or bool(off_i.get(p["end"], False))
                if bool(p["end"] == seam):   # the stub's start is the bar before the seam
                    ends_off = bool(off_i.get(p["start"], False))
                rows_i.append({"ticker": t, "year": y, "start": p["start"], "end": p["end"],
                               "seam_stub": bool(p["end"] == seam), "x_pp": p["x_pp"],
                               "x_cache_pp": q["x_pp"], "floor_pp": floor,
                               "x_yf_vs_t265_pp": yf_vs.get((p["start"], p["end"]), np.nan),
                               "med_abs_daily_vs_t265": float(med_d.get(y, np.nan)),
                               "endpoint_in_offset": ends_off,
                               **diag.get(y, {}),
                               "pass": abs(p["x_pp"]) <= T265_TOL_PP + floor,
                               "pass_strict": abs(p["x_pp"]) <= T265_TOL_PP})
        # (ii) yfinance 2000-2015 and (iii) non-payers
        if px is not None:
            j = align_reference(raw, px)
            ident = year_identity(j) if len(j) > 10 else pd.DataFrame(columns=["valid"])
            valid = set(int(y) for y in ident.index[ident["valid"].astype(bool)]) if len(ident) else set()
            lrj = np.log(j[["adj_close", "close"]]).diff().dropna()
            yy = (lrj["adj_close"] - lrj["close"]).groupby(lrj.index.year).sum()
            y_0310 = yy[(yy.index >= 2003) & (yy.index <= 2010) & yy.index.isin(valid)]
            y_0015 = yy[(yy.index >= 2000) & (yy.index <= 2015) & yy.index.isin(valid)]
            name_yield = float(y_0310.mean()) if len(y_0310) else (float(y_0015.mean()) if len(y_0015) else np.nan)
            c_ii = cand[(cand.index < seam) & (cand.index >= "1999-12-01") & (cand.index <= "2015-12-31")]
            k_ii = cache[(cache.index < seam) & (cache.index >= "1999-12-01") & (cache.index <= "2015-12-31")]
            ref_ii = px["adj_close"]
            pc, pk = yearly_periods(c_ii, ref_ii), yearly_periods(k_ii, ref_ii)
            pk = pk.set_index("year")
            dj = (np.log(j).diff()["stooq"] - np.log(j).diff()["adj_close"]).fillna(0.0)
            off_ii = pd.Series(transient_offsets(dj.to_numpy()), index=j.index)
            for _, p in pc.iterrows():
                y = int(p["year"])
                if not p["full_year"] or y < 2000 or y > 2015 or y >= seam.year or y not in valid:
                    continue
                rows_ii.append({"ticker": t, "year": y, "x_pp": p["x_pp"],
                                "x_cache_pp": float(pk.loc[y, "x_pp"]) if y in pk.index else np.nan,
                                "name_yield_pp": 100 * name_yield, "sector": sectors.get(t, "unknown"),
                                "year_yield_pp": 100 * float(yy.get(y, np.nan)),
                                "endpoint_in_offset": bool(off_ii.get(p["start"], False))
                                or bool(off_ii.get(p["end"], False)), **diag.get(y, {})})
            n_div_pre = int((dv.index < seam).sum()) if dv is not None else 0
            # §1.1: a non-payer is REFERENCE-BACKED (v1 also admitted no-overlap symbols — a test bug)
            if n_div_pre == 0 and r.get("reference") == "reference":
                pr = yearly_periods(cand[cand.index < seam], raw[raw.index < seam])
                worst = float(pr["x_pp"].abs().max()) if len(pr) else 0.0
                rows_iii.append({"ticker": t, "n_years": int(len(pr)), "max_abs_vs_raw_pp": worst,
                                 "pass_a": worst < NONPAYER_TOL_PP})
        # (iii)(c) [v4, the review's "(iii-b)"] and the step audit: the candidate may differ from raw
        # Stooq's daily returns ONLY at labelled added ex-dates, by exactly −log(1 − D/P_prev).
        pre_c = cand[cand.index < seam]
        raw_pre = raw.reindex(pre_c.index)
        step = np.diff(np.log(pre_c.to_numpy() / raw_pre.to_numpy()))       # step[i-1] = bar i
        expected = np.zeros(len(pre_c) + 1)
        lab_p = out / "probe" / "labels" / f"{t}.parquet"
        if lab_p.exists():
            lab = pd.read_parquet(lab_p)
            lab = lab[lab["missed"].astype(bool) & (pd.DatetimeIndex(lab["day"]) < seam)]
            pos = pre_c.index.searchsorted(pd.DatetimeIndex(lab["day"]), side="left")
            np.add.at(expected, pos, -lab["log_f"].to_numpy())
        exp_bar = expected[1:len(pre_c)]
        dev = np.abs(step - exp_bar)
        unexpected = (np.abs(step) > STEP_TOL) & (np.abs(exp_bar) == 0)
        rows_step.append({"ticker": t, "n_steps_expected": int((np.abs(exp_bar) > 0).sum()),
                          "n_unexpected_steps": int(unexpected.sum()),
                          "max_abs_dev": float(dev.max()) if len(dev) else 0.0})
        nr_mask = np.zeros(len(pre_c), dtype=bool)
        kind = None
        if r.get("reference") != "reference":
            nr_mask = global_missed(pre_c.index)
            kind = "no_reference_name"
        else:
            for a_, b_ in r.get("unverified_missed_era_spans") or []:
                nr_mask |= (pre_c.index >= a_) & (pre_c.index <= b_)
            kind = "uncovered_span_of_a_referenced_name" if nr_mask.any() else None
        if kind is not None:
            chk = nr_mask[1:] & nr_mask[:-1]                                  # both ends of the return inside
            worst = float(np.abs(step[chk]).max()) if chk.any() else 0.0
            rows_iiic.append({"ticker": t, "kind": kind, "n_returns_checked": int(chk.sum()),
                              "max_abs_daily_vs_raw": worst, "pass": bool(worst < STEP_TOL)})
        # b before / after: mean excess vs the reference over full years 2012..seam-1
        mine = ([x for x in rows_i[n_i0:] if not x["seam_stub"] and x["year"] < seam.year]
                + [x for x in rows_ii[n_ii0:] if 2012 <= x["year"] <= 2015])
        exc_c = [x["x_pp"] for x in mine]
        exc_k = [x["x_cache_pp"] for x in mine]
        rows_b.append({"ticker": t, "b_applied_pp": r["b_pct_per_year"], "n_years": len(exc_c),
                       "mean_excess_cache_pp": float(np.mean(exc_k)) if exc_k else np.nan,
                       "mean_excess_candidate_pp": float(np.mean(exc_c)) if exc_c else np.nan})
        if (n + 1) % 100 == 0:
            print(f"[accept] {n + 1}/{len(written)}", flush=True)

    di, dii, diii, div_, dera, db = (pd.DataFrame(x) for x in (rows_i, rows_ii, rows_iii, rows_iv, rows_era, rows_b))
    diiic, dstep = pd.DataFrame(rows_iiic), pd.DataFrame(rows_step)
    di["cause"] = [classify_failure(r, "i") if not r["pass"] else "" for _, r in di.iterrows()]
    dii["outlier"] = dii["x_pp"].abs() > YF_P95_PP
    dii["cause"] = [classify_failure(r, "ii") if r["outlier"] else "" for _, r in dii.iterrows()]
    for name, d in [("i_t265", di), ("ii_yf", dii), ("iii_nonpayers", diii), ("iv_bytes", div_),
                    ("era_deltas", dera), ("b_before_after", db), ("iii_c_no_reference", diiic),
                    ("step_audit", dstep)]:
        d.to_csv(adir / f"{name}.csv", index=False)
    summary = summarize_acceptance(di, dii, diii, div_, dera, db, recs, diiic, dstep)
    (adir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary["verdict"], indent=2))
    return 0


def summarize_acceptance(di: pd.DataFrame, dii: pd.DataFrame, diii: pd.DataFrame, div_: pd.DataFrame,
                         dera: pd.DataFrame, db: pd.DataFrame, recs: Dict[str, dict],
                         diiic: Optional[pd.DataFrame] = None, dstep: Optional[pd.DataFrame] = None) -> dict:
    s: dict = {}
    # (i)
    s["i"] = {"names": int(di["ticker"].nunique()), "name_years": int(len(di)),
              "pass": int(di["pass"].sum()), "fail": int((~di["pass"]).sum()),
              "pass_strict": int(di["pass_strict"].sum()),
              "failing_names": sorted(di.loc[~di["pass"], "ticker"].unique().tolist())}
    by_year = di.assign(ax=di["x_pp"].abs(), axc=di["x_cache_pp"].abs()).groupby(
        np.where(di["seam_stub"], "seam_stub", di["year"].astype(str)))
    s["i"]["by_year"] = {k: {"n": int(len(g)), "median_abs_pp": float(g["ax"].median()),
                             "p95_abs_pp": float(g["ax"].quantile(.95)), "fail": int((~g["pass"]).sum()),
                             "cache_median_abs_pp": float(g["axc"].median())} for k, g in by_year}
    # (ii)
    d = dii.copy()
    d["ax"] = d["x_pp"].abs()
    d["axc"] = d["x_cache_pp"].abs()
    names_y = d.drop_duplicates("ticker").set_index("ticker")["name_yield_pp"]
    q = pd.qcut(names_y.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    d["quintile"] = d["ticker"].map(q).astype(int)
    yr = {}
    for y, g in d.groupby("year"):
        qmed = g.groupby("quintile")["ax"].median()
        row = {"n": int(len(g)), "median_abs_pp": float(g["ax"].median()),
               "p95_abs_pp": float(g["ax"].quantile(.95)),
               "quintile_median_abs_pp": {int(k): float(v) for k, v in qmed.items()},
               "cache_median_abs_pp": float(g["axc"].median()), "cache_p95_abs_pp": float(g["axc"].quantile(.95))}
        row["pass"] = bool(row["n"] >= YF_MIN_NAMES and row["median_abs_pp"] <= YF_MEDIAN_PP
                           and row["p95_abs_pp"] <= YF_P95_PP and bool((qmed <= YF_MEDIAN_PP).all())
                           and len(qmed) == 5)
        yr[int(y)] = row
    s["ii"] = {"names": int(d["ticker"].nunique()), "name_years": int(len(d)), "by_year": yr,
               "quintile_yield_bounds_pp": {int(k): [float(names_y[q == k].min()), float(names_y[q == k].max())]
                                            for k in range(1, 6)},
               "by_sector_median_abs_pp": d.groupby("sector")["ax"].median().round(4).to_dict()}
    # (iii)
    np_names = set(diii["ticker"]) if len(diii) else set()
    i_np = di[di["ticker"].isin(np_names)]
    s["iii"] = {"names": int(len(diii)), "pass_a": int(diii["pass_a"].sum()) if len(diii) else 0,
                "i_rows": int(len(i_np)), "i_fail": int((~i_np["pass"]).sum()) if len(i_np) else 0,
                "failing": sorted(set(diii.loc[~diii["pass_a"], "ticker"]) | set(i_np.loc[~i_np["pass"], "ticker"]))
                if len(diii) else []}
    # (iv)
    s["iv"] = {"files": int(len(div_)), "pass": int(div_["pass"].sum()),
               "failing": div_.loc[~div_["pass"], "ticker"].tolist()}
    # era deltas and b before/after
    s["era_deltas"] = {e: {"n": int(len(g)), "median": float(g["delta_pp_per_year"].median()),
                           "p10": float(g["delta_pp_per_year"].quantile(.1)),
                           "p90": float(g["delta_pp_per_year"].quantile(.9)),
                           "mean_abs": float(g["delta_pp_per_year"].abs().mean())}
                       for e, g in dera.groupby("era")}
    bb = db.dropna(subset=["mean_excess_cache_pp"])
    s["b_share"] = {"files_total": len(recs),
                    "b_applied_gt_0p5_of_written": int((db["b_applied_pp"] > 0.5).sum()),
                    "written": int(len(db)),
                    "measured_names": int(len(bb)),
                    "cache_mean_excess_gt_0p5": int((bb["mean_excess_cache_pp"] > 0.5).sum()),
                    "candidate_mean_excess_gt_0p5": int((bb["mean_excess_candidate_pp"].abs() > 0.5).sum())}
    # (iii)(c) — v4: no no-reference bar in a missed era moves off raw Stooq
    if diiic is not None and len(diiic):
        s["iii_c"] = {"files": int(len(diiic)), "pass": int(diiic["pass"].sum()),
                      "by_kind": diiic.groupby("kind").size().to_dict(),
                      "failing": sorted(diiic.loc[~diiic["pass"], "ticker"].tolist())}
    else:
        s["iii_c"] = {"files": 0, "pass": 0, "by_kind": {}, "failing": []}
    # the step audit — evidence that NO price was copied from the reference
    if dstep is not None and len(dstep):
        s["step_audit"] = {"files": int(len(dstep)), "steps_expected": int(dstep["n_steps_expected"].sum()),
                           "unexpected_steps": int(dstep["n_unexpected_steps"].sum()),
                           "files_with_unexpected": sorted(dstep.loc[dstep["n_unexpected_steps"] > 0, "ticker"].tolist()),
                           "max_abs_dev": float(dstep["max_abs_dev"].max())}
    # which evidence is INDEPENDENT of the build, and which is circular by construction (review MAJOR-2)
    cap = d[(d["year"] >= 2011) & (d["year"] <= 2015)]
    cap12 = d[(d["year"] >= 2012) & (d["year"] <= 2015)]
    mis = d[(d["year"] >= 2004) & (d["year"] <= 2010)]
    s["evidence"] = {
        "independent_i_vs_t265": {"name_years": int(len(di)), "candidate_fail": s["i"]["fail"],
                                  "cache_fail": int((di["x_cache_pp"].abs() > T265_TOL_PP + di["floor_pp"]).sum())},
        "independent_ii_2011_2015_gt_0p30": {"name_years": int(len(cap)),
                                             "cache": int((cap["axc"] > YF_P95_PP).sum()),
                                             "candidate": int((cap["ax"] > YF_P95_PP).sum())},
        "independent_ii_2012_2015_gt_0p30": {"name_years": int(len(cap12)),
                                             "cache": int((cap12["axc"] > YF_P95_PP).sum()),
                                             "candidate": int((cap12["ax"] > YF_P95_PP).sum())},
        "circular_ii_2004_2010": {"name_years": int(len(mis)), "median_abs_pp": float(mis["ax"].median()),
                                  "note": "added dividends AND labels come from the reference's own series"},
    }
    s["verdict"] = {
        "i": s["i"]["fail"] == 0,
        "ii": all(v["pass"] for v in yr.values()) and set(yr) == set(range(2000, 2016)),
        "iii": len(s["iii"]["failing"]) == 0 and len(s["iii_c"]["failing"]) == 0,
        "iv": s["iv"]["pass"] == s["iv"]["files"],
    }
    s["verdict"]["PASS"] = all(s["verdict"].values())
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="cache yfinance prices + dividends under the candidate dir")
    f.add_argument("--out", default=str(DEFAULT_OUT))
    f.add_argument("--yf-dir", default=str(DEFAULT_YF))
    f.add_argument("--tickers", nargs="*")
    f.add_argument("--sleep", type=float, default=0.4)
    f.add_argument("--refetch", action="store_true")
    f.set_defaults(func=cmd_fetch)
    b = sub.add_parser("build", help="write the candidate files (two passes) under <out>/processed")
    b.add_argument("--out", default=str(DEFAULT_OUT))
    b.add_argument("--yf-dir", default=str(DEFAULT_YF))
    b.add_argument("--tickers", nargs="*")
    b.add_argument("--min-free-gb", type=float, default=MIN_FREE_BYTES / 1024 ** 3)
    b.set_defaults(func=cmd_build)
    a = sub.add_parser("accept", help="run the pre-declared acceptance test on the written candidate")
    a.add_argument("--out", default=str(DEFAULT_OUT))
    a.add_argument("--yf-dir", default=str(DEFAULT_YF))
    a.set_defaults(func=cmd_accept)
    mf = sub.add_parser("manifest", help="md5 manifest of every file under <out>")
    mf.add_argument("--out", default=str(DEFAULT_OUT))
    mf.set_defaults(func=cmd_manifest)
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
