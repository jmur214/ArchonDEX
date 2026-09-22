# Program Checkpoint Review — the pre-stated ~Sept-20 checkpoint

> **Author:** Agent R, the independent reviewer (not the director, not A–E), assigned by the
> director on 2026-09-17 on the principle that a program should not grade itself.
> **Written:** 2026-09-17 from the record as of that date. **Addendum slot** at the bottom for the
> 09-18 → 09-20 firings (the director pass's first scheduled run, account-2's third and fourth
> days); the verdict below is written so that nothing in those three days can flip it without
> being visible here.
> **The pre-stated test** (`~/.claude/plans/foamy-foraging-horizon.md` §Verification; `forward_plan.md:78`):
> *"~Sept 20 review — if the structural stack is not live and accruing by then, the honest
> conclusion is 'research instrument mistaken for an investment system' and the program re-points,
> with that sentence in the review doc."*

---

## 1. The verdict sentence

**The structural stack is live, and it is accruing — as of 2026-09-17, not 2026-09-15.** The
pre-stated sentence does not apply; the program does not re-point. But the bar was cleared by two
days, not five, and the record that clears it is one durable point long at the time of writing.

## 2. The evidence, term by term

| term | what the bar requires | what the record shows | verdict |
|---|---|---|---|
| **live** | the deploy-candidate allocation trading on a real paper account from a scheduled firing | Arrival event 09-15, scheduled principal, canonical: 12 VOO / 5 MTUM / 1 SGOV, $9,978.42 of the $10k tier, 3 buys no sells, fills verified from S3; shape matched the pre-statement written 09-11 BEFORE the event (`act2_arrival_event_t350.md`). First attempt (09-14) FAILED CLOSED on a `sleeve_cap` NameError — postponed, not corrupted. | **MET 09-15** |
| **accruing** | a forward record that survives to be read | The deploy-candidate tracker was on ephemeral disk — in neither `DURABLE_PATHS` nor S3 — while the account ran canonical (T-351, found 09-16 by C verifying a colleague's flag). 09-15 and 09-16 points were discarded at container exit. Durable from 09-17. The 09-16 digest row exists because it was rendered from the arrival fills, not from the tracker. | **MET 09-17.** Two days of the record are reconstructible-with-labeling; per the lab's own rule they are never blended. |
| **structural stack** | VOO core + momentum satellite + SGOV cash + enforcing wash guard + Rule-B contributions (plan Phase 1 items 1–4) | Core, satellite, cash leg, contributions: built and observed. **Wash guard: enforcing on account-2, but NOT cross-account** — the lot ledger is per-account, account-1 has never written a lot, so the coupling every surface claimed was never in force (T-358, from the fresh-eyes audit A1, corrected same day). | **4 of 5 as specified; the 5th is honestly relabeled and phased.** |

The plan's Phase-1 "first artifacts" were: the arrival-event day (canonical) ✅; the first scheduled
rebalance respecting the bands (not yet — no band has been crossed in two days; expected) ⏳; the
first digest row ✅ (09-16, with the "Coupled" banner since corrected).

## 3. What this checkpoint can and cannot say

- It **can** say the machine executes the allocation a real-money decision would read, at the tier
  the user would start with, with its execution cost in the record from day one.
- It **cannot** say anything about performance. The 60-day evaluability gate reads ~mid-November.
  Two days of NAV is noise, and the lab refuses to quote it (correctly).
- It **cannot** say the stack is +225–430 bps/yr over the robo. That figure is the plan's estimate
  from tax law and arithmetic; it is not a measurement and this review does not promote it to one.

## 4. Grading the program, director included (the reason an outsider writes this)

**What worked, and should be named as working:**
- The pre-statement discipline. The arrival plan was written 09-11, before the event, with the
  failure shapes enumerated; the event matched. That is verification, not narration.
- Fail-closed held twice in one week: the 09-14 NameError postponed rather than corrupted; the
  09-17 wash-guard finding was processed the same day into a relabel-plus-phased-build, with the
  two tests that had locked the false claim reframed rather than deleted.
- The drill week found seven defects no suite had caught, including an alarm channel dead its whole
  life. The instinct to drill on an ordinary Tuesday is the single best habit this program has.

**What did not, and the checkpoint should not soften:**
- **The record carried a false control for a week.** From 09-10 (guard "enforcing") to 09-17, three
  surfaces — the driver comment, the digest banner placed above the number, and a framing fix that
  propagated it — asserted a cross-account coupling that had no feed. Four verifications passed
  because every check asked "is the guard built?", never "has it ever seen a lot?". It was caught by
  an outside audit, not by the record's own instruments. The program's own T-342 lesson describes
  this class exactly; the lesson existed and did not fire.
- **The record's durability was found on day 1 by luck.** The deploy-candidate tracker — the single
  most decision-relevant stream — was not durable until a colleague's flag was verified. The
  durability sweep (T-356) ran the same day and found the autonomy ledger one disk failure from gone.
  Two "records that never accrue" in one week means the class is systemic, not incidental.
- **State drifted seven weeks.** `CURRENT_STATE.md` was last reconciled 07-27 until today; fifteen
  task IDs (T-344 → T-358) had no ledger row; no September session summary existed; the Stop hook
  warned at every session end and was ignored ~45 times. The director's own reconcile today was
  one 20KB line appended to a 40KB line. The truth lived in commit essays and gitignored inboxes.
- **The referee has no owner.** HMM blind pre-2020 (diagnosed 08-26, one-line fix), legacy HMM in
  production, dead Engine-F producers, silent-default excepts on the live path: all open since
  June–August. Assigned today, to B, after B's current plate clears.
- **The runner is a 1,157-line function locked by text tests**, and the one path carrying the real
  forward record is the unrefactored inline one. Every live-path fix approved today lands on top of
  it. Extraction is now sequenced first; it should have been sequenced before Act 2.

**Net grade:** the program did what it said it would do, on the date it said, with the failures loud.
It also spent a week asserting a protection it did not have and seven weeks not knowing what it
had built. Those are process defects in the director loop, not in the workers, and the fixes are
mechanical: durable-by-default for every forward record, liveness checks on every claimed control,
and a current-truth surface that costs less than a page to keep current.

## 5. What the checkpoint re-points, even though the sentence did not fire

1. **Every forward record durable by construction**, not by registry: a writer that is not in a
   survival mechanism in its own venue fails its own suite (D's tripwire is the model; extend it
   from books and trackers to every `data/state/` writer).
2. **Every control on the record carries a liveness question**, rendered where the control is
   claimed: "has this ever fired / ever been fed?" beside "is it built?".
3. **`CURRENT_STATE.md` at one page**, reconciled per merge wave, with the ledger row written in
   the same commit as the merge (done for the fifteen rows today; make it the merge template).
4. **The referee gets an owner and a cadence** (B, then quarterly): the measurement stack's own
   open defects are the program's highest-leverage debt because every verdict reads through them.

## 6. Addendum — 09-18 → 09-20 (to be filled from the artifacts, not from reports)

| date | expected artifact | observed |
|---|---|---|
| 09-18 07:00 | director pass first scheduled firing, observe-only, one report | **OBSERVED** — ledger row `session=director_pass, trigger=scheduled_pass` at 12:00:07Z = 07:00:07 local (Δ 0 min vs the plist; the first schedule-class row whose label is self-evidencing after B's 4c94219 fix) |
| 09-18 09:50 | account-2 third firing; tracker point #2 durable in S3 | **OBSERVED** — `paper_state_offense_sso/data/state/deploy_candidate_tracking.json` in S3 (08:52 local object time) holds points 2026-09-17 and 2026-09-18, both `canonical: true`. **"Accruing" holds.** |
| 09-19 09:50 | account-2 fourth firing | **NO FIRING WAS SCHEDULED** — 09-19 was a SATURDAY and the cron is MON-FRI; the expectation itself was miscalendared (director, filling from the objects 09-22: an expected-artifact row must be checked against the calendar that generates the artifact, or its absence reads as a failure). The next scheduled firings, 09-21 and 09-22, both fired: the tracker in S3 holds FOUR points — 2026-09-17, -18, -21, -22 — all `canonical: true`. |
| 09-20 | this review's verdict re-read against the three rows above | **VERDICT STANDS** (director, 2026-09-22, from the S3 objects per §6's own rule — objects, not outboxes): the tracker accrued on every scheduled trading day through and past the checkpoint window with zero missed points since durability landed. "Live (09-15) and accruing" is now a four-point fact. The pre-stated failure sentence does not apply. |

The verdict in §1 stands unless the addendum shows the tracker not accruing in S3 on 09-18 or
09-19 — in which case "accruing" is not met and the sentence applies.

## 7. The reviewer liveness sweep — first artifact (2026-09-18), per `[NN-FIRST-ARTIFACT]`

The instrument approved by the director on 09-18 (`scripts/reviewer_liveness_sweep.py`; three
rails proven in `tests/test_reviewer_liveness_sweep.py`) was run over the three accounts' real
S3 artifacts and the local autonomy ledger. Full table:
`docs/Measurements/2026-09/reviewer_liveness_sweep_2026_09_18.md`. The rows that matter:

**Retroactive catches — the proof the instrument closes the class it was born from:**

| what | sweep row | the miss it would have caught |
|---|---|---|
| ledger row labeled `scheduled_pass` at **13:37** local vs a 07:00 schedule (Δ 397 min) — plus 18:34 / 18:35 | §3, three `LABEL_MISMATCH` rows, now `annotated: yes` (B's 09-18 correction row) | miss 1 |
| `cash_adj` **ABSENT** on all 43 points (acct-1) and all 2 (acct-2) | §2, `ABSENT`, `in registry: yes` (T-352 declared it) | miss 2 |

**New candidates surfaced by the same run (findings to route, not fixes):**

| candidate | evidence | route |
|---|---|---|
| **Seven janitor rows 09-02 → 09-10 labeled `nightly_schedule` at 18:42, 05:23, 09:45, 08:48, 04:04, 10:51, 22:34 local** — the schedule has been 03:00 since the plist's first commit (`54a462e`). These are the janitor's own pre-fix version of the row-10 defect and, unlike the three director-pass rows, are **not annotated**. | §3, 7 `LABEL_MISMATCH` / `annotated: no` | B (annotate, never rewrite — the 09-16 convention) |
| **`book_damped_offense.json` has NEVER produced a NAV**: 37/37 days `degraded: true`, reason "strategy stance unavailable → parked", `book_nav: null` since 07-29. The 09-16 digest rendered it as "too early to say (35 days)" and "no data this period" — a stream that has never had data reading as a young one. | §2, `book_nav` / `twin_nav` `NEVER_NONDEFAULT`, undeclared | C (books lane): feed-or-retire, and the digest should say NEVER, not "this period" |
| `llm_analyst_tracking.json` `exec.te` never computed (17/17 None) | §2, undeclared | E, minor |
| `deploy_candidate_tracking.json` `exec.slippage_bps` 0.0 on both durable points | §2 | **consistent with T-351** (the arrival-day point carrying the real slippage was the one lost); watch, no action |
| 28 never-non-default fields undeclared in the T-342 registry; most benign by construction (`degraded: false`, open/closed counts of 0 on books with no closes, `spy_null.excess_growth` ≡ 0) | §2 | registry owner (C) to triage: declare the load-bearing ones, name the benign ones so the sweep can stop listing them |

**What the sweep does NOT say:** the clock-census MISSED lines under §1 for acct-2/acct-3 are
expected — those roots hold only the files their container writes, and the census asks about
every clock. Read §1 per root, not as a fleet verdict.
