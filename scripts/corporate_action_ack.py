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


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--marks", required=True, help="a LOCAL price_basis_marks.json")
    ap.add_argument("--list", action="store_true", help="print the freezes and exit")
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
        if not a.ticker:
            raise ValueError("--ticker is required (or --list)")
        print(ack(Path(a.marks), a.ticker, a.who or "", a.reason or ""))
        return 0
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
