# Wider-Breadth Trend Sleeve — VERDICT (T-214, 2026-06-18)

Reads against the **pre-registered** rules
(`trend_wider_breadth_preregistration_t214_2026_06_18.md`, locked `aa3fc98`
BEFORE the backtest). 6 new arms, `N_trials += 6`. Common window
**2006-02-03 → 2026-05-22** (DBC inception). Deterministic (md5-stable).
**Reproduce:** `python -m scripts.trend_wider_breadth_validation_t214`.

## Headline verdict
**Wider breadth buys SOME real convexity — but it is a TRADE-OFF, not a free
win, and "breadth" here is NOT "more diversification."** The literal
pre-registered rule is technically satisfied by Wide-9 EW 5-month (stronger
skew, lower MDD/crisis, capt > 0.7), but the honest read is that the wider
sleeve pays a real ~0.24 absolute-Sharpe cost, the capture-efficiency metric
**flatters** it against a weak baseline, and it is *more* cross-asset
correlated (not less). **The tight 3-asset SPY/AGG/GLD remains the better
core sleeve.**

## Baselines (buy-hold, common window)
| | Sharpe (ci_low) | MDD | skew d/m |
|---|---|---|---|
| 3-asset SPY/AGG/GLD | **0.86 (0.43)** | −24.3% | −0.19 / −0.44 |
| Wide-9 | 0.55 (0.12) | −36.1% | +0.03 / −0.85 |

**Already telling:** the Wide-9 buy-hold is *worse* than the 3-asset
(Sharpe 0.55 vs 0.86, MDD −36% vs −24%) — the extra ETFs (EFA/EEM/DBC/VNQ)
are lower-quality, higher-drawdown. The 3-asset is a near-optimally
diversified set to begin with.

## The arms (monthly skew = the convexity test)
| sleeve | weight | k | Sharpe (ci_low) | MDD | skew_m | capt | GFC / COVID / 2022 MDD |
|---|---|---|---|---|---|---|---|
| 3-asset | equal | 5mo | **0.85 (0.45)** | −10.6% | +0.14 | 0.99 | −10.6 / −6.6 / −6.8% |
| 3-asset | equal | 10mo | **0.87 (0.45)** | −11.1% | +0.01 | 1.01 | −10.9 / −11.1 / −5.3% |
| Wide-9 | equal | 5mo | 0.61 (0.23) | −8.9% | **+0.34** | 1.12 | −7.7 / −4.8 / −4.7% |
| Wide-9 | equal | 10mo | 0.62 (0.23) | −9.0% | +0.17 | 1.13 | −9.0 / −7.2 / −3.7% |
| Wide-9 | inv-vol | 5mo | 0.66 (0.25) | **−8.2%** | +0.07 | 1.21 | −6.6 / −6.0 / −4.6% |
| Wide-9 | inv-vol | 10mo | 0.65 (0.24) | −8.7% | −0.07 | 1.18 | −7.2 / −6.7 / −3.5% |
| Wide-9 | equal | 3mo | 0.51 (0.12) | −14.4% | +0.19 | 0.93 | −12.5 / −4.1 / −5.9% |
| Wide-9 | inv-vol | 3mo | 0.58 (0.16) | −9.5% | +0.09 | 1.06 | −6.4 / −6.0 / −5.8% |

## What's real vs what's flattery
- **REAL: more breadth strengthens the convexity + cuts the tail.** Wide-9
  EW 5mo monthly skew **+0.34** vs 3-asset EW +0.14, and every crisis-window
  drawdown is genuinely cut further (GFC −7.7 vs −10.6, COVID −4.8 vs −6.6,
  2022 −4.7 vs −6.8%). Not pure in-sample flattery — the tail improves.
- **THE COST: absolute Sharpe drops 0.85 → 0.61.** The breadth assets are
  low-quality; trend-following de-risks them but they don't ADD risk-adjusted
  return over SPY/AGG/GLD. The wider sleeve is a *worse risk-adjusted* sleeve.
- **THE FLATTERY: capture-efficiency lies here.** Wide-9 capt (1.12) > 3-asset
  capt (0.99) ONLY because capt is Sharpe(sleeve)/Sharpe(its-own-buy-hold)
  and the Wide-9 buy-hold is so weak (0.55). The capt ratio whitewashes the
  absolute-Sharpe loss — exactly the "more assets always looks better
  in-sample" trap the pre-registration flagged. **Do not prefer the wider
  sleeve on capt alone.**

## "Breadth" ≠ "diversification" — the correlation check (the honest caveat, confirmed)
Mean pairwise return correlation:
| | full | GFC-2008 | COVID-2020 | 2022 |
|---|---|---|---|---|
| 3-asset | **0.087** | 0.032 | 0.145 | 0.257 |
| Wide-9 | 0.229 | 0.156 | 0.314 | 0.337 |

The Wide-9 is **MORE correlated** than the tight 3-asset everywhere — and the
gap *widens* in crises (everything-sells-off). SPY/AGG/GLD is already a
near-orthogonal triad (corr 0.09); adding equity-flavored ETFs (EFA/EEM/VNQ)
*raises* average correlation. So the wider sleeve's better skew/MDD comes
from **trend-following more assets (each individually de-risked), NOT from
better diversification.** The pre-registered "everything-sells-off" caveat is
confirmed: breadth diversifies calm regimes far more than the tail.

## Inverse-vol trades skew for Sharpe/MDD
Wide-9 inverse-vol (5mo) has the best Sharpe (0.66) + MDD (−8.2%) of the
wide arms but **kills the skew** (+0.07 vs EW +0.34) — it down-weights the
vol-bombs (EEM/DBC/TLT) that were *providing* the convexity. EW is the
skew/convexity choice; inverse-vol is the smoothness choice.

## Recommendation (for the director)
- **Keep the 3-asset SPY/AGG/GLD sleeve as the core** (Sharpe 0.85-0.87,
  already orthogonal, the better risk-adjusted choice).
- The Wide-9 EW (5mo) is available as a **higher-skew / lower-Sharpe
  alternative** IF C's composition explicitly wants maximal convexity / tail
  (the stated skew preference) and accepts the ~0.24-Sharpe give-up. It is a
  deliberate trade, not a strict improvement — flag it as such; don't let the
  flattered capt metric auto-select it.
- Net: breadth is **not** the lever to chase. The 3-asset sleeve + the
  earlier vol-target / defensive-tilt levers are the better Phase-1 spend.

## NOT done (deferred, as pre-registered)
- Composing any sleeve into Engine C/B sizing — propose-first.
- The beat-the-robo / `evaluate_deploy_readiness` measurement — post-gate.
- OFF-default; canon unchanged (new script only); 9 module tests green;
  validation md5-deterministic.
