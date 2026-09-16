"""tests/test_family_tracker_durability_t351.py — T-351.

The T-350 tripwire asserted every LiveBook is durable AND clocked. It did not cover
FAMILY TRACKERS, and the identical failure happened one registry over: the deploy
candidate traded canonically from the 09-15 arrival event while its forward tracker was
written to the ephemeral container disk and discarded on every exit.

Nothing alarmed. The runs were clean, the fills real, the heartbeat green, `canonical:
true`. **A record that never accrues is indistinguishable from one that is merely young**
— which is exactly why this needs a mechanical check rather than an attentive reader.

The tracker filenames are spelled as literals at the strategy dispatch, so this reads them
from the source that actually decides them. That is deliberately the same grep-assertion
shape as T-348's: it cannot drift from the thing it is guarding, because it IS the thing
it is guarding.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.clock_census import EXEMPT, REGISTRY  # noqa: E402
from paper_trader.cloud_state import DURABLE_PATHS  # noqa: E402

PULSE = ROOT / "scripts/run_paper_cloud_day.py"
TRACKER_RE = re.compile(r'"tracker_file":\s*"([A-Za-z0-9_]+\.json)"')


def declared_trackers() -> set[str]:
    """Every tracker file the pulse can select, read from the dispatch itself."""
    return {f"data/state/{m}" for m in TRACKER_RE.findall(PULSE.read_text())}


def test_the_scan_finds_the_trackers_so_this_cannot_pass_vacuously():
    """A tripwire that scans nothing passes forever."""
    found = declared_trackers()
    assert len(found) >= 4, f"tracker scan collapsed to {found} — it is not scanning"
    assert "data/state/deploy_candidate_tracking.json" in found


def test_every_family_tracker_is_durable():
    """THE finding. A family tracker absent from DURABLE_PATHS is written to the
    ephemeral Fargate disk and thrown away on exit — the stream's forward record can
    never accrue, and no gate that waits on ">= N live records" can ever fire. It fails
    by looking permanently young."""
    missing = sorted(declared_trackers() - set(DURABLE_PATHS))
    assert not missing, (
        f"family trackers that evaporate on container exit: {missing}")


def test_every_family_tracker_is_clocked_or_exempted_with_a_reason():
    """Covered-or-exempted, extended to trackers. These are per-account files, so most
    are legitimately exempt — but the exemption must be STATED, because 'this file is
    empty in this container' and 'this clock is dead' look identical from here."""
    clocked = {p for c in REGISTRY for p in c.covers}
    for rel in sorted(declared_trackers()):
        assert rel in clocked or rel in EXEMPT, f"{rel} is neither clocked nor exempted"
        if rel in EXEMPT:
            assert len(EXEMPT[rel].strip()) > 20, f"{rel}'s exemption states no reason"


def test_the_deploy_candidate_tracker_specifically():
    """Named, because this is the one that was actually lost and the regression is worth
    pinning rather than leaving to the general rule above."""
    rel = "data/state/deploy_candidate_tracking.json"
    assert rel in DURABLE_PATHS
    assert rel in EXEMPT and "acct-2" in EXEMPT[rel]


def test_books_and_trackers_are_both_covered_so_neither_registry_is_the_gap():
    """T-350 closed this for books; the gap was that BOOKS were not the only registry.
    Assert both together so a third registry is the only way to reopen the class."""
    from paper_trader.live_books import ALL_BOOKS
    durable = set(DURABLE_PATHS)
    gaps = sorted([b.state_path for b in ALL_BOOKS if b.state_path not in durable]
                  + list(declared_trackers() - durable))
    assert not gaps, f"forward records that cannot accrue: {gaps}"
