---
task_id: T-2026-08-15-342
title: VOL-TERM-STRUCTURE conditioning of family #3 — pre-registration DRAFT (C2 from the external review)
date: 2026-08-15
author: Agent D (fair-harness lane)
type: PRE-REGISTRATION DRAFT — draft → director freeze → run. **NOTHING HAS RUN.** N_trials += 2.
status: DRAFT — NOT RUN, NOT FROZEN. Awaiting the director's freeze.
---

# T-342 (DRAFT) — does the volatility term structure improve family #3's entry/exit timing?

**The question (queued 2026-07-28, approved then):** does conditioning on the vol term structure improve the
pre-registered "lever into the crash" rule's **entry/exit timing** versus a drawdown-threshold-only trigger?

**Scope guard, stated first.** This conditions **family #3** — the conditional-exposure member pre-stated
2026-07-27 (`docs/Sources/prereg_adaptation_rule_t314.md`), *"RAISE exposure (1.0 → 1.25-1.5×) only when the
market sits ≥X% below its prior high, gliding back on recovery"* — the rule **only a genuinely won't-sell
holder can execute**. It does **not** re-litigate T-220/T-221's regime-gating closures: those closed
*regime-gating a self-timing signal*; this conditions a *drawdown trigger* that does not time itself.
**Family #3 remains forward-only per the contamination ruling regardless of this result** — the conditioner
tunes a rule that only ever fires forward.

---

## ⚠️ 0. THE PRE-RUN MEASUREMENT THAT SHOULD GOVERN HOW THIS RESULT IS READ

Computed **before** the run, from episode **counts and durations only** — never from returns conditional on
those episodes, so nothing here reveals the outcome. An episode = first close ≤ X below the running peak,
ending when that peak is regained.

| window | X=10% | X=15% | **X=20%** | X=25% | X=30% |
|---|---|---|---|---|---|
| **primary 2006-07-17 → 2026 (19.7yr)** | 7 | 5 | **3** | 2 | 2 |
| SKEW-only 1990 → 2006-07 (16.5yr) | 7 | 3 | 2 | 1 | 1 |

**At the primary threshold the rule fires on THREE episodes: 2008-07-14 (GFC), 2020-03-12 (COVID),
2022-06-13.** Not three hundred observations — **three events**, and they are radically heterogeneous in
character (a slow grinding bear; the fastest crash on record with an immediate V-recovery; a slow grind with
no single panic day). A vol-term-structure conditioner behaves completely differently across those three.

**Consequence, pre-declared and binding:**

> **This test is REFUTATION-CAPABLE ONLY. Its positive branch is pre-declared NON-CONFIRMATORY.**
> A null at n=3 legitimately closes the door (§5). A "win" at n=3 clears no honest bar, authorizes nothing,
> and may **not** be quoted as evidence for the conditioner — it only fails to close the door. The asymmetry
> is real and is the reason the test is still worth running at $0.

This is written **now** so that a favorable number cannot later be read as confirmation. It is the same
disease I caught in T-312, where a ~99yr window's "SIGNIFICANT" CI turned out to be driven entirely by
1929-32; **here the analogous risk is COVID-2020**, the one episode with an extreme, short-lived inversion and
an immediate recovery. Hence §4's mandatory leave-one-episode-out.

## 1. THE CONDITIONING SIGNAL — exact construction, no sweep

All series verified on disk in canon, $0, no vendor: `data/macro/VIX.parquet` (2002-01-02 → 2026-07-01, 6,164
obs, no nulls), `VIX3M.parquet` (**2006-07-17** → 2026-06-26, 5,018 obs, no nulls), `SKEW.parquet`
(1990-01-02 → 2026-07-01, 9,175 obs, no nulls). VIX∩VIX3M = 5,018 days, complete. Verified complete inside
all three episodes (GFC 1,033/1,068 bdays; COVID 111/114; 2022 403/420 — the residuals are market holidays).

```
ts(t)        = VIX(t) / VIX3M(t)                  # term-structure ratio
depth(t)     = ts(t) - 1                          # "inversion depth"; INVERTED when depth > 0
skew_pct(t)  = rank of SKEW(t) among all SKEW observations STRICTLY BEFORE t
                 (expanding window, min 500 prior obs, else UNAVAILABLE)

C(t)  =  1  if  [ ts(t) >= 1.0 ]  OR  [ skew_pct(t) >= 0.80 ]   else 0
```

