# backtester/safef_car25.py
"""safe-f / CAR25 — Bandy's position-sizing health metric (T-151).

REPORTING-FIRST: nothing consumes these numbers for sizing; they are a
system-health diagnostic (and the designated future live-ops kill
metric: a falling safe_f/CAR25 is the pre-registered health alarm).
A sizing enable is a later, user-gated step.

Method (reconstructed from Bandy's published *Modeling Trading System
Performance* approach — the research flagged his EXACT parameters as
unverified, so every default below is CONFIG, not gospel):

  1. From the system's daily return record, draw ``n_paths`` Monte
     Carlo resamples of a ``horizon_days`` (default 2-year) equity
     sequence — CIRCULAR BLOCK bootstrap (default 10-day blocks) so
     serial correlation survives the resample (iid resampling
     understates drawdown risk on autocorrelated dailies; same
     rationale as the project's block-bootstrap CI standard).
  2. At candidate fraction ``f``, the levered daily return is
     ``f × r_t`` (f = 1.0 reproduces the system's current implicit
     sizing). Per path compute max drawdown.
  3. **safe_f** = the largest f such that
     ``P(MaxDD > dd_tolerance) ≤ dd_probability``
     (defaults: P(DD > 20% over 2y) ≤ 5%).
  4. At safe_f, compute the per-path CAGR distribution → **CAR25** =
     its 25th percentile (a conservative compound-growth estimate at
     the safe sizing level).

Determinism: the resample index matrix is drawn ONCE from a pinned
seed and reused for every f evaluated — this both pins the result
bitwise and makes the 95th-pct MaxDD strictly monotone in f (scaling
the SAME paths), so safe_f is solved by bisection with no MC noise
between iterations.

The over/under diagnostic: safe_f > 1 ⇒ the current sizing sits INSIDE
the Bandy-safe envelope (headroom = safe_f − 1); safe_f < 1 ⇒ the
current book is OVERSIZED relative to the configured drawdown
tolerance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

__all__ = ["SafeFConfig", "compute_safef_car25"]

TRADING_DAYS = 252.0


@dataclass
class SafeFConfig:
    """All defaults are documented reconstructions, NOT verified Bandy
    parameters — tune via the ``safef_car25`` block in
    backtest_settings.json."""
    dd_tolerance: float = 0.20       # the drawdown that must stay rare
    dd_probability: float = 0.05     # max P(MaxDD > tolerance)
    horizon_days: int = 504          # 2 trading years
    n_paths: int = 1000
    block_days: int = 10             # circular block length
    f_max: float = 5.0               # search ceiling (also the cap when
                                     # the tolerance never binds)
    f_tol: float = 0.01              # bisection resolution
    seed: int = 0
    min_history_days: int = 126      # below this: skip (half a year)


def _resample_matrix(n_obs: int, cfg: SafeFConfig) -> np.ndarray:
    """(n_paths × horizon_days) index matrix, circular block bootstrap,
    drawn once from the pinned seed."""
    rng = np.random.default_rng(cfg.seed)
    n_blocks = int(np.ceil(cfg.horizon_days / cfg.block_days))
    starts = rng.integers(0, n_obs, size=(cfg.n_paths, n_blocks))
    offsets = np.arange(cfg.block_days)
    idx = (starts[:, :, None] + offsets[None, None, :]).reshape(cfg.n_paths, -1)
    return (idx[:, : cfg.horizon_days]) % n_obs


def _max_drawdowns(levered: np.ndarray) -> np.ndarray:
    """Per-path max drawdown for an (n_paths × horizon) levered-return
    matrix. Returns positive magnitudes."""
    equity = np.cumprod(1.0 + levered, axis=1)
    peaks = np.maximum.accumulate(equity, axis=1)
    dd = 1.0 - equity / peaks
    return dd.max(axis=1)


def _exceedance(returns_matrix: np.ndarray, f: float, cfg: SafeFConfig) -> float:
    return float((_max_drawdowns(f * returns_matrix) > cfg.dd_tolerance).mean())


def compute_safef_car25(
    daily_returns: pd.Series,
    cfg: Optional[SafeFConfig] = None,
) -> Dict[str, Any]:
    """Compute safe_f and CAR25 for a daily return record.

    Returns a JSON-native dict; on any precluding input the metric
    fields are None with a ``skip_reason`` (reporting never raises —
    the T-141 fail-open contract).
    """
    cfg = cfg or SafeFConfig()
    base: Dict[str, Any] = {
        "safe_f": None,
        "car25_pct": None,
        "prob_dd_at_f1": None,
        "mdd95_at_f1_pct": None,
        "car25_at_f1_pct": None,
        "headroom": None,
        "n_obs": None,
        "config": {k: (float(v) if isinstance(v, (int, float)) else v)
                   for k, v in asdict(cfg).items()},
        "skip_reason": None,
    }
    try:
        r = pd.to_numeric(daily_returns, errors="coerce").dropna()
        r = r[np.isfinite(r)]
        n = len(r)
        base["n_obs"] = int(n)
        if n < cfg.min_history_days:
            base["skip_reason"] = "insufficient_history"
            return base
        arr = r.values.astype(float)
        if np.all(arr >= 0.0):
            # No losing day on record: the tolerance never binds.
            base["skip_reason"] = "degenerate_nonnegative_returns"
            base["safe_f"] = float(cfg.f_max)
            return base

        idx = _resample_matrix(n, cfg)
        paths = arr[idx]                       # (n_paths × horizon)

        def cagr_pct(f: float) -> Dict[str, float]:
            levered = f * paths
            growth = np.prod(1.0 + levered, axis=1)
            growth = np.clip(growth, 1e-12, None)
            cagr = growth ** (TRADING_DAYS / cfg.horizon_days) - 1.0
            return {
                "car25": float(np.percentile(cagr, 25) * 100.0),
                "mdd95": float(np.percentile(_max_drawdowns(levered), 95) * 100.0),
            }

        # Diagnostics at the current implicit sizing (f = 1).
        at1 = cagr_pct(1.0)
        base["prob_dd_at_f1"] = round(_exceedance(paths, 1.0, cfg), 4)
        base["mdd95_at_f1_pct"] = round(at1["mdd95"], 2)
        base["car25_at_f1_pct"] = round(at1["car25"], 2)

        # safe_f by bisection on the SAME paths (exceedance is monotone
        # non-decreasing in f, so this is exact to f_tol).
        lo, hi = 0.0, float(cfg.f_max)
        if _exceedance(paths, hi, cfg) <= cfg.dd_probability:
            safe_f = hi                        # ceiling never binds
        else:
            while hi - lo > cfg.f_tol:
                mid = 0.5 * (lo + hi)
                if _exceedance(paths, mid, cfg) <= cfg.dd_probability:
                    lo = mid
                else:
                    hi = mid
            safe_f = lo
        base["safe_f"] = round(float(safe_f), 3)
        base["headroom"] = round(float(safe_f) - 1.0, 3)
        base["car25_pct"] = round(cagr_pct(safe_f)["car25"], 2)
        return base
    except Exception as exc:  # reporting must never fail a backtest
        base["skip_reason"] = f"error:{type(exc).__name__}"
        return base
