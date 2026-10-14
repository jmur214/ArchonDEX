---
id: merge-feature-observability-backup
status: pending
kind: merge
asked_by: agent_b
asked_on: 2026-10-13
---

# Merge `feature/observability-backup`: nightly guarded S3 copy of the honest-N inputs

Adopted from R's T-356b review. Since RR-3, `data/observability/run_registry.sqlite` (N_raw) and
`n_effective_*.json` (ρ̄ gate inputs) are Discovery's **fail-closed N**, and both are gitignored single
copies. D's census (`core/durability_census.py:213,227`) records the hazard. `rebuild()` after a loss
re-reads local `trade_logs`, and 125 run rows exist nowhere else. So the rebuilt N is **smaller** and
the gate **looser**, with no alarm. **Agent B did not merge this and cannot.**

## What it does
This extends the ledger's survival job in `scripts/ledger_backup.py` and keeps the same rails: a dated
daily key, deferral when the laptop's network is down, and `allow_rewrite` never on the nightly path.

- **The registry is judged on the `run_id` set, not on bytes.** SQLite rewrites the whole file on every
  rebuild.
  - A local copy that lacks **any** run the remote holds is **REFUSED**.
  - It is pushed as a consistent snapshot (SQLite's backup API, with the source opened read-only), so
    the job never writes the gate's input.
  - "Unchanged" is detected by a SQL-dump digest, so a SQLite library upgrade is not mistaken for a
    change.
- **ρ̄ artifacts are immutable by name.** A changed `n_effective_<date>.json` is **REFUSED**.
- **An unreadable remote copy is never overwritten.**
- **Janitor wiring:**
  - a start-of-run `observability_backup` check;
  - the end-of-run push, via `survival_syncs()`;
  - both are non-fatal, and one record's failure never costs the other its push.

Commit `df7f7c9`.

## Evidence
- 59 tests pass (new, ledger, and janitor).
- A fake-S3 loss drill runs four nights: first push; a quiet night that pushes nothing; a rebuild
  after loss (2 of 5 runs), which is **REFUSED** with the remote byte-untouched; then an extension,
  which is pushed.
- **Reversion-proven.** Dropping the lost-rows refusal, unregistering the check, or passing
  `allow_rewrite` on the nightly path makes 5 tests fail. Restored, all pass.
- On the real host, read-only: two snapshots are byte-identical, the live registry is untouched, and
  231 run ids read back. `OBS_DIR` resolves to the main tree's `data/observability` from any worktree.
- The 09-16 lock grepped `main()`'s source for the call. It broke when the call moved into
  `survival_syncs`, and it is now an **execution** lock.

## Honest limits
- **Not done until the first artifact exists.** No S3 write was made here. The first real push
  happens at the end of the first nightly run after merge. `ops/observability/` is a **new prefix**,
  and IAM write access to it is unverified. An AccessDenied would print as REFUSE in the janitor log,
  and the next morning's check would be red, so it fails loudly.
- **One red night, and it is true.** The start-of-run check runs before that night's push, so the first
  night after merge reads `observability_backup FAIL — single copy`. That is the actual state today.
  It turns green the next night if the push lands.
- **Census status is not edited.** Both entries remain owned KNOWN_GAPs in D's census. Re-classifying
  them after the first verified push is D's or the referee's call.

## Decision for the director
1. Merge.

## To answer
Set `status:` to `approved` or `declined` in the frontmatter above and commit.
