"""scripts/lazy_prices/ingest_sections_t237.py
================================================
T-2026-06-25-237 — DISK-BOUNDED parse-and-discard EDGAR 10-K ingest.

The original two-stage path cached every raw 10-K HTML to disk (multi-MB ×
~13k filings → tens of GB → it filled the volume mid-run). This driver fetches
each filing into MEMORY, extracts ONLY Item 1A + Item 7 text, and persists just
that small text to sections.parquet. The raw HTML is NEVER written to disk.

`sections.parquet` is the durable, resumable cache: a re-run skips any accession
already parsed (ok OR fail-closed), so an interrupted run resumes cheaply and
the disk footprint stays at a few hundred MB (extracted text) instead of tens of
GB (raw HTML). Reuses the validated t237 EDGAR access layer (ticker→CIK,
submissions API, acceptanceDateTime PIT key, amendment exclusion) and the
validated section parser (similarity_t237.html_to_text / extract_sections).

[NN-FAIL-CLOSED]: a fetch failure or a section that cannot be located writes a
parse_ok=False row with a reason — never a silent drop, never a parsed-but-empty
section. [NN-AI-GATE]: research pilot, NOT wired into any live/canonical path.
data/edgar/ stays outside the pinned substrate (no canon regen).

Output schema is byte-compatible with similarity_t237.run_parse's
sections.parquet, so `similarity` Stage 2 consumes it unchanged.

Usage:
  python -m scripts.lazy_prices.ingest_sections_t237 \
      --tickers-file data/edgar/lazy_prices/pit_universe_t237.txt \
      [--since-year 2005] [--limit N] [--flush-every 25] [--force]
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lazy_prices.ingest_filings_t237 import (  # noqa: E402
    UA, RATE_SLEEP, ticker_cik_map, select_company_filings,
)
from scripts.lazy_prices.similarity_t237 import (  # noqa: E402
    SECTIONS_PATH, SectionResult, html_to_text, extract_sections, _MIN_SECTION_CHARS,
)

DEFAULT_FORMS = frozenset({"10-K"})

SECTIONS_COLUMNS = [
    "accession", "cik", "ticker", "acceptance_dt",
    "item_1a_text", "item_7_text", "parse_ok", "skip_reason",
]
SECTIONS_DTYPES = {
    "accession": "string", "cik": "int64", "ticker": "string",
    "acceptance_dt": "string", "item_1a_text": "string", "item_7_text": "string",
    "parse_ok": "bool", "skip_reason": "string",
}


def _fetch_text(url: str) -> tuple[str | None, str]:
    """Fetch a filing document into MEMORY (never to disk). Returns (text, reason).
    text is None on failure with a non-empty reason ([NN-FAIL-CLOSED])."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            blob = r.read()
        time.sleep(RATE_SLEEP)
        if not blob:
            return None, "empty_document_body"
        return blob.decode("utf-8", errors="ignore"), ""
    except Exception as e:  # noqa: BLE001 — offline-safe, recorded as a skip
        print(f"[T237-sections] WARN doc {url.split('/')[-1]}: "
              f"{type(e).__name__} {e}", flush=True)
        time.sleep(RATE_SLEEP)
        return None, f"fetch_error:{type(e).__name__}"


def parse_html_in_memory(html: str) -> SectionResult:
    """Item 1A / Item 7 from in-memory HTML (mirrors similarity_t237.parse_filing
    without the disk read). Fails closed on too-small / unlocatable sections."""
    if html is None or len(html) < 1000:
        return SectionResult("", "", False, "raw_html_too_small")
    text = html_to_text(html)
    item_1a, item_7 = extract_sections(text)
    missing: list[str] = []
    if len(item_1a) < _MIN_SECTION_CHARS:
        missing.append("item_1a")
    if len(item_7) < _MIN_SECTION_CHARS:
        missing.append("item_7")
    if missing:
        return SectionResult("", "", False, "section_not_located:" + ",".join(missing))
    return SectionResult(item_1a, item_7, True, "")


def _load_existing() -> tuple[pd.DataFrame, set[str]]:
    """Existing sections.parquet (for resume) + the set of done accessions."""
    if SECTIONS_PATH.is_file():
        df = pd.read_parquet(SECTIONS_PATH)
        return df, set(df["accession"].astype(str))
    return pd.DataFrame(columns=SECTIONS_COLUMNS), set()


