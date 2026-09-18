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
| 09-18 07:00 | director pass first scheduled firing, observe-only, one report | _pending_ |
| 09-18 09:50 | account-2 third firing; tracker point #2 durable in S3 | _pending_ |
| 09-19 09:50 | account-2 fourth firing | _pending_ |
| 09-20 | this review's verdict re-read against the three rows above | _pending_ |

The verdict in §1 stands unless the addendum shows the tracker not accruing in S3 on 09-18 or
09-19 — in which case "accruing" is not met and the sentence applies.
