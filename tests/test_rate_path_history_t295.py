# tests/test_rate_path_history_t295.py
"""T-295 / T-295e — the CORRECTED FedWatch meeting-move math + idempotent append.

Rewritten (T-295e) against the fixed method. The ORIGINAL tests covered the buggy
pre-fix `_two_outcome_prob` (single meeting-month decomposition, anchored to
today's EFFR for every meeting), which produced a spurious +284bp Oct-28 move and
was deleted by the fix. These tests target what replaced it — `_solve_meeting_move`:

  * in-month decomposition when the meeting is well-conditioned,
  * NEXT-MONTH contract read when the meeting is late in its month (tiny n_after,
    where the N/n_after leverage was the actual bug),
  * fail-closed skips (unavailable contract / contaminated next month /
    non-physical solve),
  * and the CHAINED anchoring (the caller feeds r_after forward as r_before).

Pure-function tests, no network.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.build_rate_path_history_t295 import (
    _solve_meeting_move, _append, MONTH_CODE, LATE_MONTH_NAFTER, MAX_MEETING_BP,
)

# A mid-month meeting in a 30-day month: n_before=15, n_after=15 → in-month path.
SEP15 = pd.Timestamp("2026-09-15")
# A LATE-month meeting: 2026-10-28 in a 31-day month → n_after=3 → next-month path.
OCT28 = pd.Timestamp("2026-10-28")


def _inmonth_price(r_before, r_after, decision=SEP15):
    """Inverse of the in-month solve: the contract price implying a given r_after,
    so tests drive KNOWN outcomes through the solver."""
    N, nb = decision.days_in_month, decision.day
    avg = (nb * r_before + (N - nb) * r_after) / N
    return 100.0 - avg


class TestInMonthPath:
    """Well-conditioned meetings decompose inside their own contract month."""

    def test_fully_priced_25bp_cut(self):
        r = _solve_meeting_move(_inmonth_price(3.63, 3.38), None, 3.63, SEP15, False)
        assert r["method"] == "fedwatch_two_outcome_inmonth"
        assert r["direction"] == "cut"
        assert r["implied_post_rate"] == pytest.approx(3.38, abs=1e-4)
        assert r["implied_change_bp"] == pytest.approx(-25.0, abs=1e-2)
        assert r["prob_25bp_move"] == pytest.approx(1.0, abs=1e-6)

    def test_half_priced_cut(self):
        r = _solve_meeting_move(_inmonth_price(3.63, 3.505), None, 3.63, SEP15, False)
        assert r["prob_25bp_move"] == pytest.approx(0.5, abs=1e-4)
        assert r["direction"] == "cut"

    def test_no_change_is_hold(self):
        r = _solve_meeting_move(_inmonth_price(3.63, 3.63), None, 3.63, SEP15, False)
        assert r["direction"] == "hold"
        assert r["prob_25bp_move"] == pytest.approx(0.0, abs=1e-6)

    def test_hike_direction(self):
        r = _solve_meeting_move(_inmonth_price(3.63, 3.88), None, 3.63, SEP15, False)
        assert r["direction"] == "hike"
        assert r["implied_change_bp"] == pytest.approx(+25.0, abs=1e-2)

    def test_overpriced_move_clips_to_one(self):
        # 50bp priced: the TWO-outcome prob cannot exceed 1 (it can't express 50bp)
        r = _solve_meeting_move(_inmonth_price(3.63, 3.13), None, 3.63, SEP15, False)
        assert r["prob_25bp_move"] == 1.0


class TestLateMonthPath:
    """THE BUG THIS FIX EXISTS FOR: a late-month meeting must NOT be decomposed
    in-month (tiny n_after ⇒ ~10x leverage on any error ⇒ the +284bp artifact)."""

    def test_late_month_reads_next_month_contract(self):
        assert OCT28.days_in_month - OCT28.day <= LATE_MONTH_NAFTER   # late by construction
        # next-month contract implies a whole month at 3.975% → that IS r_after
        r = _solve_meeting_move(96.09, 100.0 - 3.975, 3.9021, OCT28, False)
        assert r["method"] == "fedwatch_two_outcome_nextmonth"
        assert r["implied_post_rate"] == pytest.approx(3.975, abs=1e-4)
        # the increment at THIS meeting (chained anchor), not the move from today
        assert r["implied_change_bp"] == pytest.approx(7.29, abs=0.05)
        assert r["direction"] == "hike"

    def test_late_month_skips_when_next_month_also_meets(self):
        # next month's average would itself be contaminated by its own decision
        assert _solve_meeting_move(96.09, 96.02, 3.9021, OCT28, True) is None

    def test_late_month_skips_without_next_contract(self):
        assert _solve_meeting_move(96.09, None, 3.9021, OCT28, False) is None

    def test_regression_the_284bp_artifact_needed_BOTH_bugs(self):
        """Reproduce the ACTUAL observed defect and pin its mechanism.

        The +284bp Oct-28 artifact was NOT the late-month leverage alone: it took
        BOTH pre-fix bugs. (1) cumulative anchoring (every meeting anchored to
        TODAY's EFFR 3.63 instead of the chained 3.9021) injected the error, and
        (2) the late-month N/n_after ≈ 10.3x leverage amplified it into a
        non-physical number. Verified: old anchor → +289bp; chained anchor →
        +8bp. Both fixes are load-bearing, so both are pinned here."""
        N, nb = OCT28.days_in_month, OCT28.day
        leverage = N / (N - nb)
        assert leverage > 10                                   # the amplifier

        def inmonth(r_before):
            return ((100.0 - 96.09) * N - r_before * nb) / (N - nb) - r_before

        # BUG-1 (cumulative anchor) x BUG-2 (leverage) → the observed artifact
        assert inmonth(3.63) * 100 == pytest.approx(289, abs=5)
        assert abs(inmonth(3.63)) * 100 > MAX_MEETING_BP       # fail-closed would catch it
        # With ONLY the chaining fixed, the same formula is physical but still
        # ill-conditioned — which is WHY the next-month path exists.
        assert abs(inmonth(3.9021)) * 100 < 20


class TestFailClosed:
    def test_no_contract_skips(self):
        assert _solve_meeting_move(None, None, 3.63, SEP15, False) is None

    def test_non_physical_move_skipped(self):
        # a price implying a >150bp single-meeting move must be REFUSED, not emitted
        assert _solve_meeting_move(_inmonth_price(3.63, 5.63), None, 3.63, SEP15, False) is None


class TestChaining:
    """The caller anchors each meeting on the PRIOR meeting's post-rate, so the
    reported change is the INCREMENT at that meeting (the 2nd bug the fix closed)."""

    def test_sequential_increments_not_cumulative(self):
        r1 = _solve_meeting_move(_inmonth_price(3.63, 3.72), None, 3.63, SEP15, False)
        r_before2 = r1["_r_after"]                       # chain forward
        r2 = _solve_meeting_move(_inmonth_price(r_before2, 3.81), None, r_before2, SEP15, False)
        assert r1["implied_change_bp"] == pytest.approx(9.0, abs=0.1)
        # +9bp INCREMENT — not the +18bp cumulative move from the original anchor
        assert r2["implied_change_bp"] == pytest.approx(9.0, abs=0.1)
        assert r2["implied_post_rate"] == pytest.approx(3.81, abs=1e-4)


class TestAppendIdempotent:
    def test_dedup_on_keys_keeps_last(self, tmp_path):
        p = tmp_path / "x.parquet"
        df1 = pd.DataFrame({"date": ["2026-07-08"], "series_type": ["a"], "v": [1]})
        assert _append(df1, p, ["date", "series_type"]) == 1
        df2 = pd.DataFrame({"date": ["2026-07-08"], "series_type": ["a"], "v": [2]})
        assert _append(df2, p, ["date", "series_type"]) == 1
        assert pd.read_parquet(p)["v"].iloc[0] == 2
        df3 = pd.DataFrame({"date": ["2026-07-09"], "series_type": ["a"], "v": [3]})
        assert _append(df3, p, ["date", "series_type"]) == 2


def test_month_code_mapping_complete():
    assert MONTH_CODE[9] == "U" and MONTH_CODE[12] == "Z" and MONTH_CODE[1] == "F"
    assert len(MONTH_CODE) == 12
