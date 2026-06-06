"""
tests/test_regime_transition_overlay_t118.py
============================================
Unit tests for the T-118 HMM transition-trigger gross-exposure overlay.

These test the stateful trigger/hysteresis LOGIC in isolation (no
backtest): de-gross on an upward Delta transition, asymmetric (slower)
re-gross, idempotency within a bar, disabled no-op, and graceful
posterior extraction. The canon-md5 inertness of the default-OFF path is
proven separately via scripts/run_isolated (see the T-118 audit doc).
"""
import pandas as pd

from engines.engine_b_risk.regime_transition_overlay import (
    RegimeOverlayConfig,
    RegimeTransitionOverlay,
)


def _ts(i: int):
    return pd.Timestamp("2022-01-01") + pd.Timedelta(days=i)


def test_disabled_is_strict_noop():
    ov = RegimeTransitionOverlay(RegimeOverlayConfig(enabled=False, degross_level=0.0))
    # Even a huge posterior jump must not arm or change the multiplier.
    for i, p in enumerate([0.0, 0.1, 0.9, 1.0, 1.0]):
        assert ov.observe(_ts(i), p) == 1.0
    assert ov.current_multiplier() == 1.0
    assert ov.armed is False


def test_degross_fires_on_upward_delta():
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=0.5, k_days=3,
        degross_delta=0.40, regross_level=0.30, regross_bars=5,
    )
    ov = RegimeTransitionOverlay(cfg)
    # Benign for k bars, then a sharp rise: Delta over 3 bars = 0.9-0.1 = 0.8 >= 0.40.
    seq = [0.10, 0.10, 0.10, 0.10, 0.90]
    mults = [ov.observe(_ts(i), p) for i, p in enumerate(seq)]
    # Not enough history until index 3 (k+1=4 samples); arming on the jump at idx 4.
    assert mults[-1] == 0.5
    assert ov.armed is True


def test_no_fire_when_delta_below_threshold():
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=0.5, k_days=3,
        degross_delta=0.40, regross_level=0.30, regross_bars=5,
    )
    ov = RegimeTransitionOverlay(cfg)
    # Slow drift: each 3-bar Delta stays < 0.40.
    seq = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
    mults = [ov.observe(_ts(i), p) for i, p in enumerate(seq)]
    assert all(m == 1.0 for m in mults)
    assert ov.armed is False


def test_asymmetric_regross_is_slower():
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=0.0, k_days=2,
        degross_delta=0.40, regross_level=0.30, regross_bars=3,
    )
    ov = RegimeTransitionOverlay(cfg)
    # Arm via a jump.
    for i, p in enumerate([0.10, 0.10, 0.90]):
        ov.observe(_ts(i), p)
    assert ov.armed is True
    # Calm but NOT yet for n_off=3 consecutive bars -> stays armed.
    ov.observe(_ts(3), 0.20)   # calm 1
    ov.observe(_ts(4), 0.20)   # calm 2
    assert ov.armed is True
    # A non-calm bar RESETS the calm counter (whipsaw guard).
    ov.observe(_ts(5), 0.50)   # not calm -> reset
    assert ov.armed is True
    ov.observe(_ts(6), 0.20)   # calm 1
    ov.observe(_ts(7), 0.20)   # calm 2
    ov.observe(_ts(8), 0.20)   # calm 3 -> disarm
    assert ov.armed is False
    assert ov.current_multiplier() == 1.0


def test_idempotent_within_bar():
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=0.5, k_days=2,
        degross_delta=0.40, regross_level=0.30, regross_bars=3,
    )
    ov = RegimeTransitionOverlay(cfg)
    ov.observe(_ts(0), 0.10)
    ov.observe(_ts(1), 0.10)
    # Same timestamp called many times (multiple tickers) must not advance state.
    first = ov.observe(_ts(2), 0.90)
    for _ in range(5):
        again = ov.observe(_ts(2), 0.90)  # repeated same-bar calls
        assert again == first
    # Buffer advanced exactly once for ts2: Delta = 0.90-0.10 = 0.80 -> armed.
    assert ov.armed is True


def test_degross_level_zero_flattens_target():
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=0.0, k_days=2,
        degross_delta=0.40, regross_level=0.30, regross_bars=3,
    )
    ov = RegimeTransitionOverlay(cfg)
    for i, p in enumerate([0.10, 0.10, 0.90]):
        ov.observe(_ts(i), p)
    assert ov.armed is True
    assert ov.current_multiplier() == 0.0  # target_notional *= 0 -> rebalance to flat


def test_level_one_is_neutral_null_arm():
    # degross_level=1.0 means "armed" but multiplier is 1.0 -> a placebo arm.
    cfg = RegimeOverlayConfig(
        enabled=True, degross_level=1.0, k_days=2,
        degross_delta=0.40, regross_level=0.30, regross_bars=3,
    )
    ov = RegimeTransitionOverlay(cfg)
    mults = [ov.observe(_ts(i), p) for i, p in enumerate([0.10, 0.10, 0.90, 1.0])]
    assert ov.armed is True          # the trigger fired ...
    assert all(m == 1.0 for m in mults)  # ... but applied multiplier is neutral


def test_combined_posterior_extraction_failsafe():
    f = RegimeTransitionOverlay.combined_posterior
    assert f(None) == 0.0
    assert f({}) == 0.0
    assert f({"hmm_regime": None}) == 0.0
    assert f({"hmm_regime": {"probabilities": {}}}) == 0.0
    got = f({"hmm_regime": {"probabilities": {"crisis": 0.3, "stressed": 0.5, "benign": 0.2}}})
    assert abs(got - 0.8) < 1e-12
    # Malformed values degrade to 0.0, never raise.
    assert f({"hmm_regime": {"probabilities": {"crisis": "x", "stressed": 0.5}}}) == 0.0
