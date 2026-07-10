---
task_id: T-2026-07-10-306
title: T-306 D-A BUILT — the multi-decade substrate (2-asset equity+bond core) + validation report
date: 2026-07-10
worker: Agent B
branch: feature/multidecade-substrate-scope-t306
status: D-A BUILT + validated. Regenerable via scripts/build_multidecade_substrate_t306.py (deterministic; FRED + Fama-French fetch). 0 N_trials (substrate build, not a measurement).
---

# T-306 D-A — multi-decade substrate BUILT (2-asset equity+bond, ~64yr)

Scope + director freeze: `docs/Sources/multidecade_substrate_scope_t306.md`. Build script:
`scripts/build_multidecade_substrate_t306.py` (deterministic; reuses the T-255 bond-TR
method verbatim). Output (regenerable, not committed — follows the T-255 CSV precedent):
`data/research/substrate_multidecade/` = `equity_tr_daily.csv`, `bond_tr_daily.csv`,
`cash_daily.csv`, `provenance.json`, `validation_report.md`.

## What was built
| Leg | Span | Source chain (oldest→newest) | CAGR (sanity) |
|---|---|---|---|
| **equity_tr_daily** | **1926-07-01 → 2026-04-17** (26,224 bars) | FF Mkt-RF+RF daily (broad-market TR) → SPY adj-close TR (S&P500) spliced at 1993-02-01 | **10.19%** (canonical long-run US equity TR ✓) |
| **bond_tr_daily** | **1962-01-03 → 2026-07-08** (16,112 bars) | FRED DGS10 → T-255 synthetic `(carry − 7·Δy).cumprod` | **5.59%** (10y-CMT TR ✓) |
| **cash_daily** | 1926-07-01 → 2026-05-29 (26,253 bars) | FF RF daily (short rate) | — |

**Joint 2-asset floor = 1962-01-03** (bond-bound; equity+cash reach 1926). **~64.3 yr.**
All legs are **index-level → survivorship-clean** (the Stooq single-stock survivorship
bias does NOT propagate here). Sources are **non-Stooq and refreshable** — the bot-wall
is irrelevant to this substrate.

## The MBL unlock (the headline)
`[NN-MBL]`: `T_required = 2·ln(75)/0.598² ≈ 24.1 yr`. Joint span **~64 yr → clears DSR for
the 0.598 baseline with ~2.7× margin** — the FIRST honest window on which the corrected
baseline clears at all (the 5-yr exploratory window needs SR≥1.55; the old 26-yr window
barely reached 24.1). This is the ceiling relief the whole program has been blocked on.

## Validation battery (bounds director-ruled)
- **REGRESSION — deep bond-synth vs the FROZEN `bond_synth_dgs10_t255` (same instrument+method):**
  median |Δret| **0.00e+00**, max 0.00e+00, **corr 1.0000** over 2000-01-05..2026-04-23
  (6,578 bars). **PASS** (≤0.15%). The deeper build reproduces the committed series
  *exactly* on the shared window — the extension adds history without perturbing the
  established substrate.
- **CONTEXT — FF broad-market vs SPY-TR** (1993-02-01+): median |Δret| **9.69e-04**, corr
  **0.9785** — within the 0.50% context bound. The pre-1993 equity segment is broad-market
  CRSP TR, **labeled "broad-equity" (not S&P-500)** per the disclosure rule; corr 0.98
  says the seam is clean.
- **CONTEXT — bond-synth vs AGG-TR** (2005-02-23+): median |Δret| **1.02e-03**, corr
  **0.7482** — the expected 10y-CMT-vs-aggregate duration/credit basis (informational; the
  synthetic is the index-level bond leg by construction).
- **calendar_guard:** max internal gap equity 12d / bond 5d / cash 12d — all ≤ 15d
  (the 12d equity/cash gaps are the 1933-era historical market closures, not data outages;
  fail-closed check passed).

## `[NN-SUBSTRATE-REVERIFY]` — demotions now in effect
Every verdict measured on the 2000–2026 substrate demotes to **"DEFENSIBLE (prior
substrate); re-verify required"** until re-run on this deep substrate. Re-run order
(director-ruled, each **individually pre-registered, +1 N_trial**): **T-255 → T-260 → T-298**,
then T-282/284/272/296/299 as they come up. This is the intended re-anchoring on **~8–10
independent crises vs the prior 4** — a feature, run per-verdict, never batched.

## D-B (the 3-asset substrate) status
**BLOCKED on LBMA gold sourcing** (1968+, off-FRED — both FRED LBMA IDs 404; no pre-2000
gold on disk; pre-1971 is a fixed peg). Chased in parallel; D-A does not depend on it.

## Durability note
The substrate is script-regenerable (deterministic from FRED DGS10 + Fama-French). It is
NOT committed to git (follows the T-255 CSV precedent — regenerable output, not source).
If the director wants it durable/shared across worktrees + the cloud, an S3 persist under
a `substrate_multidecade/` prefix (the altdata/news pattern) is a one-line follow-up.

**T-306 D-A built + validated.** Deliverable complete; awaiting the pre-registered T-255
re-verification as the next step.
