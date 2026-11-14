"""T-398 — a buy-and-hold stacked trend overlay (100 % equity + trend, the RSST structure) vs 1x
equity on terminal wealth, on INVESTABLE net-of-fee trend returns.

Pre-registration: docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md (frozen at ac01413;
amendment 1 = the director's rulings + A1.1; amendment 2 = the membership-and-ER table).

Standalone harness (the T-311 / B-5 pattern). Never BacktestController. Touches no engine.
B-5's simulator pieces are IMPORTED from scripts/b5_levered_diversified.py, never edited.

Subcommands (A1.1-1):
    meta       one-time: yfinance Ticker.info + Ticker.actions per ticker (BEFORE any price)
    fetch      one-time: prices via fetch_yf_tr (Adj Close, auto_adjust=False) + pinned byte copies
    btop50     one-time: read BarclayHedge's public page and terms (R-8); level 2 context only
    integrity  D1-D4 on every candidate's prices; a flag on a candidate HALTS (no auto-fix)
    gates      E1-E4 evaluability gates + V1-V3 reported validations
    smoke      mechanics on the FIRST 12 months of each window (never quoted)
    run --tag  the measurement; run twice (A, B) to identical md5s

Everything is written under data/t398_local/ (worktree-local; nothing through data/research).
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from scripts import b5_levered_diversified as b5  # noqa: E402  (import only — never edited)

# --------------------------------------------------------------------------- paths
OUT = ROOT / "data/t398_local"
INPUTS = OUT / "inputs"
META = OUT / "meta"
META_MANIFEST = META / "META_MANIFEST.json"
MANIFEST = INPUTS / "MANIFEST.json"
BTOP_DIR = OUT / "btop50"
INTEGRITY = OUT / "integrity.json"
RULINGS = OUT / "integrity_rulings.json"
GATES = OUT / "gates.json"
SMOKE = OUT / "smoke.json"
SUB = ROOT / "data/research/substrate_multidecade"
B5_INPUTS = ROOT / "data/research/b5/inputs"
AQR_SRC = ROOT / "data/research/aqr_tsmom_monthly_t296.xlsx"

# --------------------------------------------------------------------------- frozen inputs (prereg §3)
PINNED_MD5 = {
    "equity_tr_daily.csv": "c2030019b8846792b5f8e3d18421c905",
    "bond_tr_daily.csv": "0ac665e8a30d04cf5506c63aaf4e0093",
    "frb_h15_all_sdmx.zip": "50fa80972f99b5f8ea06ef52483c5926",
    "nyfed_sofr.csv": "8cbceec98342202d2168618b48822ade",
    "aqr_tsmom_monthly_t296.xlsx": "5bcb8dbf28146f729b99b629147bb0cd",
}
PINNED_SRC = {
    "frb_h15_all_sdmx.zip": B5_INPUTS / "frb_h15_all_sdmx.zip",
    "nyfed_sofr.csv": B5_INPUTS / "nyfed_sofr.csv",
    "aqr_tsmom_monthly_t296.xlsx": AQR_SRC,
}
PREREG_REF = "ac01413 + amendment 1 + amendment 2 (membership and ER)"

# §4.1 the candidate list, fixed in the prereg (15 tickers) with the from-memory fallback ERs.
CANDIDATES: Dict[str, Dict] = {
    "RYMFX": {"fallback_er": 0.0170, "memory_first": "2007-03", "flag": "strategy change (~2012)"},
    "AQMIX": {"fallback_er": 0.0125, "memory_first": "2010-01", "flag": None},
    "ASFYX": {"fallback_er": 0.0145, "memory_first": "2010-07", "flag": None},
    "WTMF": {"fallback_er": 0.0065, "memory_first": "2011-01", "flag": "strategy changes (2016, 2021)"},
    "EVOIX": {"fallback_er": 0.0160, "memory_first": "2011-10", "flag": "bond-sleeve collateral"},
    "GMSSX": {"fallback_er": 0.0100, "memory_first": "2012-02", "flag": None},
    "CSAIX": {"fallback_er": 0.0130, "memory_first": "2012-09", "flag": "may be delisted"},
    "FMF": {"fallback_er": 0.0095, "memory_first": "2013-08", "flag": "strategy change"},
    "PQTIX": {"fallback_er": 0.0140, "memory_first": "2013-12", "flag": None},
    "ABYIX": {"fallback_er": 0.0179, "memory_first": "2014-07", "flag": None},
    "LOTIX": {"fallback_er": 0.0175, "memory_first": "2014-07", "flag": None},
    "AHLIX": {"fallback_er": 0.0150, "memory_first": "2014-08", "flag": None},
    "DBMF": {"fallback_er": 0.0085, "memory_first": "2019-05", "flag": None},
    "KMLM": {"fallback_er": 0.0090, "memory_first": "2020-12", "flag": None},
    "CTA": {"fallback_er": 0.0075, "memory_first": "2022-03", "flag": None},
}
FLAGGED = ("RYMFX", "WTMF", "FMF", "EVOIX")            # S1 removes these four
ETF_ONLY = ("DBMF", "KMLM", "CTA", "WTMF", "FMF")       # S2
ANCHORS = ("RSST", "BLNDX", "MAFIX", "SPY", "VT")
ELIGIBLE_CATEGORY = "Systematic Trend"                  # rule (b)
LAST_FIRST_PRICE = pd.Timestamp("2022-12-30")           # rule (c)
YF_START, YF_ASOF = "1990-01-01", "2026-01-01"
WINDOW_END = pd.Timestamp("2025-12-31")
ER_CAP = 0.0200
ER_RANGE = (0.0020, 0.0500)

TD = 252
ER_S = 0.0100                                           # the stacked fund's all-in ER (B-5's RSST)
ER_E = b5.ER_SPY_SLEEVE                                 # 0.09 % (T-311)
S_H1 = 0.0050                                           # 50 bp on the whole overlay notional
H_SURV = 0.0100                                         # decision cell (R-3)
SPREADS_BP = list(range(0, 401, 5))
N_ITER, SEED, BLOCK_DAILY, SENS2_DAILY = 1000, 0, 21, 252
BLOCK_MONTHLY, SENS2_MONTHLY = 1, 12
MIN_MEMBERS = 3
E1_MIN_YEARS = 12.0
E2_MIN_CORR = 0.50
N_EFF_T391_PLUS1 = 372.28                               # T-391 R3 count 371.28 + 1 (not merged)
D1_DROP, D1_MEDIAN, D2_RUN, D3_GAP, D4_MOVE = -0.03, -0.01, 5, 5, 0.08
EPISODE_DEPTH = -0.10
T316_CORR_BAR = 0.30                                    # T-316 GATE_A_CORR_MAX, quoted (never imported)

# Amendment 2 (committed alone BEFORE any price was loaded, R-10): rule (b) and the ER used, from the
# yfinance metadata step. `fetch` and everything after it REFUSE while this is None.
MEMBERSHIP_FROZEN: Optional[Dict[str, Dict]] = {
    "RYMFX": {"rule_b": True, "er": 0.0199, "er_source": "metadata"},
    "AQMIX": {"rule_b": True, "er": 0.0200, "er_source": "metadata 3.09 %, capped"},
    "ASFYX": {"rule_b": True, "er": 0.0145, "er_source": "metadata"},
    "WTMF": {"rule_b": True, "er": 0.0066, "er_source": "metadata"},
    "EVOIX": {"rule_b": True, "er": 0.0134, "er_source": "metadata"},
    "GMSSX": {"rule_b": True, "er": 0.0080, "er_source": "metadata"},
    "CSAIX": {"rule_b": True, "er": 0.0130, "er_source": "fallback (no metadata ER)"},
    "FMF": {"rule_b": True, "er": 0.0098, "er_source": "metadata"},
    "PQTIX": {"rule_b": True, "er": 0.0151, "er_source": "metadata"},
    "ABYIX": {"rule_b": True, "er": 0.0179, "er_source": "metadata"},
    "LOTIX": {"rule_b": True, "er": 0.0181, "er_source": "metadata"},
    "AHLIX": {"rule_b": True, "er": 0.0156, "er_source": "metadata"},
    "DBMF": {"rule_b": True, "er": 0.0085, "er_source": "metadata"},
    "KMLM": {"rule_b": True, "er": 0.0090, "er_source": "metadata"},
    "CTA": {"rule_b": True, "er": 0.0086, "er_source": "metadata"},
}


class T398Halt(RuntimeError):
    """A fail-closed halt in the measurement path. Never caught inside the harness."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_frozen() -> Dict[str, Dict]:
    if MEMBERSHIP_FROZEN is None:
        raise T398Halt("the membership-and-ER table is not frozen (amendment 2); no price may be loaded")
    return MEMBERSHIP_FROZEN


