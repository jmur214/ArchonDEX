"""core.measurement — backtest validity + DSR-precondition gates."""
from core.measurement.mbl_gate import (
    check_mbl_gate,
    compute_mbl_min,
    compute_n_effective,
    years_from_window,
)

__all__ = [
    "check_mbl_gate",
    "compute_mbl_min",
    "compute_n_effective",
    "years_from_window",
]
