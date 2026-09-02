# tests/test_scan_evidence_floor_t327.py
"""T-327 drill-6 collateral: the scan must REFUSE TO CALL on a starved bundle.

The injected news fault (drill 6) starved the scan bundle to n_documents=0 and
the scan called the model anyway — n_docs existed only in the post-hoc reason
classification, never as a call gate — and the model filed a prior-recitation
(evidence-free near-duplicate of an open basket; quarantined same day).
The desk failed UNSAFE on input starvation; this guard is the fix's first half
(D's evidence-floor v2 owns the deeper threshold + duplicate detection)."""
from intelligence.thesis_desk.thesis_scan_runner import (
    MIN_SCAN_DOCUMENTS, run_blind_scan)


class _MustNotBeCalled:
    def __call__(self, *a, **k):
        raise AssertionError("the model was CALLED on a starved bundle")


class _Gov:
    def check(self, month, cost):
        raise AssertionError("the governor ran before the evidence floor — "
                             "the floor must refuse before anything spends")


def test_zero_document_bundle_never_reaches_the_model(tmp_path):
    r = run_blind_scan(
        "2026-09-02", model_call=_MustNotBeCalled(), governor=_Gov(),
        model_id_requested="m", prompt_version="scan/v1", projected_cost_usd=0.3,
        raw_dir=str(tmp_path), prompt_path="config/prompts/analyst/weekly_v1.md",
        news=[], events=[],
        ledger=tmp_path / "l.jsonl", scan_state=tmp_path / "s.json",
        prov_log=tmp_path / "p.jsonl", inbox=tmp_path / "i.md")
    assert r.reason == "empty_bundle"
    assert "evidence_floor" in (r.skip_reason or "")
    assert r.n_documents == 0
    # clean skip: the scan was NOT recorded, so the cadence retries when the tape returns
    assert not (tmp_path / "s.json").exists()


def test_the_floor_is_a_named_constant_not_a_magic_number():
    assert MIN_SCAN_DOCUMENTS >= 1
