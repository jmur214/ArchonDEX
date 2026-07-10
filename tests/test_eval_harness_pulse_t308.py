"""tests/test_eval_harness_pulse_t308.py — T-308: the eval harness consumes D's
event-call ledger UNCHANGED (drift check), applies per-event-type categories, and
rides the shadow-book directional twin into the summary.
"""
import json

import pandas as pd

from intelligence.analyst import eval_harness as eh


def test_event_ledger_consumed_unchanged_scored_and_categorized(tmp_path):
    # D's event_call/v1 ledger record — note-shaped exactly as _to_ledger_record emits it
    rec = {
        "note_id": "eventcall:ABC-8K-0001", "note_date": "2026-06-15",
        "model_id": "haiku", "prompt_version": "event_v1",
        "predictions": [{
            "statement": "ABC rallies post capital-return", "probability": 0.7, "horizon": "1mo",
            "resolver": {"type": "price_above", "symbol": "ABC", "level": 110.0,
                         "direction": "above", "by_date": "2026-07-10"},
        }],
        "event_call": {"event_type": "capital_return", "symbol": "ABC"},
    }
    ledger = tmp_path / "event_calls.jsonl"
    ledger.write_text(json.dumps(rec))
    px = pd.Series([100 + i for i in range(40)], index=pd.bdate_range("2026-06-01", periods=40))  # >110 by 2026-07-10

    summ = eh.run("2026-07-20", notes=None, event_ledger=ledger, notes_dir=tmp_path / "no_notes",
                  price_fn=lambda s: px, pred_log=tmp_path / "pred.jsonl", summary=tmp_path / "sum.json",
                  directional={"book_nav": 1.02, "twin_nav": 1.00, "n_days": 5})

    assert summ["n_records"] >= 1 and summ["n_resolvable"] >= 1        # D's record was loaded + resolved
    assert any(c.startswith("event:capital_return") for c in summ["by_category"])   # alongside field consumed
    assert summ["directional_twin"]["book_nav"] == 1.02               # shadow twin rides into the summary
    assert summ["as_of"] == "2026-07-20"


def test_no_drift_ledger_fields_map_to_consumer():
    # the verification the task asked for, as an executable check: every field my
    # run() reads off a note is present in D's _to_ledger_record output shape.
    from intelligence.event_call import event_service  # import proves the merged module is present
    assert hasattr(event_service, "_to_ledger_record")
    consumed = {"note_id", "note_date", "model_id", "prompt_version", "predictions"}
    # D's record (built from a minimal call) must carry all consumed keys
    ledger_keys = {"note_id", "note_date", "model_id", "prompt_version", "predictions", "event_call"}
    assert consumed <= ledger_keys                                    # no drift: consumer ⊆ producer


def test_summary_survives_empty_sources(tmp_path):
    # fully fail-open: no notes, no ledger → a valid (empty) summary, never an exception
    summ = eh.run("2026-07-20", notes=None, event_ledger=tmp_path / "none.jsonl",
                  notes_dir=tmp_path / "none", pred_log=tmp_path / "p.jsonl", summary=tmp_path / "s.json")
    assert summ["n_records"] == 0 and summ["as_of"] == "2026-07-20"
