"""
scripts/lazy_prices/ingest_filings_t237.py
==========================================
T-2026-06-26-237 — "Lazy Prices" pilot: EDGAR 10-K / 10-Q DOCUMENT ingest.

FALSIFICATION research pilot. Cohen-Malloy-Nguyen (2020) "Lazy Prices" find that
quarter-over-quarter / year-over-year CHANGES in the text of a firm's periodic
filings (10-K, 10-Q) predict negative future returns. To test that on our
substrate we first need the raw filing DOCUMENTS (not just the 8-K structured
fields) with a defensible point-in-time (PIT) key. This module is the ingest
layer; the YoY textual-similarity scoring is a downstream step.

Reuses the EDGAR access layer proven in scripts/fetch_8k_edgar_t137.py:
  - ticker -> CIK map     https://www.sec.gov/files/company_tickers.json
  - submissions API       https://data.sec.gov/submissions/CIK##########.json
      (filings.recent arrays + older pages under filings.files)
  - primary document      https://www.sec.gov/Archives/edgar/data/{cik}/
                          {accession_nodashes}/{primaryDocument}
  - UA header with contact, RATE_SLEEP=0.13 (~7.7 req/s < SEC 10/s ceiling)
  - raw responses cached so re-runs are OFFLINE (politeness + determinism)

PIT key: `acceptance_dt` is `acceptanceDateTime` from the submissions arrays —
the wall-clock instant EDGAR accepted the filing and it became public. This is
the market's first-sight timestamp. We do NOT use `filingDate` (a date only,
can precede market visibility) or `reportDate` (the fiscal period end, months
before the filing). The pairing/return side must lag this with a same-day
acceptance-after-close convention; that is a downstream concern.

Amendments: form must be EXACTLY "10-K"/"10-Q"; "10-K/A" and "10-Q/A" are
EXCLUDED — a restated filing is not the market's first sight of the document
(same rationale as the 8-K/A exclusion in fetch_8k_edgar_t137).

[NN-FAIL-CLOSED]: every SELECTED filing appears in the index. A filing whose
primaryDocument is missing, or whose document fetch fails, is written with
fetch_ok=False and a non-empty skip_reason — NEVER silently dropped, NEVER a
clean zero row that reads like success. Downstream treats fetch_ok=False as a
FAIL, not a zero.

data/edgar/ is OUTSIDE the pinned-substrate manifest dirs (processed/raw/
governor) and is gitignored; no manifest regen, nothing here is committed.

Output: data/edgar/lazy_prices/filing_index.parquet

Usage:
  python -m scripts.lazy_prices.ingest_filings_t237 \\
      --tickers AAPL,MSFT,JPM,XOM,KO --forms 10-K --since-year 2005
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LP_DIR = ROOT / "data" / "edgar" / "lazy_prices"
RAW_DIR = LP_DIR / "raw"
OUT_PARQUET = LP_DIR / "filing_index.parquet"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
RATE_SLEEP = 0.13  # ~7.7 req/s, under the SEC 10 req/s fair-access ceiling

DEFAULT_FORMS = ("10-K",)

# Exact-string column contract for filing_index.parquet (order is the schema).
INDEX_COLUMNS = (
    "ticker",
    "cik",
    "form",
    "accession",
    "acceptance_dt",
    "period_end",
    "primary_doc",
    "primary_doc_url",
    "raw_path",
    "fetch_ok",
    "skip_reason",
)


# --------------------------------------------------------------------------- #
# Cached fetch primitives (mirrors fetch_8k_edgar_t137)
# --------------------------------------------------------------------------- #
def _get_json(url: str, cache_path: Path, force: bool = False) -> dict | None:
    """Fetch + cache a JSON endpoint. Returns None on any failure (offline-safe)."""
    if cache_path.exists() and not force:
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
        time.sleep(RATE_SLEEP)
        return data
    except Exception as e:
        print(f"[T237-ingest] WARN json {url.split('/')[-1]}: "
              f"{type(e).__name__} {e}", flush=True)
        time.sleep(RATE_SLEEP)
        return None


def _get_doc(url: str, cache_path: Path, force: bool = False) -> tuple[bool, str]:
    """Fetch + cache a filing document (HTML or plain-text .txt).

    Returns (ok, skip_reason). Documents are stored as bytes verbatim — the
    Lazy-Prices similarity step needs the raw bytes, and older filings are
    plain-text .txt rather than HTML, so we never assume an encoding here.
    """
    if cache_path.exists() and not force and cache_path.stat().st_size > 0:
        return True, ""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            blob = r.read()
        if not blob:
            time.sleep(RATE_SLEEP)
            return False, "empty_document_body"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(blob)
        time.sleep(RATE_SLEEP)
        return True, ""
    except Exception as e:
        print(f"[T237-ingest] WARN doc {url.split('/')[-1]}: "
              f"{type(e).__name__} {e}", flush=True)
        time.sleep(RATE_SLEEP)
        return False, f"fetch_error:{type(e).__name__}"


def ticker_cik_map() -> dict[str, int]:
    """ticker (upper) -> CIK int, from the SEC company_tickers.json map."""
    d = _get_json("https://www.sec.gov/files/company_tickers.json",
                  RAW_DIR / "company_tickers.json")
    if not d:
        raise RuntimeError("could not load company_tickers.json")
    return {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}


# --------------------------------------------------------------------------- #
# Filing selection + ingest
# --------------------------------------------------------------------------- #
def _select_rows(
    arr: dict,
    ticker: str,
    cik: int,
    forms: frozenset[str],
    since_year: int | None,
) -> list[dict]:
    """Select periodic-filing rows from one submissions array.

    Exact-string `form` match excludes "10-K/A"/"10-Q/A" amendments. Filters
    by acceptance year >= since_year (the Item 1A risk-factor mandate landed
    in 2005, so older 10-Ks have no comparable risk section). Carries the raw
    Archives URL and metadata needed to fetch the primary document later.
    """
    rows: list[dict] = []
    form_arr = arr.get("form", [])
    accession_arr = arr.get("accessionNumber", [])
    acceptance_arr = arr.get("acceptanceDateTime", [])
    report_arr = arr.get("reportDate", [])
    primary_arr = arr.get("primaryDocument", [])
    n = len(form_arr)
    for i in range(n):
        if form_arr[i] not in forms:  # exact match -> amendments excluded
            continue
        acceptance = acceptance_arr[i] if i < len(acceptance_arr) else ""
        if since_year is not None and acceptance[:4].isdigit():
            if int(acceptance[:4]) < since_year:
                continue
        accession = accession_arr[i]
        primary_doc = primary_arr[i] if i < len(primary_arr) else ""
        nodash = accession.replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
               f"{nodash}/{primary_doc}") if primary_doc else ""
        rows.append({
            "ticker": ticker,
            "cik": cik,
            "form": form_arr[i],
            "accession": accession,
            "acceptance_dt": acceptance,
            "period_end": report_arr[i] if i < len(report_arr) else "",
            "primary_doc": primary_doc,
            "primary_doc_url": url,
        })
    return rows


def select_company_filings(
    ticker: str,
    cik: int,
    forms: frozenset[str],
    since_year: int | None,
    force: bool = False,
) -> list[dict]:
    """All selected (recent + older-page) periodic filings for one company."""
    cik10 = f"CIK{cik:010d}"
    sub = _get_json(f"https://data.sec.gov/submissions/{cik10}.json",
                    RAW_DIR / f"{cik10}.json", force)
    if not sub:
        return []
    rows = _select_rows(sub["filings"]["recent"], ticker, cik, forms, since_year)
    for older in sub["filings"].get("files", []):
        name = older["name"]
        page = _get_json(f"https://data.sec.gov/submissions/{name}",
                         RAW_DIR / name, force)
        if page:
            rows += _select_rows(page, ticker, cik, forms, since_year)
    return rows


def ingest_filing(row: dict, force: bool = False) -> dict:
    """Fetch+cache one filing's primary document; stamp fetch_ok / skip_reason.

    [NN-FAIL-CLOSED]: returns a fully-populated index row in every case. A
    missing primaryDocument or a failed fetch yields fetch_ok=False with a
    non-empty skip_reason; it is never dropped.
    """
    cik = int(row["cik"])
    cik10 = f"CIK{cik:010d}"
    raw_path = RAW_DIR / cik10 / f"{row['accession']}.html"
    rel_path = str(raw_path.relative_to(ROOT))

    out = {
        "ticker": row["ticker"],
        "cik": cik,
        "form": row["form"],
        "accession": row["accession"],
        "acceptance_dt": row["acceptance_dt"],
        "period_end": row["period_end"],
        "primary_doc": row["primary_doc"],
        "primary_doc_url": row["primary_doc_url"],
        "raw_path": rel_path,
        "fetch_ok": False,
        "skip_reason": "",
    }

    if not row["primary_doc"] or not row["primary_doc_url"]:
        out["skip_reason"] = "missing_primary_document"
        return out

    ok, reason = _get_doc(row["primary_doc_url"], raw_path, force)
    out["fetch_ok"] = ok
    out["skip_reason"] = reason
    return out


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def build_index(
    tickers: list[str],
    forms: frozenset[str],
    since_year: int | None,
    limit: int | None,
    force: bool,
) -> pd.DataFrame:
    """Resolve tickers, select filings, fetch documents, return the index frame."""
    cmap = ticker_cik_map()
    resolved = [t for t in tickers if t in cmap]
    missing = [t for t in tickers if t not in cmap]
    if limit is not None:
        resolved = resolved[:limit]
    print(f"[T237-ingest] {len(tickers)} tickers requested; CIK resolved "
          f"{len(resolved)}, missing {len(missing)} {missing or ''}", flush=True)

    out_rows: list[dict] = []
    t0 = time.time()
    for n, t in enumerate(resolved, 1):
        selected = select_company_filings(t, cmap[t], forms, since_year, force)
        for sel in selected:
            out_rows.append(ingest_filing(sel, force))
        ok_so_far = sum(r["fetch_ok"] for r in out_rows)
        print(f"[T237-ingest] {n}/{len(resolved)} {t}: "
              f"{len(selected)} selected ({len(out_rows)} rows, "
              f"{ok_so_far} ok, {time.time() - t0:.0f}s)", flush=True)

    if not out_rows:
        df = pd.DataFrame(columns=list(INDEX_COLUMNS))
    else:
        df = pd.DataFrame(out_rows, columns=list(INDEX_COLUMNS))
        df = df.drop_duplicates(subset=["accession"])
        # acceptance_dt sorts lexicographically (ISO-8601), preserving PIT order.
        df = df.sort_values(["ticker", "acceptance_dt"]).reset_index(drop=True)

    # Pin dtypes so the contract is stable across runs / empty frames.
    df = df.astype({
        "ticker": "string",
        "cik": "int64",
        "form": "string",
        "accession": "string",
        "acceptance_dt": "string",
        "period_end": "string",
        "primary_doc": "string",
        "primary_doc_url": "string",
        "raw_path": "string",
        "fetch_ok": "bool",
        "skip_reason": "string",
    })
    df.attrs["missing_ciks"] = ",".join(missing)
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EDGAR 10-K/10-Q document ingest (T-237).")
    ap.add_argument("--tickers", default=None,
                    help="comma list, e.g. AAPL,MSFT (required for the pilot)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap number of companies (for sampling)")
    ap.add_argument("--forms", default="10-K",
                    help="comma list of forms, default 10-K; e.g. 10-K,10-Q")
    ap.add_argument("--since-year", type=int, default=2005,
                    help="keep filings with acceptance year >= this (Item 1A mandate)")
    ap.add_argument("--force", action="store_true",
                    help="bypass cache and re-fetch")
    args = ap.parse_args(argv)

    if not args.tickers:
        print("[T237-ingest] ERROR: --tickers is required for this pilot.",
              file=sys.stderr)
        return 2

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    forms = frozenset(f.strip() for f in args.forms.split(",") if f.strip())
    bad = forms - {"10-K", "10-Q"}
    if bad:
        print(f"[T237-ingest] ERROR: unsupported --forms {sorted(bad)} "
              f"(allowed: 10-K, 10-Q)", file=sys.stderr)
        return 2

    df = build_index(tickers, forms, args.since_year, args.limit, args.force)

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET)

    n_ok = int(df["fetch_ok"].sum()) if len(df) else 0
    n_skip = len(df) - n_ok
    print(f"[T237-ingest] wrote {OUT_PARQUET}: {len(df)} filings, "
          f"{df['ticker'].nunique() if len(df) else 0} tickers, "
          f"{n_ok} ok / {n_skip} fetch_ok=False", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
