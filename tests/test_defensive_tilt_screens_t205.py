"""T-205 unit tests — defensive-tilt signals (quality tilt + high-IVOL exclusion).

Deterministic, fixture-fed (no live SimFin / no network). Verifies the
composable signal contracts: quality score ranks by gp/roic, the tilt
picks the top quantile, IVOL exclusion drops the high-vol quantile, and
both abstain below the universe floor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engines.engine_a_alpha.screens import defensive_tilt as dt


def _panel(rows):
    """Build a minimal SimFin-shaped panel: MultiIndex (Ticker, Report Date)
    with publish_date + the columns the quality formulas read."""
    recs = []
    for tkr, gp, oi, assets, equity, ltd in rows:
        # 4 identical quarterly publishes so ttm_sum(4) has clean data.
        for q in range(4):
            recs.append({
                "Ticker": tkr, "Report Date": pd.Timestamp("2023-01-01") + pd.offsets.QuarterEnd(q),
                "publish_date": pd.Timestamp("2023-02-01") + pd.offsets.QuarterEnd(q),
                "gross_profit": gp, "operating_income": oi,
                "total_assets": assets, "total_equity": equity, "long_term_debt": ltd,
            })
    df = pd.DataFrame(recs).set_index(["Ticker", "Report Date"])
    return df


def _price_map(vol_by_ticker, n=60):
    """Synthetic price frames with controlled daily vol per ticker."""
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2023-01-01", periods=n)
    out = {}
    for tkr, dvol in vol_by_ticker.items():
        rets = rng.normal(0, dvol, n)
        closes = 100 * np.exp(np.cumsum(rets))
        out[tkr] = pd.DataFrame({"Close": closes}, index=idx)
    return out


def test_quality_score_ranks_by_gp_and_roic():
    # A: high gp + high roic; B: mid; C: low. (assets/equity equal → gp & roic monotone)
    rows = [(t, gp, oi, 1000.0, 500.0, 0.0) for t, gp, oi in
            [(f"T{i}", gp, gp) for i, gp in enumerate([10, 20, 30, 40, 50,
                                                       60, 70, 80, 90, 100,
                                                       110, 120, 130, 140, 150,
                                                       160, 170, 180, 190, 200,
                                                       210, 220, 230, 240, 250,
                                                       260, 270, 280, 290, 300,
                                                       310, 320])]]
    panel = _panel(rows)
    dmap = {t: pd.DataFrame({"Close": [1.0]}, index=[pd.Timestamp("2024-01-01")]) for t, *_ in rows}
    scores = dt.quality_score(dmap, pd.Timestamp("2024-06-01"), panel=panel, min_universe=30)
    assert len(scores) == 32
    # Highest gp/oi ticker (T31, gp=320) must score top; lowest (T0) bottom.
    assert scores["T31"] == max(scores.values())
    assert scores["T0"] == min(scores.values())


def test_quality_tilt_picks_top_quantile():
    rows = [(f"T{i}", float(10 * (i + 1)), float(10 * (i + 1)), 1000.0, 500.0, 0.0)
            for i in range(40)]
    panel = _panel(rows)
    dmap = {t: pd.DataFrame({"Close": [1.0]}, index=[pd.Timestamp("2024-01-01")]) for t, *_ in rows}
    longs = dt.quality_tilt_longs(dmap, pd.Timestamp("2024-06-01"),
                                  quality_quantile=0.25, panel=panel, min_universe=30)
    # ~top 25% of 40 = ~10 names, all from the high-gp end (T30..T39).
    assert 8 <= len(longs) <= 12
    assert all(int(t[1:]) >= 28 for t in longs), longs


def test_quality_abstains_below_universe_floor():
    rows = [(f"T{i}", 100.0, 100.0, 1000.0, 500.0, 0.0) for i in range(10)]
    panel = _panel(rows)
    dmap = {t: pd.DataFrame({"Close": [1.0]}, index=[pd.Timestamp("2024-01-01")]) for t, *_ in rows}
    assert dt.quality_score(dmap, pd.Timestamp("2024-06-01"), panel=panel, min_universe=30) == {}


def test_high_ivol_exclusion_drops_high_vol_quantile():
    # 40 tickers, vol increasing with index → top quantile = highest indices.
    vols = {f"T{i}": 0.005 * (i + 1) for i in range(40)}
    dmap = _price_map(vols, n=60)
    excl = dt.high_ivol_exclusion(dmap, pd.Timestamp("2023-12-31"),
                                  ivol_cutoff=0.75, lookback=30, min_universe=30)
    # ~top 25% excluded (~10 names), all from the high-vol end.
    assert 6 <= len(excl) <= 14
    assert all(int(t[1:]) >= 26 for t in excl), excl
    # A low-vol name is retained.
    assert "T0" not in excl


def test_ivol_abstains_below_floor():
    vols = {f"T{i}": 0.01 for i in range(10)}
    dmap = _price_map(vols, n=60)
    assert dt.high_ivol_exclusion(dmap, pd.Timestamp("2023-12-31"), min_universe=30) == set()


def test_signals_are_pure_not_wired():
    # Contract guard: the production backtest path must not import these
    # screens (OFF-by-construction → canon unchanged). If a future wiring
    # adds them to the live path, this test should be updated alongside a
    # propose-first decision.
    import importlib
    bc = importlib.import_module("backtester.backtest_controller")
    src = importlib.util.find_spec("backtester.backtest_controller").origin
    text = open(src).read()
    assert "screens.defensive_tilt" not in text and "defensive_tilt" not in text
