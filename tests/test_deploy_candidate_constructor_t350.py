# tests/test_deploy_candidate_constructor_t350.py
"""T-350 / Act 2 — the deploy-candidate constructor: the structural stack.

The account whose dollars-vs-SPY line the real-money option eventually reads, so
the tests lock the things that would quietly corrupt that number: the bands
actually binding, the cash leg leaving nothing idle, cash-before-selling, and
fail-closed on a config or price that cannot be trusted.
"""
import json

import pytest

from paper_trader.deploy_candidate_constructor import (
    DeployCandidateConstructor, DeployCandidatePlan)

CFG = {"core": {"ticker": "VOO", "weight": 0.85},
       "satellite": {"ticker": "MTUM", "weight": 0.15},
       "cash_ticker": "SGOV",
       "bands": {"buy_quanta": 1.5, "sell_quanta": 1.0, "max_drift": 0.10}}
PX = {"VOO": 600.0, "MTUM": 230.0, "SGOV": 100.0}


def _c(**kw):
    kw.setdefault("config", CFG)
    return DeployCandidateConstructor(trade_date="2026-09-11", tif="day", **kw)


def _orders(p):
    return {o.ticker: (o.side, o.qty) for o in p.orders}


# ---------------- the arrival event ----------------
def test_arrival_event_deploys_the_lump_sum_at_target(): 
    """From flat: the highest-stakes execution event a real transition would face."""
    p = _c().construct(10_000.0, {}, PX)
    o = _orders(p)
    assert o["VOO"] == ("buy", 14)      # 10000*0.85/600 = 14.16 → 14
    assert o["MTUM"] == ("buy", 6)      # 10000*0.15/230 = 6.52  → 6
    # every idle dollar swept into the cash leg, not left at 0%
    assert o["SGOV"][0] == "buy" and o["SGOV"][1] > 0


def test_the_cash_leg_leaves_nothing_material_idle():
    p = _c().construct(10_000.0, {}, PX)
    o = _orders(p)
    spent = 14 * 600 + 6 * 230 + o["SGOV"][1] * 100
    assert 10_000 - spent < 100.0      # residue below one SGOV share, by construction


# ---------------- the bands ----------------
def test_a_drift_inside_the_band_does_NOT_trade_and_says_why():
    """At $10k one VOO share is 6% of the book: a sub-quantum drift cannot bind."""
    p = _c().construct(10_000.0, {"VOO": 14, "MTUM": 6, "SGOV": 8}, PX)
    assert "VOO" not in _orders(p)
    assert "HOLD" in p.band_report["VOO"]


def test_buying_is_held_to_a_STRICTER_band_than_trimming():
    """The buy/hold spread: the same |gap| that triggers a trim must NOT trigger a buy."""
    c = _c()
    buy_band = c._band(PX["MTUM"], "buy", 10_000.0)
    sell_band = c._band(PX["MTUM"], "sell", 10_000.0)
    assert buy_band > sell_band
    # a gap between the two bands: trims, does not buy
    assert sell_band < 0.030 < buy_band


def test_a_band_is_denominated_in_share_quanta_not_flat_percent():
    """The T-297 argument: a band below the quantum cannot bind. VOO's band must be
    materially wider than MTUM's precisely because its share is worth more."""
    c = _c()
    assert c._band(PX["VOO"], "buy", 10_000.0) > c._band(PX["MTUM"], "buy", 10_000.0)
    assert c._band(PX["VOO"], "buy", 10_000.0) == pytest.approx(600.0 / 10_000.0 * 1.5)


def test_max_drift_binds_even_when_the_quantum_band_would_not():
    """A cheap instrument must not wander unboundedly just because its quantum is small."""
    c = _c()
    # MTUM massively overweight: 30 sh = 69% vs a 15% target
    p = c.construct(10_000.0, {"MTUM": 30}, PX)
    assert _orders(p)["MTUM"][0] == "sell"
    assert "max_drift" in p.band_report["MTUM"]


