#!/usr/bin/env python
# scripts/mf_etf_satellite_t253.py
"""T-253 — bought MF-ETF (DBMF/KMLM) vs our trend overlay as the barbell's
convex satellite. FREE, on-disk stooq daily; deterministic. Reuses
core/trend_overlay (our sleeve) + the T-204 metrics harness. [NN-SHARPE-CI]
block-bootstrap; [NN-FAIL-CLOSED] on a degenerate series.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import sleeve_returns, buy_hold_returns
from scripts.trend_overlay_validation_t204 import load_close, metrics, STOOQ

ROOT = Path(__file__).resolve().parents[1]
CRISES = {"COVID_2020": ("2020-02-19", "2020-03-23"),
          "BEAR_2022": ("2022-01-03", "2022-10-12")}
SATELLITE_W = 0.20            # pre-registered barbell satellite weight


def _resolve(base: str) -> Path:
    hits = list(STOOQ.rglob(base))
    if not hits:
        raise RuntimeError(f"[NN-FAIL-CLOSED] {base} not found on disk")
    return hits[0]


def crisis_returns(returns: pd.Series) -> Dict[str, Optional[float]]:
    out = {}
    for nm, (a, b) in CRISES.items():
        seg = returns.loc[a:b]
        out[nm] = round(float((1 + seg).prod() - 1), 4) if len(seg) > 2 else None
    return out


def _full(returns: pd.Series, bh_ref: Optional[float] = None) -> Dict:
    m = metrics(returns)
    boot = ME.bootstrap_distribution(returns, ME.sortino_ratio, n_iterations=1000, seed=0)
    m["sortino_ci_low"] = round(float(boot["ci_low"]), 3)
    m["crisis_returns"] = crisis_returns(returns)
    # calm = full-window return minus the crisis windows (the carry-bleed read)
    return m


def main() -> int:
    closes = {
        "DBMF": load_close(_resolve("dbmf.us.txt")),
        "KMLM": load_close(_resolve("kmlm.us.txt")),
        "SPY": load_close(_resolve("spy.us.txt")),
        "AGG": load_close(_resolve("agg.us.txt")),
        "GLD": load_close(_resolve("gld.us.txt")),
    }
    sat_ret = {
        "our_trend_sleeve": sleeve_returns({k: closes[k] for k in ("SPY", "AGG", "GLD")}, 105),
        "DBMF": buy_hold_returns(closes["DBMF"]),
        "KMLM": buy_hold_returns(closes["KMLM"]),
    }
    agg_ret = buy_hold_returns(closes["AGG"])

    results = {"satellites": {}, "barbells": {}}
    # windows: DBMF 2019-05+, KMLM 2020-12+. Evaluate each satellite (and our
    # sleeve) on the DBMF window for the head-to-head; KMLM on its own window.
    dbmf_start = sat_ret["DBMF"].index[0]
    kmlm_start = sat_ret["KMLM"].index[0]

    def on(window_start, r):
        return r.loc[window_start:].dropna()

    # --- standalone (each on the relevant window) ----------------------- #
    for name, r in sat_ret.items():
        ws = kmlm_start if name == "KMLM" else dbmf_start
        results["satellites"][name] = {"window_start": str(ws.date()), **_full(on(ws, r))}

    # --- 80/20 barbell: AGG core + 20% satellite (DBMF window) ----------- #
    def barbell(sat_r, ws):
        s = on(ws, sat_r)
        a = agg_ret.reindex(s.index).fillna(0.0)
        bb = SATELLITE_W * s + (1 - SATELLITE_W) * a
        return bb.dropna()
    for name, r in sat_ret.items():
        ws = kmlm_start if name == "KMLM" else dbmf_start
        bb = barbell(r, ws)
        results["barbells"][f"AGG80_{name}20"] = {"window_start": str(ws.date()),
                                                  **_full(bb)}
    # also the pure AGG core for reference (DBMF window)
    results["barbells"]["AGG_core_only"] = {"window_start": str(dbmf_start.date()),
                                            **_full(on(dbmf_start, agg_ret))}

    # --- print ---------------------------------------------------------- #
    print("=== T-253 MF-ETF vs our trend overlay as the convex satellite ===")
    print("(crisis-window RETURNS = the convexity test: does it print POSITIVE when equities crash?)\n")
    print("STANDALONE SATELLITES:")
    print(f"  {'satellite':18s} {'from':>10s} {'Sortino(ci)':>13s} {'MaxDD':>7s} {'CAGR':>7s} "
          f"{'COVID':>7s} {'2022':>7s}")
    for n, m in results["satellites"].items():
        cr = m["crisis_returns"]
        cov = f"{cr['COVID_2020']:+.0%}" if cr['COVID_2020'] is not None else "  n/a"
        b22 = f"{cr['BEAR_2022']:+.0%}" if cr['BEAR_2022'] is not None else "  n/a"
        print(f"  {n:18s} {m['window_start']:>10s} {m['sortino']:>6.2f}({m['sortino_ci_low']:>5.2f}) "
              f"{m['mdd']:>+6.1%} {m['cagr']:>+6.1%} {cov:>7s} {b22:>7s}")
    print("\n80/20 BARBELL (AGG safe core + 20% satellite, DBMF window):")
    print(f"  {'barbell':22s} {'Sortino(ci)':>13s} {'MaxDD':>7s} {'CAGR':>7s} {'COVID':>7s} {'2022':>7s}")
    for n, m in results["barbells"].items():
        cr = m["crisis_returns"]
        cov = f"{cr['COVID_2020']:+.0%}" if cr['COVID_2020'] is not None else "  n/a"
        b22 = f"{cr['BEAR_2022']:+.0%}" if cr['BEAR_2022'] is not None else "  n/a"
        print(f"  {n:22s} {m['sortino']:>6.2f}({m['sortino_ci_low']:>5.2f}) {m['mdd']:>+6.1%} "
              f"{m['cagr']:>+6.1%} {cov:>7s} {b22:>7s}")

    out = ROOT / "data" / "research" / "mf_etf_satellite_t253.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
