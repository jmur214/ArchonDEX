---
task_id: T-2026-08-31-349
title: Buy/hold-spread retest of the gated-offense family — the last constructible rung
date: 2026-08-31
author: Agent C (composition lane)
type: PRE-REGISTRATION DRAFT (draft → director freeze → run; N_trials += 1)
status: DRAFT — NOT RUN. Awaiting freeze. Contains a PREMISE CORRECTION the director should rule on first.
---

# T-349 (DRAFT) — buy/hold spread on the gated-offense gate

## 0. Premise correction — read before the design

The dispatch asks whether Novy-Marx–Velikov buy/hold-spread construction (a stricter
threshold to ENTER than to MAINTAIN) can revive the T-298 variant. **T-298 already IS a
buy/hold spread**, and in the only orientation this strategy permits:

```
T-298 (frozen, ran):  increase only when e_target − e_held > B      (strict to ENTER)
                      decrease executes immediately, always          (no maintain threshold)
```

So "apply a buy/hold spread to T-298" is not a new construction. The real question is
narrower and answerable: **which band pairs are constructible at all, and which of them
remain untested?**

### The family is finite, and enumerable

The gate signal is quantized. Ensemble fraction `frac ∈ {0, ⅓, ⅔, 1}` (three speeds), and
`e_target = 2·frac ∈ {0, ⅔, 4/3, 2}`. A buy/hold spread has two thresholds — an entry band
`B_up` and a maintain/exit band `B_dn` — and each can only take a value on the ⅓ lattice,
because **any band below the quantum cannot bind** (T-297's argument, unchanged and not
re-litigated). That makes the whole family a 4×4 grid. Enumerated, with each cell checked
for (i) reachability of full exposure under arbitrary signal paths and (ii) the frozen
crash-exit gate (b):

| `B_up` | `B_dn` | identity | verdict |
|---|---|---|---|
| 0 | 0 | undamped V1 | no damping |
| ⅓ | 0 | **T-298** | constructible — **RAN** |
| ⅓ | ⅓ | **T-297 Arm 1** | violates gate (b) — **RAN, failed** (225-day exit lag) |
| **⅔** | **0** | — | **constructible — UNTESTED** |
| 1 | any | — | degenerate (full exposure unreachable) |
| any | > 0 | — | violates gate (b) |

**The structural result: every `B_dn > 0` violates gate (b).** A nonzero maintain band
delays de-risking by construction, and gate (b) — never delay the crash exit — is frozen.
So *the "loose to maintain" half of a buy/hold spread is unavailable to this strategy on
principle, not by measurement.* The spread can only ever be one-sided here.

That leaves `B_up` as the single free parameter, on a lattice with four rungs, of which
one is the undamped baseline, one is T-298, one is degenerate, and **exactly one is
untested.** There is no sweep to run because there is nothing to sweep: the space is
exhausted by enumeration. This satisfies the "freeze the bands on non-data grounds" rule
in the strongest available form — the band is not chosen, it is *the only remaining value*.

The enumeration reproduces both known results (T-298 constructible and it ran; T-297 Arm 1
gate-(b)-violating and it failed exactly that way), which is the check that the classifier
is describing this strategy and not a model of it.

## 1. The arm

**ARM U ("unanimity re-entry"):** `B_up = ⅔` in frac-space (= 4/3 in exposure units),
`B_dn = 0`.

```
e_held[t] = e_target[t]                      if e_target[t] < e_held[t-1]     (never damp de-risking)
          = e_target[t]                      if e_target[t] − e_held[t-1] > ⅔ (+1e-9 tolerance)
          = e_held[t-1]                      otherwise
```

Stated as a convention rather than a number: T-298 requires **two of three speeds** to agree
before adding leverage; Arm U requires **all three**. That is the next and last rung.

### Its mechanism, stated honestly before running

Arm U is not a small tightening of T-298 — it changes the strategy's shape, and the
pre-registration should say so rather than let the result explain it afterwards. Because
increases require a strictly-greater-than-⅔ jump:

- from `frac = 0`, only a jump to `1` qualifies;
- from `frac = ⅓` or `⅔`, **no increase ever qualifies** (the largest available jump is ⅔,
  which is not > ⅔).

So **exposure can only rise from flat, and only to full.** Between visits to zero the
position is monotonically non-increasing. Arm U is therefore an "all-or-nothing from flat"
re-entry rule. It should cut turnover substantially below T-298 — it removes every partial
re-entry, not merely the single-increment ones — and it pays for that in missed
participation during partial-signal recoveries. Both effects are large and they oppose.

### Gate (b) holds by the same invariant T-298 proved

