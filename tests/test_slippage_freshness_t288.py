# tests/test_slippage_freshness_t288.py
"""T-288 — gate-(b) slippage may ONLY measure fills that happened after the
arrival price was captured.

The bug this locks out: `client_order_id` is a deterministic hash of
(trade_date, ticker, side, qty, config) and `target_qty` is computed off the
prior CLOSE, so a same-day re-submit produces the SAME coid, the broker returns
the ALREADY-FILLED order, and its hours-old fill price is measured against a
fresh arrival — fabricating a 146 bps "SSO slippage" that was pure artifact.
"""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

from scripts.run_paper_cloud_day import _fresh_fill_slippage_bps

ARRIVAL_TS = dt.datetime(2026, 7, 8, 17, 20, 0, tzinfo=dt.timezone.utc)


def _order(ticker, fill, filled_at, qty=10):
    return SimpleNamespace(ticker=ticker, filled_avg_price=fill,
                           filled_qty=qty, filled_at=filled_at)


def test_fresh_fill_is_measured():
    # filled 2s AFTER arrival capture → real execution, real slippage
    o = _order("SPY", 100.05, "2026-07-08T17:20:02+00:00")
    bps = _fresh_fill_slippage_bps([o], {"SPY": 100.00}, ARRIVAL_TS)
    assert bps == 5.0                      # |100.05-100|/100 * 1e4


def test_stale_fill_is_excluded_not_fabricated(capsys):
    # THE REGRESSION: filled hours BEFORE arrival capture (re-discovered coid).
    o = _order("SSO", 66.04, "2026-07-08T15:30:44+00:00")
    bps = _fresh_fill_slippage_bps([o], {"SSO": 67.02}, ARRIVAL_TS)
    assert bps is None                     # would have been ~146 bps of nonsense
    assert "EXCLUDED" in capsys.readouterr().err


def test_missing_filled_at_is_excluded_fail_closed():
    # unknown fill time ⇒ cannot prove freshness ⇒ no sample (never assume fresh)
    o = _order("SPY", 100.05, None)
    assert _fresh_fill_slippage_bps([o], {"SPY": 100.00}, ARRIVAL_TS) is None


def test_unparseable_filled_at_is_excluded():
    o = _order("SPY", 100.05, "not-a-timestamp")
    assert _fresh_fill_slippage_bps([o], {"SPY": 100.00}, ARRIVAL_TS) is None


def test_no_arrival_ts_means_no_sample():
    o = _order("SPY", 100.05, "2026-07-08T17:20:02+00:00")
    assert _fresh_fill_slippage_bps([o], {"SPY": 100.00}, None) is None


def test_mixed_batch_counts_only_fresh_fills():
    fresh = _order("SPY", 100.05, "2026-07-08T17:20:03+00:00")   # 5 bps
    stale = _order("SSO", 66.04, "2026-07-08T15:30:44+00:00")    # excluded
    bps = _fresh_fill_slippage_bps([fresh, stale],
                                   {"SPY": 100.00, "SSO": 67.02}, ARRIVAL_TS)
    assert bps == 5.0            # mean over the FRESH fill only, stale dropped


def test_zulu_suffix_and_naive_timestamps_handled():
    z = _order("SPY", 100.05, "2026-07-08T17:20:02Z")
    assert _fresh_fill_slippage_bps([z], {"SPY": 100.00}, ARRIVAL_TS) == 5.0
    naive = _order("SPY", 100.05, "2026-07-08T17:20:02")   # assumed UTC
    assert _fresh_fill_slippage_bps([naive], {"SPY": 100.00}, ARRIVAL_TS) == 5.0
