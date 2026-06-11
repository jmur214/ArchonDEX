# tests/test_engine_c_dynamic_optimizer.py
"""T-139 — Carver dynamic optimization (integer-position layer) tests.

Covers, per the T-139 brief:
  * unit tests on the greedy loop (hand-computable small cases)
  * property tests over seeded random fixtures:
      - scale invariance (2x capital => tracking error non-increasing)
      - cost-penalty monotonicity (higher cost => fewer shares traded)
      - never-exceeds-buying-power
      - Engine-B truncation parity (the +-1e-6-share nudge contract)
      - determinism (repeat calls + input-dict-order invariance)
  * fail-open behavior (bad equity / prices / covariance)
  * wiring inertness at the unit level: flag OFF leaves
    PortfolioEngine.compute_target_allocations output unchanged and never
    imports the optimizer module.

No hypothesis dependency — seeded NumPy generators, matching existing
test conventions (see tests/test_engine_c_hrp.py).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

from engines.engine_c_portfolio.dynamic_optimizer import (
    DynamicOptimizationConfig,
    DynamicOptimizationResult,
    naive_rounded_positions,
    optimize_integer_positions,
)


# --------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------- #
def _diag_cov(tickers, daily_var=1e-4):
    n = len(tickers)
    return pd.DataFrame(np.eye(n) * daily_var, index=tickers, columns=tickers)


def _random_fixture(seed: int, n_assets=None, long_only=True, with_prior=False):
    """Deterministic random book: prices, weights, factor-model covariance."""
    rng = np.random.default_rng(seed)
    n = int(n_assets or rng.integers(2, 9))
    tickers = [f"T{i:02d}" for i in range(n)]
    prices = dict(zip(tickers, np.exp(rng.uniform(np.log(5.0), np.log(500.0), n))))
    raw = rng.dirichlet(np.ones(n))
    gross = rng.uniform(0.6, 1.0)
    signs = np.ones(n) if long_only else rng.choice([-1.0, 1.0], n)
    weights = dict(zip(tickers, raw * gross * signs))
    # PSD daily covariance from a 2-factor model + idiosyncratic diag.
    beta = rng.normal(0.0, 0.01, (n, 2))
    cov = beta @ beta.T + np.diag(rng.uniform(0.5e-4, 4e-4, n))
    cov_df = pd.DataFrame(cov, index=tickers, columns=tickers)
    equity = float(rng.uniform(3_000, 100_000))
    if with_prior:
        naive = naive_rounded_positions(
            np.array([weights[t] for t in tickers]),
            np.array([prices[t] for t in tickers]),
            np.zeros(n, dtype=np.int64),
            equity,
        )
        jitter = rng.integers(-2, 3, n)
        current = {t: int(max(naive[i] + jitter[i], 0) if long_only else naive[i] + jitter[i])
                   for i, t in enumerate(tickers)}
    else:
        current = {t: 0 for t in tickers}
    return tickers, weights, prices, current, equity, cov_df


def _no_buffer_cfg(**kw) -> DynamicOptimizationConfig:
    """Buffer/speed-control off => pure greedy outcome (full trade)."""
    defaults = dict(tracking_error_buffer=0.0)
    defaults.update(kw)
    return DynamicOptimizationConfig(**defaults)


def _te_of_positions(result: DynamicOptimizationResult) -> float:
    return result.tracking_error_optimized


# --------------------------------------------------------------------- #
# Unit tests — hand-computable greedy cases
# --------------------------------------------------------------------- #
class TestGreedyKnownCases:
    def test_two_assets_diagonal_cov_rounds_to_nearest(self):
        # E=1000, p=100 => one share = 0.1 weight. Targets 0.54 / 0.22 =>
        # ideal 5.4 / 2.2 shares. With diagonal cov and zero cost the
        # nearest integer book {5, 2} is the unambiguous optimum (gaps
        # 0.04/0.02 vs 0.06/0.08 for any one-share move). Half-step
        # targets (e.g. 5.5 ideal) are FP-tie territory and deliberately
        # not asserted exactly.
        tickers = ["AAA", "BBB"]
        res = optimize_integer_positions(
            target_weights={"AAA": 0.54, "BBB": 0.22},
            prices={"AAA": 100.0, "BBB": 100.0},
            current_positions={"AAA": 0, "BBB": 0},
            equity=1_000.0,
            covariance=_diag_cov(tickers),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert res.positions == {"AAA": 5, "BBB": 2}
        assert res.trades == {"AAA": 5, "BBB": 2}
        assert not res.buffered and not res.skipped

    def test_exact_integer_target_is_hit_exactly(self):
        tickers = ["AAA", "BBB"]
        res = optimize_integer_positions(
            target_weights={"AAA": 0.5, "BBB": 0.3},
            prices={"AAA": 100.0, "BBB": 100.0},
            current_positions={"AAA": 0, "BBB": 0},
            equity=1_000.0,
            covariance=_diag_cov(tickers),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert res.positions == {"AAA": 5, "BBB": 3}
        assert res.tracking_error_optimized == pytest.approx(0.0, abs=1e-12)

    def test_zero_target_stays_zero(self):
        tickers = ["AAA", "BBB"]
        res = optimize_integer_positions(
            target_weights={"AAA": 0.6, "BBB": 0.0},
            prices={"AAA": 100.0, "BBB": 50.0},
            current_positions={"AAA": 0, "BBB": 0},
            equity=1_000.0,
            covariance=_diag_cov(tickers),
            cfg=_no_buffer_cfg(),
        )
        assert res.positions["BBB"] == 0

    def test_short_target_produces_negative_position(self):
        tickers = ["AAA", "BBB"]
        res = optimize_integer_positions(
            target_weights={"AAA": 0.4, "BBB": -0.3},
            prices={"AAA": 100.0, "BBB": 100.0},
            current_positions={"AAA": 0, "BBB": 0},
            equity=1_000.0,
            covariance=_diag_cov(tickers),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert res.positions["AAA"] == 4
        assert res.positions["BBB"] == -3

    def test_single_asset_book(self):
        res = optimize_integer_positions(
            target_weights={"AAA": 0.8},
            prices={"AAA": 333.0},
            current_positions={"AAA": 0},
            equity=5_000.0,
            covariance=_diag_cov(["AAA"]),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        # ideal 0.8*5000/333 = 12.01 shares; greedy floor-or-ceil of the walk
        assert res.positions["AAA"] in (12, 13)

    def test_correlated_pair_beats_or_matches_naive(self):
        # Strong positive correlation lets an overweight in one name
        # substitute for an underweight in the other — exactly the effect
        # naive per-name rounding cannot exploit.
        tickers = ["AAA", "BBB"]
        daily_var = 2e-4
        rho = 0.95
        cov = np.array([[daily_var, rho * daily_var], [rho * daily_var, daily_var]])
        res = optimize_integer_positions(
            target_weights={"AAA": 0.35, "BBB": 0.35},
            prices={"AAA": 180.0, "BBB": 170.0},
            current_positions={"AAA": 0, "BBB": 0},
            equity=2_500.0,
            covariance=pd.DataFrame(cov, index=tickers, columns=tickers),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert res.tracking_error_optimized <= res.tracking_error_naive + 1e-12


class TestBuffering:
    def test_prior_within_buffer_keeps_positions(self):
        tickers = ["AAA", "BBB"]
        # Prior = exact integer expression of the target => TE(prior) = 0.
        res = optimize_integer_positions(
            target_weights={"AAA": 0.5, "BBB": 0.3},
            prices={"AAA": 100.0, "BBB": 100.0},
            current_positions={"AAA": 5, "BBB": 3},
            equity=1_000.0,
            covariance=_diag_cov(tickers),
            cfg=DynamicOptimizationConfig(tracking_error_buffer=0.02),
        )
        assert res.buffered
        assert res.positions == {"AAA": 5, "BBB": 3}
        assert res.trades == {}

    def test_buffer_reduces_total_shares_traded(self):
        tickers, weights, prices, current, equity, cov = _random_fixture(
            7, n_assets=6, with_prior=True
        )
        full = optimize_integer_positions(
            weights, prices, current, equity, cov,
            cfg=_no_buffer_cfg(),
        )
        damped = optimize_integer_positions(
            weights, prices, current, equity, cov,
            cfg=DynamicOptimizationConfig(tracking_error_buffer=0.05),
        )
        assert (sum(abs(v) for v in damped.trades.values())
                <= sum(abs(v) for v in full.trades.values()))


# --------------------------------------------------------------------- #
# Property tests — seeded batteries
# --------------------------------------------------------------------- #
SEEDS = list(range(40))


class TestProperties:
    @pytest.mark.parametrize("seed", SEEDS)
    def test_scale_invariance_doubling_capital_never_hurts(self, seed):
        # 2x capital halves the weight granularity: every book expressible
        # at E is expressible at 2E, so achieved tracking error must be
        # non-increasing. Pure-expressibility setting: zero cost, zero
        # buffer, flat start.
        tickers, weights, prices, current, equity, cov = _random_fixture(seed)
        cfg = _no_buffer_cfg(shadow_cost=0.0)
        res_1x = optimize_integer_positions(weights, prices, current, equity, cov, cfg=cfg)
        res_2x = optimize_integer_positions(weights, prices, current, 2.0 * equity, cov, cfg=cfg)
        assert res_2x.tracking_error_optimized <= res_1x.tracking_error_optimized + 1e-9

    @pytest.mark.parametrize("seed", SEEDS)
    def test_cost_penalty_monotonicity_less_weight_traded(self, seed):
        # The cost term is linear in traded WEIGHT (notional/equity), so
        # that is the quantity a rising penalty must suppress — share
        # counts are a bad proxy when prices span 5..500 (nine shares of
        # a $5 name is ~zero weight and ~zero cost). Greedy is
        # path-dependent, so adjacent levels get a one-max-share
        # tolerance; the endpoints must be monotone outright.
        tickers, weights, prices, current, equity, cov = _random_fixture(
            seed, with_prior=True
        )
        one_share_w = max(prices[t] for t in tickers) / equity
        traded_w = []
        for shadow in (0.0, 10.0, 100.0, 1000.0):
            res = optimize_integer_positions(
                weights, prices, current, equity, cov,
                cfg=_no_buffer_cfg(shadow_cost=shadow),
            )
            traded_w.append(
                sum(abs(v) * prices[t] for t, v in res.trades.items()) / equity
            )
        assert all(a + one_share_w + 1e-12 >= b for a, b in zip(traded_w, traded_w[1:])), traded_w
        assert traded_w[-1] <= traded_w[0] + 1e-12, traded_w

    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("fraction", [0.5, 1.0])
    def test_never_exceeds_buying_power(self, seed, fraction):
        tickers, weights, prices, current, equity, cov = _random_fixture(seed)
        res = optimize_integer_positions(
            weights, prices, current, equity, cov,
            cfg=_no_buffer_cfg(shadow_cost=0.0, buying_power_fraction=fraction),
        )
        gross = sum(abs(res.positions[t]) * prices[t] for t in res.positions)
        assert gross <= fraction * equity * (1.0 + 1e-9)

    @pytest.mark.parametrize("seed", SEEDS)
    def test_engine_b_truncation_parity(self, seed):
        # The output-weight contract: Engine B Path A computes
        # int((w*E - cur*p)/p) and MUST land exactly on the optimizer's
        # chosen trade for every ticker.
        tickers, weights, prices, current, equity, cov = _random_fixture(
            seed, with_prior=True
        )
        res = optimize_integer_positions(
            weights, prices, current, equity, cov, cfg=_no_buffer_cfg()
        )
        for t, n in res.positions.items():
            cur = current.get(t, 0)
            target_notional = res.weights[t] * equity
            delta_notional = target_notional - cur * prices[t]
            engine_b_add_qty = int(delta_notional / prices[t])
            assert engine_b_add_qty == n - cur, (
                f"{t}: engine_b={engine_b_add_qty} expected={n - cur}"
            )

    @pytest.mark.parametrize("seed", SEEDS[:20])
    def test_optimized_te_not_worse_than_naive(self, seed):
        # Greedy is a heuristic, but on realistic books it should never
        # lose to naive truncation in pure-TE mode. Empirical guarantee —
        # a failure here means the greedy walk regressed.
        tickers, weights, prices, current, equity, cov = _random_fixture(seed)
        res = optimize_integer_positions(
            weights, prices, current, equity, cov,
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert res.tracking_error_optimized <= res.tracking_error_naive + 1e-9

    @pytest.mark.parametrize("seed", SEEDS[:10])
    def test_determinism_repeat_calls(self, seed):
        tickers, weights, prices, current, equity, cov = _random_fixture(
            seed, with_prior=True
        )
        cfg = DynamicOptimizationConfig()
        r1 = optimize_integer_positions(weights, prices, current, equity, cov, cfg=cfg)
        r2 = optimize_integer_positions(weights, prices, current, equity, cov, cfg=cfg)
        assert r1.positions == r2.positions
        assert r1.weights == r2.weights
        assert r1.tracking_error_optimized == r2.tracking_error_optimized

    @pytest.mark.parametrize("seed", SEEDS[:10])
    def test_input_dict_order_invariance(self, seed):
        tickers, weights, prices, current, equity, cov = _random_fixture(
            seed, with_prior=True
        )
        rev = lambda d: dict(reversed(list(d.items())))
        r_fwd = optimize_integer_positions(
            weights, prices, current, equity, cov, cfg=DynamicOptimizationConfig()
        )
        r_rev = optimize_integer_positions(
            rev(weights), rev(prices), rev(current), equity, cov,
            cfg=DynamicOptimizationConfig(),
        )
        assert r_fwd.positions == r_rev.positions
        assert r_fwd.weights == r_rev.weights


# --------------------------------------------------------------------- #
# Fail-open behavior
# --------------------------------------------------------------------- #
class TestFailOpen:
    @pytest.mark.parametrize("bad_equity", [0.0, -100.0, float("nan"), None])
    def test_invalid_equity_passes_weights_through(self, bad_equity):
        weights = {"AAA": 0.5, "BBB": 0.3}
        res = optimize_integer_positions(
            target_weights=weights,
            prices={"AAA": 100.0, "BBB": 100.0},
            current_positions={},
            equity=bad_equity,
            covariance=_diag_cov(["AAA", "BBB"]),
        )
        assert res.skipped and res.weights == weights

    def test_empty_weights(self):
        res = optimize_integer_positions({}, {}, {}, 1_000.0, _diag_cov(["A"]))
        assert res.skipped and res.weights == {}

    def test_missing_price_drops_ticker_but_preserves_its_weight(self):
        weights = {"AAA": 0.5, "BBB": 0.3}
        res = optimize_integer_positions(
            target_weights=weights,
            prices={"AAA": 100.0},  # BBB unpriced
            current_positions={},
            equity=1_000.0,
            covariance=_diag_cov(["AAA", "BBB"]),
            cfg=_no_buffer_cfg(shadow_cost=0.0),
        )
        assert not res.skipped
        assert "BBB" in res.dropped_tickers
        assert res.weights["BBB"] == 0.3          # passed through untouched
        assert "BBB" not in res.positions
        assert res.positions["AAA"] == 5

    def test_empty_covariance_passes_through(self):
        weights = {"AAA": 0.5}
        res = optimize_integer_positions(
            weights, {"AAA": 100.0}, {}, 1_000.0, pd.DataFrame()
        )
        assert res.skipped and res.weights == weights

    def test_non_finite_covariance_passes_through(self):
        cov = _diag_cov(["AAA", "BBB"])
        cov.iloc[0, 1] = np.nan
        weights = {"AAA": 0.5, "BBB": 0.3}
        res = optimize_integer_positions(
            weights, {"AAA": 100.0, "BBB": 100.0}, {}, 1_000.0, cov
        )
        assert res.skipped and res.weights == weights


# --------------------------------------------------------------------- #
# Wiring inertness (unit level) — flag OFF must be a strict no-op
# --------------------------------------------------------------------- #
def _price_data_fixture(n_bars=80, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-02", periods=n_bars)
    out = {}
    for t, p0 in (("AAA", 120.0), ("BBB", 45.0), ("CCC", 310.0)):
        rets = rng.normal(0.0003, 0.012, n_bars)
        close = p0 * np.exp(np.cumsum(rets))
        out[t] = pd.DataFrame({"Close": close}, index=idx)
    return out


class TestPortfolioEngineWiring:
    def test_flag_off_weights_identical_and_module_not_imported(self):
        from engines.engine_c_portfolio.policy import PortfolioPolicyConfig
        from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

        sys.modules.pop("engines.engine_c_portfolio.dynamic_optimizer", None)

        cfg = PortfolioPolicyConfig(
            mode="parrondo_fixed",
            fixed_allocations={"AAA": 0.5, "BBB": 0.3, "CCC": 0.2},
        )
        assert cfg.dynamic_optimization_enabled is False  # the shipped default

        engine = PortfolioEngine(10_000.0, policy_cfg=cfg)
        price_data = _price_data_fixture()
        expected = engine.policy.allocate(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, 10_000.0
        )
        got = engine.compute_target_allocations(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, 10_000.0
        )
        assert got == expected
        assert "engines.engine_c_portfolio.dynamic_optimizer" not in sys.modules

    def test_flag_on_produces_integer_feasible_weights(self):
        from engines.engine_c_portfolio.policy import PortfolioPolicyConfig
        from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine

        cfg = PortfolioPolicyConfig(
            mode="parrondo_fixed",
            fixed_allocations={"AAA": 0.5, "BBB": 0.3, "CCC": 0.2},
            dynamic_optimization_enabled=True,
            dynopt_tracking_error_buffer=0.0,
        )
        equity = 5_000.0
        engine = PortfolioEngine(equity, policy_cfg=cfg)
        price_data = _price_data_fixture()
        weights = engine.compute_target_allocations(
            {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}, price_data, equity
        )
        result = engine.last_dynopt_result
        assert not result.skipped
        # Every optimized weight implies a whole-share position at this
        # equity (within the documented 1e-6-share nudge) and Engine B's
        # truncation recovers exactly that integer.
        for t, w in weights.items():
            price = float(price_data[t]["Close"].iloc[-1])
            implied_shares = w * equity / price
            assert abs(implied_shares - round(implied_shares)) < 1e-4
            assert int((w * equity - 0.0) / price) == result.positions[t]
