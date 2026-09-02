"""tests/test_analyst_eval_t293.py — verification for the analyst eval harness (T-293).

Verification bar (program doc §Verification): hand-resolve 5 synthetic predictions
and match the harness output exactly; idempotency (re-running never double-resolves).
"""
from pathlib import Path

import pandas as pd
import pytest

from intelligence.analyst import eval_harness as eh

# fixture prices — hand-computed outcomes below
PRICES = {
    "SPY": pd.Series([600.0, 630.0, 590.0, 610.0, 620.0],
                     index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-02-01"])),
    "XLK": pd.Series([100.0, 110.0], index=pd.to_datetime(["2026-01-02", "2026-01-05"])),
}
def _price(sym): return PRICES.get(sym)
def _event(src, eid): return None            # nothing settled → event_occurs is fail-closed

# 5 synthetic predictions (one per resolver behavior) + a 6th not-yet-expired
NOTE = {
    "note_id": "n1", "note_date": "2026-01-02", "model_id": "m", "prompt_version": "v1",
    "predictions": [
        # 1 price_above terminal: SPY close 610 >= 600 -> 1
        {"prediction_id": "p1", "probability": 0.7, "category": "market_direction",
         "resolver": {"type": "price_above", "symbol": "SPY", "level": 600.0,
                      "direction": "above", "by_date": "2026-01-05", "mode": "terminal"}},
        # 2 price_above below: SPY 610 <= 500 -> 0
        {"prediction_id": "p2", "probability": 0.2,
         "resolver": {"type": "price_above", "symbol": "SPY", "level": 500.0,
                      "direction": "below", "by_date": "2026-01-05"}},
        # 3 relative_return: XLK +10% vs SPY +1.67% -> gt -> 1
        {"prediction_id": "p3", "probability": 0.6,
         "resolver": {"type": "relative_return", "symbol_a": "XLK", "symbol_b": "SPY",
                      "start_date": "2026-01-02", "end_date": "2026-01-05", "op": "gt"}},
        # 4 dd_exceeds: SPY 630->590 = -6.35% >= 5% -> 1
        {"prediction_id": "p4", "probability": 0.4,
         "resolver": {"type": "dd_exceeds", "symbol": "SPY", "threshold_pct": 5.0,
                      "start_date": "2026-01-02", "end_date": "2026-01-05"}},
        # 5 event_occurs kalshi: unsettled + expired -> resolvable=False (fail-closed)
        {"prediction_id": "p5", "probability": 0.5,
         "resolver": {"type": "event_occurs", "source": "kalshi_settlement",
                      "event_id": "KXFED-26JAN", "predicate": {"settles": "yes"},
                      "by_date": "2026-01-05"}},
        # 6 not yet expired -> must NOT be logged at as_of 2026-01-10
        {"prediction_id": "p6", "probability": 0.5,
         "resolver": {"type": "price_above", "symbol": "SPY", "level": 600.0,
                      "direction": "above", "by_date": "2026-02-01"}},
    ],
}


def _run(tmp_path: Path, as_of="2026-01-10"):
    return eh.run(as_of, notes=[NOTE], price_fn=_price, event_fn=_event,
                  pred_log=tmp_path / "preds.jsonl", summary=tmp_path / "summ.json")


def test_five_synthetic_predictions_resolve_exactly(tmp_path):
    summ = _run(tmp_path)
    recs = {r["prediction_id"]: r for r in eh._load_log(tmp_path / "preds.jsonl")}
    # p6 not expired -> not logged
    assert "p6" not in recs and len(recs) == 5
    assert recs["p1"]["outcome"] == 1 and recs["p1"]["resolvable"]
    assert recs["p2"]["outcome"] == 0
    assert recs["p3"]["outcome"] == 1
    assert recs["p4"]["outcome"] == 1
    assert recs["p5"]["resolvable"] is False and recs["p5"]["outcome"] is None
    assert "source_absent" in recs["p5"]["resolve_detail"]
    # Brier over the 4 resolvable = (.09+.04+.16+.36)/4 = 0.1625
    assert summ["brier"] == pytest.approx(0.1625, abs=1e-9)
    assert summ["n_resolvable"] == 4 and summ["n_unresolvable"] == 1
    assert summ["base_rate"] == pytest.approx(0.75)   # 3 of 4 outcomes = 1


def test_idempotency_settled_rows_never_double_resolve(tmp_path):
    """T-349 amends this: idempotency binds on SETTLED rows only.

    The original assertion (`n1 == n2`, nothing ever re-attempted) encoded the defect
    that killed the live record — a fail-closed `resolvable: false` row is "could not
    settle YET", not a verdict, and treating it as terminal meant 55/57 live rows sat
    permanently dead while every one of them resolved cleanly against live prices.
    Settled rows must still never be re-resolved; unresolvable ones must be retried."""
    _run(tmp_path)
    log1 = eh._load_log(tmp_path / "preds.jsonl")
    settled1 = [r for r in log1 if r.get("resolvable")]
    _run(tmp_path)                                     # re-run same as-of
    log2 = eh._load_log(tmp_path / "preds.jsonl")
    settled2 = [r for r in log2 if r.get("resolvable")]

    # settled rows are NEVER duplicated — one row per prediction_id
    ids = [r["prediction_id"] for r in settled2]
    assert len(ids) == len(set(ids)) == len(settled1)
    # and an UNRESOLVABLE row is re-attempted rather than left permanently dead
    unres1 = [r for r in log1 if not r.get("resolvable")]
    if unres1:
        assert len(log2) > len(log1)
        assert any(r.get("retry_of_unresolvable") for r in log2)
    else:
        assert len(log2) == len(log1)


def test_p6_resolves_once_expired(tmp_path):
    _run(tmp_path, as_of="2026-01-10")                 # p6 not yet expired
    assert "p6" not in {r["prediction_id"] for r in eh._load_log(tmp_path / "preds.jsonl")}
    _run(tmp_path, as_of="2026-02-05")                 # now expired -> resolves (SPY 610>=600 -> 1)
    recs = {r["prediction_id"]: r for r in eh._load_log(tmp_path / "preds.jsonl")}
    assert recs["p6"]["outcome"] == 1


def test_invalid_resolver_rejected_by_validator():
    ok, _ = eh.is_resolvable_spec({"type": "price_above", "symbol": "SPY"})   # missing fields
    assert ok is False
    ok, _ = eh.is_resolvable_spec({"type": "nonsense"})
    assert ok is False
    ok, _ = eh.is_resolvable_spec({"type": "dd_exceeds", "symbol": "SPY", "threshold_pct": 10.0,
                                   "start_date": "2026-01-02", "end_date": "2026-01-05"})
    assert ok is True
