"""
tests/test_vol_estimator_fix_t153.py
====================================
T-2026-06-11-153 — unit tests for the vol-estimator collapse fixes:
Fix A (sigma-floor guard) + Fix B (Yang-Zhang estimator option).

The load-bearing case is the COLLAPSE FIXTURE: a quiet stretch where the
EWMA recursion decays to a tiny-but-positive sigma that sails past the
`<= 0` guard and pins the requested leverage at the ceiling — the state
D's T-150 measured and the T-153 assessment found on 14% of canonical
26-yr bars. The guard must catch it; YZ must read sane vol on the same
kind of tape (flat closes, live ranges); and every default path must be
bit-identical to pre-T-153 behavior.
"""
import numpy as np
import pandas as pd
import pytest

from engines.engine_b_risk.vol_target import (
    VolTargetConfig,
    apply_vol_floor,
    compute_portfolio_vol_scale,
    compute_realized_vol_from_history_ewma,
)
from engines.engine_b_risk.yz_vol import portfolio_yang_zhang_vol, yang_zhang_vol


def _history_from_returns(returns, start_equity=100_000.0):
    """Build a snapshot-history list from a daily return sequence."""
    eq = start_equity
    hist = [{"timestamp": pd.Timestamp("2020-01-01"), "equity": eq}]
    for i, r in enumerate(returns):
        eq *= 1.0 + r
        hist.append({"timestamp": pd.Timestamp("2020-01-01") + pd.Timedelta(days=i + 1),
                     "equity": eq})
    return hist


# --------------------------------------------------------------------- #
# The collapse fixture
# --------------------------------------------------------------------- #

def _collapse_history():
    """30 normal-vol days, then 250 near-flat days (r = 1e-6).

    The EWMA recursion decays the normal-vol variance by 0.94^250 ≈ 2e-7
    while the quiet returns contribute ~1e-12 — sigma lands ~1e-4
    annualized: tiny-but-POSITIVE, so the `<= 0` guard does NOT fire —
    the exact over-lever state from the T-153 assessment (min observed
    3e-06).
    """
    rng = np.random.RandomState(7)
    normal = rng.normal(0.0, 0.01, 30).tolist()
    quiet = [1e-6] * 250
    return _history_from_returns(normal + quiet)


def test_ewma_collapses_to_tiny_positive_sigma():
    hist = _collapse_history()
    sigma = compute_realized_vol_from_history_ewma(hist, ewma_lambda=0.94,
                                                   min_returns_required=60)
    assert sigma is not None
    assert 0.0 < sigma < 0.001  # collapsed: < 0.1% annualized — garbage


def test_collapse_pins_ceiling_without_guard():
    hist = _collapse_history()
    cfg = VolTargetConfig(enabled=True, estimator_type="ewma",
                          min_returns_required=60)
    scale = compute_portfolio_vol_scale(hist, cfg)
    assert scale == cfg.leverage_ceiling  # 2.0x requested off a garbage sigma


def test_floor_guard_catches_collapse():
    hist = _collapse_history()
    cfg = VolTargetConfig(enabled=True, estimator_type="ewma",
                          min_returns_required=60,
                          vol_floor_enabled=True, vol_floor_annual=0.02)
    scale = compute_portfolio_vol_scale(hist, cfg)
    # floored sigma = 0.02 -> raw = 0.10/0.02 = 5 -> still ceiling-clipped,
    # BUT with a tighter floor relative to the fixture's real vol the
    # request is now driven by the floor, not the garbage estimate.
    # Use the relative floor to assert the meaningful contraction:
    cfg2 = VolTargetConfig(enabled=True, estimator_type="ewma",
                           min_returns_required=60,
                           vol_floor_enabled=True, vol_floor_annual=0.02,
                           vol_floor_full_sample_frac=1.0)
    scale2 = compute_portfolio_vol_scale(hist, cfg2)
    # full-sample sigma of the fixture ≈ 0.075 annualized -> floor ≈ 0.075
    # -> raw = 0.10/0.075 ≈ 1.33 -> NOT ceiling-pinned.
    assert scale == cfg.leverage_ceiling          # absolute floor alone: still 2.0 (0.10/0.02 = 5)
    assert scale2 < cfg2.leverage_ceiling          # relative floor: sane request
    assert scale2 >= cfg2.leverage_floor


def test_floor_never_invents_estimate():
    cfg = VolTargetConfig(vol_floor_enabled=True, vol_floor_annual=0.02)
    assert apply_vol_floor(None, cfg, []) is None


def test_floor_disabled_is_passthrough():
    cfg = VolTargetConfig()  # vol_floor_enabled defaults False
    assert apply_vol_floor(1.7e-5, cfg, []) == 1.7e-5
    assert apply_vol_floor(None, cfg, []) is None


