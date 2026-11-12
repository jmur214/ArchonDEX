---
name: reversion-harness-and-worktree-bash
description: How to prove locks by reversion without touching git (mutate-run-restore harness printing the first E-line), and the worktree-isolation bash refusals hit on 2026-11-12
metadata:
  type: feedback
---

Prove every lock by REVERSION with a scratch harness: for each mode, replace one exact source string
(assert count == 1), run only the locking tests via `python -m pytest -q -p no:cacheprovider <ids>`,
require a non-zero exit, restore the original bytes and assert the md5 matches. Print the FIRST `E ` line,
not the summary: it shows whether the test caught it or an unrelated crash/rail did (on T-387 one mode was
caught by the test, not the rail I meant to prove — the summary line alone hid that).

**Why:** a lock that passes under its own reversion is vacuous; and "it failed" is not "it failed for the
intended reason" (the user's standard: reversion-proven locks, honest about which rail fired).
**How to apply:** keep the harness in the scratchpad (no git stash/reset needed); report each mode with
its failure line.

Worktree-isolated bash: commands chaining `git` with `;`/`&&`, `ls` of main-tree paths inside a git
compound, or Python heredocs naming main-tree paths alongside git were REFUSED as "too complex to verify".
Use separate plain `git` calls run from the worktree, and write Python to the scratchpad and run it by path.
