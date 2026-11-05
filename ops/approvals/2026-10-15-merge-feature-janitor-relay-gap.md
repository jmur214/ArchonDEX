---
id: merge-feature-janitor-relay-gap
status: withdrawn
kind: merge
asked_by: director_pass
asked_on: 2026-10-15
---

# Merge `feature/janitor-relay-gap`

A merge decision is ready for `feature/janitor-relay-gap`.

**This pass did not merge it and cannot.** Rung 0 is prepare-only: the judgment in a merge is the gated part, and only the transport was ever the cost being retired.

## Evidence
- branch `feature/janitor-relay-gap` is 66 commit(s) ahead of origin/main (verified by git, not by any outbox claim)
- newest commit: feat(janitor): relay_gap — every row states WHICH TREE its checks certified; WARN on a gap, never FA

## To answer
Set `status:` to `approved` or `declined` in the frontmatter above and commit.
The pass that raised this never acts on it — answering is the action.

## Withdrawn
On 2026-10-23 the branch was no longer ahead of origin/main — merged, deleted, or rebased away. The decision this asked for is no longer open; the record of having asked stands.
