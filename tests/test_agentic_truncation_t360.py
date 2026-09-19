# tests/test_agentic_truncation_t360.py
"""T-360 — the agentic coverage collapse: the note was TRUNCATED, not malformed.

Measured from the live raw archives (`data/intel/llm_raw/agentic_raw_*.json`)
before anything was changed:

    date      preamble   json part   braces balanced   note written
    09-15        880       3524           yes              YES
    09-16       2869       2177            no              no
    09-17       2587       2460            no              no
    09-18       2664       2251            no              no

The tool loop COMPLETED every time (5-7 calls). What changed is that the arm's
prose preamble before the JSON roughly TRIPLED, and the 1500-token output cap
then cut the note mid-value — `…"probability":` and nothing after. Coverage went
84.4% → 33.3% while the constrained arm, which emits the note and nothing else,
stayed at 100%.

So this is not the fail-loud principle misfiring and not a tool-contract fault:
fail-loud did exactly its job, on a note that really was unusable. The defect is
the OUTPUT BUDGET, plus a diagnostic channel that hid it — the API's real
`stop_reason` was never recorded, so a max_tokens truncation was filed as
`end_turn` and reported as `invalid:not_json` for four sessions.
"""
from __future__ import annotations

import json

import pytest

from intelligence.analyst.analyst_service import _loads_lenient

# The measured shapes. Prose preamble, then the note — complete vs cut.
_GOOD = ('Good context from Sep 15-17. The tape shows several things.\n\n'
         '```json\n{"schema_version": "daily_agentic/v2", "as_of": "2026-09-15",'
         ' "hypothetical_actions": [{"account": "shadow", "symbol": "SPY",'
         ' "set_weight": 0.025}]}\n```')
_TRUNCATED = ('Good context from Sep 15-17. The tape shows several things.\n\n'
              '{"schema_version": "daily_agentic/v2", "as_of": "2026-09-18",'
              ' "predictions": [{"statement": "SPY outperforms AGG.",'
              ' "probability":')


def test_the_parser_handles_a_prose_preamble_which_is_NOT_the_defect():
    """09-15 succeeded WITH a preamble, so the preamble alone never broke it —
    ruling that out is what pointed at the budget."""
    obj = _loads_lenient(_GOOD)
    assert obj["as_of"] == "2026-09-15"


def test_a_truncated_note_cannot_be_parsed_which_is_the_defect():
    with pytest.raises(Exception):
        _loads_lenient(_TRUNCATED)


def test_truncation_is_DETECTABLE_by_unbalanced_braces():
    """The signal the fix keys on — no guessing required."""
    assert _TRUNCATED.count("{") > _TRUNCATED.count("}")
    assert _GOOD.count("{") == _GOOD.count("}")


def test_the_agentic_cap_is_SEPARATE_from_the_control_arms():
    """The fix must not touch the CONTROL arm mid-experiment: the constrained
    analyst is the A/B's control and is at 100% coverage. Raising the shared
    `daily` tier would have changed both."""
    s = json.load(open("config/llm_settings.json"))
    assert s["tiers"]["daily"]["max_output_tokens"] == 1500, (
        "the control arm's output budget must not move")
    assert s["tiers"]["daily_agentic"]["max_output_tokens"] > 1500
    assert s["tiers"]["daily_agentic"]["model_id"] == s["tiers"]["daily"]["model_id"] \
        if "model_id" in s["tiers"]["daily_agentic"] else True


def test_the_override_can_RAISE_the_cap_but_never_LOWER_the_governors():
    """The governor's cap is a COST control; this is a truncation fix. It may
    only raise the ceiling, or a config typo becomes a budget bypass."""
    import inspect

    import intelligence.analyst.analyst_agentic as ag
    src = inspect.getsource(ag.run_agentic_note)
    assert "max(int(decision.max_output_tokens)" in src


def test_truncation_reports_itself_as_TRUNCATED_not_as_not_json():
    """A truncated note and a malformed one need opposite fixes. Filing both as
    `not_json` is what sent four sessions of diagnosis nowhere."""
    import inspect

    import intelligence.analyst.analyst_agentic as ag
    src = inspect.getsource(ag.run_agentic_note)
    assert "invalid:truncated" in src
    assert 'stop_reason' in src


def test_the_adapter_records_the_APIs_OWN_stop_reason():
    """`stopped` is our loop's verdict and only ever says 'max_calls'. Without
    the API's stop_reason a max_tokens cut files itself as a normal end_turn —
    the record claiming the call finished when it had been severed mid-JSON."""
    import inspect

    import intelligence.analyst.anthropic_adapter as ad
    src = inspect.getsource(ad)
    assert src.count('"stop_reason": d') + src.count('"stop_reason": data') >= 2
