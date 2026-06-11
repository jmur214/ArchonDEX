"""
scripts/build_13f_panel_t145.py
===============================
T-2026-06-10-145 Phase 0 — institutional-ownership panel from the SEC's own
structured Form-13F datasets (quarterly ZIPs, 2013q2+; the data research's
"check SEC structured first" path — raw-filing parsing avoided entirely).

Pipeline per quarter (streamed via /tmp; ZIPs are NOT retained — re-fetchable
public data, and local disk is tight):
  SUBMISSION.tsv  -> 13F-HR originals only (amendments excluded, documented)
  INFOTABLE.tsv   -> chunked filter to our CUSIP set (8-char prefix match),
                     SH-type holdings only, PUT/CALL excluded
  aggregate       -> per (ticker, period): n_holders, total_shares,
                     hhi_holders (share-based, immune to the Jan-2023 VALUE
                     units change), top10_share

CUSIP->ticker map: data/edgar/cusip_ticker_map.parquet (built from SEC FTD
files 2013-2026 — 35,378 pairs, 716/730 panel coverage; the 14 unmapped are
almost all pre-2013 delistings, before this window starts).

Antón-Polk pairwise CONNECTEDNESS is NOT computed (O(pairs×holders) on the
full filer panel) — the pre-registered fallback per the brief is ownership
CONCENTRATION/crowding levels; stated in the audit.

Output: data/edgar/13f/ownership_panel.parquet
Usage: python -m scripts.build_13f_panel_t145 [--limit N]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "edgar" / "13f"
OUT_PARQUET = OUT_DIR / "ownership_panel.parquet"
STATE_JSON = OUT_DIR / "build_state.json"
MAP_PARQUET = ROOT / "data" / "edgar" / "cusip_ticker_map.parquet"
TMP = Path("/tmp/archondex_13f")
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"


def zip_urls() -> list[str]:
    req = urllib.request.Request(INDEX_URL, headers=UA)
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    links = re.findall(r'href="([^"]+form13f\.zip)"', html)
    return ["https://www.sec.gov" + l if l.startswith("/") else l
            for l in dict.fromkeys(links)]


def cusip_lookup() -> dict[str, str]:
    m = pd.read_parquet(MAP_PARQUET)
    m["c8"] = m["cusip"].astype(str).str.strip().str.upper().str[:8]
    m["symbol"] = m["symbol"].astype(str).str.upper().str.replace(".", "-", regex=False)
    return dict(zip(m["c8"], m["symbol"]))


def process_quarter(url: str, lut: dict[str, str]) -> pd.DataFrame | None:
    name = url.split("/")[-1]
    dest = TMP / name
    TMP.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        print(f"[T145-P0] WARN download {name}: {type(e).__name__}", flush=True)
        return None
    try:
        with zipfile.ZipFile(dest) as z:
            names = {n.upper().split("/")[-1]: n for n in z.namelist()}
            sub = pd.read_csv(z.open(names["SUBMISSION.TSV"]), sep="\t",
                              low_memory=False, dtype=str)
            sub = sub.rename(columns=str.upper)
            sub = sub[sub["SUBMISSIONTYPE"] == "13F-HR"]
            keep_acc = set(sub["ACCESSION_NUMBER"])
            period = pd.to_datetime(sub["PERIODOFREPORT"].iloc[0]) \
                if len(sub) else None
            parts = []
            with z.open(names["INFOTABLE.TSV"]) as f:
                for chunk in pd.read_csv(f, sep="\t", low_memory=False, dtype=str,
                                         chunksize=500_000, on_bad_lines="skip"):
                    chunk = chunk.rename(columns=str.upper)
                    chunk = chunk[chunk["ACCESSION_NUMBER"].isin(keep_acc)]
                    if "PUTCALL" in chunk.columns:
                        chunk = chunk[chunk["PUTCALL"].isna() |
                                      (chunk["PUTCALL"].astype(str).str.strip() == "")]
                    if "SSHPRNAMTTYPE" in chunk.columns:
                        chunk = chunk[chunk["SSHPRNAMTTYPE"] == "SH"]
                    c8 = chunk["CUSIP"].astype(str).str.strip().str.upper().str[:8]
                    chunk["ticker"] = c8.map(lut)
                    chunk = chunk.dropna(subset=["ticker"])
                    if chunk.empty:
                        continue
                    chunk["shares"] = pd.to_numeric(chunk["SSHPRNAMT"], errors="coerce")
                    parts.append(chunk[["ACCESSION_NUMBER", "ticker", "shares"]])
            if not parts:
                return None
            hold = pd.concat(parts, ignore_index=True).dropna(subset=["shares"])
            # one row per (holder, ticker): sum split lots
            hold = hold.groupby(["ACCESSION_NUMBER", "ticker"], as_index=False)["shares"].sum()
            sub_dates = sub.set_index("ACCESSION_NUMBER")["FILING_DATE"]

            def agg(g: pd.DataFrame) -> pd.Series:
                sh = g["shares"].to_numpy()
                tot = sh.sum()
                w = sh / tot if tot > 0 else sh
                top10 = float(pd.Series(sh).nlargest(10).sum() / tot) if tot > 0 else 0.0
                return pd.Series({
                    "n_holders": int(len(sh)),
                    "total_shares_13f": float(tot),
                    "hhi_holders": float((w ** 2).sum()),
                    "top10_share": top10,
                })
            out = hold.groupby("ticker").apply(agg, include_groups=False).reset_index()
            out["period"] = period
            # PIT availability: last original filing date for this period
            out["max_filing_date"] = pd.to_datetime(sub_dates, errors="coerce").max()
            return out
    except Exception as e:
        print(f"[T145-P0] WARN parse {name}: {type(e).__name__}: {e}", flush=True)
        return None
    finally:
        try:
            dest.unlink()  # /tmp hygiene; ZIP is re-fetchable
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    urls = zip_urls()
    if args.limit:
        urls = urls[:args.limit]
    lut = cusip_lookup()
    print(f"[T145-P0] {len(urls)} quarter files; cusip map {len(lut)} prefixes", flush=True)

    done = set()
    if STATE_JSON.exists():
        done = set(json.loads(STATE_JSON.read_text()).get("done", []))
    frames = [pd.read_parquet(OUT_PARQUET)] if OUT_PARQUET.exists() else []
    t0 = time.time()
    for i, url in enumerate(urls, 1):
        name = url.split("/")[-1]
        if name in done:
            continue
        time.sleep(2.0)  # politeness gap — rapid sequences get throttled
        df = process_quarter(url, lut)
        if df is not None:
            frames.append(df)
            done.add(name)
            allp = pd.concat(frames, ignore_index=True).drop_duplicates(
                subset=["ticker", "period"], keep="last")
            allp.to_parquet(OUT_PARQUET, index=False)
            frames = [allp]
            STATE_JSON.write_text(json.dumps({"done": sorted(done)}))
            print(f"[T145-P0] {i}/{len(urls)} {name}: +{len(df)} ticker rows "
                  f"({time.time()-t0:.0f}s)", flush=True)
    if frames:
        final = frames[0]
        print(f"[T145-P0] panel: {len(final)} (ticker,quarter) rows, "
              f"{final.ticker.nunique()} tickers, "
              f"{final.period.min()}..{final.period.max()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
