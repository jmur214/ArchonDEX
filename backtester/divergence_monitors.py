# backtester/divergence_monitors.py
"""CUSUM + Page-Hinkley divergence monitors (T-152).

The pre-registered live-vs-expected kill metrics, built and CALIBRATED
on backtest data BEFORE paper trading exists — tuning a kill metric
while capital is at risk is how kill metrics get loosened (ops
playbook). SHADOW/REPORTING ONLY: nothing consumes these for action;
the eventual paper-loop hook is documented in the T-152 audit, not
built.

Both monitors consume STANDARDIZED innovations
``z_t = (r_t − μ_t) / σ_t`` where (μ, σ) is the expected-return model.
In shadow mode the expectation is the series' own LAGGED rolling stats
(the null: the backtest diverging from itself ⇒ structural break inside
the backtest). In the live use-case the expectation stream is the
backtest's — same interface, different feed.

  * CUSUM (two-sided, standardized): S⁺ ← max(0, S⁺ + z − k),
    S⁻ ← max(0, S⁻ − z − k); alarm when either exceeds h; reset after
    alarm. Research starting points (configurable, provenance =
    2026-06-10 research pass, flagged as starting points not gospel):
    k = 0.5 (σ units), h = 4-5.
  * Page-Hinkley (two-sided): m_t = Σ(z_i − z̄_i ∓ δ) tracked against
    its running extremum; alarm when the gap exceeds λ. Research
    starting points: δ = 0.005, λ = 50δ (σ units).

Streaming-friendly: each monitor exposes ``update(z) -> bool`` and is
restart-free; ``run_monitor`` drives a whole series and is PROVEN
equivalent to incremental updates in the tests. Deterministic — pure
arithmetic, no RNG. σ-guard follows the project tolerance rule
(σ < 1e-12 or non-finite ⇒ the observation is skipped, never divided).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

__all__ = [
    "CusumMonitor",
    "PageHinkleyMonitor",
    "standardized_innovations",
    "run_monitor",
    "shadow_report",
]

_SIGMA_TOL = 1e-12


class CusumMonitor:
    """Two-sided standardized CUSUM. ``update(z)`` returns True on alarm
    (state resets so the monitor keeps watching)."""

    def __init__(self, k: float = 0.5, h: float = 4.0):
        if h <= 0 or k < 0:
            raise ValueError("CUSUM requires h > 0 and k >= 0")
        self.k = float(k)
        self.h = float(h)
        self.s_pos = 0.0
        self.s_neg = 0.0
        self.n_alarms = 0

    def update(self, z: float) -> bool:
        if not np.isfinite(z):
            return False
        self.s_pos = max(0.0, self.s_pos + z - self.k)
        self.s_neg = max(0.0, self.s_neg - z - self.k)
        if self.s_pos > self.h or self.s_neg > self.h:
            self.n_alarms += 1
            self.s_pos = 0.0
            self.s_neg = 0.0
            return True
        return False


class PageHinkleyMonitor:
    """Two-sided Page-Hinkley on standardized innovations. ``update(z)``
    returns True on alarm (full state reset afterward)."""

    def __init__(self, delta: float = 0.005, lam: float = 0.25):
        if lam <= 0 or delta < 0:
            raise ValueError("Page-Hinkley requires lam > 0 and delta >= 0")
        self.delta = float(delta)
        self.lam = float(lam)
        self.n_alarms = 0          # cumulative; survives post-alarm resets
        self._reset()

    def _reset(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m_pos = 0.0   # cumulative for downward-shift detection
        self.m_neg = 0.0
        self.min_m_pos = 0.0
        self.max_m_neg = 0.0

    def update(self, z: float) -> bool:
        if not np.isfinite(z):
            return False
        self.n += 1
        self.mean += (z - self.mean) / self.n
        self.m_pos += z - self.mean - self.delta
        self.m_neg += z - self.mean + self.delta
        self.min_m_pos = min(self.min_m_pos, self.m_pos)
        self.max_m_neg = max(self.max_m_neg, self.m_neg)
        up = (self.m_pos - self.min_m_pos) > self.lam     # upward shift
        down = (self.max_m_neg - self.m_neg) > self.lam   # downward shift
        if up or down:
            self.n_alarms += 1
            self._reset()
            return True
        return False


def standardized_innovations(
    returns: pd.Series,
    expected_mean: Optional[pd.Series] = None,
    expected_std: Optional[pd.Series] = None,
    window: int = 60,
    min_periods: int = 20,
) -> pd.Series:
    """``z_t = (r_t − μ_t)/σ_t`` with NO lookahead.

    When an expectation stream isn't supplied (shadow/null mode), μ and
    σ are the series' own rolling stats LAGGED one observation (stats
    through t−1 standardize r_t). Observations with no valid σ are
    dropped (tolerance guard, never divide-by-tiny).
    """
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if expected_mean is None:
        expected_mean = r.rolling(window, min_periods=min_periods).mean().shift(1)
    if expected_std is None:
        expected_std = r.rolling(window, min_periods=min_periods).std().shift(1)
    mu = expected_mean.reindex(r.index)
    sd = expected_std.reindex(r.index)
    ok = sd.notna() & np.isfinite(sd) & (sd > _SIGMA_TOL) & mu.notna()
    return ((r[ok] - mu[ok]) / sd[ok]).astype(float)


def shadow_report(
    returns: pd.Series,
    cfg: Optional[dict] = None,
) -> Dict[str, Any]:
    """The T-152 shadow block for performance summaries.

    Runs all three monitors at the CALIBRATED operating points (T-152,
    2026-06-11: most sensitive grid cell ≤1 false alarm/yr on 200
    block-bootstrap null replicas of the 2024 book — see
    scripts/calibrate_divergence_monitors_t152.py and the audit doc)
    over the record's own lagged-rolling-null innovations. REPORTING
    ONLY — nothing acts on these. Config overrides via the optional
    ``divergence_monitors`` block in backtest_settings.json.
    """
    c = dict(cfg or {})
    cusum_k = float(c.get("cusum_k", 1.0))
    cusum_h = float(c.get("cusum_h", 5.0))
    var_k = float(c.get("var_k", 2.0))
    var_h = float(c.get("var_h", 12.0))
    ph_delta = float(c.get("ph_delta", 0.05))
    ph_lambda = float(c.get("ph_lambda", 20.0))
    window = int(c.get("window", 60))
    min_periods = int(c.get("min_periods", 20))

    base: Dict[str, Any] = {
        "divergence_alarms": None,
        "divergence_detail": {
            "cusum_mean": None, "cusum_var": None, "page_hinkley": None,
            "operating_points": {
                "cusum_mean": [cusum_k, cusum_h],
                "cusum_var": [var_k, var_h],
                "page_hinkley": [ph_delta, ph_lambda],
            },
            "skip_reason": None,
        },
    }
    try:
        z = standardized_innovations(returns, window=window,
                                     min_periods=min_periods)
        if len(z) < min_periods:
            base["divergence_detail"]["skip_reason"] = "insufficient_history"
            return base
        zv = ((z ** 2) - 1.0) / np.sqrt(2.0)
        rep_mean = run_monitor(z, CusumMonitor(cusum_k, cusum_h))
        rep_var = run_monitor(zv, CusumMonitor(var_k, var_h))
        rep_ph = run_monitor(z, PageHinkleyMonitor(ph_delta, ph_lambda))
        base["divergence_alarms"] = int(
            rep_mean["n_alarms"] + rep_var["n_alarms"] + rep_ph["n_alarms"]
        )
        base["divergence_detail"].update({
            "cusum_mean": rep_mean, "cusum_var": rep_var,
            "page_hinkley": rep_ph,
        })
        return base
    except Exception as exc:  # reporting must never fail a backtest
        base["divergence_detail"]["skip_reason"] = f"error:{type(exc).__name__}"
        return base


def run_monitor(z: pd.Series, monitor) -> Dict[str, Any]:
    """Drive a monitor over a standardized-innovation series.

    Returns JSON-native: alarm dates (ISO strings), counts, and the
    per-year rate. Equivalent to calling ``update`` incrementally —
    proven in tests (the streaming contract for the future paper loop).
    """
    alarms: List[str] = []
    for ts, val in z.items():
        if monitor.update(float(val)):
            alarms.append(str(pd.Timestamp(ts).date()))
    n = len(z)
    years = max(n / 252.0, 1e-9)
    return {
        "n_obs": int(n),
        "n_alarms": len(alarms),
        "alarms_per_year": round(len(alarms) / years, 3),
        "alarm_dates": alarms,
    }
