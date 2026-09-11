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


# ── T-351: STAMPED vs PENDING — an unconfirmed boundary must not assert the old label ──
REG_PENDING = {"analyst_agentic": {"default_cohort": "price_blind", "cohorts": [
    {"label": "price_blind", "from_date": None},
    {"label": "price_fed", "from_date": None, "pending_from": "2026-09-11"}]}}

REG_STAMPED = {"analyst_agentic": {"default_cohort": "price_blind", "cohorts": [
    {"label": "price_blind", "from_date": None},
    {"label": "price_fed", "from_date": "2026-09-11", "pending_from": "2026-09-11"}]}}


def test_once_the_fix_is_LIVE_the_old_default_becomes_a_MISLABEL():
    """The defect T-351 closes: rev33 deployed and the arm could see prices, but with a
    null from_date every post-fix row would still have been labelled `price_blind` —
    a confident claim that is simply false."""
    assert ic.cohort_for("analyst_agentic", "2026-09-10", REG_PENDING) == "price_blind"
    after = ic.cohort_for("analyst_agentic", "2026-09-11", REG_PENDING)
    assert after == "price_fed_UNSTAMPED"
    assert ic.is_unstamped(after) is True
    assert after != "price_blind"          # the mislabel is what this prevents


def test_stamping_RESOLVES_the_declared_unknown():
    """Resolving an explicit UNSTAMPED marker is a resolution, not a retroactive
    reinterpretation — the never-reinterpret rule protects SETTLED claims."""
    assert ic.cohort_for("analyst_agentic", "2026-09-11", REG_STAMPED) == "price_fed"
    assert ic.is_unstamped("price_fed") is False
    # and a SETTLED pre-boundary row is untouched by the stamp landing
    assert ic.cohort_for("analyst_agentic", "2026-08-15", REG_STAMPED) == "price_blind"
    assert ic.cohort_for("analyst_agentic", "2026-08-15", REG_PENDING) == "price_blind"


def test_a_stamped_boundary_wins_over_a_pending_one():
    assert ic.cohort_for("analyst_agentic", "2026-09-20", REG_STAMPED) == "price_fed"


def test_AB_still_refuses_when_rows_straddle_into_the_UNSTAMPED_era():
    """An unstamped era is still a different information set — pooling it is invalid."""
    con = [_row("analyst_constrained", f"2026-08-{d:02d}", key=str(d)) for d in (15, 16, 17)]
    ag = [_row("analyst_agentic", "2026-08-15", "price_blind", key="15"),
          _row("analyst_agentic", "2026-08-16", "price_blind", key="16"),
          _row("analyst_agentic", "2026-09-12", "price_fed_UNSTAMPED", key="17")]
    out = fs.ab_constrained_vs_agentic(con, ag)
    assert out["verdict"] == "INCONCLUSIVE_SPANS_INFORMATION_BOUNDARY"
    assert out["tie_break"].startswith("keep_constrained")


# ── T-352: the per-era A/B — the VALID path a refusal must offer ─────────────
def test_per_era_AB_buckets_BOTH_arms_by_DATE_not_by_their_own_label():
    """THE BUG THIS LOCKS: only the agentic arm carries cohort labels. Bucketing each
    row by its OWN label put constrained in `unsegmented` and agentic in `price_blind`
    — ZERO pairs in every era, a comparison that could never run. Both arms must bucket
    by DATE against the boundary-carrying source."""
    con = [_row("analyst_constrained", f"2026-08-{d:02d}", key=str(d)) for d in (15, 16, 17)]
    ag = [_row("analyst_agentic", f"2026-08-{d:02d}", "price_blind", key=str(d))
          for d in (15, 16, 17)]
    out = fs.ab_by_information_cohort(con, ag)["by_cohort"]
    assert "price_blind" in out
    assert out["price_blind"]["eligible_pairs"] == 3, "both arms must land in the same era"


def test_the_blinded_era_is_NOT_quotable_as_the_AB():
    """An era whose agentic arm was blinded cannot say whether the agentic DESIGN is
    better — only what a blinded version did. The result must say so itself."""
    con = [_row("analyst_constrained", "2026-08-15", key="a")]
    ag = [_row("analyst_agentic", "2026-08-15", "price_blind", key="a")]
    res = fs.ab_by_information_cohort(con, ag)["by_cohort"]["price_blind"]
    assert res["quotable_as_the_AB"] is False
    assert "NOT a comparison of the agentic DESIGN" in res["question_answered"]


def test_a_post_stamp_era_IS_quotable():
    con = [_row("analyst_constrained", "2026-09-15", key="a")]
    ag = [_row("analyst_agentic", "2026-09-15", key="a")]
    out = fs.ab_by_information_cohort(con, ag)["by_cohort"]
    era = [k for k in out if "fed" in k][0]
    assert out[era]["quotable_as_the_AB"] is True


def test_eras_are_kept_SEPARATE_so_neither_pools_into_the_other():
    con = ([_row("analyst_constrained", "2026-08-15", key="a")]
           + [_row("analyst_constrained", "2026-09-15", key="b")])
    ag = ([_row("analyst_agentic", "2026-08-15", key="a")]
          + [_row("analyst_agentic", "2026-09-15", key="b")])
    out = fs.ab_by_information_cohort(con, ag)["by_cohort"]
    assert len(out) == 2                      # one comparison per era, never merged
    assert all(r["spans_information_boundary"] is False for r in out.values())
