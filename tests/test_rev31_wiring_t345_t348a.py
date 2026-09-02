# tests/test_rev31_wiring_t345_t348a.py
"""rev31's two E-shipped wires: the advisor monthly/on-change step (T-345) and
the agentic_v2 caller repoint (T-348a — A drafts, E ships)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "scripts/run_paper_cloud_day.py").read_text()
PULSE = (ROOT / "paper_trader/intel_pulse.py").read_text()


def test_advisor_step_is_wired_report_only_and_artifact_derived():
    i = RUNNER.index("T-345 ADVISOR")
    block = RUNNER[i:i + 2600]
    assert "advisor_surface.md" in block and "wrapper_census.json" in block
    # cadence from the ARTIFACT's own date, never a run-flag
    assert "ARTIFACT-DERIVED" in block
    # monthly OR census-newer on-change
    assert '[:7]' in block and 'as_of' in block
    assert "except Exception" in block and "non-fatal" in block
    assert "canonical =" not in block


def test_advisor_step_runs_in_the_acct1_branch_after_the_digest():
    assert RUNNER.index("T-344 DIGEST") < RUNNER.index("T-345 ADVISOR")


def test_agentic_caller_ships_v2_everywhere_the_record_segments():
    assert 'prompt_path="config/prompts/analyst/daily_agentic_v2.md"' in PULSE
    assert 'prompt_version="daily_agentic/v2"' in PULSE
    assert 'prompt_version="daily_agentic/v1"' not in PULSE


def test_agentic_v2_keeps_the_predictions_and_tools_contract_byte_identical():
    v1 = (ROOT / "config/prompts/analyst/daily_agentic_v1.md").read_text()
    v2 = (ROOT / "config/prompts/analyst/daily_agentic_v2.md").read_text()
    def span(t):
        return t[t.index("# Anchor questions"):t.index("# Output shape")]
    assert span(v1) == span(v2)
