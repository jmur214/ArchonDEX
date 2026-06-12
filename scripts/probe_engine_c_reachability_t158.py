"""
scripts/probe_engine_c_reachability_t158.py
===========================================
T-2026-06-11-158 — Engine C reachability probe + scale-invariance
quantification. READ-MOSTLY: zero engine edits — all instrumentation is
runtime monkeypatching of class methods inside this script; the engine
files on disk are untouched.

Part 1 (reachability, empirical): run a short prod-config backtest window
(2022-01-01..2022-03-31) inside run_isolated's governor isolation with
counters wrapped around:
  - PortfolioPolicy.allocate            (total allocation calls)
  - PortfolioOptimizer.optimize         (mean_variance branch executions)
  - PortfolioPolicy._apply_vol_target   (adaptive-overlay executions)
  - PortfolioPolicy._apply_exposure_cap (adaptive-overlay executions)
  - PortfolioPolicy._apply_regime_overrides (mode-override events — the
    `:138` safe-keys list includes "mode", so a learned allocation
    recommendation could flip mean_variance -> adaptive mid-run)
Fallthrough detection: an allocate call where cfg.mode == "mean_variance"
at entry but optimize() was NOT invoked (the `len(returns_df) < 5: pass`
fallthrough at policy.py:204) is counted explicitly.

Part 2 (cancellation): capture REAL allocate inputs (signals, price_data,
equity, regime_meta) from the live run, then replay OFFLINE through fresh
PortfolioPolicy instances: weights(S) vs weights(0.5*S) under BOTH modes
(mean_variance and adaptive). regime_meta=None in replays so regime
overrides cannot flip the mode under test (controlled experiment on the
allocator algebra only). Reports max-abs weight diff and gross
(sum|w|) diff. Determinism guard: each replay runs twice and must be
identical before the S-vs-0.5S diff is trusted.

Usage: PYTHONHASHSEED=0 python -m scripts.probe_engine_c_reachability_t158
Output: data/research/t158_reachability/probe_results.json + stdout.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "research" / "t158_reachability" / "probe_results.json"

COUNTS = {
    "allocate_calls": 0,
    "optimize_calls": 0,
    "vol_target_overlay_calls": 0,
    "exposure_cap_overlay_calls": 0,
    "regime_override_mode_flips": 0,
    "mean_variance_fallthroughs": 0,
    "parrondo_calls": 0,
}
CAPTURES: list = []   # up to 3 real (signals, price_data, equity, mode_at_entry)
_MAX_CAPTURES = 3


def install_probes():
    from engines.engine_c_portfolio.policy import PortfolioPolicy
    from engines.engine_c_portfolio.optimizer import PortfolioOptimizer

    orig_allocate = PortfolioPolicy.allocate
    orig_optimize = PortfolioOptimizer.optimize
    orig_vt = PortfolioPolicy._apply_vol_target
    orig_ec = PortfolioPolicy._apply_exposure_cap
    orig_ro = PortfolioPolicy._apply_regime_overrides

    def allocate(self, signals, price_data, equity, current_weights=None, regime_meta=None):
        COUNTS["allocate_calls"] += 1
        mode_at_entry = self.cfg.mode
        opt_before = COUNTS["optimize_calls"]
        if len(CAPTURES) < _MAX_CAPTURES and signals and len(signals) >= 3:
            CAPTURES.append({
                "signals": dict(signals),
                "price_data": {t: df.copy() for t, df in (price_data or {}).items() if t in signals},
                "equity": float(equity),
            })
        out = orig_allocate(self, signals, price_data, equity,
                            current_weights=current_weights, regime_meta=regime_meta)
        if mode_at_entry == "mean_variance" and COUNTS["optimize_calls"] == opt_before and signals:
            COUNTS["mean_variance_fallthroughs"] += 1
        if mode_at_entry == "parrondo_fixed":
            COUNTS["parrondo_calls"] += 1
        return out

    def optimize(self, *a, **k):
        COUNTS["optimize_calls"] += 1
        return orig_optimize(self, *a, **k)

    def vt(self, *a, **k):
        COUNTS["vol_target_overlay_calls"] += 1
        return orig_vt(self, *a, **k)

    def ec(self, *a, **k):
        COUNTS["exposure_cap_overlay_calls"] += 1
        return orig_ec(self, *a, **k)

    def ro(self, regime_meta=None):
        before = self.cfg.mode
        out = orig_ro(self, regime_meta)
        if self.cfg.mode != before:
            COUNTS["regime_override_mode_flips"] += 1
        return out

    PortfolioPolicy.allocate = allocate
    PortfolioOptimizer.optimize = optimize
    PortfolioPolicy._apply_vol_target = vt
    PortfolioPolicy._apply_exposure_cap = ec
    PortfolioPolicy._apply_regime_overrides = ro
    return orig_allocate


def cancellation_replay(orig_allocate) -> dict:
    """Offline S-vs-0.5S replays on captured real inputs, both modes."""
    from engines.engine_c_portfolio.policy import PortfolioPolicy, PortfolioPolicyConfig

    base_cfg_raw = json.loads((ROOT / "config" / "portfolio_settings.json").read_text())
    known = set(PortfolioPolicyConfig.__annotations__)
    base_kwargs = {k: v for k, v in base_cfg_raw.items() if k in known}
    base_kwargs["debug"] = False

    results = {}
    for mode in ("mean_variance", "adaptive"):
        mode_res = []
        for i, cap in enumerate(CAPTURES):
            cfg = PortfolioPolicyConfig(**{**base_kwargs, "mode": mode})
            pol = PortfolioPolicy(cfg)
            S = cap["signals"]
            S_half = {t: 0.5 * v for t, v in S.items()}

            def run(signals):
                # fresh policy per call so regime-override snapshots can't leak
                p = PortfolioPolicy(PortfolioPolicyConfig(**{**base_kwargs, "mode": mode}))
                return orig_allocate(p, signals, cap["price_data"], cap["equity"],
                                     current_weights=None, regime_meta=None)

            w1a, w1b = run(S), run(S)              # determinism guard
            det_ok = w1a == w1b
            w_half = run(S_half)
            keys = sorted(set(w1a) | set(w_half))
            max_dw = max((abs(w1a.get(k, 0.0) - w_half.get(k, 0.0)) for k in keys), default=0.0)
            gross1 = sum(abs(v) for v in w1a.values())
            gross_h = sum(abs(v) for v in w_half.values())
            mode_res.append({
                "capture": i,
                "n_signals": len(S),
                "deterministic_replay": det_ok,
                "gross_S": round(gross1, 6),
                "gross_halfS": round(gross_h, 6),
                "gross_diff": round(gross_h - gross1, 6),
                "max_abs_weight_diff": round(max_dw, 6),
            })
        results[mode] = mode_res
    return results


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from scripts.run_isolated import isolated, _run_q1_inside_context

    orig_allocate = install_probes()

    print("[T158] running prod-config probe window 2022-01-01..2022-03-31 ...")
    with isolated():
        summary = _run_q1_inside_context(
            override_start="2022-01-01", override_end="2022-03-31",
        )

    print("[T158] reachability counters:")
    for k, v in COUNTS.items():
        print(f"  {k}: {v}")

    print(f"[T158] captured {len(CAPTURES)} real allocate inputs; running cancellation replays ...")
    canc = cancellation_replay(orig_allocate)

    res = {
        "task": "T-2026-06-11-158",
        "window": "2022-01-01..2022-03-31 (prod config, env=prod)",
        "reachability_counts": COUNTS,
        "cancellation": canc,
        "probe_run_sharpe": summary.get("sharpe") if isinstance(summary, dict) else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res["cancellation"], indent=2))
    print(f"[T158] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
