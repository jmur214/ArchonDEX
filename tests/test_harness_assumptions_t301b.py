"""T-301b — the consume-policy (core/harness_assumptions). Locks in the FROZEN rule:
min-n-or-keep, Bayesian shrinkage toward the current assumption, the ≤25%/quarter cap, and — the
load-bearing one — the DECISION-FLIP tripwire that HALTS to a human instead of auto-applying (the SSO
slippage crossing the pre-registered 1.55 bps offense breakeven). Operational-cost learning, never a verdict.
"""
import json

from core.harness_assumptions import (ABS_CAP_RATE, DECISION_FLIP_BREAKEVENS, N_MIN, REL_CAP,
                                       _default_assumptions, apply_cap, load_assumptions,
                                       refresh_harness_assumptions, shrink_continuous, shrink_rate,
                                       write_refresh)


def _cur():
    return _default_assumptions()


# ---- the frozen shrinkage math ----
def test_shrink_continuous_toward_current():
    # (n·measured + k·current)/(n+k); n=30, k=50
    assert abs(shrink_continuous(6.0, 1.5, 30) - (30 * 6.0 + 50 * 1.5) / 80) < 1e-9
    # at the min n the current keeps the majority weight (k=50 > n=30)
    assert shrink_continuous(6.0, 1.5, 30) < (6.0 + 1.5) / 2


def test_shrink_rate_toward_current():
    # (k·p0 + successes)/(k+n); p0=1.0, k=100, n=60
    assert abs(shrink_rate(48, 60, 1.0) - (100 * 1.0 + 48) / 160) < 1e-9


def test_cap_is_25pct_relative_for_continuous_and_absolute_for_rates():
    capped, was = apply_cap(1.5, 5.0, is_rate=False)
    assert was and abs(capped - 1.5 * (1 + REL_CAP)) < 1e-9        # 1.875
    capped_r, was_r = apply_cap(0.9, 0.2, is_rate=True)
    assert was_r and abs(capped_r - (0.9 - ABS_CAP_RATE)) < 1e-9   # 0.80


# ---- min-n gate: below the floor, KEEP the current assumption ----
def test_below_n_min_keeps_current_no_update():
    res = refresh_harness_assumptions(
        "2026Q3",
        slippage_agg={("roth", "SPY"): {"n": N_MIN["slippage_bps"] - 1, "median_slippage_bps": 9.0}},
        rate_counts={("roth", "SPY", "fill_rate"): (30, N_MIN["fill_rate"] - 1)},
        current=_cur())
    for e in res.entries:
        assert e.applied is False and e.reason == "below_n_min" and e.new == e.old
    assert res.new_assumptions["instruments"] == {}                # nothing written


# ---- the DECISION-FLIP tripwire: crossing 1.55 bps HALTS, does NOT apply ----
def test_slippage_crossing_offense_breakeven_halts_and_is_not_applied():
    # SSO slippage: current 1.5 (< 1.55, offense config beats SPY). Measured 6.0 over many fills →
    # shrink 5.79 → capped to 1.875 (> 1.55) → a decision FLIP → HALT.
    res = refresh_harness_assumptions(
        "2026Q3",
        slippage_agg={("roth_offense", "SSO"): {"n": 400, "median_slippage_bps": 6.0}},
        rate_counts={}, current=_cur())
    e = [x for x in res.entries if x.instrument == "SSO"][0]
    assert e.applied is False and e.reason.startswith("tripwire_halt")
    assert e.new == e.old == 1.5                                    # verdict-relevant value UNCHANGED
    assert res.halts and res.halts[0]["breakeven"] == 1.55         # escalated to the human
    assert res.new_assumptions["instruments"] == {}                # not written


def test_non_flip_slippage_applies_capped():
    # SPY (no breakeven registered): current 1.5, measured 3.0, n=100 → shrink 2.5 → cap 1.875 → applies.
    res = refresh_harness_assumptions(
        "2026Q3", slippage_agg={("roth", "SPY"): {"n": 100, "median_slippage_bps": 3.0}},
        rate_counts={}, current=_cur())
    e = [x for x in res.entries if x.instrument == "SPY"][0]
    assert e.applied is True and e.reason == "capped"
    assert abs(res.new_assumptions["instruments"]["roth:SPY"]["slippage_bps"] - 1.875) < 1e-9


def test_rate_applies_and_stays_bounded_0_1():
    res = refresh_harness_assumptions(
        "2026Q3", slippage_agg={},
        rate_counts={("roth", "SPY", "fill_rate"): (48, 60)}, current=_cur())
    e = res.entries[0]
    assert e.applied and 0.0 <= res.new_assumptions["instruments"]["roth:SPY"]["fill_rate"] <= 1.0


# ---- tripwire: strategy params / non-operational metrics are ignored entirely ----
def test_non_operational_metric_is_ignored():
    res = refresh_harness_assumptions(
        "2026Q3", slippage_agg={},
        rate_counts={("roth", "SPY", "lookback"): (5, 100)}, current=_cur())   # 'lookback' ∉ RATE_METRICS
    assert res.entries == [] and res.new_assumptions["instruments"] == {}


# ---- fail-closed load + versioned provenance ----
def test_load_fails_closed_to_defaults(tmp_path):
    missing = tmp_path / "nope.json"
    assert load_assumptions(missing) == _default_assumptions()
    (tmp_path / "empty.json").write_text("{}")
    assert load_assumptions(tmp_path / "empty.json") == _default_assumptions()  # empty → defaults, not {}


def test_write_refresh_is_versioned_and_appends_history(tmp_path):
    res = refresh_harness_assumptions(
        "2026Q3", slippage_agg={("roth", "SPY"): {"n": 100, "median_slippage_bps": 3.0}},
        rate_counts={("roth_offense", "SSO", "x"): (1, 1)},  # ignored non-metric, harmless
        current=_cur())
    # also add a halt to confirm halts are logged
    res2 = refresh_harness_assumptions(
        "2026Q3", slippage_agg={("roth_offense", "SSO"): {"n": 400, "median_slippage_bps": 6.0}},
        rate_counts={}, current=_cur())
    cfg = tmp_path / "harness_assumptions.json"; hist = tmp_path / "history.jsonl"
    write_refresh(res, config_path=cfg, history_path=hist, now_iso="2026-07-10T00:00:00")
    write_refresh(res2, config_path=cfg, history_path=hist, now_iso="2026-07-10T00:00:00")
    written = json.loads(cfg.read_text())
    assert written["version"] == "refresh-2026Q3"
    lines = [json.loads(x) for x in hist.read_text().splitlines()]
    assert any(row.get("TRIPWIRE_HALT") for row in lines)          # the halt is in the audit trail
    assert any(row.get("metric") == "slippage_bps" and row.get("applied") for row in lines)
