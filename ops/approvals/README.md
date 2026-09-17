# The approvals queue — Phase-6 rung 0

**Every judgment gate the human holds today, they still hold — asynchronously.** That is
the constitution's promise. This directory is its mechanism: a scheduled pass never
decides anything a human decides today; it PREPARES the decision with its evidence
attached, so answering costs one action instead of a relay.

## Answering
Open the entry, set `status:` in the frontmatter to `approved` or `declined`, commit.
**The pass that raised it never acts on it — answering is the action.** For a merge
approval, approving means *you* merge; rung 0 cannot and does not.

## Why tracked, and why one file each
**Tracked**, by ruling: *a gitignored gate is an uninspectable gate*. What was asked,
when, on what evidence, and what was answered all live in git history rather than on one
machine's disk.

**One file per decision**, deliberately: a single shared queue file makes every answer a
conflict-prone edit and makes "what changed" unreadable. Here the diff IS the audit
trail — creation is the ask, the status line is the answer.

## Statuses
| status | meaning |
|---|---|
| `pending` | open; awaiting a human |
| `approved` / `declined` | answered; the pass never re-asks, in either direction |
| `withdrawn` | the question stopped being live (e.g. the branch was merged or deleted) before it was answered |

A decision is **never re-asked once answered** — including declined. Re-asking something
a human already refused is how an automated queue becomes something people stop reading.

Stale entries are **withdrawn, never deleted**: the answer supersedes the question, it
does not erase that it was asked.

## What this queue is not
It is not a task list and not a notification feed. Every entry is a decision that is
*already prepared* and blocked only on judgment. If an entry can be resolved without a
human, it should not be here.
