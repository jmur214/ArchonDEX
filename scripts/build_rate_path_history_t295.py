"""
scripts/build_rate_path_history_t295.py
=======================================
T-2026-07-08-295 — the RATE-PATH BACKFILL: a free historical market-implied
rate path to seed the "rate-path archive only starts accruing now" gap ($0).

WHY: no free FedWatch-style *archive* exists (CME sells ~1yr). But the implied
path RECONSTRUCTS from free raw ZQ (30-day fed-funds) futures — 100 − price =
the month-average implied EFFR — and cross-checks against the free official
Minneapolis Fed option-implied densities. Per Diercks-Katz-Wright (FEDS
2026-010) Kalshi BEATS futures/surveys on the Fed path near meetings, so this
reconstruction is the BASELINE series and our forward Kalshi archive (accruing
since 2026-07-07) is the better-calibrated live overlay.

SOURCE NOTE (deviation from the task's named sources, approved):
  - stooq (a named source) is now behind a JavaScript proof-of-work anti-bot
    wall — its CSV endpoint returns a challenge, not data (logged in
    health_check.md as a MEDIUM cross-cutting finding).
  - FRED has the realized rates (EFFR/DFEDTARU) but NOT ZQ futures prices.
  - So the free ZQ source is Yahoo Finance: ZQ=F (front-continuous, ~10yr) for
    the deep implied-EFFR PATH, and individual monthly contracts (ZQ<code><yy>
    .CBT) for meeting-dated probabilities. Yahoo DELISTS expired contracts, so
    individual-contract history reaches only currently-active meetings (~2yr
    forward); the deep historical baseline is the front-continuous series.

OUTPUT (data/macro_data/alt/):
  - rate_path_reconstructed.parquet   — long-form, two series_type values:
      'implied_effr_frontcont' : date, price, implied_effr (deep ~10yr; ZQ=F)
      'meeting_prob'           : per FOMC meeting, the two-outcome implied move
                                 prob from the meeting-month contract (active
                                 meetings only; accrues forward via snap_date)
  - fed_tracker_minneapolis.parquet   — the Minneapolis Fed MPD cross-check
    (vintage-stamped, idempotent).

Usage: python -m scripts.build_rate_path_history_t295
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engines.data_manager.macro_calendar import load_fomc_dates  # T-290 d3 (my own)

OUT_DIR = ROOT / "data" / "macro_data" / "alt"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
SNAP_DATE = pd.Timestamp.now().strftime("%Y-%m-%d")

# CME/CBOT month codes for the individual ZQ contracts.
MONTH_CODE = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
              7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}


# --------------------------------------------------------------------------- #
# fetch helpers
# --------------------------------------------------------------------------- #
def _get(url: str, timeout: int = 60, retries: int = 4) -> bytes:
    """GET with backoff on transient 429/5xx (Yahoo rate-limits bursts)."""
    import time
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                          timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt * 3)      # 3s, 6s, 12s
                continue
            raise
    raise RuntimeError("unreachable")


def _yahoo_daily(symbol: str, rng: str = "10y") -> pd.Series:
    """Daily close series for a Yahoo symbol (deduped by date). Empty on any
    error (a delisted/expired contract 404s — expected, not fatal)."""
    try:
        d = json.loads(_get(f"https://query1.finance.yahoo.com/v8/finance/chart/"
                            f"{urllib.parse.quote(symbol)}?range={rng}&interval=1d"))
        r = d["chart"]["result"][0]
        ts, cl = r["timestamp"], r["indicators"]["quote"][0]["close"]
        s = pd.Series(cl, index=pd.to_datetime([date.fromtimestamp(t) for t in ts])).dropna()
        return s[~s.index.duplicated(keep="last")]
    except Exception:
        return pd.Series(dtype=float)


def _fred(series_id: str) -> pd.Series:
    b = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    df = pd.read_csv(io.BytesIO(b))
    df.columns = ["date", "v"]
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna().set_index("date")["v"]


def _append(df: pd.DataFrame, path: Path, keys: List[str]) -> int:
    """Idempotent append+dedup (the T-136 archiver pattern). Returns rows total."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    df = df.drop_duplicates(subset=keys, keep="last")
    df.to_parquet(path, index=False)
    return len(df)


