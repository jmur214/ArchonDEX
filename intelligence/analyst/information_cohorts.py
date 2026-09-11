"""intelligence/analyst/information_cohorts.py — INFORMATION-SET cohort labels (T-350).

A cohort boundary is not always a prompt bump. The agentic arm's `query_prices`
returned `[]` from deploy — the price substrate was never packaged — so the arm was
**price-blind** the entire time while carrying `prompt_version: daily_agentic/v1`.
`by_prompt_version` cannot see that boundary **because the prompt never changed**, so
an aggregate over "the agentic arm" silently pools a blinded era with a fed one.

THE RULE (the same one the risk-flag canonicalization follows): a label describes what
the arm ACTUALLY SAW, and is **never retroactively reinterpreted**. A price-blind row
stays price-blind forever, even after the fix — pretending otherwise would rewrite what
the model had to work with.

Boundaries live in `config/information_cohorts.json` so E can stamp a deploy date as a
FACT without a code change. A cohort whose `from_date` is null has not started yet.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config" / "information_cohorts.json"
_CACHE: Optional[dict] = None
UNSTAMPED_SUFFIX = "_UNSTAMPED"


def load_registry(path: Path = REGISTRY) -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(path.read_text()).get("sources", {})
        except Exception:          # noqa: BLE001 — absent registry => no boundaries
            _CACHE = {}
    return _CACHE


def cohort_for(source: str, note_date: str, registry: Optional[dict] = None) -> Optional[str]:
    """The information-set cohort a row belongs to. None when the source has no
    declared boundaries (most sources) — callers treat None as "not segmented"."""
    reg = registry if registry is not None else load_registry()
    spec = (reg or {}).get(source)
    if not spec:
        return None
    best_label, best_date = spec.get("default_cohort"), None
    pending_label = None
    for c in spec.get("cohorts", []):
        frm, pend = c.get("from_date"), c.get("pending_from")
        if not note_date:
            continue
        if frm and str(note_date)[:10] >= str(frm)[:10]:
            if best_date is None or str(frm)[:10] >= str(best_date)[:10]:
                best_label, best_date = c.get("label"), frm
        elif not frm and pend and str(note_date)[:10] >= str(pend)[:10]:
            # T-351: announced but UNCONFIRMED. Flag it rather than asserting the prior
            # cohort — once the fix is live, defaulting to "price_blind" is a MISLABEL.
            pending_label = f"{c.get('label')}{UNSTAMPED_SUFFIX}"
    # a STAMPED boundary always wins over a pending one
    return best_label if best_date else (pending_label or best_label)


def is_unstamped(cohort: Optional[str]) -> bool:
    """True for a label that is explicitly NOT vouched for yet (T-351)."""
    return bool(cohort) and str(cohort).endswith(UNSTAMPED_SUFFIX)


def label_rows(rows: list[dict], registry: Optional[dict] = None) -> list[dict]:
    """Attach `information_cohort` in place-ish (returns the same list)."""
    for r in rows or []:
        c = cohort_for(r.get("source", ""), r.get("note_date", ""), registry)
        if c:
            r["information_cohort"] = c
    return rows


def spans_a_boundary(rows: list[dict]) -> bool:
    """True iff these rows straddle an information-set boundary — i.e. pooling them
    into ONE aggregate would mix arms that saw different things. The A/B uses this to
    refuse a comparison rather than quietly average across the change."""
    by_src: dict[str, set] = {}
    for r in rows or []:
        c = r.get("information_cohort")
        if c:
            by_src.setdefault(r.get("source", ""), set()).add(c)
    return any(len(v) > 1 for v in by_src.values())


def cohort_counts(rows: list[dict]) -> dict[str, Any]:
    out: dict[str, dict] = {}
    for r in rows or []:
        c = r.get("information_cohort")
        if c:
            out.setdefault(r.get("source", ""), {}).setdefault(c, 0)
            out[r.get("source", "")][c] += 1
    return out
