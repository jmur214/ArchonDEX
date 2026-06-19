#!/usr/bin/env python
# scripts/regime_ground_truth_deepwindow_t221.py
"""T-221 — regime ground-truth + defensive-behavior pre-spec for the deep-window
cloud cells (A/T-216 conjunctive selector, C/T-211 composition).

LABELING + VERIFICATION SPEC ONLY — 0 N_trials, no new strategy arms. Reuses
the frozen causal HMM (T-172) + the always-on overlay (T-204/T-220); forks
nothing. Causal labels only. [NN-CENSUS]/[NN-FAIL-CLOSED].

Emits, for the 2000-2025 deep window:
  1. the regime ground-truth per crisis (HMM CATCHES vs MISSES),
  2. the expected overlay de-gross windows (pre-spec, BEFORE the cells run),
  3. the regime-sanity checklist the cloud cells must pass.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pandas as pd

from core.trend_overlay import TrendOverlay
from scripts.regime_oos_loco_t172 import (
    FIRE_SUSTAIN, FIRE_THRESH, _sustained_crossings, build_deep_panel,
)
from scripts.regime_conditional_overlay_t220 import (
    LOOKBACK, TRAIN_END, causal_p_crisis, regime_label,
)

ROOT = Path(__file__).resolve().parents[1]

# Crisis windows (peak → trough), the T-118b/v3 anchors. fast/vol vs slow/value
# per T-172/T-220 (the HMM catches the first, is structurally blind to the second).
CRISES = {
    "dotcom_2000": {"win": ("2000-03-01", "2002-10-09"), "type": "slow_valuation"},
    "GFC_2008":    {"win": ("2007-10-09", "2009-03-09"), "type": "fast_credit"},
    "COVID_2020":  {"win": ("2020-02-19", "2020-03-23"), "type": "fast_vol"},
    "BEAR_2022":   {"win": ("2022-01-03", "2022-10-12"), "type": "slow_valuation"},
}


def _dd_at(spy: pd.Series, peak: float, when) -> float:
    """SPY drawdown from the window peak already incurred by date `when`."""
    if when is None:
        return 0.0
    px = spy.loc[:pd.Timestamp(when)]
    return round(float(px.iloc[-1] / peak - 1.0), 3) if len(px) else 0.0


def _crisis_label_stats(p: pd.Series, label: pd.Series, spy: pd.Series,
                        a: str, b: str) -> Dict:
    win = (p.index >= pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))
    pw, lw = p[win], label[win]
    spy_w = spy[win]
    peak = float(spy_w.iloc[0])
    onsets = _sustained_crossings(pw, FIRE_THRESH, FIRE_SUSTAIN)
    first_cross = str(pw.index[onsets[0]].date()) if onsets else None
    return {
        "max_p_crisis": round(float(pw.max()), 3),
        "fired_sustained": bool(onsets),          # p_crisis ≥0.50 for ≥3d
        "first_crossing": first_cross,
        # the load-bearing metric: how much SPY had ALREADY fallen from the
        # window peak by the time the HMM fired (small = prompt, large = late).
        "spy_dd_at_first_cross": _dd_at(spy, peak, first_cross),
        "pct_bars_crisis_lbl": round(float((lw == "crisis").mean()), 3),
        "pct_bars_cautious_plus": round(float((lw != "calm").mean()), 3),
        "n_bars": int(len(lw)),
    }


def _overlay_degross(spy: pd.Series, a: str, b: str) -> Dict:
    """Pre-spec: the always-on overlay should be FLAT (de-grossed) whenever SPY
    < its 5-month trend. Report the actual flat span + share within the crisis
    (this is what the cloud cells must reproduce)."""
    sig = TrendOverlay(LOOKBACK, enabled=True).exposure(spy).shift(1)   # causal position
    win = (sig.index >= pd.Timestamp(a)) & (sig.index <= pd.Timestamp(b))
    sw = sig[win].dropna()
    flat = sw[sw == 0.0]
    first_degross = str(flat.index[0].date()) if len(flat) else None
    peak = float(spy[win].iloc[0])
    return {
        "expected_flat": bool(len(flat) > 0),
        "first_degross": first_degross,
        "last_degross": str(flat.index[-1].date()) if len(flat) else None,
        "pct_time_flat": round(float((sw == 0.0).mean()), 3) if len(sw) else 0.0,
        # SPY drawdown already incurred when the overlay first de-grossed
        # (small = the overlay caught it EARLY, the slow-bear win).
        "spy_dd_at_first_degross": _dd_at(spy, peak, first_degross),
    }


def main() -> int:
    panel = build_deep_panel()
    p = causal_p_crisis(panel, TRAIN_END)
    label = regime_label(p)
    spy = panel["spy_close"]

    # [NN-FAIL-CLOSED] / [NN-CENSUS]: the label must be non-degenerate + crisis-grade.
    shares = label.value_counts(normalize=True).round(3).to_dict()
    if label.nunique() < 2 or max(shares.values()) >= 0.99:
        raise RuntimeError(f"[NN-FAIL-CLOSED] degenerate regime label census {shares}")

    gt = {"window": [str(p.index[0].date()), str(p.index[-1].date())],
          "train_end": TRAIN_END, "regime_census": shares, "crises": {}}
    PROMPT_DD = -0.15      # HMM is "prompt" only if it fires before -15% from peak
    for name, meta in CRISES.items():
        a, b = meta["win"]
        rl = _crisis_label_stats(p, label, spy, a, b)
        dg = _overlay_degross(spy, a, b)
        # Timeliness, not just "fired somewhere": the HMM is PROMPT iff it fired
        # before -15% drawdown; LATE if most of the decline preceded its fire
        # (the slow-bear blindness — T-172/T-220). The overlay de-grosses far
        # earlier on the slow bears, so the tail there relies on the OVERLAY.
        hmm_prompt = rl["fired_sustained"] and rl["spy_dd_at_first_cross"] > PROMPT_DD
        gt["crises"][name] = {
            "window": [a, b], "type": meta["type"],
            "hmm": rl, "overlay_prespec": dg,
            "hmm_verdict": "PROMPT" if hmm_prompt else "LATE (most of the decline preceded the fire)",
            "tail_protection_relies_on": (
                "HMM + overlay (both early)" if hmm_prompt
                else "OVERLAY ONLY (HMM fires after the damage — slow-bear blindness)"),
        }

    # global crisis-grade check (mean p_crisis higher in-crisis than calm)
    in_crisis = pd.Series(False, index=p.index)
    for _, m in CRISES.items():
        a, b = m["win"]; in_crisis |= (p.index >= pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))
    gt["mean_p_in_crisis"] = round(float(p[in_crisis].mean()), 3)
    gt["mean_p_calm"] = round(float(p[~in_crisis].mean()), 3)
    if gt["mean_p_in_crisis"] <= gt["mean_p_calm"]:
        raise RuntimeError("[NN-FAIL-CLOSED] p_crisis not elevated in crises — not crisis-grade")

    # --- print ---------------------------------------------------------- #
    print(f"=== T-221 regime ground-truth | {gt['window'][0]} → {gt['window'][1]} "
          f"| census {shares} | p_crisis in/out crisis {gt['mean_p_in_crisis']}/{gt['mean_p_calm']} ===\n")
    print(f"  {'crisis':13s} {'type':16s} HMM-first(ddSPY)      overlay-first(ddSPY)   HMM")
    for name, c in gt["crises"].items():
        h, d = c["hmm"], c["overlay_prespec"]
        print(f"  {name:13s} {c['type']:16s} "
              f"{str(h['first_crossing']):11s}({h['spy_dd_at_first_cross']:+.0%})  "
              f"{str(d['first_degross']):11s}({d['spy_dd_at_first_degross']:+.0%})  {c['hmm_verdict']}")
        print(f"      → tail protection relies on: {c['tail_protection_relies_on']}")

    out = ROOT / "data" / "research" / "regime_ground_truth_t221.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(gt, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
