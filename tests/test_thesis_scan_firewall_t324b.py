"""T-324b — the BIAS FIREWALL + the blind-scan experiment. Synthetic fixtures only.

The load-bearing assertion: a user-seeded thesis can NEVER reach the machine generator's context. The guard
is fail-closed, so a future refactor that widens retrieval trips a test rather than silently biasing the
machine's record. Both channels are scored identically; only GENERATION is isolated.
"""
import json

import pytest

from intelligence.thesis_desk.thesis_scan import (FirewallBreach, assert_bundle_is_blind, build_scan_bundle,
                                                  due, load_machine_theses, load_user_seed_fingerprints,
                                                  record_scan, scan_provenance, seeds_are_held)

USER_NARRATIVE = "Synthetic user seed: the physical supply chain is the binding constraint on the buildout."


def _ledger(tmp_path, rows):
    p = tmp_path / "thesis_calls.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _inbox(tmp_path, text=""):
    p = tmp_path / "thesis_inbox.md"; p.write_text(text); return p


# ---- the namespace split ----
def test_generator_sees_only_machine_theses(tmp_path):
    led = _ledger(tmp_path, [
        {"thesis_id": "m1", "origin": "machine", "theme_class": "tech_inflection", "as_of": "2026-07-01"},
        {"thesis_id": "u1", "origin": "user_seeded", "theme_class": "picks_and_shovels",
         "as_of": "2026-07-02", "narrative": USER_NARRATIVE},
    ])
    got = load_machine_theses(led)
    assert [t["thesis_id"] for t in got] == ["m1"], "user-seeded theses must be invisible to the generator"


def test_bundle_excludes_user_theses_and_passes_the_firewall(tmp_path):
    led = _ledger(tmp_path, [
        {"thesis_id": "m1", "origin": "machine", "theme_class": "tech_inflection", "as_of": "2026-07-01"},
        {"thesis_id": "u1", "origin": "user_seeded", "as_of": "2026-07-02", "narrative": USER_NARRATIVE},
    ])
    b = build_scan_bundle("2026-07-28", news=[{"headline": "synthetic macro item"}], ledger=led,
                          assert_blind=False)
    assert [t["thesis_id"] for t in b["prior_machine_theses"]] == ["m1"]
    assert_bundle_is_blind(b, fingerprints=[USER_NARRATIVE, "u1"])          # must NOT raise


# ---- fail-closed: a leak RAISES ----
def test_leaked_user_narrative_raises(tmp_path):
    b = build_scan_bundle("2026-07-28", news=[{"headline": USER_NARRATIVE}], ledger=_ledger(tmp_path, []),
                          assert_blind=False)
    with pytest.raises(FirewallBreach, match="BIAS FIREWALL"):
        assert_bundle_is_blind(b, fingerprints=[USER_NARRATIVE])


def test_leaked_user_thesis_in_prior_list_raises(tmp_path):
    b = build_scan_bundle("2026-07-28", ledger=_ledger(tmp_path, []), assert_blind=False)
    b["prior_machine_theses"].append({"thesis_id": "u1", "origin": "user_seeded"})
    with pytest.raises(FirewallBreach):
        assert_bundle_is_blind(b, fingerprints=[])


def test_fingerprints_pick_up_both_ledger_and_inbox(tmp_path):
    led = _ledger(tmp_path, [{"thesis_id": "u1", "origin": "user_seeded", "narrative": USER_NARRATIVE}])
    inbox = _inbox(tmp_path, "## Synthetic seeded theme\nA distinctive synthetic narrative line for matching.\n")
    fps = load_user_seed_fingerprints(led, inbox)
    assert any(USER_NARRATIVE[:40] in f for f in fps)
    assert any("distinctive synthetic narrative" in f.lower() for f in fps)


# ---- the blind-scan experiment: sequencing + provenance ----
def test_seeds_are_held_until_the_first_blind_scan(tmp_path):
    st = tmp_path / "scan_state.json"
    assert seeds_are_held(st) is True                       # nothing scanned yet -> seeds held UNFILED
    record_scan("2026-07-28", n_theses=3, path=st)
    assert seeds_are_held(st) is False                      # first blind scan done -> both may file


def test_provenance_stamps_the_blind_ordinal_and_seed_context(tmp_path):
    st = tmp_path / "scan_state.json"
    inbox = _inbox(tmp_path, "## Synthetic seeded theme\nSynthetic narrative.\n")
    p = scan_provenance("2026-07-28", path=st, inbox=inbox)
    assert p["blind_scan_ordinal"] == 1 and p["is_first_blind_scan"] is True
    assert p["seeds_existed_at_scan_time"] == ["synthetic_seeded_theme"]     # provable blindness
    assert p["firewall_asserted"] is True
    record_scan("2026-07-28", n_theses=2, path=st)
    p2 = scan_provenance("2026-08-04", path=st, inbox=inbox)
    assert p2["blind_scan_ordinal"] == 2 and p2["is_first_blind_scan"] is False


# ---- cadence: the PRIMARY engine runs weekly ----
def test_weekly_cadence(tmp_path):
    st = tmp_path / "scan_state.json"
    assert due("2026-07-28", path=st) is True               # never run -> due
    record_scan("2026-07-28", n_theses=1, path=st)
    assert due("2026-08-01", path=st) is False              # 4 days later -> not due
    assert due("2026-08-04", path=st) is True               # 7 days later -> due
