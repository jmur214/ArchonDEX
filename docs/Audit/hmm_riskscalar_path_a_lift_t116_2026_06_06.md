# T-116 — HMM-modulated `risk_scalar` Path-A lift (PROPOSE-FIRST PoC)

**Date:** 2026-06-06
**Agent:** C (worktree `trading_machine-agent-c`, branch `feature/hmm-riskscalar-path-a-lift-t116`)
**Status:** PROPOSE-FIRST. Default-OFF gated PoC + canon proof + double-count design analysis. **No prod-default change. No full A/B run** (that is a separate director-gated dispatch).
**Sibling of:** T-111 (`docs/Audit/engine_b_defensive_wiring_sweep_t111_2026_06_05.md`) — the drawdown kill-switch Path-A lift. T-111 explicitly deferred this `risk_scalar` lift as a *separate* propose-first task so each dead-defensive control is reviewed and A/B-tested one at a time (no blind bulk-revive).

---

## 1. Headline

The Engine-E advisory `risk_scalar` (the HMM-modulated de-gross validated in T-101) is consumed **only** in the legacy Path-B `else:` block of `risk_engine.prepare_order` (`risk_scaler *= advisory_risk_scalar`, `risk_engine.py:987`). Production sizing runs **Path A** (`target_weight`), which never reaches Path B — so the HMM's risk-off signal has **never affected production order sizing**. T-101 proved exactly this: flipping `hmm_enabled` on changed nothing, because the only Engine-B consumer of the HMM-modulated scalar is dead code in prod.

This PoC mirrors T-111's shape: a new default-OFF flag `advisory_risk_scalar_apply_on_path_a` that, when enabled, applies the same `advisory_risk_scalar` value Path B uses to Path A's `target_notional` multiplicatively.

**Proven inert by default; proven to bite when ON:**

| Run | Flag state | Canon md5 (2022 cell) | Sharpe |
|-----|-----------|------------------------|--------|
| OFF | `advisory_risk_scalar_apply_on_path_a=False` (default) | `0145c03a6496d9d823bc8e50b0635ec2` | 0.464 |
| ON  | flag `True` (+ `risk_advisory_enabled=True`, already prod-default) | `9ea576c912672bc94ad539041a703943` | −0.194 |

OFF canon is **bitwise-identical to the T-101 / T-111 baseline** (`0145c03a…`). Determinism `--runs 3` on default-OFF: 3/3 identical, Sharpe range 0.0000 (T-099 floor preserved).

---

## 2. The dead-path problem (re-confirmed)

`risk_engine.prepare_order` splits at the `target_weight` check (`risk_engine.py:888`):

- **Path A (production)** — `target_weight is not None`. Computes
  `target_notional = equity · target_weight · optimizer_weight · portfolio_vol_scalar · _drawdown_size_mult` (`:902-905`, the last factor added by T-111) and sizes from that. **`advisory_risk_scalar` is absent here.**
- **Path B (`else:`, legacy ATR-risk)** — never reached in prod. Builds `risk_scaler` as a multi-source product including `risk_scaler *= advisory_risk_scalar` (`:987`).

`advisory_risk_scalar` is extracted once at `:737-753` (defaults to 1.0; set to `advisory['risk_scalar']` only when an advisory is present **and** `risk_advisory_enabled`). It is the same value Engine E's `advisory.py:195` produces: `risk_scalar = clip(max(0.3, 1.2 − risk_score·0.9), 0.3, 1.2)`, then HMM-confidence-modulated (`:209`). In the 2022 stressed cell, the live advisory emits `risk_scalar = 0.728` — a real 27% de-gross that Path A currently ignores.

**Live vs dead, precisely (per T-100/T-101):**
- `suggested_max_positions` → `effective_max_positions` (`:743`) → enforced as a **count ceiling** at `:763`. **LIVE on Path A.**
- `suggested_exposure_cap` → `effective_max_gross` (`:748`) → enforced as a **gross-notional ceiling** at `:1191`. **LIVE on Path A.**
- `risk_scalar` → `advisory_risk_scalar` (`:753`) → **DEAD on Path A** (Path-B-only multiplier). ← this PoC lifts it.

---

## 3. The lift (mirror of T-111, not a new shape)

Three edits to `engines/engine_b_risk/risk_engine.py`, all gated default-OFF:

