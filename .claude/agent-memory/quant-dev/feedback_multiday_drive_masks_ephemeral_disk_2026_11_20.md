---
name: multiday-drive-masks-ephemeral-disk
description: A multi-day main() drive on ONE persistent tmp root hid a step-order reversion that bites only on the cloud's ephemeral disk; pin each assertion to the day's own rows
metadata:
  type: feedback
---

When a lock drives `run_paper_cloud_day.main()` over several days on one tmp root, files a LATER step of
day 1 leaves on disk (step 7's alt-data pull) are already present for day 2's earlier readers. A cloud
container never has that: each run starts empty and only S3 pulls fill it. In T-412 the step-order reversion
(alt-data pulled only in step 7) still PASSED the eval lock, because day 2 retried day 1's unresolvable rows
against the leftover hoard and the test keyed the log by prediction_id (last row wins). Only the register
lock caught it. Fix: assert on rows stamped with the day under test (`resolved_at == DAY1`) and on that
day's own printed line.

**Why:** a lock that passes under its own reversion is vacuous, and this one passed for a reason that is
specific to the test's persistent disk — exactly the environment difference the defect lives in.
**How to apply:** in every multi-day drive, ask "could day N+1 succeed on something day N's tail left
behind?" — if yes, pin the assertion to day N, or rebuild day N+1's root from the stub S3 only. Always run
the mutate-run-restore harness ([[reversion-harness-and-worktree-bash]]) and read which test's E-line fired.
