---
task_id: T-2026-07-02-269
title: Asymmetric EXITS (the "when to sell" trader skill) — FROZEN pre-registration
date: 2026-07-02
worker: Agent B
branch: feature/asymmetric-exits-t269
status: FROZEN pre-registration (bound BEFORE the run; ONE spec, NO sweep; N_trials += 1)
---

# T-269 — asymmetric exits: FROZEN pre-registration

**This spec is FROZEN before any result is seen.** One pre-registered trial. The
entry is a mechanical trigger; the HYPOTHESIS is the EXIT structure.

## Hypothesis (and the framing that makes it valid)
The **exit structure** — an asymmetric trailing stop (bounded loss, unbounded
gain: cut losers at a fixed stop, let winners run until a trailing pullback) —
manufactures **positive skew** and a risk-adjusted edge that a fixed-holding
backtest cannot express. The **entry is JUST a trigger**, not the hypothesis
(single-gene entries are H0 per T-196); we deliberately use a boring, classic
entry so any edge is attributable to the SELL discipline, not stock selection.
**Prior: LOW–MEDIUM (~15–20%)** — the stop-loss literature is mixed and
stock-level trend-riding is adjacent to killed momentum families; trailing-stop
trend-riding may just be time-series-momentum BETA (the kill-test below).

## Frozen spec (economic reasoning; NO sweep, NO re-tuning)
- **Universe (survivorship-free):** PIT S&P 500 membership
  (`data/universe/sp500_membership_pit.parquet`, `[ticker,start,end]` intervals)
  ∩ names with OHLC in `data/processed`. Entries are gated on PIT membership at
  the entry date; a name that LEAVES the index (delist/removal) is force-exited
  at its last available close. Delisted names are included (no survivorship).
- **Entry trigger (a boring classic):** a new **252-trading-day high** (close >
  the max close over the prior 252 sessions) AND the name is a PIT member that
  day. One position per name, no pyramiding. Signal at close t → enter at close
  t+1 (1-bar lag, causal).
- **Exit (THE HYPOTHESIS — asymmetric):** **Chandelier trailing stop** = (highest
  close since entry) − **3 × ATR(22)**. Exit at close t+1 when close t < the
  trail level computed from data through t−1 (causal stop level). **NO profit
  target** — winners run until the trail. Force-exit on PIT removal.
- **Sizing:** fixed **5% per position**, max **20 concurrent** (new entries
  skipped when full — a capacity cap, NOT a selection edge). Uninvested capital
  earns the **short rate** (DGS3MO). No leverage.
- **Costs:** **3 bps per side** (liquid large-cap) on entry + exit turnover.
- **Window:** full available (OHLC ∩ PIT overlap); report the span. Cash @ short
  rate throughout.

**Frozen parameter rationale:** 252d high = the classic 52-week Donchian breakout;
ATR(22) ≈ one month of range; Chandelier **k = 3** = the standard "let winners
run" trail that survives normal noise but cuts sustained reversals; 20-name cap =
diversification without over-dilution; 3 bps = large-cap liquid cost. All chosen a
priori and FROZEN — no optimization over any of them.

## Gates (all pre-committed)
1. **Skew (the mechanism's core claim):** does the exit structure actually
   manufacture positive skew? Report per-trade R-multiple skew AND daily-return
   skew. If skew is NOT positive, the mechanism failed on its own terms.
2. **Sortino + block-bootstrap ci_low** vs BOTH robos (60_40, schwab_like — D's
   fair harness), net of cost.
3. **`is_it_beta_or_edge` (FF5+Mom, HAC) — THE KILL-TEST:** decompose the daily
   returns; "edge-candidate" only if significant positive HAC alpha net of the
   factors. Trailing-stop trend-riding that decomposes to momentum beta = H0.
4. **Paired vs the trend sleeve (T-236 fair):** ΔSortino / ΔMaxDD block-bootstrap
   — does the exit skill add anything the sleeve doesn't already have?
5. **MBL at effective-N** on the Sharpe/Sortino ci_low.

## Decision rule
**Clears** iff: (positive skew confirmed) AND (Sortino ci_low > 0 AND beats ≥1
robo net-of-cost) AND (`is_it_beta_or_edge` = "edge-candidate": significant HAC
alpha net of FF5+Mom) AND (paired-vs-sleeve adds something). **H0** otherwise —
and the likely outcome per the prior is: the exit structure DOES manufacture
positive skew (mechanical) but the returns decompose to momentum beta (no
orthogonal alpha) and/or don't beat the robos net-of-cost. Either verdict closes
the user's standing "when to sell" question with EVIDENCE.
