# tests/test_after_tax_t141.py
"""T-141 — after-tax gate + account router tests.

Covers: state-rate tax arithmetic (additive to federal; 0.0 = pre-T-141
back-compat), holding-period classification boundaries (same-day / 364 /
365 / 366 — documenting the model's >=365 LT semantics), FIFO lot
splitting across partial exits, wash-sale flagging, the report-only
after-tax module (never consults the canon-changing `enabled` flag),
producer emission, and the Roth/taxable router rules (st_heavy evidence
gate incl. CI-awareness; disjoint-universe and 31-day-blackout
cross-account wash-sale modes).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from backtester.after_tax_metrics import compute_after_tax_report
from backtester.tax_drag_model import TaxDragConfig, TaxDragModel, get_tax_drag_model
from core.account_router import (
    BLACKOUT_DAYS,
    CrossAccountWashSaleChecker,
    RoutingViolation,
    validate_routing,
)


# --------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------- #
def _fill(ts: str, ticker: str, side: str, qty: int, price: float) -> dict:
    return {
        "timestamp": ts, "ticker": ticker, "side": side,
        "qty": qty, "fill_price": price,
    }


def _fills_df(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _equity(dates, values) -> pd.Series:
    return pd.Series(values, index=pd.to_datetime(dates), dtype=float)


# --------------------------------------------------------------------- #
# Tax arithmetic — state rates
# --------------------------------------------------------------------- #
class TestStateRateArithmetic:
    def _one_st_gain(self, cfg: TaxDragConfig) -> float:
        """One $1,000 short-term gain, return tax owed."""
        model = TaxDragModel(cfg)
        fills = _fills_df([
            _fill("2024-02-01", "AAA", "long", 10, 100.0),
            _fill("2024-03-01", "AAA", "exit", 10, 200.0),  # +$1,000, 29d ST
        ])
        trades = model.reconstruct_trades(fills)
        yearly = model.compute_yearly_tax(trades)
        return yearly[2024]["tax_owed"]

    def test_zero_state_rates_match_pre_t141_arithmetic(self):
        cfg = TaxDragConfig(short_term_rate=0.30, long_term_rate=0.15)
        assert self._one_st_gain(cfg) == pytest.approx(300.0)

    def test_illinois_state_rate_adds_to_federal(self):
        cfg = TaxDragConfig(
            short_term_rate=0.30, long_term_rate=0.15,
            state_st_rate=0.0495, state_lt_rate=0.0495,
        )
        assert self._one_st_gain(cfg) == pytest.approx(349.50)

    def test_lt_state_rate_applies_to_long_term_bucket(self):
        cfg = TaxDragConfig(
            short_term_rate=0.30, long_term_rate=0.15,
            state_st_rate=0.0495, state_lt_rate=0.0495,
        )
        model = TaxDragModel(cfg)
        fills = _fills_df([
            _fill("2022-01-03", "AAA", "long", 10, 100.0),
            _fill("2024-03-01", "AAA", "exit", 10, 200.0),  # +$1,000 LT
        ])
        trades = model.reconstruct_trades(fills)
        yearly = model.compute_yearly_tax(trades)
        assert yearly[2024]["tax_owed"] == pytest.approx(1000.0 * 0.1995)

    def test_factory_reads_state_rates_and_defaults_zero(self):
        m = get_tax_drag_model({"state_st_rate": 0.0495, "state_lt_rate": 0.0495})
        assert m.config.state_st_rate == pytest.approx(0.0495)
        assert m.config.state_lt_rate == pytest.approx(0.0495)
        m_default = get_tax_drag_model({"enabled": False})
        assert m_default.config.state_st_rate == 0.0
        assert m_default.config.state_lt_rate == 0.0

    def test_carry_forward_interacts_with_state_rates(self):
        # Year 1: -$500 ST loss. Year 2: +$1,000 ST gain → taxable $500.
        cfg = TaxDragConfig(
            short_term_rate=0.30, state_st_rate=0.0495,
        )
        model = TaxDragModel(cfg)
        fills = _fills_df([
            _fill("2023-02-01", "AAA", "long", 10, 100.0),
            _fill("2023-03-01", "AAA", "exit", 10, 50.0),    # -$500 ST
            _fill("2024-02-01", "BBB", "long", 10, 100.0),
            _fill("2024-03-01", "BBB", "exit", 10, 200.0),   # +$1,000 ST
        ])
        trades = model.reconstruct_trades(fills)
        yearly = model.compute_yearly_tax(trades)
        assert yearly[2023]["tax_owed"] == pytest.approx(0.0)
        assert yearly[2024]["taxable_st"] == pytest.approx(500.0)
        assert yearly[2024]["tax_owed"] == pytest.approx(500.0 * 0.3495)


# --------------------------------------------------------------------- #
# Holding-period classification boundaries
# --------------------------------------------------------------------- #
class TestHoldingPeriodBoundaries:
    @pytest.mark.parametrize(
        "entry,exit_,expected",
        [
            ("2024-03-01", "2024-03-01", "short_term"),   # same-day
            ("2024-03-01", "2024-03-02", "short_term"),   # T+1
            ("2023-03-02", "2024-02-29", "short_term"),   # 364 days
            # Exactly 365 days classifies LONG TERM under the model's
            # >=365 semantics. The IRS rule is "MORE than one year", so
            # this boundary day is technically optimistic (less tax) —
            # pre-existing model behavior, documented in the T-141 audit;
            # changing it would alter enabled=True results (out of an
            # additive task's scope).
            ("2023-03-02", "2024-03-01", "long_term"),    # 365 days
            ("2023-03-01", "2024-03-01", "long_term"),    # 366 days
        ],
    )
    def test_boundary(self, entry, exit_, expected):
        model = TaxDragModel(TaxDragConfig())
        fills = _fills_df([
            _fill(entry, "AAA", "long", 10, 100.0),
            _fill(exit_, "AAA", "exit", 10, 110.0),
        ])
        trades = model.reconstruct_trades(fills)
        assert len(trades) == 1
        assert trades[0].classification == expected

    def test_partial_exits_split_lot_with_distinct_classifications(self):
        # One 20-share lot; 10 shares exit at 100 days (ST), 10 at 400
        # days (LT). FIFO must produce two realized lots with their own
        # holding periods.
        model = TaxDragModel(TaxDragConfig())
        fills = _fills_df([
            _fill("2023-01-02", "AAA", "long", 20, 100.0),
            _fill("2023-04-12", "AAA", "exit", 10, 120.0),
            _fill("2024-02-06", "AAA", "exit", 10, 130.0),
        ])
        trades = model.reconstruct_trades(fills)
        assert len(trades) == 2
        assert trades[0].classification == "short_term"
        assert trades[1].classification == "long_term"
        assert trades[0].qty == trades[1].qty == 10

    def test_fifo_order_across_multiple_lots(self):
        # Two lots opened at different prices; one exit spans both →
        # FIFO closes the older lot first.
        model = TaxDragModel(TaxDragConfig())
        fills = _fills_df([
            _fill("2024-01-02", "AAA", "long", 10, 100.0),
            _fill("2024-02-01", "AAA", "long", 10, 110.0),
            _fill("2024-03-01", "AAA", "exit", 15, 120.0),
        ])
        trades = model.reconstruct_trades(fills)
        assert len(trades) == 2
        assert trades[0].entry_price == pytest.approx(100.0)
        assert trades[0].qty == 10
        assert trades[1].entry_price == pytest.approx(110.0)
        assert trades[1].qty == 5

    def test_wash_sale_flags_loss_with_repurchase_inside_window(self):
        model = TaxDragModel(TaxDragConfig())
        fills = _fills_df([
            _fill("2024-01-02", "AAA", "long", 10, 100.0),
            _fill("2024-02-01", "AAA", "exit", 10, 80.0),    # -$200 loss
            _fill("2024-02-15", "AAA", "long", 10, 85.0),    # repurchase, 14d
        ])
        trades = model.reconstruct_trades(fills)
        trades = model.apply_wash_sale_rule(trades)
        loss = [t for t in trades if t.pnl < 0][0]
        assert loss.wash_sale_disallowed


# --------------------------------------------------------------------- #
# Report-only after-tax module
# --------------------------------------------------------------------- #
class TestAfterTaxReport:
    def _simple_inputs(self):
        fills = _fills_df([
            _fill("2024-02-01", "AAA", "long", 10, 100.0),
            _fill("2024-06-03", "AAA", "exit", 10, 200.0),  # +$1,000 ST
        ])
        dates = pd.bdate_range("2024-01-02", "2024-12-31")
        equity = pd.Series(
            np.linspace(10_000.0, 11_000.0, len(dates)), index=dates
        )
        return fills, equity

    def test_report_ignores_enabled_false(self):
        # The canon-changing flag is False — reporting must run anyway.
        fills, equity = self._simple_inputs()
        rep = compute_after_tax_report(
            fills, equity, {"enabled": False, "state_st_rate": 0.0495}
        )
        assert rep["skip_reason"] is None
        assert rep["total_tax_usd"] == pytest.approx(1000.0 * 0.3495, abs=0.01)

    def test_taxable_sharpe_below_roth_sharpe_when_gains_taxed(self):
        fills, equity = self._simple_inputs()
        rep = compute_after_tax_report(fills, equity, {})
        assert rep["sharpe_roth"] is not None
        assert rep["after_tax_sharpe_taxable"] is not None
        assert rep["after_tax_sharpe_taxable"] < rep["sharpe_roth"]
        assert rep["tax_drag_pct"] is not None and rep["tax_drag_pct"] > 0

    def test_no_trades_means_zero_drag(self):
        _, equity = self._simple_inputs()
        rep = compute_after_tax_report(_fills_df([]), equity, {})
        assert rep["tax_drag_pct"] == 0.0
        assert rep["after_tax_sharpe_taxable"] == rep["sharpe_roth"]
        assert rep["skip_reason"] == "no_trades"

    def test_insufficient_equity_fails_open(self):
        rep = compute_after_tax_report(
            _fills_df([]), pd.Series(dtype=float), {}
        )
        assert rep["skip_reason"] == "insufficient_equity_history"
        assert rep["after_tax_sharpe_taxable"] is None

    def test_report_is_json_native(self):
        fills, equity = self._simple_inputs()
        rep = compute_after_tax_report(fills, equity, {"state_st_rate": 0.0495})
        json.dumps(rep)  # raises on any non-native type


# --------------------------------------------------------------------- #
# Producer emission (cockpit/metrics.py)
# --------------------------------------------------------------------- #
class TestProducerEmission:
    def test_summary_carries_after_tax_keys(self, tmp_path):
        snaps = pd.DataFrame({
            "timestamp": pd.bdate_range("2024-01-02", periods=60).astype(str),
            "equity": np.linspace(10_000, 10_500, 60),
        })
        trades = pd.DataFrame([
            {**_fill("2024-02-01", "AAA", "long", 10, 100.0), "pnl": np.nan,
             "commission": 0.0},
            {**_fill("2024-03-01", "AAA", "exit", 10, 150.0), "pnl": 500.0,
             "commission": 0.0},
        ])
        sp = tmp_path / "snaps.csv"
        tp = tmp_path / "trades.csv"
        snaps.to_csv(sp, index=False)
        trades.to_csv(tp, index=False)

        from cockpit.metrics import PerformanceMetrics
        m = PerformanceMetrics(snapshots_path=str(sp), trades_path=str(tp))
        s = m.summary()
        for key in ("after_tax_sharpe_taxable", "sharpe_roth", "tax_drag_pct",
                    "after_tax_detail"):
            assert key in s
        assert isinstance(s["after_tax_detail"], dict)
        assert s["after_tax_detail"]["tax_rates_source"] in ("config", "defaults")
        # summary_metrics must stay JSON-serializable with the new keys.
        json.dumps(m.summary_metrics())


# --------------------------------------------------------------------- #
# Router — RULE A (st_heavy evidence gate)
# --------------------------------------------------------------------- #
def _base_config(**sleeve_overrides):
    sleeve = {"account": "taxable", "st_heavy": True, "universe": ["AAA"]}
    sleeve.update(sleeve_overrides)
    return {
        "default_account": "taxable",
        "rules": {"cross_account_wash_sale": "disjoint_universes"},
        "sleeves": {"s1": sleeve},
    }


class TestRouterRuleA:
    def test_st_heavy_taxable_without_evidence_is_violation(self):
        v = validate_routing(_base_config())
        assert any(x.rule == "st_heavy_taxable" and x.severity == "error" for x in v)

    def test_ci_low_evidence_clears(self):
        v = validate_routing(
            _base_config(),
            after_tax_evidence={"s1": {"after_tax_sharpe_taxable": 0.6, "ci_low": 0.1}},
        )
        assert not [x for x in v if x.rule == "st_heavy_taxable"]

    def test_point_only_evidence_downgrades_to_warning(self):
        v = validate_routing(
            _base_config(),
            after_tax_evidence={"s1": {"after_tax_sharpe_taxable": 0.6}},
        )
        flags = [x for x in v if x.rule == "st_heavy_taxable"]
        assert len(flags) == 1 and flags[0].severity == "warning"

    def test_negative_ci_low_still_violates(self):
        v = validate_routing(
            _base_config(),
            after_tax_evidence={"s1": {"after_tax_sharpe_taxable": 0.45, "ci_low": -0.1}},
        )
        assert any(x.rule == "st_heavy_taxable" and x.severity == "error" for x in v)

    def test_st_heavy_in_roth_is_fine(self):
        v = validate_routing(_base_config(account="roth"))
        assert not [x for x in v if x.rule == "st_heavy_taxable"]

    def test_slow_taxable_sleeve_is_fine(self):
        v = validate_routing(_base_config(st_heavy=False))
        assert not [x for x in v if x.rule == "st_heavy_taxable"]


# --------------------------------------------------------------------- #
# Router — RULE B (cross-account wash sale)
# --------------------------------------------------------------------- #
class TestRouterRuleB:
    def test_universe_overlap_flagged_in_disjoint_mode(self):
        cfg = {
            "rules": {"cross_account_wash_sale": "disjoint_universes"},
            "sleeves": {
                "tax_sleeve": {"account": "taxable", "universe": ["AAA", "BBB"]},
                "roth_sleeve": {"account": "roth", "universe": ["BBB", "CCC"]},
            },
        }
        v = validate_routing(cfg)
        overlaps = [x for x in v if x.rule == "universe_overlap"]
        assert len(overlaps) == 1 and "BBB" in overlaps[0].message

    def test_disjoint_universes_pass(self):
        cfg = {
            "rules": {"cross_account_wash_sale": "disjoint_universes"},
            "sleeves": {
                "tax_sleeve": {"account": "taxable", "universe": ["AAA"]},
                "roth_sleeve": {"account": "roth", "universe": ["CCC"]},
            },
        }
        assert validate_routing(cfg) == []

    def test_either_account_universe_counts_for_both(self):
        cfg = {
            "rules": {"cross_account_wash_sale": "disjoint_universes"},
            "sleeves": {
                "both": {"account": "either", "universe": ["AAA"]},
                "tax_sleeve": {"account": "taxable", "universe": ["AAA"]},
            },
        }
        v = validate_routing(cfg)
        assert any(x.rule == "universe_overlap" for x in v)

    def test_blackout_mode_skips_static_overlap_check(self):
        cfg = {
            "rules": {"cross_account_wash_sale": "blackout_31d"},
            "sleeves": {
                "tax_sleeve": {"account": "taxable", "universe": ["AAA"]},
                "roth_sleeve": {"account": "roth", "universe": ["AAA"]},
            },
        }
        assert not [x for x in validate_routing(cfg) if x.rule == "universe_overlap"]

    def test_schema_violations(self):
        v = validate_routing({"sleeves": {"s1": {"account": "ira"}}})
        assert any(x.rule == "schema" for x in v)
        v2 = validate_routing({
            "rules": {"cross_account_wash_sale": "nonsense"},
            "sleeves": {"s1": {"account": "roth"}},
        })
        assert any(x.rule == "schema" for x in v2)
        assert any(x.rule == "schema" for x in validate_routing({}))


class TestBlackoutChecker:
    def test_roth_buy_inside_blackout_blocked(self):
        c = CrossAccountWashSaleChecker()
        c.record_taxable_loss("AAA", "2024-03-01")
        verdict = c.check_trade("AAA", "roth", "2024-03-15")
        assert not verdict["allowed"]
        assert "blackout" in verdict["reason"]

    def test_roth_buy_on_day_31_allowed(self):
        c = CrossAccountWashSaleChecker()
        c.record_taxable_loss("AAA", "2024-03-01")
        assert c.check_trade("AAA", "roth", "2024-03-31")["allowed"] is False  # day 30
        assert c.check_trade("AAA", "roth", "2024-04-01")["allowed"] is True   # day 31

    def test_taxable_buys_unaffected(self):
        c = CrossAccountWashSaleChecker()
        c.record_taxable_loss("AAA", "2024-03-01")
        assert c.check_trade("AAA", "taxable", "2024-03-05")["allowed"]

    def test_other_ticker_unaffected_and_events_logged(self):
        c = CrossAccountWashSaleChecker()
        c.record_taxable_loss("AAA", "2024-03-01")
        assert c.check_trade("BBB", "roth", "2024-03-05")["allowed"]
        assert len(c.events) == 1

    def test_default_blackout_is_31_days(self):
        assert BLACKOUT_DAYS == 31


# --------------------------------------------------------------------- #
# The shipped config validates (with the intended RULE A flag)
# --------------------------------------------------------------------- #
class TestShippedConfig:
    def test_shipped_routing_config_loads_and_flags_core_book(self):
        from core.account_router import load_routing_config
        cfg = load_routing_config()
        v = validate_routing(cfg)
        # The shipped config deliberately routes the st_heavy core book
        # to taxable WITHOUT evidence — that RULE A error is the
        # deploy-gate signal T-141 exists to surface (see config _note).
        assert [x for x in v if x.rule == "st_heavy_taxable"]
        # No schema or universe violations.
        assert not [x for x in v if x.rule in ("schema", "universe_overlap")]
