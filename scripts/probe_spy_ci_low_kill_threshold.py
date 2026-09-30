"""
probe_spy_ci_low_kill_threshold.py — does the project's own `ci_low < 0.4` kill
thesis (CLAUDE.md [NN-SHARPE-CI]) kill buy-and-hold SPY itself on a 12-year window?

Seeded claim 1A.6 (alpha-frontier review 2026-09-30).

Two independent computations, both using the project's own referee code
(`core/metrics_engine.py::MetricsEngine.bootstrap_distribution`, stationary block
bootstrap):

  A. ANALYTIC (data-free). Lo (2002) / Bailey-López de Prado (2012) standard error
     of an annualized Sharpe estimated from T years of daily returns:
         SE(SR) ≈ sqrt((1 + SR²/2 − γ3·SR + (γ4−3)/4·SR²) / T_years)   [per-year SR]
     with skew γ3 and excess kurtosis (γ4−3) of SPY daily returns (≈ −0.5, ≈ 12 in
     2014–2025 per the fat-tail literature; iid form when both are 0). The 5th
     percentile lower bound is SR − 1.645·SE.

  B. CALIBRATED SIMULATION. A GARCH(1,1)-style series with Student-t(4) shocks,
     calibrated to SPY-total-return-like annual moments (mean 13%, vol 17.5%, i.e.
     point SR ≈ 0.74 on a 12-yr window), pushed through the project's
     `bootstrap_distribution` (1000 iter, auto block length). Reports ci_low.
     THIS IS NOT A MEASUREMENT OF SPY — the container has no market data and the
     proxy blocks every data host. It is a calibrated check of what the project's
     own CI machinery returns for a SPY-shaped 12-year series.

  C. REAL DATA (optional). `--csv path` with columns date,close (dividend-adjusted)
     runs (B) on the real series instead. Run this on the substrate when available.

Deterministic: seed 0 everywhere. No wall-clock in output.
Verdict rule (pre-stated): CONFIRMED iff every analytic arm has lb_5pct < 0.4 AND a
majority of calibrated seeds return ci_low < 0.4 (a single lucky path does not refute
a claim about the expected outcome). Exit 0 if confirmed, else 1.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.metrics_engine import MetricsEngine  # noqa: E402


def analytic_lower_bound(sr: float, t_years: float, skew: float, ex_kurt: float, q: float = 1.645) -> dict:
    var = (1.0 + 0.5 * sr * sr - skew * sr + (ex_kurt / 4.0) * sr * sr) / t_years
    se = math.sqrt(max(var, 1e-12))
    return {"sr": sr, "t_years": t_years, "skew": skew, "ex_kurt": ex_kurt, "se": round(se, 4), "lb_5pct": round(sr - q * se, 4)}


def simulate_spy_like(n_days: int, ann_mean: float, ann_vol: float, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    omega, alpha, beta = 1e-6, 0.08, 0.90
    target_var = (ann_vol ** 2) / 252.0
    omega = target_var * (1 - alpha - beta)
    h = target_var
    df = 4.0
    out = np.empty(n_days)
    mu = ann_mean / 252.0
    for t in range(n_days):
        z = rng.standard_t(df) / math.sqrt(df / (df - 2))
        eps = math.sqrt(h) * z
        out[t] = mu + eps
        h = omega + alpha * eps * eps + beta * h
    idx = pd.bdate_range("2014-01-02", periods=n_days)
    return pd.Series(out, index=idx)


def bootstrap_ci(returns: pd.Series) -> dict:
    res = MetricsEngine.bootstrap_distribution(returns, MetricsEngine.sharpe_ratio, n_iterations=1000, seed=0)
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="optional real SPY TR csv: date,close")
    args = ap.parse_args()

    out: dict = {"claim": "ci_low < 0.4 kills SPY on a 12-yr window", "arms": {}}
    analytic_ok = True
    sim_below = 0

    # A. analytic
    arms_a = []
    for sr in (0.65, 0.75, 0.85):
        for (sk, ek, label) in ((0.0, 0.0, "iid"), (-0.5, 12.0, "fat-tail")):
            r = analytic_lower_bound(sr, 12.0, sk, ek)
            r["label"] = label
            arms_a.append(r)
            if r["lb_5pct"] >= 0.4:
                analytic_ok = False
    out["arms"]["A_analytic_12yr"] = arms_a

    # B. calibrated simulation through the project's own bootstrap
    sims = []
    for seed in range(5):
        s = simulate_spy_like(252 * 12, 0.13, 0.175, seed)
        r = bootstrap_ci(s)
        r["seed"] = seed
        sims.append(r)
        if r["ci_low"] < 0.4:
            sim_below += 1
    out["arms"]["B_calibrated_sim_12yr"] = sims
    out["arms"]["B_seeds_with_ci_low_below_0.4"] = f"{sim_below}/5"
    out["arms"]["B_note"] = "NOT a measurement of SPY; container has no market data. Calibrated GARCH-t(4), mean 13%/vol 17.5%."

    # C. real data
    if args.csv:
        df = pd.read_csv(args.csv, parse_dates=["date"]).set_index("date").sort_index()
        rets = df["close"].pct_change().dropna()
        rets = rets["2014-01-01":"2025-12-31"]
        r = bootstrap_ci(rets)
        r["n_obs"] = int(len(rets))
        out["arms"]["C_real_spy"] = r
        out["arms"]["C_real_spy_ci_low_below_0.4"] = bool(r["ci_low"] < 0.4)

    confirmed = analytic_ok and (sim_below >= 3)
    out["claim_confirmed"] = confirmed
    print(json.dumps(out, indent=2))
    return 0 if confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())
