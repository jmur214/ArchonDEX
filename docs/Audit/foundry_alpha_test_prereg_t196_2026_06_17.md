---
task_id: T-2026-06-17-196
title: PRE-REGISTRATION — cloud foundry-vocabulary alpha test (the program swing question)
date: 2026-06-17
worker: Agent B
branch: feature/cloud-discover-foundry-t196
status: PRE-REGISTERED before launch (per CLAUDE.md MBL/DSR discipline)
---

# Pre-registration — does the Foundry vocabulary have alpha in the existing book?

Registered BEFORE any cell is launched. The verdict reported afterward is bound to this.

## Hypothesis
- **H1:** ≥1 of the 35 tier-A/B Foundry features, added as a single-gene long CompositeEdge candidate, clears the full gauntlet + DSR with a **real positive marginal contribution** — `contribution_sharpe = Sharpe(book + candidate) − Sharpe(book) > 0`, **ci_low-aware**, census-canonical, and **N≥5 reproducible**.
- **H0 (honest null):** explored, nothing clears — the Foundry vocabulary adds no alpha to the existing 6-edge book.

## Fixed parameters (no post-hoc changes)
- **Harness:** D's `scripts/run_foundry_eval_t195.py` (T-195: full-window MBL Gate-0 + real clean-governor baseline + gate1-cache fail-open neutralized). NOT forked.
- **Candidates:** the 35 tier-A/B features in `core.feature_foundry` registry (one single-gene long composite each; ticker-independent → `operator=greater, threshold=0`; ticker-relative → `top_percentile 80`). DSR `n_trials = 35`.
- **Window:** 2012-01-01 … 2024-12-31 (13yr) — the MBL-clearing window per T-195 (NOT the 2yr that kills everything at Gate-0).
- **Baseline:** the clean 6-edge production book (`restore_clean_governor()` in the harness); `signal_cache=OFF` (FIX-2b). Marginal contribution is the TRUE `(book+candidate) − book`.
- **Gate (clears iff ALL):** the 8-gate gauntlet + DSR pass (`passed_all_gates=True`) AND `contribution_sharpe` ci_low > 0 AND census-canonical (`fundamentals_blind=0`, regime live) AND N≥5 reproducible (the standing rule: arm0/baseline reproduces N≥5 unanimous; a candidate verdict is only trusted if its contribution reproduces across the 5 reps).
- **Image:** `sha-9f36f28` (main HEAD: census + cov-pin + simfin bake [T-180] + T-194 loader-HALT + the T-195 harness), substrate `6e36e42d`, manifest-pinned/git-archived (T-127 discipline). Census-canonical + cov-pin `--runs 3` verified before launch.
- **Cloud design:** the FULL 35-candidate sweep runs per cell (so DSR `n_trials=35` is natural and the baseline is memoized once per cell by `PureBacktestCache`); **N=5 cells** give the reproducibility (5 reps of the baseline + 5 reps of every candidate's contribution). This avoids the per-candidate-cell DSR-undercount (n_trials would be 1) without forking the harness.

## Honest-N accounting
- **35** distinct candidate configurations are evaluated → **+35 toward the program N_trials** (DSR within this test already penalizes by 35). The 5 reps are determinism/reproducibility, NOT new trials. Logged in the outbox.

## Decision rule (bound now)
- Any candidate meeting ALL gate conditions above → flagged as a **CANDIDATE for director cloud-validation**. **Promote NOTHING by hand** (no `edge_weights.json` edits).
- If none → report H0 (honest null): the existing-book Foundry vocabulary has no alpha; the forward alpha lever is elsewhere (new vocabulary / gene-encoding extension), not this sweep.

---
## UPDATE (2026-06-18) — ACTUAL launch shape (director GO; committed BEFORE results)
The full-35-sweep-per-cell design is INFEASIBLE: a 13yr backtest is ~3-4h (verify: 1yr 2022 = ~26min), and one candidate's gauntlet runs several → many hours; a serial 35-sweep would be days/cell. **Pivoted to 35 per-candidate parallel cells** (each `T195_FEATURES=<one feature>`, its own clean baseline + gauntlet), >24h timeout each, census-gated. The probe `mom_12_1` is candidate #1.

**DSR honesty (the bar is not n_trials=35):**
- **In-cell screen:** D's `T195_NTRIALS` override (T-200) is NOT yet merged, so a per-candidate cell runs the in-cell DSR at `n_trials = len(feats) = 1` (LENIENT). Per the director: launch anyway, don't block. **A candidate that fails the gauntlet even at n=1 is definitively out at any higher N** → an H0-at-n=1 verdict is ROBUST (no post-process needed; more trials only raise the bar).
- **Authoritative deploy bar:** DSR at the **cumulative honest-N**, NOT 35. Per CURRENT_STATE the real count is `run_registry` **125 rows; effective ~260+** (cloud cells not all back-synced) — +35 this campaign. The MBL/DSR bar at N≈260+ is brutal (SR≫1.55), consistent with "no validated edge in the existing book."
- **Survivors only:** any candidate that passes the gauntlet at n=1 is a CANDIDATE → must be re-screened at n_trials=35 (via T-200 once merged) AND clear the cumulative-honest-N deploy bar AND reproduce at cloud N≥5 before it is trusted. **Promote NOTHING by hand.**

**Reproducibility gate:** the 35 cells each compute the SAME clean-governor baseline → assert all 35 `baseline_sharpe` are bitwise-identical (cov-pin should guarantee it; verified `--runs 3` on this image). ANY baseline divergence ⇒ STOP + report (the verdict is untrustworthy). This is the standing arm0-N≥5 rule, here N=35.

**Guardrails:** per-cell timeout 30h (108000s, > the multi-year-cell footgun); census-gate every cell (`fundamentals_blind=0`); a timed-out or non-canonical cell is VOID, not a verdict. Cost ~$20 / ~1 day (user-approved); pause+flag if concurrency caps push it toward 2+ days.

**N_trials consumed:** +35 (this campaign) toward the cumulative count; logged in the outbox verdict.
