---
task_id: T-2026-06-25-234
title: Tail re-score (Sortino + crisis-drawdown) of T-215 base/composition + sleeves vs both robos
date: 2026-06-25
author: Agent D
type: re-score of EXISTING equity curves (no new backtest, no cloud spend)
outcome: >
  The Sharpe→Sortino reframe was right to run — it surfaces a tail-competitive config that
  Sharpe + the base-book framing had buried. The T-215 COMPOSITION itself is still NOT
  tail-competitive (the no-return PIT equity book drags it: Sortino 0.113 < base 0.383 <
  both robos), though it DOES lose less than the 60/40 in every crisis. The standout is the
  CLEAN T-204 overlay SLEEVE (SPY/AGG/GLD long-flat, NOT the equity book): Sortino 1.130
  (ci_low 0.619) BEATS both robos (0.747 / 0.935) with comparable CAGR (5.82%) and crisis
  drawdowns 1/3–1/4 of the robo's. DIRECTIONAL (different substrate, 2005+ window) → the
  Step-2 candidate is the OVERLAY SLEEVE as the strategy, not the equity book.
status: DONE (branch feature/tail-rescore-step1-t234)
---

# T-234 — tail re-score: is anything tail-competitive with the robo?

## Method (no new backtest)
- **Robos (monthly-rebal):** `60_40` (SPY .60/AGG .40) + `schwab_like` (SPY .45/AGG .30/
  GLD .05/cash .20@4%), built from **raw stooq** SPY/AGG/GLD (the processed GLD was 2020+
  only; raw has 2005-02+), net of ER, monthly rebalance. `scripts/tail_rescore_t234.py`.
- **Strategies:** T-215 base + composition equity curves (rev5 S3 `portfolio_snapshots.csv`);
  the T-204 overlay sleeve via `core.trend_overlay.sleeve_returns` (reused, not re-run).
- **Metrics:** Sortino (+ block-bootstrap ci_low, `MetricsEngine.bootstrap_distribution`,
  1000 iter — `[NN-SHARPE-CI]`), MaxDD, Calmar, monthly up/down-capture, per-crisis in-window MaxDD.
- **⚠️ DATA CAVEAT `[NN-FAIL-CLOSED]`:** AGG/GLD inception ≈ 2005-02, so the robos cover
  **2005-2025 (GFC/COVID/2022) but NOT dotcom (2000-2002)** — the ETFs literally predate it.
  Robo dotcom numbers are NOT fabricated; flagged n/a. base/comp dotcom is reported standalone.

## Tail-metric table (common vs-robo window 2005-2025; base/comp are LEVERED — see T-215)
| strategy | Sortino | ci_low | MaxDD | Calmar | CAGR | up/down-cap vs 60_40 |
|---|---|---|---|---|---|---|
| 60_40 robo | 0.747 | 0.251 | −38.6% | 0.170 | 6.58% | 1.00 / 1.00 |
| schwab_like robo | **0.935** | **0.407** | −28.9% | 0.223 | 6.43% | 0.81 / 0.71 |
| T-215 BASE (lev) | 0.383 | −0.111 | −38.8% | 0.105 | 4.06% | 0.70 / 0.65 |
| T-215 COMPOSITION (lev) | 0.113 | −0.396 | −39.9% | 0.011 | 0.46% | 0.53 / 0.81 |
| **T-204 overlay SLEEVE** | **1.130** | **0.619** | **−10.6%** | **0.549** | 5.82% | 0.52 / **0.29** |

(MaxDD/Calmar for base/comp are LEVERAGE-CONTAMINATED — T-215 Engine-B per-name sizing, 3.48×;
Sortino/capture/crisis-DD are ~leverage-invariant and lead. Sleeve is un-levered.)

