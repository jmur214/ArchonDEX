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
