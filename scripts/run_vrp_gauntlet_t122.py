"""scripts/run_vrp_gauntlet_t122.py
====================================
T-2026-06-06-122 — run the Discovery gauntlet on the new VRP literature edge.

Mirrors scripts/run_spinoff_gauntlet_t041b.py (the prior "one hand-written
candidate through validate_candidate" precedent). VRP is registered
status='candidate', so the baseline ensemble (active+paused via list_tradeable)
excludes it; the with-candidate run adds it at full weight.

Window: 2021-2025 — the substrate where T-117 found 0/11 existing edges clear
factor-α t>2. The make-or-break test: does VRP (structurally non-FF5) clear
Gate 6 (FF5+Mom α t>2) where they all failed?

Output: data/measurements/vrp_gauntlet_t122/result.json
Determinism: PYTHONHASHSEED=0 via re-exec.

Usage: PYTHONHASHSEED=0 python -m scripts.run_vrp_gauntlet_t122 [--start 2021-01-01 --end 2025-12-31]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "data" / "measurements" / "vrp_gauntlet_t122"
OUTPUT_PATH = OUTPUT_DIR / "result.json"
DIAG_LOG_PATH = OUTPUT_DIR / "diagnostic.log"


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable,
                 [sys.executable, "-m", "scripts.run_vrp_gauntlet_t122", *sys.argv[1:]])


def _build_data_map(start: str, end: str):
    from engines.data_manager.data_manager import DataManager
    from engines.data_manager.universe_resolver import (
        discover_cached_tickers, resolve_universe,
    )
    cache_root = ROOT / "data"
    cached = discover_cached_tickers(cache_root, timeframe="1d")
    tickers, uni_info = resolve_universe(
        static_tickers=[], start=start, end=end, use_historical=True,
        cache_dir=cache_root, anchor_dates=None, available_filter=cached,
    )
    print(f"[T122] universe: mode={uni_info['mode']} "
          f"hist={uni_info.get('n_historical_union')} "
          f"filtered={uni_info.get('n_after_available_filter')}", flush=True)
    dm = DataManager(cache_dir=str(cache_root / "processed"))
    data_map = dm.ensure_data(tickers, start, end, timeframe="1d")
    print(f"[T122] data_map: {len(data_map)} tickers", flush=True)
    return data_map, uni_info


def _candidate_spec() -> dict:
    from engines.engine_a_alpha.edges.volatility_risk_premium_edge import (
        VolatilityRiskPremiumEdge,
    )
    return {
        "edge_id": "volatility_risk_premium_v1",
        "module": VolatilityRiskPremiumEdge.__module__,
        "class": VolatilityRiskPremiumEdge.__name__,
        "category": VolatilityRiskPremiumEdge.CATEGORY,
        "params": dict(VolatilityRiskPremiumEdge.DEFAULT_PARAMS),
        "status": "candidate",
        "version": "1.0.0",
        "origin": "manual_dispatch_t122",
    }


def main() -> int:
    _reexec_if_hashseed_unset()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default="2025-12-31")
    args = ap.parse_args()

    t0 = time.time()
    print(f"[T122] window: {args.start} → {args.end}", flush=True)
    data_map, uni_info = _build_data_map(args.start, args.end)

    from engines.engine_d_discovery.discovery import DiscoveryEngine
    disc = DiscoveryEngine()
    cand = _candidate_spec()
    print(f"[T122] candidate: {cand['edge_id']} (status={cand['status']})", flush=True)

    result = disc.validate_candidate(
        cand, data_map,
        start_date=args.start, end_date=args.end,
        diagnostic_log_path=str(DIAG_LOG_PATH),
        n_trials_for_dsr=1,
    )
    elapsed = time.time() - t0

    out = {
        "task_id": "T-2026-06-06-122",
        "candidate": cand,
        "window": [args.start, args.end],
        "wall_seconds": round(elapsed, 1),
        "universe_info": uni_info,
        "n_tickers": len(data_map),
        "gauntlet_result": result,
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[T122] gauntlet done in {elapsed/60:.1f} min → {OUTPUT_PATH}", flush=True)
    for k in ("gate_1_passed", "gate_2_passed", "gate_4_passed", "gate_5_passed",
              "gate_6_passed", "gate_7_passed", "gate_8_passed", "passed_all_gates",
              "attribution_sharpe", "factor_alpha_annualized", "factor_alpha_tstat",
              "factor_alpha_reason"):
        print(f"  {k}: {result.get(k)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
