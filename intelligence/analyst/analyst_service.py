"""T-292 — the analyst service: one governed, injection-hardened structured call.

Stage-0 is report-only. `run_daily_note` orchestrates:

  1. cost governor + kill switch check → refuse ⇒ NO call, a skip record;
  2. build the deterministic, secret-free input bundle (context_builder);
  3. ONE structured model call — NO tools, NO agent loop (the injection surface
     is minimized by construction); the raw response is always archived;
  4. independent local re-validation against note_schema → a bad field ⇒ NO note
     (raw kept for forensics), never a suspect note;
  5. semantic firewall on the validated note: every symbol referenced in an
     action must be on the caller's allowlist, else the ACTION is rejected and
     logged (the note survives; the attempt becomes signal);
  6. record spend; return the note (or a structured skip reason).

The live Anthropic call is injected as ``model_call`` (a callable) so the whole
service is unit-testable with zero network + zero key. Production passes a thin
adapter that reads ANTHROPIC_API_KEY from env/Secrets Manager and makes the
single Messages call with enforced JSON output + prompt caching. NO credentials
and NO account numbers ever enter the prompt (guaranteed by context_builder).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from intelligence.analyst.context_builder import build_bundle, bundle_sha256, canonical_json
from intelligence.analyst.cost_governor import CostGovernor
from intelligence.analyst.note_schema import validate_note

# model_call(prompt_text, bundle_json, max_output_tokens) -> {"text","model_id_served","usage"}
ModelCall = Callable[[str, str, int], Dict[str, Any]]


@dataclass
class AnalystResult:
    note: Optional[dict]            # the validated analyst_note/v1 dict, or None
    status: str                     # "ok" | "skipped:<reason>" | "invalid:<reason>"
    raw_path: Optional[str] = None  # where the raw response was archived
    firewall_rejections: Optional[List[dict]] = None


def _prompt_text(prompt_path: str) -> "tuple[str, str]":
    text = Path(prompt_path).read_text()
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _apply_semantic_firewall(note: dict, allowlist: set) -> List[dict]:
    """Drop any hypothetical_action whose symbol is not allowlisted; return the
    rejected attempts (logged signal). Mutates note in place."""
    rejected, kept = [], []
    for a in note.get("hypothetical_actions", []):
        if str(a.get("symbol", "")).upper() in allowlist:
            kept.append(a)
        else:
            rejected.append({"reason": "symbol_not_allowlisted", "action": a})
    note["hypothetical_actions"] = kept
    return rejected


def run_daily_note(as_of, *, portfolios, allowlist, prompt_path,
                   model_call: ModelCall, governor: CostGovernor,
                   model_id_requested: str, prompt_version: str,
                   projected_cost_usd: float, raw_dir: str,
                   watchlist=None, event_state=None, load_panel=None,
                   now_iso: str = "1970-01-01T00:00:00") -> AnalystResult:
    month = str(now_iso)[:7]

    # 1. governor / kill switch — fail-closed, no call on refusal
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return AnalystResult(None, f"skipped:{decision.reason}")

    # 2. deterministic, secret-free bundle
    bundle = build_bundle(as_of, portfolios=portfolios, watchlist=watchlist,
                          event_state=event_state, load_panel=load_panel)
    bundle_json = canonical_json(bundle)
    prompt, prompt_sha = _prompt_text(prompt_path)

    # 3. ONE structured call (no tools, no loop); raw always archived
    try:
        resp = model_call(prompt, bundle_json, decision.max_output_tokens)
    except Exception as e:   # noqa: BLE001
        return AnalystResult(None, f"skipped:model_call_error:{type(e).__name__}")

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    raw_path = str(Path(raw_dir) / f"raw_{bundle['as_of']}.json")
    Path(raw_path).write_text(json.dumps(
        {"as_of": bundle["as_of"], "response": resp.get("text", ""),
         "model_id_served": resp.get("model_id_served"),
         "input_bundle_sha256": bundle_sha256(bundle)}, default=str))

    # record spend regardless of validity (the call happened)
    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    # 4. parse + independent local re-validation → bad ⇒ NO note
    try:
        payload = json.loads(resp.get("text", ""))
    except Exception:
        return AnalystResult(None, "invalid:not_json", raw_path=raw_path)

    payload.setdefault("as_of", bundle["as_of"])
    payload["provenance"] = {
        "model_id_requested": model_id_requested,
        "model_id_served": str(resp.get("model_id_served", model_id_requested)),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "input_bundle_sha256": bundle_sha256(bundle),
    }
    payload["usage"] = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "cost_usd": float(usage.get("cost_usd", 0.0) or 0.0),
    }
    note, err = validate_note(payload)
    if note is None:
        return AnalystResult(None, f"invalid:{err}", raw_path=raw_path)

    # 5. semantic firewall — reject non-allowlisted action symbols (keep the note)
    note_dict = note.model_dump()
    rejected = _apply_semantic_firewall(note_dict, {s.upper() for s in allowlist})
    return AnalystResult(note_dict, "ok", raw_path=raw_path,
                         firewall_rejections=rejected or None)
