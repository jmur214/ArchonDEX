# tests/test_analyst_daily_v4_t331bc.py
"""T-331bc — daily/v4 + the `market_tape` bundle section: the input repair.

The analyst flagged degraded news on 19/19 notes because its slice is
TICKER-SCOPED and its ETF sleeve is structurally near-uncovered on a
company-tagged tape (AGG/BIL/IEF: zero tags). The repair feeds the daily
analysts the same ticker-agnostic broad slice the blind scan already reads.

Same discipline as T-329c: the SCOPE locks are the tests that matter. v4 adds
one prose section and one bundle key; the predictions contract must stay
byte-identical so the Brier record remains comparable across every cohort
boundary, and the actions contract must survive from v3 untouched.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd

from intelligence.analyst.context_builder import (
    build_bundle, bundle_sha256, _market_tape_section)

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "config/prompts/analyst/daily_v2.md"
V3 = ROOT / "config/prompts/analyst/daily_v3.md"
V4 = ROOT / "config/prompts/analyst/daily_v4.md"


def _section(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end)]


def _flat(p: Path) -> str:
    return " ".join(p.read_text().split())


# ------------------------------------------------------ the scope locks
def test_v3_still_exists_unmodified_so_the_revert_is_one_edit():
    """The revert ID in the prompt-evolution log points at this exact artifact —
    the sha is the one stamped into every production v3 note's provenance."""
    assert V3.exists()
    assert (hashlib.sha256(V3.read_bytes()).hexdigest()
            == "64bd8544c50fd5b009abda388e5911da6c6ca4e49670dfd500a940cd7e913067")


def test_predictions_contract_is_BYTE_IDENTICAL_across_the_v3_v4_boundary():
    a = _section(V3.read_text(), "# Anchor questions", "# Output shape")
    b = _section(V4.read_text(), "# Anchor questions", "# Output shape")
    assert a == b


def test_predictions_contract_is_still_identical_all_the_way_back_to_v2():
    """Transitivity made explicit: one Brier record, three prompt cohorts."""
    a = _section(V2.read_text(), "# Anchor questions", "# Output shape")
    b = _section(V4.read_text(), "# Anchor questions", "# Output shape")
    assert a == b


def test_the_predictions_line_of_the_output_shape_is_unchanged():
    def pred_line(p):
        return [l for l in p.read_text().splitlines() if '"predictions"' in l]
    assert pred_line(V3) == pred_line(V4) != []


def test_v4_keeps_the_open_channel_and_the_firewall_verbatim():
    """v4 is an INPUT repair; the v3 actions contract is not in scope. Both
    halves must survive: the channel stays open, the bound stays hard."""
    t = _flat(V4)
    assert "are consumed" in t and "real paper orders" in t
    assert "no_action_reason" in t
    assert "[-0.20, 0.20]" in t and "NEVER above 0.20" in t
    assert "REJECTED WHOLE — never quietly trimmed to fit" in t
    assert "They are never executed" not in t


def test_v4_describes_the_market_tape_and_pins_the_no_invented_tickers_rule():
    t = _flat(V4)
    assert "market_tape" in t
    assert "not filtered to your symbols" in t
    # the tape names non-sleeve companies by design — the symbol discipline must
    # be restated where the temptation is created
    assert "never names lifted from a headline" in t


def test_the_caller_points_at_v4_everywhere_the_record_segments():
    src = (ROOT / "paper_trader/intel_pulse.py").read_text()
    assert 'prompt_path="config/prompts/analyst/daily_v4.md"' in src
    assert 'prompt_version="daily/v4"' in src
    assert 'prompt_version="daily/v3"' not in src


def test_the_prompt_evolution_stamp_exists_and_carries_every_required_field():
    log = (ROOT / "docs/Core/prompt_evolution_log.md").read_text()
    assert "## `daily/v4`" in log
    v4 = log[log.index("## `daily/v4`"):]
    for field in ("Scope of change", "Trigger", "Pre-stated outcome measure",
                  "Revert ID", "Cohort note"):
        assert field in v4, f"stamp missing required field: {field}"
    # the trigger is the 19/19 structural diagnosis, not vibes
    assert "19 of 19" in v4 and "TICKER-SCOPED" in v4


