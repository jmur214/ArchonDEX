#!/usr/bin/env python3
"""T-2026-06-17-195 — CORRECTED discovery eval harness for a valid foundry test.

Fixes the two T-193 blockers (both measurement-correctness):
  FIX 1 (Gate-0 window): validate on the FULL MBL-clearing window (default
    2012-2024 = 13yr > MBL_min~9.66yr), NOT the production 24-month quick-filter
    (where MBL Gate-0 kills every candidate at T_years=2.0 before any alpha gate).
  FIX 2 (real baseline): (a) restore the CLEAN governor anchor so the real
    6-edge production book trades (a polluted/empty book → baseline_sharpe=0 →
    meaningless contribution); (b) use_signal_cache=False — the production default
    Gate1SignalCache wrapper SWALLOWS baseline-edge exceptions
    (gate1_signal_cache.py:147-152) → empty signals → silent degenerate baseline.
    PureBacktestCache still memoizes the baseline RESULT across candidates, so the
    cross-candidate speedup is preserved.

contribution is then a TRUE marginal: Sharpe(book + candidate) − Sharpe(book).
Foundry candidates = one single-gene long composite per tier-A/B feature (the
fair-seed Gen-0 archetype). Cross-sectional → percentile; ticker-independent →
absolute (T-177 feature-class). DSR n_trials = #candidates. Offline + simfin-live.

Standing rule: any local clear is a CANDIDATE → cloud N>=5 before trusted.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WIN_START = os.environ.get("T195_START", "2012-01-01")
WIN_END = os.environ.get("T195_END", "2024-12-31")
OUT = os.environ.get("T195_OUT", "/tmp/t195_foundry_eval.jsonl")
# optional comma-list of features to limit the sweep (bounded local runs)
ONLY = [s for s in os.environ.get("T195_FEATURES", "").split(",") if s]


def restore_clean_governor():
    """FIX 2a: restore the canonical 6-edge production book from the anchor."""
    gov = ROOT / "data" / "governor"
    anc = gov / "_isolated_anchor"
    import shutil
    for f in ("edges.yml", "edge_weights.json", "regime_edge_performance.json",
              "lifecycle_history.csv"):
        if (anc / f).exists():
            shutil.copyfile(anc / f, gov / f)


def _ti(feat) -> bool:
    if getattr(feat, "ticker_independent", False):
        return True
    try:
        from engines.engine_d_discovery.feature_engineering import _classify_feature_ticker_independence
        return bool(_classify_feature_ticker_independence(feat))
    except Exception:
        return False


def main() -> int:
    import core.feature_foundry.features  # noqa: F401
    from core.feature_foundry import get_feature_registry
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    from engines.data_manager.data_manager import DataManager
    from orchestration.run_backtest_pure import PureBacktestCache

    restore_clean_governor()
    cfg = json.loads((ROOT / "config" / "backtest_settings.json").read_text())
    dm = DataManager()
    data_map = {}
    for t in cfg.get("tickers", []):
        d = dm.load_cached(t, "1d")
        if d is not None and not d.empty:
            data_map[t] = d[(d.index >= WIN_START) & (d.index <= WIN_END)]
    first = next(iter(data_map.values()))
    vs, ve = first.index[0].isoformat(), first.index[-1].isoformat()
    print(f"[T195] data_map {len(data_map)} tickers | window {vs[:10]}..{ve[:10]} ({len(first)} bars) | signal_cache=OFF clean-governor")

    reg = get_feature_registry()
    feats = [f for f in reg.list_features() if f.tier in ("A", "B")]
    if ONLY:
        feats = [f for f in feats if f.feature_id in ONLY]
    print(f"[T195] sweeping {len(feats)} tier-A/B features")

    eng = DiscoveryEngine()
    cache = PureBacktestCache()
    n_trials = len(feats)
    results = []
    for i, f in enumerate(feats, 1):
        ti = _ti(f)
        gene = ({"type": "foundry_feature", "feature_id": f.feature_id,
                 "operator": "greater", "threshold": 0.0} if ti else
                {"type": "foundry_feature", "feature_id": f.feature_id,
                 "operator": "top_percentile", "threshold": 80})
        spec = {"module": "engines.engine_a_alpha.edges.composite_edge",
                "class": "CompositeEdge", "category": "evolutionary",
                "edge_id": f"t195_{f.feature_id}", "status": "candidate",
                "params": {"genes": [gene], "direction": "long"}}
        t0 = time.time()
        try:
            r = eng.validate_candidate(
                spec, data_map, significance_threshold=None, cache=cache,
                start_date=vs, end_date=ve, n_trials_for_dsr=n_trials,
                use_signal_cache=False,  # FIX 2b
            )
        except Exception as e:
            r = {"error": repr(e)[:200]}
        dt = time.time() - t0
        ff = r.get("killed_by_gate")
        if ff is None and "error" not in r:
            for g in range(1, 9):
                if r.get(f"gate_{g}_evaluated", True) and not r.get(f"gate_{g}_passed", False):
                    ff = f"gate_{g}"; break
        rec = {"feature": f.feature_id, "ticker_independent": ti,
               "passed_all_gates": bool(r.get("passed_all_gates", False)),
               "first_failed_gate": ff,
               "baseline_sharpe": r.get("baseline_sharpe"),
               "with_candidate_sharpe": r.get("with_candidate_sharpe"),
               "contribution_sharpe": r.get("contribution_sharpe"),
               "attribution_sharpe": r.get("attribution_sharpe"),
               "robustness_survival": r.get("robustness_survival"),
               "significance_p": r.get("significance_p"),
               "gates": {f"g{g}": r.get(f"gate_{g}_passed") for g in range(1, 9)},
               "wall_s": round(dt, 1), "error": r.get("error")}
        results.append(rec)
        print(f"[T195] [{i}/{len(feats)}] {f.feature_id:<34} pass={rec['passed_all_gates']} "
              f"died={ff} baseline={rec['baseline_sharpe']} contrib={rec['contribution_sharpe']} {dt:.0f}s", flush=True)
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    passed = [r for r in results if r["passed_all_gates"]]
    nonzero_base = [r for r in results if (r["baseline_sharpe"] or 0) != 0]
    from collections import Counter
    print(f"\n[T195] === RESULT === {len(results)} features | baseline NON-zero on {len(nonzero_base)}/{len(results)} "
          f"(harness-fix check: should be all) | {len(passed)} cleared the gauntlet+DSR")
    print(f"[T195] died-at: {dict(Counter(str(r['first_failed_gate']) for r in results))}")
    print(f"[T195] N_trials (DSR): {n_trials}")
    if passed:
        print("[T195] CLEARED (CANDIDATES — need cloud N>=5):")
        for r in passed:
            print(f"    {r['feature']} contrib={r['contribution_sharpe']} surv={r['robustness_survival']}")
    print("[T195] VERDICT:", "H1 — >=1 foundry feature cleared (candidate; cloud-validate)"
          if passed else "H0 — explored, nothing cleared (honest null)")
    print(f"[T195] jsonl: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
