---
task_id: T-2026-06-26-254
title: Factor momentum (Ehsani-Linnainmaa) — is timing factors by their own returns a real edge?
date: 2026-06-26
author: Agent D
type: pre-registered probe (free, orthogonal to the single-signal sweep)
outcome: >
  FAIL the edge test — decisively. Factor momentum (timing FF5+Mom factors by their own trailing 12-1
  returns) is MOMENTUM-FACTOR BETA, not a new timing edge: alpha net of FF5+Mom is t_HAC=0.49 (both
  variants; ann alpha ~0.3%), and it is 69-73% correlated with the Mom factor. It IS the momentum
  factor by construction (E-L's own point). No new alpha for a retail Roth — the deployable form is
  just holding MTUM (a known factor beta that hasn't beaten the robo net of cost). Coverage gap closed.
status: DONE (branch feature/factor-momentum-t254)
---

# T-254 — factor momentum (the meta-effect we never tested)

## PRE-REGISTRATION (rule FIXED by the paper — no sweep)
Ehsani-Linnainmaa (JF 2022): factor momentum subsumes individual stock momentum — a factor's own
recent return predicts its next. We tested 35 signals INDIVIDUALLY but never whether the FACTORS'
own returns predict the factors'. **Rule (verbatim, no DOF):** each FF5+Mom factor timed by its own
trailing **12-1** return (11-month cum, lagged 1mo); long recently-winning factors, monthly rebalance.
**The KILL TEST = `is_it_beta_or_edge`:** regress the factor-momentum return on FF5+Mom (Newey-West
HAC) — is there alpha net of the factors, or is it just exposure to the factors (esp. Mom)?
**H0 / kill:** alpha t_HAC < 2 net of FF5+Mom → it's factor beta, not a timing edge. Prior LOW (~15%).

## RESULTS (Ken French daily factors, 1964-2026, monthly)
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|
| Factor-mom (long-short, EW 6 factors) | 0.694 | 0.393 | 0.514 | 3.1% | −16.1% |
| Factor-mom (long-only tilt) | 1.001 | 0.672 | 0.768 | 5.6% | −25.0% |
| _ref: Mom factor alone_ | 0.626 | 0.260 | 0.516 | 6.6% | −56.2% |
| _ref: Mkt-RF_ | 0.633 | 0.244 | 0.452 | 5.9% | −55.4% |

### 🎯 THE KILL TEST — `is_it_beta_or_edge`: BETA (decisive)
| variant | alpha (ann) net of FF5+Mom | t_HAC | verdict | corr w/ Mom |
|---|---|---|---|---|
| FM long-short | +0.3% | **0.49** | **BETA (not sig)** | 0.73 |
| FM long-only | +0.3% | **0.49** | **BETA (not sig)** | 0.69 |

Factor momentum has **NO alpha net of the FF5+Mom factors** (t_HAC 0.49, both variants) and is
**69-73% correlated with the Momentum factor.** It IS the momentum factor by another name — exactly
Ehsani-Linnainmaa's point (factor momentum and stock momentum are the same phenomenon; FM "times other
factors," but that timing return is spanned by the Mom factor itself). Net of Mom-ONLY there's a small
residual (long-only t 3.93), but net of the FULL FF5+Mom set it vanishes (t 0.49) — the residual is
just the other static factor premia, not timing alpha.

## VERDICT — FAIL the edge test (factor momentum is Momentum beta, not a new edge)
- **The kill test fired decisively:** no alpha net of FF5+Mom (t_HAC 0.49). Factor momentum is
  exposure to the KNOWN Momentum factor (corr 0.69-0.73), which a retail investor captures by simply
  holding MTUM (the momentum ETF) — a known factor beta that has NOT beaten the robo net of cost
  (momentum crashes, e.g. 2009 −55% factor MaxDD).
- **The FM long-only Sortino (1.001) is misleading** — it's gross, it's long-SHORT-derived factor beta
  (not a cash-Roth-deployable NEW edge), and net of cost + the 50% McLean-Pontiff haircut + the
  beta-verdict there is nothing new to deploy. (Sortino/MaxDD were the pre-registered SCORECARD, not a
  target; the binding gate is the beta-or-edge kill test, which it fails.)
- **Coverage gap CLOSED honestly:** we tested the factor-momentum meta-effect the single-signal sweep
  couldn't see — it's subsumed by the Momentum factor, no new alpha. Confirms the LOW (~15%) prior.

**Net:** factor momentum joins the comprehensive-H0 pile — it's the Momentum factor, a known beta, not
a timing edge, and not a retail-deployable robo-beater. The honest ceiling stands: "trend sleeve + the
robo's own return." (Reusable factor loader + the beta-or-edge harness kept in the script.)
