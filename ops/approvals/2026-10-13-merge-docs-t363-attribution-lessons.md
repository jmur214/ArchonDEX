---
id: merge-docs-t363-attribution-lessons
status: approved
kind: merge
asked_by: agent_e
asked_on: 2026-10-13
---

# Merge `docs/t363-attribution-lessons`

Docs only — two `lessons_learned.md` entries and the T-363 `TASK_LEDGER.md`
row. No code, no config, no deploy surface. Raised at the director's
instruction after T-363's three items were accepted.

## Evidence
- branch `docs/t363-attribution-lessons` is 1 commit ahead of **local** `main`
  (verified by git: `git rev-list --count main..HEAD` = 1), branched off local
  main at `84f4eee`. Deliberately NOT off `origin/main`, which is 35 commits
  behind local main; nothing is pushed — that remains the user's gate.
- commit: `6e60fea docs(t363): verify a deploy by something the new code emits
  — and a retraction of a check that could not fail`
- files touched: `docs/State/lessons_learned.md`, `docs/State/TASK_LEDGER.md`
- `scripts/doc_lint.py` exit 0
- **No test run.** Docs-only change and the director asked for no compute while
  C's cells hold the Mac. If the reviewer wants a suite run before merging,
  say so and it runs when the machine is free.

## What it records
1. **The attribution method** — verify a deploy by something the new code emits
   that the old code could not; the deploy record claims, the artifact proves.
   Worked example: Batch retains ~5 job summaries and reached only to 10-07,
   so `:38`'s first firing (09-30) was attributed by `stop_reason` being ABSENT
   in the 09-29 raw archive and PRESENT from 09-30. Includes the negative half
   — two candidate markers that did NOT distinguish, because they shipped in
   earlier revisions.
2. **The retraction** — T-362's claim that 09-21 "passes `validate_note`" was a
   vacuous check (the function returns a tuple and never raises). The
   UNEXPLAINED verdict stands; its stated reason is withdrawn. Generalised to:
   before trusting a local reproduction of a production failure, run it against
   a known-bad input and confirm it CAN fail.

## Not in this branch
The approved one-line `loc`-in-status fix (so the next schema failure names its
field) is a SEPARATE unit, to be branched and queued after C's cells free the
machine — it needs a suite run.

## To answer
Set `status:` to `approved` or `declined` in the frontmatter above and commit.
