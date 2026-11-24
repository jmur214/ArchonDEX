---
name: feedback-variance-proportional-survivorship
description: Survivor-selected samples overstate returns in HIGH-VARIANCE windows (earnings weeks, event days) more than ordinary periods; long-short announcer-minus-non-announcer does not cancel it
metadata:
  type: feedback
---

**The rule:** a survivorship hole biases an event-window test more than its average drift suggests.

The mechanism: the sample is selected on cumulative return S = Σ r_w (the firm survived or kept its
ticker). Then E[r_w | selected] − E[r_w] ∝ Var(r_w). Each period's share of the survivor drift is its
share of the variance.

- Earnings weeks carry about 2× an average week's variance for large caps [R; not measured here].
- So the bias on an earnings-week basket ≈ 2b, where b is the covered-sample weekly drift.
- On announcers minus non-announcers it is ≈ (VR − 1)·b. The long-short reduces the bias but does not
  remove it.

**Worked numbers (T-415, 2026-11-20):**
- T-136's EW gap between members with files and imputed full membership is 3.0–5.5 pp/yr, so
  b ≈ 0.06–0.11 %/wk.
- That gives an earnings-week bias of ≈ 0.12–0.22 %/wk, against E-2's planning net effect of 0.10 %/wk.

**Why:** a survivor-biased event study can pass with zero true effect. The usual "the hole is only X%
of member-days" reassurance understates this.

**How to apply:**
- For any per-event test on a substrate with an outcome-correlated hole, bound the bias as
  (missing share) × (variance ratio) × (drift). Use already-measured drift, never test-window returns.
- If the bias is at least the effect, the test is blocked, or allowed only under the asymmetric
  FAIL-stands rule.
- Watch for a counter-term: deals announced inside predicted event windows push the bias the other
  way (≈ 0.02 %/wk for S&P).

Related: [[t265-panel-not-survivorship-complete]], [[per-event-effect-to-noise]].
