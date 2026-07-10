"""T-292 — the raw-REST Anthropic adapter: contract shape, prompt caching, cost,
key hygiene, fail-loud. Zero network + zero key (a fake session)."""
from __future__ import annotations

import json

import pytest

from intelligence.analyst.anthropic_adapter import make_model_call, _cost_usd, load_settings

SETTINGS = {
    "api": {"base_url": "https://api.anthropic.com", "messages_path": "/v1/messages",
            "anthropic_version": "2023-06-01", "timeout_seconds": 60},
    "tiers": {
        "daily": {"model_id": "claude-haiku-4-5-20251001", "max_output_tokens": 1500,
                  "price_per_mtok_input_usd": 1.0, "price_per_mtok_output_usd": 5.0,
                  "price_per_mtok_cache_write_usd": 1.25, "price_per_mtok_cache_read_usd": 0.1},
    },
}


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload) if isinstance(payload, dict) else str(payload)

    def json(self):
        return self._payload


class _FakeSession:
    """Captures the last POST + returns a scripted response."""
    def __init__(self, resp):
        self._resp = resp
        self.last = None

    def post(self, url, headers=None, json=None, timeout=None):
        self.last = {"url": url, "headers": headers, "json": json, "timeout": timeout}
        return self._resp


def _ok_payload(text='{"ok": 1}'):
    return {"model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 1000, "output_tokens": 200}}


def test_happy_path_returns_the_modelcall_contract(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-DUMMY")
    sess = _FakeSession(_FakeResp(200, _ok_payload('{"market_assessment": "x"}')))
    call = make_model_call("daily", settings=SETTINGS, session=sess)
    r = call("PROMPT", '{"as_of": "2026-07-09"}', 1500)
    assert r["text"] == '{"market_assessment": "x"}'
    assert r["model_id_served"] == "claude-haiku-4-5-20251001"
    assert set(r["usage"]) == {"input_tokens", "output_tokens", "cost_usd"}
    assert r["usage"]["input_tokens"] == 1000 and r["usage"]["output_tokens"] == 200


def test_prompt_is_system_bundle_is_user_and_cached(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-DUMMY")
    sess = _FakeSession(_FakeResp(200, _ok_payload()))
    make_model_call("daily", settings=SETTINGS, session=sess)("PROMPT", "BUNDLE", 900)
    body = sess.last["json"]
    # prompt → system (a cached text block); bundle → the user turn (data)
    assert body["system"][0]["text"] == "PROMPT"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert body["messages"] == [{"role": "user", "content": "BUNDLE"}]
    assert body["model"] == "claude-haiku-4-5-20251001" and body["max_tokens"] == 900


def test_key_never_leaks_into_the_prompt_or_return(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-SECRET-VALUE-123")
    sess = _FakeSession(_FakeResp(200, _ok_payload()))
    r = make_model_call("daily", settings=SETTINGS, session=sess)("P", "B", 100)
    # the key rides ONLY the header, never the body or the response dict
    assert sess.last["headers"]["x-api-key"] == "sk-SECRET-VALUE-123"
    assert "sk-SECRET-VALUE-123" not in json.dumps(sess.last["json"])
    assert "sk-SECRET-VALUE-123" not in json.dumps(r)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sess = _FakeSession(_FakeResp(200, _ok_payload()))
    with pytest.raises(RuntimeError, match="not set"):
        make_model_call("daily", settings=SETTINGS, session=sess)("P", "B", 100)


def test_non_200_raises_loudly(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-DUMMY")
    sess = _FakeSession(_FakeResp(429, {"error": {"message": "rate limited"}}))
    with pytest.raises(RuntimeError, match="429"):
        make_model_call("daily", settings=SETTINGS, session=sess)("P", "B", 100)


def test_cost_includes_cache_tokens():
    tier = SETTINGS["tiers"]["daily"]
    # 1M input, 1M output, 1M cache-write, 1M cache-read = 1+5+1.25+0.1
    c = _cost_usd({"input_tokens": 1_000_000, "output_tokens": 1_000_000,
                   "cache_creation_input_tokens": 1_000_000,
                   "cache_read_input_tokens": 1_000_000}, tier)
    assert c == pytest.approx(7.35)


def test_cost_zero_usage_is_zero():
    assert _cost_usd({}, SETTINGS["tiers"]["daily"]) == 0.0


def test_multiple_text_blocks_are_concatenated(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-DUMMY")
    payload = {"model": "m", "content": [{"type": "text", "text": "a"},
                                         {"type": "text", "text": "b"}],
               "usage": {"input_tokens": 1, "output_tokens": 1}}
    sess = _FakeSession(_FakeResp(200, payload))
    r = make_model_call("daily", settings=SETTINGS, session=sess)("P", "B", 100)
    assert r["text"] == "ab"


def test_shipped_settings_file_pins_both_tiers():
    cfg = load_settings()
    assert cfg["tiers"]["daily"]["model_id"] == "claude-haiku-4-5-20251001"
    assert cfg["tiers"]["weekly"]["model_id"]  # a stronger tier is pinned
    assert cfg["api"]["anthropic_version"]
