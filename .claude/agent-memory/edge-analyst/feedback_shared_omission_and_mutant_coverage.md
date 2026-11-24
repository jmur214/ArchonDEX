---
name: feedback-shared-omission-and-mutant-coverage
description: A fuzz against a reference I wrote myself shares my omissions; anchor to published worked examples, and run a mutant list before calling a harness reviewed
metadata:
  type: feedback
---

**A reference I write myself shares my blind spots.** In T-409 rev. 4, a 3,000-case fuzz compared the tax engine with a Form 1040 path I also wrote. Both left out the Qualified Dividends worksheet's LAST step (the smaller of the worksheet tax and the ordinary tax), so 3,000 random cases agreed and the gap (≤ $30/yr, in the $49,450–$50,400 strip) survived. My text had also claimed "including its smaller-of steps", which was false.

**How to apply:**
- Anchor at least one hand case per worksheet step to the PUBLISHED worked form (brackets' "$X plus Y %" rows), not to my own code or my own reference.
- Never write "includes every step" about a worksheet without listing the steps against the code.
- Run the reviewer's mutants, or a mutant list of my own, BEFORE asking for review. Rev. 4's 11 survivors out of 45 were all in the wiring (`study()` passing the wrong cohort table, block runs dropped, deltas dropped, the paired SE), not in the formulas my unit tests covered.
- The efficient kill for wiring mutants is one full-Config REHEARSAL on a small synthetic panel, spying on `run_paths` / `choose` and asserting counts, the same deltas object, and which cohort table is passed.

**Also:** when a decision rule is chosen after a smoke was read, write that order in the frozen file. A rule that does not pick the answer still needs the disclosure.

See [[project-t409-real-money-home-2026-11-19]], [[feedback-long-history-data-traps]].
