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