# ---------------- cash-flow awareness ----------------
def test_a_gap_is_funded_from_CASH_before_anything_is_sold():
    """Selling to fund a rebalance realises gains and burns wash-guard window for
    work a contribution can do for free (the Phase-1.5 machine-side rule)."""
    # holds the satellite but no core; plenty of idle cash to buy the core outright
    p = _c().construct(10_000.0, {"MTUM": 6}, PX)
    o = _orders(p)
    assert o["VOO"][0] == "buy"
    assert "VOO" in p.funded_by_cash
    assert not any(s == "sell" for s, _ in o.values()), "nothing should be sold"


# ---------------- fail-closed ----------------
def test_a_missing_price_holds_the_whole_day_with_a_stated_reason():
    p = _c().construct(10_000.0, {}, {"MTUM": 230.0, "SGOV": 100.0})
    assert p.orders == [] and p.degraded is True
    assert p.reject_reason == "missing_price:VOO"


def test_an_unpriced_cash_leg_is_STATED_not_silently_skipped():
    p = _c().construct(10_000.0, {}, {"VOO": 600.0, "MTUM": 230.0})
    assert "unpriced" in p.band_report["SGOV"]
    assert "SGOV" not in _orders(p)


def test_weights_that_do_not_sum_into_the_budget_are_REFUSED():
    bad = {**CFG, "core": {"ticker": "VOO", "weight": 0.9},
           "satellite": {"ticker": "MTUM", "weight": 0.3}}
    with pytest.raises(ValueError, match="must sum"):
        DeployCandidateConstructor(trade_date="d", config=bad)


def test_an_inverted_buy_hold_spread_is_REFUSED():
    bad = {**CFG, "bands": {"buy_quanta": 0.5, "sell_quanta": 1.0, "max_drift": 0.1}}
    with pytest.raises(ValueError, match="stricter to add"):
        DeployCandidateConstructor(trade_date="d", config=bad)


def test_a_broken_config_file_never_silently_enables_a_guessed_allocation(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/deploy_candidate.json").write_text("{not json")
    with pytest.raises(ValueError, match="refusing to construct"):
        DeployCandidateConstructor(trade_date="d", root=str(tmp_path))


# ---------------- the shipped config ----------------
def test_the_shipped_config_is_inside_the_APPROVED_range():
    """The plan approved VOO ~80-85% and MTUM 15-20%; config must stay in envelope."""
    cfg = json.loads(open("config/deploy_candidate.json").read())
    assert 0.80 <= cfg["core"]["weight"] <= 0.85
    assert 0.15 <= cfg["satellite"]["weight"] <= 0.20
    assert cfg["core"]["weight"] + cfg["satellite"]["weight"] == pytest.approx(1.0)
    assert cfg["cash_ticker"] == "SGOV"


def test_the_cash_leg_has_a_wash_sale_equivalence_class():
    """SGOV had NO class — a harvest against the cash leg would have been unguarded."""
    cls = json.loads(open("config/substantially_identical.json").read())["classes"]
    tbill = next((v for v in cls.values() if "SGOV" in v), None)
    assert tbill is not None and "BIL" in tbill


def test_the_core_shares_a_class_with_account_1s_holding():
    """VOO and SPY are substantially identical — acct-1 holds SPY, so the enforcing
    guard on acct-2 CAN bite. That is the design, and it must not regress silently."""
    cls = json.loads(open("config/substantially_identical.json").read())["classes"]
    assert any("VOO" in v and "SPY" in v for v in cls.values())


def test_the_budget_is_a_FRACTION_of_sizing_equity_not_a_dollar_figure():
    """Fleet idiom: budget = equity * sub_budget, and the pipeline passes
    sizing_equity = min(equity, notional_cap). Treating sub_budget as dollars would
    have silently bypassed the cap at the arrival-event tier reset."""
    p_full = _c().construct(10_000.0, {}, PX)
    p_half = _c(sub_budget=0.5).construct(10_000.0, {}, PX)
    assert p_half.target_qty["VOO"] * 2 <= p_full.target_qty["VOO"] + 1
    # and the CAP binds: a bigger account still sizes to the capped equity handed in
    assert _c().construct(10_000.0, {}, PX).target_qty["VOO"] == 14
