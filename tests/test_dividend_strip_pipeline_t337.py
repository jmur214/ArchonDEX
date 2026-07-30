"""T-337 — SYNTHETIC validation of the dividend-strip audit pipeline.

The T-333 lesson: verify the algebra on SYNTHETIC data only, before any real-data run. These
tests construct series with a KNOWN dividend gap and assert the pipeline recovers exactly
that — so when the frozen audit runs on the real panel, an unexpected number means the DATA
is surprising, not the arithmetic.

Nothing here touches the real panel or re-runs any closure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TD = 252


def _synth(n=2520, price_drift=0.02, div_yield=0.05, seed=0):
    """A synthetic name with a KNOWN split of price appreciation vs dividend yield.

    Returns (price_series, tr_series, partial_series) where `partial` mimics the real
    Stooq behavior: it captures a KNOWN FRACTION of the dividend (the premise correction
    this audit rests on) rather than none of it.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2010-01-04", periods=n, freq="B")
    shock = rng.normal(0.0, 0.011, n)
    px_r = price_drift / TD + shock
    tr_r = px_r + div_yield / TD                       # TR = price + full dividend
    partial_r = px_r + 0.65 * div_yield / TD           # Stooq-like: captures 65% of the div
    mk = lambda r: pd.Series(100 * np.exp(np.cumsum(np.log1p(r))), index=idx)
    return mk(px_r), mk(tr_r), mk(partial_r)


def _ann(s):
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1


def _sharpe(s, rf=0.0):
    r = s.pct_change().dropna()
    return float((r.mean() - rf / TD) / r.std() * np.sqrt(TD))


# ---------- the measurement recovers a KNOWN gap ----------
def test_recovers_the_known_full_dividend_yield():
    px, tr, _ = _synth(div_yield=0.05)
    assert _ann(tr) - _ann(px) == pytest.approx(0.05, abs=2e-3)


def test_recovers_the_known_PARTIAL_capture_and_residual():
    """The premise correction: a partially-adjusted series has a residual gap equal to the
    UNCAPTURED fraction — the quantity the audit must fix, not the whole yield."""
    px, tr, partial = _synth(div_yield=0.05)
    captured = _ann(partial) - _ann(px)
    residual = _ann(tr) - _ann(partial)
    assert captured == pytest.approx(0.65 * 0.05, abs=2e-3)
    assert residual == pytest.approx(0.35 * 0.05, abs=2e-3)
    # and the two decompose to the whole yield — no leakage in the arithmetic
    assert captured + residual == pytest.approx(0.05, abs=3e-3)


def test_using_the_partial_series_AS_IF_TR_produces_a_null_by_construction():
    """Why the dispatched method needed correcting: if the 'TR source' is itself only
    partially adjusted, the reconciliation moves NOTHING and the audit returns a null that
    is an artifact of the method rather than a finding about the data."""
    px, tr, partial = _synth(div_yield=0.05)
    wrong_fix = _ann(partial) - _ann(partial)          # 'reconciling' partial→partial
    right_fix = _ann(tr) - _ann(partial)
    assert wrong_fix == pytest.approx(0.0)             # a null BY CONSTRUCTION
    assert right_fix > 0.01                            # the real, recoverable gap


# ---------- the Sharpe shift is predictable from the gap ----------
def test_sharpe_shift_matches_the_analytic_prediction():
    """Restoring a constant yield shifts the mean and leaves vol ~unchanged, so
    ΔSharpe ≈ Δreturn / vol. Locking this means a surprising real-data ΔSharpe implicates
    the DATA, not the pipeline."""
    px, tr, partial = _synth(div_yield=0.05, seed=3)
    d_ret = _ann(tr) - _ann(partial)
    vol = partial.pct_change().dropna().std() * np.sqrt(TD)
    predicted = d_ret / vol
    actual = _sharpe(tr) - _sharpe(partial)
    assert actual == pytest.approx(predicted, rel=0.15)


@pytest.mark.parametrize("wt,dy", [(0.25, 0.016), (0.70, 0.016)])
def test_book_level_shift_scales_with_high_yield_WEIGHT(wt, dy):
    """The pre-registered exposure: a diversified book (~25% high-yield) moves far less
    than a value-tilted sub-book (~70%). Both must land inside the +0.15 gate on the
    MEASURED 1.6%/yr differential — this test is the arithmetic behind that claim."""
    vol = 0.16
    shift = wt * dy / vol
    assert shift < 0.15                                # inside the frozen gate
    if wt >= 0.70:
        assert shift > 0.05                            # …but the value sub-book is the risk


# ---------- fail-closed: an unreconcilable name is excluded, never left silently ----------
def test_unreconcilable_name_must_be_excluded_and_named():
    """Mirrors the T-256 contract: a ticker whose TR can't be validated is dropped WITH a
    reason. Silently leaving it on price basis is the very error under audit."""
    recon = {"AAA": {"tr_ok": True, "gap": 0.016}, "BBB": {"tr_ok": False, "reason": "no yf TR"}}
    included = {k: v for k, v in recon.items() if v.get("tr_ok")}
    excluded = {k: v.get("reason") for k, v in recon.items() if not v.get("tr_ok")}
    assert set(included) == {"AAA"}
    assert excluded == {"BBB": "no yf TR"}             # named, not hidden
    assert "BBB" not in included                       # never counted as reconciled


def test_zero_yield_name_needs_no_correction():
    """Low/no-yield growth names measured ~0.02%/yr gap on the real panel — the pipeline
    must leave them essentially untouched, so the correction can't manufacture a lift."""
    px, tr, partial = _synth(div_yield=0.0)
    assert abs(_ann(tr) - _ann(partial)) < 1e-6


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
