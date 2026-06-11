# tests/test_divergence_monitors_t152.py
"""T-152 — CUSUM / Page-Hinkley divergence monitor tests.

Detection on injected breaks, near-quiet on the iid null at the
calibrated operating points, streaming==batch equivalence (the paper-
loop contract), determinism, σ-guard degenerates, lookahead-free
standardization, and the additive shadow-report emission.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from backtester.divergence_monitors import (
    CusumMonitor,
    PageHinkleyMonitor,
    run_monitor,
    shadow_report,
    standardized_innovations,
)

OP_CUSUM = dict(k=1.0, h=5.0)        # T-152 calibrated operating points
OP_PH = dict(delta=0.05, lam=20.0)


def _null_z(seed=0, n=1000) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0, 1.0, n),
                     index=pd.bdate_range("2020-01-02", periods=n))


class TestDetection:
    def test_cusum_detects_large_mean_break(self):
        z = _null_z()
        z.iloc[500:] -= 1.5          # a 1.5σ daily mean shift
        rep = run_monitor(z, CusumMonitor(**OP_CUSUM))
        assert rep["n_alarms"] >= 1
        assert rep["alarm_dates"][0] >= str(z.index[500].date())

    def test_ph_detects_large_mean_break(self):
        z = _null_z(seed=1)
        z.iloc[500:] -= 1.5
        rep = run_monitor(z, PageHinkleyMonitor(**OP_PH))
        assert rep["n_alarms"] >= 1

    def test_cusum_two_sided(self):
        z_up = _null_z(seed=2)
        z_up.iloc[500:] += 1.5       # upward break must also alarm
        assert run_monitor(z_up, CusumMonitor(**OP_CUSUM))["n_alarms"] >= 1

    def test_variance_channel_detects_vol_doubling(self):
        rng = np.random.default_rng(3)
        z = np.concatenate([rng.normal(0, 1, 500), rng.normal(0, 2, 200)])
        zv = pd.Series((z ** 2 - 1.0) / np.sqrt(2.0),
                       index=pd.bdate_range("2020-01-02", periods=700))
        rep = run_monitor(zv, CusumMonitor(2.0, 12.0))   # var operating point
        assert rep["n_alarms"] >= 1
        assert rep["alarm_dates"][0] >= str(zv.index[500].date())


class TestNullQuiet:
    def test_cusum_near_quiet_on_iid_null(self):
        # ~4 years of iid null: expect ≈0-4 alarms at ~1/yr calibration.
        rep = run_monitor(_null_z(seed=4, n=1008), CusumMonitor(**OP_CUSUM))
        assert rep["alarms_per_year"] <= 2.0

    def test_ph_near_quiet_on_iid_null(self):
        rep = run_monitor(_null_z(seed=5, n=1008), PageHinkleyMonitor(**OP_PH))
        assert rep["alarms_per_year"] <= 2.0


class TestStreamingContract:
    def test_streaming_equals_batch(self):
        z = _null_z(seed=6, n=600)
        z.iloc[300:] -= 1.0
        batch = run_monitor(z, CusumMonitor(**OP_CUSUM))
        m = CusumMonitor(**OP_CUSUM)
        incremental = [str(ts.date()) for ts, v in z.items() if m.update(float(v))]
        assert batch["alarm_dates"] == incremental
        assert batch["n_alarms"] == m.n_alarms

    def test_ph_streaming_equals_batch(self):
        z = _null_z(seed=7, n=600)
        z.iloc[300:] += 1.2
        batch = run_monitor(z, PageHinkleyMonitor(**OP_PH))
        m = PageHinkleyMonitor(**OP_PH)
        incremental = [str(ts.date()) for ts, v in z.items() if m.update(float(v))]
        assert batch["alarm_dates"] == incremental


class TestDeterminismAndGuards:
    def test_repeat_runs_identical(self):
        z = _null_z(seed=8)
        a = run_monitor(z, CusumMonitor(**OP_CUSUM))
        b = run_monitor(z, CusumMonitor(**OP_CUSUM))
        assert a == b

    def test_nan_observations_skipped(self):
        m = CusumMonitor(**OP_CUSUM)
        assert m.update(float("nan")) is False
        assert m.s_pos == 0.0 and m.s_neg == 0.0

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            CusumMonitor(k=-0.1, h=4.0)
        with pytest.raises(ValueError):
            CusumMonitor(k=0.5, h=0.0)
        with pytest.raises(ValueError):
            PageHinkleyMonitor(delta=0.05, lam=0.0)

    def test_standardization_is_lagged_no_lookahead(self):
        # A huge spike at t must NOT shrink its own z via same-day σ:
        # stats through t−1 standardize r_t.
        r = pd.Series(np.full(100, 0.001),
                      index=pd.bdate_range("2024-01-02", periods=100))
        r.iloc[80] = 0.20
        z = standardized_innovations(r, window=60, min_periods=20)
        # constant pre-history has ~0 std → those obs are σ-guarded out;
        # the spike day must survive standardized by PRE-spike stats only
        # if pre-stats were valid — construct valid pre-stats instead:
        rng = np.random.default_rng(9)
        r2 = pd.Series(rng.normal(0.0005, 0.01, 100),
                       index=pd.bdate_range("2024-01-02", periods=100))
        r2.iloc[80] = 0.20
        z2 = standardized_innovations(r2, window=60, min_periods=20)
        spike_z = z2.loc[r2.index[80]]
        assert spike_z > 10  # ~20σ on pre-spike vol; same-day σ would shrink it

    def test_sigma_guard_drops_flat_history(self):
        r = pd.Series(np.zeros(200),
                      index=pd.bdate_range("2024-01-02", periods=200))
        z = standardized_innovations(r)
        assert len(z) == 0  # never divides by ~0


class TestShadowReport:
    def test_shadow_report_shape_and_json(self):
        rng = np.random.default_rng(10)
        r = pd.Series(rng.normal(0.0004, 0.01, 400),
                      index=pd.bdate_range("2023-01-02", periods=400))
        rep = shadow_report(r)
        assert isinstance(rep["divergence_alarms"], int)
        d = rep["divergence_detail"]
        assert d["skip_reason"] is None
        for ch in ("cusum_mean", "cusum_var", "page_hinkley"):
            assert d[ch]["n_obs"] > 0
        json.dumps(rep)

    def test_shadow_report_short_history_skips(self):
        rep = shadow_report(pd.Series([0.001] * 10))
        assert rep["divergence_alarms"] is None
        assert rep["divergence_detail"]["skip_reason"] == "insufficient_history"

    def test_summary_carries_divergence_keys(self, tmp_path):
        rng = np.random.default_rng(11)
        n = 300
        equity = 100_000.0 * np.cumprod(1.0 + rng.normal(0.0004, 0.01, n))
        snaps = pd.DataFrame({
            "timestamp": pd.bdate_range("2024-01-02", periods=n).astype(str),
            "equity": equity,
        })
        sp = tmp_path / "snaps.csv"
        snaps.to_csv(sp, index=False)
        from cockpit.metrics import PerformanceMetrics
        m = PerformanceMetrics(snapshots_path=str(sp), trades_path=None)
        s = m.summary()
        assert "divergence_alarms" in s and "divergence_detail" in s
        assert isinstance(s["divergence_detail"], dict)
        json.dumps(m.summary_metrics())
