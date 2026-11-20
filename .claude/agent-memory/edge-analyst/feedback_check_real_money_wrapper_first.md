---
name: feedback-check-real-money-wrapper-first
description: Before designing any real-money allocation study, establish the account's tax wrapper, profile and balance from the owner — the repo assumed "Roth" for months and the robo turned out to be taxable
metadata:
  type: feedback
---

Before designing any study about where real money should sit, establish four facts first: the account's tax wrapper (taxable, Roth or traditional), the broker and program, the risk profile, and the balance with its embedded gain. Ask for them up front, as one batched question, with defaults.

**Why:**
- The project's records (advisor surface, T-402, my T-409 rev. 1) carried "the robo is the Roth" as an unverified assumption.
- The owner's 2026-11-19 answers showed the robo is a TAXABLE aggressive account.
- That inverted the design: switching now costs tax, the robo's loss harvesting has value, the glide's sells are taxable, and leverage belongs in the separate Roth.
- Rev. 1's moderate-robo "settled" finding was moot. A whole draft was redone.

**How to apply:**
- In any real-money or advisor task, list the wrapper / profile / balance / embedded-gain facts and mark any not confirmed by the owner as an ASSUMPTION in the doc's first section.
- Design branches for both wrappers if unknown, rather than defaulting to the Roth.
- Leverage and turnover go in tax-free wrappers. A taxable account's decisions are dominated by the switching tax, the 0 % long-term-gain years and TLH, not by the premium.

See [[project-t409-real-money-home-2026-11-19]].
