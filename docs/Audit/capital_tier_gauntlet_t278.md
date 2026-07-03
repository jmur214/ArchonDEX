---
task_id: T-2026-07-02-278
title: Capital-tier gauntlet — the deploying sleeve validated at every tier ($5K–$250K)
date: 2026-07-02
worker: Agent B
branch: feature/capital-tier-t278
status: DONE — 0 new N_trials (per-tier validation of the already-validated config). The per-tier config map.
---

# T-278 — capital-tier gauntlet (the investment-advisor map, column 1)

USER DIRECTIVE: the system must be CAPITAL-ADAPTIVE — validate the deploying trend
sleeve (105d long/flat SPY/AGG/GLD, EW; T-236) in WHOLE shares at every tier so the
per-tier map exists before the capital does. Extends the T-257 integer-share
machinery to 6 tiers × 2 instrument sets, fair T-255 conventions (flat leg @ short
rate, ER, 3bps/side), Carver deadband 0.05 (the deploying config). Window 2020-2026
(data/processed GLD starts 2020-04 → the HIGH-PRICE "deploy-today" regime; the
conservative granularity test — pre-2020's lower prices discretize finer).

## Per-tier result (deploying = deadband 0.05; TE(noDB) = the no-deadband churn baseline)
| tier | set | deploying TE | TE (no DB) | CAGR drift | MaxDD drift |
|---|---|---|---|---|---|
| **$5K** | SPY/AGG/GLD | 0.58%/yr | 0.76% | **−0.14pp** | −0.10pp |
| **$5K** | **SPLG/AGG/GLDM** ✓ | **0.37%/yr** | 0.12% | +0.41pp | −0.18pp |
| **$10K** | **SPLG/AGG/GLDM** ✓ | 0.41%/yr | 0.08% | +0.40pp | −0.47pp |
| $25K | **SPY/AGG/GLD** ✓ | 0.38%/yr | 0.15% | +0.42pp | −0.20pp |
| $65K | **SPY/AGG/GLD** ✓ | 0.43%/yr | 0.07% | +0.38pp | −0.51pp |
| $100K | **SPY/AGG/GLD** ✓ | 0.43%/yr | 0.06% | +0.37pp | −0.65pp |
| $250K | **SPY/AGG/GLD** ✓ | 0.44%/yr | 0.06% | +0.38pp | −0.70pp |

(✓ = the lower-TE / recommended set at that tier. CAGR drift is small and
noise-dominated on a 5.5yr window — the tracking error is the cleaner measure; MaxDD
drift < 1pp at every tier ⇒ the tail protection survives integer discretization at
all sizes.)

## The per-tier configuration map (deliverable)
| tier | instruments | expected drag vs continuous | config delta |
|---|---|---|---|
| **$5K** | **SPLG / AGG / GLDM** | TE ~0.37%/yr, CAGR within noise | **substitute low-price classes** (SPY 2 shares / GLD 3 shares is too coarse → 0.58% TE + a −0.14pp drag) |
| **$10K** | **SPLG / AGG / GLDM** | TE ~0.41%/yr | cheap classes still marginally better |
| **$25K** | SPY / AGG / GLD | TE ~0.38%/yr | granularity negligible — standard set fine |
| **$65K–$250K** | SPY / AGG / GLD | TE ~0.43–0.44%/yr | none — either set equivalent |

## What changes with size (the flags)
1. **Instrument set (the ONE real delta):** below ~$25K, use **SPLG (≈SPY/9) + GLDM
   (≈GLD/5)** — finer share granularity halves the discretization TE at $5K. Bonus:
   they also carry **lower expense ratios** (SPLG 0.02% vs SPY 0.09%; GLDM 0.10% vs
   GLD 0.40% — a durable ~5–10 bps/yr saving on the gold leg), so SPLG/GLDM are a
   defensible default at ALL retail tiers; SPY/GLD are only strictly preferred at
   >>$250K for maximum liquidity.
2. **Carver deadband — NO tier-scaling needed.** It is a weight-drift threshold
   (tier-invariant by construction). Its job is turnover control (T-148 tax lever):
   it trades a small, tier-invariant tracking-looseness (~0.4%/yr TE vs the ~0.06%
   no-deadband book at high tiers) for a large turnover reduction. At low tiers
   integer rounding is already a natural deadband, so the explicit 0.05 works
   unchanged at every tier.
3. **ADV / market impact — non-issue through $250K and far beyond.** A $250K
   rebalance trades ~$83K/name; vs the thinnest leg's ADV (AGG ~$825M) that is
   <0.02% — zero market impact. SPY ~$56B, GLD ~$5.3B ADV give orders of magnitude
   of headroom.

## Verdict
**The deploying sleeve is viable at EVERY tier from $5K to $250K** with only a
modest, well-characterized integer-share drag (~0.4–0.6%/yr tracking error, CAGR
drift within noise, MaxDD drift < 1pp — the tail protection is intact at all sizes).
The single tier-dependent configuration choice is the **low-tier instrument
substitution (SPLG/GLDM ≤ ~$10–25K)**; the deadband and ADV need no tier-scaling.
This is column 1 of the capital-adaptive investment-advisor map. Measurement only;
nothing enabled.
