"""tests/test_confidence_gated_execution.py
=============================================
Regression tests for T-2026-05-12-057 confidence-gated execution.

Coverage per spec acceptance:
1. test_gate_disabled_passthrough -- enabled=False produces identical
   output to current weighted_sum (no change in process() output)
2. test_n_threshold_2_filters_correctly -- 1-edge-firing bar gets
   filtered; 2-edge-agreeing bar passes
3. test_n_threshold_3_filters_correctly -- same shape at higher n
4. test_disagreement_kills_signal -- long_count == short_count → gate
   fails regardless of n_threshold
5. test_turnover_reduction_at_higher_threshold -- synthetic substrate
   gate ON reduces effective signal count significantly
6. test_a_b_determinism_at_processor_level -- repeat with same input
   produces identical output (pure-function contract)
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from engines.engine_a_alpha.signal_processor import (
    ConfidenceGateConfig,
    EnsembleSettings,
    HygieneSettings,
    RegimeSettings,
    SignalProcessor,
)


def _make_processor(
    enabled: bool = False,
    n_threshold: int = 2,
) -> SignalProcessor:
    return SignalProcessor(
        regime=RegimeSettings(),
        hygiene=HygieneSettings(),
        ensemble=EnsembleSettings(),
        edge_weights={"e1": 1.0, "e2": 1.0, "e3": 1.0, "e4": 1.0, "e5": 1.0},
        confidence_gate=ConfidenceGateConfig(
            enabled=enabled, n_threshold=n_threshold,
        ),
    )


def _synthetic_data_map(tickers, n_bars=120):
    """Build a tiny OHLCV map: deterministic random walk per ticker."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-02", periods=n_bars, freq="B")
    out = {}
    for i, t in enumerate(tickers):
        px = 100 + rng.normal(0, 1, size=n_bars).cumsum()
        out[t] = pd.DataFrame(
            {
                "Open": px, "High": px + 0.5, "Low": px - 0.5,
                "Close": px, "Volume": rng.integers(1e5, 1e7, size=n_bars),
            },
            index=dates,
        )
    return out


# -------------------- 1. Disabled passthrough -------------------- #

def test_gate_disabled_passthrough():
    """enabled=False must produce identical output to current
    weighted_sum behavior. Verified by running same input through
    both an off-gate processor and a never-gated processor (which is
    the default ConfidenceGateConfig)."""
    data_map = _synthetic_data_map(["AAA", "BBB"])
    now = data_map["AAA"].index[-1]
    raw_scores = {
        "AAA": {"e1": 0.5},  # single-edge: N≥2 would filter this
        "BBB": {"e1": 0.3, "e2": 0.4},  # two edges agreeing
    }
    sp_off = _make_processor(enabled=False, n_threshold=2)
    sp_default = SignalProcessor(
        regime=RegimeSettings(),
        hygiene=HygieneSettings(),
        ensemble=EnsembleSettings(),
        edge_weights={"e1": 1.0, "e2": 1.0},
        # No confidence_gate passed → default config (enabled=False)
    )

    out_off = sp_off.process(data_map, now, raw_scores)
    out_default = sp_default.process(data_map, now, raw_scores)

    # Both should produce identical aggregate_scores per ticker
    assert set(out_off.keys()) == set(out_default.keys())
    for t in out_off:
        assert out_off[t]["aggregate_score"] == out_default[t]["aggregate_score"], (
            f"ticker {t} differs: off={out_off[t]['aggregate_score']} "
            f"default={out_default[t]['aggregate_score']}"
        )
    # Both should include AAA (single-edge would pass without gate)
    assert "AAA" in out_off
    assert "AAA" in out_default


# -------------------- 2. N>=2 filters correctly -------------------- #

def test_n_threshold_2_filters_correctly():
    """1-edge-firing bar gets filtered; 2-edge-agreeing bar passes."""
    data_map = _synthetic_data_map(["SOLO", "PAIR"])
    now = data_map["SOLO"].index[-1]
    raw_scores = {
        "SOLO": {"e1": 0.5},  # only one edge fires
        "PAIR": {"e1": 0.3, "e2": 0.4},  # two edges both long
    }
    sp = _make_processor(enabled=True, n_threshold=2)
    out = sp.process(data_map, now, raw_scores)

    assert "SOLO" not in out, "single-edge bar should be filtered at N>=2"
    assert "PAIR" in out, "2-edges-agreeing bar should pass at N>=2"
    assert sp._confidence_gate_bars_filtered == 1
    assert sp._confidence_gate_bars_passed == 1


# -------------------- 3. N>=3 filters correctly -------------------- #

def test_n_threshold_3_filters_correctly():
    """At N=3, only 3+ agreeing-on-direction bars pass."""
    data_map = _synthetic_data_map(["TWO", "THREE", "FOUR"])
    now = data_map["TWO"].index[-1]
    raw_scores = {
        "TWO": {"e1": 0.3, "e2": 0.4},  # only two edges long
        "THREE": {"e1": 0.3, "e2": 0.4, "e3": 0.5},  # three long
        "FOUR": {"e1": 0.3, "e2": 0.4, "e3": 0.5, "e4": 0.6},  # four
    }
    sp = _make_processor(enabled=True, n_threshold=3)
    out = sp.process(data_map, now, raw_scores)

    assert "TWO" not in out
    assert "THREE" in out
    assert "FOUR" in out


# -------------------- 4. Disagreement kills signal -------------------- #

