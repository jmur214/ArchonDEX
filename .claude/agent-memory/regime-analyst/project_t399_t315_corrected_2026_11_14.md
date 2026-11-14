---
name: t399-t315-corrected
description: T-399 (2026-11-14) corrected T-315 static leverage — no arm CI-beats or CI-loses; 1.35×+ ahead on point, 1.25× sign not established (two leverage-favouring conventions); process lessons from the review
metadata:
  type: project
---

T-399 re-ran T-315 with the rebalance cost charged once a year instead of daily (branch `fix/t315-static-leverage-cost-t399`; results appended to `docs/Audit/static_leverage_t315_2026_07_27.md`; N_trials 0 by director ruling).

**Corrected D-B (1968-01-02 to 2026-04-17) numbers:** bar $3.36M; 1.25× $3.67M (Δlog +0.15 %/yr [−0.95, +1.17]); 2× $8.86M (+1.66 [−2.76, +5.83], MaxDD −88 %). Every static arm straddles zero in all three windows. At −2 % every arm trails on point by 9–19 %; at −3 % the ordering inverts. 1929 at 2×: $10,000 → $158, 19 years.

**Why:** the July verdict mixed one true statement ("no static arm CI-beats") with artifacts of the defect — "1.25× significantly LOSES", the non-monotone frontier, the Japan-path loss, "the glide wins the accumulation race", Kelly 2.20 → 1.13 (arithmetic mean: 2.55 → 1.83 → 1.48). "Loses in the high-rate era" is different: after the fix the 1962–89 gaps (−0.03 pp at 1.5×, +0.22 pp at 2×) are inside the fee-convention error, so neither "loses" nor "ahead" is established there.

**How to apply:**
- Quote static leverage as "not refuted, not supported — a risk-preference decision" ([[t396-lifecycle-leverage-note]]), never as "leverage loses" and never as "every arm is ahead". Ahead on point holds at 1.35× and above; at 1.25× the sign is not established.
- The frozen T-312/T-315 model leans toward leverage in two ways: the T-306 cash leg (B-5 financing costs 0.07 %/yr more at 1.25×, 0.29 at 2×), and a fee convention — the levered fund adds 9 bp back before levering, the bar subtracts 9 bp, on a leg that is gross before 1993-02-01 and net after (overstates arm-minus-bar by L × 9 bp/yr, then 9 bp/yr; about 0.10–0.16 %/yr). Subtract both before reading the sign of any small lead on this harness. Changing either is a new pre-registration.
- The blended-fee result (SPY+SSO saves 0.53 %/yr at 1.25× and puts the low arms slightly ahead at −2 %) is a labelled sensitivity whose sign is not established. Do not quote it as a finding.
- Before fixing a measurement defect: run the unmodified script first and keep its output, pre-declare the amendment in its own commit, and make the reproduced ORIGINAL column a fail-closed acceptance check — then test that check's halt branch with a real mismatch, not an empty dict.
- When a fix moves a point estimate across zero by a small amount, check what else in the model is the same size before writing "ahead". The review caught this; I had flagged the fee add-back to myself in T-396 and not carried it forward.
- "No interval excludes zero" needs its scope: the gated T-312 arm on ~99yr does ([+86, +5.1M], the 1929 episode).
- `PeriodIndex.shift(1)` shifts the period; `Series.shift(1)` of period values is positional. One look-alike exists (`scripts/premium_tier_t279.py:75`) and is the Series form.
- In a subagent worktree built by `wt_data_layout.sh`, three tests fail on any commit because `data/governor/` is empty: `test_layer3a_capability_ledger_source_files_exist`, `test_golden_master_pipeline_replay`, `test_before_arm_reproduces_the_pre_rr1_golden_bit_for_bit`. Confirm on main's commit before blaming a change.
- Closing a ledger row dated on or after 2026-11-13 needs a `python -m scripts.honest_n_trials record` row, even at 0; a fix that removes a HIGH row's anchored line needs that row closed for `doc_lint` to pass.
