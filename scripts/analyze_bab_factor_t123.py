"""
scripts/analyze_bab_factor_t123.py
==================================
T-2026-06-06-123 — the DECISIVE cross-sectional alpha referendum (BAB).

Constructs the Frazzini-Pedersen Betting-Against-Beta factor on our universe and
runs it through the SAME factor machinery T-117/T-122 used, for an apples-to-apples
answer: does a recognized, free-data, FF-orthogonal CROSS-SECTIONAL factor clear
α t>2 in our substrate — or is the substrate genuinely empty of accessible
cross-sectional alpha?

Two constructions (monthly rebalance, daily P&L, beta vs the cap-weighted market
= FF MktRF to avoid the equal-weight artifact that bit T-122):
  1. BAB long-short beta-neutral (classic FP): long low-β leg levered to β=1,
     short high-β leg de-levered to β=1. Self-financing → excess = stream.
  2. BAB long-only low-beta (deployable): long bottom-beta tercile, inverse-vol.

Both decomposed with HAC + 1000-iter block-bootstrap CI on the α t-stat.

Reuse: core.factor_decomposition.load_factor_data, scripts.factor_decomp_substrate_honest
(regress_with_hac), engines.engine_f_governance.factor_alpha_gate
(compute_alpha_tstat_with_bootstrap_ci), core.metrics_engine.bootstrap_distribution.

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_bab_factor_t123
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

OUT_DIR = ROOT / "data" / "measurements" / "bab_gauntlet_t123"
OUT_JSON = OUT_DIR / "bab_factor_analysis.json"

START, END = "2014-01-01", "2025-12-31"
BETA_LOOKBACK = 252
VOL_WINDOW = 60
TERCILE = 1.0 / 3.0
COST_BPS_PER_TURNOVER = 5.0


def build_returns_panel(start: str, end: str) -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < BETA_LOOKBACK + 60:
            continue
        df = df[(df.index >= start) & (df.index <= end)]
        if len(df) < BETA_LOOKBACK + 60:
            continue
        cols.append(np.log(df["Close"].astype(float)).diff().rename(
            f.split("/")[-1].replace("_1d.csv", "")))
    if not cols:
        raise RuntimeError("no price data")
    return pd.concat(cols, axis=1).sort_index()


def build_bab_streams(rets: pd.DataFrame, factors: pd.DataFrame):
    """Monthly-rebalanced BAB. Returns (longshort_daily, longonly_daily)."""
    mkt = (factors["MktRF"] + factors["RF"]).reindex(rets.index).dropna()
    rets = rets.loc[mkt.index]
    mkt_dev = mkt - mkt.mean()
    # month-end rebalance dates present in the index
    rebal = pd.Series(rets.index, index=rets.index).groupby(
        [rets.index.year, rets.index.month]).last().tolist()

    ls_daily = pd.Series(0.0, index=rets.index)
    lo_daily = pd.Series(0.0, index=rets.index)
    prev_ls_w = pd.Series(dtype=float)
    prev_lo_w = pd.Series(dtype=float)
    ls_turn = pd.Series(0.0, index=rets.index)
    lo_turn = pd.Series(0.0, index=rets.index)

    for i, d in enumerate(rebal):
        win = rets.loc[:d].tail(BETA_LOOKBACK)
        if len(win) < BETA_LOOKBACK:
            continue
        m = mkt_dev.loc[win.index]
        var_m = float((m * m).mean())
        if var_m <= 0:
            continue
        # vectorized beta per name: cov(r_i, m)/var(m)
        cov = win.mul(m, axis=0).mean()
        beta = (cov / var_m).dropna()
        vol = win.std() * np.sqrt(252.0)
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

        def _legw(names):
            w = ivol.reindex(names).fillna(0.0)
            return w / w.sum() if w.sum() > 0 else w

        wL, wH = _legw(low), _legw(high)
        bL = float((beta.reindex(low) * wL).sum())
        bH = float((beta.reindex(high) * wH).sum())
        # classic FP: lever low leg to beta 1, de-lever high leg to beta 1
        ls_w = pd.Series(0.0, index=beta.index)
        if bL > 0:
            ls_w.loc[low] += wL / bL
        if bH > 0:
            ls_w.loc[high] -= wH / bH
        lo_w = pd.Series(0.0, index=beta.index)
        lo_w.loc[low] = wL  # long-only low-beta tercile

        # hold until next rebalance
        end_d = rebal[i + 1] if i + 1 < len(rebal) else rets.index[-1]
        hold = rets.loc[d:end_d].iloc[1:]  # day after rebalance onward
        if hold.empty:
            continue
        ls_daily.loc[hold.index] = hold.reindex(columns=ls_w.index).mul(ls_w, axis=1).sum(axis=1)
        lo_daily.loc[hold.index] = hold.reindex(columns=lo_w.index).mul(lo_w, axis=1).sum(axis=1)
        # turnover cost on rebalance day
        ls_turn_val = float((ls_w.subtract(prev_ls_w, fill_value=0.0)).abs().sum())
        lo_turn_val = float((lo_w.subtract(prev_lo_w, fill_value=0.0)).abs().sum())
        if not hold.empty:
            ls_turn.loc[hold.index[0]] = ls_turn_val
            lo_turn.loc[hold.index[0]] = lo_turn_val
        prev_ls_w, prev_lo_w = ls_w, lo_w

    cost = COST_BPS_PER_TURNOVER / 1e4
    rf = factors["RF"].reindex(rets.index).fillna(0.0)
    # long-short is self-financing → add RF so factor_report's excess = stream
    ls_net = (ls_daily - ls_turn * cost + rf).loc[ls_daily.ne(0).cumsum() > 0]
    lo_net = (lo_daily - lo_turn * cost).loc[lo_daily.ne(0).cumsum() > 0]
    return ls_net.dropna(), lo_net.dropna()


def factor_report(stream: pd.Series, factors: pd.DataFrame, label: str) -> Dict:
    hac = regress_with_hac(stream, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(stream, factors, min_obs=30, n_iter=1000, seed=0)
    bd = MetricsEngine.bootstrap_distribution(stream.dropna(), MetricsEngine.sharpe_ratio,
                                              n_iterations=1000, seed=0)
    return {
        "n_obs": hac.get("n_obs"),
        "alpha_annual_pct": hac.get("alpha_annualized", 0.0) * 100.0 if hac.get("ok") else None,
        "alpha_tstat_hac": hac.get("alpha_tstat_hac") if hac.get("ok") else None,
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
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    rets = build_returns_panel(START, END)
    print(f"[T123-α] panel: {rets.shape[1]} names, {rets.shape[0]} days "
          f"{rets.index.min().date()}..{rets.index.max().date()}")
    ls, lo = build_bab_streams(rets, factors)
    print(f"[T123-α] BAB streams: long-short {len(ls)}d, long-only {len(lo)}d")

    results = {
        "task": "T-2026-06-06-123",
        "window": [START, END],
        "construction": "monthly-rebalanced BAB, beta vs FF MktRF (cap-weighted), "
                        "inverse-vol legs, FP beta-neutralization; net of 5bps/turnover.",
        "bab_long_short_beta_neutral": factor_report(ls, factors, "bab_ls"),
        "bab_long_only_low_beta": factor_report(lo, factors, "bab_lo"),
        "correlation_long_short": book_correlation(ls),
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))

    for name in ("bab_long_short_beta_neutral", "bab_long_only_low_beta"):
        r = results[name]
        print(f"[T123-α] {name}: α={r['alpha_annual_pct']:+.2f}% "
              f"t={r['alpha_tstat_point']:+.2f} ci[{r['alpha_tstat_ci_low']:+.2f},{r['alpha_tstat_ci_high']:+.2f}] "
              f"clears_t2={r['clears_t2_point']} | MktRFβ={r['betas'].get('MktRF') if r['betas'] else '?'} "
              f"Sharpe={r['sharpe_point']:+.2f} ci_low={r['sharpe_ci_low']:+.2f}")
    print(f"[T123-α] book corr (LS): {results['correlation_long_short'].get('book_corr')}")
    print(f"[T123-α] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
