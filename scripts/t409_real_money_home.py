"""T-409 — where the owner's real money should sit: an after-tax household decision study.

Pre-registration: docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md (revision 3, DRAFT until frozen).

Every arm is an ordinary manual choice at an institutional broker:
- keep the Schwab robo;
- leave the program without selling;
- hold a broad index fund;
- hold a 2x index ETF in the Roth.

Nothing here uses this project's trading machine, paper fleet or strategies.

Commands
    python -m scripts.t409_real_money_home fetch --inputs DIR --shiller-csv PATH [--env-file PATH] [--jst]
        Download the free inputs (Ken French daily factors; FRED CPIAUCNS through the API; optionally JST R6)
        and copy the Shiller dividend CSV. Writes DIR/manifest.json with each file's md5. The FRED key is
        read from the environment or --env-file and never printed.
    python -m scripts.t409_real_money_home run --inputs DIR --out DIR --control-root ROOT [--smoke]
        Verify the manifest, run the two positive controls (HALT if either fails), then the arms.
        Writes DIR/results.json and DIR/results.md5. Deterministic: fixed seed, no timestamps in the JSON.

Fail closed: any missing, unparseable or md5-mismatched input raises. Nothing is ever written under
ROOT/data/. The full run is authorised only after the prereg is frozen; use --smoke otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402

UA = "ArchonDEX-research/1.0"
SEED = 409
DAYS_YEAR = 365.25

# ----------------------------------------------------------------------------------------------------
# Frozen parameters (prereg rev. 3 §4.2–§4.3). Fund costs per year; spreads over the French 1-month bill.
# ----------------------------------------------------------------------------------------------------
ER = {"voo": 0.0003, "sso": 0.0089, "upro": 0.0090, "robo": 0.0015}
SPREAD = {"sso": 0.0057, "upro": 0.0056}          # B-5 measured swap spreads over B-5's financing base
BASE_ADJ = 0.0029                                  # B-5 base minus the French bill (T-399 R.6)
DIST = {"voo": None, "robo": None, "sso": 0.006, "upro": 0.005}   # None = Shiller D/P (equity funds)
ROBO_DY_UPLIFT = 0.006                             # intl/REIT uplift on the robo's yield [assumption]
ROBO_QUALIFIED = 0.80                              # qualified share of the robo's dividends [assumption]
ROBO_CASH = 0.06                                   # aggressive SIP cash allocation (brochure: 6-30 %)
SWEEP_HAIRCUT = 0.0030                             # sweep yield = bill - 0.30 %/yr, floored at 0
TLH_MIN_NOMINAL = 50_000.0                         # SIP TLH activation balance (brochure), held nominal
TLH_THETA = 0.05                                   # harvest when a lot is 5 % below basis [assumption]
ROBO_REBAL_REALIZE = 0.02                          # robo sells/rebuys 2 %/yr of equity [assumption]
SLIP = 0.51e-4                                     # per traded dollar (E's measured, T-315)
EXPOSURE = {"voo": 1.0, "robo": 1.0, "sso": 2.0, "upro": 3.0}

# 2026 federal parameters, single filer (Rev. Proc. 2025-32, read 2026-11-19/20).
BRACKETS_2026 = ((12_400, 0.10), (50_400, 0.12), (105_700, 0.22), (201_775, 0.24),
                 (256_225, 0.32), (640_600, 0.35), (math.inf, 0.37))
STD_DED_2026 = 16_100.0
ZERO_RATE_TOP_2026 = 49_450.0
FIFTEEN_TOP_2026 = 545_500.0
NIIT_THRESHOLD = 200_000.0                         # fixed nominal by statute
LOSS_OFFSET = 3_000.0                              # fixed nominal by statute

# Positive controls (prereg rev. 3 §4.9). Inputs are pinned by md5; targets are the published numbers.
CONTROL_FILES = {
    "t306_equity": ("data/research/substrate_multidecade/equity_tr_daily.csv", "c2030019b8846792b5f8e3d18421c905"),
    "t306_cash": ("data/research/substrate_multidecade/cash_daily.csv", "28a1446d578e3867c2a1d3b33eabe182"),
    "spy": ("data/processed/SPY_1d.csv", "7c44e6061906db4984f9bfa81982fa6e"),
    "bond": ("data/research/bond_synth_dgs10_t255.csv", "c3cde0a3cc21fdafc4f007d5c5000839"),
    "gold": ("data/research/gold_gcf_t255.csv", "77fa0313aef1deb32a0ef4a8ffc18323"),
    "dgs3mo": ("data/macro/DGS3MO.parquet", "549d04561c80bbce3658622126c68e02"),
    "t284_curves": ("data/research/t284/daily_curves.parquet", "303fe0856400d88f47a36ddf43a81447"),
}
CONTROL_TARGETS = {
    # T-399 R.2, D-B 1968-01-02 -> 2026-04-17, $10,000 (static_leverage_t315_2026_07_27.md:334-342)
    "t399_bar": 3_363_893.0, "t399_static_2x": 8_864_568.0,
    # T-287 canonical, $7,000 each January from 2000-10-30 (dividend_reconcile_verdict_t287_2026_07_07.md:46-53)
    "t287_bh_spy": 929_498.0, "t287_schwab_like": 494_701.0,
}
CONTROL_TOL_DOLLARS = 1.0

INPUT_NAMES = {"french": "F-F_Research_Data_Factors_daily_CSV.zip", "cpi": "fred_CPIAUCNS.csv",
               "shiller": "shiller_ie_data.csv", "jst": "JSTdatasetR6.xlsx"}
FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip"
JST_URL = "https://www.macrohistory.net/app/download/9834512569/JSTdatasetR6.xlsx"
MAX_DP_CARRY_MONTHS = 30
# The frozen inputs (fetched 2026-11-20). A re-fetch will NOT reproduce them: French updates monthly and FRED
# adds a month of CPI each month. `run` halts unless every input file has exactly this md5.
INPUT_MD5 = {"french": "98fad1a66fe8c9e792fcd013b979b962", "cpi": "74ac80ebee616f81dd98d5ec2a5934e1",
             "shiller": "6e1e19fa864401cf66f8b022619efec1", "jst": "76884a335991ece55366255bd629d312"}
CANDIDATES_A = ("K0", "K1")
CANDIDATES_B = ("K1", "B1", "B2", "B3")
DEFAULT_ARM = "K1"
STUDY_CONTROL_START = "1990-01"
STUDY_CONTROL_MONTHS = 120
STUDY_CONTROL_TOL = 0.01


class InputError(RuntimeError):
    """A load-bearing input is missing, unparseable, stale or md5-mismatched. The run halts."""


class ControlFailed(RuntimeError):
    """A positive control did not reproduce its published number. The run halts."""


# ----------------------------------------------------------------------------------------------------
# Owner profile and study configuration
# ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Owner:
    """Owner facts (2026-11-20 answers) and labelled defaults; real 2026 dollars."""
    taxable0: float = 25_000.0       # owner: under $50,000
    g: float = 0.15                  # embedded gain fraction of the legacy robo balance (grid 0, .15, .30)
    roth0: float = 15_000.0          # owner: $10-25k
    c_taxable_month: float = 500.0   # automatic contribution, continues through every fall
    roth_contrib: float = 7_500.0    # each January of a contribution year
    roth_in_school: bool = True      # rev. 2 §4.4: a school year contributes iff its wages >= the contribution
    roth_post_school: bool = True    # † backdoor Roth: $160k sits inside the 2026 single $153k-$168k phase-out
    school_start: int = 3            # 1-based year of the first school year (owner: more than a year away)
    school_years: int = 3
    wages_pre: float = 60_000.0
    wages_school: float = 8_000.0
    wages_post: float = 160_000.0
    liq_wages: float = 160_000.0     # wages in the year-40 liquidation year; the sale goes through annual_tax
    state_rate: float = 0.05
    horizon_years: int = 40
    real_discount: float = 0.01
    tlh_theta: float = TLH_THETA            # robo harvest threshold (Schwab does not disclose it)
    robo_rebal: float = ROBO_REBAL_REALIZE  # robo's yearly realised-sale share of equity [assumption]
    liquidate: bool = True                  # False = hold for step-up: no tax on the year-40 gain


@dataclass(frozen=True)
class Config:
    horizon_years: int = 40
    cohort_starts: Tuple[int, ...] = tuple(range(1927, 1987))
    n_paths: int = 2000
    block_mean: int = 60
    block_sensitivity: Tuple[int, ...] = (12, 120)
    rows: Tuple[float, ...] = (0.0, -0.01, -0.02, -0.03)
    param_rows: Tuple[float, ...] = (0.0, -0.02)
    param_se: float = 0.0183
    g_grid: Tuple[float, ...] = (0.0, 0.15, 0.30)
    g_primary: float = 0.15
    loss_bound: float = 0.5
    owner_sensitivity: Tuple[Tuple[str, Tuple[Tuple[str, object], ...]], ...] = (
        ("roth_10k", (("roth0", 10_000.0),)), ("roth_25k", (("roth0", 25_000.0),)),
        ("taxable_10k", (("taxable0", 10_000.0),)), ("taxable_45k", (("taxable0", 45_000.0),)),
        ("school_year6", (("school_start", 6),)), ("contrib_250", (("c_taxable_month", 250.0),)),
        ("contrib_1000", (("c_taxable_month", 1_000.0),)), ("tlh_theta_3pct", (("tlh_theta", 0.03),)),
        ("tlh_theta_10pct", (("tlh_theta", 0.10),)), ("robo_rebal_0", (("robo_rebal", 0.0),)),
        ("robo_rebal_5pct", (("robo_rebal", 0.05),)), ("step_up", (("liquidate", False),)),
        ("no_roth_post_school", (("roth_post_school", False),)), ("no_roth_in_school", (("roth_in_school", False),)),
    )
    owner_sensitivity_rows: Tuple[float, ...] = (0.0, -0.02)
    decision_row: Optional[str] = None       # the owner's row, fixed BEFORE the run and recorded in the frozen prereg
    seed: int = SEED
    smoke: bool = False


SMOKE = Config(horizon_years=10, cohort_starts=tuple(range(1990, 1997)), n_paths=16, block_mean=24,
               block_sensitivity=(), rows=(0.0, -0.02), param_rows=(), g_grid=(0.0, 0.30), g_primary=0.30,
               owner_sensitivity=(("roth_25k", (("roth0", 25_000.0),)), ("step_up", (("liquidate", False),))),
               owner_sensitivity_rows=(0.0,), smoke=True)


# ----------------------------------------------------------------------------------------------------
# I/O helpers (fail closed)
# ----------------------------------------------------------------------------------------------------
def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_file(path: Path, expected_md5: Optional[str] = None) -> Path:
    if not path.is_file():
        raise InputError(f"missing input: {path}")
    if expected_md5 is not None:
        got = md5_of(path)
        if got != expected_md5:
            raise InputError(f"md5 mismatch for {path}: expected {expected_md5}, got {got}")
    return path


def read_manifest(inputs: Path, need: Iterable[str],
                  pinned: Optional[Dict[str, str]] = INPUT_MD5) -> Dict[str, Path]:
    man_path = require_file(inputs / "manifest.json")
    try:
        man = json.loads(man_path.read_text())
    except json.JSONDecodeError as exc:
        raise InputError(f"unparseable manifest {man_path}: {exc}") from exc
    out = {}
    for key in need:
        name = INPUT_NAMES[key]
        if name not in man.get("files", {}):
            raise InputError(f"manifest lacks {name}")
        out[key] = require_file(inputs / name, man["files"][name])
        if pinned is not None and md5_of(out[key]) != pinned[key]:
            raise InputError(f"{name} is not the frozen input: md5 {md5_of(out[key])} != {pinned[key]}")
    return out


# ----------------------------------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------------------------------
def load_french_daily(path: Path) -> pd.DataFrame:
    """Ken French daily factors -> DataFrame[mkt_rf, rf] in decimals, DatetimeIndex. Sentinels halt."""
    with zipfile.ZipFile(path) as z:
        text = z.read(z.namelist()[0]).decode("latin-1")
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5 and len(parts[0]) == 8 and parts[0].isdigit():
            rows.append((parts[0], parts[1], parts[4]))
    if len(rows) < 1000:
        raise InputError(f"French daily file has {len(rows)} daily rows")
    df = pd.DataFrame(rows, columns=["date", "mkt_rf", "rf"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df[["mkt_rf", "rf"]] = df[["mkt_rf", "rf"]].astype(float)
    if (df[["mkt_rf", "rf"]] <= -99.0).any().any():
        raise InputError("French daily file contains a missing-data sentinel (-99.99 / -999)")
    df = df.set_index("date").sort_index()
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise InputError("French daily dates are not strictly increasing")
    gaps = df.index.to_series().diff().dt.days.dropna()
    if (gaps > 15).any():
        raise InputError(f"French daily calendar hole of {int(gaps.max())} days")
    return df / 100.0


# BLS never published October 2025 CPI (the federal shutdown); FRED has no observation. This one declared
# month is filled by geometric interpolation of its neighbours; any other missing month halts.
KNOWN_CPI_GAPS = ("2025-10",)


def load_cpi(path: Path) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"])
    s = df.set_index("date")["value"].astype(float).sort_index()
    s.index = s.index.to_period("M")
    if s.isna().any() or (s <= 0).any():
        raise InputError("CPI series has missing or non-positive values")
    full = pd.period_range(s.index[0], s.index[-1], freq="M")
    missing = full.difference(s.index)
    undeclared = [str(p) for p in missing if str(p) not in KNOWN_CPI_GAPS]
    if undeclared:
        raise InputError(f"CPI series has missing months: {undeclared}")
    s = s.reindex(full)
    for p in missing:
        lo, hi = s.get(p - 1), s.get(p + 1)
        if lo is None or hi is None or not (np.isfinite(lo) and np.isfinite(hi)):
            raise InputError(f"declared CPI gap {p} lacks both neighbours")
        s[p] = math.sqrt(lo * hi)
    return s


def load_dividend_yield(path: Path, last_month: pd.Period) -> Tuple[pd.Series, int]:
    """Shiller D/P (annual) by month from the repo CSV; carried forward past the last dividend, capped."""
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.dropna(subset=["price"]).set_index("date").sort_index()
    have = df.dropna(subset=["dividend"])
    if have.empty:
        raise InputError("Shiller CSV has no dividends")
    dp = (have["dividend"] / have["price"]).astype(float)
    dp.index = dp.index.to_period("M")
    full = pd.period_range(dp.index[0], last_month, freq="M")
    carried = int((full > dp.index[-1]).sum())
    if carried > MAX_DP_CARRY_MONTHS:
        raise InputError(f"dividend yield would be carried {carried} months (> {MAX_DP_CARRY_MONTHS})")
    inside = dp.reindex(pd.period_range(dp.index[0], dp.index[-1], freq="M"))
    if inside.isna().any():
        raise InputError("Shiller dividend yield has gaps inside its span")
    return dp.reindex(full).ffill(), carried


# ----------------------------------------------------------------------------------------------------
# Vehicles (shared by the study and control 1)
# ----------------------------------------------------------------------------------------------------
def accrual_fractions(index: pd.DatetimeIndex, mode: str) -> Tuple[np.ndarray, np.ndarray]:
    """Per-bar year fractions (fee basis 365.25, financing basis 360). 'bar252' reproduces T-315."""
    if mode == "bar252":
        f = np.full(len(index), 1.0 / 252.0)
        return f, f
    if mode != "calendar":
        raise ValueError(mode)
    d = np.diff(index.values).astype("timedelta64[D]").astype(float)
    d = np.concatenate([[1.0], d])
    return d / DAYS_YEAR, d / 360.0


def levered_fund_returns(gross: np.ndarray, financing: np.ndarray, L: float, spread: float, er: float,
                         fee_frac: np.ndarray, fin_frac: np.ndarray) -> np.ndarray:
    """Daily-reset L-x fund: L*gross - (L-1)*(financing + spread) - ER, all per bar."""
    out = L * gross - (L - 1.0) * (financing + spread * fin_frac)
    if L > 1.0:
        out = out - er * fee_frac
    return out


def year_change_mask(index: pd.DatetimeIndex) -> np.ndarray:
    """True on the first bar and on the first bar of each later calendar year (positional, T-399)."""
    years = np.asarray(index.year)
    first = np.ones(len(years), dtype=bool)
    first[1:] = years[1:] != years[:-1]
    return first


# ----------------------------------------------------------------------------------------------------
# Positive controls
# ----------------------------------------------------------------------------------------------------
def control_t399(root: Path) -> Dict[str, float]:
    """T-399 corrected static 2x on T-306 D-B, $10k, frozen T-315 conventions (bar252, add-back)."""
    eq_p = require_file(root / CONTROL_FILES["t306_equity"][0], CONTROL_FILES["t306_equity"][1])
    ca_p = require_file(root / CONTROL_FILES["t306_cash"][0], CONTROL_FILES["t306_cash"][1])
    eq = pd.read_csv(eq_p, parse_dates=[0], index_col=0).iloc[:, 0].sort_index().dropna()
    cash = pd.read_csv(ca_p, parse_dates=[0], index_col=0).iloc[:, 0].sort_index()
    r = eq.pct_change().dropna()
    c = cash.reindex(eq.index).ffill().fillna(0.0).reindex(r.index).ffill().fillna(0.0)
    m = r.index >= pd.Timestamp("1968-01-01")
    r, c = r[m], c[m]
    bar = r.values - 0.0009 / 252.0
    fee, fin = accrual_fractions(r.index, "bar252")
    lev = levered_fund_returns(r.values + 0.0009 / 252.0, c.values, 2.0, 0.0060, 0.0089, fee, fin)
    lev = lev - np.where(year_change_mask(r.index), SLIP, 0.0)
    return {"t399_bar": float(10_000 * np.prod(1 + bar)), "t399_static_2x": float(10_000 * np.prod(1 + lev)),
            "window": [str(r.index[0].date()), str(r.index[-1].date())]}


def robo_daily(closes: Dict[str, pd.Series], weights: Dict[str, float], er: Dict[str, float],
               cash_daily: pd.Series, txn: float = 0.00015) -> pd.Series:
    """Monthly-rebalanced proxy (T-287 robo_clean): legs net of ER, cash at the bill, 1.5 bp turnover."""
    etfs = [k for k in weights if k != "_cash"]
    cw = weights.get("_cash", 0.0)
    rets = pd.concat({k: closes[k].pct_change() - er[k] / 252.0 for k in etfs}, axis=1, sort=True).dropna()
    cr = cash_daily.reindex(rets.index).ffill().fillna(0.0).values
    hold = np.array([weights[k] for k in etfs], dtype=float)
    w = hold.copy()
    cash = cw
    out = np.empty(len(rets))
    months = rets.index.year * 12 + rets.index.month
    vals = rets.values
    for i in range(len(rets)):
        rc = 0.0
        if i > 0 and months[i] != months[i - 1]:
            tot = hold.sum() + cash
            nh = tot * w
            rc = np.abs(nh - hold).sum() / max(tot, 1e-9) * txn
            hold, cash = nh, tot * cw
        prev = hold.sum() + cash
        hold = hold * (1 + vals[i])
        cash = cash * (1 + cr[i])
        out[i] = (hold.sum() + cash) / prev - 1 - rc
    return pd.Series(out, index=rets.index)


def accumulate_annual(r: pd.Series, start: str, contrib: float) -> float:
    """Contribute each January (first bar of each calendar year from `start`), compound daily."""
    r = r[r.index >= pd.Timestamp(start)].dropna()
    first = year_change_mask(r.index)
    w = 0.0
    for add, x in zip(first, r.values):
        if add:
            w += contrib
        w *= 1.0 + x
    return float(w)


def control_t287(root: Path) -> Dict[str, float]:
    """T-287 canonical: buy-hold SPY TR and the schwab_like proxy, $7k each January from 2000-10-30."""
    paths = {k: require_file(root / CONTROL_FILES[k][0], CONTROL_FILES[k][1])
             for k in ("spy", "bond", "gold", "dgs3mo", "t284_curves")}
    spy = pd.read_csv(paths["spy"], usecols=["Date", "Close"])
    spy = pd.Series(spy["Close"].astype(float).values,
                    index=pd.to_datetime(spy["Date"].str[:10])).sort_index()

    def ser(p: Path) -> pd.Series:
        d = pd.read_csv(p, index_col=0)
        d.index = pd.to_datetime(d.index)
        return d.iloc[:, 0].astype(float).sort_index()

    d3 = pd.read_parquet(paths["dgs3mo"])["value"].astype(float)
    d3.index = pd.to_datetime(d3.index)
    d3 = (d3.dropna().sort_index() / 100.0 / 252.0)
    d3 = d3.reindex(pd.date_range(d3.index[0], d3.index[-1], freq="D")).ffill()
    closes = {"SPY": spy, "BOND": ser(paths["bond"]), "GOLD": ser(paths["gold"])}
    er = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
    schwab = robo_daily(closes, {"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20}, er, d3)
    curves = pd.read_parquet(paths["t284_curves"])
    curves.index = pd.to_datetime(curves.index)
    bh = curves["bh_spy"].dropna()
    # Diagnostics, never gating: the published T-287 inputs drop the days the bond synthetic lacks (an
    # inner join / T-284's holey calendar, the T-297 defect class). Calendar-complete versions put the
    # bond and gold legs on SPY's calendar with a zero return on their missing days.
    end = pd.Timestamp("2025-12-31")
    spy_r = spy.pct_change().dropna()          # like for like: T-284's bh_spy curve carries no fund fee
    spy_r = spy_r[spy_r.index <= end]
    full_closes = {k: (v.reindex(spy.index).ffill() if k != "SPY" else v) for k, v in closes.items()}
    schwab_full = robo_daily(full_closes, {"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20}, er, d3)
    missing = int(len(spy_r[spy_r.index >= bh.index[0]].index.difference(bh.index)))
    return {"t287_bh_spy": accumulate_annual(bh, "2000-10-30", 7_000.0),
            "t287_schwab_like": accumulate_annual(schwab, "2000-10-30", 7_000.0),
            "diag_bh_spy_calendar_complete": accumulate_annual(spy_r, "2000-10-30", 7_000.0),
            "diag_schwab_like_calendar_complete": accumulate_annual(schwab_full[schwab_full.index <= end],
                                                                     "2000-10-30", 7_000.0),
            "diag_spy_days_missing_from_t284_curve": missing}


def run_controls(root: Path) -> Dict[str, object]:
    """Both controls must reproduce to within $1; otherwise HALT before any arm is computed."""
    got = {**control_t399(root), **control_t287(root)}
    checks = {}
    for key, target in CONTROL_TARGETS.items():
        diff = abs(got[key] - target)
        checks[key] = {"target": target, "reproduced": round(got[key], 2), "abs_diff": round(diff, 4),
                       "pass": bool(diff <= CONTROL_TOL_DOLLARS)}
    failed = [k for k, v in checks.items() if not v["pass"]]
    if failed:
        raise ControlFailed(f"positive controls did not reproduce: {failed}: {checks}")
    diag = {k: got[k] for k in got if k.startswith("diag_")}
    return {"checks": checks, "t399_window": got["window"], "diagnostics_not_gating": diag}


# ----------------------------------------------------------------------------------------------------
# The monthly panel (L1)
# ----------------------------------------------------------------------------------------------------
def build_monthly_panel(french: pd.DataFrame, cpi: pd.Series, dp: pd.Series) -> pd.DataFrame:
    """Daily funds compounded to calendar months. Columns are monthly simple returns unless named."""
    idx = french.index
    gross = (french["mkt_rf"] + french["rf"]).values
    rf = french["rf"].values
    fee, fin = accrual_fractions(idx, "calendar")
    daily = pd.DataFrame({
        "voo": gross - ER["voo"] * fee,
        "robo": gross - ER["robo"] * fee,
        "sso": levered_fund_returns(gross, rf, 2.0, SPREAD["sso"] + BASE_ADJ, ER["sso"], fee, fin),
        "upro": levered_fund_returns(gross, rf, 3.0, SPREAD["upro"] + BASE_ADJ, ER["upro"], fee, fin),
        "rf": rf,
        "days": fee * DAYS_YEAR,
    }, index=idx)
    per = idx.to_period("M")
    g = daily.groupby(per)
    panel = pd.DataFrame({c: g[c].apply(lambda x: float(np.prod(1.0 + x.values) - 1.0))
                          for c in ("voo", "robo", "sso", "upro", "rf")})
    panel["days"] = g["days"].sum()
    panel["cash_robo"] = np.maximum(0.0, (1 + panel["rf"]) * np.exp(-SWEEP_HAIRCUT * panel["days"] / DAYS_YEAR) - 1)
    first, last = panel.index[0], panel.index[-1]
    if first - 1 < cpi.index[0] or last > cpi.index[-1]:
        raise InputError(f"CPI does not cover {first}..{last}")
    c = cpi.reindex(pd.period_range(first - 1, last, freq="M"))
    panel["infl"] = (c.values[1:] / c.values[:-1]) - 1.0
    d = dp.reindex(panel.index)
    if d.isna().any():
        raise InputError("dividend yield does not cover the panel")
    panel["dy"] = d.values / 12.0
    if panel.isna().any().any():
        raise InputError("monthly panel has missing values")
    return panel


def apply_belief(panel_arrays: Dict[str, np.ndarray], h: float) -> Dict[str, np.ndarray]:
    """Shift the arithmetic equity return by h per year of calendar time, scaled by each fund's exposure."""
    out = dict(panel_arrays)
    if h == 0.0:
        return out
    t = panel_arrays["days"] / DAYS_YEAR
    for f, k in EXPOSURE.items():
        out[f] = (1.0 + panel_arrays[f]) * np.exp(k * h * t) - 1.0
    return out


