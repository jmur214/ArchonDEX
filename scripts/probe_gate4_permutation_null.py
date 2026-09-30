"""
probe_gate4_permutation_null.py — deterministic probe of the Engine D Gate 4
permutation null (engines/engine_d_discovery/significance.py::monte_carlo_permutation_test).

Claim under test (alpha-frontier review 2026-09-30, seeded claim 1A.1):
    The null is built by `rng.permutation(returns)` — shuffling the strategy's
    OWN return series. A permutation of a vector leaves its mean and std
    invariant, so every null Sharpe equals the actual Sharpe to floating-point
    precision, null_std ~ 1e-16, and the p-value is rounding noise. No edge
    can pass Gate 4 by construction.

This probe:
  1. Runs the production function on synthetic series with known true Sharpe
     (0.0, 0.5, 1.6, 5.2) and prints p_value / null_std.
  2. Runs a CORRECT null for comparison — permute the SIGNAL against the
     returns (destroys signal-return alignment, preserves both marginals) —
     and a sign-flip null around zero mean — to show what the p-value should be.
  3. Asserts the defect: null_std < 1e-10 for every series.

Deterministic: seeded RandomState(0); no wall-clock in output.
Run:  python scripts/probe_gate4_permutation_null.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.engine_d_discovery.significance import monte_carlo_permutation_test  # noqa: E402

ANN = np.sqrt(252.0)


def make_series(true_sr_annual: float, n: int, rng: np.random.RandomState) -> tuple[np.ndarray, np.ndarray]:
    """Return (signal, asset_returns) such that strategy = signal * asset_returns
    has approximately the requested annual Sharpe."""
    asset = rng.normal(0.0, 0.01, n)
    # signal that is correlated with next return with strength tuned to hit target SR
    daily_sr = true_sr_annual / ANN
    signal = np.sign(asset + rng.normal(0.0, 0.01 / max(daily_sr, 1e-6) * 0.0 + 0.01, n))
    strat = signal * asset
    # rescale mean to hit target daily SR exactly (keeps the sign/permutation structure)
    strat = strat - strat.mean() + daily_sr * strat.std()
    return signal, strat


def correct_null_signal_permutation(signal: np.ndarray, asset: np.ndarray, n_perm: int, rng: np.random.RandomState) -> tuple[float, float]:
    """Permute the SIGNAL against the returns. Preserves marginals; destroys alignment."""
    actual = (signal * asset).mean() / (signal * asset).std() * ANN
    nulls = np.empty(n_perm)
    for i in range(n_perm):
        s = rng.permutation(signal)
        r = s * asset
        sd = r.std()
        nulls[i] = 0.0 if sd < 1e-12 else r.mean() / sd * ANN
    return float((nulls >= actual).mean()), float(nulls.std())


def sign_flip_null(strat: np.ndarray, n_perm: int, rng: np.random.RandomState) -> tuple[float, float]:
    """Sign-flip null around zero mean (valid H0: E[r]=0, symmetric)."""
    actual = strat.mean() / strat.std() * ANN
    nulls = np.empty(n_perm)
    for i in range(n_perm):
        flips = rng.choice([-1.0, 1.0], size=strat.size)
        r = strat * flips
        nulls[i] = r.mean() / r.std() * ANN
    return float((nulls >= actual).mean()), float(nulls.std())


def main() -> int:
    rng = np.random.RandomState(0)
    n = 756  # 3 years daily
    out = {"n_obs": n, "rows": []}
    defect_confirmed = True
    for target in (0.0, 0.5, 1.6, 5.2):
        asset = rng.normal(0.0, 0.01, n)
        # construct strat with exact target SR
        daily_sr = target / ANN
        noise = rng.normal(0.0, 0.01, n)
        strat = noise - noise.mean() + daily_sr * noise.std()
        # a signal such that signal*asset == strat is not needed for the production test;
        # the production test takes only the strategy return series.
        prod = monte_carlo_permutation_test(strat, n_permutations=1000, random_state=42)
        # For the correct-null comparison build an explicit (signal, asset) pair with same SR.
        sig = np.sign(rng.normal(0, 1, n))
        asset2 = rng.normal(0.0, 0.01, n)
        # inject alignment: asset2 = asset2 + k*sig so that strategy sig*asset2 has target SR
        k = daily_sr * 0.01  # approx: mean of sig*asset2 = k, std ~ 0.01
        asset2 = asset2 + k * sig
        p_sigperm, sd_sigperm = correct_null_signal_permutation(sig, asset2, 1000, np.random.RandomState(1))
        p_flip, sd_flip = sign_flip_null(sig * asset2, 1000, np.random.RandomState(2))
        row = {
            "target_sr": target,
            "prod_actual_sharpe": round(prod["actual_sharpe"], 4),
            "prod_p_value": prod["p_value"],
            "prod_null_std": prod["null_std"],
            "prod_null_mean": round(prod["null_mean"], 4),
            "correct_signal_perm_p": p_sigperm,
            "correct_signal_perm_null_std": round(sd_sigperm, 4),
            "sign_flip_p": p_flip,
            "sign_flip_null_std": round(sd_flip, 4),
        }
        out["rows"].append(row)
        if prod["null_std"] > 1e-10:
            defect_confirmed = False
    out["defect_confirmed_null_std_lt_1e-10_for_all"] = defect_confirmed
    print(json.dumps(out, indent=2))
    return 0 if defect_confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())
