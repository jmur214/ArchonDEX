---
name: making-data-visible-switches-on-dormant-code
description: T-412 review lesson — feeding a starved reader activates every downstream consumer that had never run on real data; audit those consumers and shared logs before claiming "no order change"
metadata:
  type: feedback
---

My T-412 build passed 24 reversion-proven locks and I reported "no order change"; a reviewer RUNNING it found
two blockers. The common cause: I tested that data reached the reader, not what the reader then does with it.

- **A shared log is an input to whoever else reads it.** The event desk's predictions went into
  `analyst_predictions.jsonl`; `context_builder.open_predictions` (no row carries `resolved`, so everything is
  "open", capped at 50) feeds the note account 3 TRADES. Parity drives of one day cannot see it.
- **Dormant code runs for the first time.** With alt-data visible, `_fred_asof` carried the last rate forward to
  any FUTURE date: December FOMC "settled" hold in September and a falsifier FIRED. Neither I nor the reviewer's
  list had it; found by asking "what does this function do on an event that has not happened?" Positive
  control: 44/44 finalized KXFED strikes agree with Kalshi's own `result`, 0/236 open ones settle.
- **`fresh` is not `works`.** The register read 14/14 fresh with the eval and the pulse both raising. A
  reader's OUTCOME (raised / refused / produced nothing) is a separate check from its input.
- **`True if ANY synced` + append + push = erased history.** A bounded pull that lands one file, then an archive
  and a sync-up, replaced 117 rows in S3 with 1. A push must be refused after an incomplete pull, and upload
  only what this run changed (`aws s3 sync` uploads whenever SIZES differ, so an older copy wins).
- **A control that always fires proves nothing**: give the fake a healthy world first (the reviewer's SEC fake
  served one index day; my stricter feed made `none` degraded until I fixed the fake).

**Why:** the director had to run a second review cycle; the S3 one would have been unrecoverable data loss.
**How to apply:** when a task's point is "X finally reaches Y", list everything that READS what Y writes, run Y's
code on real data including not-yet-happened and finalized cases, and diff every bundle/ledger a trading
account consumes over a simulated WEEK, not a day. See [[t412-information-reaches-desks]] and
[[multiday-drive-masks-ephemeral-disk]].