def stationary_bootstrap(n_obs: int, length: int, n_paths: int, block_mean: int,
                         rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap of month indices (circular), shape (n_paths, length)."""
    out = np.empty((n_paths, length), dtype=np.int64)
    p = 1.0 / block_mean
    for k in range(n_paths):
        i = rng.integers(n_obs)
        jumps = rng.random(length) < p
        starts = rng.integers(n_obs, size=length)
        for t in range(length):
            if t > 0:
                i = starts[t] if jumps[t] else (i + 1) % n_obs
            out[k, t] = i
    return out


# ----------------------------------------------------------------------------------------------------
# Lots and tax
# ----------------------------------------------------------------------------------------------------
class LotBook:
    """Tax lots of one fund in the taxable account. All lots share the fund's price-only index.

    `wash_carry` holds losses disallowed by the wash-sale rule (a repurchase within 30 days); they are added to
    the basis of the next purchase (the replacement), and count against the gain if no purchase follows."""

    def __init__(self, cap: int = 256) -> None:
        self.shares = np.zeros(cap)
        self.basis = np.zeros(cap)
        self.month = np.zeros(cap, dtype=np.int64)
        self.n = 0
        self.total_shares = 0.0
        self.total_basis = 0.0
        self.wash_carry = 0.0

    def _slot(self, t: int) -> int:
        if self.n and self.month[self.n - 1] == t and self.shares[self.n - 1] > 0:
            return self.n - 1
        if self.n == len(self.shares):
            for name in ("shares", "basis", "month"):
                arr = getattr(self, name)
                setattr(self, name, np.concatenate([arr, np.zeros_like(arr)]))
        i = self.n
        self.n += 1
        self.shares[i] = 0.0
        self.basis[i] = 0.0
        self.month[i] = t
        return i

    def buy(self, dollars: float, price: float, t: int, basis: Optional[float] = None) -> None:
        if dollars <= 0:
            return
        i = self._slot(t)
        sh = dollars / price
        b = dollars if basis is None else basis
        if self.wash_carry > 0:
            b += self.wash_carry
            self.wash_carry = 0.0
        self.shares[i] += sh
        self.basis[i] += b
        self.total_shares += sh
        self.total_basis += b

    def value(self, price: float) -> float:
        return self.total_shares * price

    def gain(self, price: float) -> float:
        return self.value(price) - self.total_basis - self.wash_carry

    def _take(self, order: np.ndarray, dollars: float, price: float, t: int,
              wash: bool = False) -> Tuple[float, float, float]:
        """Sell `dollars` taking lots in `order`; returns (proceeds, st_gain, lt_gain). With `wash`, a lot's
        loss is disallowed (a repurchase follows within 30 days) and moves to `wash_carry`."""
        vals = self.shares[order] * price
        cum = np.cumsum(vals)
        k = int(np.searchsorted(cum, dollars, side="left"))
        full = order[:k] if k < len(order) else order
        frac_i, frac = None, 0.0
        if k < len(order):
            prev = cum[k - 1] if k > 0 else 0.0
            frac_i, frac = order[k], (dollars - prev) / vals[k] if vals[k] > 0 else 0.0
        st = lt = proceeds = 0.0
        for idx, f in [(i, 1.0) for i in full] + ([(frac_i, frac)] if frac_i is not None else []):
            if f <= 0:
                continue
            sh = self.shares[idx] * f
            b = self.basis[idx] * f
            gain = sh * price - b
            if wash and gain < 0:
                self.wash_carry += -gain
            elif t - self.month[idx] >= 12:
                lt += gain
            else:
                st += gain
            proceeds += sh * price
            self.shares[idx] -= sh
            self.basis[idx] -= b
            self.total_shares -= sh
            self.total_basis -= b
        return proceeds, st, lt

    def live(self) -> np.ndarray:
        return np.nonzero(self.shares[: self.n] > 1e-12)[0]

    def sell_hifo(self, dollars: float, price: float, t: int, wash: bool = False) -> Tuple[float, float, float]:
        """Highest basis per share first (the lowest gain per dollar sold)."""
        live = self.live()
        if len(live) == 0 or dollars <= 0:
            return 0.0, 0.0, 0.0
        bps = self.basis[live] / self.shares[live]
        order = live[np.argsort(-bps, kind="stable")]
        return self._take(order, min(dollars, self.value(price)), price, t, wash)

    def harvest(self, price: float, t: int, theta: float) -> Tuple[float, float]:
        """Realise every lot whose value is >= theta below its basis; the replacement keeps the shares."""
        live = self.live()
        if len(live) == 0:
            return 0.0, 0.0
        v = self.shares[live] * price
        hit = live[v < self.basis[live] * (1.0 - theta)]
        st = lt = 0.0
        for i in hit:
            loss = self.shares[i] * price - self.basis[i]
            if t - self.month[i] >= 12:
                lt += loss
            else:
                st += loss
            self.total_basis += self.shares[i] * price - self.basis[i]
            self.basis[i] = self.shares[i] * price
            self.month[i] = t
        return st, lt

    def realize_gains_prorata(self, frac: float, price: float, t: int) -> Tuple[float, float]:
        """The robo's sell-and-rebuy: `frac` of every lot is sold and immediately rebought. A gain lot realises
        frac x its gain (the rebought shares start a new lot at value). A loss lot changes nothing: a loss on an
        immediate rebuy is a wash sale and its basis and holding period carry to the replacement."""
        live = self.live()
        st = lt = moved = 0.0
        if frac <= 0 or len(live) == 0:
            return 0.0, 0.0
        for i in live:
            v, b = self.shares[i] * price, self.basis[i]
            if v <= b:
                continue
            sh, bf = self.shares[i] * frac, b * frac
            g = sh * price - bf
            if t - self.month[i] >= 12:
                lt += g
            else:
                st += g
            self.shares[i] -= sh
            self.basis[i] -= bf
            self.total_shares -= sh
            self.total_basis -= bf
            moved += sh * price
        if moved > 0:
            j = self._slot(t)
            self.shares[j] += moved / price
            self.basis[j] += moved
            self.total_shares += moved / price
            self.total_basis += moved
        return st, lt

    def realize_lt_gains_upto(self, room: float, price: float, t: int) -> Tuple[float, float]:
        """Sell long-term gain lots, largest gain per dollar first, until `room` of gain is realised.

        Returns (proceeds, lt_gain). Used for the school-year 0 % window (S1)."""
        live = self.live()
        if room <= 0 or len(live) == 0:
            return 0.0, 0.0
        v = self.shares[live] * price
        gfrac = (v - self.basis[live]) / v
        ok = (gfrac > 0) & ((t - self.month[live]) >= 12)
        cand = live[ok]
        if len(cand) == 0:
            return 0.0, 0.0
        order = cand[np.argsort(-gfrac[ok], kind="stable")]
        proceeds = lt = 0.0
        for i in order:
            val = self.shares[i] * price
            gain = val - self.basis[i]
            f = min(1.0, (room - lt) / gain) if gain > 0 else 0.0
            if f <= 0:
                break
            p_, s_, l_ = self._take(np.array([i]), val * f, price, t)
            proceeds += p_
            lt += l_ + s_
            if lt >= room - 1e-9:
                break
        return proceeds, lt


def bracket_tax(taxable: float, idx: float) -> float:
    """Ordinary federal tax on `taxable` with 2026 single brackets scaled by the CPI index `idx`."""
    tax, lo = 0.0, 0.0
    for top, rate in BRACKETS_2026:
        hi = top * idx
        if taxable <= lo:
            break
        tax += (min(taxable, hi) - lo) * rate
        lo = hi
    return tax


@dataclass
class TaxYear:
    qual: float = 0.0
    ordinary: float = 0.0
    st: float = 0.0
    lt: float = 0.0


def annual_tax(y: TaxYear, wages: float, idx: float, state: float,
               st_cf: float, lt_cf: float) -> Tuple[float, float, float, Dict[str, float]]:
    """Incremental tax caused by the taxable account in one year (nominal), Form 1040 order.

    Taxable income may be negative before its zero floor (wages below the standard deduction shelter
    investment income). Netting and carryovers follow Schedule D and its Capital Loss Carryover Worksheet
    (the $3,000 deduction is not used up by a year whose taxable income is negative). Preferential income
    follows the Qualified Dividends and Capital Gain Tax Worksheet (including its "smaller of" step). NIIT
    (Form 8960) counts the capped $3,000 loss. Wages' own tax is common to every arm and excluded.
    Brackets, the standard deduction and the 0 %/15 % thresholds are CPI-indexed by `idx`; the $200,000
    NIIT threshold and the $3,000 deduction are nominal-fixed. Returns (tax, new_st_cf, new_lt_cf, detail).
    """
    net_st = y.st - st_cf
    net_lt = y.lt - lt_cf
    total = net_st + net_lt
    std = STD_DED_2026 * idx
    ded = 0.0
    if total >= 0:
        if net_st < 0:
            st_pos, lt_pos = 0.0, total
        elif net_lt < 0:
            st_pos, lt_pos = total, 0.0
        else:
            st_pos, lt_pos = net_st, net_lt
        cap_line = st_pos + lt_pos
    else:
        st_pos = lt_pos = 0.0
        ded = min(LOSS_OFFSET, -total)
        cap_line = -ded
    qual = max(0.0, y.qual)
    other = y.ordinary + qual
    ti_raw = wages + other + cap_line - std
    ti = max(0.0, ti_raw)
    new_st_cf = new_lt_cf = 0.0
    used = 0.0
    if total < 0:
        used = min(ded, max(0.0, ti_raw + ded))
        st_loss, lt_loss = max(0.0, -net_st), max(0.0, -net_lt)
        st_gain, lt_gain = max(0.0, net_st), max(0.0, net_lt)
        new_st_cf = max(0.0, st_loss - (used + lt_gain))
        new_lt_cf = max(0.0, lt_loss - (st_gain + max(0.0, used - st_loss)))
    pref = min(qual + lt_pos, ti)
    ord_ti = ti - pref
    z0, z15 = ZERO_RATE_TOP_2026 * idx, FIFTEEN_TOP_2026 * idx
    at0 = min(ti, z0) - min(ord_ti, min(ti, z0))
    rest = pref - at0
    at15 = min(rest, max(0.0, min(ti, z15) - (ord_ti + at0)))
    at20 = rest - at15
    pref_tax = 0.15 * at15 + 0.20 * at20
    base_ti = max(0.0, wages - std)
    fed_ord = bracket_tax(ord_ti, idx) - bracket_tax(base_ti, idx)
    nii = max(0.0, other + cap_line)
    magi = wages + other + cap_line
    niit = 0.038 * min(nii, max(0.0, magi - NIIT_THRESHOLD))
    st_tax = state * max(0.0, other + cap_line)
    tax = fed_ord + pref_tax + niit + st_tax
    detail = {"fed_ord": fed_ord, "pref": pref_tax, "fed": fed_ord + pref_tax, "niit": niit, "state": st_tax,
              "at0": at0, "deduction": ded, "deduction_used": used, "taxable_income": ti}
    return tax, new_st_cf, new_lt_cf, detail


def zero_rate_room(y: TaxYear, wages: float, idx: float, st_cf: float, lt_cf: float) -> float:
    """Largest extra long-term gain this year that adds no federal tax (income tax + NIIT), found by bisection
    on `annual_tax` itself, so it counts the unused standard deduction and any loss being absorbed."""
    def fed(x: float) -> float:
        _, _, _, d = annual_tax(TaxYear(qual=y.qual, ordinary=y.ordinary, st=y.st, lt=y.lt + x),
                                wages, idx, 0.0, st_cf, lt_cf)
        return d["fed"] + d["niit"]

    base = fed(0.0)
    hi = (ZERO_RATE_TOP_2026 + STD_DED_2026) * idx + abs(y.st) + abs(y.lt) + st_cf + lt_cf + LOSS_OFFSET + 1.0
    if fed(hi) <= base + 1e-6:
        return hi
    lo = 0.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if fed(mid) <= base + 1e-6:
            lo = mid
        else:
            hi = mid
    return lo


# ----------------------------------------------------------------------------------------------------
# Arms
# ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Arm:
    name: str
    taxable: str          # "ref" | "robo" | "k1" | "s0" | "s1" | "b4"
    roth: str = "voo"     # "voo" | "life" | "static"
    lev_fund: str = "sso"
    cap: float = 2.0
    static_L: float = 1.25
    tlh: bool = True
    primary: bool = True
    decision: str = "A"


ARMS: Tuple[Arm, ...] = (
    Arm("REF", "ref", primary=False, decision="ref"),
    Arm("K0", "robo"),
    Arm("K0_noTLH", "robo", tlh=False, primary=False),
    Arm("K1", "k1"),
    Arm("S0", "s0", primary=False),
    Arm("S1", "s1", primary=False),
    Arm("B1", "k1", roth="life", cap=2.0, decision="B"),
    Arm("B2", "k1", roth="life", cap=1.5, decision="B"),
    Arm("B3", "k1", roth="static", static_L=1.25, decision="B"),
    Arm("B4", "b4", roth="voo", cap=2.0, primary=False, decision="B"),
    Arm("B1_upro", "k1", roth="life", cap=2.0, lev_fund="upro", primary=False, decision="B"),
    Arm("B2_upro", "k1", roth="life", cap=1.5, lev_fund="upro", primary=False, decision="B"),
    Arm("B3_upro", "k1", roth="static", static_L=1.25, lev_fund="upro", primary=False, decision="B"),
)


@dataclass
class PathInputs:
    """One path: monthly arrays of length T (months), plus derived price-only indices."""
    r: Dict[str, np.ndarray]
    dist: Dict[str, np.ndarray]
    price: Dict[str, np.ndarray]
    cpi_idx: np.ndarray
    cash_robo: np.ndarray


def make_path(arrays: Dict[str, np.ndarray]) -> PathInputs:
    dy = arrays["dy"]
    dist = {"voo": dy, "robo": dy + ROBO_DY_UPLIFT / 12.0,
            "sso": np.full_like(dy, DIST["sso"] / 12.0), "upro": np.full_like(dy, DIST["upro"] / 12.0)}
    r = {f: arrays[f] for f in ("voo", "robo", "sso", "upro")}
    price = {}
    for f in r:
        pf = (1.0 + r[f]) / (1.0 + dist[f])
        price[f] = np.concatenate([[1.0], np.cumprod(pf)])
    cpi_idx = np.concatenate([[1.0], np.cumprod(1.0 + arrays["infl"])])
    return PathInputs(r=r, dist=dist, price=price, cpi_idx=cpi_idx, cash_robo=arrays["cash_robo"])


def roth_contribution(owner: Owner, year0: int) -> float:
    """Real Roth contribution in January of 0-based year `year0` (prereg rev. 4 §2)."""
    ph = phase_of(owner, year0)
    if ph == "school":
        ok = owner.roth_in_school and owner.wages_school >= owner.roth_contrib
        return owner.roth_contrib if ok else 0.0
    if ph == "post" and not owner.roth_post_school:
        return 0.0
    return owner.roth_contrib


def contribution_schedule(owner: Owner, months: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Real contributions per month (taxable, Roth) and the real PV of all contributions after month t."""
    tax_c = np.full(months, owner.c_taxable_month)
    roth_c = np.zeros(months)
    for t in range(0, months, 12):
        roth_c[t] = roth_contribution(owner, t // 12)
    v = (1.0 + owner.real_discount) ** (-1.0 / 12.0)
    flows = tax_c + roth_c
    pv_after = np.zeros(months)
    acc = 0.0
    for t in range(months - 1, -1, -1):
        pv_after[t] = acc
        acc = flows[t] + v * acc
    # pv_after[t] is the PV at month t+1 of flows from t+1 onward; discount one month back to t
    return tax_c, roth_c, pv_after * v


def phase_of(owner: Owner, year0: int) -> str:
    s = owner.school_start - 1
    if year0 < s:
        return "pre"
    if year0 < s + owner.school_years:
        return "school"
    return "post"


def wages_of(owner: Owner, year0: int) -> float:
    return {"pre": owner.wages_pre, "school": owner.wages_school, "post": owner.wages_post}[phase_of(owner, year0)]


@dataclass
class ArmResult:
    terminal_real: float
    pre_tax_real: float
    taxes_real: float
    max_dd_real: float
    below_contrib_y20: bool
    tlh_years: int
    zero_room_used_real: float
    delever_gain_real: float


def simulate(arm: Arm, owner: Owner, path: PathInputs) -> ArmResult:
    """Run one arm on one path, month by month (nominal dollars; reported in real 2026 dollars)."""
    T = len(path.cash_robo)
    P = path.price
    idx = path.cpi_idx
    tax_c, roth_c, pv_after = contribution_schedule(owner, T)
    books = {"voo": LotBook(), "robo": LotBook(), "sso": LotBook()}
    robo_cash = 0.0
    lev = arm.lev_fund
    roth = {"voo": owner.roth0, lev: 0.0}
    # Legacy robo balance: 94 % equity lots (long-term) + 6 % cash. The cash carries basis 1:1, so the
    # equity basis is (1 - g) * B - cash; the embedded gain g is a fraction of the whole balance.
    if not 0.0 <= owner.g <= 1.0 - ROBO_CASH:
        raise ValueError(f"embedded gain fraction g={owner.g} outside [0, {1 - ROBO_CASH}]")
    legacy_basis = owner.taxable0 * (1.0 - owner.g)
    legacy_eq = owner.taxable0 * (1.0 - ROBO_CASH)
    legacy_cash = owner.taxable0 * ROBO_CASH
    eq_basis = legacy_basis - legacy_cash
    if arm.taxable == "ref":
        books["voo"].buy(owner.taxable0, P["voo"][0], -24, basis=legacy_basis)
    elif arm.taxable == "robo":
        books["robo"].buy(legacy_eq, P["robo"][0], -24, basis=eq_basis)
        robo_cash = legacy_cash
    else:  # k1, s0, s1, b4: legacy equity lots kept; the cash slice buys VOO at t = 0
        books["robo"].buy(legacy_eq, P["robo"][0], -24, basis=eq_basis)
        books["voo"].buy(legacy_cash, P["voo"][0], 0)
    # `year` accumulates the current tax year. Sales that pay a December tax bill are realised into the
    # NEXT year's accumulator (they settle when the tax is paid), so the 0 % room and every bill see them.
    year = TaxYear()
    st_cf = lt_cf = 0.0
    taxes_real = 0.0
    peak = 0.0
    max_dd = 0.0
    contributed_real = owner.taxable0 + owner.roth0
    below20 = False
    tlh_years = 0
    tlh_active_year = False
    room_used = 0.0
    delever_gain = 0.0

    def taxable_value(t1: int) -> float:
        return (books["voo"].value(P["voo"][t1]) + books["robo"].value(P["robo"][t1])
                + books["sso"].value(P["sso"][t1]) + robo_cash)

    def realize(acc: TaxYear, st: float, lt: float) -> None:
        acc.st += st
        acc.lt += lt

    if arm.taxable == "s0":
        pr, st, lt = books["robo"].sell_hifo(books["robo"].value(P["robo"][0]), P["robo"][0], 0)
        realize(year, st, lt)
        books["voo"].buy(pr, P["voo"][0], 0)

    for t in range(T):
        y0 = t // 12
        jan, dec = t % 12 == 0, t % 12 == 11
        ct = tax_c[t] * idx[t]
        cr = roth_c[t] * idx[t]
        contributed_real += tax_c[t] + roth_c[t]
        # ---- contributions (start of month t) ----
        roth["voo"] += cr
        if arm.taxable == "robo":
            books["robo"].buy(ct * (1 - ROBO_CASH), P["robo"][t], t)
            robo_cash += ct * ROBO_CASH
            ct = 0.0
        # ---- January resets (household leverage) ----
        if jan and (arm.roth != "voo" or arm.taxable == "b4"):
            w_t = taxable_value(t) + ct
            w_r = roth["voo"] + roth[lev]
            w_h = w_t + w_r
            if arm.roth == "static":
                L = arm.static_L
            else:
                L = min(arm.cap, max(1.0, (w_h / idx[t] + pv_after[t]) / (w_h / idx[t])))
            if arm.taxable == "b4":
                L_t = min(2.0, max(1.0, (L * w_h - w_r) / w_t)) if w_t > 0 else 1.0
                target = (L_t - 1.0) * w_t
                cur = books["sso"].value(P["sso"][t])
                delta = target - cur
                if delta > 0:
                    use = min(delta, ct)
                    books["sso"].buy(use, P["sso"][t], t)
                    ct -= use
                    rest = delta - use
                    if rest > 0:  # VOO is bought every month: a VOO loss here is a wash sale
                        pr, st, lt = books["voo"].sell_hifo(rest, P["voo"][t], t, wash=True)
                        realize(year, st, lt)
                        books["sso"].buy(pr * (1 - SLIP), P["sso"][t], t)
                elif delta < 0:
                    pr, st, lt = books["sso"].sell_hifo(-delta, P["sso"][t], t)
                    realize(year, st, lt)
                    delever_gain += (st + lt) / idx[t]
                    books["voo"].buy(pr * (1 - SLIP), P["voo"][t], t)
            else:
                k_max = EXPOSURE[lev]
                need = L * w_h - w_t
                L_r = min(k_max, max(1.0, need / w_r)) if w_r > 0 else 1.0
                w_lev = (L_r - 1.0) / (k_max - 1.0)
                new_lev = w_lev * w_r
                traded = abs(new_lev - roth[lev])
                roth[lev] = new_lev
                roth["voo"] = w_r - new_lev - traded * SLIP
        books["voo"].buy(ct, P["voo"][t], t)
        # ---- month t returns and distributions ----
        for f, book in books.items():
            if book.total_shares <= 0:
                continue
            v_end = book.value(P[f][t + 1])
            d = v_end * path.dist[f][t]
            if f == "voo":
                year.qual += d
            elif f == "robo":
                year.qual += d * ROBO_QUALIFIED
                year.ordinary += d * (1 - ROBO_QUALIFIED)
            else:
                year.ordinary += d
            book.buy(d, P[f][t + 1], t)
        if robo_cash > 0:
            interest = robo_cash * path.cash_robo[t]
            robo_cash += interest
            year.ordinary += interest
        roth["voo"] *= 1.0 + path.r["voo"][t]
        roth[lev] *= 1.0 + path.r[lev][t]
        # ---- robo behaviour (K0) ----
        if arm.taxable == "robo":
            v_tax = taxable_value(t + 1)
            if arm.tlh and v_tax >= TLH_MIN_NOMINAL:
                st, lt = books["robo"].harvest(P["robo"][t + 1], t, owner.tlh_theta)
                realize(year, st, lt)
                tlh_active_year = True
            if dec:
                st, lt = books["robo"].realize_gains_prorata(owner.robo_rebal, P["robo"][t + 1], t)
                realize(year, st, lt)
                tot = taxable_value(t + 1)
                gap = ROBO_CASH * tot - robo_cash
                if gap > 0:  # new money buys the robo's ETFs every month: a loss here is a wash sale
                    pr, st, lt = books["robo"].sell_hifo(gap, P["robo"][t + 1], t, wash=True)
                    realize(year, st, lt)
                    robo_cash += pr
                elif gap < 0:
                    books["robo"].buy(-gap, P["robo"][t + 1], t)
                    robo_cash += gap
        # ---- S1: the school-year 0 % window, each December ----
        if arm.taxable == "s1" and dec and phase_of(owner, y0) == "school":
            w = wages_of(owner, y0) * idx[t + 1]
            room = zero_rate_room(year, w, idx[t + 1], st_cf, lt_cf)
            pr, g1 = books["robo"].realize_lt_gains_upto(room, P["robo"][t + 1], t)
            year.lt += g1
            books["voo"].buy(pr, P["voo"][t + 1], t)
            room2 = room - g1
            pr2, g2 = books["voo"].realize_lt_gains_upto(room2, P["voo"][t + 1], t)
            year.lt += g2
            books["voo"].buy(pr2, P["voo"][t + 1], t)
            room_used += (g1 + g2) / idx[t + 1]
        # ---- December: the year's tax, paid from the taxable account ----
        if dec:
            w = wages_of(owner, y0) * idx[t + 1]
            tax, st_cf, lt_cf, _ = annual_tax(year, w, idx[t + 1], owner.state_rate, st_cf, lt_cf)
            taxes_real += tax / idx[t + 1]
            year = TaxYear()
            tlh_years += int(tlh_active_year)
            tlh_active_year = False
            if tax > 0:
                due = tax
                if arm.taxable == "robo":
                    take = min(robo_cash, due)
                    robo_cash -= take
                    due -= take
                for f in ("voo", "robo", "sso"):
                    if due <= 1e-9:
                        break
                    pr, st, lt = books[f].sell_hifo(due, P[f][t + 1], t, wash=(f != "sso"))
                    realize(year, st, lt)
                    due -= pr
                if due > 1e-6:
                    raise RuntimeError(f"arm {arm.name}: the taxable account cannot pay its tax at month {t}")
            elif tax < 0:
                if arm.taxable == "robo":
                    books["robo"].buy(-tax, P["robo"][t + 1], t)
                else:
                    books["voo"].buy(-tax, P["voo"][t + 1], t)
        # ---- tracking ----
        hh = (taxable_value(t + 1) + roth["voo"] + roth[lev]) / idx[t + 1]
        peak = max(peak, hh)
        max_dd = max(max_dd, peak - hh)
        if t == 239 and hh < contributed_real:
            below20 = True
    t_end = T
    v_tax = taxable_value(t_end)
    liq = liquidation_tax(books, P, t_end, year, owner, idx[t_end], st_cf, lt_cf) if owner.liquidate else 0.0
    pre = (v_tax + roth["voo"] + roth[lev]) / idx[t_end]
    after = (v_tax - liq + roth["voo"] + roth[lev]) / idx[t_end]
    return ArmResult(terminal_real=after, pre_tax_real=pre, taxes_real=taxes_real + liq / idx[t_end],
                     max_dd_real=max_dd, below_contrib_y20=below20, tlh_years=tlh_years,
                     zero_room_used_real=room_used, delever_gain_real=delever_gain)


def liquidation_tax(books: Dict[str, LotBook], P: Dict[str, np.ndarray], t_end: int, year: TaxYear,
                    owner: Owner, idx: float, st_cf: float, lt_cf: float) -> float:
    """The year-40 sale of every taxable lot, taxed through `annual_tax` (20 % bracket and NIIT included)
    together with whatever the last tax payment realised. Mutates the books (the account is sold)."""
    final = TaxYear(qual=year.qual, ordinary=year.ordinary, st=year.st, lt=year.lt)
    for f, book in books.items():
        if book.total_shares > 0:
            carry = book.wash_carry
            _, st, lt = book.sell_hifo(book.value(P[f][t_end]), P[f][t_end], t_end)
            final.st += st
            final.lt += lt - carry
    tax, _, _, _ = annual_tax(final, owner.liq_wages * idx, idx, owner.state_rate, st_cf, lt_cf)
    return tax


# ----------------------------------------------------------------------------------------------------
# Running a layer
# ----------------------------------------------------------------------------------------------------
def panel_arrays(panel: pd.DataFrame) -> Dict[str, np.ndarray]:
    return {c: panel[c].to_numpy(dtype=float) for c in panel.columns}


def run_paths(index_paths: np.ndarray, arrays: Dict[str, np.ndarray], owner: Owner, arms: Sequence[Arm],
              h: float, deltas: Optional[np.ndarray] = None) -> Dict[str, List[ArmResult]]:
    out: Dict[str, List[ArmResult]] = {a.name: [] for a in arms}
    for k, ix in enumerate(index_paths):
        sub = {c: v[ix] for c, v in arrays.items()}
        shift = h + (float(deltas[k]) if deltas is not None else 0.0)
        path = make_path(apply_belief(sub, shift))
        for a in arms:
            out[a.name].append(simulate(a, owner, path))
    return out


def summarize(res: Dict[str, List[ArmResult]], ref: str = "REF", kind: str = "bootstrap",
              effective_n: Optional[float] = None) -> Dict[str, Dict[str, float]]:
    """Bootstrap paths carry Monte Carlo SEs and probabilities. Overlapping historical cohorts are NOT
    independent: they carry shares and the effective number of independent 40-year windows, never an SE."""
    if kind not in ("bootstrap", "cohort"):
        raise ValueError(kind)
    w_ref = np.array([r.terminal_real for r in res[ref]])
    out = {}
    for name, rs in res.items():
        w = np.array([r.terminal_real for r in rs])
        if (w <= 0).any() or not np.all(np.isfinite(w)):
            raise RuntimeError(f"arm {name}: non-positive or non-finite terminal wealth")
        lw = np.log(w)
        d = lw - np.log(w_ref)
        row = {
            "median": float(np.median(w)), "mean": float(np.mean(w)), "E_log": float(np.mean(lw)),
            "dlog_vs_ref_mean": float(np.mean(d)), "CE_gamma2": float(1.0 / np.mean(1.0 / w)),
            "ratio_p05": float(np.quantile(w / w_ref, 0.05)), "ratio_p50": float(np.quantile(w / w_ref, 0.5)),
            "ratio_p95": float(np.quantile(w / w_ref, 0.95)), "ratio_min": float(np.min(w / w_ref)),
            "max_dd_median": float(np.median([r.max_dd_real for r in rs])),
            "max_dd_p95": float(np.quantile([r.max_dd_real for r in rs], 0.95)),
            "taxes_real_median": float(np.median([r.taxes_real for r in rs])),
            "tlh_years_median": float(np.median([r.tlh_years for r in rs])),
            "zero_room_used_median": float(np.median([r.zero_room_used_real for r in rs])),
            "delever_gain_median": float(np.median([r.delever_gain_real for r in rs])),
        }
        if kind == "bootstrap":
            n = len(d)
            row.update({"n_paths": n,
                        "E_log_mcse": float(np.std(lw, ddof=1) / math.sqrt(n)) if n > 1 else float("nan"),
                        "dlog_vs_ref_mcse": float(np.std(d, ddof=1) / math.sqrt(n)) if n > 1 else float("nan"),
                        "p_below_ref": float(np.mean(w < w_ref)),
                        "p_below_contrib_y20": float(np.mean([r.below_contrib_y20 for r in rs]))})
        else:
            row.update({"n_cohorts": len(d), "effective_independent_windows": effective_n,
                        "share_of_cohorts_below_ref": float(np.mean(w < w_ref)),
                        "share_of_cohorts_below_contrib_y20": float(np.mean([r.below_contrib_y20 for r in rs]))})
        out[name] = row
    return out


def cohort_index_paths(panel: pd.DataFrame, starts: Sequence[int], months: int) -> Tuple[np.ndarray, List[int]]:
    """Every pre-registered January start must fit the panel; one that does not HALTS (never a silent skip)."""
    periods = panel.index
    rows = []
    for y in starts:
        p0 = pd.Period(f"{y}-01", freq="M")
        if p0 not in periods:
            raise InputError(f"cohort {y} starts outside the panel {periods[0]}..{periods[-1]}")
        i0 = periods.get_loc(p0)
        if i0 + months > len(periods):
            raise InputError(f"cohort {y} needs {months} months; the panel ends {periods[-1]}")
        rows.append(np.arange(i0, i0 + months))
    if not rows:
        raise InputError("no cohort starts were given")
    return np.array(rows), list(starts)


def choose(raw: Dict[str, np.ndarray], raw_blocks: Dict[int, Dict[str, np.ndarray]],
           cohort_unshifted: Dict[str, Dict[str, float]], cohort_row: Optional[Dict[str, Dict[str, float]]],
           candidates: Sequence[str], default: str, bound: float) -> Dict[str, object]:
    """The owner's rule (prereg rev. 4 §3), per decision.

    Eligible: worst UNshifted historical cohort >= bound x REF (the row's shifted cohorts are reported).
    Among eligible arms, in descending E[log W] order, the first whose paired lead over the default exceeds its
    band is chosen; otherwise the default. Band = max(2 x the paired Monte Carlo SE of (arm - default), the
    range of that lead across the block-length runs). `raw[a]` are log terminal wealths on the paired paths."""
    elig = [a for a in candidates if cohort_unshifted[a]["ratio_min"] >= bound]
    out: Dict[str, object] = {
        "eligible": elig,
        "worst_cohort_ratio_unshifted": {a: cohort_unshifted[a]["ratio_min"] for a in candidates},
        "worst_cohort_ratio_this_row": ({a: cohort_row[a]["ratio_min"] for a in candidates}
                                        if cohort_row is not None else None),
        "contrasts": {}}
    if not elig:
        out["choice"], out["rule"] = None, "no eligible arm"
        return out
    if default not in elig:
        out["choice"] = max(elig, key=lambda a: float(np.mean(raw[a])))
        out["rule"] = "default ineligible: highest E_log"
        return out
    choice = default
    for a in sorted((x for x in elig if x != default), key=lambda x: -float(np.mean(raw[x]))):
        d = raw[a] - raw[default]
        lead = float(np.mean(d))
        mcse = float(np.std(d, ddof=1) / math.sqrt(len(d))) if len(d) > 1 else math.inf
        leads = [lead] + [float(np.mean(rb[a] - rb[default])) for _, rb in sorted(raw_blocks.items())]
        spread = max(leads) - min(leads)
        band = max(2.0 * mcse, spread)
        out["contrasts"][a] = {"lead": lead, "paired_mcse": mcse, "block_leads": leads, "block_spread": spread,
                               "band": band, "distinct": bool(lead > band)}
        if lead > band and choice == default:
            choice = a
    out["choice"], out["rule"] = choice, "first distinct lead over the default, else the default"
    return out


# ----------------------------------------------------------------------------------------------------
# Pre-tax gate and Sortino for the static fund mixes (reported, never deciding)
# ----------------------------------------------------------------------------------------------------
def static_mix_returns(panel: pd.DataFrame) -> Dict[str, pd.Series]:
    voo = panel["voo"]
    robo = (1 - ROBO_CASH) * panel["robo"] + ROBO_CASH * panel["cash_robo"]
    blend = 0.75 * panel["voo"] + 0.25 * panel["sso"]
    return {"voo": voo, "robo_mix": robo, "blend_1.25_sso": blend}


def gate_and_sortino(panel: pd.DataFrame, seed: int) -> Dict[str, Dict[str, float]]:
    mixes = static_mix_returns(panel)
    out = {}
    if len(panel) < 24:
        raise InputError("panel too short for the gate statistics")

    def sortino12(r: pd.Series) -> float:
        return MetricsEngine.sortino_ratio(r, periods=12)

    for name, r in mixes.items():
        s = MetricsEngine.bootstrap_distribution(r.reset_index(drop=True), sortino12, n_iterations=1000,
                                                 block_length=12, seed=seed)
        row = {"sortino_point": s["point_estimate"], "sortino_ci_low": s["ci_low"], "sortino_ci_high": s["ci_high"]}
        if name != "voo":
            d = (np.log1p(r) - np.log1p(mixes["voo"])).reset_index(drop=True)
            b = MetricsEngine.bootstrap_distribution(d, lambda x: float(np.mean(x)) * 12.0, n_iterations=1000,
                                                     block_length=12, seed=seed)
            row.update({"dlog_vs_voo_per_yr": b["point_estimate"], "dlog_ci_low": b["ci_low"],
                        "dlog_ci_high": b["ci_high"],
                        "t_boot": b["point_estimate"] / b["std"] if b["std"] > 1e-12 else float("nan")})
        out[name] = row
    return out


# ----------------------------------------------------------------------------------------------------
# JST (L3): pre-tax, annual-reset leverage robustness outside the US (descriptive)
# ----------------------------------------------------------------------------------------------------
def load_jst(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl", usecols=["year", "iso", "eq_tr", "bill_rate", "cpi"])
    if df.empty:
        raise InputError("JST file is empty")
    return df


LEV_MODES = (("one", "one", 1.0), ("life2", "life", 2.0), ("life15", "life", 1.5), ("static125", "static", 1.25))


def _annual_household(eq: np.ndarray, bill: np.ndarray, infl: np.ndarray, w0: float, contrib: float,
                      mode: str, cap: float, real_discount: float) -> float:
    """Pre-tax, household-level, ANNUAL-reset leverage path (the JST approximation). Real terminal $."""
    n = len(eq)
    v = 1.0 / (1.0 + real_discount)
    pv = np.array([contrib * sum(v ** (k + 1) for k in range(n - j - 1)) for j in range(n)])
    spread = SPREAD["sso"] + BASE_ADJ
    w = w0
    for j in range(n):
        L = 1.0 if mode == "one" else (cap if mode == "static" else min(cap, max(1.0, (w + pv[j]) / w)))
        cost = ER["sso"] * (L - 1.0) if L > 1.0 else ER["voo"]
        rr = L * eq[j] - (L - 1.0) * (bill[j] + spread) - cost
        w = max(w * (1.0 + rr) / (1.0 + infl[j]), 1e-9) + contrib
    return w


def jst_cohorts(df: pd.DataFrame, owner: Owner, years: int = 40) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Per JST country: 40-year cohorts of household 1x vs annual-reset leverage (pre-tax, uncapped by Roth
    capacity, real local currency). Descriptive only; the US calibration below sizes the approximation."""
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    contrib = owner.c_taxable_month * 12 + owner.roth_contrib
    w0 = owner.taxable0 + owner.roth0
    for iso, g in df.groupby("iso"):
        g = g.sort_values("year").set_index("year")[["eq_tr", "bill_rate", "cpi"]].astype(float)
        infl = g["cpi"].pct_change()
        frame = pd.DataFrame({"eq": g["eq_tr"], "bill": g["bill_rate"], "infl": infl}).dropna()
        if len(frame) < years:
            continue
        yrs = frame.index.values
        ratios: Dict[str, List[float]] = {nm: [] for nm, _, _ in LEV_MODES if nm != "one"}
        for s in range(0, len(frame) - years + 1):
            if yrs[s + years - 1] - yrs[s] != years - 1:
                continue  # a gap inside the window (wars, missing years): skip the cohort
            win = frame.iloc[s:s + years]
            res = {nm: _annual_household(win["eq"].values, win["bill"].values, win["infl"].values, w0, contrib,
                                         mode, cap, owner.real_discount) for nm, mode, cap in LEV_MODES}
            for nm in ratios:
                ratios[nm].append(res[nm] / res["one"])
        if ratios["life2"]:
            out[str(iso)] = {nm: {"worst": float(np.min(v)), "median": float(np.median(v)), "n_cohorts": len(v)}
                             for nm, v in ratios.items()}
    return out


def us_reset_calibration(panel: pd.DataFrame, owner: Owner, starts: Sequence[int], years: int) -> Dict[str, Dict[str, float]]:
    """On the L1 panel: the same household rule with the daily-reset SSO blend (monthly steps, January
    resets) vs the annual-reset approximation on calendar-year aggregates. Reports both median ratios."""
    yearly = pd.DataFrame({
        "eq": panel["voo"].groupby(panel.index.year).apply(lambda x: float(np.prod(1 + x) - 1)) + ER["voo"],
        "bill": panel["rf"].groupby(panel.index.year).apply(lambda x: float(np.prod(1 + x) - 1)),
        "infl": panel["infl"].groupby(panel.index.year).apply(lambda x: float(np.prod(1 + x) - 1)),
    })
    contrib = owner.c_taxable_month * 12 + owner.roth_contrib
    w0 = owner.taxable0 + owner.roth0
    v = 1.0 / (1.0 + owner.real_discount)
    out: Dict[str, Dict[str, float]] = {}
    annual: Dict[str, List[float]] = {nm: [] for nm, _, _ in LEV_MODES if nm != "one"}
    daily: Dict[str, List[float]] = {nm: [] for nm, _, _ in LEV_MODES if nm != "one"}
    for y in starts:
        if y not in yearly.index or y + years - 1 not in yearly.index:
            continue
        win = yearly.loc[y:y + years - 1]
        ra = {nm: _annual_household(win["eq"].values, win["bill"].values, win["infl"].values, w0, contrib,
                                    mode, cap, owner.real_discount) for nm, mode, cap in LEV_MODES}
        m = panel.loc[pd.Period(f"{y}-01", "M"):pd.Period(f"{y + years - 1}-12", "M")]
        rd = {}
        for nm, mode, cap in LEV_MODES:
            w = w0
            for j, (_, grp) in enumerate(m.groupby(m.index.year)):
                pv = contrib * sum(v ** (k + 1) for k in range(years - j - 1))
                L = 1.0 if mode == "one" else (cap if mode == "static" else min(cap, max(1.0, (w + pv) / w)))
                a, b = w * (2.0 - L), w * (L - 1.0)  # VOO and SSO slices, drifting until next January
                for _, row in grp.iterrows():
                    a = a * (1.0 + row["voo"]) / (1.0 + row["infl"])
                    b = b * (1.0 + row["sso"]) / (1.0 + row["infl"])
                w = max(a + b, 1e-9) + contrib
            rd[nm] = w
        for nm in annual:
            annual[nm].append(ra[nm] / ra["one"])
            daily[nm].append(rd[nm] / rd["one"])
    for nm in annual:
        if annual[nm]:
            out[nm] = {"annual_reset_median": float(np.median(annual[nm])),
                       "daily_reset_median": float(np.median(daily[nm])),
                       "annual_reset_worst": float(np.min(annual[nm])), "daily_reset_worst": float(np.min(daily[nm])),
                       "n_cohorts": len(annual[nm])}
    return out


# ----------------------------------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------------------------------
def _round(obj):
    if isinstance(obj, float):
        return round(obj, 6) if math.isfinite(obj) else str(obj)
    if isinstance(obj, dict):
        return {k: _round(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(v) for v in obj]
    return obj


def logw(res: Dict[str, List[ArmResult]]) -> Dict[str, np.ndarray]:
    return {a: np.log(np.array([r.terminal_real for r in rs])) for a, rs in res.items()}


def study(panel: pd.DataFrame, cfg: Config, owner: Owner, jst: Optional[pd.DataFrame] = None,
          log: Callable[[str], None] = print) -> Dict[str, object]:
    months = cfg.horizon_years * 12
    owner = replace(owner, horizon_years=cfg.horizon_years)
    if 0.0 not in cfg.rows:
        raise ValueError("the unshifted row h=0 is required: the loss bound is read on it")
    arrays = panel_arrays(panel)
    coh_ix, coh_used = cohort_index_paths(panel, cfg.cohort_starts, months)
    eff_n = (coh_used[-1] + cfg.horizon_years - coh_used[0]) / cfg.horizon_years
    rng = np.random.default_rng(cfg.seed)
    boot_ix = stationary_bootstrap(len(panel), months, cfg.n_paths, cfg.block_mean, rng)
    deltas = rng.normal(0.0, cfg.param_se, cfg.n_paths)
    block_ix = {b: stationary_bootstrap(len(panel), months, cfg.n_paths, b, np.random.default_rng(cfg.seed + b))
                for b in cfg.block_sensitivity}
    a_arms = [a for a in ARMS if a.decision in ("ref", "A")]
    choice_arms = [a for a in ARMS if a.name in ("REF",) + CANDIDATES_A + CANDIDATES_B]
    rows = ([(f"h={h:+.2f}", h, None) for h in cfg.rows]
            + [(f"param:h={h:+.2f}", h, deltas) for h in cfg.param_rows])
    gp = f"g={cfg.g_primary:.2f}"
    results: Dict[str, object] = {"cohorts": {}, "bootstrap": {}, "block_sensitivity": {}, "owner_sensitivity": {}}
    raw_boot: Dict[str, Dict[str, np.ndarray]] = {}
    raw_blocks: Dict[str, Dict[int, Dict[str, np.ndarray]]] = {}
    for rk, h, dl in rows:
        results["bootstrap"][rk] = {}
        if dl is None:
            results["cohorts"][rk] = {}
        for g in cfg.g_grid:
            own = replace(owner, g=g)
            arms = list(ARMS) if g == cfg.g_primary else a_arms
            t0 = time.time()
            if dl is None:
                results["cohorts"][rk][f"g={g:.2f}"] = summarize(run_paths(coh_ix, arrays, own, arms, h),
                                                                 kind="cohort", effective_n=eff_n)
            rb = run_paths(boot_ix, arrays, own, arms, h, dl)
            results["bootstrap"][rk][f"g={g:.2f}"] = summarize(rb)
            if g == cfg.g_primary:
                raw_boot[rk] = logw(rb)
            log(f"  {rk} g={g:.2f}: {len(arms)} arms in {time.time() - t0:.1f}s")
        own = replace(owner, g=cfg.g_primary)
        raw_blocks[rk] = {}
        for b, ix in block_ix.items():
            rbb = run_paths(ix, arrays, own, choice_arms, h, dl)
            raw_blocks[rk][b] = logw(rbb)
            results["block_sensitivity"].setdefault(rk, {})[f"block={b}"] = summarize(rbb)
    own = replace(owner, g=cfg.g_primary)
    n_sens = max(cfg.n_paths // 4, 8)
    for label, overrides in cfg.owner_sensitivity:
        own_s = replace(own, **dict(overrides))
        results["owner_sensitivity"][label] = {}
        for h in cfg.owner_sensitivity_rows:
            results["owner_sensitivity"][label][f"h={h:+.2f}"] = {
                "cohorts": summarize(run_paths(coh_ix, arrays, own_s, list(ARMS), h), kind="cohort", effective_n=eff_n),
                "bootstrap": summarize(run_paths(boot_ix[:n_sens], arrays, own_s, list(ARMS), h))}
    unshifted = results["cohorts"]["h=+0.00"][gp]
    choice = {}
    for rk, h, dl in rows:
        shifted = results["cohorts"][f"h={h:+.2f}"][gp] if f"h={h:+.2f}" in results["cohorts"] else None
        choice[rk] = {"A": choose(raw_boot[rk], raw_blocks[rk], unshifted, shifted, CANDIDATES_A, DEFAULT_ARM,
                                  cfg.loss_bound),
                      "B": choose(raw_boot[rk], raw_blocks[rk], unshifted, shifted, CANDIDATES_B, DEFAULT_ARM,
                                  cfg.loss_bound)}
    decision = None
    if cfg.decision_row is not None:
        if cfg.decision_row not in choice:
            raise InputError(f"decision row {cfg.decision_row!r} is not one of {sorted(choice)}")
        decision = {"row": cfg.decision_row, **choice[cfg.decision_row]}
    out = {
        "config": asdict(cfg), "owner": asdict(owner), "arms": [asdict(a) for a in ARMS],
        "census": {"panel_months": len(panel), "panel_span": [str(panel.index[0]), str(panel.index[-1])],
                   "cohorts_used": coh_used, "n_cohorts": len(coh_used), "effective_independent_windows": eff_n,
                   "n_bootstrap_paths": int(len(boot_ix)), "block_runs": {str(b): int(len(ix)) for b, ix in block_ix.items()},
                   "months_per_path": months},
        "results": results, "choice": choice, "decision": decision,
        "gate_and_sortino_pre_tax": gate_and_sortino(panel, cfg.seed),
    }
    if jst is not None:
        out["jst_pre_tax_leverage"] = jst_cohorts(jst, owner, cfg.horizon_years)
        out["us_reset_calibration"] = us_reset_calibration(panel, owner, cfg.cohort_starts, cfg.horizon_years)
    return _round(out)


def canonical_md5(obj: Dict[str, object]) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _table_tax_2026(ti: float, idx: float) -> float:
    """Independent of `bracket_tax`: Rev. Proc. 2025-32 Table 3 in its published '$X plus Y %' form."""
    x = ti / idx
    rows = ((640_600, 192_979.25, 0.37), (256_225, 58_448.0, 0.35), (201_775, 41_024.0, 0.32),
            (105_700, 17_966.0, 0.24), (50_400, 5_800.0, 0.22), (12_400, 1_240.0, 0.12), (0, 0.0, 0.10))
    for lo, base, rate in rows:
        if x > lo:
            return idx * (base + rate * (x - lo))
    return 0.0


def independent_ref_terminal(arr: Dict[str, np.ndarray], own: Owner) -> float:
    """REF re-derived without the study's lot book, tax engine or schedule code. Valid only with zero
    dividends and zero state tax: then no tax is due until the final sale, which this taxes itself."""
    n = len(arr["voo"])
    cpi = 1.0
    lots = [(own.taxable0 * (1.0 - own.g), own.taxable0, -24)]   # (basis, value, purchase month)
    roth = own.roth0
    s0 = own.school_start - 1
    for t in range(n):
        y = t // 12
        if t % 12 == 0:
            if y < s0:
                rc = own.roth_contrib
            elif y < s0 + own.school_years:
                rc = own.roth_contrib if (own.roth_in_school and own.wages_school >= own.roth_contrib) else 0.0
            else:
                rc = own.roth_contrib if own.roth_post_school else 0.0
            roth += rc * cpi
        c = own.c_taxable_month * cpi
        lots.append((c, c, t))
        r = arr["voo"][t]
        lots = [(b, v * (1.0 + r), m) for b, v, m in lots]
        roth *= 1.0 + r
        cpi *= 1.0 + arr["infl"][t]
    st = sum(v - b for b, v, m in lots if n - m < 12)
    lt = sum(v - b for b, v, m in lots if n - m >= 12)
    if st < 0 <= lt or lt < 0 <= st:
        st, lt = (0.0, st + lt) if st < 0 else (st + lt, 0.0)
        if st < 0 or lt < 0:
            raise ValueError("the independent control assumes a net gain")
    wages, std = own.liq_wages * cpi, STD_DED_2026 * cpi
    ti = max(0.0, wages - std + st + lt)
    pref = min(lt, ti)
    ordi = ti - pref
    z0, z15 = ZERO_RATE_TOP_2026 * cpi, FIFTEEN_TOP_2026 * cpi
    at0 = max(0.0, min(ti, z0) - min(ordi, z0))
    at15 = min(pref - at0, max(0.0, min(ti, z15) - ordi - at0))
    fed = (_table_tax_2026(ordi, cpi) + 0.15 * at15 + 0.20 * (pref - at0 - at15)
           - _table_tax_2026(max(0.0, wages - std), cpi))
    niit = 0.038 * min(st + lt, max(0.0, wages + st + lt - NIIT_THRESHOLD))
    taxable = sum(v for _, v, _ in lots)
    return (taxable + roth - fed - niit) / cpi


def control_study_path(panel: pd.DataFrame) -> Dict[str, float]:
    """The study's own path (French loader -> monthly panel -> simulate -> lots -> annual_tax at the final
    sale) on the 1990 cohort over 10 years, dividends zeroed, state tax 0, against `independent_ref_terminal`.
    HALTS on a difference above $0.01."""
    p0 = pd.Period(STUDY_CONTROL_START, "M")
    if p0 not in panel.index:
        raise InputError(f"the study-path control needs {p0} in the panel")
    i0 = panel.index.get_loc(p0)
    if i0 + STUDY_CONTROL_MONTHS > len(panel):
        raise InputError("the study-path control window does not fit the panel")
    ix = np.arange(i0, i0 + STUDY_CONTROL_MONTHS)
    arr = {c: v[ix].copy() for c, v in panel_arrays(panel).items()}
    arr["dy"] = np.zeros_like(arr["dy"])
    own = Owner(state_rate=0.0, horizon_years=STUDY_CONTROL_MONTHS // 12)
    ref = next(a for a in ARMS if a.name == "REF")
    got = simulate(ref, own, make_path(arr)).terminal_real
    want = independent_ref_terminal(arr, own)
    diff = abs(got - want)
    if diff > STUDY_CONTROL_TOL:
        raise ControlFailed(f"study-path control: simulate {got:.4f} vs independent {want:.4f} (diff {diff:.4f})")
    return {"simulate_ref_real": got, "independent_real": want, "abs_diff": diff, "pass": True,
            "window": [str(p0), str(panel.index[i0 + STUDY_CONTROL_MONTHS - 1])]}


def _inside(path: Path, base: Path) -> bool:
    """True if `path` is `base` or below it, comparing both the literal and the symlink-resolved forms."""
    cands = {path.absolute(), path.resolve()}
    bases = {base.absolute(), base.resolve()}
    return any(c == b or b in c.parents for c in cands for b in bases)


def cmd_run(args: argparse.Namespace) -> int:
    decision_row = getattr(args, "decision_row", None)
    if not args.smoke:
        if not args.jst:
            raise InputError("the full run requires --jst (prereg rev. 4 §5)")
        if decision_row is None:
            raise InputError("the full run requires --decision-row: the owner's row, recorded in the frozen prereg")
    cfg = replace(SMOKE if args.smoke else Config(), decision_row=decision_row)
    inputs, out_dir, root = Path(args.inputs), Path(args.out), Path(args.control_root)
    for base in (root / "data", ROOT / "data"):
        if _inside(out_dir, base):
            raise InputError(f"refusing to write under a data/ tree: {out_dir} is inside {base}")
    need = ["french", "cpi", "shiller"] + (["jst"] if args.jst else [])
    files = read_manifest(inputs, need)
    print("== T-409: positive controls (HALT on failure) ==")
    controls = run_controls(root)
    for k, v in controls["checks"].items():
        print(f"  {k:18} target {v['target']:>14,.0f}  reproduced {v['reproduced']:>14,.2f}  pass={v['pass']}")
    french = load_french_daily(files["french"])
    last = french.index[-1].to_period("M")
    dp, carried = load_dividend_yield(files["shiller"], last)
    panel = build_monthly_panel(french, load_cpi(files["cpi"]), dp)
    controls["study_path"] = control_study_path(panel)
    sp = controls["study_path"]
    print(f"  {'study_path_REF':18} independent {sp['independent_real']:>14,.4f}  simulate {sp['simulate_ref_real']:>14,.4f}"
          f"  pass={sp['pass']}")
    if cfg.smoke:
        panel = panel.loc[pd.Period("1985-01", "M"):]
    jst = load_jst(files["jst"]) if args.jst else None
    print(f"== panel {panel.index[0]}..{panel.index[-1]} ({len(panel)} months); dividend yield carried "
          f"{carried} months; smoke={cfg.smoke}; decision row {cfg.decision_row} ==")
    res = study(panel, cfg, Owner(), jst)
    res["controls"] = _round(controls)
    res["census"]["dividend_yield_carried_months"] = carried
    res["census"]["input_md5"] = {k: md5_of(p) for k, p in files.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(res, sort_keys=True, indent=1))
    digest = canonical_md5(res)
    (out_dir / "results.md5").write_text(digest + "\n")
    print_summary(res)
    print(f"results md5 {digest}")
    return 0


def print_summary(res: Dict[str, object]) -> None:
    r = res["results"]
    eff = res["census"]["effective_independent_windows"]
    for layer in ("cohorts", "bootstrap"):
        for rk, by_g in r[layer].items():
            for gk, arms in by_g.items():
                head = (f"-- cohorts {rk} {gk}: {res['census']['n_cohorts']} overlapping cohorts, "
                        f"~{eff:.2f} independent windows (shares, not probabilities)"
                        if layer == "cohorts" else f"-- bootstrap {rk} {gk}")
                print(head)
                for name, m in arms.items():
                    tail = (f"share<REF {m['share_of_cohorts_below_ref']:.2f}" if layer == "cohorts"
                            else f"P(<REF) {m['p_below_ref']:.2f}")
                    print(f"   {name:10} median ${m['median']:>12,.0f}  Δlog vs REF {m['dlog_vs_ref_mean']:+.4f}"
                          f"  min ratio {m['ratio_min']:.3f}  {tail}")
    for rk, c in res["choice"].items():
        print(f"-- choice {rk}: A -> {c['A']['choice']}, B -> {c['B']['choice']}")
    print("-- decision (the owner's frozen row):", json.dumps(res["decision"], sort_keys=True)[:400])


# ----------------------------------------------------------------------------------------------------
# fetch (network; writes only into --inputs)
# ----------------------------------------------------------------------------------------------------
def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _fred_key(env_file: Optional[str]) -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key and env_file:
        for line in Path(env_file).read_text().splitlines():
            if line.startswith("FRED_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise InputError("FRED_API_KEY not available (environment or --env-file)")
    return key


def cmd_fetch(args: argparse.Namespace) -> int:
    inputs = Path(args.inputs)
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / INPUT_NAMES["french"]).write_bytes(_get(FRENCH_URL))
    q = urllib.parse.urlencode({"series_id": "CPIAUCNS", "api_key": _fred_key(args.env_file), "file_type": "json"})
    obs = json.loads(_get(f"https://api.stlouisfed.org/fred/series/observations?{q}"))["observations"]
    rows = [(o["date"], o["value"]) for o in obs if o["value"] not in (".", "")]
    pd.DataFrame(rows, columns=["date", "value"]).to_csv(inputs / INPUT_NAMES["cpi"], index=False)
    shutil.copyfile(require_file(Path(args.shiller_csv)), inputs / INPUT_NAMES["shiller"])
    if args.jst:
        (inputs / INPUT_NAMES["jst"]).write_bytes(_get(JST_URL))
    files = {n: md5_of(inputs / n) for n in sorted(p.name for p in inputs.iterdir()) if n != "manifest.json"}
    (inputs / "manifest.json").write_text(json.dumps({"files": files}, indent=1, sort_keys=True))
    print(json.dumps(files, indent=1, sort_keys=True))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--inputs", required=True)
    f.add_argument("--shiller-csv", required=True)
    f.add_argument("--env-file")
    f.add_argument("--jst", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--inputs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--control-root", required=True)
    r.add_argument("--smoke", action="store_true")
    r.add_argument("--jst", action="store_true")
    r.add_argument("--decision-row", dest="decision_row", default=None,
                   help='the owner\'s row, e.g. "h=-0.02" or "param:h=+0.00" (required for the full run)')
    a = ap.parse_args(argv)
    return cmd_fetch(a) if a.cmd == "fetch" else cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
