"""T-329 — the account-3 (stage-2) LLMAnalystConstructor: the analyst's validated target
weights → real paper orders, with the shadow-book safety discipline re-enforced."""
from __future__ import annotations

import json

import pandas as pd

from paper_trader.llm_analyst_constructor import LLMAnalystConstructor, LLMAnalystPlan

HEX64 = "a" * 64


def _closes(**px) -> dict:
    # a short flat series per ticker; the constructor reads the LAST value
    return {t: pd.Series([float(v)] * 5) for t, v in px.items()}


def _note(as_of="2026-09-01", actions=None):
    """A minimal note dict for the INJECTED path (bypasses re-validation)."""
    return {"as_of": as_of,
            "hypothetical_actions": [dict(account="shadow", **a) for a in (actions or [])]}


def _act(symbol, target_weight, set_weight=None):
    return {"symbol": symbol, "set_weight": set_weight if set_weight is not None else target_weight,
            "target_weight": target_weight}


def _ctor(note, *, positions=None, equity=100_000.0, closes=None, **kw):
    c = LLMAnalystConstructor(trade_date="2026-09-02", note=note, **kw)
    return c.construct(equity, positions or {}, closes or _closes(SPY=100.0, AGG=50.0, GLD=200.0))


# ---------------- happy path ----------------
def test_targets_become_whole_share_orders(tmp_path):
    p = _ctor(_note(actions=[_act("SPY", 0.15), _act("AGG", 0.10)]))
    assert isinstance(p, LLMAnalystPlan) and p.reject_reason is None and not p.degraded
    assert p.note_as_of == "2026-09-01" and p.stream == "analyst"
    # SPY: 100k*0.15/100 = 150 sh; AGG: 100k*0.10/50 = 200 sh
    assert p.target_qty["SPY"] == 150 and p.target_qty["AGG"] == 200
    o = {x.ticker: x for x in p.orders}
    assert o["SPY"].side == "buy" and o["SPY"].qty == 150 and o["SPY"].edge == "llm_analyst"
    assert o["AGG"].side == "buy" and o["AGG"].qty == 200


def test_delta_against_held_positions(tmp_path):
    # already hold 100 SPY; target 150 → buy 50. Hold 300 AGG; target 200 → sell 100.
    p = _ctor(_note(actions=[_act("SPY", 0.15), _act("AGG", 0.10)]),
              positions={"SPY": 100, "AGG": 300})
    o = {x.ticker: x for x in p.orders}
    assert o["SPY"].side == "buy" and o["SPY"].qty == 50
    assert o["AGG"].side == "sell" and o["AGG"].qty == 100 and o["AGG"].engine_side == "exit"


def test_no_order_when_already_at_target(tmp_path):
    p = _ctor(_note(actions=[_act("SPY", 0.15)]), positions={"SPY": 150})
    assert p.orders == [] and p.target_qty["SPY"] == 150   # a no-trade day is canonical, not degraded
    assert not p.degraded and p.reject_reason is None


def test_sub_budget_scales_sizing(tmp_path):
    # analyst gets 50% of the account → half the shares
    p = _ctor(_note(actions=[_act("SPY", 0.15)]), sub_budget=0.5)
    assert p.target_qty["SPY"] == 75    # 50k*0.15/100


# ---------------- fail-closed ----------------
def test_no_note_holds_and_states_why(tmp_path):
    p = _ctor(None)
    assert p.degraded and p.orders == [] and p.reject_reason.startswith("no_note:")


def test_missing_price_holds_the_whole_day(tmp_path):
    # note targets TSLA but we have no TSLA price → HOLD everything, degraded (never a blind order)
    p = _ctor(_note(actions=[_act("SPY", 0.10), _act("TSLA", 0.10)]))
    assert p.degraded and p.orders == [] and "missing_price" in p.reject_reason and "TSLA" in p.reject_reason


def test_missing_price_on_a_held_name_also_holds(tmp_path):
    # we hold a name we can't price → can't safely rebalance → HOLD
    p = _ctor(_note(actions=[_act("SPY", 0.10)]), positions={"ZZZZ": 10})
    assert p.degraded and p.orders == [] and "ZZZZ" in p.reject_reason


# ---------------- firewall (reject loudly, never clamp) ----------------
def test_weight_over_cap_is_rejected_not_clamped(tmp_path):
    p = _ctor(_note(actions=[_act("SPY", 0.35)]))     # > 20%
    assert p.orders == [] and p.reject_reason.startswith("REJECTED:") and "exceeds" in p.reject_reason


def test_gross_over_cap_is_rejected(tmp_path):
    acts = [_act("SPY", 0.20), _act("AGG", 0.20), _act("GLD", 0.20)]  # gross 0.60 within; push over 2.0 impossible w/ 3 names ≤0.2
    # use many names via a wide allowlist-free note near cap each → gross > 2.0 needs 11 names @0.2; simulate with high single-name blocked already.
    # instead test gross with weights within per-name but summing > max_gross via a low max_gross
    c = LLMAnalystConstructor(trade_date="2026-09-02",
                              note=_note(actions=[_act("SPY", 0.15), _act("AGG", 0.15)]),
                              max_gross=0.20)          # force the gross cap to bite
    p = c.construct(100_000.0, {}, _closes(SPY=100.0, AGG=50.0))
    assert p.orders == [] and "gross" in p.reject_reason


