"""T-325 #5 — the stage-2 operational-proof clock (readiness, not calendar)."""
from __future__ import annotations

from paper_trader.stage2_clock import record_day, evaluate, PROPOSED_N


def _rec(path, day, a_ok=True, g_ok=True, cost=1.0, budget=30.0):
    return record_day(path, as_of=f"2026-07-{day:02d}", analyst_ok=a_ok,
                      agentic_ok=g_ok, cost_mtd=cost, budget=budget)


def test_empty_is_not_ready(tmp_path):
    v = evaluate(str(tmp_path / "s.jsonl"))
    assert not v.ready and v.consecutive_clean == 0 and "no days" in v.reason


def test_n_clean_days_becomes_ready(tmp_path):
    p = str(tmp_path / "s.jsonl")
    for d in range(20, 20 + PROPOSED_N):
        _rec(p, d)
    v = evaluate(p, PROPOSED_N)
    assert v.ready and v.consecutive_clean == PROPOSED_N and "PROPOSE" in v.reason


def test_one_short_is_not_ready(tmp_path):
    p = str(tmp_path / "s.jsonl")
    for d in range(20, 20 + PROPOSED_N - 1):
        _rec(p, d)
    v = evaluate(p, PROPOSED_N)
    assert not v.ready and v.consecutive_clean == PROPOSED_N - 1


def test_an_invalid_analyst_resets_the_streak(tmp_path):
    p = str(tmp_path / "s.jsonl")
    _rec(p, 20); _rec(p, 21); _rec(p, 22, g_ok=False)   # agentic invalid on day 22
    _rec(p, 23); _rec(p, 24)
    v = evaluate(p, 5)
    # only days 23-24 are clean after the reset
    assert v.consecutive_clean == 2 and not v.ready


def test_a_budget_breach_resets_the_streak(tmp_path):
    p = str(tmp_path / "s.jsonl")
    _rec(p, 20); _rec(p, 21, cost=31.0, budget=30.0)   # over envelope
    _rec(p, 22); _rec(p, 23)
    v = evaluate(p, 5)
    assert v.consecutive_clean == 2
    # the breaching day was recorded as not-clean
    days = {r["as_of"]: r for r in v.last_days}
    assert days["2026-07-21"]["clean"] is False and days["2026-07-21"]["in_envelope"] is False


def test_same_day_rerun_is_idempotent(tmp_path):
    p = str(tmp_path / "s.jsonl")
    _rec(p, 20); _rec(p, 20); _rec(p, 20)   # three runs of the SAME day
    v = evaluate(p, 5)
    assert v.consecutive_clean == 1   # counted once, not thrice


def test_clean_requires_both_analysts_and_envelope(tmp_path):
    row = _rec(str(tmp_path / "s.jsonl"), 20, a_ok=True, g_ok=True, cost=1.0, budget=30.0)
    assert row["clean"] is True
    row2 = _rec(str(tmp_path / "s2.jsonl"), 20, a_ok=True, g_ok=False)
    assert row2["clean"] is False


def test_survives_reload_from_disk(tmp_path):
    p = str(tmp_path / "s.jsonl")
    for d in range(20, 25):
        _rec(p, d)
    # a fresh evaluate() re-reads the durable file (simulated ephemeral restart)
    assert evaluate(p, 5).ready
