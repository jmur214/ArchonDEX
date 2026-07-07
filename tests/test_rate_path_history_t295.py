# tests/test_rate_path_history_t295.py
"""T-2026-07-08-295 — the FedWatch two-outcome math + the idempotent append.
Pure-function tests (no network); the fetch paths are integration-smoked by
running the script."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.build_rate_path_history_t295 import (
    _two_outcome_prob, _append, MONTH_CODE,
)

# A meeting on the 15th of a 30-day month (2026-09-15): n_before = n_after = 15.
SEP15 = pd.Timestamp("2026-09-15")


def _price_for(r_start, r_end, decision=SEP15):
    """Inverse of the method: the contract price that a given post-meeting rate
    implies, so the test drives KNOWN outcomes through the solver."""
    N = decision.days_in_month
    nb = decision.day
    avg = (nb * r_start + (N - nb) * r_end) / N
    return 100.0 - avg


class TestTwoOutcome:
    def test_fully_priced_25bp_cut(self):
        px = _price_for(3.63, 3.38)                 # market fully prices a 25bp cut
        r = _two_outcome_prob(px, 3.63, SEP15)
        assert r["direction"] == "cut"
        assert r["prob_25bp_move"] == pytest.approx(1.0, abs=1e-6)
        assert r["implied_post_rate"] == pytest.approx(3.38, abs=1e-6)
        assert r["implied_change_bp"] == pytest.approx(-25.0, abs=1e-2)

    def test_half_priced_cut(self):
        px = _price_for(3.63, 3.505)                # 12.5bp priced → prob 0.5
        r = _two_outcome_prob(px, 3.63, SEP15)
        assert r["prob_25bp_move"] == pytest.approx(0.5, abs=1e-6)
        assert r["direction"] == "cut"

    def test_no_change(self):
        px = _price_for(3.63, 3.63)                 # month avg == r_start
        r = _two_outcome_prob(px, 3.63, SEP15)
        assert r["prob_25bp_move"] == pytest.approx(0.0, abs=1e-6)
        assert r["direction"] == "hold"

    def test_hike_direction(self):
        px = _price_for(3.63, 3.88)                 # 25bp hike
        r = _two_outcome_prob(px, 3.63, SEP15)
        assert r["direction"] == "hike"
        assert r["prob_25bp_move"] == pytest.approx(1.0, abs=1e-6)

    def test_overpriced_move_clips_to_one(self):
        px = _price_for(3.63, 3.13)                 # 50bp priced → clipped, NOT 2.0
        r = _two_outcome_prob(px, 3.63, SEP15)
        assert r["prob_25bp_move"] == 1.0           # two-outcome CANNOT exceed 1

    def test_meeting_on_last_day_returns_empty(self):
        # decision on the final day of the month → n_after == 0 → undefined split
        last = pd.Timestamp("2026-09-30")
        assert _two_outcome_prob(96.4, 3.63, last) == {}


class TestAppendIdempotent:
    def test_dedup_on_keys_keeps_last(self, tmp_path):
        p = tmp_path / "x.parquet"
        df1 = pd.DataFrame({"date": ["2026-07-08"], "series_type": ["a"], "v": [1]})
        assert _append(df1, p, ["date", "series_type"]) == 1
        # same key, new value → replaces, not duplicates
        df2 = pd.DataFrame({"date": ["2026-07-08"], "series_type": ["a"], "v": [2]})
        assert _append(df2, p, ["date", "series_type"]) == 1
        assert pd.read_parquet(p)["v"].iloc[0] == 2
        # distinct key → grows
        df3 = pd.DataFrame({"date": ["2026-07-09"], "series_type": ["a"], "v": [3]})
        assert _append(df3, p, ["date", "series_type"]) == 2


def test_month_code_mapping_complete():
    assert MONTH_CODE[9] == "U" and MONTH_CODE[12] == "Z" and MONTH_CODE[1] == "F"
    assert len(MONTH_CODE) == 12
