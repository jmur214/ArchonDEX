"""T-325 #5 — the stage-2 operational-proof clock (READINESS, not calendar).

The user green-lit real-paper authority "at a good point" — and clarified the
intent is "don't jump into things," NOT a fixed two weeks. So "the good point"
is a MEASURED readiness criterion, not a date on a calendar:

  READY ⇔ N consecutive clean days where, on each day,
    * BOTH analysts produced a VALID note (the constrained AND the agentic one),
    * the shared LLM budget stayed IN ENVELOPE (month-to-date < the cap),
    * (and — checked OUT of band, not per-day — the injection red-team suite is
      green and the shadow books are consuming cleanly).

Proposed N = 5 trading days. The machinery (governor, validators, shadow book,
eval) is already proven elsewhere, so this is a short confirmation window, not a
long ceremony — it could clear in a week if the pulse behaves. A single bad day
(either analyst invalid, or a budget breach) RESETS the streak — readiness is
about a clean *run*, not a lucky average. When the criteria are met the clock
reports ``ready=True`` with the evidence; E then PROPOSES the flip and the
director + user confirm. The clock never flips anything itself.

Append-only + durable (rides DURABLE_PATHS) so the streak survives the ephemeral
Fargate disk — a reset-to-empty would silently restart the count.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

PROPOSED_N = 5


@dataclass
class Stage2Verdict:
    ready: bool
    consecutive_clean: int
    n_required: int
    reason: str
    last_days: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"ready": self.ready, "consecutive_clean": self.consecutive_clean,
                "n_required": self.n_required, "reason": self.reason,
                "last_days": self.last_days, "_schema": "paper_stage2/v1"}


def record_day(path: str, *, as_of: str, analyst_ok: bool, agentic_ok: bool,
               cost_mtd: float, budget: float) -> Dict[str, Any]:
    """Append one day's readiness signals (idempotent per as_of — a re-run of the
    same day overwrites, it does not double-count). ``clean`` = both notes valid
    AND cost in envelope."""
    p = Path(path)
    rows = _load(p)
    rows = [r for r in rows if r.get("as_of") != as_of]     # de-dup this day
    in_envelope = float(cost_mtd) < float(budget)
    row = {"as_of": as_of, "analyst_ok": bool(analyst_ok),
           "agentic_ok": bool(agentic_ok), "cost_mtd": round(float(cost_mtd), 6),
           "in_envelope": in_envelope,
           "clean": bool(analyst_ok) and bool(agentic_ok) and in_envelope}
    rows.append(row)
    rows.sort(key=lambda r: r.get("as_of", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text("\n".join(json.dumps(r, default=str) for r in rows) + "\n")
    tmp.replace(p)
    return row


def evaluate(path: str, n_required: int = PROPOSED_N) -> Stage2Verdict:
    """The readiness verdict from the trailing record. A day that is NOT clean
    (either analyst invalid, or out of envelope) RESETS the streak."""
    rows = _load(Path(path))
    streak = 0
    for r in reversed(rows):
        if r.get("clean"):
            streak += 1
        else:
            break
    ready = streak >= n_required
    if not rows:
        reason = "no days recorded yet"
    elif ready:
        reason = f"{streak} consecutive clean days (≥ {n_required}) — PROPOSE the flip"
    else:
        last = rows[-1]
        why = ("both analysts valid + in-envelope" if last.get("clean")
               else f"last day NOT clean (analyst_ok={last.get('analyst_ok')} "
                    f"agentic_ok={last.get('agentic_ok')} in_envelope={last.get('in_envelope')})")
        reason = f"{streak}/{n_required} consecutive clean; {why}"
    return Stage2Verdict(ready=ready, consecutive_clean=streak,
                         n_required=n_required, reason=reason,
                         last_days=rows[-n_required:])


def _load(p: Path) -> List[Dict[str, Any]]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
