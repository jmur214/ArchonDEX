---
task_id: T-2026-06-10-135
title: Overnight/intraday composition (Lou-Polk-Skouras) — first frontier edge through the gauntlet
date: 2026-06-10
author: Agent D (alpha/edge lane)
outcome: The LPS structure REPLICATES on our data — and contains the FIRST
  strict-gate factor-α this project has ever measured (overnight component
  α=+13.9%/yr, t=+5.69, ci[+4.51,+13.45] — ci_low clears t>2) — but it is
  UNHARVESTABLE - the intraday side nets it to zero (total tradeable α=−1.05%,
  t=−0.41, MISSES t>2) and direct overnight-only execution is cost-dead ~4-5×
  at retail fees. Verdict: closed cell, with the sharpest mechanism yet.
  N_trials += 1. Determinism PASS.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.analyze_overnight_intraday_t135   (seed 0, bit-identical ×2)
---

# T-135 — the first frontier edge: LPS overnight/intraday composition

## TL;DR — the structure is real; the harvest is not

Canonical construction (documented per brief): **Lou-Polk-Skouras (JFE 2019)
overnight-return persistence** — monthly rebalance, rank on trailing 21-day
mean overnight return (r_on = Open_t/Close_{t-1}−1), long top / short bottom
tercile, inverse-vol legs, dollar-neutral, 5 bps/turnover. House deviations
stated: terciles not deciles (universe breadth), inverse-vol legs (house risk
convention). Window 2000-2025 (26 yr), breadth 246-662 names (median 519),
survivor-only substrate → α upper bounds; PIT membership re-test deferred.

| object | α ann | α t | 95% CI | clears t>2 | Sharpe (ci_low) |
|---|---|---|---|---|---|
| **TOTAL close-to-close (the tradeable verdict object)** | **−1.05%** | **−0.41** | [−3.58, +1.00] | **NO** | −0.03 (−0.62) |
| Overnight component (diagnostic) | **+13.88%** | **+5.69** | **[+4.51, +13.45]** | **YES — strict ci_low>2** | +0.76 |
| Intraday component (diagnostic) | −12.7%/yr ann. drag | — | — | — | — |

**The LPS tug-of-war replicates exactly as published:** the overnight
component of the spread earns +13.6%/yr with the project's first-ever
strict-gate-clearing t-stat, the intraday component fights it at −12.7%/yr,
and the net — the only thing a close-to-close system can trade — is zero.
Structure diagnostic: cross-sectional rank persistence of the overnight
component is mean Spearman +0.101, 83% of months positive, t≈14.6.

## Why "just trade MOC/MOO" does not rescue it (pre-empting the follow-up)

The overnight harvest (enter market-on-close, exit market-on-open, both legs)
is simulable for free from daily OHLC, but the arithmetic kills it:

- gross overnight spread ≈ 13.6%/yr ÷ 252 ≈ **5.4 bps/day**;
- daily round-trip of ~2× gross exposure ≈ 4 turnover-units/day →
  at our standard 5 bps/side: **~20 bps/day cost ≈ −50%/yr** (dead 4-5×);
  even at institutional ~1 bp/side: ~10%/yr cost vs 13.6%/yr gross → net
  ~+3.6%/yr *before* slippage on auction fills — marginal at best, and not at
  retail. This matches the literature's own conclusion: the overnight drift is
  a market-maker/zero-cost phenomenon, not a retail-harvestable edge.
- The LOW-cost route (monthly-rebalanced total-return version) is exactly what
  we measured: α −1.05%, t −0.41. Both ends of the frequency spectrum close.

So the cell closes **definitively** — not "execution-blocked, revisit later":
high-frequency harvest = cost-dead; low-frequency harvest = alpha-zero.

## Data hygiene (documented; cleaning, NOT variant-shopping)

The first (raw) run produced ±1000%/yr offsetting overnight/intraday
components — a corruption signature, not economics. Diagnosis: **83 corrupt
open prints** (open hundreds of log-% from prior close, snapping back by the
close — e.g. SBNY 2025-11-06 r_on −6.48 / r_id +6.46; vendor artifact in the
Stooq-extended files; same-day OHLC internally consistent so the T-129-era
close-only work is unaffected). Repairs: (1) snap-back rows (|r_on|>25% AND
|r_id|>25%, opposite sign) → open treated as untrusted (r_on:=0, r_id:=total);
(2) signal input winsorized at ±20% so one residual bad print cannot own a
21-day mean. **Raw run preserved as sensitivity:** raw total α −5.08%
(t −1.98) vs cleaned −1.05% (t −0.41) — the corrupt opens were *manufacturing
spurious negative* alpha via the signal ranks; the verdict (miss) is the same
under both. Open-quality audit by year: open==close ≤4% (1999, worst), ~1%
typical; opens outside [Low,High] ≈ 0% — full window usable.

## Orthogonality + loadings

Total-return loadings near zero (MktRF −0.01, Mom +0.20, R²=0.03) — the
strategy is genuinely factor-orthogonal; it just has no net alpha. Correlation
to the existing book: **+0.001** (fully orthogonal).

## Verdict (per the pre-registered interpretation) + next item

**MISS — one more closed cell**, stated plainly. But the most informative miss
of the arc: the first strict-gate t>2 α the project has measured exists in our
data and is structurally inaccessible at our execution costs. Two forward
implications:

1. **The frontier process works.** One cheap test (1 N-trial, zero new data)
   replicated a top-journal anomaly, located the alpha to the hour of day, and
   priced the harvest. The map's ranking logic is validated even when the item
   misses.
2. **Recommended next frontier item: 8-K event-type reactions** (map #2;
   different DATA, EDGAR fetcher pattern exists) — with the **Form-4 feed
   repoint** as the cheap parallel item (insider edge exists, feed dir is 0 B).
   The metalearner-training dispatch (T-132 weak-prior GO) remains third.

## Files

- `engines/engine_a_alpha/edges/overnight_intraday_edge.py` (NEW — candidate,
  status='candidate', NOT promoted; mirrors xsec_momentum)
- `scripts/analyze_overnight_intraday_t135.py` (NEW — pre-registered; data
  hygiene documented inline)
- `data/measurements/overnight_intraday_t135/overnight_intraday_analysis.json`
  (gitignored; raw-sensitivity copy in /tmp note — numbers quoted above)
- This audit. Builds on: T-132 map (#1 item), T-129 discipline.

## NOT included

- No promotion, no governor/edges.yml edits committed (edges.yml gitignored).
- No MOO/MOC execution build (priced out above — would need ~1bp/side to be
  marginal; not proposed).
- No variant sweep (ONE canonical construction per pre-registration).
- No TASK_LEDGER write (T-114 — row in outbox). Branch only; director merges.
