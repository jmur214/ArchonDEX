---
task_id: T-2026-06-26-249
title: Small-cap momentum gauntlet — survivorship-free universe attempt + honest cost-kill test
date: 2026-06-26
author: Agent D (measurement lane)
type: pre-registered build + gauntlet (the C2 return-frontier bet; prior LOW ~10%)
status: PRE-REGISTERED (results below the line)
---

# T-249 — small-cap momentum gauntlet (does it survive honest small-cap cost?)

## PRE-REGISTRATION (written BEFORE the verdict — `[NN-MBL]`)

**Context:** the C2 return-frontier bet (moonshot scope T-240): a DIFFERENT, less-efficient universe
(small-cap) where the large-cap H0 may not transfer — small-caps have fatter right tails. The
literature's own verdict: **retail COST kills small-cap momentum.** Prior LOW (~10%). The load-bearing
gate is the HONEST small-cap cost model, not the gross lift.

**⚠️ SURVIVORSHIP INTEGRITY WALL (found in recon — `[NN-FAIL-CLOSED]`/`[NN-CENSUS]`):** the only free
broad universe (Stooq US, 8,516 names) is **100% survivor-biased** — 0/399 sampled names are delisted
(all end 2026). There is no free comprehensive small-cap delisting list (the S&P PIT works via S&P
membership + the T-219 delisted-cohort backfill; no small-cap equivalent exists free → would need
CRSP/Norgate, paid). **A truly survivorship-free small-cap universe is NOT achievable from free data.**

**The design that turns this into a STRONGER test (upper-bound a fortiori):** run the gauntlet on the
survivor-biased universe, which **inflates the gross momentum lift** (survivors are exactly the names
that didn't blow up). If small-cap momentum DIES at honest small-cap cost even on this FAVORABLE
(upward-biased) universe → the FAIL is robust, because the real survivorship-free universe would be
strictly worse. (If it SURVIVES, the survivorship bias means we cannot certify it — it would need
paid data to confirm.)

**Hypothesis H1:** small-cap 12-1 momentum (long top-decile by 12-month-return-skip-1, monthly EW
rebalance) beats BOTH robos on Sortino/tail **net of honest small-cap cost**, and is not just SMB+UMD
beta.

**H0 / THE PRE-REGISTERED KILL CONDITION:** the gross lift DIES at honest small-cap cost (net Sortino
ci_low ≤ the robo's, or net CAGR ≤ the robo's) → **FAIL — cost is the assassin.** AND/OR the survivor
bias means it cannot be certified survivorship-free.

**Honest small-cap cost model (the load-bearing gate):** per-rebalance cost = Σ|Δw| × (half-spread +
impact). Half-spread by ADV tier grounded in T-210 / retail effective-spread evidence: small-cap 35
bps, micro-cap 75 bps (vs large-cap 2-3 bps). Impact = a convex function of trade-size/ADV (tiny at
$5-15K AUM, so spread dominates). Report gross AND net at small AND micro cost.

**Thresholds:** Sortino + ci_low (block-bootstrap, `[NN-SHARPE-CI]`); net-of-cost vs both robos;
`is_it_beta_or_edge` net of SMB+UMD (is the lift just the size + momentum factor premium, capturable
via a cheap ETF?). MBL at honest-N (this is a fresh universe; N_trials = 1 pre-registered config — the
canonical 12-1 monthly decile, NO param sweep).

**Decision rule:** survives honest small-cap cost vs both robos AND not pure SMB/UMD beta → a real
(but un-certifiable-from-free-data) lead, escalate the paid-data question. Dies at honest cost → FAIL,
state plainly that cost is the assassin (confirming the literature + the LOW prior).

---
## RESULTS

**Universe (best free effort):** 6,733 Stooq US names loaded → **3,628 small-cap** (3mo dollar-ADV
$1M-$200M; 2,388 micro <$20M). **100% SURVIVOR-BIASED (0 delisted — confirmed in recon).** 12-1
momentum (skip-1), monthly EW top-decile (~360 names), 2006-2025.

**Honest small-cap cost model (the load-bearing deliverable — sound + reusable):** turnover **662%/yr**
(Σ|Δw| 0.55/mo); cost = Σ|Δw| × half-spread → **2.3%/yr at all-small (35bps), 3.8%/yr tier-accurate
(35bps small / 75bps micro).**

| variant | Sortino | ci_low | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|
| **GROSS (no cost)** | 4.907 | 1.523 | **3.210** | 15.1% | −59.7% |
| NET @ 35bps (small) | 4.185 | 0.903 | 2.761 | 12.5% | −60.9% |
| NET @ tier (35/75bps) | 3.709 | 0.491 | 2.467 | 10.8% | −61.7% |
| (robo bars, T-236) | — | — | — | 60_40 So 0.807 / schwab 1.008 | — |

### Verdict — FAIL the gauntlet, but the assassin is SURVIVORSHIP (not cost), and it's UNCORRECTABLE on free data
1. **The gross is FAKE.** Sortino 4.9 / **Sharpe 3.2** for a diversified momentum decile is not real —
   it's the survivorship bias the pre-registration flagged. The universe is 100% survivors (the
   small-caps that 10×'d and DIDN'T delist); momentum rides them up and **never eats the delisting
   craters** that a real small-cap momentum book is full of. This is the uninterpretable UPPER BOUND.
2. **Honest cost is real but is NOT the binding assassin here** — 3.8%/yr only knocks the fake gross
   15.1%→10.8% CAGR (Sharpe 3.2→2.5). Survivorship inflation (≈ +7-10%/yr) DWARFS the cost (−3.8%/yr).
   So the pre-registered "dies at honest cost" test is MOOT on a fake gross.
3. **The real binding problem = SURVIVORSHIP, uncorrectable on free data.** Stooq has 0 delisted names;
   there is no free small-cap delisting list; a survivorship-free small-cap universe needs PAID data
   (CRSP/Norgate). I will NOT fabricate one (`[NN-FAIL-CLOSED]`).
4. **Under a literature-grounded survivorship correction, cost IS the secondary assassin.** The
   survivorship-free small-cap momentum gross premium in the literature is ~5-8%/yr (vs my survivor-
   biased 15%); subtract the honest **3.8%/yr** cost → **~1-4%/yr net, BELOW the robo's ~6%** → FAIL.
   And `is_it_beta_or_edge`: the lift is dominated by survivorship + SMB + UMD factor beta (capturable
   via a cheap small-cap-momentum ETF), not a certifiable edge.

**Net:** the C2 small-cap avenue FAILS the honest gauntlet — not because the cost-kill fired on a clean
number (it couldn't: the free universe is irreducibly survivor-biased), but because (a) a
survivorship-free evaluation is impossible from free data, and (b) the honest cost (3.8%/yr) is
material against any realistic survivorship-free gross. Confirms the LOW (~10%) prior and the
literature's verdict. **Do NOT pursue without paid survivorship-free data — and even then the honest
cost makes the prior low.** The cost model + the survivor-biased universe builder are kept (reusable
if paid data ever lands).

