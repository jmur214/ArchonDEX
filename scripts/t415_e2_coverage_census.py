"""
scripts/t415_e2_coverage_census.py
==================================
T-415 (candidate E-2: the earnings-announcement premium as a weekly basket of point-in-time S&P 500
members) — PHASE 1 CENSUS. COUNTS ONLY.

Nothing here computes a return, a price-level statistic, a portfolio or a benchmark. A price file is
read only for the DATES on which it carries a usable bar (close > 0 and volume > 0). An 8-K is read
only for its filing date, acceptance time and item list. The census answers two questions:

1. Survivorship. Of the PIT S&P 500 member-days in the E-2 window, what share has a usable bar in the
   project's free price stores, and is the gap concentrated in members that LEFT the index (an
   outcome-correlated hole) rather than spread evenly?
2. The date source. Does the on-disk EDGAR 8-K panel (item 2.02, and item 12 before 2004-08-23) give
   one dated earnings release per member-quarter, how often does "last year's date + 364 days" land
   near the actual date, and how many predicted announcers fall in each week?

Price sources and the two coverage modes:
  any    — `data/processed/<T>_1d.csv` (any date) or T-265 Alpaca bars
           `data/research/t265/prices/<T>.parquet` (2016-01 onward).
  clean  — the B-6 ruling R1 rule (prereg_b6 Amendment 1, 2026-11-12): T-265 bars at any date, and
           `data/processed` ONLY on or after 2020-04-09, because the canonical cache mis-counts
           dividends by era before each name's seam (health_check HIGH, 2026-11-11).
Ticker identity: a member's CIK is read from the SEC Form 345 SUBMISSION tables (ISSUERTRADINGSYMBOL,
2006q1 onward); a renamed member is covered by its successor symbol's file when the CIK matches
(FB -> META); share classes use the file name's dot form (BRK-B -> BRK.B); the 17 identity-problem
names of the 2026-10-23 survivorship list are never covered. `strict` identity additionally refuses a
member's own-ticker file when the live SEC map gives that ticker a different CIK (ticker reuse, or a
holding-company reorganisation the census cannot tell apart).

Fail-closed (`[NN-FAIL-CLOSED]`): a missing input, an empty window, an empty membership, a failed
positive control or an output path under the repo's `data/` raises `CensusError` and exits non-zero.
Deterministic: inputs are md5-pinned in the output; no clock, no network, no randomness.

Usage:
  python -m scripts.t415_e2_coverage_census --out <json path outside data/>
  python -m scripts.t415_e2_coverage_census --controls-only
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"

from engines.data_manager.exclusions import truncate_declared, withhold_declared_tickers  # noqa: E402

WINDOW_START = pd.Timestamp("2004-08-01")     # first E-2 week (the prereg sketch, T-410 §7.3)
PRIOR_YEAR_START = pd.Timestamp("2003-08-01")  # predicted dates need last year's actuals
CLEAN_PROCESSED_FROM = pd.Timestamp("2020-04-09")  # B-6 ruling R1: last dividend-era seam
DEDUPE_DAYS = 50          # one earnings release per firm-quarter: drop 2.02s < 50 days after the last kept
PREDICT_DAYS = 364        # Savor-Wilson / Frazzini-Lamont: last year's same-quarter date + 52 weeks
MIN_ANNOUNCERS = 10       # the sketch: weeks with < 10 predicted announcers hold SPY
AFTER_CLOSE_HHMM = 1600   # accepted at/after 16:00 ET -> the market reacts the next trading day
FAILURE_SUFFIX_MIN_LEN = 5  # 5-letter tickers ending in Q are post-bankruptcy symbols (LEHMQ, WAMUQ)


class CensusError(RuntimeError):
    """A load-bearing input is missing or a control failed. Never degrade to a plausible count."""


@dataclass(frozen=True)
class Inputs:
    data_root: Path = DATA
    window_end: pd.Timestamp = pd.Timestamp("2026-04-17")  # last SPY bar in data/processed

    @property
    def membership(self) -> Path:
        return self.data_root / "universe" / "sp500_membership_pit.parquet"

    @property
    def calendar_csv(self) -> Path:
        return self.data_root / "processed" / "SPY_1d.csv"

    @property
    def processed_dir(self) -> Path:
        return self.data_root / "processed"

    @property
    def t265_dir(self) -> Path:
        return self.data_root / "research" / "t265" / "prices"

    @property
    def calendar_pinned(self) -> Path:
        return self.data_root / "processed" / "earnings_dates_pinned.parquet"

    @property
    def panel_8k(self) -> Path:
        return self.data_root / "edgar" / "8k" / "panel_8k_items.parquet"

    @property
    def live_tickers(self) -> Path:
        return self.data_root / "edgar" / "8k" / "raw" / "company_tickers.json"

    @property
    def form345_glob(self) -> str:
        return str(self.data_root / "edgar" / "insider_zips" / "*_form345.zip")

    @property
    def wiki_html(self) -> Path:
        return self.data_root / "universe" / "raw_membership_sources" / "wikipedia_sp500.html"

    @property
    def wanted_csv(self) -> Path:
        return ROOT / "docs" / "Sources" / "wanted_names_survivorship_gap_2026_10_23.csv"

    @property
    def firstrate_csv(self) -> Path:
        return (ROOT / "docs" / "Measurements" / "2026-10"
                / "firstrate_coverage_vs_wanted_names_2026_10_23.csv")


# --------------------------------------------------------------------------- inputs
def require(path: Path) -> Path:
    if not Path(path).exists():
        raise CensusError(f"missing load-bearing input: {path}")
    return Path(path)


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_manifest(paths: list[Path]) -> str:
    """md5 over sorted 'name:md5' lines — one pin for a directory's files actually read."""
    lines = sorted(f"{p.name}:{md5_file(p)}" for p in paths)
    return hashlib.md5("\n".join(lines).encode()).hexdigest()


