"""scripts/lazy_prices/b6_cik_map.py
===================================
T-383 (B-6) step 1 — DATE-AWARE S&P ticker -> CIK *candidates*, built OFFLINE.

Why: T-237 resolved tickers through the LIVE `company_tickers.json`, which only knows today's
filers. That (a) dropped S&P members whose ticker no longer exists (970 tickers were members
since 2005; T-237 held sections for 604) and (b) pointed recycled tickers at the WRONG company
(`S` -> SentinelOne, not Sprint; 13 tickers had zero ingested filings inside their membership).

Source: the SEC Form 3/4/5 quarterly datasets cached at `data/edgar/insider_zips/` (2006Q1 ->).
Their SUBMISSION table records WHO USED WHICH SYMBOL WHEN (ISSUERCIK, ISSUERTRADINGSYMBOL,
FILING_DATE) for every insider filing.

Membership-file convention (measured 2026-11-11): each company is listed under its LAST ticker
for its whole history — LB = L Brands since 1996 (it traded as LTD until 2013, while LaBarge
Inc. used "LB"); WM = Waste Management since 1998 (WaMu used "WM" and has its own WAMUQ
interval); PTC = Parametric (PMTC then); no ACE/NU/LTD/WPO intervals exist. So the symbol's
historical user is NOT always the member; the decision needs each candidate's own filing dates,
which only the panel builder has (submissions JSON). This module emits the evidence:

  sp_interval_users.parquet   per interval: every issuer that used the symbol inside it
                              (n, first, last, q05, q95 of its insider filings under the symbol)
  sp_intervals.parquet        per interval: ticker, dates, live-map CIK, T-237's CIK, match method
  cik_year_activity.parquet   insider filings per (CIK, year) under ANY symbol — a size proxy
                              (an S&P 500 issuer files far more Forms 3/4/5 than a small one)

Decision rule (applied in `b6_build_panel.py universe`, documented here so it travels):
  anchor = live-map CIK if it was already a periodic filer at the interval start (+1y), else the
           LAST chain user of the symbol; a month goes to the anchor if the anchor was a filer
           then, else to the chain user of that month (a succession predecessor, e.g. Google Inc
           before Alphabet); where both filed, the chain user wins only with >= 1.5x the
           anchor's insider activity (CB: Chubb Corp 2.3x ACE -> Chubb Corp; WM: WaMu 0.64x
           Waste Management -> Waste Management). Every decision is flagged in the output.

Bankruptcy-suffixed membership tickers (ABKFQ, BTUUQ, ...) retry with the suffix stripped under
the same date condition (method `insider_qstrip`); the builder rejects a qstrip CIK that is a
concurrent member under another ticker (SUNEQ -> Sunoco is wrong: Sunoco is SUN).

Reads the shared cache read-only; writes only under `data/b6_local/cik_map/`.

Usage:
  python -m scripts.lazy_prices.b6_cik_map [--since 2006-01-01]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INSIDER_DIR = ROOT / "data" / "edgar" / "insider_zips"
MEMBERSHIP = ROOT / "data" / "universe" / "sp500_membership_pit.parquet"
LIVE_MAP = ROOT / "data" / "edgar" / "raw" / "company_tickers.json"
T237_SECTIONS = ROOT / "data" / "edgar" / "sections.parquet"
OUT_DIR = ROOT / "data" / "b6_local" / "cik_map"
INTERVALS_PATH = OUT_DIR / "sp_intervals.parquet"
USERS_PATH = OUT_DIR / "sp_interval_users.parquet"
ACTIVITY_PATH = OUT_DIR / "cik_year_activity.parquet"

OPEN_END = pd.Timestamp("2026-12-31")
INSIDER_START = pd.Timestamp("2006-01-01")
SLACK = pd.Timedelta(days=180)
MIN_SHARE = 0.05            # a symbol user below 5% of in-interval filings (or < 3) is noise

_NULL_SYMBOLS = {"N/A", "NA", "NONE", "N.A.", "NOT APPLICABLE", "-", "--", "NO SYMBOL", "N/A."}
_PREFIX_RE = re.compile(r"^(NYSE|NASDAQ|NASD|AMEX|OTC|OTCBB|NYSEMKT|NYSEAMERICAN)\s*[:\-]\s*")
_SPLIT_RE = re.compile(r"[,;/&]|\s+AND\s+")
_PIECE_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]*$")


def symbol_keys(raw: str | None) -> list[str]:
    """Normalise a hand-typed ISSUERTRADINGSYMBOL into alnum-only keys ('BRK.B' -> 'BRKB').

    - Null markers ('N/A', 'NONE') are caught BEFORE splitting ('N/A' would otherwise yield 'A',
      Agilent's real symbol). Single-letter symbols are real (A, C, F, K, M, O, S, T ...).
    - Pieces split only on , ; / & and ' AND '; internal spaces are COLLAPSED, never split
      ('N O G' is Northern Oil & Gas's NOG, not N + O + G — it matched Realty Income's 'O').
    - A piece with any character outside [A-Z0-9.-] is rejected ('M??????' — a mis-encoded
      Japanese issuer name — matched Macy's 'M')."""
    if raw is None or not isinstance(raw, str):
        return []
    s = raw.strip().upper()
    if not s or s in _NULL_SYMBOLS:
        return []
    s = _PREFIX_RE.sub("", s)
    out: list[str] = []
    for piece in _SPLIT_RE.split(s):
        piece = re.sub(r"\s+", "", piece)
        if not piece or not _PIECE_RE.match(piece):
            continue
        key = re.sub(r"[^A-Z0-9]", "", piece)
        if key and len(key) <= 6 and key not in {"NONE", "NA"}:
            out.append(key)
    return out


def ticker_key(ticker: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", ticker.upper())


def candidate_keys(ticker: str) -> list[tuple[str, str]]:
    """(key, method) in priority order: exact, class root, bankruptcy-suffix strips."""
    key = ticker_key(ticker)
    out = [(key, "insider_exact")]
    root = ticker_key(ticker.split("-")[0].split(".")[0])
    if root != key:
        out.append((root, "insider_root"))
    if key.endswith("Q") and len(key) >= 4:
        for k in (1, 2, 3):
            if len(key) - k >= 1:
                out.append((key[:-k], "insider_qstrip"))
    return out


def load_insider_rows(insider_dir: Path = INSIDER_DIR) -> pd.DataFrame:
    """Every insider filing as (cik, date, sym_key list) — one zip at a time."""
    parts: list[pd.DataFrame] = []
    zips = sorted(insider_dir.glob("*_form345.zip"))
    if not zips:
        raise SystemExit(f"FATAL: no insider zips under {insider_dir}")
    for zp in zips:
        with zipfile.ZipFile(zp) as z, z.open("SUBMISSION.tsv") as fh:
            df = pd.read_csv(fh, sep="\t", dtype=str, quoting=3, on_bad_lines="skip",
                             usecols=["FILING_DATE", "ISSUERCIK", "ISSUERTRADINGSYMBOL"])
        df["date"] = pd.to_datetime(df["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
        df["cik"] = pd.to_numeric(df["ISSUERCIK"], errors="coerce")
        df = df.dropna(subset=["date", "cik"])
        df["sym_key"] = df["ISSUERTRADINGSYMBOL"].map(symbol_keys)
        parts.append(df[["cik", "date", "sym_key"]])
    out = pd.concat(parts, ignore_index=True)
    out["cik"] = out["cik"].astype("int64")
    return out


def interval_users(membership: pd.DataFrame, ins: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per interval: the symbol's in-interval users (noise-filtered) and the match method."""
    sym = ins.explode("sym_key").dropna(subset=["sym_key"])
    by_key = {k: g for k, g in sym.groupby("sym_key")}
    iv_rows, user_rows = [], []
    for iv_id, iv in membership.reset_index(drop=True).iterrows():
        tkr = str(iv["ticker"])
        start = pd.Timestamp(iv["start"])
        end = pd.Timestamp(iv["end"]) if pd.notna(iv["end"]) else OPEN_END
        lo, hi = max(start, INSIDER_START) - SLACK, end + SLACK
        method = "none"
        for key, m in candidate_keys(tkr):
            g = by_key.get(key)
            if g is None:
                continue
            inside = g[(g.date >= lo) & (g.date <= hi)]
            if inside.empty:
                continue
            per = inside.groupby("cik").date.agg(
                n="size", first="min", last="max",
                q05=lambda d: d.quantile(0.05), q95=lambda d: d.quantile(0.95)).reset_index()
            total = int(per.n.sum())
            per = per[(per.n >= 3) & (per.n >= MIN_SHARE * total)]
            if per.empty:
                continue
            method = m
            for _, u in per.iterrows():
                user_rows.append({"iv_id": int(iv_id), "cik": int(u.cik), "n": int(u.n),
                                  "first": u["first"], "last": u["last"],
                                  "q05": u.q05, "q95": u.q95, "key": key})
            break
        iv_rows.append({"iv_id": int(iv_id), "ticker": tkr, "iv_start": start,
                        "iv_end": pd.Timestamp(iv["end"]) if pd.notna(iv["end"]) else pd.NaT,
                        "method": method})
    return pd.DataFrame(iv_rows), pd.DataFrame(user_rows)


def _live_map() -> dict[str, int]:
    if not LIVE_MAP.is_file():
        return {}
    d = json.loads(LIVE_MAP.read_text())
    return {ticker_key(v["ticker"]): int(v["cik_str"]) for v in d.values()}


def _t237_map() -> dict[str, int]:
    if not T237_SECTIONS.is_file():
        return {}
    s = pd.read_parquet(T237_SECTIONS, columns=["ticker", "cik"]).drop_duplicates("ticker")
    return {str(t): int(c) for t, c in zip(s["ticker"], s["cik"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 date-aware S&P ticker->CIK candidates (offline).")
    ap.add_argument("--since", default="2006-01-01",
                    help="keep membership intervals ending on/after this date")
    args = ap.parse_args(argv)

    mem = pd.read_parquet(MEMBERSHIP)
    since = pd.Timestamp(args.since)
    mem = mem[mem["end"].isna() | (mem["end"] >= since)].reset_index(drop=True)
    ins = load_insider_rows()
    print(f"[b6-cikmap] insider filings: {len(ins):,}; intervals {len(mem)} "
          f"({mem.ticker.nunique()} tickers) ending >= {since.date()}", flush=True)
    ivs, users = interval_users(mem, ins)
    live, t237 = _live_map(), _t237_map()
    ivs["live_cik"] = ivs["ticker"].map(lambda t: live.get(ticker_key(t))).astype("Int64")
    ivs["t237_cik"] = ivs["ticker"].map(t237).astype("Int64")

    cands = set(users["cik"]) | set(ivs["live_cik"].dropna().astype(int))
    act = ins[ins.cik.isin(cands)].assign(year=lambda d: d.date.dt.year)
    act = act.groupby(["cik", "year"]).size().rename("n").reset_index()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ivs.to_parquet(INTERVALS_PATH, index=False)
    users.to_parquet(USERS_PATH, index=False)
    act.to_parquet(ACTIVITY_PATH, index=False)
    n_users = users.groupby("iv_id").size()
    print(f"[b6-cikmap] intervals with >=1 symbol user: {n_users.size}; with >1: "
          f"{int((n_users > 1).sum())}; methods {ivs.method.value_counts().to_dict()}")
    print(f"[b6-cikmap] candidate CIKs (users + live): {len(cands)}")
    print(f"[b6-cikmap] wrote {INTERVALS_PATH.relative_to(ROOT)}, {USERS_PATH.name}, "
          f"{ACTIVITY_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