# --------------------------------------------------------------------------- #
# deliverable 1a — the deep front-continuous implied-EFFR PATH
# --------------------------------------------------------------------------- #
def build_frontcont_path() -> Dict:
    """ZQ=F front-continuous → implied_effr = 100 − price. Validated vs FRED
    EFFR on the overlap (settlement-month proxy). Fail-LOUD if the core ZQ
    fetch is empty — this series is the whole point of the script."""
    zq = _yahoo_daily("ZQ=F", rng="10y")
    if zq.empty:
        raise SystemExit("FATAL [NN-FAIL-CLOSED]: ZQ=F fetch empty — no free ZQ "
                         "source (Yahoo down / symbol changed). Refusing to write "
                         "an empty rate-path baseline.")
    impl = (100.0 - zq).rename("implied_effr")
    df = pd.DataFrame({
        "date": impl.index.strftime("%Y-%m-%d"),
        "series_type": "implied_effr_frontcont",
        "price": zq.values.round(4),
        "implied_effr": impl.values.round(4),
        "source": "yahoo:ZQ=F",
        "snap_date": SNAP_DATE,
    })
    # validation vs FRED EFFR
    effr = _fred("EFFR")
    j = pd.DataFrame({"impl": impl, "effr": effr}).dropna()
    diff = (j["impl"] - j["effr"]).abs()
    val = {
        "overlap_days": int(len(j)),
        "start": str(impl.index.min().date()),
        "end": str(impl.index.max().date()),
        "mean_abs_diff_bp": round(float(diff.mean()) * 100, 2),
        "median_abs_diff_bp": round(float(diff.median()) * 100, 2),
        "corr": round(float(j["impl"].corr(j["effr"])), 4),
    }
    n = _append(df, OUT_DIR / "rate_path_reconstructed.parquet",
                ["date", "series_type"])
    return {"rows_written": len(df), "parquet_total": n, "validation": val}


# --------------------------------------------------------------------------- #
# deliverable 1b — meeting-dated two-outcome implied move probabilities
# --------------------------------------------------------------------------- #
def _two_outcome_prob(contract_price: float, r_start: float,
                      decision: pd.Timestamp) -> Dict:
    """The documented CME FedWatch TWO-OUTCOME method for a single meeting in
    its contract month. The ZQ contract settles to the month-average EFFR:
        avg = (n_before*r_start + n_after*r_end)/N
    where the new rate is effective the day AFTER the decision. Solve r_end,
    then the two-outcome prob of a 25bp move = |r_end - r_start| / 0.25.

    LIMITATION (stated verbatim per the task): this is a TWO-OUTCOME
    approximation (no-change vs a single 25bp move). It cannot represent a 50bp
    move or the full bucket distribution — that exists ONLY in our forward
    Kalshi KXFED archive. It is also a near-term single-meeting method (a
    contract month with two meetings, or a meeting split across contract
    months, is out of scope)."""
    N = decision.days_in_month
    n_before = int(decision.day)          # days 1..decision at the OLD rate
    n_after = N - n_before
    if n_after <= 0:
        return {}
    implied_avg = 100.0 - contract_price
    r_end = (implied_avg * N - r_start * n_before) / n_after
    change = r_end - r_start
    prob_move = max(0.0, min(1.0, abs(change) / 0.25))
    return {
        "implied_month_avg": round(implied_avg, 4),
        "implied_post_rate": round(r_end, 4),
        "implied_change_bp": round(change * 100, 2),
        "prob_25bp_move": round(prob_move, 4),
        "direction": "cut" if change < -1e-9 else ("hike" if change > 1e-9 else "hold"),
        "n_before": n_before, "n_after": n_after,
    }


def build_meeting_probs() -> Dict:
    """For every FOMC meeting with an available Yahoo contract (active window
    only — expired contracts are delisted), compute the two-outcome implied
    move prob from the meeting-month contract. Accrues forward via snap_date."""
    effr = _fred("EFFR")
    r_start = float(effr.iloc[-1])        # current effective rate = the base
    tgt_u = float(_fred("DFEDTARU").iloc[-1])
    today = pd.Timestamp(SNAP_DATE)
    recs: List[Dict] = []
    skipped = 0
    for d in load_fomc_dates():
        if d < today:                     # only current/future meetings are live
            continue
        yy = d.year % 100
        sym = f"ZQ{MONTH_CODE[d.month]}{yy:02d}.CBT"
        px = _yahoo_daily(sym, rng="1mo")
        if px.empty:
            skipped += 1
            continue
        prob = _two_outcome_prob(float(px.iloc[-1]), r_start, d)
        if not prob:
            skipped += 1
            continue
        recs.append({
            "date": str(d.date()), "series_type": "meeting_prob",
            "snap_date": SNAP_DATE, "contract": sym,
            "contract_price": round(float(px.iloc[-1]), 4),
            "r_start_effr": round(r_start, 4), "target_upper": round(tgt_u, 4),
            "source": "yahoo:ZQ-monthly", "method": "fedwatch_two_outcome",
            **prob,
        })
    if not recs:
        return {"rows_written": 0, "skipped": skipped, "note": "no active ZQ contracts resolved"}
    df = pd.DataFrame(recs)
    n = _append(df, OUT_DIR / "rate_path_reconstructed.parquet",
                ["date", "series_type", "snap_date"])
    return {"rows_written": len(df), "skipped": skipped, "parquet_total": n,
            "meetings": [r["date"] for r in recs]}


