"""
scripts/firing_curve_sweep_t118fc.py
====================================
T-2026-06-13-118fc — the de-gross FIRING-CURVE sweep.

QUESTION (firing only): does a trigger δ exist that ARMS the HMM
transition overlay on the 2022 known-transition window, and in what
range, for each model {crisis, V1}?

FIRING-ONLY INTEGRITY (CLAUDE.md #7): this script computes NO performance
metric. It captures the per-bar CAUSAL combined posterior
(p_crisis + p_stressed, from predict_proba_at / 60-bar — the production
path) and characterizes the INSTRUMENT: at which δ does the Δ-trigger
arm. No Sharpe / MDD / return / gross is read. The overlay runs at
degross_level=1.0 (neutral multiplier) so the capture backtest produces
ZERO trade change — we only record the posterior series via a monkeypatch
on RegimeTransitionOverlay.observe, then re-evaluate the trigger OFFLINE
across the δ ladder (δ is the trigger threshold; the posterior series is
δ-independent, so 2 capture runs serve the whole sweep).

Method:
  1. For model in {crisis, V1}: patch config/regime_settings.json
     hmm.model_path, enable the overlay at level=1.0, monkeypatch
     observe() to append (ts, p_combined) per bar, run the 2022 cell
     under run_isolated. Capture the causal posterior series. Restore
     configs.
  2. OFFLINE: for each model series × δ in {0.05..0.30} × k in {3,5,10},
     run a fresh RegimeTransitionOverlay and count arm-events
     (fire-count). Also report max Δ_k over the series — the firing
     threshold is exactly max Δ_k (any δ ≤ max Δ_k fires at least once).

Output: data/research/t118fc/firing_curve.json + printed table.
Usage: PYTHONHASHSEED=0 python -m scripts.firing_curve_sweep_t118fc
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RG = ROOT / "config" / "regime_settings.json"
RS = ROOT / "config" / "risk_settings.prod.json"
OUT = ROOT / "data" / "research" / "t118fc" / "firing_curve.json"

MODELS = {
    "crisis": "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl",
    "v1": "engines/engine_e_regime/models/hmm_3state_v1.pkl",
}
# Two windows: 2022 (the dispatch's window — a clean V1 transition, but the
# crisis model enters it ALREADY stressed so it holds no crisis transition);
# and COVID 2019→2020 (a benign→stress boundary the crisis model DOES see).
# The second window is required to truthfully answer "does a firing δ exist
# for the crisis model" — 2022 alone would mislead (no in-window transition).
WINDOWS = {
    "2022": ("2022-01-01", "2022-12-31"),
    "covid_2019_2020": ("2019-06-01", "2020-12-31"),
}
DELTAS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
KS = [3, 5, 10]
# Fixed hysteresis for the sweep (firing of the de-gross arm depends on
# the de-gross condition Δ_k ≥ δ; regross params don't affect first-arm).
REGROSS_LEVEL, REGROSS_BARS = 0.25, 10

_CAPTURE: list = []  # (ts_str, p_combined) for the current model run


def _capture_run(model_path: str, start: str, end: str) -> list:
    """Run the window with the overlay enabled+neutral; capture posterior."""
    import json as _json
    rg = _json.loads(RG.read_text()); rs = _json.loads(RS.read_text())
    rg_bak, rs_bak = _json.dumps(rg), _json.dumps(rs)
    try:
        rg["hmm"]["model_path"] = model_path
        RG.write_text(_json.dumps(rg, indent=2))
        rs.update({
            "regime_transition_overlay_enabled": True,
            "regime_overlay_degross_level": 1.0,   # NEUTRAL → zero trade change
            "regime_overlay_k_days": 5,
            "regime_overlay_degross_delta": 0.05,  # irrelevant; we recompute offline
            "regime_overlay_regross_level": REGROSS_LEVEL,
            "regime_overlay_regross_bars": REGROSS_BARS,
            "advisory_risk_scalar_apply_on_path_a": False,
        })
        RS.write_text(_json.dumps(rs, indent=2))

        from engines.engine_b_risk.regime_transition_overlay import RegimeTransitionOverlay
        _CAPTURE.clear()
        orig = RegimeTransitionOverlay.observe

        def patched(self, now_ts, p_combined):
            # record once per (new) timestamp — mirror observe's own idempotency
            if not _CAPTURE or _CAPTURE[-1][0] != str(now_ts):
                _CAPTURE.append((str(now_ts), float(p_combined)))
            return orig(self, now_ts, p_combined)

        RegimeTransitionOverlay.observe = patched
        try:
            from scripts.run_isolated import isolated, _run_q1_inside_context
            with isolated():
                _run_q1_inside_context(override_start=start, override_end=end)
        finally:
            RegimeTransitionOverlay.observe = orig
        return list(_CAPTURE)
    finally:
        RG.write_text(rg_bak); RS.write_text(rs_bak)


def _fire_count(series, delta, k):
    """Offline: arm-event count over the posterior series at (δ, k)."""
    from engines.engine_b_risk.regime_transition_overlay import (
        RegimeOverlayConfig, RegimeTransitionOverlay,
    )
    ov = RegimeTransitionOverlay(RegimeOverlayConfig(
        enabled=True, degross_level=0.5, k_days=k,
        degross_delta=delta, regross_level=REGROSS_LEVEL, regross_bars=REGROSS_BARS,
    ))
    arms = 0
    prev = False
    for i, (ts, p) in enumerate(series):
        ov.observe(ts, p)
        now = ov.armed
        if now and not prev:
            arms += 1  # count rising edges = distinct de-gross events
        prev = now
    return arms


def _max_delta_k(series, k):
    vals = [p for _, p in series]
    if len(vals) < k + 1:
        return None
    return max(vals[i] - vals[i - k] for i in range(k, len(vals)))


def main() -> int:
    result = {"path": "causal predict_proba_at 60-bar", "deltas": DELTAS, "ks": KS,
              "windows": {w: f"{s}..{e}" for w, (s, e) in WINDOWS.items()}, "results": {}}
    for wname, (start, end) in WINDOWS.items():
        result["results"][wname] = {}
        for name, path in MODELS.items():
            series = _capture_run(path, start, end)
            n = len(series)
            pvals = [p for _, p in series]
            m = {
                "n_bars_captured": n,
                "p_combined_min": round(min(pvals), 4) if pvals else None,
                "p_combined_max": round(max(pvals), 4) if pvals else None,
                "p_combined_mean": round(sum(pvals) / n, 4) if n else None,
                "max_delta_k": {str(k): (round(v, 4) if (v := _max_delta_k(series, k)) is not None else None) for k in KS},
                "fire_count": {str(k): {str(d): _fire_count(series, d, k) for d in DELTAS} for k in KS},
            }
            result["results"][wname][name] = m
            print(f"\n=== [{wname}] {name} ({path.split('/')[-1]}) — {n} bars ===")
            print(f"  p_combined: min {m['p_combined_min']} / mean {m['p_combined_mean']} / max {m['p_combined_max']}")
            for k in KS:
                mdk = m["max_delta_k"][str(k)]
                fc = m["fire_count"][str(k)]
                print(f"  k={k}: max Δ_k={mdk} | fire-count by δ: " +
                      " ".join(f"{d}:{fc[str(d)]}" for d in DELTAS))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))
    print(f"\n[T118fc] wrote {OUT}")
    print("[T118fc] FIRING-ONLY: zero performance metrics computed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
