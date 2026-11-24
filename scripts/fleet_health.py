"""Fleet health — does anything in the autonomous loop READ the paper fleet's own alarms?

Until 2026-11-10 nothing did. The deploy-candidate account halted on 2026-11-06 (an
unhandled 4-for-1 split in MTUM), its CloudWatch alarm fired the same morning, two
virtual books printed a −76% and a −16% day with `degraded: False`, and three nights of
janitor rows and director passes reported green — because neither reads the fleet. An
alarm whose only consumer is a human who is not watching is not a control.

This module is READ-ONLY. It fetches the accounts' heartbeats and the live books' state
from S3 (through an injected reader, so tests never touch the network) and returns one
verdict. UNKNOWN IS NOT HEALTHY: an unreachable or unparseable object fails the check
with its reason — it never passes by absence (`[NN-FAIL-CLOSED]`).

Usage:
    python -m scripts.fleet_health            # prints the verdict; exit 0 healthy, 1 not
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Dict, List, Optional, Tuple

#: account label → S3 prefix holding `data/state/paper_heartbeat.json`.
ACCOUNTS: Dict[str, str] = {
    "account-1 trend sleeve": "paper_state",
    "account-2 deploy candidate": "paper_state_offense_sso",
    "account-3 ai trader": "paper_state_ai_trader",
}
#: live_book/v1 state files (all written under account-1's prefix). Locked equal to
#: `paper_trader.live_books`' registered state paths by the test file.
BOOKS: Tuple[str, ...] = (
    "book_spy_null.json", "book_damped_offense.json", "book_quality_satellite.json",
    "book_sleeve_tier50k.json", "book_momentum_satellite.json",
)
BOOK_PREFIX = "paper_state"
#: A heartbeat older than this many calendar days is a silent stop (covers a 3-day
#: weekend plus one missed session).
STALE_AFTER_DAYS = 4
#: One-day change in (book growth − twin growth) beyond this, on a day NOT marked
#: degraded, is not a market move for any book in the roster — it is a data or
#: corporate-action defect (the 2026-11-05 split printed −0.70 and −0.19).
MAX_ONE_DAY_GAP = 0.10
#: (The WHOLE record is scanned: a corrupt day stays corrupt until it is restated, and
#: the check must keep saying so.)
#: A book parked (degraded) for at least this many consecutive sessions is reported.
PARKED_SESSIONS = 5
#: T-412: every account's run ends by writing a ``source_register`` block (did each
#: information source reach its reader?). A heartbeat without one means the run never
#: reached its tail — a container killed after trading — or the register could not be
#: written. Required of every account once ANY account has written one (the image is
#: deployed), and of all of them from this date whatever they have written: a merged
#: register nobody runs is itself a finding. Move the date if the deploy is held.
SOURCE_REGISTER_REQUIRED_FROM = date(2026, 12, 7)

Reader = Callable[[str], Tuple[Optional[bytes], str]]


@dataclass
class FleetVerdict:
    ok: bool
    problems: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    checked: int = 0
    #: Worth reading, not a failure: a working register that reported a degraded path.
    notes: List[str] = field(default_factory=list)

    @property
    def detail(self) -> str:
        notes = "".join(f" | note: {n}" for n in self.notes)
        if self.ok:
            return f"{self.checked} objects read; all accounts canonical, no book defect{notes}"
        parts = self.problems + [f"UNKNOWN {u}" for u in self.unknown]
        return f"{len(parts)} problem(s): " + " | ".join(parts) + notes


def judge_heartbeat(label: str, hb: dict, today: date) -> List[str]:
    """Problems in one account's heartbeat. An absent field is a problem, never a pass."""
    out: List[str] = []
    run = hb.get("last_run")
    if not isinstance(run, dict):
        return [f"{label}: heartbeat has no last_run"]
    run_date = run.get("run_date")
    try:
        age = (today - datetime.strptime(str(run_date), "%Y-%m-%d").date()).days
    except ValueError:
        return [f"{label}: unreadable run_date {run_date!r}"]
    if age > STALE_AFTER_DAYS:
        out.append(f"{label}: SILENT — last run {run_date} ({age} days ago)")
    if run.get("canonical") is not True:
        out.append(f"{label}: NON-CANONICAL on {run_date} — {run.get('reason', 'no reason recorded')}")
    if run.get("halted") is True and run.get("canonical") is True:
        out.append(f"{label}: HALTED on {run_date}")
    return out


