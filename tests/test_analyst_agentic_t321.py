"""T-321 — the agentic analyst: tool-use loop mechanics, read-only tool safety,
the tool-abuse red-team, and the governed orchestration. Zero network + zero key
(a fake requests session / injected agentic_call)."""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import pytest

from intelligence.analyst.agentic_tools import AgenticTools, MAX_RESULT_CHARS
from intelligence.analyst.anthropic_adapter import make_agentic_call
from intelligence.analyst.analyst_agentic import run_agentic_note
from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig

AS_OF = dt.date(2026, 7, 28)
PORT = {"sleeve": {"SPY": 0.66}}
PROMPT = "config/prompts/analyst/daily_agentic_v1.md"

SETTINGS = {
    "api": {"base_url": "https://api.anthropic.com", "messages_path": "/v1/messages",
            "anthropic_version": "2023-06-01", "timeout_seconds": 60},
    "tiers": {"daily": {"model_id": "claude-haiku-4-5-20251001", "max_output_tokens": 1500,
                        "price_per_mtok_input_usd": 1.0, "price_per_mtok_output_usd": 5.0,
                        "price_per_mtok_cache_write_usd": 1.25, "price_per_mtok_cache_read_usd": 0.1}}}

_NOTE = json.dumps({
    "market_assessment": "trend intact after checking history",
    "predictions": [{"statement": "SPY above 750 by 2026-08-15", "probability": 0.4,
                     "horizon": "3w", "resolver": {"type": "price_above", "symbol": "SPY",
                     "level": 750.0, "direction": "above", "by_date": "2026-08-15",
                     "mode": "terminal"}}],
    "hypothetical_actions": []})


def _empty_panel(*a, **k):
    return pd.DataFrame(columns=["created_at", "symbols", "headline", "content"])


def _gov(tmp_path, **cfg):
    return CostGovernor(GovernorConfig(**cfg), str(tmp_path / "spend.jsonl"))


def _readers():
    return {
        "query_news": lambda i: [{"headline": "SPY steady", "created_at": "2026-07-20"}],
        "query_prices": lambda i: [{"date": "2026-07-27", "close": 655.0}],
        "query_own_notes": lambda i: [{"as_of": "2026-07-25", "market_assessment": "cautious"}],
        "query_resolved_predictions": lambda i: [{"statement": "x", "outcome": 1, "brier": 0.16}],
    }


# ── a scripted fake requests session for the raw-REST loop ─────────────────────
class _Resp:
    def __init__(self, payload): self.status_code = 200; self._p = payload; self.text = "{}"
    def json(self): return self._p


class _ScriptSession:
    """Returns queued responses in order; records each POST body."""
    def __init__(self, *payloads): self._q = list(payloads); self.posts = []
    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append(json)
        return _Resp(self._q.pop(0))


def _tool_use_resp(name, tool_input, tid="tu1"):
    return {"model": "claude-haiku-4-5-20251001", "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "id": tid, "name": name, "input": tool_input}],
            "usage": {"input_tokens": 100, "output_tokens": 20}}


def _final_resp(text):
    return {"model": "claude-haiku-4-5-20251001", "stop_reason": "end_turn",
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}


# ── AgenticTools: read-only, fail-closed, scrubbed, bounded ────────────────────
def test_specs_only_offers_tools_with_a_reader():
    t = AgenticTools(readers={"query_news": lambda i: []})
    names = {s["name"] for s in t.specs()}
    assert names == {"query_news"}


def test_unknown_tool_is_error_not_crash():
    t = AgenticTools(readers=_readers())
    out, err = t.execute("query_web", {"url": "http://evil"})
    assert err and "unknown tool" in out
    assert t.trace[-1].reason == "unknown_tool"


def test_reader_that_raises_is_fail_closed():
    def boom(i): raise RuntimeError("store down")
    t = AgenticTools(readers={"query_news": boom})
    out, err = t.execute("query_news", {"ticker": "SPY"})
    assert err and "RuntimeError" in out and t.trace[-1].reason == "reader_error:RuntimeError"