def test_disagreement_kills_signal():
    """long_count == short_count → gate fails regardless of n_threshold."""
    data_map = _synthetic_data_map(["BALANCED2", "BALANCED4"])
    now = data_map["BALANCED2"].index[-1]
    raw_scores = {
        "BALANCED2": {"e1": +0.5, "e2": -0.3},  # 1L 1S — fails
        "BALANCED4": {  # 2L 2S — fails despite |max| >= 2
            "e1": +0.5, "e2": +0.3, "e3": -0.4, "e4": -0.2,
        },
    }
    # Even at N=2 (where 4 agreeing edges would pass), balanced kills.
    sp = _make_processor(enabled=True, n_threshold=2)
    out = sp.process(data_map, now, raw_scores)
    assert "BALANCED2" not in out
    assert "BALANCED4" not in out, "2L 2S must fail despite max == n"


# -------------------- 5. Turnover reduction at higher threshold -------------------- #

def test_turnover_reduction_at_higher_threshold():
    """Synthetic substrate: gate ON reduces signal emissions by ≥40% at N>=3.

    Build 100 ticker-bars where 70% have single-edge firing (noise),
    20% have 2-edges agreeing (moderate), 10% have 3+ agreeing
    (high-confidence). Off: 100% pass. N>=2: 30% pass. N>=3: 10% pass.
    """
    rng = np.random.default_rng(42)
    n_tickers = 100
    tickers = [f"T{i:03d}" for i in range(n_tickers)]
    data_map = _synthetic_data_map(tickers, n_bars=60)
    now = data_map[tickers[0]].index[-1]

    raw_scores: Dict[str, Dict[str, float]] = {}
    for i, t in enumerate(tickers):
        if i < 70:
            # noise: only one edge fires
            raw_scores[t] = {"e1": rng.uniform(0.1, 0.5)}
        elif i < 90:
            # moderate: 2 edges agreeing
            raw_scores[t] = {
                "e1": rng.uniform(0.1, 0.5),
                "e2": rng.uniform(0.1, 0.5),
            }
        else:
            # high conviction: 3+ edges agreeing
            raw_scores[t] = {
                "e1": rng.uniform(0.1, 0.5),
                "e2": rng.uniform(0.1, 0.5),
                "e3": rng.uniform(0.1, 0.5),
                "e4": rng.uniform(0.1, 0.5),
            }

    sp_off = _make_processor(enabled=False)
    sp_n2 = _make_processor(enabled=True, n_threshold=2)
    sp_n3 = _make_processor(enabled=True, n_threshold=3)

    out_off = sp_off.process(data_map, now, raw_scores)
    out_n2 = sp_n2.process(data_map, now, raw_scores)
    out_n3 = sp_n3.process(data_map, now, raw_scores)

    n_off = len(out_off)
    n_n2 = len(out_n2)
    n_n3 = len(out_n3)

    # Sanity: off passes all (modulo regime/hygiene which apply to all
    # arms equally, so the comparison is fair).
    assert n_off == 100, f"off should emit all 100 tickers, got {n_off}"
    # N>=2 keeps the 30 with at least 2 agreeing.
    assert n_n2 == 30, f"N>=2 should emit 30 tickers, got {n_n2}"
    # N>=3 keeps the 10 with at least 3 agreeing.
    assert n_n3 == 10, f"N>=3 should emit 10 tickers, got {n_n3}"
    # Turnover-reduction spec: ≥40% at N>=3
    reduction_n3 = 1.0 - (n_n3 / n_off)
    assert reduction_n3 >= 0.40, (
        f"N>=3 should reduce trade-bar count by >=40%, got "
        f"{reduction_n3:.2%}"
    )
    # Looser check at N>=2: still substantial
    reduction_n2 = 1.0 - (n_n2 / n_off)
    assert reduction_n2 >= 0.40, f"N>=2 reduction {reduction_n2:.2%}"


# -------------------- 6. Determinism within an arm -------------------- #

def test_a_b_determinism_at_processor_level():
    """Same input twice → identical output (pure-function contract)."""
    data_map = _synthetic_data_map(["AAA", "BBB", "CCC"])
    now = data_map["AAA"].index[-1]
    raw_scores = {
        "AAA": {"e1": 0.3, "e2": 0.4},
        "BBB": {"e1": 0.2},
        "CCC": {"e1": 0.5, "e2": 0.3, "e3": 0.1},
    }
    sp1 = _make_processor(enabled=True, n_threshold=2)
    sp2 = _make_processor(enabled=True, n_threshold=2)
    out1 = sp1.process(data_map, now, raw_scores)
    out2 = sp2.process(data_map, now, raw_scores)
    assert set(out1.keys()) == set(out2.keys())
    for k in out1:
        assert out1[k]["aggregate_score"] == out2[k]["aggregate_score"]


# -------------------- Helpers -------------------- #

def test_gate_handles_invalid_inputs_safely():
    """None values, NaN, inf are skipped; gate handles them robustly."""
    sp = _make_processor(enabled=True, n_threshold=2)
    em = {"e1": None, "e2": float("nan"), "e3": float("inf"), "e4": 0.3, "e5": 0.4}
    assert sp._check_confidence_gate(em) is True  # 2 valid edges agree


def test_gate_config_defaults():
    """ConfidenceGateConfig default is disabled."""
    cfg = ConfidenceGateConfig()
    assert cfg.enabled is False
    assert cfg.n_threshold == 2
