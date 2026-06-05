# T-2026-06-05-111 — Engine B defensive-wiring systemic sweep (Path A vs Path B inventory + lift-out design + drawdown PoC)

**Date:** 2026-06-05
**Branch:** `feature/engine-b-defensive-wiring-sweep-t111`
**Worker:** Agent B
**Predecessors:** T-088 (`risk_per_trade_pct` dead-knob), T-101 (HMM `risk_scalar` dead-knob), T-106 (drawdown kill-switch dead-knob)

## TL;DR

**Engine B has 10 defensive / sizing-modulation capabilities. 7 are DEAD on production (Path A); 3 are LIVE.** Every recent "is the de-gross helping?" A/B has been measuring code that production never executed. The systemic root cause is a single structural decision: when `prepare_order` reaches its sizing branch at `risk_engine.py:820`, Path A (`target_weight`, used by production via Engine C) computes `target_notional` from 4 multipliers and falls through; Path B (`else:` `atr_risk`) carries the entire dynamic-sizing apparatus (`risk_scaler` and its 6 sub-multipliers, the drawdown kill-switch, ATR stop-widening, the per-position `max_pos_value_pct` cap, even `risk_per_trade_pct` itself) and is never executed in production.

| Defensive control | Live on Path A? | Source | Audit |
|---|---|---|---|
| Crisis floor on `suggested_max_positions` (5/7/12/18) | **YES** | `risk_engine.py:729-731` consumed at `:751` | T-100 confirmed |
| `suggested_exposure_cap` → `effective_max_gross` | **YES** | `risk_engine.py:734-736` consumed at `:1119` | T-100 confirmed |
| `effective_sector_cap` from `correlation_regime` | **structurally yes BUT producer dead** | `risk_engine.py:744-748` consumed at `:1111` | T-104 / T-107 — writer never injects key into advisory |
| Engine C HRP `optimizer_weight` on `target_notional` | **YES** | `risk_engine.py:827, 831` | charter-documented |
| `portfolio_vol_scalar` on `target_notional` | **YES** (when flag) | `risk_engine.py:808 → 832` | T-055h flag-gated default OFF, refuted on 12-yr |
| Wash-sale gate | **YES** (pre-path) | `risk_engine.py:704-716` | sub-config default OFF |
| LT-hold-defer on exits | **YES** (pre-path; exit-only) | `risk_engine.py:592-621` | sub-config default OFF |
| Liquidity / min-notional / ADV clip | **YES** (post-path) | `risk_engine.py:1062-1083` | always-on |
| `risk_scaler` (6 sub-multipliers: gate_conf, signal_strength, governor_weight, **`advisory_risk_scalar`** (T-101), optimizer_weight Path-B-copy, portfolio_vol_scalar Path-B-copy) | **NO** — lives in Path B `else:` | `risk_engine.py:893-934` | T-101 confirmed `risk_scaler *= advisory_risk_scalar` is dead in prod |
| `base_risk_pct = risk_per_trade_pct` | **NO** — Path B base | `risk_engine.py:892` | T-088 dead-knob |
| Drawdown kill-switch (warn/degrade/halt) | **NO** — Path B `else:` | `risk_engine.py:940-979` | T-106 dead-knob; **T-111 PoC lifts it** (default OFF) |
| ATR stop-widening (high vol → wider stops) | **NO** — Path B vol_state branch | `risk_engine.py:881-889` | dead Path B |
| `max_pos_value_pct` cap (per-position $ ceiling) | **NO** — Path B `max_value` clamp | `risk_engine.py:996-998` | dead-knob (Engine C `max_weight=0.30` is the live per-position cap) |

**3 LIVE, 7 DEAD.** The dispatch asked which controls production ACTUALLY applies: it's exactly **(a) advisory `suggested_max_positions` floor, (b) advisory `suggested_exposure_cap` gross gate, (c) sector-cap gate** (with the caveat T-104 documented that the producer side is broken). Everything else — every `risk_scaler` modulation including the validated HMM input from T-101, the entire drawdown kill-switch, all the per-position ATR-risk sizing math — is structurally inert.

## Part 1 — full Engine B dead-defensive-surface inventory

### Production flow through `prepare_order` (`risk_engine.py:513`)

The function executes in **three blocks** stitched around the sizing-path split at line 820:

1. **Pre-path (lines 513-819)** — runs regardless of which sizing path executes
2. **Sizing path (lines 820-1052)** — `if target_weight is not None and np.isfinite(target_weight): # Path A; else: # Path B`
3. **Post-path (lines 1054-1162)** — runs after the sizing block

