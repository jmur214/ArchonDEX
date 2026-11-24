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
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from intelligence.analyst.cost_governor import CostGovernor
from intelligence.event_call.eightk_body import fetch_8k_text
from intelligence.event_call.eightk_feed import EventDocument, new_documents, panel_status
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
    # T-412: what the 8-K feed looked like at read time (None = no panel_path given),
    # how many documents reached a model call, and how many the run budget deferred.
    feed: Optional[Dict[str, Any]] = None
    n_called: int = 0
    n_deferred: int = 0


# T-331 item 6 — a body must be NON-TRIVIAL to justify a paid model call. Today
# `terms` serialized as the literal "{}" (or "null"/"[]"/whitespace) is a TRUTHY
# string, so an empty-terms doc would fire a call and burn budget on nothing. The
# durable seen-ledger already prevents replay; this closes the once-each waste.
_TRIVIAL_BODIES = {"", "{}", "[]", "null", "none", "{ }", "[ ]"}
MIN_BODY_CHARS = 40


def _is_nontrivial(text: Optional[str]) -> bool:
    t = (text or "").strip()
    return bool(t) and t.lower() not in _TRIVIAL_BODIES and len(t) >= MIN_BODY_CHARS


def _attach_body(doc: EventDocument, fetch=fetch_8k_text,
                 cache: Optional[Dict[str, Optional[str]]] = None) -> bool:
    """Fetch + attach the primary-document text. True only if a NON-TRIVIAL body is
    present (T-331 item 6) — an empty/placeholder body must never fire a paid call.

    T-412: ``cache`` (per run, keyed by accession) — one 8-K carries several allowlisted
    items, and each item is its own document, so without it the same filing body was
    fetched once per item. The forward panel's ``primary_document`` skips the
    submissions lookup."""
    if _is_nontrivial(doc.text):
        return True
    if doc.source != "8k":
        return False
    meta = doc.meta or {}
    cik, acc = meta.get("cik"), meta.get("accession")
    if cache is not None and acc in cache:
        text = cache[acc]
    else:
        pdoc = meta.get("primary_document")
        text = fetch(cik, acc, **({"primary_document": pdoc} if pdoc else {}))
        if cache is not None:
            cache[acc] = text
    if _is_nontrivial(text):
        doc.text = text
        return True
    return False


def _within_date_floor(doc: EventDocument, floor: Optional[str]) -> bool:
    """T-331 item 6 — file_date LOWER BOUND: a document older than the floor is stale
    context, not news; skip it rather than pay to interpret it. A doc with no parseable
    file_date is KEPT (fail-open on the filter; the seen-ledger still bounds it)."""
    if not floor:
        return True
    # file_date is a TOP-LEVEL EventDocument field (meta is a fallback only)
    fd = str(getattr(doc, "file_date", "") or (doc.meta or {}).get("file_date") or "")[:10]
    if not fd:
        return True
    try:
        return _dt.date.fromisoformat(fd) >= _dt.date.fromisoformat(floor)
    except Exception:
        return True


# A session this far back is not "the one before a long weekend" — a price series that
# stopped must not widen the window without limit.
MAX_SESSION_REACH_DAYS = 7


def _date_floor(aod: _dt.date, max_lag_days: int, prev_session: Optional[str]) -> str:
    """The oldest filing date this run may read (see ``run_forward`` on prev_session)."""
    floor = aod - _dt.timedelta(days=max_lag_days)
    try:
        prev = _dt.date.fromisoformat(str(prev_session)[:10]) if prev_session else None
    except ValueError:
        prev = None
    if prev is not None and aod - _dt.timedelta(days=MAX_SESSION_REACH_DAYS) <= prev < floor:
        floor = prev
    return floor.isoformat()


