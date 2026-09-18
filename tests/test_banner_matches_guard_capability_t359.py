"""tests/test_banner_matches_guard_capability_t359.py — the banner must match what the
guard CAN DO, probed behaviourally.

MY DEFECT, ONE LAYER DOWN. T-354's test asserted the coupling sentence was PRESENT — it
certified that we said it, and passed hardest exactly when the claim was false. E's
T-358 reframe fixed the sentence and added a negative assert on the old wording, which
is a real improvement but is still a TEXT check pinned to today's state of the world.

That leaves the MIRROR defect uncovered: when the approved phased build makes the guard
genuinely cross-account, every existing test still passes while the banner keeps saying
"SINGLE-ACCOUNT TODAY" — now understating a protection that exists. The text tests
cannot notice, because nothing ties them to the code's actual capability.

This test probes the FEED (per the standing lesson: verify a control by its feed, not
its construction): it writes a loss sale into a SIBLING account's ledger and asks
whether the guard can see it. Then it asserts the banner says whichever thing is TRUE.
It fails in BOTH directions — a false in-force claim today, and a stale pending claim
after the build lands.
"""
import datetime as dt

from engines.engine_b_risk.cross_account_wash_guard import (
    CrossAccountWashGuard, EquivalenceClasses, TaxLotLedger)
from intelligence.analyst import performance_digest as pdg

CLASSES = EquivalenceClasses({"US_LARGE_BLEND": ["SPY", "VOO"]}, version="test")


def _guard_sees_sibling_loss(tmp_path) -> bool:
    """Behavioural capability probe: account-1 takes a SPY loss; can an account-2
    guard see it when deciding a VOO buy (same wash class)?"""
    today = dt.date(2026, 9, 18)
    acct1 = TaxLotLedger(str(tmp_path / "acct1_lots.jsonl"))
    acct1.record_fill(account="acct1", symbol="SPY", side="buy", qty=10,
                      price=700.0, ts=today - dt.timedelta(days=30))
    acct1.record_fill(account="acct1", symbol="SPY", side="sell", qty=10,
                      price=600.0, ts=today - dt.timedelta(days=5))   # a LOSS sale

    acct2 = TaxLotLedger(str(tmp_path / "acct2_lots.jsonl"))          # its OWN ledger
    guard = CrossAccountWashGuard(ledger=acct2, classes=CLASSES)
    d = guard.check_order(account="acct2", symbol="VOO", side="buy", ts=today)
    return bool(getattr(d, "refused", False))


def test_the_banner_states_whichever_is_TRUE_of_the_guard(tmp_path):
    """The consistency check the text tests cannot make."""
    cross_account = _guard_sees_sibling_loss(tmp_path)
    banner = pdg.DEPLOY_CANDIDATE_FRAMING["coupling"]

    if cross_account:
        # the phased build has landed — the banner must STOP saying it is pending
        assert "SINGLE-ACCOUNT TODAY" not in banner, (
            "the guard now sees sibling lots, but the banner still calls the coupling "
            "pending — it is understating a protection that exists")
        assert "NOT" not in banner or "in force" not in banner
    else:
        # today's truth — the banner must NOT assert the protection as live
        assert "SINGLE-ACCOUNT TODAY" in banner
        assert "A rebalance here can be refused because of an account-1 loss" not in banner
        assert "INTENT" in banner or "intent" in banner


def test_the_probe_itself_is_honest_about_todays_answer(tmp_path):
    """Pin the CURRENT capability so a silent change to it is visible as a diff here,
    not discovered later through a wrong banner."""
    assert _guard_sees_sibling_loss(tmp_path) is False, (
        "the wash guard became cross-account — update the digest banner and this pin")


def test_the_guard_DOES_still_enforce_within_its_own_account(tmp_path):
    """Single-account is not the same as inert: the control that DOES exist must work,
    or 'single-account' would be overstating it in the other direction."""
    today = dt.date(2026, 9, 18)
    led = TaxLotLedger(str(tmp_path / "own_lots.jsonl"))
    led.record_fill(account="acct2", symbol="VOO", side="buy", qty=10,
                    price=700.0, ts=today - dt.timedelta(days=30))
    led.record_fill(account="acct2", symbol="VOO", side="sell", qty=10,
                    price=600.0, ts=today - dt.timedelta(days=5))     # own loss sale
    guard = CrossAccountWashGuard(ledger=led, classes=CLASSES)
    d = guard.check_order(account="acct2", symbol="VOO", side="buy", ts=today)
    assert d.refused is True, "the account's OWN 61-day rule must still bind"
