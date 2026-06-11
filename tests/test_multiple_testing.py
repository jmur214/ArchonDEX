"""Tests for core/multiple_testing.py (T-149 Part A)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.multiple_testing import romano_wolf_stepm, spa_test


def _series_panel(n_days=1500, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-01", periods=n_days, freq="B")
    return idx, rng


def test_stepm_all_null_no_survivors():
    """A pure-noise family must produce no survivors (seeded, deterministic)."""
    idx, rng = _series_panel()
    fam = {f"m{i}": pd.Series(rng.normal(0, 1e-3, len(idx)), index=idx)
           for i in range(8)}
    out = romano_wolf_stepm(fam, b=300, seed=0)
    assert out["survivors_fwer05"] == []


def test_stepm_strong_signal_found():
    """An injected strong-mean member must survive; nulls must not."""
    idx, rng = _series_panel()
    fam = {f"null{i}": pd.Series(rng.normal(0, 1e-3, len(idx)), index=idx)
           for i in range(5)}
    fam["signal"] = pd.Series(rng.normal(3e-4, 1e-3, len(idx)), index=idx)
    out = romano_wolf_stepm(fam, b=300, seed=0)
    assert "signal" in out["survivors_fwer05"]
    assert all(s == "signal" for s in out["survivors_fwer05"])


def test_stepm_single_hypothesis_matches_plain_t():
    """With one member, survival should track the plain |t| vs the null max
    (which IS that member's bootstrap |t| distribution)."""
    idx, rng = _series_panel()
    strong = pd.Series(rng.normal(4e-4, 1e-3, len(idx)), index=idx)
    out = romano_wolf_stepm({"only": strong}, b=300, seed=0)
    assert out["survivors_fwer05"] == ["only"]
    draw = rng.normal(0, 1e-3, len(idx))
    weak = pd.Series(draw - draw.mean(), index=idx)  # exactly-zero mean → t=0
    out2 = romano_wolf_stepm({"only": weak}, b=300, seed=0)
    assert out2["survivors_fwer05"] == []


def test_stepm_deterministic():
    idx, rng = _series_panel()
    fam = {f"m{i}": pd.Series(rng.normal(0, 1e-3, len(idx)), index=idx)
           for i in range(4)}
    a = romano_wolf_stepm(fam, b=200, seed=0)
    b = romano_wolf_stepm(fam, b=200, seed=0)
    assert a == b


def test_spa_better_model_rejects():
    idx, rng = _series_panel()
    diff = pd.Series(rng.normal(4e-4, 1e-3, len(idx)), index=idx)  # model wins
    out = spa_test({"gbm_minus_ridge": diff}, b=300, seed=0)
    assert out["rejects_h0_at_05"] is True
    assert out["spa_p_value"] < 0.05


def test_spa_equal_model_does_not_reject():
    idx, rng = _series_panel()
    diff = pd.Series(rng.normal(0.0, 1e-3, len(idx)), index=idx)   # no edge
    out = spa_test({"gbm_minus_ridge": diff}, b=300, seed=0)
    assert out["rejects_h0_at_05"] is False


def test_spa_family_max_uses_best_model():
    idx, rng = _series_panel()
    out = spa_test({
        "bad": pd.Series(rng.normal(-2e-4, 1e-3, len(idx)), index=idx),
        "good": pd.Series(rng.normal(4e-4, 1e-3, len(idx)), index=idx),
    }, b=300, seed=0)
    assert out["t_max_observed"] == max(out["t_per_model"].values())
    assert out["rejects_h0_at_05"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
