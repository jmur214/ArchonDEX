"""T-2026-06-18-210 — realistic-retail cost mode: OFF byte-identical + ON cap-tier.

The mode is ADDITIVE + default-OFF so the current anchors' canon is unchanged.
These tests lock: (1) with realistic_retail_costs OFF the model is byte-identical
to the existing ADV-bucket realistic model; (2) ON applies the market-cap-tier
half-spread; (3) an unknown cap (delisted/PIT) falls back to the ADV bucket (never
silently UNDER-prices); (4) the factory defaults the flag OFF.
"""
from __future__ import annotations

import pandas as pd
import pytest

from engines.execution.slippage_model import (
    SlippageConfig, RealisticSlippageModel, get_slippage_model,
)


def _bars(close, vol, n=40):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({"Close": [float(close)] * n, "Volume": [int(vol)] * n}, index=idx)


# mega ADV (800M): 400*2M ; small ADV (2M): 20*100k
MEGA = _bars(400, 2_000_000)
SMALL = _bars(20, 100_000)


def test_off_is_byte_identical_to_baseline():
    base = RealisticSlippageModel(SlippageConfig(model_type="realistic"))
    off = RealisticSlippageModel(SlippageConfig(model_type="realistic",
                                                realistic_retail_costs=False))
    for df in (MEGA, SMALL):
        for qty in (None, 100, 100000):
            assert base.calculate_slippage_bps("X", df, "buy", qty) == \
                   off.calculate_slippage_bps("X", df, "buy", qty)
    # Series fallback + adv-None fallback also identical
    assert base.calculate_slippage_bps("X", MEGA.iloc[-1], "buy") == \
           off.calculate_slippage_bps("X", MEGA.iloc[-1], "buy")


def test_on_uses_cap_tier_half_spread():
    on = RealisticSlippageModel(SlippageConfig(model_type="realistic",
                                               realistic_retail_costs=True))
    on._cap_cache_d = {"MEGA": 300e9, "MID": 5e9, "SMALL": 5e8, "MICRO": 1e8}
    # half-spread alone (qty=None) so we read the tier directly
    assert on.calculate_slippage_bps("MEGA", MEGA, "buy") == 2.0    # mega tier
    assert on.calculate_slippage_bps("MID", MEGA, "buy") == 8.0     # mid tier
    assert on.calculate_slippage_bps("SMALL", SMALL, "buy") == 35.0  # small tier
    assert on.calculate_slippage_bps("MICRO", SMALL, "buy") == 75.0  # micro tier


def test_on_unknown_cap_falls_back_to_adv_bucket():
    """A delisted/PIT name with no current cap must fall back to the ADV bucket
    (15 bps small here), NOT silently under-price to mega 1 bps."""
    on = RealisticSlippageModel(SlippageConfig(model_type="realistic",
                                               realistic_retail_costs=True))
    on._cap_cache_d = {}  # nothing known
    assert on.calculate_slippage_bps("DELISTED", SMALL, "buy") == 15.0  # ADV small bucket
    assert on.calculate_slippage_bps("DELISTED", MEGA, "buy") == 1.0    # ADV mega bucket


def test_factory_defaults_flag_off():
    m = get_slippage_model({"model_type": "realistic"})
    assert m.config.realistic_retail_costs is False
    on = get_slippage_model({"model_type": "realistic", "realistic_retail_costs": True})
    assert on.config.realistic_retail_costs is True


def test_micro_is_much_costlier_than_mega():
    """Sanity: the whole point — micro friction >> mega (the bias being fixed)."""
    on = RealisticSlippageModel(SlippageConfig(model_type="realistic",
                                               realistic_retail_costs=True))
    on._cap_cache_d = {"M": 300e9, "U": 1e8}
    assert on.calculate_slippage_bps("U", SMALL, "buy") > \
           10 * on.calculate_slippage_bps("M", MEGA, "buy")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
