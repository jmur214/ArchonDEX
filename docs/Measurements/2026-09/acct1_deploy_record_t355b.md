# Account-1 deploy record — `paper-sha-6dcd923` (jobdef `:35`)

**Date:** 2026-09-17 (pre-market) · **Owner:** E · **Approved:** director, T-355 merge

## What shipped

| | |
|---|---|
| image | `paper-sha-6dcd923` (merged main) |
| jobdef | `archondex-paper-cloud-day:34` → **`:35`** |
| schedule | `archondex-paper-daily` — ENABLED, `cron(45 9 ? * MON-FRI *) America/New_York` |
| method | `scripts/redeploy_one_account.py` (clone-from-LIVE, image-only diff asserted) |
| drift gate | **No drift. Safe to provision.** |
| fleet after | acct-1 `:35` 6dcd923 · acct-2 `:19` dc46c68 · **acct-3 `:7` c288c42 (deliberately unchanged)** |

## The image bump carries 29 commits, and what makes that safe

Account-1 had been held at `c288c42` since 2026-09-11 while accounts 2 and 3 were
observed, so this is not a one-change deploy. It carries **13 merges**:

`t355-E` (this change) · `survival-B` · `t356-D` (the durability sweep) ·
`t350g-E` · `t351-C` (the tracker) · `reexec-B` · `t354-A` (the deploy-candidate
digest row) · `t350f-E` · `forensics-B` · `t350e-E` · `t350d-E` ·
`bootstrap-guard-B` · `t353-A`

**What makes a 29-commit bump safe is not that each was reviewed — it is the
drift gate.** `diff_live_paper_infra.py` compares the LIVE fleet (schedules,
jobdef targets, scheduler-role submit policy, alarm arming and suppression
reasons) against what the provisioner would render, and it reports **no drift**
after the deploy. The jobdef itself was cloned from the live `:34` with the
**image as the only delta, asserted programmatically** — so nothing in the
account's configuration moved: strategy `trend_sleeve`, cap `10000`, DLQ, and
the infra-only retry classes (`CannotPullContainerError*`→retry,
`Task failed to start*`→retry, application exit→EXIT) all verified by readback
after the write, not assumed from the write.

## NO cohort stamp — stated explicitly so nobody re-derives it later

**2026-09-17 is NOT an information boundary.** This deploy adds a *consumer*
downstream of the analyst notes (the agentic arm's shadow book) and retires a
desk that never consumed anything. **It changes nothing the analyst arm sees** —
not the prompt, not the tool set, not the information bundle, not the model. The
`price_fed` cohort stamped `2026-09-11` is unaffected and no new cohort is
opened. Per T-351's schema, a stamp records a change to the *information set*;
this is not one.

## First artifact — still pending [NN-FIRST-ARTIFACT]

The deploy is not the claim. The claim is `llm_shadow_book_agentic.json` in S3
with `n_days ≥ 1` after the 09:45 ET firing. Until then the agentic arm has a
book in code and no book in fact — which is exactly the state the retired desk
was in for 36 sessions.

## Tooling note

This was the redeploy tool's second use and it found a naming exception:
account-1's jobdef `archondex-paper-cloud-day` is driven by schedule
`archondex-paper-daily`, not `…-cloud-day-daily`. The convention default failed
**loudly** (`ResourceNotFoundException`) rather than doing anything wrong, and a
`--schedule` override now carries the exception at the flag. The absence also
exposed a missing guard, now added: the schedule being rewritten must already
target the same jobdef **name** whose revision was just registered — otherwise a
wrong pair could point one account's cron at another account's jobdef, which is
an account running the wrong strategy on the right schedule.