def judge_source_register(label: str, hb: dict, required: bool) -> Tuple[List[str], List[str]]:
    """(problems, notes) in one account's ``source_register`` block. A MISSING block (when
    one is required), a block that says the register FAILED, or one left over from another
    run is a problem; a degraded but working register is a note — its own notify channel
    already fired, and a nightly that is red every time a path degrades is one nobody reads."""
    run_date = str((hb.get("last_run") or {}).get("run_date") or "")
    blk = hb.get("source_register")
    if not isinstance(blk, dict):
        return ([f"{label}: no source_register block on {run_date} — the run did not reach its "
                 f"tail (killed after trading?) or the register could not be written"]
                if required else []), []
    why = " | ".join(str(p) for p in (blk.get("problems") or [])[:3]) or "no reason recorded"
    if blk.get("failed") or blk.get("n_sources") is None:
        return [f"{label}: the source register FAILED on {run_date}: {why}"], []
    if str(blk.get("as_of")) != run_date:
        return [f"{label}: source_register is from {blk.get('as_of')}, not {run_date}"], []
    if blk.get("degraded"):
        return [], [f"{label}: {blk.get('n_problems')} information-path problem(s): {why}"]
    return [], []


def judge_book(name: str, book: dict) -> List[str]:
    """Problems in one live_book/v1 state file."""
    days = book.get("days")
    if not isinstance(days, list) or not days:
        return [f"{name}: no days recorded"]
    out: List[str] = []
    prev: Optional[Tuple[float, float]] = None
    worst: Optional[Tuple[float, str]] = None
    for row in days:
        bg, tg = row.get("book_growth"), row.get("twin_growth")
        if row.get("degraded") or bg is None or tg is None:
            continue
        if prev is not None and prev[0] > 0 and prev[1] > 0:
            gap = (bg / prev[0] - 1.0) - (tg / prev[1] - 1.0)
            if abs(gap) > MAX_ONE_DAY_GAP and (worst is None or abs(gap) > abs(worst[0])):
                worst = (gap, str(row.get("date")))
        prev = (float(bg), float(tg))
    if worst is not None:
        out.append(f"{name}: implausible one-day gap vs twin {worst[0]:+.1%} on {worst[1]} "
                   f"recorded as clean (split or bad mark?) — the record is corrupt from that date")
    parked = 0
    for row in reversed(days):
        if not row.get("degraded"):
            break
        parked += 1
    if parked >= PARKED_SESSIONS:
        out.append(f"{name}: parked {parked} consecutive session(s) — "
                   f"{days[-1].get('reason', 'no reason recorded')}")
    return out


def _load(reader: Reader, key: str) -> Tuple[Optional[dict], Optional[str]]:
    blob, why = reader(key)
    if blob is None:
        return None, f"{key}: {why}"
    try:
        doc = json.loads(blob)
    except ValueError as exc:
        return None, f"{key}: unparseable ({exc})"
    if not isinstance(doc, dict):
        return None, f"{key}: not a JSON object"
    return doc, None


def evaluate(reader: Reader, today: Optional[date] = None) -> FleetVerdict:
    today = today or date.today()
    v = FleetVerdict(ok=True)
    beats: Dict[str, dict] = {}
    for label, prefix in ACCOUNTS.items():
        doc, err = _load(reader, f"{prefix}/data/state/paper_heartbeat.json")
        if doc is None:
            v.unknown.append(f"{label} ({err})")
            continue
        v.checked += 1
        beats[label] = doc
        v.problems += judge_heartbeat(label, doc, today)
    # the register's deploy is observed, not assumed: the first block any account writes
    seen = [str(b["source_register"].get("as_of")) for b in beats.values()
            if isinstance(b.get("source_register"), dict)
            and b["source_register"].get("as_of")]
    for label, doc in beats.items():
        run_date = str((doc.get("last_run") or {}).get("run_date") or "")
        required = (run_date >= SOURCE_REGISTER_REQUIRED_FROM.isoformat()
                    or bool(seen) and run_date >= min(seen))
        problems, notes = judge_source_register(label, doc, required)
        v.problems += problems
        v.notes += notes
    for fname in BOOKS:
        doc, err = _load(reader, f"{BOOK_PREFIX}/data/state/{fname}")
        if doc is None:
            v.unknown.append(f"book {fname} ({err})")
            continue
        v.checked += 1
        v.problems += judge_book(str(doc.get("book", fname)), doc)
    v.ok = not v.problems and not v.unknown
    return v


def main(argv: Optional[List[str]] = None) -> int:
    from scripts import ledger_backup
    v = evaluate(ledger_backup.read_remote)
    print(("HEALTHY: " if v.ok else "NOT HEALTHY: ") + v.detail)
    return 0 if v.ok else 1


if __name__ == "__main__":
    sys.exit(main())
