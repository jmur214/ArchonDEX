"""tests/test_reconstructed_point_policy_t352.py — T-352.

The director referred the 09-15/16 deploy-candidate gap back to me: E showed the points
are RECONSTRUCTIBLE (the durable ledger carries shares and cash; closes are fetchable), so
my earlier "permanent holes" claim was wrong and is retracted. The decision was mine.

These lock the ruling and, more importantly, the REASON — a rule whose reason is not
recorded gets re-litigated by whoever finds the ledger next.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.live_books import RECONSTRUCTED_POINT_POLICY as P  # noqa: E402


def test_we_do_not_reconstruct():
    assert P["reconstruct"] is False


def test_the_reason_is_the_EXEC_HALF_not_a_style_preference():
    """The decisive fact, kept in the record: a ledger replay rebuilds the NAV half only.
    slippage_bps needs an arrival price captured at execution; `canonical` is a verdict a
    run reaches about itself. Neither survives the run that was not recorded."""
    why = P["why"]
    assert "slippage_bps" in why and "canonical" in why
    assert "NAV-real and exec-absent" in why


def test_a_reconstructed_point_would_have_to_be_labelled_and_unblended():
    """The constraint holds even though we declined — a future ruling may differ, and the
    label rule must already be on the record when it does."""
    r = P["if_ever_reconstructed"]
    assert "reconstructed" in r and "never blend" in r


def test_reconstructed_days_do_not_count_toward_the_evaluable_gate():
    assert P["counts_toward_evaluable_gate"] is False


def test_the_gate_reason_is_the_ROBO_PAIRED_definition_not_merely_strictness():
    """Why this matters: 'the gate proves live operation' is a preference someone can
    argue with. 'The digest counts robo-paired evaluable days and this point has no
    execution half' is a category error, which they cannot."""
    g = P["gate_reason"]
    assert "robo" in g.lower() and "evaluable" in g


def test_the_ruling_is_dated_so_it_can_be_superseded_knowingly():
    assert "2026-09-18" in P["ruled"]


# ---------- the cash_rate channel: a zero that means NEVER MEASURED ----------
import json  # noqa: E402

from paper_trader.clock_census import (  # noqa: E402
    CHANNELS, LIVE, NEVER_ALIVE, NO_HISTORY, UNVERIFIABLE, _scan_points_field)


def _tracker(tmp_path, rel, pts):
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"points": pts}))
    return tmp_path


def test_a_never_written_annotation_reads_NEVER_ALIVE_not_a_measured_zero(tmp_path):
    """THE finding. `cash_rate` has no call site in the pulse, so `cash_adj` was never
    written on any point of any account — and the summary then reports an accrual of
    exactly 0. That zero is indistinguishable from a real, correctly-measured zero, which
    is precisely why it needed an existence-over-history assertion and not a freshness
    check."""
    root = _tracker(tmp_path, "data/state/sleeve_tracking.json",
                    [{"date": f"2026-09-{d:02d}"} for d in range(1, 12)])
    status, detail = _scan_points_field("data/state/sleeve_tracking.json", "cash_adj")(root)
    assert status == NEVER_ALIVE
    assert "NEVER MEASURED" in detail and "11 point" in detail


def test_one_fed_point_is_enough_to_read_LIVE(tmp_path):
    """The check asserts EXISTENCE over history, not freshness — one real accrual ever
    is the whole bar, because the question is 'has this channel ever carried anything'."""
    root = _tracker(tmp_path, "data/state/sleeve_tracking.json",
                    [{"date": "2026-09-01"},
                     {"date": "2026-09-02", "cash_adj": {"day_accrual": 0.01}}])
    status, _ = _scan_points_field("data/state/sleeve_tracking.json", "cash_adj")(root)
    assert status == LIVE


def test_an_empty_tracker_is_NO_HISTORY_not_NEVER_ALIVE(tmp_path):
    """A brand-new tracker must not cry wolf — the distinction that kept T-342 from
    being tuned away."""
    root = _tracker(tmp_path, "data/state/sleeve_tracking.json", [])
    status, _ = _scan_points_field("data/state/sleeve_tracking.json", "cash_adj")(root)
    assert status == NO_HISTORY


def test_a_missing_tracker_is_UNVERIFIABLE_never_assumed_alive(tmp_path):
    status, _ = _scan_points_field("data/state/sleeve_tracking.json", "cash_adj")(tmp_path)
    assert status == UNVERIFIABLE


def test_both_family_trackers_are_registered_as_consumers():
    """Registered per consumer so the dead channel is visible rather than silent. Whether
    to FEED it or RETIRE it is the tracker owner's call — this only refuses the silence."""
    rows = {(c.consumer, c.name) for c in CHANNELS}
    assert ("family_tracker(trend_sleeve)", "cash_rate") in rows
    assert ("family_tracker(deploy_candidate)", "cash_rate") in rows
