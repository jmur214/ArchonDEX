"""
scripts/ci_coverage_audit_t257.py
=================================
T-2026-07-02-257 Part 2 — CI-machinery coverage audit (the yardstick's validity).

The program gates on `MetricsEngine.bootstrap_distribution` block-bootstrap
`ci_low` for Sortino/MaxDD, but its coverage on a realistic (fat-tailed, vol-
clustered) DGP was never verified, and block-bootstrap MaxDD is structurally
suspect (resampling reorders paths → breaks the contiguous worst run →
SHORTENS drawdowns → optimistic CI).

This is a Monte-Carlo coverage study on a GARCH(1,1)-t DGP (fat tails + vol
clustering — the serial dependence block-bootstrap exists to handle):
  1. SORTINO coverage: does the nominal-90% CI contain the POPULATION Sortino
     ~90% of the time? Across block_length ∈ {1(iid), 5, auto, 21, 63}.
  2. MAXDD bias: is the bootstrap MaxDD distribution shifted SHORTER (less
     negative) than the true across-path MaxDD distribution? By how much?

Read-only (calls the production bootstrap; no metrics_engine change).
Deterministic (seeded). Output: data/research/t257/ci_coverage.json + table.
Usage: python -m scripts.ci_coverage_audit_t257
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402

OUT = ROOT / "data" / "research" / "t257" / "ci_coverage.json"

# GARCH(1,1)-t DGP — realistic daily equity: ~8%/yr drift, ~16%/yr uncond vol,
# fat tails (t df=5), persistent vol clustering (alpha+beta≈0.97).
MU = 0.0003
ALPHA, BETA = 0.09, 0.88
UNCOND_VAR = (0.01) ** 2                       # ~1%/day → ~16%/yr
OMEGA = UNCOND_VAR * (1.0 - ALPHA - BETA)
DF = 5.0
T = 1512          # ~6yr sample (a typical gauntlet window)
N_SAMPLES = 300   # Monte-Carlo replications
BOOT = 500
CONF = 0.90       # nominal coverage under test


def simulate_garch_t(n: int, rng: np.random.Generator, burn: int = 500) -> np.ndarray:
    """GARCH(1,1) with standardized Student-t innovations."""
    m = n + burn
    z = rng.standard_t(DF, size=m) / np.sqrt(DF / (DF - 2.0))   # unit-variance t
    r = np.empty(m)
    s2 = UNCOND_VAR
    eps = 0.0
    for i in range(m):
        s2 = OMEGA + ALPHA * eps * eps + BETA * s2
        eps = np.sqrt(s2) * z[i]
        r[i] = MU + eps
    return r[burn:]


def _maxdd(returns: pd.Series) -> float:
    eq = (1.0 + returns).cumprod() * 100.0
    return float(MetricsEngine.max_drawdown(eq))


def main() -> int:
    rng = np.random.default_rng(12345)

    # population truth (very long path)
    pop = simulate_garch_t(400_000, np.random.default_rng(1))
    pop_sortino = float(MetricsEngine.sortino_ratio(pd.Series(pop)))

    # pre-generate the Monte-Carlo samples (shared across block-lengths)
    samples = [pd.Series(simulate_garch_t(T, rng)) for _ in range(N_SAMPLES)]
    true_maxdds = np.array([_maxdd(s) for s in samples])   # the true across-path MaxDD dist

    report = {"task": "T-2026-07-02-257 Part 2 — CI coverage audit",
              "dgp": {"model": "GARCH(1,1)-t", "df": DF, "alpha": ALPHA, "beta": BETA,
                      "uncond_vol_ann": round(np.sqrt(UNCOND_VAR * 252), 4),
                      "persistence_alpha_plus_beta": ALPHA + BETA},
              "T": T, "n_samples": N_SAMPLES, "boot_iters": BOOT, "nominal_conf": CONF,
              "population_sortino": round(pop_sortino, 4),
              "sortino_coverage_by_block": {}, "maxdd_bias": {}}

    # 1. Sortino coverage across block lengths (block=1 == iid)
    for blk in [1, 5, None, 21, 63]:
        hits, widths, lows = 0, [], []
        for s in samples:
            d = MetricsEngine.bootstrap_distribution(
                s, MetricsEngine.sortino_ratio, n_iterations=BOOT,
                block_length=blk, seed=0, confidence=CONF)
            if d["ci_low"] <= pop_sortino <= d["ci_high"]:
                hits += 1
            widths.append(d["ci_high"] - d["ci_low"])
            lows.append(d["ci_low"])
        key = "auto" if blk is None else str(blk)
        report["sortino_coverage_by_block"][key] = {
            "coverage": round(hits / N_SAMPLES, 3),
            "mean_ci_width": round(float(np.mean(widths)), 4),
            "mean_ci_low": round(float(np.mean(lows)), 4),
        }

    # 2. MaxDD bootstrap bias (auto block): bootstrap-MaxDD median vs the
    #    true across-path MaxDD median. Also MaxDD-CI coverage of the true dist.
    boot_medians, hits = [], 0
    true_median = float(np.median(true_maxdds))
    for s in samples:
        d = MetricsEngine.bootstrap_distribution(
            s, _maxdd, n_iterations=BOOT, block_length=None, seed=0, confidence=CONF)
        boot_medians.append(d["median"])
        if d["ci_low"] <= true_median <= d["ci_high"]:
            hits += 1
    boot_median = float(np.median(boot_medians))
    report["maxdd_bias"] = {
        "true_maxdd_median": round(true_median, 4),
        "true_maxdd_p05": round(float(np.percentile(true_maxdds, 5)), 4),
        "bootstrap_maxdd_median": round(boot_median, 4),
        "shortening_bias_pp": round((boot_median - true_median) * 100.0, 2),
        "shortening_ratio": round(boot_median / true_median, 3) if true_median != 0 else None,
        "maxdd_ci_coverage_of_true_median": round(hits / N_SAMPLES, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"\nT-257 Part 2 — CI coverage (GARCH-t, T={T}, {N_SAMPLES} samples, nominal {int(CONF*100)}%)")
    print(f"population Sortino = {report['population_sortino']}")
    print(f"\nSORTINO CI coverage by block_length (nominal {int(CONF*100)}%):")
    for k, v in report["sortino_coverage_by_block"].items():
        print(f"   block={k:>4s}: coverage {v['coverage']*100:5.1f}%  "
              f"(mean width {v['mean_ci_width']}, mean ci_low {v['mean_ci_low']})")
    mb = report["maxdd_bias"]
    print(f"\nMAXDD bootstrap bias (auto block):")
    print(f"   true MaxDD median (across paths)  = {mb['true_maxdd_median']}  (p05 {mb['true_maxdd_p05']})")
    print(f"   bootstrap MaxDD median            = {mb['bootstrap_maxdd_median']}")
    print(f"   SHORTENING bias                   = {mb['shortening_bias_pp']:+.2f}pp "
          f"(ratio {mb['shortening_ratio']}) — positive = bootstrap UNDERSTATES the drawdown")
    print(f"   MaxDD-CI coverage of true median  = {mb['maxdd_ci_coverage_of_true_median']*100:.1f}% (nominal {int(CONF*100)}%)")
    print(f"\n[T257] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
