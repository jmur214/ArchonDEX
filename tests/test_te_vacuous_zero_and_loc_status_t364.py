# tests/test_te_vacuous_zero_and_loc_status_t364.py
"""T-364 — close the OTHER half of the vacuous-zero class, and name the field.

Two defects, one unit, both found by reading account-3's live tracker
(`paper_state_ai_trader/data/state/llm_analyst_tracking.json`, 34 points).

=== 1. The vacuous tracking error, second half ===

Every one of the 9 non-None `te` values on that account is 0.0, and FIVE of
them are vacuous. T-361 closed only the rarer kind:

    date     te    held_w / target_w                      verdict
    08-26    0     {}                      {}             VACUOUS — no names
    09-04    0.0   {SPY 0.0}               same           VACUOUS — all zero
    09-09    0.0   {GLD 0.0, SPY 0.0766}   same           GENUINE
    09-23    0.0   {AGG 0, GLD 0, SPY 0}   same           VACUOUS — all zero
    10-02    0.0   {SPY 0.0764}            same           GENUINE
    10-05    0.0   {SPY 0.077}             same           GENUINE
    10-06    0.0   {SPY 0.0775}            same           GENUINE
    10-08    0.0   {SPY 0.0}               same           VACUOUS — all zero
    10-13    0.0   {SPY 0.0}               same           VACUOUS — all zero

Sum of |0.0 - 0.0| over a NON-EMPTY set of zero weights is also 0.0, and gate
(a) reads it as "tracked its targets exactly" on a day the account targeted
nothing and held nothing. That is 4 of the 5 — the COMMON case — so closing
only the empty-set half left the larger half still reporting a measurement it
never made.

The distinction being locked is "nothing to track" vs "tracked it exactly",
never "the number happens to be zero": the four GENUINE rows must keep
computing 0.0.

=== 2. The rejection reason that named no field ===

`validate_note` returned `str(e).splitlines()[0]`, and pydantic's first line is
only the COUNT — "1 validation error for AnalystNote". The agentic arm rejected
notes on 2026-10-05 and 2026-10-09 and the record could not say which field was
wrong; by the time anyone looked the Batch logs had aged out. Typing a failure
only helps if the name SELECTS THE FIX.
"""
from __future__ import annotations

import pytest

from intelligence.analyst.note_schema import validate_note
from paper_trader.sleeve_tracker import SleeveTracker

CLOSES = {"SPY": 754.05, "AGG": 95.81, "GLD": 391.74}

# Verbatim from the live artifact: (date, weights, expected te).
# held_w == target_w on every one of these real points.
ACCT3_ROWS = [
    # --- VACUOUS: no names ---
    ("2026-08-26", {}, None),
    # --- VACUOUS: names present, every weight zero ---
    ("2026-09-04", {"SPY": 0.0}, None),
    ("2026-09-23", {"AGG": 0.0, "GLD": 0.0, "SPY": 0.0}, None),
    ("2026-10-08", {"SPY": 0.0}, None),
    ("2026-10-13", {"SPY": 0.0}, None),
    # --- GENUINE: a real zero over real non-zero weights ---
    ("2026-09-09", {"GLD": 0.0, "SPY": 0.0766}, 0.0),
    ("2026-10-02", {"SPY": 0.0764}, 0.0),
    ("2026-10-05", {"SPY": 0.077}, 0.0),
    ("2026-10-06", {"SPY": 0.0775}, 0.0),
]


def _te(tmp_path, date, weights, name):
    t = SleeveTracker(path=f"data/state/{name}.json", root=str(tmp_path))
    t.record(date, 100_000.0, CLOSES,
             target_weights=dict(weights), held_weights=dict(weights))
    return t._load()[-1]["exec"]["te"]


@pytest.mark.parametrize("date,weights,expected", ACCT3_ROWS,
                         ids=[r[0] for r in ACCT3_ROWS])
def test_acct3_row_by_row(tmp_path, date, weights, expected):
    """One test per row of the live table — the four GENUINE days must still
    produce 0.0, the five VACUOUS days None."""
    got = _te(tmp_path, date, weights, date.replace("-", ""))
    assert got == expected, (
        f"{date}: weights={weights} -> te={got!r}, expected {expected!r}")


def test_a_real_drift_is_unaffected(tmp_path):
    """The guard must not swallow an actual tracking error."""
    t = SleeveTracker(path="data/state/drift.json", root=str(tmp_path))
    t.record("2026-10-14", 100_000.0, CLOSES,
             target_weights={"SPY": 0.5}, held_weights={"SPY": 0.4})
    assert t._load()[-1]["exec"]["te"] == 0.1


def test_one_nonzero_among_zeros_still_measures(tmp_path):
    """The boundary: 'all zero' means ALL. A single live position makes the
    comparison real, which is exactly the 09-09 row's shape."""
    t = SleeveTracker(path="data/state/mixed.json", root=str(tmp_path))
    t.record("2026-10-14", 100_000.0, CLOSES,
             target_weights={"GLD": 0.0, "SPY": 0.08},
             held_weights={"GLD": 0.0, "SPY": 0.05})
    assert t._load()[-1]["exec"]["te"] == pytest.approx(0.03)


def test_held_weights_None_remains_no_data(tmp_path):
    """T-361's pre-existing rebalance-morning rule, re-locked: an unsettled
    book is no-data, never a spurious full-weight drift. This is ALSO why a
    bare te=None cannot attribute the deploy — the old code produced it too."""
    t = SleeveTracker(path="data/state/pre.json", root=str(tmp_path))
    t.record("2026-10-14", 100_000.0, CLOSES,
             target_weights={"SPY": 0.5}, held_weights=None)
    assert t._load()[-1]["exec"]["te"] is None


# --------------------------------------------------------------------------- #
# 2. the rejection reason must name the field
# --------------------------------------------------------------------------- #

def test_the_rejection_reason_NAMES_THE_FIELD():
    """THE REGRESSION. Previously this returned only '<n> validation errors for
    AnalystNote' and the field was unrecoverable from the record."""
    note, err = validate_note({"schema_version": "daily/v1"})
    assert note is None
    assert "schema_version" in err, f"the reason names no field: {err!r}"
    assert "validation error" in err


def test_the_reason_still_leads_with_the_count_and_is_bounded():
    """Additive, not a rewrite: the old first line is preserved so existing
    readers and greps keep working, and the string stays capped."""
    note, err = validate_note({"schema_version": "daily/v1"})
    assert err.startswith("5 validation errors for AnalystNote")
    assert len(err) <= 300


def test_the_describer_NEVER_raises_on_a_non_pydantic_error():
    """A diagnostic that throws turns a rejected note into a crashed pulse."""
    from intelligence.analyst.note_schema import _describe_validation_error

    class _Odd(Exception):
        def errors(self):
            raise RuntimeError("not pydantic")

    assert _describe_validation_error(_Odd("boom")) == "boom"
    assert _describe_validation_error(ValueError("plain")) == "plain"


def test_a_VALID_note_is_still_accepted():
    """The change must touch the REASON only, never the accept/reject verdict."""
    import json
    from pathlib import Path
    fx = Path(__file__).parent / "fixtures" / "agentic_note_2026-09-15.json"
    payload = json.loads(fx.read_text())
    note, err = validate_note(payload)
    assert note is not None and err is None
