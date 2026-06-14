# tests/test_paper_pr3_partB_t163.py
"""T-163 PR-3 Part B — production order-construction wiring (read-only)
+ allocator visibility + the shadow kill layer + promotion telemetry.

The constructor is tested against FAKE engines (the read-only contract:
the adapter only CALLS engines, so fakes prove the A→C→B SEQUENCE).
Telemetry is tested against the REAL shipped modules (T-152 monitors,
T-151 safe-f, T-141 router) — they are lightweight and importable.
"""
from __future__ import annotations

import pandas as pd
import pytest

from paper_trader import (
    DivergenceShadow,
    OrderSpec,
    PaperConfig,
    PaperOrderConstructor,
    PromotionReport,
    RouterShadow,
    SafefWeeklyJob,
)


# --------------------------------------------------------------------- #
# PaperConfig — allocator visibility (T-158)
# --------------------------------------------------------------------- #
class TestPaperConfig:
    def test_defaults_are_t159_roth(self):
        c = PaperConfig(allocator="adaptive")
        assert c.account == "roth" and c.starting_equity == 5_000.0
        assert c.dynamic_optimization_enabled is True   # whole-share for auctions

    def test_allocator_must_be_explicit_and_valid(self):
        with pytest.raises(ValueError, match="allocator"):
            PaperConfig(allocator="magic")

    def test_allocator_has_no_silent_default(self):
        # M4/T-158: a bare PaperConfig() must RAISE — never silently
        # pick the local/adaptive machine.
        with pytest.raises(TypeError):
            PaperConfig()

    def test_allocator_is_in_log_dict_every_cycle(self):
        c = PaperConfig(allocator="mean_variance")
        d = c.log_dict()
        assert d["allocator"] == "mean_variance"    # visible, not inherited
        assert "config_hash" in d

    def test_config_hash_deterministic_and_sensitive(self):
        assert PaperConfig(allocator="adaptive").config_hash() == PaperConfig(allocator="adaptive").config_hash()
        assert PaperConfig(allocator="adaptive").config_hash() != \
            PaperConfig(allocator="mean_variance").config_hash()

    def test_policy_config_carries_allocator_and_dynopt(self):
        c = PaperConfig(allocator="mean_variance")
        pcfg = c.portfolio_policy_config()
        assert pcfg.mode == "mean_variance"
        assert pcfg.dynamic_optimization_enabled is True


# --------------------------------------------------------------------- #
# PaperOrderConstructor — A→C→B sequence (fake engines)
# --------------------------------------------------------------------- #
class _FakeAlpha:
    def __init__(self, signals): self._signals = signals
    def generate_signals(self, data_map, now, regime_meta=None):
        return list(self._signals)


class _FakePortfolio:
    def __init__(self): self.last_signal_map = None
    def compute_target_allocations(self, signals, price_data, equity, regime_meta=None):
        self.last_signal_map = dict(signals)
        return {t: 0.3 for t in signals}


class _FakeRisk:
    """Returns one order per signal, qty proportional to |score|."""
    def prepare_order(self, signal, equity, df_hist, current_qty=0,
                      target_weights=None, regime_meta=None):
        side = signal.get("side")
        if side == "none":
            return None
        engine_side = {"long": "long", "short": "short",
                       "exit": "exit"}.get(side, "long")
        return {"ticker": signal["ticker"], "side": engine_side,
                "qty": 10, "edge": signal.get("edge", "e1")}


def _bars(tickers):
    idx = pd.bdate_range("2026-06-01", periods=40)
    return {t: pd.DataFrame({"Close": [100.0] * 40}, index=idx) for t in tickers}


class TestOrderConstructor:
    def test_constructs_specs_through_real_sequence(self):
        signals = [{"ticker": "AAPL", "side": "long", "strength": 0.8, "edge": "mom"},
                   {"ticker": "MSFT", "side": "short", "strength": 0.5}]
        ctor = PaperOrderConstructor(_FakeAlpha(signals), _FakePortfolio(),
                                     _FakeRisk(), PaperConfig(allocator="adaptive"))
        specs = ctor.construct(_bars(["AAPL", "MSFT"]),
                               pd.Timestamp("2026-06-15"), 5_000.0)
        assert len(specs) == 2
        by = {s.ticker: s for s in specs}
        assert by["AAPL"].side == "buy" and by["AAPL"].tif == "opg"   # long entry → OPG
        assert by["MSFT"].side == "sell"                              # short → sell

    def test_signal_map_drops_none_and_signs_shorts(self):
        port = _FakePortfolio()
        signals = [{"ticker": "AAPL", "side": "long", "strength": 0.8},
                   {"ticker": "MSFT", "side": "short", "strength": 0.6},
                   {"ticker": "SPY", "side": "none", "strength": 0.0}]
        ctor = PaperOrderConstructor(_FakeAlpha(signals), port, _FakeRisk(), PaperConfig(allocator="adaptive"))
        ctor.construct(_bars(["AAPL", "MSFT", "SPY"]), pd.Timestamp("2026-06-15"), 5_000.0)
        assert port.last_signal_map["AAPL"] == pytest.approx(0.8)
        assert port.last_signal_map["MSFT"] == pytest.approx(-0.6)   # short → negative
        assert "SPY" not in port.last_signal_map                     # none dropped

    def test_exit_routes_to_cls_under_moo_moc(self):
        signals = [{"ticker": "AAPL", "side": "exit", "strength": 1.0}]
        ctor = PaperOrderConstructor(_FakeAlpha(signals), _FakePortfolio(),
                                     _FakeRisk(), PaperConfig(allocator="adaptive", auction_execution="moo_moc"))
        specs = ctor.construct(_bars(["AAPL"]), pd.Timestamp("2026-06-15"), 5_000.0)
        assert specs[0].side == "sell" and specs[0].tif == "cls"

    def test_exit_routes_to_opg_under_moo(self):
        signals = [{"ticker": "AAPL", "side": "exit", "strength": 1.0}]
        ctor = PaperOrderConstructor(_FakeAlpha(signals), _FakePortfolio(),
                                     _FakeRisk(), PaperConfig(allocator="adaptive", auction_execution="moo"))
        specs = ctor.construct(_bars(["AAPL"]), pd.Timestamp("2026-06-15"), 5_000.0)
        assert specs[0].tif == "opg"

    def test_spec_stage_args_match_order_manager(self):
        from paper_trader import OrderManager, FakePaperClient, TimeInForce
        signals = [{"ticker": "AAPL", "side": "long", "strength": 0.8}]
        ctor = PaperOrderConstructor(_FakeAlpha(signals), _FakePortfolio(),
                                     _FakeRisk(), PaperConfig(allocator="adaptive"))
        spec = ctor.construct(_bars(["AAPL"]), pd.Timestamp("2026-06-15"), 5_000.0)[0]
        # stage_args feed straight into OrderManager.stage(**args)
        mgr = OrderManager(FakePaperClient(), journal_path="/tmp/_t163_x.jsonl",
                           reconcile_on_start=False)
        o = mgr.stage("2026-06-15", config_hash="c", **spec.stage_args())
        assert o.ticker == "AAPL" and o.side == "buy" and o.tif == "opg"


