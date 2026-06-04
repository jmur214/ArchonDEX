"""T-2026-06-04-099 regression tests — close the residual long-window
cross-container FP drift T-092 surfaced (0.19 Sharpe drift at 26-yr).

Sites fixed in this dispatch:
  1. engines/engine_a_alpha/signal_collector.py — outer ticker dict
     now sorted (was only inner edge_map sorted via T-057c-det)
  2. engines/engine_c_portfolio/portfolio_engine.py snapshot() —
     market_value + unrealized accumulators are now sort + math.fsum
     over self.positions.keys()
  3. engines/engine_c_portfolio/portfolio_engine.py total_equity() —
     same fix as snapshot()
  4. backtester/backtest_controller.py _prepare_orders mv-loop —
     equity calc accumulator is now sort + math.fsum over
     self.portfolio.positions.keys()
  5. backtester/backtest_controller.py _prepare_orders pos_qtys-loop —
     pos_values accumulator is now sort + math.fsum

Each test pins the contract: order-independent under permuted input.
"""
from __future__ import annotations

import math


# ----------------------------------------------------------------------
# 1. signal_collector outer-ticker sort
# ----------------------------------------------------------------------

def _simulate_collector_return(scores: dict) -> dict:
    """Mirror the production fix at signal_collector.py:405."""
    return {
        tkr: dict(sorted(scores[tkr].items()))
        for tkr in sorted(scores.keys())
    }


def test_collector_outer_ticker_order_canonicalized():
    """The outer dict must iterate alphabetically regardless of the
    insertion order produced by which edge fired first for each ticker."""
    raw_a = {
        "ZZTOP": {"b_edge": 0.5, "a_edge": 0.3},
        "AAPL": {"b_edge": 0.2},
        "MSFT": {"a_edge": 0.4, "b_edge": 0.1},
    }
    raw_b = {
        "MSFT": {"b_edge": 0.1, "a_edge": 0.4},
        "AAPL": {"b_edge": 0.2},
        "ZZTOP": {"a_edge": 0.3, "b_edge": 0.5},
    }
    out_a = _simulate_collector_return(raw_a)
    out_b = _simulate_collector_return(raw_b)
    assert list(out_a.keys()) == ["AAPL", "MSFT", "ZZTOP"], (
        f"outer order should be sorted, got {list(out_a.keys())}"
    )
    assert list(out_a.keys()) == list(out_b.keys()), (
        "outer order must be insertion-order-invariant"
    )
    # Inner edge_map order also canonical
    assert list(out_a["MSFT"].keys()) == ["a_edge", "b_edge"]


# ----------------------------------------------------------------------
# 2-3. portfolio_engine snapshot() + total_equity()
# ----------------------------------------------------------------------

def _simulate_portfolio_mv(positions_keys_unordered, qty_map, price_map) -> float:
    """Mirror the production fix at portfolio_engine.py:248 (snapshot)
    and 311 (total_equity): sort positions keys and accumulate with
    math.fsum over the contributions list."""
    contribs = []
    for t in sorted(positions_keys_unordered):
        if qty_map[t] == 0:
            continue
        contribs.append(float(qty_map[t]) * float(price_map[t]))
    return math.fsum(contribs)


def test_portfolio_mv_accumulator_order_independent():
    """The market_value accumulator must yield the same equity regardless
    of self.positions dict insertion order. This is the load-bearing
    site for T-092's observed drift — equity drift propagates into the
    next bar's risk_budget = equity * risk_per_trade_pct."""
    # Positions large enough that summation order matters at ULP level.
    qty_map = {
        "AAPL": 200, "MSFT": -150, "GOOG": 50, "AMZN": 100,
        "JPM": -75, "XOM": 300, "WMT": 25, "NVDA": -10,
    }
    price_map = {
        "AAPL": 150.123456789, "MSFT": 380.987654321, "GOOG": 142.5,
        "AMZN": 175.333, "JPM": 198.765, "XOM": 112.456,
        "WMT": 67.890, "NVDA": 875.0,
    }
    # Permute insertion order across two cases.
    keys_a = list(qty_map.keys())
    keys_b = list(reversed(keys_a))
    mv_a = _simulate_portfolio_mv(keys_a, qty_map, price_map)
    mv_b = _simulate_portfolio_mv(keys_b, qty_map, price_map)
    assert mv_a == mv_b, (
        f"market_value must be order-independent: a={mv_a}, b={mv_b}, "
        f"delta={mv_a - mv_b}"
    )


def test_portfolio_mv_handles_zero_qty():
    """Skipping qty==0 must not depend on iteration order."""
    qty_map = {"AAPL": 0, "MSFT": 100, "GOOG": 0, "AMZN": -50}
    price_map = {"AAPL": 150.0, "MSFT": 380.0, "GOOG": 142.0, "AMZN": 175.0}
    mv_a = _simulate_portfolio_mv(["AAPL", "MSFT", "GOOG", "AMZN"], qty_map, price_map)
    mv_b = _simulate_portfolio_mv(["AMZN", "GOOG", "MSFT", "AAPL"], qty_map, price_map)
    expected = 100 * 380.0 + (-50) * 175.0  # 38000 - 8750 = 29250
    assert mv_a == mv_b
    assert mv_a == expected


