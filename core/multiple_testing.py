"""
core/multiple_testing.py
========================
Family-wise multiple-testing machinery (T-2026-06-11-149 Part A).

Promoted from the T-137/T-144/T-145 analysis scripts (three consumers) into
standing infrastructure — the family-wise gate the 2026-05-31 external
research specified for any event-family / model-family comparison.

Contents:
  - romano_wolf_stepm: Romano & Wolf (2005) stepwise multiple testing with a
    JOINT circular-block bootstrap null (shared resample indices across
    family members → cross-member dependence preserved). Two-sided,
    studentized, FWER-controlled.
  - spa_test: Hansen (2005) Superior Predictive Ability — does ANY model in
    a family beat the benchmark? Studentized max-statistic over recentred
    block-bootstrap draws. With a single model this reduces to a robust
    one-sided test of mean(difference) > 0.

Both are deterministic given `seed` (CLAUDE.md determinism discipline) and use
block bootstraps (iid resampling underestimates CI width on serially-
correlated financial series — CLAUDE.md `[NN-SHARPE-CI]`).
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

DEFAULT_B = 1000
DEFAULT_BLOCK = 21
DEFAULT_ALPHA = 0.05


def _tstat(col: np.ndarray) -> float:
    v = col[np.isfinite(col)]
    if len(v) < 30 or not np.isfinite(v.std()) or v.std() < 1e-12:
        return 0.0
    return float(v.mean() / (v.std(ddof=1) / np.sqrt(len(v))))


def romano_wolf_stepm(series: Dict[str, pd.Series], b: int = DEFAULT_B,
                      block: int = DEFAULT_BLOCK, alpha: float = DEFAULT_ALPHA,
                      seed: int = 0) -> Dict:
    """FWER-controlled stepwise test that each series' mean != 0 (two-sided).

    Parameters
    ----------
    series : {name: pd.Series} — per-period values per family member (e.g.
        calendar-time event-portfolio daily returns). Indices are union-aligned.
    b, block : bootstrap draws and circular block length.
    alpha : family-wise error rate.

    Returns dict with observed t-stats, the FWER-alpha survivor list, the
    final critical value, and the union-calendar length.
    """
    names = list(series.keys())
    cal = pd.Index(sorted(set().union(*[s.index for s in series.values()])))
    X = pd.DataFrame({k: s.reindex(cal) for k, s in series.items()})
    n = len(cal)

    t_obs = {k: _tstat(X[k].to_numpy()) for k in names}

    rng = np.random.default_rng(seed)
    Xc = (X - X.mean()).to_numpy()
    n_blocks = int(np.ceil(n / block))
    boot_T = np.zeros((b, len(names)))
    for i in range(b):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(np.arange(s, s + block) % n) for s in starts])[:n]
        sample = Xc[idx]
        for j in range(len(names)):
            boot_T[i, j] = abs(_tstat(sample[:, j]))

    rejected: list[str] = []
    active = list(range(len(names)))
    order = sorted(active, key=lambda j: -abs(t_obs[names[j]]))
    while active:
        max_null = boot_T[:, active].max(axis=1)
        crit = float(np.quantile(max_null, 1 - alpha))
        newly = [j for j in order if j in active and abs(t_obs[names[j]]) > crit]
        if not newly:
            break
        for j in newly:
            rejected.append(names[j])
            active.remove(j)
    crit_final = float(np.quantile(boot_T[:, active].max(axis=1), 1 - alpha)) \
        if active else None
    return {
        "t_observed": {k: round(v, 3) for k, v in t_obs.items()},
        "survivors_fwer05": rejected,
        "final_critical_value": crit_final,
        "n_days_union_calendar": int(n),
    }


def spa_test(diff_series: Dict[str, pd.Series], b: int = DEFAULT_B,
             block: int = DEFAULT_BLOCK, seed: int = 0) -> Dict:
    """Hansen (2005) SPA: does any model beat the benchmark?

    Parameters
    ----------
    diff_series : {model_name: pd.Series} — per-period PERFORMANCE DIFFERENCE
        (model minus benchmark; positive = model better). One entry = the
        single-comparison case (a robust one-sided mean>0 test).

    Returns dict with the studentized max statistic, the SPA p-value
    (one-sided: H0 = no model beats the benchmark), and per-model t-stats.
    """
    names = list(diff_series.keys())
    cal = pd.Index(sorted(set().union(*[s.index for s in diff_series.values()])))
    D = pd.DataFrame({k: s.reindex(cal) for k, s in diff_series.items()})
    n = len(cal)

    t_obs = {k: _tstat(D[k].to_numpy()) for k in names}
    t_max = max(t_obs.values()) if t_obs else 0.0

    rng = np.random.default_rng(seed)
    Dc = (D - D.mean()).to_numpy()        # recentred null: no model beats
    n_blocks = int(np.ceil(n / block))
    null_max = np.empty(b)
    for i in range(b):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(np.arange(s, s + block) % n) for s in starts])[:n]
        sample = Dc[idx]
        null_max[i] = max(_tstat(sample[:, j]) for j in range(len(names)))

    p = float((null_max >= t_max).mean())
    return {
        "t_per_model": {k: round(v, 3) for k, v in t_obs.items()},
        "t_max_observed": round(t_max, 3),
        "spa_p_value": p,
        "n_periods": int(n),
        "rejects_h0_at_05": bool(p < 0.05),
    }


__all__ = ["romano_wolf_stepm", "spa_test"]
