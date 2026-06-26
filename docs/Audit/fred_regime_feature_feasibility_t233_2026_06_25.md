# FRED Credit / VIX-Term Regime Feature — FEASIBILITY VERDICT (T-233, 2026-06-25)

Reads against the pre-registration (`fred_regime_feature_preregistration_t233`,
locked `3babb56` BEFORE measurement). Branch
`feature/fred-regime-feature-feasibility-t233`. Deterministic. Reproduce:
`python -m scripts.fred_regime_feature_feasibility_t233`.

## VERDICT: REFUTED — no lead. The FRED credit / VIX-term signal is NOT an overlay-timing improvement.
Critically, **credit stress LAGS the always-on trend overlay in EVERY crisis,
and worst on the slow bears (dotcom, 2022) — exactly where it was hoped to
help.** No pre-registered A/B is proposed.

## Per-crisis: signal first de-gross vs overlay (SPY drawdown-at-trigger; lead in trading days, − = signal led)
| crisis | type | overlay de-gross | credit (BAA−AAA) | VIX level | VIX/VIX3M | DXY mom |
|---|---|---|---|---|---|---|
| dotcom | **slow** | 2000-07-31 (+4%) | 2001-03-14 (−14%) **+156td LAGS** | 2000-04-04 (+9%) −81td* | n/a (pre-2020) | n/a (pre-2006) |
| GFC | fast | 2007-10-22 (−4%) | 2007-11-16 (−7%) +19td lags | 2007-10-19 (−4%) −1td tie | n/a | 2007-11-30 (−5%) +28td lags |
| COVID | fast | 2020-02-26 (−8%) | 2020-03-09 (−19%) **+8td lags** | 2020-02-24 (−5%) −2td leads | 2020-02-24 (−5%) −2td leads | 2020-02-19 (0%) −5td leads |
| 2022 | **slow** | 2022-01-20 (−6%) | 2022-02-14 (−8%) **+17td LAGS** | 2022-01-19 (−5%) −1td tie | 2022-10-11 (−24%) **+182td LAGS** | 2022-03-04 (−10%) +30td lags |

\* the dotcom VIX "lead" is a **false de-gross**: it fired at **+9%** SPY (an
April-2000 vol spike during an SPY *rally*, before any drawdown) — a whipsaw,
not protection.

## The mechanism (why credit can't lead the price-trend)
1. **Credit spreads react to REALIZED stress; the price-trend reacts to
   PRICE.** A credit spread widens once defaults/illiquidity are visible —
   which is *after* equities have already broken trend. So the overlay
   (de-gross when SPY < its 5-month trend) leads credit by construction. The
   data confirms it: credit fired AFTER the overlay in all four crises, and
   12–17 trading days / 8–14pp of drawdown late on the slow bears.
2. **The slow bears are the worst case for credit, not the best.** dotcom and
   2022 ground lower with NO credit-event spike until late (dotcom credit
   fired at −14%; 2022 credit at −8%, and VIX-term never backwardated until
   −24%). The hoped-for "credit catches the slow valuation bear early" is the
   opposite of what happened.
3. **VIX signals only marginally lead the FAST V-crises** (COVID 2–5 td) and
   are trigger-happy (the dotcom false de-gross). They do NOT lead the slow
   2022 bear (1 td tie at best; term-structure fails). Marginal, non-robust.

## Decision rule → result
The pre-registered "LEADS" condition (≥5pp-earlier drawdown-at-trigger in ≥2
crises **including ≥1 slow bear**) is **NOT met** by any signal: no signal
de-grosses materially earlier than the overlay on dotcom OR 2022. → **REFUTED.**

## Data caveats (honest)
- **HY OAS (`BAMLH0A0HYM2`) deep history unobtainable** this session — the
  live FRED series is restricted to ~3yr (on disk 2023+) and the ALFRED
  vintage query returned HTTP 400. **BAA−AAA** (deep, 2000+) was the stand-in.
  HY OAS is *more sensitive* than Baa−Aaa, but it reacts to the SAME realized
  credit stress, so it would still LAG the price-trend — the conclusion is
  robust to the proxy (a more-sensitive credit signal fires earlier in
  *absolute* terms but still after the price breaks). A deep HY OAS pull
  (ALFRED/Wayback) would refine the magnitude, not the direction.
- **VIX/VIX3M** on disk is 2020+ only → dotcom/GFC term-structure unavailable
  (reported `n/a`, not fabricated — `[NN-FAIL-CLOSED]`).

## Outcome
**No lead — FRED credit/VIX-term regime feature is refuted as an
overlay-timing improvement.** The always-on price-trend overlay (T-204/220/221)
remains the front-line tail signal; it leads credit and matches/beats VIX
without the whipsaw. Consistent with T-221 (the overlay de-grosses early
everywhere) and T-220 (lagging regime classifiers don't improve a self-timing
signal). **Feasibility only — no integration, no canon change, OFF-default;
nothing built.**
