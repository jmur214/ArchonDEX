"""The B-1 post-hoc exposure re-score (scripts/rescore_b1_ey_exposure.py)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import rescore_b1_ey_exposure as rs
from tests.test_raw_signal_decile_b1 import _census, _panel, _spy_root

FAM = ["value_book_to_market_v1", "value_earnings_yield_v1", "quality_gross_profitability_v1",
       "quality_roic_v1", "accruals_inv_sloan_v1", "accruals_inv_asset_growth_v1"]


def _recorded(n_months, ey_p=0.36):
    rows = [{"signal": s, "family": "short_window", "ic_p": (ey_p if s == rs.SIGNAL else 0.8)}
            for s in FAM]
    return {"rows": rows, "benchmarks": {"short_window": {"n_months": n_months}}}


def _planted_panel(spy, tilt_three: bool):
    """value_earnings_yield_v1 is noise for everyone EXCEPT the three, which are planted at
    the top of the signal with large next-month returns. Removing them must remove the
    planted relationship — the re-score sees only the other names."""
    def ey(rng, n, fwd):
        v = rng.normal(size=n)
        if tilt_three:
            v[:3] = 10.0
        return v
    p = _panel(spy, cols={rs.SIGNAL: ey})
    names = sorted(p.index.get_level_values("ticker").unique())[:3]
    p = p.rename(index=dict(zip(names, rs.REMOVED)), level="ticker")
    if tilt_three:
        idx = p.index.get_level_values("ticker").isin(rs.REMOVED)
        p.loc[idx, "__fwd_ret_1m"] = 0.30
    return p


def test_the_three_are_REMOVED_and_the_family_is_the_short_window_six(tmp_path):
    root, spy = _spy_root(tmp_path)
    p = _planted_panel(spy, tilt_three=True)
    cen = _census(p)
    months = len([m for m in p.index.get_level_values("month_end").unique()
                  if m >= pd.Timestamp("2021-07-01")])
    res, halts = rs.rescore(p, cen, _recorded(months), root, 0, 100, 6)
    assert halts == [], halts
    assert res["family"] == "short_window" and len(res["family_p_used"]) == 6
    assert res["rescored"]["n_months"] == months
    # with the planted three removed, what remains is noise — no clear, no change
    assert res["rescored"]["clears_ic"] is False
    assert res["decision"] == "no change to the verdict"
    # control: the same method WITHOUT the removal finds the plant (so the removal is what bites)
    from scripts import raw_signal_decile_b1 as h
    _, frames = h.window_frames(p, "2021-07", p.index.get_level_values(0).max())
    kept = h.evaluate_signal(rs.SIGNAL, False, frames, np.zeros(months), np.zeros(months),
                             [fr.index for fr in frames], 0, 50, 6)
    assert kept["ic_t_nw"] > res["rescored"]["ic_t_nw"] + 2


def test_a_rescore_that_CLEARS_is_labelled_CONTAMINATED_never_clear(tmp_path):
    root, spy = _spy_root(tmp_path)
    p = _panel(spy, cols={rs.SIGNAL: lambda rng, n, fwd: fwd + rng.normal(0, 0.02, n)})
    names = sorted(p.index.get_level_values("ticker").unique())[:3]
    p = p.rename(index=dict(zip(names, rs.REMOVED)), level="ticker")
    months = len([m for m in p.index.get_level_values("month_end").unique()
                  if m >= pd.Timestamp("2021-07-01")])
    res, halts = rs.rescore(p, _census(p), _recorded(months), root, 0, 100, 6)
    assert halts == [], halts
    assert res["rescored"]["clears_ic"] is True
    assert res["decision"] == "CONTAMINATED — UNTESTED"


def test_a_panel_missing_one_of_the_three_HALTS(tmp_path):
    root, spy = _spy_root(tmp_path)
    p = _panel(spy, cols={rs.SIGNAL: lambda rng, n, fwd: rng.normal(size=n)})
    names = sorted(p.index.get_level_values("ticker").unique())[:2]
    p = p.rename(index=dict(zip(names, rs.REMOVED[:2])), level="ticker")
    _, halts = rs.rescore(p, _census(p), _recorded(42), root, 0, 50, 6)
    assert any("expected all of" in x for x in halts), halts
