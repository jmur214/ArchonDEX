#!/usr/bin/env python
# scripts/trend_wider_breadth_validation_t214.py
"""T-214 — does WIDER cross-asset breadth strengthen the trend sleeve's
positive-skew convexity (the thing T-204 found needs diversification)?

Runs ONLY the pre-registered arms
(trend_wider_breadth_preregistration_t214_2026_06_18.md): the Wide-9 sleeve
× lookback {3,5,10mo} × weighting {equal, inverse-vol}, vs the T-204 3-asset
EW sleeve, ALL on the common window (2006-02, DBC inception). Reuses
core/trend_overlay.py + the T-204 metrics harness. Deterministic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import overlay_returns, sleeve_returns, buy_hold_returns
from scripts.trend_overlay_validation_t204 import (
    CRISES, load_close, metrics, crisis_mdds, _equity, STOOQ,
)

ROOT = Path(__file__).resolve().parents[1]

# pre-registered Wide-9 (macro-spanning; LOCKED) + the T-204 3-asset.
WIDE9 = {
    "SPY": "nyse etfs/2/spy.us.txt", "EFA": "nyse etfs/1/efa.us.txt",
    "EEM": "nyse etfs/1/eem.us.txt", "AGG": "nyse etfs/1/agg.us.txt",
    "TLT": "nasdaq etfs/1/tlt.us.txt", "TIP": "nyse etfs/1/tip.us.txt",
    "GLD": "nyse etfs/1/gld.us.txt", "DBC": "nyse etfs/1/dbc.us.txt",
    "VNQ": "nyse etfs/1/vnq.us.txt",
}
THREE = ["SPY", "AGG", "GLD"]
LOOKBACKS = {3: 63, 5: 105, 10: 210}
VOL_WINDOW = 60   # pre-registered causal trailing window for inverse-vol


def _resolve(rel: str) -> Path:
    """Locate a stooq file by basename (subdir digit varies)."""
    base = rel.split("/")[-1]
    hits = list(STOOQ.rglob(base))
    return hits[0] if hits else (STOOQ / rel)


def load_all() -> Dict[str, pd.Series]:
    return {k: load_close(_resolve(v)) for k, v in WIDE9.items()}


def common_window(closes: Dict[str, pd.Series]) -> pd.Timestamp:
    return max(s.index[0] for s in closes.values())


def inverse_vol_sleeve(closes: Dict[str, pd.Series], k: int,
                       start: pd.Timestamp) -> pd.Series:
    """Wide sleeve, each asset long/flat (cash off-leg), combined with
    CAUSAL inverse-vol weights (1/σ on a trailing 60-day asset-return vol,
    using data up to t-1, renormalized daily)."""
    per_asset, inv_vol = {}, {}
    for name, close in closes.items():
        per_asset[name] = overlay_returns(close, k)          # cash off-leg
        raw = close.pct_change()
        sd = raw.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std().shift(1)
        inv_vol[name] = (1.0 / sd).replace([np.inf, -np.inf], np.nan)
    R = pd.DataFrame(per_asset)
    W = pd.DataFrame(inv_vol).reindex(R.index)
    W = W.where(R.notna())                  # only weight assets present that day
    W = W.div(W.sum(axis=1), axis=0)        # renormalize to sum 1 each day
    sleeve = (R * W).sum(axis=1, min_count=1)
    return sleeve.loc[start:].dropna()


def equal_weight_sleeve(closes: Dict[str, pd.Series], k: int,
                        start: pd.Timestamp) -> pd.Series:
    return sleeve_returns(closes, k).loc[start:].dropna()


def buyhold_sleeve(closes: Dict[str, pd.Series], start: pd.Timestamp) -> pd.Series:
    n = len(closes)
    parts = [buy_hold_returns(c).rename(name) / n for name, c in closes.items()]
    return pd.concat(parts, axis=1).dropna(how="all").sum(axis=1, min_count=1).loc[start:].dropna()


def mean_pairwise_corr(closes: Dict[str, pd.Series], a=None, b=None) -> float:
    rets = pd.DataFrame({k: c.pct_change() for k, c in closes.items()})
    if a is not None:
        rets = rets.loc[a:b]
    if len(rets) < 5:
        return float("nan")
    cm = rets.corr().values
    iu = np.triu_indices_from(cm, k=1)
    return round(float(np.nanmean(cm[iu])), 3)


def main() -> int:
    closes = load_all()
    start = common_window(closes)
    three = {k: closes[k] for k in THREE}
    results = {"window_start": str(start.date()), "arms": [], "baselines": {}, "correlation": {}}

    # baselines on the COMMON window
    bh3 = buyhold_sleeve(three, start)
    bh9 = buyhold_sleeve(closes, start)
    results["baselines"]["3asset_buy_hold"] = {**metrics(bh3), "crisis": crisis_mdds(bh3)}
    results["baselines"]["wide9_buy_hold"] = {**metrics(bh9), "crisis": crisis_mdds(bh9)}

    # T-204 3-asset EW sleeve (comparison) on the common window
    for mo, k in LOOKBACKS.items():
        r = equal_weight_sleeve(three, k, start)
        results["arms"].append({"sleeve": "3asset", "weight": "equal", "lookback_mo": mo,
                                **metrics(r, bh_sharpe=metrics(bh3)["sharpe"]),
                                "crisis": crisis_mdds(r)})

    # Wide-9 × {equal, inverse-vol} × {3,5,10mo}  (the 6 pre-registered arms)
    bh9_sharpe = metrics(bh9)["sharpe"]
    for mo, k in LOOKBACKS.items():
        for wname, fn in (("equal", equal_weight_sleeve), ("inverse_vol", None)):
            r = (equal_weight_sleeve(closes, k, start) if wname == "equal"
                 else inverse_vol_sleeve(closes, k, start))
            results["arms"].append({"sleeve": "wide9", "weight": wname, "lookback_mo": mo,
                                    **metrics(r, bh_sharpe=bh9_sharpe),
                                    "crisis": crisis_mdds(r)})

    # the honest-caveat check: mean pairwise correlation, calm vs each crisis
    results["correlation"]["wide9_full"] = mean_pairwise_corr(closes)
    results["correlation"]["3asset_full"] = mean_pairwise_corr(three)
    for name, (a, b) in CRISES.items():
        results["correlation"][f"wide9_{name}"] = mean_pairwise_corr(closes, a, b)
        results["correlation"][f"3asset_{name}"] = mean_pairwise_corr(three, a, b)

    # ---- print ---- #
    print(f"=== T-214 wider-breadth trend sleeve | window {start.date()} → 2026-05-22 ===\n")
    print("BASELINES (buy-hold, common window):")
    for n, m in results["baselines"].items():
        print(f"  {n:20s} CAGR {m['cagr']:+.2%}  Sharpe {m['sharpe']:.2f}({m['sharpe_ci_low']:.2f})  "
              f"MDD {m['mdd']:.1%}  skew d/m {m['skew_daily']:+.2f}/{m['skew_monthly']:+.2f}")
    print("\nARMS:")
    print(f"  {'sleeve':8s} {'weight':12s} {'k':>3s} {'CAGR':>7s} {'Shrp':>5s} {'cilo':>5s} "
          f"{'MDD':>7s} {'skM':>6s} {'capt':>5s}")
    for a in results["arms"]:
        print(f"  {a['sleeve']:8s} {a['weight']:12s} {a['lookback_mo']:>2d}m {a['cagr']:>+6.2%} "
              f"{a['sharpe']:>5.2f} {a['sharpe_ci_low']:>5.2f} {a['mdd']:>+6.1%} "
              f"{a['skew_monthly']:>+6.2f} {a.get('capture_efficiency','-'):>5}")
        print(f"      crisis MDDs: {a['crisis']}")
    print("\nMEAN PAIRWISE CORRELATION (does breadth diversify the TAIL or just calm?):")
    for k, v in results["correlation"].items():
        print(f"  {k:24s} {v}")

    out = ROOT / "data" / "research" / "trend_wider_breadth_t214.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
