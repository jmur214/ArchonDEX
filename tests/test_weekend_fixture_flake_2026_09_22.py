"""The weekend flake — a test whose fixture consults the real calendar.

Found by the janitor's forensics instrument on its first real red night. The chain:
persisted failing NAME (09-19, 09-20) -> both dates are Sat/Sun -> `pd.date_range(
end=datetime.now(), periods=N, freq="B")` returns N-1 dates when `end` falls on a
weekend -> the price array, still built from `N`, no longer matches the index ->
"Length of values (200) does not match length of index (199)".

Same class as the 2026-09-02 month-rollover fixture: a test that passes on the days
someone happens to run it and fails on the days nobody is watching.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest


@pytest.mark.parametrize("day,name", [(18, "Fri"), (19, "Sat"), (20, "Sun"),
                                      (21, "Mon"), (22, "Tue"), (23, "Wed"), (24, "Thu")])
def test_the_mock_fixture_builds_on_EVERY_day_of_the_week(day, name, monkeypatch):
    """The fixture must not care what day it is run on."""
    import tests.test_alpha_pipeline as t

    class _Frozen(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, day, 3, 0)

    monkeypatch.setattr(t, "datetime", _Frozen)
    data_map, now = t.create_mock_data(["MOCK1"], days=200)
    df = data_map["MOCK1"]
    assert len(df) == len(df.index), "values and index must agree"
    assert df["Close"].notna().all()
    assert now == df.index[-1], "the returned `now` must be the fixture's last bar"


def test_business_day_range_really_does_shrink_on_a_weekend():
    """The pandas behaviour the fixture tripped on, pinned — so if a future pandas
    changes it, this fails loudly instead of the fixture silently starting to work
    for a different reason."""
    sat = dt.datetime(2026, 9, 19, 3, 0)
    fri = dt.datetime(2026, 9, 18, 3, 0)
    assert len(pd.date_range(end=sat, periods=200, freq="B")) == 199
    assert len(pd.date_range(end=fri, periods=200, freq="B")) == 200


def test_the_fixture_derives_length_from_the_INDEX_not_from_days():
    """The fix itself: `days` is a request, `len(dates)` is what pandas actually gave."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent / "test_alpha_pipeline.py").read_text()
    assert "n = len(dates)" in src
    assert "np.random.randn(n)" in src and "np.linspace(0, 20, n)" in src
    assert "np.random.randn(days)" not in src, "the old length source must not return"