# --------------------------------------------------------------------------- #
# deliverable 2 — the Fed-tracker cross-checks
# --------------------------------------------------------------------------- #
def ingest_minneapolis() -> Dict:
    """Minneapolis Fed Market-Based Probabilities (option-implied MPDs). The
    CSV has a prose PREAMBLE and NO column-header row — data rows are
    `"<asset>","MM/DD/YYYY",<numeric fields...>`. So we detect the first real
    data row (field[1] is a date), read the rest header-less, and name the
    first two columns asset/date (the numeric fields are defined in the
    separate mpd_data_dictionary.csv — over-inclusive is fine for a
    cross-check; A can join the dictionary). Vintage-stamped + idempotent."""
    import re
    try:
        raw = _get("https://www.minneapolisfed.org/-/media/files/banking/mpd/mpd_stats.csv").decode("utf-8", "replace")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        date_re = re.compile(r'^"?[^"]*"?,\s*"?\d{1,2}/\d{1,2}/\d{4}')
        start = next(i for i, ln in enumerate(lines) if date_re.match(ln))
        df = pd.read_csv(io.StringIO("\n".join(lines[start:])), header=None)
        ncols = df.shape[1]
        df.columns = (["asset", "date"] + [f"f{i}" for i in range(ncols - 2)])[:ncols]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["snap_date"] = SNAP_DATE
        n = _append(df, OUT_DIR / "fed_tracker_minneapolis.parquet",
                    ["asset", "date", "snap_date"])
        rate_assets = sorted(a for a in df["asset"].dropna().astype(str).unique()
                             if any(k in a.lower() for k in ("rate", "sofr", "fed", "libor", "ff")))
        return {"rows": len(df), "parquet_total": n, "n_cols": ncols,
                "assets_sample": sorted(df["asset"].dropna().astype(str).unique())[:12],
                "rate_assets": rate_assets,
                "date_span": [str(df["date"].min().date()), str(df["date"].max().date())]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def ingest_atlanta() -> Dict:
    """Atlanta Fed Market Probability Tracker — BEST-EFFORT (the task: if the
    page has moved and it can't be relocated, Minneapolis + FRED suffice; say
    so and move on). Tries the known data-file locations."""
    candidates = [
        "https://www.atlantafed.org/-/media/documents/datafiles/cqer/research/market-probability-tracker/market-probability-tracker-data.xlsx",
        "https://www.atlantafed.org/-/media/documents/datafiles/cqer/researchcq/market-probability-tracker/data.xlsx",
    ]
    for url in candidates:
        try:
            b = _get(url, timeout=40)
            if b[:4] == b"PK\x03\x04":       # a real xlsx
                df = pd.read_excel(io.BytesIO(b))
                df["snap_date"] = SNAP_DATE
                n = _append(df, OUT_DIR / "fed_tracker_atlanta.parquet",
                            list(df.columns[:2]) + ["snap_date"])
                return {"rows": len(df), "parquet_total": n, "url": url}
        except Exception:
            continue
    return {"skipped": "Atlanta tracker data file not resolvable (page moved); "
            "Minneapolis MPD + FRED EFFR validation suffice per the task."}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[T295] --- deliverable 1a: front-continuous implied EFFR path ---")
    a = build_frontcont_path()
    print(f"[T295] frontcont: {a['rows_written']} rows (parquet {a['parquet_total']}); "
          f"validation vs FRED EFFR: {a['validation']}")
    print("[T295] --- deliverable 1b: meeting-dated two-outcome probs ---")
    b = build_meeting_probs()
    print(f"[T295] meeting_probs: {b}")
    print("[T295] --- deliverable 2: Fed-tracker cross-checks ---")
    print(f"[T295] minneapolis: {ingest_minneapolis()}")
    print(f"[T295] atlanta: {ingest_atlanta()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