`e_held ≤ e_target` at all times: decreases execute exactly, increases are damped. By
induction, for any threshold θ, `e_target ≤ θ ⇒ e_held ≤ θ` on the same day. Exit-lag ≤ 0,
never positive. Measured empirically anyway on 2008 / 2020 / 2022 at both frozen thresholds
(≤1.0 and 0.0); a positive lag falsifies the implementation, not the theory.

## 2. Pairing and substrate

- **Paired against the frozen T-298 spec**, same harness, same vehicle (basis-checked SSO
  synthetic, T-282/T-294), same T-284 PRIMARY equity-only config. Only the entry band differs.
- **Substrate: T-306 D-B, 1968-01-03 → 2025-12-31 (~58.3 yr)** — the same window T-312 used,
  so the comparison shares its honest-N and reads directly against T-312's refutation.
- **Reported per `[NN-SHARPE-CI]`:** block-bootstrap (Künsch, 1000 iter, Politis-White block
  length) paired **Δwealth** and **ΔSortino** vs T-298 *and* vs buy-and-hold SPY TR, each with
  `ci_low`/`ci_high`. Point estimates alone are not a result.
- **Also reported, because they are the mechanism:** exposure-units/yr turned (total and
  SSO-leg) vs T-298's figure and the undamped 14.67; terminal wealth on the frozen
  0 / 1.55 / 5 / 10 bps slippage grid, charged the fair way (extra bps on the SSO leg only,
  SPY leg at its measured 0.51 bps); crash-window exit lag at both thresholds; and the count
  of suppressed partial re-entries, which is the cost side of the mechanism.

## 3. Pre-stated gate

Arm U earns the offense row only if **both** hold:

- **(a) wealth:** paired Δwealth vs buy-and-hold SPY TR has `ci_low > 0` at the 5 bps grid
  point — the bar T-312 failed. Directional-but-straddling is **not** a pass; that verdict
  already exists and repeating it earns nothing.
- **(b) exit fidelity:** crash exit-lag ≡ 0 at both thresholds, empirically, on all three
  crisis windows.

Failing (b) with a wealth win is a **fail**, not a trade-off — that ruling is what T-297
already established and it is not reopened here.

## 4. Honest prior — LOW

Below the dispatch's LOW-MODERATE, and the reasoning is worth stating because it is the
main argument against running this at all:

1. **T-312 refuted the family's wealth edge at depth**, on ~10 crises, with a *near-symmetric*
   CI (Δwealth vs buy-hold [−1486, +1438]). It also established the correct interpretation:
   the tail protection is real but is **a path improvement, not a wealth edge**. Arm U changes
   the turnover/participation trade-off; it does not introduce a new source of return.
2. **The cost side is larger here than in T-298.** T-298 suppressed only single-increment
   re-entries (89% of events, all of them the whipsaw-prone kind). Arm U suppresses *every*
   partial re-entry including the genuine two-speed ones that T-298 deliberately kept.
3. **The one thing that would make it work is already measured to be small.** Turnover
   reduction only helps through slippage, and the breakeven is 1.55 bps of SSO-leg slippage
   against a measured ~2.2 bps. The recoverable margin is bounded and thin.

The honest expectation is that Arm U cuts turnover convincingly and still straddles on
Δwealth — i.e. reproduces T-312's verdict through a different construction.

## 5. N_trials

**N += 1.** One arm, one gate, jointly reported. No secondary width exists to promote later:
the lattice is exhausted, so this trial cannot spawn a follow-on within the family.

## 6. Kill statement

**A null closes the gated-leverage family's last open construction door, with a receipt.**
The enumeration in §0 is the strong half of that claim — it shows the family is *finite* and
that only one member was ever untested. If Arm U straddles, then every constructible
buy/hold spread on this signal has been either run or ruled out by a frozen gate, and the
family closes on evidence rather than on fatigue. The closure should be recorded with the
enumeration table attached, so that a future proposal to "try a different band" can be
answered by pointing at the lattice rather than by re-running anything.

## 7. Recommendation to the director

**The enumeration is worth more than the run, and it is already done.** §0 closes the
maintain-side of the family analytically — no trial can be spent to learn that, because
gate (b) forbids those cells on principle.

Two defensible decisions, and I do not think the second is wrong:

- **Run Arm U** for the empirical receipt on the last rung, accepting a LOW prior and N += 1.
- **Close the family on the enumeration alone**, recording Arm U as "constructible, untested,
  prior LOW, not run — the lattice is exhausted and the family's wealth edge was refuted at
  depth by T-312." This spends **zero** trials, and under `[NN-MBL]` a trial not spent is a
  real gain to every other measurement's DSR bar.

My recommendation is the second, with the enumeration table filed as the receipt — but the
call is the director's, and if the answer is "run it," the arm above is frozen as drafted.
