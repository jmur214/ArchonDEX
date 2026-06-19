#!/usr/bin/env python
# scripts/regime_conditional_overlay_t220.py
"""T-220 — always-on vs regime-gated trend overlay (the SHAPE verdict for C).

Runs ONLY the pre-registered 4 arms
(regime_conditional_overlay_preregistration_t220). Reuses T-204
(core/trend_overlay.py), T-217 thresholds (regime_gate.py), and T-172's
causal forward-filter p_crisis (scripts/regime_oos_loco_t172.py) — forks
nothing. Deterministic; [NN-SHARPE-CI]/[NN-CENSUS]/[NN-FAIL-CLOSED].
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay, buy_hold_returns
from engines.engine_e_regime.regime_gate import CALM_MAX, CAUTIOUS_MAX
from scripts.regime_oos_loco_t172 import (
    FEATURES, N_INIT, N_STATES, SEED, _causal_filtered_posterior,
    build_deep_panel, _standardize,
)
from scripts.trend_overlay_validation_t204 import (
    CRISES, crisis_mdds, load_close, metrics, PATHS,
)

ROOT = Path(__file__).resolve().parents[1]
LOOKBACK = 105          # 5 months (T-204 sweet spot) — fixed, no sweep
TRAIN_END = "2012-12-31"
ASSETS = ["SPY", "AGG", "GLD"]


def causal_p_crisis(panel: pd.DataFrame, train_end: str) -> pd.Series:
    """Frozen-HMM causal p_crisis: train on [start, train_end] (crisis-state =
    highest-vol state), then the T-089 forward-filter posterior over the FULL
    panel (lookahead-clean for the post-train span). Seed-pinned."""
    from hmmlearn.hmm import GaussianHMM
    train = panel.loc[:train_end]
    Xtrain, _, _ = _standardize(train, train)
    Xfull, _, _ = _standardize(train, panel)
    best, best_ll = None, -np.inf
    for k in range(N_INIT):
        m = GaussianHMM(n_components=N_STATES, covariance_type="diag",
                        n_iter=200, random_state=SEED + k)
        try:
            m.fit(Xtrain); ll = m.score(Xtrain)
        except Exception:
            continue
        if ll > best_ll:
            best, best_ll = m, ll
    if best is None:
        raise RuntimeError("[NN-FAIL-CLOSED] HMM failed to fit on the train window")
    states = best.predict(Xtrain)
    vol_idx = FEATURES.index("spy_vol_20d")
    means = [Xtrain[states == s, vol_idx].mean() if (states == s).any() else -np.inf
             for s in range(N_STATES)]
    crisis_state = int(np.argmax(means))
    post = _causal_filtered_posterior(best, Xfull)
    return pd.Series(post[:, crisis_state], index=panel.index, name="p_crisis")


def regime_label(p: pd.Series) -> pd.Series:
    lab = pd.Series("crisis", index=p.index)
    lab[p < CAUTIOUS_MAX] = "cautious"
    lab[p < CALM_MAX] = "calm"
    return lab


def _census_or_halt(label: pd.Series, p: pd.Series) -> Dict:
    """[NN-CENSUS] + [NN-FAIL-CLOSED]: the regime label must be non-degenerate
    AND concentrate crisis mass inside the known crises."""
    if label.empty or label.nunique() < 2:
        raise RuntimeError("[NN-FAIL-CLOSED] regime label is empty/constant — degraded")
    shares = (label.value_counts(normalize=True)).round(3).to_dict()
    if max(shares.values()) >= 0.99:
        raise RuntimeError(f"[NN-FAIL-CLOSED] degenerate label census {shares}")
    in_crisis = pd.Series(False, index=p.index)
    for _, (a, b) in CRISES.items():
        in_crisis |= (p.index >= pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))
    crisis_p_incrisis = round(float(p[in_crisis].mean()), 3)
    crisis_p_calm = round(float(p[~in_crisis].mean()), 3)
    if crisis_p_incrisis <= crisis_p_calm:
        raise RuntimeError(
            f"[NN-FAIL-CLOSED] p_crisis not elevated in crises "
            f"({crisis_p_incrisis} ≤ calm {crisis_p_calm}) — label not crisis-grade")
    return {"regime_shares": shares, "mean_p_in_crisis": crisis_p_incrisis,
            "mean_p_calm": crisis_p_calm}


def _ew(parts) -> pd.Series:
    mat = pd.concat(parts, axis=1)
    return mat.dropna(how="all").sum(axis=1, min_count=1).dropna()


def main() -> int:
    # --- causal regime label --------------------------------------------- #
    panel = build_deep_panel()
    p = causal_p_crisis(panel, TRAIN_END)
    label = regime_label(p)
    census = _census_or_halt(label, p)
    print(f"=== T-220 regime-conditional overlay | label census {census['regime_shares']} "
          f"| mean p_crisis in-crisis {census['mean_p_in_crisis']} vs calm {census['mean_p_calm']} ===\n")

    closes = {k: load_close(PATHS[k]) for k in ASSETS}
    n = len(ASSETS)

    def per_asset(close, mode):
        """mode: buyhold | always | gated | inverse."""
        ret = close.pct_change()
        sig = TrendOverlay(LOOKBACK, enabled=True).exposure(close)
        pos_always = sig.shift(1)                       # causal
        reg = label.reindex(close.index, method="ffill").shift(1)  # regime_{t-1}, causal
        active = reg.isin(["cautious", "crisis"])
        if mode == "buyhold":
            pos = pd.Series(1.0, index=close.index)
        elif mode == "always":
            pos = pos_always
        elif mode == "gated":                           # overlay only in cautious/crisis
            pos = pos_always.where(active, 1.0)
        else:                                           # inverse: overlay only in calm
            pos = pos_always.where(~active, 1.0)
        return (pos * ret)

    arms = {"a_no_overlay": "buyhold", "b_always_on": "always",
            "c_regime_gated": "gated", "d_inverse_gated": "inverse"}
    results = {"census": census, "arms": []}
    bh = _ew([per_asset(closes[k], "buyhold").rename(k) / n for k in ASSETS]).dropna()
    bh_sharpe = metrics(bh)["sharpe"]
    for arm, mode in arms.items():
        r = _ew([per_asset(closes[k], mode).rename(k) / n for k in ASSETS]).dropna()
        m = metrics(r, bh_sharpe=bh_sharpe)
        results["arms"].append({"arm": arm, **m, "crisis": crisis_mdds(r)})

    print(f"window: {bh.index[0].date()} → {bh.index[-1].date()}  (lookback 5mo, EW SPY/AGG/GLD)\n")
    print(f"  {'arm':16s} {'CAGR':>7s} {'Sharpe(ci_low)':>15s} {'MDD':>7s} {'skewM':>6s} {'capt':>5s}")
    for a in results["arms"]:
        print(f"  {a['arm']:16s} {a['cagr']:>+6.2%} "
              f"{a['sharpe']:>6.2f}({a['sharpe_ci_low']:>5.2f}) {a['mdd']:>+6.1%} "
              f"{a['skew_monthly']:>+6.2f} {a.get('capture_efficiency','-'):>5}")
        print(f"      crisis MDDs: {a['crisis']}")

    # --- verdict ---------------------------------------------------------- #
    b = next(a for a in results["arms"] if a["arm"] == "b_always_on")
    c = next(a for a in results["arms"] if a["arm"] == "c_regime_gated")
    d = next(a for a in results["arms"] if a["arm"] == "d_inverse_gated")
    gated_better_shape = (c["mdd"] > b["mdd"] + 0.01) and (c["sharpe_ci_low"] >= b["sharpe_ci_low"])
    carries_info = c["sharpe"] - d["sharpe"] > 0.10
    verdict = ("REGIME-GATE the overlay" if (gated_better_shape and carries_info)
               else "KEEP the overlay ALWAYS-ON (do not regime-condition)")
    results["verdict"] = verdict
    print(f"\nVERDICT: {verdict}")
    print(f"  (c gated MDD {c['mdd']:+.1%} vs b always-on {b['mdd']:+.1%}; "
          f"c Sharpe {c['sharpe']:.2f} vs inverse-control d {d['sharpe']:.2f})")

    out = ROOT / "data" / "research" / "regime_conditional_overlay_t220.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
