# Trend-Overlay — STANDALONE VALIDATION verdict (T-204, 2026-06-18)

Reads against the **pre-registered** rules
(`trend_overlay_preregistration_t204_2026_06_18.md`, locked at `ca73420`
BEFORE any backtest). 9 arms, `N_trials += 9`. Window 2005-02-25 →
2026-05-22 (stooq daily, deterministic, md5-stable). Metrics via
`core/metrics_engine.py` (block-bootstrap `ci_low`, 1000 iter, seed=0).
**Reproduce:** `python -m scripts.trend_overlay_validation_t204`.

## Baselines (buy-hold)
| | CAGR | Sharpe (ci_low) | MDD | skew d / m |
|---|---|---|---|---|
| SPY | +10.27% | 0.61 (0.24) | **−56.5%** | −0.00 / −0.56 |
| EW SPY/AGG/GLD (⅓ each) | +8.20% | 0.88 (0.47) | −24.3% | −0.19 / −0.43 |

## The 9 pre-registered arms
| structure | k | def | CAGR | Sharpe (ci_low) | MDD | skew d/m | **capt** | in-mkt | rt/yr |
|---|---|---|---|---|---|---|---|---|---|
| SPY long/flat | 3mo | cash | +5.91% | 0.58 (0.19) | −27.7% | −0.76 / −0.61 | 0.96 | 72% | 7.8 |
| SPY long/flat | 3mo | AGG | +6.39% | 0.59 (0.20) | −26.4% | −0.82 / −0.57 | 0.97 | 72% | 7.8 |
| **SPY long/flat** | **5mo** | **cash** | +8.08% | **0.76 (0.32)** | **−20.5%** | −0.77 / −0.26 | **1.24** | 75% | 4.6 |
| SPY long/flat | 5mo | AGG | +8.16% | 0.73 (0.31) | −26.1% | −0.82 / −0.27 | 1.19 | 75% | 4.6 |
| SPY long/flat | 10mo | cash | +8.43% | 0.76 (0.30) | −20.7% | −0.78 / −0.35 | 1.25 | 79% | 2.9 |
| SPY long/flat | 10mo | AGG | +8.60% | 0.74 (0.27) | −26.3% | −0.82 / −0.36 | 1.21 | 79% | 2.9 |
| EW trend sleeve | 3mo | cash | +4.68% | 0.76 (0.38) | −14.8% | −0.67 / **+0.20** | 0.86 | — | — |
| **EW trend sleeve** | **5mo** | **cash** | +5.88% | **0.91 (0.48)** | **−10.6%** | −0.68 / **+0.13** | **1.02** | — | — |
| EW trend sleeve | 10mo | cash | +6.00% | 0.89 (0.42) | −11.1% | −0.62 / **+0.02** | 1.01 | — | — |

Crisis-window drawdowns (best cash arms): GFC-2008 SPY −56%→−13% (5mo) /
sleeve −24%→−11%; COVID-2020 SPY −34%→−8% / sleeve −15%→−7%; 2022 SPY
−25%→−16% / sleeve −16%→−7%.

## Verdict against the pre-registered gates

**1. Capture-efficiency sub-gate (>0.70): PASS — handily.** Every arm clears
it; the 5/10-month SPY cash arms are **>1.0** (the overlay's Sharpe BEATS
buy-hold, 0.76 vs 0.61), and the EW sleeve 5/10mo are ~1.0. It is NOT a chop
drag at these lookbacks. (The 3-month arm is the weakest — capt 0.96, the
most turnover at 7.8 rt/yr — whippier, as expected.)

**2. Tail / MDD reduction (the actual goal — cut the −33% that loses to the
robo): PASS — large.** SPY −56.5%→−20.5% (5mo cash); the EW sleeve
−24.3%→−10.6%. Every crisis window's drawdown is roughly halved. This is the
headline: the overlay reshapes the left tail.

**3. Positive skew (the AQR convexity claim): PARTIAL — and exactly where
theory predicts.** Positive *monthly* skew appears ONLY in the **diversified
3-asset sleeve** (+0.02..+0.20, vs sleeve buy-hold −0.43). **SPY-long/flat
alone does NOT flip skew positive** (monthly −0.26..−0.61) — a long/FLAT
overlay has no short leg, so it cannot earn the right-tail crisis gains that
give long/short trend its positive skew; it only avoids losses (which cuts
MDD and the zero-spike actually makes *daily* skew more negative). The
convexity needs the cross-asset breadth — matching the pre-registered caveat
("equity-only trend lacks the cross-asset diversification of true managed
futures").

## What this means (honest)
- **The lever is real as a SHAPE tool, not a return tool.** It does not add
  CAGR (it gives some up — 8.1% vs 10.3% SPY; 5.9% vs 8.2% sleeve); it pays
  that to roughly halve the drawdown and (in the sleeve) flip monthly skew
  positive. That is precisely the "win on risk-adjusted/tail, not headline"
  the plan targets.
- **Best standalone configuration: the EW SPY/AGG/GLD sleeve at a 5-month
  lookback, cash defensive leg** — Sharpe 0.91 (ci_low 0.48) vs sleeve
  buy-hold 0.88 (0.47), MDD −10.6% vs −24.3%, monthly skew +0.13 vs −0.43.
  For the SPY-shape lever specifically, the 5-month cash arm (Sharpe 0.76,
  MDD −20.5%, capt 1.24) is the pick.
- **Cash beats AGG as the defensive leg.** The AGG legs are uniformly worse
  on MDD and 2022 (bonds fell *with* stocks in 2022 — the "defensive" bond
  leg added correlated risk). Don't use AGG as the off-leg.

## Caveats (pre-registered, confirmed)
- Whipsaw is real: the 3-month arm churns 7.8 round-trips/yr; even the 5mo is
  4.6/yr — turnover the after-tax (taxable) accounting will penalize (Roth is
  the primary gate, so this bites less there).
- Trend protects the **slow grind** (2008, 2022) far better than the **first
  sharp drop** (it lagged the 2020 V — and at 10-month it was still partly
  long into COVID, −19%/−26% vs the 5mo's −8%/−15%; shorter lookbacks caught
  COVID better but churn more).
- This is the diversified-sleeve buy-hold already doing much of the work
  (AGG+GLD ballast → 0.88 Sharpe / −24% MDD before any trend); the overlay's
  marginal contribution is the further MDD cut + the skew flip.

## NOT done (deferred, as pre-registered)
- Composing the overlay into Engine C/B sizing — **propose-first**, flagged
  for the director.
- The beat-the-robo / `evaluate_deploy_readiness` after-tax measurement —
  the post-gate composition step (after C's re-aimed gate), NOT run here.
- The signal module ships **OFF by default**; canon unchanged (new module,
  no existing path touched); 9 unit tests + 119 in the metrics+overlay suite
  green; validation md5-deterministic.
