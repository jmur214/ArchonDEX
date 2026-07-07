"""
scripts/archive_altdata_t136.py
===============================
T-2026-06-10-136 Part D — alt-data pulls + forward archivers ($0).

ONE-TIME BULK (backtestable-now indices; revision semantics noted per source):
  - GPR (Caldara-Iacoviello geopolitical risk): daily-recent + monthly-history
    XLS from matteoiacoviello.com. REVISION NOTE: GPR is reconstructed from
    newspaper archives and the full series is re-released monthly — values
    can revise; archive every vintage (dated pulls), use as point-in-time
    only from our archive dates forward.
  - EPU (Baker-Bloom-Davis policy uncertainty): daily US series CSV from
    policyuncertainty.com. Same revision caveat (constructed index).
  - GDELT: the 1979+ BULK event archive is GB-scale (BigQuery/bulk job) —
    out of scope here, FLAGGED as follow-up. What we archive forward: the
    GDELT v2 doc-API tone timelines for fixed macro query buckets (shallow
    but ours from today).

FORWARD ARCHIVERS (the hoard-now principle; cron-able, idempotent):
  - Polymarket (gamma-api.polymarket.com, public): daily snapshot of active
    markets in macro/Fed/recession/election/geopolitics buckets.
  - Kalshi (public market-data API): same buckets. (Public GET; if the
    endpoint requires auth at runtime we report + skip — status printed.)

Output: data/macro_data/alt/*.parquet (+ dated snapshot rows appended)
Usage: python -m scripts.archive_altdata_t136
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "macro_data" / "alt"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
SNAP_DATE = pd.Timestamp.now().strftime("%Y-%m-%d")

KEYWORDS = ["fed", "rate", "recession", "inflation", "cpi", "gdp", "election",
            "president", "war", "china", "tariff", "geopolit", "nuclear",
            "oil", "opec", "treasury", "shutdown", "debt ceiling",
            # widened 2026-07-07 (info-layer program day-1): filtering later is
            # possible, un-missing markets is not. Dedup keys make this safe.
            "fomc", "powell", "rate cut", "rate hike", "payroll", "jobs report",
            "unemployment", "pce", "ppi", "vix", "volatility", "s&p", "sp500",
            "nasdaq", "stock market", "bitcoin", "crypto", "taiwan", "sanction",
            "bank", "default", "yield", "bond", "dollar", "gold", "housing",
            "mortgage", "energy", "gas price", "strike", "congress", "senate"]


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _append(df: pd.DataFrame, path: Path, keys: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    df.drop_duplicates(subset=keys, keep="last").to_parquet(path, index=False)


def pull_gpr() -> str:
    from scripts._xlsx_min import read_xlsx_first_sheet
    got = []
    # No Excel engine installed (no-new-deps): try .xlsx variants (stdlib
    # parser); legacy binary .xls is unsupported -> flagged if only .xls exists.
    for name, urls in [
        ("gpr_daily_recent", [
            "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xlsx",
            "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"]),
        ("gpr_monthly_full", [
            "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xlsx",
            "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"]),
    ]:
        ok = False
        for url in urls:
            try:
                blob = _get(url)
                if url.endswith(".xlsx"):
                    df = read_xlsx_first_sheet(blob)
                else:
                    # legacy binary .xls — xlrd dep user-approved 2026-06-10
                    try:
                        import io
                        import pandas as _pd
                        df = _pd.read_excel(io.BytesIO(blob), engine="xlrd")
                    except ImportError:
                        got.append(f"{name}: only legacy .xls reachable — "
                                   f"UNPARSEABLE without xlrd (dep approval needed)")
                        ok = True
                        break
                df.columns = [str(c).strip().lower() for c in df.columns]
                df["archive_vintage"] = SNAP_DATE
                dcol = next((c for c in df.columns if "date" in c or c in ("day", "month")),
                            df.columns[0])
                _append(df, OUT_DIR / f"{name}.parquet", [dcol, "archive_vintage"])
                got.append(f"{name}({len(df)})")
                ok = True
                break
            except Exception:
                continue
        if not ok:
            got.append(f"{name} FAILED (no variant reachable)")
        time.sleep(0.3)
    return "gpr: " + ", ".join(got) + " | revision-prone constructed index; vintage-stamped"


def pull_epu() -> str:
    got = []
    from scripts._xlsx_min import read_xlsx_first_sheet
    for name, url in [
        ("epu_daily_us", "https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv"),
        ("epu_monthly_us", "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx"),
    ]:
        try:
            blob = _get(url)
            df = (pd.read_csv(io.BytesIO(blob)) if url.endswith(".csv")
                  else read_xlsx_first_sheet(blob))
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            df["archive_vintage"] = SNAP_DATE
            _append(df, OUT_DIR / f"{name}.parquet",
                    list(df.columns[:3]) + ["archive_vintage"])
            got.append(f"{name}({len(df)})")
        except Exception as e:
            got.append(f"{name} FAILED ({type(e).__name__})")
        time.sleep(0.3)
    return "epu: " + ", ".join(got) + " | revision-prone constructed index; vintage-stamped"


def pull_gdelt_timelines() -> str:
    got = []
    for bucket, query in [
        ("geopolitics", '"geopolitical risk"'),
        ("fed_policy", '"federal reserve"'),
        ("recession", "recession"),
    ]:
        try:
            url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
                   + urllib.request.quote(query)
                   + "&mode=timelinetone&timespan=12m&format=json")
            data = json.loads(_get(url, timeout=60))
            series = data["timeline"][0]["data"]
            df = pd.DataFrame(series)
            df["bucket"] = bucket
            df["archive_vintage"] = SNAP_DATE
            _append(df, OUT_DIR / "gdelt_tone_timelines.parquet",
                    ["date", "bucket"])
            got.append(f"{bucket}({len(df)})")
        except Exception as e:
            got.append(f"{bucket} FAILED ({type(e).__name__})")
        time.sleep(6.0)  # GDELT fair-use: one request per 5 seconds (429 otherwise)
    return ("gdelt: " + ", ".join(got)
            + " | NOTE: 1979+ BULK events = BigQuery/bulk job, flagged follow-up")


def snapshot_polymarket() -> str:
    try:
        rows, offset = [], 0
        while offset <= 1000:
            url = (f"https://gamma-api.polymarket.com/markets?closed=false"
                   f"&limit=100&offset={offset}")
            page = json.loads(_get(url, timeout=60))
            if not page:
                break
            rows += page
            offset += 100
            time.sleep(0.2)
        recs = []
        for m in rows:
            text = (str(m.get("question", "")) + " " + str(m.get("category", ""))).lower()
            if not any(k in text for k in KEYWORDS):
                continue
            recs.append({
                "snap_date": SNAP_DATE,
                "id": m.get("id"),
                "question": m.get("question"),
                "category": m.get("category"),
                "outcomes": str(m.get("outcomes")),
                "prices": str(m.get("outcomePrices")),
                "volume": m.get("volume"),
                "end_date": m.get("endDate"),
            })
        df = pd.DataFrame(recs)
        if df.empty:
            return "polymarket: 0 matching markets (keyword set?)"
        _append(df, OUT_DIR / "polymarket_snapshots.parquet", ["snap_date", "id"])
        return f"polymarket: snapped {len(df)} macro-bucket markets"
    except Exception as e:
        return f"polymarket: FAILED ({type(e).__name__}: {e})"


def snapshot_kalshi() -> str:
    try:
        rows, cursor = [], None
        for _ in range(10):
            url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open"
            if cursor:
                url += f"&cursor={cursor}"
            data = json.loads(_get(url, timeout=60))
            rows += data.get("markets", [])
            cursor = data.get("cursor")
            if not cursor:
                break
            time.sleep(0.2)
        recs = []
        for m in rows:
            text = (str(m.get("title", "")) + " " + str(m.get("category", ""))).lower()
            if not any(k in text for k in KEYWORDS):
                continue
            recs.append({
                "snap_date": SNAP_DATE,
                "ticker": m.get("ticker"),
                "title": m.get("title"),
                "category": m.get("category"),
                "yes_bid": m.get("yes_bid"), "yes_ask": m.get("yes_ask"),
                "last_price": m.get("last_price"), "volume": m.get("volume"),
                "close_time": m.get("close_time"),
            })
        df = pd.DataFrame(recs)
        if df.empty:
            return "kalshi: 0 matching markets"
        _append(df, OUT_DIR / "kalshi_snapshots.parquet", ["snap_date", "ticker"])
        return f"kalshi: snapped {len(df)} macro-bucket markets"
    except Exception as e:
        return f"kalshi: FAILED ({type(e).__name__}: {e}) — if 401/403, public access changed; report"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for r in [pull_gpr(), pull_epu(), pull_gdelt_timelines(),
              snapshot_polymarket(), snapshot_kalshi()]:
        print(f"[T136-D] {r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