def test_result_is_scrubbed_of_secret_shaped_values():
    t = AgenticTools(readers={"query_news": lambda i: [{"h": "PKABCDEFGH12345678", "ok": "fine"}]})
    out, err = t.execute("query_news", {"ticker": "SPY"})
    assert not err and "PKABCDEFGH12345678" not in out and "[REDACTED]" in out


def test_result_is_size_bounded():
    big = [{"h": "x" * 100} for _ in range(500)]
    t = AgenticTools(readers={"query_news": lambda i: big})
    out, _ = t.execute("query_news", {"ticker": "SPY"})
    assert len(out) <= MAX_RESULT_CHARS + 60 and "truncated" in out


def test_trace_records_every_call():
    t = AgenticTools(readers=_readers())
    t.execute("query_news", {"ticker": "SPY"})
    t.execute("query_prices", {"ticker": "SPY"})
    assert [r.tool for r in t.trace] == ["query_news", "query_prices"]


# ── the raw-REST tool-use loop ─────────────────────────────────────────────────
def test_loop_runs_tools_then_returns_final_note(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    sess = _ScriptSession(_tool_use_resp("query_news", {"ticker": "SPY"}), _final_resp(_NOTE))
    call = make_agentic_call("daily", settings=SETTINGS, session=sess)
    tools = AgenticTools(readers=_readers())
    r = call("SYS", '{"as_of":"2026-07-28"}', 1500, tools.specs(), tools.execute, 8)
    assert r["stopped"] == "end_turn" and r["n_tool_calls"] == 1
    assert "trend intact" in r["text"]
    # usage accumulated across BOTH hops (governor must see the true cost)
    assert r["usage"]["input_tokens"] == 200 and r["usage"]["cost_usd"] > 0
    # the second POST carried a tool_result user turn
    assert any(isinstance(m.get("content"), list) and m["content"][0].get("type") == "tool_result"
               for m in sess.posts[1]["messages"])


def test_loop_enforces_the_tool_call_cap(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # the model keeps asking for tools; the cap must force a final answer.
    scripted = [_tool_use_resp("query_news", {"ticker": "SPY"}, tid=f"t{i}") for i in range(5)]
    scripted.append(_final_resp(_NOTE))   # the forced final hop (no tools)
    sess = _ScriptSession(*scripted)
    call = make_agentic_call("daily", settings=SETTINGS, session=sess)
    tools = AgenticTools(readers=_readers())
    r = call("SYS", "{}", 1500, tools.specs(), tools.execute, 2)
    assert r["stopped"] == "max_calls" and r["n_tool_calls"] == 2
    # the forced final hop must NOT offer tools
    assert "tools" not in sess.posts[-1]


def test_loop_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    call = make_agentic_call("daily", settings=SETTINGS, session=_ScriptSession())
    with pytest.raises(RuntimeError, match="not set"):
        call("SYS", "{}", 100, [], lambda n, i: ("", False), 4)


# ── governed orchestration + the red-team ──────────────────────────────────────
def _fake_agentic(text, n_calls=1, stopped="end_turn"):
    def call(prompt, bundle_json, max_tokens, tools, execute, max_calls):
        # exercise one real tool call so the trace is populated
        execute("query_news", {"ticker": "SPY"})
        return {"text": text, "model_id_served": "claude-haiku-4-5-20251001",
                "usage": {"input_tokens": 200, "output_tokens": 80, "cost_usd": 0.02},
                "n_tool_calls": n_calls, "stopped": stopped}
    return call


def _run(tmp_path, text, allowlist=("SPY", "AGG", "GLD"), gov=None):
    return run_agentic_note(
        AS_OF, portfolios=PORT, allowlist=allowlist, prompt_path=PROMPT,
        agentic_call=_fake_agentic(text), tools=AgenticTools(readers=_readers()),
        governor=gov or _gov(tmp_path), model_id_requested="claude-haiku-4-5-20251001",
        prompt_version="daily_agentic/v1", projected_cost_usd=0.05,
        raw_dir=str(tmp_path / "raw"), load_panel=_empty_panel,
        now_iso="2026-07-28T13:00:00")


def test_happy_path_note_carries_the_tool_trace(tmp_path):
    r = _run(tmp_path, _NOTE)
    assert r.status == "ok" and r.note is not None
    assert r.note["provenance"]["n_tool_calls"] == 1
    assert r.note["provenance"]["tool_trace"][0]["tool"] == "query_news"
    assert r.note["provenance"]["agentic_stopped"] == "end_turn"
    # the persisted note re-validates like a constrained one (shared contract)
    from intelligence.analyst.note_schema import validate_note
    assert validate_note(r.note)[0] is not None


def test_kill_switch_skips_before_any_call(tmp_path):
    r = _run(tmp_path, _NOTE, gov=_gov(tmp_path, kill_switch=True))
    assert r.status == "skipped:kill_switch" and r.note is None


def test_budget_breach_skips(tmp_path):
    r = _run(tmp_path, _NOTE, gov=_gov(tmp_path, monthly_budget_usd=0.001))
    assert r.status.startswith("skipped:budget_breach")


def test_redteam_real_account_action_voids_note(tmp_path):
    bad = json.dumps({"market_assessment": "x", "hypothetical_actions": [
        {"account": "roth", "symbol": "SPY", "set_weight": 0.05, "target_weight": 0.05}]})
    r = _run(tmp_path, bad)
    assert r.note is None and r.status == "invalid:non_shadow_account"


def test_redteam_nonallowlisted_symbol_dropped_note_survives(tmp_path):
    bad = json.dumps({"market_assessment": "x",
        "predictions": [{"statement": "SPY above 750 by 2026-08-15", "probability": 0.4,
            "horizon": "3w", "resolver": {"type": "price_above", "symbol": "SPY", "level": 750.0,
            "direction": "above", "by_date": "2026-08-15", "mode": "terminal"}}],
        "hypothetical_actions": [{"account": "shadow", "symbol": "TSLA",
                                  "set_weight": 0.05, "target_weight": 0.05}]})
    r = _run(tmp_path, bad)
    assert r.status == "ok" and r.note["hypothetical_actions"] == []
    assert r.firewall_rejections and r.firewall_rejections[0]["reason"] == "symbol_not_allowlisted"


def test_redteam_non_json_yields_no_note_but_keeps_trace(tmp_path):
    r = _run(tmp_path, "I browsed everything and here is prose, no JSON.")
    assert r.note is None and r.status == "invalid:not_json"
    assert r.tool_trace and r.tool_trace[0]["tool"] == "query_news"


def test_redteam_leading_prose_narration_still_parses(tmp_path):
    # the real failure mode: an agentic model narrates BEFORE the fenced JSON.
    narrated = "Now I'll assess the situation:\n\n**Situation:** SPY steady.\n\n```json\n" + _NOTE + "\n```"
    r = _run(tmp_path, narrated)
    assert r.status == "ok" and r.note is not None and len(r.note["predictions"]) == 1


def test_model_call_error_skips_cleanly(tmp_path):
    def boom(*a, **k): raise RuntimeError("api 500")
    r = run_agentic_note(AS_OF, portfolios=PORT, allowlist=("SPY",), prompt_path=PROMPT,
        agentic_call=boom, tools=AgenticTools(readers=_readers()), governor=_gov(tmp_path),
        model_id_requested="m", prompt_version="daily_agentic/v1", projected_cost_usd=0.05,
        raw_dir=str(tmp_path / "raw"), load_panel=_empty_panel, now_iso="2026-07-28T13:00:00")
    assert r.note is None and r.status.startswith("skipped:model_call_error")
