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
# Amendment 3, ruling 2 (BEFORE any return was computed; AGAINST the arm): AQMIX is grossed up by
# 1.25 % ("from memory, unverified") in the decision cell; Yahoo's 3.09 % capped at 2.00 % is S7.
AQMIX_ER_AS_WRITTEN = 0.0200
MEMBERSHIP_FROZEN: Optional[Dict[str, Dict]] = {
    "RYMFX": {"rule_b": True, "er": 0.0199, "er_source": "metadata"},
    "AQMIX": {"rule_b": True, "er": 0.0125, "er_source": "from memory, unverified (amendment 3, ruling 2)"},
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


RULING_TEXT = "accepted as-is (amendment 3, ruling 1)"


def cmd_record_rulings() -> int:
    """Amendment 3, ruling 1: the director accepted every flag as-is. One entry per flag in the
    integrity file; refuses to overwrite. No price file is touched."""
    if RULINGS.exists():
        raise T398Halt(f"{RULINGS} already exists; rulings are recorded once")
    integ = json.loads(INTEGRITY.read_text())
    out = {f"{tk}|{f['check']}|{f['date']}": RULING_TEXT
           for tk, c in integ["candidates"].items() for f in c["flags"]}
    b5.write_json(RULINGS, out)
    print(f"{len(out)} rulings recorded: {RULINGS}")
    return 0


# --------------------------------------------------------------------------- S3: the screener call
SCREEN_DIR = OUT / "screen"
SCREEN_FILE = SCREEN_DIR / "response.json"


def cmd_screen() -> int:
    """S3 (A1.1-10): ONE yfinance fund-screen call on the category; the response is stored raw.
    A failure is recorded verbatim and S3 is then 'not run'. Runs once."""
    if SCREEN_FILE.exists():
        raise T398Halt(f"{SCREEN_FILE} exists; the screener call is made once")
    import yfinance as yf
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    rec: Dict = {"requested_utc": _now(), "yfinance_version": yf.__version__,
                 "query": f"FundQuery('eq', ['categoryname', {ELIGIBLE_CATEGORY!r}]), size=250"}
    try:
        resp = yf.screen(yf.FundQuery("eq", ["categoryname", ELIGIBLE_CATEGORY]), size=250)
        rec["response"] = _plain(resp)
    except Exception as exc:  # noqa: BLE001 — the provider's reason is kept verbatim
        rec["error"] = f"{type(exc).__name__}: {exc}"
    SCREEN_FILE.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    quotes = (rec.get("response") or {}).get("quotes") or []
    print(f"screen: error={rec.get('error')} quotes={len(quotes)} total={(rec.get('response') or {}).get('total')}")
    return 0


# --------------------------------------------------------------------------- the panel
def financing_base() -> pd.Series:
    """B-5 §5.1 unchanged: the H.15 3-month bill (money-market-converted) to 2018-04-02, SOFR from
    2018-04-03, parsed from the md5-pinned byte copies with B-5's own parsers."""
    bill, _ = b5.parse_h15_bill(INPUTS / "frb_h15_all_sdmx.zip")
    sofr = b5.parse_nyfed_sofr(INPUTS / "nyfed_sofr.csv")
    d = bill[bill.index < b5.SOFR_START]
    mm = pd.Series(b5.mm_from_discount(d.values), index=d.index)
    so = sofr[sofr.index >= b5.SOFR_START]
    if so.index.min() != b5.SOFR_START:
        raise T398Halt(f"SOFR does not start {b5.SOFR_START.date()} (starts {so.index.min()})")
    return pd.concat([mm, so]).sort_index()


def member_returns(adj: pd.Series, cal: pd.DatetimeIndex) -> Tuple[pd.Series, pd.Timestamp, pd.Timestamp, int]:
    """A1.1-4/5: Adj Close on the equity calendar from first to last price, forward-filled inside;
    the fund enters on the first calendar day of the month after the month of its first price."""
    on = adj[adj.index.isin(cal)]
    dropped = int(len(adj) - len(on))
    if len(on) < 2:
        raise T398Halt("a member has fewer than two prices on the equity calendar")
    span = cal[(cal >= on.index[0]) & (cal <= on.index[-1])]
    ret = on.reindex(span).ffill().pct_change()
    m1 = on.index[0].to_period("M") + 1
    after = span[span.to_period("M") >= m1]
    if len(after) == 0:
        raise T398Halt("a member has no full month after its first price")
    entry = after[0]
    return ret.loc[entry:], entry, span[-1], dropped


class Panel:
    """Everything the measurement reads, built once from the md5-verified snapshot."""

    def __init__(self) -> None:
        self.man = verify_snapshot()
        frozen = _require_frozen()
        self.base = financing_base()
        self.sub = b5.Substrate(self.base)
        cal = self.sub.px2.index
        self.cal = pd.DatetimeIndex(cal[cal <= WINDOW_END])
        fin_cal = self.cal[self.cal >= pd.Timestamp("2006-12-01")]
        r, dcal = b5.financing_arrays(fin_cal, self.base)
        self.c = pd.Series(r * dcal / 360.0, index=fin_cal[1:])          # cash accrual per calendar day
        self.fin_gap = b5.fin_gap_check(self.base, pd.Timestamp("2007-01-01"), WINDOW_END)
        self.er: Dict[str, float] = {}
        self.ret: Dict[str, pd.Series] = {}
        self.table: Dict[str, Dict] = {}
        for tk in CANDIDATES:
            row: Dict = {"rule_a": f"yf_{tk}.csv" in self.man["files"], "rule_b": bool(frozen[tk]["rule_b"])}
            if not row["rule_a"]:
                row.update({"member": False, "why_out": "rule (a): the provider returned no prices"})
                self.table[tk] = row
                continue
            px = load_px(tk)
            row["first_price"] = str(px.index[0].date())
            row["last_price"] = str(px.index[-1].date())
            row["rule_c"] = bool(px.index[0] <= LAST_FIRST_PRICE)
            if not (row["rule_b"] and row["rule_c"]):
                row.update({"member": False, "why_out": "rule (b) or (c)"})
                self.table[tk] = row
                continue
            er = frozen[tk].get("er")
            if er is None or not np.isfinite(er):
                raise T398Halt(f"{tk}: no ER (neither metadata nor fallback)")
            ret, entry, last, dropped = member_returns(px["adj_close"], self.cal)
            if not np.isfinite(ret.values).all():
                raise T398Halt(f"{tk}: non-finite member return")
            self.er[tk] = float(er)
            self.ret[tk] = ret
            row.update({"member": True, "entry": str(entry.date()), "exit": str(last.date()),
                        "er": float(er), "er_source": frozen[tk]["er_source"],
                        "price_dates_off_calendar": dropped, "flag": CANDIDATES[tk]["flag"]})
            self.table[tk] = row
        self.members = list(self.ret)

    def excess(self, tk: str, er: Optional[float] = None, gross_up: bool = True) -> pd.Series:
        """§4.1: x_f = r_f − c + ER_f/252 (cash subtracted ONCE; the fund's own fee added back)."""
        r = self.ret[tk]
        c = self.c.reindex(r.index)
        if c.isna().any():
            raise T398Halt(f"{tk}: cash accrual missing on a member day")
        add = (self.er[tk] if er is None else er) / TD if gross_up else 0.0
        return r - c + add

    def composite(self, funds: Optional[Sequence[str]] = None, gross_up: bool = True,
                  er_override: Optional[Dict[str, float]] = None) -> Tuple[pd.Series, pd.Series]:
        """Equal-weight mean of member excess returns per equity-calendar day, and the member count."""
        funds = self.members if funds is None else [f for f in funds if f in self.ret]
        ov = er_override or {}
        frame = pd.DataFrame({tk: self.excess(tk, ov.get(tk), gross_up) for tk in funds})
        return frame.mean(axis=1, skipna=True), frame.notna().sum(axis=1)

    def window(self, x: pd.Series, count: pd.Series, k: int, start: Optional[pd.Timestamp] = None,
               end: pd.Timestamp = WINDOW_END) -> Dict:
        ok = count[count >= k]
        if len(ok) == 0:
            raise T398Halt(f"the composite never has {k} members")
        start = ok.index[0] if start is None else max(start, ok.index[0])
        seg = count.loc[start:end]
        if (seg < k).any():
            raise T398Halt(f"fewer than {k} members on {int((seg < k).sum())} day(s) of {start.date()}..{end.date()}")
        w = self.sub.window(str(start.date()), str(end.date()), gold=False)
        if w["dates"].max() > WINDOW_END:
            raise T398Halt("a window date is inside the 2026 holdout")
        xw = x.reindex(w["dates"])
        if xw.isna().any() or not np.isfinite(xw.values).all():
            raise T398Halt("the composite is incomplete inside the window")
        w["x"] = xw.values
        w["n_members"] = count.reindex(w["dates"]).values.astype(int)
        w["years"] = float((w["dates"][-1] - w["base_date"]).days / 365.25)
        if not np.allclose(equity_sleeve(w["e"]), w["bench"], rtol=0.0, atol=1e-15):
            raise T398Halt("the equity sleeve is not T-311's buyhold_equity")
        return w


# --------------------------------------------------------------------------- the stacked return (§5)
def equity_sleeve(e: np.ndarray) -> np.ndarray:
    return e - ER_E / TD


def stacked_sleeve(e: np.ndarray, x: np.ndarray, dcal: np.ndarray, s: float, h_surv: float,
                   er_s: float = ER_S) -> np.ndarray:
    """R^S = e + (x − h_surv/252) − s·Δcal/360 − ER_S/252. x is already an EXCESS return, so no cash
    term appears here: the stack's collateral is the equity, and cash is not earned twice (§5.2)."""
    return e + (x - h_surv / TD) - s * dcal / 360.0 - er_s / TD


def arm_returns(w: Dict, weight: float, s: float = S_H1, h_surv: float = H_SURV,
                x: Optional[np.ndarray] = None) -> np.ndarray:
    """+100 %: the stacked sleeve. +50 % / +25 %: two drifting sleeves reset at each month-end,
    5 bp per traded dollar (A1.1-6)."""
    rs = stacked_sleeve(w["e"], w["x"] if x is None else x, w["dcal"], s, h_surv)
    if weight >= 1.0:
        return rs
    rets = np.column_stack([equity_sleeve(w["e"]), rs])
    tgt = np.tile([1.0 - weight, weight], (len(rets), 1))
    rp, cost = b5.drifting_portfolio_init(rets, np.array([1.0 - weight, weight]), tgt,
                                          b5.month_end_flags(w["dates"]))
    return b5.apply_cost(rp, cost)


# --------------------------------------------------------------------------- statistics
def honest_n() -> Dict:
    from core.measurement.mbl_gate import expected_max_normal
    hn = b5.honest_n()
    hn["n_eff_t391_plus1"] = N_EFF_T391_PLUS1
    hn["e_max_t391_plus1"] = float(expected_max_normal(N_EFF_T391_PLUS1))
    return hn


def mbl_line(ir: float, years: float, hn: Dict) -> Dict:
    a = hn["e_max_plus1"] / math.sqrt(years)
    b = hn["e_max_t391_plus1"] / math.sqrt(years)
    return {"ir": ir, "years": years, "ir_needed_neff_gate_plus1": a, "ir_needed_neff_372": b,
            "clears_gate_n": bool(ir >= a), "clears_n_372": bool(ir >= b)}


def _per_year(st: Dict, years: float) -> Dict:
    st["per_year"] = {k: st[k] / years for k in ("point", "ci_low", "ci_high", "mean")}
    return st


def cell(R: np.ndarray, bench: np.ndarray, dates: pd.DatetimeIndex, base_date: pd.Timestamp,
         boot: b5.Boot, hn: Dict, periods: int = TD, sortino: bool = True) -> Dict:
    """One arm on one window: Δ log wealth with the three bootstraps, wealth stats, IR, MBL."""
    d = b5.log_diff(R, bench)
    n = len(d)
    years = float((dates[-1] - base_date).days / 365.25) if periods == TD else n / 12.0
    blocks = (BLOCK_DAILY, b5.auto_block(n), SENS2_DAILY) if periods == TD else \
        (BLOCK_MONTHLY, b5.auto_block(n), SENS2_MONTHLY)
    prim, s1, s2 = (_per_year(boot.stat(d, L), years) for L in blocks)
    ir = b5.ir_of(d, periods)
    out = {"n": n, "years": years, "dlogTW": prim, "dlogTW_sens_auto": s1, "dlogTW_sens_long": s2,
           "ir": ir, "mbl": mbl_line(ir, years, hn), "_d": d, "_R": R}
    if periods == TD:
        out["arm"] = b5.wealth_stats(R, dates, base_date, periods)
    if sortino:
        out["sortino"] = b5.sortino_ci(R, periods)
    return out


def curve(w: Dict, weight: float, boot: b5.Boot, h_surv: float = H_SURV) -> Dict:
    """§8.5: Δ per year at each spread 0..400 bp with the SAME draws (monotone by construction)."""
    pts, lo, hi = [], [], []
    for sbp in SPREADS_BP:
        d = b5.log_diff(arm_returns(w, weight, s=sbp / 1e4, h_surv=h_surv), w["bench"])
        st = boot.stat(d, BLOCK_DAILY)
        pts.append(st["point"] / w["years"])
        lo.append(st["ci_low"] / w["years"])
        hi.append(st["ci_high"] / w["years"])
    return {"spreads_bp": SPREADS_BP, "point_per_year": pts, "ci_low_per_year": lo, "ci_high_per_year": hi,
            "s_star_ci": b5.crossing(SPREADS_BP, lo), "s_star_point": b5.crossing(SPREADS_BP, pts)}


# --------------------------------------------------------------------------- §8.4 what must be sat through
def worst_rolling(d: np.ndarray, dates: pd.DatetimeIndex, win: int = 756) -> Optional[Dict]:
    if len(d) < win:
        return None
    cs = np.concatenate([[0.0], np.cumsum(d)])
    roll = cs[win:] - cs[:-win]
    i = int(np.argmin(roll))
    return {"window_days": win, "sum_d": float(roll[i]), "relative_wealth_pct": float(np.expm1(roll[i]) * 100.0),
            "start": str(dates[i].date()), "end": str(dates[i + win - 1].date())}


def drought(d: np.ndarray, dates: pd.DatetimeIndex) -> Dict:
    """Longest stretch with cumulative Σd below its running maximum, and the deepest point below."""
    cum = np.cumsum(d)
    runmax = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    below = cum < runmax - 1e-15
    runs = _runs(below)
    gap = cum - runmax
    j = int(np.argmin(gap))
    out: Dict = {"deepest_sum_d": float(gap[j]), "deepest_relative_wealth_pct": float(np.expm1(gap[j]) * 100.0),
                 "deepest_date": str(dates[j].date()), "below_peak_at_window_end": bool(below[-1])}
    if runs:
        s, ln = max(runs, key=lambda r: r[1])
        out.update({"longest_days": int(ln), "longest_years": float(ln / TD),
                    "longest_start": str(dates[s].date()), "longest_end": str(dates[s + ln - 1].date())})
    else:
        out.update({"longest_days": 0, "longest_years": 0.0})
    return out


def span_sum(d: np.ndarray, dates: pd.DatetimeIndex, a: str, b: str) -> Dict:
    m = np.asarray((dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)))
    n = int(m.sum())
    if n == 0:
        return {"n": 0}
    s = float(d[m].sum())
    return {"n": n, "from": str(dates[m][0].date()), "to": str(dates[m][-1].date()), "sum_d": s,
            "relative_wealth_pct": float(np.expm1(s) * 100.0), "per_year": float(s / n * TD)}


