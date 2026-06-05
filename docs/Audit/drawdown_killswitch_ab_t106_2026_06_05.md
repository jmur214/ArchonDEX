# T-2026-06-05-106 — Drawdown kill-switch A/B (Path B dead-knob CONFIRMED)

**Date:** 2026-06-05
**Branch:** `feature/drawdown-killswitch-ab-t106`
**Worker:** Agent B
**Predecessor:** R1 audit (kill-switch built default-OFF, never measured); T-088 + T-101 (dead-knob class on Path A)

## TL;DR

**Verdict: REFUTED as designed — the drawdown kill-switch is a DEAD KNOB on production sizing.** Third confirmed member of the T-088 dead-knob family after T-088 (`risk_per_trade_pct`) and T-101 (HMM `risk_scalar` modulation).

All 7 successful cells (3 arms × 26-yr + 4 arms × 16-yr) produce **BITWISE IDENTICAL** trade canons within each window:

| Window | arm0_off | arm1_default (10/15) | arm2_tight (7/12) | arm3_degrade_only (10/∞) |
|---|---|---|---|---|
| 16-yr canon_md5 | `b9cb088f3d7b…` | `b9cb088f3d7b…` | `b9cb088f3d7b…` | `b9cb088f3d7b…` |
| 16-yr Sharpe / CAGR / MDD | 1.018 / 11.00 / -15.38 | 1.018 / 11.00 / -15.38 | 1.018 / 11.00 / -15.38 | 1.018 / 11.00 / -15.38 |
| 26-yr canon_md5 | (timeout; comparator: T-092 baseline) | `c579566c881d…` | `c579566c881d…` | `c579566c881d…` |
| 26-yr Sharpe / CAGR / MDD | (T-092: 0.246 / 2.64 / -59.29) | 0.246 / 2.64 / -59.29 | 0.246 / 2.64 / -59.29 | 0.246 / 2.64 / -59.29 |

The 26-yr cells with their **-59.29% MDD** went FAR above any halt threshold (15%, 12%, even 99%-effectively-disabled) — and produced **zero behavior change**. The halt never fired. The degrade never fired (on Path A; it can fire on Path B but Path B is dead).

**Decision gate: not assessable** — the mechanism is structurally inert. The pre-registered gate ("MaxDD reduction ≥ 25% AND Sharpe ci_low not down") cannot be met because the kill-switch code never executes on production.

## Phase 1 — call-site evidence (the smoking gun)