# ------------------------------------------------------ the bundle section
def _panel(rows):
    return pd.DataFrame(rows)


def _lp(rows):
    def load_panel(as_of=None):
        return _panel(rows)
    return load_panel


def test_market_tape_is_ticker_agnostic_and_pit_guarded():
    rows = [
        {"created_at": "2026-08-24T13:00:00Z", "headline": "grid buildout accelerates",
         "symbols": ["VRT"]},
        {"created_at": "2026-08-25T09:00:00Z", "headline": "SAME-DAY headline must not leak",
         "symbols": ["SPY"]},
        {"created_at": "2026-08-23T10:00:00Z", "headline": "shipping rates spike",
         "symbols": []},
    ]
    s = _market_tape_section(dt.date(2026, 8, 25), load_panel=_lp(rows))
    heads = [i["headline"] for i in s["items"]]
    assert s["degraded"] is False
    # ticker-agnostic: the untagged row is present; PIT: the as_of-dated row is not
    assert "shipping rates spike" in heads
    assert "grid buildout accelerates" in heads
    assert "SAME-DAY headline must not leak" not in heads


def test_market_tape_dedupes_and_caps_deterministically():
    rows = ([{"created_at": f"2026-08-{d:02d}T10:00:00Z", "headline": f"h{d}"}
             for d in range(1, 21)]
            + [{"created_at": "2026-08-20T11:00:00Z", "headline": "h20"}])  # dup headline
    s = _market_tape_section(dt.date(2026, 8, 25), load_panel=_lp(rows), cap=5)
    assert len(s["items"]) == 5
    # newest survive the cap; the duplicate headline appears once
    heads = [i["headline"] for i in s["items"]]
    assert heads == ["h16", "h17", "h18", "h19", "h20"]


def test_market_tape_degrades_honestly_on_an_empty_panel():
    s = _market_tape_section(dt.date(2026, 8, 25), load_panel=_lp([]))
    assert s["items"] == [] and s["degraded"] is True and s["reason"] == "empty_panel"


def test_market_tape_fails_open_with_a_named_reason():
    def boom(as_of=None):
        raise RuntimeError("panel exploded")
    s = _market_tape_section(dt.date(2026, 8, 25), load_panel=boom)
    assert s["items"] == [] and s["degraded"] is True
    assert s["reason"].startswith("tape_error:")


def test_bundle_carries_market_tape_and_bumps_bundle_version():
    rows = [{"created_at": "2026-08-24T13:00:00Z", "headline": "x", "symbols": ["SPY"]}]
    b = build_bundle("2026-08-25", portfolios={"sleeve": {"SPY": 0.6}},
                     load_panel=_lp(rows))
    assert b["bundle_version"] == "analyst_input/v2"
    assert b["market_tape"]["degraded"] is False
    assert [i["headline"] for i in b["market_tape"]["items"]] == ["x"]
    # the ticker-scoped news section and its coverage block are untouched
    assert "coverage" in b["news"]


def test_bundle_stays_deterministic_with_the_new_section():
    rows = [{"created_at": "2026-08-24T13:00:00Z", "headline": "x", "symbols": ["SPY"]}]
    b1 = build_bundle("2026-08-25", portfolios={"sleeve": {"SPY": 0.6}}, load_panel=_lp(rows))
    b2 = build_bundle("2026-08-25", portfolios={"sleeve": {"SPY": 0.6}}, load_panel=_lp(rows))
    assert bundle_sha256(b1) == bundle_sha256(b2)


def test_both_analyst_arms_share_the_bundle_builder():
    """The A/B stays paired: constrained and agentic must receive market_tape from
    the same first day, which they do by construction iff both import build_bundle."""
    for mod in ("intelligence/analyst/analyst_service.py",
                "intelligence/analyst/analyst_agentic.py"):
        assert "build_bundle" in (ROOT / mod).read_text()
