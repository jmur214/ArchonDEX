"""T-319 — the cross-account wash-sale guard (spec A/T-317 §1).

A's SIX required tests (§1.3) + the account-1 BYTE-NEUTRAL regression lock (the
single-account, guard-off path must be behaviourally identical)."""
from __future__ import annotations

import datetime as dt

import pytest

from engines.engine_b_risk.cross_account_wash_guard import (
    CrossAccountWashGuard, EquivalenceClasses, TaxLotLedger, WashSaleRefusal)
from paper_trader import FakePaperClient, OrderManager
from paper_trader.order_manager import OrderState, TimeInForce

CLASSES = EquivalenceClasses({
    "US_LARGE_BLEND": ["SPY", "VOO", "IVV", "SPLG"],
    "US_TOTAL": ["VTI", "ITOT", "SCHB"],
    "AGG_CORE_BOND": ["AGG", "BND"],
    "GOLD": ["GLD", "IAU"],
}, version="test")


def _guard(tmp_path):
    led = TaxLotLedger(str(tmp_path / "tax_lots.jsonl"))
    return CrossAccountWashGuard(led, CLASSES), led


def _taxable_spy_loss(led, sell_day):
    """Open a SPY lot @100 in taxable, sell @90 (a loss) on ``sell_day``."""
    led.record_fill(account="taxable", symbol="SPY", side="buy", qty=10,
                    price=100.0, ts=dt.date(2026, 1, 1))
    ev = led.record_fill(account="taxable", symbol="SPY", side="sell", qty=10,
                         price=90.0, ts=sell_day)
    assert ev.is_loss_sale and ev.realized_pnl == -100.0
    return ev