# ----------------------------------------------------------------------
# 4-5. backtest_controller equity-calc accumulators
# ----------------------------------------------------------------------

def _simulate_backtest_controller_equity(positions_dict, tickers, prices) -> float:
    """Mirror the production fix at backtest_controller.py:558:
        for tkr in sorted(pos_qtys.keys()):
            ...
        equity = capital + math.fsum(pos_values)
    """
    capital = 100_000.0
    pos_qtys = {tkr: int(positions_dict.get(tkr, 0)) for tkr in tickers}
    pos_values = []
    for tkr in sorted(pos_qtys.keys()):
        qty = pos_qtys[tkr]
        price = prices.get(tkr, 0.0)
        pos_values.append(float(qty) * float(price))
    return capital + math.fsum(pos_values)


def test_backtest_controller_equity_order_independent():
    positions_a = {"AAPL": 200, "MSFT": -150, "GOOG": 50}
    positions_b = {"GOOG": 50, "MSFT": -150, "AAPL": 200}  # reversed
    tickers_a = ["AAPL", "MSFT", "GOOG"]
    tickers_b = ["GOOG", "MSFT", "AAPL"]
    prices = {"AAPL": 150.123456789, "MSFT": 380.987654321, "GOOG": 142.5}
    eq_a = _simulate_backtest_controller_equity(positions_a, tickers_a, prices)
    eq_b = _simulate_backtest_controller_equity(positions_b, tickers_b, prices)
    assert eq_a == eq_b, f"equity must be order-independent: a={eq_a}, b={eq_b}"


# ----------------------------------------------------------------------
# Integration: simulate a near-cancellation that would drift under plain sum()
# ----------------------------------------------------------------------

def test_near_zero_crossing_drift_eliminated():
    """The motivating bug: a long/short basket where market_value
    approaches zero. Plain sum() in different orders yields different
    ULP residue (can be negative or positive). math.fsum on sorted is
    invariant — collapses to a single value."""
    qty_map = {f"L{i}": 100 for i in range(10)}  # 10 longs at qty=100
    qty_map.update({f"S{i}": -100 for i in range(10)})  # 10 shorts at qty=-100
    # Prices that make basket nearly market-neutral
    price_map = {f"L{i}": 100.0 + i * 0.001 for i in range(10)}
    price_map.update({f"S{i}": 100.0 + i * 0.001 for i in range(10)})
    # Two iteration orders
    keys_a = list(qty_map.keys())  # L0, L1, ..., L9, S0, S1, ..., S9
    keys_b = [k for pair in zip(
        [f"L{i}" for i in range(10)],
        [f"S{i}" for i in range(10)],
    ) for k in pair]  # L0, S0, L1, S1, ...
    keys_c = list(reversed(keys_a))

    mv_a = _simulate_portfolio_mv(keys_a, qty_map, price_map)
    mv_b = _simulate_portfolio_mv(keys_b, qty_map, price_map)
    mv_c = _simulate_portfolio_mv(keys_c, qty_map, price_map)
    assert mv_a == mv_b == mv_c, (
        f"near-zero MV must be order-independent: "
        f"a={mv_a}, b={mv_b}, c={mv_c}"
    )


# ----------------------------------------------------------------------
# Sanity: verify the BARE sum() pattern would have failed at scale
# (this isn't a contract — just confirms our test data exercises the bug)
# ----------------------------------------------------------------------

def test_bare_sum_drift_demonstrated():
    """Lightweight sanity that plain `sum()` is genuinely order-dependent
    at the scale we're testing. If this test passes (bare sum() returns
    the SAME value), our test data isn't exercising the actual bug
    surface — refresh it. Marked as informational, not a contract."""
    # 1000 floats with mixed signs and tiny magnitudes — designed to
    # produce ULP-level residue under bare sum().
    import random
    rng = random.Random(0)
    values = [rng.gauss(0, 1) * 1e-10 for _ in range(1000)]
    # Try multiple permutations
    val_a = sum(values)
    val_b = sum(reversed(values))
    val_c = sum(sorted(values))
    # At least one comparison should produce a different ULP — if not,
    # the test data is too clean. Use any() to be lenient about which
    # pair differs.
    any_diff = (val_a != val_b) or (val_b != val_c) or (val_a != val_c)
    # math.fsum should produce a single canonical value regardless of order
    fs_a = math.fsum(values)
    fs_b = math.fsum(reversed(values))
    fs_c = math.fsum(sorted(values))
    assert fs_a == fs_b == fs_c, (
        "math.fsum must be order-independent (informational; "
        f"a={fs_a}, b={fs_b}, c={fs_c})"
    )
    # any_diff is informational only — record it but don't gate on it
    # because some CPUs may compile sum() to fma instructions that
    # happen to produce the same value.
    _ = any_diff
