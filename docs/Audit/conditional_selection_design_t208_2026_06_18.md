---
task_id: T-2026-06-18-208
title: "Trade like a trader" conditional + combined selection framework — DESIGN ONLY
date: 2026-06-18
scope: design/pre-registration for Engine-A signal-path conjunctive selection; NO code, NO measurement, NO N_trials consumed; gated for execution behind Phases 0-2
status: CURRENT (design doc; Phase 3 forward-prep, parallels A's T-190)
references: re-architecture plan Phase 3; T-156 (averaging washes edges out); signal_processor regime_gate plumbing (L585-593)
---

# T-208 — Conditional + Combined "Trader-Like" Selection (Design)

## 0. Honest odds up front (lead with the prior, per the brief)

**Prior of success: < 20%.** 12 of 13 edges are factor-negative;
cross-sectional retail stock-selection is the hardest corner of this
whole program (cross-sectional alpha is already 0/16, VRP refuted). The
user's conjunctive intuition ("good fundamentals → technical
confirmation → right regime") is *genuinely un-tested* — today the
ensemble AVERAGES fundamental + technical edges as independent votes
(weighted-sum + tanh + ridge shrinkage), which T-156 showed tends to
WASH them OUT — so it deserves one rigorous shot. But the design's job is
to make a likely-null **cheap, unambiguous, and overfit-proof**: a
clean, well-measured FAIL that closes the front is as valuable an
outcome as a pass, and far more likely. Everything below is built so the
gated execution is fast + pre-registered, not invented under pressure.

## 1. The conjunctive structure (vs the current averaging)

**Today (averaging — the thing to beat):** each edge emits a score; the
ensemble does `weighted_sum(scores) → tanh(raw/clamp) → ridge shrinkage`.
Fundamental and technical edges are INDEPENDENT ADDENDS — a great
fundamental name with weak technicals and a weak fundamental name with
great technicals can net to the same middling score. T-156: averaging
washes the signal out.

**Proposed (conjunctive — the user's bet):** make the dimensions
MULTIPLICATIVE gates on each other, not addends. A name fires only when
fundamentals are good **AND** technicals confirm **AND** the regime is
right:

```
conjunctive_score(ticker) = s_tech(ticker)               # the technical entry signal
                            × g_fund(ticker)              # fundamental "is this a better BUY?" gate ∈ [0,1]
                            × g_regime(current_regime)    # regime/sector gate ∈ [0,1]
```

- **`g_fund`** = the defensive-tilt quality/value score (T-205's
  `quality_score`, and/or the dormant value edges) mapped to a gate:
  e.g. top-quantile → 1.0, soft ramp below, 0 in the bottom — "only buy
  names whose fundamentals justify a buy."
- **`s_tech`** = the existing technical edges (momentum / RSI-bounce /
  gap-fill / volume) — the entry timing/confirmation.
- **`g_regime`** = **REUSE the existing `regime_gate` plumbing**
  (`signal_processor.py` L585-593: `w *= gate.get(current_regime, 1.0)`,
  currently fed empty dicts = no-op). The conjunctive design FILLS those
  dicts with theory-driven per-edge regime multipliers — no new plumbing,
  no engine-boundary cross.

**Implementation shape (canon-safe):** add a new ensemble MODE in
`signal_processor` alongside the existing `weighted_sum` and meta-learner
modes — `ensemble_mode="conjunctive"`, **default OFF** (weighted_sum
preserved bitwise → prod canon unchanged). The fundamental edges become
GATES on the technical signal rather than independent contributors;
this is a re-WIRING of existing edges through the existing multiplicative
hook, not new alpha. No Engine-B/boundary cross — it lives entirely in
Engine A's signal weighting.

## 2. The multiple-testing explosion (the killer — and the discipline)

The conjunctive space is combinatorial:
`N = (#fundamental variants) × (#regime conditions) × (#technical
confirmations) × (#timing gates)`. Even a modest 3×4×3×2 = **72
combinations** — at retail-N every one is a trial, and DSR's deflation
grows with `ln(N_trials)` (already ~2.5+ accumulated decades of trials),
pushing the DSR-clearing SR absurdly high. **Searching this space IS the
overfit.** Controls:

1. **Pre-register ONE canonical structure — theory-driven, not searched.**
   One fundamental gate (T-205 quality top-quantile), one regime
   condition (the validated `hmm_p_crisis`-derived regime, risk-on when
   benign), one technical confirmation (the single strongest existing
   technical edge by prior evidence, e.g. momentum), one timing rule
   (§3). Chosen a-priori from the user's intuition + the existing
   evidence — NOT by grid search. This is the T-118b template: commit to
   the structure before seeing the result.
2. **Count EVERY branch toward N_trials.** Any variant ever evaluated —
   including a later re-spec — increments honest-N and re-inflates the
   DSR bar. The pre-registration records `N_trials_consumed` before the
   run (CLAUDE.md `[NN-MBL]`).
3. **OOS-only / walk-forward.** The structure is fixed on an in-sample
   blind; judged only on out-of-sample / forward data. No in-sample
   Sharpe is ever quoted as evidence.
4. **Honest expected outcome: a wide-CI null.** State it in the
   pre-registration so a null isn't spun as "almost." The success
   condition explicitly includes "a clean FAIL closes the front."

## 3. Timing (the user's "confirm + time the entry")

- **Use the EXISTING post-close daily aggregates** for entry/exit timing.
  **NO intraday** — not because of PDT (it isn't the blocker here) but
  because intraday timing is a speed-competition we lose and a cost we
  can't afford at retail; the edge (if any) must survive daily-close
  execution.
- **One pre-registered hardcoded timing rule**, e.g. "enter at the next
  close after the conjunctive score crosses its threshold; exit on a
  fixed stop/target or regime flip" — a single rule, not a swept family.
- **Advisory-log first:** log the timing decision (would-enter /
  would-exit + the conjunctive score components) for a window BEFORE it
  acts on sizing, to confirm the rule is sane and PIT-correct — the same
  advisory-before-active discipline used elsewhere.

## 4. The bar (what success means)

**Gate on the robo scorecard (C/T-203), after-tax, OOS — NOT
factor-orthogonality, NOT an in-sample Sharpe bump.** A combined
conjunctive strategy that **BEATS THE SCHWAB ROBO net-of-cost,
after-tax, out-of-sample** is a WIN even if it carries zero academic
"alpha." This is the right bar because it matches the user's actual
objective (beat the robo on risk-adjusted/tail terms for a $5-50K book),
and because the after-tax/OOS/net-of-cost framing is itself
overfit-resistant (it's a high, real-money-relevant hurdle, not a
massageable IS statistic). The defensive tilts (T-205) and any crisis
sleeve (T-170/171/173) compose into the same scorecard — the conjunctive
selector is judged on the whole-portfolio robo-beat, not in isolation.

## 5. Honest odds + the kill criterion (concrete)

- **Prior < 20%** (restated; §0). The base rate for retail
  conjunctive stock-selection beating a robo after-tax OOS is low.
- **KILL CRITERION (pre-registered):** if the single pre-registered
  conjunctive structure does NOT beat the robo scorecard OOS after-tax
  (point estimate, with its CI reported), **the front is declared
  CLOSED** — recorded as a clean negative, NOT iterated. Iterating the
  structure after seeing the result is the overfit the whole design
  exists to prevent.
- **At most ONE structural re-spec**, and only with a fresh
  pre-registration + an explicit N_trials increment (which raises the DSR
  bar further). After that, closed. This bounds the search to ≤2 honest
  shots, not a fishing expedition.
- **A clean FAIL is a deliverable.** It closes the user's
  highest-belief-but-low-prior front unambiguously and frees the program
  to settle on the deployable system (base + defensive tilts + MF
  tail-defense). Saying "this doesn't work" with a well-measured OOS
  robo-scorecard miss is the honest win the design is built to enable.

## 6. Why this is safe to design now (and gated to execute later)

Phase 3 executes LAST — after the clean base (Phase 0), the re-aimed
robo gate (C/T-203), and the de-biased substrate. Designing it now means
the gated run is a single pre-registered structure measured on a ready
scorecard, with the overfit controls already locked — exactly the
posture that makes a low-prior bet cheap to resolve honestly.

## 7. Constraints honored

- DESIGN ONLY — no code, no measurement, no N_trials consumed.
- Signals/combination is Engine-A lane; reuses the existing `regime_gate`
  multiplicative hook (no engine-boundary cross); conjunctive mode would
  ship default-OFF (canon-safe) when built.
- Gated for execution behind Phases 0-2; this is forward-prep.
- NO TASK_LEDGER write (T-114 — row in outbox). Branch push; director merges.
