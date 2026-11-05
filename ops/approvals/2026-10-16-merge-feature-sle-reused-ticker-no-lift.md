---
id: merge-feature-sle-reused-ticker-no-lift
status: withdrawn
kind: merge
asked_by: director_pass
asked_on: 2026-10-16
---

# Merge `feature/sle-reused-ticker-no-lift`

A merge decision is ready for `feature/sle-reused-ticker-no-lift`.

**This pass did not merge it and cannot.** Rung 0 is prepare-only: the judgment in a merge is the gated part, and only the transport was ever the cost being retired.

## Evidence
- branch `feature/sle-reused-ticker-no-lift` is 254 commit(s) ahead of origin/main (verified by git, not by any outbox claim)
- newest commit: fix(data): SLE re-kinded as a class (i) REUSED TICKER that is NEVER lifted — lift_verified() refuses

## To answer
Set `status:` to `approved` or `declined` in the frontmatter above and commit.
The pass that raised this never acts on it — answering is the action.

## Withdrawn
On 2026-10-23 the branch was no longer ahead of origin/main — merged, deleted, or rebased away. The decision this asked for is no longer open; the record of having asked stands.
