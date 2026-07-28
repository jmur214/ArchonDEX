# Archived git stashes — agent-d worktree, cleared 2026-07-30 (approved; `[NN-ARCHIVE]` honored)

Seven stale stashes accumulated across long-closed tasks. Each diff is preserved here VERBATIM
(`stash_<n>.diff`, restore with `git apply`) and then dropped from the stash list. Nothing deleted.

| stash | task / branch | why superseded |
|---|---|---|
| 0 | T-232 `feature/no-borrow-cash-budget-t232` — multi-name no-borrow proof (Σ executed == equity, 0 borrow) | T-232 CLOSED and merged; the no-borrow finding is recorded (borrow = held-position accumulation, not per-name sizing) |
| 1 | T-218 `feature/factor-neutrality-sizing-t218` — re-smoke: turnover 17×→3.2× but still return-dilutive | T-218 closed H0-leaning; the sizing family is superseded by the sleeve/offense arc |
| 2 | T-159 `feature/divergence-monitors-t152` — stray `sync_docs` index regen | regenerable output, never source (`python scripts/sync_docs.py` reproduces it) |
| 3 | T-114 `feature/ecr-rebuild-static20-t109` — outbox watcher + ledger-conflict-free protocol | the T-114 protocol shipped (propose rows in OUTBOX, director writes TASK_LEDGER) |
| 4 | T-054 `feature/production-hunt-ticker-wiring-fix` — wire `ticker=` through `hunt()` | fix landed long ago; Engine D has since been superseded by the PIT/foundry lineage |
| 5 | `cap-recalibration` — leftover round-x residue | scratch residue from the cap-cache work (T-215 prep), no longer applicable |
| 6 | `per-ticker-score-logging` — WIP carried in from another agent's cap-recal isolation | cross-agent scratch, not this lane's work |

**Restore any of these with:** `git apply Archive/git_stashes_2026_07_30/stash_<n>.diff`
