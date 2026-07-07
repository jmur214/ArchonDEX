# T-291 Deliverable 2 — even_week × is_fomc_week interaction: PRE-REGISTRATION (frozen BEFORE the run)

**Date:** 2026-07-07 · **Agent:** C · Branch `feature/event-state-t291` · **N_trials += 1**
Committed BEFORE running the test (the director verifies the freeze predates the results commit). Pre-registered per `[NN-MBL]` / `[NN-SHARPE-CI]`.

## The mechanism-locating question
The JF-2019 even-FOMC-cycle-week equity premium: is it **CONCENTRATED in the FOMC decision week (cycle week 0)**, or spread across all even weeks (0, 2, 4, 6)? T-268 already closed `even-week × sleeve` as H0 (a deployable even-week *timing* tilt does not beat buy-hold). This is a DIFFERENT, mechanism-locating question — **family-N = 2** (same family, stated honestly). Locating the mechanism (if any) is what would justify an event-day-aware SIZING modifier, not a timing signal.

## Definitions (frozen)
- `even_week(d)` — weeks since the most recent FOMC decision is even (0,2,4,6) [T-250 definition].
- `is_fomc_week(d)` — `d` falls in the same ISO calendar week as an FOMC decision (= cycle week 0). Coded to B/T-290's `macro_calendar.is_fomc_week` contract; the T-250 fixture is the temporary source until B merges.
- Groups on SPY daily returns: **G1** = even & fomc-week (week 0); **G2** = even & ¬fomc-week (weeks 2,4,6); **G3** = odd weeks (1,3,5,7 — baseline).

## Panel & windows (frozen)
- SPY daily returns, the T-250 panel. **Primary window: full 1994-2026** (the FOMC fixture range). **Secondary: post-2015** (recency / post-publication decay read — JF 2019 published mid-decade).

## Metric & gate (frozen)
- Per group: mean daily return (bps/day) + n.
- **Test statistic:** the difference **G1 − G2** (is the even-week premium bigger in the FOMC week than in the other even weeks?), with a **block-bootstrap 95% CI** (block length 5 trading days, 1000 iterations, seed 0).
- **CONFIRMED** iff, on the full-sample primary window, the (G1 − G2) 95% CI **excludes 0 AND G1 mean > G2 mean** — i.e. the premium is significantly concentrated in the FOMC week. Otherwise **H0 / not-concentrated** (the even-week effect, if present, is not FOMC-week-specific → no mechanism located).
- Also report G1 vs G3 and G2 vs G3 for context, and the post-2015 half (decay).

## Role if CONFIRMED (pre-stated)
An event-day-aware **SIZING MODIFIER** on the sleeve (a bounded 0.5–1.5× tilt in the confirmed FOMC window) — **explicitly NOT a timing signal / gate** (T-233 role constraint). If H0, the event axis remains built + default-OFF for the `event_window` context only, with no sizing role earned.

## Honest prior
LOW-MEDIUM. The even-week effect is a documented but small (~few bps/day) and decay-prone flow effect; concentration in the FOMC week is plausible (the decision is the information event) but noisy at daily frequency. N_trials += 1; family-N = 2.
