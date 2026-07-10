"""T-304b — the today-forward runner. Opens + accrues the event-interpreter's forward record.

Gets today's NEW documents (allowlisted 8-K items + special-sit deltas), fetches 8-K bodies from EDGAR
(special-sit deltas are already text-bearing), and fires ONE `run_event_call` per document via the injected
model adapter, appending each to `data/intel/event_calls.jsonl`.

`[NN-AI-GATE]` — the load-bearing guard: FORWARD-ONLY. `run_forward` REFUSES to run for an `as_of` more than
`max_lag_days` before `today` — a hard stop against ever firing a model call on a historical document
(memorization look-ahead). There is no backfill path, by construction.

The model adapter is E's shared seam (the injected `ModelCall`). This runner accepts it as a parameter; it
does not construct one. `pulse_step` is the fail-OPEN daily entrypoint (interpreter failure never fails the
pulse) — if no adapter is supplied it returns `degraded`, never raises.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from intelligence.analyst.cost_governor import CostGovernor
from intelligence.event_call.eightk_body import fetch_8k_text
from intelligence.event_call.eightk_feed import EventDocument, new_documents
from intelligence.event_call.event_service import (EVENT_CALLS_LEDGER, ModelCall,
                                                  load_seen, run_event_call)

DEFAULT_MAX_LAG_DAYS = 3          # as_of must be within this many days of `today` — no historical firing


@dataclass
class ForwardRunResult:
    as_of: str
    n_documents: int = 0
    n_ok: int = 0
    n_skipped: int = 0
    n_invalid: int = 0
    n_no_body: int = 0
    degraded: bool = False
    reason: Optional[str] = None
    statuses: List[str] = field(default_factory=list)


def _attach_body(doc: EventDocument, fetch=fetch_8k_text) -> bool:
    """For an 8-K document, fetch + attach the primary-document text. Returns True if a body is present."""
    if doc.text:
        return True
    if doc.source != "8k":
        return False
    cik = (doc.meta or {}).get("cik")
    acc = (doc.meta or {}).get("accession")
    text = fetch(cik, acc)
    if text:
        doc.text = text
        return True
    return False


def run_forward(as_of, *, model_call: ModelCall, governor: CostGovernor,
                prompt_path: str, model_id_requested: str, prompt_version: str,
                projected_cost_usd: float, raw_dir: str,
                universe: Optional[Set[str]] = None, since: Optional[str] = None,
                ledger_path=EVENT_CALLS_LEDGER, now_iso: Optional[str] = None,
                today: Optional[_dt.date] = None, max_lag_days: int = DEFAULT_MAX_LAG_DAYS,
                body_fetch=fetch_8k_text) -> ForwardRunResult:
    """Fire one event call per NEW document dated on/around `as_of`. Forward-only (hard PIT guard)."""
    as_of_s = _dt.date.fromisoformat(str(as_of)[:10]).isoformat()
    today = today or _dt.date.today()
    aod = _dt.date.fromisoformat(as_of_s)
    # HARD forward-only guard: refuse any historical run (would be a memorization-look-ahead model call).
    if aod > today or (today - aod).days > max_lag_days:
        return ForwardRunResult(as_of_s, degraded=True,
                                reason=f"refused:not_forward (as_of {as_of_s} vs today {today}, max_lag {max_lag_days}d)")
    now_iso = now_iso or f"{as_of_s}T21:00:00"
    seen: Set[str] = load_seen(ledger_path)
    docs = new_documents(as_of_s, universe=universe, since=since, seen=seen)
    res = ForwardRunResult(as_of_s, n_documents=len(docs))
    for doc in docs:
        if not _attach_body(doc, fetch=body_fetch):
            res.n_no_body += 1
            res.statuses.append(f"no_body:{doc.document_ref}")
            continue                             # no interpretable body → no call (8-K body unavailable)
        r = run_event_call(doc, as_of=as_of_s, prompt_path=prompt_path, model_call=model_call,
                           governor=governor, model_id_requested=model_id_requested,
                           prompt_version=prompt_version, projected_cost_usd=projected_cost_usd,
                           raw_dir=raw_dir, ledger_path=ledger_path, now_iso=now_iso)
        res.statuses.append(r.status)
        if r.status == "ok":
            res.n_ok += 1
        elif r.status.startswith("skipped:"):
            res.n_skipped += 1
        else:
            res.n_invalid += 1
        if r.status.startswith("skipped:") and "budget" in r.status:
            break                                # governor exhausted → stop the batch
    return res


def pulse_step(as_of, *, model_call: Optional[ModelCall], governor: CostGovernor,
               prompt_path: str, model_id_requested: str, prompt_version: str,
               projected_cost_usd: float, raw_dir: str, **kw) -> Dict[str, Any]:
    """Fail-OPEN daily pulse entrypoint (interpreter failure NEVER fails the pulse). Report-only.

    The pulse supplies E's shared model adapter as `model_call`. If it is None (adapter not yet wired),
    this returns a degraded flag and fires NO call — the record simply does not open that day."""
    if model_call is None:
        return {"status": "degraded", "reason": "no_model_adapter", "n_ok": 0}
    try:
        r = run_forward(as_of, model_call=model_call, governor=governor, prompt_path=prompt_path,
                        model_id_requested=model_id_requested, prompt_version=prompt_version,
                        projected_cost_usd=projected_cost_usd, raw_dir=raw_dir, **kw)
        return {"status": "degraded" if r.degraded else "ok", "reason": r.reason,
                "n_documents": r.n_documents, "n_ok": r.n_ok, "n_skipped": r.n_skipped,
                "n_invalid": r.n_invalid, "n_no_body": r.n_no_body}
    except Exception as e:   # noqa: BLE001 — never fail the pulse
        return {"status": "degraded", "reason": f"error:{type(e).__name__}", "n_ok": 0}