# --------------------------------------------------------------------------- step 1: metadata
def _plain(o):
    """Make a yfinance info dict JSON-safe without dropping anything."""
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (str, int, bool)) or o is None:
        return o
    return str(o)


def er_unit_from_spy(spy_value: Optional[float]) -> Optional[str]:
    """A1.1-2: the ER field's units are fixed by SPY's value in the same field."""
    if spy_value is None or not np.isfinite(spy_value):
        return None
    if 0.05 <= spy_value <= 0.15:
        return "percent"
    if 0.0005 <= spy_value <= 0.0015:
        return "fraction"
    return None


def convert_er(value: Optional[float], unit: Optional[str]) -> Optional[float]:
    """Metadata ER -> decimal, or None when unusable (outside [0.20 %, 5.00 %], A1.1-2)."""
    if value is None or unit is None or not np.isfinite(value):
        return None
    er = float(value) / 100.0 if unit == "percent" else float(value)
    lo, hi = ER_RANGE
    return er if lo <= er <= hi else None


def cmd_meta() -> int:
    """One-time metadata fetch: BEFORE any price (R-10). Stores the provider's output raw."""
    if META_MANIFEST.exists():
        raise T398Halt(f"metadata already fetched ({META_MANIFEST}); the step runs ONCE")
    if META.exists() and any(META.iterdir()):
        raise T398Halt(f"{META} holds files but no manifest — a foreign or partial state; stop")
    import yfinance as yf
    stage = OUT / f"meta_attempt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    stage.mkdir(parents=True, exist_ok=False)
    entries: Dict[str, Dict] = {}
    for tk in list(CANDIDATES) + list(ANCHORS):
        rec: Dict = {"ticker": tk, "fetched_utc": _now(), "errors": []}
        t = yf.Ticker(tk)
        try:
            info = _plain(dict(t.info or {}))
        except Exception as exc:  # noqa: BLE001 — the provider's reason is kept verbatim, never filtered
            info = {}
            rec["errors"].append(f"info: {type(exc).__name__}: {exc}")
        try:
            act = t.actions
            act = act if act is not None else pd.DataFrame()
        except Exception as exc:  # noqa: BLE001
            act = pd.DataFrame()
            rec["errors"].append(f"actions: {type(exc).__name__}: {exc}")
        overview: Dict = {}
        operations: Dict = {}
        try:
            fd = t.funds_data
            overview = _plain(dict(fd.fund_overview or {}))
            fo = fd.fund_operations
            operations = {str(i): {str(c): (None if pd.isna(v) else str(v)) for c, v in row.items()}
                          for i, row in fo.iterrows()}
        except Exception as exc:  # noqa: BLE001
            rec["errors"].append(f"funds_data: {type(exc).__name__}: {exc}")
        (stage / f"{tk}_info.json").write_text(json.dumps(
            {"info": info, "fund_overview": overview, "fund_operations": operations},
            indent=1, sort_keys=True) + "\n")
        act = act.copy()
        if len(act):
            act.index = pd.DatetimeIndex(act.index).tz_localize(None).normalize()
        act.index.name = "Date"
        act.to_csv(stage / f"{tk}_actions.csv")
        rec.update({"info_keys": len(info), "actions_rows": int(len(act)),
                    "info_md5": b5.md5_file(stage / f"{tk}_info.json"),
                    "actions_md5": b5.md5_file(stage / f"{tk}_actions.csv"),
                    "yfinance_version": yf.__version__})
        entries[tk] = rec
        print(f"  {tk}: info keys {len(info)}, actions rows {len(act)}, errors {rec['errors']}")
        time.sleep(1.0)
    b5.write_json(stage / META_MANIFEST.name, {"prereg": PREREG_REF, "staged_as": stage.name,
                                               "tickers": entries})
    stage.rename(META)
    print(f"metadata written: {META_MANIFEST}")
    return 0