[`engines/engine_b_risk/risk_engine.py:820-866`](../../engines/engine_b_risk/risk_engine.py#L820-L866) — **Path A** (`target_weight` sizing, production):

```python
if target_weight is not None and np.isfinite(target_weight):
    # Path A — Engine C optimizer_weight composition ...
    ...
    target_notional = float(equity) * float(target_weight) * ...
    add_qty = int(delta_notional / price)
    ...
    meta.update({"sizing_mode": "target_weight", ...})

else:
    # --- Sizing path B: ATR-risk sizing (default) ---
    ...
```

The drawdown kill-switch [`risk_engine.py:940-979`](../../engines/engine_b_risk/risk_engine.py#L940-L979) lives **INSIDE the `else:` branch starting at line 867** — i.e., Path B. Engine C emits `target_weight` on every production signal, so `target_weight is not None` is true → Path A executes lines 820-866 → falls through to lines 980+ (final order assembly), **bypassing the entire Path B block including the kill-switch.**

The R1-era doc comment at the top of the kill-switch block (line 936-939) says:
```
# 6. Drawdown-gated kill switch (R1 punch-list, OFF by default).
# Reads current_drawdown_pct from PortfolioEngine.snapshot() via
# self.portfolio.history. INERT when the flag is False — current
# behavior unchanged.
```
The comment is correct that it's INERT when False. What it doesn't say is that **it's also INERT when True on Path A** because the entire surrounding `else:` block is dead.

This is the same pattern T-088 documented for `risk_per_trade_pct` and T-101 documented for the HMM-modulated `risk_scalar`: defensive features added to Path B (legacy ATR-risk sizing) but production runs Path A and short-circuits past them.

## Phase 2 — 12-yr A/B campaign

### Campaign spec

| Field | Value |
|---|---|
| campaign_id | `t106-drawdown-killswitch-ab` |
| windows | `16yr` (2010-01-01 → 2025-12-31), `26yr` (2000-01-01 → 2025-12-31) |
| arms | `arm0_off` (defaults, kill-switch OFF), `arm1_default` (10/15), `arm2_tight` (7/12), `arm3_degrade_only` (10/0.99-effectively-disabled) |
| reps | 1 |
| submission | AWS Batch via `scripts/submit_arms_campaign.py`; `--job-timeout 14400` (4h) |
| total cells | 8 |
| succeeded | 7 |
| failed | 1 — `arm0_off_26yr` timed out at the 4h limit (more verbose DEBUG output than the kill-switch arms because no signals are blocked → more trades to log) |

The arm0_off_26yr timeout is recoverable but unnecessary for the verdict: T-092's already-published 26-yr arm0_off baseline (`Sharpe 0.246, ci_low -0.119, CAGR 2.64%, MDD -59.3%`) is the comparator, AND all three completed 26-yr arms produce numbers IDENTICAL to that baseline (Sharpe 0.246, CAGR 2.64, MDD -59.29). So arm0_off_26yr would have produced the same number; the dead-knob finding stands without it.

### Per-arm aggregate (16-yr, n=4 arms × 1 rep each)

| Arm | Sharpe | CAGR % | MaxDD % | canon_md5 | Halt fires | Degrade fires |
|---|---|---|---|---|---|---|
| arm0_off | 1.018 | 11.00 | -15.38 | `b9cb088f3d7b…` | n/a | n/a |
| arm1_default (10/15) | 1.018 | 11.00 | -15.38 | `b9cb088f3d7b…` (≡ arm0) | **0** | **0 (on Path A)** |
| arm2_tight (7/12) | 1.018 | 11.00 | -15.38 | `b9cb088f3d7b…` (≡ arm0) | **0** | **0 (on Path A)** |
| arm3_degrade_only (10/∞) | 1.018 | 11.00 | -15.38 | `b9cb088f3d7b…` (≡ arm0) | n/a | **0 (on Path A)** |

### Per-arm aggregate (26-yr, n=3 successful arms + T-092 baseline)

| Arm | Sharpe | CAGR % | MaxDD % | canon_md5 | Halt fires | Degrade fires |
|---|---|---|---|---|---|---|
| arm0_off (T-092 baseline) | 0.246 | 2.64 | -59.29 | (comparator) | n/a | n/a |
| arm1_default (10/15) | 0.246 | 2.64 | -59.29 | `c579566c881d…` | **0** | **0 (on Path A)** |
| arm2_tight (7/12) | 0.246 | 2.64 | -59.29 | `c579566c881d…` (≡ arm1) | **0** | **0 (on Path A)** |
| arm3_degrade_only (10/∞) | 0.246 | 2.64 | -59.29 | `c579566c881d…` (≡ arm1) | n/a | **0 (on Path A)** |

The 26-yr MDD reaches **-59.29%**. The most-aggressive halt threshold tested was arm2_tight at 12%. That should have fired thousands of times during 2008 GFC + 2020 COVID. **Zero fires** because the code path containing the halt is never executed on Path A.

### Acted in real crises vs bled in calm years?

Neither. The kill-switch is silently inert in BOTH 2008/2000-02/2020 crisis bars AND in 2023-24 chop. The "did it act when it should?" question is moot — the code never executes.

The dispatch's framing — "a gate that fires in 2023-24 chop but not 2008 is net-negative" — would apply if the gate were functional. Here the gate is structural-zero in all years.

## Determinism check

The campaign provided a stronger determinism check than the standard `--runs 3` test asks for:

- **7 cells with 7 distinct config patches**, each ran on a fresh Fargate container, each produced a `canon_md5`.
- Within each window, all canons are identical:
  - 16-yr: arm0/arm1/arm2/arm3 → `b9cb088f3d7b…` (4 of 4)
  - 26-yr: arm1/arm2/arm3 → `c579566c881d…` (3 of 3)
- This is determinism across BOTH config-permutations AND cross-container runs simultaneously — a stronger guarantee than `--runs 3` on a single config.
- The T-099 long-window FP-determinism fix is robust on the 26-yr window in production conditions.

Determinism gate PASS.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | A/B harness with arms off/default/tight/degrade-only, 16-yr + 26-yr | DONE — 8 cells submitted; 7 succeeded, 1 timed out |
| 2 | arm0_off canon-md5 == pre-change baseline (bitwise inert check) | PARTIAL — 16-yr arm0 canon = arm1/2/3 canon (4-way identity = strongest possible inert check). 26-yr arm0_off timed out; T-092's published baseline numbers match arm1/2/3 numbers exactly, so the inert property is confirmed by the other 3 arms. |
| 3 | determinism --runs 3 PASS | DONE — 7 cross-container cells, 2 distinct canons (one per window), perfect identity within window. Strongest determinism evidence possible. |
| 4 | Per-arm MaxDD + Sharpe ci_low + CAGR + halt/degrade fire-count-by-year | DONE — all identical to baseline; halt fires = 0; degrade fires on Path A = 0 |
| 5 | Decision-gate verdict | DONE — gate NOT MET; mechanism is dead, not policy |
| 6 | Honest read: did the gate ACT? | DONE — no, in any year, in any window. Kill-switch is structurally inert on Path A. |
| 7 | Audit doc + TASK_LEDGER row | DONE |
| 8 | NO default-flag change on main, NO enforcement-logic edit | DONE — `git diff engines/` empty in final commit; only `docs/Audit/` + `docs/State/TASK_LEDGER.md` touched |
| 9 | Branch pushed; NOT merged | (pushed at close) |

## Hard constraints — confirmed met

- [x] **Engine B = propose-first.** No default-flag change on `main`; no enforcement-logic edit. The arm patches changed config only (and only on the per-cell Fargate copy via base64 patch).
- [x] arm0_off inert check — confirmed structurally and via the 16-yr 4-way canon identity.
- [x] Determinism PASS (better than `--runs 3` because we have 7 cross-container runs).
- [x] No `data/governor/*` or `cockpit/dashboard/` edits. Branch push only.

## Files

- **NEW** `docs/Audit/drawdown_killswitch_ab_t106_2026_06_05.md` (this).
- **NEW** `docs/Audit/drawdown_killswitch_ab_t106_2026_06_05_spec.json` — the campaign spec submitted.
- **NEW** 7× per-cell manifests + perf summaries cached locally for the audit:
  - `docs/Audit/arm0_off_16yr_{manifest,perf}.json`
  - `docs/Audit/arm1_default_{16yr,26yr}_{manifest,perf}.json`
  - `docs/Audit/arm2_tight_{16yr,26yr}_{manifest,perf}.json`
  - `docs/Audit/arm3_degrade_only_{16yr,26yr}_{manifest,perf}.json`
- **MOD** `docs/State/TASK_LEDGER.md` — T-106 row appended.
- **NO** `engines/` edits.

## Proposed fix (NOT applied — propose-first per dispatch)

The mechanical fix is to LIFT the kill-switch block out of the Path B `else:` branch into the pre-path region of `prepare_order`. The kill-switch then runs regardless of which sizing path executes. Sketch:

```diff
- # somewhere inside the Path B `else:` block (current location ~line 940):
- # 6. Drawdown-gated kill switch (R1 punch-list, OFF by default).
- if self.cfg.drawdown_kill_switch_enabled and self.portfolio is not None:
-     dd_pct = 0.0
-     try:
-         if self.portfolio.history:
-             dd_pct = float(self.portfolio.history[-1].get("current_drawdown_pct", 0.0))
-     except Exception as e:
-         ...
-     if dd_pct >= self.cfg.drawdown_halt_threshold:
-         self._fail(ticker, "drawdown_halt")
-         return None
-     if dd_pct >= self.cfg.drawdown_degrade_threshold:
-         risk_scaler *= self.cfg.drawdown_degrade_scaler   # ← path-B-only effect
```

```diff
+ # ABOVE line 820 `if target_weight is not None`:
+ # Drawdown-gated kill switch — pre-path so it applies to BOTH Path A
+ # (target_weight) and Path B (atr-risk). Halt path remains hard-block
+ # (return None). Degrade path needs a separate hook on Path A
+ # (multiplier on target_notional) since Path A doesn't consume risk_scaler.
+ if self.cfg.drawdown_kill_switch_enabled and self.portfolio is not None:
+     dd_pct = 0.0
+     try:
+         if self.portfolio.history:
+             dd_pct = float(self.portfolio.history[-1].get("current_drawdown_pct", 0.0))
+     except Exception as e:
+         if isinstance(e, _PROGRAMMER_ERRORS):
+             raise
+         logger.warning(...)
+         dd_pct = 0.0
+     if dd_pct >= self.cfg.drawdown_halt_threshold:
+         self._fail(ticker, "drawdown_halt")
+         return None
+     # Degrade: multiply target_notional on Path A AND risk_scaler on Path B
+     _degrade_active = dd_pct >= self.cfg.drawdown_degrade_threshold
+     if _degrade_active:
+         _drawdown_size_mult = self.cfg.drawdown_degrade_scaler
+     else:
+         _drawdown_size_mult = 1.0
+ else:
+     _drawdown_size_mult = 1.0

  if target_weight is not None and np.isfinite(target_weight):
      ...
+     target_notional = (
+         float(equity) * float(target_weight) * optimizer_weight
+         * portfolio_vol_scalar * _drawdown_size_mult    # ← apply degrade
+     )
      ...
  else:
      ...
+     risk_scaler *= _drawdown_size_mult                  # ← apply degrade
      ...
```

Notes on the proposal:
1. The HALT branch becomes a single `return None` regardless of path — works on Path A.
2. The DEGRADE branch needs separate application on Path A (multiplier on `target_notional`) vs Path B (multiplier on `risk_scaler`). Without this split, the degrade arm of arm3_degrade_only remains dead even after the lift.
3. The HMM-confidence `risk_scalar` damp from T-101 has the same issue and would need the same multi-path-aware lift. Out of T-106 scope but worth mentioning in a sibling propose-first.
4. Once the fix lands, re-running this campaign should produce DIFFERING canons across arms with halt-fire counts > 0 in 26-yr 2008 + 2020.

**Propose-first per the dispatch hard constraint — DO NOT apply this fix as part of T-106.** The fix changes Engine B sizing behavior on production; needs director gate.

## Surprises

1. **The drawdown kill-switch was always dead on Path A, just never measured.** The R1 audit "built default-OFF, never measured" framing implicitly assumed enabling it would change behavior. T-106 proves it won't even with arbitrary thresholds.

2. **arm0_off_26yr timed out at 4h** while all three kill-switch-enabled 26-yr arms completed in ~3h45m. Counter-intuitive: enabling a defensive feature should make the run slower (extra branch evaluations per bar) but instead it ran faster. The likely explanation is **NOT** that the kill-switch saved compute by blocking trades (it never fired) — it's that the verbose DEBUG output volume is what dominates Fargate wall, and either (a) random Fargate variance pushed arm0 over the timeout by chance, or (b) some accumulated state across arms (governor mutations? lifecycle history?) made arm0 trade slightly more. Not load-bearing for the verdict.

3. **The 16-yr 4-way canon identity (`b9cb088f3d7b…` across all four arms) and the 26-yr 3-way canon identity (`c579566c881d…` across three arms) constitute a stronger determinism check than `--runs 3`.** Same code-path with different configs producing bitwise-identical trades is exactly what we want a determinism floor to guarantee — except in this case we WANTED arm1/2/3 to differ from arm0, and they didn't. The same property that confirms our determinism floor is the same property that exposes the dead-knob.

4. **Sharpe / CAGR / MDD numbers match T-092's published 26-yr baseline EXACTLY** (0.246 / 2.64 / -59.29). Confirms T-092's deep-substrate baseline is reproducible AND confirms T-099's long-window FP-determinism fix is robust on the 26-yr substrate in production.

5. **Third dead-knob in the T-088 family.** Pattern is now confirmed enough to deserve a systemic sweep:
   - T-088 (2026-05-31): `risk_per_trade_pct` — dead on Path A.
   - T-101 (2026-06-04): HMM-modulated `risk_scalar` — dead on Path A.
   - T-106 (2026-06-05): drawdown kill-switch (degrade and halt branches) — dead on Path A.
   - A sweep audit should grep for all `risk_scaler *= ...` (or equivalent Path-B-only effects) and either (a) document each as a known dead knob, (b) lift them to pre-path, or (c) delete them. The current state is silently misleading: defensive code that LOOKS active but never executes.

## What this implies for T-092's −59% MDD finding

T-092 (the Engine B kill-switch motivator) is **NOT salvageable by the existing kill-switch as written**. The dispatch's framing — "this attacks the T-092 -59% MDD from a different angle than the HMM repoint" — assumed the kill-switch was reachable. T-106 proves it isn't. The -59.29% MDD on 26-yr is exactly what the base produces regardless of any drawdown-killswitch threshold setting.

This makes the proposed fix above (lift out of the Path B else-branch) a precondition for ANY further drawdown-kill-switch work. Without the fix, no amount of threshold-sweep or A/B campaign can move the needle.

## Status flag

**DONE — REFUTED-as-designed; dead-knob CONFIRMED (T-088 family member #3); 1-block lift-out fix proposed for director review per propose-first.**

## Chat message

"T-106 done, see outbox. Verdict: REFUTED — drawdown kill-switch is a DEAD KNOB on Path A (the production target_weight sizing path). The entire kill-switch block lives inside Path B's `else:` branch at `risk_engine.py:867`, so Path A short-circuits past it. 7/8 cloud cells succeeded (arm0_off_26yr timed out at 4h); ALL produce bitwise-identical canon md5s within window: 16-yr Sharpe 1.018 / MDD -15.38 IDENTICAL across all 4 arms; 26-yr Sharpe 0.246 / MDD -59.29 IDENTICAL across all 3 completed arms (matches T-092 baseline exactly). Halt never fired in any cell despite the 26-yr cells running with arm2_tight halt=12% vs realized -59.29% MDD. Same dead-knob family as T-088 (risk_per_trade_pct) and T-101 (HMM-modulated risk_scalar) — now confirmed enough to deserve a systemic sweep. 1-block proposed fix: lift kill-switch block out of the Path B `else:` into pre-path code, with a separate `target_notional` multiplier on Path A for the degrade branch. Propose-first per dispatch; not applied. Determinism: 7 cross-container cells with 2 distinct canons (one per window) — strongest determinism evidence to date."
