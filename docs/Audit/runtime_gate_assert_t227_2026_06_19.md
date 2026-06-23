# T-227 — Close the last dead-gate gap: runtime assert on `_regime_weights`

**Date:** 2026-06-19 · **Agent:** A · **Branch:** `feature/runtime-gate-assert-t227`
**Lane:** measurement-integrity / contract guard (Engine F governance — additive defensive assert, autonomous-OK; NOT propose-first).
**Status:** SHIPPED — runtime assert + 5 tests green, full governor/regime/contract suites green (43 passed, 1 pre-existing xfail), doc_lint exit 0. **Zero weight-logic touched; canon provably unaffected.**

## 1. The gap (from T-223)

The T-223 static Layer-4 guard asserts every **module-level** categorical
gate dict's keys ⊆ its emitter vocabulary. It registered 5 gates but flagged
ONE it structurally cannot reach: `StrategyGovernor._regime_weights` — a
**runtime-built per-instance dict** (`_rebuild_regime_weights_from_tracker`),
invisible to static introspection. This task closes that last gap with one
targeted runtime assertion. Scope: this gate only — NOT the broader deferred
Layer-3 signal-dict contract.

## 2. The contract (consumer-anchored)

`get_edge_weights()` (`governor.py`) resolves regime weights **only** by
`macro_regime['label']`:

```python
macro = regime_meta.get("macro_regime")
label = macro.get("label", "") if isinstance(macro, dict) else macro
regime_w = self._regime_weights.get(label)        # ← the ONLY lookup
```

There is **no forward_stress fallback in the consumer**. Therefore every key
in `_regime_weights` must be a member of the macro_regime vocabulary, or that
key is **unreachable** — a silently-dead gate entry (the T-216 `g_regime`
class). The vocabulary is `MACRO_RULES` keys ∪ `{"transitional"}` (the literal
fallback in `AdvisoryEngine._compute_macro_regime`) — **the same set the static
Layer-4 guard checks `MACRO_EDGE_AFFINITY` against**, so static and runtime
guards share one definition of "valid regime label."

The assert is **consumer-anchored**: it is correct regardless of what the
producer (the trade-log `regime_label` column, sourced in `policy.py` from
`macro['label']` with a forward_stress fallback) writes. If the producer ever
writes a forward_stress state (`calm/cautious/stressed/panic`) into a key, that
key cannot be retrieved by the macro lookup → the assert surfaces it.

## 3. Implementation

`StrategyGovernor._assert_regime_weight_keys_reachable()`, called once at the
end of `_rebuild_regime_weights_from_tracker()` (the build site). Behavior:

- **Empty dict → return immediately.** No false-fire when
  `regime_conditional_enabled=False` (the prod default — `config/governor_settings.json`)
  or when no trades were recorded.
- **`foreign = keys − (MACRO_RULES ∪ {transitional})`; empty → return.**
- **Severity by path** (CLAUDE.md `[NN-FAIL-CLOSED]`):
  - `core.measured.is_measured()` True (cloud / anchor / hermetic-strict) →
    `raise MeasurementHalt` → maps to the census-FAIL non-zero exit family. A
    real vocab mismatch in a measured run IS the dead-gate bug and must surface.
  - otherwise (live / paper / local / test) → `log.warning(...)` only — a
    defensive check must never break the live governor path.

Additive only: the method reads `_regime_weights` and returns/raises/logs; it
does **not** touch the weight LOGIC. Lazy imports (`MACRO_RULES`,
`is_measured`/`MeasurementHalt`) keep module load cheap and avoid import-order
risk.

## 4. Canon-safety

In prod, `regime_conditional_enabled=false` → `_rebuild_regime_weights_from_tracker`
is never called (gated in both `__init__` and `update_from_trades`), so the new
method never even runs on the canonical path. Even if reached, an empty dict
returns immediately. The assert adds zero behavior to any canonical/measured
run that isn't already a dead-gate bug → **no canon-md5 change is possible.**

## 5. Tests (`tests/test_governor_regime_weight_gate_t227.py`, 5, all green)

(a) **fires on mismatch:**
- `test_measured_run_HALTS_on_foreign_regime_key` — `ARCHONDEX_MEASURED=1` +
  forged `{"stressed": ...}` → `MeasurementHalt` (names the key + "UNREACHABLE").
- `test_live_path_WARNS_not_halts_on_foreign_regime_key` — same mismatch,
  not-measured → WARNs, no raise.

(b) **does NOT false-fire:**
- `test_empty_gate_does_not_fire` — empty dict, even measured → silent.
- `test_valid_macro_keys_do_not_fire` — all `MACRO_RULES ∪ {transitional}`
  keys, even measured → silent.
- `test_consumer_vocab_matches_macro_rules` — guard-the-guard: every
  `MACRO_RULES` label is accepted (vocab tracks the emitter, can't rot).

Full regression: `test_governor_reset` + `test_contracts` + `test_regime_gate_t217`
+ this file = **43 passed, 1 xfailed** (pre-existing Layer-3b tracker). doc_lint
exit 0.

## 6. Note (no rabbit hole — per the LOW-URGENCY guardrail)

The trade-log `regime_label` column WRITER was not exhaustively traced; the
gate is disabled in prod and the consumer-anchored invariant is correct
regardless of producer, so a full producer trace was unnecessary. If a future
measured run enables the gate and HALTs here, that HALT is the producer/consumer
vocab mismatch surfacing — exactly what the guard is for.

## 7. Compliance

- Engine F additive defensive assert (governance — not propose-first); weight
  LOGIC untouched. ✓
- `[NN-FAIL-CLOSED]` severity split (measured HALT / live WARN). ✓
- No false-fire when disabled/empty (prod default). ✓
- `git diff` = `governor.py` (additive method + 1 call) + the new test. ✓
- Branch push only; director merges. ✓
