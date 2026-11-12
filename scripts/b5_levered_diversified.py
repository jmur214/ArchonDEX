"""T-382 (B-5) — levered diversified book vs 1x SPY under honest Roth financing.

Pre-registration FROZEN at 535a3fc; amendment 1 (director rulings + pre-data implementation
decisions) at 3dcf399: docs/Sources/prereg_b5_levered_diversified_2026-11-11.md. N_trials += 1.

Standalone harness (T-249 / T-311 pattern). Never touches BacktestController. Substrate = T-306
(`data/research/substrate_multidecade/`) read through T-311's `load_substrate` (imported, not edited).
Financing = the 3-month T-bill (= FRED DTB3, fetched from its publisher, the Fed Board's H.15 DDP;
money-market converted) to 2018-04-02, SOFR (= FRED SOFR, from the NY Fed Markets API) from
2018-04-03, + spread s. Amendment 2 (891cc3c): FRED's keyless endpoint was blocked for this client.

Subcommands (run in this order):
  fetch      one-time snapshot of every network input into data/research/b5/inputs/ + MANIFEST.json
             (REFUSES if the manifest exists)
  er-check   informational: UGL/UST expense ratios from yfinance fund data (does not alter 0.66 %)
  validate   synthetic vs live ETF (V1 gates, V2 reported) -> data/research/b5/validation.json
  smoke      the FIRST 12 months of each window, identity checks -> data/research/b5/smoke.json
  run --tag  the full measurement -> data/research/b5/run_<tag>/ (results.json + returns CSVs)

Fail-closed everywhere in the measurement path ([NN-FAIL-CLOSED]): a missing/unverifiable input,
a forward-fill run > 7 days, a financing gap > 5 business days, a NaN/inf inside a window, a gating
validation failure for a scoped arm, or a bootstrap off-spec raises B5Halt (exit 2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from scripts import deep_reverify_sleeve_t311 as t311  # noqa: E402  (import only — never edited)

# --------------------------------------------------------------------------- paths
B5 = ROOT / "data/research/b5"
INPUTS = B5 / "inputs"
MANIFEST = INPUTS / "MANIFEST.json"
VALIDATION = B5 / "validation.json"
SMOKE = B5 / "smoke.json"
AQR_SRC = ROOT / "data/research/aqr_tsmom_monthly_t296.xlsx"
SUB = ROOT / "data/research/substrate_multidecade"

# --------------------------------------------------------------------------- frozen inputs (prereg §7)
SUBSTRATE_MD5 = {
    "equity_tr_daily.csv": "c2030019b8846792b5f8e3d18421c905",
    "bond_tr_daily.csv": "0ac665e8a30d04cf5506c63aaf4e0093",
    "gold_tr_daily.csv": "30c9d15d18ce2a0c511a0e2398c55a26",
    "cash_daily.csv": "28a1446d578e3867c2a1d3b33eabe182",   # read by load_substrate; NOT used (§3.2)
}
AQR_MD5 = "5bcb8dbf28146f729b99b629147bb0cd"
YF_TICKERS = ["SSO", "UPRO", "UBT", "TMF", "NTSX", "RSSB", "RSST", "SPY", "TLT", "IEF", "VT", "DBMF"]
# Amendment 2 (891cc3c): FRED's keyless endpoint is blocked for this client, so the SAME series come
# from the publishers FRED republishes. Everything downstream of the parse is unchanged.
# A2.1 (b0c05b8): amendment 2's package hash was the CMT package (halted by the identity check);
# the DDP retired "Build your package" the week of 2026-11-09, so the full-history bill series is
# only in the full H.15 SDMX/ZIP release at the same publisher.
H15_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip"
H15_ID = "H15/H15/RIFSGFSM03_N.B"              # 3-month T-bill, secondary market, discount basis, bd
H15_SERIES_NAME = H15_ID.split("/")[-1]         # SDMX SERIES_NAME attribute
H15_FILE = "frb_h15_all_sdmx.zip"
H15_PUBLISHER = ("Board of Governors of the Federal Reserve System - H.15 Selected Interest Rates, "
                 "Data Download Program")
SOFR_URL = ("https://markets.newyorkfed.org/api/rates/secured/sofr/search.csv"
            "?startDate=2018-04-02&endDate=2025-12-31")
SOFR_FILE = "nyfed_sofr.csv"
SOFR_PUBLISHER = "Federal Reserve Bank of New York - Markets Data API"
SOFR_MIN_ROWS = 1900
GUARD_BILL = {"min_corr": 0.99, "max_abs_mean_gap": 0.0050}   # vs data/macro/DGS3MO.parquet
GUARD_SOFR = {"min_corr": 0.99, "max_abs_mean_gap": 0.0025}   # vs data/macro/DFF.parquet
MACRO = ROOT / "data/macro"
PREREG_REF = "535a3fc + amendment 1 3dcf399 + amendment 2 891cc3c"
YF_START, YF_ASOF = "1990-01-01", "2026-01-01"
SOFR_START = pd.Timestamp("2018-04-03")

TD = 252
S_H1 = 0.0050                                   # the current embedded spread (brief, frozen)
SPREADS_BP = list(range(0, 401, 5))             # 81-point characterization sweep
REBAL = 0.0005                                  # 5 bp per rebalanced dollar
ER_PROD = {"NTSX": 0.0020, "RSSB": 0.0041, "RSST": 0.0100, "SSO": 0.0089,
           "UBT": 0.0095, "UPRO": 0.0090, "TMF": 0.0090}
ER_III = 0.0066                                 # arm (iii), derived a priori (§7, R-5)
ER_DBMF = 0.0085                                # DBMF's own ER, grossed up in (iv-L) (A1.1-4)
ER_SPY_SLEEVE = t311.ER["equity"]               # 0.09 % (T-311)
L_III = 1.9
VOL_WIN = 252
W_IV = (0.50, 0.25)

N_ITER, SEED, BLOCK_DAILY, BLOCK_MONTHLY = 1000, 0, 21, 1
SENS2_DAILY, SENS2_MONTHLY = 252, 12
FFILL_MAX = 7
FIN_GAP_MAX = 5
N_EFF_OPTION_B = 267.0                          # CURRENT_STATE.md:124, director ruling 9.2

DAILY_WINDOWS = {"W-68": ("1968-01-01", "2025-12-31"),
                 "W-72": ("1972-01-01", "2025-12-31"),
                 "W-00": ("2000-01-01", "2025-12-31")}
ARMS_BY_WINDOW = {"W-68": ["i", "ii", "v"], "W-72": ["i", "ii", "iii", "v"],
                  "W-00": ["i", "ii", "iii", "v"]}
MONTHLY_WINDOWS = {"W-85": ("1985-01", "2025-12", "aqr"),
                   "W-00m": ("2000-01", "2025-12", "aqr"),
                   "L-19": ("2019-06", "2025-12", "dbmf")}
STACKED = {"i": (0.90, 0.60, ER_PROD["NTSX"]), "ii": (1.00, 1.00, ER_PROD["RSSB"])}
GATE_SCOPE = {"SSO": "ALL", "UPRO": "ALL", "UBT": "iii", "TMF": "iii", "NTSX": "i,ii"}


class B5Halt(RuntimeError):
    """A fail-closed halt in the measurement path. Never caught inside the harness."""


# --------------------------------------------------------------------------- small utils
def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _guard_std(x: float, what: str) -> float:
    if x is None or not np.isfinite(x) or x < 1e-12:
        raise B5Halt(f"degenerate std for {what}: {x!r}")
    return float(x)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return str(o.date())
    return o


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_jsonable(obj), indent=1, sort_keys=True, allow_nan=False) + "\n")


# --------------------------------------------------------------------------- pure simulator core
def mm_from_discount(d: np.ndarray) -> np.ndarray:
    """T-bill discount yield (decimal) -> money-market (act/360) yield: 360d/(360-91d)."""
    d = np.asarray(d, dtype=float)
    return 360.0 * d / (360.0 - 91.0 * d)


def daily_reset(u: np.ndarray, f: np.ndarray, L: float, er: float) -> np.ndarray:
    """Brief formula, daily reset: R = L*u - (L-1)*f - ER/252."""
    return L * u - (L - 1.0) * f - er / TD


def stacked_fund(e: np.ndarray, b: np.ndarray, f: np.ndarray, w_e: float, w_f: float,
                 er: float, rebal: np.ndarray) -> np.ndarray:
    """Stacked fund (NTSX/RSSB-type): equity E and Treasury overlay F drift between rebalances;
    borrowing = gross - 1 at (cash + s); reset after the close of each `rebal` day (prereg §5.2)."""
    n = len(e)
    out = np.empty(n)
    E, F, N = w_e, w_f, 1.0
    for t in range(n):
        gross = (E + F) / N
        r = (E * e[t] + F * b[t]) / N - (gross - 1.0) * f[t] - er / TD
        E *= 1.0 + e[t]
        F *= 1.0 + b[t]
        N *= 1.0 + r
        if rebal[t]:
            cost = REBAL * (abs(w_e * N - E) + abs(w_f * N - F)) / N
            r = (1.0 + r) * (1.0 - cost) - 1.0
            N *= 1.0 - cost
            E, F = w_e * N, w_f * N
        out[t] = r
    return out


def drifting_portfolio_init(rets: np.ndarray, w0: np.ndarray, targets: np.ndarray,
                            rebal: np.ndarray, cost_mult: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """Unlevered drifting portfolio starting at weights w0; after the close of each rebal day t the
    holdings reset to targets[t]; cost = REBAL * cost_mult * sum|target - drifted|."""
    n, k = rets.shape
    h = np.array(w0, dtype=float)
    rp = np.empty(n)
    cost = np.zeros(n)
    for t in range(n):
        tot = h.sum()
        rp[t] = float((h * rets[t]).sum() / tot)
        h = h * (1.0 + rets[t])
        if rebal[t]:
            wd = h / h.sum()
            cost[t] = REBAL * cost_mult * float(np.abs(targets[t] - wd).sum())
            h = np.array(targets[t], dtype=float)
    return rp, cost


def apply_cost(r: np.ndarray, cost: np.ndarray) -> np.ndarray:
    return (1.0 + r) * (1.0 - cost) - 1.0


def arm_iv_monthly(e_m: np.ndarray, tau_m: np.ndarray, w: float, s: float) -> np.ndarray:
    """(1-w) NAV SPY sleeve (ER 0.09 %) + w NAV RSST-class sleeve (equity + 1.0 overlay at
    tau - s, ER 1.00 %); monthly reset, 5 bp per rebalanced dollar (prereg §6, A1.1-9)."""
    n = len(e_m)
    out = np.empty(n)
    hs, hr = 1.0 - w, w
    for t in range(n):
        rs = e_m[t] - ER_SPY_SLEEVE / 12.0
        rr = e_m[t] + tau_m[t] - s / 12.0 - ER_PROD["RSST"] / 12.0
        tot = hs + hr
        r = (hs * rs + hr * rr) / tot
        hs *= 1.0 + rs
        hr *= 1.0 + rr
        tot = hs + hr
        cost = REBAL * (abs((1.0 - w) - hs / tot) + abs(w - hr / tot))
        out[t] = (1.0 + r) * (1.0 - cost) - 1.0
        hs, hr = 1.0 - w, w
    return out


# --------------------------------------------------------------------------- bootstrap
def auto_block(n: int) -> int:
    """MetricsEngine.bootstrap_distribution's block_length=None rule, verbatim."""
    return max(5, int(round(n ** (1.0 / 3.0))))


