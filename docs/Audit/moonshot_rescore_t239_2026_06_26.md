---
task_id: T-2026-06-26-239
title: Moonshot / return-side Sortino re-score — does Sharpe bury an UPSIDE candidate too?
date: 2026-06-26
author: Agent D
type: re-score of existing/rebuildable sleeves (no equity-book backtest)
outcome: >
  NO. The parallel to T-234 does NOT hold on the upside. The prime suspect (T-214 Wide-9) has
  the skew (+0.33) Sharpe penalized, but it DILUTES return — CAGR 3.9% (lowest), terminal $11K
  (lowest), Sortino 0.831 (WORSE than the 3-asset sleeve's 1.103, below schwab_like 0.968), and
  up-capture 0.46 < the 3-asset's 0.53. The Sortino reframe surfaced a buried DOWNSIDE candidate
  (the trend sleeve) but does NOT surface a buried UPSIDE one — because the trend overlay
  structurally CAPS upside (long/flat), so no trend variant is a moonshot. The genuine
  asymmetric-upside half needs a NEW backtest of upside-AMPLIFYING asset selection
  (small-cap momentum / concentration / breakouts) — NOT leverage (cash Roth), NOT the trend
  family. A real moonshot half WOULD complement the trend sleeve; it just doesn't exist yet.
status: DONE (branch feature/moonshot-rescore-t239)
---

# T-239 — moonshot/return-side re-score: is there a buried UPSIDE half?

## Question
T-234 found Sharpe had buried the DOWNSIDE-half candidate (the trend sleeve) — Sortino surfaced
it. This is the parallel for the RETURN/UPSIDE half (the moonshot / asymmetric-upside objective,
[[project_retail_capital_constraint_2026_05_01]]): Sharpe penalizes big UP-swings (they inflate
the denominator); Sortino doesn't. So re-score the high-skew/return candidates on Sortino +
up-capture + skew. Prime suspect: **T-214 Wide-9** (skew +0.34, KILLED on Sharpe 0.85→0.61).

## Results (rebuilt sleeves + robos, 2005/06+ ETF substrate — DIRECTIONAL)
| strategy | Sortino | ci_low | Sharpe | mSkew | MaxDD | Calmar | CAGR | up/dn-cap | $5K→ |
|---|---|---|---|---|---|---|---|---|---|
| 60_40 robo | 0.775 | 0.276 | 0.633 | −0.62 | −38.5% | 0.177 | 6.8% | 1.00/1.00 | $19.8K |
| schwab_like robo | 0.968 | 0.446 | 0.786 | −0.65 | −28.8% | 0.231 | 6.7% | 0.81/0.71 | $19.2K |
| SPY buy-hold | 0.749 | 0.263 | 0.613 | −0.57 | −56.5% | 0.184 | **10.4%** | 1.56/1.56 | **$39.2K** |
| **TREND 3-asset** | **1.103** | **0.581** | 0.906 | +0.13 | −10.6% | 0.554 | 5.9% | 0.53/0.30 | $16.4K |
| **WIDE-9** | 0.831 | 0.310 | 0.656 | **+0.33** | −8.9% | 0.436 | **3.9%** | 0.46/0.38 | **$11.1K** |

## Verdict — NO buried upside candidate (the parallel doesn't hold)
- **Wide-9 has the skew but is a RETURN-DILUTER, not a moonshot.** Highest skew (+0.33) and
  shallowest MaxDD (−8.9%), but LOWEST CAGR (3.9%) and terminal ($11K) — the breadth assets
  (EFA/EEM/DBC/VNQ) are low-quality (confirming T-214). Even on Sortino it LOSES: 0.831 < the
  3-asset sleeve's 1.103 and < schwab_like's 0.968. Its **up-capture (0.46) is LOWER than the
  3-asset's (0.53)** — more breadth captured LESS upside, the opposite of a moonshot. **The
  Sortino reframe does NOT rescue Wide-9.**
- **Why the parallel fails:** the trend overlay is structurally DOWNSIDE-only — long/flat caps
  exposure at 1× and sits in cash in downtrends, so NO trend variant can be an asymmetric-upside
  moonshot. Adding breadth raises skew (more small de-grossing assets) but DILUTES return. The
  whole trend family (3-asset, Wide-9) is the downside half; there is no upside half hiding in it.
- **The upside IS available via plain equity beta** (SPY buy-hold: CAGR 10.4%, $39K) — but with
  no asymmetry and a −56% drawdown. A moonshot is upside WITHOUT the full drawdown — which the
  trend/breadth family cannot provide.

## The genuine moonshot half = a Step-2 BUILD (flagged, not run here)
An asymmetric-upside sleeve must AMPLIFY the right tail via ASSET SELECTION (a cash Roth cannot
lever, so leverage is out — the T-215 lesson):
- **Concentrated conviction-weighting** of the edge book (the EW/diversified book is closet-beta,
  T-117; concentrating the highest-conviction names could restore a right tail).
- **Small-cap / high-momentum universe** (the current universe is large-cap S&P — small-cap
  momentum has materially fatter right tails).
- **Breakout edges** (structurally asymmetric: small loss when wrong, large gain when right).
None has a saved equity curve → each is a NEW backtest, not a re-score. T-170 bought-MF
(KMLM/DBMF) is ANOTHER defensive sleeve (crisis-alpha), not a moonshot — same downside family.

## Recommendation
- **Do NOT pursue Wide-9** — the re-score confirms it's a higher-skew/lower-return defensive
  variant, dominated by the 3-asset trend sleeve on every axis that matters (Sortino, return, MDD).
- **The moonshot half is real strategic value but requires a Step-2 BUILD.** A working
  upside-amplifying sleeve WOULD complement the trend sleeve (downside half) → pair them to beat
  the robo on BOTH terminal wealth AND drawdown (fixing the trend sleeve's ~1%/yr give-up). The
  highest-prior, cash-Roth-deployable build is **concentrated/small-cap momentum** (asset
  selection, not leverage). Scope it as a pre-registered Step-2 if the user wants the upside half.
- **Honest read:** the Sortino reframe paid off ONCE (the downside trend sleeve) — it does not
  pay off a second time on existing artifacts. The upside half has to be built, not re-graded.
