"""tests/test_advisor_surface_t343.py — the advisor memo generator's design laws."""
from intelligence.analyst import advisor_surface as ad


def test_equivalent_alpha_math_is_sane_and_decays_with_horizon():
    """+$1k/yr is worth MORE bps on a short horizon (small base) and less on a long
    one (compounding dominates) — the exchange rate must fall monotonically."""
    rows = ad.sensitivity_table(15_000, 7_000, 0.07)
    bps = [r["equivalent_alpha_bps"] for r in rows]
    assert all(b is not None and b > 0 for b in bps)
    assert bps == sorted(bps, reverse=True)          # strictly decaying with horizon
    for r in rows:
        assert r["plus_terminal"] > r["base_terminal"] and r["delta_dollars"] > 0


def test_zero_return_does_not_divide_by_zero():
    assert ad.fv(1000, 1000, 0.0, 10) == 11_000


def test_no_pressure_mechanics_and_generate_refuses_if_they_appear(tmp_path):
    res = ad.generate(15_000, 7_000, 0.07, as_of="2026-08-25", out_path=tmp_path / "a.md")
    assert res["ok"] is True
    low = (tmp_path / "a.md").read_text().lower()
    for w in ad.BANNED_PRESSURE_WORDS:
        assert w not in low
    assert "does not recommend a date" in low


def test_missing_census_is_REPORTED_not_invented(tmp_path):
    text = ad.render(15_000, 7_000, 0.07, as_of="2026-08-25")
    assert "Awaiting the wrapper census" in text
    assert "Input contract" in text                  # tells the director what to collect
    assert "| rank | move |" not in text             # no fabricated ranking


def test_census_present_ranks_by_annual_dollars_certain_sign_only():
    census = {"accounts": [
        {"account_type": "401k", "balance": 50_000, "annual_contribution": 2_000,
         "employer_match": {"rate": 0.5, "cap_dollars": 6_000}, "fee_drag_bps": 60,
         "contribution_headroom": 0},
        {"account_type": "roth", "balance": 15_000, "annual_contribution": 7_000,
         "fee_drag_bps": 3, "contribution_headroom": 0}]}
    moves = ad.rank_wrapper_moves(census, 0.07)
    vals = [m["annual_value"] for m in moves]
    assert vals == sorted(vals, reverse=True)        # ranked by dollars
    assert any("employer match" in m["move"] for m in moves)
    assert all("allocation" not in m["move"] for m in moves)   # forecasts are NOT ranked
    text = ad.render(15_000, 7_000, 0.07, wrapper_census=census, as_of="2026-08-25")
    assert "| rank | move |" in text and "Awaiting the wrapper census" not in text


def test_generator_is_fail_open():
    assert ad.generate("bad", 7_000, 0.07, as_of="x")["ok"] is False   # never raises


# ── T-345: capital-adaptive tier matrix + assumption labelling ────────────────
def test_tier_matrix_is_capital_adaptive_and_decays_with_balance():
    """A contribution increase dominates MORE at small balances — the exchange rate
    must fall as the tier rises (that is the whole point of showing tiers)."""
    rows = ad.tier_matrix(ad.DEFAULT_TIERS, 7_000, 0.07, horizons=(10, 20, 40))
    assert [r["tier"] for r in rows] == list(ad.DEFAULT_TIERS)
    y10 = [dict(r["cells"])[10] for r in rows]
    assert y10 == sorted(y10, reverse=True)      # smaller balance -> larger equivalent alpha
    for r in rows:                                # and decays with horizon within a tier
        c = dict(r["cells"])
        assert c[10] > c[20] > c[40] > 0


def test_inputs_are_labelled_ASSUMPTIONS_until_the_census_lands():
    """The surface must never read as if it knows the user's balance."""
    no_census = ad.render(10_000, 7_000, 0.07, as_of="2026-08-26")
    assert "ASSUMED starting balance" in no_census
    assert "these are ASSUMPTIONS, not the user's figures" in no_census
    with_census = ad.render(10_000, 7_000, 0.07, as_of="2026-08-26",
                            wrapper_census={"accounts": []})
    assert "Actual starting balance" in with_census
    assert "these are ASSUMPTIONS" not in with_census


# ── T-346: the phase-structured census memo ───────────────────────────────────
import json as _json
from pathlib import Path as _Path

_CENSUS = _json.loads(_Path("config/wrapper_census.json").read_text())


def test_memo_leads_with_the_open_question_not_a_ranked_list():
    """The school-funding question determines liquidity; ranking anything above it
    would be optimising under an unknown constraint."""
    t = ad.render_memo(_CENSUS, as_of="2026-08-27")
    q_at = t.index("The top open question")
    assert q_at < t.index("Phase 1")            # the question precedes every phase
    assert "UNANSWERED" in t
    assert "does not try" in t                   # it declines to rank against liquidity


def test_memo_is_scoped_as_a_sidebar_not_a_steering_input():
    t = ad.render_memo(_CENSUS, as_of="2026-08-27")
    assert "sidebar, not a steering input" in t
    assert "does **not** re-prioritise the research program" in t


def test_memo_carries_the_liquidity_flag_before_any_optimisation():
    t = ad.render_memo(_CENSUS, as_of="2026-08-27")
    assert t.index("liquidity flag") < t.index("Phase 1")
    assert "must NOT sit in the 40-year" in t


def test_memo_has_three_phases_and_states_capacity_drops_during_school():
    t = ad.render_memo(_CENSUS, as_of="2026-08-27")
    for p in ("Phase 1 — NOW", "Phase 2 — DURING SCHOOL", "Phase 3 — POST-SCHOOL"):
        assert p in t
    assert "falls to ~zero" in t                 # capacity is NOT projected straight-line
    assert "pre- and post-school" in t


def test_memo_reports_absent_wrappers_honestly_not_as_moves():
    """No 401k and no match today: a calendar trigger, never a 'capture the match' item."""
    t = ad.render_memo(_CENSUS, as_of="2026-08-27")
    assert "no match exists to capture now" in t.lower()
    assert "calendar trigger" in t
    assert "HDHP" in t and "verify" in t.lower()  # HSA is conditional on a fact to check


def test_memo_has_no_pressure_words():
    t = ad.render_memo(_CENSUS, as_of="2026-08-27").lower()
    for w in ad.BANNED_PRESSURE_WORDS:
        assert w not in t