def mbb_starts(n: int, L: int, n_iter: int = N_ITER, seed: int = SEED) -> np.ndarray:
    """Replays MetricsEngine.bootstrap_distribution's exact draws (A1.1-6)."""
    L = max(1, min(L, n))
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / L))
    max_start = max(0, n - L)
    S = np.empty((n_iter, nb), dtype=np.int64)
    for i in range(n_iter):
        S[i] = rng.integers(0, max_start + 1, size=nb)
    return S


def mbb_sums(d: np.ndarray, S: np.ndarray, L: int) -> np.ndarray:
    """Sum of each moving-block resample (concatenation truncated to n), via prefix sums."""
    n = len(d)
    L = max(1, min(L, n))
    P = np.concatenate([[0.0], np.cumsum(d)])
    nb = S.shape[1]
    last = n - (nb - 1) * L
    full = (P[S[:, :-1] + L] - P[S[:, :-1]]).sum(axis=1) if nb > 1 else 0.0
    part = P[S[:, -1] + last] - P[S[:, -1]]
    return full + part


def ci_from_samples(samples: np.ndarray) -> Dict[str, float]:
    return {"ci_low": float(np.percentile(samples, 2.5)), "ci_high": float(np.percentile(samples, 97.5)),
            "mean": float(np.mean(samples)), "p_above_zero": float(np.mean(samples > 0))}


class Boot:
    """Caches block-start draws per (n, L) so every spread on a cell uses identical resamples."""

    def __init__(self) -> None:
        self._c: Dict[Tuple[int, int], np.ndarray] = {}

    def sums(self, d: np.ndarray, L: int) -> np.ndarray:
        n = len(d)
        Le = max(1, min(L, n))
        key = (n, Le)
        if key not in self._c:
            self._c[key] = mbb_starts(n, Le)
        return mbb_sums(d, self._c[key], Le)

    def stat(self, d: np.ndarray, L: int, scale: float = 1.0) -> Dict[str, float]:
        out = ci_from_samples(self.sums(d, L) * scale)
        out["point"] = float(np.sum(d) * scale)
        out["block_length"] = int(max(1, min(L, len(d))))
        out["n_iterations"] = N_ITER
        return out


def me_sum_stat(d: np.ndarray, L: Optional[int]) -> Dict[str, float]:
    """MetricsEngine's own bootstrap on Σd (the project standard; quoted for H1)."""
    r = ME.bootstrap_distribution(pd.Series(d), lambda x: float(np.sum(np.asarray(x))),
                                  n_iterations=N_ITER, block_length=L, seed=SEED)
    return {k: float(r[k]) for k in ("point_estimate", "ci_low", "ci_high", "mean", "p_above_zero")} | \
        {"block_length": int(r["block_length"]), "n_iterations": int(r["n_iterations"])}


def crossing(spreads_bp: Sequence[float], stat: Sequence[float]) -> Dict:
    """First grid crossing of `stat` through 0 (linear interpolation). Monotone decreasing in s."""
    s = np.asarray(spreads_bp, dtype=float)
    v = np.asarray(stat, dtype=float)
    if v[0] <= 0:
        return {"s_star_bp": None, "label": "< 0 (<= 0 already at s = 0)"}
    if v[-1] > 0:
        return {"s_star_bp": None, "label": f"> {int(s[-1])}"}
    k = int(np.argmax(v <= 0))
    x = s[k - 1] + (s[k] - s[k - 1]) * v[k - 1] / (v[k - 1] - v[k])
    return {"s_star_bp": float(x), "label": f"{x:.1f} bp"}


def binding_sentence(curve_ci_low: Sequence[float], s_star: Dict) -> str:
    """Prereg §9 / R-12, three cases, exhaustive."""
    if curve_ci_low[0] <= 0:
        return "NOT BINDING: ci_low <= 0 already at s = 0 — the premia and the ER bind, not financing"
    if s_star["s_star_bp"] is None:
        return "NOT BINDING: ci_low > 0 across the whole 0-400 bp sweep"
    if s_star["s_star_bp"] < 50.0:
        return f"BINDING: break-even spread {s_star['s_star_bp']:.1f} bp < the current 50 bp"
    return f"NOT BINDING at today's spread: break-even {s_star['s_star_bp']:.1f} bp >= 50 bp"