def read_meta(tk: str) -> Dict:
    return json.loads((META / f"{tk}_info.json").read_text())


def meta_table() -> Dict[str, Dict]:
    """The mechanical reading of the metadata (A1.1-2). Prints what amendment 2 freezes."""
    if not META_MANIFEST.exists():
        raise T398Halt("no metadata snapshot — run `meta` first")
    spy = read_meta("SPY")["info"]
    field, unit = None, None
    for f in ("netExpenseRatio", "annualReportExpenseRatio"):
        u = er_unit_from_spy(spy.get(f))
        if u is not None:
            field, unit = f, u
            break
    out: Dict[str, Dict] = {"_er_field": {"field": field, "unit": unit,
                                          "spy_values": {f: spy.get(f) for f in
                                                         ("netExpenseRatio", "annualReportExpenseRatio")}}}
    for tk in list(CANDIDATES) + [a for a in ANCHORS if a not in ("SPY", "VT")]:
        m = read_meta(tk)
        info, ov = m["info"], m["fund_overview"]
        cat = info.get("category") or ov.get("categoryName") or None
        raw = None
        for f in ("netExpenseRatio", "annualReportExpenseRatio"):
            if info.get(f) is not None and er_unit_from_spy(spy.get(f)) is not None:
                raw = (f, info.get(f), er_unit_from_spy(spy.get(f)))
                break
        er_meta = convert_er(raw[1], raw[2]) if raw else None
        inc = info.get("fundInceptionDate")
        inc_s = None
        if isinstance(inc, (int, float)) and np.isfinite(inc):
            inc_s = str(pd.Timestamp(int(inc), unit="s").date())
        cand = CANDIDATES.get(tk, {})
        fb = cand.get("fallback_er")
        er_used = er_meta if er_meta is not None else fb
        out[tk] = {"name": info.get("longName") or info.get("shortName"), "quoteType": info.get("quoteType"),
                   "category": cat, "category_rule_b": (cat is None) or (cat == ELIGIBLE_CATEGORY),
                   "er_raw": raw, "er_meta": er_meta, "er_fallback": fb,
                   "er_used_before_cap": er_used,
                   "er_used": None if er_used is None else min(er_used, ER_CAP),
                   "er_source": "metadata" if er_meta is not None else "fallback",
                   "inception_meta": inc_s, "memory_first": cand.get("memory_first"),
                   "info_keys": len(info)}
    return out


