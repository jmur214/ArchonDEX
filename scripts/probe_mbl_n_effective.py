"""
probe_mbl_n_effective.py — data-free arithmetic on the MBL / DSR bar.

Seeded claim 1A.4 (alpha-frontier review 2026-09-30):
  (a) the MBL gate uses the upper bound 2·ln(N) instead of the exact E[max_N]²;
  (b) N counts every run as an independent trial (no correlation adjustment);
  (c) with N_eff computed for correlated trials the DSR bar could drop materially.

This probe computes:
  1. E[max of N iid standard normals] via the Bailey-López de Prado (2014)
     approximation  E[max_N] ≈ (1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e)),  γ = 0.5772,
     and via exact numerical integration, for N ∈ {75, 231, 260, 500}.
  2. The overstatement ratio  2·ln(N) / E[max_N]²  (how much the upper-bound MBL
     formula inflates required years relative to the exact form).
  3. Required SR to clear MBL on T ∈ {5, 12, 26, 64} years under each form:
        SR_req = sqrt(2·ln N / T)     (upper-bound form, as in mbl_gate.py)
        SR_req = E[max_N] / sqrt(T)   (exact form)
  4. The equicorrelated-trials identity: if N trials have pairwise correlation ρ,
        X_i = sqrt(ρ)·Z₀ + sqrt(1−ρ)·Z_i  ⇒  E[max_i X_i] = sqrt(1−ρ)·E[max_N iid]
     so E[max]² scales by (1−ρ). Table of SR_req over ρ̄ ∈ {0, .3, .5, .7, .9}.
     (The general case uses López de Prado's ONC clustering on the run registry's
     return-series correlation matrix; the registry is not in this container, so
     this probe reports the bar as a FUNCTION of ρ̄ — the empirical ρ̄ is the
     first deliverable of the repair brief.)

Deterministic; no randomness. Prints JSON.
"""
from __future__ import annotations

import json
import math

import numpy as np
from scipy import integrate, stats

GAMMA = 0.5772156649


def emax_approx(n: int) -> float:
    return (1 - GAMMA) * stats.norm.ppf(1 - 1.0 / n) + GAMMA * stats.norm.ppf(1 - 1.0 / (n * math.e))


def emax_exact(n: int) -> float:
    # E[max] = ∫ x · n · φ(x) · Φ(x)^(n−1) dx
    f = lambda x: x * n * stats.norm.pdf(x) * stats.norm.cdf(x) ** (n - 1)
    v, _ = integrate.quad(f, -10, 10, limit=200)
    return v


def main() -> None:
    out = {"rows": [], "sr_required": [], "sr_required_vs_rho": []}
    for n in (75, 231, 260, 500):
        ea, ee = emax_approx(n), emax_exact(n)
        ub = 2 * math.log(n)
        out["rows"].append({
            "N": n,
            "E_max_approx": round(ea, 4),
            "E_max_exact": round(ee, 4),
            "E_max_sq_exact": round(ee * ee, 4),
            "two_ln_N": round(ub, 4),
            "overstatement_ratio_2lnN_over_Emax_sq": round(ub / (ee * ee), 4),
            "required_years_overstated_pct": round((ub / (ee * ee) - 1) * 100, 1),
        })
        for t in (5, 12, 26, 64):
            out["sr_required"].append({
                "N": n, "T_years": t,
                "SR_req_upper_bound_form": round(math.sqrt(ub / t), 3),
                "SR_req_exact_form": round(ee / math.sqrt(t), 3),
            })
    n = 260
    ee = emax_exact(n)
    for rho in (0.0, 0.3, 0.5, 0.7, 0.9):
        for t in (12, 26):
            out["sr_required_vs_rho"].append({
                "N": n, "rho_bar": rho, "T_years": t,
                "SR_req_exact_equicorr": round(math.sqrt(1 - rho) * ee / math.sqrt(t), 3),
            })
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
