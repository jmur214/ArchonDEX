---
name: project-t409-real-money-home-2026-11-19
description: T-409 DRAFT decision study (rev. 2) — the owner's real money is a TAXABLE aggressive Schwab robo plus a separate Roth; after-tax switching, 0 % school window, robo TLH ($50k opt-in), Roth-first leverage, owner loss bound 0.5x S&P 500
metadata:
  type: project
---

**Owner facts (answered 2026-11-19, via the director):**
- The robo is Schwab SIP on the **aggressive** profile, in a **taxable** account, not the Roth.
- A Roth exists separately; its size and broker are unknown.
- Loss bound: never below **0.5× the S&P 500** in any historical cohort.
- Auto-contributions continue through crashes, with no behavioural sell.

**Rev. 2 draft:** `docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md` (`bd3e2c7`). Rev. 1 is kept verbatim in `..._DRAFT_rev1_...`. Nothing run, no trial count stated (8–17 proposed).

**Decision A (the legacy robo balance):**
- K0: stay.
- K1: de-enroll in place, no sale. This needs a Schwab phone check that positions stay.
- S0: sell now.
- S1: sell inside the school-year 0 % room. 2026: $49,450 + $16,100 standard deduction (Rev. Proc. 2025-32); 2027: $51,050 + $16,600.
- The kiddie tax voids S1.
- Break-even drag for switching ≈ −ln(1 − τ₀·g)/40.

**Robo TLH:** opt-in, $50k to activate, an undisclosed maintenance minimum, blind to the owner's tax situation. Its wash-sale guard does not cover an outside Roth.

**Decision B (leverage):** Roth first. Household capacity is 1+r with SSO or 1+2r with UPRO, where r = Roth share.
- Margin: dead (loses at any spread > 4.4 pp over bills).
- LEAPS: dropped.
- Taxable futures: dropped below ~$76k (an MES is ~$38k notional).
- Roth futures: from $25k NLV.
- Box spread: conditional on Schwab confirming Reg-T short-box proceeds are usable.
- Borrowing routes hit a margin call at 2× after a ~29–33 % fall, so a never-seller's ceiling is ~1.3–1.4×.

**Inputs that flip the decision:** balance vs $50k, embedded gain g, school timing and income, age/dependency, monthly contribution (and whether loan-funded), Roth size and broker, bracket and state, belief row.

**Why:** the owner asked "where does the real money sit"; the director asks the owner once, only for decision-relevant inputs.

**How to apply:**
- Never quote Roth-frame (tax-free) results for this money.
- Price any move in after-tax household terms.

See [[feedback-check-real-money-wrapper-first]], [[feedback-long-history-data-traps]], [[reference-free-long-history-sources]].