### Pre-path inventory (lines 513-819) — runs every time

| Capability | Path-A-live? | Source | Default state | Notes |
|---|---|---|---|---|
| `side` validation (long/short/none) | YES | `:556` | n/a | always-on |
| Warmup bars check (`min_bars_warmup`) | YES | `:564` | always-on | |
| Cooldown bars (`cooldown_bars > 0`) | YES | `:574-581` | `cooldown_bars=0` default → no-op | |
| Exit-signal early return + LT-hold defer | YES (exits only) | `:584-635` | `lt_hold.enabled=False` default | Path A; sub-config |
| Flip-direction exit-first | YES | `:642-688` | always-on | |
| `allow_shorts` gate | YES | `:691-695` | `allow_shorts=False` default | |
| **Wash-sale gate** | **YES** | `:702-718` | `wash_sale.enabled=False` default | Path A; sub-config |
| Advisory pre-compute: `effective_max_positions ← min(suggested_max_positions, cfg)` | **YES** | `:729-731` | `risk_advisory_enabled=True` default | **Live crisis floor** |
| Advisory pre-compute: `effective_max_gross ← min(suggested_exposure_cap, cfg)` | **YES** | `:734-736` | same | **Live de-gross** |
| Advisory pre-compute: `advisory_risk_scalar = advisory.risk_scalar` | **NO** | `:739-741` | same | **DEAD** — variable only consumed inside Path B at `:915` |
| Advisory pre-compute: `effective_sector_cap` from `correlation_regime` | YES (consumer) / **NO** (producer-dead) | `:744-748` | same | T-104 confirmed: `correlation_regime` writer is broken; consumer always sees default "normal" |
| `max_positions_reached` gate (count check) | **YES** | `:751-755` | always-on | consumes `effective_max_positions` |
| Price/ATR sanity (`close_missing`, `invalid_price`, `invalid_atr_after_fallback`) | YES | `:758-792` | always-on | |
| `portfolio_vol_scalar = _compute_portfolio_vol_scalar(advisory)` | YES (consumer for Path A at `:832`) / Path-B-copy at `:934` | `:808` | `portfolio_vol_target_enabled=False` default | T-055h refuted; default OFF returns 1.0 |

**Pre-path live defensive surface = 5 controls** (`max_positions_reached`, `suggested_max_positions` floor, `suggested_exposure_cap`, `effective_sector_cap` consumer, wash-sale, LT-hold-defer). One of those (`effective_sector_cap`) has a producer-side dead-letter per T-104.

### Path A inventory (lines 820-866) — production sizing branch

| Capability | Path-A-live? | Source | Notes |
|---|---|---|---|
| `target_weight` from Engine C `target_weights` | YES | `:817-820` | required for Path A entry |
| `optimizer_weight` (HRP-composed) into `target_notional` | YES | `:827-833` | per-bar from `signal.meta`, default 1.0 |
| `portfolio_vol_scalar` into `target_notional` | YES | `:832` | T-055h-refuted, default OFF returns 1.0 |
| **`_drawdown_size_mult` into `target_notional`** (T-111 PoC) | **YES when flag pair ON** | `:884` (Path A) and pre-path block at `:826-878` | **NEW T-111 reference implementation** |
| `target_notional = equity × target_weight × optimizer_weight × portfolio_vol_scalar [× _drawdown_size_mult]` | YES | `:830-836` | the ONLY multiplicative chain Path A consumes |
| `rebalance_tolerance` skip (drift below threshold) | YES | `:837-843` | `rebalance_tolerance` default small |
| `add_qty = int(delta_notional / price)` | YES | `:845` | |
| `force_min_qty_on_signal` 1-share probe | YES | `:846-854` | |
| `meta.update({"sizing_mode": "target_weight", ...})` | YES | `:859-865` | logger sees Path A every time |

**Path A has exactly ZERO defensive risk-multipliers besides what we add via the T-111 pre-path lift.** The defensive features that live HERE are:

1. **Inherent**: `target_weight` is what Engine C's `compute_target_allocations` produced, which already incorporates `max_weight=0.30` per-asset cap.
2. **Pre-path advisory caps** that affect `effective_max_positions` + `effective_max_gross` consumed later.
3. **(NEW T-111 PoC)** drawdown halt (returns None) + drawdown-degrade multiplier on `target_notional`.

