"""
scripts/archive_positioning_t136.py
===================================
T-2026-06-10-136 Part C — positioning archivers ($0, public sources).

These series are SHALLOW at the source (limited lookback) — every week not
archived is depth lost forever (the hoard-now principle). Each source is
failure-isolated (one 404 doesn't kill the run) and idempotent
(append-to-parquet with dedup). Cron-able: run daily/weekly as-is.

Sources (free, license-safe):
  - FINRA Reg SHO daily short volume (CNMS consolidated file; short VOLUME ≠
    short INTEREST — documented; TRF/ADF/ORF venues are inside the CNMS file)
  - SEC fails-to-deliver (half-month ZIPs, 2008+)
  - NAAIM manager-exposure index (weekly CSV/XLS from naaim.org)
  - FINRA margin statistics (monthly; page-scraped XLSX link)
  - FINRA bi-monthly equity short interest (API/file availability varies —
    best-effort, status reported)
  - AAII sentiment: LOGIN-WALLED (free account) — NOT automated; documented
    for a manual/credentialed pull (per brief "login noted").

Output: data/positioning/<source>.parquet
Usage: python -m scripts.archive_positioning_t136 [--days-back 10]
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

OUT_DIR = ROOT / "data" / "positioning"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}


def _get_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _append_parquet(df: pd.DataFrame, path: Path, dedup_keys: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_parquet(path)
        df = pd.concat([old, df], ignore_index=True)
    n0 = len(df)
    df = df.drop_duplicates(subset=dedup_keys, keep="last")
    df.to_parquet(path, index=False)
    return n0 - len(df)


def pull_regsho_short_volume(days_back: int) -> str:
    rows = []
    today = pd.Timestamp.now().normalize()
    for i in range(days_back):
        d = today - pd.Timedelta(days=i)
        if d.weekday() >= 5:
            continue
        ds = d.strftime("%Y%m%d")
        try:
            blob = _get_bytes(f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{ds}.txt")
            df = pd.read_csv(io.BytesIO(blob), sep="|")
            df = df[df.columns[:6]]
            df.columns = ["date", "symbol", "short_volume", "short_exempt_volume",
                          "total_volume", "market"][:len(df.columns)]
            df = df[pd.to_numeric(df["short_volume"], errors="coerce").notna()]
            rows.append(df)
            time.sleep(0.13)
        except Exception:
            continue
    if not rows:
        return "regsho: no files in window (weekend/holiday or URL change)"
    allr = pd.concat(rows, ignore_index=True)
    _append_parquet(allr, OUT_DIR / "finra_regsho_short_volume.parquet",
                    ["date", "symbol"])
    return f"regsho: archived {len(rows)} day-files ({len(allr)} rows). NOTE short volume != short interest."


def pull_sec_ftd() -> str:
    now = pd.Timestamp.now()
    pulled = []
    for back in range(1, 4):  # last ~2 months of half-month files
        d = now - pd.DateOffset(months=back // 2)
        ym = d.strftime("%Y%m")
        for half in ("a", "b"):
            url = f"https://www.sec.gov/files/data/fails-deliver-data/cnsfails{ym}{half}.zip"
            try:
                blob = _get_bytes(url, timeout=120)
                with zipfile.ZipFile(io.BytesIO(blob)) as z:
                    name = z.namelist()[0]
                    df = pd.read_csv(z.open(name), sep="|", encoding="latin-1",
                                     on_bad_lines="skip", dtype=str)
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                pulled.append((f"{ym}{half}", df))
                time.sleep(0.2)
            except Exception:
                continue
    if not pulled:
        return "ftd: no files reachable (URL/format change?) — check manually"
    allf = pd.concat([d for _, d in pulled], ignore_index=True)
    keys = [c for c in ("settlement_date", "symbol", "cusip") if c in allf.columns]
    _append_parquet(allf, OUT_DIR / "sec_ftd.parquet", keys or list(allf.columns[:2]))
    return f"ftd: archived {[k for k, _ in pulled]} ({len(allf)} rows)"


def pull_naaim() -> str:
    candidates = [
        "https://naaim.org/wp-content/uploads/USE_Data.xlsx",
        "https://naaim.org/wp-content/uploads/USE-Data.xlsx",
    ]
    # fall back to scraping the program page for the data link
    try:
        page = _get_bytes("https://naaim.org/programs/naaim-exposure-index/").decode(
            "utf-8", errors="replace")
        import re
        links = re.findall(r'href="([^"]+\.(?:xlsx?|csv))"', page)
        candidates = [l if l.startswith("http") else "https://naaim.org" + l
                      for l in links] + candidates
    except Exception:
        pass
    from scripts._xlsx_min import read_xlsx_first_sheet, excel_serial_to_datetime
    for url in candidates:
        try:
            blob = _get_bytes(url)
            if url.endswith(".xlsx"):
                df = read_xlsx_first_sheet(blob)   # stdlib (no openpyxl)
            elif url.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(blob))
            else:
                continue  # legacy .xls (binary BIFF) unsupported without deps
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            dcol = next((c for c in df.columns if "date" in c), df.columns[0])
            df = df.rename(columns={dcol: "date"})
            parsed = pd.to_datetime(df["date"], errors="coerce")
            if parsed.isna().mean() > 0.5:  # Excel serial dates
                parsed = excel_serial_to_datetime(df["date"])
            df["date"] = parsed
            df = df.dropna(subset=["date"])
            if df.empty:
                continue
            _append_parquet(df, OUT_DIR / "naaim_exposure.parquet", ["date"])
            return f"naaim: archived {len(df)} rows from {url.split('/')[-1]}"
        except Exception:
            continue
    return "naaim: no data link reachable (page layout change?) — check manually"


def pull_finra_margin() -> str:
    try:
        page = _get_bytes(
            "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
        ).decode("utf-8", errors="replace")
        import re
        # inline HTML table first (no Excel engine installed); xlsx via the
        # stdlib reader as fallback
        try:
            tables = pd.read_html(io.StringIO(page))
        except Exception:
            tables = []
        if tables:
            df = max(tables, key=len)
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            _append_parquet(df, OUT_DIR / "finra_margin_debt.parquet",
                            [df.columns[0]])
            return f"margin: archived inline table ({len(df)} rows)"
        links = re.findall(r'href="([^"]+\.xlsx)"', page)
        if links:
            from scripts._xlsx_min import read_xlsx_first_sheet
            url = links[0] if links[0].startswith("http") else "https://www.finra.org" + links[0]
            df = read_xlsx_first_sheet(_get_bytes(url))
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            _append_parquet(df, OUT_DIR / "finra_margin_debt.parquet", [df.columns[0]])
            return f"margin: archived {len(df)} rows from {url.split('/')[-1]}"
        return "margin: no inline table and no xlsx link — layout change"
    except Exception as e:
        return f"margin: FAILED ({type(e).__name__}: {e}) — check manually"


def pull_finra_short_interest() -> str:
    # FINRA's consolidated equity short interest moved behind api.finra.org
    # (free but registered). The legacy public CSV path is tried; status
    # reported honestly either way.
    try:
        d = pd.Timestamp.now().normalize()
        # try the most recent likely settlement dates (15th & EOM, T+~9 publish)
        for back in range(0, 45):
            dd = d - pd.Timedelta(days=back)
            if dd.day not in (15, 28, 29, 30, 31):
                continue
            ds = dd.strftime("%Y%m%d")
            url = f"https://cdn.finra.org/equity/otcmarket/biweekly/shrt{ds}.csv"
            try:
                blob = _get_bytes(url)
                df = pd.read_csv(io.BytesIO(blob), sep="|")
                _append_parquet(df, OUT_DIR / "finra_short_interest.parquet",
                                list(df.columns[:2]))
                return f"short_interest: archived {ds} ({len(df)} rows)"
            except Exception:
                continue
        return ("short_interest: legacy CSV path 404 — series now behind "
                "api.finra.org (free registration). FLAGGED: needs a one-time "
                "credential decision (user) or the API onboarding.")
    except Exception as e:
        return f"short_interest: FAILED ({e})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=10)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = [
        pull_regsho_short_volume(args.days_back),
        pull_sec_ftd(),
        pull_naaim(),
        pull_finra_margin(),
        pull_finra_short_interest(),
        "aaii: LOGIN-WALLED (free account) — not automated; manual pull of "
        "sentiment.xls documented as the procedure (per brief).",
    ]
    for r in report:
        print(f"[T136-C] {r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
