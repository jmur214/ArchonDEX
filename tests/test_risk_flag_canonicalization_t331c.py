"""tests/test_risk_flag_canonicalization_t331c.py — ONE canonical name per condition.

The defect this locks: the analysts emitted ~10 spellings for one condition
(news_degraded / news_panel_degraded / news_feed_degraded / degraded_news_feed /
degraded_news_panel / empty_news_panel / news_feed_unavailable / no_news_feed ...).
Three-plus names for one condition means NO GATE CAN COUNT IT.

THE RULE: grandfather variants in the READER, never in the writer.
"""
from intelligence.analyst import risk_flags as rf


def test_every_observed_variant_normalizes_to_ONE_countable_token():
    variants = ["news_degraded", "news_panel_degraded", "news_feed_degraded",
                "degraded_news_feed", "degraded_news_panel", "empty_news_panel",
                "news_feed_unavailable", "no_news_feed"]
    assert {rf.normalize(v) for v in variants} == {rf.NEWS_DEGRADED_LEGACY}


def test_writer_may_emit_ONLY_canonical_tokens():
    assert rf.is_writer_legal(rf.NEWS_COVERAGE_THIN) is True
    assert rf.is_writer_legal(rf.NEWS_FEED_DEGRADED) is True
    # every legacy spelling is reader-only — grandfathering the WRITER is how five
    # names became untrackable in the first place
    for v in ("news_degraded", "news_panel_degraded", "degraded_news_feed"):
        assert rf.is_writer_legal(v) is False
    assert rf.is_writer_legal(rf.NEWS_DEGRADED_LEGACY) is False   # legacy is not writable either


def test_legacy_is_NOT_retroactively_reinterpreted():
    """We cannot know whether a 2026-08 `news_degraded` meant a fault or thin coverage —
    the bundle could not distinguish them then. It must stay labelled ambiguous."""
    assert rf.normalize("news_degraded") == rf.NEWS_DEGRADED_LEGACY
    assert rf.normalize("news_degraded") not in (rf.NEWS_FEED_DEGRADED, rf.NEWS_COVERAGE_THIN)
    assert "ambiguous" in rf.NEWS_DEGRADED_LEGACY


def test_unknown_flag_passes_through_not_swallowed():
    """A normalizer, not a filter — swallowing an unrecognized flag would hide the
    very drift this module exists to expose."""
    assert rf.normalize("some_brand_new_flag") == "some_brand_new_flag"


def test_compound_flags_are_left_distinct():
    """A flag bundling news with prices/events must NOT be absorbed into a news count."""
    for c in rf.COMPOUND_UNMAPPED:
        assert rf.normalize(c) == c
        assert rf.normalize(c) != rf.NEWS_DEGRADED_LEGACY


def test_count_condition_is_what_a_gate_calls():
    notes = [{"risk_flags": ["news_degraded"]},          # variant 1
             {"risk_flags": ["news_panel_degraded"]},    # variant 2
             {"risk_flags": ["degraded_news_feed"]},     # variant 3
             {"risk_flags": ["something_else"]}]
    assert rf.count_condition(notes, rf.NEWS_DEGRADED_LEGACY) == 3   # ONE number from 3 spellings


def test_normalize_all_dedupes_variants_within_one_note():
    """Two spellings of the SAME condition in one note must count once, not twice."""
    out = rf.normalize_all(["news_degraded", "news_panel_degraded", "other"])
    assert out.count(rf.NEWS_DEGRADED_LEGACY) == 1 and "other" in out
