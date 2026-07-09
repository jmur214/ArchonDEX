---
task_id: T-2026-07-09-299
title: Pre-registration — the contribution-vs-gate rule (DCA × trend gate)
date: 2026-07-08
worker: Agent B
branch: feature/contribution-rule-t299
status: DRAFT — awaiting director FREEZE before any run. N_trials += 1 on run (one family, jointly reported).
---

# T-299 pre-registration — where does new money go when the gate is (partially) OFF?

## The question
A ~40yr accumulator contributes ~$7K/yr. The deploy candidate is a trend-GATED
leveraged-SPY arm whose exposure swings between 0 (cash, gate off) and ~2×
(gate fully on). **When a contribution lands while the gate is partially/fully
OFF, should it (A) sit in cash until the gate re-engages, or (B) buy in
immediately and let the gate manage it thereafter?** Unanswered for both the
T-298 damped config and the undamped one.

## Honest prior (stated BEFORE the run)
**Rule B favored, ~60-70%** — for small periodic sums, time-in-market usually
beats gate-timing, and the gate already de-risks existing capital so B's "buy
then let the gate exit" is rarely punished for long. BUT a deep multi-year
crash at/near a start (2000, 2008) may flip it: B deploys fresh money INTO a
sustained decline that the gate then rides down before exiting, while A holds
that money in cash and buys the eventual re-engagement. That start-sensitivity
is exactly why it must be run, not assumed.

## Machinery (all deterministic, offline — zero network)
- **DCA harness:** the T-283 accumulation model (`scripts/accumulation_model_t283*.py`),
  `accumulate(daily_returns, start)` → terminal wealth, worst-dollar-drawdown,
  fraction-of-time-underwater, mult-on-contributions.
- **Config exposure → returns:** `scripts/asymmetric_damping_t298.py`:
  `ens = mean(TrendOverlay([42,105,210]).exposure(spy))`, then `arm(e, slip_bps)`
  applies SSO leverage costs (SSO_ER 0.89%, spread 0.60%), txn, and SPY slippage
  to an exposure series → a net daily-return series.
- **Fair harness + calendar:** `core/calendar_guard.py`
  (`safe_common_index` / `assert_no_calendar_holes` / `reindex_onto`) on the
  fair T-255 substrate. All series aligned to ONE benchmark calendar with zero
  holes before any DCA.

## Configs (frozen)
| id | exposure series | mean exp. | role |
|----|-----------------|-----------|------|
| **C1** | T-298 asymmetric-damped `e_asym` (B=2/3 re-entry, undamped de-risk) | ~1.1× | **PRIMARY** (the deploy candidate) |
| C2 | undamped `e_target` | ~1.1–1.2× | secondary (completeness) |
| C0 | buy-hold SPY total-return (no gate, always 100%) | 1.0× | contributing baseline |

## The two contribution rules (precise — the gate-off behaviour is the crux)
Both DCA **$7K/yr, invested on the first trading day of each calendar year**
(annual schedule FROZEN; matches T-283). Let `e[t]` be the config's exposure on
contribution day `t`, `e_max = 2.0` the arm's full-on exposure.

- **Rule A — contributions FOLLOW the gate.** A contribution deploys a fraction
  `e[t]/e_max` of itself into the arm and holds the remainder in CASH (short
  rate, DGS3MO). When the gate is fully OFF (`e[t]=0`) the whole contribution
  sits in cash; it is only pulled into the arm as the gate re-engages on later
  bars. New money never enters a market the gate is currently avoiding.
- **Rule B — always-invest-immediately.** The full contribution joins the arm's
  managed capital at once; from the next bar it rides `e[t]` exactly like
  existing capital (so during a gate-off period it too is in cash via the arm,
  but during a partial-gate period it is FULLY committed to the arm's target,
  not scaled by `e[t]/e_max`). "Buy in, then let the gate manage it."

The measurable difference lives entirely in partial/off-gate windows: A withholds
fresh money from a distrusted market; B commits it and delegates to the gate.

## Metrics (reported for C1,C2,C0 × {A,B}, one joint table)
1. **Terminal wealth** ($ and ×-contributions).
2. **Worst contributing-path drawdown in DOLLARS** (peak-to-trough of the
   accumulating balance) + fraction-of-time-underwater.
3. **Cash-drag decomposition (Rule A only):** total $-years of contribution
   capital held un-invested, and WHEN (which gate-off windows) — the explicit
   cost of A's discipline.
4. **Start-date sensitivity:** 5 staggered starts — **2000, 2003, 2006, 2009,
   2012** (T-283 convention) — every headline reported per start, not just the
   full window.

## FROZEN decision gate → the pre-registered advisor rule
Decided on **C1 (the deploy candidate)**; C2/C0 are context.
1. **Primary:** the rule with higher **median terminal wealth across the 5
   starts** wins — PROVIDED its **worst-dollar-drawdown (deepest across starts)
   is ≤ 110%** of the other rule's (i.e. not more than 10% deeper in dollars).
2. **Defense override:** if the wealth-winner worsens worst-$-DD by **>10%**,
   the DD-safer rule is adopted instead (the user won't sell, but a materially
   deeper paper hole is a behavioural risk that outweighs a marginal wealth
   edge).
3. **Robustness:** the adopted rule must win terminal wealth at **≥3 of 5
   starts**. If neither does (split ≤2), declare **H0 — no robust winner** and
   default to **Rule B** (time-in-market; simpler, no cash-timing operational
   surface).

## N-accounting
**N_trials += 1** on run — the whole 2 configs × 2 rules + baseline is ONE
family, reported jointly (per the task). No sweep, no per-cell trial inflation.

## Sequence
DRAFT (this doc) → **director FREEZE** → run on the frozen spec → results table
+ the frozen verdict appended here → advisor-row update → "T-299 done".
NOTHING runs until freeze.

## DIRECTOR FREEZE — 2026-07-09 (no amendments; BINDING)
Frozen exactly as drafted. The two flagged knobs are ruled as proposed: (1) the **110% worst-dollar-DD
tolerance** stands — it operationalizes "max wealth, but a materially deeper paper hole is a behavioural
risk" without letting a marginal wealth edge buy unlimited drawdown; (2) the **≥3/5-start robustness bar
with H0→Rule B on a split** stands — Rule B is the correct default (time-in-market prior, no cash-timing
operational surface, simpler to explain to the accumulator). RUN AUTHORIZED on the frozen spec
(C1 primary; calendar_guard in the harness; N_trials += 1, one family). Any deviation = a new
pre-registration.
