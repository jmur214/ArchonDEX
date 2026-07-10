---
task_id: T-2026-07-09-301b
title: The exec-cost / per-event-rate CONSUME-POLICY — a bounded, pre-registered adaptation rule
date: 2026-07-10
author: Agent D
type: PRE-REGISTRATION DRAFT (awaiting director freeze → then it is policy; 0 N_trials)
status: DRAFT — NOT ACTIVE. Awaiting freeze.
---

# T-301b (DRAFT) — how measured operational rates feed back into the harness, safely

T-301's `ExecCostLedger` reports per-(account, instrument) execution cost but, by design, **does not move any
assumption** — "it reports, it does not move a threshold." This pre-registers the ONE rule by which measured
operational rates are allowed to update the harness's assumptions. Scope EXPANDED per B/T-305 from slippage
alone to **per-event-rate learning generally**. This is the concrete, honest form of the user's directive
("the machine should improve from what works"): B/T-305 dissolved the disagreement — **free-fit overfits (the
MetaLearner/HRP graves), but a BOUNDED adaptation RULE — fit long-history, pre-register, FREEZE, run OOS — is
legitimate.** This is that rule, frozen before it runs.

## What it consumes (measured, forward, report-only sources)
| metric | source | what it currently feeds (the assumption it may update) |
|---|---|---|
| **slippage_bps** per (account, instrument) | `ExecCostLedger` (proven-fresh fills, T-301) | the harness cost model (e.g. the SSO-leg slippage in the T-294 offense grid; the 1.5bps liquid-ETF assumption) |
| **fill_rate** per (account, instrument) | filled / submitted (pulse order log) | the harness's "orders fill" assumption (today: implicitly 100%) |
| **gate_pass_rate / defer_rate** | gate-b pass vs defer (freshness/exec gates) | the deployable-fraction / turnover-realized assumption |
| **reconcile_clean_rate** | clean held-position reconcile / trading day | the "state is trustworthy" operational assumption |

All four are OPERATIONAL rates the machine measures about ITSELF. None is a strategy parameter or a P&L-fit
signal (see the tripwires).

## The frozen rule (proposed)

### 1. Cadence — QUARTERLY, scheduled, never intra-quarter
Refresh runs on the **first pulse of each calendar quarter** (Jan/Apr/Jul/Oct). **Never** intra-quarter: a
single bad fill or one noisy week must not move an assumption — reacting fast IS the overfit trap. One refresh
= one versioned, logged config bump.

### 2. Minimum n — below it, KEEP the current assumption (no update)
An (account, instrument, metric) estimate updates only if it has accumulated `n ≥ N_min` **new** observations
since the last refresh. Below `N_min` → the current assumption stands, unchanged, and the shortfall is logged.
| metric | N_min | rationale |
|---|---|---|
| slippage_bps | **30 fills** | a mean of a noisy continuous quantity; 30 is the floor for a stable median |
| fill_rate | **60 orders** | a binomial rate; 60 gives a usable CI width |
| gate_pass_rate / defer_rate | **60 gate events** | ditto |
| reconcile_clean_rate | **60 trading days** | ~one quarter of daily reconciles |

### 3. Shrinkage — the measured value shrinks toward the CURRENT assumption (bounded, Bayesian)
No refresh ever adopts the raw measured value. It adopts a **shrinkage estimate** toward the current (prior)
assumption, with a prior pseudo-sample size `k` that makes the estimate move only at large n:
- **Rates (binomial: fill/gate/reconcile):** Beta prior centred on the current assumption `p0` with strength
  `k=100` pseudo-counts. New = `(k·p0 + successes) / (k + n)`. (A quarter of n≈60 moves `p0` by at most
  ~`n/(k+n)` ≈ 37% of the gap — most of the prior survives one quarter.)
- **Slippage (continuous):** normal shrinkage with `k=50` pseudo-observations. New =
  `(n·measured + k·current) / (n + k)`. At n=30 the measured value gets ≈37% weight; the current model keeps
  the majority for the first refresh.
