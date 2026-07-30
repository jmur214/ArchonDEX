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


# --- T-290 d2: the rate-path store (our free FedWatch equivalent) --------- #
#
# The generic snapshot_kalshi() above KEYWORD-filters and reads the legacy
# yes_bid/last_price fields (now null on the current API) — so it is blind to
# the Fed rate-decision market. This dedicated fetch is UNFILTERED, keyed on
# the KXFED series prefix, and archives the FULL target-range bucket
# distribution every day. For each FOMC meeting Kalshi lists threshold markets
# ("upper bound above X% following the <meeting>") whose yes prices ARE the
# market-implied probabilities the CME FedWatch tool sells — free, and ours
# forward from today. History accrues from the first run; thin far-future
# buckets may have null prices now (archived anyway so the series is complete
# once liquidity appears). Paired with the FRED resolution series (the realized
# target range + effective rate the markets settle against).
KXFED_SERIES = "KXFED"
# FRED keyless CSV (fredgraph.csv?id=): the resolution series. DFEDTARL/U = the
# realized target-range lower/upper bound; EFFR = the effective fed funds rate.
FRED_RATE_SERIES = ["DFEDTARL", "DFEDTARU", "EFFR"]


def snapshot_kxfed() -> str:
    """Daily snapshot of the FULL KXFED (Fed funds rate) bucket distribution —
    the free FedWatch-equivalent. Unfiltered, keyed on the series prefix; reads
    the current *_dollars/*_fp fields (the legacy yes_bid/last_price are null)."""
    try:
        rows, cursor = [], None
        for _ in range(20):
            url = (f"https://api.elections.kalshi.com/trade-api/v2/markets?"
                   f"series_ticker={KXFED_SERIES}&limit=200")
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
            recs.append({
                "snap_date": SNAP_DATE,
                "series": KXFED_SERIES,
                "event_ticker": m.get("event_ticker"),   # the FOMC meeting
                "ticker": m.get("ticker"),                # the threshold bucket
                "title": m.get("title"),
                "yes_sub_title": m.get("yes_sub_title"),
                "floor_strike": m.get("floor_strike"),    # the % threshold
                "cap_strike": m.get("cap_strike"),
                "strike_type": m.get("strike_type"),
                # implied probabilities (dollars = 0..1 yes price on this API)
                "yes_bid": m.get("yes_bid_dollars"),
                "yes_ask": m.get("yes_ask_dollars"),
                "no_bid": m.get("no_bid_dollars"),
                "no_ask": m.get("no_ask_dollars"),
                "last_price": m.get("last_price_dollars"),
                "previous_price": m.get("previous_price_dollars"),
                "volume": m.get("volume_fp"),
                "volume_24h": m.get("volume_24h_fp"),
                "open_interest": m.get("open_interest_fp"),
                "liquidity": m.get("liquidity_dollars"),
                "status": m.get("status"),
                "result": m.get("result"),
                "close_time": m.get("close_time"),
                "expiration_time": m.get("expiration_time"),
            })
        df = pd.DataFrame(recs)
        if df.empty:
            return "kxfed: 0 markets (API empty/changed — report if persistent)"
        _append(df, OUT_DIR / "kalshi_kxfed_snapshots.parquet",
                ["snap_date", "ticker"])
        n_meet = df["event_ticker"].nunique()
        return f"kxfed: snapped {len(df)} buckets across {n_meet} FOMC meetings"
    except Exception as e:
        return f"kxfed: FAILED ({type(e).__name__}: {e})"


def pull_fred_rate_path() -> str:
    """The FRED resolution series (DFEDTARL/U + EFFR) — what the KXFED markets
    settle against. Keyless fredgraph.csv; long-form (series, observation_date,
    value), deduped so it re-fetches the full history idempotently each run."""
    try:
        frames = []
        for sid in FRED_RATE_SERIES:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            df = pd.read_csv(io.BytesIO(_get(url, timeout=60)))
            df.columns = ["observation_date", "value"]
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["value"])
            df.insert(0, "series", sid)
            frames.append(df)
        if not frames:
            return "fred_rate_path: no series fetched"
        allf = pd.concat(frames, ignore_index=True)
        _append(allf, OUT_DIR / "fred_rate_path.parquet",
                ["series", "observation_date"])
        last = {s: g["observation_date"].iloc[-1]
                for s, g in allf.groupby("series")}
        return f"fred_rate_path: archived {len(allf)} rows for {FRED_RATE_SERIES}; last {last}"
    except Exception as e:
        return f"fred_rate_path: FAILED ({type(e).__name__}: {e})"