def load_calendar(spy_csv: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    x = pd.read_csv(require(spy_csv), usecols=["Date"], parse_dates=["Date"])
    cal = pd.DatetimeIndex(x.Date[(x.Date >= start) & (x.Date <= end)]).sort_values()
    if len(cal) < 250:
        raise CensusError(f"trading calendar has {len(cal)} days in {start.date()}..{end.date()}")
    return cal


def load_membership(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    m = pd.read_parquet(require(path))
    if not {"ticker", "start", "end"} <= set(m.columns):
        raise CensusError(f"membership columns {list(m.columns)}")
    m = m.copy()
    m["open"] = m["end"].isna()
    m["end"] = m["end"].fillna(pd.Timestamp("2099-12-31"))
    m = m[(m.start <= end) & (m.end >= start)].reset_index(drop=True)
    if m.empty:
        raise CensusError("no membership intervals overlap the window")
    return m


def load_issuer_symbols(form345_glob: str) -> pd.DataFrame:
    """(sym, cik, first, last, n) from every Form 345 SUBMISSION table on disk."""
    zips = sorted(glob.glob(form345_glob))
    if not zips:
        raise CensusError(f"no Form 345 zips at {form345_glob}")
    parts = []
    for zp in zips:
        with zipfile.ZipFile(zp) as z, z.open("SUBMISSION.tsv") as f:
            x = pd.read_csv(f, sep="\t", usecols=["FILING_DATE", "ISSUERCIK", "ISSUERTRADINGSYMBOL"],
                            dtype=str, on_bad_lines="skip")
        x["date"] = pd.to_datetime(x["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
        x["sym"] = normalize_symbol(x["ISSUERTRADINGSYMBOL"].fillna(""))
        x["cik"] = pd.to_numeric(x["ISSUERCIK"], errors="coerce")
        x = x.dropna(subset=["date", "cik"])
        x = x[x.sym != ""]
        parts.append(x.groupby(["sym", "cik"]).date.agg(["min", "max", "size"]).reset_index())
    t = (pd.concat(parts).groupby(["sym", "cik"])
         .agg(first=("min", "min"), last=("max", "max"), n=("size", "sum")).reset_index())
    t["cik"] = t["cik"].astype("int64")
    return t


def normalize_symbol(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.upper().str.replace(".", "-", regex=False)


def load_live_maps(path: Path) -> tuple[dict[str, int], dict[int, list[str]]]:
    d = json.loads(require(path).read_text())
    t2c = {str(v["ticker"]).upper().replace(".", "-"): int(v["cik_str"]) for v in d.values()}
    c2t: dict[int, list[str]] = {}
    for t, c in sorted(t2c.items()):
        c2t.setdefault(c, []).append(t)
    return t2c, c2t


# --------------------------------------------------------------------------- price-bar dates
@dataclass
class BarIndex:
    """Dates with a usable bar (close > 0, volume > 0) per ticker, per coverage mode."""
    processed_dir: Path
    t265_dir: Path
    files_read: list[Path] = field(default_factory=list)
    withheld: set[str] = field(default_factory=set)
    _cache: dict[tuple[str, str], pd.DatetimeIndex] = field(default_factory=dict)

    def processed_file(self, t: str) -> Path | None:
        for cand in (t, t.replace("-", ".")):
            f = self.processed_dir / f"{cand}_1d.csv"
            if f.exists():
                return f
        return None

    def t265_file(self, t: str) -> Path | None:
        f = self.t265_dir / f"{t}.parquet"
        return f if f.exists() else None

    def dates(self, t: str, mode: str) -> pd.DatetimeIndex:
        if mode not in ("any", "clean"):
            raise CensusError(f"unknown coverage mode {mode}")
        key = (t, mode)
        if key in self._cache:
            return self._cache[key]
        out = pd.DatetimeIndex([])
        # The declared ticker exclusions (AZO/MTD/NVR/SLE) count as NOT covered: their cached bars
        # are withheld by ruling, so a member-day on them has no usable bar. DAL's stitched pre-2007
        # rows are withheld by truncate_declared below.
        if not withhold_declared_tickers([t], where="t415_e2_coverage_census"):
            self.withheld.add(t)
            self._cache[key] = out
            return out
        fp = self.processed_file(t)
        if fp is not None:
            x = pd.read_csv(fp, usecols=["Date", "Close", "Volume"], parse_dates=["Date"])
            x = truncate_declared(t, x)
            ok = (x.Volume > 0) & (x.Close > 0) & np.isfinite(x.Close)
            d = pd.DatetimeIndex(x.Date[ok])
            if mode == "clean":
                d = d[d >= CLEAN_PROCESSED_FROM]
            out = out.union(d)
            self.files_read.append(fp)
        fs = self.t265_file(t)
        if fs is not None:
            x = pd.read_parquet(fs, columns=["close", "volume"])
            ok = (x.volume > 0) & (x.close > 0)
            idx = pd.DatetimeIndex(x.index[ok])
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            out = out.union(idx.normalize())
            self.files_read.append(fs)
        self._cache[key] = out
        return out


# --------------------------------------------------------------------------- identity
def member_cik(syms: pd.DataFrame, ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> int | None:
    """The CIK filing Forms 3/4/5 under this symbol around the membership interval (most filings)."""
    m = syms[(syms.sym == ticker)
             & (syms["last"] >= start - pd.Timedelta(days=365))
             & (syms["first"] <= end + pd.Timedelta(days=90))]
    if m.empty:
        return None
    return int(m.sort_values(["n", "cik"], ascending=[False, True]).cik.iloc[0])


def resolve_candidates(ticker: str, cik: int | None, live_t2c: dict[str, int],
                       live_c2t: dict[int, list[str]], syms: pd.DataFrame,
                       identity_blocked: set[str]) -> tuple[list[str], list[str], str]:
    """(own-ticker candidates, successor candidates, identity status) for one member interval."""
    if ticker in identity_blocked:
        return [], [], "identity_blocked"
    own_live = live_t2c.get(ticker)
    if cik is not None and own_live is not None and own_live != cik:
        ident = "own_file_other_cik"
    elif cik is not None and own_live == cik:
        ident = "same_cik"
    else:
        ident = "unverified"
    succ: list[str] = []
    if cik is not None:
        later = syms.loc[(syms.cik == cik) & (syms.sym != ticker), "sym"].tolist()
        succ = sorted(set(later + live_c2t.get(cik, [])) - {ticker})
    return [ticker], succ, ident


def departure_kind(ticker: str, end: pd.Timestamp, is_open: bool, changes: pd.DataFrame) -> str:
    if is_open:
        return "continuing"
    if len(ticker) >= FAILURE_SUFFIX_MIN_LEN and ticker.endswith("Q"):
        return "failure"
    m = changes[(changes.rem_t == ticker) & ((changes.date - end).abs() <= pd.Timedelta(days=12))]
    return str(m.kind.iloc[0]) if len(m) else "no_reason_row"


def classify_reason(reason: str) -> str:
    r = str(reason).lower()
    if re.search(r"bankrupt|chapter 11|chapter 7|default|seized|receivership|liquidat|fdic", r):
        return "failure"
    if re.search(r"ticker|renam|name change|changed its name|symbol change", r):
        return "rename"
    if re.search(r"acquir|merg|purchas|bought|taken private|buyout|combin|takeover", r):
        return "M&A"
    if re.search(r"market cap|capitaliz|representative|float|liquidity|criteria", r):
        return "demotion"
    if re.search(r"spun|spin", r):
        return "spin"
    return "other"


def load_changes(wiki_html: Path) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(require(wiki_html).read_text()))
    ch = next((t for t in tables if t.shape[1] == 6), None)
    if ch is None:
        raise CensusError("no 6-column changes table in the Wikipedia snapshot")
    ch = ch.copy()
    ch.columns = ["date", "add_t", "add_s", "rem_t", "rem_s", "reason"]
    ch["date"] = pd.to_datetime(ch["date"], errors="coerce")
    ch["rem_t"] = normalize_symbol(ch["rem_t"].fillna(""))
    ch["kind"] = ch["reason"].map(classify_reason)
    return ch.dropna(subset=["date"])


# --------------------------------------------------------------------------- coverage
def interval_coverage(memb: pd.DataFrame, cal: pd.DatetimeIndex, bars: BarIndex, syms: pd.DataFrame,
                      live_t2c: dict[str, int], live_c2t: dict[int, list[str]],
                      identity_blocked: set[str], changes: pd.DataFrame) -> pd.DataFrame:
    """One row per (member interval, calendar year) with member-days and covered days per mode."""
    rows = []
    for r in memb.itertuples(index=False):
        days = cal[(cal >= r.start) & (cal <= r.end)]
        if len(days) == 0:
            continue
        cik = member_cik(syms, r.ticker, r.start, r.end)
        own, succ, ident = resolve_candidates(r.ticker, cik, live_t2c, live_c2t, syms, identity_blocked)
        kind = departure_kind(r.ticker, r.end, bool(r.open), changes)
        masks = {}
        for mode in ("any", "clean"):
            m_len = np.zeros(len(days), bool)
            for c in own + succ:
                m_len |= days.isin(bars.dates(c, mode))
            m_str = np.zeros(len(days), bool)
            for c in (own if ident != "own_file_other_cik" else []) + succ:
                m_str |= days.isin(bars.dates(c, mode))
            masks[mode] = (m_len, m_str)
        years = days.year
        for y in np.unique(years):
            sel = years == y
            rows.append(dict(
                ticker=r.ticker, start=r.start, end=r.end, departed=not bool(r.open), kind=kind,
                ident=ident, cik=cik if cik is not None else -1, successors=",".join(succ), year=int(y),
                n=int(sel.sum()),
                any_lenient=int(masks["any"][0][sel].sum()), any_strict=int(masks["any"][1][sel].sum()),
                clean_lenient=int(masks["clean"][0][sel].sum()),
                clean_strict=int(masks["clean"][1][sel].sum())))
    out = pd.DataFrame(rows)
    if out.empty:
        raise CensusError("coverage table is empty")
    return out


def pct(a: float, b: float) -> float:
    return round(100.0 * a / b, 2) if b > 0 else float("nan")


def coverage_by_year(cov: pd.DataFrame) -> list[dict]:
    out = []
    for y, g in cov.groupby("year"):
        row = {"year": int(y), "member_days": int(g.n.sum())}
        for col in ("any_lenient", "any_strict", "clean_lenient", "clean_strict"):
            row[f"pct_{col}"] = pct(g[col].sum(), g.n.sum())
        for dep, gd in g.groupby("departed"):
            tag = "departed" if dep else "continuing"
            row[f"pct_any_lenient_{tag}"] = pct(gd.any_lenient.sum(), gd.n.sum())
            row[f"member_days_{tag}"] = int(gd.n.sum())
        out.append(row)
    return out


def coverage_by_kind(cov: pd.DataFrame, start: pd.Timestamp) -> list[dict]:
    g = cov[cov.year >= start.year]
    iv = g.groupby(["ticker", "start", "kind"]).agg(n=("n", "sum"), c=("any_lenient", "sum")).reset_index()
    out = []
    for k, gk in iv.groupby("kind"):
        out.append({"kind": k, "intervals": int(len(gk)), "member_days": int(gk.n.sum()),
                    "pct_days_covered_any_lenient": pct(gk.c.sum(), gk.n.sum()),
                    "intervals_covered_95pct": int(((gk.c / gk.n) >= 0.95).sum())})
    return sorted(out, key=lambda d: -d["member_days"])


def window_summary(cov: pd.DataFrame, a: int, b: int) -> dict:
    g = cov[(cov.year >= a) & (cov.year <= b)]
    out = {"years": f"{a}-{b}", "member_days": int(g.n.sum())}
    for col in ("any_lenient", "any_strict", "clean_lenient", "clean_strict"):
        out[f"pct_{col}"] = pct(g[col].sum(), g.n.sum())
    miss = g.n - g.any_lenient
    out["missing_days_any_lenient"] = int(miss.sum())
    out["missing_share_departed"] = pct(miss[g.departed].sum(), miss.sum())
    return out


# --------------------------------------------------------------------------- dates
def earnings_events(panel: pd.DataFrame, td: pd.DatetimeIndex) -> pd.DataFrame:
    """Deduped earnings releases with the first trading day the market can react on.

    An 8-K with item 2.02 (or item 12, its 2003-03 → 2004-08 predecessor). Accepted at/after 16:00 ET →
    the next trading day reacts; otherwise the filing day. One release per firm-quarter: a filing
    within DEDUPE_DAYS of the last kept one (a guidance update, a restated release) is dropped."""
    items = panel["items"].fillna("").str.split(",")
    e = panel[items.apply(lambda xs: ("2.02" in xs) or ("12" in xs))].copy()
    if e.empty:
        raise CensusError("no item 2.02 / 12 filings in the 8-K panel")
    et = pd.to_datetime(e["acceptance_dt"], utc=True).dt.tz_convert("America/New_York")
    hhmm = (et.dt.hour * 100 + et.dt.minute).to_numpy()
    tdv = td.values.astype("datetime64[D]")
    pos = np.searchsorted(tdv, e["filing_date"].values.astype("datetime64[D]"), side="left")
    pos = np.where(hhmm >= AFTER_CLOSE_HHMM, pos + 1, pos)
    e = e[pos < len(td)].copy()
    e["react"] = td.values[pos[pos < len(td)]]
    e = e.sort_values(["ticker", "react", "accession"])
    kept: list[tuple[str, pd.Timestamp]] = []
    for t, g in e.groupby("ticker", sort=True):
        last = None
        for d in g["react"]:
            if last is None or (d - last).days >= DEDUPE_DAYS:
                kept.append((t, d))
                last = d
    return pd.DataFrame(kept, columns=["ticker", "react"])


def predict(events: pd.DataFrame, td: pd.DatetimeIndex) -> pd.DataFrame:
    """Each release at date d predicts the same-quarter release at d + 364, rolled to a trading day."""
    p = events.copy()
    target = (p["react"] + pd.Timedelta(days=PREDICT_DAYS)).values
    pos = np.searchsorted(td.values, target, side="left")
    p = p[pos < len(td)].copy()
    p["pred"] = td.values[pos[pos < len(td)]]
    return p


def prediction_census(events: pd.DataFrame, td: pd.DatetimeIndex, since: pd.Timestamp) -> dict:
    """How far "last year's release + 364 days" lands from the actual release, in TRADING days.
    Dates only: the actual release dates are compared with the rule's predictions."""
    errs, unmatched = [], 0
    tdv = td.values.astype("datetime64[D]")
    for _, g in events.groupby("ticker", sort=True):
        ds = g["react"].values.astype("datetime64[D]")
        for d in ds[ds >= np.datetime64(since.date())]:
            prev = ds[(ds >= d - PREDICT_DAYS - 45) & (ds <= d - PREDICT_DAYS + 45)]
            if len(prev) == 0:
                unmatched += 1
                continue
            pred_pos = np.searchsorted(tdv, prev + PREDICT_DAYS, side="left")
            act_pos = int(np.searchsorted(tdv, d, side="left"))
            diff = act_pos - pred_pos
            errs.append(int(diff[np.argmin(np.abs(diff))]))
    a = np.abs(np.array(errs))
    n = len(errs) + unmatched
    if n == 0:
        raise CensusError("prediction census found no releases")
    return {"events": int(n), "share_no_prior_year_release": round(unmatched / n, 4),
            "share_abs_err_0_tdays": round(float((a == 0).mean()), 4),
            "share_abs_err_le_2_tdays": round(float((a <= 2).mean()), 4),
            "share_abs_err_le_5_tdays": round(float((a <= 5).mean()), 4),
            "share_abs_err_gt_5_tdays": round(float((a > 5).mean()), 4),
            "share_actual_before_predicted": round(float((np.array(errs) < 0).mean()), 4)}


def calendar_crosscheck(events: pd.DataFrame, cal_parquet: Path, td: pd.DatetimeIndex) -> dict:
    """8-K reaction days against the pinned vendor calendar (`earnings_dates_pinned`, 2008+):
    the vendor's date is the announcement day, so an after-close release reacts one trading day later."""
    cal = pd.read_parquet(require(cal_parquet))
    cal = cal[cal["earnings_date"] <= td.max()]
    tdv = td.values.astype("datetime64[D]")
    diffs = []
    for t, g in cal.groupby("ticker", sort=True):
        ev = events.loc[events.ticker == t, "react"].values.astype("datetime64[D]")
        if len(ev) == 0:
            continue
        ev_pos = np.searchsorted(tdv, ev, side="left")
        for d in g["earnings_date"].values.astype("datetime64[D]"):
            dp = int(np.searchsorted(tdv, d, side="left"))
            k = ev_pos - dp
            diffs.append(int(k[np.argmin(np.abs(k))]))
    a = np.array(diffs)
    if len(a) == 0:
        raise CensusError("calendar cross-check matched no ticker")
    return {"calendar_dates": int(len(a)),
            "share_8k_react_same_or_next_tday": round(float(((a == 0) | (a == 1)).mean()), 4),
            "share_within_3_tdays": round(float((np.abs(a) <= 3).mean()), 4),
            "share_more_than_10_tdays": round(float((np.abs(a) > 10).mean()), 4)}


def week_ends(td: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(td, index=td)
    return pd.DatetimeIndex(s.groupby(td.to_period("W-FRI")).max().values)


def announcers_per_week(pred: pd.DataFrame, memb: pd.DataFrame, wk: pd.DatetimeIndex) -> pd.Series:
    """Distinct PIT members whose predicted reaction day falls in (week_end[i-1], week_end[i]]."""
    i = np.searchsorted(wk.values, pred["pred"].values, side="left")
    p = pred[i < len(wk)].copy()
    p["week"] = wk.values[i[i < len(wk)]]
    p = p.merge(memb[["ticker", "start", "end"]], on="ticker")
    p = p[(p["pred"] >= p["start"]) & (p["pred"] <= p["end"])]
    return p.groupby("week").ticker.nunique().reindex(wk, fill_value=0)


def weeks_summary(cnt: pd.Series, a: str, b: str) -> dict:
    c = cnt[(cnt.index > pd.Timestamp(a)) & (cnt.index <= pd.Timestamp(b))]
    q = c[c >= MIN_ANNOUNCERS]
    yrs = len(c) / 52.18
    return {"from": a, "to": b, "weeks": int(len(c)), "qualifying_weeks": int(len(q)),
            "qualifying_weeks_per_year": round(len(q) / yrs, 1) if yrs else float("nan"),
            "median_basket_in_qualifying_weeks": float(q.median()) if len(q) else float("nan"),
            "years": round(yrs, 2)}


def dated_member_share(cov: pd.DataFrame, panel_tickers: set[str]) -> dict:
    iv = cov.groupby(["ticker", "start", "departed", "successors"]).n.sum().reset_index()
    has = iv.apply(lambda r: r.ticker in panel_tickers
                   or any(s in panel_tickers for s in str(r.successors).split(",") if s), axis=1)
    out = {}
    for dep, g in iv.assign(has=has).groupby("departed"):
        out["departed" if dep else "continuing"] = {
            "intervals": int(len(g)), "with_8k_panel_dates": int(g.has.sum()),
            "member_days_with_dates_pct": pct(g.n[g.has].sum(), g.n.sum())}
    return out


def departed_cik_share(cov: pd.DataFrame, panel_tickers: set[str]) -> dict:
    iv = cov[cov.departed].groupby(["ticker", "start"]).agg(cik=("cik", "first")).reset_index()
    iv = iv[~iv.ticker.isin(panel_tickers)]
    return {"departed_intervals_without_panel_dates": int(len(iv)),
            "of_which_cik_from_form345": int((iv.cik > 0).sum())}


# --------------------------------------------------------------------------- paid-data unlock
def firstrate_unlock(cov: pd.DataFrame, fr_csv: Path, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Weekdays of under-covered wanted-list members a FirstRate `-DELISTED` series would reach
    (the director's 2026-10-23 per-name table; delisted start dates only)."""
    fr = pd.read_csv(require(fr_csv), parse_dates=["fr_delisted_start"])
    iv = cov.groupby(["ticker", "start", "end"]).agg(n=("n", "sum"), c=("any_lenient", "sum")).reset_index()
    under = iv[iv.c < 0.95 * iv.n].merge(fr[["ticker", "fr_delisted_start"]], on="ticker", how="left",
                                         indicator=True)
    listed = under[under["_merge"] == "both"]

    def wd(s: pd.Timestamp, e: pd.Timestamp) -> int:
        return int(max(0, np.busday_count(s.date(), e.date())))

    tot = sum(wd(max(r.start, start), min(r.end, end)) for r in listed.itertuples())
    frd = sum(wd(max(r.start, start, r.fr_delisted_start), min(r.end, end))
              for r in listed.itertuples() if pd.notna(r.fr_delisted_start))
    return {"under_covered_intervals": int(len(under)),
            "of_which_on_wanted_list": int(len(listed)),
            "wanted_list_weekdays_in_window": tot,
            "firstrate_delisted_weekdays": frd,
            "firstrate_share_of_wanted_list_gap": round(frd / tot, 3) if tot else float("nan"),
            "under_covered_member_days_not_on_wanted_list":
                int((under.n - under.c)[under["_merge"] == "left_only"].sum())}


# --------------------------------------------------------------------------- controls
def positive_controls(cov: pd.DataFrame, events: pd.DataFrame, td: pd.DatetimeIndex) -> list[dict]:
    """Known answers on this module's own code path. A miss HALTS the census."""
    def share(ticker: str, col: str, y0: int, y1: int) -> float:
        g = cov[(cov.ticker == ticker) & (cov.year >= y0) & (cov.year <= y1)]
        if g.empty:
            raise CensusError(f"control: {ticker} absent from the coverage table")
        return float(g[col].sum() / g.n.sum())

    checks = [
        ("AAPL continuing member covered (any) 2005-2025", share("AAPL", "any_lenient", 2005, 2025) >= 0.99),
        ("FB covered through its CIK successor META (rename lineage) 2014-2021",
         share("FB", "any_strict", 2014, 2021) >= 0.99),
        ("BRK-B covered through the BRK.B file name (share-class form) 2011-2025",
         share("BRK-B", "any_lenient", 2011, 2025) >= 0.99),
        ("LEHMQ (failed 2008) has no usable bar — a known survivorship hole is detected",
         share("LEHMQ", "any_lenient", 2004, 2008) == 0.0),
        ("clean mode refuses data/processed before 2020-04-09 (AAPL 2010-2015 clean = 0)",
         share("AAPL", "clean_lenient", 2010, 2015) == 0.0),
    ]
    aapl = events[events.ticker == "AAPL"]
    pr = predict(aapl, td)
    hit = pr[(pr["react"] == pd.Timestamp("2023-11-03"))]
    checks.append(("AAPL 2023-11-02 16:30 ET release reacts 2023-11-03 and predicts 2024-11-01",
                   len(hit) == 1 and hit["pred"].iloc[0] == pd.Timestamp("2024-11-01")))
    checks.append(("AAPL has exactly 4 deduped releases in 2024",
                   int((aapl["react"].dt.year == 2024).sum()) == 4))
    out = [{"control": name, "pass": bool(ok)} for name, ok in checks]
    failed = [c["control"] for c in out if not c["pass"]]
    if failed:
        raise CensusError(f"positive control(s) FAILED: {failed}")
    return out


# --------------------------------------------------------------------------- main
def refuse_data_path(out: Path, data_root: Path) -> None:
    """The census never writes into any data tree (the worktree's, the main checkout's, or --data-root)."""
    resolved = Path(out).resolve()
    roots = {Path(data_root).resolve(), (ROOT / "data").absolute()}
    if (ROOT / "data").exists():
        roots.add((ROOT / "data").resolve())
    for root in roots:
        if resolved == root or root in resolved.parents:
            raise CensusError(f"refusing to write under a data tree: {out}")


def run(inp: Inputs) -> dict:
    td = load_calendar(inp.calendar_csv, PRIOR_YEAR_START, inp.window_end)
    memb = load_membership(inp.membership, PRIOR_YEAR_START, inp.window_end)
    wanted = pd.read_csv(require(inp.wanted_csv))
    blocked = set(wanted.loc[wanted["priority"].astype(str).str.startswith("P2"), "ticker"])
    syms = load_issuer_symbols(inp.form345_glob)
    live_t2c, live_c2t = load_live_maps(inp.live_tickers)
    changes = load_changes(inp.wiki_html)
    bars = BarIndex(require(inp.processed_dir), require(inp.t265_dir))
    cov = interval_coverage(memb, td, bars, syms, live_t2c, live_c2t, blocked, changes)
    panel = pd.read_parquet(require(inp.panel_8k))
    events = earnings_events(panel, td)
    controls = positive_controls(cov, events, td)
    pred = predict(events, td)
    wk = week_ends(td)
    cnt = announcers_per_week(pred, memb, wk)
    panel_tickers = set(panel["ticker"].unique())
    end_s = str(inp.window_end.date())
    form345 = [Path(p) for p in sorted(glob.glob(inp.form345_glob))]
    return {
        "task": "T-415 (E-2) Phase 1 census — counts only; no return computed",
        "window": {"prior_year_start": str(PRIOR_YEAR_START.date()),
                   "test_start": str(WINDOW_START.date()), "end": end_s},
        "input_md5": {
            "membership": md5_file(inp.membership), "calendar_spy_csv": md5_file(inp.calendar_csv),
            "panel_8k": md5_file(inp.panel_8k), "live_tickers": md5_file(inp.live_tickers),
            "wiki_html": md5_file(inp.wiki_html), "wanted_csv": md5_file(inp.wanted_csv),
            "firstrate_csv": md5_file(inp.firstrate_csv),
            "form345_manifest": md5_manifest(form345),
            "price_files_manifest": md5_manifest(sorted(set(bars.files_read))),
            "price_files_read": len(set(bars.files_read)),
            "calendar_pinned": md5_file(inp.calendar_pinned)},
        "declared_exclusions_withheld": sorted(bars.withheld),
        "controls": controls,
        "coverage_by_year": coverage_by_year(cov),
        "coverage_windows": [window_summary(cov, 2004, 2015), window_summary(cov, 2016, 2020),
                             window_summary(cov, 2021, 2026), window_summary(cov, 2004, 2026),
                             window_summary(cov, 2016, 2026)],
        "coverage_by_departure_kind": coverage_by_kind(cov, WINDOW_START),
        "identity_status_intervals": cov.groupby(["ticker", "start"]).ident.first().value_counts().to_dict(),
        "dates": {
            "panel_tickers": len(panel_tickers),
            "first_item_202": str(panel.loc[panel["items"].fillna("").str.split(",")
                                            .apply(lambda x: "2.02" in x), "filing_date"].min().date()),
            "deduped_releases": int(len(events)),
            "prediction": prediction_census(events, td, pd.Timestamp("2005-01-01")),
            "calendar_crosscheck": calendar_crosscheck(events, inp.calendar_pinned, td),
            "dated_members": dated_member_share(cov, panel_tickers),
            "departed_cik": departed_cik_share(cov, panel_tickers)},
        "announcers_per_week": [weeks_summary(cnt, str(WINDOW_START.date()), end_s),
                                weeks_summary(cnt, "2016-01-01", end_s),
                                weeks_summary(cnt, "2021-01-01", end_s)],
        "paid_unlock_firstrate": firstrate_unlock(cov, inp.firstrate_csv, WINDOW_START, inp.window_end),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", type=Path, help="JSON output path (never under data/)")
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--data-root", type=Path, default=DATA,
                    help="read-only data tree (default: <repo>/data; a worktree may point at the main checkout's)")
    a = ap.parse_args(argv)
    if a.out is None and not a.controls_only:
        ap.error("--out is required unless --controls-only")
    try:
        if a.out is not None:
            refuse_data_path(a.out, a.data_root)
        res = run(Inputs(data_root=require(a.data_root)))
    except CensusError as e:
        print(f"[T415-census] HALT: {e}", file=sys.stderr)
        return 2
    if a.controls_only:
        print(json.dumps(res["controls"], indent=1))
        return 0
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, default=str))
    print(f"[T415-census] wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
