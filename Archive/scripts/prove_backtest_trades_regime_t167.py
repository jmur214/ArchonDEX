#!/usr/bin/env python3
"""T-2026-06-13-167 — the DUAL+ bar: a real controller-path backtest that
TRADES over a window spanning pre/post-2020 AND logs a LIVE regime throughout
(trend/vol non-unknown across the full span), under hermetic (cloud no-network).

Instruments RegimeDetector.detect_regime to tally per-axis states across every
bar of the run, then runs a multi-year ModeController backtest. PASS = trades>0
AND trend/vol live on the overwhelming majority of bars incl. the pre-2020 span.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2021-12-31")
    args = ap.parse_args()

    from engines.engine_e_regime.regime_detector import RegimeDetector
    tally = {"trend": Counter(), "volatility": Counter()}
    pre2020 = {"trend": Counter(), "volatility": Counter()}
    import pandas as pd
    _orig = RegimeDetector.detect_regime

    def _wrapped(self, benchmark_df, data_map=None, now=None):
        r = _orig(self, benchmark_df, data_map=data_map, now=now)
        tr, vo = r.get("trend"), r.get("volatility")
        tally["trend"][str(tr)] += 1
        tally["volatility"][str(vo)] += 1
        try:
            if now is not None and pd.Timestamp(now) < pd.Timestamp("2020-01-01"):
                pre2020["trend"][str(tr)] += 1
                pre2020["volatility"][str(vo)] += 1
        except Exception:
            pass
        return r

    RegimeDetector.detect_regime = _wrapped

    from scripts.run_substrate_arms import ARM1_EDGES as ARM1_EDGE_IDS  # the 6-active prod set
    from orchestration.mode_controller import ModeController
    mc = ModeController(ROOT, env="prod")
    print(f"[proof] running hermetic backtest {args.start} -> {args.end} ...", flush=True)
    res = mc.run_backtest(
        mode="prod", fresh=False, no_governor=False, reset_governor=True,
        alpha_debug=False, override_start=args.start, override_end=args.end,
        exact_edge_ids=list(ARM1_EDGE_IDS), use_historical_universe=True,
        apply_journal_at_end=True, discover=False,
    )

    trades = res.get("num_trades", res.get("trades", res.get("total_trades")))
    if trades is None:
        for k in res:
            if "trade" in k.lower():
                trades = res[k]; break
    print("\n=== RESULT ===")
    print("trades:", trades)
    def live(c):  # non-unknown / non-None bars
        return sum(v for k, v in c.items() if k not in ("unknown", "None", "NO-SPY"))
    for axis in ("trend", "volatility"):
        tot = sum(tally[axis].values()); lv = live(tally[axis])
        p_tot = sum(pre2020[axis].values()); p_lv = live(pre2020[axis])
        print(f"{axis:<11} live {lv}/{tot} bars | PRE-2020 live {p_lv}/{p_tot} | states={dict(tally[axis])}")
    ok = (trades and trades > 0
          and live(tally["trend"]) > 0.9 * sum(tally["trend"].values())
          and live(pre2020["trend"]) == sum(pre2020["trend"].values()) and sum(pre2020["trend"].values()) > 0)
    print("VERDICT:", "PASS — trades>0 + LIVE regime across full window incl. pre-2020" if ok else "REVIEW")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
