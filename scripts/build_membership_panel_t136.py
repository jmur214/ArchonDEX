"""
scripts/build_membership_panel_t136.py
======================================
T-2026-06-10-136 Part A — point-in-time S&P 500 membership layer ($0).

Sources (free, license-safe to bake — public/open data per the 2026-06-10
data-vendor research):
  PRIMARY: github.com/fja05680/sp500 (Clenow base + maintained changes, 1996+)
    - "sp500_ticker_start_end.csv"  → membership intervals per ticker
    - "S&P 500 Historical Components & Changes (Updated).csv"
        → date-stamped constituent lists (used for INTERNAL consistency check)
  CROSS-CHECK (second source): Wikipedia "List of S&P 500 companies" —
    current constituents + the "Selected changes" table (adds/removes with
    dates). We FLAG disagreements rather than trusting either blindly.

Output:
  data/universe/sp500_membership_pit.parquet     (ticker, start, end intervals)
  data/universe/sp500_membership_pit_meta.json   (provenance, cross-check report)
  Loader: in_index(ticker, date) via scripts.membership_loader_t136

Caveats documented: pre-2000 accuracy is weaker in all free sources (the
research's stated caveat); tickers are share-class-ambiguous in places
(BRK.B vs BRK-B normalization applied: '.' -> '-').

Usage: python -m scripts.build_membership_panel_t136
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "universe"
RAW_DIR = OUT_DIR / "raw_membership_sources"
OUT_PARQUET = OUT_DIR / "sp500_membership_pit.parquet"
OUT_META = OUT_DIR / "sp500_membership_pit_meta.json"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}

REPO_RAW = "https://raw.githubusercontent.com/fja05680/sp500/master/"
F_INTERVALS = "sp500_ticker_start_end.csv"
F_COMPONENTS = "S&P 500 Historical Components & Changes (Updated).csv"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _fetch_text(url: str, cache: Path) -> str:
    if cache.exists():
        return cache.read_text()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8", errors="replace")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text)
    return text


def _norm(t: str) -> str:
    return str(t).strip().upper().replace(".", "-")


def build_intervals() -> pd.DataFrame:
    text = _fetch_text(REPO_RAW + urllib.request.quote(F_INTERVALS),
                       RAW_DIR / F_INTERVALS)
    df = pd.read_csv(io.StringIO(text))
    cols = {c.lower().strip(): c for c in df.columns}
    tick = cols.get("ticker") or cols.get("symbol")
    start = cols.get("start") or cols.get("start_date") or cols.get("start date")
    end = cols.get("end") or cols.get("end_date") or cols.get("end date")
    out = pd.DataFrame({
        "ticker": df[tick].map(_norm),
        "start": pd.to_datetime(df[start], errors="coerce"),
        "end": pd.to_datetime(df[end], errors="coerce"),  # NaT = still a member
    }).dropna(subset=["ticker", "start"])
    return out.sort_values(["ticker", "start"]).reset_index(drop=True)


def internal_consistency_check(intervals: pd.DataFrame) -> dict:
    """Cross-check the intervals against the repo's own date-stamped
    constituent lists at a few sample dates."""
    text = _fetch_text(REPO_RAW + urllib.request.quote(F_COMPONENTS),
                       RAW_DIR / "components_updated.csv")
    comp = pd.read_csv(io.StringIO(text))
    comp["date"] = pd.to_datetime(comp[comp.columns[0]], errors="coerce")
    tick_col = comp.columns[1]
    sample_dates = ["2000-01-03", "2008-09-15", "2015-06-30", "2020-03-31", "2024-12-31"]
    report = {}
    for ds in sample_dates:
        d = pd.Timestamp(ds)
        row = comp[comp["date"] <= d].tail(1)
        if row.empty:
            continue
        listed = {_norm(t) for t in str(row.iloc[0][tick_col]).split(",")}
        from_intervals = set(intervals[
            (intervals["start"] <= d) &
            ((intervals["end"].isna()) | (intervals["end"] >= d))
        ]["ticker"])
        report[ds] = {
            "n_components_file": len(listed),
            "n_intervals": len(from_intervals),
            "in_file_not_intervals": sorted(listed - from_intervals)[:10],
            "in_intervals_not_file": sorted(from_intervals - listed)[:10],
            "agreement_pct": round(100 * len(listed & from_intervals)
                                   / max(len(listed | from_intervals), 1), 2),
        }
    return report


def wikipedia_cross_check(intervals: pd.DataFrame) -> dict:
    """Second source: Wikipedia current constituents vs the panel TODAY."""
    try:
        html = _fetch_text(WIKI_URL, RAW_DIR / "wikipedia_sp500.html")
        tables = pd.read_html(io.StringIO(html))
        cur = tables[0]
        sym_col = [c for c in cur.columns if "symbol" in str(c).lower()][0]
        wiki_now = {_norm(t) for t in cur[sym_col].astype(str)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    today = pd.Timestamp("2026-06-10")
    panel_now = set(intervals[
        (intervals["start"] <= today) &
        ((intervals["end"].isna()) | (intervals["end"] >= today))
    ]["ticker"])
    return {
        "wiki_n": len(wiki_now), "panel_n": len(panel_now),
        "agreement_pct": round(100 * len(wiki_now & panel_now)
                               / max(len(wiki_now | panel_now), 1), 2),
        "wiki_not_panel": sorted(wiki_now - panel_now)[:15],
        "panel_not_wiki": sorted(panel_now - wiki_now)[:15],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    intervals = build_intervals()
    print(f"[T136-A] intervals: {len(intervals)} rows, "
          f"{intervals.ticker.nunique()} tickers, "
          f"start range {intervals.start.min().date()}..{intervals.start.max().date()}")

    internal = internal_consistency_check(intervals)
    for d, r in internal.items():
        print(f"[T136-A] internal {d}: agreement {r['agreement_pct']}% "
              f"(file {r['n_components_file']} vs intervals {r['n_intervals']})")

    wiki = wikipedia_cross_check(intervals)
    print(f"[T136-A] wikipedia cross-check: {wiki.get('agreement_pct')}% "
          f"(wiki {wiki.get('wiki_n')} vs panel {wiki.get('panel_n')})")

    intervals.to_parquet(OUT_PARQUET)
    OUT_META.write_text(json.dumps({
        "task": "T-2026-06-10-136 Part A",
        "primary_source": "github.com/fja05680/sp500 (Clenow base + maintained)",
        "cross_check_source": "Wikipedia List_of_S%26P_500_companies (current)",
        "caveats": [
            "pre-2000 accuracy weaker in all free sources (research-stated)",
            "ticker normalization: '.' -> '-' (share classes)",
            "Wikipedia check covers CURRENT membership only; historical "
            "changes cross-checked via the repo's own components file",
        ],
        "internal_consistency": internal,
        "wikipedia_cross_check": wiki,
    }, indent=2, default=str))
    print(f"[T136-A] wrote {OUT_PARQUET} + meta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
