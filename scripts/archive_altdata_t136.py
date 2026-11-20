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
  - Kalshi (public market-data API): the macro SERIES listed in the reviewed, committed
    config/kalshi_macro_series.json (T-405, 2026-11-19). One request per listed series,
    under a time budget and a request cap.

KALSHI SNAPSHOT HISTORY (T-405 — read before using kalshi_snapshots.parquet):
  Every row written June → 2026-11-18 (21,294 rows) is a multivariate sports parlay
  (ticker prefix KXMVE). The old selector paged the first 2,000 OPEN markets — on the
  current API almost all of them parlays — and kept titles containing a keyword as a
  SUBSTRING, so "powell" matched Norman Powell and "gold" matched Golden State. Those rows
  carry no quote (0.0 bid, 0.0 last, 0 volume). They are KEPT, never rewritten
  ([NN-ARCHIVE]), and stay identifiable: `selector` is null and the ticker starts with
  KXMVE. Rows from T-405 on carry `selector == "series_v1"` and `series_ticker`. Filter on
  `selector` before using this file. The old selector's code is in git history (b74a490).

  Which series are listed: `--discover-kalshi-series` reads /series and the open events,
  keeps macro series by a whole-word match on the series title (or an exact Kalshi tag),
  drops parlays/combos, KXFED (snapshot_kxfed has it), intraday series and state/city
  series, and writes the config for review. Re-run it when Kalshi lists new series.

  A "real quote" (T-405) is bid > 0, or last > 0, or 0 < ask < 1. A zero bid, a zero last
  and a 1.00 ask are an empty book. The snapshot's priced count and its fail-closed check,
  and both resolvers' choice of what to look up, use this rule.

