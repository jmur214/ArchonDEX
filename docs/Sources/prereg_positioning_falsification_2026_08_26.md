# Pre-registration DRAFT — the positioning-data falsification

**Status: DRAFT — awaiting director FREEZE. NOT RUN. 0 N_trials consumed.**
**Date:** 2026-08-26 · **Agent:** B · Branch `feature/positioning-falsification-prereg`
**Scope:** the four positioning feeds accruing with zero code consumers — FINRA RegSHO daily
short volume, FINRA short interest, SEC failures-to-deliver, FINRA margin debt.

## 0. The headline, before any hypothesis

**The branch is NOT TESTABLE on the current accrual**, and the reason does not depend on any
contested methodological reading. "~1M rows" is **cross-sectional width, not time depth**:

| feed | rows | **independent time periods** | span |
|---|--:|--:|---|
| RegSHO short volume | 604,388 | **50 trading days** | 2026-06-01 → 2026-08-26 |
| Short interest | 111,001 | **5 settlement snapshots** | 2026-05-15 → 2026-07-31 |
| SEC FTD | 312,879 | **63 settlement days** | 2026-05-01 → 2026-07-31 |
| Margin debt | 16 | 16 months | — |

A forward-return test is a **time-series** test: cross-sectional returns share a market factor,
so 24,063 symbols on one date are ≈ one observation, not 24,063. A Fama-MacBeth run on the
short-interest panel today has **5 periods → 4 degrees of freedom**. No threshold set on that
is meaningful, in either direction. **Running it now would consume a trial to learn nothing.**

## 1. The cost side — measured, because the dispatch framed this as "a branch we pay to feed"

**Total on-disk cost: 18.3 MB** (RegSHO 11.0 / SI 3.7 / FTD 3.6 / margin+NAAIM ~0).
The feeds are free, the collectors already run, and the marginal cost of continuing is storage
plus gate attention. **Recommendation: do NOT close this branch on cost grounds** — the cost
does not justify the loss of an accruing, un-repeatable time series. (Positioning history
cannot be back-filled later: FINRA/SEC publish it forward, and vendors charge for depth.)

## 2. What IS worth doing now — verify the channel, not the pipe

Per `feedback_verify_the_input_channel_not_just_the_pipe`: the failure mode that would waste
years is accruing a feed that turns out to be unusable *after* the accrual gate opens. So the
cheap, zero-N action is to prove the channel is real and joins. **Done, and it passes:**

- `currentShortPositionQuantity` — **100% non-null**, median 39,841, **0% zeros**.
- `daysToCoverQuantity` — **100% non-null**, already computed by FINRA (no derivation needed).
- `settlementDate` present (prefer it over `accountingYearMonthNumber`).
- **Universe join: 39/39** `tr_reconciled` tickers are present in the short-interest panel.

**⚠ One data trap to guard at test time:** `averageDailyVolumeQuantity` is **13.4% zeros**.
Days-to-cover divides by it. Any derived ratio must use the `[NN-FP-GUARDS]` pattern
(`if adv is None or adv < 1e-12 or not np.isfinite(adv): return None`) and count the excluded
names explicitly — never silently drop them into a plausible-looking cross-section.

## 3. THE PRE-REGISTERED HYPOTHESIS (to run when the accrual gate opens — not before)

**Prior: LOW**, per the dispatch, and consistent with the family's record — insider-directional
is already refuted, and the McLean-Pontiff decay prior applies to everything here.

Test the **single strongest documented claim** in this family, not a search over four feeds
(a four-feed sweep is a fishing expedition that would consume N per arm):

> **H1 — Cross-sectional short interest predicts forward returns NEGATIVELY.**
> Boehmer-Huszár-Jones (2010); Rapach-Ringgenberg-Zhou (2016). Rank symbols each settlement
> date by short-interest ratio (shares short / shares outstanding, ADV-guarded); form a
> long-low/short-high decile spread; measure forward returns to the next settlement date.
> **H0: the spread's mean forward return is zero.**

**Endpoint and threshold (CI-aware, `[NN-SHARPE-CI]`):** block-bootstrap (21d blocks, 1000
iter, seed 0) CI on the mean spread return. **REFUTED if `ci_high < 0` fails to exclude 0 in
the documented direction** — i.e. the pre-committed refutation is `ci` straddling zero after
the gate is met. **No positive deployment claim may be made from this test** (see §4).
**N_trials += 1 on the run**, one family, no arm sweep.

**Long-only constraint, stated up front:** our wrapper cannot short. Even a confirmed result
is only actionable as an *avoidance/exclusion* screen on the long leg — and Daniel-Moskowitz's
lesson (the crash lives in the short leg) means the long-only half is the weaker half. This
caps the realistic value of the whole branch and is a reason the prior is LOW.

## 4. The accrual gate, and an MBL question the director must rule on

**Gate to run §3: ≥ 60 short-interest settlement snapshots (~2.5 years, i.e. ~2029-Q1).**
Below that the Fama-MacBeth t has too few periods to refute anything.

**⚠ MBL reading — I am not choosing this silently.** `[NN-MBL]` requires
`T_years ≥ 2·ln(N_eff)/SR²`. With **N_eff = 231**, that is **T ≥ 10.885 / SR²**:

| plausible SR | required T |
|---|---|
| 1.5 | 4.8 yr |
| 1.0 | **10.9 yr** |
| 0.8 | **17.0 yr** |
| 0.5 | 43.5 yr |

The reading matters and the two answers differ by a decade:
- **(A) substrate = the positioning panel** — a fresh predictor never searched → N ≈ 1, MBL
  trivially cleared; only the power gate in §4 binds.
- **(B) substrate = US equity returns** — the *outcome* variable we have searched 231 times →
  **11-17 years** before any deployable claim can clear DSR.

**I recommend (B) for any DEPLOYMENT claim and (A) for an ASSOCIATION claim**, and have written
§3's endpoint accordingly: the test as pre-registered is **refutation-only** — it can close the
branch, it cannot open a deployment. That asymmetry matches the dispatch's own framing ("either
finds something or closes a branch we pay to feed") and is robust to whichever way you rule.

## 5. What this draft deliberately does NOT do
- Does not run anything (freeze first).
- Does not sweep the four feeds (one hypothesis, one trial).
- Does not recommend closing the branch — 18.3 MB does not buy back an un-backfillable series.
- Does not scope a vendor purchase for depth.

## 6. Decision requested
1. **Freeze §3 as written?** (or amend the hypothesis/threshold before it is frozen)
2. **Rule on the MBL reading** in §4.
3. **Confirm the branch keeps accruing** to the 2029-Q1 gate, with the feeds' exemption/alarm
   status unchanged in the meantime.
