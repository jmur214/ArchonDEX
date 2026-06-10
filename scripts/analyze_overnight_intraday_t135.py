"""
scripts/analyze_overnight_intraday_t135.py
==========================================
T-2026-06-10-135 — overnight/intraday composition (Lou-Polk-Skouras): the
first frontier edge, through the T-129 analytical gauntlet discipline.

PRE-REGISTERED (fixed before running; ONE canonical construction, no
variant-shopping — a sweep would be a separate pre-registered task):
  - Window: 2000-01-01 → 2025-12-31 (deep; open-quality audited — open==close
    ≤4% worst-year 1999, ~1% typical; opens-out-of-[L,H] ≈ 0%).
  - Construction (LPS JFE 2019 overnight-persistence): monthly rebalance; rank
    names on trailing 21d mean overnight return r_on = Open_t/Close_{t-1}−1;
    LONG top tercile / SHORT bottom tercile; inverse-vol leg weights;
    dollar-neutral; 5 bps per unit turnover. Names need ≥126 non-NaN days in
    the trailing 252d window (T-129 coverage guard).
  - VERDICT OBJECT: the strategy's TOTAL close-to-close return stream (what a
    daily-fill system can trade). FF5+Mom HAC α t-stat + 1000-iter residual
    moving-block bootstrap CI. Clears iff t>2 (point), strict gate ci_low>2.
  - Sub-periods (T-129's set): 2000-2007, 2008-2013, 2014-2025, 2000-2013.
  - DIAGNOSTICS (not verdict-bearing): (a) LPS structure check — rank
    persistence of the overnight component (Spearman corr of past-21d r_on
    rank vs forward-21d r_on rank, monthly); (b) P&L decomposition — the
    strategy stream split into overnight (w·r_on) vs intraday (w·r_id)
    components, showing WHERE any spread accrues (LPS predict: overnight leg
    positive, intraday leg fights it).
  - Survivor-bias: substrate survivor-only (T-092) → α upper bounds.
    Membership-correct PIT re-test deferred (noted per brief).
  - N-accounting: this IS a backtest trial — N_trials += 1.
  - Determinism: seed 0; NO wall-clock inside the result JSON (T-132 lesson).

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_overnight_intraday_t135
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

OUT_DIR = ROOT / "data" / "measurements" / "overnight_intraday_t135"
OUT_JSON = OUT_DIR / "overnight_intraday_analysis.json"

PANEL_START = "1999-01-01"
PNL_START, END = "2000-01-01", "2025-12-31"
ON_LOOKBACK = 21
COVERAGE_WIN = 252
MIN_DAYS_IN_WINDOW = 126
VOL_WINDOW = 60
TERCILE = 1.0 / 3.0
COST_BPS_PER_TURNOVER = 5.0

SUB_PERIODS = {
    "2000_2007": ("2000-01-01", "2007-12-31"),
    "2008_2013": ("2008-01-01", "2013-12-31"),
    "2014_2025": ("2014-01-01", "2025-12-31"),
    "pre_2014_2000_2013": ("2000-01-01", "2013-12-31"),
}


def build_panels():
    """Return (total, overnight, intraday) daily log-return panels."""
    tot, on, idy = [], [], []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if not {"Open", "Close"} <= set(df.columns) or len(df) < 300:
            continue
        df = df[(df.index >= PANEL_START) & (df.index <= END)]
        if len(df) < 300:
            continue
        name = f.split("/")[-1].replace("_1d.csv", "")
        o = df["Open"].astype(float)
        c = df["Close"].astype(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            r_on = np.log(o / c.shift(1))
            r_id = np.log(c / o)
        total = r_on + r_id
        # DATA HYGIENE (documented in audit; cleaning, not variant-shopping):
        # corrupt open prints show as huge offsetting r_on/r_id pairs (open
        # ±X00% off prior close, snapping back by the close — vendor artifact;
        # 83 such rows found, e.g. SBNY 2025-11-06 r_on −6.48 / r_id +6.46).
        # Repair: treat the open as untrusted → r_on=0, r_id=total for the row.
        snap = (r_on.abs() > 0.25) & (r_id.abs() > 0.25) & (np.sign(r_on) != np.sign(r_id))
        r_on = r_on.where(~snap, 0.0)
        r_id = r_id.where(~snap, total)
        tot.append(total.rename(name))
        on.append(r_on.rename(name))
        idy.append(r_id.rename(name))
    if not tot:
        raise RuntimeError("no OHLC data")
    return (pd.concat(tot, axis=1).sort_index(),
            pd.concat(on, axis=1).sort_index(),
            pd.concat(idy, axis=1).sort_index())


def build_strategy(tot: pd.DataFrame, on: pd.DataFrame, idy: pd.DataFrame):
    """Monthly-rebalanced LPS overnight-persistence long-short.
    Returns (total_net, on_component, id_component, breadth)."""
    idx = tot.index
    rebal = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).last().tolist()
    rebal = [d for d in rebal if d >= pd.Timestamp(PNL_START) - pd.offsets.MonthEnd(1)]

    s_tot = pd.Series(0.0, index=idx)
    s_on = pd.Series(0.0, index=idx)
    s_id = pd.Series(0.0, index=idx)
    turn = pd.Series(0.0, index=idx)
    prev_w = pd.Series(dtype=float)
    breadth = {}

    for i, d in enumerate(rebal):
        win_on = on.loc[:d].tail(ON_LOOKBACK)
        cov_win = tot.loc[:d].tail(COVERAGE_WIN)
        if len(win_on) < ON_LOOKBACK or len(cov_win) < COVERAGE_WIN:
            continue
        coverage = cov_win.notna().sum()
        eligible = coverage.index[coverage >= MIN_DAYS_IN_WINDOW]
        # winsorize signal input at ±20%: one residual bad print must not own
        # a 21d mean (data hygiene, documented)
        sig = win_on[eligible].clip(-0.20, 0.20).mean()
        n_on = win_on[eligible].notna().sum()
        sig = sig[(n_on >= ON_LOOKBACK - 2) & sig.notna()]
        vol = cov_win[eligible].std() * np.sqrt(252.0)
        sig = sig[vol.reindex(sig.index) > 0]
        if len(sig) < 15:
            continue
        ranks = sig.rank(pct=True)
        high = sig.index[ranks >= 1 - TERCILE]
        low = sig.index[ranks <= TERCILE]
        if len(high) < 3 or len(low) < 3:
            continue
        breadth[str(d.date())] = int(len(sig))

        ivol = (1.0 / vol.reindex(sig.index)).replace([np.inf, -np.inf], np.nan).dropna()

        def _legw(names):
            w = ivol.reindex(names).fillna(0.0)
            return w / w.sum() if w.sum() > 0 else w

        w = pd.Series(0.0, index=sig.index)
        w.loc[high] += _legw(high)
        w.loc[low] -= _legw(low)

        end_d = rebal[i + 1] if i + 1 < len(rebal) else idx[-1]
        hold = tot.loc[d:end_d].iloc[1:]
        if hold.empty:
            continue
        cols = w.index
        s_tot.loc[hold.index] = hold.reindex(columns=cols).fillna(0.0).mul(w, axis=1).sum(axis=1)
        s_on.loc[hold.index] = on.loc[hold.index].reindex(columns=cols).fillna(0.0).mul(w, axis=1).sum(axis=1)
        s_id.loc[hold.index] = idy.loc[hold.index].reindex(columns=cols).fillna(0.0).mul(w, axis=1).sum(axis=1)
        turn.loc[hold.index[0]] = float((w.subtract(prev_w, fill_value=0.0)).abs().sum())
        prev_w = w

    cost = COST_BPS_PER_TURNOVER / 1e4
    live = s_tot.ne(0).cumsum() > 0
    s_net = (s_tot - turn * cost).loc[live]
    s_net = s_net.loc[s_net.index >= PNL_START]
    s_on = s_on.loc[s_net.index]
    s_id = s_id.loc[s_net.index]
    return s_net.dropna(), s_on, s_id, breadth


def persistence_check(on: pd.DataFrame) -> Dict:
    """LPS structure diagnostic: Spearman corr of past-21d mean r_on rank vs
    forward-21d mean r_on rank, at monthly anchors."""
    idx = on.index
    anchors = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).last().tolist()
    cors = []
    for d in anchors:
        past = on.loc[:d].tail(ON_LOOKBACK).mean()
        fut = on.loc[d:].iloc[1:ON_LOOKBACK + 1].mean()
        both = pd.concat({"p": past, "f": fut}, axis=1).dropna()
        if len(both) >= 30:
            cors.append(float(both["p"].rank().corr(both["f"].rank())))
    arr = np.array(cors)
    return {"n_anchors": int(len(arr)), "mean_spearman": float(arr.mean()),
            "frac_positive": float((arr > 0).mean()),
            "t_stat_naive": float(arr.mean() / (arr.std() / np.sqrt(len(arr)))) if len(arr) > 2 else None}


def factor_report(stream: pd.Series, factors: pd.DataFrame, label: str) -> Dict:
    r = stream.dropna()
    if len(r) < 60:
        return {"n_obs": int(len(r)), "skipped": "too few obs"}
    # long-short is self-financing → add RF so the regression's excess = stream
    full = (r + factors["RF"].reindex(r.index).fillna(0.0))
    hac = regress_with_hac(full, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(full, factors, min_obs=30, n_iter=1000, seed=0)
    bd = MetricsEngine.bootstrap_distribution(r, MetricsEngine.sharpe_ratio,
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
            out["note"] = "book = 12yr run 0dcae34c; overlap 2014+ only"
    except Exception as e:
        out["error"] = str(e)
    return out


def ann_stats(s: pd.Series) -> Dict:
    r = s.dropna()
    if len(r) < 2:
        return {}
    return {"ann_return_pct": float(r.mean() * 252 * 100),
            "ann_vol_pct": float(r.std() * np.sqrt(252) * 100),
            "sharpe_naive": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    tot, on, idy = build_panels()
    print(f"[T135] panels: {tot.shape[1]} names, {tot.shape[0]} days "
          f"{tot.index.min().date()}..{tot.index.max().date()}")

    pers = persistence_check(on)
    print(f"[T135] LPS persistence (rank-corr past->fwd overnight): "
          f"mean={pers['mean_spearman']:+.3f} frac>0={pers['frac_positive']:.2f} "
          f"t~{pers['t_stat_naive']:.1f}")

    s_net, s_on, s_id, breadth = build_strategy(tot, on, idy)
    b = pd.Series(breadth)
    print(f"[T135] strategy: {len(s_net)}d | breadth min={b.min()} "
          f"median={b.median():.0f} max={b.max()}")

    results = {
        "task": "T-2026-06-10-135",
        "construction": "LPS (JFE 2019) overnight-persistence: monthly rebal, rank on "
                        "trailing 21d mean overnight return, long top / short bottom "
                        "tercile, inverse-vol, dollar-neutral, 5bps/turnover; verdict "
                        "object = TOTAL close-to-close net stream",
        "preregistered_window": [PNL_START, END],
        "survivor_bias": "survivor-only substrate (T-092): alpha estimates are UPPER "
                         "bounds; membership-correct PIT re-test deferred",
        "n_trials_consumed": 1,
        "universe_breadth": {"min": int(b.min()), "median": float(b.median()),
                             "max": int(b.max()), "n_rebalances": int(len(b))},
        "lps_persistence_diagnostic": pers,
        "pnl_decomposition": {
            "total_net": ann_stats(s_net),
            "overnight_component": ann_stats(s_on),
            "intraday_component": ann_stats(s_id),
        },
        "full_window_total_return": factor_report(s_net, factors, "lps_total"),
        "overnight_component_factor": factor_report(s_on.loc[s_net.index], factors, "lps_on"),
        "sub_periods": {},
        "correlation": book_correlation(s_net),
    }
    for name, (a, z) in SUB_PERIODS.items():
        results["sub_periods"][name] = factor_report(s_net.loc[a:z], factors, f"lps_{name}")

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))

    fw = results["full_window_total_return"]
    print(f"[T135] TOTAL-return α={fw['alpha_annual_pct']:+.2f}% t={fw['alpha_tstat_point']:+.2f} "
          f"ci[{fw['alpha_tstat_ci_low']:+.2f},{fw['alpha_tstat_ci_high']:+.2f}] "
          f"clears_t2={fw['clears_t2_point']} | Sharpe={fw['sharpe_point']:+.2f} "
          f"ci_low={fw['sharpe_ci_low']:+.2f}")
    oc = results["overnight_component_factor"]
    print(f"[T135] OVERNIGHT-component α={oc['alpha_annual_pct']:+.2f}% t={oc['alpha_tstat_point']:+.2f} "
          f"(diagnostic: where the spread lives)")
    dec = results["pnl_decomposition"]
    print(f"[T135] decomposition ann%: total={dec['total_net'].get('ann_return_pct',0):+.1f} "
          f"overnight={dec['overnight_component'].get('ann_return_pct',0):+.1f} "
          f"intraday={dec['intraday_component'].get('ann_return_pct',0):+.1f}")
    for name in SUB_PERIODS:
        r = results["sub_periods"][name]
        if r.get("skipped"):
            continue
        print(f"[T135] {name}: α={r['alpha_annual_pct']:+.2f}% t={r['alpha_tstat_point']:+.2f}")
    print(f"[T135] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
