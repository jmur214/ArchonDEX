"""tests/test_analyst_eval_baselines_t293b.py — T-293b: real event resolution +
market-implied/persistence baselines + the amended-G1 skill gate.

Key proof: a base-rate-HEDGING analyst does NOT clear the amended G1 (skill ci_low>0),
while a genuinely skilled one does — the exact gameability hole the review closed.
"""
import pandas as pd
import pytest

from intelligence.analyst import eval_harness as eh


@pytest.fixture
def kalshi_fred(monkeypatch):
    kal = pd.DataFrame([{
        "ticker": "KXFED-26JUL-T4.00", "event_ticker": "KXFED-26JUL", "snap_date": "2026-07-07",
        "floor_strike": 4.00, "strike_type": "greater", "expiration_time": "2026-07-30T18:00:00Z",
        "yes_bid": 0.30, "yes_ask": 0.34, "last_price": 0.32,
    }])
    fred = pd.DataFrame([
        {"series": "DFEDTARU", "observation_date": "2026-07-06", "value": 4.00},
        {"series": "DFEDTARU", "observation_date": "2026-07-30", "value": 4.25},   # realized 4.25 > 4.00 strike
    ])
    monkeypatch.setattr(eh, "_KALSHI", kal)
    monkeypatch.setattr(eh, "_FRED", fred)
    return kal, fred


def test_event_occurs_resolves_via_kalshi_and_fred(kalshi_fred):
    resolver = {"type": "event_occurs", "source": "kalshi_settlement",
                "event_id": "KXFED-26JUL-T4.00", "predicate": {"settles": "yes"},
                "by_date": "2026-07-30"}
    res = eh.resolve(resolver, note_date="2026-07-07", as_of="2026-08-01", event_fn=eh._disk_event)
    assert res.resolvable and res.outcome == 1        # realized 4.25 > strike 4.00 -> settles yes


def test_market_implied_baseline_is_kalshi_yes_mid(kalshi_fred):
    resolver = {"type": "event_occurs", "source": "kalshi_settlement",
                "event_id": "KXFED-26JUL-T4.00", "predicate": {"settles": "yes"}, "by_date": "2026-07-30"}
    assert eh.market_implied_prob(resolver, "2026-07-07") == pytest.approx(0.32)   # (0.30+0.34)/2
    assert eh.market_implied_prob(resolver, "2026-06-01") is None                  # no PIT snapshot that day


def test_persistence_baseline_in_unit_interval():
    idx = pd.bdate_range("2025-10-01", periods=80)
    px = pd.Series([100 + i * 0.1 for i in range(80)], index=idx)
    resolver = {"type": "price_above", "symbol": "SPY", "level": 110.0,
                "direction": "above", "by_date": "2025-11-15"}
    p = eh.persistence_prob(resolver, "2025-10-31", price_fn=lambda s: px)
    assert p is not None and 0.0 <= p <= 1.0


def _recs(model_probs, outcomes, baseline_key=None, baseline_vals=None):
    out = []
    for i, (p, o) in enumerate(zip(model_probs, outcomes)):
        r = {"resolvable": True, "probability": p, "outcome": o, "category": "c"}
        if baseline_key:
            r[baseline_key] = baseline_vals[i]
        out.append(r)
    return out


def test_amended_g1_skilled_clears_hedger_fails():
    outcomes = [1, 0] * 15                                   # base rate 0.5, N=30
    skilled = eh._brier_skill(_recs([0.85 if o else 0.15 for o in outcomes], outcomes), "base_rate")
    hedger = eh._brier_skill(_recs([0.5] * 30, outcomes), "base_rate")
    # 2nd amendment: clears iff the block-bootstrap CI on the Brier DIFFERENTIAL excludes 0
    assert skilled["clears"] is True and skilled["diff_ci_low"] > 0       # discrimination -> clears
    assert hedger["clears"] is False and abs(hedger["mean_brier_diff"]) < 0.02   # hedger: differential ~0 -> FAILS


def test_recalibration_reveals_hedged_discrimination():
    # a DISCRIMINATING but HEDGED model: prob 0.55 when outcome 1, 0.45 when 0 (compressed to 0.5).
    # raw Brier is poor; walk-forward isotonic (fit on earlier history) recovers the discrimination.
    recs = []
    for i in range(60):
        o = i % 2
        recs.append({"resolvable": True, "outcome": o, "probability": 0.55 if o else 0.45,
                     "category": "c", "resolve_date": f"2026-08-{(i % 27) + 1:02d}",
                     "prediction_id": f"p{i:03d}"})
    g1 = eh._g1_block(recs)
    assert g1["brier_recalibrated"] < g1["brier_raw"]        # recalibration is the honest read
    # recalibrated skill vs base rate clears where raw (hedged) does not distinguish as well
    assert g1["recalibrated"]["vs_base_rate"]["clears"] is True


def test_gimme_exclusion_drops_near_certain_baseline():
    # 20 records; baseline_implied = 0.97 (gimme) on half -> those are excluded from the skill pool
    outcomes = [1, 0] * 10
    vals = [0.97, 0.97] * 5 + [0.5, 0.5] * 5
    s = eh._brier_skill(_recs([0.6] * 20, outcomes, "baseline_implied", vals), "implied")
    assert s["n"] == 10                                     # the 10 gimme (>0.9) records dropped
