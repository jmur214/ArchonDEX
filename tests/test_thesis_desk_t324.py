"""T-324 — thesis-desk tests. All fixtures are SYNTHETIC/PARAPHRASED ([NN-AI-GATE] contamination rule):
never a real historical thesis with a known outcome. These test the schema + desk plumbing + the skew-aware
metric, not model skill.

The load-bearing assertions: a thesis WITHOUT a falsifier cannot be filed; a picks-and-shovels thesis must
name a second-order instrument; a backdated thesis is REFUSED; and the skew metric must score a 1-in-5
hit-rate-with-a-big-winner as GOOD (the whole design concession).
"""
import datetime as _dt

import pytest

from intelligence.thesis_desk.thesis_desk import (assert_forward_only, load_filed, file_thesis,
                                                  parse_seeds)
from intelligence.thesis_desk.thesis_schema import THEME_CLASSES, validate_thesis_call
from intelligence.thesis_desk.thesis_scoring import (ThesisOutcome, bootstrap_log_wealth_ci, brier,
                                                     log_wealth_ratio, payoff_profile, promotion_check)

TODAY = _dt.date(2026, 7, 28)


def _prov():
    return {"model_id_requested": "m", "model_id_served": "m", "prompt_version": "thesis_desk/v1",
            "prompt_sha256": "a" * 64, "input_bundle_sha256": "b" * 64}


