"""
scripts/fetch_8k_edgar_t137.py
==============================
T-2026-06-10-137 — EDGAR 8-K panel builder (STRUCTURED fields only, no LLM).

Pulls, for every ticker in our price panel, the company's full EDGAR filing
history via the submissions API and extracts 8-K rows with:
  ticker, cik, accessionNumber, filingDate, acceptanceDateTime, items

Endpoints (free, public domain):
  - https://www.sec.gov/files/company_tickers.json       (ticker -> CIK)
  - https://data.sec.gov/submissions/CIK##########.json  (per-company filings;
    `filings.recent` arrays + older pages listed under `filings.files`)

Etiquette per SEC fair-access policy: <=8 req/s, mandatory User-Agent with
contact, raw responses cached under data/edgar/8k/raw/ so re-runs are
OFFLINE (determinism + politeness). data/edgar/ is OUTSIDE the pinned
substrate manifest dirs (processed/raw/governor), so no manifest regen needed.

Amendments: form == '8-K' only; '8-K/A' EXCLUDED from the event panel (an
amendment's acceptance time is not the market's first sight of the event).

Output: data/edgar/8k/panel_8k_items.parquet

Usage: python -m scripts.fetch_8k_edgar_t137 [--tickers AAPL,MSFT] [--force]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "edgar" / "8k" / "raw"
OUT_PARQUET = ROOT / "data" / "edgar" / "8k" / "panel_8k_items.parquet"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
RATE_SLEEP = 0.13  # ~7.7 req/s, under the 10 req/s fair-access ceiling


def _get(url: str, cache_path: Path, force: bool = False) -> dict | None:
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
        print(f"[T137-fetch] WARN {url.split('/')[-1]}: {type(e).__name__} {e}",
              flush=True)
        time.sleep(RATE_SLEEP)
        return None


def panel_tickers() -> list[str]:
    return sorted({f.split("/")[-1].replace("_1d.csv", "")
                   for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv"))})


def ticker_cik_map() -> dict[str, int]:
    d = _get("https://www.sec.gov/files/company_tickers.json",
             RAW_DIR / "company_tickers.json")
    if not d:
        raise RuntimeError("could not load company_tickers.json")
    return {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}


def _rows_from_filing_arrays(arr: dict, ticker: str, cik: int) -> list[dict]:
    rows = []
    forms = arr.get("form", [])
    for i, form in enumerate(forms):
        if form != "8-K":  # excludes 8-K/A by exact match
            continue
        rows.append({
            "ticker": ticker,
            "cik": cik,
            "accession": arr["accessionNumber"][i],
            "filing_date": arr["filingDate"][i],
            "acceptance_dt": arr["acceptanceDateTime"][i],
            "items": arr.get("items", [""] * len(forms))[i],
        })
    return rows


def fetch_company(ticker: str, cik: int, force: bool = False) -> list[dict]:
    cik10 = f"CIK{cik:010d}"
    sub = _get(f"https://data.sec.gov/submissions/{cik10}.json",
               RAW_DIR / f"{cik10}.json", force)
    if not sub:
        return []
    rows = _rows_from_filing_arrays(sub["filings"]["recent"], ticker, cik)
    for older in sub["filings"].get("files", []):
        name = older["name"]
        page = _get(f"https://data.sec.gov/submissions/{name}",
                    RAW_DIR / name, force)
        if page:
            rows += _rows_from_filing_arrays(page, ticker, cik)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=None,
                    help="comma list (default: full price panel)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    tickers = ([t.strip().upper() for t in args.tickers.split(",")]
               if args.tickers else panel_tickers())
    cmap = ticker_cik_map()
    have = [t for t in tickers if t in cmap]
    missing = [t for t in tickers if t not in cmap]
    print(f"[T137-fetch] {len(tickers)} panel tickers; CIK found {len(have)}, "
          f"missing {len(missing)} (mostly delisted pre-mapping; listed in parquet attrs)")

    all_rows: list[dict] = []
    t0 = time.time()
    for n, t in enumerate(have, 1):
        all_rows += fetch_company(t, cmap[t], args.force)
        if n % 50 == 0:
            print(f"[T137-fetch] {n}/{len(have)} companies "
                  f"({len(all_rows)} 8-K rows, {time.time()-t0:.0f}s)", flush=True)

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["accession"])
    df["filing_date"] = pd.to_datetime(df["filing_date"])
    df["acceptance_dt"] = pd.to_datetime(df["acceptance_dt"], errors="coerce")
    df = df.sort_values(["ticker", "acceptance_dt"]).reset_index(drop=True)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.attrs["missing_ciks"] = ",".join(missing)
    df.to_parquet(OUT_PARQUET)
    print(f"[T137-fetch] wrote {OUT_PARQUET}: {len(df)} 8-K filings, "
          f"{df.ticker.nunique()} tickers, "
          f"{df.filing_date.min().date()}..{df.filing_date.max().date()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
