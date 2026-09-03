# Janitor nightly report — 2026-09-02

Rung-0 autonomous pilot (`docs/Core/autonomous_development_prestatement.md`). This surface is watched by the `janitor_ran_nightly` clock: if it stops being written, the census alarms like any dead feed.

| check | result | detail |
|---|---|---|
| worktree_canon | FAIL | 2 uncommitted path(s); 0 commit(s) behind origin/main |
| doc_lint | PASS | all doc-lint checks pass |
| census_review | PASS | 23 clocks registered |
| suite | FAIL | 3 failed, 3605 passed, 22 skipped, 4 deselected, 3 xfailed, 312 warnings in 249.72s (0:04:09) |

**Fix phase:** fix phase DISABLED (checks-only run — the record comes first)

