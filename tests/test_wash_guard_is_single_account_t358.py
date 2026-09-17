# tests/test_wash_guard_is_single_account_t358.py
"""T-358 — the wash guard is SINGLE-ACCOUNT, and the record must say so.

Fresh-eyes audit finding A1 (2026-09-17), verified from the live artifacts
before anything was rewritten:

  * account-1 has NO `tax_lots.jsonl` under its prefix at all;
  * account-2's ledger holds 3 events, all its own (VOO/MTUM/SGOV), no SPY;
  * the guard's ledger is rooted at the CONTAINER's own prefix, and the only
    writer of lot events lives inside the guard, which only account-2 has.

Single-account twice over. Two surfaces asserted otherwise — a code comment at
the wiring site ("reads every account's lots… cross-account by design") and the
digest's "⚠ Coupled" banner ("can be refused because of an account-1 loss").

This is the T-342 channel-liveness class: has the consumed field EVER been
non-empty? Never. And it produced a wrong ANSWER, not just a dormant channel —
drill 12's silence was reported as "account-1 evidently had no SPY loss in the
window", a plausible cause for an absence whose real cause was an unfed channel.

These tests lock the HONEST statement so the claim cannot drift back before the
mechanism exists.
"""
from __future__ import annotations

import inspect

from intelligence.analyst.performance_digest import DEPLOY_CANDIDATE_FRAMING


def test_the_digest_banner_does_not_claim_a_protection_that_is_not_wired():
    """The banner is placed above the table so it cannot be read after the
    number — which makes a false banner worse than none."""
    c = DEPLOY_CANDIDATE_FRAMING["coupling"]
    assert "SINGLE-ACCOUNT TODAY" in c
    assert "NOT" in c and "in force" in c
    # the old false assertion, in its exact load-bearing form
    assert "A rebalance here can be refused because of an account-1 loss" not in c


def test_the_intent_is_still_on_the_record_not_deleted():
    """Correcting a false claim must not erase the real plan — otherwise the
    next reader rebuilds the coupling thinking nobody considered it."""
    c = DEPLOY_CANDIDATE_FRAMING["coupling"]
    assert "US_LARGE_BLEND" in c and "INTENT" in c


def test_the_wiring_site_states_single_account_and_why():
    """The comment a future maintainer meets before the guard is constructed."""
    import scripts.run_paper_cloud_day as drv
    src = inspect.getsource(drv)
    assert "IT IS NOT CROSS-ACCOUNT YET" in src
    assert "cross-account by design" not in src, "the false claim is back"


def test_only_the_guarded_strategy_can_write_lots_which_is_the_root_cause():
    """The mechanism, asserted so the fix can be recognised when it lands: lots
    are written only inside the guard, and only one strategy carries one."""
    from scripts.run_paper_cloud_day import WASH_GUARDED_STRATEGIES
    assert WASH_GUARDED_STRATEGIES == {"deploy_candidate"}, (
        "if this grew, re-check whether the guard is still single-account — the "
        "ledger path is still the container's own prefix either way")
