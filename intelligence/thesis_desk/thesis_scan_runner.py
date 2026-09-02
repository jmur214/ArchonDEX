"""T-325 #4 — the E-side ORCHESTRATOR for the machine-originated thematic scan.

D (T-324b) built the desk's *contract*: `build_scan_bundle` (blind, firewall-asserted),
`scan_provenance`, `record_scan`, `due`, `seeds_are_held`, `file_thesis`, and the
`thesis_call/v1` schema. What was missing is the seat that turns a blind bundle into
*filed theses*: the strong-tier LLM call + the same governor/provenance/validation
pipeline the analyst uses (`run_daily_note`). That is this module.

TWO entry points, both fail-closed, both mirroring the analyst pipeline exactly:

  * ``run_blind_scan`` — the PRIMARY engine. It assembles the generator's context ONLY
    through D's ``build_scan_bundle`` (never hand-assembled: hand-assembly would silently
    lose blindness, and ``assert_bundle_is_blind`` inside ``build_scan_bundle`` is what
    guarantees the generator never sees a user seed). It runs ONE strong-tier call, stamps
    provenance, re-validates every thesis locally (``file_thesis`` → ``validate_thesis_call``),
    files the valid ones as ``origin="machine"``, and calls ``record_scan`` — which RELEASES
    the blind-scan hold (``seeds_are_held`` flips False once ``scans > 0``).

  * ``run_seed_thesis`` — the user-seeded channel (LOW-PRIORITY, firewalled). Runs ONLY
    after the first blind scan has released the hold. Researches ONE user seed across the
    same machine-visible context and files a ``origin="user_seeded"`` thesis, later-dated.

THE FIREWALL IS D'S, NOT MINE: I call ``build_scan_bundle`` and let ``FirewallBreach``
propagate. A breach means our own machine-visible data leaked user-seed material — a build
bug, not a data condition — so it must HALT loudly (`[NN-FAIL-CLOSED]`), never be swallowed
into a clean skip. The pulse wrapper reports the breach; it NEVER files on one.

Forward-only by necessity (`[NN-AI-GATE]`): ``assert_forward_only`` refuses any as_of
materially in the past — a backtested thesis is memorization, not judgement.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from intelligence.analyst.cost_governor import CostGovernor
from intelligence.thesis_desk.thesis_desk import (THESIS_INBOX, THESIS_LEDGER, ModelCall,
                                                  assert_forward_only, build_seed_bundle,
                                                  file_thesis, load_filed, load_seeds)
from intelligence.thesis_desk.thesis_scan import (SCAN_STATE, build_scan_bundle, due,
                                                  record_scan, scan_provenance, seeds_are_held)

# the auditable blindness record — one line per scan, DURABLE (rides S3). This is what
# makes "the first scan was provably blind" a checkable artifact, not a claim.
SCAN_PROV_LOG = SCAN_STATE.parent / "thesis_scan_provenance.jsonl"
# T-327 (drill-6 collateral): the scan EVIDENCE FLOOR — below this the model is
# never called (a generator with no documents has nothing to generalize from).
# 1 restores the refuse-literally-empty intent; D's evidence-floor v2 owns more.
MIN_SCAN_DOCUMENTS = 1


# ---------------- results ----------------
@dataclass
class BlindScanResult:
    filed: List[dict] = field(default_factory=list)          # filed machine thesis records
    rejected: List[dict] = field(default_factory=list)       # {index, reason} — validation failures
    provenance: Optional[dict] = None                        # scan_provenance stamp (blindness audit)
    skip_reason: Optional[str] = None                        # non-None ⇒ NO call happened / NO scan recorded
    raw_path: Optional[str] = None
    n_theses_seen: int = 0
    # T-325 (post-Wed): a zero-thesis scan must be SELF-EXPLAINING. '0 filed' with no
    # stated why is the silent-wrongness class — these make every zero unambiguous.
    n_documents: int = 0            # news + event docs the generator actually saw
    bundle_bytes: int = 0           # size of the JSON bundle handed to the model
    reason: Optional[str] = None    # filed | empty_bundle | model_declined | unparseable_response | call_skipped | call_failed

    @property
    def scanned(self) -> bool:
        """True iff a scan actually COMPLETED (call succeeded, parsed, record_scan ran)."""
        return self.skip_reason is None


@dataclass
class SeedThesisResult:
    filed: Optional[dict] = None
    skip_reason: Optional[str] = None
    reason: Optional[str] = None                              # validation reason when not filed
    raw_path: Optional[str] = None


# ---------------- helpers ----------------
def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _prompt(prompt_path: str) -> "tuple[str, str]":
    text = pathlib.Path(prompt_path).read_text()
    return text, _sha256(text)


def _lenient(text: str) -> Any:
    # reuse the ONE shared robust-parse helper (strip fence, skip leading prose, raw_decode)
    from intelligence.analyst.analyst_service import _loads_lenient
    return _loads_lenient(text)


def _slug(s: str, n: int = 40) -> str:
    return "".join(c if (c.isalnum() or c in "-_") else "-" for c in str(s).lower())[:n].strip("-") or "x"


def _stamp(thesis: dict, *, origin: str, as_of: str, resp: dict, bundle_sha: str,
           prompt_sha: str, model_id_requested: str, prompt_version: str,
           usage: dict, attribute_usage: bool, thesis_id: str) -> dict:
    """Stamp the machine-owned fields onto a raw model thesis. The model NEVER supplies
    provenance/usage/origin/schema_version/thesis_id — we do, so they cannot be forged in the
    body and the thesis_id is DETERMINISTIC (so filing is idempotent across re-runs)."""
    thesis = dict(thesis)
    thesis["schema_version"] = "thesis_call/v1"
    thesis["origin"] = origin
    thesis["as_of"] = as_of
    thesis["thesis_id"] = thesis_id[:96]
    thesis.setdefault("suspected_prompt_injection", bool(thesis.get("suspected_prompt_injection", False)))
    thesis["provenance"] = {
        "model_id_requested": model_id_requested,
        "model_id_served": str(resp.get("model_id_served", model_id_requested)),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "input_bundle_sha256": bundle_sha,
    }
    # usage is per-CALL; attribute the real cost/tokens to the FIRST filed thesis only so
    # summing per-thesis usage reconstructs the one call's cost (the rest carry zeros).
    thesis["usage"] = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0) if attribute_usage else 0,
        "output_tokens": int(usage.get("output_tokens", 0) or 0) if attribute_usage else 0,
        "cost_usd": float(usage.get("cost_usd", 0.0) or 0.0) if attribute_usage else 0.0,
    }
    return thesis


def _archive_raw(raw_dir: str, tag: str, as_of: str, resp: dict, bundle_sha: str) -> str:
    d = pathlib.Path(raw_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"raw_{tag}_{as_of}.json"
    p.write_text(json.dumps({"as_of": as_of, "response": resp.get("text", ""),
                             "model_id_served": resp.get("model_id_served"),
                             "input_bundle_sha256": bundle_sha}, default=str))
    return str(p)


# ---------------- the primary engine ----------------
def run_blind_scan(as_of: str, *, model_call: ModelCall, governor: CostGovernor,
                   model_id_requested: str, prompt_version: str, projected_cost_usd: float,
                   raw_dir: str, prompt_path: str, max_output_tokens: int = 4000,
                   news: Optional[list] = None, events: Optional[list] = None,
                   rate_path: Optional[dict] = None, universe_hint: Optional[list] = None,
                   ledger: pathlib.Path = THESIS_LEDGER, scan_state: pathlib.Path = SCAN_STATE,
                   prov_log: pathlib.Path = SCAN_PROV_LOG, inbox: pathlib.Path = THESIS_INBOX,
                   now_iso: str = "1970-01-01T00:00:00", today=None) -> BlindScanResult:
    """Run the machine's blind thematic scan. FAIL-CLOSED: a governor refusal or a model
    error is a clean skip (no scan recorded, hold NOT released); a ``FirewallBreach`` PROPAGATES."""
    month = str(now_iso)[:7]
    n_docs = len(news or []) + len(events or [])     # what the generator actually sees

    # 0. THE EVIDENCE FLOOR (T-327 drill-6 collateral, 2026-09-02): n_docs was
    # computed here and then used only for the POST-HOC reason classification —
    # the call itself was never gated. When the injected news fault starved the
    # tape, the scan called the model on 822 bytes of non-news context and it
    # FILED A PRIOR-RECITATION (evidence-free near-duplicate of an open basket;
    # quarantined same day). Refusing the call is the only honest output. Same
    # clean-skip shape as a governor refusal: no spend, no record_scan — the scan
    # stays due and retries when the tape returns.
    if n_docs < MIN_SCAN_DOCUMENTS:
        return BlindScanResult(
            skip_reason=f"skipped:evidence_floor:n_documents={n_docs}<{MIN_SCAN_DOCUMENTS}",
            reason="empty_bundle", n_documents=n_docs)

    # 1. governor / kill switch — no call on refusal
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return BlindScanResult(skip_reason=f"skipped:{decision.reason}",
                               reason="call_skipped", n_documents=n_docs)

    # 2. forward-only guard BEFORE spending anything ([NN-AI-GATE]) — same as_of for all theses
    assert_forward_only(as_of, today=today)

    # 3. THE BLIND BUNDLE — assembled ONLY through D's builder, which asserts the firewall.
    # A FirewallBreach here is a BUILD BUG (our own data leaked a user seed) — let it raise.
    bundle = build_scan_bundle(as_of, news=news, events=events, rate_path=rate_path,
                               universe_hint=universe_hint, ledger=ledger)
    prov = scan_provenance(as_of, path=scan_state, inbox=inbox)   # stamp blindness BEFORE the call
    bundle_json = _canonical_json(bundle)
    bundle_bytes = len(bundle_json.encode("utf-8"))
    bundle_sha = _sha256(bundle_json)
    prompt_text, prompt_sha = _prompt(prompt_path)

    # 4. ONE strong-tier call; raw always archived; spend recorded regardless of validity.
    # Use the SCAN's own token budget, NOT the governor's daily cap: intel_pulse builds the
    # shared governor with max_output_tokens=1500 (a daily-note bound), which TRUNCATED the
    # strong-tier scan's multi-thesis response mid-JSON → not_json, 0 filed (the Aug 12 defect;
    # a 2-thesis reply needs ~2300 tokens). The governor still gates COST (the real budget guard).
    try:
        resp = model_call(prompt_text, bundle_json, max_output_tokens)
    except Exception as e:   # noqa: BLE001
        return BlindScanResult(skip_reason=f"skipped:model_call_error:{type(e).__name__}",
                               provenance=prov, reason="call_failed",
                               n_documents=n_docs, bundle_bytes=bundle_bytes)
    raw_path = _archive_raw(raw_dir, "scan", as_of, resp, bundle_sha)
    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    # 5. parse → expect {"theses": [...]}. A parse failure is a completed-but-empty scan
    # (the call happened, spend recorded); we still record_scan so the cadence advances.
    filed: List[dict] = []
    rejected: List[dict] = []
    parse_failed = False
    try:
        payload = _lenient(resp.get("text", ""))
        raw_theses = payload.get("theses", []) if isinstance(payload, dict) else []
        if not isinstance(raw_theses, list):
            raw_theses = []
    except Exception:
        raw_theses = []
        parse_failed = True
        # keep a snippet so a parse failure is diagnosable even if the raw is unavailable
        _txt = str(resp.get("text", ""))
        rejected.append({"index": -1, "reason": "not_json",
                         "resp_len": len(_txt), "resp_tail": _txt[-120:]})

    # 6. stamp + re-validate + file each thesis (bad thesis ⇒ NOT filed, never crashes the scan)
    for i, raw in enumerate(raw_theses):
        if not isinstance(raw, dict):
            rejected.append({"index": i, "reason": "not_an_object"})
            continue
        # deterministic id: namespaced by as_of so a re-run of the SAME scan-day re-files
        # the SAME ids (idempotent), and two scan-days never collide.
        mid = f"m-{as_of}-{_slug(raw.get('thesis_id') or raw.get('theme_class') or i)}"
        payload_i = _stamp(raw, origin="machine", as_of=as_of, resp=resp, bundle_sha=bundle_sha,
                           prompt_sha=prompt_sha, model_id_requested=model_id_requested,
                           prompt_version=prompt_version, usage=usage,
                           attribute_usage=(len(filed) == 0),   # real usage on the first FILED thesis
                           thesis_id=mid)
        rec, err = file_thesis(payload_i, ledger=ledger)
        if rec is None:
            rejected.append({"index": i, "reason": err})
        else:
            filed.append(rec)

    # 7. classify the OUTCOME so a zero is never ambiguous (the self-explaining rule):
    #    filed>0 → filed; parse failure → unparseable_response (NOT a decline — a real tape
    #    whose reply didn't parse, e.g. token-truncated: the Aug 12 defect); empty_bundle if
    #    the generator saw nothing; else model_declined (a real tape, an honest empty return).
    if filed:
        reason = "filed"
    elif parse_failed:
        reason = "unparseable_response"
    elif n_docs == 0:
        reason = "empty_bundle"
    else:
        reason = "model_declined"

    # 8. record the scan (releases the blind-scan hold) + append the blindness audit line
    record_scan(as_of, n_theses=len(filed), path=scan_state)
    prov_log.parent.mkdir(parents=True, exist_ok=True)
    with prov_log.open("a") as fh:
        fh.write(json.dumps({**prov, "n_filed": len(filed), "n_rejected": len(rejected),
                             "n_theses_seen": len(raw_theses), "n_documents": n_docs,
                             "bundle_bytes": bundle_bytes, "reason": reason},
                            default=str) + "\n")

    return BlindScanResult(filed=filed, rejected=rejected, provenance=prov,
                           raw_path=raw_path, n_theses_seen=len(raw_theses),
                           n_documents=n_docs, bundle_bytes=bundle_bytes, reason=reason)


# ---------------- the user-seeded channel ----------------
def run_seed_thesis(seed, as_of: str, *, model_call: ModelCall, governor: CostGovernor,
                    model_id_requested: str, prompt_version: str, projected_cost_usd: float,
                    raw_dir: str, prompt_path: str, max_output_tokens: int = 4000,
                    research_context: Optional[dict] = None,
                    ledger: pathlib.Path = THESIS_LEDGER,
                    now_iso: str = "1970-01-01T00:00:00", today=None) -> SeedThesisResult:
    """Research ONE user seed and file it as a later-dated ``origin="user_seeded"`` thesis.
    Callers MUST gate this behind ``not seeds_are_held()`` — the blind scan files FIRST."""
    month = str(now_iso)[:7]
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return SeedThesisResult(skip_reason=f"skipped:{decision.reason}")

    assert_forward_only(as_of, today=today)
    bundle = build_seed_bundle(seed, as_of=as_of, context=research_context)
    bundle_json = _canonical_json(bundle)
    bundle_sha = _sha256(bundle_json)
    prompt_text, prompt_sha = _prompt(prompt_path)

    try:
        # scan-tier token budget, not the governor's daily cap (see run_blind_scan)
        resp = model_call(prompt_text, bundle_json, max_output_tokens)
    except Exception as e:   # noqa: BLE001
        return SeedThesisResult(skip_reason=f"skipped:model_call_error:{type(e).__name__}")
    raw_path = _archive_raw(raw_dir, f"seed_{seed.seed_id}", as_of, resp, bundle_sha)
    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    try:
        payload = _lenient(resp.get("text", ""))
    except Exception:
        return SeedThesisResult(skip_reason="invalid:not_json", raw_path=raw_path)
    if not isinstance(payload, dict):
        return SeedThesisResult(skip_reason="invalid:not_an_object", raw_path=raw_path)

    payload_i = _stamp(payload, origin="user_seeded", as_of=as_of, resp=resp, bundle_sha=bundle_sha,
                       prompt_sha=prompt_sha, model_id_requested=model_id_requested,
                       prompt_version=prompt_version, usage=usage, attribute_usage=True,
                       thesis_id=f"seed-{_slug(seed.seed_id)}")
    rec, err = file_thesis(payload_i, ledger=ledger)
    if rec is None:
        return SeedThesisResult(reason=err, raw_path=raw_path)
    return SeedThesisResult(filed=rec, raw_path=raw_path)


# ---------------- the pulse orchestration (scan → release → seeds) ----------------
def run_thesis_pulse(as_of: str, *, scan_model_call: ModelCall, seed_model_call: ModelCall,
                     governor: CostGovernor, model_id_requested: str,
                     scan_prompt_path: str, seed_prompt_path: str, raw_dir: str,
                     scan_projected_cost_usd: float, seed_projected_cost_usd: float,
                     news: Optional[list] = None, events: Optional[list] = None,
                     rate_path: Optional[dict] = None, universe_hint: Optional[list] = None,
                     ledger: pathlib.Path = THESIS_LEDGER, scan_state: pathlib.Path = SCAN_STATE,
                     prov_log: pathlib.Path = SCAN_PROV_LOG, inbox: pathlib.Path = THESIS_INBOX,
                     now_iso: str = "1970-01-01T00:00:00", today=None,
                     max_output_tokens: int = 4000, force: bool = False) -> Dict[str, Any]:
    """The weekly desk step for the daily pulse: run the scan when DUE, then file any
    held/new user seeds AFTER (the seed research reuses the same machine-visible context).
    Returns a summary dict for the heartbeat. ``force`` overrides the cadence gate (for the
    one-time ignition scan)."""
    out: Dict[str, Any] = {"as_of": as_of, "due": False, "scan": None, "seeds": []}
    if not (force or due(as_of, path=scan_state)):
        return out
    out["due"] = True

    scan = run_blind_scan(as_of, model_call=scan_model_call, governor=governor,
                          model_id_requested=model_id_requested, prompt_version="scan/v1",
                          projected_cost_usd=scan_projected_cost_usd, raw_dir=raw_dir,
                          prompt_path=scan_prompt_path, max_output_tokens=max_output_tokens,
                          news=news, events=events,
                          rate_path=rate_path, universe_hint=universe_hint, ledger=ledger,
                          scan_state=scan_state, prov_log=prov_log, inbox=inbox,
                          now_iso=now_iso, today=today)
    out["scan"] = {"scanned": scan.scanned, "n_filed": len(scan.filed),
                   "n_rejected": len(scan.rejected), "n_theses_seen": scan.n_theses_seen,
                   "skip_reason": scan.skip_reason,
                   "reason": scan.reason, "n_documents": scan.n_documents,
                   "bundle_bytes": scan.bundle_bytes,
                   "blind_scan_ordinal": (scan.provenance or {}).get("blind_scan_ordinal"),
                   "is_first_blind_scan": (scan.provenance or {}).get("is_first_blind_scan")}

    # seeds file ONLY once the hold is released (scans > 0) — the blind scan went first.
    if not seeds_are_held(path=scan_state):
        already = load_filed(ledger)
        for seed in load_seeds(inbox):
            if f"seed-{_slug(seed.seed_id)}"[:96] in already:   # deterministic id ⇒ idempotent
                continue
            ctx = {"news_digest": (news or [])[:20], "event_calls": (events or [])[:20],
                   "rate_path": rate_path or {}}
            res = run_seed_thesis(seed, as_of, model_call=seed_model_call, governor=governor,
                                  model_id_requested=model_id_requested, prompt_version="seed/v1",
                                  projected_cost_usd=seed_projected_cost_usd, raw_dir=raw_dir,
                                  prompt_path=seed_prompt_path, max_output_tokens=max_output_tokens,
                                  research_context=ctx, ledger=ledger,
                                  now_iso=now_iso, today=today)
            out["seeds"].append({"seed_id": seed.seed_id,
                                 "filed": res.filed is not None,
                                 "skip_reason": res.skip_reason, "reason": res.reason})
    return out
