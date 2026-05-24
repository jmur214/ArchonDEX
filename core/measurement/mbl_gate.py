"""core/measurement/mbl_gate.py
==============================
T-083: MBL Gate-0 — Minimum Backtest Length check.

Per CLAUDE.md non-negotiable #7 + the 2026-05-16 fourth research dive:

    T_years >= 2 * ln(N_effective) / SR_target^2

A backtest window that doesn't satisfy this is statistically incapable
of clearing DSR at SR_target given N_effective accumulated trial count
— no matter how clean the measurement. Per the dev: *"You cannot
out-discipline a too-short data window."*

Before T-082b activated the extended substrate (commit eb90d23 +
follow-on swap), the project's 5-year window failed this check at
N=100/SR=1.0 (MBL = 9.2 yr required). Now that the substrate spans
30-60 years for the surviving universe, the gate is passable for the
first time and the project should ENFORCE it on every backtest.

This module is the standalone implementation. Discovery gauntlet wires
it as Gate 0 (pre-flight). Agents can also use it directly when
evaluating campaign feasibility.

Public API
----------
- `compute_n_effective(db_path)`: query run_registry for honest N
- `compute_mbl_min(n_effective, sr_target)`: the math
- `check_mbl_gate(t_years, n_effective=None, sr_target=1.0)`: full check
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data/observability/run_registry.sqlite"


def compute_mbl_min(n_effective: int, sr_target: float = 1.0) -> float:
    """Bailey-Borwein-López de Prado-Zhu (2014) Minimum Backtest Length.

        T_years >= 2 * ln(N_effective) / SR_target^2

    At N_effective = 1 (no multiple-testing accumulation), ln(1) = 0 →
    MBL = 0. At N_effective = 100 trials, SR_target = 1.0 → 9.2 years.
    At N_effective = 1000 trials, SR_target = 1.0 → 13.8 years.

    Raises:
        ValueError if n_effective < 1 or sr_target <= 0.
    """
    if n_effective < 1:
        raise ValueError(f"n_effective must be >= 1, got {n_effective}")
    if sr_target <= 0:
        raise ValueError(f"sr_target must be > 0, got {sr_target}")
    if n_effective == 1:
        return 0.0
    return 2.0 * math.log(n_effective) / (sr_target ** 2)


def compute_n_effective(
    db_path: Path = DEFAULT_DB_PATH,
    since_iso: Optional[str] = None,
) -> int:
    """Query the run registry for honest N = count of distinct backtest configs.

    Returns 1 if the registry doesn't exist (treats as "no prior trials"),
    making this safe to call during bootstrap / fresh-environment scenarios.

    `since_iso`: if set, only count runs at-or-after this date. Useful
    for "trials within this measurement campaign" vs "total project N".

    What constitutes a "distinct configuration" is project-policy:
    every row in `runs` is one backtest execution → one trial. The
    schema currently stores run_id + snapshot_at + (sharpe, ...). PCA-
    reduction for correlated trials is a future refinement (per the dev
    review); for now, raw count is the honest-upper-bound estimate.
    """
    if not db_path.exists():
        return 1
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        if since_iso:
            cur = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE snapshot_at >= ?",
                (since_iso,),
            )
        else:
            cur = conn.execute("SELECT COUNT(*) FROM runs")
        n = cur.fetchone()[0]
        return max(1, int(n))
    finally:
        conn.close()


def check_mbl_gate(
    t_years: float,
    n_effective: Optional[int] = None,
    sr_target: float = 1.0,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict:
    """Run the MBL Gate-0 check. Returns a verdict dict.

    Args:
        t_years: backtest window length in years (end_date - start_date)
        n_effective: honest trial count. If None, query run_registry.
        sr_target: target Sharpe (dev spec default = 1.0)

    Returns dict with keys:
        passed: bool — whether the gate is satisfied
        t_years: float — the input
        mbl_min: float — required minimum
        n_effective: int — trial count used
        sr_target: float — target Sharpe used
        margin_years: float — t_years - mbl_min (positive = pass headroom,
                              negative = how far under-powered)
        reason: str — human-readable verdict
    """
    if n_effective is None:
        n_effective = compute_n_effective(db_path)
    mbl_min = compute_mbl_min(n_effective, sr_target)
    margin = t_years - mbl_min
    passed = margin >= 0.0
    if passed:
        reason = (
            f"PASS: T_years={t_years:.2f} >= MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective}, SR_target={sr_target}, margin={margin:+.2f}yr)"
        )
    else:
        reason = (
            f"FAIL: T_years={t_years:.2f} < MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective}, SR_target={sr_target}, short by {-margin:.2f}yr). "
            f"Backtest is statistically under-powered to clear DSR — "
            f"per CLAUDE.md #7, no deployment decision is valid until the "
            f"window extends or N_effective decreases."
        )
    return {
        "passed": passed,
        "t_years": float(t_years),
        "mbl_min": float(mbl_min),
        "n_effective": int(n_effective),
        "sr_target": float(sr_target),
        "margin_years": float(margin),
        "reason": reason,
    }


def years_from_window(start_date: str, end_date: str) -> float:
    """Convert ISO date strings (YYYY-MM-DD) to a year-fraction window length."""
    from datetime import datetime
    s = datetime.fromisoformat(start_date)
    e = datetime.fromisoformat(end_date)
    return (e - s).days / 365.25
