"""T-321 — the AGENTIC analyst service (P2.5): investigate-then-decide.

Same note schema, same cost governor, and the SAME safety stack as the
constrained analyst (``analyst_service``) — the ONLY difference is that the model
gets read-only tools over our own stores and a capped tool-use loop before it
writes the note. It is the treatment arm of the A/B: does AGENCY add skill
(Brier, directional) or only cost + attack surface?

The safety posture is deliberately identical to the constrained path, reused
verbatim rather than reimplemented:
  * one governed budget (the SAME ``CostGovernor`` — the tool loop's accumulated
    cost is charged once);
  * ``_loads_lenient`` tolerant parse → strict ``validate_note`` re-validation
    (a bad field ⇒ NO note, raw archived);
  * the non-``shadow`` (real-account) action HARD-VOIDS the note; benign shape/
    bound issues on shadow actions are dropped by the same ``_filter_actions``
    firewall;
  * the whole tool corpus is our own stores, ``_scrub``'d + size-bounded in
    ``agentic_tools`` — tools ADD retrieval, not exposure.
Every tool call is recorded in the note's ``provenance.tool_trace`` — the audit
of what the model looked at before deciding.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from intelligence.analyst.context_builder import build_bundle, bundle_sha256, canonical_json
from intelligence.analyst.cost_governor import CostGovernor
from intelligence.analyst.note_schema import validate_note
from intelligence.analyst.analyst_service import (
    _prompt_text, _strip_json_fence, _filter_actions)


def _loads_lenient(text: str):
    """Locate and parse the analyst_note JSON object inside an agentic response.
    A tool-using model narrates: it commonly writes reasoning prose BEFORE the
    JSON and appends text AFTER it. So: strip an outer fence, skip any leading
    prose to the first ``{``, then ``raw_decode`` the first complete object and
    ignore the trailing remainder. The full note is still validated downstream,
    so this tolerance never weakens the gate (a genuinely non-JSON body has no
    ``{`` or fails raw_decode → raises → NO note)."""
    import json as _json
    s = _strip_json_fence(text)
    i = s.find("{")
    if i > 0:
        s = s[i:]
    obj, _ = _json.JSONDecoder().raw_decode(s)
    return obj

# the tool loop's ceiling on investigation depth (also budget-gated). ~3-5× a
# constrained note in cost; the cap bounds the worst case.
DEFAULT_MAX_TOOL_CALLS = 8


@dataclass
class AgenticResult:
    note: Optional[dict]
    status: str
    raw_path: Optional[str] = None
    firewall_rejections: Optional[List[dict]] = None
    tool_trace: Optional[List[dict]] = None
    n_tool_calls: int = 0


def run_agentic_note(as_of, *, portfolios, allowlist, prompt_path,
                     agentic_call: Callable, tools, governor: CostGovernor,
                     model_id_requested: str, prompt_version: str,
                     projected_cost_usd: float, raw_dir: str,
                     watchlist=None, event_state=None, load_panel=None,
                     max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
                     now_iso: str = "1970-01-01T00:00:00") -> AgenticResult:
    """Run one governed agentic note. ``agentic_call`` is
    ``anthropic_adapter.make_agentic_call(...)``; ``tools`` an ``AgenticTools``.
    Never raises into the trading path."""
    month = str(now_iso)[:7]

    # 1. governor / kill switch — fail-closed, no call on refusal
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return AgenticResult(None, f"skipped:{decision.reason}")

    # 2. the SAME deterministic secret-free bundle as the constrained analyst,
    # PLUS the shared question anchor (T-325): both analysts commit a prediction
    # for each anchor question so the A/B pairs like-for-like (extras beyond the
    # anchor are scored but do not enter the paired comparison). The constrained
    # path injects the SAME anchor — identical questions, by construction.
    from intelligence.analyst.question_anchor import anchor_questions
    bundle = build_bundle(as_of, portfolios=portfolios, watchlist=watchlist,
                          event_state=event_state, load_panel=load_panel)
    bundle["anchor_questions"] = anchor_questions(bundle["as_of"])
    bundle_json = canonical_json(bundle)
    prompt, prompt_sha = _prompt_text(prompt_path)

    # 3. the capped tool-use loop (raw REST, no SDK). Raw always archived.
    try:
        resp = agentic_call(prompt, bundle_json, decision.max_output_tokens,
                            tools.specs(), tools.execute, max_tool_calls)
    except Exception as e:   # noqa: BLE001
        return AgenticResult(None, f"skipped:model_call_error:{type(e).__name__}",
                             tool_trace=tools.trace_dicts())

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    raw_path = str(Path(raw_dir) / f"agentic_raw_{bundle['as_of']}.json")
    Path(raw_path).write_text(json.dumps(
        {"as_of": bundle["as_of"], "response": resp.get("text", ""),
         "model_id_served": resp.get("model_id_served"),
         "n_tool_calls": resp.get("n_tool_calls"), "stopped": resp.get("stopped"),
         "tool_trace": tools.trace_dicts(),
         "input_bundle_sha256": bundle_sha256(bundle)}, default=str))

    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    # 4. tolerant parse → strict re-validation (identical to the constrained path)
    try:
        payload = _loads_lenient(resp.get("text", ""))
    except Exception:
        return AgenticResult(None, "invalid:not_json", raw_path=raw_path,
                             tool_trace=tools.trace_dicts(),
                             n_tool_calls=resp.get("n_tool_calls", 0))

    raw_actions = payload.pop("hypothetical_actions", []) or []
    if not isinstance(raw_actions, list):
        return AgenticResult(None, "invalid:hypothetical_actions_not_a_list",
                             raw_path=raw_path, tool_trace=tools.trace_dicts())
    for a in raw_actions:
        if isinstance(a, dict) and str(a.get("account", "shadow")) != "shadow":
            return AgenticResult(None, "invalid:non_shadow_account", raw_path=raw_path,
                                 tool_trace=tools.trace_dicts())
    payload["hypothetical_actions"] = []

    payload.setdefault("as_of", bundle["as_of"])
    payload["provenance"] = {
        "model_id_requested": model_id_requested,
        "model_id_served": str(resp.get("model_id_served", model_id_requested)),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "input_bundle_sha256": bundle_sha256(bundle),
        # the investigation audit — validated (known optional Provenance fields),
        # so the persisted note re-validates like a constrained one.
        "tool_trace": tools.trace_dicts(),
        "n_tool_calls": int(resp.get("n_tool_calls", 0)),
        "agentic_stopped": str(resp.get("stopped", "end_turn")),
    }
    payload["usage"] = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "cost_usd": float(usage.get("cost_usd", 0.0) or 0.0),
    }
    note, err = validate_note(payload)
    if note is None:
        return AgenticResult(None, f"invalid:{err}", raw_path=raw_path,
                             tool_trace=tools.trace_dicts(),
                             n_tool_calls=resp.get("n_tool_calls", 0))

    # 5. same per-item shadow-action firewall (drop bad, keep note); the tool
    # audit is already in provenance (validated above).
    note_dict = note.model_dump()
    kept, rejected = _filter_actions(raw_actions, {s.upper() for s in allowlist})
    note_dict["hypothetical_actions"] = kept
    return AgenticResult(note_dict, "ok", raw_path=raw_path,
                         firewall_rejections=rejected or None,
                         tool_trace=tools.trace_dicts(),
                         n_tool_calls=int(resp.get("n_tool_calls", 0)))