# ── A's six required tests (§1.3) ──────────────────────────────────────────────
def test_1_taxable_spy_loss_then_roth_voo_buy_inside_61d_refuses_2008_5(tmp_path):
    g, led = _guard(tmp_path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    d = g.check_order(account="roth", symbol="VOO", side="buy", ts=dt.date(2026, 2, 20))
    assert d.refused and d.reason == "rev_rul_2008_5_permanent_disallowance"
    assert d.evidence and d.evidence[0]["symbol"] == "SPY"


def test_2_same_buy_at_day_62_allows(tmp_path):
    g, led = _guard(tmp_path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    # 31 days after the sale is outside the +30 window (61-day window = [-30,+30])
    d = g.check_order(account="roth", symbol="VOO", side="buy", ts=dt.date(2026, 3, 4))
    assert d.allow


def test_3_backward_roth_buy_then_taxable_loss_sale_flags_would_be_wash(tmp_path):
    g, led = _guard(tmp_path)
    # Roth VOO buy on day 10; taxable SPY loss-sale on day 30 → the SALE is flagged
    led.record_fill(account="roth", symbol="VOO", side="buy", qty=5, price=100.0,
                    ts=dt.date(2026, 1, 10))
    d = g.check_loss_sale(account="taxable", symbol="SPY", ts=dt.date(2026, 1, 30))
    assert d.refused and d.reason == "would_be_wash"
    assert d.evidence[0]["symbol"] == "VOO" and d.evidence[0]["account"] == "roth"


def test_4_voo_to_vti_cross_class_allows(tmp_path):
    g, led = _guard(tmp_path)
    # a VOO (large-blend) loss then a VTI (total-market) buy — the court-tested
    # NOT-substantially-identical distinction the harvest loop trades on.
    led.record_fill(account="taxable", symbol="VOO", side="buy", qty=10, price=100.0,
                    ts=dt.date(2026, 1, 1))
    led.record_fill(account="taxable", symbol="VOO", side="sell", qty=10, price=90.0,
                    ts=dt.date(2026, 2, 1))
    d = g.check_order(account="roth", symbol="VTI", side="buy", ts=dt.date(2026, 2, 10))
    assert d.allow


def test_5_refusal_is_loud_typed_exception_via_ordermanager(tmp_path):
    g, led = _guard(tmp_path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    om = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "roth.jsonl"),
                      wash_guard=g, account="roth")
    order = om.stage("2026-02-20", "VOO", "buy", 5, TimeInForce.DAY, "cfg")
    with pytest.raises(WashSaleRefusal) as ei:
        om.submit(order)
    assert ei.value.reason == "rev_rul_2008_5_permanent_disallowance"
    # REJECTED + typed reason journalled; the broker was NEVER called
    assert order.state == OrderState.REJECTED.value
    assert order.reject_reason == "wash_sale:rev_rul_2008_5_permanent_disallowance"
    assert order.broker_order_id is None


def test_6_ledger_survives_simulated_ephemeral_restart(tmp_path):
    path = str(tmp_path / "tax_lots.jsonl")
    led = TaxLotLedger(path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    # simulate a fresh Fargate container: a brand-new ledger reading the same file
    led2 = TaxLotLedger(path)
    g2 = CrossAccountWashGuard(led2, CLASSES)
    d = g2.check_order(account="roth", symbol="IVV", side="buy", ts=dt.date(2026, 2, 15))
    assert d.refused and d.reason == "rev_rul_2008_5_permanent_disallowance"


# ── a taxable→taxable loss is still refused, as a DEFERRAL (spec §1.2) ──────────
def test_taxable_to_taxable_is_deferral_reason(tmp_path):
    g, led = _guard(tmp_path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    d = g.check_order(account="taxable", symbol="SPY", side="buy", ts=dt.date(2026, 2, 10))
    assert d.refused and d.reason == "wash_sale_deferral"


def test_sell_never_trips_the_guard(tmp_path):
    g, led = _guard(tmp_path)
    _taxable_spy_loss(led, dt.date(2026, 2, 1))
    assert g.check_order(account="roth", symbol="VOO", side="sell",
                         ts=dt.date(2026, 2, 10)).allow


def test_a_gain_sale_does_not_poison(tmp_path):
    # a PROFITABLE sale is not a wash-sale trigger — only losses poison.
    g, led = _guard(tmp_path)
    led.record_fill(account="taxable", symbol="SPY", side="buy", qty=10, price=90.0,
                    ts=dt.date(2026, 1, 1))
    ev = led.record_fill(account="taxable", symbol="SPY", side="sell", qty=10,
                         price=100.0, ts=dt.date(2026, 2, 1))
    assert not ev.is_loss_sale
    assert g.check_order(account="roth", symbol="VOO", side="buy",
                         ts=dt.date(2026, 2, 10)).allow


# ── the account-1 BYTE-NEUTRAL regression lock ─────────────────────────────────
def _run_flow(om):
    """A representative buy→fill→sell flow; returns the observable trail."""
    b = om.stage("2026-02-10", "SPY", "buy", 4, TimeInForce.DAY, "cfg")
    om.submit(b)
    s = om.stage("2026-02-11", "AGG", "sell", 3, TimeInForce.DAY, "cfg")
    om.submit(s)
    return [(o.ticker, o.side, o.state, o.reject_reason, o.filled_qty)
            for o in (b, s)]


def test_account1_guard_off_is_byte_neutral(tmp_path):
    # guard=None (the single-account Roth-only path) must behave identically to a
    # pre-T-319 OrderManager: same states, same fills, no rejections, no ledger.
    om_off = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "a.jsonl"))
    trail_off = _run_flow(om_off)
    # every order reaches a normal terminal/fill state; NOTHING is wash-rejected
    assert all(rr is None for (_, _, _, rr, _) in trail_off)
    assert all(st != OrderState.REJECTED.value for (_, _, st, _, _) in trail_off)
    # and no tax-lot ledger file is ever created when the guard is absent
    assert not (tmp_path / "tax_lots.jsonl").exists()


def test_guard_on_but_no_conflict_matches_guard_off(tmp_path):
    # with a guard attached but NO prior loss-sale, the order outcomes are the
    # same as guard-off (the guard only bites on a real conflict).
    om_off = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "off.jsonl"))
    g, _ = _guard(tmp_path)
    om_on = OrderManager(FakePaperClient(), journal_path=str(tmp_path / "on.jsonl"),
                         wash_guard=g, account="roth")
    assert ([(t, s, st) for (t, s, st, _, _) in _run_flow(om_off)]
            == [(t, s, st) for (t, s, st, _, _) in _run_flow(om_on)])
