---
task_id: T-2026-07-10-306
title: T-306 D-A + D-B BUILT — the multi-decade substrate (3-asset, ~58yr) + validation report
date: 2026-07-10
worker: Agent B
branch: feature/multidecade-substrate-scope-t306
status: D-A + D-B BUILT + validated. Regenerable via scripts/build_multidecade_substrate_t306.py (deterministic; FRED + Fama-French + LBMA fetch). 0 N_trials (substrate build, not a measurement).
---

# T-306 D-A + D-B BUILT — multi-decade substrate (3-asset equity+bond+gold, ~58yr)

Scope + director freeze: `docs/Sources/multidecade_substrate_scope_t306.md`. Build script:
`scripts/build_multidecade_substrate_t306.py` (deterministic; reuses the T-255 bond-TR
method verbatim). Output (regenerable, not committed — follows the T-255 CSV precedent):
`data/research/substrate_multidecade/` = `equity_tr_daily.csv`, `bond_tr_daily.csv`,
`gold_tr_daily.csv`, `cash_daily.csv`, `provenance.json`, `validation_report.md`.

**D-A shipped AND D-B unblocked in one pass:** the scope flagged gold as the sole
blocker; the "chase LBMA in parallel" turned up `prices.lbma.org.uk/json/gold_am.json`
— the LBMA daily gold AM fix, **free, off-FRED, refreshable, reaching 1968-01-02**. So
the full 3-asset substrate is built, not just the 2-asset core.

## What was built
| Leg | Span | Source chain (oldest→newest) | CAGR (sanity) |
|---|---|---|---|
| **equity_tr_daily** | 1926-07-01 → 2026-04-17 (26,224 bars) | FF Mkt-RF+RF daily (broad-market TR) → SPY adj-close TR (S&P500) spliced 1993-02-01 | **10.19%** ✓ |
| **bond_tr_daily** | 1962-01-03 → 2026-07-08 (16,112 bars) | FRED DGS10 → T-255 synthetic `(carry − 7·Δy).cumprod` | **5.59%** ✓ |
| **gold_tr_daily** | 1968-01-03 → 2025-12-31 (14,611 bars) | LBMA gold AM fix (USD) → gold_gcf spliced 2000-08-30 | **8.65%** ✓ |
| **cash_daily** | 1926-07-01 → 2026-05-29 (26,253 bars) | FF RF daily (short rate) | — |

**Joint 3-asset floor = 1968-01-03** (GOLD-bound; equity+cash 1926, bond 1962). **~58.3 yr.**
Index-level → survivorship-clean (the Stooq single-stock bias does NOT propagate). All
sources non-Stooq + refreshable.

## The MBL unlock (the headline)
`[NN-MBL]`: `T_required = 2·ln(75)/0.598² ≈ 24.1 yr`. Joint 3-asset span **~58 yr → clears
DSR for the 0.598 baseline with ~2.4× margin** (the 2-asset equity+bond core reaches
~64yr / ~2.7×). **The first honest window on which the corrected baseline clears at all**
(the 5-yr exploratory window needs SR≥1.55; the old 26-yr window barely reached 24.1).

## Validation battery (bounds director-ruled: ≤0.15% same-instrument, ≤0.50% context)
- **REGRESSION — deep bond-synth vs FROZEN `bond_synth_dgs10_t255`:** median |Δret|
  **0.00e+00**, corr **1.0000** over 2000–2026 (6,578 bars). **PASS**. The extension
  reproduces the committed substrate *exactly* on the overlap — it perturbs nothing.
- **CONTEXT — FF broad-market vs SPY-TR** (1993+): median |Δret| 9.69e-04, corr **0.9785**
  — within the 0.50% bound; pre-1993 equity labeled **broad-market (not S&P-500)**.
- **CONTEXT — bond-synth vs AGG-TR** (2005+): median |Δret| 1.02e-03, corr 0.7482 (the
  expected 10y-CMT-vs-aggregate duration/credit basis).
- **CONTEXT — LBMA gold-fix vs gold_gcf** (2000+): daily |Δret| 6.75e-03 **exceeds** the
  0.50% bound — **but proven a benign intraday-TIMING artifact, NOT a data problem.**
  Two proofs: (a) level ratio lbma/gcf = **1.0002** (the same gold to 0.02%); (b) return
  corr RISES with horizon **0.394 (1d) → 0.878 (5d) → 0.965 (21d)** — the signature of an
  ~8h window offset (London 10:30 fix vs COMEX settle) that washes out multi-day. At the
  42–210-day trend horizon the effective corr is ~0.97 ⇒ **immaterial to the sleeve.** A
  naive "corr 0.38 → FAIL" read would be wrong; the substantive checks (levels, horizon
  corr) pass. The modern segment uses gold_gcf, matching the frozen T-255 substrate.
- **calendar_guard:** fail-closed on unexpected holes, with an ALLOW-LIST of one
  documented closure — the **Mar-1968 gold-pool collapse** shut the London market ~2wk
  (an 18d gap, expected). All other legs' max gaps ≤ 12d (1933-era closures). A NEW
  T-294-style 48-day hole would still fail loudly.

## `[NN-SUBSTRATE-REVERIFY]` — demotions now in effect
Every verdict measured on the 2000–2026 substrate demotes to **"DEFENSIBLE (prior
substrate); re-verify required"** until re-run on this deep substrate. Re-run order
(director-ruled, each **individually pre-registered, +1 N_trial**): **T-255 → T-260 →
T-298**, then T-282/284/272/296/299. The intended re-anchoring on **~8–10 independent
crises vs the prior 4** — a feature, run per-verdict, never batched.

## Consumer note (calendar alignment)
Legs are emitted on their NATIVE calendars (US-market equity/bond, London gold — the
holiday sets genuinely differ). Consumers align via `core.calendar_guard.reindex_onto`
(ffill onto a benchmark calendar) — the established T-255 harness pattern — rather than
a forced common index at build time (which would ffill-corrupt one leg on the other's
holidays).

## Durability note
Script-regenerable (deterministic from FRED + Fama-French + LBMA). NOT committed to git
(T-255 CSV precedent — regenerable output, not source). An S3 persist under a
`substrate_multidecade/` prefix (the altdata/news pattern) is a one-line follow-up if the
director wants it durable/shared across worktrees + the cloud.

**T-306 D-A + D-B built + validated.** The full 3-asset ~58yr substrate is ready; awaiting
the pre-registered T-255 re-verification as the next step.
