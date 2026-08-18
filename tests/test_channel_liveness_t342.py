"""T-342 — channel liveness: has each load-bearing CONSUMED field ever been non-empty?

The disease the clock census could NOT see: a consumer that runs perfectly every day while
the field it consumes has never once carried anything. The llm_shadow_book logged 17 honest
days of action:'applied' over a structurally empty `hypothetical_actions` — applying nothing
IS applying the note, so every clock ticked and every record was truthful.

E's rule is the charter and the reason this check must be existence-over-history:
AN ALWAYS-EMPTY CHANNEL DEGRADES NOTHING, so no freshness gate or daily assertion can see it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.clock_census import (  # noqa: E402
    CHANNELS, LIVE, NEVER_ALIVE, NO_HISTORY, UNVERIFIABLE, channel_liveness, liveness_line)


def _note(tmp, day, actions=None, preds=None, agentic=False):
    d = tmp / ("data/intel/analyst_notes_agentic" if agentic else "data/intel/analyst_notes")
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{day}.json").write_text(json.dumps({
        "as_of": day,
        "hypothetical_actions": actions if actions is not None else [],
        "predictions": preds if preds is not None else [{"statement": "s"}]}))


def _find(res, consumer):
    return next(d for d in res["detail"] if d["consumer"] == consumer)


# ---------- THE INSTANCE: an always-empty channel is caught ----------
def test_channel_empty_across_ENTIRE_history_is_NEVER_ALIVE(tmp_path):
    for i in range(17):                       # the real shape: 17 honest, empty days
        _note(tmp_path, f"2026-08-{i+1:02d}", actions=[])
    r = channel_liveness(root=str(tmp_path))
    d = _find(r, "llm_shadow_book")
    assert d["status"] == NEVER_ALIVE
    assert "entire" in d["detail"] and "VERIFY UPSTREAM INTENT" in d["detail"]
    assert r["degraded"] is True
    assert "llm_shadow_book:hypothetical_actions" in liveness_line(r)   # NAMED


def test_ONE_non_empty_record_in_all_of_history_makes_it_LIVE(tmp_path):
    """Liveness is existence-over-history: a single non-empty record ever is enough."""
    for i in range(16):
        _note(tmp_path, f"2026-08-{i+1:02d}", actions=[])
    _note(tmp_path, "2026-08-17", actions=[{"symbol": "SPY", "target_weight": 0.1}])
    assert _find(channel_liveness(root=str(tmp_path)), "llm_shadow_book")["status"] == LIVE


def test_it_DISCRIMINATES_between_fields_in_the_SAME_records(tmp_path):
    """The proof it isn't just flagging everything: same files, one field dead, one alive —
    exactly what production shows (predictions 17/17 live, actions 0/17)."""
    for i in range(17):
        _note(tmp_path, f"2026-08-{i+1:02d}", actions=[], preds=[{"statement": "s"}])
    r = channel_liveness(root=str(tmp_path))
    assert _find(r, "llm_shadow_book")["status"] == NEVER_ALIVE
    assert _find(r, "eval_harness")["status"] == LIVE


# ---------- FAIL-CLOSED: never assume a channel is alive ----------
def test_missing_source_is_UNVERIFIABLE_and_a_FINDING(tmp_path):
    r = channel_liveness(root=str(tmp_path))
    d = _find(r, "event_shadow_book")
    assert d["status"] == UNVERIFIABLE and "cannot establish liveness" in d["detail"]
    assert any(f["consumer"] == "event_shadow_book" for f in r["findings"])  # flagged, not benign


def test_unparseable_records_are_UNVERIFIABLE_not_alive(tmp_path):
    d = tmp_path / "data/intel/analyst_notes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-08-01.json").write_text("{ not json")
    assert _find(channel_liveness(root=str(tmp_path)), "llm_shadow_book")["status"] == UNVERIFIABLE


def test_a_raising_check_is_UNVERIFIABLE_never_LIVE(tmp_path, monkeypatch):
    import paper_trader.clock_census as cc

    def boom(root):
        raise RuntimeError("boom")
    monkeypatch.setattr(cc.CHANNELS[0], "check", boom)
    r = channel_liveness(root=str(tmp_path))
    assert r["detail"][0]["status"] == UNVERIFIABLE and "raised" in r["detail"][0]["detail"]


def test_no_records_yet_is_NO_HISTORY_not_a_false_alarm(tmp_path):
    """Before the first record exists there is nothing to assert — distinguishing this from
    NEVER_ALIVE is what keeps the check honest on a newly-armed consumer."""
    (tmp_path / "data/intel/analyst_notes").mkdir(parents=True, exist_ok=True)
    assert _find(channel_liveness(root=str(tmp_path)), "llm_shadow_book")["status"] == NO_HISTORY


# ---------- every channel is declared BY ITS CONSUMER ----------
def test_every_channel_names_its_consumer_and_field():
    for ch in CHANNELS:
        assert ch.consumer and ch.name, "a channel must say who breaks if it is dead"


def test_clean_line_states_all_channels_alive():
    assert "all consumed channels alive" in liveness_line(
        {"degraded": False, "n_live": 3, "n_channels": 3, "n_no_history": 0, "findings": []})


# ---------- read-only ----------
def test_liveness_is_read_only(tmp_path):
    _note(tmp_path, "2026-08-01", actions=[])
    d = tmp_path / "data/intel/analyst_notes"
    before = {f.name: f.read_bytes() for f in d.iterdir()}
    channel_liveness(root=str(tmp_path))
    assert {f.name: f.read_bytes() for f in d.iterdir()} == before


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
