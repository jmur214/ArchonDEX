---
name: t391-honest-n-standalone-trials
description: T-391 (2026-11-12) — what the honest-N "267" and "231" really contain, the 37-trial gap the hand count missed, and the unmerged branch that adds standalone trials to the gate (R2 gated, R3 reported)
metadata:
  type: project
---

The "267" quoted beside the gate's N is an N_eff, NOT a raw count: ruling 9.2 = 36.5 (258 curve-bearing executed
controller trials, compressed) + 231 (registry curve-less rows at raw). The registry's 231 = 125 lost May run rows
(source NULL) + 106 `ledger:<task>` rows from `scripts/backfill_run_registry_t336.py` (26 tasks, 2026-08-06). So
standalone trials are inside the 267 ONLY via those 26 tasks (the July T-306 series is inside). 37 standalone trials
from 2026-06-18..08-28 (T-213…T-341, many with no ledger row or an N-less ledger row) are in neither; 16 more since
10-13 (B-1 6, T-379 2, B-9 2, B-2 2, B-5 1, B-6 1, B-10 2, B-8 0). S = 53.

Branch `referee/honest-n-trials-recorder-t391` (commits edc103a §1, 080aff1 code+record, 2bbff22 tests, 906b67e
docs): committed record `config/honest_n_trials.json`, gate = registry N_eff + S at raw (R2) 36.92 → 89.92; R3
(9.2 for all curve-less, computable from the pinned 09-30 artifact's funnel.after_dedupe 252) reported 324.28.
UNMERGED — user decides merge, R2 vs R3, 12 unresolved items (U1 T-193's 35 VOID is the big one).

REVIEW ROUND 1 (2026-11-13, NOT READY → follow-ups): my first inventory was itself short by 7 (T-236, T-247, T-249,
T-252 ×3, T-263) — I had swept only docs/Audit|Sources|Measurements for `+=`/`+k` forms and missed `N_trials = k`,
lineage tallies, script docstrings (`scripts/*_tNNN.py`) and `docs/State/conditional_shelf.md`; and I had withheld
T-263 on a reason I never checked ("no doc on main" — the script was on main). Now S = 96 (60 firm + 36 pending a
ruling: T-193 35, T-237 1); R2 132.92, R3 367.28. Lesson: an inventory sweep must cover scripts + State files and
every assignment form, and a "not on main" claim must be grepped before it is written. docs/ is NOT in the backtest
image, so the gate can only check citation existence where docs/ exists.

REVIEW ROUND 2 (2026-11-13): my gated rule R2 = N_eff(registry) + S counted NONE of the 252 executed
controller/cloud trials (registry and artifact population are DISJOINT — I wrote "inside the executed universe" as
if that put them in the gate; only R3 had them). Now R2′ = 36.92 + N_eff(executed 252) 40.28 + S; S = 100 (60 firm +
40 pending); gated 177.20, R3 371.28. Lesson: when a rule sums populations, list every population and name the term
each one lands in before calling anything "covered".

DIRECTOR'S CORRECTION (2026-11-13): I offered "R2′ or R3" as the user's choice; ruling 9.2 (no borrowed credit,
curve-less at raw) had ALREADY decided it. Gate = R3 = N_eff(executed 252) 40.28 + registry 231 at raw + S 100 =
371.28 (331.28 without pending rows). Lesson: before listing a referee choice as open, check whether a standing
ruling already closes it. Also: the session scratchpad does NOT survive between sessions — the reversion harness
and the backfill builder were lost; the harness now lives at `tests/_drivers/t391_reversion_harness.py`. Commit
any harness a reviewer must re-run.

**Why:** the brief's "hand count ≥ 283" assumed the 267 covered all pre-10-13 trials; it does not.
**How to apply:** before quoting honest N, run `python -m scripts.honest_n_trials show` if merged; otherwise cite the
proposal `docs/Sources/proposal_honest_n_trials_recorder_t391_2026-11-13.md` §1.2. Any new pin-input requirement
breaks every temp-pin fixture (4 test files) — `tests/_honest_n_trials_fixture.py` is the shared S=0 helper. See
[[reversion-harness-and-worktree-bash]].
