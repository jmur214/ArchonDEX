"""
tests/test_vol_target_guard_t212.py
===================================
T-2026-06-18-212 — the vol-target HARD-PRECONDITION guard.

T-153 BUILT the sigma-floor mechanism (`apply_vol_floor`) but left it
OPTIONAL (default-OFF, no enforcement). T-212 makes it a HARD precondition:
a vol-target run is NOT VALID unless the sigma-floor is enabled AND high
enough to neutralize the T-150/T-153 collapse (the estimator emits
sigma < target/ceiling on ~14% of canonical bars, min 3e-06, pinning
leverage at the ceiling off a garbage estimate).

These tests prove:
  1. `validate_vol_target_config` FAILS LOUD (VolTargetGuardError) when
     vol-target is enabled with the floor off, or with an absolute floor
     below the `target/ceiling` collapse bound.
  2. It is a NO-OP on the default-OFF path (so the OFF canon is untouched).
  3. The error subclasses AssertionError → propagates through
     risk_engine's `_PROGRAMMER_ERRORS` re-raise (fail-loud, not swallowed).
  4. The TUNED floor (frac=0.5) eliminates the collapse: the canonical
     26yr book's 928 near-zero bars (min 3e-06) no longer pin the ceiling.

The derived tuning rule (proven below on the real book numbers):
  a collapsed sigma pins the ceiling iff sigma <= target/ceiling, so the
  GUARANTEED (absolute) floor must satisfy
      vol_floor_annual >= target_annual_vol / leverage_ceiling   (= 0.05)
  and the relative component (frac * sigma_full) adds adaptive margin on
  top (sigma_full = 0.1574 on the 26yr book → frac=0.5 → 0.0787 > 0.05).
"""
import numpy as np
import pandas as pd
import pytest

from engines.engine_b_risk.vol_target import (
    VolTargetConfig,
    VolTargetGuardError,
    apply_vol_floor,
    compute_portfolio_vol_scale,
    compute_vol_scale,
    validate_vol_target_config,
)


# --------------------------------------------------------------------- #
# 1. The fail-loud mandate
# --------------------------------------------------------------------- #

def test_disabled_config_is_noop_no_raise():
    """Default-OFF path: validate must NEVER raise (OFF canon untouched),
    even with a floor that would be illegal if enabled."""
    cfg = VolTargetConfig(enabled=False, vol_floor_enabled=False)
    assert validate_vol_target_config(cfg) is None  # no raise


def test_enabled_without_floor_raises():
    cfg = VolTargetConfig(enabled=True, vol_floor_enabled=False)
    with pytest.raises(VolTargetGuardError, match="sigma-floor guard is OFF"):
        validate_vol_target_config(cfg)


def test_enabled_floor_on_but_too_low_raises():
    # target/ceiling = 0.10/2.0 = 0.05; default vol_floor_annual=0.02 < 0.05.
    cfg = VolTargetConfig(
        enabled=True, target_annual_vol=0.10, leverage_ceiling=2.0,
        vol_floor_enabled=True, vol_floor_annual=0.02,
    )
    with pytest.raises(VolTargetGuardError, match="sigma-floor too low"):
        validate_vol_target_config(cfg)


def test_relative_frac_does_not_satisfy_the_guarantee():
    """A non-zero frac adds runtime margin but DEGRADES to the absolute
    floor on degenerate history — so it cannot substitute for a sufficient
    absolute floor. annual=0.02 + frac=1.0 must still raise."""
    cfg = VolTargetConfig(
        enabled=True, target_annual_vol=0.10, leverage_ceiling=2.0,
        vol_floor_enabled=True, vol_floor_annual=0.02,
        vol_floor_full_sample_frac=1.0,
    )
    with pytest.raises(VolTargetGuardError, match="sigma-floor too low"):
        validate_vol_target_config(cfg)


def test_enabled_with_sufficient_floor_passes():
    cfg = VolTargetConfig(
        enabled=True, target_annual_vol=0.10, leverage_ceiling=2.0,
        vol_floor_enabled=True, vol_floor_annual=0.05,
        vol_floor_full_sample_frac=0.5,
    )
    assert validate_vol_target_config(cfg) is None  # boundary annual==bound passes