def _thesis(**over):
    base = {
        "thesis_id": "t1", "as_of": "2026-07-28", "origin": "user_seeded",
        "narrative": "Synthetic: a capability threshold is crossed and the physical supply chain is the constraint.",
        "theme_class": "picks_and_shovels",
        "instruments": [{"symbol": "ZZZA", "role": "second_order",
                         "mapping_reason": "supplies the thermal gear every buildout requires regardless of winner",
                         "weight_hint": 0.5}],
        "conviction": 0.6, "horizon_days": 540,
        "entry_basis": "Synthetic: the constraint migrated this quarter and is not yet in consensus.",
        "falsifiers": [{"kind": "resolver", "statement": "underperforms SPY over the horizon",
                        "check_by": "2027-07-01",
                        "resolver": {"type": "relative_return", "symbol_a": "ZZZA", "symbol_b": "SPY",
                                     "start_date": "2026-07-28", "end_date": "2027-07-01",
                                     "op": "gt", "margin_bps": 0}}],
        "provenance": _prov(), "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}}
    base.update(over)
    return base


# ---- schema: the falsifier requirement is the whole point ----
def test_thesis_without_a_falsifier_cannot_be_filed():
    call, reason = validate_thesis_call(_thesis(falsifiers=[]))
    assert call is None and reason, "a thesis without a falsifier is a story, not a position"


def test_falsifier_must_be_resolver_valid_when_kind_is_resolver():
    bad = [{"kind": "resolver", "statement": "x", "check_by": "2027-07-01",
            "resolver": {"type": "relative_return", "symbol_a": "ZZZA"}}]   # missing fields
    assert validate_thesis_call(_thesis(falsifiers=bad))[0] is None


def test_falsifier_must_fire_before_the_horizon_ends():
    far = [{"kind": "qualitative", "statement": "x", "check_by": "2031-01-01"}]   # way past horizon
    assert validate_thesis_call(_thesis(falsifiers=far))[0] is None
    past = [{"kind": "qualitative", "statement": "x", "check_by": "2026-01-01"}]  # before as_of
    assert validate_thesis_call(_thesis(falsifiers=past))[0] is None


def test_picks_and_shovels_requires_a_second_order_instrument():
    only_primary = [{"symbol": "ZZZA", "role": "primary", "mapping_reason": "the obvious winner itself"}]
    assert validate_thesis_call(_thesis(instruments=only_primary))[0] is None


def test_second_order_needs_a_substantive_mapping_chain():
    thin = [{"symbol": "ZZZA", "role": "second_order", "mapping_reason": "benefits"}]   # < 5 words
    assert validate_thesis_call(_thesis(instruments=thin))[0] is None


def test_happy_path_validates_and_horizons_are_long():
    call, reason = validate_thesis_call(_thesis())
    assert call is not None and reason is None
    assert call.horizon_days == 540                      # months-to-years, honestly
    assert call.theme_class in THEME_CLASSES


# ---- desk: forward-only + the user-seeded channel ----
def test_backdated_thesis_is_refused():
    with pytest.raises(ValueError, match="NN-AI-GATE"):
        assert_forward_only("2015-01-02", today=TODAY)   # a thesis whose outcome the model knows
    assert_forward_only("2026-07-28", today=TODAY)       # today is fine


def test_seed_parser_reads_the_dead_simple_format():
    seeds = parse_seeds("## AI picks-and-shovels\nThe suppliers are the constraint.\ntickers: VRT, ETN\n")
    assert len(seeds) == 1
    s = seeds[0]
    assert s.tickers == ["ETN", "VRT"] and "constraint" in s.narrative and s.seed_id == "ai_picks-and-shovels"


def test_seed_without_tickers_is_valid_desk_maps_them():
    seeds = parse_seeds("## Defense during conflict\nRearmament cycles run for years.\n")
    assert len(seeds) == 1 and seeds[0].tickers == []


def test_file_thesis_appends_and_is_idempotent_by_id(tmp_path):
    led = tmp_path / "thesis_calls.jsonl"
    rec, err = file_thesis(_thesis(), ledger=led)
    assert rec and not err
    assert load_filed(led) == {"t1"}
    bad, err2 = file_thesis(_thesis(falsifiers=[]), ledger=led)
    assert bad is None and err2
    assert len(led.read_text().splitlines()) == 1        # the invalid one was NOT filed


# ---- the skew-aware metric: it MUST score 1-in-5-with-a-big-winner as good ----
def _o(tid, ret, twin, conv=0.5, tc="picks_and_shovels"):
    return ThesisOutcome(thesis_id=tid, theme_class=tc, conviction=conv, ret=ret, twin_ret=twin)


def test_one_in_five_with_a_big_winner_scores_POSITIVE():
    """The RKLB shape: four theses lose ~40% vs a flat twin, one is a multi-bagger. Hit rate 20% —
    a Brier/hit-rate view calls that a failure; the log-wealth view must be able to call it a success.

    The honest threshold (worth stating, because it is NOT free): with four −40% losses each costing
    log(0.60/1.05) ≈ −0.56, the winner must clear ≈ e^(4·0.56) ≈ 9.4× the twin just to break even. The
    RKLB trade (+557% ≈ 6.6×) does NOT clear that bar against four −40% losers — it does against three.
    The metric refuses to launder a losing record into a win, which is exactly what it is for."""
    outs = [_o("a", -0.40, 0.05), _o("b", -0.40, 0.05), _o("c", -0.40, 0.05), _o("d", -0.40, 0.05),
            _o("e", 9.5, 0.05)]                                  # a true 10-bagger clears it
    prof = payoff_profile(outs)
    assert prof["hit_rate"] == pytest.approx(0.2)               # 1-in-5
    assert log_wealth_ratio(outs) > 0                            # ...and it COMPOUNDS above the twin
    assert prof["win_loss_ratio"] > 1                            # the payoff asymmetry is visible


def test_the_metric_refuses_to_launder_a_losing_skewed_record():
    """The counterpart: 4x(−40%) + the actual RKLB (+557%) is NET NEGATIVE in compounding space
    (mean log-wealth ≈ −0.08). A hit-rate-with-big-winner story is NOT automatically a good record —
    the size of the winner has to actually cover the losses, and the metric says so."""
    outs = [_o("a", -0.40, 0.05), _o("b", -0.40, 0.05), _o("c", -0.40, 0.05), _o("d", -0.40, 0.05),
            _o("e", 5.57, 0.05)]
    assert payoff_profile(outs)["hit_rate"] == pytest.approx(0.2)
    assert log_wealth_ratio(outs) < 0                             # honest: this record LOST money
    # ...but the same winner against THREE losers clears it — the threshold is real and computable
    assert log_wealth_ratio(outs[1:]) > 0


def test_all_losers_scores_negative():
    outs = [_o(str(i), -0.30, 0.05) for i in range(5)]
    assert log_wealth_ratio(outs) < 0


def test_promotion_bar_blocks_on_small_n_even_when_profitable():
    outs = [_o("a", 5.0, 0.05), _o("b", 4.0, 0.05), _o("c", 3.0, 0.05)]   # great, but n=3
    res = promotion_check(outs, "picks_and_shovels")
    assert res["PROMOTED"] is False and res["reason"] == "insufficient_n"


def test_promotion_bar_blocks_when_ci_straddles_zero():
    outs = [_o(str(i), 0.10 if i % 2 else -0.10, 0.0) for i in range(25)]  # noisy, no edge
    res = promotion_check(outs, "picks_and_shovels")
    assert res["n_ok"] is True and res["PROMOTED"] is False and res["reason"] == "ci_straddles_zero"


def test_brier_and_log_wealth_are_reported_together():
    outs = [_o(str(i), 0.5, 0.05, conv=0.9) for i in range(5)]
    assert brier(outs) is not None and bootstrap_log_wealth_ci(outs) is not None