# --------------------------------------------------------------------------- fetch (one time)
def _http_get(url: str) -> bytes:
    """Keyless GET with a generic User-Agent (no personal details). Any network failure HALTS:
    the snapshot is written only after EVERY input succeeds, so a failure leaves inputs/ empty."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research-script)"})
    try:
        return urllib.request.urlopen(req, timeout=90).read()
    except (OSError, ValueError) as exc:          # URLError, TimeoutError, ConnectionResetError, ...
        raise B5Halt(f"unreachable: {url} ({type(exc).__name__}: {exc}) — nothing written") from exc


def cmd_fetch() -> int:
    if MANIFEST.exists():
        raise B5Halt(f"snapshot already exists ({MANIFEST}); the fetch runs ONCE (prereg §2.5)")
    if INPUTS.exists() and any(INPUTS.iterdir()):
        raise B5Halt(f"{INPUTS} holds files but no manifest — a foreign or partial state; stop")
    # Stage every file in a per-attempt directory; rename it to inputs/ only after ALL succeed, so a
    # failed attempt never leaves a partial snapshot where the runs read (and nothing is deleted).
    stage = B5 / f"inputs_attempt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    stage.mkdir(parents=True, exist_ok=False)
    import yfinance as yf
    from scripts.reconcile_stooq_tr_t256 import fetch_yf_tr   # the helper only; never its writer
    entries: Dict[str, Dict] = {}
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: E731
    for fname, url, publisher in ((H15_FILE, H15_URL, H15_PUBLISHER), (SOFR_FILE, SOFR_URL, SOFR_PUBLISHER)):
        raw = _http_get(url)
        p = stage / fname
        p.write_bytes(raw)                      # the exact response bytes
        entries[fname] = {"source": publisher, "call": url, "fetched_utc": now(), "md5": md5_file(p)}
    bill, desc = parse_h15_bill(stage / H15_FILE)
    sofr = parse_nyfed_sofr(stage / SOFR_FILE)
    guard = guard_financing(bill, sofr)          # HALTS on misidentification (amendment 2)
    entries[H15_FILE].update({"series": H15_ID, "series_description": desc, "rows": int(len(bill)),
                              "first": str(bill.index[0].date()), "last": str(bill.index[-1].date())})
    entries[SOFR_FILE].update({"series": "SOFR", "rows": int(len(sofr)), "first": str(sofr.index[0].date()),
                               "last": str(sofr.index[-1].date())})
    print(f"  H.15 {H15_ID}: {len(bill)} rows {bill.index[0].date()}..{bill.index[-1].date()} [{desc}]")
    print(f"  NY Fed SOFR: {len(sofr)} rows {sofr.index[0].date()}..{sofr.index[-1].date()}")
    print(f"  guard: {json.dumps(guard)}")
    for tk in YF_TICKERS:
        tr, close = fetch_yf_tr(tk, YF_START, YF_ASOF)
        if tr is None or close is None or len(tr) < 100:
            raise B5Halt(f"yfinance returned nothing usable for {tk} (fail closed)")
        df = pd.DataFrame({"adj_close": tr["Close"].astype(float), "raw_close": close.astype(float)})
        df.index.name = "Date"
        df = df.dropna()
        p = stage / f"yf_{tk}.csv"
        df.to_csv(p, float_format="%.10g")
        entries[p.name] = {"source": "yfinance via scripts/reconcile_stooq_tr_t256.py::fetch_yf_tr "
                                     "(Adj Close, auto_adjust=False)",
                           "call": f"fetch_yf_tr({tk!r}, {YF_START!r}, {YF_ASOF!r})", "fetched_utc": now(),
                           "rows": int(len(df)), "first": str(df.index[0].date()),
                           "last": str(df.index[-1].date()), "md5": md5_file(p),
                           "yfinance_version": yf.__version__}
        print(f"  {tk}: {len(df)} rows {df.index[0].date()}..{df.index[-1].date()}")
    if md5_file(AQR_SRC) != AQR_MD5:
        raise B5Halt("AQR TSMOM on disk does not match the prereg md5")
    p = stage / "aqr_tsmom_monthly_t296.xlsx"
    shutil.copyfile(AQR_SRC, p)
    entries[p.name] = {"source": "copied byte-for-byte from data/research/aqr_tsmom_monthly_t296.xlsx",
                       "call": "shutil.copyfile", "fetched_utc": now(), "md5": md5_file(p)}
    if entries[p.name]["md5"] != AQR_MD5:
        raise B5Halt("AQR snapshot copy md5 mismatch")
    write_json(stage / MANIFEST.name, {"prereg": PREREG_REF, "staged_as": stage.name,
                                       "misidentification_guard": guard, "files": entries})
    stage.rename(INPUTS)                 # POSIX rename onto an EMPTY directory (or none) is atomic
    print(f"snapshot written: {MANIFEST}")
    return 0


def cmd_er_check() -> int:
    """Informational (R-5): UGL / UST expense ratios from yfinance fund data. Alters nothing."""
    import yfinance as yf
    out = {}
    for tk in ("UGL", "UST"):
        rec: Dict = {"ticker": tk}
        try:
            fo = yf.Ticker(tk).funds_data.fund_operations
            rec["fund_operations"] = {str(i): {str(c): (None if pd.isna(v) else float(v) if isinstance(
                v, (int, float, np.floating)) else str(v)) for c, v in row.items()}
                for i, row in fo.iterrows()}
        except Exception as exc:  # noqa: BLE001 — informational only, outside the measurement path
            rec["error"] = f"{type(exc).__name__}: {exc}"
        out[tk] = rec
    out["note"] = "Informational only; the frozen arm (iii) ER stays 0.66 % (amendment 1, R-5)."
    out["fetched_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(B5 / "er_check.json", out)
    print(json.dumps(_jsonable(out), indent=1))
    return 0


# --------------------------------------------------------------------------- snapshot loaders
def parse_h15_bill(p: Path) -> Tuple[pd.Series, str]:
    """Dispatch: the full-release SDMX/ZIP (A2.1, the production path) or a DDP CSV package."""
    if p.suffix.lower() == ".zip":
        return parse_h15_sdmx_zip(p)
    return parse_h15_csv(p)


def _desc_ok(text: str) -> bool:
    t = text.lower()
    return "3-month" in t and "secondary market" in t


def parse_h15_sdmx_zip(p: Path) -> Tuple[pd.Series, str]:
    """The full H.15 SDMX/ZIP -> the 3-month bill (decimal), by SERIES_NAME (A2.1 identity check).
    Streams the XML (iterparse) and drops every finished Series element, so memory stays small.
    HALTS unless exactly one series carries SERIES_NAME == RIFSGFSM03_N.B AND its own description /
    annotation text contains '3-month' and 'secondary market'."""
    import xml.etree.ElementTree as ET
    import zipfile
    hits: List[Dict] = []
    matching_desc: List[str] = []
    with zipfile.ZipFile(p) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not names:
            raise B5Halt("H.15 SDMX/ZIP holds no XML file")
        for name in names:
            with zf.open(name) as fh:
                stack: List = []
                cur: Optional[Dict] = None
                for ev, el in ET.iterparse(fh, events=("start", "end")):
                    tag = el.tag.rsplit("}", 1)[-1]
                    if ev == "start":
                        stack.append(el)
                        if tag == "Series":
                            cur = {"name": el.attrib.get("SERIES_NAME"), "obs": [], "text": [],
                                   "attrs": dict(el.attrib)}
                        continue
                    stack.pop()
                    if cur is not None:
                        if tag == "Obs":
                            if cur["name"] == H15_SERIES_NAME:
                                cur["obs"].append((el.attrib.get("TIME_PERIOD"), el.attrib.get("OBS_VALUE"),
                                                   el.attrib.get("OBS_STATUS")))
                            if stack:
                                stack[-1].remove(el)
                        elif tag == "Series":
                            text = " ".join(t for t in cur["text"] if t)
                            if cur["name"] == H15_SERIES_NAME:
                                hits.append({**cur, "desc": text})
                            elif _desc_ok(text):
                                matching_desc.append(f"{cur['name']}: {text[:160]}")
                            cur = None
                            if stack:
                                stack[-1].remove(el)
                        elif el.text and el.text.strip():
                            cur["text"].append(el.text.strip())
    if len(hits) != 1:
        raise B5Halt(f"H.15 SDMX holds {len(hits)} series named {H15_SERIES_NAME}; series whose "
                     f"description matches (NOT used without a ruling): {matching_desc[:10]}")
    h = hits[0]
    if not _desc_ok(h["desc"]):
        raise B5Halt(f"H.15 {H15_SERIES_NAME} description fails the identity check: {h['desc'][:300]!r}")
    # A2.2: "no data" is a STATUS flag here (OBS_STATUS="ND", OBS_VALUE="-9999"), so keep "A" only.
    obs = [o for o in h["obs"] if o[2] == "A"]
    dates = pd.to_datetime(pd.Series([o[0] for o in obs]), errors="coerce", format="%Y-%m-%d")
    vals = pd.to_numeric(pd.Series([o[1] for o in obs]), errors="coerce")
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates)).dropna()
    s = s[s.index.notna()]
    if s.index.duplicated().any() or len(s) < 10000:
        raise B5Halt(f"H.15 bill series malformed (rows {len(s)}, duplicates {int(s.index.duplicated().sum())})")
    return _rate_range_check((s / 100.0).sort_index(), "H.15 bill"), h["desc"][:300]


def parse_h15_csv(p: Path) -> Tuple[pd.Series, str]:
    """A DDP H.15 CSV package -> the 3-month bill (decimal, discount basis), by its Unique Identifier.
    Amendment 2 identity check: exactly one column with H15_ID; its description must contain
    '3-month' and 'secondary market'. Non-numeric cells (ND/NC) are dropped, never filled."""
    raw = pd.read_csv(p, header=None, dtype=str, keep_default_na=False)
    first = raw.iloc[:, 0].astype(str).str.strip().str.lower()
    uid_rows = np.where(first.str.startswith("unique identifier"))[0]
    tp_rows = np.where(first == "time period")[0]
    desc_rows = np.where(first.str.startswith("series description"))[0]
    if not (len(uid_rows) and len(tp_rows) and len(desc_rows)):
        raise B5Halt("H.15 package CSV lacks its label rows (Series Description / Unique Identifier / Time Period)")
    uid = raw.iloc[uid_rows[0]].astype(str).str.strip()
    cols = np.where(uid == H15_ID)[0]
    if len(cols) != 1:
        raise B5Halt(f"H.15 package holds {len(cols)} columns with identifier {H15_ID}")
    j = int(cols[0])
    desc = str(raw.iloc[desc_rows[0], j]).strip()
    if "3-month" not in desc.lower() or "secondary market" not in desc.lower():
        raise B5Halt(f"H.15 column {H15_ID} description fails the identity check: {desc!r}")
    data = raw.iloc[tp_rows[0] + 1:, [0, j]]
    dates = pd.to_datetime(data.iloc[:, 0].str.strip(), errors="coerce", format="%Y-%m-%d")
    vals = pd.to_numeric(data.iloc[:, 1].str.strip(), errors="coerce")
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates)).dropna()
    s = s[s.index.notna()]
    if s.index.duplicated().any() or len(s) < 10000:
        raise B5Halt(f"H.15 bill series malformed (rows {len(s)}, duplicates {int(s.index.duplicated().sum())})")
    return _rate_range_check((s / 100.0).sort_index(), "H.15 bill (csv)"), desc


def parse_nyfed_sofr(p: Path) -> pd.Series:
    """NY Fed Markets API search.csv -> SOFR (decimal) by Effective Date (amendment 2)."""
    df = pd.read_csv(p)
    cols = {c.strip().lower(): c for c in df.columns}
    need = ("effective date", "rate type", "rate (%)")
    if not all(k in cols for k in need):
        raise B5Halt(f"NY Fed SOFR CSV lacks columns {need}: {list(df.columns)}")
    types = set(df[cols["rate type"]].astype(str).str.strip().str.upper())
    if types != {"SOFR"}:
        raise B5Halt(f"NY Fed CSV rate types {types} != {{'SOFR'}}")
    s = pd.Series(pd.to_numeric(df[cols["rate (%)"]], errors="coerce").values,
                  index=pd.DatetimeIndex(pd.to_datetime(df[cols["effective date"]]))).dropna()
    if s.index.duplicated().any() or len(s) < SOFR_MIN_ROWS:
        raise B5Halt(f"NY Fed SOFR malformed (rows {len(s)} < {SOFR_MIN_ROWS} or duplicated dates)")
    return _rate_range_check((s / 100.0).sort_index(), "NY Fed SOFR")


RATE_RANGE = (-0.01, 0.25)


def _rate_range_check(s: pd.Series, what: str) -> pd.Series:
    """A2.2: every rate used must lie in [-1 %, +25 %] per year — a HALT-only input-validity check."""
    lo, hi = RATE_RANGE
    bad = s[(s < lo) | (s > hi) | ~np.isfinite(s)]
    if len(bad):
        raise B5Halt(f"{what}: {len(bad)} values outside [{lo}, {hi}] (first {bad.index[0].date()}: {bad.iloc[0]})")
    return s


def _guard_pair(x: pd.Series, ref: pd.Series, spec: Dict, what: str, ref_minus_x: bool) -> Dict:
    j = pd.concat({"x": x, "ref": ref}, axis=1, join="inner").dropna()
    if len(j) < 250:
        raise B5Halt(f"misidentification guard ({what}): only {len(j)} common dates")
    corr = float(np.corrcoef(j["x"], j["ref"])[0, 1])
    gap = float((j["ref"] - j["x"]).mean() if ref_minus_x else (j["x"] - j["ref"]).mean())
    ok = corr >= spec["min_corr"] and abs(gap) <= spec["max_abs_mean_gap"]
    out = {"n_common": int(len(j)), "level_corr": corr, "mean_gap": gap, **spec, "pass": bool(ok)}
    if not ok:
        raise B5Halt(f"misidentification guard FAILED ({what}): {out}")
    return out


def guard_financing(bill: pd.Series, sofr: pd.Series) -> Dict:
    """Amendment 2: each publisher series vs its on-disk FRED sibling (read-only). HALT-only."""
    dg_p, dff_p = MACRO / "DGS3MO.parquet", MACRO / "DFF.parquet"
    dg = pd.read_parquet(dg_p)["value"].astype(float) / 100.0
    dff = pd.read_parquet(dff_p)["value"].astype(float) / 100.0
    dg.index, dff.index = pd.DatetimeIndex(dg.index), pd.DatetimeIndex(dff.index)
    so = sofr[(sofr.index >= SOFR_START) & (sofr.index <= pd.Timestamp("2025-12-31"))]
    return {"bill_vs_DGS3MO (DGS3MO - bill)": _guard_pair(bill, dg, GUARD_BILL, "bill vs DGS3MO", True),
            "SOFR_vs_DFF (SOFR - EFFR)": _guard_pair(so, dff, GUARD_SOFR, "SOFR vs DFF", False),
            "reference_md5": {"DGS3MO.parquet": md5_file(dg_p), "DFF.parquet": md5_file(dff_p)}}


def verify_snapshot() -> Dict:
    if not MANIFEST.exists():
        raise B5Halt(f"no snapshot manifest at {MANIFEST} — run `fetch` first")
    man = json.loads(MANIFEST.read_text())
    for name, e in man["files"].items():
        p = INPUTS / name
        if not p.exists() or md5_file(p) != e["md5"]:
            raise B5Halt(f"snapshot file {name} missing or md5 != manifest")
    for name, want in SUBSTRATE_MD5.items():
        if md5_file(SUB / name) != want:
            raise B5Halt(f"T-306 substrate {name} md5 != prereg §3.1 — re-verify required")
    return man


def load_yf(tk: str) -> pd.Series:
    df = pd.read_csv(INPUTS / f"yf_{tk}.csv", parse_dates=["Date"], index_col="Date")
    return df["adj_close"].astype(float).sort_index()


def financing_base() -> pd.Series:
    """Annual act/360 rate (decimal): the 3-month bill (H.15; = FRED DTB3) money-market-converted
    to 2018-04-02, SOFR (NY Fed; = FRED SOFR) from 2018-04-03 (amendment 2: publishers, same series)."""
    dtb3, _ = parse_h15_bill(INPUTS / H15_FILE)
    sofr = parse_nyfed_sofr(INPUTS / SOFR_FILE)
    d = dtb3[dtb3.index < SOFR_START]
    mm = pd.Series(mm_from_discount(d.values), index=d.index)
    so = sofr[sofr.index >= SOFR_START]
    if so.index.min() != SOFR_START:
        raise B5Halt(f"SOFR snapshot does not start {SOFR_START.date()} (starts {so.index.min()})")
    return pd.concat([mm, so]).sort_index()


def financing_arrays(dates: pd.DatetimeIndex, base: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """For return dates[1:]: r_{t-1} (last base rate on or before dates[t-1]) and Δcal_t."""
    prev = dates[:-1]
    pos = base.index.searchsorted(prev, side="right") - 1
    if (pos < 0).any():
        raise B5Halt("financing base does not cover the start of the series")
    lag_days = (prev - base.index[pos]).days
    if (lag_days > 10).any():
        raise B5Halt(f"financing base stale by {int(lag_days.max())} calendar days")
    r = base.values[pos]
    dcal = (dates[1:] - dates[:-1]).days.values.astype(float)
    return r, dcal


def fin_gap_check(base: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> int:
    b = base[(base.index >= start - pd.Timedelta(days=15)) & (base.index <= end)]
    d = b.index.values.astype("datetime64[D]")
    gaps = np.busday_count(d[:-1], d[1:]) - 1
    g = int(gaps.max()) if len(gaps) else 0
    if g > FIN_GAP_MAX:
        raise B5Halt(f"financing base gap of {g} business days inside {start.date()}..{end.date()}")
    return g


def load_aqr() -> pd.Series:
    d = pd.read_excel(INPUTS / "aqr_tsmom_monthly_t296.xlsx", "TSMOM Factors", header=None)
    t = d.iloc[18:, :2].dropna()
    s = pd.Series(t.iloc[:, 1].astype(float).values, index=pd.to_datetime(t.iloc[:, 0]).dt.to_period("M"))
    if s.index.duplicated().any():
        raise B5Halt("AQR months duplicated")
    return s.sort_index()


# --------------------------------------------------------------------------- substrate
class Substrate:
    """T-306 legs on the equity calendar via T-311 load_substrate, with a REAL ffill guard."""

    def __init__(self, base: pd.Series) -> None:
        legs2, _ = t311.load_substrate(["equity", "bond"])
        legs3, _ = t311.load_substrate(["equity", "bond", "gold"])
        self.px2 = pd.DataFrame(legs2)
        self.px3 = pd.DataFrame(legs3)
        common = self.px3.index
        if not self.px2.loc[common].index.equals(common):
            raise B5Halt("2-asset and 3-asset frames disagree on the equity calendar")
        self.orig = {k: t311._leg(k) for k in ("equity", "bond", "gold")}
        self.base = base
        self.bench_daily = t311.buyhold_equity(legs2)      # equity_tr - 0.09 %/252 (T-311)

    def ffill_runs(self, leg: str, start: pd.Timestamp, end: pd.Timestamp) -> Dict:
        cal = self.px2.index if leg != "gold" else self.px3.index
        cal = cal[(cal >= start) & (cal <= end)]
        miss = ~cal.isin(self.orig[leg].index)
        runs, cur = 0, 0
        for m in miss:
            cur = cur + 1 if m else 0
            runs = max(runs, cur)
        if runs > FFILL_MAX:
            raise B5Halt(f"{leg}: forward-filled run of {runs} days inside {start.date()}..{end.date()}")
        return {"ffilled_days": int(miss.sum()), "longest_run": int(runs)}

    def window(self, start: str, end: str, gold: bool) -> Dict:
        px = self.px3 if gold else self.px2
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        idx = px.index
        wd = idx[(idx >= s) & (idx <= e)]
        if len(wd) == 0 or wd[-1] < e - pd.Timedelta(days=5):
            raise B5Halt(f"window {start}..{end} not covered (gold={gold})")
        i0 = idx.get_loc(wd[0])
        if i0 < 1:
            raise B5Halt(f"window {start} has no prior close")
        dates = idx[i0 - 1: i0 + len(wd)]                    # base date + window dates
        rets = px.loc[dates].pct_change().iloc[1:]
        r, dcal = financing_arrays(dates, self.base)
        bench = self.bench_daily.reindex(wd)
        out = {"dates": wd, "base_date": dates[0], "e": rets["equity"].values,
               "b": rets["bond"].values, "r": r, "dcal": dcal, "bench": bench.values}
        if gold:
            out["g"] = rets["gold"].values
        for k in ("e", "b", "bench") + (("g",) if gold else ()):
            if not np.isfinite(out[k]).all():
                raise B5Halt(f"non-finite {k} inside window {start}..{end}")
        return out


def fin(w: Dict, s: float) -> np.ndarray:
    return (w["r"] + s) * w["dcal"] / 360.0


def cash_acc(w: Dict) -> np.ndarray:
    return w["r"] * w["dcal"] / 360.0


def quarter_end_flags(dates: pd.DatetimeIndex) -> np.ndarray:
    q = dates.to_period("Q")
    f = np.zeros(len(dates), dtype=bool)
    f[:-1] = q[:-1] != q[1:]
    return f


def month_end_flags(dates: pd.DatetimeIndex) -> np.ndarray:
    m = dates.to_period("M")
    f = np.zeros(len(dates), dtype=bool)
    f[:-1] = m[:-1] != m[1:]
    return f


def rp_weights(sub: Substrate) -> pd.DataFrame:
    """Inverse-vol weights at every date (used only at month-ends): 252-day trailing std of daily log
    returns, inclusive of the date (causal: applied from the next day)."""
    lr = np.log(sub.px3.pct_change() + 1.0)
    vol = lr.rolling(VOL_WIN).std()
    inv = 1.0 / vol
    return inv.div(inv.sum(axis=1), axis=0)


# --------------------------------------------------------------------------- arms (daily)
def arm_returns(arm: str, w: Dict, s: float, rpw: Optional[pd.DataFrame] = None,
                rp_cache: Optional[Dict] = None) -> np.ndarray:
    if arm in STACKED:
        we, wf, er = STACKED[arm]
        return stacked_fund(w["e"], w["b"], fin(w, s), we, wf, er, quarter_end_flags(w["dates"]))
    if arm == "v":
        rets = np.column_stack([w["e"] - t311.ER["equity"] / TD, w["b"] - t311.ER["bond"] / TD])
        tgt = np.tile([0.6, 0.4], (len(rets), 1))
        rp, cost = drifting_portfolio_init(rets, np.array([0.6, 0.4]), tgt, month_end_flags(w["dates"]))
        return apply_cost(rp, cost)
    if arm == "iii":
        if rp_cache is None or "rp" not in rp_cache:
            rets = np.column_stack([w["e"], w["b"], w["g"]])
            wts = rpw.loc[w["dates"], ["equity", "bond", "gold"]].values
            w0 = rpw.loc[w["base_date"], ["equity", "bond", "gold"]].values
            if not (np.isfinite(w0).all() and np.isfinite(wts).all()):
                raise B5Halt("arm (iii) inverse-vol weights incomplete (warm-up not covered)")
            rp, cost = drifting_portfolio_init(rets, w0, wts, month_end_flags(w["dates"]), cost_mult=L_III)
            if rp_cache is not None:
                rp_cache.update({"rp": rp, "cost": cost, "w0": w0})
        else:
            rp, cost = rp_cache["rp"], rp_cache["cost"]
        return apply_cost(daily_reset(rp, fin(w, s), L_III, ER_III), cost)
    raise ValueError(arm)


def log_diff(r_arm: np.ndarray, r_bench: np.ndarray) -> np.ndarray:
    d = np.log1p(r_arm) - np.log1p(r_bench)
    if not np.isfinite(d).all():
        raise B5Halt("non-finite paired log difference")
    return d


def wealth_stats(r: np.ndarray, dates: pd.DatetimeIndex, base_date: pd.Timestamp, periods: int) -> Dict:
    wealth = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    dd = wealth / np.maximum.accumulate(wealth) - 1.0
    years = (dates[-1] - base_date).days / 365.25
    vol = _guard_std(float(np.std(r, ddof=1)), "arm returns") * math.sqrt(periods)
    return {"terminal_multiple": float(wealth[-1]), "cagr": float(wealth[-1] ** (1.0 / years) - 1.0),
            "vol_ann": vol, "max_dd": float(dd.min()),
            "max_dd_trough": str(dates[int(np.argmin(dd[1:]))].date())}


def sortino_ci(r: np.ndarray, periods: int) -> Dict:
    res = ME.bootstrap_distribution(pd.Series(r), lambda x: ME.sortino_ratio(x, 0.0, periods),
                                    n_iterations=N_ITER, block_length=None, seed=SEED)
    return {"point": float(res["point_estimate"]), "ci_low": float(res["ci_low"]),
            "ci_high": float(res["ci_high"]), "block_length": int(res["block_length"])}


def ir_of(d: np.ndarray, periods: int) -> float:
    return float(np.mean(d) / _guard_std(float(np.std(d, ddof=1)), "paired diff") * math.sqrt(periods))


# --------------------------------------------------------------------------- honest N (read-only)
def honest_n() -> Dict:
    from core.measurement.mbl_gate import (compute_n_effective, compute_n_effective_correlated,
                                           expected_max_normal, load_n_effective_artifact,
                                           n_eff_equicorrelated, N_EFF_FLOOR)
    n_raw = compute_n_effective()
    cons = compute_n_effective_correlated(method="conservative")
    gi = load_n_effective_artifact()["gate_inputs"]
    n1 = n_raw + 1
    eq1 = n_eff_equicorrelated(n1, float(gi["rho_bar"]))
    onc1 = max(N_EFF_FLOOR, min(float(n1), n1 * float(gi["onc_compression"])))
    return {"n_raw_registry": int(n_raw), "n_eff_conservative": float(cons),
            "n_eff_conservative_plus1": float(max(eq1, onc1)), "n_eff_option_b": N_EFF_OPTION_B,
            "e_max_plus1": float(expected_max_normal(max(eq1, onc1))),
            "e_max_option_b": float(expected_max_normal(N_EFF_OPTION_B)),
            "registry_medium": "573fc62 (registry never sees standalone-harness trials)"}


def mbl_line(ir: float, years: float, hn: Dict) -> Dict:
    need_a = hn["e_max_plus1"] / math.sqrt(years)
    need_b = hn["e_max_option_b"] / math.sqrt(years)
    return {"ir": ir, "years": years, "ir_needed_neff_gate": need_a, "ir_needed_neff_267": need_b,
            "clears_gate_n": bool(ir >= need_a), "clears_n_267": bool(ir >= need_b)}


# --------------------------------------------------------------------------- monthly helpers
def to_monthly(daily: pd.Series) -> pd.Series:
    return (1.0 + daily).groupby(daily.index.to_period("M")).prod() - 1.0


def monthly_inputs(sub: Substrate, kind: str, m0: str, m1: str) -> Dict:
    eq = sub.px2["equity"].pct_change()
    e_m = to_monthly(eq.dropna())
    bench_m = to_monthly(sub.bench_daily)
    months = pd.period_range(m0, m1, freq="M")
    if kind == "aqr":
        tau = load_aqr().reindex(months)
    else:
        full_dates = sub.px2.index
        r, dcal = financing_arrays(full_dates, sub.base)
        c_daily = pd.Series(r * dcal / 360.0, index=full_dates[1:])
        fin_gap_check(sub.base, months[0].to_timestamp(), months[-1].to_timestamp(how="end"))
        px = load_yf("DBMF")
        me_px = px.groupby(px.index.to_period("M")).last()
        r_db = me_px.pct_change().reindex(months)
        c_m = to_monthly(c_daily).reindex(months)
        tau = r_db - c_m + ER_DBMF / 12.0          # A1.1-4: excess over the base, ER grossed up
    e = e_m.reindex(months)
    b = bench_m.reindex(months)
    for name, v in (("equity", e), ("bench", b), ("tau", tau)):
        if v.isna().any() or not np.isfinite(v.values).all():
            raise B5Halt(f"monthly {name} incomplete over {m0}..{m1} ({kind})")
    return {"months": months, "e": e.values, "bench": b.values, "tau": tau.values}


# --------------------------------------------------------------------------- validation
def _first_full_month_start(live: pd.Series, idx: pd.DatetimeIndex) -> pd.Timestamp:
    m1 = live.first_valid_index().to_period("M") + 1
    cands = idx[idx.to_period("M") >= m1]
    if len(cands) == 0:
        raise B5Halt("no full month after first price")
    return cands[0]


def _val_stats(live_r: np.ndarray, syn_r: np.ndarray, periods: int, L_minus_1: float,
               slope_gate: bool) -> Dict:
    d = np.log1p(live_r) - np.log1p(syn_r)
    td = float(np.mean(d) * periods)
    te = _guard_std(float(np.std(d, ddof=1)), "tracking diff") * math.sqrt(periods)
    var = _guard_std(float(np.var(syn_r, ddof=1)), "synthetic var")
    slope = float(np.cov(live_r, syn_r, ddof=1)[0, 1] / var)
    g1_band = 0.0100 * L_minus_1
    out = {"n": int(len(d)), "td_ann": td, "te_ann": te, "slope": slope,
           "implied_spread_bp": 50.0 - td / L_minus_1 * 1e4, "g1_band_ann": g1_band,
           "g1_pass": bool(abs(td) <= g1_band + 1e-15),
           "corr": float(np.corrcoef(live_r, syn_r)[0, 1])}
    out["g2_pass"] = bool(0.90 <= slope <= 1.10) if slope_gate else None
    out["pass"] = bool(out["g1_pass"] and (out["g2_pass"] if slope_gate else True))
    return out


def _daily_frame(cols: Dict[str, pd.Series]) -> pd.DataFrame:
    return pd.concat(cols, axis=1, join="inner").dropna().sort_index()


def validate_daily(live_tk: str, under: Dict[str, pd.Series], kind: str, L: float, er: float,
                   base: pd.Series, stacked_w: Optional[Tuple[float, float]] = None,
                   live_override: Optional[pd.Series] = None) -> Dict:
    live = live_override if live_override is not None else load_yf(live_tk)
    df = _daily_frame({"live": live, **under})
    start = _first_full_month_start(live, df.index)
    df = df[df.index <= pd.Timestamp("2025-12-31")]
    i0 = df.index.get_loc(start)
    df = df.iloc[i0 - 1:]
    dates = df.index
    rets = df.pct_change().iloc[1:]
    r, dcal = financing_arrays(dates, base)
    fin_gap_check(base, dates[0], dates[-1])
    f = (r + S_H1) * dcal / 360.0
    if kind == "daily":
        syn = daily_reset(rets["u"].values, f, L, er)
        lm1 = L - 1.0
    else:
        we, wf = stacked_w
        syn = stacked_fund(rets["e"].values, rets["b"].values, f, we, wf, er, quarter_end_flags(dates[1:]))
        lm1 = we + wf - 1.0
    st = _val_stats(rets["live"].values, syn, TD, lm1, slope_gate=True)
    st.update({"first": str(dates[1].date()), "last": str(dates[-1].date()), "L": L if kind == "daily" else
               stacked_w[0] + stacked_w[1], "er": er, "kind": kind,
               "years": (dates[-1] - dates[0]).days / 365.25})
    return st


def cmd_validate() -> int:
    verify_snapshot()
    base = financing_base()
    spy, tlt, ief, vt = load_yf("SPY"), load_yf("TLT"), load_yf("IEF"), load_yf("VT")
    v1 = {
        "SSO": validate_daily("SSO", {"u": spy}, "daily", 2.0, ER_PROD["SSO"], base),
        "UPRO": validate_daily("UPRO", {"u": spy}, "daily", 3.0, ER_PROD["UPRO"], base),
        "UBT": validate_daily("UBT", {"u": tlt}, "daily", 2.0, ER_PROD["UBT"], base),
        "TMF": validate_daily("TMF", {"u": tlt}, "daily", 3.0, ER_PROD["TMF"], base),
        "NTSX": validate_daily("NTSX", {"e": spy, "b": ief}, "stacked", 1.5, ER_PROD["NTSX"], base,
                               stacked_w=(0.90, 0.60)),
        "RSSB": validate_daily("RSSB", {"e": vt, "b": ief}, "stacked", 2.0, ER_PROD["RSSB"], base,
                               stacked_w=(1.00, 1.00)),
    }
    # RSST monthly (report-only): SPY TR month + AQR tau - s/12 - 1.00 %/12
    rsst = load_yf("RSST")
    months = pd.period_range(rsst.first_valid_index().to_period("M") + 1, "2025-12", freq="M")
    mlast = lambda s: s.groupby(s.index.to_period("M")).last()  # noqa: E731
    live_m = mlast(rsst).pct_change().reindex(months)
    spy_m = mlast(spy).pct_change().reindex(months)
    tau = load_aqr().reindex(months)
    if live_m.isna().any() or spy_m.isna().any() or tau.isna().any():
        raise B5Halt("RSST validation months incomplete")
    syn_m = spy_m.values + tau.values - S_H1 / 12.0 - ER_PROD["RSST"] / 12.0
    st = _val_stats(live_m.values, syn_m, 12, 1.0, slope_gate=False)
    st.update({"first": str(months[0]), "last": str(months[-1]), "kind": "monthly", "L": 2.0,
               "er": ER_PROD["RSST"], "years": len(months) / 12.0})
    v1["RSST"] = st
    for k, v in v1.items():
        v["role"] = "GATING" if k in GATE_SCOPE else "REPORTED"
        v["scope"] = GATE_SCOPE.get(k, "none")
    # V2 — the substrate-leg synthetic (the object extended back), reported with the caveat rule (R-6)
    sub_eq = t311._leg("equity")
    sub_bd = t311._leg("bond")
    sso_live = load_yf("SSO")
    ntsx_live = load_yf("NTSX")
    v2 = {"SSO": validate_daily("SSO", {"u": sub_eq}, "daily", 2.0, ER_PROD["SSO"], base,
                                live_override=sso_live),
          "NTSX": validate_daily("NTSX", {"e": sub_eq, "b": sub_bd}, "stacked", 1.5, ER_PROD["NTSX"],
                                 base, stacked_w=(0.90, 0.60), live_override=ntsx_live)}
    for k, v in v2.items():
        v["role"] = "REPORTED (V2 substrate basis)"
        v["caveat_triggered"] = bool(not v["g1_pass"] and v1[k]["g1_pass"])
    halted: List[str] = []
    for k, scope in GATE_SCOPE.items():
        if not v1[k]["pass"]:
            halted += ["i", "ii", "iii", "v", "iv"] if scope == "ALL" else scope.split(",")
    verdict = {"halted_arms": sorted(set(halted)),
               "h1_status": "NOT EVALUABLE" if ("ii" in halted) else "EVALUABLE",
               "all_gating_pass": not halted}
    bill_ok, _ = parse_h15_bill(INPUTS / H15_FILE)
    write_json(VALIDATION, {"prereg": PREREG_REF, "manifest_md5": md5_file(MANIFEST),
                            "h15_bill_rows_status_A": int(len(bill_ok)),
                            "h15_bill_span": [str(bill_ok.index[0].date()), str(bill_ok.index[-1].date())],
                            "spread_bp": 50, "v1": v1, "v2": v2, "verdict": verdict})
    for k, v in v1.items():
        print(f"  V1 {k:5} {v['role']:8} TD {v['td_ann']*1e4:+8.1f} bp/yr  band ±{v['g1_band_ann']*1e4:5.0f}"
              f"  TE {v['te_ann']*100:5.2f}%  slope {v['slope']:.4f}  s* {v['implied_spread_bp']:+7.1f} bp"
              f"  {v['first']}..{v['last']}  pass={v['pass']}")
    for k, v in v2.items():
        print(f"  V2 {k:5} TD {v['td_ann']*1e4:+8.1f} bp/yr  TE {v['te_ann']*100:5.2f}%  slope {v['slope']:.4f}"
              f"  caveat={v['caveat_triggered']}")
    print("  verdict:", verdict)
    return 0


def load_validation() -> Dict:
    if not VALIDATION.exists():
        raise B5Halt("validation.json absent — run `validate` before `smoke`/`run`")
    return json.loads(VALIDATION.read_text())


# --------------------------------------------------------------------------- smoke (first 12 months)
def cmd_smoke() -> int:
    verify_snapshot()
    val = load_validation()
    base = financing_base()
    sub = Substrate(base)
    rpw = rp_weights(sub)
    out: Dict = {"note": "SMOKE — first 12 months of each window; NOTHING here is quoted.", "windows": {}}
    for wn, (s0, _) in DAILY_WINDOWS.items():
        e1 = str(pd.Timestamp(s0) + pd.DateOffset(years=1) - pd.Timedelta(days=1))[:10]
        w = sub.window(s0, e1, gold=("iii" in ARMS_BY_WINDOW[wn]))
        chk: Dict = {"first": str(w["dates"][0].date()), "last": str(w["dates"][-1].date()),
                     "n": len(w["dates"])}
        f = fin(w, S_H1)
        chk["financing_first_week"] = [
            {"date": str(w["dates"][i].date()), "r_prev": float(w["r"][i]), "dcal": float(w["dcal"][i]),
             "f": float(f[i]), "f_hand": float((w["r"][i] + 0.005) * w["dcal"][i] / 360.0)} for i in range(5)]
        for arm in ARMS_BY_WINDOW[wn]:
            if arm in val["verdict"]["halted_arms"]:
                chk[arm] = "HALTED by validation"
                continue
            R = arm_returns(arm, w, S_H1, rpw, {})
            c: Dict = {"finite": bool(np.isfinite(R).all())}
            if arm in STACKED:
                we, wf, er = STACKED[arm]
                ident = we * w["e"][0] + wf * w["b"][0] - (we + wf - 1.0) * f[0] - er / TD
                c["day1_identity_abs_err"] = float(abs(R[0] - ident))
            if arm == "v":
                ident = 0.6 * (w["e"][0] - 0.0009 / TD) + 0.4 * (w["b"][0] - 0.0003 / TD)
                c["day1_identity_abs_err"] = float(abs(R[0] - ident))
            if arm == "iii":
                w0 = rpw.loc[w["base_date"], ["equity", "bond", "gold"]].values
                c["w0"] = [float(x) for x in w0]
                c["w0_sum"] = float(w0.sum())
            c["sum_log_diff_vs_bench"] = "computed, not quoted"
            log_diff(R, w["bench"])
            chk[arm] = c
        out["windows"][wn] = chk
    for wn, (m0, _, kind) in MONTHLY_WINDOWS.items():
        m1 = str(pd.Period(m0, "M") + 11)
        mi = monthly_inputs(sub, kind, m0, m1)
        R = arm_iv_monthly(mi["e"], mi["tau"], 0.5, S_H1)
        ident = mi["e"][0] + 0.5 * (mi["tau"][0] - S_H1 / 12.0) - (0.5 * 0.0009 + 0.5 * 0.01) / 12.0
        out["windows"][wn] = {"finite": bool(np.isfinite(R).all()), "months": [str(mi["months"][0]),
                              str(mi["months"][-1])], "month1_identity_abs_err_pre_cost": float(abs(R[0] - ident))}
    write_json(SMOKE, out)
    print(json.dumps(_jsonable(out), indent=1)[:6000])
    return 0


# --------------------------------------------------------------------------- the run
def rho_years(w: Dict) -> Tuple[List[int], List[int]]:
    yrs = w["dates"].year
    pos, neg = [], []
    for y in sorted(set(yrs)):
        m = yrs == y
        c = float(np.corrcoef(w["e"][m], w["b"][m])[0, 1])
        (pos if c > 0 else neg).append(int(y))
    return pos, neg


def cell_daily(arm: str, w: Dict, boot: Boot, rpw, hn: Dict, cache: Dict, years: float) -> Dict:
    R = arm_returns(arm, w, S_H1, rpw, cache)
    d = log_diff(R, w["bench"])
    n = len(d)
    prim = boot.stat(d, BLOCK_DAILY)
    s1 = boot.stat(d, auto_block(n))
    s2 = boot.stat(d, SENS2_DAILY)
    for x in (prim, s1, s2):
        x["per_year"] = {k: x[k] / years for k in ("point", "ci_low", "ci_high", "mean")}
    ws = wealth_stats(R, w["dates"], w["base_date"], TD)
    ir = ir_of(d, TD)
    return {"n_days": n, "years": years, "dlogTW": prim, "dlogTW_sens_auto": s1, "dlogTW_sens_252": s2,
            "arm": ws, "sortino": sortino_ci(R, TD), "mbl": mbl_line(ir, years, hn), "_R": R, "_d": d}


def curve_daily(arm: str, w: Dict, boot: Boot, rpw, cache: Dict, years: float) -> Dict:
    pts, lo, hi = [], [], []
    for sbp in SPREADS_BP:
        R = arm_returns(arm, w, sbp / 1e4, rpw, cache)
        d = log_diff(R, w["bench"])
        st = boot.stat(d, BLOCK_DAILY)
        pts.append(st["point"] / years)
        lo.append(st["ci_low"] / years)
        hi.append(st["ci_high"] / years)
    sci = crossing(SPREADS_BP, lo)
    spt = crossing(SPREADS_BP, pts)
    return {"spreads_bp": SPREADS_BP, "point_per_year": pts, "ci_low_per_year": lo, "ci_high_per_year": hi,
            "s_star_ci": sci, "s_star_point": spt, "binding": binding_sentence(lo, sci)}


def subsample(d: np.ndarray, mask: np.ndarray, boot: Boot, L: int, periods: int) -> Dict:
    x = d[mask]
    if len(x) < 2 * L:
        return {"n": int(len(x)), "note": "too short"}
    st = boot.stat(x, L, scale=periods / len(x))           # mean log diff per year
    return {"n": int(len(x)), "per_year": st}


def arithmetic(w: Dict, cache: Dict) -> Dict:
    c = cash_acc(w)
    E = float(np.mean(w["e"] - c) * TD)
    T = float(np.mean(w["b"] - c) * TD)
    se = float(np.std(w["e"], ddof=1) * math.sqrt(TD))
    sb = float(np.std(w["b"], ddof=1) * math.sqrt(TD))
    rho = float(np.corrcoef(w["e"], w["b"])[0, 1])
    s = S_H1
    sp = float(np.std(0.9 * w["e"] + 0.6 * w["b"], ddof=1) * math.sqrt(TD))
    er_b = t311.ER["equity"]
    out = {"E": E, "T": T, "sigma_e": se, "sigma_b": sb, "rho": rho, "s": s,
           "arm_i": {"brief_delta_no_var": 0.6 * T - 0.1 * E - 0.5 * s - ER_PROD["NTSX"],
                     "delta_with_var_net_bench_er": 0.6 * T - 0.1 * E - 0.5 * s - (ER_PROD["NTSX"] - er_b)
                     - (sp ** 2 - se ** 2) / 2.0, "sigma_p": sp,
                     "brief_s_star": 2.0 * (0.6 * T - 0.1 * E - ER_PROD["NTSX"])},
           "arm_ii": {"delta_with_var_net_bench_er": T - s - (ER_PROD["RSSB"] - er_b)
                      - (sb ** 2 + 2 * rho * se * sb) / 2.0,
                      "s_star_with_var": T - (ER_PROD["RSSB"] - er_b) - (sb ** 2 + 2 * rho * se * sb) / 2.0}}
    if "g" in w and "rp" in cache:
        rp = cache["rp"]
        srp = float(np.std(rp, ddof=1) * math.sqrt(TD))
        sr = float(np.mean(rp - c) * TD) / _guard_std(srp, "rp vol")
        out["arm_iii"] = {"sigma_rp": srp, "levered_vol": L_III * srp, "realized_sr_rp": sr,
                          "breakeven_sr_brief_16_2": (E + 0.9 * s + ER_III) / 0.162,
                          "breakeven_sr_realized_vol": (E + 0.9 * s + ER_III) / (L_III * srp),
                          "delta_arith_no_var": L_III * sr * srp - 0.9 * s - ER_III - E}
    return out


def cmd_run(tag: str) -> int:
    man = verify_snapshot()
    val = load_validation()
    halted = set(val["verdict"]["halted_arms"])
    base = financing_base()
    sub = Substrate(base)
    rpw = rp_weights(sub)
    hn = honest_n()
    boot = Boot()
    outdir = B5 / f"run_{tag}"
    outdir.mkdir(parents=True, exist_ok=True)
    res: Dict = {"prereg": PREREG_REF,
                 "honest_n": hn, "validation_md5": md5_file(VALIDATION),
                 "validation_verdict": val["verdict"], "windows": {}, "monthly": {},
                 "census": {"inputs": {k: v["md5"] for k, v in man["files"].items()},
                            "substrate_md5": SUBSTRATE_MD5,
                            "bootstrap": {"n_iterations": N_ITER, "seed": SEED, "primary_block_daily": BLOCK_DAILY,
                                          "primary_block_monthly": BLOCK_MONTHLY, "sens2_daily": SENS2_DAILY,
                                          "sens2_monthly": SENS2_MONTHLY, "sens1": "max(5, round(n^(1/3)))"},
                            "windows": {}}}
    for wn, (s0, s1) in DAILY_WINDOWS.items():
        gold = "iii" in ARMS_BY_WINDOW[wn]
        w = sub.window(s0, s1, gold=gold)
        start, end = w["dates"][0], w["dates"][-1]
        years = (end - w["base_date"]).days / 365.25
        fg = fin_gap_check(base, start, end)
        ff = {leg: sub.ffill_runs(leg, start, end) for leg in ("equity", "bond")}
        if gold:
            ff["gold"] = sub.ffill_runs("gold", rpw.index[rpw.index.get_loc(w["base_date"]) - VOL_WIN], end)
        res["census"]["windows"][wn] = {"first": str(start.date()), "last": str(end.date()),
                                        "base_date": str(w["base_date"].date()), "n_days": len(w["dates"]),
                                        "years": years, "ffill": ff, "fin_max_gap_bd": fg}
        bench_ws = wealth_stats(w["bench"], w["dates"], w["base_date"], TD)
        cells: Dict = {"benchmark": {"stats": bench_ws, "sortino": sortino_ci(w["bench"], TD)}}
        frame = {"date": w["dates"].strftime("%Y-%m-%d"), "bench": w["bench"]}
        pos, neg = rho_years(w)
        ymask = lambda ys: np.isin(w["dates"].year, ys)  # noqa: E731
        m22 = w["dates"].year == 2022
        caches: Dict[str, Dict] = {}
        for arm in ARMS_BY_WINDOW[wn]:
            if arm in halted:
                cells[arm] = {"status": "NOT EVALUABLE — halted by validation"}
                continue
            cache = caches.setdefault(arm, {})
            c = cell_daily(arm, w, boot, rpw, hn, cache, years)
            R, d = c.pop("_R"), c.pop("_d")
            frame[f"arm_{arm}"] = R
            c["delta_max_dd"] = c["arm"]["max_dd"] - bench_ws["max_dd"]
            c["rho_pos_years"] = subsample(d, ymask(pos), boot, BLOCK_DAILY, TD)
            c["rho_nonpos_years"] = subsample(d, ymask(neg), boot, BLOCK_DAILY, TD)
            if m22.any():
                x = d[m22]
                st = boot.stat(x, BLOCK_DAILY)
                c["y2022"] = {"dlogTW": st,
                              "arm_max_dd": wealth_stats(R[m22], w["dates"][m22],
                                                         w["dates"][m22][0] - pd.Timedelta(days=1), TD)["max_dd"],
                              "bench_max_dd": wealth_stats(w["bench"][m22], w["dates"][m22],
                                                           w["dates"][m22][0] - pd.Timedelta(days=1), TD)["max_dd"]}
            if arm in ("i", "ii", "iii"):
                c["curve"] = curve_daily(arm, w, boot, rpw, cache, years)
            cells[arm] = c
        cells["rho_pos_years"], cells["rho_nonpos_years"] = pos, neg
        cells["arithmetic"] = arithmetic(w, caches.get("iii", {}))
        res["windows"][wn] = cells
        pd.DataFrame(frame).to_csv(outdir / f"returns_{wn}.csv", index=False, float_format="%.17g")
        print(f"  {wn} done ({len(w['dates'])} days)")
    # ---- H1 (quoted from MetricsEngine itself; the replay must match)
    h1 = res["windows"]["W-68"].get("ii", {})
    if "dlogTW" in h1:
        wh = sub.window(*DAILY_WINDOWS["W-68"], gold=False)
        Rh = arm_returns("ii", wh, S_H1)
        dh = log_diff(Rh, wh["bench"])
        me = me_sum_stat(dh, BLOCK_DAILY)
        rep = h1["dlogTW"]
        for k_me, k_rep in (("ci_low", "ci_low"), ("ci_high", "ci_high"), ("mean", "mean"),
                            ("point_estimate", "point")):
            if abs(me[k_me] - rep[k_rep]) > 1e-9:
                raise B5Halt(f"bootstrap replay != MetricsEngine on the H1 cell ({k_me}: {me[k_me]} vs {rep[k_rep]})")
        if me["n_iterations"] != N_ITER or me["block_length"] != BLOCK_DAILY:
            raise B5Halt("H1 bootstrap off-spec")
        me_auto = me_sum_stat(dh, None)
        yrs = h1["years"]
        ci_low = me["ci_low"]
        verdict = "H1 MET" if ci_low > 0 else "H1 NOT MET"
        res["H1"] = {"cell": "arm (ii) RSSB-synthetic 100/100, s = 50 bp, W-68, 21-day MBB, 1000 iter, seed 0",
                     "metricsengine": me, "metricsengine_auto_block": me_auto,
                     "per_year": {"point": me["point_estimate"] / yrs, "ci_low": ci_low / yrs,
                                  "ci_high": me["ci_high"] / yrs},
                     "verdict": verdict, "binding": h1["curve"]["binding"],
                     "s_star_ci": h1["curve"]["s_star_ci"], "s_star_point": h1["curve"]["s_star_point"],
                     "mbl": h1["mbl"], "replay_matches_metricsengine": True}
    else:
        res["H1"] = {"verdict": "NOT EVALUABLE", "reason": "arm (ii) halted by the NTSX/SSO/UPRO gate"}
    # ---- arm (iv): AQR refute-only, DBMF exploratory (monthly)
    eb = sub.px2.pct_change().dropna()
    rho_pos_all = [int(y) for y, g in eb.groupby(eb.index.year)
                   if float(np.corrcoef(g["equity"], g["bond"])[0, 1]) > 0]
    res["rho_pos_years_all"] = rho_pos_all
    for wn, (m0, m1, kind) in MONTHLY_WINDOWS.items():
        if "iv" in halted:
            res["monthly"][wn] = {"status": "NOT EVALUABLE — halted by validation"}
            continue
        mi = monthly_inputs(sub, kind, m0, m1)
        n = len(mi["months"])
        years = n / 12.0
        block = {}
        bench_m = mi["bench"]
        mframe = {"month": [str(m) for m in mi["months"]], "bench": bench_m, "tau": mi["tau"]}
        for wv in W_IV:
            R = arm_iv_monthly(mi["e"], mi["tau"], wv, S_H1)
            d = log_diff(R, bench_m)
            prim = boot.stat(d, BLOCK_MONTHLY)
            s1 = boot.stat(d, auto_block(n))
            s2 = boot.stat(d, SENS2_MONTHLY)
            for x in (prim, s1, s2):
                x["per_year"] = {k: x[k] / years for k in ("point", "ci_low", "ci_high", "mean")}
            mdates = mi["months"].to_timestamp(how="end").normalize()
            ws = wealth_stats(R, pd.DatetimeIndex(mdates), mi["months"][0].to_timestamp() - pd.Timedelta(days=1), 12)
            bws = wealth_stats(bench_m, pd.DatetimeIndex(mdates),
                               mi["months"][0].to_timestamp() - pd.Timedelta(days=1), 12)
            curve_lo, curve_pt = [], []
            for sbp in SPREADS_BP:
                Rs = arm_iv_monthly(mi["e"], mi["tau"], wv, sbp / 1e4)
                st = boot.stat(log_diff(Rs, bench_m), BLOCK_MONTHLY)
                curve_lo.append(st["ci_low"] / years)
                curve_pt.append(st["point"] / years)
            yrs_m = np.asarray(mi["months"].year)
            y22 = yrs_m == 2022
            cell = {"role": "REFUTE-ONLY (AQR over-captures)" if kind == "aqr" else "EXPLORATORY (DBMF live)",
                    "n_months": n, "years": years, "dlogTW": prim, "dlogTW_sens_auto": s1,
                    "dlogTW_sens_12m": s2, "arm": ws, "bench": bws, "delta_max_dd": ws["max_dd"] - bws["max_dd"],
                    "sortino": sortino_ci(R, 12), "mbl": mbl_line(ir_of(d, 12), years, hn),
                    "curve": {"spreads_bp": SPREADS_BP, "ci_low_per_year": curve_lo, "point_per_year": curve_pt,
                              "s_star_ci": crossing(SPREADS_BP, curve_lo),
                              "s_star_point": crossing(SPREADS_BP, curve_pt)}}
            if y22.any():
                cell["y2022"] = {"dlogTW": boot.stat(d[y22], BLOCK_MONTHLY)}
            cell["rho_pos_years"] = subsample(d, np.isin(yrs_m, rho_pos_all), boot, BLOCK_MONTHLY, 12)
            cell["rho_nonpos_years"] = subsample(d, ~np.isin(yrs_m, rho_pos_all), boot, BLOCK_MONTHLY, 12)
            block[f"w{int(wv*100)}"] = cell
            mframe[f"arm_iv_w{int(wv*100)}"] = R
        res["monthly"][wn] = {"kind": kind, "months": [str(mi["months"][0]), str(mi["months"][-1])], **block}
        pd.DataFrame(mframe).to_csv(outdir / f"returns_monthly_{wn}.csv", index=False, float_format="%.17g")
        print(f"  {wn} done ({n} months)")
    write_json(outdir / "results.json", res)
    files = sorted(p.name for p in outdir.iterdir() if p.name != "run_manifest.json")
    write_json(outdir / "run_manifest.json", {"files": {f: md5_file(outdir / f) for f in files}})
    print(f"run {tag} written: {outdir}")
    for f in files:
        print(f"  {md5_file(outdir / f)}  {f}")
    return 0


# --------------------------------------------------------------------------- CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("fetch")
    sp.add_parser("er-check")
    sp.add_parser("validate")
    sp.add_parser("smoke")
    pr = sp.add_parser("run")
    pr.add_argument("--tag", required=True, choices=["A", "B"])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "fetch":
            return cmd_fetch()
        if a.cmd == "er-check":
            return cmd_er_check()
        if a.cmd == "validate":
            return cmd_validate()
        if a.cmd == "smoke":
            return cmd_smoke()
        return cmd_run(a.tag)
    except B5Halt as exc:
        print(f"B5 HALT [NN-FAIL-CLOSED]: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
