"""
scripts/analyze_vrp_factor_t122.py
==================================
T-2026-06-06-122 — rigorous factor-α test of the VRP edge's signal.

WHY analytical (not the full engine):
The Discovery gauntlet run (scripts/run_vrp_gauntlet_t122.py, 2014-2025) found
VRP fails Gate 1 with contribution EXACTLY +0.000 — the cross-sectional, rank-
and-normalize ensemble constructor WASHES OUT a uniform market-timing signal
(every ticker gets the same score, so the relative ranking is unchanged and the
portfolio is identical with/without VRP). This is the same structural reason the
macro_* timing edges (which also emit a uniform tilt, see macro_yield_curve_edge
line 180) are inert. So the engine never computes Gate 6 for VRP.

But VRP's signal IS a volatility-managed market overlay (Moreira-Muir 2017): be
long the market scaled by the VIX−RV premium, flat when it inverts. This script
reproduces the edge's REAL signal (same VIX−RV formula as compute_signals,
vectorized, point-in-time) and maps it to the vol-managed equal-weight market
return — the faithful standalone object — then runs it through the SAME factor
machinery T-117 used on the existing 13 edges, for an apples-to-apples answer to
"does VRP clear factor-α t>2 where 0/11 existing edges failed?"

Reuse: core.factor_decomposition.load_factor_data, scripts.factor_decomp_substrate_honest
(regress_with_hac), engines.engine_f_governance.factor_alpha_gate
(compute_alpha_tstat_with_bootstrap_ci), core.metrics_engine.bootstrap_distribution.

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_vrp_factor_t122
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
from engines.engine_a_alpha.edges.volatility_risk_premium_edge import (  # noqa: E402
    VolatilityRiskPremiumEdge,
)

OUT_DIR = ROOT / "data" / "measurements" / "vrp_gauntlet_t122"
OUT_JSON = OUT_DIR / "vrp_factor_analysis.json"

START, END = "2014-01-01", "2025-12-31"
RV_LOOKBACK = 21          # matches VRP DEFAULT_PARAMS
VRP_THRESHOLD = 0.0
VRP_FULL_SCALE = 0.05
COST_BPS_PER_TURNOVER = 5.0   # 5 bps per unit |Δscale| (vol-managed = low turnover)


def build_market_return(start: str, end: str) -> pd.Series:
    """Equal-weight daily return of the processed universe — the market proxy
    the VRP edge's _market_realized_vol sees internally."""
    rets = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 252:
            continue
        df = df[(df.index >= start) & (df.index <= end)]
        if len(df) < 252:
            continue
        r = np.log(df["Close"].astype(float)).diff()
        rets.append(r.rename(f.split("/")[-1].replace("_1d.csv", "")))
    if not rets:
        raise RuntimeError("no universe price data found")
    panel = pd.concat(rets, axis=1)
    mkt = panel.mean(axis=1).dropna()
    mkt.name = "mkt_ew"
    return mkt


def vrp_signal_series(mkt_ret: pd.Series) -> pd.Series:
    """Daily VRP scale ∈[0,1] using the SAME VIX−RV formula as the edge
    (point-in-time, no lookahead). Reuses the edge's VIX loader."""
    edge = VolatilityRiskPremiumEdge()
    vix = edge._ensure_vix_loaded()  # decimal-vol conversion done in _implied_vol_at
    if vix is None:
        raise RuntimeError("VIX cache unavailable")
    # realized vol: trailing RV_LOOKBACK std of market return, annualized
    realized = mkt_ret.rolling(RV_LOOKBACK).std() * np.sqrt(252)
    # implied vol at each date (asof, /100), aligned to market calendar
    implied = pd.Series(
        {d: (vix.asof(d) / 100.0 if pd.notna(vix.asof(d)) else np.nan)
         for d in mkt_ret.index},
        name="implied",
    )
    spread = implied - realized
    scale = ((spread - VRP_THRESHOLD) / max(VRP_FULL_SCALE, 1e-9)).clip(0.0, 1.0)
    scale = scale.where(spread > VRP_THRESHOLD, 0.0)
    scale.name = "vrp_scale"
    return scale


def vrp_return_stream(mkt_ret: pd.Series, scale: pd.Series, net: bool) -> pd.Series:
    """Vol-managed market return: scale_{t-1} * market_return_t, minus cost on
    |Δscale| when net=True. Signal lagged one day → no lookahead."""
    lagged = scale.shift(1).reindex(mkt_ret.index).fillna(0.0)
    gross = lagged * mkt_ret
    if not net:
        return gross.dropna()
    turnover = lagged.diff().abs().fillna(0.0)
    cost = turnover * (COST_BPS_PER_TURNOVER / 1e4)
    return (gross - cost).dropna()