# --- T-334: the archive queue (hoard-now; each feed's VALUE accrues with history) --- #
# SEC requires a declared UA with contact info (their fair-access policy).
SEC_UA = {"User-Agent": "ArchonDEX Research jsm13700@gmail.com"}
# The CEF fields worth keeping: the discount-capture signal set the parked T-267 alpha
# needed (its data objection dissolves PROSPECTIVELY — nobody sells this PIT panel).
CEF_FIELDS = ["Ticker", "Name", "SponsorName", "CategoryName", "NAV", "Price",
              "Discount", "Discount52WkAvg", "IsDiscountBelow52WkAvg", "Price52WkAvg",
              "ZScore3M", "ZScore6M", "ZScore1Yr", "ZScoreDate", "DistributionRateNAV",
              "DistributionRatePrice", "DistributionFrequency", "DistributionDate",
              "CurrentDistribution", "UNIIPerShare", "IsManagedDistribution",
              "LeverageRatioPercentage", "IsLeveraged", "ExpenseRatio", "AvgDailyVolume",
              "MarketCapUSDm", "TotalAssetsUSDm", "NAVPublished", "LastUpdated", "Cusip"]


def snapshot_cef() -> str:
    """Daily CEF panel: NAV, price, DISCOUNT (+52wk avg, z-scores), distribution rate.
    CEFConnect's public DailyPricing endpoint. This is the point-in-time discount panel
    T-267's alpha was parked for want of (paid CRSP); archived forward it becomes a
    5-year-fuse asset nobody can buy retroactively."""
    try:
        # BROWSER UA required: CEFConnect stalls on our contact-info UA but serves a
        # generic one in <1s (verified). Same UA-sensitivity class as the T-295 Yahoo
        # 429 — a per-endpoint header quirk, not a rate limit.
        _req = urllib.request.Request("https://www.cefconnect.com/api/v3/DailyPricing",
                                      headers={"User-Agent": "Mozilla/5.0"})
        rows = json.loads(urllib.request.urlopen(_req, timeout=120).read())
        if not rows:
            return "cef: 0 funds returned (endpoint changed?) — LOUD"
        df = pd.DataFrame(rows)
        keep = [c for c in CEF_FIELDS if c in df.columns]
        df = df[keep].copy()
        df.insert(0, "snap_date", SNAP_DATE)
        _append(df, OUT_DIR / "cef_daily.parquet", ["snap_date", "Ticker"])
        n = len(pd.read_parquet(OUT_DIR / "cef_daily.parquet"))
        disc = pd.to_numeric(df.get("Discount"), errors="coerce")
        return (f"cef: snapped {len(df)} funds ({len(keep)} fields); "
                f"median discount {disc.median():.2f}%, "
                f"{int((disc < -10).sum())} at >10% discount; parquet {n}")
    except Exception as e:
        return f"cef: FAILED ({type(e).__name__}: {e})"


def pull_form4_index(days_back: int = 5) -> str:
    """EDGAR Form 4 (insider transactions) DAILY-INDEX archive.

    Scope note (honest): this archives the INDEX — who filed a Form 4, for which CIK,
    when, and the accession path — NOT the parsed per-transaction XML. That is the
    deliberate prerequisite the dispatch asked for: the opportunistic-vs-routine
    classification needs accumulated HISTORY, and the index is what makes the filings
    retrievable later. Per-filing XML parsing is a separate, larger task."""
    try:
        frames, hit, miss = [], [], []
        for i in range(days_back):
            d = pd.Timestamp.now().normalize() - pd.Timedelta(days=i)
            if d.weekday() >= 5:
                continue                                  # no dissemination on weekends
            url = (f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/"
                   f"QTR{(d.month - 1) // 3 + 1}/form.{d.strftime('%Y%m%d')}.idx")
            try:
                txt = _get(url, timeout=60).decode("latin-1")
            except Exception:
                miss.append(str(d.date()))                # holiday / not yet posted
                continue
            recs = []
            for line in txt.splitlines():
                p = line.split()
                # fixed-width: [form, ...company..., CIK, date_filed, file_name]
                if len(p) < 5 or p[0] != "4" or not p[-3].isdigit():
                    continue
                recs.append({"form_type": p[0], "company": " ".join(p[1:-3]),
                             "cik": p[-3], "date_filed": p[-2], "file_name": p[-1],
                             "archive_vintage": SNAP_DATE})
            if recs:
                frames.append(pd.DataFrame(recs))
                hit.append(f"{d.date()}:{len(recs)}")
        if not frames:
            return f"form4: 0 rows across {days_back}d (missing {miss}) — LOUD"
        allf = pd.concat(frames, ignore_index=True)
        _append(allf, OUT_DIR / "edgar_form4_index.parquet",
                ["cik", "date_filed", "file_name"])
        n = len(pd.read_parquet(OUT_DIR / "edgar_form4_index.parquet"))
        return (f"form4: archived {len(allf)} filings [{', '.join(hit)}]; "
                f"{allf['cik'].nunique()} distinct CIKs; parquet {n} (INDEX only, not XML)")
    except Exception as e:
        return f"form4: FAILED ({type(e).__name__}: {e})"


