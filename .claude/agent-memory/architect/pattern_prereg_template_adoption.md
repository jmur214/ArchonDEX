---
name: pattern-prereg-template-adoption
description: Pre-registrations adopted from external research templates can be internally inconsistent — verify the mechanical rule actually generates the locked list, and check model-training-window overlap with evaluation episodes
metadata:
  type: project
---

Pattern (found 2026-06-10, T-118b audit): when the director adopts an external-research evaluation template into a LOCKED pre-registration, three defect classes slip through:

1. **Rule-vs-list mismatch.** T-118b locks a "mechanical" episode rule (S&P 500 TR DD >= 15%) AND a hand-listed episode set — but the set contradicts the rule (2015 episode is ~-13% TR, below threshold; dotcom 2000-02 ~-47% qualifies but is absent). The list was the researcher's verbatim example, the rule decorative.
2. **In-sample contamination unexamined.** The crisis HMM driving the overlay trained 2006-04 to 2019-12 (T-103) — 4 of 6 locked episodes sit inside its training window; only COVID + 2022 are OOS. No pre-reg doc mentions it.
3. **Benefit-side floor missing.** The calm-drag ceiling is in return units; the crisis benefit criterion is in MaxDD-pp units with no return-side threshold — the "actuarially fair insurance" rationale is unenforceable as written.

**Why:** lock-in + integrity rules ("no threshold edits after commit") make these defects irreversible post-unblinding, so they must be caught BEFORE results land.

**How to apply:** any future pre-registration audit: (a) re-derive the locked set from the stated mechanical rule independently; (b) overlay every model's training window on the evaluation episodes; (c) check the pass criteria units are commensurable with the stated rationale; (d) check multiplicity handling when the campaign sweeps configs (T-118 = 36 configs) but the gate evaluates "the" overlay. Related: [[verdict-buries-capability]] (docs lag), [[pattern-flag-vs-path-disconnect]].