## Per-crisis MaxDD — does each strategy lose LESS than the robo? (the key tail question)
| crisis | 60_40 | schwab_like | BASE | COMPOSITION | **T-204 sleeve** |
|---|---|---|---|---|---|
| dotcom (00-02) | n/a* | n/a* | −58.0% | −23.8% | n/a* |
| GFC (07-09) | −38.6% | −28.9% | −38.8% | −31.7% | **−10.6%** |
| COVID (20) | −21.7% | −16.6% | −14.2% | −14.9% | **−6.6%** |
| 2022 bear | −20.8% | −15.7% | −8.3% | −4.3% | **−6.8%** |

*ETFs predate dotcom. — The **composition DOES lose less than the 60/40 in every crisis**
(GFC −31.7 vs −38.6, COVID −14.9 vs −21.7, 2022 −4.3 vs −20.8) — real crisis defense (the
overlay de-grosses, late but effective; T-221). But vs **schwab_like** it's mixed (GFC worse),
and the **T-204 sleeve dominates everything** (−6.6 to −10.6% in every crisis).

## Verdict — is anything tail-competitive with the robo?
1. **The T-215 COMPOSITION is NOT tail-competitive.** On the tail yardstick it still loses:
   Sortino 0.113 ≪ both robos, and WORSE than the base (0.383) — the overlay's crisis
   protection is real but it's bolted onto a **no-return PIT equity book** (CAGR 0.46%), so it
   buys defense by killing return. The schwab_like robo gets comparable crisis defense from
   20% cash + 5% gold while KEEPING 6.4% CAGR — it dominates the composition. **H0 holds for
   the composition even on Sortino.**
2. **The CLEAN T-204 overlay SLEEVE IS tail-competitive — it BEATS both robos.** Sortino
   1.130 (ci_low 0.619 > both robos' ci_low), CAGR 5.82% (≈ robo), MaxDD −10.6%, and crisis
   drawdowns ~1/3–1/4 of the 60/40's. **This is the "better defensive portfolio than the robo"
   the reframe was looking for** — Sharpe + the base-book-centric framing had buried it (T-204
   was filed as a "skew-for-Sharpe trade," not a winner). **The lesson: the win is the SLEEVE,
   not the equity book** — the equity book has no alpha (T-215 H0); the trend overlay is the
   asset.

## Sleeves — directional (different substrate/window; NOT the 26yr PIT base)
- **T-204 overlay sleeve (SPY/AGG/GLD):** the standout (above). DIRECTIONAL.
- **T-214 Wide-9 / T-170 bought-MF:** NOT re-scored here (their equity artifacts aren't on
  this worktree). From their own audits: Wide-9 was LOWER-Sharpe than the 3-asset (breadth
  assets low-quality, "breadth≠diversification" — T-214); bought-MF (KMLM/DBMF) is a separate
  defensive sleeve worth a tail look but needs its curve. **The 3-asset T-204 sleeve is the
  clear priority** — re-score Wide-9/MF only if Step-2 wants alternatives.

## HONEST caveats on the sleeve result (do not over-claim)
- **Different substrate:** SPY/AGG/GLD ETF trend-following, NOT the PIT equity book. Directional.
- **Window:** 2005-2025 (no dotcom — ETFs predate). Crisis-inclusive (GFC/COVID/2022) but the
  full-cycle dotcom leg is untested for the sleeve.
- **Known result, re-graded:** this is the SAME T-204 sleeve, now scored on Sortino (which by
  design rewards convex/defensive shapes — the reframe's whole point). Not new alpha.
- **schwab_like is close:** Sortino 0.935 vs the sleeve's 1.130 — a real, defensive competitor;
  the edge must survive honest-N + full-cycle to justify deploying over it.

## Step-2 recommendation
**Validate the T-204 overlay SLEEVE full-cycle as the deploy candidate** — reframed as "the
overlay sleeve IS the strategy" (a small base-equity allocation optional), measured vs both
robos on Sortino + crisis-drawdown + after-tax money-EV, honest-N, full-cycle (extend the
sleeve to a dotcom-capable bond/gold proxy if cheap). This is the one config that looks
tail-competitive with — and superior to — the robo on the right yardstick. Do NOT pursue the
T-215 composition (overlay-on-no-return-book) as a deploy candidate.
