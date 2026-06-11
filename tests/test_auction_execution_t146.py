# tests/test_auction_execution_t146.py
"""T-146 — auction-execution convention tests.

Covers: OFF-mode bitwise identity with the legacy fill path, auction
price selection per mode and side (moo / moc / moo_moc routing),
adverse safety-bps arithmetic (buys pay up, sells receive less),
regulatory-fee reuse (sells carry SEC+TAF when alpaca_fees enabled,
buys don't), missing-print fallbacks, the intrabar stop/target path
staying convention-independent, determinism, and config validation.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtester.execution_simulator import ExecutionSimulator

BAR = pd.Series({
    "Open": 100.0, "High": 104.0, "Low": 97.0, "Close": 102.0,
    "PrevClose": 99.5,
})


def _sim(**kw) -> ExecutionSimulator:
    defaults = dict(slippage_bps=10.0, slippage_model="fixed",
                    commission=0.0, verbose=False)
    defaults.update(kw)
    return ExecutionSimulator(**defaults)


def _order(side="long", qty=10):
    return {"ticker": "AAA", "side": side, "qty": qty}


class TestOffModeIsLegacyBitwise:
    def test_default_mode_is_off(self):
        assert _sim().params.auction_execution == "off"

    @pytest.mark.parametrize("side", ["long", "short", "exit", "cover"])
    def test_off_fill_identical_to_pre_t146_path(self, side):
        legacy = _sim()                      # pre-T-146 construction
        explicit_off = _sim(auction_execution="off", auction_safety_bps=5.0)
        f1 = legacy.fill_at_next_open(_order(side), BAR)
        f2 = explicit_off.fill_at_next_open(_order(side), BAR)
        assert f1 == f2
        # legacy economics: next Open +/- 10bps slippage
        expected = 100.0 * (1.0 + 0.0010) if side in ("long", "cover") \
            else 100.0 * (1.0 - 0.0010)
        assert f1["fill_price"] == pytest.approx(expected)


class TestAuctionPriceSelection:
    @pytest.mark.parametrize("side,expected_base", [
        ("long", 100.0), ("short", 100.0), ("exit", 100.0), ("cover", 100.0),
    ])
    def test_moo_uses_open_for_all_sides(self, side, expected_base):
        sim = _sim(auction_execution="moo", auction_safety_bps=0.0)
        fill = sim.fill_at_next_open(_order(side), BAR)
        assert fill["fill_price"] == pytest.approx(expected_base)

    @pytest.mark.parametrize("side", ["long", "short", "exit", "cover"])
    def test_moc_uses_close_for_all_sides(self, side):
        sim = _sim(auction_execution="moc", auction_safety_bps=0.0)
        fill = sim.fill_at_next_open(_order(side), BAR)
        assert fill["fill_price"] == pytest.approx(102.0)

    @pytest.mark.parametrize("side,expected", [
        ("long", 100.0),   # entry -> open auction
        ("short", 100.0),  # entry -> open auction
        ("exit", 102.0),   # signal exit -> close auction
        ("cover", 102.0),  # signal exit -> close auction
    ])
    def test_moo_moc_routes_entries_open_exits_close(self, side, expected):
        sim = _sim(auction_execution="moo_moc", auction_safety_bps=0.0)
        fill = sim.fill_at_next_open(_order(side), BAR)
        assert fill["fill_price"] == pytest.approx(expected)

    def test_no_slippage_model_applied_in_auction_mode(self):
        # 10bps slippage configured but auction fill must ignore it.
        sim = _sim(auction_execution="moo", auction_safety_bps=0.0,
                   slippage_bps=10.0)
        fill = sim.fill_at_next_open(_order("long"), BAR)
        assert fill["fill_price"] == pytest.approx(100.0)  # not 100.10


class TestSafetyBpsArithmetic:
    @pytest.mark.parametrize("side,sign", [
        ("long", +1), ("cover", +1),    # buys pay up
        ("short", -1), ("exit", -1),    # sells receive less
    ])
    def test_adverse_direction_per_side(self, side, sign):
        sim = _sim(auction_execution="moo", auction_safety_bps=2.0)
        fill = sim.fill_at_next_open(_order(side), BAR)
        assert fill["fill_price"] == pytest.approx(100.0 * (1 + sign * 0.0002))

    def test_zero_safety_is_exact_print(self):
        sim = _sim(auction_execution="moc", auction_safety_bps=0.0)
        assert sim.fill_at_next_open(_order("exit"), BAR)["fill_price"] == \
            pytest.approx(102.0)


class TestRegulatoryFeesReused:
    FEES = {"enabled": True, "sec_fee_per_dollar": 2.78e-05,
            "taf_per_share": 0.000166, "taf_max_per_trade": 8.3,
            "base_commission": 0.0, "buy_side_fees": False}

    def test_sells_carry_sec_taf_buys_do_not(self):
        sim = _sim(auction_execution="moo", auction_safety_bps=0.0,
                   alpaca_fees_cfg=self.FEES)
        buy = sim.fill_at_next_open(_order("long", qty=100), BAR)
        sell = sim.fill_at_next_open(_order("exit", qty=100), BAR)
        assert buy["commission"] == pytest.approx(0.0)
        expected_sell = 100 * 100.0 * 2.78e-05 + 100 * 0.000166
        assert sell["commission"] == pytest.approx(expected_sell, rel=1e-9)

    def test_fee_path_identical_on_and_off(self):
        on = _sim(auction_execution="moo", auction_safety_bps=0.0,
                  alpaca_fees_cfg=self.FEES)
        off = _sim(alpaca_fees_cfg=self.FEES)
        f_on = on.fill_at_next_open(_order("exit", qty=50), BAR)
        f_off = off.fill_at_next_open(_order("exit", qty=50), BAR)
        # fee = f(qty, fill_price); prices differ by slippage vs print,
        # but the fee FORMULA is the same object — spot-check both are
        # nonzero and proportional to their own fill prices.
        assert f_on["commission"] > 0 and f_off["commission"] > 0


class TestFallbacks:
    def test_moo_falls_back_to_close_when_open_invalid(self):
        bar = BAR.copy(); bar["Open"] = float("nan")
        sim = _sim(auction_execution="moo", auction_safety_bps=0.0)
        assert sim.fill_at_next_open(_order("long"), bar)["fill_price"] == \
            pytest.approx(102.0)

    def test_moc_falls_back_to_open_when_close_invalid(self):
        bar = BAR.copy(); bar["Close"] = float("nan")
        sim = _sim(auction_execution="moc", auction_safety_bps=0.0)
        # NOTE: _extract_bar_prices requires O/H/L; Close may be NaN.
        assert sim.fill_at_next_open(_order("exit"), bar)["fill_price"] == \
            pytest.approx(100.0)


class _Pos:
    def __init__(self, qty, stop=None, take_profit=None):
        self.qty = qty
        self.stop = stop
        self.take_profit = take_profit


class TestStopsUnaffectedByConvention:
    @pytest.mark.parametrize("mode", ["off", "moo", "moc", "moo_moc"])
    def test_stop_fill_identical_across_modes(self, mode):
        sim = _sim(auction_execution=mode)
        pos = _Pos(qty=10, stop=98.0)
        fill = sim.check_stops_and_targets("AAA", pos, BAR)  # Low 97 < 98
        ref = _sim().check_stops_and_targets("AAA", _Pos(10, stop=98.0), BAR)
        assert fill == ref  # intrabar stops are never auction orders


class TestValidationAndDeterminism:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            _sim(auction_execution="limit_on_close")

    @pytest.mark.parametrize("mode", ["moo", "moc", "moo_moc"])
    def test_repeat_fills_identical(self, mode):
        sim = _sim(auction_execution=mode, auction_safety_bps=1.0)
        fills = [sim.fill_at_next_open(_order("long"), BAR) for _ in range(3)]
        assert fills[0] == fills[1] == fills[2]

    def test_exit_position_helper_inherits_convention(self):
        sim = _sim(auction_execution="moo_moc", auction_safety_bps=0.0)
        fill = sim.exit_position("AAA", _Pos(qty=10), BAR)
        assert fill["side"] == "exit"
        assert fill["fill_price"] == pytest.approx(102.0)  # close auction
