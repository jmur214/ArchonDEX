"""tests/test_performance_digest_t329.py — T-329 weekly digest design laws.

Locks the laws that protect the user's main touchpoint: dollars-per-$10K, n ALWAYS
visible (short records can't overclaim), NO pressure mechanics, missing streams
reported not dropped, fail-open.
"""
import re

from intelligence.analyst import performance_digest as pd_


def test_short_record_cannot_overclaim_however_good_the_numbers():
    # a spectacular 10-day record still reads "too early to say"
    v = pd_.verdict(delta_per_10k=5000.0, n_days=10)
    assert v.startswith("too early to say") and "10 days" in v


def test_verdicts_carry_n_and_use_only_allowlisted_phrases():
    for d, n in [(500.0, 200), (-500.0, 200), (5.0, 200), (100.0, 3)]:
        v = pd_.verdict(d, n)
        assert any(v.startswith(a) for a in pd_.ALLOWED_VERDICTS), v
        assert re.search(r"\(\d+ days\)", v), v          # n is ALWAYS visible


def test_small_gap_reads_as_roughly_matching_not_a_win():
    assert pd_.verdict(10.0, 200).startswith("roughly matching")


def test_no_pressure_mechanics_anywhere_in_the_rendered_digest():
    rows = pd_.build_rows({
        "account-1 sleeve": {"book_nav": 1.02, "twin_nav": 1.00, "n_days": 200, "current_drawdown_pct": -3.1},
        "llm shadow": {"book_nav": 0.99, "twin_nav": 1.00, "n_days": 20, "current_drawdown_pct": -6.0},
    })
    text = pd_.render(rows, "2026-07-28").lower()
    banned = ["countdown", "days remaining", "decision approaching", "ready for real money",
              "deadline", "act now", "on track to deploy", "streak", "don't miss"]
    for b in banned:
        assert b not in text, f"pressure mechanic leaked: {b}"
    assert "informational only" in text


def test_dollars_per_10k_is_the_unit():
    rows = pd_.build_rows({"s": {"book_nav": 1.018, "twin_nav": 1.000, "n_days": 200}})
    assert rows[0]["delta_per_10k"] == 180.0             # (1.018-1.000)*10_000
    assert "per $10K" in pd_.render(rows, "2026-07-28")


def test_missing_stream_is_reported_not_dropped():
    rows = pd_.build_rows({"live": {"book_nav": 1.01, "twin_nav": 1.0, "n_days": 90},
                           "silent": {}})
    text = pd_.render(rows, "2026-07-28")
    assert any(r["missing"] for r in rows)
    assert "Not reporting" in text and "silent" in text


def test_summary_is_three_lines_and_says_nothing_decidable_when_all_early():
    rows = pd_.build_rows({"a": {"book_nav": 1.05, "twin_nav": 1.0, "n_days": 5},
                           "b": {"book_nav": 0.95, "twin_nav": 1.0, "n_days": 5}})
    text = pd_.render(rows, "2026-07-28")
    assert "Nothing is decidable yet" in text
    body = text.split("---")[0]
    assert body.count("streams tracked") == 1


def test_generate_is_fail_open(tmp_path):
    bad = pd_.generate({"x": {"book_nav": 1.0, "twin_nav": 1.0, "n_days": 10}},
                       "2026-07-28", out_path=tmp_path / "nope" / "d.md", archive=False)
    assert bad["ok"] is True                              # parent dirs created, no raise
    res = pd_.generate({"x": {"book_nav": "not-a-number", "twin_nav": 1.0, "n_days": 10}},
                       "2026-07-28", out_path=tmp_path / "d2.md", archive=False)
    assert isinstance(res, dict) and "ok" in res          # never raises into the pulse


# ── T-332a rider (C): the cash-drag annotation is SECONDARY, never the record ──
_CA_NOTE = ("ANNOTATION ONLY — the raw NAV above is the record. Live paper cash earns "
            "0%; the backtest spec credits the short rate, so this shows what that gap "
            "is worth. Never a restatement.")


def _stream_with_cash_adj():
    return {"book": {"book_nav": 1.000, "twin_nav": 1.000, "n_days": 200,
                     "current_drawdown_pct": -2.0,
                     "cash_adj": {"book_nav_cash_adj": 1.000, "twin_nav_cash_adj": 1.030,
                                  "rate_missing_days": 2, "note": _CA_NOTE}}}


def test_cash_adj_is_secondary_never_replaces_the_record():
    rows = pd_.build_rows(_stream_with_cash_adj())
    r = rows[0]
    # raw record: flat vs twin -> "roughly matching". The annotation says -$300/10K.
    assert r["delta_per_10k"] == 0.0
    assert r["cash_adj_per_10k"] == -300.0
    # THE LAW: the verdict is computed off the RAW record, never the annotation
    assert r["verdict"].startswith("roughly matching")
    text = pd_.render(rows, "2026-07-29")
    # the table column carries the RAW number; the annotation lives in its own section
    table = text.split("### Cash-drag annotation")[0]
    assert "−$300" not in table and "-$300" not in table
    assert "Cash-drag annotation (secondary — not the record)" in text


def test_cash_adj_note_is_carried_verbatim_and_missing_days_surfaced():
    text = pd_.render(pd_.build_rows(_stream_with_cash_adj()), "2026-07-29")
    assert _CA_NOTE in text                     # verbatim, unedited — the disclaimer travels
    assert "2 day(s) missing a rate" in text
    assert "verdicts above are computed from the RAW record only" in text


def test_no_annotation_section_when_no_stream_has_one():
    text = pd_.render(pd_.build_rows({"b": {"book_nav": 1.01, "twin_nav": 1.0, "n_days": 90}}),
                      "2026-07-29")
    assert "Cash-drag annotation" not in text
