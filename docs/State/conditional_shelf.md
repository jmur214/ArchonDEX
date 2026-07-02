# Conditional Shelf

**Status:** seeded 2026-06-13 (T-166); backfilled 2026-07-02 (T-258) with the
T-233→T-254 kill-wave (entries 6–10); currency pass 2026-07-02 (T-275) — **CLOSED
#6 (even-week, T-268 step-2 H0) + #11 (off-leg, T-266 family N=2)**, added **#12
(BTC forward-validation, T-272) + #13 (CEF alpha PARKED, T-267)**. Mutates in
place — add an entry at every conditional burial; re-test entries when a gating
switch is validated.

## What this is

The 2026-06-11 decompose directive (`forward_plan.md`) established that a
strategy killed at the **unconditional** gate is not necessarily dead — it
may be a real **conditional** lift whose activation switch we haven't
validated yet. Burying it as a "uniform-lift miss" throws away the measured
conditional profile. This shelf preserves that profile so the regime layer
(Engine E/F) can shop it the moment a switch is validated.

A shelf entry is NOT a live capability and NOT a recommendation to flip a
flag. It is a recorded, audit-cited hypothesis of the form *"strategy X
helped in regime R and hurt elsewhere; if a switch that detects R is
validated, X becomes a re-test candidate under fresh pre-registration."*

## The one validated switch today

Only **`hmm_p_crisis`** (Engine E HMM combined crisis posterior, causal
`predict_proba_for_row`) is a validated regime switch — AUC 0.887 on the
12-yr causal test, fires 5/5 stress events with 27-60d lead
(`docs/Audit/...engine_e_reversal_predictive...`, T-087; verified causal by
T-089). **Caveat: it is currently cloud-dead** (T-118fc) — wired but not
feeding a live consumer on the cloud path. So every shelf entry that gates
on it is **"armed when the switch is live,"** not deployable today. No other
switch (VVIX-z was NO-GO per T-087; dwell-time monitors can't see alpha
decay per T-152) is validated.

## Convention — how an entry is ADDED and RE-TESTED

**ADD (at burial).** When a measurement kills a strategy as a uniform lift
but the per-regime / per-year breakdown shows it helped somewhere and hurt
elsewhere, record one entry here in the same session as the burial. Required
fields: (a) **measured profile** — where it helped / hurt, with the audit
numbers and the audit filename; (b) **named activation condition** — the
regime/account/AUM state under which it's a candidate; (c) **capacity
ceiling** if known; (d) **gating switch** it would key on (today: only
`hmm_p_crisis`, or "none validated yet"). Quote audit numbers; never
paraphrase from memory.

