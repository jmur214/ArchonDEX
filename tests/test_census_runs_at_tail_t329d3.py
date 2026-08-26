# tests/test_census_runs_at_tail_t329d3.py
"""T-329d3 — the clock census must run at the TRUE tail of the daily run.

Found by the census's own first in-cloud emission (2026-08-26): it ran before
the intel pulse, shadow book, and news append, so five of its clocks measured
state their producing steps had not yet written and false-MISSED every day —
a permanent cry-wolf that would have gotten the census tuned away, which is
the exact failure T-338's design warns about.

These are source-order locks (the ordering is a property of the script, not of
any importable function), the same style as the repo's other caller greps.
"""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "scripts/run_paper_cloud_day.py").read_text()


def test_census_runs_after_every_step_it_measures():
    census = SRC.rindex("run_census(")
    for producer in ("run_intel_pulse(", "LlmShadowBook(", "append_today(",
                     "push_news_month("):
        assert SRC.index(producer) < census, (
            f"{producer} must run BEFORE the census that measures its artifact")


def test_channel_liveness_runs_after_the_shadow_book():
    assert SRC.index("LlmShadowBook(") < SRC.rindex("channel_liveness(")


def test_a_tail_push_persists_the_post_step5_heartbeat_blocks():
    """Steps 7/8 + the census mutate the heartbeat after the step-5 push; a
    second push must exist after them or their records die with the container
    (the S3 heartbeat carried no news block at all before this fix)."""
    tail_push = SRC.rindex("cloud.push()")
    assert SRC.rindex("run_census(") < tail_push
    assert SRC.rindex("push_news_month(") < tail_push


def test_the_tail_push_never_touches_canonical():
    tail = SRC[SRC.rindex("Tail heartbeat re-sync"):]
    assert "canonical = False" not in tail
