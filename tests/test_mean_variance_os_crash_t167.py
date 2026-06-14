"""T-2026-06-13-167 — regression guard for the mean_variance allocator crash.

A function-local `import os` inside PortfolioPolicy.allocate() shadowed the
module-level `os`, so the T-140-fu2 cov→MVO probe's earlier
`os.environ.get("ARCHONDEX_COV_MVO_PROBE")` raised UnboundLocalError on EVERY
mean_variance bar (introduced by d0cdf6e, 2026-06-13). The backtest controller's
broad `except Exception` swallowed it -> silent 0-trades. The Apr-23 allocator
artifact (adaptive mode) masked it locally; archiving the artifact (mean_variance
is the production allocator) exposed it and blocked B's re-anchor. This test
exercises the mean_variance branch directly and asserts it neither raises nor
silently returns empty.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _price_frame(seed, n=30, p0=100.0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.01, n)
    close = p0 * np.exp(np.cumsum(rets))
    idx = pd.date_range("2018-01-02", periods=n, freq="B")
    return pd.DataFrame({"Open": close, "High": close * 1.01,
                         "Low": close * 0.99, "Close": close,
                         "Volume": 1e6}, index=idx)


def test_mean_variance_allocate_does_not_crash():
    """The mean_variance branch (len(returns_df) >= 5 reaches the probe line)
    must return non-empty weights without UnboundLocalError."""
    from engines.engine_c_portfolio.policy import PortfolioPolicy, PortfolioPolicyConfig

    tickers = ["AAA", "BBB", "CCC", "DDD"]
    signals = {t: float(i + 1) for i, t in enumerate(tickers)}
    price_data = {t: _price_frame(seed=i) for i, t in enumerate(tickers)}

    pol = PortfolioPolicy(PortfolioPolicyConfig(mode="mean_variance"))
    # No exception (the bug raised UnboundLocalError here):
    weights = pol.allocate(signals=signals, price_data=price_data,
                           equity=100_000.0, current_weights={},
                           regime_meta=None)
    assert isinstance(weights, dict)
    assert weights, "mean_variance returned empty weights (the swallowed-crash signature)"
    assert any(abs(w) > 0 for w in weights.values()), "all-zero weights — allocator inert"


def test_mean_variance_probe_path_with_env_set():
    """Even with the cov→MVO probe env var SET (the exact line that referenced
    the shadowed `os`), allocate() must run."""
    import os
    from engines.engine_c_portfolio.policy import PortfolioPolicy, PortfolioPolicyConfig

    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    signals = {t: float(i + 1) for i, t in enumerate(tickers)}
    price_data = {t: _price_frame(seed=10 + i) for i, t in enumerate(tickers)}
    prev = os.environ.get("ARCHONDEX_COV_MVO_PROBE")
    os.environ["ARCHONDEX_COV_MVO_PROBE"] = "1"
    try:
        pol = PortfolioPolicy(PortfolioPolicyConfig(mode="mean_variance"))
        weights = pol.allocate(signals=signals, price_data=price_data,
                               equity=100_000.0, current_weights={}, regime_meta=None)
        assert isinstance(weights, dict) and weights
    finally:
        if prev is None:
            os.environ.pop("ARCHONDEX_COV_MVO_PROBE", None)
        else:
            os.environ["ARCHONDEX_COV_MVO_PROBE"] = prev


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