**Every number here is frozen and justified without reference to our data:**
- **`ts >= 1.0` is definitional**, not fitted — 1.0 *is* the inversion point. This is the primary arm's only
  threshold and it has zero degrees of freedom.
- **`skew_pct >= 0.80`** is a stated convention for "elevated," frozen a priori. It is a DoF I am **freezing
  rather than sweeping**; changing it after seeing any result is forbidden by this pre-registration.
- **`OR`, not `AND`** — the mechanism is *"acute stress is being priced"* and either channel evidences it.
  No other combination will be tried.
- **`skew_pct` is a TRAILING expanding-window percentile, never a full-sample one.** A full-sample percentile
  ranks a 2008 observation against 2026's — look-ahead. (Same rule as T-341's flag.)
- **Inversion depth enters only through its SIGN and a fixed 5-day smoother** (§2 exit). A magnitude-scaled
  exposure ladder would introduce a free parameter and is **forbidden by this pre-registration.**

## 2. THE RULE AND THE PAIRED COMPARISON — and the confound that would otherwise fake a win

Family #3 as pre-stated leaves **X and the exposure ladder unspecified**. Both are frozen here, on non-data
grounds, before any run:

- **X = 20%** — the pre-existing *public convention* for a bear market. Chosen because it is a convention that
  exists outside our data, which is the cleanest available defence against fitting.
- **Ladder = 1.0× → 1.25× at −20%, → 1.50× at −40%** — inside family #3's own pre-stated "1.25-1.5×" band, so
  it adds no new degree of freedom. Cost basis is T-315's identity (break-even μₑ: 1.25× → 7.04%,
  1.5× → 5.58%); the mechanism's claim is precisely that post-drawdown μₑ exceeds those levels.
- **Financing/ER/slippage inherit the measured T-294/T-298/T-315 costs unchanged.** A levered path is a
  *different* strategy, not a scaled one.

**⭐ The chatter confound — the reason a naive paired test would be uninterpretable.** Counting *contiguous*
threshold-crossings rather than episodes gives a **non-monotone** count (37 "episodes" at X=15% vs 35 at
X=10%): the bare drawdown trigger **re-triggers on every re-crossing**. That is turnover, and turnover at the
measured gate-flip cost is exactly what killed the entire offense arc (T-294 execution-bound, T-297/298).

> **A conditioner that merely damps chatter will LOOK like improved timing when it is only acting as a
> low-pass filter.** So the WITHOUT arm gets the *same* hysteresis as the WITH arm:

```
ENTRY : step up on the first close <= -X below the running peak      [both arms]
        WITH arm additionally requires C(t) == 1                     [the ONLY difference]
EXIT  : glide 1 step down when drawdown recovers above -X/2          [both arms — matched hysteresis]
        WITH arm additionally exits a step when the 5-day mean of depth(t) < 0 (normalization)
```

**The only difference between arms is the vol-term-structure information.** Both carry identical hysteresis,
identical ladder, identical costs, identical rebalancing. Turnover is reported per arm so that any timing
difference can be read net of the trading it caused.

**Metrics, per `[NN-SHARPE-CI]`:** primary = **Sortino**; co-primary = **time-underwater**. Both with
**block-bootstrap** CIs (Künsch block bootstrap, 1000 iterations, auto block length per Politis-White — iid
resampling is not acceptable on serially-correlated returns). **Paired** on identical dates. **All gating
reads `ci_low`, never the point estimate.**

**Win condition, frozen:** Δ Sortino `ci_low` **> 0** *and* Δ time-underwater `ci_low` **< 0** *and* the
leave-one-episode-out check (§4) passes. **Anything less is a null.**

**MBL Gate-0 (`[NN-MBL]`).** `run_registry` shows 125 rows, effective N ≈ 260+. With this pre-registration's
+2, `T ≥ 2·ln(N)/SR²` on the 19.7yr primary window requires **SR ≥ 0.70 (N=127) to 0.75 (N=260)**; the 16.5yr
SKEW-only leg requires **0.77 to 0.82**. Recorded now so the bar cannot move afterwards.

## 3. WINDOW HONESTY

- **Primary: 2006-07-17 → present (19.7yr).** Bound by VIX3M's genuine start, **not** by choice. Note what
  this excludes: the window opens *after* the 2000-02 dot-com bear and *before* the GFC. VIXCLS (2000+)
  cannot rescue this — the term structure needs **both** legs, so VIX3M binds regardless, and VIX (not
  VIXCLS) is pinned for the whole run to prevent a silent source switch.
