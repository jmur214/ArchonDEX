---
name: b2-smallcap-verdict
description: B-2/T-381 (2026-11-11) — small-cap 12-1 momentum and insider-buying clusters both FAIL on the T-265 panel; numbers, what drove them, and which follow-ups are not worth proposing
metadata:
  type: project
---

Verdict: `docs/Audit/b2_smallcap_t265_verdict_2026-11-11.md` (prereg + amendment 1 alongside it).

**Momentum** (top decile of $1M–$200M-ADV names, 2017-02 → 2026-04, 70/150 bps RT):
- CAGR 8.3% against IWM 9.5% and SPY 15.1%.
- Alpha vs IWM −0.9%/yr (t −0.25), β 1.11.
- Satellite Δ log W −0.11, ci [−0.41, +0.19].
- Cost drag 4.8%/yr at 815% turnover.
- Survivor-only beats the base by +2.7 pp/yr, but that is NOT a measured haircut, and the review
  corrected my "lower bound" claim. All 59 in-decile deaths were takeovers (flat, about +0.5% over
  their last 20 days). About 1.0 pp/yr is the assumed −30% charged on deal exits; about 1.7 pp/yr is
  ex-post exclusion of names parked at a deal price. The two biases run opposite ways.
- The gate fails even at LAST-PRICE (no death penalty): satellite −0.090, ci_low −0.38.
- One year, 2020 (+49%), carries the arm.

**Insider clusters ≥ 3** (1,895 tradable events):
- Pooled CAR(0,126) vs IWM +2.0%, but cohort-weighted +0.3%, t_HAC 0.20.
- March 2020 alone is 186 events at +15.5%: insiders bought the crash bottom, which is a regime bet,
  not an event signal.
- The 40-name book's alpha vs IWM is −4.3%/yr.
- Sub-$1M-ADV events show +8.8% summed CAR, but their BHAR median is −3.8% and the summed measure
  has a bid-ask-bounce bias. It is UNTESTED; do not call it alpha.

**Why:** both are "priced net of cost and survivorship" on the best free small-cap panel this project
has. The brief's refutations stand. C-1 (PEAD × insider) does not run.

**How to apply:**
- Do not re-propose small-cap momentum or insider clusters on free data without a
  survivorship-complete panel AND a sub-$1M cost model.
- A future insider test must report cohort-weighted statistics. Pooled event means are dominated by
  crash-bottom months.
- Before reading a death or stress arm, check what the deaths ARE (last-20-day vol and return, price
  below $1). In a winners decile the exits are deal closings, so a death penalty there is an
  assumption, not evidence.
- For illiquid names, prefer BHAR or a bounce-robust measure over summed daily returns.
- See [[t265-panel-not-survivorship-complete]] and [[satellite-gate-low-power]].