def pull_usaspending(days_back: int = 7) -> str:
    """USASpending.gov federal contract awards (free, structured, underexplored).
    Prime contract awards (types A-D) over the trailing window, largest first."""
    try:
        end = pd.Timestamp.now().normalize()
        start = end - pd.Timedelta(days=days_back)
        body = json.dumps({
            "filters": {"time_period": [{"start_date": str(start.date()),
                                         "end_date": str(end.date())}],
                        "award_type_codes": ["A", "B", "C", "D"]},
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                       "Awarding Sub Agency", "Start Date", "End Date",
                       "Description", "recipient_id"],
            "page": 1, "limit": 100, "sort": "Award Amount", "order": "desc"}).encode()
        req = urllib.request.Request(
            "https://api.usaspending.gov/api/v2/search/spending_by_award/",
            data=body, headers={**UA, "Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req, timeout=90).read()).get("results", [])
        if not res:
            return f"usaspending: 0 awards in {days_back}d window — LOUD"
        df = pd.DataFrame(res)
        df.insert(0, "snap_date", SNAP_DATE)
        key = "Award ID" if "Award ID" in df.columns else "internal_id"
        _append(df, OUT_DIR / "usaspending_awards.parquet", ["snap_date", key])
        n = len(pd.read_parquet(OUT_DIR / "usaspending_awards.parquet"))
        amt = pd.to_numeric(df.get("Award Amount"), errors="coerce")
        return (f"usaspending: archived {len(df)} awards (top-100 by $) "
                f"total ${amt.sum()/1e9:.2f}B, max ${amt.max()/1e6:.0f}M; parquet {n}")
    except Exception as e:
        return f"usaspending: FAILED ({type(e).__name__}: {e})"



# --- T-336 / C5: the CREDIT-SPREAD RECOVERY (preservation first) --------------
# FRED now serves only a ~3yr ROLLING window on the ICE BofA OAS series (verified
# 2026-07-30: BAMLH0A0HYM2 returns 786 obs from 2023-07-31; `cosd=1996-12-31` does
# NOT restore it, so the truncation is at source — consistent with an ICE licensing
# change, which also explains why ALFRED vintage_date 404s). The 1996+ history is
# recoverable ONLY from archived snapshots. Recovered once, then archived by us
# forever: the live tail is appended daily onto the preserved deep history.
OAS_SERIES = ["BAMLH0A0HYM2", "BAMLC0A4CBBB"]      # HY OAS, BBB OAS
OAS_WAYBACK_SNAPSHOTS = ["20251104204105"]          # pre-truncation captures (CSV endpoint)


def pull_credit_spread_oas() -> str:
    """Deep ICE BofA OAS history: recover from Wayback (once), then append the live
    rolling tail daily. Idempotent — the deep rows are written once and preserved."""
    import gzip
    out = []
    for sid in OAS_SERIES:
        try:
            frames = []
            # (1) the DEEP history, from pre-truncation archived snapshots
            for ts in OAS_WAYBACK_SNAPSHOTS:
                try:
                    url = (f"https://web.archive.org/web/{ts}id_/"
                           f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
                    raw = _get(url, timeout=120)
                    if raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    frames.append(pd.read_csv(io.BytesIO(raw)))
                except Exception:
                    continue
            # (2) the LIVE rolling tail (keeps the series current going forward)
            try:
                frames.append(pd.read_csv(io.BytesIO(_get(
                    f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60))))
            except Exception:
                pass
            if not frames:
                out.append(f"{sid}: NO source reachable — LOUD")
                continue
            df = pd.concat(frames, ignore_index=True)
            df.columns = ["observation_date", "value"][:len(df.columns)]
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["value"])
            df.insert(0, "series", sid)
            _append(df, OUT_DIR / "credit_spread_oas.parquet", ["series", "observation_date"])
            cur = pd.read_parquet(OUT_DIR / "credit_spread_oas.parquet")
            cur = cur[cur["series"] == sid]
            out.append(f"{sid}: {len(cur)} obs {cur.observation_date.min()}..{cur.observation_date.max()}")
        except Exception as e:
            out.append(f"{sid}: FAILED ({type(e).__name__})")
    return ("credit_oas: " + " | ".join(out)
            + "  [deep history from archived snapshots; FRED live serves ~3yr only]")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for r in [pull_gpr(), pull_epu(),
              snapshot_polymarket(), snapshot_kalshi(),
              snapshot_kxfed(), pull_fred_rate_path(),
              snapshot_cef(), pull_form4_index(), pull_usaspending(),
              pull_credit_spread_oas()]:
        print(f"[T136-D] {r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
