# tests/test_redeploy_one_account_t350g.py
"""T-350g — the two guards on the single-account redeploy path.

Both guard against failures that have already cost this program real days, so
they are locked rather than trusted:

* the STRANDED FIX (2026-07-28) — a re-render silently reverts hand-fixes, so
  the new revision must differ from LIVE in the image and nothing else;
* the REVISIONLESS ARN (the 2026-07-13→24 two-week silent outage) — a bare
  jobdef ARN fails the scheduler role's `:*` IAM pattern and every submit
  AccessDenies with nothing surfaced.
"""
from __future__ import annotations

import pytest

import scripts.redeploy_one_account as r

NEW = "407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:paper-sha-newsha"

LIVE = {
    "jobDefinitionName": "archondex-paper-offense-sso",
    "jobDefinitionArn": "arn:aws:batch:us-east-1:407539788432:job-definition/"
                        "archondex-paper-offense-sso:17",
    "revision": 17, "status": "ACTIVE", "type": "container",
    "containerProperties": {
        "image": "…/archondex-backtest:paper-sha-oldsha",
        "environment": [{"name": "ARCHONDEX_PAPER_STRATEGY",
                         "value": "deploy_candidate"},
                        {"name": "ARCHONDEX_SLEEVE_NOTIONAL_CAP",
                         "value": "10000"}],
        "vcpus": 2, "memory": 4096},
    # the hand-applied fix that a template re-render would strand
    "retryStrategy": {"attempts": 2, "evaluateOnExit": [
        {"onStatusReason": "CannotPullContainerError*", "action": "retry"},
        {"onExitCode": "*", "action": "exit"}]},
}


def test_the_clone_carries_the_handapplied_retry_strategy_forward():
    """The infra-only retry is exactly the kind of fix a re-render strands."""
    reg = r.clone_with_image(LIVE, NEW)
    assert reg["retryStrategy"] == LIVE["retryStrategy"]
    assert reg["containerProperties"]["environment"] == \
        LIVE["containerProperties"]["environment"]
    assert reg["containerProperties"]["image"] == NEW


def test_image_only_diff_PASSES_for_an_honest_clone():
    r.assert_image_only(LIVE, r.clone_with_image(LIVE, NEW), NEW)


def test_a_clone_that_drops_the_retry_strategy_is_REFUSED(capsys):
    """The guard must catch the silent loss, not just the loud one."""
    bad = r.clone_with_image(LIVE, NEW)
    del bad["retryStrategy"]
    with pytest.raises(SystemExit):
        r.assert_image_only(LIVE, bad, NEW)


def test_a_clone_that_changes_the_notional_cap_is_REFUSED():
    """An env drift here is the notional-cap bypass class arriving via infra."""
    bad = r.clone_with_image(LIVE, NEW)
    bad["containerProperties"]["environment"][1]["value"] = "100000"
    with pytest.raises(SystemExit):
        r.assert_image_only(LIVE, bad, NEW)


def test_a_revisionless_jobdef_ARN_is_REFUSED(monkeypatch):
    """The two-week-outage guard: repoint must never write a bare ARN."""
    monkeypatch.setattr(r, "aws", lambda *a: pytest.fail("must refuse BEFORE any call"))
    with pytest.raises(SystemExit) as e:
        r.repoint("archondex-paper-offense-sso-daily",
                  "arn:aws:batch:us-east-1:407539788432:job-definition/"
                  "archondex-paper-offense-sso", execute=True)
    assert "revision-pinned" in str(e.value)
