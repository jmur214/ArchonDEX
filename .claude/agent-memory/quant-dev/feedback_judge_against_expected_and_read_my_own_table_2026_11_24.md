---
name: feedback-judge-against-expected-and-read-my-own-table
description: Lessons from the T-416 review (2026-11-24) — judge completeness against what was EXPECTED, reconcile counts in my own printed table, label a category only after testing it, pin the clock, prove survivors are equivalent before dropping them
metadata:
  type: feedback
---

An independent reviewer found nine silent-loss paths in a build I had reported as proven (36/36 reversions). What to carry forward:

- **Reversion proofs only cover the locks I thought of.** Every one of my modes was caught and nine defects were live. Also run ADVERSARIAL INPUTS through the real entrypoint: empty/odd payloads, one odd value, a hang, a drip, a missing page key, partial pages, a corrupt existing file, a late clock, a closed day.
- **Judge completeness against what was expected, not what came back.** "49/49 covered" was computed on returned rows, so 1 of 6 expiries read OK.
- **Reconcile the numbers in my own table.** I printed XSP bid-0 = 19 % (369 rows) next to 225 non-real rows and did not ask where the other 144 went: they were junk the rule had passed.
- **Do not label a category without testing it.** "Every non-real row lacks IV" was vacuous for XSP, which never has IV.
- **A test that "works on any date" must be proven on a closed day.** Pin the clock; lock by AST that the module reads it in one function; run the file in several time zones.
- **An acceptance condition I cannot meet is reported with the measurement, not quietly tuned.** (Spread leg: no threshold rejects ≈ 0.)
- **A surviving mutant is a question.** Of three survivors, one was nearly equivalent, one a missing lock (infinite price), one needed > 50 rows to show (pandas hashes values above 50, so a list in a long column raises TypeError).

**Why:** the director held the merge; each defect loses data that cannot be recaptured.
**How to apply:** before reporting a data-capture build as done, write the adversarial probe set first. Related: [[project-t416-options-snapshot-archive]], [[report-the-checks-actual-scope]].
