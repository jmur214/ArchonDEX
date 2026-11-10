#!/usr/bin/env python
# scripts/corporate_action_ack.py
"""Acknowledge a corporate-action FREEZE in a local copy of the price-basis marks file.

The corporate-action gate (``paper_trader/corporate_actions.py``) persists every
freeze in ``data/state/price_basis_marks.json`` and never releases one because
a price drifted. A freeze releases only by a feed-confirmed split that matches
the move, by the feed answering "no split" on three consecutive sessions, or by
THIS: an operator saying, in writing, why the freeze may be lifted.

What it does: it stamps ``ack: {who, why, at}`` onto the named ticker's freeze
entry and appends a line to the file's own journal. The NEXT run of the daily
driver reads the ack, releases the freeze, journals the release, and lays a
fresh mark. If the underlying condition still holds (a mixed-basis position is
still mixed), that run freezes the ticker again — an ack cannot make an
unprovable share basis provable.

What it never does: touch S3 (pull the file, ack the local copy, push it back
through the normal durable-state path — a separate, propose-first step), edit
any other file, or run without a reason.

Run:
  python -m scripts.corporate_action_ack --marks /path/to/price_basis_marks.json --list
  python -m scripts.corporate_action_ack --marks /path/to/price_basis_marks.json \\
      --ticker MTUM --who jackson --reason "real -31% session, confirmed against the tape"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path
from typing import Optional, Sequence

from paper_trader.corporate_actions import GateState

MIN_REASON_CHARS = 12


def ack(marks_path: Path, ticker: str, who: str, reason: str,
        now: Optional[_dt.datetime] = None) -> str:
    """Stamp the acknowledgement; return the line that was journaled. Raises
    ``ValueError`` (nothing written) on any refusal."""
    raw = str(marks_path).strip()
    if raw.lower().startswith("s3:"):
        raise ValueError("S3 paths are refused — acknowledge a LOCAL copy")
    if not Path(marks_path).is_file():
        raise ValueError(f"{marks_path} does not exist")
    if not reason or len(reason.strip()) < MIN_REASON_CHARS:
        raise ValueError(f"a reason of at least {MIN_REASON_CHARS} characters is required — "
                         "an acknowledgement without a why is not one")
    if not who or not who.strip():
        raise ValueError("--who is required: an acknowledgement is signed")
    st = GateState.load(Path(marks_path))
    if any("marks file unreadable" in p for p in st.problems):
        raise ValueError(f"{marks_path} is unreadable: {st.problems}")
    t = ticker.upper()
    if t not in st.frozen:
        raise ValueError(f"{t} is not frozen in this file (frozen: {sorted(st.frozen)})")
    at = (now or _dt.datetime.now(_dt.timezone.utc)).isoformat()
    st.frozen[t]["ack"] = {"who": who.strip(), "why": reason.strip(), "at": at}
    line = {"date": at[:10], "ticker": t, "event": "ack", "who": who.strip(),
            "why": reason.strip(), "at": at, "freeze": st.frozen[t].get("reason")}
    st.journal.append(line)
    st.save(Path(marks_path))
    return f"ACK {t} by {who.strip()} at {at}: {reason.strip()}"


def reset_unreadable(marks_path: Path, who: str, reason: str,
                     now: Optional[_dt.datetime] = None) -> str:
    """The operator's answer to a marks file that EXISTS but cannot be parsed.

    The gate stands the book down on every run while that file is there — the
    freezes it held are unknowable, so it will neither trust it nor write over
    it. This moves the bad file aside (kept, never deleted) and leaves a fresh,
    valid, EMPTY marks file whose journal records who reset it and why. The
    next run is then an ordinary seeding day. Refuses a file that is readable
    (use a ticker ack), a missing reason or name, and any ``s3:`` path."""
    raw = str(marks_path).strip()
    if raw.lower().startswith("s3:"):
        raise ValueError("S3 paths are refused — reset a LOCAL copy")
    p = Path(marks_path)
    if not p.is_file():
        raise ValueError(f"{marks_path} does not exist (an ABSENT file needs no reset: "
                         "the next run simply seeds)")
    if not reason or len(reason.strip()) < MIN_REASON_CHARS:
        raise ValueError(f"a reason of at least {MIN_REASON_CHARS} characters is required")
    if not who or not who.strip():
        raise ValueError("--who is required: a reset is signed")
    if not GateState.load(p).unreadable:
        raise ValueError(f"{marks_path} is READABLE — nothing to reset; its freezes are "
                         "released one ticker at a time with --ticker")
    at = now or _dt.datetime.now(_dt.timezone.utc)
    aside = p.with_name(f"{p.name}.unreadable-{at.strftime('%Y%m%dT%H%M%SZ')}")
    if aside.exists():
        raise ValueError(f"{aside} already exists")
    p.replace(aside)
    fresh = GateState()
    fresh.journal.append({"date": at.date().isoformat(), "ticker": None,
                          "event": "reset_unreadable", "who": who.strip(),
                          "why": reason.strip(), "at": at.isoformat(),
                          "moved_to": aside.name})
    fresh.save(p)
    return (f"RESET by {who.strip()} at {at.isoformat()}: unreadable file kept as "
            f"{aside.name}; the next run is a seeding day — {reason.strip()}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--marks", required=True, help="a LOCAL price_basis_marks.json")
    ap.add_argument("--list", action="store_true", help="print the freezes and exit")
    ap.add_argument("--reset-unreadable", action="store_true",
                    help="the marks file exists but cannot be parsed: move it aside and "
                         "leave an empty valid one (needs --who and --reason)")
    ap.add_argument("--ticker")
    ap.add_argument("--who")
    ap.add_argument("--reason")
    a = ap.parse_args(argv)
    try:
        if a.list:
            if str(a.marks).strip().lower().startswith("s3:") or not Path(a.marks).is_file():
                raise ValueError(f"{a.marks} is not a local file")
            st = GateState.load(Path(a.marks))
            for p in st.problems:
                print(f"PROBLEM: {p}")
            for t, e in sorted(st.frozen.items()):
                print(f"{t}: kind={e.get('kind')} frozen_on={e.get('frozen_on')} "
                      f"ref={e.get('ref_px')}@{e.get('ref_date')} "
                      f"no_split_streak={e.get('no_split_streak')} "
                      f"ack={'yes' if e.get('ack') else 'no'}\n    {e.get('reason')}")
            print(f"{len(st.frozen)} frozen | feed_unavailable_streak="
                  f"{st.feed_unavailable_streak}")
            return 0
        if a.reset_unreadable:
            print(reset_unreadable(Path(a.marks), a.who or "", a.reason or ""))
            return 0
        if not a.ticker:
            raise ValueError("--ticker is required (or --list / --reset-unreadable)")
        print(ack(Path(a.marks), a.ticker, a.who or "", a.reason or ""))
        return 0
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
