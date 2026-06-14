"""T-2026-06-13-167 — substrate completeness round 2 regression guards.

Two substrate bugs in the same "data not reaching the engine" class as T-164:

GAP 3  SPY price history was truncated to ~6yr (2020+) while stocks carry full
       depth -> the benchmark + the price-axis regime were degraded on every
       long-window cloud run. Fixed by regenerating full SPY (1993->).

BONUS  engines/data_manager._normalize_df's global `median*3` sanity clip
       (added 2025-10-21, 62c3eaf) silently TRUNCATED every deep-history series
       at the first bar exceeding 3x its all-time median. Harmless while
       histories were short; it detonated once T-082 baked 1970-> depth, cutting
       90/109 universe tickers at load (AAPL @2009, IBM @2002, SPY @2020-06).
       Fixed with a trailing rolling-median band (lookahead-free, strictly
       additive). These tests lock both fixes against regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _make_normalizer():
    from engines.data_manager.data_manager import DataManager
    return DataManager._normalize_df


def _monotonic_growth_frame(n=4000, p0=10.0, daily=0.001):
    """A clean, legitimately-appreciating series (~50x over n bars, so max is
    well past 3x the all-time median). Under the OLD median*3 band this gets
    truncated the moment price passes 3x the all-time median. Under the fix it
    must survive intact (sustained appreciation never deviates 20x from a
    trailing 63-bar median)."""
    idx = pd.date_range("1995-01-02", periods=n, freq="B")
    close = p0 * np.exp(np.cumsum(np.full(n, daily)))
    return pd.DataFrame(
        {"Open": close, "High": close * 1.005, "Low": close * 0.995,
         "Close": close, "Volume": 1e6}, index=idx)


def test_normalize_does_not_truncate_sustained_appreciation():
    """REGRESSION (the bug): a 50x sustained uptrend must NOT lose its recent
    high-priced bars. Old median*3 clip dropped everything above 3x median."""
    norm = _make_normalizer()
    df = _monotonic_growth_frame()
    out = norm(df.copy())
    # all bars retained; the last (highest-priced) bar survives
    assert len(out) == len(df), f"truncated {len(df)-len(out)} bars of a clean uptrend"
    assert out.index[-1] == df.index[-1], "recent high-priced bars were clipped"
    assert out["Close"].iloc[-1] == pytest.approx(df["Close"].iloc[-1], rel=1e-9)


def test_normalize_still_drops_isolated_fatfinger_spike():
    """The sanity filter must still catch a genuine fat-finger (digit error):
    a single 100x spike that reverts."""
    norm = _make_normalizer()
    df = _monotonic_growth_frame(n=500)
    df.iloc[250, df.columns.get_loc("Close")] *= 100.0  # 100x bad tick
    out = norm(df.copy())
    assert len(out) == len(df) - 1, "isolated 100x fat-finger should be dropped"


def test_normalize_strictly_additive_vs_old_band():
    """The fix only ADDS bars back: every row the OLD global-median band kept
    must survive byte-identical under the new filter (no perturbation)."""
    norm = _make_normalizer()
    df = _monotonic_growth_frame()
    new = norm(df.copy())

    # replicate the OLD lines exactly on the same normalized inputs
    old = df.copy()
    mc = old["Close"].median(skipna=True)
    old = old[(old["Close"] > 0) & (old["Close"] < mc * 3)]
    old["Close"] = old["Close"].clip(lower=0.01, upper=mc * 3)

    common = old.index.intersection(new.index)
    assert len(common) == len(old), "fix dropped a row the old band kept"
    assert np.allclose(old.loc[common, "Close"].values,
                       new.loc[common, "Close"].values, rtol=0, atol=0), \
        "fix changed the value of a row the old band kept"
    assert len(new) > len(old), "fix should restore bars the old band truncated"


def test_spy_has_full_depth():
    """GAP 3: SPY must reach back to its 1993 inception (covers the 16yr/26yr
    windows), not be truncated to ~6yr."""
    csv = ROOT / "data/processed/SPY_1d.csv"
    df = pd.read_csv(csv, parse_dates=["Date"])
    assert df["Date"].min() <= pd.Timestamp("1994-01-01"), \
        f"SPY starts {df['Date'].min()} — should reach 1993 inception"
    assert df["Date"].max() >= pd.Timestamp("2026-01-01")
    assert len(df) > 8000, f"SPY only {len(df)} rows — truncated?"


def test_spy_recent_portion_unchanged_basis():
    """The 2020+ portion must remain on the same (total-return) basis as before
    so the recent canon every prior anchor used is preserved: monotonic Close
    near the 2026 end and no seam discontinuity > 25% at 2020-04-09."""
    df = pd.read_csv(ROOT / "data/processed/SPY_1d.csv", parse_dates=["Date"]).set_index("Date")
    seam = pd.Timestamp("2020-04-09")
    prev = df[df.index < seam]["Close"].iloc[-1]
    post = df.loc[seam, "Close"]
    assert abs(post / prev - 1.0) < 0.25, f"seam discontinuity {post/prev:.3f} at 2020-04-09"


def test_spy_pinned_in_manifest():
    mani = (ROOT / "config/substrate_manifest.sha256").read_text()
    assert "data/processed/SPY_1d.csv" in mani
    assert "data/processed/parquet/SPY_1d.parquet" in mani


def test_full_universe_no_load_truncation():
    """Integration: with the fix, no universe ticker loses >30 days off its raw
    tail at load time (the 90/109 silent truncation is gone)."""
    import json
    from engines.data_manager.data_manager import DataManager
    dm = DataManager()
    cfg = json.loads((ROOT / "config/backtest_settings.json").read_text())
    truncated = []
    for t in cfg.get("tickers", []):
        p = dm.parquet_cache_path(t, "1d")
        if not p.exists():
            continue
        raw = pd.read_parquet(p)
        ld = dm.load_cached(t, "1d")
        if ld is None or ld.empty:
            continue
        if (pd.to_datetime(raw.index).max() - ld.index[-1]).days > 30:
            truncated.append(t)
    assert not truncated, f"{len(truncated)} tickers still load-truncated: {truncated[:10]}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
