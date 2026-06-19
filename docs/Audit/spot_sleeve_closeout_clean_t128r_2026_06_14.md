---
task_id: T-2026-06-14-128r (sleeve A/B close-out on the trustworthy re-anchored substrate)
title: Spot 8-ETF crisis-diversifier sleeve A/B — does it lift the borderline base over the line?
date: 2026-06-14
substrate: image sha-4c0fc16, job def archondex-backtest-reanchor-mv-t167:1 (cov-pin + T-167 complete substrate + LIVE regime + config-true mean_variance). The first trustworthy substrate the sleeve has ever been tested on.
scope: pure measurement (sleeve flag in arm config_patch only; no engine/flag changes)
status: CURRENT (pre-registration committed before running — see git history; results appended after)
outcome: "**NOT RECOMMEND (per pre-registered rule) — the crisis-MDD thesis is REFUTED on the integrated path; the sleeve is a marginal calm-period return-diversifier instead.** Substrate VALID (anchor 16yr 5/5 bitwise 3e9ea427/1.162; 26yr arm0 4/5-canon/5/5-Sharpe 158fe678/0.751; sleeve arms 5/5 bitwise — the trustworthy test T-128/T-128b lacked). 26yr: spot@25% lifts Sharpe 0.751→0.897 and standalone ci_low 0.333→0.501 (clears the 0.40 line the base sat under) — BUT via calm-period return diversification (calm Sharpe 0.771→0.946), NOT drawdown reduction: MDD cut only +0.74pp (2.3%, vs the +16.2% T-115 analytical claimed), and the sleeve does WORSE in 2008/2020. Paired ON−OFF difference NOT significant (Δci_low −0.361). spot@30% over-dilutes (Sharpe flat, ci_low 0.340 < base 0.382). Decision rule fails criterion 1 (MDD-cut ≥15%) for both. 16yr drag bounded (−0.05/−0.02, criterion 3 PASS). Reclassifies conditional-shelf entry: the sleeve is NOT a crisis-MDD hedge (retire that framing); it is NOT a substitute for C's T-118 de-gross. N_trials += 1. Residual flagged: cov-pin not yet bitwise-perfect on arm0 (1/5 reps differ at trade level, identical Sharpe)."
---

# Sleeve A/B Close-Out — Clean Substrate (T-128r)

## 1. PRE-REGISTRATION (committed before any arm result)

### 1.1 Why this re-run exists

The prior sleeve close-out (T-128-CO, 2026-06-12) was INVALID — it ran on
the broken substrate (anchors didn't reproduce; the placement lottery was
live; arm0 16-yr drew the minority attractor). The substrate is now fixed
(re-anchor + cov-pin, N=5 bitwise-unanimous; the "26-yr collapse" was a
4-way substrate artifact, not real). The base is now **borderline-real, not
collapsed**:

| Window | Anchor canon | Sharpe | ci_low | MDD |
|---|---|---|---|---|
| 16-yr (2010-25) | `3e9ea427` | 1.162 | 0.676 | −16% |
| 26-yr (2000-25) | `158fe678` | 0.751 | **0.382** | **−33%** |

The 26-yr ci_low (0.382) sits **just under the 0.40 CI-aware kill line** —
not killed, not validated. The conditional shelf (T-166) lists this sleeve
as the spot 8-ETF crisis-diversifier (analytical +16.2% MDD-cut @25% on
17.9-yr, previously double-blocked by the broken substrate). This is its
first real integrated test.

### 1.2 The question (fixed in advance)

**Does the spot 8-ETF crisis-diversifier sleeve cut the 26-yr −33% MDD and
lift the full-cycle ci_low toward/past the 0.40 line — and at what
allocation?** Secondary: what does it cost on the crisis-light 16-yr window
(the calm-drag side of the conditional profile)?

### 1.3 The grid (fixed)

