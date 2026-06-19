"""T-211 — Phase-1 composition tests (post director-review FIX 1 + FIX 2).

FIX 1 — the overlay CONSUMES core.trend_overlay.TrendOverlay on E/T-204's STOOQ
substrate (no inline reimplementation, no data/processed price-source mismatch).
FIX 2 — the defensive screens are MONTHLY-cached with a TRAILING-month-end causal
key (BAR B, a declared change), and the composition is FAIL-CLOSED in measured mode.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_c_portfolio import phase1_composition as P  # noqa: E402


# --------------------------------------------------------------------------- #
# FIX 1 — consume the validated TrendOverlay on its validated substrate
# --------------------------------------------------------------------------- #
def test_overlay_consumes_trendoverlay_no_inline_sma():
    import inspect
    src = inspect.getsource(P._overlay_series)
    assert "TrendOverlay" in src                 # consumes the validated component
    assert "rolling(" not in src                 # no inline SMA reimplementation
    assert "data/processed" not in src and "PROCESSED" not in src


def test_overlay_degrosses_in_crises_from_stooq():
    # full STOOQ history (incl. GLD pre-2020) → EW SPY/AGG/GLD long/flat
    assert P._overlay_series(105, ("SPY", "AGG", "GLD")) is not None
    assert P._trend_exposure(pd.Timestamp("2008-10-15"), 105, ("SPY", "AGG", "GLD")) == 0.0
    assert P._trend_exposure(pd.Timestamp("2020-03-23"), 105, ("SPY", "AGG", "GLD")) == 0.0


def test_overlay_matches_trendoverlay_component_exactly():
    # the composition's per-asset signal IS TrendOverlay.exposure(close).shift(1)
    from core.trend_overlay import TrendOverlay
    close = P._load_stooq_close(P._STOOQ_PATHS["SPY"])
    direct = TrendOverlay(105, enabled=True).exposure(close).shift(1)
    ew = P._overlay_series(105, ("SPY",))   # single asset → equals the direct signal
    aligned = pd.concat({"a": direct, "b": ew}, axis=1).dropna()
    assert np.allclose(aligned["a"].values, aligned["b"].values)


# --------------------------------------------------------------------------- #
# FIX 2 — monthly cache causality + fail-closed
# --------------------------------------------------------------------------- #
def test_trailing_month_key_is_causal():
    # key = the LAST COMPLETED month before now's month; asof <= now
    for d in ("2008-03-15", "2020-01-02", "2012-12-31"):
        mk, asof = P._trailing_month_asof(pd.Timestamp(d))
        assert asof <= pd.Timestamp(d)                      # never future-leak
        assert asof.to_period("M") < pd.Timestamp(d).to_period("M")  # strictly prior month


def test_monthly_cache_is_stable_within_a_month():
    P._SCREEN_CACHE.clear()
    idx = pd.bdate_range("2008-01-01", "2008-03-20")
    pdat = {"AAPL": pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx)}
    a = P._cached_defensive_screens(pdat, pd.Timestamp("2008-03-05"))
    b = P._cached_defensive_screens(pdat, pd.Timestamp("2008-03-25"))
    assert a is b                                           # same trailing month → one compute


def test_fail_closed_in_measured_mode(monkeypatch):
    from core.measured import MeasurementHalt
    monkeypatch.setenv("ARCHONDEX_MEASURED", "1")
    idx = pd.bdate_range("2008-01-01", "2008-10-15")
    pdat = {"AAPL": pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx)}
    with pytest.raises(MeasurementHalt):
        P.apply_phase1_composition({"AAPL": 0.3}, pdat, pd.Timestamp("2008-10-15"),
                                   trend_assets=("NONEXIST",))   # missing overlay → HALT


def test_fail_open_outside_measured_mode():
    # ensure not measured
    os.environ.pop("ARCHONDEX_MEASURED", None)
    idx = pd.bdate_range("2008-01-01", "2008-10-15")
    pdat = {"AAPL": pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx)}
    w = {"AAPL": 0.3}
    out = P.apply_phase1_composition(w, pdat, pd.Timestamp("2008-10-15"), trend_assets=("NONEXIST",))
    assert out == w                                          # fails open (unmodified), no raise


def test_composition_degrosses_to_cash_in_gfc():
    os.environ.pop("ARCHONDEX_MEASURED", None)
    idx = pd.bdate_range("2008-01-01", "2008-10-15")
    pdat = {"AAPL": pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx)}
    out = P.apply_phase1_composition({"AAPL": 0.3, "MSFT": 0.2}, pdat, pd.Timestamp("2008-10-15"))
    assert all(abs(v) < 1e-9 for v in out.values())          # overlay 0.0 → full cash


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