def cmd_meta_table() -> int:
    t = meta_table()
    b5.write_json(OUT / "meta_table.json", t)
    print(json.dumps(b5._jsonable(t), indent=1))
    return 0


# --------------------------------------------------------------------------- step 2: prices
def _fetch_one(tk: str) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """fetch_yf_tr (Adj Close, auto_adjust=False; never the module's writer). One retry after 60 s
    (A1.1-3). The provider's own messages go to stdout unfiltered; the outcome is recorded."""
    from scripts.reconcile_stooq_tr_t256 import fetch_yf_tr
    notes: List[str] = []
    for attempt in (1, 2):
        tr, close = fetch_yf_tr(tk, YF_START, YF_ASOF)
        if tr is not None and close is not None and len(tr) > 0:
            df = pd.DataFrame({"adj_close": tr["Close"].astype(float), "raw_close": close.astype(float)})
            df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
            df.index.name = "Date"
            return df.dropna(), notes
        notes.append(f"attempt {attempt}: provider returned no rows")
        if attempt == 1:
            time.sleep(60)
    return None, notes


def cmd_fetch() -> int:
    """One-time price fetch + byte copies of the pinned inputs. Refuses before amendment 2."""
    _require_frozen()
    if MANIFEST.exists():
        raise T398Halt(f"snapshot already exists ({MANIFEST}); the fetch runs ONCE (prereg §2.6)")
    if INPUTS.exists() and any(INPUTS.iterdir()):
        raise T398Halt(f"{INPUTS} holds files but no manifest — a foreign or partial state; stop")
    import yfinance as yf
    stage = OUT / f"inputs_attempt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    stage.mkdir(parents=True, exist_ok=False)
    entries: Dict[str, Dict] = {}
    missing: Dict[str, List[str]] = {}
    for tk in list(CANDIDATES) + list(ANCHORS):
        df, notes = _fetch_one(tk)
        if df is None:
            missing[tk] = notes
            print(f"  {tk}: NOTHING RETURNED {notes}")
            continue
        if df.index.max() >= pd.Timestamp(YF_ASOF):
            raise T398Halt(f"{tk}: a row dated {df.index.max().date()} is inside the 2026 holdout")
        p = stage / f"yf_{tk}.csv"
        df.to_csv(p, float_format="%.10g")
        entries[p.name] = {"source": "yfinance via scripts/reconcile_stooq_tr_t256.py::fetch_yf_tr "
                                     "(Adj Close, auto_adjust=False)",
                           "call": f"fetch_yf_tr({tk!r}, {YF_START!r}, {YF_ASOF!r})", "fetched_utc": _now(),
                           "rows": int(len(df)), "first": str(df.index[0].date()),
                           "last": str(df.index[-1].date()), "md5": b5.md5_file(p),
                           "yfinance_version": yf.__version__, "notes": notes}
        print(f"  {tk}: {len(df)} rows {df.index[0].date()}..{df.index[-1].date()} {notes}")
        time.sleep(1.0)
    for name, src in PINNED_SRC.items():
        if b5.md5_file(src) != PINNED_MD5[name]:
            raise T398Halt(f"pinned input {src} does not match the prereg md5")
        p = stage / name
        shutil.copyfile(src, p)
        if b5.md5_file(p) != PINNED_MD5[name]:
            raise T398Halt(f"copy of {name} md5 mismatch")
        entries[name] = {"source": f"copied byte-for-byte from {src.relative_to(ROOT)}",
                         "call": "shutil.copyfile", "fetched_utc": _now(), "md5": PINNED_MD5[name]}
    for a in ANCHORS:
        if a in missing and a in ("RSST", "SPY"):
            raise T398Halt(f"anchor {a} returned nothing (fail closed)")
    b5.write_json(stage / MANIFEST.name, {"prereg": PREREG_REF, "staged_as": stage.name,
                                          "files": entries, "returned_nothing": missing})
    stage.rename(INPUTS)
    print(f"snapshot written: {MANIFEST}")
    return 0