`k` is the frozen "long-history prior strength" — it encodes *"one quarter is weak evidence; trust the standing
model until the data is heavy."*

### 4. Per-refresh change CAP — ≤ 25% relative move per quarter
Even at huge n, no single refresh may move an assumption by more than **25% of its current value** (rates
capped in absolute terms at ±0.10). A real regime shift is adopted over several quarters, not in one. This is
the hard rate-limiter on the whole loop.

### 5. What NEVER auto-updates — the tripwires (BINDING)
The rule touches ONLY the four operational rates above, feeding ONLY the harness's cost/operational
assumptions. It may NEVER auto-move any of:
- **Decision thresholds:** the beat-robo gate, the kill-thesis trigger (`[NN-SHARPE-CI]` `ci_low<0.4`), the
  DSR/MBL bars (`[NN-MBL]`), any pre-registered gate. These are human/pre-registered, permanently.
- **Strategy parameters:** lookback, band, leverage, weights, speeds — the T-152 / MetaLearner / HRP /
  concentration graves. Never fit from P&L, ever. (B/T-305: learning from what WORKS is a *data limit* with
  tripwires, not a permanent no — but the tripwire here is absolute: strategy params stay pre-registered.)
- **The measurement apparatus:** census gates, freshness gates, the calendar-HALT rule, `[NN-FAIL-CLOSED]`
  paths. Learning may never soften what catches its own errors.
- **DECISION-FLIPPING updates → HUMAN REVIEW, not auto-apply.** If a refreshed assumption would flip a live
  or candidate deploy decision (e.g. the SSO slippage moving the offense config from beats-SPY to loses-SPY,
  across the pre-registered **1.55 bps** breakeven, T-294/298), the auto-update **HALTS and escalates** — the
  number is recorded, but the flip is a human call. Learning tunes the *model*; it never silently changes the
  *verdict*.

### 6. Provenance + reversibility (`[NN-FAIL-CLOSED]`-aligned)
Every refresh writes a NEW versioned row to an append-only assumptions history
(`config/harness_assumptions.json` + `data/state/harness_assumptions_history.jsonl`) carrying, per changed
assumption: `quarter, account, instrument, metric, old, measured, n, k, shrinkage_weight, new, capped(bool),
tripwire_halt(bool)`. Fully auditable and revertible; a refresh is a logged config bump, never an in-place
mutation. The harness reads the current `harness_assumptions.json`; a missing/empty file fails closed to the
hardcoded defaults (never a fabricated one).

### 7. OOS by construction
The rule is fit on long history and FROZEN here. Each quarter it runs on the NEXT quarter's fills — data that
did not set the rule. So every refresh is out-of-sample by construction, exactly the T-305 "pre-register,
freeze, run OOS" discipline.

## Honest scope / non-claims
This is **operational-cost learning, not alpha learning.** It makes the machine's assumptions about its OWN
execution more accurate over time; it makes NO claim to find or improve alpha, and it cannot move a deploy
verdict (§5). Its value is that a validated config's honest cost inputs stop being a hand-measured constant
and become a bounded, self-correcting, fully-auditable estimate — with the one-quarter overfit trap and the
decision-flip trap both closed by construction.

## Build hand-off (AFTER the freeze)
On freeze: a `refresh_harness_assumptions(quarter, ledger, order_log, ...)` job implementing §1-6 (report a
diff + write the versioned history; the decision-flip tripwire calls out to the heartbeat, not to auto-apply),
plus `config/harness_assumptions.json` seeded from today's hardcoded defaults, plus tests (min-n gate,
shrinkage math, the 25% cap, the tripwire HALT on a synthetic decision-flip). N_trials = 0 (a policy + infra,
not a hypothesis).

---
**DRAFT — NOT ACTIVE.** Awaiting director freeze. On freeze this becomes the standing consume-policy and the
build proceeds. Any change after the freeze line = a new pre-registration.
