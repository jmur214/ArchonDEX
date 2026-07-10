"""T-304 — the event-interpreter service. ONE structured model call per NEW document.

Clones the ordered seam of `analyst_service.run_daily_note`, scoped to a single document:
    governor.check → build per-document bundle → ONE model_call (no tools/loop) → archive raw →
    governor.record_spend → json.loads + validate_event_call → append to the forward ledger.

The ledger record is written in the shape A's `eval_harness.run()` consumes (a `note`-like dict
with `note_id`, `note_date`, `model_id`, `prompt_version`, and a `predictions:[...]` array whose
each element carries a resolver/v1 `resolver`), so A scores event calls with ZERO harness changes.

FORWARD-ONLY, machine-scoreable, `[NN-AI-GATE]`. Live model calls await the shared adapter; this
runs today against the injected `ModelCall` seam (tests pass a closure).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from intelligence.analyst.cost_governor import CostGovernor
from intelligence.event_call.eightk_feed import EventDocument
from intelligence.event_call.event_schema import sha256_text, validate_event_call

# The model-adapter seam — identical to analyst_service.ModelCall (one source of truth).
ModelCall = Callable[[str, str, int], Dict[str, Any]]

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENT_CALLS_LEDGER = ROOT / "data" / "intel" / "event_calls.jsonl"


@dataclass
class EventCallResult:
    call: Optional[dict]                 # validated EventCall.model_dump(), or None
    status: str                          # "ok" | "skipped:<reason>" | "invalid:<reason>"
    document_ref: str = ""
    raw_path: Optional[str] = None
    ledger_record: Optional[dict] = None


def build_document_bundle(doc: EventDocument, *, as_of: str) -> dict:
    """Deterministic, secret-free serialization of the ONE document the model interprets.
    No account numbers, no portfolio, no credentials — a document interpreter needs none."""
    return {
        "as_of": as_of,
        "document_ref": doc.document_ref,
        "source": doc.source,
        "symbol": doc.symbol,
        "file_date": doc.file_date,
        "item_code": doc.item_code,
        "event_class_hint": doc.event_class_hint,
        "document_text": doc.text or "",
    }


def canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _prompt_text(prompt_path: str) -> "tuple[str, str]":
    t = pathlib.Path(prompt_path).read_text()
    return t, _sha(t)


def _to_ledger_record(call: dict, doc: EventDocument) -> dict:
    """Project a validated event call into A's eval_harness.run() note-shape (zero harness change):
    a `note_id`/`note_date`, `model_id`, `prompt_version`, and a `predictions` array of resolver/v1
    predictions. The event-specific fields ride alongside for the per-event-type Brier breakdown."""
    return {
        "note_id": f"eventcall:{doc.document_ref}",
        "note_date": call["as_of"],
        "model_id": call["provenance"]["model_id_served"],
        "prompt_version": call["provenance"]["prompt_version"],
        "predictions": call["predictions"],           # already resolver/v1-valid (schema-gated)
        # event-call context (for per-type scoring; ignored by the generic harness):
        "event_call": {
            "schema_version": call["schema_version"], "source": call["source"],
            "document_ref": call["document_ref"], "symbol": call["symbol"],
            "file_date": call["file_date"], "event_type": call["event_type"],
            "materiality": call["materiality"], "direction": call["direction"],
            "suspected_prompt_injection": call["suspected_prompt_injection"],
            "input_document_sha256": call["input_document_sha256"],
        },
    }


def run_event_call(doc: EventDocument, *, as_of: str, prompt_path: str,
                   model_call: ModelCall, governor: CostGovernor,
                   model_id_requested: str, prompt_version: str,
                   projected_cost_usd: float, raw_dir: str,
                   ledger_path: pathlib.Path = EVENT_CALLS_LEDGER,
                   now_iso: str = "1970-01-01T00:00:00") -> EventCallResult:
    """Interpret ONE document. Fail-closed on the governor; a bad response ⇒ NO call (raw archived)."""
    month = str(now_iso)[:7]

    # 1. governor / kill switch — fail-closed, no call on refusal
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return EventCallResult(None, f"skipped:{decision.reason}", document_ref=doc.document_ref)

    # 2. deterministic, secret-free per-document bundle
    bundle = build_document_bundle(doc, as_of=as_of)
    bundle_json = canonical_json(bundle)
    prompt, prompt_sha = _prompt_text(prompt_path)
    doc_sha = sha256_text(bundle["document_text"])
    bundle_sha = _sha(bundle_json)

    # 3. ONE structured call (no tools, no loop); raw always archived
    try:
        resp = model_call(prompt, bundle_json, decision.max_output_tokens)
    except Exception as e:   # noqa: BLE001
        return EventCallResult(None, f"skipped:model_call_error:{type(e).__name__}",
                               document_ref=doc.document_ref)

    pathlib.Path(raw_dir).mkdir(parents=True, exist_ok=True)
    safe_ref = doc.document_ref.replace("/", "_").replace("#", "_")
    raw_path = str(pathlib.Path(raw_dir) / f"raw_{safe_ref}.json")
    pathlib.Path(raw_path).write_text(json.dumps(
        {"document_ref": doc.document_ref, "as_of": as_of,
         "response": resp.get("text", ""), "model_id_served": resp.get("model_id_served"),
         "input_bundle_sha256": bundle_sha}, default=str))

    # record spend regardless of validity (the call happened)
    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    # 4. parse + independent local re-validation → bad ⇒ NO call
    try:
        payload = json.loads(resp.get("text", ""))
    except Exception:
        return EventCallResult(None, "invalid:not_json", document_ref=doc.document_ref, raw_path=raw_path)

    # the service (not the model) fills provenance + the PIT document identity
    payload.setdefault("as_of", as_of)
    payload.setdefault("source", doc.source)
    payload.setdefault("document_ref", doc.document_ref)
    payload.setdefault("symbol", doc.symbol)
    payload.setdefault("file_date", doc.file_date)
    payload["input_document_sha256"] = doc_sha
    payload["provenance"] = {
        "model_id_requested": model_id_requested,
        "model_id_served": str(resp.get("model_id_served", model_id_requested)),
        "prompt_version": prompt_version, "prompt_sha256": prompt_sha,
        "input_bundle_sha256": bundle_sha,
    }
    payload["usage"] = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "cost_usd": float(usage.get("cost_usd", 0.0) or 0.0),
    }
    call, err = validate_event_call(payload)
    if call is None:
        return EventCallResult(None, f"invalid:{err}", document_ref=doc.document_ref, raw_path=raw_path)

    # 5. append to the forward ledger (A's harness consumes this), in A's note-shape
    record = _to_ledger_record(call.model_dump(), doc)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    return EventCallResult(call.model_dump(), "ok", document_ref=doc.document_ref,
                           raw_path=raw_path, ledger_record=record)


def load_seen(ledger_path: pathlib.Path = EVENT_CALLS_LEDGER) -> Set[str]:
    """The idempotency set: document_refs already called (one call per document, ever)."""
    seen: Set[str] = set()
    if not ledger_path.exists():
        return seen
    for line in ledger_path.read_text().splitlines():
        try:
            seen.add(json.loads(line)["event_call"]["document_ref"])
        except Exception:
            continue
    return seen
