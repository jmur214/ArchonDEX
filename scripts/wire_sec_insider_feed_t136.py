"""
scripts/wire_sec_insider_feed_t136.py
=====================================
T-2026-06-10-136 Part B — SEC Insider Transactions structured datasets as the
canonical insider feed (REPOINT the feed; the edge is untouched).

Source (free, public domain, license-safe to bake): SEC "Insider Transactions
Data Sets" — quarterly ZIPs of flattened Form 3/4/5 XML, 2006q1+.
  https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/YYYYqQ_form345.zip
Tables used: SUBMISSION.tsv (ACCESSION_NUMBER, FILING_DATE, ISSUERTRADINGSYMBOL),
NONDERIV_TRANS.tsv (TRANS_DATE, TRANS_CODE, TRANS_SHARES, TRANS_PRICEPERSHARE,
TRANS_ACQUIRED_DISP_CD, SHRS_OWND_FOLWNG_TRANS), REPORTINGOWNER.tsv (name, title).

Output: per-ticker parquet in the EXISTING InsiderDataManager format
(INSIDER_TXN_COLUMNS, indexed by transaction_date) — written to
data/insider_sec/ (a PARALLEL feed dir; repointing the production cache dir
from the openinsider vintage to this one is the director's一-line flip via
InsiderDataManager(cache_dir=...) — propose-first, not done here).

Amendments: the structured sets carry the latest accepted version per
accession; 4/A rows replace originals by ACCESSION lineage — we dedup on
(ticker, trans_date, insider_name, shares, price) keeping the LAST filing.

Form-4 transaction codes mapped to the edge's expectations:
  TRANS_CODE 'P' (open-market purchase) -> transaction_type 'P'
  TRANS_CODE 'S' (open-market sale)     -> transaction_type 'S'
  everything else (A, M, G, F, ...)     -> kept verbatim in transaction_type
  (the edge filters == 'P', so awards/options-exercises do NOT pollute the
  cluster math — same semantics as the openinsider feed).

Usage:
  python -m scripts.wire_sec_insider_feed_t136 --quarters 2024q1,2024q2
  python -m scripts.wire_sec_insider_feed_t136 --start 2006q1 --end 2026q1
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "edgar" / "insider_zips"
OUT_DIR = ROOT / "data" / "insider_sec"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
URLS = [
    "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{q}_form345.zip",
    "https://www.sec.gov/files/dera/data/form-345/{q}_form345.zip",
]
INSIDER_TXN_COLUMNS = [
    "filing_date", "ticker", "insider_name", "insider_title",
    "transaction_type", "transaction_subtype", "price", "shares",
    "holdings_after", "delta_holdings_pct", "value",
]


def quarters(start: str, end: str) -> list[str]:
    y0, q0 = int(start[:4]), int(start[5])
    y1, q1 = int(end[:4]), int(end[5])
    out = []
    y, q = y0, q0
    while (y, q) <= (y1, q1):
        out.append(f"{y}q{q}")
        q += 1
        if q == 5:
            y, q = y + 1, 1
    return out


def fetch_zip(q: str) -> Path | None:
    dest = RAW_DIR / f"{q}_form345.zip"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    for tmpl in URLS:
        url = tmpl.format(q=q)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                blob = r.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
            time.sleep(0.13)
            return dest
        except Exception:
            time.sleep(0.13)
            continue
    print(f"[T136-B] WARN no zip for {q}")
    return None


def parse_quarter(zp: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zp) as z:
        def rd(name):
            with z.open(name) as f:
                return pd.read_csv(io.BytesIO(f.read()), sep="\t",
                                   low_memory=False, on_bad_lines="skip")
        sub = rd("SUBMISSION.tsv")
        trans = rd("NONDERIV_TRANS.tsv")
        owner = rd("REPORTINGOWNER.tsv")
    sub = sub.rename(columns=str.upper)
    trans = trans.rename(columns=str.upper)
    owner = owner.rename(columns=str.upper)

    own1 = (owner.sort_values("ACCESSION_NUMBER")
            .groupby("ACCESSION_NUMBER").first().reset_index())
    df = (trans.merge(sub[["ACCESSION_NUMBER", "FILING_DATE",
                           "ISSUERTRADINGSYMBOL"]], on="ACCESSION_NUMBER")
               .merge(own1[["ACCESSION_NUMBER", "RPTOWNERNAME",
                            "RPTOWNER_RELATIONSHIP" if "RPTOWNER_RELATIONSHIP" in own1.columns
                            else "RPTOWNERNAME"]].rename(
                   columns={"RPTOWNER_RELATIONSHIP": "TITLE"}),
                   on="ACCESSION_NUMBER", how="left"))
    out = pd.DataFrame({
        "transaction_date": pd.to_datetime(df["TRANS_DATE"], errors="coerce"),
        "filing_date": pd.to_datetime(df["FILING_DATE"], errors="coerce"),
        "ticker": df["ISSUERTRADINGSYMBOL"].astype(str).str.upper().str.replace(".", "-", regex=False),
        "insider_name": df["RPTOWNERNAME"].astype(str),
        "insider_title": df.get("TITLE", pd.Series(dtype=str)),
        "transaction_type": df["TRANS_CODE"].astype(str).str.upper(),
        "transaction_subtype": df["TRANS_ACQUIRED_DISP_CD"].astype(str),
        "price": pd.to_numeric(df["TRANS_PRICEPERSHARE"], errors="coerce"),
        "shares": pd.to_numeric(df["TRANS_SHARES"], errors="coerce"),
        "holdings_after": pd.to_numeric(df.get("SHRS_OWND_FOLWNG_TRANS"), errors="coerce"),
    }).dropna(subset=["transaction_date", "ticker"])
    out["delta_holdings_pct"] = float("nan")
    out["value"] = out["price"] * out["shares"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarters", default=None)
    ap.add_argument("--start", default="2024q1")
    ap.add_argument("--end", default="2025q4")
    args = ap.parse_args()
    qs = ([q.strip() for q in args.quarters.split(",")] if args.quarters
          else quarters(args.start, args.end))

    frames = []
    for q in qs:
        zp = fetch_zip(q)
        if zp is None:
            continue
        try:
            d = parse_quarter(zp)
            frames.append(d)
            print(f"[T136-B] {q}: {len(d)} txn rows", flush=True)
        except Exception as e:
            print(f"[T136-B] WARN parse {q}: {type(e).__name__}: {e}", flush=True)
    if not frames:
        print("[T136-B] nothing parsed")
        return 1
    allq = pd.concat(frames, ignore_index=True)
    # amendment dedup: keep LAST filing per economic transaction
    allq = (allq.sort_values("filing_date")
                 .drop_duplicates(subset=["ticker", "transaction_date",
                                          "insider_name", "shares", "price"],
                                  keep="last"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_files = 0
    import re
    for t, sub in allq.groupby("ticker"):
        if not t or t in ("NAN", "NONE", "N/A"):
            continue
        # raw SEC symbols can carry slashes/junk (GTII/U, BRK/A) — normalize
        # share-class '/' to '-', then require a clean symbol
        t = t.replace("/", "-")
        if not re.fullmatch(r"[A-Z0-9-]{1,10}", t):
            continue
        existing = OUT_DIR / f"{t}.parquet"
        sub = sub.set_index("transaction_date").sort_index()[INSIDER_TXN_COLUMNS]
        if existing.exists():
            old = pd.read_parquet(existing)
            sub = (pd.concat([old, sub])
                   .reset_index()
                   .drop_duplicates(subset=["transaction_date", "insider_name",
                                            "shares", "price"], keep="last")
                   .set_index("transaction_date").sort_index())
        sub.to_parquet(existing)
        n_files += 1
    print(f"[T136-B] wrote/updated {n_files} ticker parquets in {OUT_DIR} "
          f"({len(allq)} rows total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
