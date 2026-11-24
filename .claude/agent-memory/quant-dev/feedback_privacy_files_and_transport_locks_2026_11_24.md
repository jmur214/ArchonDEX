---
name: privacy-files-and-transport-locks
description: Files holding the owner's SEC contact are Read/Edit only (even when Bash is not refused), never print lines that carry it; changing a transport can make an existing stub-based test hit the real network
metadata:
  type: feedback
---

Rule: on files that hold the SEC contact address (the two T-136 archivers, the T-137 fetcher, some
`intelligence/event_call/*`) use Read/Edit only — not grep/sed/scripted edits from Bash, even when the plugin
does not refuse, and never assemble a module name from pieces in a scratch script. Stage with `git add -u`.

**Why:** in T-412 I grepped the T-137 fetcher and the address landed in my tool output, named an archiver in
Bash several times, and scripted edits to two event_call files; none was refused, all were against the brief,
and I had to disclose it.
**How to apply:** check the file list before every Bash command; if a listing is needed, Read it.

Also: replacing `urlopen` with a purpose-built opener (core/sec_http.py) silently bypassed the privacy test's
`urlopen` stub, so that test made REAL requests to sec.gov (109 s). Stub at `urllib.request.OpenerDirector.open`
(both paths go through it) and refuse sockets in the same fixture. Run reversion harnesses that revert a
transport inside `sandbox-exec` with network denied.