### Path B inventory (lines 867-1052) — atr_risk fallback, **NEVER runs in prod**

| Capability | Path-A-live? | Source | Audit |
|---|---|---|---|
| `vol_state` regime-conditional ATR stop multiplier (high/low → adjust `stop_dist`) | **NO** | `:881-889` | |
| `base_risk_pct = risk_per_trade_pct` | **NO** | `:892` | **T-088 dead-knob** |
| `risk_scaler = 1.0` start; reduced by `gate_conf` (4-band table) | **NO** | `:898-904` | |
| `risk_scaler *= 0.5 + signal.strength` | **NO** | `:906-908` | |
| `risk_scaler *= governor_weight` | **NO** | `:911-912` | |
| `risk_scaler *= advisory_risk_scalar` (HMM-modulated) | **NO** | `:915` | **T-101 dead-knob** (HMM repoint behaviorally inert because of this) |
| `risk_scaler *= optimizer_weight` (Path-B copy) | **NO** | `:924-926` | duplicate of Path-A consumer at line 831 |
| `risk_scaler *= portfolio_vol_scalar` (Path-B copy) | **NO** | `:934` | duplicate of Path-A consumer at line 832 |
| Drawdown kill-switch warn/degrade/halt | **NO** | `:940-979` | **T-106 dead-knob** |
| `adjusted_risk_pct = base_risk_pct * risk_scaler` cap | **NO** | `:981-984` | |
| `risk_budget = equity × adjusted_risk_pct` | **NO** | `:986` | |
| `raw_qty = risk_budget / stop_dist` | **NO** | `:995` | |
| `max_value = equity × max_pos_value_pct` cap | **NO** | `:996-998` | **Dead-knob** (live per-position cap is Engine C `max_weight=0.30`) |
| `meta.update({"sizing_mode": "atr_risk", ...})` | **NO** | `:1043-1052` | logger never sees this in prod |

**Every single defensive multiplier in Path B is dead in production.** The `meta.update({"sizing_mode": "atr_risk"})` line at `:1043` is the canary — if it ever appears in a prod trade log, something has gone wrong with target-weight emission upstream.

### Post-path inventory (lines 1054-1162) — runs after the sizing branch

| Capability | Path-A-live? | Source | Notes |
|---|---|---|---|
| `min_qty` floor | YES | `:1055-1059` | always-on |
| Liquidity / ADV clip | YES | `:1062-1076` | always-on |
| `min_notional` floor | YES | `:1079-1083` | always-on |
| `debug_override` fallback 1-share | YES | `:1086-1090` | dev-only |
| **Sector exposure check vs `effective_sector_cap`** | **YES** | `:1107-1115` | live consumer of the dead-producer key (per T-104) |
| **Gross exposure check vs `effective_max_gross`** | **YES** | `:1117-1123` | live consumer of advisory's `suggested_exposure_cap` |
| SL/TP off `atr_stop_mult` / `atr_tp_mult` | YES | `:1129-1135` | always-on; **not Path B-gated** (computed from cfg defaults, not the `vol_state`-adjusted `stop_mult` from Path B) |

The SL/TP at line 1129-1135 is subtle: it uses `self.cfg.atr_stop_mult` directly, NOT the `stop_mult` that Path B may have widened via vol_state. So even the vol-state-aware stop-widening in Path B is doubly dead in prod — the value computed there is overwritten by the cfg default in the post-path block.

## Part 1 — what production ACTUALLY applies as defense

Stripping the inventory down to what's actively gating trades on Path A:

1. **Max-positions cap with crisis floor** (`effective_max_positions`): from advisory's `suggested_max_positions` floored by `cfg.max_positions`. **LIVE.**
2. **Gross exposure cap with advisory de-gross** (`effective_max_gross`): from advisory's `suggested_exposure_cap` floored by `cfg.max_gross_exposure`. **LIVE.**
3. **Sector exposure cap** (`effective_sector_cap`): consumer is live, but the `correlation_regime` writer side is broken per T-104 — so this control effectively pins to `cfg.max_sector_exposure_pct=0.30` regardless of regime.
4. **Engine C per-asset `max_weight=0.30`**: embedded in `target_weight` itself. Live.
5. **Wash-sale gate** (when sub-config enabled).
6. **LT-hold-defer** on exit signals (when sub-config enabled).
7. **Liquidity / min-notional / ADV clip**: always-on.

