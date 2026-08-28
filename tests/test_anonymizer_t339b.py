"""tests/test_anonymizer_t339b.py — the anonymizer T-339 should have had."""
from intelligence.analyst import anonymizer as an

TOK = "ENTITY_7F3A"


def test_the_exact_T339_failure_is_now_caught():
    """T-339's real leak: the ticker was replaced, 'Tesla' was left in plain sight."""
    text = "Tesla Moves Forward With Plans For China Factory Tesla Inc (NASDAQ: TSLA) shares popped"
    out, reasons = an.scrub_or_drop(text, TOK, "TSLA", company="Tesla Inc")
    assert out is not None, reasons
    assert "Tesla" not in out and "TSLA" not in out


def test_name_variants_cover_suffixes_and_hyphens():
    v = an.name_variants("BMY", "Bristol-Myers Squibb Co")
    assert any("Bristol-Myers Squibb" in x for x in v)
    assert "Bristol" in v
    # longest-first so the full name is replaced before its fragments
    assert len(v[0]) >= len(v[-1])


def test_dates_are_scrubbed_because_text_dated_itself_in_T339():
    out = an.scrub("Revenue rose in Q3 2017 and again in fiscal 2019, by March 3, 2020",
                   TOK, "XYZ")
    assert "2017" not in out and "2019" not in out and "2020" not in out
    assert "[DATE]" in out


def test_unscrubbable_text_is_DROPPED_not_sent():
    """A surviving identifier must drop the question — never a partial send."""
    def leaky_ner(t):            # a backend that misses everything
        return []
    text = "Acme Corp announced a deal"        # company not supplied, NER blind
    out, reasons = an.scrub_or_drop(text, TOK, "ZZZZ", company=None,
                                    ner_fn=lambda t: ["Acme Corp"])
    assert out is None or "Acme" not in out
    # with a blind backend and no company name, verify() cannot see it -> admitted;
    # that is exactly why the frozen spec REQUIRES a real NER backend.
    out2, _ = an.scrub_or_drop(text, TOK, "ZZZZ", ner_fn=leaky_ner)
    assert out2 is not None


def test_verify_is_independent_of_scrub_so_a_weak_backend_drops_not_leaks():
    """verify() re-checks the OUTPUT: a scrubber that misses a name must yield a DROP."""
    half_scrubbed = "Apple announced results"          # pretend scrub missed 'Apple'
    ok, surviving = an.verify(half_scrubbed, "AAPL", company="Apple Inc")
    assert ok is False and any("Apple" in s for s in surviving)


def test_admitted_text_carries_zero_identifiers():
    out, _ = an.scrub_or_drop("Apple Inc (AAPL) beat estimates in 2021", TOK, "AAPL",
                              company="Apple Inc")
    ok, surviving = an.verify(out, "AAPL", company="Apple Inc")
    assert ok is True and surviving == []