Output: data/macro_data/alt/*.parquet (+ dated snapshot rows appended)
Usage: python -m scripts.archive_altdata_t136                       (the daily run)
       python -m scripts.archive_altdata_t136 --discover-kalshi-series
       python -m scripts.archive_altdata_t136 --kalshi-only --out-dir DIR   (smoke)
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "macro_data" / "alt"
# Generic client name for every NON-SEC host (privacy, 2026-11-17): the owner's contact
# address is approved for SEC EDGAR hosts ONLY (user ruling 2026-11-11). Before this fix the
# contact UA went to every host this script calls (Polymarket, Kalshi, FRED, Wayback,
# USASpending, policyuncertainty.com, matteoiacoviello.com). `_get` picks SEC_UA only for
# sec.gov hosts.
UA = {"User-Agent": "ArchonDEX-research/1.0"}
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


def _is_sec_host(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    return host == "sec.gov" or host.endswith(".sec.gov")


def _headers_for(url: str) -> dict:
    """SEC hosts get the declared-contact UA their fair-access policy requires; every other
    host gets the generic client name. Never send the contact address anywhere else."""
    return SEC_UA if _is_sec_host(url) else UA


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=_headers_for(url))
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
                # 2026-11-17: the quote fields the probe audit (T-403) found missing.
                "best_bid": _num(m.get("bestBid")),
                "best_ask": _num(m.get("bestAsk")),
                "last_trade_price": _num(m.get("lastTradePrice")),
                "spread": _num(m.get("spread")),
                "liquidity": _num(m.get("liquidityNum")),
                "volume_24h": _num(m.get("volume24hr")),
                "condition_id": m.get("conditionId"),
            })
        df = pd.DataFrame(recs)
        if df.empty:
            return "polymarket: 0 matching markets (keyword set?)"
        # T-405: a real quote, not merely a non-null field (a 0 bid / 1.00 ask is empty).
        quoted = int(_real_quote(df["best_bid"], df["best_ask"], df["last_trade_price"]).sum())
        if quoted == 0:
            # Fail closed: a day of rows with no quote at all is a changed schema, not a
            # quiet market. Write nothing, so the verifier's zero-fresh-rows gate fires.
            return (f"polymarket: FAILED — {len(df)} matching markets but NONE carries a real "
                    f"quote (API field names changed?); nothing written — LOUD")
        _append(df, OUT_DIR / "polymarket_snapshots.parquet", ["snap_date", "id"])
        return f"polymarket: snapped {len(df)} macro-bucket markets ({quoted} quoted)"
    except Exception as e:
        return f"polymarket: FAILED ({type(e).__name__}: {e})"


# --- T-405 (2026-11-19): the Kalshi archive selects by SERIES ------------------------------ #
# See the module docstring for why: the old open-market paging + substring keywords archived
# nothing but parlays. Discovery (rare, reviewed) writes the series list; the daily snapshot
# reads only that list and never falls back to paging the open-market firehose.
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_SERIES_CONFIG = ROOT / "config" / "kalshi_macro_series.json"
KALSHI_SELECTOR = "series_v1"
KALSHI_TIME_BUDGET_S = 180.0        # the daily snapshot's wall-clock cap
KALSHI_MAX_REQUESTS = 600           # and its request cap (one per series, + cursor pages)
# Concurrency, measured 2026-11-19 on the public endpoint: 1 worker = 403 requests in 177 s,
# 0 errors; 4 workers = ~68 s but 21-30 series lost to HTTP 429. Two workers with backoff.
KALSHI_WORKERS = 2                  # concurrent series fetches (I/O-bound; see snapshot_kalshi)
KALSHI_PAUSE_S = 0.1                # per worker, between requests
KALSHI_429_RETRIES = 3              # per request, backing off 1/2/4 s (or Retry-After)
KALSHI_TIMEOUT_S = 20               # per request; bounds the overrun past the deadline
KALSHI_MAX_PAGES_PER_SERIES = 5     # 5 x 1000 markets; one endless cursor cannot eat the budget
KALSHI_DISCOVERY_MAX_PAGES = 400    # /events?status=open pages (200 each) before discovery gives up
# A recurring series BETWEEN events (last one settled, next not listed yet) is still listed if
# its latest settled event closed within this window. 120 days = a quarterly cycle (~92 days,
# the longest normal gap of a monthly/quarterly series) plus four weeks of listing slack.
# one_off series never list again, so they need an open event. Annual series can gap longer;
# a re-discovery picks them up when relisted (the snapshot WARNs past KALSHI_CONFIG_STALE_DAYS).
KALSHI_DISCOVERY_LOOKBACK_DAYS = 120
KALSHI_DISCOVERY_MAX_ERROR_SHARE = 0.10   # more lookup errors than this -> config not written
KALSHI_CONFIG_STALE_DAYS = 60       # the snapshot line WARNs when the series list is older
# The snapshot writes what came back (hoard), but the day is a FAILED day — main() exits
# non-zero so the wrapper alarms — when fewer than this share of listed series completed
# (an empty pull is a completed series) or the budget cut the run short.
KALSHI_MIN_COMPLETE_SHARE = 0.90
# ... and it writes NOTHING when fewer than this share of rows carry a real quote (measured
# 2026-11-19: 5,653 of 5,681 = 99.5 %), or when any price is outside [0, 1] (a units change,
# e.g. cents: the numbers would be wrong, not just empty).
KALSHI_MIN_QUOTED_SHARE = 0.50
_KALSHI_PRICE_COLS = ("yes_bid", "yes_ask", "no_bid", "no_ask", "last_price")

# Intraday series are skipped: a once-a-day snapshot of a market that lives 15 minutes or an
# hour is one random intraday point on an underlying whose price we already have, and the
# hourly ladders are the heaviest series per row (6 open events x a strike ladder each).
KALSHI_SKIP_FREQUENCIES = frozenset({"fifteen_min", "hourly"})


def _word_pattern(words: Iterable[str], capture: bool = True) -> str:
    """A regex matching any of ``words`` as a WHOLE word (use with re.IGNORECASE); one
    capture group when ``capture`` (for str.extract), none otherwise (for str.contains).

    Alphanumeric lookarounds rather than ``\\b``: ``\\b`` misfires on tokens that begin or
    end with punctuation ("s&p 500", "eur/usd"). Whole-word matching is what stops "gold"
    matching "Golden State". It does not stop a person's name ("Norman Powell" contains the
    word "powell"), so no person names are keywords and the category gate comes first."""
    alts = "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))
    group = "(" if capture else "(?:"
    return rf"(?<![a-z0-9]){group}{alts})(?![a-z0-9])"


# Title keywords for Economics / Financials / Commodities series. Words, not stems.
_MACRO_TITLE_WORDS = (
    # prices
    "inflation", "deflation", "cpi", "pce", "ppi",
    # labour
    "unemployment", "payrolls", "jobs numbers", "jobs report", "jobless claims",
    "initial claims", "nonfarm", "job openings", "jolts", "adp", "hourly earnings",
    "labor force participation", "sahm rule",
    # activity
    "gdp", "recession", "recessions", "retail sales", "ism", "pmi", "consumer sentiment",
    "industrial production", "durable goods", "productivity", "trade deficit",
    "balance of trade",
    # housing
    "housing starts", "home sales", "building permits", "mortgage", "case-shiller",
    # rates, money, credit
    "fed", "fomc", "federal reserve", "fed funds", "rate cut", "rate cuts", "rate hike",
    "rate hikes", "interest rate", "dot plot", "balance sheet", "sofr", "effr", "treasury",
    "treasuries", "ust", "2y", "5y", "7y", "10y", "30y", "m2", "money supply", "central bank",
    "credit rating", "default", "defaults", "debt ceiling", "deficit",
    # equity indices and risk
    "s&p 500", "s&p500", "s&p", "sp500", "nasdaq", "nasdaq-100", "dow jones", "djia",
    "russell 2000", "vix", "fear and greed", "stock market", "nyse",
    # currencies
    "eur/usd", "eurusd", "usd/jpy", "usdjpy", "gbp/usd", "gbpusd", "usd/cad", "usdcad",
    "aud/usd", "audusd", "usd/mxn", "usdmxn", "dxy", "dollar index", "usd index",
    "de-dollarization",
    # energy and metals
    "wti", "brent", "crude", "oil price", "opec", "spr", "natural gas", "gas price",
    "gasoline", "diesel", "gold", "silver", "copper", "platinum", "palladium",
)
# Exact Kalshi tags (case-insensitive) that qualify a macro-category series on their own.
_MACRO_TAGS = frozenset({
    "fed", "federal reserve", "interest rates", "gdp", "global central banks", "s&p 500",
    "nasdaq-100", "indices", "foreign exchange", "credit & bonds", "precious metals",
    "oil & gas",
})
# Politics qualifies by one of these exact tags (monetary, trade and fiscal policy) or by a
# NARROW title phrase (Fed chair / FOMC / government shutdown; several such series carry only
# a "Trump" or "Congress" tag). Generic words are not enough there ("tax" alone is a thousand
# state and city bills; bare "shutdown" is "Federal AI model shutdown authority").
_POLICY_TAGS = frozenset({"federal reserve", "trade & tariffs", "budget & shutdowns"})
_POLICY_TITLE_WORDS = (
    "fed chair", "fomc", "federal reserve", "government shutdown", "government shut down",
    "shutdown by", "shutdown this year", "shutdown vote",
)
# ... but a policy phrase inside a NOVELTY market is not policy: "Will Trump visit the
# Federal Reserve?", "Will the Fed chair attend the dinner?". Politics only, whole words.
_POLITICS_NOVELTY_PATTERN = _word_pattern(
    ("visit", "visits", "attend", "attends", "dinner", "lunch", "golf"), capture=False)
# Crypto: the two majors only (the system has a BTC arm in forward validation, T-272).
_CRYPTO_TITLE_WORDS = ("bitcoin", "btc", "ethereum", "eth")

# category -> (title pattern or None, qualifying tags). A category absent here is never
# archived. Excluded, with the reason: Elections (8.9k open events, candidate races — not a
# market input, and it would swamp the rest); World (3 open events, none macro); Sports,
# Entertainment, Mentions, Exotics (the parlays), Climate, Science, Companies (per-firm KPIs).
_KALSHI_RULES: dict[str, tuple[str | None, frozenset[str]]] = {
    "Economics": (_word_pattern(_MACRO_TITLE_WORDS), _MACRO_TAGS),
    "Financials": (_word_pattern(_MACRO_TITLE_WORDS), _MACRO_TAGS),
    "Commodities": (_word_pattern(_MACRO_TITLE_WORDS), _MACRO_TAGS),
    "Politics": (_word_pattern(_POLICY_TITLE_WORDS), _POLICY_TAGS),
    "Crypto": (_word_pattern(_CRYPTO_TITLE_WORDS), frozenset()),
}
_US_STATES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "district of columbia", "nyc",
)
# State and city series (50 state gas prices a day, state employment by industry) are
# regional detail, not market inputs. Dropped by title or by Kalshi's own local tags.
_REGIONAL_PATTERN = _word_pattern(_US_STATES, capture=False)
_REGIONAL_TAGS = frozenset({"local", "nyc"})
# ... and titles that START with an upper-case postal code AND go on to name a local retail
# price ("TX gas price"). A bare code is ambiguous with country codes — "IN CPI" (India),
# "DE GDP" (Germany), "CA unemployment", "ID rate decision" (Indonesia) — so a code in front
# of a macro statistic is read as national/foreign and KEPT: a wrongly kept state series costs
# one request a day, a wrongly dropped national one loses information. Case-sensitive code,
# anchored (measured 2026-11-19: of 52 candidate titles opening with two capitals, TX gas
# price was the only state series).
_STATE_CODE_PREFIX = (r"^(?:AK|AL|AR|AZ|CA|CO|CT|DC|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|"
                      r"ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|"
                      r"UT|VA|VT|WA|WI|WV|WY)\s(?i:.*(?<![a-z0-9])(?:gas prices?|diesel(?: prices?)?"
                      r"|home prices?|home values?|house prices?|rents?|electricity prices?)"
                      r"(?![a-z0-9]))")
# ... except national series NAMED after a state: the University of Michigan survey.
_NATIONAL_TITLE_PATTERN = _word_pattern(
    ("university of michigan", "michigan consumer sentiment", "umich"), capture=False)
_COMBO_PATTERN = _word_pattern(("combo",), capture=False)
# The "<X> after economic events" family ("Will the 10Y yield be above 4.59% on Nov 19 at
# 1:15pm ET?") is an intraday point-price ladder keyed to a release minute — the same class
# as the hourly series — and measured 2026-11-19 it was 8,010 of 13,691 rows (58%), most
# with zero volume (51-strike market-maker ladders). Skipped for the same reason.
_EVENT_LADDER_PATTERN = r"(?<![a-z0-9])after (?:economic )?events(?![a-z0-9])"


def _parse_ts(values: pd.Series | list, utc: bool = True) -> pd.Series:
    """API timestamps -> datetimes. format="ISO8601" is REQUIRED: Kalshi sends both
    "…:00Z" and "…:00.484355Z" (the historical API carries microseconds), and pandas 3
    otherwise infers one format from the first value and silently coerces the other shape
    to NaT — which once dropped every between-events series from a discovery."""
    return pd.to_datetime(pd.Series(values), utc=utc, errors="coerce", format="ISO8601")


def _tag_match(tags: pd.Series, allowed: frozenset[str]) -> pd.Series:
    """Per row: the first of the row's tags (a list) that equals an allowed tag,
    case-insensitively, lower-cased; NA when none does."""
    flat = tags.explode().astype("string").str.strip().str.lower()
    first = flat.where(flat.isin(allowed).fillna(False)).groupby(level=0).first()
    return first.reindex(tags.index).astype("string")


def _classify_series(series: list[dict], open_events: dict[str, int]) -> pd.DataFrame:
    """Every /series row with `matched` (the qualifying keyword/tag, or NA), `excluded`
    (a parlay, combo, KXFED, intraday, event-minute ladder or state/city series) and
    n_open_events. Pure. A candidate is matched & ~excluded."""
    cols = ["ticker", "title", "category", "frequency", "tags"]
    df = pd.DataFrame.from_records(series, columns=cols) if series else pd.DataFrame(columns=cols)
    for c in ("ticker", "title", "category", "frequency"):
        df[c] = df[c].astype("string").fillna("").str.strip()
    df["tags"] = df["tags"].map(lambda t: list(t) if isinstance(t, (list, tuple)) else [])
    df["n_open_events"] = df["ticker"].map(open_events).fillna(0).astype(int)

    matched = pd.Series(pd.NA, index=df.index, dtype="string")
    for category, (pattern, tags) in _KALSHI_RULES.items():
        in_cat = df["category"] == category
        if pattern is not None:
            word = df["title"].str.extract(pattern, flags=re.IGNORECASE)[0]
            matched = matched.mask(in_cat & matched.isna() & word.notna(),
                                   "title:" + word.str.lower())
        if tags:
            tag = _tag_match(df["tags"], tags)
            matched = matched.mask(in_cat & matched.isna() & tag.notna(), "tag:" + tag)
    df["matched"] = matched

    upper = df["ticker"].str.upper()
    title = df["title"]
    regional = ((title.str.contains(_REGIONAL_PATTERN, flags=re.IGNORECASE, regex=True)
                 | title.str.contains(_STATE_CODE_PREFIX, regex=True))
                & ~title.str.contains(_NATIONAL_TITLE_PATTERN, flags=re.IGNORECASE, regex=True))
    df["excluded"] = (
        upper.str.startswith("KXMVE")                       # multivariate parlays
        | (upper == KXFED_SERIES)                           # snapshot_kxfed archives it whole
        | upper.str.endswith("COMBO")                       # joint-outcome bundles
        | title.str.contains(_COMBO_PATTERN, flags=re.IGNORECASE, regex=True)
        | df["frequency"].isin(KALSHI_SKIP_FREQUENCIES)
        | title.str.contains(_EVENT_LADDER_PATTERN, flags=re.IGNORECASE, regex=True)
        | regional
        | _tag_match(df["tags"], _REGIONAL_TAGS).notna()
        | (df["category"].eq("Politics")
           & title.str.contains(_POLITICS_NOVELTY_PATTERN, flags=re.IGNORECASE, regex=True))
    ).astype(bool)
    return df


def _is_candidate(df: pd.DataFrame) -> pd.Series:
    return df["matched"].notna() & ~df["excluded"]


def select_kalshi_series(series: list[dict], open_events: dict[str, int],
                         last_close: dict[str, str] | None = None,
                         now: pd.Timestamp | None = None) -> pd.DataFrame:
    """The macro series to archive. Pure (no network).

    A candidate (rule-matched, not excluded) is kept when it has an OPEN event, or — for a
    recurring (not one_off) series between events — when its latest settled event closed
    within KALSHI_DISCOVERY_LOOKBACK_DAYS (``last_close``: ticker -> ISO close time).
    Returns ticker, title, category, frequency, tags, n_open_events, last_close and
    `matched`, sorted by category then ticker."""
    df = _classify_series(series, open_events)
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    closes = _parse_ts(df["ticker"].map(last_close or {}))
    recent = (closes.notna() & (now - closes <= pd.Timedelta(days=KALSHI_DISCOVERY_LOOKBACK_DAYS))
              & df["frequency"].ne("one_off"))
    keep = _is_candidate(df) & ((df["n_open_events"] > 0) | recent)
    df["last_close"] = closes.dt.strftime("%Y-%m-%dT%H:%M:%SZ").astype(object).where(
        closes.notna(), None)
    out = df.loc[keep, ["ticker", "title", "category", "frequency", "tags",
                        "n_open_events", "last_close", "matched"]]
    return out.sort_values(["category", "ticker"]).reset_index(drop=True)


def _last_settled_close(ticker: str, budget: _RequestBudget) -> str | None:
    """The latest market close of the series' most recent SETTLED event (Kalshi lists
    settled events newest first), or None when it has none. The event's last_updated_ts is
    NOT a close time (KXGDP's reads its creation date), so the nested markets are read —
    and when that list is EMPTY (the event settled before /historical/cutoff, ~2 months
    back, so its markets moved to the historical API) the historical listing is read.
    Without that, the 120-day lookback would silently act as ~61 days."""
    if not budget.take():
        raise RuntimeError("discovery budget exhausted")
    data = _kalshi_json(f"{KALSHI_API}/events?series_ticker={quote(ticker, safe='')}"
                        f"&status=settled&limit=1&with_nested_markets=true", budget)
    time.sleep(KALSHI_PAUSE_S)
    events = [e for e in (data.get("events") or [])[:1] if isinstance(e, dict)]
    if not events:
        return None
    markets = [m for m in (events[0].get("markets") or []) if isinstance(m, dict)]
    if not markets and events[0].get("event_ticker"):
        if not budget.take():
            raise RuntimeError("discovery budget exhausted")
        hist = _kalshi_json(f"{KALSHI_API}/historical/markets?event_ticker="
                            f"{quote(str(events[0]['event_ticker']), safe='')}&limit=1000", budget)
        markets = [m for m in (hist.get("markets") or []) if isinstance(m, dict)]
        time.sleep(KALSHI_PAUSE_S)
    closes = [str(m["close_time"]) for m in markets if m.get("close_time")]
    if not closes:
        return None
    parsed = _parse_ts(closes)       # compare instants, not strings ("…:00Z" vs "…:00.48Z")
    if parsed.isna().any():
        raise _UnparseableClose(f"{ticker}={closes[int(parsed.isna().argmax())]!r}")
    return closes[int(parsed.argmax())]


class _UnparseableClose(ValueError):
    """A close time the API returned that does not parse: discovery fails closed on it
    (not a tolerated lookup error — a silent drop is the defect class T-405 is about)."""


def _recent_closes(tickers: list[str]) -> tuple[dict[str, str], int, list[str]]:
    """ticker -> latest settled close for each series, fetched with the snapshot's worker
    pool; returns (closes, n_lookup_errors, unparseable 'ticker=value' strings)."""
    budget = _RequestBudget(len(tickers) * 3 + 25, time.monotonic() + 900.0)

    def one(t: str) -> tuple[str, str | None, str]:
        try:
            return t, _last_settled_close(t, budget), ""
        except _UnparseableClose as e:
            return t, None, f"unparseable:{e}"
        except Exception:
            return t, None, "error"

    with ThreadPoolExecutor(max_workers=KALSHI_WORKERS) as pool:
        got = list(pool.map(one, tickers))
    return ({t: c for t, c, _ in got if c}, sum(why == "error" for _, _, why in got),
            [why.split(":", 1)[1] for _, _, why in got if why.startswith("unparseable:")])


def _open_event_counts(max_pages: int | None = None) -> dict[str, int]:
    """Open events per series ticker, from the full /events?status=open scan. Raises if the
    scan does not finish inside ``max_pages`` (default KALSHI_DISCOVERY_MAX_PAGES, read at
    call time) — a partial scan would silently drop series."""
    max_pages = max_pages or KALSHI_DISCOVERY_MAX_PAGES
    counts: dict[str, int] = {}
    cursor: str | None = None
    for _ in range(max_pages):
        url = f"{KALSHI_API}/events?status=open&limit=200"
        if cursor:
            url += f"&cursor={quote(cursor, safe='')}"
        data = json.loads(_get(url, timeout=60))
        if not isinstance(data, dict):
            raise ValueError("events: response is not a JSON object")
        for e in data.get("events") or []:
            t = str(e.get("series_ticker") or "")
            counts[t] = counts.get(t, 0) + 1
        cursor = data.get("cursor") or None
        if not cursor:
            return counts
        time.sleep(KALSHI_PAUSE_S)
    raise RuntimeError(f"events scan incomplete after {max_pages} pages")


def _config_text(doc: dict) -> str:
    """The config as JSON with ONE LINE PER SERIES, so a re-discovery reviews as a diff."""
    head = {k: v for k, v in doc.items() if k != "series"}
    rows = ",\n  ".join(json.dumps(r, ensure_ascii=False) for r in doc["series"])
    return json.dumps(head, indent=1, ensure_ascii=False)[:-2] + (
        f',\n "series": [\n  {rows}\n ]\n}}\n')


def discover_kalshi_series(out_path: Path | None = None) -> str:
    """Write the reviewed series list (``config/kalshi_macro_series.json`` by default) from
    the live /series and open-events listings. Writes nothing on any failure."""
    path = out_path or KALSHI_SERIES_CONFIG
    try:
        data = json.loads(_get(f"{KALSHI_API}/series", timeout=120))
        series = data.get("series") if isinstance(data, dict) else None
        if not series:
            return "kalshi_discover: FAILED — /series returned no series; config not written — LOUD"
        opened = _open_event_counts()
        if not opened:
            return "kalshi_discover: FAILED — 0 open events; config not written — LOUD"
        cls = _classify_series(series, opened)
        between = cls[_is_candidate(cls) & (cls["n_open_events"] == 0)
                      & cls["frequency"].ne("one_off")]["ticker"].tolist()
        closes, lookup_errors, bad = _recent_closes(between)
        if between and lookup_errors > KALSHI_DISCOVERY_MAX_ERROR_SHARE * len(between):
            return (f"kalshi_discover: FAILED — {lookup_errors}/{len(between)} settled-event "
                    f"lookups errored; config not written — LOUD")
        bad += [f"{t}={c!r}" for t, c, ok in zip(closes, closes.values(),
                                                  _parse_ts(list(closes.values())).notna())
                if not ok]
        if bad:      # a silent NaT here drops a series from the list without a trace
            return (f"kalshi_discover: FAILED — {len(bad)} returned close times do not parse "
                    f"(e.g. {bad[0]}); config not written — LOUD")
        picked = select_kalshi_series(series, opened, closes)
        if picked.empty:
            return "kalshi_discover: FAILED — 0 series selected; config not written — LOUD"
        n_between = int((picked["n_open_events"] == 0).sum())
        doc = {
            "selector": KALSHI_SELECTOR,
            "discovered": SNAP_DATE,
            "source": (f"{KALSHI_API}/series + /events?status=open + per-series latest settled"
                       " event"),
            "n_series_listed": len(series),
            "n_series_with_open_events": len(opened),
            "n_kept_between_events": n_between,
            "rule": ("category in " + ", ".join(_KALSHI_RULES)
                     + "; whole-word title keyword or exact tag (Politics: policy tags or a"
                       " Fed-chair/FOMC/shutdown title phrase, never visit/attend/dinner"
                       " novelty; Crypto: BTC/ETH only); excludes KXMVE parlays, *COMBO, KXFED, "
                     + "/".join(sorted(KALSHI_SKIP_FREQUENCIES))
                     + " series, 'after economic events' intraday ladders, state/city series"
                       " (not the University of Michigan survey; a postal code only before a"
                       " local price); keeps a series with an open event, or a recurring one"
                       " whose latest settled event (live or historical API) closed within "
                     + f"{KALSHI_DISCOVERY_LOOKBACK_DAYS} days"),
            "series": [{**r, "discovered": SNAP_DATE} for r in picked.to_dict("records")],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(_config_text(doc))
        tmp.replace(path)
        by_cat = picked["category"].value_counts().to_dict()
        by_freq = picked["frequency"].value_counts().to_dict()
        return (f"kalshi_discover: wrote {len(picked)} series to {path} "
                f"(of {len(series)} listed, {len(opened)} with open events; {n_between} kept "
                f"between events from {len(between)} settled-event lookups, {lookup_errors} "
                f"errors); by category {by_cat}; by frequency {by_freq}")
    except Exception as e:
        return f"kalshi_discover: FAILED ({type(e).__name__}: {e}); config not written — LOUD"


def load_kalshi_series(path: Path | None = None) -> tuple[pd.DataFrame, str | None]:
    """(the listed series — ticker, category — and the config's `discovered` date). The
    frame is EMPTY when the file is missing, unparseable or lists nothing. Parlays and KXFED
    are dropped even if listed."""
    try:
        doc = json.loads((path or KALSHI_SERIES_CONFIG).read_text())
        rows = doc.get("series") if isinstance(doc, dict) else None
        df = pd.DataFrame.from_records(rows or [], columns=["ticker", "category"])
        discovered = str(doc.get("discovered")) if doc.get("discovered") else None
    except Exception:          # missing, unreadable or malformed: the caller fails closed
        return pd.DataFrame(columns=["ticker", "category"]), None
    df["ticker"] = df["ticker"].astype("string").fillna("").str.strip()
    upper = df["ticker"].str.upper()
    ok = df["ticker"].ne("") & ~upper.str.startswith("KXMVE") & upper.ne(KXFED_SERIES)
    return df[ok].drop_duplicates("ticker").reset_index(drop=True), discovered


def _config_age_note(discovered: str | None) -> str:
    """'list discovered D' — with a WARN when D is older than KALSHI_CONFIG_STALE_DAYS or
    unreadable (new series are then missing until --discover-kalshi-series is re-run)."""
    when = pd.to_datetime(discovered, errors="coerce", format="ISO8601")
    if pd.isna(when):
        return "series list discovered ? — WARN: no readable discovered date"
    age = int((pd.Timestamp(SNAP_DATE) - when.normalize()).days)
    warn = (f" — WARN: {age} days old (> {KALSHI_CONFIG_STALE_DAYS}); re-run "
            f"--discover-kalshi-series" if age > KALSHI_CONFIG_STALE_DAYS else "")
    return f"series list discovered {when.date()}{warn}"


@dataclass
class _RequestBudget:
    """A request cap and a wall-clock deadline (time.monotonic()) shared by one run's
    worker threads. ``take`` is the only shared mutation, under a lock."""
    max_requests: int
    deadline: float
    used: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def take(self) -> bool:
        with self._lock:
            if self.used >= self.max_requests or time.monotonic() >= self.deadline:
                return False
            self.used += 1
            return True


def _retry_wait(e: Exception, attempt: int) -> float:
    """Seconds to wait after a 429: the server's Retry-After (capped at 10 s) when it sends
    one, else 1, 2, 4 s."""
    try:
        return min(10.0, max(0.0, float(e.headers.get("Retry-After"))))  # type: ignore[attr-defined]
    except (AttributeError, TypeError, ValueError):
        return float(2 ** attempt)


def _kalshi_json(url: str, budget: _RequestBudget) -> dict:
    """GET one Kalshi URL as a JSON object. A 429 is retried up to KALSHI_429_RETRIES times
    with backoff, each retry spending one request of the budget; any other error raises."""
    from urllib.error import HTTPError
    attempt = 0
    while True:
        try:
            data = json.loads(_get(url, timeout=KALSHI_TIMEOUT_S))
            break
        except HTTPError as e:
            if e.code != 429 or attempt >= KALSHI_429_RETRIES or not budget.take():
                raise
            time.sleep(_retry_wait(e, attempt))
            attempt += 1
    if not isinstance(data, dict):
        raise ValueError("response is not a JSON object")
    return data


def _series_markets(ticker: str, budget: _RequestBudget) -> tuple[list[dict], str]:
    """The OPEN markets of one series, cursor-paged. Returns (markets, outcome): "ok" (an
    empty list is a successful empty pull), "budget" (the run's budget ran out first) or
    "page cap" (KALSHI_MAX_PAGES_PER_SERIES pages and the cursor still going; the markets
    read so far are kept). Network and parse errors propagate.

    One request per series: /markets takes ONE series_ticker (a comma list silently returns
    0 markets; a repeated parameter is a 400 — measured 2026-11-19). /events with nested
    markets costs the same (0.33 vs 0.35 s median, same bytes, same markets)."""
    markets: list[dict] = []
    cursor: str | None = None
    for _ in range(KALSHI_MAX_PAGES_PER_SERIES):
        if not budget.take():
            return markets, "budget"
        url = f"{KALSHI_API}/markets?series_ticker={quote(ticker, safe='')}&status=open&limit=1000"
        if cursor:
            url += f"&cursor={quote(cursor, safe='')}"
        data = _kalshi_json(url, budget)
        markets += [m for m in (data.get("markets") or []) if isinstance(m, dict)]
        cursor = data.get("cursor") or None
        time.sleep(KALSHI_PAUSE_S)
        if not cursor:
            return markets, "ok"
    return markets, "page cap"


@dataclass
class _SeriesResult:
    ticker: str
    markets: list[dict]
    complete: bool
    error: str | None = None


def _error_label(e: Exception) -> str:
    """A short, countable label: 'HTTP 429', 'URLError', 'ValueError'."""
    code = getattr(e, "code", None)
    return f"HTTP {code}" if isinstance(code, int) else type(e).__name__


def _fetch_series(ticker: str, budget: _RequestBudget) -> _SeriesResult:
    """One series, never raising: an error is recorded on the result and counted. A page-cap
    hit keeps the markets read but counts as an error and as an incomplete series."""
    try:
        got, outcome = _series_markets(ticker, budget)
    except Exception as e:
        return _SeriesResult(ticker, [], False, _error_label(e))
    return _SeriesResult(ticker, got, outcome == "ok",
                         "page cap" if outcome == "page cap" else None)


# snapshot column -> the current API field (the legacy yes_bid/last_price/volume fields are
# null; 2026-11-17). Prices are dollars per contract, 0..1.
_KALSHI_NUMERIC = {
    "yes_bid": "yes_bid_dollars", "yes_ask": "yes_ask_dollars",
    "no_bid": "no_bid_dollars", "no_ask": "no_ask_dollars",
    "yes_bid_size": "yes_bid_size_fp", "yes_ask_size": "yes_ask_size_fp",
    "last_price": "last_price_dollars", "previous_price": "previous_price_dollars",
    "volume": "volume_fp", "volume_24h": "volume_24h_fp", "open_interest": "open_interest_fp",
    "floor_strike": "floor_strike", "cap_strike": "cap_strike",
}
_KALSHI_TEXT = ("ticker", "event_ticker", "title", "yes_sub_title", "strike_type", "status",
                "close_time", "expiration_time")


def _kalshi_frame(markets: list[dict], series_of: list[str], category_of: dict[str, str]
                  ) -> pd.DataFrame:
    """Snapshot rows: the pre-T-405 columns, plus series_ticker, selector and the strike
    fields (a ladder row means nothing without its threshold)."""
    # Text columns keep pandas' inferred dtype (as the pre-T-405 rows were built), so the
    # append concatenates like-with-like; numerics are coerced to float64.
    raw = pd.DataFrame.from_records(markets)
    out = pd.DataFrame({"snap_date": SNAP_DATE}, index=raw.index)
    for col in _KALSHI_TEXT:
        out[col] = raw[col] if col in raw else None
    for col, src in _KALSHI_NUMERIC.items():
        out[col] = (pd.to_numeric(raw[src], errors="coerce").astype("float64") if src in raw
                    else np.nan)
    out["series_ticker"] = pd.Series(series_of, index=raw.index)
    out["category"] = out["series_ticker"].map(category_of)
    out["selector"] = KALSHI_SELECTOR
    return out


def snapshot_kalshi() -> str:
    """Daily snapshot of the OPEN markets in every series listed in the reviewed config.

    Writes NOTHING and returns a LOUD "FAILED" line when the config is missing or empty, when
    no market comes back, when any price is outside [0, 1] (a units change), or when fewer
    than KALSHI_MIN_QUOTED_SHARE of the rows carry a real quote. On a SHORT day — fewer than
    KALSHI_MIN_COMPLETE_SHARE of the listed series completed, or the budget cut the run — it
    still writes the real rows that came back (hoard), and the line says FAILED so main()
    exits non-zero and the wrapper alarms. It never falls back to paging the open-market
    list (the parlay defect, T-405). Never raises: main() evaluates every pull, and the
    cloud pulse reports this line as is."""
    try:
        return _snapshot_kalshi()
    except Exception as e:
        return f"kalshi: FAILED ({type(e).__name__}: {e}) — LOUD"


def _bad_units(df: pd.DataFrame) -> pd.Series:
    """Rows with any price outside [0, 1] (dollars per contract): a units change upstream."""
    prices = pd.concat([_num_col(df, c) for c in _KALSHI_PRICE_COLS], axis=1)
    return ((prices > 1) | (prices < 0)).any(axis=1)


def _snapshot_kalshi() -> str:
    t0 = time.monotonic()
    listed, discovered = load_kalshi_series()
    age = _config_age_note(discovered)
    if listed.empty:
        return (f"kalshi: FAILED — no series listed in {KALSHI_SERIES_CONFIG} (missing, empty "
                f"or unparseable; run --discover-kalshi-series); nothing written — LOUD")
    budget = _RequestBudget(KALSHI_MAX_REQUESTS, t0 + KALSHI_TIME_BUDGET_S)
    tickers = [str(t) for t in listed["ticker"]]
    # Threads, not asyncio: urllib is blocking and the work is I/O. No deadlock is possible —
    # workers share only the budget's lock (held for a counter update, never across I/O),
    # none waits on another, and every request has a timeout, so leaving the pool waits at
    # most one KALSHI_TIMEOUT_S per worker past the deadline. map() keeps the listed order.
    with ThreadPoolExecutor(max_workers=KALSHI_WORKERS) as pool:
        results = list(pool.map(lambda t: _fetch_series(t, budget), tickers))
    markets = [mk for r in results for mk in r.markets]
    series_of = [r.ticker for r in results for _ in r.markets]
    errs = [r.error for r in results if r.error]
    cut = sum(r.error is None and not r.complete for r in results)
    done = sum(r.complete for r in results)
    df = (_kalshi_frame(markets, series_of, dict(zip(listed["ticker"], listed["category"])))
          if markets else pd.DataFrame(columns=["ticker"]))
    no_ticker = df["ticker"].isna() | df["ticker"].astype("string").fillna("").str.strip().eq("")
    errs += ["no ticker"] * int(no_ticker.sum())          # never counted, never written
    df = df[~no_ticker.to_numpy(dtype=bool)]
    df = df[~df["ticker"].astype("string").str.upper().str.startswith("KXMVE").fillna(False)]
    err_by = pd.Series(errs, dtype="object").value_counts()
    kinds = f" {err_by.to_dict()}" if len(errs) else ""
    stats = (f"{done}/{len(tickers)} series, {len(errs)} errors{kinds}, "
             f"{budget.used} requests, {time.monotonic() - t0:.0f}s; {age}")
    if df.empty:
        return f"kalshi: FAILED — 0 open markets ({stats}); nothing written — LOUD"
    bad_units = int(_bad_units(df).sum())
    if bad_units:
        return (f"kalshi: FAILED — {bad_units} of {len(df)} markets carry a price outside "
                f"[0, 1] (units changed?) ({stats}); nothing written — LOUD")
    quoted = int(_kalshi_quoted(df).sum())
    if quoted == 0:
        return (f"kalshi: FAILED — {len(df)} markets but NONE carries a real quote (bid > 0, "
                f"last > 0 or 0 < ask < 1) ({stats}); nothing written — LOUD")
    if quoted < KALSHI_MIN_QUOTED_SHARE * len(df):
        return (f"kalshi: FAILED — only {quoted} of {len(df)} markets carry a real quote "
                f"(< {KALSHI_MIN_QUOTED_SHARE:.0%}) ({stats}); nothing written — LOUD")
    _append(df, OUT_DIR / "kalshi_snapshots.parquet", ["snap_date", "ticker"])
    head = (f"snapped {len(df)} markets ({quoted} priced = a real quote) from {stats}; "
            f"selector {KALSHI_SELECTOR}")
    if done < KALSHI_MIN_COMPLETE_SHARE * len(tickers) or cut:
        why = (f"the budget ({KALSHI_MAX_REQUESTS} requests / {KALSHI_TIME_BUDGET_S:.0f}s) ran "
               f"out before {cut} series" if cut else
               f"fewer than {KALSHI_MIN_COMPLETE_SHARE:.0%} of listed series completed")
        return f"kalshi: FAILED — PARTIAL day, {why}; the real rows were kept: {head} — LOUD"
    return f"kalshi: {head}"


# --- 2026-11-17: OUTCOMES for the markets we snapshot ------------------------ #
# A probability archive is worth nothing without what happened. Each run looks up the
# markets we captured WITH A REAL QUOTE whose close/end time has passed and that have no
# final outcome recorded yet, capped per run, and appends the outcome. Rows without a real
# quote are never looked up: there is nothing to score. That covers the July-November
# Kalshi rows (prices null).
#
# Kalshi (T-405 follow-up, 2026-11-19): only rows with selector == "series_v1" are resolved —
# every older row is a parlay by construction — and the lookup is ONE GET PER EVENT
# (/events/{event_ticker}, which lists every market of the event with status / result /
# settlement_value_dollars / expiration_value, and 404s for a gone event). The series archive
# closes ~750 strikes a day (each daily ladder is new tickers) in ~33 events; one GET per
# market against a 300 cap would fall ~450 a day further behind, forever.
MAX_RESOLVE_PER_RUN = 300                  # Polymarket: markets per run (one GET each)
# Kalshi: events per run. ~35-50 events close a day at the 2026-11-19 list (31 daily series,
# plus the weekly/monthly/one-off ones); 150 is ~3x that, so a backlog from a missed day or
# two drains within days, and a full run stays ~1 minute.
MAX_RESOLVE_EVENTS_PER_RUN = 150
# A snapped ticker missing from its own event's live response — or whose event GET is a
# 404 — is first looked for in the HISTORICAL API by event (markets settled before
# /historical/cutoff, ~2 months back, move there), then on its own: live /markets/{ticker},
# and on its 404 /historical/markets/{ticker}. Only when BOTH 404 is it recorded final
# "not_found". It is never marked final from an event listing that lacks it, and it is not
# left to ride on the event: its event would then be re-fetched every day forever. Beyond
# this cap (tickers per run) it simply stays pending.
MAX_RESOLVE_MARKET_FALLBACKS_PER_RUN = 50
KALSHI_RESOLVE_TIME_BUDGET_S = 120.0
# Order: events never asked before go first (earliest close first), then re-asks of events
# that came back not yet settled (least recently asked first), so re-asks cannot starve new
# events. A non-final event whose earliest pending close is older than this many days
# (settlement is normally hours to a few days after close; 30 days means a dispute or a
# delayed source) is re-asked at most once every KALSHI_STALE_REASK_EVERY_DAYS. Nothing is
# ever marked final that the API does not report final.
KALSHI_STALE_REASK_DAYS = 30
KALSHI_STALE_REASK_EVERY_DAYS = 7


def _num_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Column ``col`` as floats; all-NaN when the column is absent (older rows)."""
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce").astype("float64")


def _real_quote(bid: pd.Series, ask: pd.Series, last: pd.Series) -> pd.Series:
    """T-405: a row carries a real quote only if bid > 0, or last > 0, or 0 < ask < 1.

    A zero bid, a zero last and a 1.00 ask (nobody selling YES below a dollar) are an empty
    book, and so is a null. A tiny positive ask (Polymarket's 0.001 on a long shot) IS a
    quote. Applied wherever a row is judged priced: the snapshots' counts and fail-closed
    checks, and the resolvers' choice of what to look up."""
    b, a, lp = (pd.to_numeric(s, errors="coerce").astype("float64") for s in (bid, ask, last))
    return (b > 0) | (lp > 0) | ((a > 0) & (a < 1))


def _kalshi_quoted(df: pd.DataFrame) -> pd.Series:
    return _real_quote(_num_col(df, "yes_bid"), _num_col(df, "yes_ask"),
                       _num_col(df, "last_price"))


def _outcome_price_inside(prices: pd.Series) -> pd.Series:
    """Per row: does the outcomePrices string ('["0.42", "0.58"]') hold any price strictly
    between 0 and 1. "None", "[]", 0 and 1 do not count."""
    nums = prices.astype("string").str.findall(r"\d*\.?\d+(?:[eE][-+]?\d+)?").explode()
    v = pd.to_numeric(nums, errors="coerce")
    inside = ((v > 0) & (v < 1)).groupby(level=0).any()
    return inside.reindex(prices.index, fill_value=False).astype(bool)


def _polymarket_quoted(df: pd.DataFrame) -> pd.Series:
    """The book rule on best_bid/best_ask/last_trade_price; rows from before 2026-11-17
    carry only `prices`, so a displayed price strictly inside (0, 1) also counts."""
    book = _real_quote(_num_col(df, "best_bid"), _num_col(df, "best_ask"),
                       _num_col(df, "last_trade_price"))
    if "prices" not in df.columns:
        return book
    return book | _outcome_price_inside(df["prices"])


def _num(x):
    """A float, or None for a missing / unparseable value (the APIs send strings)."""
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _pending_frame(snap_path: Path, res_path: Path, key: str, end_col: str,
                   quoted: Callable[[pd.DataFrame], pd.Series],
                   keep: Callable[[pd.DataFrame], pd.Series] | None = None) -> pd.DataFrame:
    """Snapshot rows to look up, one per ``key``, earliest close first: a real quote
    (``quoted``), an optional extra row filter (``keep``), a close/end in the past, and no
    final outcome recorded yet. Uncapped; the callers cap."""
    if not snap_path.exists():
        return pd.DataFrame(columns=[key, "_end"])
    snaps = pd.read_parquet(snap_path)
    if key not in snaps.columns or end_col not in snaps.columns:
        return pd.DataFrame(columns=[key, "_end"])
    mask = quoted(snaps).to_numpy(dtype=bool)
    if keep is not None:          # not `&=`: to_numpy() can hand back a read-only view
        mask = mask & keep(snaps).to_numpy(dtype=bool)
    snaps = snaps[mask]
    snaps = snaps.assign(_end=_parse_ts(snaps[end_col]))        # index-aligned
    snaps = snaps[snaps["_end"] < pd.Timestamp.now(tz="UTC")]
    done: set = set()
    if res_path.exists():
        res = pd.read_parquet(res_path)
        done = set(res.loc[res["final"].astype(bool), key].astype(str))
    out = snaps.sort_values("_end", kind="stable").assign(**{key: lambda d: d[key].astype(str)})
    out = out.drop_duplicates(key)
    return out[~out[key].isin(done)].reset_index(drop=True)


def _pending(snap_path: Path, res_path: Path, key: str, end_col: str,
             quoted: Callable[[pd.DataFrame], pd.Series]) -> list[str]:
    """Keys to look up one GET each (Polymarket), capped at MAX_RESOLVE_PER_RUN."""
    frame = _pending_frame(snap_path, res_path, key, end_col, quoted)
    return frame[key].tolist()[:MAX_RESOLVE_PER_RUN]


def _is_series_v1(df: pd.DataFrame) -> pd.Series:
    """Rows written by the series selector. Every older row is a parlay (T-405)."""
    if "selector" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["selector"].astype("string").eq(KALSHI_SELECTOR).fillna(False).astype(bool)


def _last_asked(res_path: Path) -> dict[str, pd.Timestamp]:
    """ticker -> the date it was last looked up and came back NOT final."""
    if not res_path.exists():
        return {}
    res = pd.read_parquet(res_path)
    nf = res[~res["final"].astype(bool)]
    return dict(zip(nf["ticker"].astype(str), _parse_ts(nf["looked_up"], utc=False)))


def _kalshi_pending_events(snap: Path, res_path: Path
                           ) -> tuple[list[tuple[str, list[str]]], list[str], int]:
    """(events to ask, in order; the pending tickers without an event_ticker, looked up one
    by one; the number of stale re-asks held back this run). Order: never-asked events by
    earliest close, then re-asks by least recently asked (see KALSHI_STALE_REASK_DAYS)."""
    pend = _pending_frame(snap, res_path, "ticker", "close_time", _kalshi_quoted,
                          keep=_is_series_v1)
    if pend.empty:
        return [], [], 0
    pend["_asked"] = pd.to_datetime(pend["ticker"].map(_last_asked(res_path)), errors="coerce")
    ev = (pend["event_ticker"].astype("string").str.strip() if "event_ticker" in pend
          else pd.Series(pd.NA, index=pend.index, dtype="string"))
    has_ev = (ev.notna() & ev.ne("")).fillna(False).astype(bool)
    g = (pend[has_ev].assign(_ev=ev[has_ev].astype(str))
         .groupby("_ev", sort=False)
         .agg(tickers=("ticker", list), first_close=("_end", "min"), last_asked=("_asked", "max")))
    today = pd.Timestamp(SNAP_DATE)
    fresh = g[g["last_asked"].isna()].sort_values("first_close", kind="stable")
    again = g[g["last_asked"].notna()]
    stale = again["first_close"] < pd.Timestamp.now(tz="UTC") - pd.Timedelta(
        days=KALSHI_STALE_REASK_DAYS)
    held = stale & (today - again["last_asked"] < pd.Timedelta(days=KALSHI_STALE_REASK_EVERY_DAYS))
    again = again[~held].sort_values("last_asked", kind="stable")
    ordered = pd.concat([fresh, again])
    return (list(zip(ordered.index.astype(str), ordered["tickers"])),
            pend.loc[~has_ev, "ticker"].tolist(), int(held.sum()))


def _kalshi_resolution(ticker: str, m: dict, via: str) -> dict:
    """One resolutions row from a market object (event listing or single-market GET)."""
    status, result = m.get("status"), m.get("result")
    return {"ticker": ticker, "event_ticker": m.get("event_ticker"), "title": m.get("title"),
            "status": status, "result": result,
            "settlement_value": _num(m.get("settlement_value_dollars")),
            "expiration_value": _num(m.get("expiration_value")),
            "close_time": m.get("close_time"), "settlement_ts": m.get("settlement_ts"),
            "final": status in ("settled", "finalized") and bool(result),
            "resolved_via": via, "looked_up": SNAP_DATE}


def _kalshi_gone(ticker: str, event_ticker: str | None, via: str) -> dict:
    """A market that neither the live API nor the historical API has (both 404 on its own
    ticker). Recorded final so it is not retried daily. A live 404 alone is NOT this: Kalshi
    moves markets settled before /historical/cutoff to the historical API."""
    return {"ticker": ticker, "event_ticker": event_ticker, "status": "not_found",
            "result": None, "final": True, "resolved_via": via, "looked_up": SNAP_DATE}


def _event_markets(data: dict) -> list[dict]:
    """The markets of an /events/{ticker} response: top-level `markets`, or nested under
    `event` when with_nested_markets=true (both shapes measured 2026-11-19)."""
    event = data.get("event")
    nested = event.get("markets") if isinstance(event, dict) else None
    return [m for m in (data.get("markets") or nested or []) if isinstance(m, dict)]


def resolve_kalshi_snapshots() -> str:
    """Outcomes for the series_v1 snapshot rows, one GET per event. Never raises."""
    try:
        return _resolve_kalshi()
    except Exception as e:
        return f"kalshi_resolve: FAILED ({type(e).__name__}: {e}) — LOUD"


def _resolve_kalshi() -> str:
    snap, res_path = OUT_DIR / "kalshi_snapshots.parquet", OUT_DIR / "kalshi_resolutions.parquet"
    events, loose, held = _kalshi_pending_events(snap, res_path)
    if not events and not loose:
        return ("kalshi_resolve: nothing pending" if not held else
                f"kalshi_resolve: nothing due ({held} stale non-final events held to a weekly "
                f"re-ask)")
    due, events = len(events), events[:MAX_RESOLVE_EVENTS_PER_RUN]
    # Each event costs at most 2 GETs (live, then historical for what the live listing
    # lacks); each single-market fallback at most 2 (live, then historical); + 429 retries.
    budget = _RequestBudget(
        2 * MAX_RESOLVE_EVENTS_PER_RUN + 2 * MAX_RESOLVE_MARKET_FALLBACKS_PER_RUN + 25,
        time.monotonic() + KALSHI_RESOLVE_TIME_BUDGET_S)
    recs, missing, ev_errored, asked = _resolve_live_events(events, budget)
    hist_recs, absent, hist_errs, hist_asked = _resolve_historical_events(missing, budget)
    one_recs, one_errored, fallbacks = _resolve_single_markets(list(loose) + absent, budget)
    recs += hist_recs + one_recs
    event_of = {t: ev for ev, ts in events for t in ts}
    attempts = ([_kalshi_attempt(t, ev) for t, ev in ev_errored.items()]
                + [_kalshi_attempt(t, event_of.get(t)) for t in one_errored])
    if recs or attempts:
        _append(pd.DataFrame(recs + attempts), res_path, ["ticker"])
    n_final = sum(1 for r in recs if r["final"])
    n_hist = sum(1 for r in recs if r.get("resolved_via") == "historical")
    errs = len(set(ev_errored.values())) + hist_errs + len(one_errored)   # events + tickers
    return (f"kalshi_resolve: {asked}/{due} due events looked up "
            f"(cap {MAX_RESOLVE_EVENTS_PER_RUN}), {len(recs)} markets recorded, {n_final} final, "
            f"{len(recs) - n_final} not yet settled, {n_hist} from the historical API; "
            f"{sum(map(len, missing.values()))} missing from their live event -> {hist_asked} "
            f"historical event lookups; {len(loose) + len(absent)} still unresolved or without "
            f"an event -> {fallbacks} single-market lookups; {held} stale re-asks held; "
            f"{errs} errors ({len(attempts)} tickers kept pending as lookup_error attempts); "
            f"{budget.used} requests")


def _resolve_live_events(events: list[tuple[str, list[str]]], budget: _RequestBudget
                         ) -> tuple[list[dict], dict[str, list[str]], dict[str, str], int]:
    """One live /events/{ev} GET per event. Returns (records, event -> snapped tickers the
    live listing lacks — all of them on a 404 or an empty listing, ticker -> event for the
    tickers whose event GET errored (left pending), events asked)."""
    from urllib.error import HTTPError
    recs: list[dict] = []
    missing: dict[str, list[str]] = {}
    errored: dict[str, str] = {}
    asked = 0
    for ev, tickers in events:
        if not budget.take():
            break
        asked += 1
        lacking: list[str] = []
        try:
            data = _kalshi_json(f"{KALSHI_API}/events/{quote(ev, safe='')}", budget)
            listed = {str(m.get("ticker")): m for m in _event_markets(data)}
            recs += [_kalshi_resolution(t, listed[t], "event") for t in tickers if t in listed]
            lacking = [t for t in tickers if t not in listed]
        except HTTPError as e:
            if e.code == 404:                      # not authoritative per market
                lacking = tickers
            else:
                errored.update(dict.fromkeys(tickers, ev))
        except Exception:
            errored.update(dict.fromkeys(tickers, ev))
        if lacking:
            missing[ev] = lacking
        time.sleep(KALSHI_PAUSE_S)
    return recs, missing, errored, asked


def _resolve_historical_events(missing: dict[str, list[str]], budget: _RequestBudget
                               ) -> tuple[list[dict], list[str], int, int]:
    """Markets settled before /historical/cutoff (~2 months back) leave the live API: the
    live event lists 0 markets and /markets/{t} 404s, while /historical/markets keeps the full
    outcome (measured 2026-11-19 on KXCPI-26AUG). One /historical/markets?event_ticker= GET
    per event with missing tickers. Returns (records, tickers still unresolved, errors,
    events asked). A ticker absent from the historical listing goes on to the single-market
    lookups; nothing is marked final here unless the historical API says it is."""
    recs: list[dict] = []
    still: list[str] = []
    errs = asked = 0
    for ev, lacking in missing.items():
        if not budget.take():
            break                                   # the rest stay pending until next run
        asked += 1
        try:
            data = _kalshi_json(f"{KALSHI_API}/historical/markets?event_ticker="
                                f"{quote(ev, safe='')}&limit=1000", budget)
            hist = {str(m.get("ticker")): m for m in (data.get("markets") or [])
                    if isinstance(m, dict)}
            recs += [_kalshi_resolution(t, hist[t], "historical") for t in lacking if t in hist]
            still += [t for t in lacking if t not in hist]
        except Exception:
            errs += 1
            still += lacking
        time.sleep(KALSHI_PAUSE_S)
    return recs, still, errs, asked


def _lookup_one_market(t: str, budget: _RequestBudget) -> tuple[dict | None, bool]:
    """(record or None, errored) for one ticker: live /markets/{t}; on its 404,
    /historical/markets/{t}; final "not_found" only when BOTH 404. The answer must BE the
    market asked for (a payload for another ticker is an error, never recorded under t).
    (None, False) means the budget ran out before the historical step."""
    from urllib.error import HTTPError
    url_t = quote(t, safe="")
    try:
        m, via = _kalshi_json(f"{KALSHI_API}/markets/{url_t}", budget).get("market"), "market"
    except HTTPError as e:
        if e.code != 404:
            return None, True
        if not budget.take():
            return None, False
        try:
            m, via = (_kalshi_json(f"{KALSHI_API}/historical/markets/{url_t}", budget)
                      .get("market"), "historical")
        except HTTPError as e2:
            return ((_kalshi_gone(t, None, "market+historical"), False) if e2.code == 404
                    else (None, True))
        except Exception:
            return None, True
    except Exception:
        return None, True
    if isinstance(m, dict) and str(m.get("ticker")) == t:
        return _kalshi_resolution(t, m, via), False
    return None, True                    # empty, or another market's payload: not t's outcome


def _resolve_single_markets(tickers: list[str], budget: _RequestBudget
                            ) -> tuple[list[dict], list[str], int]:
    """Per ticker (≤ MAX_RESOLVE_MARKET_FALLBACKS_PER_RUN), see _lookup_one_market. Returns
    (records, tickers whose lookup errored — left pending, tickers attempted)."""
    recs: list[dict] = []
    errored: list[str] = []
    tried = 0
    for t in tickers[:MAX_RESOLVE_MARKET_FALLBACKS_PER_RUN]:
        if not budget.take():
            break
        tried += 1
        rec, err = _lookup_one_market(t, budget)
        time.sleep(KALSHI_PAUSE_S)
        if rec is not None:
            recs.append(rec)
        if err:
            errored.append(t)
    return recs, errored, tried


def _kalshi_attempt(ticker: str, event_ticker: str | None) -> dict:
    """A NON-final row for a ticker whose lookup errored this run. Without it the ticker has
    no resolutions row at all, so its event reads as never asked every run: it sorts first
    and escapes the stale-event weekly hold. Never final; a later real answer replaces it."""
    return {"ticker": ticker, "event_ticker": event_ticker, "status": "lookup_error",
            "result": None, "final": False, "resolved_via": "error", "looked_up": SNAP_DATE}


def resolve_polymarket_snapshots() -> str:
    """Outcomes for the Polymarket snapshot rows, one GET per market. Never raises (one
    corrupt parquet must not turn main()'s log into a bare traceback); a FAILED line makes
    main() exit non-zero, because no other gate watches the resolvers."""
    try:
        return _resolve_polymarket()
    except Exception as e:
        return f"polymarket_resolve: FAILED ({type(e).__name__}: {e}) — LOUD"


def _resolve_polymarket() -> str:
    from urllib.error import HTTPError
    snap, res_path = (OUT_DIR / "polymarket_snapshots.parquet",
                      OUT_DIR / "polymarket_resolutions.parquet")
    todo = _pending(snap, res_path, "id", "end_date", _polymarket_quoted)
    if not todo:
        return "polymarket_resolve: nothing pending"
    recs, errs = [], 0
    for i in todo:
        try:
            m = json.loads(_get(f"https://gamma-api.polymarket.com/markets/{int(i)}", timeout=30))
            status = m.get("umaResolutionStatus")
            final = bool(m.get("closed")) and status == "resolved"
            recs.append({"id": str(i), "question": m.get("question"),
                         "closed": bool(m.get("closed")), "resolution_status": status,
                         "outcomes": str(m.get("outcomes")),
                         "final_prices": str(m.get("outcomePrices")),
                         "closed_time": m.get("closedTime"),
                         "final": final, "looked_up": SNAP_DATE})
        except HTTPError as e:
            if e.code == 404:
                recs.append({"id": str(i), "resolution_status": "not_found",
                             "final": True, "looked_up": SNAP_DATE})
            else:
                errs += 1
        except Exception:
            errs += 1
        time.sleep(0.2)
    if recs:
        _append(pd.DataFrame(recs), res_path, ["id"])
    n_final = sum(1 for r in recs if r["final"])
    return (f"polymarket_resolve: looked up {len(todo)}, {n_final} final, "
            f"{len(recs) - n_final} not yet resolved, {errs} errors")


# --- T-290 d2: the rate-path store (our free FedWatch equivalent) --------- #
#
# When this was written the generic snapshot_kalshi() keyword-filtered and read the
# legacy yes_bid/last_price fields — blind to the Fed rate-decision market. (Since
# T-405 it reads a series list, from which KXFED is excluded because this fetch has
# it.) This dedicated fetch is UNFILTERED, keyed on
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


# --- T-412: the event desk's FORWARD 8-K feed ---------------------------------------- #
# The event interpreter (intelligence/event_call/) read a batch-built research panel
# (data/edgar/8k/panel_8k_items.parquet) that is in no image and no sync and ends
# 2026-06-10, so in the cloud it saw no document on any day (T-411 Part 3 row 6). This is
# its forward feed, built from the same two SEC sources the research panel and the Form 4
# pull already use:
#   1. the EDGAR daily FORM index (one request per business day) -> the day's 8-K rows
#      (form == "8-K" exactly; 8-K/A excluded, as T-137) for the tracked universe's CIKs;
#   2. ONE submissions request per filing company -> the item codes, acceptance time and
#      primary document for each new accession (the research panel's own field names).
# Accessions already in the panel are never asked for again. SEC fair access: SEC_UA (via
# _get, sec.gov hosts only), ~7.7 req/s, a request cap and a wall-clock budget. The result
# lands in OUT_DIR (the synced alt-data directory) beside a receipt that states what was
# asked and what came back, so a zero is never silent.
EDGAR_8K_PANEL = "edgar_8k_items.parquet"
EDGAR_8K_RECEIPT = "edgar_8k_fetch_receipt.json"
EDGAR_TICKERS_CACHE = "edgar_company_tickers.json"
EDGAR_TICKERS_MAX_AGE_DAYS = 7          # SEC's ticker map changes slowly; refresh weekly
EDGAR_8K_RATE_SLEEP_S = 0.13            # ~7.7 req/s, under SEC's 10 req/s ceiling
EDGAR_8K_MAX_SUBMISSIONS = 150          # a normal day needs ~25 (one per filing company)
EDGAR_8K_TIME_BUDGET_S = 120.0          # wall-clock cap on the whole pull
EDGAR_8K_TIMEOUT_S = 20                 # per request
EDGAR_8K_COLUMNS = ["ticker", "cik", "accession", "filing_date", "acceptance_dt", "items",
                    "primary_document", "company", "index_date", "fetched_at"]


def _sec_ticker_key(t: str) -> str:
    """SEC's ticker map spells share classes with '-' (BRK-B); the membership file and
    Alpaca use '.' (BRK.B). Compare on one spelling."""
    return str(t).strip().upper().replace(".", "-")


def _edgar_cik_map(universe: list[str], today: pd.Timestamp) -> dict[int, str]:
    """{CIK: the universe ticker that files under it}, from SEC's company_tickers.json,
    cached in OUT_DIR and refreshed weekly. Where one CIK carries several universe tickers
    (GOOG/GOOGL) the first in sorted order is used, so a filing is recorded once."""
    cache = OUT_DIR / EDGAR_TICKERS_CACHE
    data = None
    try:
        cached = json.loads(cache.read_text())
        age = (today - pd.Timestamp(cached["fetched_at"][:10])).days
        if age <= EDGAR_TICKERS_MAX_AGE_DAYS and isinstance(cached.get("data"), dict):
            data = cached["data"]
    except Exception:
        data = None
    if data is None:
        data = json.loads(_get("https://www.sec.gov/files/company_tickers.json",
                               timeout=EDGAR_8K_TIMEOUT_S))
        time.sleep(EDGAR_8K_RATE_SLEEP_S)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"fetched_at": str(today.date()), "data": data}))
    by_key = {_sec_ticker_key(t): t for t in universe}
    out: dict[int, str] = {}
    for v in data.values():
        t = by_key.get(_sec_ticker_key(v.get("ticker", "")))
        if t is None:
            continue
        cik = int(v["cik_str"])
        out[cik] = min(out.get(cik, t), t)
    return out


def _parse_form_index_8k(txt: str) -> pd.DataFrame:
    """The 8-K rows of one EDGAR daily form index (fixed-width: form, company..., CIK,
    date filed, file name). Vectorised over the ~3,000 lines of a business day."""
    empty = pd.DataFrame(columns=["cik", "accession", "index_date", "company"])
    parts = pd.Series(txt.splitlines(), dtype=object).str.split()
    parts = parts[(parts.str.len() >= 5) & parts.str[0].eq("8-K")]
    parts = parts[parts.str[-3].str.isdigit().fillna(False).astype(bool)]
    if parts.empty:
        return empty
    dates = pd.to_datetime(parts.str[-2], format="mixed", errors="coerce")
    parts, dates = parts[dates.notna()], dates[dates.notna()]
    if parts.empty:
        return empty
    return pd.DataFrame({
        "cik": parts.str[-3].astype(int).to_numpy(),
        # edgar/data/<cik>/<accession>.txt -> the accession
        "accession": parts.str[-1].str.rsplit("/", n=1).str[-1]
                                  .str.replace(".txt", "", regex=False).to_numpy(),
        "index_date": dates.dt.strftime("%Y-%m-%d").to_numpy(),
        "company": parts.str[1:-3].str.join(" ").to_numpy(),
    })


def pull_8k_items(universe: Iterable[str] | None = None, *, as_of: str | None = None,
                  days_back: int = 5, max_submissions: int | None = None,
                  time_budget_s: float | None = None) -> str:
    """The forward 8-K feed for the tracked universe (see the block comment above). Never
    raises: every failure is a 'FAILED (...)' line, and the receipt records it."""
    try:
        return _pull_8k_items(universe, as_of=as_of, days_back=days_back,
                              max_submissions=max_submissions, time_budget_s=time_budget_s)
    except Exception as e:
        _write_8k_receipt({"ok": False, "error": f"{type(e).__name__}: {e}"})
        return f"edgar_8k: FAILED ({type(e).__name__}: {e})"


def _write_8k_receipt(receipt: dict) -> None:
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        receipt = {"_schema": "edgar_8k_fetch_receipt/v1",
                   "fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), **receipt}
        (OUT_DIR / EDGAR_8K_RECEIPT).write_text(json.dumps(receipt, indent=2, default=str))
    except Exception:
        pass                               # the returned line still carries the outcome


def _pull_8k_items(universe: Iterable[str] | None, *, as_of: str | None, days_back: int,
                   max_submissions: int | None, time_budget_s: float | None) -> str:
    t0 = time.monotonic()
    max_submissions = max_submissions or EDGAR_8K_MAX_SUBMISSIONS     # call-time reads,
    time_budget_s = time_budget_s or EDGAR_8K_TIME_BUDGET_S           # so tests can patch
    today = pd.Timestamp(as_of or pd.Timestamp.now()).normalize()
    uni = sorted({str(t).strip().upper() for t in (universe or []) if str(t).strip()})
    if not uni:
        _write_8k_receipt({"ok": False, "error": "empty universe"})
        return "edgar_8k: FAILED (empty universe — no tracked tickers to ask about)"
    cik_of = _edgar_cik_map(uni, today)
    if not cik_of:
        _write_8k_receipt({"ok": False, "error": "no universe ticker mapped to a CIK",
                           "universe_size": len(uni)})
        return f"edgar_8k: FAILED (none of {len(uni)} tickers mapped to an SEC CIK)"

    index_ok: list[str] = []
    index_missing: list[str] = []
    frames: list[pd.DataFrame] = []
    for i in range(days_back):
        d = today - pd.Timedelta(days=i)
        if d.weekday() >= 5:
            continue                                     # no dissemination on weekends
        url = (f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/"
               f"QTR{(d.month - 1) // 3 + 1}/form.{d.strftime('%Y%m%d')}.idx")
        try:
            txt = _get(url, timeout=EDGAR_8K_TIMEOUT_S).decode("latin-1")
        except Exception:
            index_missing.append(str(d.date()))          # holiday / not posted yet
            continue
        finally:
            time.sleep(EDGAR_8K_RATE_SLEEP_S)
        index_ok.append(str(d.date()))
        frames.append(_parse_form_index_8k(txt))
    if not index_ok:
        _write_8k_receipt({"ok": False, "index_ok": [], "index_missing": index_missing,
                           "error": "no daily index readable"})
        return (f"edgar_8k: FAILED (no EDGAR daily index readable in {days_back}d: "
                f"missing {index_missing})")
    idx = (pd.concat(frames, ignore_index=True) if frames
           else pd.DataFrame(columns=["cik", "accession", "index_date", "company"]))
    n_8k_in_index = len(idx)
    idx = idx[idx["cik"].isin(list(cik_of))].drop_duplicates("accession")
    n_universe = len(idx)

    panel = OUT_DIR / EDGAR_8K_PANEL
    try:
        have = set(pd.read_parquet(panel, columns=["accession"])["accession"].astype(str))
    except Exception:
        have = set()
    todo = idx[~idx["accession"].isin(have)]

    rows: list[dict] = []
    n_sub = n_sub_fail = n_unmatched = 0
    truncated = False
    fetched_at = pd.Timestamp.now(tz="UTC").isoformat()
    for cik, grp in todo.groupby("cik", sort=True):
        if n_sub >= max_submissions or (time.monotonic() - t0) > time_budget_s:
            truncated = True
            break
        n_sub += 1
        try:
            sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json",
                                  timeout=EDGAR_8K_TIMEOUT_S))
        except Exception:
            n_sub_fail += 1
            continue
        finally:
            time.sleep(EDGAR_8K_RATE_SLEEP_S)
        recent = (sub.get("filings") or {}).get("recent") or {}
        accs = list(recent.get("accessionNumber") or [])
        pos = {a: k for k, a in enumerate(accs)}

        def _col(name: str, k: int):
            vals = recent.get(name) or []
            return vals[k] if k < len(vals) else None

        for r in grp.itertuples(index=False):
            k = pos.get(r.accession)
            if k is None or _col("form", k) != "8-K":
                n_unmatched += 1                         # not in this CIK's recent block
                continue
            rows.append({"ticker": cik_of[int(cik)], "cik": int(cik), "accession": r.accession,
                         # the submissions date where SEC gives one, else the index's own
                         "filing_date": str(_col("filingDate", k) or r.index_date)[:10],
                         "acceptance_dt": str(_col("acceptanceDateTime", k) or ""),
                         "items": str(_col("items", k) or ""),
                         "primary_document": str(_col("primaryDocument", k) or ""),
                         "company": r.company, "index_date": r.index_date,
                         "fetched_at": fetched_at})
    new = pd.DataFrame(rows, columns=EDGAR_8K_COLUMNS)
    if len(new) or not panel.exists():
        _append(new, panel, ["accession"])
    n_total = len(pd.read_parquet(panel, columns=["accession"]))
    receipt = {"ok": True, "as_of": str(today.date()), "days_back": days_back,
               "universe_size": len(uni), "universe_ciks": len(cik_of),
               "index_ok": index_ok, "index_missing": index_missing,
               "n_8k_in_index": n_8k_in_index, "n_universe_filings": n_universe,
               "n_already_in_panel": n_universe - len(todo), "n_new": len(new),
               "n_submissions": n_sub, "n_submission_failures": n_sub_fail,
               "n_unmatched": n_unmatched, "truncated": truncated, "panel_rows": n_total,
               "elapsed_s": round(time.monotonic() - t0, 1)}
    if n_sub and n_sub_fail == n_sub:
        receipt["ok"] = False
        _write_8k_receipt(receipt)
        return (f"edgar_8k: FAILED (all {n_sub} submissions requests failed; "
                f"{len(todo)} filing(s) not recorded)")
    _write_8k_receipt(receipt)
    return (f"edgar_8k: +{len(new)} new 8-K filing(s) for {len(uni)} tracked tickers "
            f"({len(cik_of)} CIKs) from index {index_ok}"
            + (f" (missing {index_missing})" if index_missing else "")
            + f"; {n_sub} submissions asked, {n_sub_fail} failed"
            + (f", {n_unmatched} unmatched" if n_unmatched else "")
            + (" — TRUNCATED by the request/time budget (the rest retry next run)"
               if truncated else "")
            + f"; panel {n_total}")


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


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="T-136 alt-data pulls + forward archivers")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--discover-kalshi-series", action="store_true",
                      help="rewrite the Kalshi series list from the live API (review the diff)")
    mode.add_argument("--kalshi-only", action="store_true",
                      help="run only the Kalshi snapshot + resolver (smoke)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="write parquets here instead of data/macro_data/alt (smoke/tests)")
    ap.add_argument("--kalshi-config", type=Path, default=None,
                    help="the series-list path (default config/kalshi_macro_series.json)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global OUT_DIR, KALSHI_SERIES_CONFIG
    args = _parse_args(argv)
    if args.out_dir is not None:
        OUT_DIR = args.out_dir
    if args.kalshi_config is not None:
        KALSHI_SERIES_CONFIG = args.kalshi_config
    if args.discover_kalshi_series:
        r = discover_kalshi_series()
        print(f"[T136-D] {r}", flush=True)
        return 1 if "FAILED" in r else 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.kalshi_only:
        rs = [snapshot_kalshi(), resolve_kalshi_snapshots()]
        for r in rs:
            print(f"[T136-D] {r}", flush=True)
        return 1 if any("FAILED" in r for r in rs) else 0
    lines = [pull_gpr(), pull_epu(),
             snapshot_polymarket(), snapshot_kalshi(),
             resolve_polymarket_snapshots(), resolve_kalshi_snapshots(),
             snapshot_kxfed(), pull_fred_rate_path(),
             snapshot_cef(), pull_form4_index(), pull_usaspending(),
             pull_credit_spread_oas()]
    for r in lines:
        print(f"[T136-D] {r}", flush=True)
    return _daily_rc(lines)


# The daily run's exit code. Most feeds are gated by the freshness verifier (zero fresh
# rows) and by their cadence budgets, so their FAILED lines keep exit 0 (no double alarm,
# no cry-wolf on known-flaky feeds). These three are not fully seen by any other gate — a
# Kalshi PARTIAL day still writes rows, and nothing watches the resolvers — so their FAILED
# line makes the run exit 1, which the launchd wrapper turns into its alarm.
_RC_GATED_PREFIXES = ("kalshi:", "kalshi_resolve:", "polymarket_resolve:")


def _daily_rc(lines: list[str]) -> int:
    return int(any(r.startswith(_RC_GATED_PREFIXES) and "FAILED" in r for r in lines))


if __name__ == "__main__":
    sys.exit(main())
