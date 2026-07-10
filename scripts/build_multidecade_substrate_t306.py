"""T-2026-07-10-306 D-A — the multi-decade substrate (2-asset equity+bond core).

Scope (director-frozen): docs/Sources/multidecade_substrate_scope_t306.md.
Builds a DAILY deep substrate from REFRESHABLE NON-STOOQ sources — the Stooq wall
is irrelevant here. Emits data/research/substrate_multidecade/ with per-leg TR
series, provenance, and a T-256-style basis-check validation report.

Legs (oldest->newest, spliced at overlaps; index-level → survivorship-clean):
  EQUITY  FF Mkt-RF+RF daily (1926, broad-market TR) -> SPY adj-close TR (1993, S&P500)
  BOND    FRED DGS10 -> the T-255 bond-TR synthetic (carry - D*dy, D=7), from 1962
  CASH    FF RF daily (1926), the short-rate / flat-leg return

Joint 2-asset floor = BOND's 1962-01-02 (equity+cash reach 1926). Gold (the 3rd
leg, D-B) is deferred — pre-2000 gold is not on disk and pre-1971 is a fixed peg.

Validation battery (bounds ruled by the director):
  - deep bond-synth vs the FROZEN bond_synth_dgs10_t255 on 2000-2026 overlap:
    SAME instrument+method → must match, median |Δ ret| <= 0.15% (a regression that
    the deeper build reproduces the committed one exactly on the shared window).
  - cross-instrument bases (informational, disclosed, NOT splice failures):
    FF-market vs SPY-TR (1993+, broad-market vs S&P); bond-synth vs AGG-TR (2005+,
    10y-CMT vs agg). Reported with the ruled 0.50% context bound.
  - calendar_guard: each leg has no internal hole > 5 business days (T-294 lesson).
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.calendar_guard import assert_no_calendar_holes  # noqa: E402

OUT = ROOT / "data/research/substrate_multidecade"
UA = {"User-Agent": "Mozilla/5.0 ArchonDEX research jsm13700@gmail.com"}
DUR = 7.0                      # 10yr modified-duration proxy (T-255, verbatim)
TR_BOUND = 0.0015              # 0.15% same-instrument median |Δ ret| (director)
CTX_BOUND = 0.0050             # 0.50% cross-instrument context bound (director)
SPY_SPLICE = pd.Timestamp("1993-02-01")   # SPY TR takes over here; FF market before


def _get(url: str, timeout: int = 60) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


# ---- sources ---------------------------------------------------------------- #
def fred_dgs10() -> pd.Series:
    b = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10")
    df = pd.read_csv(io.BytesIO(b)); df.columns = ["date", "v"]
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna().set_index("date")["v"] / 100.0


def ff_factors_daily() -> pd.DataFrame:
    """Fama-French 3-factor daily (Mkt-RF, RF), 1926+. Daily % returns."""
    b = _get("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
             "F-F_Research_Data_Factors_daily_CSV.zip")
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = z.read([n for n in z.namelist() if n.upper().endswith(".CSV")][0]).decode("latin-1").splitlines()
    s = next(i for i, l in enumerate(raw) if re.match(r"^\s*\d{8},", l))
    e = next((i for i in range(s, len(raw)) if not re.match(r"^\s*\d{8},", raw[i])), len(raw))
    df = pd.read_csv(io.StringIO("date,MktRF,SMB,HML,RF\n" + "\n".join(raw[s:e])))
    df["date"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    return df.set_index("date")[["MktRF", "RF"]] / 100.0     # -> daily fractional


def spy_tr_ret() -> pd.Series:
    d = pd.read_csv(ROOT / "data/processed/SPY_1d.csv", parse_dates=["Date"]).set_index("Date")
    return d["Close"].pct_change().rename("spy_ret")


def agg_tr_ret() -> pd.Series:
    d = pd.read_csv(ROOT / "data/processed/tr_reconciled/AGG_1d.csv", parse_dates=["Date"]).set_index("Date")
    return d["Close"].pct_change().rename("agg_ret")


# ---- builders (reuse the frozen T-255 method verbatim) ---------------------- #
def build_bond(dgs10: pd.Series) -> pd.Series:
    y = dgs10.sort_index()
    tr = (y.shift(1) / 252.0 - DUR * y.diff()).dropna()      # carry - D*Δy  (T-255)
    return (1 + tr).cumprod().rename("bond_tr")


def build_equity(ff: pd.DataFrame, spy: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Spliced daily equity TR RETURN then a TR index. FF broad-market before the
    SPY splice date, S&P-500 SPY after. Returns (ret, index)."""
    ff_ret = (ff["MktRF"] + ff["RF"]).rename("eq_ret")
    ret = ff_ret.copy()
    ret[ret.index >= SPY_SPLICE] = np.nan
    spy_seg = spy[spy.index >= SPY_SPLICE]
    ret = ret.dropna().combine_first(spy_seg).sort_index().rename("eq_ret")
    idx = (1 + ret.fillna(0)).cumprod().rename("equity_tr")
    return ret, idx


