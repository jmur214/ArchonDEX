#!/usr/bin/env python3
"""T-2026-06-17-193 Phase-0b — the first HONEST test of the Foundry vocabulary.

Controlled vocabulary sweep: build ONE single-gene long composite per tier-A/B
Foundry feature (the fair-seed's Gen-0 archetype — T-183's foundry genomes are
single-gene), and run each through the EXACT production discovery gauntlet
(validate_candidate, shared PureBacktestCache baseline, Gate-8 DSR with n_trials =
#features) on an MBL-CLEARING 14yr window (2010-2024 → T_years=15 > MBL_min~9.66
at N~125; the production 24-month quick-filter window CANNOT clear Gate-0 MBL, so
everything dies there artifactually — the T-193 finding).

Controlled (not the registry-seeded GA) on purpose: the edges.yml registry has
accumulated 60+ stale candidate composites across runs that seed_from_registry
pulls in; this sweep is clean, full-coverage (all 35 features, not the GA's ~10
random sample), and interpretable. Cross-sectional features get percentile
operators; ticker-independent (calendar/macro) get absolute operators (the T-177
feature-class insight) so they aren't degenerate. Offline + simfin-live.

Standing rule: a local clear is a CANDIDATE → needs cloud N>=5 before trusted.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WINDOW_START = os.environ.get("PHASE0B_START", "2010-01-01")
WINDOW_END = os.environ.get("PHASE0B_END", "2024-12-31")
OUT = os.environ.get("PHASE0B_OUT", "/tmp/t193_phase0b_foundry.jsonl")


def _is_ticker_independent(feat) -> bool:
    if getattr(feat, "ticker_independent", False):
        return True
    try:
        from engines.engine_d_discovery.feature_engineering import _classify_feature_ticker_independence
        return bool(_classify_feature_ticker_independence(feat))
    except Exception:
        return False


def main() -> int:
    import core.feature_foundry.features  # noqa: F401  populate the registry
    from core.feature_foundry import get_feature_registry
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    from engines.data_manager.data_manager import DataManager
    from orchestration.run_backtest_pure import PureBacktestCache

    cfg = json.loads((ROOT / "config" / "backtest_settings.json").read_text())
    tickers = list(cfg.get("tickers", []))
    dm = DataManager()
    data_map = {}
    for t in tickers:
        df = dm.load_cached(t, "1d")
        if df is not None and not df.empty:
            data_map[t] = df[(df.index >= WINDOW_START) & (df.index <= WINDOW_END)]
    first = next(iter(data_map.values()))
    val_start, val_end = first.index[0].isoformat(), first.index[-1].isoformat()
    print(f"[P0B] data_map: {len(data_map)} tickers | window {val_start[:10]}..{val_end[:10]} ({len(first)} bars)")

    reg = get_feature_registry()
    feats = [f for f in reg.list_features() if f.tier in ("A", "B")]
    print(f"[P0B] tier-A/B foundry features to sweep: {len(feats)}")

    # build one single-gene long composite per feature
    specs = []
    for f in feats:
        ti = _is_ticker_independent(f)
        gene = ({"type": "foundry_feature", "feature_id": f.feature_id,
                 "operator": "greater", "threshold": 0.0} if ti else
                {"type": "foundry_feature", "feature_id": f.feature_id,
                 "operator": "top_percentile", "threshold": 80})
        specs.append({
            "module": "engines.engine_a_alpha.edges.composite_edge",
            "class": "CompositeEdge", "category": "evolutionary",
            "edge_id": f"p0b_{f.feature_id}", "status": "candidate",
            "params": {"genes": [gene], "direction": "long"},
            "_ticker_independent": ti, "_feature": f.feature_id,
        })

    eng = DiscoveryEngine()
    cache = PureBacktestCache()
    n_trials = len(specs)
    print(f"[P0B] DSR n_trials = {n_trials} | validating {len(specs)} single-feature composites on the MBL-clearing window\n")

    results = []
    for i, spec in enumerate(specs, 1):
        fid = spec["_feature"]
        t0 = time.time()
        try:
            r = eng.validate_candidate(
                spec, data_map, significance_threshold=None,
                cache=cache, start_date=val_start, end_date=val_end,
                n_trials_for_dsr=n_trials,
            )
        except Exception as e:
            r = {"passed_all_gates": False, "error": repr(e)[:200]}
        dt = time.time() - t0
        # determine first failed gate from the gate_N_passed flags (Gate-0 MBL
        # only appears as gate_0_* / killed_by_gate when it FAILS; absent = passed)
        first_fail = r.get("killed_by_gate")
        if first_fail is None:
            for g in range(1, 9):
                ev = r.get(f"gate_{g}_evaluated", True)
                if ev and not r.get(f"gate_{g}_passed", False):
                    first_fail = f"gate_{g}"; break
        rec = {
            "feature": fid, "ticker_independent": spec["_ticker_independent"],
            "passed_all_gates": bool(r.get("passed_all_gates", False)),
            "first_failed_gate": first_fail,
            "contribution_sharpe": r.get("contribution_sharpe"),
            "attribution_sharpe": r.get("attribution_sharpe"),
            "baseline_sharpe": r.get("baseline_sharpe"),
            "with_candidate_sharpe": r.get("with_candidate_sharpe"),
            "robustness_survival": r.get("robustness_survival"),
            "significance_p": r.get("significance_p"),
            "gate_6_passed": r.get("gate_6_passed"), "gate_8_passed": r.get("gate_8_passed"),
            "gates": {f"g{g}": r.get(f"gate_{g}_passed") for g in range(1, 9)},
            "wall_s": round(dt, 1), "error": r.get("error"),
        }
        results.append(rec)
        print(f"[P0B] [{i}/{len(specs)}] {fid:<34} ti={int(spec['_ticker_independent'])} "
              f"pass={rec['passed_all_gates']} died={first_fail} "
              f"contrib={rec['contribution_sharpe']} attr={rec['attribution_sharpe']} {dt:.0f}s", flush=True)
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    passed = [r for r in results if r["passed_all_gates"]]
    from collections import Counter
    died = Counter(str(r["killed_by_gate"]) for r in results)
    print(f"\n[P0B] === RESULT === {len(results)} foundry features swept | "
          f"{len(passed)} cleared the full gauntlet+DSR")
    print(f"[P0B] death distribution by gate: {dict(died)}")
    print(f"[P0B] N_trials consumed (DSR family): {n_trials}")
    if passed:
        print("[P0B] CLEARED (CANDIDATES — need cloud N>=5):")
        for r in passed:
            print(f"    {r['feature']}  contrib={r['gate1_contribution']} t={r['alpha_t']} dsr={r['dsr_p']}")
    print("[P0B] VERDICT:", "H1 — >=1 foundry feature CLEARED locally (candidate; cloud-validate)"
          if passed else "H0 — explored full vocabulary, nothing cleared (honest null)")
    print(f"[P0B] jsonl: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
