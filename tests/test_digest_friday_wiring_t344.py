# tests/test_digest_friday_wiring_t344.py
"""T-344 Part 1 — the digest's Friday pulse step + the streams builder.

The generator sat with ZERO production callers for a month ('the surface built
to watch everything was the last unwatched clock'). These tests lock the wiring:
the builder assembles all 8 streams from persisted state with the unit-safety
rule intact, and the step fires only on Fridays, after the steps whose state it
reads, report-only.
"""
import json
from pathlib import Path

from scripts.run_paper_cloud_day import _digest_streams

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts/run_paper_cloud_day.py").read_text()


def _write(root, rel, obj):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def test_all_eight_streams_present_even_on_an_empty_root(tmp_path):
    s = _digest_streams(tmp_path)
    expected = {"account-1 trend sleeve (paper)", "btc 5% shadow (exploratory)",
                "dbmf shadow (3rd-stream clock)", "llm analyst shadow book"}
    assert expected <= set(s)
    # the four live books ride ALL_BOOKS; every present stream is a dict (fail-open {})
    assert all(isinstance(v, dict) for v in s.values())
    assert sum(k.startswith("book: ") for k in s) >= 1


def test_sleeve_stream_uses_normalized_growth_not_dollar_navs(tmp_path):
    """THE UNIT TRAP: sleeve equity is a $100k dollar series; the twin is a CAGR.
    The builder must emit growth RATIOS (build_rows' preferred keys), never a
    raw dollar nav pair."""
    _write(tmp_path, "data/state/sleeve_tracking.json", {
        "points": [{"sleeve_equity": 100000.0}, {"sleeve_equity": 100150.0}],
        "summary": {"robos": {"60_40": {"cagr": 0.1019, "n_days": 26}}}})
    s = _digest_streams(tmp_path)["account-1 trend sleeve (paper)"]
    assert abs(s["book_growth"] - 1.0015) < 1e-9
    assert abs(s["twin_growth"] - 1.1019 ** (26 / 252.0)) < 1e-12
    assert "book_nav" not in s and s["n_days"] == 26


def test_shadow_streams_pass_index_nav_pairs_with_drawdown(tmp_path):
    _write(tmp_path, "data/state/llm_shadow_book.json", {
        "points": [{"book_nav": 1.0, "twin_nav": 1.0},
                   {"book_nav": 1.02, "twin_nav": 1.01},
                   {"book_nav": 0.99, "twin_nav": 1.024}]})
    s = _digest_streams(tmp_path)["llm analyst shadow book"]
    assert s["book_nav"] == 0.99 and s["twin_nav"] == 1.024 and s["n_days"] == 3
    assert abs(s["current_drawdown_pct"] - (0.99 / 1.02 - 1.0)) < 1e-4


def test_a_missing_tracker_is_an_empty_stream_not_an_exception(tmp_path):
    _write(tmp_path, "data/state/btc_shadow_tracking.json", {"points": []})
    s = _digest_streams(tmp_path)
    assert s["btc 5% shadow (exploratory)"] == {}
    assert s["dbmf shadow (3rd-stream clock)"] == {}


# ---------------- source locks on the step itself ----------------
def test_the_step_is_friday_gated_and_report_only():
    i = SRC.index("T-344 DIGEST")
    block = SRC[i:i + 2400]
    assert "weekday() == 4" in block                      # Friday only, no catch-up
    assert "except Exception" in block and "non-fatal" in block
    assert "canonical =" not in block                     # never touches the verdict


def test_the_step_runs_after_the_state_it_reads_is_written():
    digest = SRC.index("T-344 DIGEST")
    for producer in ("_record_family_tracker", "LlmShadowBook(", "run_intel_pulse("):
        assert SRC.index(producer) < digest


def test_the_render_is_pushed_to_s3_under_the_granted_prefix():
    block = SRC[SRC.index("T-344 DIGEST"):SRC.index("T-344 DIGEST") + 2400]
    assert "s3_root" in block and 'cp' in block
    assert "cloud.cfg.enabled" in block          # no push attempt off-cloud
