"""tests/test_eval_repair_t331.py — T-331: the broken clock, test-locked.

THE REGRESSION THAT MATTERS: intel_pulse writes `note_<date>.json`; the harness used
to glob `analyst_note_*.json` → the analyst pool was ALWAYS empty and nothing was ever
scored. These tests fail if that joint (or the field projection behind it) ever breaks
again — including the agentic dir the T-323 A/B depends on.
"""
import json

import pandas as pd

from intelligence.analyst import eval_harness as eh
from intelligence.event_call.run_forward import _attach_body, _is_nontrivial, _within_date_floor
from intelligence.event_call.eightk_feed import EventDocument


def _note(as_of: str, level: float = 100.0, sym: str = "SPY") -> dict:
    """A note in the REAL shape intel_pulse writes: `as_of` + nested provenance,
    NO note_date/note_id/model_id at top level."""
    return {
        "schema_version": "analyst_note/v1", "as_of": as_of,
        "market_assessment": "x", "predictions": [{
            "statement": "SPY above", "probability": 0.6,
            "resolver": {"type": "price_above", "symbol": sym, "level": level,
                         "direction": "above", "by_date": "2026-08-10"},
        }],
        "provenance": {"model_id_requested": "m-req", "model_id_served": "m-served",
                       "prompt_version": "daily/v2"},
        "usage": {},
    }


def test_pulse_written_filename_is_actually_loaded(tmp_path):
    """The exact defect: a `note_<date>.json` must be picked up."""
    d = tmp_path / "analyst_notes"; d.mkdir()
    (d / "note_2026-08-01.json").write_text(json.dumps(_note("2026-08-01")))
    loaded = eh._load_notes(d)
    assert len(loaded) == 1, "note_<date>.json must be loaded (this was the broken clock)"


def test_projection_fills_note_date_model_id_and_source(tmp_path):
    """Fixing the glob alone was NOT enough — a note carries `as_of` + provenance."""
    d = tmp_path / "analyst_notes"; d.mkdir()
    (d / "note_2026-08-01.json").write_text(json.dumps(_note("2026-08-01")))
    n = eh._load_notes(d)[0]
    assert n["note_date"] == "2026-08-01"          # was "" → resolution impossible
    assert n["model_id"] == "m-served"             # projected from provenance
    assert n["prompt_version"] == "daily/v2"
    assert n["source"] == "analyst_constrained"
    assert n["note_id"] == "analyst_constrained:2026-08-01"


def test_legacy_prefix_still_loads_and_no_double_count(tmp_path):
    d = tmp_path / "analyst_notes"; d.mkdir()
    (d / "analyst_note_2026-08-02.json").write_text(json.dumps(_note("2026-08-02")))
    assert len(eh._load_notes(d)) == 1


def test_agentic_dir_is_scanned_and_tagged(tmp_path):
    a = tmp_path / "analyst_notes_agentic"; a.mkdir()
    (a / "note_2026-08-03.json").write_text(json.dumps(_note("2026-08-03")))
    n = eh._load_notes(a, "analyst_agentic")[0]
    assert n["source"] == "analyst_agentic"        # the T-323 A/B depends on this tag


def test_end_to_end_repaired_path_scores_a_real_row(tmp_path):
    """THE ACCEPTANCE BAR: a scored analyst row lands in analyst_predictions.jsonl."""
    d = tmp_path / "analyst_notes"; d.mkdir()
    (d / "note_2026-08-01.json").write_text(json.dumps(_note("2026-08-01", level=100.0)))
    idx = pd.bdate_range("2026-07-01", "2026-08-12")
    px = pd.Series([100.0 + 0.2 * i for i in range(len(idx))], index=idx)   # ends > 100 → outcome 1
    log, summ = tmp_path / "preds.jsonl", tmp_path / "summary.json"
    out = eh.run("2026-08-12", price_fn=lambda s: px, pred_log=log, summary=summ,
                 notes_dir=d, event_ledger=tmp_path / "none.jsonl",
                 agentic_notes_dir=tmp_path / "no_agentic")
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(rows) == 1 and rows[0]["resolvable"] is True and rows[0]["outcome"] == 1
    assert rows[0]["source"] == "analyst_constrained"
    assert rows[0]["baseline_implied"] is not None      # item 7: implied baseline for price_above
    assert out["n_resolvable"] == 1


def test_backfill_recovers_archived_notes_but_rejects_unvalidated(tmp_path):
    raw = tmp_path / "raw"; raw.mkdir()
    (raw / "note_2026-08-05.json").write_text(json.dumps(_note("2026-08-05")))
    (raw / "garbage.json").write_text(json.dumps({"as_of": "2026-08-06"}))      # no predictions
    (raw / "malformed.json").write_text(json.dumps({"as_of": "2026-08-07",
                                                    "predictions": [{"statement": "no resolver"}]}))
    got = eh._load_raw_backfill(raw)
    assert [g["note_date"] for g in got] == ["2026-08-05"]     # only the valid one
    assert got[0]["backfilled"] is True
    assert eh._load_raw_backfill(raw, seen_dates={"2026-08-05"}) == []   # never double-counts


