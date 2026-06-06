#!/usr/bin/env python3
"""Coordination outbox watcher — notify the director when any agent finishes.

Eliminates the "user forgets to relay 'X done'" failure mode documented in
docs/Coordination/PROTOCOL.md (Failure modes & known risks). Polls every
agent outbox in data/coordination/; when an outbox's mtime + content hash
changes, prints a one-line notification with the new headline.

Scale-ready: discovers agents by globbing agent_*_outbox.md, so it works for
A/B today and any number of agents (C, specialists) without code change.

Usage:
    python scripts/watch_coordination.py                 # poll forever, 10s
    python scripts/watch_coordination.py --interval 5    # custom interval
    python scripts/watch_coordination.py --once          # one snapshot + exit
    python scripts/watch_coordination.py --headline-lines 5

Runs in the DIRECTOR worktree (data/coordination/ lives here; agent worktrees
symlink to it). Read-only: never writes the coordination files.
"""
from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COORD = REPO / "data" / "coordination"


def _agent_outboxes() -> list[Path]:
    """All agent outboxes, sorted; discovers any agent_<x>_outbox.md."""
    return sorted(COORD.glob("agent_*_outbox.md"))


def _agent_name(outbox: Path) -> str:
    # agent_a_outbox.md -> A
    stem = outbox.name.removeprefix("agent_").removesuffix("_outbox.md")
    return stem.upper()


def _fingerprint(p: Path) -> tuple[float, str]:
    """(mtime, content-hash). Content hash guards against mtime-only touches."""
    try:
        data = p.read_bytes()
    except OSError:
        return (0.0, "")
    return (p.stat().st_mtime, hashlib.md5(data).hexdigest())


def _headline(p: Path, n_lines: int) -> str:
    """First n non-empty content lines (skip the title + blank lines)."""
    try:
        lines = [ln.rstrip() for ln in p.read_text().splitlines()]
    except OSError:
        return "(unreadable)"
    out: list[str] = []
    for ln in lines:
        if not ln.strip():
            continue
        if ln.startswith("# "):  # task title — keep it, it carries the verdict
            out.append(ln[2:].strip())
            continue
        out.append(ln.lstrip("-* ").strip())
        if len(out) >= n_lines:
            break
    return " | ".join(out[:n_lines]) if out else "(empty)"


def _ts() -> str:
    # Local clock; avoids importing datetime-with-now banned elsewhere — time.strftime is fine.
    return time.strftime("%H:%M:%S")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interval", type=float, default=10.0, help="poll seconds (default 10)")
    ap.add_argument("--once", action="store_true", help="print current state once and exit")
    ap.add_argument("--headline-lines", type=int, default=4, help="headline lines to show on change")
    args = ap.parse_args()

    if not COORD.is_dir():
        print(f"[watch] coordination dir not found: {COORD}")
        return 1

    boxes = _agent_outboxes()
    if not boxes:
        print(f"[watch] no agent outboxes under {COORD} (looking for agent_*_outbox.md)")
        return 1

    state: dict[Path, tuple[float, str]] = {b: _fingerprint(b) for b in boxes}

    if args.once:
        for b in boxes:
            print(f"[{_agent_name(b)}] {_headline(b, args.headline_lines)}")
        return 0

    print(f"[watch] watching {len(boxes)} outbox(es) every {args.interval:g}s — "
          f"agents: {', '.join(_agent_name(b) for b in boxes)}. Ctrl-C to stop.")
    try:
        while True:
            time.sleep(args.interval)
            # Re-glob each cycle so a NEW agent (C, specialist) is picked up live.
            for b in _agent_outboxes():
                fp = _fingerprint(b)
                if b not in state:
                    state[b] = fp
                    print(f"[watch {_ts()}] NEW agent online: {_agent_name(b)}")
                    continue
                if fp != state[b] and fp[1]:
                    state[b] = fp
                    print(f"\n*** [{_ts()}] AGENT {_agent_name(b)} REPORTED ***")
                    print(f"    {_headline(b, args.headline_lines)}")
                    print(f"    -> read {b.relative_to(REPO)}")
    except KeyboardInterrupt:
        print("\n[watch] stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
