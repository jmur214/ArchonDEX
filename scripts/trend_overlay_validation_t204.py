#!/usr/bin/env python
# scripts/trend_overlay_validation_t204.py
"""T-204 — standalone validation of the trend overlay (the PRE-REGISTERED
9-arm grid only). Deterministic, on-disk stooq ETF data; no network.

Runs ONLY the arms fixed in
docs/Audit/trend_overlay_preregistration_t204_2026_06_18.md and reports, per
arm: annualized return, Sharpe (point + block-bootstrap ci_low), Sortino,
MDD, skew, time-in-market, round-trips/yr, capture-efficiency vs buy-hold,
and per-crisis-window drawdown (GFC/COVID/2022).

This is the STANDALONE shape validation — it does NOT compose the overlay
into sizing and does NOT run the beat-the-robo measurement (both deferred).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pandas as pd

from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import (
    LOOKBACK_DAYS,
    TrendOverlay,
    buy_hold_returns,
    overlay_returns,
    sleeve_returns,
)

ROOT = Path(__file__).resolve().parents[1]
STOOQ = ROOT / "data" / "raw" / "stooq" / "daily" / "us"
PATHS = {
    "SPY": STOOQ / "nyse etfs" / "2" / "spy.us.txt",
    "AGG": STOOQ / "nyse etfs" / "1" / "agg.us.txt",
    "GLD": STOOQ / "nyse etfs" / "1" / "gld.us.txt",
}
CRISES = {
    "GFC_2008": ("2007-10-09", "2009-03-09"),
    "COVID_2020": ("2020-02-19", "2020-03-23"),
    "BEAR_2022": ("2022-01-03", "2022-10-12"),
}


def load_close(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df.set_index("date").sort_index()["close"].astype(float)


def _equity(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).cumprod()


def metrics(returns: pd.Series, *, bh_sharpe: float = None) -> Dict:
    eq = _equity(returns)
    yrs = max(1e-9, (returns.index[-1] - returns.index[0]).days / 365.25)
    cagr = float(eq.iloc[-1] ** (1.0 / yrs) - 1.0)
    sharpe = float(ME.sharpe_ratio(returns))
    boot = ME.bootstrap_distribution(returns, ME.sharpe_ratio, n_iterations=1000, seed=0)
    # AQR's positive trend-skew lives at LONGER horizons ("skew grows over
    # horizon"); daily skew of a long/FLAT (no short) overlay is dominated by
    # a zero-spike. Report both — monthly is the fair test of the convexity claim.
    monthly = (1.0 + returns).resample("ME").prod() - 1.0
    out = {
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "sharpe_ci_low": round(float(boot["ci_low"]), 3),
        "sortino": round(float(ME.sortino_ratio(returns)), 3),
        "mdd": round(float(ME.max_drawdown(eq)), 4),
        "skew_daily": round(float(ME.skewness(returns)), 3),
        "skew_monthly": round(float(ME.skewness(monthly)), 3),
        "n_days": int(len(returns)),
    }
    if bh_sharpe is not None:
        out["capture_efficiency"] = (round(sharpe / bh_sharpe, 3)
                                     if bh_sharpe > 1e-9 else None)
    return out


def crisis_mdds(returns: pd.Series) -> Dict[str, float]:
    out = {}
    for name, (a, b) in CRISES.items():
        seg = returns.loc[a:b]
        out[name] = round(float(ME.max_drawdown(_equity(seg))), 4) if len(seg) > 2 else None
    return out


def position_stats(close: pd.Series, k: int) -> Dict:
    pos = TrendOverlay(k, enabled=True).exposure(close).shift(1).dropna()
    flips = int((pos.diff().abs() > 0.5).sum())
    yrs = max(1e-9, (pos.index[-1] - pos.index[0]).days / 365.25)
    return {"time_in_market": round(float(pos.mean()), 3),
            "round_trips_per_yr": round(flips / 2.0 / yrs, 2)}


def main() -> int:
    closes = {k: load_close(p) for k, p in PATHS.items()}
    spy = closes["SPY"]
    results = {"arms": [], "baselines": {}}

    # --- baselines (buy-hold) -------------------------------------------- #
    bh_spy = buy_hold_returns(spy)
    bh_spy_m = metrics(bh_spy)
    results["baselines"]["SPY_buy_hold"] = {**bh_spy_m, "crisis": crisis_mdds(bh_spy)}
    bh_sleeve = pd.concat(
        [buy_hold_returns(closes[k]).rename(k) / 3.0 for k in ["SPY", "AGG", "GLD"]],
        axis=1).dropna(how="all").sum(axis=1, min_count=1).dropna()
    bh_sleeve_m = metrics(bh_sleeve)
    results["baselines"]["EW_sleeve_buy_hold"] = {**bh_sleeve_m, "crisis": crisis_mdds(bh_sleeve)}

    spy_bh_sharpe = bh_spy_m["sharpe"]

    # --- (A) SPY long/flat: 3 lookbacks x {cash, AGG} = 6 arms ----------- #
    agg_ret = buy_hold_returns(closes["AGG"])
    for mo, k in LOOKBACK_DAYS.items():
        for leg, dret in (("cash", None), ("AGG", agg_ret)):
            r = overlay_returns(spy, k, defensive_returns=dret)
            m = metrics(r, bh_sharpe=spy_bh_sharpe)
            results["arms"].append({
                "structure": "SPY_long_flat", "lookback_mo": mo, "defensive": leg,
                **m, **position_stats(spy, k), "crisis": crisis_mdds(r),
            })

    # --- (B) 3-asset diversified sleeve: 3 lookbacks = 3 arms ------------ #
    for mo, k in LOOKBACK_DAYS.items():
        r = sleeve_returns({x: closes[x] for x in ["SPY", "AGG", "GLD"]}, k)
        m = metrics(r, bh_sharpe=bh_sleeve_m["sharpe"])
        results["arms"].append({
            "structure": "EW_trend_sleeve", "lookback_mo": mo, "defensive": "cash",
            **m, "crisis": crisis_mdds(r),
        })

    # --- print ----------------------------------------------------------- #
    print(f"=== T-204 trend-overlay validation | {len(results['arms'])} pre-registered arms ===")
    print(f"window: {spy.index[0].date()} → {spy.index[-1].date()}\n")
    print("BASELINES (buy-hold):")
    for n, m in results["baselines"].items():
        print(f"  {n:22s} CAGR {m['cagr']:+.2%}  Sharpe {m['sharpe']:.2f} "
              f"(ci_low {m['sharpe_ci_low']:.2f})  MDD {m['mdd']:.1%}  "
              f"skew d/m {m['skew_daily']:+.2f}/{m['skew_monthly']:+.2f}  crisis {m['crisis']}")
    print("\nARMS:")
    hdr = (f"  {'structure':16s} {'k':>4s} {'def':>5s} {'CAGR':>7s} {'Shrp':>5s} "
           f"{'cilo':>5s} {'MDD':>7s} {'skD':>6s} {'skM':>6s} {'capt':>5s} {'inMkt':>6s} {'rt/y':>5s}")
    print(hdr)
    for a in results["arms"]:
        ce = a.get("capture_efficiency")
        ce_s = f"{ce:.2f}" if ce is not None else "  - "
        print(f"  {a['structure']:16s} {a['lookback_mo']:>3d}m {a['defensive']:>5s} "
              f"{a['cagr']:>+6.2%} {a['sharpe']:>5.2f} {a['sharpe_ci_low']:>5.2f} "
              f"{a['mdd']:>+6.1%} {a['skew_daily']:>+6.2f} {a['skew_monthly']:>+6.2f} {ce_s:>5s} "
              f"{a.get('time_in_market','-'):>6} {a.get('round_trips_per_yr','-'):>5}")
        print(f"      crisis MDDs: {a['crisis']}")

    out = ROOT / "data" / "research" / "trend_overlay_validation_t204.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