def _flush(existing: pd.DataFrame, new_rows: list[dict]) -> pd.DataFrame:
    """Merge new rows into the on-disk sections.parquet (dedup by accession)."""
    if not new_rows:
        return existing
    merged = pd.concat([existing, pd.DataFrame(new_rows, columns=SECTIONS_COLUMNS)],
                       ignore_index=True)
    merged = merged.drop_duplicates(subset=["accession"], keep="last")
    merged = merged.astype(SECTIONS_DTYPES)
    SECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(SECTIONS_PATH, index=False)
    return merged


def build_sections(
    tickers: list[str], since_year: int | None, limit: int | None,
    flush_every: int, force: bool,
) -> pd.DataFrame:
    cmap = ticker_cik_map()
    resolved = [t for t in tickers if t in cmap]
    missing = [t for t in tickers if t not in cmap]
    if limit is not None:
        resolved = resolved[:limit]
    existing, done = (_load_existing() if not force else (pd.DataFrame(columns=SECTIONS_COLUMNS), set()))
    print(f"[T237-sections] {len(tickers)} requested; CIK resolved {len(resolved)}, "
          f"missing {len(missing)}; {len(done)} accessions already parsed (resume).",
          flush=True)

    pending: list[dict] = []
    t0 = time.time()
    for n, t in enumerate(resolved, 1):
        selected = select_company_filings(t, cmap[t], DEFAULT_FORMS, since_year, force=False)
        n_new = 0
        for sel in selected:
            acc = sel["accession"]
            if acc in done:
                continue
            done.add(acc)
            base = {"accession": acc, "cik": int(sel["cik"]), "ticker": sel["ticker"],
                    "acceptance_dt": sel["acceptance_dt"]}
            if not sel.get("primary_doc_url"):
                pending.append({**base, "item_1a_text": "", "item_7_text": "",
                                "parse_ok": False, "skip_reason": "missing_primary_document"})
                n_new += 1
                continue
            html, reason = _fetch_text(sel["primary_doc_url"])
            if html is None:
                pending.append({**base, "item_1a_text": "", "item_7_text": "",
                                "parse_ok": False, "skip_reason": reason})
            else:
                res = parse_html_in_memory(html)  # html discarded after this
                pending.append({**base, "item_1a_text": res.item_1a_text,
                                "item_7_text": res.item_7_text,
                                "parse_ok": res.parse_ok, "skip_reason": res.skip_reason})
            n_new += 1
        ok = int(existing["parse_ok"].sum()) + sum(1 for r in pending if r["parse_ok"]) \
            if len(existing) else sum(1 for r in pending if r["parse_ok"])
        print(f"[T237-sections] {n}/{len(resolved)} {t}: {len(selected)} filings, "
              f"+{n_new} new ({ok} ok total, {time.time()-t0:.0f}s)", flush=True)
        if n % flush_every == 0:
            existing = _flush(existing, pending)
            pending = []

    final = _flush(existing, pending)
    return final


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Disk-bounded parse-and-discard 10-K ingest (T-237).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tickers", default=None, help="comma list, e.g. AAPL,MSFT")
    src.add_argument("--tickers-file", type=Path, default=None, help="file of comma/newline tickers")
    ap.add_argument("--since-year", type=int, default=2005)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--flush-every", type=int, default=25, help="write sections.parquet every N companies")
    ap.add_argument("--force", action="store_true", help="ignore existing sections.parquet (re-parse all)")
    args = ap.parse_args(argv)

    if args.tickers_file:
        raw = args.tickers_file.read_text()
        tickers = [x.strip().upper() for x in raw.replace("\n", ",").split(",") if x.strip()]
    else:
        tickers = [x.strip().upper() for x in args.tickers.split(",") if x.strip()]

    df = build_sections(tickers, args.since_year, args.limit, args.flush_every, args.force)
    ok = int(df["parse_ok"].sum()) if len(df) else 0
    print(f"[T237-sections] DONE: {len(df)} filings in sections.parquet "
          f"({ok} parse_ok, {len(df)-ok} fail-closed). -> {SECTIONS_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
