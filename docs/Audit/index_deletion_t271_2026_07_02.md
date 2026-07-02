---
task_id: T-2026-07-02-271
title: S&P 500 index-deletion reversal — event study (the last uncovered event family)
date: 2026-07-02
author: Agent D (measurement lane)
type: PRE-REGISTERED event study (1 arm, N_trials += 1)
status: DONE — H0/NULL (fails gate + kill-test); last event family closed. Branch feature/index-deletion-t271
---

# T-271 — S&P 500 deletion-reversal event study

The completeness critic flagged index-deletion reversal as the one documented, long-only, retail-capacity
flow anomaly the audit never tested. Event dates are already on disk
(`data/universe/sp500_membership_pit.parquet`, 1,255 spells) and the T-265 event-study + SIP-price
machinery reuses directly.

## Hypothesis (H1)
Stocks **deleted from the S&P 500** are depressed by forced index-fund selling into the effective date,
then **REVERT** (positive abnormal returns) over the following 1-12 months — a flow/structure effect
(Chen-Noronha-Singal 2004, Shleifer 1986 in reverse), long-only-compatible (buy the deleted name after
the deletion), capacity-constrained (too small for institutions to bother). The reversal must survive a
**size-matched** control and factor adjustment — deleted names are small/value/junk, and "deleted names
bounce because small-caps bounce" is NOT the edge.

## Data scope + honest limitation
- Deletion events = membership rows with a non-null `end` (the ticker left the index on that date). 752
  total; **217 with `end` ∈ [2016-01, 2025-06]** — the SIP-priceable window (SIP floors 2016-01-04, needs
  ≥12mo post-deletion price). **Pre-2016 deletions are DATA-BLOCKED on the clean survivorship-complete
  feed** (SIP floor; yfinance/Stooq are survivor-biased/unreliable for delisted, per T-249/T-265). So the
  clean study is **2016-2025**, and the McLean-Pontiff decay read is **2016-19 vs 2020-25** (not
  pre/post-2015 — that era is unavailable on the honest feed). Stated as a limitation, not hidden.

## Method (pre-registered — no sweep)
- **Prices:** Alpaca SIP daily (adjustment=all) for each deleted ticker + SPY + **IWM** (Russell 2000,
  the size-matched control). Reuse the T-265 SIP path ("$0-marginal, paid feed", not free-tier).
- **Reason classification (tradeability filter):** a reversal is only tradeable if the stock keeps
  trading. **Rule-deletion / tradeable = the ticker has ≥126 trading days (~6mo) of prices after `end`.**
  M&A / cash-buyout / hard-delisting = prices stop at/near `end` → **NOT tradeable, EXCLUDED** (counted
  separately; a cash-acquired name has no reversal to capture). This price-continuation classifier is the
  load-bearing one; EDGAR 8-K reason labels (per T-265) are a secondary cross-check on a sample, not the
  gate.
- **Entry:** effective date `end` **+5 trading days** (let the forced index-fund selling clear — tradeable
  entry), also report from +1 for completeness.
- **Abnormal return:** CAR over [+5, +5+h] for h ∈ {21, 63, 126, 252} td (1/3/6/12mo), computed BOTH
  market-adjusted (`− SPY`) and **size-adjusted (`− IWM`)**. Lead with the IWM-adjusted (the fair control).
- **t-stat:** calendar-month-clustered Newey-West t (the T-265 `_nw_t` on monthly-grouped event means) —
  controls the earnings-season-style clustering of deletions.

## Gates (pre-registered)
- **Primary (signal exists):** mean **IWM-adjusted** CAR at the 3mo and 6mo horizons **> 0 with t_HAC ≥ 2.0**
  on the rule-deletion (survivor) set (`[NN-SHARPE-CI]` discipline — gate on the t, not the point).
