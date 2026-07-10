"""T-292 ignition-hardening: the fixes the first real smoke note surfaced —
markdown-fence tolerance, an optional action rationale, and the drop-not-void
firewall for malformed SHADOW actions (a non-shadow account still voids)."""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from intelligence.analyst.analyst_service import run_daily_note, _strip_json_fence
from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
from intelligence.analyst.note_schema import validate_action, HypotheticalAction

AS_OF = dt.date(2026, 7, 9)
PORT = {"sleeve": {"SPY": 0.66}}
PROMPT = "config/prompts/analyst/daily_v1.md"


def _empty_panel(*a, **k):
    return pd.DataFrame(columns=["created_at", "symbols", "headline", "content"])


def _gov(tmp_path, **cfg):
    return CostGovernor(GovernorConfig(**cfg), str(tmp_path / "spend.jsonl"))


def _note_json(actions, pred=True):
    body = {"market_assessment": "trend intact", "hypothetical_actions": actions}
    if pred:
        body["predictions"] = [{
            "statement": "SPY above 750 by 2026-07-31", "probability": 0.4, "horizon": "3w",
            "resolver": {"type": "price_above", "symbol": "SPY", "level": 750.0,
                         "direction": "above", "by_date": "2026-07-31", "mode": "terminal"}}]
    return json.dumps(body)


def _call(text):
    def c(prompt, bundle_json, max_tokens):
        return {"text": text, "model_id_served": "claude-haiku-4-5-20251001",
                "usage": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001}}
    return c


def _run(tmp_path, text, allowlist=("SPY", "AGG")):
    return run_daily_note(
        AS_OF, portfolios=PORT, allowlist=allowlist, prompt_path=PROMPT,
        model_call=_call(text), governor=_gov(tmp_path),
        model_id_requested="claude-haiku-4-5-20251001", prompt_version="daily/v1",
        projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
        load_panel=_empty_panel, now_iso="2026-07-09T13:00:00")


# --- fence tolerance -------------------------------------------------------- #
def test_strip_json_fence_variants():
    assert _strip_json_fence('```json\n{"a":1}\n```') == '{"a":1}'
    assert _strip_json_fence('```\n{"a":1}\n```') == '{"a":1}'
    assert _strip_json_fence('{"a":1}') == '{"a":1}'
    assert _strip_json_fence('  {"a":1}  ') == '{"a":1}'


def test_fenced_response_still_produces_a_note(tmp_path):
    r = _run(tmp_path, "```json\n" + _note_json([]) + "\n```")
    assert r.status == "ok" and r.note is not None


# --- optional rationale ----------------------------------------------------- #
def test_action_rationale_is_accepted_and_preserved(tmp_path):
    r = _run(tmp_path, _note_json([{
        "account": "shadow", "symbol": "SPY", "set_weight": 0.05,
        "target_weight": 0.05, "rationale": "small equity tilt"}]))
    assert r.status == "ok"
    assert r.note["hypothetical_actions"][0]["rationale"] == "small equity tilt"


def test_action_unknown_field_still_rejected_per_item():
    # extra="forbid" still rejects a truly-unknown key per-item (rationale is the
    # only added optional field; 'bogus' is not).
    a, why = validate_action({"account": "shadow", "symbol": "SPY", "set_weight": 0.05,
                              "target_weight": 0.05, "bogus": 1})
    assert a is None and why  # rejected, with a reason string
    ok, _ = validate_action({"account": "shadow", "symbol": "SPY", "set_weight": 0.05,
                             "target_weight": 0.05, "rationale": "fine"})
    assert ok is not None      # rationale is accepted


# --- drop-not-void for malformed SHADOW actions ----------------------------- #
def test_out_of_bounds_shadow_action_is_dropped_note_survives(tmp_path):
    # target_weight 0.4 > the ±0.20 bound → drop the action, KEEP the note.
    r = _run(tmp_path, _note_json([{
        "account": "shadow", "symbol": "SPY", "set_weight": 0.4, "target_weight": 0.4}]))
    assert r.status == "ok" and r.note is not None
    assert r.note["hypothetical_actions"] == []
    assert r.firewall_rejections and r.firewall_rejections[0]["reason"].startswith("schema:")


def test_valid_and_invalid_actions_partition(tmp_path):
    r = _run(tmp_path, _note_json([
        {"account": "shadow", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05},
        {"account": "shadow", "symbol": "AGG", "set_weight": 0.9, "target_weight": 0.9},
    ]))
    assert r.status == "ok"
    assert len(r.note["hypothetical_actions"]) == 1
    assert r.note["hypothetical_actions"][0]["symbol"] == "SPY"
    assert len(r.firewall_rejections) == 1


def test_note_survives_when_only_actions_are_bad(tmp_path):
    # a note whose ONLY problem is an out-of-bounds action still yields a note
    # (its predictions/assessment are independently valuable).
    r = _run(tmp_path, _note_json([{
        "account": "shadow", "symbol": "SPY", "set_weight": 5.0, "target_weight": 5.0}]))
    assert r.note is not None and len(r.note["predictions"]) == 1


# --- the ONE security-critical case still voids the note -------------------- #
def test_non_shadow_account_voids_the_whole_note(tmp_path):
    r = _run(tmp_path, _note_json([{
        "account": "roth", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05}]))
    assert r.note is None and r.status == "invalid:non_shadow_account"


def test_non_shadow_account_voids_even_alongside_valid_actions(tmp_path):
    r = _run(tmp_path, _note_json([
        {"account": "shadow", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05},
        {"account": "live", "symbol": "AGG", "set_weight": 0.05, "target_weight": 0.05},
    ]))
    assert r.note is None and r.status == "invalid:non_shadow_account"


def test_hypothetical_actions_not_a_list_is_rejected(tmp_path):
    bad = json.dumps({"market_assessment": "x", "hypothetical_actions": {"oops": 1}})
    r = _run(tmp_path, bad)
    assert r.note is None and r.status == "invalid:hypothetical_actions_not_a_list"