def test_turnover_over_cap_is_rejected(tmp_path):
    # target a full 20% SPY from flat, with a tiny turnover cap → rejected
    c = LLMAnalystConstructor(trade_date="2026-09-02",
                              note=_note(actions=[_act("SPY", 0.20)]), max_turnover=0.05)
    p = c.construct(100_000.0, {}, _closes(SPY=100.0))
    assert p.orders == [] and "turnover" in p.reject_reason


# ---------------- allowlist + look-ahead ----------------
def test_allowlist_filters_out_of_universe_targets(tmp_path):
    p = _ctor(_note(actions=[_act("SPY", 0.15), _act("NVDA", 0.10)]),
              allowlist=("SPY", "AGG", "GLD"))
    assert "SPY" in p.target_qty and "NVDA" not in p.target_qty


def test_look_ahead_is_impossible_only_prior_notes_load(tmp_path):
    # write two REAL (validated) notes: one dated BEFORE trade_date, one ON it. Only the prior loads.
    from intelligence.analyst.note_schema import validate_note
    nd = tmp_path / "data/intel/analyst_notes"
    nd.mkdir(parents=True)
    def _valid(as_of, tw):
        payload = {"as_of": as_of, "market_assessment": "test",
                   "hypothetical_actions": [{"account": "shadow", "symbol": "SPY",
                                             "set_weight": tw, "target_weight": tw}],
                   "provenance": {"model_id_requested": "m", "model_id_served": "m",
                                  "prompt_version": "daily/v2", "prompt_sha256": HEX64,
                                  "input_bundle_sha256": HEX64},
                   "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}}
        assert validate_note(payload)[0] is not None, "fixture note must validate"
        (nd / f"note_{as_of}.json").write_text(json.dumps(payload))
    _valid("2026-09-01", 0.10)      # yesterday — should load
    _valid("2026-09-02", 0.18)      # TODAY — must be ignored (look-ahead)
    c = LLMAnalystConstructor(trade_date="2026-09-02", root=str(tmp_path))
    p = c.construct(100_000.0, {}, _closes(SPY=100.0))
    assert p.note_as_of == "2026-09-01"        # the prior note, never today's
    assert p.target_qty["SPY"] == 100          # 100k*0.10/100, not 0.18


def test_orders_are_orderspecs_fleet_plan_parity(tmp_path):
    p = _ctor(_note(actions=[_act("SPY", 0.15)]))
    assert all(hasattr(o, "stage_args") for o in p.orders)   # plugs into _run_family_strategy
    assert p.orders[0].stage_args()["ticker"] == "SPY"


# ---------------- T-329d3: the NEGATIVE-weight (short-tilt) path ----------------
# The channel's spec has permitted negative target_weights in [-0.20, 0) since
# daily/v2 — the prompt's own bound language — and the shadow book applies them
# as virtual short positions. These tests document what the REAL order path does
# with one, discovered on the eve of the first action-bearing note (2026-08-26:
# SPY +0.08 / AGG -0.05). NOTE for the record: there is NO long-only firewall
# anywhere in this path; whether the real account should ever short is a
# DIRECTOR-RULING question, not something this module decides. If a long-only
# gate is ever added, it must cover the shadow book too or the paired
# real-vs-shadow A/B breaks.

def test_short_rounding_truncates_toward_zero_never_overshooting(tmp_path):
    """floor(-5.1) is -6: under math.floor a -5% target on a $10k budget became
    a $588 (5.9%) short — |realized| EXCEEDED |requested|, the exact thing the
    conservative long-side rounding exists to prevent. int() truncation keeps
    the invariant sign-symmetric: -5.1 shares → -5."""
    p = _ctor(_note(actions=[_act("AGG", -0.05)]), equity=10_000.0,
              closes=_closes(AGG=98.01))
    assert p.reject_reason is None
    assert p.target_qty["AGG"] == -5                      # not -6
    assert abs(p.target_qty["AGG"] * 98.01) <= 0.05 * 10_000.0


def test_a_short_target_currently_emits_a_sell_of_unheld_shares(tmp_path):
    """CURRENT behavior, documented: a negative target with nothing held becomes
    a plain SELL order (qty = |target_qty|) — i.e. a broker short on the paper
    account. No gate in the constructor or the OMS refuses it (the ±20%/gross/
    turnover firewall passes it by design). If this test starts failing because
    a long-only gate was added, make sure that was a ruled, stamped decision."""
    p = _ctor(_note(actions=[_act("AGG", -0.05)]), equity=10_000.0,
              closes=_closes(AGG=98.01))
    o = {x.ticker: x for x in p.orders}
    assert o["AGG"].side == "sell" and o["AGG"].qty == 5


def test_a_short_beyond_the_bound_is_still_rejected_whole(tmp_path):
    p = _ctor(_note(actions=[_act("AGG", -0.25)]))
    assert p.reject_reason is not None and "REJECTED" in p.reject_reason
    assert p.orders == []