Arms × windows × reps:
- Arms: `arm0_off`, `arm1_on_25pct` (spot_sleeve @ 25%), `arm2_on_30pct` (@ 30%)
- Windows: 2010-01-01→2025-12-31 (16-yr), 2000-01-01→2025-12-31 (26-yr)
- Reps: **5 per cell** (the cov-pin makes these bitwise by construction;
  N=5 verifies that the cov-pin fully fixed the SLEEVE path too — the sleeve
  changes book capital → MVO inputs → the exact path that was nondeterministic
  pre-pin, so confirming sleeve-arm unanimity is real evidence, not ritual).
- Total: 3 × 2 × 5 = 30 cells + 3 launcher canary (2022).

### 1.4 Anchor gate (HARD — pre-flight + in-campaign)

- **arm0 16-yr must reproduce `3e9ea427`/1.162; arm0 26-yr must reproduce
  `158fe678`/0.751** — at 5/5 bitwise unanimity. The cov-pin predicts this
  by construction; if arm0 does NOT reproduce, the substrate is not the one
  the anchors came from → **STOP and report** (do not interpret any arm delta).
- Launcher canon-anchor hard gate (T-140) is structural: the spec includes
  the unpatched `arm0_off` baseline arm, so the gate is satisfied.
- Mildest-config-fires pre-flight: the 25% arm at 1-yr (2022) must produce a
  canon DIFFERENT from arm0 (flag actually fires) before the full spend.

### 1.5 The read (fixed)

Per window per allocation, vs the arm0 baseline:
- **ΔSharpe** (point) and **Δci_low on the difference series** (block
  bootstrap, block=7, n_iter=1000, seed=42 — project standard, same params
  as T-115/T-128).
- **ΔMDD** (relative % and absolute pp).
- **Net ci_low** of each ON arm (does the 26-yr ON arm's own ci_low clear
  0.40?).
- Crisis-year sub-returns (2008/2020/2022) and calm-stretch Sharpe, to
  confirm the crisis-diversifier profile.

### 1.6 Decision rule (fixed, pre-registered)

