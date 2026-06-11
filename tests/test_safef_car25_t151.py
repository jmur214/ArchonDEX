# tests/test_safef_car25_t151.py
"""T-151 — safe-f / CAR25 (Bandy) tests.

MC determinism (seed-pinned resample matrix), tolerance monotonicity,
the exact half-vol ⇒ double-safe_f scaling identity (same paths, so it
holds to bisection tolerance), degenerate inputs, diagnostics-at-f1,
and the additive producer emission (JSON-safe, contract suite covers
the key set).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from backtester.safef_car25 import SafeFConfig, compute_safef_car25


def _returns(seed=0, n=750, mu=0.0006, sigma=0.012) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2022-01-03", periods=n)
    return pd.Series(rng.normal(mu, sigma, n), index=idx)


class TestDeterminism:
    def test_repeat_calls_bitwise_identical(self):
        r = _returns()
        a = compute_safef_car25(r, SafeFConfig())
        b = compute_safef_car25(r, SafeFConfig())
        assert a == b

    def test_seed_changes_result(self):
        r = _returns()
        a = compute_safef_car25(r, SafeFConfig(seed=0))
        b = compute_safef_car25(r, SafeFConfig(seed=1))
        # different resample paths ⇒ (almost surely) different safe_f
        assert a["safe_f"] != b["safe_f"] or a["car25_pct"] != b["car25_pct"]


class TestMonotonicity:
    def test_higher_dd_tolerance_raises_safe_f(self):
        r = _returns()
        fs = [
            compute_safef_car25(r, SafeFConfig(dd_tolerance=t))["safe_f"]
            for t in (0.10, 0.20, 0.30)
        ]
        assert fs[0] <= fs[1] <= fs[2]
        assert fs[0] < fs[2]

    def test_higher_dd_probability_raises_safe_f(self):
        r = _returns()
        fs = [
            compute_safef_car25(r, SafeFConfig(dd_probability=p))["safe_f"]
            for p in (0.01, 0.05, 0.20)
        ]
        assert fs[0] <= fs[1] <= fs[2]

    def test_half_vol_returns_double_safe_f(self):
        # exceedance(f, r/2) == exceedance(f/2, r) on the SAME resample
        # paths, so safe_f scales exactly (to bisection tolerance,
        # unless capped by f_max).
        r = _returns()
        cfg = SafeFConfig(f_max=20.0)
        full = compute_safef_car25(r, cfg)["safe_f"]
        half = compute_safef_car25(r / 2.0, cfg)["safe_f"]
        assert half == pytest.approx(2.0 * full, abs=4 * cfg.f_tol)


class TestDegenerateInputs:
    def test_short_history_skips(self):
        out = compute_safef_car25(_returns(n=60))
        assert out["safe_f"] is None
        assert out["skip_reason"] == "insufficient_history"

    def test_empty_series_skips(self):
        out = compute_safef_car25(pd.Series(dtype=float))
        assert out["skip_reason"] == "insufficient_history"

    def test_nonnegative_returns_cap_at_f_max(self):
        r = pd.Series(np.full(300, 0.001))
        out = compute_safef_car25(r, SafeFConfig(f_max=5.0))
        assert out["safe_f"] == 5.0
        assert out["skip_reason"] == "degenerate_nonnegative_returns"

    def test_nan_laden_series_cleaned(self):
        r = _returns(n=400)
        r.iloc[::5] = np.nan
        out = compute_safef_car25(r)
        assert out["safe_f"] is not None
        assert out["n_obs"] == 320

    def test_brutal_returns_give_small_safe_f(self):
        r = _returns(mu=-0.001, sigma=0.04)   # nasty record
        out = compute_safef_car25(r)
        assert out["safe_f"] is not None and out["safe_f"] < 1.0
        assert out["headroom"] < 0.0          # the OVERSIZED diagnostic


class TestDiagnosticsAndShape:
    def test_f1_diagnostics_and_headroom(self):
        out = compute_safef_car25(_returns())
        assert out["prob_dd_at_f1"] is not None
        assert out["mdd95_at_f1_pct"] is not None
        assert out["car25_at_f1_pct"] is not None
        assert out["headroom"] == pytest.approx(out["safe_f"] - 1.0, abs=1e-9)
        assert out["config"]["dd_tolerance"] == 0.20

    def test_output_json_native(self):
        json.dumps(compute_safef_car25(_returns()))


class TestProducerEmission:
    def test_summary_carries_safef_keys(self, tmp_path):
        rng = np.random.default_rng(7)
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
        assert "safe_f" in s and "car25_pct" in s and "safef_detail" in s
        assert isinstance(s["safef_detail"], dict)
        assert s["safef_detail"]["skip_reason"] in (None,
                                                    "insufficient_history")
        json.dumps(m.summary_metrics())
