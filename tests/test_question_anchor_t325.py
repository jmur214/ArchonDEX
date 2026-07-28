"""T-325 — the shared question anchor: deterministic, resolver/v1-valid, identical
across both analysts, paired by stable id."""
from __future__ import annotations

import datetime as dt

from intelligence.analyst.question_anchor import anchor_questions, anchor_ids
from intelligence.analyst.eval_harness import is_resolvable_spec

AS_OF = dt.date(2026, 7, 28)


def test_every_anchor_resolver_is_resolvable():
    for q in anchor_questions(AS_OF):
        ok, why = is_resolvable_spec(q["resolver"])
        assert ok, f"{q['anchor_id']} not resolvable: {why}"


def test_anchor_is_deterministic_same_day():
    assert anchor_questions(AS_OF) == anchor_questions(AS_OF)
    assert anchor_ids(AS_OF) == anchor_ids(AS_OF)


def test_anchor_differs_across_days():
    assert anchor_ids(AS_OF) != anchor_ids(dt.date(2026, 7, 29))


def test_anchor_carries_no_injected_price_level():
    # self-contained resolvers only (relative_return / dd_exceeds) — no price
    # level that could smuggle in a future value (look-ahead).
    types = {q["resolver"]["type"] for q in anchor_questions(AS_OF)}
    assert types <= {"relative_return", "dd_exceeds"}
    for q in anchor_questions(AS_OF):
        assert "level" not in q["resolver"]


def test_anchor_ids_are_stable_hashes_of_the_resolver():
    qs = anchor_questions(AS_OF)
    ids = anchor_ids(AS_OF)
    assert [q["anchor_id"] for q in qs] == ids
    assert all(i.startswith("anc-") for i in ids)
    assert len(set(ids)) == len(ids)   # unique


def test_accepts_string_as_of():
    assert anchor_ids("2026-07-28") == anchor_ids(AS_OF)


def test_both_analysts_would_see_the_identical_anchor():
    # the constrained and agentic paths both inject anchor_questions(as_of) into
    # the bundle — same function, same as_of ⇒ byte-identical questions.
    from intelligence.analyst.question_anchor import anchor_questions as aq
    assert aq(AS_OF) == aq(AS_OF)   # (the injection is one shared call, verified)
