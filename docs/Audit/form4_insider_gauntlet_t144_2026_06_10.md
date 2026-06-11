---
task_id: T-2026-06-10-144
title: Form-4 insider-cluster gauntlet (SEC feed) — the directional event-data test, dual-universe
date: 2026-06-10
author: Agent D (alpha/edge lane)
outcome: CLEAN MISS on both universes. 39,148 open-market insider buys (669
  tickers, 2006-2026) → cluster families K{2,3}×{20,60}d: Romano-Wolf StepM
  survivors NONE (membership-correct max |t| 0.63; survivor 0.45). Primary
  member α t = +0.14 / −0.08. FIRST DUAL-UNIVERSE EDGE TEST: verdicts AGREE —
  no survivor-sensitivity here. Structured-insider cell closes; the
  openinsider-vintage insider_cluster_v1 edge is RETIREMENT-PROPOSED
  (never better than its feed); the production repoint is MOOT. N_trials += 8.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.analyze_form4_clusters_t144  (determinism PASS ×2, md5 ba31f471…)
---

# T-144 — Form-4 insider clusters: the directional event test

## TL;DR

T-137 closed unconditional 8-K drift but flagged the structural gap: item
codes carry no sign. Form-4 is the structured-data answer — direction (P/S),
size, and role are native fields. On the T-136 canonical SEC feed (6.89M
transactions), with the T-137 multiplicity discipline, at 20-year depth, in
BOTH universes:

| universe | events (K2/K3) | StepM survivors | max \|t\| | primary K2_20d gate |
|---|---|---|---|---|
| **membership-correct (verdict)** | 1,539 / 639 | **NONE** | 0.63 | α +0.50%, t **+0.14**, ci[−1.86,+1.90] |
| survivor (comparison) | 2,366 / 1,068 | **NONE** | 0.45 | α −0.29%, t −0.08 |

Sub-periods all noise (|t| ≤ 0.52; signs flip between eras AND universes —
no decay story because there is nothing decaying). Mean daily abnormal
returns: −1.0 to +0.6 bps across the family. Breakeven costs 2-6 bps/side —
even costless, nothing is there.

## The dual-universe first (the T-136 payoff)

This is the first edge test in project history run on both the survivor and
the membership-correct universe. **The verdicts agree** — insider-cluster
drift is dead on both. Datum for the broader program: survivor bias (~10pp/yr
at the substrate level per T-136) does NOT automatically flip event-study
verdicts — market-adjusted event tests difference out much of the universe
drift. Prior event verdicts (T-137) gain credibility retroactively.

## Construction (pre-registered; feed-source parameter, prod default untouched)

Cluster trigger: ≥K distinct insiders filing open-market purchases
(TRANS_CODE 'P', subtype 'A') totaling ≥$50k within trailing 30 calendar
days; 30d per-ticker cool-off; **anchor = first close AFTER the FILING date**
(the PIT timestamp — transaction dates precede public knowledge). Family =
K∈{2,3} × horizons {20,60}d = 4 members × 2 universes (N_trials += 8,
honestly counted). Calendar-time portfolios, market-adjusted (member-mean for
the membership variant), Romano-Wolf StepM with joint CBB — all reused by
import from the T-137 module (one implementation, two tasks). Closes only.

## Verdicts and dispositions (per the pre-registered interpretation)

1. **The structured-insider cell CLOSES.** The literature's robust form
   (cluster buying) has no family-wise-significant drift on S&P large/mid
   caps at 20-year depth, either universe. Consistent with the established
   pattern: insider alpha concentrates in small caps; at our universe scale
   it is priced.
2. **insider_cluster_v1 → RETIREMENT-PROPOSED** (director/Engine-F gated, not
   executed): the edge was "never better than its feed" — and on the better
   feed, at depth, with multiplicity honesty, the construction family is
   zero. It has also never fired meaningfully in production (T-136
   reconciliation: clusters are rare AND, now we know, unprofitable).
3. **The production feed repoint is MOOT** — no reason to flip feeds for a
   dead edge. The SEC feed itself stays (it is the canonical insider panel
   for any future use; infra not wasted).
4. **Event lane next:** 13F crowding/connectedness is the last untested
   structured-event item on the frontier map; the directional-8-K text
   upgrade stays gated on the prompt-injection research. If 13F also misses,
   the structured-event lane closes as a class.

## Files

- `scripts/analyze_form4_clusters_t144.py` (NEW — pre-registered; imports the
  T-137 StepM/factor-gate machinery)
- `data/measurements/form4_gauntlet_t144/form4_cluster_analysis.json` (gitignored)
- This audit. Builds on: T-136 (feed + membership panel), T-137 (discipline).

## NOT included

- No production feed flip, no edges.yml/governor edits, no retirement
  EXECUTION (proposed only — Engine F lifecycle + director gate).
- No TASK_LEDGER write (T-114 — row in outbox). Branch only; director merges.