def test_bound_uses_base_target_not_regime_muted():
    """Regime multipliers only LOWER the effective target → lower bound →
    easier to clear. The guard validates against the BASE target (the
    binding/conservative case): a config legal at the base target stays
    legal under any stress multiplier."""
    cfg = VolTargetConfig(
        enabled=True, target_annual_vol=0.10, leverage_ceiling=2.0,
        regime_aware=True, stressed_target_multiplier=0.60,
        vol_floor_enabled=True, vol_floor_annual=0.05,
    )
    assert validate_vol_target_config(cfg) is None


def test_guard_is_assertion_error_for_failloud_propagation():
    """VolTargetGuardError must subclass AssertionError so risk_engine's
    _PROGRAMMER_ERRORS handler re-raises it fail-loud instead of swallowing
    it into the 1.0 operational fallback."""
    assert issubclass(VolTargetGuardError, AssertionError)


# --------------------------------------------------------------------- #
# 2. The derived tuning rule, proven on real-book numbers
# --------------------------------------------------------------------- #

def test_collapse_bound_math():
    """target/ceiling is exactly the sigma below which a reading pins the
    ceiling. Demonstrate at the production grid (0.10, ceiling 2.0)."""
    target, ceiling = 0.10, 2.0
    bound = target / ceiling  # 0.05
    # the canonical collapse value sails past the <=0 guard and pins ceiling
    assert compute_vol_scale(3e-06, target, 0.5, ceiling) == ceiling
    # exactly AT the bound → scale == ceiling (boundary; not OVER)
    assert compute_vol_scale(bound, target, 0.5, ceiling) == pytest.approx(ceiling)
    # just ABOVE the bound → strictly below ceiling (de-pinned)
    assert compute_vol_scale(bound * 1.2, target, 0.5, ceiling) < ceiling


def test_tuned_relative_floor_depins_canonical_min_sigma():
    """The canonical 26yr book: sigma_full = 0.1574 (measured), min sigma
    observed = 3e-06. With frac=0.5 the floor is 0.0787 > 0.05 = bound →
    the 3e-06 collapse bar is floored to 0.0787 → scale 1.27x, NOT ceiling.
    Synthesize a history whose full-sample sigma ≈ 0.1574 and inject the
    collapse to prove the floor de-pins it end-to-end."""
    rng = np.random.RandomState(212)
    # daily sigma for 0.1574 annualized = 0.1574/sqrt(252) ≈ 0.00991
    daily = rng.normal(0.0, 0.1574 / np.sqrt(252.0), 400).tolist()
    quiet = [1e-6] * 120  # collapse the rolling estimator to ~0
    eq, hist = 100_000.0, [{"timestamp": pd.Timestamp("2000-01-03"), "equity": 100_000.0}]
    for i, r in enumerate(daily + quiet):
        eq *= 1.0 + r
        hist.append({"timestamp": pd.Timestamp("2000-01-03") + pd.Timedelta(days=i + 1),
                     "equity": eq})

    base = dict(enabled=True, estimator_type="rolling", min_returns_required=60,
                target_annual_vol=0.10, leverage_floor=0.5, leverage_ceiling=2.0)
    # floor OFF → collapse pins ceiling
    off = compute_portfolio_vol_scale(hist, VolTargetConfig(**base))
    assert off == 2.0
    # tuned floor ON (frac=0.5, annual=0.05) → de-pinned, strictly < ceiling
    tuned = VolTargetConfig(**base, vol_floor_enabled=True,
                            vol_floor_annual=0.05, vol_floor_full_sample_frac=0.5)
    validate_vol_target_config(tuned)  # legal config
    on = compute_portfolio_vol_scale(hist, tuned)
    assert on < 2.0
    assert on >= 0.5


def test_apply_vol_floor_floors_the_collapse_value():
    """Unit: the 3e-06 collapse value is floored to the effective floor
    (here the absolute 0.06) before the divide."""
    cfg = VolTargetConfig(vol_floor_enabled=True, vol_floor_annual=0.06,
                          vol_floor_full_sample_frac=0.0)
    assert apply_vol_floor(3e-06, cfg, []) == 0.06
    # and that floored sigma de-pins the ceiling at target 0.10 / ceil 2.0
    assert compute_vol_scale(0.06, 0.10, 0.5, 2.0) == pytest.approx(0.10 / 0.06)