**That's it.** Every "the engine has a drawdown kill-switch / vol-target overlay / HMM-modulated risk_scalar / regime-conditional vol-target multipliers / ATR stop-widening" claim in the codebase is true at the level of CODE EXISTING, false at the level of CODE EXECUTING in prod.

## Part 2 — wiring-fix design proposal (the systematic answer)

### Principle: lift defensive modulations to PRE-PATH; apply via a path-aware multiplier

The pattern Path B uses (`risk_scaler` as a multi-source multiplier with a final `adjusted_risk_pct = base_risk_pct * risk_scaler`) is the right SHAPE — wrong LOCATION. The fix is:

1. **Compose all defensive multipliers OUT OF PATH B into a pre-path `_defensive_size_mult`** that starts at 1.0 and is reduced by each defensive feature.
2. **Apply `_defensive_size_mult` symmetrically to BOTH Path A (`target_notional *= _defensive_size_mult`) AND Path B (`risk_scaler *= _defensive_size_mult`).** This keeps Path B's behavior identical when both flags off, and makes the entire defensive surface Path-A-aware.
3. **Each lifted feature stays behind its own flag**, and a new "apply on Path A" flag is paired with each so the lift can be A/B-tested per feature without revealing all of Path B at once.

### Reference shape

```python
# PRE-PATH (after advisory pre-compute, before line 820 `if target_weight is not None`):
_defensive_size_mult: float = 1.0

# 1. Drawdown kill-switch (T-106 motivator, T-111 PoC):
if (
    self.cfg.drawdown_kill_switch_enabled
    and self.cfg.drawdown_kill_switch_apply_on_path_a
    and self.portfolio is not None
):
    dd_pct = self._safe_drawdown_pct()
    if dd_pct >= self.cfg.drawdown_halt_threshold:
        self._fail(ticker, "drawdown_halt_path_a")
        return None
    if dd_pct >= self.cfg.drawdown_degrade_threshold:
        _defensive_size_mult *= float(self.cfg.drawdown_degrade_scaler)

# 2. HMM-modulated advisory_risk_scalar (T-101 motivator):
#    Gated by a parallel `advisory_risk_scalar_apply_on_path_a` flag.
if (
    self.cfg.risk_advisory_enabled
    and getattr(self.cfg, "advisory_risk_scalar_apply_on_path_a", False)
    and advisory_risk_scalar != 1.0
):
    _defensive_size_mult *= float(advisory_risk_scalar)

# 3. Future: portfolio_vol_scalar already lives pre-path correctly;
#    consider folding it in too once T-055 is re-opened.
```

### Composition + double-count guard

The two LIVE Path-A advisory controls are `suggested_max_positions` and `suggested_exposure_cap`. These are **ABSOLUTE ceilings** (`min(suggested, cfg)`) — they take effect by REJECTING orders that would breach the cap. The proposed multiplier `_defensive_size_mult` is a **multiplicative scaler** that REDUCES `target_notional` before the order is built.

**They compose coherently because they act on different surfaces:**

- The advisory caps are evaluated against the *resulting* gross / position-count, AFTER the order would be applied. A halved `target_notional` reduces the resulting gross; the cap still holds.
- The drawdown degrade multiplier of 0.5 takes a hypothetical `target_notional=$40k` to `$20k`. The `effective_max_gross` check at line 1119 then sees `gross_after = (current_gross + $20k/equity) ≤ effective_max_gross` — still enforced. No double-cut.

**Conservative-tighten-wins is automatic.** Whichever (degrade scaler vs cap) is tighter ends up enforcing. The order can only get smaller; the cap can only get tighter. Both are reductive.

### Default-OFF + canon-identical (the silent-mismatch guard)

Every lifted feature gets a **paired flag** (parallel to the existing on/off flag):

| Feature | Existing flag | New "apply on Path A" flag |
|---|---|---|
| Drawdown kill-switch | `drawdown_kill_switch_enabled` (default False) | `drawdown_kill_switch_apply_on_path_a` (default False) ← T-111 PoC |
| HMM-modulated `risk_scalar` | `risk_advisory_enabled` (default True; the HMM modulation is inside advisory.py) | `advisory_risk_scalar_apply_on_path_a` (default False) ← not in T-111 PoC; future propose-first |

The pre-path block early-exits when EITHER flag is False, so:

- **Default state** (any flag off): `_defensive_size_mult = 1.0` → Path A `target_notional` unchanged → canon-md5 byte-identical to pre-T-111 main. **VERIFIED via T-111 PoC: 2022 OFF canon `0145c03a6496…` ≡ T-101 baseline.**
- **Both flags ON**: drawdown kill-switch + Path-A application active; canon DIFFERS as designed. **VERIFIED via T-111 PoC: 2022 ON canon `52202e510d27…`.**

