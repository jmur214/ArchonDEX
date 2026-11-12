"""T-383 (B-6) — locks for the text signals (scripts/lazy_prices/b6_signals.py). No data files:
the LM dictionary is replaced by a tiny in-test one."""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
import pytest

from scripts.lazy_prices import b6_signals as S


@pytest.fixture(autouse=True)
def tiny_lm(monkeypatch):
    lm = {"negative": frozenset({"loss", "decline"}), "positive": frozenset({"gain", "strong"}),
          "uncertainty": frozenset({"may"}), "litigious": frozenset({"lawsuit"})}
    monkeypatch.setattr(S, "load_lm", lambda: lm)


def test_cosine_tf_identical_disjoint_and_degenerate():
    a = Counter({"risk": 3, "market": 1})
    assert S.cosine_tf(a, a) == pytest.approx(1.0)
    assert S.cosine_tf(a, Counter({"other": 2})) == 0.0
    assert np.isnan(S.cosine_tf(Counter(), a))          # degenerate -> NaN, never a clean 0


def test_tone_and_lm_negation_rule():
    t = S.tone_counts(S.tokens("Strong gain. We had no gain and a loss. Not strong."))
    # positives: strong (counted), gain (counted), 'no gain' (negated), 'not strong' (negated)
    assert t["pos_share"] == pytest.approx(2 / t["n_tokens"])
    assert t["neg_share"] == pytest.approx(1 / t["n_tokens"])
    assert t["tone"] == pytest.approx((2 - 1) / t["n_tokens"])


def _row(acc, form, accepted, period, risk="OK", mda="OK", rt="risk words here", mt="mda words",
         src="item"):
    return {"cik": 1, "form": form, "accession": acc, "acceptance_dt": accepted,
            "period_end": period, "risk_status": risk, "risk_text": rt if risk == "OK" else "",
            "mda_status": mda, "mda_text": mt if mda == "OK" else "", "mda_source": src}


def test_pairing_is_pit_same_form_and_same_quarter():
    f = pd.DataFrame([
        _row("k1", "10-K", "2015-02-20T21:00:00.000Z", "2014-12-31"),
        _row("q1", "10-Q", "2015-05-01T21:00:00.000Z", "2015-03-31"),
        _row("q2", "10-Q", "2015-08-01T21:00:00.000Z", "2015-06-30"),
        _row("k2", "10-K", "2016-02-19T21:00:00.000Z", "2015-12-31"),
        _row("q3", "10-Q", "2016-05-02T21:00:00.000Z", "2016-03-31", rt="changed risk entirely"),
    ])
    rows = {r["accession"]: r for r in S.company_signals(f)}
    assert rows["k2"]["prior_accession"] == "k1"
    assert rows["q3"]["prior_accession"] == "q1"          # same fiscal quarter, a year earlier
    assert rows["q3"]["qoq_prior_accession"] is None       # q2 is 9 months back: not adjacent
    assert rows["q2"]["qoq_prior_accession"] == "q1"
    assert rows["k1"]["yoy_combo_why"] == "no_prior"
    assert rows["k2"]["yoy_combo_cos"] == pytest.approx(1.0)
    assert rows["q3"]["yoy_risk_cos"] < 1.0
    assert rows["q3"]["decision_floor_date"] == "2016-05-03"


def test_section_not_ok_and_mda_source_switch_give_nan_with_reason():
    f = pd.DataFrame([
        _row("k1", "10-K", "2015-02-20T21:00:00.000Z", "2014-12-31", src="item"),
        _row("k2", "10-K", "2016-02-19T21:00:00.000Z", "2015-12-31", src="title_fallback"),
        _row("k3", "10-K", "2017-02-19T21:00:00.000Z", "2016-12-31", risk="NOT_LOCATED",
             src="title_fallback"),
    ])
    rows = {r["accession"]: r for r in S.company_signals(f)}
    assert rows["k2"]["yoy_combo_why"] == "mda_source_switch" and np.isnan(rows["k2"]["yoy_combo_cos"])
    assert rows["k2"]["yoy_risk_why"] == "ok"
    assert rows["k3"]["yoy_combo_why"] == "current_not_ok" and np.isnan(rows["k3"]["yoy_combo_cos"])
    assert rows["k3"]["yoy_mda_why"] == "ok"


def test_a_successful_retry_beats_the_recorded_failure_in_every_reader():
    """Cisco's 37 filings failed on a transient DNS outage (2026-11-12); `fetch --retry-failed`
    appends new rows. The reader must keep the success, wherever it sits in shard order."""
    from scripts.lazy_prices.b6_build_panel import latest_by_accession
    d = pd.DataFrame({"accession": ["a", "a", "b", "b", "c"],
                      "fetch_ok": [False, True, True, False, False],
                      "v": ["fail", "ok", "ok", "fail", "fail"]})
    out = latest_by_accession(d).set_index("accession").v.to_dict()
    assert out == {"a": "ok", "b": "ok", "c": "fail"}
