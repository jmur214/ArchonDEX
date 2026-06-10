"""
scripts/analyze_bab_deep_t129.py
================================
T-2026-06-10-129 — the FAIR BAB re-test: deep 2008-inclusive window.

T-123 found BAB ~0 α on 2014-2025 but flagged the test as unfair: that window is
a documented low-beta HEADWIND and the universe was large-cap-only. This is the
referendum done right — the deepest window the local substrate supports
(2000-2025, 26 yr, including the 2008 crisis where low-beta historically shone).

PRE-REGISTERED (before running, per CLAUDE.md):
  - Window: 2000-01-01 → 2025-12-31 (P&L; beta lookback reaches into 1999).
  - Construction: IDENTICAL to T-123 (monthly-rebalanced FP BAB, beta vs FF
    MktRF, inverse-vol legs, beta-neutralization, 5bps/turnover) except the
    window and one documented robustness guard (names need ≥126 non-NaN days in
    the 252d beta window to be ranked — prevents post-IPO noise betas, which
    could not occur in T-123's filtered panel).
  - Headline: long-short BAB FF5+Mom HAC α t-stat + 1000-iter residual
    moving-block bootstrap CI on the FULL window.
  - Sub-period splits (fixed a priori): 2000-2007, 2008-2013, 2014-2025, and
    the aggregate pre-headwind 2000-2013. The literature says BAB's α lives
    pre-2014; if it does on OUR substrate, the T-123 miss was the headwind.
  - Interpretation: clears t>2 on the deep window → headwind explanation right,
    template found. ~0 α even with 2008 → substrate-empty hypothesis EVIDENCED.
  - Survivor-bias honesty (T-092): the deep substrate is survivor-only →
    α estimates are UPPER bounds for the long leg (dead names absent); the
    SHORT high-beta leg is *understated* (the best shorts — bankruptcies —
    are missing). Stated on the headline either way.

LOCAL run (not cloud): the substrate is on local disk (data/processed/, T-082b
extension — 249 names with data ≤1999, 489 ≤2008) and the analysis is
pandas-only (no backtest engine). Cloud would add image-pinning overhead for
zero compute benefit.

Reuse: same machinery as T-123 (load_factor_data, regress_with_hac,
compute_alpha_tstat_with_bootstrap_ci, MetricsEngine.bootstrap_distribution).

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_bab_deep_t129
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.factor_decomposition import load_factor_data  # noqa: E402
from core.metrics_engine import MetricsEngine  # noqa: E402
from scripts.factor_decomp_substrate_honest import regress_with_hac  # noqa: E402
from engines.engine_f_governance.factor_alpha_gate import (  # noqa: E402
    compute_alpha_tstat_with_bootstrap_ci,
)

OUT_DIR = ROOT / "data" / "measurements" / "bab_deep_retest_t129"
OUT_JSON = OUT_DIR / "bab_deep_analysis.json"

PANEL_START = "1999-01-01"   # extra year so betas exist at the first 2000 rebalance
PNL_START, END = "2000-01-01", "2025-12-31"
BETA_LOOKBACK = 252
MIN_DAYS_IN_WINDOW = 126     # robustness guard (documented in pre-registration)
VOL_WINDOW = 60
TERCILE = 1.0 / 3.0
COST_BPS_PER_TURNOVER = 5.0

SUB_PERIODS = {
    "2000_2007": ("2000-01-01", "2007-12-31"),
    "2008_2013": ("2008-01-01", "2013-12-31"),
    "2014_2025": ("2014-01-01", "2025-12-31"),
    "pre_headwind_2000_2013": ("2000-01-01", "2013-12-31"),
}


def build_returns_panel() -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns:
            continue
        df = df[(df.index >= PANEL_START) & (df.index <= END)]
        if len(df) < BETA_LOOKBACK + 60:
            continue
        cols.append(np.log(df["Close"].astype(float)).diff().rename(
            f.split("/")[-1].replace("_1d.csv", "")))
    if not cols:
        raise RuntimeError("no price data")
    return pd.concat(cols, axis=1).sort_index()


def build_bab_streams(rets: pd.DataFrame, factors: pd.DataFrame):
    """Monthly-rebalanced FP BAB — identical to T-123 except the window and the
    MIN_DAYS_IN_WINDOW coverage guard. Returns (longshort, longonly, breadth)."""
    mkt = (factors["MktRF"] + factors["RF"]).reindex(rets.index).dropna()
    rets = rets.loc[mkt.index]
    mkt_dev = mkt - mkt.mean()
    rebal = pd.Series(rets.index, index=rets.index).groupby(
        [rets.index.year, rets.index.month]).last().tolist()
    # only rebalance from the P&L start onward
    rebal = [d for d in rebal if d >= pd.Timestamp(PNL_START) - pd.offsets.MonthEnd(1)]

    ls_daily = pd.Series(0.0, index=rets.index)
    lo_daily = pd.Series(0.0, index=rets.index)
    prev_ls_w = pd.Series(dtype=float)
    prev_lo_w = pd.Series(dtype=float)
    ls_turn = pd.Series(0.0, index=rets.index)
    lo_turn = pd.Series(0.0, index=rets.index)
    breadth = {}

    for i, d in enumerate(rebal):
        win = rets.loc[:d].tail(BETA_LOOKBACK)
        if len(win) < BETA_LOOKBACK:
            continue
        m = mkt_dev.loc[win.index]
        var_m = float((m * m).mean())
        if var_m <= 0:
            continue
        coverage = win.notna().sum()
        eligible = coverage.index[coverage >= MIN_DAYS_IN_WINDOW]
        sub = win[eligible]
        cov = sub.mul(m, axis=0).mean()
        beta = (cov / var_m).dropna()
        vol = sub.std() * np.sqrt(252.0)
        valid = beta.index[(beta.notna()) & (vol.reindex(beta.index) > 0)]
        beta = beta.loc[valid]
        if len(beta) < 15:
            continue
        ivol = (1.0 / vol.reindex(beta.index)).replace([np.inf, -np.inf], np.nan).dropna()
        beta = beta.loc[ivol.index]
        ranks = beta.rank(pct=True)
        low = beta.index[ranks <= TERCILE]
        high = beta.index[ranks >= 1 - TERCILE]
        if len(low) < 3 or len(high) < 3:
            continue
        breadth[str(d.date())] = int(len(beta))

        def _legw(names):
            w = ivol.reindex(names).fillna(0.0)
            return w / w.sum() if w.sum() > 0 else w

        wL, wH = _legw(low), _legw(high)
        bL = float((beta.reindex(low) * wL).sum())
        bH = float((beta.reindex(high) * wH).sum())
        ls_w = pd.Series(0.0, index=beta.index)
        if bL > 0:
            ls_w.loc[low] += wL / bL
        if bH > 0:
            ls_w.loc[high] -= wH / bH
        lo_w = pd.Series(0.0, index=beta.index)
        lo_w.loc[low] = wL

        end_d = rebal[i + 1] if i + 1 < len(rebal) else rets.index[-1]
        hold = rets.loc[d:end_d].iloc[1:]
        if hold.empty:
            continue
        # fillna(0): a name with no print that day contributes 0 (held flat)
        ls_daily.loc[hold.index] = hold.reindex(columns=ls_w.index).fillna(0.0).mul(ls_w, axis=1).sum(axis=1)
        lo_daily.loc[hold.index] = hold.reindex(columns=lo_w.index).fillna(0.0).mul(lo_w, axis=1).sum(axis=1)
        ls_turn_val = float((ls_w.subtract(prev_ls_w, fill_value=0.0)).abs().sum())
        lo_turn_val = float((lo_w.subtract(prev_lo_w, fill_value=0.0)).abs().sum())
        ls_turn.loc[hold.index[0]] = ls_turn_val
        lo_turn.loc[hold.index[0]] = lo_turn_val
        prev_ls_w, prev_lo_w = ls_w, lo_w

    cost = COST_BPS_PER_TURNOVER / 1e4
    rf = factors["RF"].reindex(rets.index).fillna(0.0)
    live = ls_daily.ne(0).cumsum() > 0
    ls_net = (ls_daily - ls_turn * cost + rf).loc[live]
    lo_net = (lo_daily - lo_turn * cost).loc[lo_daily.ne(0).cumsum() > 0]
    ls_net = ls_net.loc[ls_net.index >= PNL_START]
    lo_net = lo_net.loc[lo_net.index >= PNL_START]
    return ls_net.dropna(), lo_net.dropna(), breadth


def factor_report(stream: pd.Series, factors: pd.DataFrame, label: str) -> Dict:
    if len(stream.dropna()) < 60:
        return {"n_obs": int(len(stream.dropna())), "skipped": "too few obs"}
    hac = regress_with_hac(stream, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(stream, factors, min_obs=30, n_iter=1000, seed=0)
    bd = MetricsEngine.bootstrap_distribution(stream.dropna(), MetricsEngine.sharpe_ratio,
                                              n_iterations=1000, seed=0)
    return {
        "n_obs": hac.get("n_obs"),
        "alpha_annual_pct": hac.get("alpha_annualized", 0.0) * 100.0 if hac.get("ok") else None,
        "alpha_tstat_point": ci.alpha_tstat_point,
        "alpha_tstat_ci_low": ci.alpha_tstat_ci_low,
        "alpha_tstat_ci_high": ci.alpha_tstat_ci_high,
        "clears_t2_point": ci.alpha_tstat_point > 2.0,
        "clears_t2_strict_ci": ci.alpha_tstat_ci_low > 2.0,
        "p_alpha_above_zero": hac.get("alpha_p_above_zero_bootstrap") if hac.get("ok") else None,
        "betas": {k: round(v["beta"], 4) for k, v in hac.get("betas", {}).items()} if hac.get("ok") else None,
        "r_squared": hac.get("r_squared") if hac.get("ok") else None,
        "sharpe_point": bd["point_estimate"],
        "sharpe_ci_low": bd["ci_low"],
        "sharpe_ci_high": bd["ci_high"],
    }


def book_correlation(stream: pd.Series) -> Dict:
    out = {}
    try:
        p = glob.glob(str(ROOT / "data" / "trade_logs" / "0dcae34c*" / "trades.csv"))[0]
        tr = pd.read_csv(p, usecols=["timestamp", "edge_id", "pnl"])
        tr["timestamp"] = pd.to_datetime(tr["timestamp"], errors="coerce")
        tr["pnl"] = pd.to_numeric(tr["pnl"], errors="coerce")
        tr = tr.dropna(subset=["pnl"])
        book = tr.groupby(tr["timestamp"].dt.normalize())["pnl"].sum() / 100_000.0
        df = pd.concat({"x": stream, "book": book}, axis=1).dropna()
        if len(df) > 30:
            out["book_corr"] = float(df["x"].corr(df["book"]))
            out["overlap_days"] = int(len(df))
            out["note"] = "book is the 2014-2025 12yr run (0dcae34c); overlap is 2014+ only"
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    rets = build_returns_panel()
    print(f"[T129] panel: {rets.shape[1]} names, {rets.shape[0]} days "
          f"{rets.index.min().date()}..{rets.index.max().date()}")
    ls, lo, breadth = build_bab_streams(rets, factors)
    b = pd.Series(breadth)
    print(f"[T129] BAB streams: LS {len(ls)}d {ls.index.min().date()}..{ls.index.max().date()} | "
          f"breadth min={b.min()} median={b.median():.0f} max={b.max()}")

    results = {
        "task": "T-2026-06-10-129",
        "preregistered_window": [PNL_START, END],
        "construction": "identical to T-123 (monthly FP BAB, beta vs FF MktRF, inverse-vol "
                        "legs, beta-neutral, 5bps/turnover) + min-coverage guard "
                        f"({MIN_DAYS_IN_WINDOW}d in beta window)",
        "run_mode": "LOCAL (substrate on disk; pandas-only analysis — no engine, no image)",
        "survivor_bias": "deep substrate is survivor-only (T-092): long-leg alpha is an "
                         "UPPER bound; short-high-beta leg UNDERSTATED (bankrupt names absent)",
        "universe_breadth_per_rebalance": {"min": int(b.min()), "median": float(b.median()),
                                           "max": int(b.max()), "n_rebalances": int(len(b))},
        "full_window": {
            "bab_long_short_beta_neutral": factor_report(ls, factors, "bab_ls_deep"),
            "bab_long_only_low_beta": factor_report(lo, factors, "bab_lo_deep"),
        },
        "sub_periods": {},
        "correlation_long_short": book_correlation(ls),
    }
    for name, (s0, s1) in SUB_PERIODS.items():
        seg = ls.loc[s0:s1]
        results["sub_periods"][name] = factor_report(seg, factors, f"bab_ls_{name}")

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))

    fw = results["full_window"]["bab_long_short_beta_neutral"]
    print(f"[T129] FULL 26yr LS: α={fw['alpha_annual_pct']:+.2f}% t={fw['alpha_tstat_point']:+.2f} "
          f"ci[{fw['alpha_tstat_ci_low']:+.2f},{fw['alpha_tstat_ci_high']:+.2f}] clears_t2={fw['clears_t2_point']} "
          f"| Sharpe={fw['sharpe_point']:+.2f} ci_low={fw['sharpe_ci_low']:+.2f}")
    for name in SUB_PERIODS:
        r = results["sub_periods"][name]
        if r.get("skipped"):
            print(f"[T129] {name}: skipped ({r['n_obs']} obs)")
            continue
        print(f"[T129] {name}: α={r['alpha_annual_pct']:+.2f}% t={r['alpha_tstat_point']:+.2f} "
              f"ci[{r['alpha_tstat_ci_low']:+.2f},{r['alpha_tstat_ci_high']:+.2f}]")
    print(f"[T129] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
