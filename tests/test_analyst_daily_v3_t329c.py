# tests/test_analyst_daily_v3_t329c.py
"""T-329c — daily/v3: open the `hypothetical_actions` channel, and ONLY that.

v2 closed the channel by its own words ("They are never executed", "Omit the whole
list if you have no small-tilt view") and the model complied for 15 straight days,
which is what held account-3's ignition. v3 opens it.

The tests that matter most here are the SCOPE locks. A prompt edit is an edit to the
measuring instrument: the director's ruling was that only the actions section moves,
so that the Brier record stays comparable across the cohort boundary the version bump
creates. That constraint is worth a test, not a promise — a future editor with good
intentions is exactly who would widen it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from intelligence.analyst.note_schema import validate_note
from paper_trader.llm_analyst_constructor import LLMAnalystConstructor

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "config/prompts/analyst/daily_v2.md"
V3 = ROOT / "config/prompts/analyst/daily_v3.md"
HEX64 = "a" * 64


def _section(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end)]


def _flat(p: Path) -> str:
    """Prompt prose is hard-wrapped, so a phrase spans lines. Collapse whitespace
    before asserting on wording — otherwise these tests break on a re-wrap, which
    is not the change they exist to catch."""
    return " ".join(p.read_text().split())


# ------------------------------------------------------ the scope locks
def test_v2_still_exists_unmodified_so_the_revert_is_one_edit():
    """The revert ID in the prompt-evolution log points at this file. If it can
    vanish or drift, 'revert' becomes an excavation."""
    assert V2.exists()
    assert "They are never executed" in _flat(V2)   # v2 is the channel-dark prompt


def test_v2_on_disk_is_the_prompt_that_actually_produced_the_live_notes():
    """Ground truth, not a self-check: this SHA is the `provenance.prompt_sha256`
    stamped into the real 2026-08-14 note pulled from S3. It proves the revert
    target on disk is byte-identical to the artifact that ran in production — a
    revert to a drifted v2 would restore a prompt we never actually observed."""
    import hashlib
    assert (hashlib.sha256(V2.read_bytes()).hexdigest()
            == "6459f11ab60277aeea2817da898dd1732a0c974d57cafb2afec7c90f33e606ec")


def test_predictions_contract_is_BYTE_IDENTICAL_across_the_v2_v3_boundary():
    """THE load-bearing lock. The anchor-questions, calibration and resolver sections
    define what predictions are and how they are scored. If they move, the Brier
    record either side of the cohort boundary is not comparable and the whole
    'labeled cohort, not a corrupted record' argument collapses."""
    a = _section(V2.read_text(), "# Anchor questions", "# Output shape")
    b = _section(V3.read_text(), "# Anchor questions", "# Output shape")
    assert a == b


def test_the_predictions_line_of_the_output_shape_is_unchanged():
    def pred_line(p):
        return [l for l in p.read_text().splitlines() if '"predictions"' in l]
    assert pred_line(V2) == pred_line(V3) != []


def test_v3_removes_the_two_sentences_that_closed_the_channel():
    t = _flat(V3)
    assert "They are never executed" not in t
    assert "Omit the whole list if you have no small-tilt view" not in t


def test_v3_states_the_actions_are_consumed_by_a_paper_account():
    t = _flat(V3)
    assert "are consumed" in t
    # and is honest about the stakes in BOTH directions — real orders, no real money
    assert "real paper orders" in t and "No real money" in t


def test_v3_requires_a_reason_on_an_empty_list():
    t = _flat(V3)
    assert "no_action_reason" in t
    assert "indistinguishable from a broken pipe" in t


def test_v3_keeps_the_firewall_bound_unchanged():
    """v3 opens a channel; it must not loosen a bound. The ±20% cap and the
    reject-whole-never-clamp contract are the safety half and are NOT in scope."""
    t = _flat(V3)
    assert "[-0.20, 0.20]" in t and "NEVER above 0.20" in t
    assert "REJECTED WHOLE — never quietly trimmed to fit" in t


def test_the_caller_points_at_v3_everywhere_the_record_segments():
    src = (ROOT / "paper_trader/intel_pulse.py").read_text()
    assert 'prompt_path="config/prompts/analyst/daily_v3.md"' in src
    assert 'prompt_version="daily/v3"' in src
    assert 'prompt_version="daily/v2"' not in src


def test_the_prompt_evolution_stamp_exists_and_carries_every_required_field():
    """The doctrine's first exercise. A stamp missing its pre-stated outcome is a
    rationalisation waiting to happen."""
    t = (ROOT / "docs/Core/prompt_evolution_log.md").read_text()
    assert "daily/v3" in t
    for required in ("Trigger", "Pre-stated outcome measure", "Revert ID",
                     "Scope of change", "Cohort note"):
        assert required in t, f"stamp missing {required}"
    assert "0 of 15 notes" in t          # the trigger is EVIDENCE, not a vibe
    assert "daily_v2.md" in t            # the revert target is named exactly


# ------------------------------------------------------------- the schema
def _note(as_of="2026-09-01", actions=(), reason=None, prompt_version="daily/v3",
          extra=None):
    p = {"schema_version": "analyst_note/v1", "as_of": as_of,
         "market_assessment": "test", "risk_flags": [], "position_notes": [],
         "special_situation_scores": [], "predictions": [],
         "hypothetical_actions": [
             {"account": "shadow", "symbol": s, "set_weight": w, "target_weight": w}
             for s, w in actions],
         "suspected_prompt_injection": False,
         "provenance": {"model_id_requested": "m", "model_id_served": "m",
                        "prompt_version": prompt_version, "prompt_sha256": HEX64,
                        "input_bundle_sha256": HEX64},
         "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}}
    if reason is not None:
        p["no_action_reason"] = reason
    if extra:
        p.update(extra)
    return p


def test_a_v3_note_carrying_no_action_reason_validates():
    n, why = validate_note(_note(reason="no tradable dislocation; tape thin"))
    assert n is not None, why
    assert n.no_action_reason.startswith("no tradable")


def test_a_v2_era_note_WITHOUT_the_field_still_validates():
    """The back-record must not break: the eval harness resolves predictions from
    notes weeks old, so a schema change that voids the archive is a data loss."""
    n, why = validate_note(_note(prompt_version="daily/v2"))
    assert n is not None, why
    assert n.no_action_reason is None


def test_extra_forbid_still_bites_on_a_genuinely_unknown_key():
    """Adding one known optional field must not turn the schema permissive."""
    n, why = validate_note(_note(extra={"surprise": 1}))
    assert n is None and why


def test_an_overlong_reason_is_rejected():
    n, _ = validate_note(_note(reason="x" * 400))
    assert n is None


def test_the_twenty_percent_bound_is_unchanged_by_v3():
    n, _ = validate_note(_note(actions=[("SPY", 0.25)]))
    assert n is None


# -------------------------------------------------- the constructor outcome
def _closes(*syms):
    idx = pd.to_datetime(["2026-08-28", "2026-08-31", "2026-09-01"])
    return {s: pd.Series([100.0, 100.0, 100.0], index=idx) for s in syms}


def _on_disk(tmp_path, payload):
    d = tmp_path / "data/intel/analyst_notes"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"note_{payload['as_of']}.json").write_text(json.dumps(payload))


def _build(tmp_path, payload, trade_date="2026-09-02"):
    _on_disk(tmp_path, payload)
    c = LLMAnalystConstructor(trade_date=trade_date, root=str(tmp_path),
                              allowlist=("SPY", "AGG", "GLD"))
    return c.construct(10_000.0, {}, _closes("SPY", "AGG", "GLD"))


def test_an_empty_list_WITH_a_reason_is_a_stated_no_view_day(tmp_path):
    """The healthy zero. NOT degraded, NOT a rejection — a real decision to hold."""
    plan = _build(tmp_path, _note(reason="no dislocation worth a tilt"))
    assert plan.orders == []
    assert plan.no_view is True and plan.no_view_reason == "no dislocation worth a tilt"
    assert plan.degraded is False and plan.reject_reason is None


def test_an_empty_list_WITHOUT_a_reason_is_recorded_as_UNSTATED(tmp_path):
    """The exact shape that held ignition: 15 notes of silent zeros. It is still a
    legal note — voiding it would destroy its predictions too — but the record now
    NAMES it, so a channel going dark again cannot read as a healthy hold."""
    plan = _build(tmp_path, _note())
    assert plan.orders == [] and plan.no_view is True
    assert "UNSTATED" in plan.no_view_reason


def test_actions_present_means_no_view_is_False(tmp_path):
    plan = _build(tmp_path, _note(actions=[("SPY", 0.10)]))
    assert plan.no_view is False and plan.no_view_reason is None
    assert [(o.ticker, o.side, o.qty) for o in plan.orders] == [("SPY", "buy", 10)]


def test_the_plan_carries_the_prompt_version_that_produced_the_note(tmp_path):
    """The trading record must show the cohort boundary too, not just the eval one."""
    plan = _build(tmp_path, _note(actions=[("SPY", 0.10)], prompt_version="daily/v3"))
    assert plan.note_prompt_version == "daily/v3"


def test_a_v2_cohort_note_is_identifiable_from_the_trading_record(tmp_path):
    plan = _build(tmp_path, _note(prompt_version="daily/v2"))
    assert plan.note_prompt_version == "daily/v2" and plan.no_view is True


def test_no_view_is_never_confused_with_a_firewall_rejection(tmp_path):
    """Two zeros, two different meanings — the distinction the whole fix is about."""
    ok = _build(tmp_path, _note(reason="flat"))
    assert ok.no_view and ok.reject_reason is None
    # a breaching note never reaches the schema, but the constructor's own
    # re-enforcement must still read as a REJECTION, not a no-view day
    c = LLMAnalystConstructor(trade_date="2026-09-02", root=str(tmp_path),
                              allowlist=("SPY",), max_weight=0.05,
                              note=_note(actions=[("SPY", 0.10)]))
    bad = c.construct(10_000.0, {}, _closes("SPY"))
    assert bad.reject_reason.startswith("REJECTED:") and bad.no_view is False
