# tests/test_position_buffering_t148.py
"""T-148 — Carver position buffering (trade-to-edge) tests.

Band semantics (no trade inside; trade to the EDGE outside, never the
center), whole-share edge rounding, zero-target close, composition with
T-139 dynamic optimization (buffering bands around dyn-opt's integer
book), scale invariance, Engine-B truncation parity, determinism,
fail-open, and the wiring inertness contract (flag OFF ⇒ identical
weights, module never imported).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

from engines.engine_c_portfolio.position_buffering import (
    apply_position_buffering,
)


def _res(weights, prices, current, equity=10_000.0, f=0.10):
    return apply_position_buffering(weights, prices, current, equity, f)


class TestBandSemantics:
    # equity 10_000, price 100 → 1 share = 1% weight. w=0.50 → N*=50,
    # band f=0.10 → [45, 55].
    W = {"AAA": 0.50}
    P = {"AAA": 100.0}

    @pytest.mark.parametrize("cur", [45, 50, 55])
    def test_inside_band_holds_current(self, cur):
        r = _res(self.W, self.P, {"AAA": cur})
        assert r.targets["AAA"] == cur
        assert r.suppressed == ["AAA"] and r.edge_trades == []
        # held position ⇒ weight implies exactly the current shares
        assert r.weights["AAA"] * 10_000 / 100.0 == pytest.approx(cur, abs=1e-9)

    @pytest.mark.parametrize("cur,expected_edge", [
        (40, 45),   # below → lower edge, NOT the 50 center
        (0, 45),    # flat → lower edge (initial entry is edge-sized)
        (60, 55),   # above → upper edge
        (100, 55),
    ])
    def test_outside_band_trades_to_edge_not_center(self, cur, expected_edge):
        r = _res(self.W, self.P, {"AAA": cur})
        assert r.targets["AAA"] == expected_edge
        assert r.edge_trades == ["AAA"]

    def test_zero_target_closes_fully(self):
        r = _res({"AAA": 0.0}, self.P, {"AAA": 30})
        assert r.targets["AAA"] == 0

    def test_short_target_band_is_symmetric(self):
        # w=-0.50 → N*=-50, band [-55, -45]
        r = _res({"AAA": -0.50}, self.P, {"AAA": -48})
        assert r.targets["AAA"] == -48          # inside
        r2 = _res({"AAA": -0.50}, self.P, {"AAA": -30})
        assert r2.targets["AAA"] == -45         # edge toward target

    def test_band_narrower_than_one_share_falls_back_to_nearest(self):
        # equity 1_000, price 100 → N* = 3 at w=0.30; band [2.7, 3.3]
        # contains 3. From cur=1 the lower edge 2.7 ceils to 3 — fine.
        # Force a no-integer band: w=0.345 → N*=3.45, band [3.105,3.795]
        # has NO integer; from cur=1 → fallback round(N*)=3.
        r = apply_position_buffering(
            {"AAA": 0.345}, {"AAA": 100.0}, {"AAA": 1}, 1_000.0, 0.10
        )
        assert r.targets["AAA"] == 3

    def test_buffered_trade_is_smaller_than_full_rebalance(self):
        r = _res(self.W, self.P, {"AAA": 30})
        assert r.shares_traded_buffered < r.shares_traded_unbuffered
        assert r.notional_traded_buffered < r.notional_traded_unbuffered
        assert r.shares_traded_buffered == 15      # 30 → 45 (edge)
        assert r.shares_traded_unbuffered == 20    # 30 → 50 (center)


class TestEngineBParity:
    def test_truncation_lands_on_buffered_integers(self):
        weights = {"AAA": 0.50, "BBB": 0.31}
        prices = {"AAA": 100.0, "BBB": 47.0}
        current = {"AAA": 30, "BBB": 80}
        equity = 10_000.0
        r = _res(weights, prices, current, equity)
        for t, n in r.targets.items():
            cur = current[t]
            delta_notional = r.weights[t] * equity - cur * prices[t]
            assert int(delta_notional / prices[t]) == n - cur, t


class TestScaleInvariance:
    @pytest.mark.parametrize("seed", range(20))
    def test_doubling_capital_and_positions_doubles_targets(self, seed):
        rng = np.random.default_rng(seed)
        n = int(rng.integers(2, 7))
        tickers = [f"T{i}" for i in range(n)]
        weights = {t: float(w) for t, w in
                   zip(tickers, rng.dirichlet(np.ones(n)) * 0.9)}
        prices = {t: float(p) for t, p in
                  zip(tickers, rng.uniform(10, 400, n))}
        # currents chosen as integers that scale exactly when doubled
        current = {t: int(rng.integers(0, 200)) for t in tickers}
        equity = 50_000.0
        r1 = _res(weights, prices, current, equity)
        r2 = _res(weights, prices, {t: 2 * c for t, c in current.items()},
                  2 * equity)
        for t in tickers:
            # bands scale linearly; integer edge-rounding can differ by
            # at most one share of granularity at the doubled scale
            assert abs(r2.targets[t] - 2 * r1.targets[t]) <= 1, t


class TestCompositionWithDynOpt:
    """allocate → dyn-opt → buffering: buffering must band around the
    integer-implied positions dyn-opt emitted (incl. its ±1e-6 nudge)."""

    def test_buffering_consumes_dynopt_integer_weights(self):
        equity = 5_000.0
        price = 123.0
        # dyn-opt style integer-implied weight for n=12 with +nudge
        w_dyn = (12 + 1e-6) * price / equity
        # current inside the band around N*≈12 → hold
        r = _res({"AAA": w_dyn}, {"AAA": price}, {"AAA": 11}, equity)
        # N* ≈ 12.000001, band [10.8, 13.2] → 11 is inside → hold
        assert r.targets["AAA"] == 11
        # current far below → lower edge ceil(10.8) = 11
        r2 = _res({"AAA": w_dyn}, {"AAA": price}, {"AAA": 5}, equity)
        assert r2.targets["AAA"] == 11

    def test_end_to_end_engine_c_composition_order(self):
        """Both flags ON through PortfolioEngine: buffering runs after
        dyn-opt (a held position stays held even though dyn-opt would
        re-express it)."""
        from engines.engine_c_portfolio.policy import PortfolioPolicyConfig
        from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

        cfg = PortfolioPolicyConfig(
            mode="parrondo_fixed",
            fixed_allocations={"AAA": 0.5, "BBB": 0.3, "CCC": 0.2},
            dynamic_optimization_enabled=True,
            dynopt_tracking_error_buffer=0.0,
            position_buffering_enabled=True,
            buffer_fraction=0.10,
        )
        equity = 5_000.0
        engine = PortfolioEngine(equity, policy_cfg=cfg)
        price_data = _price_data_fixture()
        weights = engine.compute_target_allocations(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, equity
        )
        buf = engine.last_buffering_result
        dyn = engine.last_dynopt_result
        assert not dyn.skipped
        # buffering's optimal = dyn-opt's integer book (±nudge): every
        # buffered target sits inside the 10% band around dyn-opt's n.
        for t, n_dyn in dyn.positions.items():
            n_buf = buf.targets[t]
            band = 0.10 * abs(n_dyn) + 1e-6
            assert n_dyn - band - 1 <= n_buf <= n_dyn + band + 1, t
        # and the final weights imply whole shares
        for t, w in weights.items():
            implied = w * equity / float(price_data[t]["Close"].iloc[-1])
            assert abs(implied - round(implied)) < 1e-4, t


class TestDeterminismAndFailOpen:
    def test_repeat_calls_identical(self):
        weights = {"AAA": 0.4, "BBB": 0.3}
        prices = {"AAA": 90.0, "BBB": 210.0}
        current = {"AAA": 10, "BBB": 3}
        r1 = _res(weights, prices, current)
        r2 = _res(weights, prices, current)
        assert r1.targets == r2.targets and r1.weights == r2.weights

    def test_input_order_invariance(self):
        weights = {"AAA": 0.4, "BBB": 0.3}
        rev = dict(reversed(list(weights.items())))
        prices = {"AAA": 90.0, "BBB": 210.0}
        r1 = _res(weights, prices, {})
        r2 = _res(rev, prices, {})
        assert r1.targets == r2.targets and r1.weights == r2.weights

    def test_unpriceable_ticker_passes_through(self):
        r = _res({"AAA": 0.4, "BBB": 0.3}, {"AAA": 90.0}, {})
        assert "BBB" in r.dropped
        assert r.weights["BBB"] == 0.3            # untouched
        assert "BBB" not in r.targets

    @pytest.mark.parametrize("bad_equity", [0.0, -5.0, float("nan"), None])
    def test_invalid_equity_drops_all(self, bad_equity):
        r = apply_position_buffering(
            {"AAA": 0.4}, {"AAA": 90.0}, {}, bad_equity, 0.10
        )
        assert r.dropped == ["AAA"]
        assert r.weights["AAA"] == 0.4

    def test_zero_buffer_fraction_is_full_rebalance_to_integer(self):
        r = apply_position_buffering(
            {"AAA": 0.50}, {"AAA": 100.0}, {"AAA": 30}, 10_000.0, 0.0
        )
        assert r.targets["AAA"] == 50   # band collapses to the center


def _price_data_fixture(n_bars=80, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-02", periods=n_bars)
    out = {}
    for t, p0 in (("AAA", 120.0), ("BBB", 45.0), ("CCC", 310.0)):
        rets = rng.normal(0.0003, 0.012, n_bars)
        close = p0 * np.exp(np.cumsum(rets))
        out[t] = pd.DataFrame({"Close": close}, index=idx)
    return out


class TestWiringInertness:
    def test_flag_off_weights_identical_and_module_not_imported(self):
        from engines.engine_c_portfolio.policy import PortfolioPolicyConfig
        from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

        sys.modules.pop("engines.engine_c_portfolio.position_buffering", None)
        cfg = PortfolioPolicyConfig(
            mode="parrondo_fixed",
            fixed_allocations={"AAA": 0.5, "BBB": 0.3, "CCC": 0.2},
        )
        assert cfg.position_buffering_enabled is False  # shipped default

        engine = PortfolioEngine(10_000.0, policy_cfg=cfg)
        price_data = _price_data_fixture()
        expected = engine.policy.allocate(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, 10_000.0
        )
        got = engine.compute_target_allocations(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, 10_000.0
        )
        assert got == expected
        assert "engines.engine_c_portfolio.position_buffering" not in sys.modules
