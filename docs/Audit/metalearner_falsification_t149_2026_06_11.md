---
task_id: T-2026-06-11-149
title: StepM→core + the metalearner falsification (closing the alpha lane's last GO)
date: 2026-06-11
author: Agent D (alpha/edge lane)
outcome: PENDING — this revision is the PRE-REGISTRATION, committed BEFORE the
  falsification run touches data (per the brief's hard constraint). The kill
  bar below is immovable after this commit. Results land in the next revision.
status: PRE-REGISTRATION (results pending)
reproduce: |
  python -m pytest tests/test_multiple_testing.py -q     (Part A: 7 tests)
  PYTHONHASHSEED=0 python -m scripts.metalearner_falsification_t149
---

# T-149 — Part A (done) + Part B pre-registration

## Part A — Romano-Wolf StepM promoted to core (DONE)

`core/multiple_testing.py` now holds the family-wise machinery with three
consumers repointed (T-137 re-exports for back-compat; T-144 resolves through
it; T-145 imports core directly — verified all three resolve to the same
function object):
- `romano_wolf_stepm` — Romano-Wolf (2005) stepwise FWER control, studentized,
  joint circular-block bootstrap (shared resample indices preserve cross-member
  dependence), two-sided.
- `spa_test` — Hansen (2005) Superior Predictive Ability vs a benchmark,
  studentized max-statistic over recentred block-bootstrap draws (single-model
  case = robust one-sided mean>0 test).

Tests (`tests/test_multiple_testing.py`, 7 passing): all-null panel → no
survivors; injected signal found (and only it); single-hypothesis behaves as a
plain test (exact-zero-mean null does not survive, strong mean does);
deterministic given seed; SPA rejects for a strictly-better model, does not
reject for an equal one, and the family max tracks the best model.

## Part B — PRE-REGISTRATION (committed before data contact; kill bar immovable)

**Framing:** falsification, NOT train-to-deploy. T-132 left a weak-prior GO
(1-of-28 interactions, selection-uncorrected); the external research predicts
ridge wins at our scale; the ≥5-individually-clearing-edges precondition is
unmet (we have zero). Expected outcome, stated up front: a clean kill — which
completes the alpha lane's record. The metalearner's production `enabled`
stays false REGARDLESS of outcome.

1. **Data:** the T-132 panel (signal log `695b0b21`, 109 tickers × 1004 days,
   2021-2024), the SAME 8 de-correlated features (assembly + |ρ|>0.5 greedy
   de-correlation imported from `scripts.interaction_diagnostic_t132`).
   Target: 1-day forward log return.
2. **Models (complete family, no architecture shopping; N_trials += 3):**
   - GBM stacker: `HistGradientBoostingRegressor`, depth ≤3, heavy
     min_samples_leaf (500), lr 0.05, 300 iters, **monotonic_cst=+1 on all
     features** (signals are constructed bullish-positive — the research's
     guardrail), seed 0.
   - Ridge (the null combiner): standardized, alpha from the fixed grid
     {0.1, 1, 10, 100} by internal 5-fold MSE.
   - Linear uniform weighted_sum (production proxy; context only).
3. **Validation:** CPCV — N=6 contiguous date groups, k=2 test → 15 paths;
   purge = 1-day label horizon at every boundary; embargo ≈1% of sample
   (~10 trading days) after each test block. No plain k-fold, no single split.
4. **Metric:** per-OOS-day cross-sectional Spearman rank-IC (≥30 names/day),
   averaged across paths per unique day → one daily IC series per model.
5. **THE KILL BAR (immovable):** the metalearner survives ONLY IF BOTH
   (a) `spa_test` on the daily IC difference (GBM − ridge) rejects at 5%, AND
   (b) the block-bootstrap (B=1000, block=21, seed 0) **ci_low of the mean IC
   difference > 0**. Anything less → the door CLOSES and the ledger gains
   "non-linear combination cannot extract compound alpha from these edges,"
   completing T-117's linear closure; the 2026-05-01 falsification stands
   reinforced.
6. **Determinism:** seed 0 end-to-end, no wall-clock in artifact, ×2.

## Results

*(pending — next revision; the section above may not be edited after this
commit, only appended below)*
