"""tests/test_fleet_scoring_t323.py — T-323 fleet scoring: the PRE-STATED gates.

Asserts the frozen behavior of docs/Audit/fleet_scoring_gates_t323_2026_07_28.md:
matched-question pairing, the two-sided A/B with a tie keeping the constrained
source, the drift override, and the disagreement channel's Q1/Q3.
"""
from intelligence.analyst import fleet_scoring as fs


def _rec(pid, sym, by, prob, outcome, src, day="2026-08-01", resolvable=True):
    return {"prediction_id": pid, "source": src, "probability": prob, "outcome": outcome,
            "resolvable": resolvable, "resolve_date": day, "category": "px",
            "resolver": {"type": "price_above", "symbol": sym, "level": 100.0,
                         "direction": "above", "by_date": by}}


def _pool(src, n, prob_fn, outcomes=None, sym_fn=lambda i: f"S{i:03d}"):
    out = []
    for i in range(n):
        o = (i % 2) if outcomes is None else outcomes[i]
        out.append(_rec(f"{src}#{i}", sym_fn(i), f"2026-08-{(i % 27) + 1:02d}",
                        prob_fn(i, o), o, src, day=f"2026-08-{(i % 27) + 1:02d}"))
    return out


def test_matched_pairs_requires_same_question_and_both_resolvable():
    a = [_rec("a1", "SPY", "2026-08-10", 0.6, 1, "analyst_constrained"),
         _rec("a2", "QQQ", "2026-08-10", 0.6, 1, "analyst_constrained")]
    b = [_rec("b1", "SPY", "2026-08-10", 0.7, 1, "analyst_agentic"),
         _rec("b2", "IWM", "2026-08-10", 0.7, 1, "analyst_agentic"),
         _rec("b3", "QQQ", "2026-08-10", 0.7, 1, "analyst_agentic", resolvable=False)]
    pairs = fs.matched_pairs(a, b)
    assert len(pairs) == 1                       # SPY only: QQQ's B-side is unresolvable, IWM unmatched


def test_ab_tie_keeps_constrained_and_reports_no_difference():
    # both sources identical -> differential ~0 -> NO_DIFFERENCE_PROVEN, tie-break = keep constrained
    con = _pool("analyst_constrained", 60, lambda i, o: 0.8 if o else 0.2)
    agt = _pool("analyst_agentic", 60, lambda i, o: 0.8 if o else 0.2)
    r = fs.ab_constrained_vs_agentic(con, agt)
    assert r["eligible_pairs"] == 60
    assert r["verdict"] == "NO_DIFFERENCE_PROVEN"
    assert "keep_constrained" in r["tie_break"]


def test_ab_detects_a_genuinely_better_agentic_source():
    con = _pool("analyst_constrained", 60, lambda i, o: 0.5)              # uninformative
    agt = _pool("analyst_agentic", 60, lambda i, o: 0.9 if o else 0.1)    # sharp + correct
    r = fs.ab_constrained_vs_agentic(con, agt)
    assert r["verdict"] == "B_WINS" and r["raw"]["diff_ci_low"] > 0


def test_ab_insufficient_pairs_is_not_a_win():
    con = _pool("analyst_constrained", 10, lambda i, o: 0.5)
    agt = _pool("analyst_agentic", 10, lambda i, o: 0.9 if o else 0.1)
    r = fs.ab_constrained_vs_agentic(con, agt)
    assert r["raw"]["verdict"] == "INSUFFICIENT" and r["raw"]["clears"] is False
    assert "keep_constrained" in r["tie_break"]


def test_question_set_drift_forces_inconclusive():
    # agentic answers a mostly DIFFERENT question set -> eligible pairs < 50% of smaller pool
    con = _pool("analyst_constrained", 60, lambda i, o: 0.5)
    agt = _pool("analyst_agentic", 60, lambda i, o: 0.9 if o else 0.1,
                sym_fn=lambda i: f"S{i:03d}" if i < 10 else f"X{i:03d}")
    r = fs.ab_constrained_vs_agentic(con, agt)
    assert r["question_set_drifted"] is True
    assert r["verdict"] == "INCONCLUSIVE_DRIFTED_SETS"     # override regardless of the differential


def test_disagreement_q1_null_when_models_agree_and_q3_ensemble_scored():
    con = _pool("analyst_constrained", 60, lambda i, o: 0.8 if o else 0.2)
    agt = _pool("analyst_agentic", 60, lambda i, o: 0.78 if o else 0.22)   # LOW divergence
    d = fs.disagreement_channel(con, agt)
    assert d["n_matched"] == 60
    assert d["buckets"]["HIGH"] == 0
    assert d["q1_side_wins_on_disagreement"]["verdict"] == "INSUFFICIENT"   # no HIGH pairs -> no claim
    assert d["q3_ensemble"]["vs_a"]["n_pairs"] == 60


def test_book_vs_twin_requires_both_ci_and_maxdd():
    good = fs.book_vs_twin({"n_days": 60, "book_nav": 1.1, "twin_nav": 1.0, "maxdd_pct": -8.0,
                            "twin_maxdd_pct": -10.0, "daily_excess_vs_twin": [0.002] * 60})
    bad_dd = fs.book_vs_twin({"n_days": 60, "book_nav": 1.1, "twin_nav": 1.0, "maxdd_pct": -30.0,
                              "twin_maxdd_pct": -10.0, "daily_excess_vs_twin": [0.002] * 60})
    assert good["clears"] is True
    assert bad_dd["clears"] is False and bad_dd["maxdd_within_tolerance"] is False


def test_fleet_table_scores_every_source_with_same_machinery():
    recs = (_pool("analyst_constrained", 40, lambda i, o: 0.8 if o else 0.2)
            + _pool("analyst_agentic", 40, lambda i, o: 0.7 if o else 0.3))
    recs.append({**_rec("e1", "SPY", "2026-08-10", 0.6, 1, None), "category": "event:capital_return"})
    t = fs.fleet_table(recs)
    assert set(t["sources"]) == {"analyst_constrained", "analyst_agentic", "event_interpreter"}
    assert t["sources"]["analyst_constrained"]["resolved"] == 40
    assert "scoring != authorization" in t["posture"]
