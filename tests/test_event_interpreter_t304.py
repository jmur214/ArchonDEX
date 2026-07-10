"""T-304 — event-interpreter tests. Mirrors the analyst fixture trio (test_analyst_service_t292):
a synthetic model JSON, a `_call_returning` closure satisfying the ModelCall seam, a tmp-path governor.

CONTAMINATION RULE ([NN-AI-GATE]): every fixture document is PARAPHRASED / SYNTHETIC — never a real
historical filing with a known outcome. These test the SCHEMA + SERVICE plumbing, not model skill.
"""
import json
import pathlib


from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
from intelligence.event_call.eightk_feed import EventDocument, ITEM_ALLOWLIST, ITEM_EXCLUDED
from intelligence.event_call.event_schema import EVENT_TYPES, validate_event_call
from intelligence.event_call.event_service import (load_seen, run_event_call)

PROMPT = str(pathlib.Path(__file__).resolve().parents[1] / "config" / "prompts" / "event_interpreter" / "v1.txt")


# ---- fixtures: synthetic documents + a ModelCall closure (zero network, zero key) ----
def _doc(source="8k", ref="0000000000-24-000001#2.02", sym="ZZZZ", fd="2024-03-01",
         item="2.02", text="Paraphrased synthetic: the company reported quarterly results below its own prior guidance."):
    return EventDocument(document_ref=ref, source=source, symbol=sym, file_date=fd,
                         item_code=item, event_class_hint="results_of_operations", text=text)


def _model_json(event_type="earnings_result", materiality=0.6, direction="bearish",
                resolver=None, extra=None):
    if resolver is None:
        resolver = {"type": "relative_return", "symbol_a": "ZZZZ", "symbol_b": "SPY",
                    "start_date": "2024-03-01", "end_date": "2024-03-22", "op": "lt", "margin_bps": 100}
    body = {"event_type": event_type, "materiality": materiality, "direction": direction,
            "rationale": "Synthetic: results came in below the company's prior guidance.",
            "predictions": [{"statement": "underperforms SPY over ~15 sessions", "probability": 0.58,
                             "horizon": "15 trading days", "resolver": resolver}],
            "suspected_prompt_injection": False}
    if extra:
        body.update(extra)
    return json.dumps(body)


def _call_returning(text, served="claude-haiku-4-5-20251001", cost=0.002):
    def _mc(prompt_text, bundle_json, max_out):
        assert "You are a securities-event interpreter" in prompt_text
        # never leak secrets into the prompt/bundle
        assert "API_KEY" not in bundle_json and "secret" not in bundle_json.lower()
        return {"text": text, "model_id_served": served,
                "usage": {"input_tokens": 400, "output_tokens": 120, "cost_usd": cost}}
    return _mc


def _gov(tmp_path, kill=False, budget=30.0):
    return CostGovernor(GovernorConfig(monthly_budget_usd=budget, kill_switch=kill),
                        str(tmp_path / "spend.jsonl"))


def _run(tmp_path, doc=None, text=None, **kw):
    return run_event_call(doc or _doc(), as_of="2024-03-01", prompt_path=PROMPT,
                          model_call=_call_returning(text or _model_json()), governor=_gov(tmp_path),
                          model_id_requested="claude-haiku-4-5-20251001", prompt_version="event_interpreter/v1",
                          projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                          ledger_path=tmp_path / "event_calls.jsonl", now_iso="2024-03-01T21:00:00", **kw)


# ---- schema ----
def test_taxonomy_is_closed_and_complete():
    assert "routine_non_material" in EVENT_TYPES and "other_material" in EVENT_TYPES
    assert "odd_lot_tender" in EVENT_TYPES
    assert len(set(EVENT_TYPES)) == len(EVENT_TYPES)          # no dupes


def test_allowlist_and_exclusions_disjoint_and_drop_boilerplate():
    assert set(ITEM_ALLOWLIST) & ITEM_EXCLUDED == set()
    assert "9.01" in ITEM_EXCLUDED and "5.07" in ITEM_EXCLUDED  # exhibits + vote tallies excluded
    assert "2.02" in ITEM_ALLOWLIST and "1.03" in ITEM_ALLOWLIST


def test_unresolvable_prediction_is_rejected():
    bad = {"type": "relative_return", "symbol_a": "ZZZZ"}     # missing fields
    call, reason = validate_event_call(json.loads(_model_json(resolver=bad)) | {
        "as_of": "2024-03-01", "source": "8k", "document_ref": "x#2.02", "symbol": "ZZZZ",
        "file_date": "2024-03-01", "input_document_sha256": "a" * 64,
        "provenance": {"model_id_requested": "m", "model_id_served": "m", "prompt_version": "v",
                       "prompt_sha256": "b" * 64, "input_bundle_sha256": "c" * 64},
        "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}})
    assert call is None and reason          # unresolvable spec ⇒ NO event call (whole record discarded)


# ---- service (happy path + guards) ----
def test_happy_path_validates_and_appends_to_ledger(tmp_path):
    res = _run(tmp_path)
    assert res.status == "ok"
    assert res.call["event_type"] == "earnings_result"
    assert res.call["input_document_sha256"] == res.ledger_record["event_call"]["input_document_sha256"]
    # ledger record is in A's note-shape (predictions array with a resolver)
    rec = json.loads((tmp_path / "event_calls.jsonl").read_text().splitlines()[0])
    assert rec["note_id"].startswith("eventcall:") and rec["predictions"][0]["resolver"]["type"] == "relative_return"
    assert load_seen(tmp_path / "event_calls.jsonl") == {"0000000000-24-000001#2.02"}


def test_kill_switch_skips_with_no_call(tmp_path):
    res = run_event_call(_doc(), as_of="2024-03-01", prompt_path=PROMPT,
                         model_call=_call_returning(_model_json()), governor=_gov(tmp_path, kill=True),
                         model_id_requested="m", prompt_version="event_interpreter/v1",
                         projected_cost_usd=0.01, raw_dir=str(tmp_path / "raw"),
                         ledger_path=tmp_path / "l.jsonl", now_iso="2024-03-01T21:00:00")
    assert res.status.startswith("skipped:") and res.call is None
    assert not (tmp_path / "l.jsonl").exists()                # nothing appended, no call made


def test_pit_violation_file_date_after_as_of_is_invalid(tmp_path):
    res = _run(tmp_path, doc=_doc(fd="2024-03-05"))          # doc dated AFTER as_of 2024-03-01
    assert res.status.startswith("invalid:") and res.call is None


def test_special_sit_type_from_8k_source_is_invalid(tmp_path):
    res = _run(tmp_path, text=_model_json(event_type="odd_lot_tender"))  # special-sit type, but source=8k
    assert res.status.startswith("invalid:") and res.call is None


def test_routine_with_high_materiality_is_invalid(tmp_path):
    res = _run(tmp_path, text=_model_json(event_type="routine_non_material", materiality=0.9))
    assert res.status.startswith("invalid:") and res.call is None


def test_non_json_response_is_invalid_and_raw_archived(tmp_path):
    res = _run(tmp_path, text="not json at all")
    assert res.status == "invalid:not_json" and res.raw_path and pathlib.Path(res.raw_path).exists()