def verify_snapshot() -> Dict:
    """E4: every pinned input and every snapshot file matches its md5, or HALT."""
    if not MANIFEST.exists():
        raise T398Halt(f"no snapshot manifest at {MANIFEST} — run `fetch` first")
    man = json.loads(MANIFEST.read_text())
    for name, e in man["files"].items():
        p = INPUTS / name
        if not p.exists() or b5.md5_file(p) != e["md5"]:
            raise T398Halt(f"snapshot file {name} missing or md5 != manifest")
    for name in ("equity_tr_daily.csv", "bond_tr_daily.csv"):
        if b5.md5_file(SUB / name) != PINNED_MD5[name]:
            raise T398Halt(f"T-306 substrate {name} md5 != prereg §3 — re-verify required")
    for name in PINNED_SRC:
        if man["files"][name]["md5"] != PINNED_MD5[name]:
            raise T398Halt(f"pinned input {name} md5 != prereg §3")
    return man


def load_px(tk: str) -> pd.DataFrame:
    df = pd.read_csv(INPUTS / f"yf_{tk}.csv", parse_dates=["Date"], index_col="Date").sort_index()
    if df.index.duplicated().any():
        raise T398Halt(f"{tk}: duplicated price dates")
    if df.index.max() > WINDOW_END:
        raise T398Halt(f"{tk}: a row dated {df.index.max().date()} is inside the 2026 holdout")
    return df.astype(float)


def load_actions(tk: str) -> pd.DataFrame:
    p = META / f"{tk}_actions.csv"
    df = pd.read_csv(p)
    if len(df) == 0 or "Date" not in df.columns:
        return pd.DataFrame(columns=["Dividends", "Capital Gains"], index=pd.DatetimeIndex([], name="Date"))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()


def equity_calendar() -> pd.DatetimeIndex:
    idx = pd.read_csv(SUB / "equity_tr_daily.csv", index_col=0, parse_dates=True).index
    return pd.DatetimeIndex(idx[idx <= WINDOW_END]).sort_values()


def have_prices(man: Dict) -> List[str]:
    return [tk for tk in CANDIDATES if f"yf_{tk}.csv" in man["files"]]


