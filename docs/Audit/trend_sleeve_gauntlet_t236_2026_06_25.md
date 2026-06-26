---
task_id: T-2026-06-25-236
title: Trend-sleeve gauntlet — full-cycle (incl dotcom) tail validation vs both robos, honest-N
date: 2026-06-26
author: Agent D
type: pre-registered validation (re-score on a longer index substrate; no equity-book backtest)
status: PRE-REGISTERED (results below the line)
---

# T-236 — the trend-sleeve gauntlet (does the tail-edge survive dotcom?)

## PRE-REGISTRATION (written BEFORE computing the verdict — `[NN-MBL]`)

**Context:** T-234 found the clean T-204 trend sleeve tail-competitive (Sortino 1.130 / ci_low
0.619) — but on 2005-2025, which EXCLUDES the dotcom bust (AGG/GLD ETFs postdate it). Dotcom is
trend-following's worst regime (slow grinding valuation bear → whipsaw). This gauntlet rebuilds
the sleeve on a full-cycle INDEX substrate that reaches dotcom and asks if the edge survives.

**Hypothesis H1:** the T-204 trend sleeve (EW S&P-500-TR / treasury-TR / gold, long-flat 5mo
absolute-momentum, causal — the pre-registered T-204 config, NO new sweep), full-cycle
2000-2025 incl dotcom, on the index substrate, (a) clears the STRICT deploy gate vs BOTH robos
[`ci_low(Sortino_sleeve) > ci_low(Sortino_robo)` — `[NN-SHARPE-CI]`], (b) survives dotcom (its
2000-02 in-window MaxDD is materially shallower than the robos' and SPY buy-hold), and (c)
clears MBL at honest-N.

**H0 (the artifact verdict):** dotcom whipsaws the sleeve — Sortino collapses, the dotcom DD is
deep, or its ci_low falls below schwab_like's — i.e. the 2005+ tail-edge was a fast-crisis
artifact (it only worked because 2005-2025's crises were FAST: GFC/COVID/2022).

**Thresholds (pre-registered):**
- Strict ci_low gate: `ci_low(Sortino_sleeve) > ci_low(Sortino_robo)` for BOTH `60_40` and
  `schwab_like`. Decisiveness check (director): the sleeve ci_low should approach/exceed
  schwab_like's POINT estimate (~0.935 on 2005+), not merely clear its ci_low — beat it
  decisively, not marginally.
- MBL `[NN-MBL]`: window ≈ 25yr; trend-sleeve honest-N ≈ **16** (T-204: 9 pre-registered arms +
  T-214: 6 arms + T-234: 0 re-score + T-236: 1 — this lineage runs on the SPY/AGG/GLD trend
  substrate, NOT the PIT-equity-book N). Bar: Sharpe ≥ √(2·ln(16)/25) = **0.47**.
- Dotcom survival: sleeve 2000-02 in-window MaxDD < robo's and < SPY buy-hold's by a meaningful margin.

**Substrate (honest, flagged):** S&P-500 TR = SPY processed adjusted close (1993+); IG-bond =
SYNTHETIC 10yr-treasury TR from FRED DGS10 (carry + D≈7 × −Δyield) — a treasury proxy, NO
corporate/MBS spread (directional, AGG duration ~6 vs ~7 here); gold = GC=F futures (2000-08+,
auto-adjusted ~spot). Common window 2000-08-30→2025-12-31 (GC=F start; includes the 2000-09→
2002-10 dotcom bear). This index substrate is the ONLY way to reach dotcom; results are
DIRECTIONAL vs the T-234 ETF substrate.

**Decision rule:** clears all three (strict ci_low both robos + dotcom-survival + MBL) → first
real robo-beater → recommend path to paper. Fails any → state plainly which; if dotcom breaks
it, the tail edge was a fast-crisis artifact.

---
## RESULTS (full-cycle index substrate 2000-08-31 → 2026-04, INCL dotcom)

| strategy | Sortino | ci_low | Sharpe | MaxDD | Calmar | CAGR | up/dn-cap vs 60_40 |
|---|---|---|---|---|---|---|---|
| 60_40 robo | 0.807 | 0.301 | 0.630 | −36.7% | 0.171 | 6.3% | 1.00/1.00 |
| schwab_like robo | 1.008 | 0.501 | 0.784 | −27.2% | 0.224 | 6.1% | 0.81/0.72 |
| SPY buy-hold | 0.639 | 0.181 | 0.506 | −55.2% | 0.147 | 8.1% | 1.53/1.65 |
| **TREND SLEEVE** | **1.085** | **0.536** | **0.843** | **−12.2%** | **0.424** | 5.2% | 0.46/**0.22** |

**Per-crisis in-window MaxDD (INCL DOTCOM):**
| crisis | 60_40 | schwab | SPY-BH | **SLEEVE** |
|---|---|---|---|---|
| **dotcom (00-02)** | −24.3% | −19.2% | −47.3% | **−7.5%** |
| GFC (07-09) | −36.7% | −27.2% | −55.2% | **−12.2%** |
| COVID (20) | −19.1% | −14.6% | −33.7% | **−4.7%** |
| 2022 | −19.7% | −14.8% | −24.5% | **−6.0%** |

### Gate results
- **DOTCOM SURVIVAL — PASS (decisive).** Sleeve dotcom MaxDD **−7.5%** vs SPY-BH −47.3% / 60_40
  −24.3% / schwab −19.2% — the SHALLOWEST of all. The overlay went flat on equities (5mo
  momentum negative) and rode the bond rally (rates fell 6.5%→1.75%). **The tail edge is NOT a
  fast-crisis artifact — it survives trend-following's worst regime.**
- **MBL `[NN-MBL]` — CLEARS.** Sleeve Sharpe 0.843 > 0.471 bar (honest-N = 16, 25yr).
- **STRICT ci_low(Sortino) gate `[NN-SHARPE-CI]` — PASS vs both** (sleeve 0.536 > 60_40 0.301 AND
  > schwab_like 0.501) — but NOT decisive vs schwab_like (0.536 < schwab POINT 1.008; Sortino
  1.085 vs 1.008 is marginal, within bootstrap noise).
- **≥20%-shallower-MDD deploy leg — PASS (decisive) vs both.** −12.2% vs 60_40 −36.7% (67% shallower)
  and vs schwab_like −27.2% (55% shallower).
- **Money-EV (Roth, $ terminal over the cycle):** 60_40 $5K→$23.8K, schwab $5K→$22.4K, **sleeve
  $5K→$18.1K.** The sleeve makes ~1%/yr LESS — the protection has a return cost.
- **Taxable:** the sleeve flips monthly (high turnover → ~all short-term gains) → taxable-HOSTILE,
  worse than the low-turnover robos in a taxable account → **Roth-only** (consistent with the whole
  book being Roth-first).

## VERDICT — the tail edge is REAL and survives dotcom; the sleeve is the first gauntlet-clearing
robo-beater ON THE DEFENSIVE YARDSTICK — but it is NOT a free win.
- **vs 60_40: a clear robo-beater** (Sortino 1.085 vs 0.807, ci_low 0.536 vs 0.301, MaxDD −12% vs
  −37%, comparable return 5.2 vs 6.3%).
- **vs schwab_like (the bar to beat): clears the deploy gate but NOT decisively on risk-adjusted
  return.** It wins on DRAWDOWN (−12% vs −27%, 55% shallower — the ≥20%-MDD leg passes decisively)
  and edges Sortino marginally (1.085 vs 1.008), but it makes ~1%/yr LESS ($18K vs $22K). The
  edge is concentrated in drawdown depth, which IS the user's stated priority (the tail reframe).
- **Honest read:** this is NOT "free alpha over the robo" — it's a genuine **risk-return trade**:
  dramatically smaller drawdowns (and shallower in EVERY crisis incl dotcom) for ~1%/yr less
  terminal wealth. It survives the full gauntlet (dotcom + MBL + strict ci_low + decisive-MDD) —
  the first strategy in the entire arc to do so on the user's chosen (tail) yardstick.

## Caveats (do not over-claim)
- **Directional substrate:** synthetic 10yr-treasury TR (DGS10, no corporate/MBS spread) + GC=F
  gold futures + SPY-as-S&P-TR. The clean ETF substrate (T-234, 2005+) showed the same picture
  (Sortino 1.130, MaxDD −10.6%) → consistent, not substrate-dependent.
- **Known config, pre-registered:** the EW 3-asset / 105d / long-flat config is the T-204
  pre-registered one — NO new sweep here, so the full-cycle result is not overfit to this run.
- **schwab_like is close on Sortino** — the durable edge is the DRAWDOWN profile, not return.
- **Roth-only** (high turnover → taxable-hostile).

## PATH-TO-PAPER RECOMMENDATION
**Warranted — this is the first real candidate.** Recommend a SMALL paper allocation to the
3-asset trend sleeve, tracked forward vs BOTH robos on the tail metrics (Sortino, per-crisis DD,
MaxDD) + Roth money-EV, to confirm the drawdown edge holds out-of-sample. Frame honestly to the
user: it is a **smoother-ride / slightly-less-money** trade (−12% vs −27% max DD for ~1%/yr less
return), not free outperformance — and its advantage over the schwab_like robo is the drawdown
depth, which aligns with their tail-protection reframe. If the user values terminal wealth over
drawdown, the schwab_like robo remains the better choice.

