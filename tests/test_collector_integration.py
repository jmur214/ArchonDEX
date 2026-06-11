import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd

from engines.engine_a_alpha.signal_collector import SignalCollector
from engines.engine_a_alpha.edges.momentum_edge import MomentumEdge
from engines.engine_a_alpha.edges.xsec_momentum import XSecMomentumEdge


def _synthetic_bars(seed: int, n_bars: int = 250, p0: float = 100.0) -> pd.DataFrame:
    """Deterministic OHLCV random-walk bars.

    T-147: this test previously called ``yf.download()`` LIVE inside the
    test body — a network dependency that failed the suite whenever
    yfinance rate-limited or changed response shape (and violated the
    project's own yfinance-contamination discipline). The contract under
    test is collector normalization over a data_map, which synthetic
    bars exercise identically and deterministically.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-02", periods=n_bars)
    rets = rng.normal(0.0005, 0.015, n_bars)
    close = p0 * np.cumprod(1.0 + rets)
    spread = np.abs(rng.normal(0.005, 0.002, n_bars))
    return pd.DataFrame({
        "Open": close * (1.0 - spread / 2),
        "High": close * (1.0 + spread),
        "Low": close * (1.0 - spread),
        "Close": close,
        "Volume": rng.integers(1_000_000, 50_000_000, n_bars).astype(float),
    }, index=idx)


def test_collector_normalization():
    data_map = {
        "AAPL": _synthetic_bars(1),
        "MSFT": _synthetic_bars(2),
        "SPY": _synthetic_bars(3),
    }
    now = max(df.index.max() for df in data_map.values())

    edges = {"momentum_edge": MomentumEdge(), "xsec_momentum": XSecMomentumEdge()}
    collector = SignalCollector(edges=edges, debug=False)
    scores = collector.collect(data_map, now)
    assert isinstance(scores, dict)
    assert len(scores) > 0
    for ticker, payload in scores.items():
        assert ticker in data_map
        assert isinstance(payload, dict)


def test_collector_normalization_deterministic():
    """Same inputs → identical score keys (no hidden RNG/network/state)."""
    data_map = {"AAPL": _synthetic_bars(1), "MSFT": _synthetic_bars(2)}
    now = max(df.index.max() for df in data_map.values())
    edges = {"momentum_edge": MomentumEdge(), "xsec_momentum": XSecMomentumEdge()}
    s1 = SignalCollector(edges=edges, debug=False).collect(data_map, now)
    s2 = SignalCollector(edges=edges, debug=False).collect(data_map, now)
    assert s1.keys() == s2.keys()
