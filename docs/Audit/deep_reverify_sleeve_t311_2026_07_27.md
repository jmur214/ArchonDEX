---
task_id: T-2026-07-27-311
title: T-311 DONE — deep re-verify of the trend sleeve on the 58-64yr substrate
date: 2026-07-27
worker: Agent B
branch: feature/deep-reverify-sleeve-t311
status: DONE. N_trials += 1 (one family). Pre-reg frozen 2026-07-27; run on the frozen spec, no deviation. SUPERSEDES the 2000-2026 T-255 as the real-money reference.
---

> ⚠️ **CORRECTION (2026-07-28):** the **MBL/DSR "CLEARS" sentence in this doc is RETRACTED.**
> It fed `[NN-MBL]` the sleeve's ABSOLUTE Sharpe (~1.5, overwhelmingly market beta) instead of the
> Sharpe of the CLAIMED EDGE. The active (difference) Sharpe vs buy-hold is **−0.210** — there is no
> positive edge to clear. **All substantive verdicts in this doc STAND** (they rest on paired
> block-bootstrap CIs on differences, the correct test). Canonical:
> `docs/Audit/mbl_framing_correction_t306_arc_2026_07_28.md`.

# T-311 — the sleeve on 64 years: the structural win CONFIRMED, the wealth verdict REVERSED

Pre-registration: `docs/Sources/prereg_deep_reverify_sleeve_t311.md` (director-FROZEN).
Script: `scripts/deep_reverify_sleeve_t311.py`. Data: `data/research/t311_deep_reverify.json`.
Substrate: T-306 `substrate_multidecade/`. Re-measurement of the FROZEN deploying config
({42,105,210} EW long/flat, T-255 fair conventions) — **nothing tuned**.

## PRIMARY — D-A 2-asset (equity+bond), 1962-01-04 → 2026-04-17 (64.3 yr)
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD | $10k → |
|---|---|---|---|---|---|---|
| **TREND SLEEVE** | **1.996** | **1.605** | 1.516 | 8.6% | **−11.6%** | $1,957,667 |
| buy-hold EQUITY | 0.876 | 0.551 | 0.690 | **10.4%** | −55.2% | **$5,726,097** |
| 60_40 | 1.176 | 0.814 | 0.888 | 8.8% | −33.1% | $2,240,638 |
| schwab_like (cash@mkt) | 1.331 | 0.962 | 1.004 | 7.9% | −26.7% | $1,350,746 |
| schwab_like (below-mkt sweep) | 1.297 | 0.928 | 0.978 | 7.7% | −26.8% | $1,181,106 |

**Paired block-bootstrap (sleeve − baseline; 21d blocks, 1000 iter, seed 0):**
| vs | ΔSortino 95% CI | Δcompound %/yr 95% CI | ΔMaxDD 95% CI |
|---|---|---|---|
| **buy-hold EQUITY** | **[+0.544, +1.027]** ✓ | [−4.77, +1.45] | **[+21.2%, +54.2%]** ✓ |
| 60_40 | **[+0.371, +0.799]** ✓ | [−1.90, +1.56] | **[+7.6%, +30.9%]** ✓ |
| schwab_like (cash@mkt) | **[+0.256, +0.688]** ✓ | [−0.71, +1.89] | **[+2.3%, +21.1%]** ✓ |
| schwab_like (below-mkt) | **[+0.282, +0.713]** ✓ | [−0.49, +2.11] | **[+2.4%, +21.4%]** ✓ |

**MBL/DSR: N=76, 64yr → required Sharpe 0.367; sleeve Sharpe 1.516 → CLEARS** (the
2000-2026 verdict could not clear DSR on any honest window; this one does, with margin).

**Methodology note (important):** the raw Δ*terminal-wealth* bootstrap is numerically
DEGENERATE over a 60+yr compounding window (terminal-multiple variance explodes → a CI
like [−6372, +110] that must NOT be read as "a tie"). The table reports **Δ compounding
rate (annualized log-wealth)** — the same economic question with a stable sampling
distribution. Both are in the JSON.

## SECONDARY — D-B 3-asset (equity+bond+gold), 1968 → 2026 (58.3 yr)
Same shape, same signs: sleeve Sortino 1.931 (ci_low 1.551) / MaxDD −14.3% / $1.71M vs
buy-hold 0.874 / −55.2% / $3.40M; ΔSortino [+0.490,+1.053] ✓, ΔMaxDD [+20.8%,+53.7%] ✓.
MBL required Sharpe 0.385, sleeve 1.425 → CLEARS.

