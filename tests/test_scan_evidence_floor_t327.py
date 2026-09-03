# tests/test_scan_evidence_floor_t327.py
"""T-327 drill-6 collateral: the scan must REFUSE TO CALL on a starved bundle —
but NEVER at the cost of swallowing a firewall breach.

Two defects, one ordering:

1. The original bug (drill-6 collateral, 2026-09-02): the injected news fault
   starved the bundle to n_documents=0 and the scan called the model anyway —
   n_docs existed only in the post-hoc reason classification, never as a call
   gate — and the model filed a prior-recitation (evidence-free near-duplicate
   of an open basket; quarantined same day). The desk failed UNSAFE on input
   starvation.

2. B's catch on the first fix, same day: the floor shipped ABOVE the bundle
   build, so a POISONED-BUT-THIN bundle would clean-skip instead of raising —
   a fail-open skip swallowing the one fail-CLOSED check in a fail-open pulse.
   **A breach always out-ranks a skip.**
"""
import datetime as dt
import json

import pytest

from intelligence.thesis_desk.thesis_scan import FirewallBreach
from intelligence.thesis_desk.thesis_scan_runner import (
    MIN_SCAN_DOCUMENTS, run_blind_scan)

TODAY = dt.date(2026, 9, 2)
AS_OF = "2026-09-02"
LEAK = "the user's own picks-and-shovels seed narrative, verbatim"


class _MustNotBeCalled:
    def __call__(self, *a, **k):
        raise AssertionError("the model was CALLED on a starved bundle")


class _Gov:
    """Allows spend — so a skip in these tests can only come from the floor."""
    def check(self, month, cost):
        return type("D", (), {"allowed": True, "reason": "ok",
                              "max_output_tokens": 4000})()


def _run(tmp_path, **kw):
    return run_blind_scan(
        AS_OF, model_call=_MustNotBeCalled(), governor=_Gov(),
        model_id_requested="m", prompt_version="scan/v1", projected_cost_usd=0.3,
        raw_dir=str(tmp_path), prompt_path="config/prompts/analyst/weekly_v1.md",
        ledger=kw.pop("ledger", tmp_path / "l.jsonl"),
        scan_state=tmp_path / "s.json", prov_log=tmp_path / "p.jsonl",
        inbox=tmp_path / "i.md", today=TODAY, **kw)


def test_zero_document_bundle_never_reaches_the_model(tmp_path):
    r = _run(tmp_path, news=[], events=[])
    assert r.reason == "empty_bundle"
    assert "evidence_floor" in (r.skip_reason or "")
    assert r.n_documents == 0
    # clean skip: the scan was NOT recorded, so the cadence retries when the tape returns
    assert not (tmp_path / "s.json").exists()
    # ...but the zero still EXPLAINS ITSELF (T-325): the provenance row is written,
    # naming the floor. Explaining a zero and advancing the clock are separate acts.
    prov = (tmp_path / "p.jsonl").read_text()
    assert '"reason": "empty_bundle"' in prov and '"n_documents": 0' in prov
    assert "evidence_floor" in prov and '"call_made": false' in prov


def _seed_the_firewall(monkeypatch):
    """Point the firewall's fingerprint source at a known seed.

    NB (flagged to D, NOT a live defect): ``build_scan_bundle(ledger=X)`` uses X
    for ``prior_machine_theses`` but calls ``assert_bundle_is_blind(bundle)`` with
    no ledger, so the firewall always reads the DEFAULT production ledger. In
    production both are the same path so nothing is wrong; it does mean a scoped
    ledger cannot scope the firewall, which is why this patches the loader.
    """
    from intelligence.thesis_desk import thesis_scan as ts
    monkeypatch.setattr(ts, "load_user_seed_fingerprints", lambda *a, **k: [LEAK])


def test_a_poisoned_bundle_RAISES_even_when_it_is_also_thin(tmp_path, monkeypatch):
    """THE ORDERING LOCK (B's catch). The firewall is the one fail-CLOSED check in
    a fail-open pulse: a build bug that leaked a user seed must propagate, never be
    masked by the thin-bundle skip that happens to be true at the same moment.
    Under the first (buggy) ordering this returned a clean skip."""
    _seed_the_firewall(monkeypatch)
    with pytest.raises(FirewallBreach):
        _run(tmp_path, news=[], events=[], universe_hint=[LEAK])


def test_a_clean_thin_bundle_still_skips_with_the_firewall_armed(tmp_path, monkeypatch):
    """The mirror of the lock: firewall armed with the same fingerprint but the
    bundle clean — so the raise above is the BREACH, not merely an armed firewall."""
    _seed_the_firewall(monkeypatch)
    r = _run(tmp_path, news=[], events=[])
    assert r.reason == "empty_bundle" and "evidence_floor" in (r.skip_reason or "")


def test_the_floor_is_a_named_constant_not_a_magic_number():
    assert MIN_SCAN_DOCUMENTS >= 1
