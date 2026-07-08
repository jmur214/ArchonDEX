"""Named regression guard for the silent-calendar-hole bug family (T-294, caught in T-297).

Sibling of tests/test_contracts.py: same disease (a silent default/coercion masks a real mismatch),
different surface. Here the "silent default" is `Series.reindex(common)` quietly dropping benchmark days.

The load-bearing test is `test_t294_bond_synth_holes_would_halt`, which reproduces the ACTUAL defect:
the DGS10 bond synth is missing 48 SPY trading days, and T-294 reindexed the buy-hold-SPY bar onto that
holey calendar — reading $64,421 instead of the true $74,104.
"""
import csv
import pathlib
from datetime import datetime

import pandas as pd
import pytest

from core.calendar_guard import (CalendarHoleError, assert_no_calendar_holes, reindex_onto,
                                 safe_common_index)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _bdays(start, n):
    return pd.bdate_range(start, periods=n)


def test_clean_intersection_passes():
    bench = _bdays('2020-01-01', 100)
    assert_no_calendar_holes(bench, bench, benchmark_name='spy')          # identical
    assert_no_calendar_holes(bench, bench[10:90], benchmark_name='spy')   # shorter WINDOW is fine


def test_hole_in_the_middle_halts():
    bench = _bdays('2020-01-01', 100)
    holey = bench.delete([25, 26, 77])                                     # 3 days punched out
    with pytest.raises(CalendarHoleError) as e:
        assert_no_calendar_holes(bench, holey, benchmark_name='spy', common_name='common')
    msg = str(e.value)
    assert 'drops 3 trading day(s)' in msg
    assert 'NN-FAIL-CLOSED' in msg
    assert 'reindex_onto' in msg          # the error must name the fix


def test_allow_tolerance_is_explicit_and_off_by_default():
    bench = _bdays('2020-01-01', 50)
    holey = bench.delete([7])
    with pytest.raises(CalendarHoleError):
        assert_no_calendar_holes(bench, holey)                 # default allow=0 -> fail closed
    assert_no_calendar_holes(bench, holey, allow=1)            # explicit opt-in only


def test_safe_common_index_halts_when_aux_series_holes_the_benchmark():
    bench = pd.Series(1.0, index=_bdays('2020-01-01', 60))
    aux = pd.Series(1.0, index=bench.index.delete([5, 6]))     # aux missing 2 benchmark days
    with pytest.raises(CalendarHoleError):
        safe_common_index({'spy': bench, 'bond': aux}, benchmark_key='spy')


def test_reindex_onto_is_the_fix_and_preserves_every_benchmark_day():
    bench = pd.Series(1.0, index=_bdays('2020-01-01', 60))
    aux = pd.Series(range(58), index=bench.index.delete([5, 6]), dtype=float)
    fixed = reindex_onto(bench.index, aux)
    assert len(fixed) == len(bench)                            # benchmark keeps ALL its days
    assert fixed.notna().all()                                 # holes filled forward, not dropped
    assert_no_calendar_holes(bench.index, fixed.index, benchmark_name='spy')   # now passes


def _load_spy_index():
    p = ROOT / 'data' / 'processed' / 'SPY_1d.csv'
    if not p.exists():
        pytest.skip('SPY substrate not present')
    rows = list(csv.DictReader(open(p)))
    idx = [datetime.strptime(r['Date'][:10], '%Y-%m-%d') for r in rows if r.get('Close')]
    return pd.DatetimeIndex(sorted(idx))


def _load_bond_index():
    p = ROOT / 'data' / 'research' / 'bond_synth_dgs10_t255.csv'
    if not p.exists():
        pytest.skip('bond synth not present')
    d = pd.read_csv(p, index_col=0)
    return pd.DatetimeIndex(pd.to_datetime(d.index)).sort_values()


def test_t294_bond_synth_holes_would_halt():
    """THE regression: T-294 intersected the bond synth into the SPY bar's calendar and lost 48 days,
    reading the buy-hold-SPY bar as $64,421 instead of $74,104. The guard must HALT on that exact case."""
    spy, bond = _load_spy_index(), _load_bond_index()
    lo, hi = pd.Timestamp('2000-08-30'), pd.Timestamp('2026-04-17')
    spy_w = spy[(spy >= lo) & (spy <= hi)]
    common = spy_w.intersection(bond)                       # what T-294 actually did
    missing = spy_w.difference(common)
    assert len(missing) > 0, 'expected the bond synth to be missing SPY trading days'
    with pytest.raises(CalendarHoleError) as e:
        assert_no_calendar_holes(spy_w, common, benchmark_name='spy_tr', common_name='t294_common')
    assert f'drops {len(missing)} trading day(s)' in str(e.value)


def test_t294_fix_pattern_restores_the_full_calendar():
    """Projecting the bond synth ONTO the SPY calendar (the fix) keeps every benchmark day."""
    spy, bond = _load_spy_index(), _load_bond_index()
    lo, hi = pd.Timestamp('2000-08-30'), pd.Timestamp('2026-04-17')
    spy_w = spy[(spy >= lo) & (spy <= hi)]
    bond_s = pd.Series(1.0, index=bond)
    fixed = reindex_onto(spy_w, bond_s)
    assert_no_calendar_holes(spy_w, fixed.index, benchmark_name='spy_tr')   # must not raise
    assert len(fixed) == len(spy_w)
