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
    assert skilled["clears"] is True and skilled["skill_ci_low"] > 0      # discrimination -> clears
    assert hedger["clears"] is False                                     # zero skill vs its own base rate -> FAILS
    assert abs(hedger["skill"]) < 0.02


def test_gimme_exclusion_drops_near_certain_baseline():
    # 20 records; baseline_implied = 0.97 (gimme) on half -> those are excluded from the skill pool
    outcomes = [1, 0] * 10
    vals = [0.97, 0.97] * 5 + [0.5, 0.5] * 5
    s = eh._brier_skill(_recs([0.6] * 20, outcomes, "baseline_implied", vals), "implied")
    assert s["n"] == 10                                     # the 10 gimme (>0.9) records dropped