def find_episodes(bench: np.ndarray, depth: float = EPISODE_DEPTH) -> List[Tuple[int, int, float]]:
    """A1.1-9: stretches between successive all-time highs of the benchmark's wealth whose deepest
    point is at least `depth` below the first. Returns (first_return_index, last_return_index,
    depth): the days run from the day after the high to the day of the low (inclusive)."""
    W = np.concatenate([[1.0], np.cumprod(1.0 + bench)])
    out: List[Tuple[int, int, float]] = []
    peak = 0

    def close(lo: int, hi: int) -> None:      # wealth indices lo+1 .. hi-1 lie strictly inside
        if hi - lo <= 1:
            return
        seg = W[lo + 1:hi]
        j = lo + 1 + int(np.argmin(seg))
        dep = float(W[j] / W[lo] - 1.0)
        if dep <= depth:
            out.append((lo, j - 1, dep))       # return k moves wealth index k -> k+1

    for i in range(1, len(W)):
        if W[i] >= W[peak]:
            close(peak, i)
            peak = i
    close(peak, len(W))
    return out


def _corr(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    if len(a) < 3:
        return None
    sa, sb = float(np.std(a, ddof=1)), float(np.std(b, ddof=1))
    if not (np.isfinite(sa) and np.isfinite(sb)) or sa < 1e-12 or sb < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _maxdd(r: np.ndarray) -> float:
    wl = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    return float((wl / np.maximum.accumulate(wl) - 1.0).min())


def paired_corr_boot(a: np.ndarray, b: np.ndarray, L: int = BLOCK_DAILY) -> Dict:
    """Pearson correlation with a PAIRED moving-block bootstrap: both series are drawn at the same
    indices, so the dependence being measured survives the resampling."""
    n = len(a)
    point = _corr(a, b)
    if point is None or n < 2 * L:
        return {"n": int(n), "corr": point, "note": "too short for an interval"}
    Le = max(1, min(L, n))
    S = b5.mbb_starts(n, Le)
    off = np.arange(Le)
    samples = np.empty(S.shape[0])
    for i in range(S.shape[0]):
        idx = (S[i][:, None] + off[None, :]).ravel()[:n]
        c = _corr(a[idx], b[idx])
        samples[i] = np.nan if c is None else c
    ok = samples[np.isfinite(samples)]
    return {"n": int(n), "corr": point, "ci_low": float(np.percentile(ok, 2.5)),
            "ci_high": float(np.percentile(ok, 97.5)), "block_length": int(Le), "n_iterations": int(len(ok))}


def episode_table(w: Dict, R100: np.ndarray) -> Tuple[List[Dict], Dict]:
    eps = find_episodes(w["bench"])
    rows: List[Dict] = []
    pe: List[np.ndarray] = []
    px: List[np.ndarray] = []
    mask = np.zeros(len(w["e"]), dtype=bool)
    for a, b, dep in eps:
        sl = slice(a, b + 1)
        e, x = w["e"][sl], w["x"][sl]
        mask[sl] = True
        m = len(e) // 5
        c5 = None
        if m >= 6:
            c5 = _corr(e[:m * 5].reshape(m, 5).sum(axis=1), x[:m * 5].reshape(m, 5).sum(axis=1))
        rows.append({"peak": str((w["dates"][a - 1] if a > 0 else w["base_date"]).date()),
                     "trough": str(w["dates"][b].date()), "days": int(len(e)), "bench_depth": dep,
                     "corr_daily": _corr(e, x), "corr_5day": c5, "n_5day": int(m),
                     "composite_excess_return": float(np.prod(1.0 + x) - 1.0),
                     "bench_return": float(np.prod(1.0 + w["bench"][sl]) - 1.0),
                     "arm100_return": float(np.prod(1.0 + R100[sl]) - 1.0),
                     "bench_maxdd": _maxdd(w["bench"][sl]), "arm100_maxdd": _maxdd(R100[sl])})
        pe.append(e)
        px.append(x)
    pooled: Dict = {"n_episodes": len(eps), "bar_t316": T316_CORR_BAR}
    if eps:
        pooled["episode_days"] = paired_corr_boot(np.concatenate(pe), np.concatenate(px))
        pooled["other_days"] = {"n": int((~mask).sum()), "corr": _corr(w["e"][~mask], w["x"][~mask])}
    pooled["all_days"] = {"n": int(len(mask)), "corr": _corr(w["e"], w["x"])}
    pooled["episodes_above_bar_daily"] = int(sum(1 for r in rows if r["corr_daily"] is not None
                                                 and r["corr_daily"] > T316_CORR_BAR))
    return rows, pooled


def accumulation(R: np.ndarray, dates: pd.DatetimeIndex, start: float = 10000.0, add: float = 5000.0) -> Dict:
    """A1.1-14: $10k at the base date; $5k at the close before the first trading day of each later year."""
    wealth, year, paid = start, int(dates[0].year), start
    for t in range(len(R)):
        if int(dates[t].year) != year:
            wealth += add
            paid += add
            year = int(dates[t].year)
        wealth *= 1.0 + R[t]
    return {"terminal_dollars": float(wealth), "contributed_dollars": float(paid)}


# --------------------------------------------------------------------------- level 3 (AQR) and h_L
AQR_OLD = ROOT / "data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx"


def load_aqr(p: Path) -> pd.Series:
    d = pd.read_excel(p, "TSMOM Factors", header=None)
    t = d.iloc[18:, :2].dropna()
    s = pd.Series(t.iloc[:, 1].astype(float).values, index=pd.to_datetime(t.iloc[:, 0]).dt.to_period("M"))
    if s.index.duplicated().any():
        raise T398Halt("AQR months duplicated")
    return s.sort_index()


def monthly_block(w: Dict, boot: b5.Boot, hn: Dict) -> Dict:
    """A1.1-8: the AQR arm on the months of the window, the composite's monthly excess, h_L, V3."""
    dates = w["dates"]
    months_all = dates.to_period("M")
    full = [m for m in months_all.unique()
            if m.to_timestamp(how="start") >= w["base_date"] and m <= WINDOW_END.to_period("M")]
    e_m = b5.to_monthly(pd.Series(w["e"], index=dates)).reindex(full)
    b_m = b5.to_monthly(pd.Series(w["bench"], index=dates)).reindex(full)
    x_m = b5.to_monthly(pd.Series(w["x"], index=dates)).reindex(full)
    tau = load_aqr(INPUTS / "aqr_tsmom_monthly_t296.xlsx").reindex(full)
    for name, v in (("equity", e_m), ("bench", b_m), ("composite", x_m), ("aqr", tau)):
        if v.isna().any() or not np.isfinite(v.values).all():
            raise T398Halt(f"monthly {name} incomplete on the window's months")
    out: Dict = {"months": [str(full[0]), str(full[-1])], "n_months": len(full)}
    arms = {}
    for wt in (1.00, 0.50, 0.25):
        R = b5.arm_iv_monthly(e_m.values, tau.values, wt, S_H1)
        c = cell(R, b_m.values, dates, w["base_date"], boot, hn, periods=12, sortino=False)
        arms[f"w{int(wt * 100)}"] = {k: v for k, v in c.items() if not k.startswith("_")}
    out["aqr_arms"] = arms
    diff = tau.values - x_m.values
    n = len(diff)
    hl = {}
    for label, L in (("primary_1m", BLOCK_MONTHLY), ("auto", b5.auto_block(n)), ("12m", SENS2_MONTHLY)):
        hl[label] = boot.stat(diff, L, scale=12.0 / n)
    out["h_L"] = hl
    out["aqr_excess_per_year"] = float(tau.mean() * 12.0)
    out["composite_gross_excess_per_year_monthly"] = float(x_m.mean() * 12.0)
    out["V3_corr_composite_aqr"] = _corr(x_m.values, tau.values)
    out["tracking_error_aqr_minus_composite"] = float(np.std(diff, ddof=1) * math.sqrt(12.0))
    out["_x_m"] = x_m
    out["_tau"] = tau
    return out


def transport_reading(hl: Dict) -> Dict:
    """§10, pre-named. Closing rows read h_L alone; the surviving row reads h_L + h_surv."""
    lo, hi = hl["ci_low"] * 100.0, hl["ci_high"] * 100.0
    surv_hi = hi + H_SURV * 100.0
    if lo > 6.56:
        r = "ci_low of h_L > 6.56: B-5's AQR arm no longer clears on either window — CLOSED on the deep window too"
    elif lo > 2.00:
        r = "ci_low of h_L > 2.00: the 2000-2025 AQR clearance is void"
    elif surv_hi < 2.00:
        r = "ci_high of h_L + h_surv < 2.00: both AQR windows survive a live-cost haircut (exploratory only)"
    else:
        r = "the haircut is still not pinned"
    return {"h_L_pct": hl["point"] * 100.0, "ci_low_pct": lo, "ci_high_pct": hi,
            "break_evens_pct": {"W-00m": 2.00, "W-85": 6.56, "W-85_mbl_372": 4.46}, "reading": r}


# --------------------------------------------------------------------------- gates and validations
def _monthly(s: pd.Series) -> pd.Series:
    return b5.to_monthly(s.dropna())


def gates_payload(panel: Panel) -> Dict:
    boot = b5.Boot()
    x, cnt = panel.composite()
    w = panel.window(x, cnt, MIN_MEMBERS)
    integ = json.loads(INTEGRITY.read_text()) if INTEGRITY.exists() else None
    e3 = bool(integ is not None and integ.get("unruled_candidate_flags") == 0)
    # E2 / V2 — composite without the fund against the fund, monthly gross excess, full member months
    v2: Dict = {}
    for tk in ("DBMF", "KMLM", "CTA"):
        if tk not in panel.ret:
            continue
        xo, _ = panel.composite([m for m in panel.members if m != tk])
        f_m = _monthly(panel.excess(tk))
        o_m = _monthly(xo).reindex(f_m.index)
        j = pd.concat({"f": f_m, "o": o_m}, axis=1).dropna()
        v2[tk] = {"months": [str(j.index[0]), str(j.index[-1])], "n": int(len(j)),
                  "corr": _corr(j["f"].values, j["o"].values),
                  "mean_diff_per_year_fund_minus_composite": float((j["f"] - j["o"]).mean() * 12.0)}
    x_m = _monthly(x.loc[w["dates"][0]:])
    for tk, eq, share in (("BLNDX", "VT", 0.5), ("MAFIX", "SPY", 0.5)):
        if f"yf_{tk}.csv" not in panel.man["files"]:
            v2[tk] = {"missing": True}
            continue
        a = load_px(tk)["adj_close"]
        q = load_px(eq)["adj_close"]
        m1 = a.index[0].to_period("M") + 1
        am = a.groupby(a.index.to_period("M")).last().pct_change()
        qm = q.groupby(q.index.to_period("M")).last().pct_change()
        j = pd.concat({"a": am - share * qm, "x": x_m}, axis=1).dropna()
        j = j[j.index >= m1]
        v2[tk] = {"months": [str(j.index[0]), str(j.index[-1])], "n": int(len(j)),
                  "corr_shape_only": _corr(j["a"].values, j["x"].values),
                  "equity_share_assumed_from_memory": share, "equity_proxy": eq}
    e2 = v2.get("DBMF", {}).get("corr")
    # V1 — the synthetic +100 % arm (h_surv = 0) against live RSST
    rsst = load_px("RSST")["adj_close"]
    m1 = rsst.index[0].to_period("M") + 1
    live = rsst.pct_change().dropna()
    live = live[live.index.to_period("M") >= m1]
    syn = pd.Series(arm_returns(w, 1.0, h_surv=0.0), index=w["dates"])
    j = pd.concat({"live": live, "syn": syn}, axis=1).dropna()
    dv = (np.log1p(j["live"]) - np.log1p(j["syn"])).values
    st = boot.stat(dv, BLOCK_DAILY, scale=TD / len(dv))
    v1 = {"from": str(j.index[0].date()), "to": str(j.index[-1].date()), "n": int(len(j)),
          "td_per_year": st["point"], "ci_low": st["ci_low"], "ci_high": st["ci_high"],
          "tracking_error": float(np.std(dv, ddof=1) * math.sqrt(TD)),
          "corr": _corr(j["live"].values, j["syn"].values)}
    mb = monthly_block(w, boot, honest_n())
    out = {"E1_depth": {"start": str(w["dates"][0].date()), "end": str(w["dates"][-1].date()),
                        "years": w["years"], "min_years": E1_MIN_YEARS, "pass": bool(w["years"] >= E1_MIN_YEARS)},
           "E2_composite_vs_DBMF": {"corr": e2, "min_corr": E2_MIN_CORR,
                                    "pass": bool(e2 is not None and e2 >= E2_MIN_CORR)},
           "E3_integrity": {"unruled_candidate_flags": None if integ is None else integ["unruled_candidate_flags"],
                            "pass": e3},
           "E4_md5": {"pass": True},
           "V1_synthetic_vs_RSST": v1, "V2": v2,
           "V3_corr_composite_aqr_monthly": mb["V3_corr_composite_aqr"]}
    out["evaluable"] = bool(all(out[k]["pass"] for k in ("E1_depth", "E2_composite_vs_DBMF", "E3_integrity", "E4_md5")))
    return out


def cmd_gates() -> int:
    panel = Panel()
    out = gates_payload(panel)
    b5.write_json(GATES, out)
    print(json.dumps(b5._jsonable(out), indent=1))
    return 0 if out["evaluable"] else 2


# --------------------------------------------------------------------------- smoke (never quoted)
def cmd_smoke() -> int:
    """Mechanics on the FIRST 12 months of each window. Booleans and counts only."""
    panel = Panel()
    x, cnt = panel.composite()
    out: Dict = {"note": "mechanics only — NO number here is a result and none may be quoted"}
    for name, k in (("W-L3", MIN_MEMBERS), ("W-L1", 1)):
        start = cnt[cnt >= k].index[0]
        end = start + pd.DateOffset(years=1) - pd.Timedelta(days=1)
        w = panel.window(x, cnt, k, end=pd.Timestamp(end))
        r100 = arm_returns(w, 1.0)
        r50 = arm_returns(w, 0.5)
        ident = r100 - w["bench"] - (w["x"] - H_SURV / TD - S_H1 * w["dcal"] / 360.0 - (ER_S - ER_E) / TD)
        zero = dict(w)
        zero["x"] = np.zeros(len(w["e"]))
        free = stacked_sleeve(zero["e"], zero["x"], zero["dcal"], 0.0, 0.0, er_s=ER_E)
        # hand check of the cash accrual on the first five days, straight from the base series
        hand = []
        for t in w["dates"][:5]:
            prev = panel.cal[panel.cal.get_loc(t) - 1]
            rate = float(panel.base[panel.base.index <= prev].iloc[-1])
            hand.append(rate * (t - prev).days / 360.0)
        ch = np.allclose(hand, panel.c.reindex(w["dates"][:5]).values, rtol=0.0, atol=1e-15)
        out[name] = {"start": str(w["dates"][0].date()), "end": str(w["dates"][-1].date()),
                     "n_days": int(len(w["e"])), "all_finite": bool(np.isfinite(r100).all() and np.isfinite(r50).all()),
                     "identity_100_max_abs_err": float(np.max(np.abs(ident))),
                     "identity_100_ok": bool(np.max(np.abs(ident)) < 1e-15),
                     "zero_overlay_free_stack_equals_bench": bool(np.allclose(free, w["bench"], rtol=0.0, atol=1e-15)),
                     "month_end_resets": int(b5.month_end_flags(w["dates"]).sum()),
                     "two_sleeve_differs_from_sleeves": bool(not np.allclose(r50, r100)),
                     "cash_accrual_hand_check_ok": bool(ch),
                     "members_min": int(w["n_members"].min()), "members_max": int(w["n_members"].max())}
        if not (out[name]["all_finite"] and out[name]["identity_100_ok"] and ch
                and out[name]["zero_overlay_free_stack_equals_bench"]):
            b5.write_json(SMOKE, out)
            raise T398Halt(f"smoke failed on {name}: {out[name]}")
    b5.write_json(SMOKE, out)
    print(json.dumps(out, indent=1))
    return 0


# --------------------------------------------------------------------------- the run
def _public(c: Dict) -> Dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


def _compact(c: Dict) -> Dict:
    return {"years": c["years"], "n": c["n"],
            "point_per_year": c["dlogTW"]["per_year"]["point"],
            "ci_low_per_year": c["dlogTW"]["per_year"]["ci_low"],
            "ci_high_per_year": c["dlogTW"]["per_year"]["ci_high"],
            "ci_low_per_year_auto": c["dlogTW_sens_auto"]["per_year"]["ci_low"],
            "ci_low_per_year_252": c["dlogTW_sens_long"]["per_year"]["ci_low"],
            "ci_high_per_year_252": c["dlogTW_sens_long"]["per_year"]["ci_high"],
            "ir": c["ir"], "max_dd": c["arm"]["max_dd"], "cagr": c["arm"]["cagr"]}


def composite_stats(panel: Panel, w: Dict, funds: Optional[Sequence[str]] = None) -> Dict:
    xn, _ = panel.composite(funds, gross_up=False)
    xn = xn.reindex(w["dates"]).values
    xg = w["x"]
    return {"members_at_start": int(w["n_members"][0]), "members_max": int(w["n_members"].max()),
            "members_at_end": int(w["n_members"][-1]),
            "members_by_year": {str(y): int(w["n_members"][np.asarray(w["dates"].year == y)].max())
                                for y in sorted(set(w["dates"].year))},
            "vol_ann": float(np.std(xg, ddof=1) * math.sqrt(TD)),
            "net_excess_per_year": float(np.mean(xn) * TD),
            "gross_excess_per_year": float(np.mean(xg) * TD),
            "net_excess_sharpe": float(np.mean(xn) / b5._guard_std(float(np.std(xn, ddof=1)), "composite") * math.sqrt(TD)),
            "corr_with_equity_daily": _corr(w["e"], xg),
            "max_dd_of_gross_excess": _maxdd(xg)}


def window_block(panel: Panel, w: Dict, boot: b5.Boot, hn: Dict, full: bool) -> Dict:
    """All arms on one window. `full` adds the curve, §8.4, the regime split and the scorecard."""
    out: Dict = {"start": str(w["dates"][0].date()), "end": str(w["dates"][-1].date()),
                 "base_date": str(w["base_date"].date()), "n_days": int(len(w["e"])), "years": w["years"],
                 "benchmark": b5.wealth_stats(w["bench"], w["dates"], w["base_date"], TD),
                 "benchmark_sortino": b5.sortino_ci(w["bench"], TD), "arms": {}}
    cells: Dict[str, Dict] = {}
    for wt in (1.00, 0.50, 0.25):
        key = f"w{int(wt * 100)}"
        c = cell(arm_returns(w, wt), w["bench"], w["dates"], w["base_date"], boot, hn)
        c["delta_max_dd"] = c["arm"]["max_dd"] - out["benchmark"]["max_dd"]
        cells[key] = c
        out["arms"][key] = _public(c)
        if full:
            out["arms"][key]["curve"] = curve(w, wt, boot)
    out["_cells"] = cells
    if not full:
        return out
    d100, R100 = cells["w100"]["_d"], cells["w100"]["_R"]
    sit: Dict = {}
    for key in ("w100", "w50", "w25"):
        d = cells[key]["_d"]
        sit[key] = {"worst_3yr": worst_rolling(d, w["dates"]), "drought": drought(d, w["dates"]),
                    "flat_decade_2011_2019": span_sum(d, w["dates"], "2011-01-03", "2019-12-31"),
                    "y2022": span_sum(d, w["dates"], "2022-01-01", "2022-12-31"),
                    "y2020_2025": span_sum(d, w["dates"], "2020-01-01", "2025-12-31")}
    out["sit_through"] = sit
    rows, pooled = episode_table(w, R100)
    out["episodes"] = rows
    out["drawdown_correlation"] = pooled
    pos, neg = b5.rho_years(w)
    yrs = w["dates"].year
    out["rho_regime"] = {"rho_pos_years": pos, "rho_nonpos_years": neg,
                         "w100_rho_pos": b5.subsample(d100, np.isin(yrs, pos), boot, BLOCK_DAILY, TD),
                         "w100_rho_nonpos": b5.subsample(d100, np.isin(yrs, neg), boot, BLOCK_DAILY, TD)}
    out["accumulation"] = {"benchmark": accumulation(w["bench"], w["dates"]),
                           **{k: accumulation(cells[k]["_R"], w["dates"]) for k in ("w100", "w50", "w25")}}
    return out


def sensitivity(panel: Panel, w3: Dict, boot: b5.Boot, hn: Dict, label: str, funds: Optional[Sequence[str]] = None,
                gross_up: bool = True, h_surv: float = H_SURV, er_override: Optional[Dict[str, float]] = None,
                x_dec: Optional[pd.Series] = None, cnt_dec: Optional[pd.Series] = None) -> Dict:
    """One sensitivity on the +100 % arm (A1.1-10). A composite with fewer than three members on
    part of W-L3 runs on the sub-window where it has three, with the decision composite beside it."""
    x, cnt = panel.composite(funds, gross_up=gross_up, er_override=er_override)
    try:
        w = panel.window(x, cnt, MIN_MEMBERS, start=w3["dates"][0])
    except T398Halt as exc:
        return {"label": label, "not_run": str(exc)}
    c = cell(arm_returns(w, 1.0, h_surv=h_surv), w["bench"], w["dates"], w["base_date"], boot, hn, sortino=False)
    out = {"label": label, "start": str(w["dates"][0].date()), "members_min": int(w["n_members"].min()),
           "members_max": int(w["n_members"].max()), "h_surv": h_surv, "gross_up": gross_up, **_compact(c)}
    if w["dates"][0] != w3["dates"][0] and x_dec is not None:
        wd = panel.window(x_dec, cnt_dec, MIN_MEMBERS, start=w["dates"][0])
        cd = cell(arm_returns(wd, 1.0), wd["bench"], wd["dates"], wd["base_date"], boot, hn, sortino=False)
        out["decision_composite_same_window"] = _compact(cd)
    return out


def b5_quoted() -> Dict:
    """Level 3: B-5's arm (iv) results, QUOTED from its results file (never re-run)."""
    p = ROOT / "data/research/b5/run_A/results.json"
    if not p.exists():
        return {"missing": True}
    m = json.loads(p.read_text())["monthly"]
    out: Dict = {"md5": b5.md5_file(p)}
    for wk in ("W-85", "W-00m", "L-19"):
        for wn in ("w50", "w25"):
            py = m[wk][wn]["dlogTW"]["per_year"]
            out[f"{wk}/{wn}"] = {"point": py["point"], "ci_low": py["ci_low"], "ci_high": py["ci_high"],
                                 "ir": m[wk][wn]["mbl"]["ir"], "role": m[wk][wn]["role"]}
    return out


def cmd_run(tag: str) -> int:
    gates = json.loads(GATES.read_text()) if GATES.exists() else None
    if gates is None or not gates.get("evaluable"):
        raise T398Halt("an evaluability gate has not passed (run `gates`); H1 is NOT EVALUABLE")
    integ = json.loads(INTEGRITY.read_text())
    if integ.get("unruled_candidate_flags") != 0:
        raise T398Halt("an integrity flag on a candidate has no recorded ruling")
    panel = Panel()
    boot = b5.Boot()
    hn = honest_n()
    x, cnt = panel.composite()
    w3 = panel.window(x, cnt, MIN_MEMBERS)
    w1 = panel.window(x, cnt, 1)
    res: Dict = {"prereg": PREREG_REF, "honest_n": hn, "membership": panel.table,
                 "windows": {}, "sensitivities": {}}
    blk3 = window_block(panel, w3, boot, hn, full=True)
    blk1 = window_block(panel, w1, boot, hn, full=False)
    dec = blk3["_cells"]["w100"]
    # A1.1-7: the replay must equal MetricsEngine on the decision cell, or HALT; ME's numbers are quoted.
    me = b5.me_sum_stat(dec["_d"], BLOCK_DAILY)
    rp = dec["dlogTW"]
    if me["n_iterations"] != N_ITER or me["block_length"] != BLOCK_DAILY:
        raise T398Halt("the primary bootstrap did not run with n = 1000 and block = 21")
    for k in ("ci_low", "ci_high", "mean"):
        if abs(me[k] - rp[k]) >= 1e-9:
            raise T398Halt(f"bootstrap replay != MetricsEngine on the decision cell ({k})")
    yrs = w3["years"]
    lo252 = dec["dlogTW_sens_long"]["per_year"]["ci_low"]
    h1 = bool(me["ci_low"] > 0)
    res["H1"] = {"cell": "+100 %, level-1 composite (14 members), ER gross-up on (AQMIX 1.25 % per amendment 3), "
                         "h_surv 1.0 %/yr, s 50 bp, ER_S 1.00 %, W-L3, 21-day MBB x1000 seed 0",
                 "window": [blk3["start"], blk3["end"]], "years": yrs,
                 "dlogTW_total": {k: me[k] for k in ("point_estimate", "ci_low", "ci_high", "mean", "p_above_zero")},
                 "per_year": {"point": me["point_estimate"] / yrs, "ci_low": me["ci_low"] / yrs,
                              "ci_high": me["ci_high"] / yrs},
                 "ci_low_per_year_252": lo252,
                 "ci_high_per_year_252": dec["dlogTW_sens_long"]["per_year"]["ci_high"],
                 "ir": dec["ir"], "mbl": dec["mbl"], "met": h1,
                 "block_fragile": bool(h1 and lo252 <= 0),
                 "verdict": ("H1 MET" if h1 else
                             ("H1 NOT MET — CLOSED (ci_high < 0)" if me["ci_high"] < 0 else
                              "H1 NOT MET — the interval straddles zero"))}
    blk3["composite"] = composite_stats(panel, w3)
    blk1["composite"] = composite_stats(panel, w1)
    mb = monthly_block(w3, boot, hn)
    res["level3"] = {k: v for k, v in mb.items() if not k.startswith("_")}
    res["level3"]["transport"] = transport_reading(mb["h_L"]["primary_1m"])
    res["level3"]["b5_quoted"] = b5_quoted()
    if AQR_OLD.exists():
        old = load_aqr(AQR_OLD)
        j = pd.concat({"new": load_aqr(INPUTS / "aqr_tsmom_monthly_t296.xlsx"), "old": old}, axis=1).dropna()
        res["level3"]["aqr_vintages"] = {
            "common_months": int(len(j)), "old_md5": b5.md5_file(AQR_OLD),
            "mean_abs_diff_monthly": float((j["new"] - j["old"]).abs().mean()),
            "mean_diff_per_year": float((j["new"] - j["old"]).mean() * 12.0),
            "corr": _corr(j["new"].values, j["old"].values),
            "months_differing_by_more_than_10bp": int(((j["new"] - j["old"]).abs() > 0.001).sum())}
    pure = [m for m in panel.members if m not in FLAGGED]
    etfs = [m for m in panel.members if m in ETF_ONLY]
    S = res["sensitivities"]
    S["S1_pure_play"] = sensitivity(panel, w3, boot, hn, "S1 pure-play (without RYMFX, WTMF, FMF, EVOIX)",
                                    funds=pure, x_dec=x, cnt_dec=cnt)
    S["S2_etfs_only"] = sensitivity(panel, w3, boot, hn, "S2 ETFs only", funds=etfs, x_dec=x, cnt_dec=cnt)
    S["S3_screener"] = screener_sensitivity(panel, w3, boot, hn)
    S["S4_double_fee"] = sensitivity(panel, w3, boot, hn, "S4 no ER gross-up (double fee)", gross_up=False)
    S["S5_no_survivorship"] = sensitivity(panel, w3, boot, hn, "S5 h_surv = 0", h_surv=0.0)
    S["S6_survivorship_2pct"] = sensitivity(panel, w3, boot, hn, "S6 h_surv = 2.0 %/yr", h_surv=0.02)
    S["S7_aqmix_er_as_written"] = sensitivity(panel, w3, boot, hn, "S7 AQMIX ER 2.00 % (Yahoo, capped; amendment 2)",
                                              er_override={"AQMIX": AQMIX_ER_AS_WRITTEN})
    S["S0_spread_zero"] = sensitivity_spread_zero(w3, boot, hn)
    blk3.pop("_cells")
    blk1.pop("_cells")
    res["windows"]["W-L3"] = blk3
    res["windows"]["W-L1"] = blk1
    res["gates"] = gates
    res["census"] = {
        "inputs_md5": {k: v["md5"] for k, v in panel.man["files"].items()},
        "substrate_md5": {k: PINNED_MD5[k] for k in ("equity_tr_daily.csv", "bond_tr_daily.csv")},
        "returned_nothing": panel.man.get("returned_nothing", {}),
        "n_members": len(panel.members), "financing_gap_max_business_days": panel.fin_gap,
        "integrity": {"flags_on_candidates": int(sum(len(c["flags"]) for c in integ["candidates"].values())),
                      "unruled": integ["unruled_candidate_flags"], "ruling": RULING_TEXT},
        "bootstrap": {"n_iterations": N_ITER, "seed": SEED, "primary_block": BLOCK_DAILY,
                      "sens_blocks": ["auto", SENS2_DAILY]},
        "window_end": str(WINDOW_END.date()), "holdout": "nothing dated 2026 is loaded into a window"}
    out_dir = OUT / f"run_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    R = {k: arm_returns(w3, wt) for k, wt in (("arm100", 1.0), ("arm50", 0.5), ("arm25", 0.25))}
    pd.DataFrame({"bench": w3["bench"], **R, "x_gross": w3["x"], "n_members": w3["n_members"]},
                 index=pd.Index(w3["dates"], name="date")).to_csv(out_dir / "returns_W-L3.csv", float_format="%.17g")
    R1 = {k: arm_returns(w1, wt) for k, wt in (("arm100", 1.0), ("arm50", 0.5), ("arm25", 0.25))}
    pd.DataFrame({"bench": w1["bench"], **R1, "x_gross": w1["x"], "n_members": w1["n_members"]},
                 index=pd.Index(w1["dates"], name="date")).to_csv(out_dir / "returns_W-L1.csv", float_format="%.17g")
    pd.DataFrame({"x_gross_m": mb["_x_m"].values, "aqr_tsmom": mb["_tau"].values},
                 index=pd.Index([str(m) for m in mb["_x_m"].index], name="month")
                 ).to_csv(out_dir / "monthly_W-L3.csv", float_format="%.17g")
    b5.write_json(out_dir / "results.json", res)
    files = sorted(p.name for p in out_dir.iterdir() if p.name != "run_manifest.json")
    b5.write_json(out_dir / "run_manifest.json", {"prereg": PREREG_REF,
                                                  "outputs_md5": {f: b5.md5_file(out_dir / f) for f in files}})
    h = res["H1"]
    print(f"H1: {h['verdict']} | point {h['per_year']['point'] * 100:+.2f} %/yr "
          f"[{h['per_year']['ci_low'] * 100:+.2f}, {h['per_year']['ci_high'] * 100:+.2f}] | IR {h['ir']:.3f} "
          f"| years {yrs:.2f}")
    print(f"written: {out_dir}")
    return 0


def sensitivity_spread_zero(w3: Dict, boot: b5.Boot, hn: Dict) -> Dict:
    """Reported (§5.1): the decision cell at s = 0 instead of 50 bp."""
    c = cell(arm_returns(w3, 1.0, s=0.0), w3["bench"], w3["dates"], w3["base_date"], boot, hn, sortino=False)
    return {"label": "decision cell at s = 0", **_compact(c)}


S3_DIR = OUT / "inputs_s3"
S3_MANIFEST = S3_DIR / "MANIFEST.json"
_CLASS_TOKENS = {"A", "C", "I", "N", "Z", "P", "R", "Y", "R5", "R6", "I-2", "I-3", "Inv", "Instl",
                 "Institutional", "Adv", "Investor", "Advisor"}


def fund_family(name: str) -> str:
    """A fund's name without its trailing share-class token (S3's 'one share class per fund')."""
    parts = (name or "").split()
    while parts and parts[-1] in _CLASS_TOKENS:
        parts = parts[:-1]
    return " ".join(parts)


def s3_selection(quotes: Sequence[Dict], decision_names: Dict[str, str]) -> Dict:
    """S3, mechanically: every fund family the screen returns that the decision composite does not
    already hold; per family the OLDEST share class (ties: lowest net ER, then symbol); rule (c)
    on Yahoo's first-trade date; rule (d) pre-named duplicates out. Metadata only."""
    held = {fund_family(n) for n in decision_names.values()}
    fam: Dict[str, List[Dict]] = {}
    for q in quotes:
        name = q.get("longName") or q.get("shortName") or ""
        ft = q.get("firstTradeDateMilliseconds")
        fam.setdefault(fund_family(name), []).append({
            "symbol": q["symbol"], "name": name, "er_pct": q.get("netExpenseRatio"),
            "first_trade": None if ft is None else pd.Timestamp(int(ft), unit="ms").normalize()})
    chosen: Dict[str, Dict] = {}
    skipped: Dict[str, str] = {}
    for f, rows in sorted(fam.items()):
        if f in held:
            skipped[f] = "already in the decision composite"
            continue
        if "HV" in f.split():
            skipped[f] = "rule (d): a re-levered copy of a program already held"
            continue
        rows = [r for r in rows if r["first_trade"] is not None]
        if not rows:
            skipped[f] = "no first-trade date"
            continue
        rows.sort(key=lambda r: (r["first_trade"], r["er_pct"] if r["er_pct"] is not None else 99.0, r["symbol"]))
        r = rows[0]
        if r["first_trade"] > LAST_FIRST_PRICE:
            skipped[f] = f"rule (c): first trade {r['first_trade'].date()}"
            continue
        er = convert_er(r["er_pct"], "percent")
        if er is None:
            skipped[f] = f"no usable ER ({r['er_pct']})"
            continue
        chosen[r["symbol"]] = {"family": f, "name": r["name"], "first_trade": str(r["first_trade"].date()),
                               "er_meta": er, "er": min(er, ER_CAP)}
    return {"chosen": chosen, "skipped": skipped}


def cmd_fetch_s3() -> int:
    """S3 only: prices for the additional fund families the one screener call returned. Once."""
    _require_frozen()
    if S3_MANIFEST.exists():
        raise T398Halt(f"{S3_MANIFEST} exists; the S3 fetch runs once")
    rec = json.loads(SCREEN_FILE.read_text())
    quotes = (rec.get("response") or {}).get("quotes") or []
    if rec.get("error") or not quotes:
        raise T398Halt("the screener call returned nothing usable; S3 is not run")
    man = verify_snapshot()
    names = {tk: (read_meta(tk)["info"].get("longName") or "") for tk in have_prices(man)}
    sel = s3_selection(quotes, names)
    import yfinance as yf
    stage = OUT / f"inputs_s3_attempt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    stage.mkdir(parents=True, exist_ok=False)
    cal = equity_calendar()
    adj_ret = pd.DataFrame({tk: load_px(tk)["adj_close"].pct_change() for tk in have_prices(man)})
    files: Dict[str, Dict] = {}
    for tk, row in sel["chosen"].items():
        df, notes = _fetch_one(tk)
        if df is None:
            row["fetched"] = False
            row["notes"] = notes
            continue
        if df.index.max() >= pd.Timestamp(YF_ASOF):
            raise T398Halt(f"{tk}: a row inside the 2026 holdout")
        p = stage / f"yf_{tk}.csv"
        df.to_csv(p, float_format="%.10g")
        try:
            act = yf.Ticker(tk).actions
            act = act.copy() if act is not None else pd.DataFrame()
            if len(act):
                act.index = pd.DatetimeIndex(act.index).tz_localize(None).normalize()
        except Exception as exc:  # noqa: BLE001 — kept verbatim; S3 is a reported sensitivity
            act = pd.DataFrame()
            notes.append(f"actions: {type(exc).__name__}: {exc}")
        fl = integrity_flags(tk, df, act, cal, adj_ret)
        row.update({"fetched": True, "first_price": str(df.index[0].date()), "last_price": str(df.index[-1].date()),
                    "notes": notes, "integrity_flags_listed_not_halting": fl})
        files[p.name] = {"md5": b5.md5_file(p), "rows": int(len(df)), "fetched_utc": _now(),
                         "call": f"fetch_yf_tr({tk!r}, {YF_START!r}, {YF_ASOF!r})"}
        print(f"  {tk} ({row['family']}): {len(df)} rows {df.index[0].date()}..{df.index[-1].date()} "
              f"flags {len(fl)}")
        time.sleep(1.0)
    b5.write_json(stage / S3_MANIFEST.name, {"files": files, **sel})
    stage.rename(S3_DIR)
    print(json.dumps({"skipped": sel["skipped"]}, indent=1))
    return 0


def screener_sensitivity(panel: Panel, w3: Dict, boot: b5.Boot, hn: Dict) -> Dict:
    """S3: the decision composite plus one share class of every additional fund family the one
    screener call returned. Recorded as not run when the call or the S3 fetch produced nothing."""
    label = "S3 screener (decision members + every other family in the category screen)"
    if not SCREEN_FILE.exists():
        return {"label": label, "not_run": "the screener call was not made"}
    rec = json.loads(SCREEN_FILE.read_text())
    if rec.get("error"):
        return {"label": label, "not_run": f"the screener call failed: {rec['error']}"}
    if not S3_MANIFEST.exists():
        return {"label": label, "not_run": "no S3 price snapshot"}
    man = json.loads(S3_MANIFEST.read_text())
    frame = {tk: panel.excess(tk) for tk in panel.members}
    added: Dict[str, Dict] = {}
    for tk, row in man["chosen"].items():
        name = f"yf_{tk}.csv"
        if not row.get("fetched") or name not in man["files"]:
            continue
        if b5.md5_file(S3_DIR / name) != man["files"][name]["md5"]:
            raise T398Halt(f"S3 file {name} md5 != its manifest")
        px = pd.read_csv(S3_DIR / name, parse_dates=["Date"], index_col="Date").sort_index().astype(float)
        if px.index.max() > WINDOW_END:
            raise T398Halt(f"{tk}: a row inside the 2026 holdout")
        if px.index[0] > LAST_FIRST_PRICE:
            continue
        ret, entry, last, _ = member_returns(px["adj_close"], panel.cal)
        frame[tk] = ret - panel.c.reindex(ret.index) + row["er"] / TD
        added[tk] = {"family": row["family"], "entry": str(entry.date()), "exit": str(last.date()), "er": row["er"],
                     "n_integrity_flags": len(row.get("integrity_flags_listed_not_halting", []))}
    if not added:
        return {"label": label, "not_run": "the screen added no fund family with prices"}
    f = pd.DataFrame(frame)
    xs, cs = f.mean(axis=1, skipna=True), f.notna().sum(axis=1)
    w = panel.window(xs, cs, MIN_MEMBERS, start=w3["dates"][0])
    c = cell(arm_returns(w, 1.0), w["bench"], w["dates"], w["base_date"], boot, hn, sortino=False)
    return {"label": label, "start": str(w["dates"][0].date()), "members_min": int(w["n_members"].min()),
            "members_max": int(w["n_members"].max()), "added": added, "skipped": man["skipped"],
            "h_surv": H_SURV, "gross_up": True, **_compact(c)}


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
    for name in ("meta", "meta-table", "fetch", "integrity", "record-rulings", "screen", "fetch-s3", "gates", "smoke"):
        sp.add_parser(name)
    bp = sp.add_parser("btop50-get")
    bp.add_argument("--url", required=True)
    bp.add_argument("--name", required=True)
    rp = sp.add_parser("run")
    rp.add_argument("--tag", required=True, choices=["A", "B"])
    a = ap.parse_args(argv)
    if a.cmd == "btop50-get":
        return cmd_btop50_get(a.url, a.name)
    if a.cmd == "record-rulings":
        return cmd_record_rulings()
    if a.cmd == "screen":
        return cmd_screen()
    if a.cmd == "fetch-s3":
        return cmd_fetch_s3()
    if a.cmd == "gates":
        return cmd_gates()
    if a.cmd == "smoke":
        return cmd_smoke()
    if a.cmd == "run":
        return cmd_run(a.tag)
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
