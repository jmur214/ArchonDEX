"""Standing-ready guard for the T-298 asymmetric-damping mode of OffenseSSOConstructor.

This mode is NOT wired into any jobdef (default = "symmetric", byte-preserved). These tests lock in the
two properties the damped spec must have if the user chooses it: (1) the default is unchanged; (2) under
asymmetric damping de-risking ALWAYS executes (exit-lag ≡ 0) while single-increment re-entry is held.
"""
import numpy as np
import pandas as pd
import pytest

from paper_trader.offense_sso_constructor import OffenseSSOConstructor, OFFENSE_REENTRY_BAND

# SPY series engineered so the ensemble signal is fully ON (rising) → exposure fraction 1.0.
_SPY_ON = pd.Series(np.linspace(100, 260, 320), index=pd.bdate_range('2023-01-02', periods=320))
_SSO = pd.Series(np.linspace(50, 130, 320), index=_SPY_ON.index)


def _closes():
    return {'SPY': _SPY_ON, 'SSO': _SSO}


def test_default_is_symmetric_and_unchanged():
    c = OffenseSSOConstructor()
    assert c.damping == 'symmetric'


def test_bad_damping_value_rejected():
    with pytest.raises(ValueError):
        OffenseSSOConstructor(damping='sometimes')


def test_reentry_band_matches_the_t298_two_thirds_e2_band():
    # SSO weight = ensemble fraction = e2/2, so the T-298 ⅔ e2-band is ⅓ here.
    assert abs(OFFENSE_REENTRY_BAND - 1.0 / 3.0) < 1e-12


def test_symmetric_and_asymmetric_agree_when_signal_is_full_on_from_flat():
    """From flat (held 0) into a full-on signal, both modes enter (a flip is never damped)."""
    eq = 10_000.0
    sym = OffenseSSOConstructor(damping='symmetric').construct(eq, {}, _closes())
    asy = OffenseSSOConstructor(damping='asymmetric').construct(eq, {}, _closes())
    assert sym.target_qty['SSO'] == asy.target_qty['SSO'] > 0
    assert sym.orders and asy.orders                      # both trade the entry (flip)


def test_asymmetric_never_damps_de_risking():
    """Target < held (de-risk) must ALWAYS produce the trade, no matter how small the move."""
    eq = 10_000.0
    last = float(_SSO.iloc[-1])
    full = int(np.floor(eq * 1.0 / last))                 # currently fully invested (held ≈ target)
    # a tiny de-risk: hold slightly MORE than the target weight so target_w < held_w by < deadband
    held = full + 1
    asy = OffenseSSOConstructor(damping='asymmetric')
    plan = asy.construct(eq, {'SSO': held}, _closes())
    assert plan.orders, 'de-risk within the band must still execute under asymmetric damping'
    assert plan.orders[0].side == 'sell'
    # symmetric default WOULD suppress the same tiny de-risk (contrast, documents the safety improvement)
    sym = OffenseSSOConstructor(damping='symmetric').construct(eq, {'SSO': held}, _closes())
    assert not sym.orders, 'symmetric default suppresses the sub-deadband de-risk (the T-298 gap)'


def test_asymmetric_damps_single_increment_reentry_but_allows_large():
    """Re-entry within the ⅓ band is held; a re-entry beyond it executes."""
    eq = 10_000.0
    last = float(_SSO.iloc[-1])
    full = int(np.floor(eq * 1.0 / last))                 # full-on target weight ≈ 1.0
    asy = OffenseSSOConstructor(damping='asymmetric')
    # held ≈ ⅔ → re-entry to 1.0 is a single ⅓ increment → within band → HELD
    held_two_thirds = int(round(full * (2.0 / 3.0)))
    p1 = asy.construct(eq, {'SSO': held_two_thirds}, _closes())
    assert not p1.orders, 'single ⅓-increment re-entry should be damped (held)'
    # held ≈ ⅓ → re-entry to 1.0 is ⅔ (> ⅓ band) → EXECUTES
    held_one_third = int(round(full * (1.0 / 3.0)))
    p2 = asy.construct(eq, {'SSO': held_one_third}, _closes())
    assert p2.orders and p2.orders[0].side == 'buy', 'large (≥⅔) re-entry should execute'