# --------------------------------------------------------------------------- integrity (D1-D4)
def _runs(mask: np.ndarray) -> List[Tuple[int, int]]:
    """(start, length) of every run of True in a boolean array."""
    out: List[Tuple[int, int]] = []
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def distribution_dates(actions: pd.DataFrame) -> pd.DatetimeIndex:
    if len(actions) == 0:
        return pd.DatetimeIndex([])
    m = pd.Series(False, index=actions.index)
    for col in ("Dividends", "Capital Gains"):
        if col in actions.columns:
            m = m | (pd.to_numeric(actions[col], errors="coerce").fillna(0.0) > 0)
    return pd.DatetimeIndex(actions.index[m.values])


def integrity_flags(tk: str, px: pd.DataFrame, actions: pd.DataFrame, cal: pd.DatetimeIndex,
                    others_adj_ret: pd.DataFrame) -> List[Dict]:
    """A1.1-12, exactly. Returns one dict per flag; never fixes anything."""
    flags: List[Dict] = []
    raw, adj = px["raw_close"], px["adj_close"]
    rr, ar = raw.pct_change(), adj.pct_change()
    dist = distribution_dates(actions)
    # D1 — a raw-close fall with no recorded distribution, on a quiet day for the other candidates
    for t in rr.index[(rr <= D1_DROP).fillna(False).values]:
        k = int(cal.searchsorted(t))
        lo = cal[max(k - 1, 0)]
        hi = cal[min(k + 1, len(cal) - 1)] if (k < len(cal) and cal[k] == t) else cal[min(k, len(cal) - 1)]
        if len(dist) and bool(((dist >= lo) & (dist <= hi)).any()):
            continue
        row = others_adj_ret.loc[t].drop(labels=[tk], errors="ignore").dropna() if t in others_adj_ret.index \
            else pd.Series(dtype=float)
        med = float(row.median()) if len(row) >= 2 else None
        if med is None or med > D1_MEDIAN:
            flags.append({"check": "D1", "date": str(t.date()), "raw_return": float(rr.loc[t]),
                          "adj_return": float(ar.loc[t]), "n_others": int(len(row)),
                          "median_other_adj_return": med,
                          "nearest_distribution": None if len(dist) == 0 else str(
                              dist[int(np.argmin(np.abs((dist - t).days)))].date())})
    # D2 — five or more consecutive identical raw closes
    same = np.concatenate([[False], np.isclose(raw.values[1:], raw.values[:-1], rtol=0.0, atol=1e-12)])
    for start, length in _runs(same):
        if length + 1 >= D2_RUN:
            flags.append({"check": "D2", "date": str(raw.index[start - 1].date()),
                          "end": str(raw.index[start + length - 1].date()), "identical_closes": int(length + 1),
                          "raw_close": float(raw.iloc[start])})
    # D3 — more than five consecutive equity-calendar days without a price inside the span
    span = cal[(cal >= px.index[0]) & (cal <= px.index[-1])]
    miss = ~span.isin(px.index)
    for start, length in _runs(np.asarray(miss)):
        if length > D3_GAP:
            flags.append({"check": "D3", "date": str(span[start].date()),
                          "end": str(span[start + length - 1].date()), "missing_days": int(length)})
    # D4 — an implausible one-day Adj Close move
    for t in ar.index[(ar.abs() > D4_MOVE).fillna(False).values]:
        flags.append({"check": "D4", "date": str(t.date()), "adj_return": float(ar.loc[t]),
                      "raw_return": float(rr.loc[t])})
    return flags