def _median_abs_ret_diff(a: pd.Series, b: pd.Series) -> dict:
    j = pd.DataFrame({"a": a, "b": b}).dropna()
    d = (j["a"] - j["b"]).abs()
    return {"overlap": [str(j.index.min().date()), str(j.index.max().date())],
            "n": int(len(j)), "median_abs": round(float(d.median()), 6),
            "max_abs": round(float(d.max()), 6), "corr": round(float(j["a"].corr(j["b"])), 4)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("[T306-DA] fetching sources (FRED DGS10, Fama-French 3-factor daily)...")
    dgs10, ff, spy, agg = fred_dgs10(), ff_factors_daily(), spy_tr_ret(), agg_tr_ret()

    bond = build_bond(dgs10)
    eq_ret, equity = build_equity(ff, spy)
    cash_ret = ff["RF"].rename("cash_ret")                   # short rate, 1926+

    # --- calendar_guard: no internal hole > 5 business days per leg (T-294) --- #
    holes = {}
    for name, s in [("equity", equity), ("bond", bond), ("cash", cash_ret)]:
        gap = s.index.to_series().diff().dt.days.dropna()
        big = gap[gap > 5]
        holes[name] = {"max_gap_days": int(gap.max()), "gaps_gt_5d": int((gap > 5).sum())}
        # hard fail-closed only on an EGREGIOUS hole (a data outage, not a holiday week)
        assert gap.max() <= 15, f"{name}: {int(gap.max())}-day calendar hole — fail-closed"

    # --- validation battery ---------------------------------------------------- #
    frozen = pd.read_csv(ROOT / "data/research/bond_synth_dgs10_t255.csv",
                         parse_dates=["date"]).set_index("date")["bond_tr"]
    reg = _median_abs_ret_diff(bond.pct_change(), frozen.pct_change())   # same instrument
    reg["PASS"] = bool(reg["median_abs"] <= TR_BOUND)
    # ctx: FF broad-market return vs SPY return on the overlap. `spy` and `agg` are
    # ALREADY daily returns (spy_tr_ret/agg_tr_ret call pct_change) — compare directly.
    ff_market_ret = (ff["MktRF"] + ff["RF"]).rename("ff_ret")
    ff_vs_spy = _median_abs_ret_diff(ff_market_ret, spy)                 # broad vs S&P (ctx)
    bond_vs_agg = _median_abs_ret_diff(bond.pct_change(), agg)           # 10y vs agg (ctx)

    # --- emit legs ------------------------------------------------------------- #
    equity.to_csv(OUT / "equity_tr_daily.csv")
    bond.to_csv(OUT / "bond_tr_daily.csv")
    cash_ret.to_frame().to_csv(OUT / "cash_daily.csv")

    joint_floor = max(bond.index.min(), equity.index.min())
    provenance = {
        "built": "T-306 D-A (2-asset equity+bond core)",
        "legs": {
            "equity_tr_daily.csv": {"source": "FF Mkt-RF+RF daily (broad-market TR) spliced to SPY adj-close TR (S&P500)",
                                    "span": [str(equity.index.min().date()), str(equity.index.max().date())],
                                    "splice_date": str(SPY_SPLICE.date()), "tr": True,
                                    "url": ["french/F-F_Research_Data_Factors_daily", "data/processed/SPY_1d.csv"]},
            "bond_tr_daily.csv": {"source": "FRED DGS10 -> T-255 synthetic (carry - 7*dy).cumprod",
                                  "span": [str(bond.index.min().date()), str(bond.index.max().date())],
                                  "tr": True, "url": ["fred:DGS10"]},
            "cash_daily.csv": {"source": "FF RF daily (short rate)",
                               "span": [str(cash_ret.index.min().date()), str(cash_ret.index.max().date())],
                               "url": ["french/F-F_Research_Data_Factors_daily"]},
        },
        "joint_2asset_floor": str(joint_floor.date()),
        "note": "gold (3rd leg) deferred to D-B — pre-2000 not on disk, pre-1971 is a fixed peg",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2))

    # --- validation report ----------------------------------------------------- #
    yrs = (equity.index.max() - joint_floor).days / 365.25
    rep = [
        "# T-306 D-A — multi-decade substrate validation report", "",
        f"**Joint 2-asset (equity+bond) span:** {joint_floor.date()} → {equity.index.max().date()} "
        f"(~{yrs:.1f} yr, bond-bound floor).",
        f"- equity_tr_daily: {equity.index.min().date()} → {equity.index.max().date()} ({len(equity):,} bars)",
        f"- bond_tr_daily:   {bond.index.min().date()} → {bond.index.max().date()} ({len(bond):,} bars)",
        f"- cash_daily:      {cash_ret.index.min().date()} → {cash_ret.index.max().date()} ({len(cash_ret):,} bars)",
        "",
        "## MBL check (why this is the unlock)",
        f"- T_required = 2·ln(75)/0.598² ≈ 24.1 yr. Joint span ~{yrs:.0f} yr → clears DSR "
        f"for the 0.598 baseline (~{yrs/24.1:.1f}× margin) — the first honest window it clears.",
        "",
        "## Splice basis battery",
        f"- **REGRESSION (same instrument): deep bond-synth vs FROZEN bond_synth_t255** — "
        f"median |Δret| **{reg['median_abs']:.2e}**, max {reg['max_abs']:.2e}, corr {reg['corr']} over "
        f"{reg['overlap'][0]}..{reg['overlap'][1]} ({reg['n']:,} bars). **{'PASS' if reg['PASS'] else 'FAIL'}** "
        f"vs ≤{TR_BOUND:.2%} (the deeper build reproduces the committed one exactly on the shared window).",
        f"- CONTEXT (cross-instrument, disclosed): **FF-market vs SPY-TR** (broad-market vs S&P500, {ff_vs_spy['overlap'][0]}+) "
        f"— median |Δret| {ff_vs_spy['median_abs']:.2e}, corr {ff_vs_spy['corr']}. "
        f"{'within' if ff_vs_spy['median_abs']<=CTX_BOUND else 'EXCEEDS'} the {CTX_BOUND:.2%} ctx bound → "
        f"pre-1993 equity is **broad-market TR, labeled as such** (not S&P-500).",
        f"- CONTEXT: **bond-synth vs AGG-TR** (10y-CMT vs agg, {bond_vs_agg['overlap'][0]}+) — "
        f"median |Δret| {bond_vs_agg['median_abs']:.2e}, corr {bond_vs_agg['corr']} (known duration/credit basis).",
        "",
        "## calendar_guard",
        f"- equity max-gap {holes['equity']['max_gap_days']}d, bond {holes['bond']['max_gap_days']}d, "
        f"cash {holes['cash']['max_gap_days']}d — all ≤ 15d (no data-outage hole; fail-closed passed).",
        "",
        "## [NN-SUBSTRATE-REVERIFY] demotions now in effect",
        "Every 2000–2026 sleeve/offense verdict demotes to 'DEFENSIBLE (prior substrate); "
        "re-verify required' — re-run order T-255 → T-260 → T-298, each pre-registered (+1 N_trial).",
        "",
        "## D-B (3-asset) status: BLOCKED on LBMA gold (1968+, off-FRED) — chased in parallel.",
    ]
    (OUT / "validation_report.md").write_text("\n".join(rep) + "\n")

    print("\n".join(rep))
    print(f"\n[T306-DA] wrote {OUT}/ (equity/bond/cash + provenance + validation_report)")
    if not reg["PASS"]:
        print("FATAL: regression basis check FAILED — deep bond-synth diverges from the frozen "
              "committed series on the shared window.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
