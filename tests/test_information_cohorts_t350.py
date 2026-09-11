"""tests/test_information_cohorts_t350.py — INFORMATION-SET cohort boundaries.

THE DEFECT THIS CLOSES: the agentic arm's `query_prices` returned [] from deploy — the
substrate was never packaged — so the arm was PRICE-BLIND while carrying
`prompt_version: daily_agentic/v1` the entire time. `by_prompt_version` cannot see that
boundary BECAUSE THE PROMPT NEVER CHANGED, so any aggregate over "the agentic arm"
silently pools a blinded era with a fed one.
"""
from intelligence.analyst import fleet_scoring as fs
from intelligence.analyst import information_cohorts as ic

REG = {"analyst_agentic": {"default_cohort": "price_blind", "cohorts": [
    {"label": "price_blind", "from_date": None},
    {"label": "price_fed", "from_date": "2026-09-15"}]}}


def _row(src, date, cohort=None, p=0.6, o=1, key="k"):
    r = {"source": src, "note_date": date, "resolvable": True, "probability": p,
         "outcome": o, "prediction_id": f"{src}:{date}#{key}", "note_id": f"{src}:{date}",
         "category": "price_above", "resolve_date": date,
         "statement": f"s{key}", "resolver": {"type": "price_above", "symbol": "SPY",
                                              "level": 1, "direction": "above",
                                              "by_date": date}}
    if cohort:
        r["information_cohort"] = cohort
    return r


def test_undeployed_fix_means_every_agentic_row_is_price_blind():
    """A null from_date has NOT started — the honest default, not a placeholder."""
    assert ic.cohort_for("analyst_agentic", "2026-08-15", REG) == "price_blind"
    assert ic.cohort_for("analyst_agentic", "2026-09-14", REG) == "price_blind"


def test_rows_on_or_after_the_stamped_deploy_date_are_price_fed():
    assert ic.cohort_for("analyst_agentic", "2026-09-15", REG) == "price_fed"
    assert ic.cohort_for("analyst_agentic", "2026-10-01", REG) == "price_fed"


def test_a_blind_row_is_NEVER_retroactively_reinterpreted():
    """The canonicalization rule, applied to information: a price-blind row stays
    price-blind forever — that is what the arm actually saw."""
    before = ic.cohort_for("analyst_agentic", "2026-08-15", REG)
    # the fix deploys; the OLD row's label must not change
    assert ic.cohort_for("analyst_agentic", "2026-08-15", REG) == before == "price_blind"


def test_sources_without_declared_boundaries_are_unsegmented():
    assert ic.cohort_for("analyst_constrained", "2026-08-15", REG) is None


def test_spans_a_boundary_detects_the_pooling_hazard():
    mixed = [_row("analyst_agentic", "2026-08-15", "price_blind"),
             _row("analyst_agentic", "2026-09-20", "price_fed")]
    assert ic.spans_a_boundary(mixed) is True
    one_era = [_row("analyst_agentic", "2026-08-15", "price_blind"),
               _row("analyst_agentic", "2026-08-16", "price_blind")]
    assert ic.spans_a_boundary(one_era) is False


def test_AB_REFUSES_a_comparison_that_straddles_the_boundary():
    """The load-bearing guard: straddling is not a weak result, it is an INVALID one —
    the arms did not see the same world."""
    con = [_row("analyst_constrained", f"2026-08-{d:02d}", key=str(d)) for d in (15, 16, 17)]
    ag = [_row("analyst_agentic", "2026-08-15", "price_blind", key="15"),
          _row("analyst_agentic", "2026-08-16", "price_blind", key="16"),
          _row("analyst_agentic", "2026-09-20", "price_fed", key="17")]
    out = fs.ab_constrained_vs_agentic(con, ag)
    assert out["verdict"] == "INCONCLUSIVE_SPANS_INFORMATION_BOUNDARY"
    assert out["spans_information_boundary"] is True
    # and a refusal still keeps the constrained arm — never promotes on an invalid read
    assert out["tie_break"].startswith("keep_constrained")


def test_single_era_comparison_is_NOT_blocked():
    con = [_row("analyst_constrained", f"2026-08-{d:02d}", key=str(d)) for d in (15, 16)]
    ag = [_row("analyst_agentic", f"2026-08-{d:02d}", "price_blind", key=str(d)) for d in (15, 16)]
    out = fs.ab_constrained_vs_agentic(con, ag)
    assert out["verdict"] != "INCONCLUSIVE_SPANS_INFORMATION_BOUNDARY"
    assert out["spans_information_boundary"] is False


def test_cohort_counts_report_what_is_in_the_pool():
    rows = [_row("analyst_agentic", "2026-08-15", "price_blind"),
            _row("analyst_agentic", "2026-08-16", "price_blind"),
            _row("analyst_agentic", "2026-09-20", "price_fed")]
    assert ic.cohort_counts(rows)["analyst_agentic"] == {"price_blind": 2, "price_fed": 1}
