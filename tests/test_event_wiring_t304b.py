"""T-304b — the forward-runner wiring. Stub adapter + stub EDGAR fetch: NO real network, NO real LLM call.

The load-bearing test is `test_forward_only_guard_refuses_historical` — the [NN-AI-GATE] hard stop against
ever firing a model call on a historical document (memorization look-ahead).
"""
import datetime as _dt
import json
import pathlib

from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
from intelligence.event_call.eightk_feed import EventDocument
from intelligence.event_call.run_forward import (ForwardRunResult, _attach_body,
                                                pulse_step, run_forward)

PROMPT = str(pathlib.Path(__file__).resolve().parents[1] / "config" / "prompts" / "event_interpreter" / "v1.txt")


def _model_json():
    return json.dumps({
        "event_type": "earnings_result", "materiality": 0.6, "direction": "bearish",
        "rationale": "Synthetic: results below the company's prior guidance.",
        "predictions": [{"statement": "underperforms SPY ~15d", "probability": 0.57, "horizon": "15d",
                         "resolver": {"type": "relative_return", "symbol_a": "ZZZZ", "symbol_b": "SPY",
                                      "end_date": "2026-07-25", "op": "lt", "margin_bps": 100}}],
        "suspected_prompt_injection": False})


def _stub_adapter(calls):
    def _mc(prompt_text, bundle_json, max_out):
        calls.append(bundle_json)
        return {"text": _model_json(), "model_id_served": "claude-haiku-4-5-20251001",
                "usage": {"input_tokens": 300, "output_tokens": 90, "cost_usd": 0.007}}
    return _mc


def _gov(tmp_path, **kw):
    return CostGovernor(GovernorConfig(**kw), str(tmp_path / "spend.jsonl"))


def _one_special_doc(fd):
    # special-situation docs are already text-bearing (no EDGAR fetch needed) — ideal for a hermetic test
    return EventDocument(document_ref="evt-1", source="special_situation", symbol="ZZZZ", file_date=fd,
                         event_class_hint="odd_lot_tender", text="Issuer XYZ: odd-lot tender at a premium.")


def test_forward_only_guard_refuses_historical(tmp_path):
    """A model call on a 2015 document is memorization look-ahead — must be refused before any call."""
    calls = []
    res = run_forward("2015-03-01", model_call=_stub_adapter(calls), governor=_gov(tmp_path),
                      prompt_path=PROMPT, model_id_requested="m", prompt_version="event_interpreter/v1",
                      projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                      ledger_path=tmp_path / "l.jsonl", today=_dt.date(2026, 7, 10))
    assert res.degraded and "not_forward" in res.reason
    assert calls == []                                   # NO model call fired
    assert not (tmp_path / "l.jsonl").exists()


def test_future_as_of_also_refused(tmp_path):
    calls = []
    res = run_forward("2026-07-20", model_call=_stub_adapter(calls), governor=_gov(tmp_path),
                      prompt_path=PROMPT, model_id_requested="m", prompt_version="event_interpreter/v1",
                      projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                      ledger_path=tmp_path / "l.jsonl", today=_dt.date(2026, 7, 10))
    assert res.degraded and calls == []


def test_forward_run_fires_and_accrues_the_ledger(tmp_path, monkeypatch):
    """Today's document → one call → one ledger line. Special-sit doc avoids EDGAR (hermetic)."""
    calls = []
    monkeypatch.setattr("intelligence.event_call.run_forward.new_documents",
                        lambda *a, **k: [_one_special_doc("2026-07-10")])
    res = run_forward("2026-07-10", model_call=_stub_adapter(calls), governor=_gov(tmp_path),
                      prompt_path=PROMPT, model_id_requested="claude-haiku-4-5-20251001",
                      prompt_version="event_interpreter/v1", projected_cost_usd=0.01,
                      raw_dir=str(tmp_path / "raw"), ledger_path=tmp_path / "l.jsonl",
                      today=_dt.date(2026, 7, 10))
    assert not res.degraded and res.n_ok == 1 and len(calls) == 1
    rec = json.loads((tmp_path / "l.jsonl").read_text().splitlines()[0])
    assert rec["event_call"]["source"] == "special_situation"


def test_8k_body_fetch_is_stubbed_and_no_body_skips(tmp_path, monkeypatch):
    """An 8-K doc whose EDGAR body is unavailable ⇒ no call (no interpretable body)."""
    calls = []
    doc = EventDocument(document_ref="acc#2.02", source="8k", symbol="ZZZZ", file_date="2026-07-10",
                        item_code="2.02", meta={"cik": 123, "accession": "acc"})
    monkeypatch.setattr("intelligence.event_call.run_forward.new_documents", lambda *a, **k: [doc])
    res = run_forward("2026-07-10", model_call=_stub_adapter(calls), governor=_gov(tmp_path),
                      prompt_path=PROMPT, model_id_requested="m", prompt_version="event_interpreter/v1",
                      projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                      ledger_path=tmp_path / "l.jsonl", today=_dt.date(2026, 7, 10),
                      body_fetch=lambda *a, **k: None)          # EDGAR body unavailable
    assert res.n_no_body == 1 and res.n_ok == 0 and calls == []


def test_8k_body_present_fires_the_call(tmp_path, monkeypatch):
    calls = []
    doc = EventDocument(document_ref="acc#2.02", source="8k", symbol="ZZZZ", file_date="2026-07-10",
                        item_code="2.02", meta={"cik": 123, "accession": "acc"})
    monkeypatch.setattr("intelligence.event_call.run_forward.new_documents", lambda *a, **k: [doc])
    res = run_forward("2026-07-10", model_call=_stub_adapter(calls), governor=_gov(tmp_path),
                      prompt_path=PROMPT, model_id_requested="m", prompt_version="event_interpreter/v1",
                      projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                      ledger_path=tmp_path / "l.jsonl", today=_dt.date(2026, 7, 10),
                      body_fetch=lambda *a, **k: "Paraphrased synthetic 8-K body about a guidance cut.")
    assert res.n_ok == 1 and len(calls) == 1


def test_pulse_step_is_fail_open_without_adapter(tmp_path):
    """No adapter wired ⇒ degraded, NO call, never raises (interpreter failure never fails the pulse)."""
    out = pulse_step("2026-07-10", model_call=None, governor=_gov(tmp_path), prompt_path=PROMPT,
                     model_id_requested="m", prompt_version="event_interpreter/v1",
                     projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"))
    assert out["status"] == "degraded" and out["reason"] == "no_model_adapter" and out["n_ok"] == 0