### Determinism preservation

The pre-path block reads `self.portfolio.history[-1].get("current_drawdown_pct", 0.0)` — same source the legacy Path-B block uses. No new FP operation chains introduced; the multiplier is a single `float *=` op applied deterministically in source order. **T-111 PoC `--runs 3` PASS on default OFF, all canons `0145c03a6496…`.** T-099's long-window FP-determinism floor is preserved.

## Part 3 — drawdown kill-switch reference implementation (PoC)

### What changed

[`engines/engine_b_risk/risk_engine.py:88`](../../engines/engine_b_risk/risk_engine.py#L88) — new RiskConfig field:
```python
drawdown_kill_switch_apply_on_path_a: bool = False
```

[`engines/engine_b_risk/risk_engine.py:826-878`](../../engines/engine_b_risk/risk_engine.py#L826-L878) — pre-path block (~50 lines including comments) that:
- Reads `dd_pct` from `self.portfolio.history[-1].get("current_drawdown_pct", 0.0)`
- Returns `None` on halt (works on both paths since `return None` short-circuits `prepare_order` entirely)
- Sets `_drawdown_size_mult = drawdown_degrade_scaler` on degrade (default 0.5)

[`engines/engine_b_risk/risk_engine.py:884`](../../engines/engine_b_risk/risk_engine.py#L884) — Path A `target_notional` consumer:
```python
target_notional = (
    float(equity) * float(target_weight) * optimizer_weight
    * portfolio_vol_scalar * _drawdown_size_mult
)
```

**The legacy Path B block at `:940-979` is left untouched.** When the new pre-path block runs, it short-circuits HALT for Path A; on degrade, both Path A's `target_notional` and Path B's `risk_scaler` get multiplied by `_drawdown_size_mult`. No double-cut: Path A consumes `_drawdown_size_mult` once in the `target_notional` formula; Path B doesn't run in prod.

### Canon-md5 A/B (2022 default cell under `isolated()`)

| State | Flags | Canon | Action |
|---|---|---|---|
| OFF | `drawdown_kill_switch_enabled=False` AND `drawdown_kill_switch_apply_on_path_a=False` (defaults) | `0145c03a6496d9d823bc8e50b0635ec2` | ≡ T-101 baseline; **bitwise-identical INERT default verified** |
| ON | both flags True + (10/15 thresholds) | `52202e510d279d561eb0528a2177e9b0` | **DIFFERS** — Path-A degrade fires in 2022 (MDD -10.86% breaches the 10% degrade threshold) |

### Determinism

3 runs of 2022 with default OFF flags (post-T-111-code) → all `0145c03a6496d9d823bc8e50b0635ec2`. T-099 floor preserved.

### Tests

- `tests/test_contracts.py` 14 passed + 1 xfailed (no change from main; Layer 3a still resolves all source lines).
- The `_drawdown_size_mult` block is a single straight-line addition; it does not change any existing test expectations.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Complete dead-defensive-surface inventory + capability_ledger update | DONE — table above + 2 ledger rows updated/added |
| 2 | Confirmed which controls ARE live on Path A today | DONE — 3 live (advisory max_positions floor, advisory exposure_cap, sector_cap consumer-with-broken-producer) + post-path safety checks |
| 3 | Wiring-fix proposal: composes onto Path A `target_notional`, default-OFF flag, double-count guard, determinism-preserving | DONE — Part 2 above |
| 4 | (Optional) ONE drawdown-switch reference impl, default-OFF, canon-md5 A/B proof | DONE — PoC implemented; canon OFF=baseline, canon ON=differs, det 3/3 PASS |
| 5 | Audit doc + TASK_LEDGER row | DONE |
| 6 | NO prod-default change; NO multi-feature blind revive | DONE — `drawdown_kill_switch_apply_on_path_a=False` default; only the drawdown switch is lifted; HMM + others remain Path-B-dead pending separate propose-first |
| 7 | Branch pushed; NOT merged | (pushed at close) |

## Hard constraints — confirmed met

- [x] **PROPOSE-FIRST.** Parts 1-2 are diagnostic + design. Part 3 is a default-OFF flag-gated reference. No prod default change. Director gates any actual enable.
- [x] **No multi-feature blind revive.** Only the drawdown kill-switch (the cleanest case) is lifted. The HMM-`risk_scalar` and the legacy `risk_per_trade_pct` remain Path-B-dead and require their own separate propose-first dispatches.
- [x] No `data/governor/*` or `cockpit/dashboard/` edits.
- [x] Branch push only; director merges.

## Files

- **MOD** `engines/engine_b_risk/risk_engine.py` — added `drawdown_kill_switch_apply_on_path_a: bool = False` field + ~55-line pre-path block + 1-line `target_notional *= _drawdown_size_mult` on Path A. Net ~60 lines of new code (all gated default OFF).
- **MOD** `docs/State/capability_ledger.md` — drawdown kill-switch row updated to reflect T-106 finding + new T-111 PoC row added.
- **NEW** `docs/Audit/engine_b_defensive_wiring_sweep_t111_2026_06_05.md` — this audit.
- **MOD** `docs/State/TASK_LEDGER.md` — T-111 row appended.

## Surprises

1. **The dead-knob count is 7 / 10**, not the 3 we already knew about. After tracing each multiplier, the cascade includes `gate_conf`, `signal_strength`, `governor_weight`, `optimizer_weight` Path-B-copy, `portfolio_vol_scalar` Path-B-copy, ATR-stop-widening, `max_pos_value_pct`. All Path-B-only. **The Engine A → Engine B signal-quality modulation (signal_strength) does not modulate Path-A sizing.** The Engine A `risk_scalar` consumer at `signal_processor.py:543` (already documented in capability_ledger) is the only place that signal-quality feedback reaches the live path.
2. **Path B's `meta.update({"sizing_mode": "atr_risk", ...})` is a built-in canary.** If a prod trade log ever shows `sizing_mode=atr_risk`, target-weight emission upstream has silently broken. Worth a contract test.
3. **The SL/TP at line 1129-1135 ignores Path B's `vol_state`-adjusted `stop_mult`** and uses `self.cfg.atr_stop_mult` directly. So even the vol-state stop-widening is doubly dead — once because Path B doesn't run, and once because the post-path SL/TP block doesn't read Path B's local `stop_mult`. Even if Path B ran in prod, the widened stop wouldn't carry through.
4. **The legacy Path-B block doesn't need to be removed.** The T-111 PoC adds a Path-A lift without touching the legacy block. Both can coexist: when both flags are on, halt fires once (the pre-path block hits first on Path A); degrade applies to both `target_notional` (Path A) and `risk_scaler` (Path B); on Path A, `risk_scaler` is dead so the redundant multiplication is harmless. This means the lift is purely-additive and Path-B-A/B-testable separately.
5. **The capability_ledger now shows 2 Engine B rows for the drawdown kill-switch** — legacy Path-B-only (dead) and T-111 PoC Path-A lift (mode-gated). Future engine charters should distinguish "code exists" from "code executes in prod" — this is the failure mode the ledger surfaces.

## Status flag

**DONE — inventory shipped; 1-block design proposal shipped; drawdown PoC shipped with canon A/B proof. Director-gated A/B campaign required before any default-flag change. Per the proposal, lifting HMM `risk_scalar` is a SEPARATE propose-first dispatch, NOT bundled into T-111.**

## Forward-look

1. **Director A/B campaign for the drawdown PoC.** Same shape as T-106 (16-yr + 26-yr × arms off / default 10-15 / tight 7-12 / degrade-only / **NEW: Path-A-lifted variants**). The previous T-106 ran with Path B → dead → no signal. With the T-111 lift, halt should fire in 2008 + 2020 + 2022 26-yr cells and MDD should change. If MDD reduction ≥ 25% on 26-yr AND Sharpe ci_low not down, recommend flag-flip.
2. **Separate propose-first for HMM `risk_scalar` Path-A lift** (T-101 motivator). The PoC pattern transfers directly: add `advisory_risk_scalar_apply_on_path_a` flag, gate the multiplier, canon A/B, A/B campaign. **Do not bundle with T-111** — director needs each lift A/B-tested independently per the proposal's no-blind-revive constraint.
3. **Cleanup: archive or delete unused Path-B features** (`risk_per_trade_pct`, `max_pos_value_pct` Path-B-cap, ATR stop-widening). These can either be deleted (since they're confirmed dead) or moved into the lift pattern. **Out of T-111 scope.**
4. **Charter / health_check update.** The 7-of-10 dead defensive surface is a single-sentence finding that belongs in the Engine B charter and the health_check. **Out of T-111 scope** (separate doc-system task).