- **Kill-test `is_it_beta_or_edge`:** the rule-deletion reversal portfolio's returns regressed on FF5+Mom
  (`core/factor_decomposition`) must retain a positive alpha with |t_HAC| ≥ 2 — net of SMB/HML the
  reversal must survive (else it's just small-value beta).
- **Decay:** report 2016-19 vs 2020-25 separately; a reversal that exists only pre-2020 is consistent with
  the literature's "index providers now stagger announcements to defeat front-running."
- **Sleeve-form test (ONLY if the event study clears):** a rolling equal-weight portfolio of names deleted
  in the trailing ~12mo, honest small/mid-cap cost (T-249: 35/75bps half-spread), Sortino + ci vs both
  robos. If the event study nulls, STOP — do not run the sleeve form.

## Honest prior — LOW-MEDIUM (~15-20%)
A real, mechanism-grounded long-side flow effect, but published (⇒ likely partly arbitraged) and the event
count is modest (~10-20 tradeable rule-deletions/yr → wide CIs). A null **closes the last uncovered event
family** and further tightens the comprehensive H0 (T-250/T-254/T-265/T-268). N_trials += 1.

---
## RESULTS (SIP, 2016-2025, entry = effective +5 trading days)

### Census / classification
217 deletion events 2016-2025 → 215 priced → **128 tradeable rule-deletions** (survive ≥6mo post-deletion)
+ **87 M&A / hard-delist EXCLUDED** (prices stop at deletion — cash buyouts have no reversal to capture).
The price-continuation classifier does the tradeability filter cleanly, no EDGAR needed.

### Post-deletion CAR by horizon (lead with IWM-adjusted — the size-matched control)
| horizon | CAR_mkt | t_HAC | **CAR_iwm** | **t_HAC** |
|---|---|---|---|---|
| 1mo | +0.0% | 0.67 | +0.1% | 0.90 |
| 3mo | +0.3% | 0.86 | **+1.0%** | **1.40** |
| 6mo | +1.3% | 0.38 | **+2.7%** | **1.36** |
| 12mo | +0.4% | −0.21 | +2.2% | 0.33 |

The reversal is **directionally positive** vs small-caps (IWM-adj +2.7% at 6mo) but **NONE clear the
t_HAC ≥ 2.0 gate**. Entry at **+1td is WEAKER** (6mo IWM +2.5%, t=1.36) → the null is not an
"entered-too-late" artifact; there is no front-loaded bounce being missed.

### Era split — the OPPOSITE of a decay pattern
| era | 6mo CAR_iwm (t) | 12mo CAR_mkt (t) |
|---|---|---|
| 2016-2019 (n=65) | −1.7% (0.22) | **−5.4% (−2.41)** ← significant *under*-performance |
| 2020-2025 (n=63) | +7.2% (1.61) | +6.4% (0.83) |

In 2016-19 the deleted names kept **under**performing (no reversal); the reversal appears **only** in
2020-25 (and even there t<2.0). This is the reverse of the McLean-Pontiff "arbitraged-away post-
publication" story and is consistent with the **2020-21 small-cap/meme rally** lifting these (small-cap)
names — a regime effect, not a stable flow edge.

### Factor kill-test (`is_it_beta_or_edge`) — DECISIVE: BETA, not edge
Rolling equal-weight 6mo-hold deletion portfolio (2,571 daily obs) regressed on FF5+Mom:
**alpha = +3.0%/yr, t_HAC = +0.40** — indistinguishable from zero. Betas: **MktRF +1.00, SMB +0.57,
HML +0.29**, CMA +0.38, **Mom −0.48** (R²=0.54). The portfolio is fully explained as **small + value +
negative-momentum** market beta — exactly the "deleted names are small-value-junk" concern. No distinct
reversal alpha survives factor adjustment.

## VERDICT — H0 / NULL. The last uncovered event family closes.
The S&P deletion reversal **fails the primary event-study gate** (best IWM-adjusted CAR +2.7% at 6mo,
t=1.36 « 2.0), **fails the factor kill-test decisively** (alpha t_HAC 0.40; the effect is small-value-junk
beta), and is **not robust** (significantly negative in 2016-19; positive only in the 2020-25 small-cap
rally; weaker at earlier entry). Per the pre-registered decision rule the event study does NOT clear →
**STOP; the sleeve-form test is not run** (no signal to deploy).

**Data honesty:** the clean window is 2016-2025 (SIP floor); pre-2016 deletions are data-blocked on the
survivorship-complete feed, so the "pre-2015 era" the literature emphasizes is unavailable here — but the
available era split already shows no stable edge, and the factor kill-test (which is era-agnostic and
well-powered) is decisive. IWM may be slightly small-tilted vs the mid-cap deleted names; a tighter
mid-cap control would only make the null firmer.

This closes the last documented long-only retail-capacity event family the audit flagged — further
tightening the comprehensive H0 (T-250 calendar / T-254 factor-momentum / T-265 small-cap PEAD / T-268
even-week). N_trials += 1. Reproducible: `scripts/index_deletion_t271.py`.

