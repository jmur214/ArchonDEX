"""Calendar guard — `[NN-FAIL-CLOSED]` protection against the silent-calendar-hole bug family.

THE BUG (T-294, 2026-07-08). A measurement harness builds a "common" index by intersecting several
series, then reindexes EVERY series — including the benchmark — onto it:

    common = arms[0].index
    for a in arms[1:]: common = common.intersection(a.index)   # a bond synth missing 48 SPY days
    bh_spy = spy_returns.reindex(common)                        # <-- the BAR silently loses 48 days

Nothing raises. The benchmark simply compounds over fewer days, so it reads LOW, and because a
2x-levered arm loses ~2x the return on each dropped up-day, the *relative* comparison distorts too.
In T-294 this made the buy-hold-SPY bar read $64,421 instead of $74,104, and the offense config's edge
read +0.45%/yr instead of +0.25%/yr — a merged audit with wrong magnitudes (verdict survived; luck).

THE RULE. A benchmark series must never silently inherit another series' holes. If an intersected
calendar drops trading days from the benchmark, that is a measurement defect: **HALT, do not reindex.**

THE FIX PATTERN. Do not intersect a short/holey series into the benchmark's calendar — project it ONTO
the benchmark calendar instead (`reindex_onto`), so the benchmark keeps every one of its days.
"""
from __future__ import annotations
import pandas as pd


class CalendarHoleError(AssertionError):
    """Raised when a common/intersected index drops trading days from the benchmark series."""


def assert_no_calendar_holes(benchmark_index, common_index, *, benchmark_name: str = 'benchmark',
                             common_name: str = 'common', allow: int = 0):
    """HALT if `common_index` drops days from `benchmark_index` inside the common date range.

    Compares only within [common.min(), common.max()] — a shorter *window* is fine; *holes* are not.

    Args:
        benchmark_index: the benchmark series' own trading calendar (DatetimeIndex).
        common_index:    the intersected/aligned index the harness intends to use.
        allow:           max tolerated dropped days (default 0 — fail closed).

    Raises:
        CalendarHoleError: if more than `allow` benchmark days fall inside the common window but are
            absent from `common_index`.
    """
    b = pd.DatetimeIndex(benchmark_index)
    c = pd.DatetimeIndex(common_index)
    if len(c) == 0 or len(b) == 0:
        raise CalendarHoleError(f"empty index: {benchmark_name}={len(b)}, {common_name}={len(c)}")
    window = b[(b >= c.min()) & (b <= c.max())]
    missing = window.difference(c)
    if len(missing) > allow:
        head = ', '.join(str(d.date()) for d in missing[:5])
        raise CalendarHoleError(
            f"[NN-FAIL-CLOSED] '{common_name}' drops {len(missing)} trading day(s) from '{benchmark_name}' "
            f"inside {c.min().date()}..{c.max().date()} (allow={allow}). "
            f"A benchmark must never inherit another series' calendar holes — its compounding, and every "
            f"levered-vs-unlevered comparison against it, silently distorts. "
            f"First missing: {head}. Fix: project the short series ONTO the benchmark calendar "
            f"(core.calendar_guard.reindex_onto), do not intersect it into the benchmark."
        )
    return c


def reindex_onto(calendar, series: pd.Series, *, method: str = 'ffill') -> pd.Series:
    """The fix pattern: project `series` onto `calendar` (the benchmark's days), never the reverse.

    Use for auxiliary series (macro rates, synthetic bond curves) whose calendars are incidental.
    """
    return series.reindex(pd.DatetimeIndex(calendar)).ffill() if method == 'ffill' \
        else series.reindex(pd.DatetimeIndex(calendar), method=method)


def safe_common_index(series_map: dict, benchmark_key: str, *, allow: int = 0):
    """Intersect the indices in `series_map`, then HALT unless the benchmark keeps all its days."""
    idx = None
    for s in series_map.values():
        i = pd.DatetimeIndex(s.dropna().index)
        idx = i if idx is None else idx.intersection(i)
    return assert_no_calendar_holes(series_map[benchmark_key].dropna().index, idx,
                                    benchmark_name=benchmark_key, allow=allow)
