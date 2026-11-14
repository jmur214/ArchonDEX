---
name: t399-t315-corrected
description: T-399 (2026-11-14) corrected T-315 static leverage — no arm CI-beats or CI-loses; what survived the daily-cost defect, and three worktree-only suite failures to expect
metadata:
  type: project
---

T-399 re-ran T-315 with the rebalance cost charged once a year instead of daily (branch `fix/t315-static-leverage-cost-t399`; results appended to `docs/Audit/static_leverage_t315_2026_07_27.md`; N_trials 0 by director ruling).

**Corrected D-B (1968+) numbers:** bar $3.36M; 1.25× $3.67M (Δlog +0.15 %/yr [−0.95, +1.17]); 2× $8.86M (+1.66 [−2.76, +5.83], MaxDD −88 %). Every static arm straddles zero in all three windows. At −2 % every arm trails on point by 9–19 %; at −3 % the ordering inverts; no CI excludes zero. 1929 at 2×: $10,000 → $158, 19 years.

**Why:** the July verdict mixed one true statement ("no arm CI-beats") with several artifacts of the defect — "1.25× significantly LOSES", the non-monotone frontier, "loses in the high-rate era", the Japan-path loss, "the glide wins the accumulation race", Kelly 2.20 → 1.13 (arithmetic: 2.55 → 1.83 → 1.48).

**How to apply:**
- Quote static leverage as "not refuted, not supported — a risk-preference decision" ([[t396-lifecycle-leverage-note]]), never as "leverage loses".
- The fee model matters at low L: a SPY+SSO blend saves 0.53 %/yr at 1.25× and flips the −2 % reading to slightly ahead. B-5's bill/SOFR financing costs ~0.29 pp/yr more than the T-306 cash leg.
- Before fixing a measurement defect: run the unmodified script first and keep its output (it reproduced the July tables to the dollar), pre-declare the amendment in its own commit, and make the reproduced ORIGINAL column a fail-closed acceptance check.
- `PeriodIndex.shift(1)` shifts the period; `Series.shift(1)` of period values is positional. Only the first is the bug. One look-alike exists (`scripts/premium_tier_t279.py:75`) and is the Series form.
- In a subagent worktree built by `wt_data_layout.sh`, three tests fail on any commit because `data/governor/` is empty: `test_layer3a_capability_ledger_source_files_exist`, `test_golden_master_pipeline_replay`, `test_before_arm_reproduces_the_pre_rr1_golden_bit_for_bit`. Confirm on main's commit before blaming a change.
- Fixing a defect that a `health_check.md` HIGH row anchors makes `doc_lint` fail until the row is closed. That is by design; hand the director the close text.
