"""T-216 unit tests — conjunctive selector (the tests that were missing).

The g_regime-dead bug (director review) would have been caught by test (c):
g_regime must resolve to the INTENDED value for a real HMM regime input,
not silently fall back to 1.0. Tests are deterministic, no backtest.
"""
from __future__ import annotations

import pandas as pd
import pytest

from engines.engine_a_alpha.signal_processor import (
    SignalProcessor, RegimeSettings, HygieneSettings, EnsembleSettings,
)


def _sp(mode: str) -> SignalProcessor:
    return SignalProcessor(RegimeSettings(), HygieneSettings(),
                           EnsembleSettings(mode=mode), edge_weights={})


def _details(tech_norm=None, fund_norm=None):
    """Build a `details` list as the combine loop produces it. Edge names
    map to categories via EDGE_CATEGORY_MAP (momentum→technical,
    fundamental→fundamental)."""
    d = []
    if tech_norm is not None:
        d.append({"edge": "momentum_v1", "raw": tech_norm, "norm": tech_norm, "weight": 1.0})
    if fund_norm is not None:
        d.append({"edge": "fundamental_value_v1", "raw": fund_norm, "norm": fund_norm, "weight": 1.0})
    return d


def _regime_meta(p_crisis):
    """regime_meta carrying a causal-HMM crisis posterior (the shape
    RegimeGate._p_crisis / hmm_regime_label read)."""
    return {"hmm_regime": {"probabilities": {"crisis": p_crisis}}}


# (a) canon-inert when OFF — default mode is the legacy weighted_mean
def test_default_mode_is_weighted_mean():
    assert EnsembleSettings().mode == "weighted_mean"


# (b) multiplicative veto: no technical → 0; no fundamental → 0
def test_veto_no_technical_signal():
    sp = _sp("conjunctive")
    assert sp._conjunctive_aggregate(_details(fund_norm=0.8), _regime_meta(0.0)) == 0.0

def test_veto_requires_fundamental_confirmation():
    sp = _sp("conjunctive")
    # strong technical, NO fundamental edge → conjunction vetoes (0.0)
    assert sp._conjunctive_aggregate(_details(tech_norm=0.9), _regime_meta(0.0)) == 0.0


# (c) THE BUG TEST: g_regime resolves to the intended value for a real regime
def test_g_regime_resolves_not_silently_one():
    sp = _sp("conjunctive")
    # calm (p_crisis<0.30) → g_regime 1.0; crisis (p_crisis>=0.60) → 0.0.
    # s_tech=0.8, g_fund=clip(0.5+0.5,0,1)=1.0 → score = 0.8 × 1.0 × g_regime.
    calm = sp._conjunctive_aggregate(_details(0.8, 0.5), _regime_meta(0.05))
    crisis = sp._conjunctive_aggregate(_details(0.8, 0.5), _regime_meta(0.95))
    cautious = sp._conjunctive_aggregate(_details(0.8, 0.5), _regime_meta(0.45))
    assert calm == pytest.approx(0.8), f"calm g_regime should be 1.0 → 0.8, got {calm}"
    assert crisis == pytest.approx(0.0), f"crisis g_regime MUST be 0.0 (this is the dead-gate bug), got {crisis}"
    assert cautious == pytest.approx(0.4), f"cautious g_regime 0.5 → 0.4, got {cautious}"
    # The bug signature: crisis != calm. If g_regime were dead (≡1.0) these
    # would be EQUAL — that is exactly what shipped before the fix.
    assert crisis != calm


# (d) scale bounds: score stays in [-1, 1]
def test_score_bounds():
    sp = _sp("conjunctive")
    s = sp._conjunctive_aggregate(_details(0.99, 0.99), _regime_meta(0.0))
    assert -1.0 <= s <= 1.0


# (e) regime-absent fail-safe: no HMM posterior → calm → g_regime 1.0 (no suppression)
def test_regime_absent_failsafe_no_suppression():
    sp = _sp("conjunctive")
    s = sp._conjunctive_aggregate(_details(0.8, 0.5), regime_meta=None)
    assert s == pytest.approx(0.8), "absent regime must NOT suppress (fail-safe calm=1.0)"