def test_default_path_unchanged_by_t153():
    """Identical scale pre/post-T-153 for default-config callers."""
    hist = _collapse_history()
    legacy_cfg = VolTargetConfig(enabled=True, estimator_type="ewma",
                                 min_returns_required=60)
    # New kwargs default to None — the rolling/ewma path must ignore them.
    assert compute_portfolio_vol_scale(hist, legacy_cfg) == \
           compute_portfolio_vol_scale(hist, legacy_cfg, data_map=None, positions=None)


# --------------------------------------------------------------------- #
# Yang-Zhang
# --------------------------------------------------------------------- #

def _flat_close_live_range_ohlc(n=60):
    """Closes pinned flat; daily ranges alive — the tape that kills EWMA
    (r_cc = 0) but that a range estimator reads correctly."""
    idx = pd.bdate_range("2022-01-03", periods=n)
    close = np.full(n, 100.0)
    return pd.DataFrame({
        "Open": np.full(n, 100.0),
        "High": np.full(n, 102.0),
        "Low": np.full(n, 98.0),
        "Close": close,
    }, index=idx)


def test_yz_sane_on_flat_close_live_range():
    ohlc = _flat_close_live_range_ohlc()
    sigma = yang_zhang_vol(ohlc, window=21)
    assert sigma is not None
    assert sigma > 0.05  # >5% annualized — far from the EWMA's ~0


def test_yz_insufficient_data_returns_none():
    assert yang_zhang_vol(_flat_close_live_range_ohlc(n=10), window=21) is None
    assert yang_zhang_vol(None, window=21) is None
    assert yang_zhang_vol(pd.DataFrame({"Close": [1.0] * 30}), window=21) is None


def test_yz_corrupt_opens_repair_active():
    """A snap-back print (open +30%, intraday reverses -30%, H/L/C clean)
    must be repaired (open := prev close). Because ONLY the open is
    corrupt, the repaired frame is numerically identical to the clean
    one — sigma must match exactly. Without the repair, the on-variance
    term (log(1.3) jump) would dominate and sigma_bad >> sigma_clean."""
    ohlc = _flat_close_live_range_ohlc(n=40)
    bad = ohlc.copy()
    bad.iloc[30, bad.columns.get_loc("Open")] = 130.0  # |r_on|=0.262, |r_id|=0.262, opposite signs
    sigma_clean = yang_zhang_vol(ohlc, window=21)
    sigma_bad = yang_zhang_vol(bad, window=21)
    assert sigma_bad is not None and sigma_clean is not None
    assert sigma_bad == pytest.approx(sigma_clean)


class _Pos:
    def __init__(self, qty, last_price):
        self.qty = qty
        self.last_price = last_price


def test_portfolio_yz_grossweighted_and_failsafe():
    ohlc = _flat_close_live_range_ohlc()
    data_map = {"AAA": ohlc, "BBB": ohlc * 2.0}
    positions = {"AAA": _Pos(10, 100.0), "BBB": _Pos(-5, 200.0)}
    sigma = portfolio_yang_zhang_vol(data_map, positions, window=21)
    assert sigma is not None and sigma > 0.0
    # fail-safes
    assert portfolio_yang_zhang_vol(None, positions) is None
    assert portfolio_yang_zhang_vol(data_map, None) is None
    assert portfolio_yang_zhang_vol(data_map, {}) is None
    assert portfolio_yang_zhang_vol({}, positions) is None
    # all-flat book -> None
    flat = {"AAA": _Pos(0, 100.0)}
    assert portfolio_yang_zhang_vol(data_map, flat) is None


def test_yang_zhang_estimator_dispatch():
    ohlc = _flat_close_live_range_ohlc()
    cfg = VolTargetConfig(enabled=True, estimator_type="yang_zhang")
    positions = {"AAA": _Pos(10, 100.0)}
    # with data: sane scale in [floor, ceiling]
    s = compute_portfolio_vol_scale([], cfg, data_map={"AAA": ohlc}, positions=positions)
    assert cfg.leverage_floor <= s <= cfg.leverage_ceiling
    # without data: estimator unavailable -> 1.0 no-op
    assert compute_portfolio_vol_scale([], cfg, data_map=None, positions=positions) == 1.0


def test_unknown_estimator_falls_back_to_rolling():
    hist = _collapse_history()
    a = compute_portfolio_vol_scale(
        hist, VolTargetConfig(enabled=True, estimator_type="rolling", min_returns_required=60))
    b = compute_portfolio_vol_scale(
        hist, VolTargetConfig(enabled=True, estimator_type="banana", min_returns_required=60))
    assert a == b
