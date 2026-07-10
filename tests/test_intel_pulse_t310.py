"""T-310 — the intel pulse orchestrator: analyst note PERSISTED (wakes the shadow
book), key-optional clean-skips, fail-open. No network, no real key."""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pandas as pd
import pytest

import paper_trader.intel_pulse as ip

VALID_NOTE = json.dumps({
    "market_assessment": "trend intact",
    "predictions": [{"statement": "SPY above 750 by 2026-07-31", "probability": 0.4,
                     "horizon": "3w",
                     "resolver": {"type": "price_above", "symbol": "SPY", "level": 750.0,
                                  "direction": "above", "by_date": "2026-07-31",
                                  "mode": "terminal"}}],
    "hypothetical_actions": [{"account": "shadow", "symbol": "SPY",
                              "set_weight": 0.05, "target_weight": 0.05}],
})


def _empty_panel(*a, **k):
    return pd.DataFrame(columns=["created_at", "symbols", "headline", "content"])


def _fake_call_note(*a, **k):
    return {"text": VALID_NOTE, "model_id_served": "claude-haiku-4-5-20251001",
            "usage": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001}}


def _run(root, model_call, monkeypatch):
    monkeypatch.setattr(ip, "_model_call_or_none", lambda tier, settings: model_call)
    # keep the event step hermetic (no SEC fetch)
    import intelligence.event_call.run_forward as rf
    monkeypatch.setattr(rf, "pulse_step",
                        lambda *a, **k: {"status": "ok", "reason": "no_new_docs", "n_ok": 0})
    return ip.run_intel_pulse(
        "2026-07-10", portfolios={"sleeve": {"SPY": 0.66}},
        allowlist=["SPY", "AGG", "GLD"], root=root,
        now_iso="2026-07-10T13:00:00", load_panel=_empty_panel)


# --- no-key path ------------------------------------------------------------ #
def test_no_key_all_clean_skip(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = ip.run_intel_pulse("2026-07-10", portfolios={"sleeve": {"SPY": 0.66}},
                           allowlist=["SPY"], root=str(tmp_path),
                           now_iso="2026-07-10T13:00:00", load_panel=_empty_panel)
    assert r.model_available is False
    assert r.analyst["status"] == "skipped:no_model_adapter"
    assert r.watchdog["status"] == "skipped:no_model_adapter"
    assert r.event.get("reason") == "no_model_adapter"
    assert r.note_written is None
    assert not glob.glob(str(tmp_path / "data/intel/analyst_notes/*.json"))


# --- the core: analyst note persisted + shadow-book-valid ------------------- #
def test_analyst_note_persisted_and_shadow_book_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE")
    r = _run(str(tmp_path), _fake_call_note, monkeypatch)
    assert r.analyst["status"] == "ok" and r.note_written
    notes = glob.glob(str(tmp_path / "data/intel/analyst_notes/*.json"))
    assert len(notes) == 1 and notes[0].endswith("note_2026-07-10.json")
    from intelligence.analyst.note_schema import validate_note
    note, reason = validate_note(json.loads(Path(notes[0]).read_text()))
    assert note is not None, reason


def test_shadow_book_wakes_on_the_persisted_note(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE")
    _run(str(tmp_path), _fake_call_note, monkeypatch)
    from paper_trader.llm_shadow_book import LlmShadowBook
    sb = LlmShadowBook(root=str(tmp_path))
    hb = sb.record("2026-07-11", closes={"SPY": 660.0, "AGG": 98.0, "GLD": 190.0})
    assert hb["n_days"] == 1 and hb["armed"] is True   # it consumed yesterday's note


# --- fail-open -------------------------------------------------------------- #
def test_analyst_fail_open_on_model_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE")
    def boom(*a, **k):
        raise RuntimeError("api 500")
    r = _run(str(tmp_path), boom, monkeypatch)
    # run_daily_note catches the model error → skipped, never a crash / note
    assert r.note_written is None
    assert r.analyst["status"].startswith("skipped:model_call_error")


def test_invalid_note_yields_no_persisted_note(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE")
    def bad(*a, **k):
        return {"text": "not json", "model_id_served": "m",
                "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}}
    r = _run(str(tmp_path), bad, monkeypatch)
    assert r.note_written is None and r.analyst["status"].startswith("invalid:")
    assert not glob.glob(str(tmp_path / "data/intel/analyst_notes/*.json"))


# --- shared governor -------------------------------------------------------- #
def test_spend_is_recorded_to_the_shared_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE")
    _run(str(tmp_path), _fake_call_note, monkeypatch)
    ledger = tmp_path / "data/intel/llm_spend.jsonl"
    assert ledger.exists() and ledger.read_text().strip()   # spend recorded durably


def test_durable_paths_carry_the_intel_state():
    from paper_trader.cloud_state import DURABLE_PATHS, DURABLE_DIRS
    assert "data/intel/event_calls.jsonl" in DURABLE_PATHS
    assert "data/intel/llm_spend.jsonl" in DURABLE_PATHS
    assert "data/intel/analyst_notes" in DURABLE_DIRS
