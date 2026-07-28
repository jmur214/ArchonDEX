"""T-325 — the shared QUESTION ANCHOR for the analyst A/B.

The A/B (constrained vs agentic analyst) dies to INCONCLUSIVE_DRIFTED_SETS if the
two analysts free-range their own questions: their resolved-prediction sets stop
overlapping and there is nothing to pair. The anchor fixes that — a small,
DETERMINISTIC set of resolver/target/date questions that BOTH analysts commit to
every day, so the paired Brier compares like-for-like. The agentic analyst may
add EXTRA questions beyond the anchor (its investigation may surface a specific
view); those extras are scored on their own but do NOT enter the paired
comparison — only the anchor predictions do.

Design constraints:
  * DETERMINISTIC from ``as_of`` alone (dates only) — no price level injected (a
    data-derived level would be look-ahead), no randomness. Same as_of → same
    anchor for both analysts, reproducibly.
  * SELF-CONTAINED resolvers (relative-return + drawdown) that need no reference
    price, so the anchor never smuggles in a future value.
  * resolver/v1-valid (each passes A's ``is_resolvable_spec``) so every anchor
    prediction is machine-scoreable.
  * a stable ``anchor_id`` per question (a hash of the resolver) so both analysts
    and the eval harness pair on identity, not on wording.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any, Dict, List

ANCHOR_VERSION = "anchor/v1"


def _as_date(as_of) -> _dt.date:
    return as_of if isinstance(as_of, _dt.date) and not isinstance(as_of, _dt.datetime) \
        else _dt.date.fromisoformat(str(as_of)[:10])


def _month_end(d: _dt.date) -> _dt.date:
    nm = d.replace(day=28) + _dt.timedelta(days=4)
    return nm - _dt.timedelta(days=nm.day)


def _anchor_id(resolver: Dict[str, Any]) -> str:
    raw = json.dumps(resolver, sort_keys=True, separators=(",", ":"))
    return "anc-" + hashlib.sha1(raw.encode()).hexdigest()[:16]


def anchor_questions(as_of) -> List[Dict[str, Any]]:
    """The deterministic anchor set for ``as_of`` — 3 self-contained,
    resolver/v1-valid questions BOTH analysts must answer. Each item:
    ``{anchor_id, statement, resolver}`` (the analyst supplies the probability)."""
    d = _as_date(as_of)
    me = _month_end(d)
    d30, d90 = (d + _dt.timedelta(days=30)).isoformat(), (d + _dt.timedelta(days=90)).isoformat()
    specs = [
        # 1. cross-asset relative return to month-end (no price level needed)
        {"statement": f"SPY outperforms AGG (total relative return) from {d.isoformat()} "
                      f"to month-end {me.isoformat()}.",
         "resolver": {"type": "relative_return", "symbol_a": "SPY", "symbol_b": "AGG",
                      "op": "gt", "start_date": d.isoformat(), "end_date": me.isoformat()}},
        # 2. near-term tail: SPY drawdown > 5% over ~30 days
        {"statement": f"SPY draws down more than 5% at some point between {d.isoformat()} "
                      f"and {d30}.",
         "resolver": {"type": "dd_exceeds", "symbol": "SPY", "threshold_pct": 5.0,
                      "start_date": d.isoformat(), "end_date": d30}},
        # 3. quarter tail: SPY drawdown > 10% over ~90 days
        {"statement": f"SPY draws down more than 10% at some point between {d.isoformat()} "
                      f"and {d90}.",
         "resolver": {"type": "dd_exceeds", "symbol": "SPY", "threshold_pct": 10.0,
                      "start_date": d.isoformat(), "end_date": d90}},
    ]
    return [{"anchor_id": _anchor_id(s["resolver"]), "statement": s["statement"],
             "resolver": s["resolver"]} for s in specs]


def anchor_ids(as_of) -> List[str]:
    """The anchor ids for ``as_of`` — what the eval harness pairs the two analysts
    on (only predictions matching these ids enter the paired Brier comparison)."""
    return [q["anchor_id"] for q in anchor_questions(as_of)]
