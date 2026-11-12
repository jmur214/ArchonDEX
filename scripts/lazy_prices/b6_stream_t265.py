"""scripts/lazy_prices/b6_stream_t265.py
=======================================
T-383 (B-6) — the T-265 small-cap arm's text signals, SIGNALS-ONLY STREAMING (no stored text).

Per the user's ruling (2026-11-11, disk): the small-cap arm never stores section text. For each
T-265 CIK (`data/research/t265/cik_ticker_final.parquet` with a T-265 price file — read for the
CIK list only; no price is read) this driver fetches the issuer's 10-K/10-Q list, then each
filing accepted from 2015-01-01 (the 2016-2026 window plus a year of priors) INTO MEMORY,
parses it with b6_parse, computes the pre-declared signals with b6_signals.company_signals
(the identical pairing and measures as the S&P panel), and writes ONLY the signal rows and
per-filing statuses. The CIK's texts are discarded when it is done.

CIKs already in the S&P fetch list are skipped (their text is in the S&P panel; Phase 2 joins).
Resumable by CIK; disk checked before every CIK (halts cleanly under the floor); a 403 halts.

Usage:
  python -m scripts.lazy_prices.b6_stream_t265 [--limit-ciks N] [--min-interval 0.45]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

from scripts.lazy_prices import b6_build_panel as B
from scripts.lazy_prices import b6_edgar as E
from scripts.lazy_prices import b6_signals as S

ROOT = Path(__file__).resolve().parents[2]
T265 = ROOT / "data" / "research" / "t265"
OUT_DIR = ROOT / "data" / "b6_local" / "t265_signals"
LOG = ROOT / "data" / "b6_local" / "logs" / "stream_t265.log"
SINCE = "2015-01-01"
META_COLS = ["cik", "form", "accession", "acceptance_dt", "period_end", "fetch_ok",
             "fetch_status", "fetch_reason", "doc_bytes", "risk_status", "risk_source",
             "risk_words", "risk_tier", "mda_status", "mda_source", "mda_words", "mda_tier"]


def t265_ciks() -> list[int]:
    ct = pd.read_parquet(T265 / "cik_ticker_final.parquet")
    files = {p.stem for p in (T265 / "prices").glob("*.parquet")}
    return sorted(int(c) for c in ct[ct.ticker.isin(files)].cik.unique())


def _done() -> set[int]:
    if not OUT_DIR.is_dir():
        return set()
    done: set[int] = set()
    for p in OUT_DIR.glob("done_*.parquet"):
        done |= set(pd.read_parquet(p).cik.astype(int))
    return done


def company_filings(cik: int) -> tuple[list[dict], str]:
    """10-K/10-Q rows accepted >= SINCE; older submission pages fetched only if they reach it."""
    cik10 = f"CIK{cik:010d}"
    sub, res = E.fetch_json(f"https://data.sec.gov/submissions/{cik10}.json")
    if sub is None:
        return [], f"submissions_failed:{res.status}:{res.reason}"
    rows = E.periodic_rows(sub["filings"]["recent"])
    for older in sub["filings"].get("files", []):
        if str(older.get("filingTo", "9999")) < SINCE:
            continue
        page, r2 = E.fetch_json(f"https://data.sec.gov/submissions/{older['name']}")
        if page is None:
            return [], f"submissions_page_failed:{r2.status}:{r2.reason}"
        rows += E.periodic_rows(page)
    keep = [r for r in rows if str(r.get("acceptanceDateTime") or "") >= SINCE]
    return keep, ""


def process_cik(cik: int) -> tuple[list[dict], list[dict], str]:
    rows, err = company_filings(cik)
    if err:
        return [], [], err
    parsed = []
    for r in rows:
        ser = pd.Series({"cik": cik, "form": r["form"], "accession": r["accessionNumber"],
                         "acceptance_dt": r["acceptanceDateTime"], "filing_date": r["filingDate"],
                         "period_end": r["reportDate"], "primary_doc": r["primaryDocument"]})
        parsed.append(B.process_filing(ser))
    if not parsed:
        return [], [], "no_periodic_filings_since_2015"
    f = pd.DataFrame(parsed)
    f["mda_source"] = f["mda_source"].fillna("")
    f["risk_text"] = f["risk_text"].fillna("")
    f["mda_text"] = f["mda_text"].fillna("")
    sig = S.company_signals(f)
    meta = f[META_COLS].to_dict("records")
    return sig, meta, ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 T-265 small-cap signals (streaming, no text).")
    ap.add_argument("--limit-ciks", type=int, default=None)
    ap.add_argument("--min-interval", type=float, default=E.MIN_INTERVAL)
    ap.add_argument("--flush-ciks", type=int, default=50)
    ap.add_argument("--disk-floor", type=float, default=E.DISK_FLOOR_GB)
    args = ap.parse_args(argv)
    E.MIN_INTERVAL = args.min_interval
    S.load_lm()
    sp = set(pd.read_parquet(B.FETCH_LIST).cik.astype(int)) if B.FETCH_LIST.is_file() else set()
    ciks = [c for c in t265_ciks() if c not in sp]
    done = _done()
    todo = [c for c in ciks if c not in done]
    if args.limit_ciks:
        todo = todo[: args.limit_ciks]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    B._log(f"[t265] CIKs {len(ciks)} (S&P overlap skipped {len(sp & set(t265_ciks()))}); done "
           f"{len(done)}; to do {len(todo)}; free {E.disk_free_gb():.2f} GB", LOG)
    sig_buf, meta_buf, done_buf = [], [], []
    t0, n_docs = time.time(), 0

    def flush() -> None:
        nonlocal sig_buf, meta_buf, done_buf
        if not done_buf:
            return
        k = len(list(OUT_DIR.glob("done_*.parquet")))
        if sig_buf:
            pd.DataFrame(sig_buf).to_parquet(OUT_DIR / f"signals_{k:05d}.parquet", index=False)
        if meta_buf:
            pd.DataFrame(meta_buf).to_parquet(OUT_DIR / f"filings_{k:05d}.parquet", index=False)
        pd.DataFrame(done_buf).to_parquet(OUT_DIR / f"done_{k:05d}.parquet", index=False)
        sig_buf, meta_buf, done_buf = [], [], []

    try:
        for i, cik in enumerate(todo, 1):
            free = E.assert_disk(args.disk_floor)
            try:
                sig, meta, err = process_cik(cik)
            except (E.DiskFloor, E.EdgarRefused):
                raise
            except Exception as e:  # noqa: BLE001 — recorded per CIK, never silent
                sig, meta, err = [], [], f"error:{type(e).__name__}:{e}"[:300]
            sig_buf += sig
            meta_buf += meta
            n_docs += len(meta)
            done_buf.append({"cik": cik, "n_filings": len(meta), "error": err})
            if i % args.flush_ciks == 0:
                flush()
                B._log(f"[t265] {i}/{len(todo)} CIKs; {n_docs} filings; "
                       f"{n_docs / max(1.0, time.time() - t0):.2f} docs/s; requests "
                       f"{E.stats['requests']} failures {E.stats['failures']}; free {free:.2f} GB",
                       LOG)
    except E.DiskFloor as e:
        flush()
        B._log(f"[t265] HALT (disk): {e}", LOG)
        return 3
    except E.EdgarRefused as e:
        flush()
        B._log(f"[t265] HALT (SEC refused): {e}", LOG)
        return 4
    flush()
    B._log(f"[t265] DONE {len(todo)} CIKs, {n_docs} filings in {time.time() - t0:.0f}s", LOG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