def cmd_integrity() -> int:
    """D1-D4 on every candidate with prices. An unruled flag on a candidate HALTS (exit 2)."""
    _require_frozen()
    man = verify_snapshot()
    cal = equity_calendar()
    cands = have_prices(man)
    px = {tk: load_px(tk) for tk in cands}
    adj_ret = pd.DataFrame({tk: p["adj_close"].pct_change() for tk, p in px.items()})
    rulings = json.loads(RULINGS.read_text()) if RULINGS.exists() else {}
    out: Dict[str, Dict] = {"candidates": {}, "anchors": {}}
    unruled = 0
    for tk in cands:
        fl = integrity_flags(tk, px[tk], load_actions(tk), cal, adj_ret)
        for f in fl:
            f["ruling"] = rulings.get(f"{tk}|{f['check']}|{f['date']}")
            unruled += f["ruling"] is None
        off_cal = int((~px[tk].index.isin(cal)).sum())
        out["candidates"][tk] = {"rows": int(len(px[tk])), "first": str(px[tk].index[0].date()),
                                 "last": str(px[tk].index[-1].date()), "price_dates_off_calendar": off_cal,
                                 "n_distributions_in_actions": int(len(distribution_dates(load_actions(tk)))),
                                 "flags": fl}
        print(f"  {tk}: {len(fl)} flag(s) {[(f['check'], f['date']) for f in fl][:12]}")
    for tk in ANCHORS:
        if f"yf_{tk}.csv" not in man["files"]:
            out["anchors"][tk] = {"missing": True}
            continue
        p = load_px(tk)
        fl = integrity_flags(tk, p, load_actions(tk), cal, adj_ret)
        out["anchors"][tk] = {"rows": int(len(p)), "first": str(p.index[0].date()),
                              "last": str(p.index[-1].date()), "flags": fl}
        print(f"  anchor {tk}: {len(fl)} flag(s) {[(f['check'], f['date']) for f in fl][:12]}")
    out["unruled_candidate_flags"] = int(unruled)
    out["halt"] = bool(unruled > 0)
    b5.write_json(INTEGRITY, out)
    print(f"integrity written: {INTEGRITY}; unruled candidate flags: {unruled}")
    return 2 if unruled else 0


# --------------------------------------------------------------------------- BTOP50 (R-8, A1.1-13)
BTOP_HOST = "barclayhedge.com"
BTOP_MAX_GETS = 4
BTOP_LOG = BTOP_DIR / "REQUESTS.json"


def cmd_btop50_get(url: str, name: str) -> int:
    """One GET to barclayhedge.com with a generic client name and no contact detail; the response
    (or the refusal) is stored raw. At most four requests in total, each logged. No mirror."""
    import urllib.error
    import urllib.parse
    import urllib.request
    host = urllib.parse.urlparse(url).netloc.lower()
    if not (host == BTOP_HOST or host.endswith("." + BTOP_HOST)):
        raise T398Halt(f"{url}: only {BTOP_HOST} may be read (R-8: no mirror)")
    BTOP_DIR.mkdir(parents=True, exist_ok=True)
    log = json.loads(BTOP_LOG.read_text()) if BTOP_LOG.exists() else {"requests": []}
    if len(log["requests"]) >= BTOP_MAX_GETS:
        raise T398Halt(f"the {BTOP_MAX_GETS}-request budget for {BTOP_HOST} is spent (A1.1-13)")
    rec: Dict = {"url": url, "name": name, "requested_utc": _now()}
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research-script)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            rec.update({"status": int(resp.status), "final_url": resp.geturl(),
                        "content_type": resp.headers.get("Content-Type")})
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        rec.update({"status": int(exc.code), "error": f"HTTPError: {exc.reason}"})
    except (OSError, ValueError) as exc:
        body = b""
        rec.update({"status": None, "error": f"{type(exc).__name__}: {exc}"})
    p = BTOP_DIR / f"{len(log['requests']) + 1}_{name}.raw"
    p.write_bytes(body)
    rec.update({"file": p.name, "bytes": len(body), "md5": b5.md5_file(p)})
    log["requests"].append(rec)
    b5.write_json(BTOP_LOG, log)
    print(json.dumps(rec, indent=1))
    return 0


# --------------------------------------------------------------------------- CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("meta", "meta-table", "fetch", "integrity"):
        sp.add_parser(name)
    bp = sp.add_parser("btop50-get")
    bp.add_argument("--url", required=True)
    bp.add_argument("--name", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "btop50-get":
        return cmd_btop50_get(a.url, a.name)
    if a.cmd == "meta":
        return cmd_meta()
    if a.cmd == "meta-table":
        return cmd_meta_table()
    if a.cmd == "fetch":
        return cmd_fetch()
    if a.cmd == "integrity":
        return cmd_integrity()
    raise T398Halt(f"unknown command {a.cmd}")


if __name__ == "__main__":
    sys.exit(main())
