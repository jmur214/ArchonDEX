"""Launchd canon — registered jobs must map to LIVE tasks, or carry an exemption.

THE CLASS THIS CLOSES. `com.archondex.t295-population` fired twice a day from
2026-07-08 to 2026-09-10 — **88 firings, 60 of which printed "already DONE ...
unload the job"** into a log nobody read. The job correctly detected it was finished,
said so in plain words, and kept running for six weeks because nothing CONSUMED the
message. Two closed T-289 jobs sat registered alongside it. That is the orphaned-
trigger class in launchd clothing, and it is the same shape as every other finding
in this program: a channel that was right, and unread.

THE FIX IS THE CENSUS TRIPWIRE, ONE LAYER DOWN — and it is BIDIRECTIONAL, which is
the part worth keeping:

  * ORPHANED  — registered but not in the registry. A task closed months ago is
    still firing. Wasteful at best; at worst it writes state nobody expects.
  * MISSING   — in the registry but NOT registered. **This is the dangerous
    direction.** It is the 2026-07-13 silent-outage shape: a schedule everyone
    believes is running, that quietly is not. A one-directional check would have
    caught the zombies and missed the outage.

This registry is GATE-SHAPED: it decides what may run unattended on this machine.
It is on the janitor's own denylist, so an autonomous session can neither grant
itself a new job nor exempt a rogue one.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

PREFIX = "com.archondex."

# label -> why this job is LIVE. An entry here is a claim that something still
# consumes its output; state the consumer, not the task name.
LIVE_JOBS: Dict[str, str] = {
    "com.archondex.altdata-archive":
        "the canonical ~EOD (18:30 ET) local alt-data snapshot; consumed by the "
        "feed-health gate in paper_trader/altdata_archive.py",
    "com.archondex.janitor":
        "Phase-6 rung 0; its report is consumed by the janitor_ran_nightly clock",
}


@dataclass
class LaunchdVerdict:
    ok: bool = True
    orphaned: List[str] = field(default_factory=list)   # registered, not live
    missing: List[str] = field(default_factory=list)    # live, not registered
    live: List[str] = field(default_factory=list)

    def report(self) -> str:
        if self.ok:
            return f"{len(self.live)} archondex job(s) registered, all mapped to live tasks"
        bits = []
        if self.missing:
            bits.append("MISSING (believed scheduled, NOT registered — the silent-outage "
                        f"shape): {', '.join(self.missing)}")
        if self.orphaned:
            bits.append("ORPHANED (registered, task closed — unload + archive the plist): "
                        f"{', '.join(self.orphaned)}")
        return " | ".join(bits)


def audit(registered: Iterable[str]) -> LaunchdVerdict:
    reg = {r for r in registered if r.startswith(PREFIX)}
    v = LaunchdVerdict()
    v.orphaned = sorted(reg - set(LIVE_JOBS))
    v.missing = sorted(set(LIVE_JOBS) - reg)
    v.live = sorted(reg & set(LIVE_JOBS))
    v.ok = not v.orphaned and not v.missing
    return v


def registered_jobs() -> List[str]:
    """Labels launchd currently has registered for this user."""
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True,
                             timeout=30).stdout
    except Exception:
        return []
    labels = []
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2].startswith(PREFIX):
            labels.append(parts[2].strip())
    return labels


def audit_live() -> LaunchdVerdict:
    return audit(registered_jobs())
