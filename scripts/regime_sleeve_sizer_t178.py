#!/usr/bin/env python
# scripts/regime_sleeve_sizer_t178.py
"""T-178 — dynamic MF-sleeve SIZER A/B vs always-on 20% (Step 2).

Implements the LOCKED pre-registration
(docs/Audit/regime_sleeve_sizer_preregistration_t178_2026_06_16.md):
the regime detector (HMM trained 2000-2012, applied OOS to 2013-2025,
causal forward filter, lagged 1 month) dynamically sizes the bought-MF
sleeve; A/B vs always-on 20%, monthly rebal, net-of-cost. 2013-2019 is
the genuinely held-out calm span for specificity. AQR TSMOM is the
optimistic MF proxy — run at raw AND a 0.5x haircut.

MEASUREMENT ONLY. Run:  python -m scripts.regime_sleeve_sizer_t178
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.regime_oos_loco_t172 import (
    build_deep_panel, _standardize, _causal_filtered_posterior, FEATURES, SEED,
)

ROOT = Path(__file__).resolve().parents[1]
TRAIN_END = "2012-12-31"
OOS_START = "2013-01-01"
COST_RT_BPS = 20.0          # round-trip cost per unit sleeve turnover
# operating point (set on held-out-calm intent, with margin — see pre-reg)
X_BASE, X_MIN, X_MAX = 0.20, 0.10, 0.40
SCALE, BASELINE = 0.25, 0.20


def _base_monthly() -> pd.Series:
    f = Path("/Users/jacksonmurphy/Dev/trading_machine-2/data/external/base_curve/"
             "t118r_v1_26yr_arm0_3b403882.csv")
    s = pd.read_csv(f)
    eq = pd.Series(pd.to_numeric(s["equity"], errors="coerce").values,
                   index=pd.to_datetime(s["timestamp"])).dropna()
    return eq.resample("ME").last().pct_change().dropna()


def _aqr_tsmom_monthly() -> pd.Series:
    p = ("/Users/jacksonmurphy/Dev/trading_machine-2/data/external/aqr/"
         "aqr_tsmom_monthly_snapshot_20260615.xlsx")
    df = pd.read_excel(p, sheet_name="TSMOM Factors", header=17)
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    s = pd.Series(pd.to_numeric(df["TSMOM"], errors="coerce").values,
                  index=df["Date"]).dropna()
    return s.resample("ME").last()


def _p_crisis_oos() -> pd.Series:
    """HMM trained 2000-2012, causal p_crisis on the full panel (OOS for
    2013+), monthly, lagged 1 month."""
    from hmmlearn.hmm import GaussianHMM
    panel = build_deep_panel()
    train = panel.loc[panel.index <= TRAIN_END]
    Xtr, _, _ = _standardize(train, train)
    Xfull, _, _ = _standardize(train, panel)
    best, bll = None, -np.inf
    for k in range(10):
        m = GaussianHMM(n_components=3, covariance_type="diag",
                        n_iter=200, random_state=SEED + k)
        try:
            m.fit(Xtr); ll = m.score(Xtr)
        except Exception:
            continue
        if ll > bll:
            best, bll = m, ll
    st = best.predict(Xtr)
    vi = FEATURES.index("spy_vol_20d")
    cstate = int(np.argmax([Xtr[st == s, vi].mean() if (st == s).any() else -1e9
                            for s in range(3)]))
    post = _causal_filtered_posterior(best, Xfull)
    p_daily = pd.Series(post[:, cstate], index=panel.index)
    p_m = p_daily.resample("ME").last()
    return p_m.shift(1)          # lag: last month's signal sizes this month


def _metrics(r: pd.Series) -> dict:
    from core.metrics_engine import MetricsEngine
    eq = (1 + r).cumprod()
    yrs = len(r) / 12.0
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    sharpe = r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else 0.0
    boot = MetricsEngine.bootstrap_distribution(
        r, MetricsEngine.sharpe_ratio, n_iterations=500, seed=0) if len(r) >= 32 else {}
    return {"cagr_pct": round(cagr * 100, 2), "mdd_pct": round(mdd * 100, 2),
            "sharpe": round(float(sharpe), 3),
            "sharpe_ci_low": round(float(boot.get("ci_low", float("nan"))), 3)}


def _run_arm(base: pd.Series, mf: pd.Series, x: pd.Series) -> pd.Series:
    idx = base.index.intersection(mf.index).intersection(x.index)
    b, m, xx = base[idx], mf[idx], x[idx].clip(X_MIN, X_MAX)
    turn = xx.diff().abs().fillna(0.0)
    cost = turn * (COST_RT_BPS / 1e4)
    return ((1 - xx) * b + xx * m - cost)


def main() -> None:
    base = _base_monthly()
    p = _p_crisis_oos()
    results = {}
    for hc_name, hc in [("raw", 1.0), ("haircut_0.5x", 0.5)]:
        mf = _aqr_tsmom_monthly() * hc
        oos = (base.index >= OOS_START)
        b = base[oos]
        x_dyn = (X_BASE + SCALE * (p - BASELINE)).clip(X_MIN, X_MAX)
        x_on = pd.Series(X_BASE, index=base.index)
        r_dyn = _run_arm(b, mf, x_dyn)
        r_on = _run_arm(b, mf, x_on)
        # sub-periods
        def sub(r, a, z):
            s = r[(r.index >= a) & (r.index <= z)]
            return _metrics(s) if len(s) >= 6 else {}
        results[hc_name] = {
            "full_oos": {"always_on": _metrics(r_on), "dynamic": _metrics(r_dyn)},
            "calm_2013_2019": {"always_on": sub(r_on, "2013-01-01", "2019-12-31"),
                               "dynamic": sub(r_dyn, "2013-01-01", "2019-12-31")},
            "covid_2020": {"always_on": sub(r_on, "2020-01-01", "2020-12-31"),
                           "dynamic": sub(r_dyn, "2020-01-01", "2020-12-31")},
            "grind_2022": {"always_on": sub(r_on, "2022-01-01", "2022-12-31"),
                           "dynamic": sub(r_dyn, "2022-01-01", "2022-12-31")},
            "sleeve_x": {"mean": round(float(x_dyn[x_dyn.index >= OOS_START].mean()), 3),
                         "min": round(float(x_dyn[x_dyn.index >= OOS_START].min()), 3),
                         "max": round(float(x_dyn[x_dyn.index >= OOS_START].max()), 3),
                         "turnover": round(float(x_dyn[x_dyn.index >= OOS_START].diff().abs().sum()), 2)},
        }

    # held-out-calm FA specificity: how often does p_crisis spike in calm OOS?
    calm = p[(p.index >= "2013-01-01") & (p.index <= "2019-12-31")].dropna()
    fa_months = int((calm > 0.5).sum())
    print(f"OOS span: {base[base.index>=OOS_START].index.min().date()} → "
          f"{base.index.max().date()}")
    print(f"held-out-calm (2013-2019) specificity: p_crisis>0.5 in "
          f"{fa_months}/{len(calm)} months ({fa_months/max(len(calm),1)*100:.0f}%)")
    print(f"dynamic sleeve x: mean {results['raw']['sleeve_x']['mean']} "
          f"[{results['raw']['sleeve_x']['min']}–{results['raw']['sleeve_x']['max']}]\n")

    for hc in ("raw", "haircut_0.5x"):
        r = results[hc]
        print(f"=== MF = {hc} ===")
        for period in ("full_oos", "calm_2013_2019", "covid_2020", "grind_2022"):
            on, dyn = r[period]["always_on"], r[period]["dynamic"]
            if not on or not dyn:
                continue
            print(f"  {period:16} always-on: Sharpe {on['sharpe']:+.2f} "
                  f"CAGR {on['cagr_pct']:+.1f}% MDD {on['mdd_pct']:.1f}%  |  "
                  f"dynamic: Sharpe {dyn['sharpe']:+.2f} CAGR {dyn['cagr_pct']:+.1f}% "
                  f"MDD {dyn['mdd_pct']:.1f}%")
        full = r["full_oos"]
        d_sh = full["dynamic"]["sharpe"] - full["always_on"]["sharpe"]
        d_mdd = full["dynamic"]["mdd_pct"] - full["always_on"]["mdd_pct"]
        wins = (d_sh > 0) and (d_mdd >= -0.01)
        print(f"  >>> full-OOS Δsharpe {d_sh:+.3f}, ΔMDD {d_mdd:+.1f}pp → "
              f"dynamic {'BEATS' if wins else 'does NOT beat'} always-on\n")

    out = ROOT / "data" / "research" / "regime_sleeve_sizer_t178.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"written: {out}")


if __name__ == "__main__":
    main()