1. **New config field** `advisory_risk_scalar_apply_on_path_a: bool = False` (placed directly after T-111's `drawdown_kill_switch_apply_on_path_a`).
2. **Pre-path block** computing `_advisory_risk_scalar_mult` (mirrors the `_drawdown_size_mult` block): `= advisory_risk_scalar` when both `advisory_risk_scalar_apply_on_path_a` **and** `risk_advisory_enabled` are True, else `1.0`.
3. **One factor** appended to Path A's `target_notional`: `… * _drawdown_size_mult * _advisory_risk_scalar_mult`.

Path B (`:987`) is **untouched**. No new `meta` keys were added (a new `trades.csv` column would break the canon-identical requirement — canon is computed over `trades.csv`, per T-088). Debug prints are gated behind `is_debug_enabled("RISK")` (off in canon runs).

**Pairing rationale** (mirrors T-111): gating on `risk_advisory_enabled` as well as the new flag means the lift cannot activate while advisory consumption is globally off, keeping the director-gated A/B clean.

---

## 4. Double-count analysis (the load-bearing deliverable)

The brief's core question: Path A already consumes the advisory's `suggested_exposure_cap` + `suggested_max_positions` floors. Adding a `risk_scalar` de-gross on top — all three driven by the **same** Engine-E `risk_score` — could double-cut in crisis. Does it compose coherently or double-count?

There are **three** potential double-count vectors. I checked all three.

### 4a. vs Engine A's own `risk_scalar` application — WASHES OUT (no double-count)

`signal_processor.py:546-549` already does `norm *= risk_scalar` — but **only in stressed/crisis** and **uniformly across all tickers**. The question is whether that propagates into `target_weight`:

- **Default `adaptive` allocator** (`policy.py:230-233`): `raw_w = (abs(s)/vol) / Σ(abs(s)/vol) · sign(s)`. A uniform shrink `s → k·s` factors out of both numerator and the `Σ` denominator → **k cancels**. `target_weight` carries no `risk_scalar`.
- **Production `mean_variance` allocator** (prod config sets `mode: "mean_variance"`; `optimizer.py:53`): the optimizer enforces a **full-investment budget constraint `Σw = 1.0`**. Total gross is pinned at 1.0 regardless of a uniform μ scale; risk_scalar only marginally reshuffles *relative* weights via the fixed cost-penalty term, and that is swamped by the `[−0.1, 0.25]` clip (`policy.py:194`). **No gross de-grossing propagates.**

**Conclusion:** across both allocators the uniform `risk_scalar` shrink is **absorbed by weight normalization / the budget constraint**. Applying `risk_scalar` in Engine-B Path A is therefore the **first and only** gross application of the scalar to production sizing — *not* a re-application of an already-applied de-gross.

> Buried-capability note (for director, not in-scope to fix): the corollary is that Engine A's stressed/crisis `risk_scalar` brake at `signal_processor.py:549` is itself **largely inert on total gross** under both allocators — another buried defensive control in the "41 buried capabilities" family. Flagged, not touched.

### 4b. vs the LIVE `suggested_exposure_cap` (gross ceiling) — COMPOSES as min(), NO double-cut

`risk_scalar` shrinks each order's `target_notional`; the gross-exposure guard (`:1191`) then rejects any order that would push **total** gross over `effective_max_gross`. Because the cap is an **absolute ceiling enforced *after* the multiplier**, the composition on total gross is:

```
final_gross = min( scaled_intended_gross , effective_max_gross )   # "more conservative wins"
```

It is **min, not product** — there is no `cap × scalar` outcome. (Identical to T-111's argument for `_drawdown_size_mult`, that doc §"Default-OFF + canon-identical".) Two regimes:

- **Cap binds (deep crisis):** the cap pins gross; `risk_scalar` is largely **redundant** on total gross — but it improves **intra-cap diversification** (more, smaller names share the capped budget instead of the first tickers in iteration order eating it). A feature, not a double-cut.
- **Cap slack (graduated middle — e.g. the 2022 cell, where `exposure_cap = 0.95` but Engine C targets ~50% gross):** `risk_scalar` (0.728) provides the *only* graduated de-gross the slack cap cannot. **This is the lift's actual value-add.**

> Note: `suggested_exposure_cap` is *also* applied as a weight-scaler in Engine C (`policy._apply_exposure_cap`, `:247`) in addition to the Engine-B gross gate — so the cap is already layered twice. The `risk_scalar` multiplier sits alongside, still bounded by the min() ceiling.

### 4c. vs the LIVE `suggested_max_positions` (count ceiling) — ORTHOGONAL AXIS; the one genuine compounding vector

`max_positions` caps **count**; `risk_scalar` shrinks **per-name size**. These are different axes. In the regime where the gross cap is **slack** but **both** the count-floor and the size-multiplier bind (exactly the 2022 cell: cap 0.95 slack, `max_positions=7` binding, `risk_scalar=0.728` binding), total gross ≈ `count_limit × per_name_size × risk_scalar` → **multiplicative compounding across two distinct controls, all keyed to the same `risk_score`.**

This is **defense-in-depth across two axes**, *not* a same-lever arithmetic double-count — but because all three controls move together with `risk_score`, in crisis they **all tighten at once**, so the book can de-gross **more than any single control's calibration intended**. This is the one hazard that T-111's drawdown lift did **not** have: drawdown% is an **independent** signal, uncorrelated with `risk_score`, so it could never co-fire this way.

### 4d. Proposed resolution ("more conservative wins, not multiply both")

On the **gross dimension** the composition is *already* "more conservative wins" (the cap is a min-ceiling — §4b), so the multiplier shape is safe there and no code change is needed. The residual hazard is the **count × size** compounding in the cap-slack regime (§4c). The PoC's job is to *expose and quantify* the lever, not pre-solve calibration. The **director-gated A/B must measure crisis-window realized gross** and choose:

1. **Accept** the deeper crisis de-gross as intended defense-in-depth (most likely fine — crisis *under*-exposure is rarely the failure mode for this book; the binding risk is the opposite), **or**
2. If the A/B shows crisis gross collapsing below a floor that starves the recovery, apply one of:
   - **Floor the Path-A scalar** (e.g. clip `_advisory_risk_scalar_mult` to `[0.5, 1.2]`) so size and count can't both bottom out, **or**
   - **Relax `max_positions` tightening** when this flag is on (let the size-multiplier carry the crisis de-gross, the count-floor carry diversification), **or**
   - **Cleanest principled fix:** make the de-gross "more conservative wins" against the exposure-cap rather than multiplying — i.e. fold `risk_scalar` into the gross ceiling (`effective_max_gross = min(effective_max_gross, scalar · max_gross)`) so a single min() governs total gross and the count-floor stays orthogonal. This eliminates the count×size compounding by construction.

**Recommendation:** ship the multiplier PoC as-is (mirrors T-111, maximally reviewable, default-OFF), and treat the **count×size crisis-gross floor as the single must-measure item** before any prod flip. Do **not** auto-enable.

---

## 5. Evidence

### Canon A/B (2022 default cell, `python -m scripts.run_isolated --task q1 --year 2022`, prod config)
| State | Config | Canon md5 | Verdict |
|-------|--------|-----------|---------|
| OFF | defaults | `0145c03a6496d9d823bc8e50b0635ec2` | ≡ T-101/T-111 baseline — **bitwise-inert default verified** |
| ON | `+ advisory_risk_scalar_apply_on_path_a: true` in `risk_settings.prod.json` | `9ea576c912672bc94ad539041a703943` | **DIFFERS** — risk_scalar 0.728 de-grosses Path A target_notional in 2022 stressed |

The new key was **not** in the loader's "ignoring unknown config key" list (it is a valid `RiskConfig` dataclass field → propagates; the T-088 unknown-key filter accepts it). Config was reverted after the ON run — working tree leaves prod default OFF.

### Determinism (default-OFF, `--runs 3`)
3/3 runs → `0145c03a6496d9d823bc8e50b0635ec2`, Sharpe `[0.464, 0.464, 0.464]`, range 0.0000. **PASS.** The lift is a single deterministic `float *=` in source order; no new FP chains. T-099 long-window floor preserved.

> The ON Sharpe (−0.194 vs OFF 0.464) is a **single-cell** datum — de-gross happened to hurt in 2022's choppy momentum-short book. It is **not** a verdict and is consistent with the project's "defensive de-gross is regime-conditional" findings. The director-gated multi-window A/B decides.

---

## 6. What the director/user must review before the lift A/B

1. **Confirm the multiplier shape** (vs the §4d.2.iii "fold into the gross ceiling" alternative). The PoC ships the multiplier to match T-111; if the director prefers the single-min() design up front, that is a ~3-line change.
2. **A/B campaign design** — same windows as T-106/T-111 (16-yr + 26-yr), arms: off / scalar-on / scalar-on-with-floor `[0.5,1.2]`. **The A/B must log per-cell realized crisis-window gross** to resolve the §4c count×size compounding question.
3. **Composition with T-111's drawdown lift** — if both flags are eventually enabled, `target_notional *= _drawdown_size_mult * _advisory_risk_scalar_mult` stacks two multipliers. Drawdown% and risk_score are partly correlated in crisis; the A/B should include a both-on arm.
4. Only after the A/B clears (crisis-gross floor acceptable **and** Sharpe ci_low not degraded, per CLAUDE.md `[NN-SHARPE-CI]` CI-aware gating) should any prod flag flip be proposed.

---

## 7. Acceptance checklist

- [x] New flag `advisory_risk_scalar_apply_on_path_a` (default False) + Path-A lift mirroring T-111's shape
- [x] Canon-md5 A/B: OFF == current-main baseline (`0145c03a…`, bitwise), ON differs (`9ea576c9…`)
- [x] Determinism `--runs 3` PASS on default-OFF (`0145c03a…` ×3, range 0.0000)
- [x] Double-count analysis: Engine-A propagation (washes out), exposure-cap (min/compose), max-positions (orthogonal count×size compounding) + proposed resolution
- [x] Audit doc (this file) + proposed ledger row in outbox
- [x] NO prod-default change (config reverted); NO full A/B (design+PoC only); branch pushed NOT merged

## 8. Files modified
- **MOD** `engines/engine_b_risk/risk_engine.py` — `+advisory_risk_scalar_apply_on_path_a: bool = False` field (~20-line comment) + ~12-line pre-path `_advisory_risk_scalar_mult` block + 1 factor on Path A `target_notional`. All gated default-OFF; Path B untouched.
- **NEW** `docs/Audit/hmm_riskscalar_path_a_lift_t116_2026_06_06.md` (this file).