def run_forward(as_of, *, model_call: ModelCall, governor: CostGovernor,
                prompt_path: str, model_id_requested: str, prompt_version: str,
                projected_cost_usd: float, raw_dir: str,
                universe: Optional[Set[str]] = None, since: Optional[str] = None,
                ledger_path=EVENT_CALLS_LEDGER, now_iso: Optional[str] = None,
                today: Optional[_dt.date] = None, max_lag_days: int = DEFAULT_MAX_LAG_DAYS,
                body_fetch=fetch_8k_text, panel_path: Optional[Path] = None,
                max_documents: Optional[int] = None,
                time_budget_s: Optional[float] = None,
                prev_session: Optional[str] = None) -> ForwardRunResult:
    """Fire one event call per NEW document dated on/around `as_of`. Forward-only (hard PIT guard).

    T-412 — ``panel_path`` names the 8-K panel this run reads (the daily pulse passes the
    FORWARD panel under its root). When it is given, a panel that is absent, unreadable,
    empty or stale makes the result ``degraded`` with that reason: "0 documents" from a
    panel that is not there is not a quiet day. Without it the research panel is read as
    before. ``since`` now defaults to the same forward window as the date floor
    (``as_of − max_lag_days``): a filing dated yesterday arrives in this morning's feed, so
    the old same-day default could never match a forward-fetched document.
    ``max_documents`` / ``time_budget_s`` bound one run (each call can take a minute; the
    pulse runs before the durable push); deferred documents stay unseen and are retried
    on the next run inside the window.
    ``prev_session`` is the date of the last completed market session (the driver's own
    price series): the window reaches back to it, because the filings of the session
    before a long weekend first appear in this run. Three calendar days alone dropped a
    Friday's filings on the Tuesday after a Monday holiday, and a Thursday's on the Monday
    after Good Friday or Christmas. It widens only which documents are read; the
    forward-only guard on ``as_of`` below is unchanged."""
    import time as _time
    t0 = _time.monotonic()
    as_of_s = _dt.date.fromisoformat(str(as_of)[:10]).isoformat()
    today = today or _dt.date.today()
    aod = _dt.date.fromisoformat(as_of_s)
    # HARD forward-only guard: refuse any historical run (would be a memorization-look-ahead model call).
    if aod > today or (today - aod).days > max_lag_days:
        return ForwardRunResult(as_of_s, degraded=True,
                                reason=f"refused:not_forward (as_of {as_of_s} vs today {today}, max_lag {max_lag_days}d)")
    now_iso = now_iso or f"{as_of_s}T21:00:00"
    # T-331 item 6: the file_date floor defaults to `as_of − max_lag_days` — the same
    # forward-only window the run itself is bounded by, so a stale document can't be
    # paid for even once.
    date_floor = _date_floor(aod, max_lag_days, prev_session)
    feed = panel_status(Path(panel_path), as_of_s) if panel_path is not None else None
    seen: Set[str] = load_seen(ledger_path)
    docs = new_documents(as_of_s, universe=universe, since=since or date_floor, seen=seen,
                         panel_path=Path(panel_path) if panel_path is not None else None)
    res = ForwardRunResult(as_of_s, n_documents=len(docs), feed=feed)
    if feed is not None and not feed["ok"]:
        res.degraded, res.reason = True, feed["reason"]
    bodies: Dict[str, Optional[str]] = {}
    for i, doc in enumerate(docs):
        if ((max_documents is not None and res.n_called >= max_documents)
                or (time_budget_s is not None and _time.monotonic() - t0 > time_budget_s)):
            res.n_deferred = len(docs) - i
            res.statuses.append(f"deferred:{res.n_deferred} (run budget reached)")
            break                                # the rest retry on the next run
        if not _within_date_floor(doc, date_floor):
            res.statuses.append(f"stale_file_date:{doc.document_ref}")
            continue                             # older than the floor → no paid call
        # One bad document must not cost the rest of the batch (recorded as invalid).
        try:
            if not _attach_body(doc, fetch=body_fetch, cache=bodies):
                res.n_no_body += 1
                res.statuses.append(f"no_body:{doc.document_ref}")
                continue                         # no interpretable/NON-TRIVIAL body → no call
            r = run_event_call(doc, as_of=as_of_s, prompt_path=prompt_path,
                               model_call=model_call, governor=governor,
                               model_id_requested=model_id_requested,
                               prompt_version=prompt_version,
                               projected_cost_usd=projected_cost_usd,
                               raw_dir=raw_dir, ledger_path=ledger_path, now_iso=now_iso)
        except Exception as e:   # noqa: BLE001
            res.n_invalid += 1
            res.statuses.append(f"invalid:error:{type(e).__name__}:{doc.document_ref}")
            continue
        res.statuses.append(r.status)
        # a call the governor refused never reached the model (an adapter error did)
        if not r.status.startswith("skipped:") or r.status.startswith("skipped:model_call_error"):
            res.n_called += 1
        if r.status == "ok":
            res.n_ok += 1
        elif r.status.startswith("skipped:"):
            res.n_skipped += 1
        else:
            res.n_invalid += 1
        if r.status.startswith("skipped:") and "budget" in r.status:
            res.n_deferred = len(docs) - i - 1   # governor exhausted → stop the batch; the
            break                                # rest were not looked at, and say so
    return res


def pulse_step(as_of, *, model_call: Optional[ModelCall], governor: CostGovernor,
               prompt_path: str, model_id_requested: str, prompt_version: str,
               projected_cost_usd: float, raw_dir: str, **kw) -> Dict[str, Any]:
    """Fail-OPEN daily pulse entrypoint (interpreter failure NEVER fails the pulse). Report-only.

    The pulse supplies E's shared model adapter as `model_call`. If it is None (adapter not yet wired),
    this returns a degraded flag and fires NO call — the record simply does not open that day.
    T-412: the 8-K feed's state rides along as ``feed`` either way (when ``panel_path`` is
    passed), so a day with no adapter still says whether the documents were there."""
    def _feed() -> Dict[str, Any]:
        if kw.get("panel_path") is None:
            return {}
        try:
            return {"feed": panel_status(Path(kw["panel_path"]), as_of)}
        except Exception as e:   # noqa: BLE001
            return {"feed": {"ok": False, "reason": f"status_error:{type(e).__name__}"}}

    if model_call is None:
        return {"status": "degraded", "reason": "no_model_adapter", "n_ok": 0, **_feed()}
    try:
        r = run_forward(as_of, model_call=model_call, governor=governor, prompt_path=prompt_path,
                        model_id_requested=model_id_requested, prompt_version=prompt_version,
                        projected_cost_usd=projected_cost_usd, raw_dir=raw_dir, **kw)
        out = {"status": "degraded" if r.degraded else "ok", "reason": r.reason,
               "n_documents": r.n_documents, "n_ok": r.n_ok, "n_skipped": r.n_skipped,
               "n_invalid": r.n_invalid, "n_no_body": r.n_no_body}
        if r.feed is not None:
            out.update(feed=r.feed, n_called=r.n_called, n_deferred=r.n_deferred)
        return out
    except Exception as e:   # noqa: BLE001 — never fail the pulse
        return {"status": "degraded", "reason": f"error:{type(e).__name__}", "n_ok": 0, **_feed()}
