# Archived launch agents — swept 2026-09-10

Moved here per `[NN-ARCHIVE]` (**moved, never deleted**), `launchctl unload`ed first.
Restore with `cp <plist> ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/<plist>`.

| job | why retired |
|---|---|
| `com.archondex.t295-population` | T-295 completed 2026-07-27. **It kept firing twice daily (22:30 / 06:30) until today — 88 firings, 60 of which printed "already DONE … unload the job" into a log nobody read.** |
| `com.archondex.t289` | T-289 closed July 2026; `RunAtLoad` only, re-ran at every login, targeting the agent-d worktree. |
| `com.archondex.t289tests` | Same task, `RunAtLoad` only; last wrote its probe log 2026-09-02. |

**Still live (deliberately kept):** `com.archondex.altdata-archive`, `com.archondex.janitor`.

## The lesson, and what now enforces it
The t295 job was not broken. It correctly detected it was finished and **said so, in
plain words, 60 times** — into a log with no consumer. That is the same shape as every
other finding in this program: a channel that was RIGHT, and unread.

`scripts/launchd_canon.py` now audits the `com.archondex.*` namespace against a registry
where each entry must state **what consumes the job's output**, and the nightly janitor
runs it as the `launchd_canon` check. It is **bidirectional** on purpose:
- **ORPHANED** — registered, task closed (this sweep's class).
- **MISSING** — in the registry but NOT registered: a schedule everyone believes is
  running that quietly is not. That is the 2026-07-13 silent-outage shape, and a
  one-directional check would have caught the zombies while missing the outage.

The registry is on the janitor's own denylist: an autonomous session may neither grant
itself a job nor exempt a rogue one.