## The three answers the deep window gives
**1. The drawdown-structural win: CONFIRMED, and it GENERALIZES.** Shallower in **9 of 9**
independent crises — including the three the shallow window never tested:
| crisis | sleeve MaxDD | buy-hold MaxDD |
|---|---|---|
| 1970 | −2.2% | −31.3% |
| **1973-74 stagflation** | **−2.9%** | **−48.2%** |
| **1980-82 Volcker** | **−6.2%** | **−20.2%** |
| **1987 crash** | **−4.9%** | **−33.1%** |
| 1990 | −3.4% | −20.8% |
| dotcom | −10.0% | −47.6% |
| GFC | −5.5% | −55.2% |
| COVID | −4.0% | −33.7% |
| 2022 | −6.4% | −24.5% |

ΔMaxDD CI is strictly positive vs **every** baseline. This is the sleeve's real, robust,
mechanism-driven edge.

**2. The Sortino edge: now CI-SIGNIFICANT (was only DIRECTIONAL on 2000-2026)** — ci_low
> 0 vs all four baselines. The deep window did what it was built to do.

**3. The wealth verdict: REVERSED vs buy-hold, HELD vs the robo.**
- vs **buy-hold equity**: the sleeve **LOSES** — $1.96M vs $5.73M (2.9×), CAGR 8.6% vs
  10.4%. The Δcompound CI spans zero but leans strongly negative (mean ≈ −1.7 pp/yr).
- vs **60/40**: the 2000-2026 "TIE" **HOLDS** (Δcompound CI spans zero symmetrically).
- vs **schwab_like (the actual robo benchmark)**: the sleeve **WINS** — Sortino + MaxDD
  significant, wealth point-estimate $1.96M vs $1.35M with the CI leaning positive.

## ⚠️ THE FINDING THAT MATTERS MOST FOR SEPTEMBER — a cash-rate regime split
The 64-year average **hides a regime dependence**. The sleeve's flat leg earns the short
rate, so "sitting out" is cheap when cash yields are high and expensive when they are not:

| era | avg cash | sleeve CAGR | buy-hold CAGR | verdict |
|---|---|---|---|---|
| **1962-1989** | **6.4%/yr** | **11.88%** | 10.00% | **sleeve BEATS buy-hold on wealth** |
| **1990-2026** | **2.7%/yr** | **6.04%** | 10.64% | **sleeve LOSES by 4.6 pp/yr** |

**The sleeve's deep-window wealth competitiveness is substantially a HIGH-CASH-RATE
artifact.** In the modern low-rate regime it underperforms buy-hold badly on wealth while
keeping its drawdown edge. This is the opposite of a flattering result and it is the most
decision-relevant thing in this document. (Context: today's EFFR ≈ 3.6% sits *between* the
two eras, so neither era is a clean forecast — but the mechanism is now measured, not
assumed.)

## Verdict → the September "robo → WHAT?" question
- **Beating the ROBO is settled: YES, decisively** — the sleeve wins Sortino + MaxDD with
  CI significance and wins wealth on point estimate. The fork-resolution bar ("beat the
  robo on the honest bar") is **CLEARED on the deepest honest window.**
- **But the max-wealth answer is BUY-HOLD EQUITY, not the sleeve** — 2.9× more terminal
  wealth over 64 years, at the price of a −55.2% drawdown vs the sleeve's −11.6%.
- **So the honest framing for the user's own directive** (max terminal wealth over ~40yr,
  *will not sell in downturns*): **if the won't-sell claim is genuine through a −55%
  drawdown, buy-hold equity maximizes wealth.** The sleeve buys a ~4.8× shallower
  drawdown for ~1.8 pp/yr of compounding — which is the right trade *only* if the
  won't-sell claim would break in a real −55% hole (the T-283 behavioral point:
  a bailout at the bottom destroys more wealth than the sleeve ever gives up).

## Disclosed caveats (frozen-accepted at freeze)
- **Anachronistic ETF-equivalent ERs** on the pre-ETF segment — conservative and
  **symmetric** (charged to sleeve and robos alike), so it cannot manufacture the result.
- **Pre-1993 equity is broad-market TR, not S&P-500** (T-306; FF-vs-SPY corr 0.9785).
- The 2-asset primary renormalizes schwab_like's gold weight away ({0.474/0.316/0.211});
  the 3-asset secondary restores the deployed weights and agrees on every sign.

## Status
**SUPERSEDES the 2000-2026 T-255** as the real-money reference. N_trials += 1 (one family,
jointly reported). **T-260 (ensemble-speed selection) is now unblocked** per the frozen
sequence; **T-314** (the adaptation rule) freezes against this deep frozen-spec baseline.
