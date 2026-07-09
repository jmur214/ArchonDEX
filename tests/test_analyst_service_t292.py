"""T-292 — analyst_service orchestration, injected model call (no key/network)."""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from intelligence.analyst.analyst_service import run_daily_note
from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig

AS_OF = dt.date(2026, 7, 8)
PORT = {"sleeve": {"SPY": 0.30, "AGG": 0.10}}
PROMPT = "config/prompts/analyst/daily_v1.md"


def _empty_panel(*a, **k):
    return pd.DataFrame(columns=["created_at", "symbols", "headline", "content"])


def _gov(tmp_path, **cfg):
    return CostGovernor(GovernorConfig(**cfg), str(tmp_path / "spend.jsonl"))


def _note_json(actions):
    return json.dumps({
        "market_assessment": "trend intact",
        "predictions": [{
            "statement": "SPY above 750 by 2026-07-31", "probability": 0.4, "horizon": "3w",
            "resolver": {"type": "price_above", "symbol": "SPY", "level": 750.0,
                         "direction": "above", "by_date": "2026-07-31", "mode": "terminal"}}],
        "hypothetical_actions": actions,
    })


def _call_returning(text):
    def call(prompt, bundle_json, max_tokens):
        assert "ANTHROPIC" not in bundle_json and "PK" not in bundle_json  # no secrets in prompt
        return {"text": text, "model_id_served": "claude-haiku-4-5-20251001",
                "usage": {"input_tokens": 200, "output_tokens": 80, "cost_usd": 0.002}}
    return call


def _run(tmp_path, model_call, gov=None, allowlist=("SPY", "AGG"), cost=0.01):
    return run_daily_note(
        AS_OF, portfolios=PORT, allowlist=allowlist, prompt_path=PROMPT,
        model_call=model_call, governor=gov or _gov(tmp_path),
        model_id_requested="claude-haiku-4-5-20251001", prompt_version="daily/v1",
        projected_cost_usd=cost, raw_dir=str(tmp_path / "raw"),
        load_panel=_empty_panel, now_iso="2026-07-08T13:00:00")


def test_happy_path_produces_a_validated_note(tmp_path):
    r = _run(tmp_path, _call_returning(_note_json(
        [{"account": "shadow", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05}])))
    assert r.status == "ok" and r.note is not None
    assert r.note["provenance"]["prompt_version"] == "daily/v1"
    assert r.note["hypothetical_actions"][0]["symbol"] == "SPY"


def test_kill_switch_skips_before_any_call(tmp_path):
    called = {"n": 0}
    def call(*a):
        called["n"] += 1; return {"text": "{}"}
    r = _run(tmp_path, call, gov=_gov(tmp_path, kill_switch=True))
    assert r.status == "skipped:kill_switch" and called["n"] == 0


def test_budget_breach_skips_before_any_call(tmp_path):
    g = _gov(tmp_path, monthly_budget_usd=0.001)
    called = {"n": 0}
    def call(*a):
        called["n"] += 1; return {"text": "{}"}
    r = _run(tmp_path, call, gov=g, cost=1.0)
    assert r.status.startswith("skipped:budget_breach") and called["n"] == 0


def test_invalid_json_yields_no_note_but_archives_raw(tmp_path):
    r = _run(tmp_path, _call_returning("not json at all"))
    assert r.note is None and r.status == "invalid:not_json"
    assert r.raw_path and "not json at all" in open(r.raw_path).read()


def test_schema_violation_yields_no_note(tmp_path):
    # a real-account action must fail validation → NO note
    r = _run(tmp_path, _call_returning(_note_json(
        [{"account": "roth", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05}])))
    assert r.note is None and r.status.startswith("invalid:")


def test_semantic_firewall_rejects_nonallowlisted_symbol_keeps_note(tmp_path):
    # valid schema, but the action symbol TSLA is not on the allowlist → drop the
    # ACTION (logged), keep the note (attacks are signal, not crashes).
    r = _run(tmp_path, _call_returning(_note_json(
        [{"account": "shadow", "symbol": "TSLA", "set_weight": 0.05, "target_weight": 0.05}])),
        allowlist=("SPY", "AGG"))
    assert r.status == "ok" and r.note["hypothetical_actions"] == []
    assert r.firewall_rejections and r.firewall_rejections[0]["reason"] == "symbol_not_allowlisted"


def test_model_call_error_skips_cleanly(tmp_path):
    def boom(*a):
        raise RuntimeError("api 500")
    r = _run(tmp_path, boom)
    assert r.note is None and r.status.startswith("skipped:model_call_error")


def test_spend_is_recorded_after_a_real_call(tmp_path):
    g = _gov(tmp_path, monthly_budget_usd=30.0)
    _run(tmp_path, _call_returning(_note_json([])), gov=g)
    assert g.month_to_date_usd("2026-07") == 0.002
