"""tests/test_deploy_candidate_row_t354.py — the digest's deploy-candidate row.

This is the stream a future real-money decision would read, so the framing discipline
is load-bearing: the coupling statement must reach the reader BEFORE the number, the
60-day gate applies as everywhere, and execution cost is never netted out.
"""
import pandas as pd

from intelligence.analyst import performance_digest as pdg

LOTS = [{"symbol": "VOO", "qty": 12, "price": 698.04},
        {"symbol": "MTUM", "qty": 5, "price": 300.28},
        {"symbol": "SGOV", "qty": 1, "price": 100.54}]


def _px(flat=None):
    idx = pd.bdate_range("2026-09-01", "2026-09-16")
    def fn(sym):
        lvl = (flat or {}).get(sym)
        if lvl is None:
            return None
        return pd.Series([lvl] * len(idx), index=idx)
    return fn


def test_basis_is_actual_fills_and_execution_cost_is_NOT_netted_out():
    """The book paid 698.04 for VOO while the session closed at 696.20. The candidate
    starts behind by that real cost; smoothing it away would flatter the row."""
    px = _px({"VOO": 698.04, "MTUM": 300.28, "SGOV": 100.54, "SPY": 757.39})
    st = pdg.deploy_candidate_stream(LOTS, px, "2026-09-16", "2026-09-15")
    assert st["basis_dollars"] == 9978.42          # the ACTUAL capital deployed
    assert st["book_growth"] == 1.0                # marked at its own fills
    assert st["twin_symbol"] == "SPY"


def test_a_missing_mark_reports_the_row_MISSING_never_a_guessed_price():
    px = _px({"VOO": 700.0, "MTUM": 300.0, "SGOV": 100.0})     # no SPY twin
    assert pdg.deploy_candidate_stream(LOTS, px, "2026-09-16", "2026-09-15") == {}
    px2 = _px({"VOO": 700.0, "SPY": 757.0})                     # no MTUM mark
    assert pdg.deploy_candidate_stream(LOTS, px2, "2026-09-16", "2026-09-15") == {}


def test_the_60_day_gate_applies_here_like_everywhere():
    px = _px({"VOO": 750.0, "MTUM": 320.0, "SGOV": 101.0, "SPY": 757.39})
    st = pdg.deploy_candidate_stream(LOTS, px, "2026-09-16", "2026-09-15")
    row = pdg.build_rows({pdg.DEPLOY_CANDIDATE_STREAM: st})[0]
    assert row["delta_per_10k"] > 0                 # a big lead...
    assert row["verdict"].startswith("too early to say")   # ...still not decidable
    assert "2 days" in row["verdict"] or "day" in row["verdict"]


def test_the_COUPLING_statement_reaches_the_reader_BEFORE_the_number():
    """A reader must not meet the dollars first and the caveat second."""
    px = _px({"VOO": 698.04, "MTUM": 300.28, "SGOV": 100.54, "SPY": 757.39})
    st = pdg.deploy_candidate_stream(LOTS, px, "2026-09-16", "2026-09-15")
    text = pdg.render(pdg.build_rows({pdg.DEPLOY_CANDIDATE_STREAM: st}), "2026-09-16")
    # REFRAMED T-358 (audit A1). The ORDERING intent — caveat above the number —
    # is untouched and still asserted. What the caveat SAYS changed: the coupling
    # was never in force (single-account guard), so the banner now states it as
    # pending. A banner promising a protection the code lacks is worse than none:
    # it makes a reader discount turnover for a constraint that never binds.
    assert "US_LARGE_BLEND" in text
    assert "SINGLE-ACCOUNT TODAY" in text
    assert text.index("US_LARGE_BLEND") < text.index("| stream |")
    assert "61-day window" in text
    assert "standalone book" in text


def test_no_pressure_words_on_the_row_that_matters_most():
    px = _px({"VOO": 698.04, "MTUM": 300.28, "SGOV": 100.54, "SPY": 757.39})
    st = pdg.deploy_candidate_stream(LOTS, px, "2026-09-16", "2026-09-15")
    low = pdg.render(pdg.build_rows({pdg.DEPLOY_CANDIDATE_STREAM: st}), "2026-09-16").lower()
    for w in ("countdown", "days remaining", "decision approaching", "ready for real money",
              "deadline", "act now", "hurry", "urgent", "last chance"):
        assert w not in low
    assert "does not recommend" in low and "nothing here proposes a date" in low


def test_header_absent_when_the_row_is_absent():
    text = pdg.render(pdg.build_rows({"other": {"book_growth": 1.0, "twin_growth": 1.0,
                                                "n_days": 90}}), "2026-09-16")
    assert "Deploy candidate:" not in text