**RE-TEST (when a switch validates).** A shelf entry is re-tested only via a
**fresh pre-registration** (hypothesis + threshold + N_trials consumed,
written before the run, per CLAUDE.md `[NN-MBL]`). The conditional re-test is a NEW
measurement and **consumes honest-N** — the shelf does not grant a free pass.
The re-test question is narrower than the original: not "does X lift
unconditionally" but "does X lift WHEN the validated switch says regime R,"
and the gate is still `ci_low > 0` on the conditional sub-sample (with the
sub-sample's MBL checked — conditioning shrinks N). This is the T-118b
template: the gate never loosens; the QUESTION changes.

**Gates never loosen.** Being on the shelf is not evidence. An entry leaves
the shelf only by (i) clearing a fresh conditional pre-registration → promote,
or (ii) failing it → retire to `docs/Archive/` with the negative result
recorded.

---

## Seed entries

### 1. Regime-conditional vol-target (Engine B) — `hmm_p_crisis`-gated

**Measured profile.** The vol-target overlay is a volatility-cluster
rescue that decays monotonically as the window lengthened and rigor rose:

| Stage | Δ Sharpe | ci_low | Verdict | Source |
|---|---|---|---|---|
| 5-yr Alpaca-only (T-055e) | **+0.549** | **+0.047** | DEFENSIBLE (cleared #6) | `engine_b_vol_target_regime_conditional_t055e_2026_05_23.md` |
| extended substrate, 75-cell (T-055g) | +0.413 | **−0.177** | no arm clears ci_low>0 | `vol_target_multiplier_sensitivity_t055g_2026_05_24.md` |
| 12-yr MBL window (T-055h) | **−0.214** | **−0.688** | CHAPTER CLOSED | `vol_target_12yr_verify_t055h_2026_05_29.md` |

Per-year signature (the conditional core, T-055e/T-055g): **2024 = rescue**
(+1.564 Δ on Alpaca; +0.221 on extended), **2025 = trap** (−0.198 on Alpaca
vs the rolling-60d −0.942 it eliminated; but −0.390 on extended — every arm
loses 2025). The mechanism: it helps when a vol cluster spikes faster than
the OFF book's rolling-60d can react (2024-style); it hurts in choppy
whipsaw where targeting de-risks into the reversal (2025-style).

**Activation condition.** Crisis-onset volatility clustering — a sharp
vol-regime transition, NOT steady chop. `hmm_p_crisis` rising through its
threshold is the candidate trigger; the 2025 trap is precisely the
"elevated-but-not-transitioning" state the switch must exclude.

**Capacity ceiling.** Engine-B overlay on the existing book; no added
capital, no capacity constraint of its own.

**Gating switch.** `hmm_p_crisis` (armed when live). Re-test question: does
the overlay lift `ci_low > 0` *restricted to bars where `hmm_p_crisis` is
above threshold*?

---

### 2. Confidence-gated execution (N≥3) — weak-base-regime-gated

**Measured profile.** A regime-dependent floor-raiser: it raises the floor
when the base book is weak and clips the ceiling when the base is strong.

| Stage | Δ Sharpe | ci_low | Verdict | Source |
|---|---|---|---|---|
| 5-yr Alpaca-only (T-057) | **+0.793** | — | "strongest lift ever" (artifact) | `confidence_gated_execution_2026_05_12.md` |
| extended substrate (T-057b) | **−0.075** | −0.532 iid / −1.154 block | DEFER | `confidence_gated_flag_flip_t057b_2026_05_24.md` |
| 12-yr MBL window (T-053b) | **−0.128** | — (p(Δ>0)=32%) | REFUTED | `multi_year_window_harness_t053b_2026_05_25.md` |

Per-year signature (T-057b, the conditional core): gate **HELPED when OFF
was weak/negative** — 2021 +0.722 (OFF very weak), 2024 +1.432 (OFF
negative); gate **HURT when OFF was strong** — 2022 −1.787, 2023 −1.131 (OFF
very strong both years). The net wash across the cycle is exactly what a
floor-raiser-ceiling-clipper produces when averaged over mixed regimes.

**Activation condition.** Predicted-weak-base regime — the state where the
unconditional book is expected to be weak or negative (2021/2024-type). This
is the inverse-correlated cousin of entry #1's trigger: confidence-gating
pays off in the same low-base-Sharpe states a crisis switch flags.

**Capacity ceiling.** Execution-layer change (N≥3 signal confirmation); no
capital/capacity constraint.

**Gating switch.** `hmm_p_crisis` as a proxy for the weak-base state (armed
when live), OR a future validated predicted-base-Sharpe state. Re-test:
does the gate lift `ci_low > 0` restricted to predicted-weak-base bars?

---

### 3. The base book itself — bull-conditional (the "bull machine missing a switch")

**Measured profile.** The 6-edge base ensemble is the largest conditional
strategy on the shelf — it is itself bull-conditional, and the 16-yr/26-yr
split IS the conditional profile (`deep_substrate_baseline_t092_2026_05_31.md`,
canons since re-anchored deterministic by T-140/T-155):

| Window | Sharpe | ci_low | CAGR | MDD | Contains |
|---|---|---|---|---|---|
| 16-yr 2010-2025 (crisis-free) | **1.018** (det. 1.021) | **+0.560** | +11.00% | −15.4% | no GFC, no dot-com |
| 26-yr 2000-2025 (crisis-inclusive) | **0.246** (det. 0.237) | **−0.119** | +2.64% | −59.3% | + 2008 GFC + 2000-02 dot-com |

The book clears every gate on the crisis-free window and fails every gate
the moment 2008 + the dot-com crash enter. It is a bull machine with no
crisis defense — the −59.3% MDD on 26-yr is the unhedged tail.

**Activation condition.** This is the meta-entry: the book is "always on,"
so the conditional is inverted — it needs a crisis **kill/de-gross switch**
to flatten or reduce in 2008/dot-com-type regimes, converting the 26-yr
−0.119 ci_low toward the 16-yr profile. The named condition is `hmm_p_crisis`
crossing its de-gross threshold.

**Capacity ceiling.** The production book; retail-AUM scale ($5-15K) per the
deployment context.

**Gating switch.** `hmm_p_crisis` de-gross (armed when live). This is the
single most fork-relevant entry: it is the switch the whole engines-first
program has been circling. Re-test: does a `hmm_p_crisis`-driven de-gross
overlay lift 26-yr `ci_low` above 0 / cut the −59.3% MDD without giving back
the 16-yr bull return?

---

### 4. Spot 8-ETF crisis-diversifier sleeve — `hmm_p_crisis`-gated additive sleeve

**Measured profile.** A cross-asset diversified-trend ETF basket
(SPY/TLT/GLD/USO/UUP/EEM/IEF/DBC) that is a crisis-alpha diversifier, NOT a
uniform lift (`managed_futures_trend_t108...`, `dbmf_kmlm_managed_futures_t110_2026_06_05.md`,
`spot_basket_extended_sweep_t115...`). On the 17.9-yr deep window the spot
basket @ 25% cleared the strict gate — **MDD reduction +16.2% (+8.55pp
absolute), calm-Sharpe-Δ +0.197, Sharpe ci_low Δ +0.083, CAGR +0.64pp** (the
Pareto curve never turned through 30%). BUT the integrated path is the open
question: T-120/T-121 found engine-side capital-scale-dependence runs
**negative** (the analytical partition isn't scale-invariant), and the
T-128 + 2026-06-12 relaunch A/B is **INVALID** — substrate nondeterminism
(arm0 16-yr drew the minority attractor;
`spot_sleeve_closeout_relaunch_2026_06_12.md`). So the conditional profile is
**measured analytically (crisis-helps/calm-mild) but not confirmed in the
integrated engine**.

**Activation condition.** Crisis regime — the basket's help concentrates in
2008/2020/2022 flashes (per-window T-108 confirmed 8/8 crisis wins); its
drag is the calm-stretch carry cost. `hmm_p_crisis` is the natural trigger
to scale the sleeve up entering crisis.

**Capacity ceiling.** Spot basket = 8 liquid ETFs, no meaningful retail
capacity limit. The DBMF/KMLM single-product variants have ~5-yr history
(shallower evidence) and ~0.9% ER drag — capacity fine, evidence-depth is
the limit there.

**Gating switch.** `hmm_p_crisis` to scale sleeve allocation (armed when
live). Re-test is double-blocked: needs (i) the determinism dispatch to fix
the cloud substrate so the integrated A/B is valid, THEN (ii) a fresh
conditional pre-registration. Until (i), this entry cannot even be
unconditionally re-measured.

**UPDATE 2026-06-15.** Both blocks resolved, opposite ways. (i) Determinism
FIXED (cov-pin, T-140-fu3) + substrate re-anchored (T-167). (ii) The
INTEGRATED **in-house capital-partitioned** sleeve was re-tested and
**REFUTED** (T-128r: 2-7% MDD cut not +16.2%, worse in 2008 — the analytical
partition is not scale-invariant, T-120/121 mechanism confirmed). BUT the
**separate-account BOUGHT** variant (own capital, no shared constraint stack)
escapes that mechanism and is **VALIDATED as an always-on floor** — see entry
#5. So this entry's IN-HOUSE form is retired-to-Archive-eligible; its
crisis-diversifier thesis lives on in the bought form. (Numbers in entries
#3 here predate the T-167 re-anchor — 26-yr is 0.751/−33% MDD, not
0.246/−59.3%; CURRENT_STATE is the live truth.)

---

### 5. Dynamic MF-sleeve sizing — the AMPLIFIER on the always-on bought sleeve (the one shelf entry whose FLOOR already works)

**Measured profile.** Unlike entries #1-4 (strategies killed at the
*unconditional* gate), this entry's unconditional version WORKS: the always-on
20% bought managed-futures **separate-account** sleeve is a validated
drawdown-defense — T-170 (recent: MDD −7.5%→−5.6%, +25.1%; 2022 DBMF
+32.7%/KMLM +48.8%) + T-171 (deep, net-of-haircut via the free AQR TSMOM
proxy — **director-corrected**: dotcom −19.0%→−11.8%/−13.5% (clears ≥25% both
haircuts); GFC −30.2%→−21.9%/−23.6% (clears the PRIMARY haircut, FAILS the
conservative — **haircut-FRAGILE at 20%**; 30% needed for a robust GFC cut)).
It is a measured DRAWDOWN-defense, NOT a proven Sharpe-lifter (ci_low
indeterminate on thin crisis samples), and an OPTIMISTIC ceiling (real
DBMF/KMLM replication distorts crisis shape vs the pure factor). *(T-171's
original combined-MDD cells were ~2× overstated by a combination bug — caught
by adversarial verification + independent director recompute; fix = T-173.)* The CONDITIONAL hypothesis (the amplifier): dynamically
SIZE the sleeve by a validated crisis signal — heavier when crisis-probability
is high, lighter in clear bull — to recover the bull-market upside the fixed
20% concedes, without losing the protection.

**Activation condition.** A regime detector that clears the OOS-generalization
bar: fires with lead on a crisis TYPE it did NOT train on, AND a dynamic-sized
sleeve beats always-on 20% net-of-cost OUT-of-sample. (Not "fires before
2018/2022" — that is in-sample-era cheap.)

**Capacity ceiling.** Separate-account bought ETF (DBMF/KMLM), ~0.9% ER;
retail-AUM fine.

**Gating switch.** `hmm_p_crisis` is predictive (T-087/089) but does NOT yet
clear the bar (dotcom-blind, T-118r). **T-172 tests whether a deep-history
re-train fixes generalization.** Same family as the de-gross overlay (T-118r
REFUTED) but a **DIFFERENT action — size the BOUGHT sleeve, not de-gross the
equity book** — so the de-gross failure does not pre-doom it, but the
dotcom-blindness must be fixed first. Re-test: does a `hmm_p_crisis`-sized
sleeve beat always-on 20%, OOS, net-of-cost, on a held-out crisis?

---

### 6. FOMC even-week SPY tilt (T-250) — ✅ CLOSED (T-268: step-2 ran → H0)

**Measured profile.** The FOMC-cycle even-week equity premium (Cieslak-Morse-
Vissing-Jorgensen, JF 2019): in-window **7.31 bps/day** vs **1.87** out-of-window
= **+5.44 bps/day** (N=4,318), ~4× — validates the anomaly on our data. But the
deployable long-SPY-in-window / cash@rf-out tilt (1.5 bps/side) does NOT survive
standalone:

| tilt (net cost) | Sortino | ci_low | Sharpe | CAGR | MaxDD | time-in-mkt | Source |
|---|---|---|---|---|---|---|---|
| FOMC even-week | 0.750 | 0.408 | 0.795 | 10.5% | −29.6% | 53% | `calendar_flow_probe_t250_2026_06_26.md` |
| robo bars (T-236) | 60_40 **0.807** / schwab_like **1.008** | | | | | | |

The even-week Sortino ci_low 0.408 sits below both robo point-Sortinos; the
higher Sortino vs Sharpe is a lower-exposure (53% time-in-market) artifact, not
a better edge. **Coverage gap was REAL; neither calendar tilt is a standalone
robo-beater.**

**Activation condition (RESOLVED → CLOSED).** The named step-2 — combine the
even-week tilt with the diversified base — was run under fresh pre-registration
as **T-268 (2026-07-02): H0/NULL.** The tilt does not add to the sleeve. Entry
retires here with the negative result recorded (`evenweek_sleeve_t268_2026_07_02.md`);
do not re-propose without a NEW mechanism (the combination hypothesis is spent).

**Capacity ceiling.** SPY-liquid; no capacity constraint.

**Gating switch.** Deterministic FOMC calendar — n/a now (closed).

---

### 7. Bought MF-ETF convex satellite (DBMF/KMLM) (T-253) — sustained-bear-confirmation

**Measured profile.** Standalone 2019-05+ (KMLM 2020-12+): our free trend sleeve
dominates the bought MF-ETFs on risk-adjusted terms, but the MF convexity is
real and regime-specific:

| satellite | Sortino (ci_low) | MaxDD | CAGR | COVID-2020 | 2022 | Source |
|---|---|---|---|---|---|---|
| our trend sleeve | **1.49 (0.65)** | **−7.5%** | +9.0% | −6% | −6% | `mf_etf_satellite_t253_2026_06_27.md` |
| DBMF | 0.64 (−0.21) | −23.7% | +5.9% | −6% | **+33%** | |
| KMLM | 0.51 (−0.41) | −28.1% | +5.1% | n/a | **+49%** | |

DBMF/KMLM printed **+33% / +49% in the sustained 2022 bear** — the right-tail our
long/flat overlay lacks (our sleeve −6% in 2022) — but DBMF was **−6% in the fast
2020 V-crash** (caught long) and bleeds carry/whipsaw otherwise.

**Activation condition.** A sustained, slow-trending 2022-type bear (confirmed) —
the regime where MF trend-convexity pays and our long/flat overlay is weakest.
NOT the fast V-crash (where it's caught long).

**Capacity ceiling.** Bought ETFs, liquid; standing ~0.85–0.95% expense drag is
the carry cost that makes it lose ex-2022.

**Gating switch.** None validated — needs a sustained-trending-bear detector
distinct from `hmm_p_crisis` (which is tuned to fast crises). Armed as a narrow
tail-hedge overlay when such a switch validates.

---

### 8. Wider-breadth trend sleeve (Wide-9) (T-214) — composition-wants-max-convexity

**Measured profile.** Wide-9 buys real convexity but pays a real Sharpe cost;
"breadth" is NOT "more diversification" (cross-asset corr widens in crises):

| sleeve (EW, 5mo) | Sharpe (ci_low) | MaxDD | skew | Source |
|---|---|---|---|---|
| 3-asset SPY/AGG/GLD | **0.85 (0.45)** | −10.6% | +0.14 | `trend_wider_breadth_validation_t214_2026_06_18.md` |
| Wide-9 | 0.61 (0.23) | **−8.9%** | **+0.34** | |

Wide-9 improves skew (+0.34 vs +0.14) and MaxDD (−8.9% vs −10.6%) at a ~0.24
absolute-Sharpe cost. A trade-off, not a free win.

**Activation condition.** When composition EXPLICITLY prioritizes maximal
convexity/skew over Sharpe (a tail-first mandate) — e.g. as the convex leg of a
barbell. Default = keep the 3-asset core.

**Capacity ceiling.** 9 liquid ETFs; no capacity constraint.

**Gating switch.** None — this is a composition-OBJECTIVE choice (max-skew vs
max-Sharpe), not a regime switch. E selects it when the objective weights tail
over Sharpe.

---

### 9. Cross-asset carry sleeve (T-247) — deep-substrate data unlock

**Measured profile.** On current on-disk data, carry is duration/factor BETA, not
alpha (prime-suspect confirmed):

| config | beta-or-edge (net FF5+Mom+DURATION) | Sharpe (ci_low) | MBL | Source |
|---|---|---|---|---|
| bond carry (AGG curve-slope, 2003–2026, 22.6y) | **BETA** — α +0.34%/yr, t_hac **0.815**, DUR β 0.80, R² 0.80 | 0.144 (−0.181) | FAILS (bar 0.70) | `carry_gauntlet_t247.json` (branch `feature/carry-signal-t247`, pre-reg `d6fdb45`, run `9a5f3b3`) |
| AGG+GLD (2020–2026, exploratory) | **BETA** — α +0.54%/yr, t_hac **0.28** | 0.332 (−0.369) | FAILS (bar 1.35) | |

Curve-slope timing adds no significant alpha over static duration; beat-robo
`passed=False`. The full cross-asset carry (GLD/TLT/IEF/DBC/UUP over a long
window, + equity-yield) was **DATA-BLOCKED**: on-disk diversifier ETFs start
2020-04-09 and no equity-yield series exists.

**Activation condition.** The 21-yr deep-ETF substrate (C/T-256, ingesting from
`data/raw/stooq/` NOW) unlocks the long-window multi-asset test that was blocked.
Re-test the FULL cross-asset carry on the deep substrate under fresh
pre-registration.

**Capacity ceiling.** Liquid asset-class ETFs; no capacity constraint.

**Gating switch.** None — this is a DATA-availability conditional, not a regime
switch. Bar to overturn: alpha_t_hac > 2 net of a bond-duration factor on the
deep substrate. `core/carry_signal.py` is general + fail-closed, ready to re-run.

---

### 10. FRED credit / VIX-term overlay signal (T-233) — confirmation/off-leg role only

**Measured profile.** Killed as a crisis-onset FRONT-RUNNER. Credit (BAA−AAA)
LAGS the always-on price-trend overlay in all four crises, worst on the slow
bears it was meant to help — **dotcom −14% / 156 td late, 2022 −8% / 17 td late,
COVID −19% / 8 td late**. VIX/VIX3M only marginally leads fast V-crises (COVID
2–5 td) and is trigger-happy (the dotcom VIX "lead" is a false de-gross at +9%
SPY during a rally). Mechanism: credit reacts to REALIZED stress, so the
price-trend leads it by construction. Source: T-233 feasibility (branch
`feature/fred-regime-feature-feasibility-t233`, pre-reg `3babb56`; **0 N_trials,
nothing built**; `[[project_t233_fred_regime_feature_2026_06_25]]`). Data caveat:
HY OAS deep history unobtainable → BAA−AAA proxy; conclusion robust to the proxy.

**Activation condition.** NOT as a front-runner (the price-trend already leads
it). Possible CONFIRMATION filter on an existing de-gross (whipsaw reduction) or
an off-leg allocation input — roles where lagging-but-corroborating is
acceptable.

**Capacity ceiling.** Signal-only; no capacity constraint.

**Gating switch.** None validated; any role is subordinate/confirmatory to the
price-trend overlay, never leading.

---

### 11. Momentum off-leg for the trend sleeve (T-259) — ✅ CLOSED (T-266: family N=2)

**Measured profile.** Replacing the trend sleeve's 0%/cash flat leg with a
momentum-selected {BIL, IEF} off-leg (argmax-12mo-momentum if positive, else
T-bills) — run on the T-255 fair harness, 2008-05..2026-04 (17.9y):

| | Sortino (ci_low) | Sharpe | CAGR | MaxDD | $10k→ | Source |
|---|---|---|---|---|---|---|
| cash off-leg (control) | 1.260 (0.621) | 0.993 | 6.2% | −9.3% | 29,231 | `scripts/offleg_ab_t259.py` |
| momentum off-leg | 1.344 (0.750) | 1.026 | 7.0% | −10.4% | **33,542** | (frozen pre-reg `offleg_ab_preregistration_t258_2026_07_02.md`) |

Point economics FAVORABLE (duration beta reclaimed: +$4.3k/$10k, Sortino +0.084,
77% bootstrap win-rate) BUT REFUTED on the frozen gates: paired ΔSortino 95%CI
[−0.085,+0.206] and Δwealth [−0.101,+1.445] both straddle 0 (not significant),
AND the **2022 must-not-degrade HARD gate FAILED** (candidate −4.62% vs control
−4.08%, −0.53pp) — momentum held IEF into part of the bond crash.

**Activation condition (RESOLVED → CLOSED).** The rescue — a fast 63d IEF
duration-trend gate — was run under fresh pre-registration as **T-266 (family
N=2, FINAL): REFUTED.** The diagnosis CLOSED the family with evidence: the off-leg
held IEF **0% of 2022** (12mo momentum already held BIL all year), so **the gate
targeted a non-problem** — the −0.53pp 2022 "degrade" is a **BIL-ETF-vs-DGS3MO
cash BASIS artifact** (BIL lagged the spot rate during the 2022 hikes), NOT the
IEF-crash risk the shelf premise assumed. Off-leg family CLOSED at N=2; the
momentum off-leg is a small, non-significant duration-beta reclaim with no
gate-able tail. (`offleg_rescue_preregistration_t266_2026_07_02.md`.)

**Capacity ceiling.** Liquid BIL/IEF; no capacity constraint.

**Gating switch.** None — family closed (N=2 exhausted). A future off-leg would
need a genuinely NEW mechanism, not another trend gate.

---

### 12. BTC 5% composition leg (T-272) — forward-validation slot (EXPLORATORY, not a burial)

**Measured profile.** The BTC 5% leg is the **FIRST composition addition in project
history to clear BOTH paired CIs** vs the sleeve (a genuine directional + CI signal,
not a null) — but it is held at **EXPLORATORY, NOT DEPLOYED**, per `[NN-MBL]`: the
Roth-clean instrument (IBIT) is only **~2.5 yr old** (launched Jan-2024), so the
backtest leans on BTC-USD, and BTC-USD/IBIT daily corr is **0.82** (24/7-vs-market-
hours timing, not tracking) — real fills differ from the monthly-signal backtest.
The window is too short to clear MBL at honest-N. Source: `btc_arm_verdict_t272_2026_07_02.md`.

**Activation condition.** This is a **forward-validation** entry, not a
regime-conditional burial: promote only when a live/paper forward window on the
actual Roth-clean instrument (IBIT) accumulates enough history to clear MBL AND
reproduces the paired-CI edge out-of-sample. Until then it rides the exploratory
slot alongside the sleeve, tracked forward.

**Capacity ceiling.** 5% sleeve leg; IBIT liquid; no capacity constraint. The
binding limit is DATA HISTORY, not capacity.

**Gating switch.** None (not regime-conditional) — the "switch" is the passage of
forward time under `[NN-MBL]`. Do NOT deploy on the current ~2.5yr history.

---

### 13. CEF discount-capture alpha (T-267) — PARKED (real alpha, no retail data path)

**Measured profile.** **The FIRST statistically-significant alpha in project
history: t_HAC 2.31**, measured on the T-264 CEF-discount substrate whose
survivorship bias runs **CONSERVATIVE** (understates the effect → this is a lower
bound, bias-DEFEATING). Real edge — but **NOT deployable**: there is no retail
point-in-time NAV/discount data path, and the capacity + operational reality
(illiquid CEFs, discount-mean-reversion horizon) don't fit a $5–15K Roth. Source:
`cef_lowerbound_probe_verdict_t267_2026_07_02.md` (+ data audit `cef_data_audit_t264_2026_07_02.md`).

**Activation condition.** A **retail-accessible PIT NAV/discount data feed** AND a
capacity/operational check that a small Roth can actually harvest it. This is a
DATA + operational unlock, not a regime switch — the alpha is real and parked
pending a way to trade it honestly.

**Capacity ceiling.** UNKNOWN but likely tight (CEF discounts live in small,
illiquid names) — a load-bearing open question for any future activation.

**Gating switch.** None — parked on data/operational feasibility, not regime.
The one real alpha we found; keep it visible so a future data path re-opens it.

---

## Not-yet-shelved candidates (flagged, not seeded — need an audit re-read)

- **`value_book_to_market_v1`** — flagged possibly-regime-conditional
  (+$2,081 5-yr cumulative but $3,006 from 2021 alone → net −$925 ex-2021)
  in `2024_attribution_dive_2026_05_12.md` (T-044 candidate). Not seeded:
  it's a single-edge lifecycle question for Engine F, not a switchable
  overlay, and the conditional profile isn't cleanly measured yet.

## Cross-references

- Decompose directive: `docs/State/forward_plan.md` (2026-06-11 block) +
  `[[feedback_decompose_dont_require_allweather_2026_06_11]]`
- Validated switch: T-087 reversal (`hmm_p_crisis` AUC 0.887); cloud-dead
  status per T-118fc.
- Re-test template: T-118b pre-registration discipline.
