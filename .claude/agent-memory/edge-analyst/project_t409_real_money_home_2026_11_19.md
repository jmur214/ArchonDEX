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

**Rev. 3 (2026-11-20), owner round 2:**
- Facts: taxable < $50k (so the robo's TLH is off until it grows), embedded gain unknown (g grid 0 / .15 / .30), law school more than a year away, Roth $10–25k.
- Stance: every arm must be an ordinary manual choice at Schwab; nothing involves the machine.
- Primary arms: K0, K1 (the default) and B1–B3, which hold SSO in the Roth bounded by capacity. Dropped: B5, B6, Shiller pre-1926 cohorts. Recommended trial count: 15 raw.
- Code `scripts/t409_real_money_home.py`, commit `7f4cd09`.
- Controls reproduce T-399 ($8,864,568) and T-287 ($929,498.35 / $494,701.10).
- Smoke md5 `838fb3a7…`; each 40-year arm-path takes 2–5 ms; a full run is ≈ 15–20 min.

**Rev. 5 (2026-11-24), the freeze candidate:** code `da224b7`, prereg `24b13fe`.
- Pair rule for an owner with no stated view: read the choice in `param:h=+0.00` and `param:h=-0.02`; agree -> that choice; disagree -> K1; K1 ineligible -> no choice.
- Choice = highest E[log W] (best typical), highest-mean arm reported beside it and never decides.
- School-year Roth default none (no source for $7,500 on ~$8k of wages); the taxable $500/month in school is an assumption.
- 668,400 arm-paths, 55-100 min a run, run twice; smoke md5 `cb5d9cea`; frozen inputs in `/Users/jacksonmurphy/Dev/_research_snapshots/t409_real_money_home_2026-11-20/inputs/`.
- Study-path control $415,477.1850.

**Result (2026-11-24, frozen at main `d109f84`, two runs, md5 `35523022`):**
- Decision A -> K1 (leave the robo without selling), decision B -> B1 (SSO in the Roth, lifecycle cap 2x); both pair rows agree.
- B1 leads K1 by +0.358 / +0.209 in E[log W] (bands 0.012); P(below S&P reference) 0.11 / 0.24; worst bootstrap path 0.62-0.66.
- Gate cannot certify leverage: t 1.50 vs bar 2.96; 1.25x blend Sortino 0.790 (ci_low 0.455) vs VOO 0.839 (ci_low 0.500).
- My pre-stated E5 was WRONG: I expected a flip at h = -2 and a loss at -3; leverage led at both (+0.20, +0.13). E7 wrong too (JST floor 0.530, France).
- Verdict doc: `docs/Audit/real_money_home_verdict_t409_2026-11-24.md`; runs in `_research_snapshots/t409_real_money_home_2026-11-20/runs/`.
- The frozen output stores worst cohorts as ratios only, never dollars; owner-grid cells have no block runs, so no band there.

**Why:** the owner asked "where does the real money sit"; the director asks the owner once, only for decision-relevant inputs.

**How to apply:**
- Never quote Roth-frame (tax-free) results for this money.
- Price any move in after-tax household terms.

See [[feedback-check-real-money-wrapper-first]], [[feedback-long-history-data-traps]], [[reference-free-long-history-sources]].
