---
task_id: T-2026-06-14-128r (sleeve A/B close-out on the trustworthy re-anchored substrate)
title: Spot 8-ETF crisis-diversifier sleeve A/B — does it lift the borderline base over the line?
date: 2026-06-14
substrate: image sha-4c0fc16, job def archondex-backtest-reanchor-mv-t167:1 (cov-pin + T-167 complete substrate + LIVE regime + config-true mean_variance). The first trustworthy substrate the sleeve has ever been tested on.
scope: pure measurement (sleeve flag in arm config_patch only; no engine/flag changes)
status: PRE-REGISTRATION committed BEFORE running (honest-N); results appended after
outcome: "[PENDING — header updated after the A/B lands. Section 1 below is committed before any arm number is unblinded.]"
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

Per CLAUDE.md #6 the gate is ci_low, never point. Per #9 the verdict is on
THIS (re-anchored) substrate, not the old one.

### 1.7 N-trials policy

**N_trials += 1** (this is a new integrated measurement of the sleeve
hypothesis on the current canonical substrate — the prior T-128/T-128b runs
were invalid, so this is the first valid integrated test; honest-N counts
it). Pre-registered before unblinding per CLAUDE.md #7.

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
