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

---

# RESULT (run on the frozen spec, 2026-07-09) — N_trials += 1

**Self-check (faithful T-298 reproduction):** mean `e_asym` = **1.101** (the ~1.1×
damped deploy candidate), mean `e_target` = 1.400; de-risk invariant
`e_asym ≤ e_target` violations = **0**. Re-derivation matches the frozen T-298
construction. Script: `scripts/contribution_rule_t299.py`; data:
`data/research/t299_contribution_rule.json`.

## C1 — T-298 damped (~1.1×), the DECISION config — $7K/yr
| start | rule | terminal $ | ×contrib | worst $DD | %uw | cash-drag $·yr |
|---|---|---|---|---|---|---|
| 2000 | **A** | **1,110,975** | 5.88 | −183,575 | 11% | 19,176 |
| 2000 | B | 1,106,400 | 5.85 | −183,007 | 12% | — |
| 2003 | A | 892,555 | 5.31 | −144,714 | 6% | 15,419 |
| 2003 | **B** | **894,021** | 5.32 | −145,221 | 6% | — |
| 2006 | A | 687,844 | 4.68 | −108,292 | 9% | 14,306 |
| 2006 | **B** | **691,354** | 4.70 | −109,163 | 9% | — |
| 2009 | A | 511,049 | 4.06 | −76,836 | 1% | 10,271 |
| 2009 | **B** | **515,026** | 4.09 | −77,791 | 1% | — |
| 2012 | A | 354,518 | 3.38 | −48,987 | 0% | 6,687 |
| 2012 | **B** | **355,602** | 3.39 | −49,426 | 0% | — |

## FROZEN VERDICT → **ADOPT RULE B** (always-invest-immediately)
- Median terminal (C1): **B $691,354 vs A $687,844** — B wins (+$3,510, +0.5%).
- Start wins: **B 4 / A 1** (≥3/5 robustness cleared). The lone A-win is the
  **2000 start** — exactly the deep-crash flip the prior flagged: A's discipline
  (hold fresh money in cash, buy the re-engagement) pays only when a contribution
  would otherwise deploy into a sustained multi-year decline.
- Worst-$-DD: **within tolerance** — A and B are near-identical at every start
  (≤ ~$600 apart, well inside the 110% bar); no defense override triggers.
- ⇒ **The pre-registered advisor contribution rule is Rule B.**

## Honest reading (the effect is SMALL — say so)
For this mildly-levered (~1.1×) gated arm the contribution rule **barely
matters**: sub-1% terminal-wealth gaps and DD within noise. B's edge is the
time-in-market prior showing through thinly; A's cash-drag ($6.7K–$19K
dollar-years, largest at the longest/deepest 2000 window) buys essentially
nothing here. **Secondary (context, not the decision):** the UNDAMPED C2 (1.4×)
marginally FLIPS to A on wealth at 4/5 starts — the more leverage, the more A's
"don't deploy fresh money into a distrusted market" discipline earns — but the
magnitudes stay tiny and C2 is not the deploy candidate. The prior (Rule B
favored ~60-70%) is confirmed for the damped config; the leverage-dependence of
the flip is the one genuinely new thing learned.