- **Secondary, pre-registered, NOT a robustness afterthought: X = 10%** (7 episodes) — reported **jointly**
  with X=20%, never cherry-picked. This is the second N_trial. Its purpose is power; its cost is that a 10%
  correction is not the "crash" the mechanism describes, so it tests a *weaker* version of the hypothesis.
- **SKEW-only 1990 → 2006-07 (16.5yr, 2 episodes) — the poor-man's OOS, with a precise caveat.** VIX3M does
  not exist before 2006-07-17, so this leg runs on the SKEW channel alone. **It is therefore an
  out-of-sample test of a DEGRADED signal, not of the signal.** It can weakly corroborate; it cannot confirm,
  and a disagreement between legs is not evidence the primary is right.
- **Data staleness, stated:** VIX ends 2026-07-01 and VIX3M 2026-06-26 — ~7 weeks stale at drafting. Not a
  blocker for a historical measurement, but the run must report each series' true last date, and a refresh
  gap must surface explicitly rather than silently truncating the window (`[NN-FAIL-CLOSED]`).

## 4. MANDATORY REPORTED OUTPUTS (pre-committed, not optional robustness)

1. **⭐ LEAVE-ONE-EPISODE-OUT.** Re-run dropping each of the 3 primary episodes in turn, and report all three
   restatements **in the headline, not an appendix.** If the verdict flips on dropping any single episode —
   **especially COVID-2020** — the result is reported as a **single-episode artifact**, exactly as T-312 was.
2. **Per-episode decomposition** — Δ Sortino and Δ time-underwater for each of GFC / COVID / 2022 separately,
   because averaging three heterogeneous events hides which one carries the number.
3. **Turnover per arm** (exposure-units/yr) and the implied cost, so a timing "win" is legible net of trading.
4. **The 1930s adversary, named in family #3's own draft:** levering at −30% and riding to −85% is what a
   drawdown trigger does *wrong*. It is out of window here (VIX3M starts 2006), so this run **cannot** speak
   to it — stated explicitly rather than quietly omitted.
5. **A census block** per `[NN-CENSUS]`: series last-dates, obs counts, episodes triggered per arm, days
   in-trigger, and `UNAVAILABLE` counts for `skew_pct`'s 500-obs warm-up. Zero episodes triggered = a
   **non-canonical run**, not a null.

## 5. THE KILL STATEMENT — why either outcome is a receipt

> **A null CLOSES the "should we buy options data?" question at $0 instead of $500.**

The standing open question is whether richer options-surface data (term structure, skew surface, dealer
positioning) would improve the conditional-exposure family. **We already hold the two cheapest, most-cited
summary statistics of exactly that surface.** If VIX/VIX3M inversion plus the SKEW percentile cannot improve
family #3's entry/exit timing on the episodes we have, the prior that a *paid* surface would is materially
lowered, and the $500 stays unspent. That is a real receipt.

**And the honest converse:** because §0 pre-declares the positive branch **non-confirmatory**, a favorable
number does **not** buy the data either — it leaves the door open at a cost of $0 and defers the question to
a forward record. **There is no branch of this experiment on which we spend money or deploy capital.** That
is what makes it worth running at n=3.

**What this experiment can NEVER do:** authorize family #3 to run, deploy, or size anything. #3 is
forward-only by the contamination ruling. This measurement can only decide **whether the forward rule's
frozen spec should include the conditioner** — and, on the null branch, close a purchasing question.

## 6. N_TRIALS AND PROVENANCE

**N_trials += 2** (primary X=20%; secondary X=10%), reported jointly as one family. Family-N accounting per
family #3's own draft: #1/#2/#3 and their conditioners test the same family on the same substrate; each is +1
and the DSR bar rises for all of them.

**Provenance:** the conditioning question was queued and approved **2026-07-28**, before any family-#3 result
existed (none exists — #3 has never run). X, the ladder, the conditioner construction, the win condition, the
leave-one-out requirement, and the non-confirmatory declaration are **all frozen in this document before the
run**. The only post-freeze act is running it and reporting the number.

---
**DRAFT — NOT RUN, NOT FROZEN.** Nothing executes before the director's freeze. Any change after the freeze
line is a new pre-registration.
