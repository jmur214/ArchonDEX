#!/usr/bin/env python3
"""T-2026-06-18-207 — DRY-RUN the PIT (survivorship-corrected) universe expansion.

Backtests the canonical 6-edge production book on STATIC-109 vs the PIT historical
universe over a fixed window, to report the survivorship Sharpe delta. The PIT
Sharpe is EXPECTED to DROP — the delisted cohort underperformed ex-ante; that drop
is the survivorship bias being REMOVED (a less-biased estimate of the SAME answer),
NOT a regression to debug. Does NOT flip the prod flag. Offline + clean governor.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

START = os.environ.get("PIT_START", "2015-01-01")
END = os.environ.get("PIT_END", "2024-12-31")


def restore_clean_governor():
    import shutil
    gov, anc = ROOT / "data/governor", ROOT / "data/governor/_isolated_anchor"
    for f in ("edges.yml", "edge_weights.json", "regime_edge_performance.json",
              "lifecycle_history.csv"):
        if (anc / f).exists():
            shutil.copyfile(anc / f, gov / f)


def _data_map(tickers):
    from engines.data_manager.data_manager import DataManager
    dm = DataManager()
    out = {}
    for t in tickers:
        d = dm.load_cached(t, "1d")
        if d is not None and not d.empty:
            w = d[(d.index >= START) & (d.index <= END)]
            if len(w) > 50:
                out[t] = w
    return out


# Price-edges-only by default: the value/accruals edges' per-ticker fundamentals
# path makes the full 6-edge book intractable on 600+ tickers (~2h + stall risk),
# AND delisted names mostly lack fundamentals so the value edges barely touch the
# survivorship cohort. The 2 price edges trade the BROAD universe → they isolate
# the survivorship Sharpe effect cleanly + fast. Set PIT_FULL_BOOK=1 to override.
PRICE_EDGES = {"gap_fill_v1", "volume_anomaly_v1"}


def _run(tickers, label):
    from pathlib import Path as P
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    from orchestration.run_backtest_pure import run_backtest_pure
    edges, weights = DiscoveryEngine._build_production_edges(
        registry_path=P("data/governor/edges.yml"), alpha_config=None)
    if not os.environ.get("PIT_FULL_BOOK"):
        edges = {k: v for k, v in edges.items() if k in PRICE_EDGES}
        weights = {k: v for k, v in weights.items() if k in PRICE_EDGES}
    dm = _data_map(tickers)
    t0 = time.time()
    res = run_backtest_pure(edges=edges, edge_weights=weights, data_map=dm,
                            start_date=START, end_date=END, initial_capital=100000.0,
                            exec_params={})
    m = res.metrics if hasattr(res, "metrics") else res
    def g(*ks):
        for k in ks:
            if k in m:
                return m[k]
        return None
    sharpe = g("Sharpe Ratio", "sharpe")
    trades = g("num_trades", "total_trades", "Total Trades")
    cagr = g("CAGR_pct", "CAGR", "cagr")
    mdd = g("Max Drawdown", "MDD_pct", "max_drawdown")
    print(f"[PIT] {label}: edges={sorted(edges)} n_loaded={len(dm)} Sharpe={sharpe} "
          f"CAGR={cagr} MDD={mdd} trades={trades} ({time.time()-t0:.0f}s)", flush=True)
    return {"label": label, "n": len(dm), "sharpe": sharpe, "cagr": cagr,
            "mdd": mdd, "trades": trades}


def main() -> int:
    from engines.data_manager.universe_resolver import resolve_universe
    restore_clean_governor()
    cfg = json.loads((ROOT / "config/backtest_settings.json").read_text())
    static = list(cfg["tickers"])
    cached = {os.path.basename(p).replace("_1d.csv", "")
              for p in glob.glob("data/processed/*_1d.csv")}
    pit, info = resolve_universe(static_tickers=static, start=START, end=END,
                                 use_historical=True, cache_dir="data",
                                 available_filter=cached)
    print(f"[PIT] window {START}..{END} | static={len(static)} PIT={len(pit)} "
          f"(+{len(pit)-len(static)}) mode={info.get('mode')}", flush=True)

    rs = _run(static, "STATIC-109")
    rp = _run(pit, "PIT")
    print("\n[PIT] === SHARPE DELTA ===")
    try:
        d = float(rp["sharpe"]) - float(rs["sharpe"])
        pct = 100 * d / float(rs["sharpe"]) if rs["sharpe"] else float("nan")
        print(f"[PIT] static Sharpe={rs['sharpe']:.4f} -> PIT Sharpe={rp['sharpe']:.4f} "
              f"| delta={d:+.4f} ({pct:+.1f}%)")
        print("[PIT] (a DROP is the survivorship bias being REMOVED — expected, not a bug)")
    except Exception as e:
        print(f"[PIT] delta calc err: {e} | static={rs} pit={rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
