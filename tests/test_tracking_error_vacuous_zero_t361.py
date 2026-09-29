# tests/test_tracking_error_vacuous_zero_t361.py
"""T-361 — a tracking error over NO positions is UNDEFINED, not perfect.

R's liveness sweep flagged account-3's `exec.te` as 17/17 None. Reading the live
artifact (`paper_state_ai_trader/.../llm_analyst_tracking.json`, 19 points) the
picture is slightly different and worse:

    2026-08-26  te=0    held_w={}                      target_w={}
    2026-09-04  te=0.0  held_w={'SPY': 0.0}            target_w={'SPY': 0.0}
    2026-09-09  te=0.0  held_w={'GLD':0,'SPY':0.0766}  target_w={'GLD':0,'SPY':0.0766}

te computes on 3 of 19 — and the 08-26 point is a sum over an EMPTY set, which
is 0.0. Gate (a) reads that as "tracked its targets exactly". A vacuous zero
wearing the look of a measurement, which is the silent-zero class again.

A real 0.0 over real names (09-09, and account-2's points) is a TRUE
measurement and must keep computing — the fix distinguishes "no names" from
"names that match".
"""
from __future__ import annotations

from paper_trader.sleeve_tracker import SleeveTracker

CLOSES = {"SPY": 754.05, "AGG": 95.81, "GLD": 391.74}


def _te(tmp_path, target_w, held_w, name="t.json"):
    t = SleeveTracker(path=f"data/state/{name}", root=str(tmp_path))
    t.record("2026-09-22", 100_000.0, CLOSES,
             target_weights=target_w, held_weights=held_w)
    return t._load()[-1]["exec"]["te"]


def test_an_empty_comparison_is_UNDEFINED_not_zero(tmp_path):
    """THE REGRESSION, from the 2026-08-26 point."""
    assert _te(tmp_path, {}, {}, "a.json") is None


def test_a_real_zero_over_real_names_still_measures(tmp_path):
    """Account-2 tracks its targets exactly most days; that 0.0 is a fact and
    must not be swallowed by the fix."""
    assert _te(tmp_path, {"VOO": 0.8319, "MTUM": 0.1499},
               {"VOO": 0.8319, "MTUM": 0.1499}, "b.json") == 0.0


def test_a_real_drift_still_measures(tmp_path):
    assert _te(tmp_path, {"SPY": 0.5}, {"SPY": 0.4}, "c.json") == 0.1


def test_held_weights_None_remains_no_data_not_full_drift(tmp_path):
    """The pre-existing rebalance-morning rule, unchanged: a book that has not
    settled yet is no-data, never a spurious full-weight drift."""
    assert _te(tmp_path, {"SPY": 0.5}, None, "d.json") is None
