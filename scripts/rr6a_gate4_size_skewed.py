"""R's F4 (RR-6a) — does Gate 4's sign-flip null hold its SIZE on skewed zero-mean streams?

PRE-REGISTRATION (written and committed BEFORE the first run; N_trials consumed: 0 — synthetic
streams only, no backtest on the data substrate):

  Hypothesis. RR-2's stationary-block SIGN-FLIP null assumes H0 = "true mean zero AND the
  distribution is symmetric". Discovery attribution spreads are skewed. Under a zero-mean but
  SKEWED stream the sign-flip null may not hold its nominal size.

  Statistic. The rejection rate of `monte_carlo_permutation_test(x, n_permutations=500)` at
  alpha = 0.05 — called exactly as `validate_candidate` calls it (Gate 4: p < 0.05) — over
  M = 400 independent zero-mean streams per cell, with a Wilson 95% CI.

  Cells. Lengths n = 756 (3 y) and n = 3269 (the RR-1 rescore window, 2012–2024), crossed with
  five H0 generators, all with true mean EXACTLY zero and daily sd 0.01:
    normal      — iid N(0, 1): the control; size must hold here or the harness is wrong
    lognorm_R   — centred lognormal, sigma 1.0 (skewness ~ +6): right-skewed
    lognorm_L   — its negation: LEFT-skewed (crash-shaped; the case that matters for spreads)
    garch_N     — GARCH(1,1) (omega .05, alpha .08, beta .90) with normal innovations
    garch_L     — the same GARCH with left-skewed centred-lognormal innovations

  Reading, fixed in advance (precedence order):
    1. normal cell's CI excludes 0.05            -> HARNESS INVALID; nothing else is read.
    2. any skewed cell's CI LOW > 0.05           -> SIZE DRIFTS (over-rejection: false
       discoveries). The brief's drop-in replacement is the stationary bootstrap centred at
       zero; that is a referee change for its own propose-first unit, not made here.
    3. any skewed cell's CI HIGH < 0.025         -> CONSERVATIVE (power loss); reported, no action.
    4. otherwise                                 -> SIZE HOLDS on these generators.

  This is a MEASUREMENT, not a reversion test. Seeds are fixed (stream seed = cell index * 10_000
  + replicate; the null's own random_state is the production default), so a re-run reproduces it.

    python -m scripts.rr6a_gate4_size_skewed                 # prints only
    python -m scripts.rr6a_gate4_size_skewed --out PATH.json # also writes the record
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from typing import Callable, Dict, List

import numpy as np

from engines.engine_d_discovery.significance import monte_carlo_permutation_test

ALPHA = 0.05
M = 400
LENGTHS = (756, 3269)
SD = 0.01


def _centred_lognormal(rng: np.random.Generator, n: int, sigma: float = 1.0) -> np.ndarray:
    # E[exp(sigma Z)] = exp(sigma^2 / 2): subtract the POPULATION mean, so the true mean is 0.
    return np.exp(sigma * rng.standard_normal(n)) - math.exp(sigma ** 2 / 2)


def _garch(n: int, innov: Callable[[int], np.ndarray]) -> np.ndarray:
    z = innov(n)
    z = z / np.sqrt(np.mean(z ** 2)) if np.mean(z ** 2) > 0 else z
    omega, a, b = 0.05, 0.08, 0.90
    h = omega / (1 - a - b)
    out = np.empty(n)
    for t in range(n):
        out[t] = math.sqrt(h) * z[t]
        h = omega + a * out[t] ** 2 + b * h
    return out


def _population_sd(kind: str) -> float:
    """Population sd of each generator BEFORE scaling, so scaling never uses the sample."""
    if kind == "normal":
        return 1.0
    if kind in ("lognorm_R", "lognorm_L"):
        s2 = 1.0
        return math.sqrt((math.exp(s2) - 1) * math.exp(s2))
    return math.sqrt(0.05 / (1 - 0.08 - 0.90))          # GARCH unconditional sd


def generate(kind: str, rng: np.random.Generator, n: int) -> np.ndarray:
    if kind == "normal":
        x = rng.standard_normal(n)
    elif kind == "lognorm_R":
        x = _centred_lognormal(rng, n)
    elif kind == "lognorm_L":
        x = -_centred_lognormal(rng, n)
    elif kind == "garch_N":
        x = _garch(n, lambda k: rng.standard_normal(k))
    elif kind == "garch_L":
        x = _garch(n, lambda k: -_centred_lognormal(rng, k))
    else:
        raise ValueError(kind)
    return x / _population_sd(kind) * SD               # true mean stays exactly 0


def wilson(k: int, m: int, z: float = 1.959964) -> tuple:
    p = k / m
    d = 1 + z * z / m
    c = (p + z * z / (2 * m)) / d
    h = z * math.sqrt(p * (1 - p) / m + z * z / (4 * m * m)) / d
    return (max(0.0, c - h), min(1.0, c + h))


KINDS = ("normal", "lognorm_R", "lognorm_L", "garch_N", "garch_L")


def run() -> Dict:
    cells: List[Dict] = []
    for ci, (n, kind) in enumerate([(n, k) for n in LENGTHS for k in KINDS]):
        t0 = time.time()
        rejects = 0
        for rep in range(M):
            x = generate(kind, np.random.default_rng(ci * 10_000 + rep), n)
            p = monte_carlo_permutation_test(x, n_permutations=500)["p_value"]
            rejects += int(p < ALPHA)
        lo, hi = wilson(rejects, M)
        cells.append({"n": n, "generator": kind, "rejections": rejects, "M": M,
                      "size": rejects / M, "ci95": [round(lo, 4), round(hi, 4)],
                      "seconds": round(time.time() - t0, 1)})
        print(f"n={n:5d} {kind:10s} size={rejects / M:.4f} [{lo:.4f}, {hi:.4f}]  ({time.time() - t0:.0f}s)",
              flush=True)

    controls = [c for c in cells if c["generator"] == "normal"]
    skewed = [c for c in cells if c["generator"] != "normal"]
    if any(not (c["ci95"][0] <= ALPHA <= c["ci95"][1]) for c in controls):
        reading = "1 HARNESS INVALID — the normal control's CI excludes 0.05; nothing else is read"
    elif any(c["ci95"][0] > ALPHA for c in skewed):
        reading = "2 SIZE DRIFTS — over-rejection on: " + ", ".join(
            f"{c['generator']}@{c['n']}" for c in skewed if c["ci95"][0] > ALPHA)
    elif any(c["ci95"][1] < 0.025 for c in skewed):
        reading = "3 CONSERVATIVE — power loss on: " + ", ".join(
            f"{c['generator']}@{c['n']}" for c in skewed if c["ci95"][1] < 0.025)
    else:
        reading = "4 SIZE HOLDS on these generators"
    return {"alpha": ALPHA, "M": M, "n_permutations": 500, "cells": cells, "reading": reading,
            "n_trials_consumed": 0}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None, help="write the record here (default: print only)")
    a = ap.parse_args(argv)
    rec = run()
    print(f"\nREADING: {rec['reading']}")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(rec, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