# --------------------------------------------------------------------- #
# DivergenceShadow — T-152 monitors, SHADOW only
# --------------------------------------------------------------------- #
class TestDivergenceShadow:
    def test_big_innovation_fires_shadow_alarm(self):
        sh = DivergenceShadow()
        fired = None
        for i in range(40):
            # sustained large adverse innovation
            fired = sh.update(realized_return=-0.05, expected_mean=0.0005,
                              expected_std=0.01, date=f"d{i}")
        assert sh.n_obs == 40
        assert len(sh.alarms) >= 1          # something fired (shadow)

    def test_sigma_guard_skips(self):
        sh = DivergenceShadow()
        out = sh.update(0.01, 0.0, 0.0)     # zero sigma
        assert out.get("skipped") == "no_valid_sigma"
        assert sh.n_obs == 0

    def test_quiet_stream_mostly_silent(self):
        sh = DivergenceShadow()
        for i in range(60):
            sh.update(0.0005 + (0.0001 if i % 2 else -0.0001), 0.0005, 0.01)
        assert len(sh.alarms) <= 2          # near-quiet at the operating point


# --------------------------------------------------------------------- #
# PromotionReport — paper-only telemetry
# --------------------------------------------------------------------- #
class TestPromotionReport:
    def test_slippage_signed_adverse(self):
        r = PromotionReport()
        # buy filled above expected = adverse positive
        assert r.record_fill("AAPL", "buy", 100.10, 100.00) == pytest.approx(10.0)
        # sell filled below expected = adverse positive
        assert r.record_fill("MSFT", "sell", 99.90, 100.00) == pytest.approx(10.0)

    def test_reject_map_and_divergence_null(self):
        r = PromotionReport()
        r.record_reject("fractional"); r.record_reject("fractional")
        r.record_reject("buying_power")
        for z in (0.1, -0.2, 0.3):
            r.record_divergence_z(z)
        snap = r.snapshot()
        assert snap["rejection_map"] == {"fractional": 2, "buying_power": 1}
        assert snap["divergence_null"]["n"] == 3

    def test_promotion_criteria_status(self):
        r = PromotionReport()
        r.n_trading_days = 60
        for _ in range(120):
            r.record_fill("AAPL", "buy", 100.02, 100.00)   # ~2bps
        for _ in range(100):
            r.record_cycle(clean=True)
        snap = r.snapshot()
        assert snap["promotion_criteria"]["duration_ok"] is True
        assert snap["promotion_criteria"]["slippage_ok"] is True
        assert snap["promotion_criteria"]["reconcile_ok"] is True

    def test_criteria_fail_when_short(self):
        r = PromotionReport()
        r.n_trading_days = 5
        snap = r.snapshot()
        assert snap["promotion_criteria"]["duration_ok"] is False


# --------------------------------------------------------------------- #
# RouterShadow (T-141) + SafefWeeklyJob (T-151)
# --------------------------------------------------------------------- #
class TestRouterShadowAndSafef:
    def test_router_shadow_blackout_verdict(self):
        rs = RouterShadow()
        rs.feed_taxable_loss("AAPL", "2026-03-01")
        v = rs.shadow_check("AAPL", "roth", "2026-03-15")  # inside 31d window
        assert v["allowed"] is False
        assert len(rs.verdicts) == 1

    def test_safef_weekly_insufficient_then_fires(self):
        job = SafefWeeklyJob(min_history_days=126)
        short = job.run([0.001] * 60)
        assert short["fired"] is False and short["reason"] == "insufficient_history"
        import numpy as np
        rng = np.random.default_rng(0)
        long_rec = list(rng.normal(0.0005, 0.01, 300))
        out = job.run(long_rec)
        assert out["fired"] is True and out["safe_f"] is not None
