---
name: t412-information-reaches-desks
description: T-412 (T-411 Phase 1) build facts that are NOT in the code — the cloud 0/59 eval reason is the PRICE resolvers', the event desk had three dead links not one, the census eval clock can never MISS, real 8-K feed volumes, and the cross-account alt-data race
metadata:
  type: project
---

Built 2026-11-20 on branch `feat/t412-information-reaches-desks-2026-11-20` (unmerged at writing;
the director merges/deploys on the owner's word). Findings a future session would otherwise re-derive:

- **The cloud eval's `source_absent_or_stale: 59` is the PRICE resolvers' reason code** (price_above /
  relative_return / dd_exceeds). `event_occurs` emits `source_absent_or_unsettled`. So the alt-data step
  order alone cannot explain the 0/59; the harness's non-sleeve fallback reads `data/processed/<SYM>_1d.csv`,
  which the paper image does not carry. T-412 added a live fetch for every due symbol plus an EVAL line that
  names today's unresolved reasons AND symbols — read that line on the first artifact before blaming anything.
- **The event desk had THREE dead links**, not one: (1) no 8-K panel in any container; (2) its loader matched a
  flat `event_call/v1` dict while `event_service` writes the eval harness's NOTE shape (`note_date`, call fields
  under `event_call`) — it would have found no call ever; (3) the driver priced TODAY's calls while `record()`
  opens the PRIOR session's (the T-343 thesis-book bug, again). The T-342 liveness row also scanned a
  top-level `symbol` the ledger never writes.
- **Census clock `eval_scored_when_due` can never MISS**: it reads `resolve_by`/`horizon_end`/`brier`/`scored_at`;
  log rows carry `resolve_date`/`resolved_at`/`resolvable`. It reports NOT_DUE forever. Reported, NOT fixed
  (the source register's eval outcome check now carries that signal).
- **8-K feed, measured live 2026-11-20**: 503 current S&P members → 494 CIKs; 2 index days → 449 8-Ks in the
  index, 49 tracked, 44 submissions requests in 47.5 s; panel ~5 KB/day; ticker map 870 KB (weekly refresh);
  58 allowlisted items in a 3-day window. The 8-K PRIMARY document is a cover page (~3k chars); the press
  release is Exhibit 99.1, which the interpreter never sees — a real information-quality limit.
- **The `altdata/` S3 prefix is SHARED by all three accounts.** My first claim that the race "self-heals" was
  WRONG (review 2026-11-24: S3 froze at 2 of 16 filings). Fixed: only account 1 pulls/gates/pushes the 8-K files,
  and any push uploads only what that run changed. Residual: two accounts that both CHANGE the same feed
  within minutes are still last-writer-wins.
- The event interpreter's window now reaches back to the last session (the driver's own SPY series — the holiday
  list ends 2026-12 and MarketCalendar caches one month); the [NN-AI-GATE] as_of guard is unchanged.
- Kalshi drops `expiration_time` on finalized markets' rows: read the last RECORDED value per ticker.

**Why:** each of these looked like the one cause of a symptom and was not. **How to apply:** before quoting
T-411's "step order" as the 0/59 cause, or "no feed" as the desk's only defect, read this; on the first
cloud artifact check the EVAL `today:` line and the heartbeat `source_register.problems`.
See [[multiday-drive-masks-ephemeral-disk]] and [[sec-edgar-forward-8k-formats]].