def test_event_feed_rejects_trivial_body_and_stale_date():
    assert _is_nontrivial("{}") is False and _is_nontrivial("null") is False
    assert _is_nontrivial("   ") is False and _is_nontrivial("short") is False
    assert _is_nontrivial("x" * 80) is True
    doc = EventDocument(document_ref="r1", source="special_situation", symbol="ABC",
                        file_date="2026-08-01", text="{}")
    assert _attach_body(doc, fetch=lambda *a: None) is False      # "{}" no longer fires a paid call
    old = EventDocument(document_ref="r2", source="8k", symbol="ABC",
                        file_date="2020-01-01", text="x" * 80)
    assert _within_date_floor(old, "2026-07-01") is False
    assert _within_date_floor(old, None) is True                  # no floor → keep
    nodate = EventDocument(document_ref="r3", source="8k", symbol="ABC",
                           file_date="", text="x" * 80)
    assert _within_date_floor(nodate, "2026-07-01") is True        # unknown date → fail-open


def test_kill_switch_has_a_real_path(tmp_path):
    from intelligence.analyst.cost_governor import load_governor
    s = tmp_path / "llm_settings.json"
    s.write_text(json.dumps({"llm": {"monthly_budget_usd": 30.0, "kill_switch": True}}))
    gov = load_governor(str(s), str(tmp_path / "spend.jsonl"))
    assert gov.check("2026-08", 0.01).allowed is False   # the documented operator control binds
    assert gov.cfg.kill_switch is True


# ── T-292 segmentation: a PROMPT BUMP must not pool two analyst regimes ────────
def test_summary_segments_by_prompt_version_and_model_prompt():
    """daily/v2 -> daily/v3 is a DIFFERENT analyst; pooling would hide what the bump
    changed. prompt_version was recorded but nothing segmented on it until T-331b."""
    recs = []
    for i in range(20):
        pv = "daily/v2" if i < 10 else "daily/v3"
        recs.append({"resolvable": True, "outcome": i % 2, "probability": 0.9 if pv.endswith("v3") else 0.5,
                     "category": "px", "prompt_version": pv, "model_id": "claude-haiku-4-5-20251001",
                     "resolve_date": f"2026-08-{(i % 27) + 1:02d}", "prediction_id": f"p{i}"})
    s = eh.summarize(recs)
    assert set(s["by_prompt_version"]) == {"daily/v2", "daily/v3"}
    assert s["by_prompt_version"]["daily/v2"]["n"] == 10
    assert s["by_prompt_version"]["daily/v3"]["n"] == 10
    # the two regimes score differently and are NOT pooled into one Brier
    assert s["by_prompt_version"]["daily/v2"]["brier"] != s["by_prompt_version"]["daily/v3"]["brier"]
    assert set(s["by_model_prompt"]) == {"claude-haiku-4-5-20251001|daily/v2",
                                         "claude-haiku-4-5-20251001|daily/v3"}
    assert set(s["g1_skill_by_prompt_version"]) == {"daily/v2", "daily/v3"}


# ── T-348: a VOIDED note must be VISIBLE, not just absent ─────────────────────
def test_note_coverage_names_the_missing_day():
    """2026-08-27: the model fenced its JSON, fail-loud voided the note, and NOTHING
    surfaced it — the harness just saw one fewer note. Coverage makes the gap a number."""
    notes = [{"note_date": "2026-08-26", "source": "analyst_constrained", "predictions": []},
             {"note_date": "2026-08-28", "source": "analyst_constrained", "predictions": []}]
    cov = eh.note_coverage(notes, "2026-08-28")["analyst_constrained"]
    assert cov["missing_days"] == ["2026-08-27"]
    assert cov["n_missing"] == 1 and cov["coverage_pct"] < 100


def test_note_coverage_segments_by_source():
    notes = [{"note_date": "2026-08-26", "source": "analyst_constrained", "predictions": []},
             {"note_date": "2026-08-26", "source": "analyst_agentic", "predictions": []},
             {"note_date": "2026-08-27", "source": "analyst_agentic", "predictions": []}]
    cov = eh.note_coverage(notes, "2026-08-27")
    assert set(cov) == {"analyst_constrained", "analyst_agentic"}
    assert cov["analyst_agentic"]["n_missing"] == 0
    assert cov["analyst_constrained"]["missing_days"] == ["2026-08-27"]