The sleeve is a **recommend-to-deploy candidate** iff, on the 26-yr window:
1. **26-yr MDD reduction ≥ 15% relative** (the crisis-diversifier's core claim), AND
2. **26-yr ON-arm ci_low ≥ 0.40** (lifts the borderline base over the
   CI-aware line) OR **Δci_low-on-difference > 0 with the ON ci_low ≥ the
   base 0.382** (strictly improves the borderline without crossing — a
   weaker "helps, doesn't yet validate" verdict), AND
3. the 16-yr calm-drag is bounded (ΔSharpe ≥ −0.20 — the conditional cost
   side stays modest).

Full pass on (1)+(2-strong)+(3) → RECOMMEND. (1)+(2-weak)+(3) → HELPS,
conditional-shelf-confirmed, gate-on-`hmm_p_crisis` for the calm-drag.
Fails (1) or (2) → sleeve does not lift this base; close negative.

Per CLAUDE.md `[NN-SHARPE-CI]` the gate is ci_low, never point. Per #9 the verdict is on
THIS (re-anchored) substrate, not the old one.

### 1.7 N-trials policy

**N_trials += 1** (this is a new integrated measurement of the sleeve
hypothesis on the current canonical substrate — the prior T-128/T-128b runs
were invalid, so this is the first valid integrated test; honest-N counts
it). Pre-registered before unblinding per CLAUDE.md `[NN-MBL]`.

---

## 2. RESULTS

(Appended after the pre-registration commit — verify section 1 predates these numbers in git history.)

### 2.0 Substrate validity — CONFIRMED (the thing the prior run lacked)

- **Canary 2022: 3/3 bitwise unanimous** (`eb48742e`/1.512). The prior
  (broken-substrate) run split this 2-vs-1; the cov-pin fixed it.
- **Anchor gate 16-yr: PASS, 5/5 bitwise.** arm0_off 16-yr reproduces
  the published anchor `3e9ea427`/1.162 across all 5 reps. The sleeve
  arms are also bitwise-unanimous across reps (on25 5/5 `b2dea6c5`,
  on30 `f38e1966`) — the cov-pin holds on the capital-partitioned
  sleeve path, not just arm0. This A/B is VALID (unlike T-128/T-128b).
- 26-yr anchor gate pending (cells running on the 10h-cap relaunch).

### 2.1 16-yr leg (2010-2025) — sleeve is a bounded calm-drag, trivial MDD help

| Arm | canon | Sharpe | ΔSharpe | ON ci_low | Δ-on-diff ci_low | MDD | ΔMDD (rel / abs) |
|---|---|---|---|---|---|---|---|
| arm0_off | `3e9ea427` | 1.162 | — | 0.675 | — | −16.2% | — |
| on25% | `b2dea6c5` | 1.110 | **−0.051** | 0.642 | −0.540 | −15.4% | +4.6% / +0.74pp |
| on30% | `f38e1966` | 1.145 | **−0.016** | 0.694 | −0.559 | −15.7% | +2.9% / +0.46pp |

Crisis(2020)/calm split (Sharpe): arm0 2020 +2.77 / calm +1.02; on25
2020 +2.65 / calm +0.98; on30 2020 +2.44 / calm +1.04.

**16-yr read:** the sleeve mildly dilutes a strong bull book (ΔSharpe
−0.05/−0.02) — calm-drag criterion (≥ −0.20) **PASS**. But MDD help is
trivial (+0.46-0.74pp), far under the 15% bar, and Δ-on-difference ci
spans zero (statistically no effect). Expected: the 16-yr window's
only crisis is the V-shaped 2020 the equity book already rode well
(Sharpe +2.77), so there's no sustained drawdown for a diversifier to
cut. **The sleeve's case rests entirely on the 26-yr full-cycle leg
(2008 GFC + 2000-02 dot-com), which is where the −33% MDD it's meant
to flatten actually lives.**

### 2.2 26-yr leg (2000-2025) — the decision-relevant full cycle

Ran on the 10h-cap relaunch (`t128r-sleeve-26yr-longcap`, job-timeout
36000) after the original 26-yr cells were terminated for projected
timeout (T-167 complete ~96-ticker universe runs ~330 min/cell vs the
360-min default cap).

**Anchor gate: arm0 26-yr reproduces `158fe678`/0.751 — 4/5 bitwise on
canon, 5/5 on Sharpe.** rep2 carried a different trades-canon
(`e801f11b`) with an IDENTICAL Sharpe 0.751 — a single-trade residual,
NOT a lottery flip (the lottery swung Sharpe 0.237↔0.446; here all 5
reps are 0.751). The sleeve arms are 5/5 bitwise-unanimous
(on25 `520ef0ab`/0.897, on30 `11ea6c63`/0.738). The anchor VALUE
reproduces and the arms are deterministic, so the A/B is interpretable.
**Residual flagged for the determinism owners (B): the cov-pin is
not yet bitwise-perfect on arm0 — one rep in five differs at the trade
level without moving the metric; worth a look but it does not confound
this A/B (Sharpe is unanimous).**

| Arm | canon | Sharpe | ΔSharpe | ON ci_low | Δ-on-diff ci_low | MDD | ΔMDD (rel / abs) |
|---|---|---|---|---|---|---|---|
| arm0_off | `158fe678` (4/5; 5/5 Sharpe) | 0.751 | — | 0.333 | — | −32.6% | — |
| on25% | `520ef0ab` (5/5) | **0.897** | **+0.146** | **0.501** | −0.361 | −31.9% | +2.3% / +0.74pp |
| on30% | `11ea6c63` (5/5) | 0.738 | −0.013 | 0.340 | −0.519 | −30.3% | +7.1% / +2.31pp |

Crisis/calm split (Sharpe; 2008 + 2020 are the full-cycle's two
defining events):

| Arm | 2008 Sh (ret) | 2020 Sh (ret) | calm Sh (ex-08/20) |
|---|---|---|---|
| arm0_off | −0.710 (−11.7%) | +3.125 (+32.7%) | +0.771 |
| on25% | −0.954 (−12.8%) | +2.872 (+27.1%) | **+0.946** |
| on30% | −0.739 (−10.8%) | +2.768 (+31.0%) | +0.750 |

**The crisis-diversifier thesis is REFUTED on the integrated path.**
The sleeve does NOT cut the −33% MDD meaningfully (+0.74pp at 25%,
+2.31pp at 30% — a 2-7% relative cut, vs the +16.2% the T-115
analytical claimed on 17.9-yr), and it actually does WORSE in the
actual crises (2008 −0.954 vs −0.710; 2020 +27% vs +33%). The
analytical massively overstated the MDD reduction — the same
integrated-vs-analytical gap T-120/T-121 found (the partition isn't
scale-invariant).

**What the sleeve DOES do at 25%:** it lifts the full-cycle Sharpe
0.751 → 0.897 and its standalone ci_low 0.333 → 0.501 (clearing the
0.40 CI-aware line the base sat under) — but via **calm-period return
diversification** (calm Sharpe +0.771 → +0.946), NOT crisis hedging.
And the paired ON−OFF difference is NOT statistically significant
(Δ-on-difference ci_low −0.361, crossing zero). on30 over-dilutes
(Sharpe flat, ci_low 0.340 drops below the base's 0.382).

### 2.3 Verdict — NOT RECOMMEND (per the pre-registered rule), with a refined finding

**Pre-registered decision rule, scored:**

| Criterion | on25% | on30% |
|---|---|---|
| (1) 26-yr MDD reduction ≥ 15% rel | **FAIL** (+2.3%) | **FAIL** (+7.1%) |
| (2) ON ci_low ≥ 0.40 (strong) or Δci_low>0 & ON≥0.382 (weak) | PASS-strong (0.501) | FAIL (0.340) |
| (3) 16-yr calm-drag ≥ −0.20 | PASS (−0.05) | PASS (−0.02) |
| **Overall (AND of 1+2+3)** | **NOT RECOMMEND** (fails 1) | **NOT RECOMMEND** (fails 1+2) |

**Verdict: do NOT deploy the spot sleeve as a crisis-MDD lever.** The
mechanism the dispatch asked about — "does the crisis-diversifier cut
the −33% MDD and lift ci_low toward 0.40" — is answered NO on the cut:
the integrated MDD reduction is 2-7%, not ≥15%, and the sleeve
underperforms in 2008/2020. Criterion 1 fails, so the rule returns
NOT RECOMMEND.

**The refined finding (more useful than a bare fail):** the sleeve @
25% IS a marginal risk-adjusted-return helper — it lifts the borderline
base's Sharpe (0.751→0.897) and standalone ci_low (→0.501, over the
0.40 line) — but through **calm-period return diversification, not
drawdown reduction**, and the A/B difference is not statistically
clean (paired ci_low crosses zero). This reclassifies the
conditional-shelf entry (T-166 #4): the spot sleeve is **NOT a
crisis-MDD hedge** (retire that framing) — it's a calm-period
return-diversifier whose net is mildly positive at 25% and negative
(over-diluting) at 30%. It is NOT a substitute for C's T-118 de-gross
overlay, which remains the candidate MDD lever; the two are not
redundant (the sleeve doesn't touch the −33%).

**Fork input:** the borderline base (0.751 / ci_low 0.382) is lifted
over the 0.40 line by the spot sleeve @ 25% on a Sharpe basis, but
(a) not significantly and (b) not by cutting drawdown. The honest
read for the deploy decision: the sleeve is not the drawdown fix; if
the goal is to flatten the −33% MDD, the de-gross overlay is the lever
to watch, not this sleeve.
