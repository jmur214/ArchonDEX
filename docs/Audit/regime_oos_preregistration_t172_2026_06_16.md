# T-172 PRE-REGISTRATION — Regime-detector OOS generalization (leave-one-crisis-out)

**Status:** LOCKED 2026-06-16, committed BEFORE running the leave-one-
crisis-out tests. Per CLAUDE.md `[NN-MBL]` (pre-register hypothesis + threshold
+ N before running). The whole point is OOS generalization — no
in-sample-era victory laps.

## The question (Step 1)

Does a deep-history-trained regime HMM **fire on a crisis TYPE it did
NOT train on** — specifically dotcom (2000-02), which the production
model is blind to (T-118r)? "Fires before crises it trained on" is cheap
and does NOT count.

## Data-feasibility constraints (established BEFORE design — they bound the test)

Verified 2026-06-16 against the re-anchored substrate + fetch sources:

| feature | deepest available | reaches dotcom (2000)? | reaches GFC (2007)? |
|---|---|---|---|
| spy_ret_5d, spy_vol_20d (SPY) | 1993 | ✓ | ✓ |
| vix_level (`^VIX` yfinance / FRED VIXCLS) | **1995** | ✓ | ✓ |
| yield_curve_spread (DGS10−DGS3MO) | 2000 | ✓ (≈) | ✓ |
| credit_spread (BAA10Y−AAA10Y) | 2000 | ✓ (≈) | ✓ |
| bond_ret (TLT/IEF ETF) | **2002** | ✗ | ✓ |
| bond_ret (DGS10-yield proxy) | 2000 | ✓ | ✓ |
| dollar_ret_63d (DTWEXBGS) | 2006 | ✗ | ✗ |
| **VIX term structure** (VIX3M/VIX9D) | **2007 / 2011** | ✗ STRUCTURAL | ✗ STRUCTURAL |

**Two consequences, pre-registered as part of the finding:**
1. The production HMM's strongest crisis features (the VIX
   term-structure slope/backwardation set) **did not exist in 2000**
   (VIX3M from 2007, VIX9D from 2011). A model using them **cannot**
   generalize to dotcom — not for distribution reasons but because the
   inputs didn't exist. This is a STRUCTURAL limit, separate from the
   training-distribution question.
2. The deep-history OOS test therefore uses a **reduced base feature
   set** (no term structure, no dollar): `spy_ret_5d, spy_vol_20d,
   bond_ret (DGS10 proxy), vix_level, yield_curve_spread,
   credit_spread`. This is the deepest HONEST common feature set across
   dotcom→present.

## Pre-registered design

**Model:** a Gaussian HMM (3 states), the same class as production
(`hmm_classifier`), trained on the reduced deep panel. The "crisis"
state is identified mechanically post-fit as the state with the
**highest mean `spy_vol_20d`** (no discretion). `p_crisis(t)` = the
smoothed posterior of that state, computed causally (growing-prefix /
forward filter — NOT `predict_proba` over the full sequence, per the
T-089 lookahead lesson).

**Leave-one-crisis-out (LOCO):** for each held-out crisis C, train the
HMM on ALL deep history EXCLUDING C's window (± a 90-calendar-day
buffer each side), then evaluate `p_crisis` ON the held-out window.
Crises (peak→trough, the T-118b/v3 anchors):
- **dotcom** 2000-03 → 2002-10 (the key untrained TYPE)
- **GFC** 2007-10 → 2009-03
- **COVID** 2020-02 → 2020-03
- **2022** 2022-01 → 2022-10

**Firing criterion (pre-set):** the model FIRES on a held-out crisis iff
`p_crisis` crosses **≥ 0.50** and stays there ≥ **3 trading days**, with
the first crossing occurring **on or before the crisis trough** AND with
positive **lead** = trading days from the first sustained crossing to
the trough (lead > 0 required; a crossing only AFTER the trough does NOT
count — that's coincident, not predictive).

**False-alarm budget (pre-set):** on all NON-crisis trading days in the
held-out evaluation (the calm stretches inside the held-out window's
surrounding year that are not within any crisis), the sustained-crossing
false-alarm rate must be **≤ 1 per year**. A model that fires constantly
"detects" every crisis trivially — the FA budget is the discriminator.

**N / multiplicity:** 4 LOCO folds (one per crisis) + 1 full-fit
reference = 5 HMM fits. Seed-pinned (`random_state=0`, 10 inits). This
pre-registration consumes these 5; any reduced/expanded feature variant
is a NEW pre-registration.

## Pass / fail (locked)

**PASS (detector generalizes — gates Step 2):** the **dotcom** fold
fires (sustained ≥0.50, lead > 0 to the 2002-10 trough) AND its
false-alarm rate ≤ 1/yr. Dotcom is the load-bearing fold (the untrained
TYPE the production model is blind to). GFC/COVID/2022 folds are
reported for profile but dotcom is the bar.

**FAIL (blindness is structural / data-bound):** the dotcom fold does
NOT fire with lead, OR only fires by blowing the false-alarm budget.
Then crash-TIMING is not viable for this system on the available data,
**always-on 20% (T-170/171) is the ceiling, and Step 2 (the
dynamic-sizing amplifier) does NOT start.**

## Integrity

No post-hoc crisis-window edits, no threshold edits after this commit.
The crisis state is identified mechanically (max mean vol). `p_crisis`
is causal (growing-prefix). If the reduced feature set materially
changes the conclusion vs production's feature set, that is itself a
reported finding (the term-structure features carry the load → dotcom
is structurally out of reach).