def factor_report(stream: pd.Series, factors: pd.DataFrame, label: str) -> Dict:
    hac = regress_with_hac(stream, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(stream, factors, min_obs=30,
                                               n_iter=1000, seed=0)
    bd = MetricsEngine.bootstrap_distribution(
        stream.dropna(), MetricsEngine.sharpe_ratio, n_iterations=1000, seed=0)
    out = {
        "n_obs": hac.get("n_obs"),
        "alpha_annual_pct": hac.get("alpha_annualized", 0.0) * 100.0 if hac.get("ok") else None,
        "alpha_tstat_hac": hac.get("alpha_tstat_hac") if hac.get("ok") else None,
        "alpha_tstat_ci_low": ci.alpha_tstat_ci_low,
        "alpha_tstat_ci_high": ci.alpha_tstat_ci_high,
        "alpha_tstat_point": ci.alpha_tstat_point,
        "clears_t2_point": ci.alpha_tstat_point > 2.0,
        "clears_t2_strict_ci": ci.alpha_tstat_ci_low > 2.0,
        "p_alpha_above_zero": hac.get("alpha_p_above_zero_bootstrap") if hac.get("ok") else None,
        "betas": {k: round(v["beta"], 4) for k, v in hac.get("betas", {}).items()} if hac.get("ok") else None,
        "r_squared": hac.get("r_squared") if hac.get("ok") else None,
        "sharpe_point": bd["point_estimate"],
        "sharpe_ci_low": bd["ci_low"],
        "sharpe_ci_high": bd["ci_high"],
    }
    return out


def book_correlation(vrp_stream: pd.Series) -> Dict:
    """Correlation of VRP return to the existing 6-active-edge book + to the
    market, on the 2014-2025 deep run (reuse T-117 substrate 0dcae34c)."""
    out = {"market_corr": None, "book_corr": None}
    try:
        p = glob.glob(str(ROOT / "data" / "trade_logs" / "0dcae34c*" / "trades.csv"))[0]
        tr = pd.read_csv(p, usecols=["timestamp", "edge_id", "pnl"])
        tr["timestamp"] = pd.to_datetime(tr["timestamp"], errors="coerce")
        tr["pnl"] = pd.to_numeric(tr["pnl"], errors="coerce")
        tr = tr.dropna(subset=["pnl"])
        book = tr.groupby(tr["timestamp"].dt.normalize())["pnl"].sum() / 100_000.0
        df = pd.concat({"vrp": vrp_stream, "book": book}, axis=1).dropna()
        if len(df) > 30:
            out["book_corr"] = float(df["vrp"].corr(df["book"]))
            out["book_overlap_days"] = int(len(df))
    except Exception as e:
        out["book_corr_error"] = str(e)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    mkt = build_market_return(START, END)
    print(f"[T122-α] market proxy: {len(mkt)} days {mkt.index.min().date()}..{mkt.index.max().date()}")
    scale = vrp_signal_series(mkt)
    active_frac = float((scale > 0).mean())
    print(f"[T122-α] VRP scale: mean={scale.mean():.3f} active_days={active_frac:.2f}")

    gross = vrp_return_stream(mkt, scale, net=False)
    net = vrp_return_stream(mkt, scale, net=True)

    # CLEAN Moreira-Muir test: apply the VRP scale to the CAP-WEIGHTED market
    # (FF MktRF) so the only residual is the TIMING — removes the equal-weight
    # proxy's own negative α. Managed total return = scale*MktRF + RF (cash on
    # the uninvested part); factor_report's excess = scale_{t-1}*MktRF.
    lagged = scale.shift(1).reindex(factors.index).fillna(0.0)
    turnover_c = lagged.diff().abs().fillna(0.0) * (COST_BPS_PER_TURNOVER / 1e4)
    vrp_cap = (lagged * factors["MktRF"] + factors["RF"] - turnover_c).dropna()

    results = {
        "task": "T-2026-06-06-122",
        "interpretation": "vol-managed equal-weight market overlay (Moreira-Muir); "
                          "the standalone object the VRP signal represents, since the "
                          "cross-sectional ensemble harness washes out a uniform timing "
                          "signal (gauntlet Gate-1 contribution = +0.000).",
        "window": [START, END],
        "vrp_scale_active_frac": active_frac,
        "vrp_scale_mean": float(scale.mean()),
        "factor_alpha_net": factor_report(net, factors, "vrp_net"),
        "factor_alpha_gross": factor_report(gross, factors, "vrp_gross"),
        "factor_alpha_capweight_timing": factor_report(vrp_cap, factors, "vrp_capweight"),
        "market_factor_alpha_reference": factor_report(mkt, factors, "mkt_ew"),
        "correlation": book_correlation(net),
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))

    n = results["factor_alpha_net"]
    print(f"[T122-α] VRP (net) factor-α: a={n['alpha_annual_pct']:+.2f}% "
          f"t_point={n['alpha_tstat_point']:+.2f} ci[{n['alpha_tstat_ci_low']:+.2f},{n['alpha_tstat_ci_high']:+.2f}] "
          f"clears_t2={n['clears_t2_point']} | Sharpe={n['sharpe_point']:+.2f} ci_low={n['sharpe_ci_low']:+.2f}")
    print(f"[T122-α] VRP MktRF beta={n['betas'].get('MktRF') if n['betas'] else '?'} R²={n['r_squared']:.2f}")
    print(f"[T122-α] book corr={results['correlation'].get('book_corr')}")
    print(f"[T122-α] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
