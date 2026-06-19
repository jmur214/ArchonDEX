# T-223 — The systemic dead-gate guard: gate-dict keys ⊆ emitter vocabulary

**Date:** 2026-06-19 · **Agent:** A · **Branch:** `feature/dead-gate-contract-guard-t223`
**Lane:** measurement-integrity / contract-suite (autonomous-OK; test-only, no gate behavior changed).
**Status:** SHIPPED — 5 gate↔emitter pairings registered, full suite green (24 passed, 1 pre-existing xfail), guard proven to FAIL on the exact pre-fix T-216 bug.

## 1. Why (the disease)

The silent-vocabulary-mismatch family has bitten this project ≥ 10 times
(cockpit `peak_equity` slot, `hunt()` ticker=, env-config, T-055g v1 patch
keys, `Sharpe` vs `Sharpe Ratio`, T-088 dead risk-knob, the Layer-1/2 null-read
sweep). The latest instance — **T-216 g_regime** — is the GATE-DICT edition and
the motivation here:

> `_CONJ_REGIME_GATE` was keyed on a macro_regime-style vocab
> (`benign/cautious/stressed/...`) but the emitter it is fed by,
> `hmm_regime_label`, produces `{calm, cautious, crisis}`. Only `cautious`
> overlapped, so `_CONJ_REGIME_GATE.get(regime, 1.0)` returned the **1.0
> default on every non-cautious bar** → `g_regime ≡ 1.0` → the shipped/tested
> "3-way" conjunctive selector was really a **2-way** (`s_tech × g_fund`), and
> the audit's H0 was the 2-way's.

It was caught **by hand** in director review. The next one should be caught by
CI, not luck. Per CLAUDE.md's silent-mismatch discipline (the same rule the
Layer-1/2 contract suite enforces), this extends that suite to the gate-dict
class.

## 2. The contract

A **gate dict** = a (module- or class-level) dict mapping a CATEGORICAL string
vocabulary → a numeric multiplier (or a field-name that selects one), consumed
via `GATE.get(label, default)` where `label` comes from a PRODUCER (an emitter
that classifies the world into a fixed vocabulary).

**Invariant (Layer 4):** the gate's keys must be a **SUBSET** of the
vocabulary the emitter actually produces. A key no emitter emits is dead
weight; the catastrophic case (all keys foreign → gate ≡ default) is the
all-foreign extreme and fires the same assert. Where the gate is meant to be
EXHAUSTIVE (`full_coverage=True`), the inverse is also asserted (vocab ⊆ gate
keys) — catching a NEW emitter label the gate forgot, which would silently
default.

**Anti-rot:** the emitter vocabulary is resolved from the **producing source** —
a live import of the producer's own constant, or an AST scrape of its
`return "..."` literals — **never hardcoded in the test**. If the emitter's
vocabulary changes, the gate must track it or Layer 4 fires. The test cannot go
stale the way a hardcoded expectation would (that being the very disease).

Implementation: `tests/test_contracts.py` → `GATE_EMITTER_CONTRACTS` registry +
`test_layer4_gate_keys_subset_of_emitter_vocab` (parametrized) +
`test_layer4_registry_nonempty_and_seeds_t216_gate` (landmark). Runs in
`.github/workflows/contract_tests.yml` (the suite is already wired into CI on
every PR/push; Layer 4 is covered automatically).

## 3. Registered pairings (all currently CORRECT → green on main)

| # | Gate dict | Emitter (producing vocab) | Resolution | full_cov |
|---|-----------|---------------------------|------------|----------|
| 1 | `signal_processor.SignalProcessor._CONJ_REGIME_GATE` (A) | `regime_gate.REGIMES` = `{calm,cautious,crisis}` (`hmm_regime_label`) | live import const | yes |
| 2 | `vol_target._REGIME_SUMMARY_TO_MULTIPLIER_FIELD` (B) | `AdvisoryEngine._risk_to_summary` returns `{benign,cautious,stressed,crisis}` | AST-scrape return literals | yes |
| 3 | `advisory.MACRO_EDGE_AFFINITY` (E) | `_compute_macro_regime` → `MACRO_RULES` keys ∪ `{transitional}` | live import const + extra | yes |
| 4 | `advisory.NORMAL_WEIGHTS` (E) | `AXIS_RISK` axis vocabulary | live import const | no¹ |
| 5 | `advisory.STRESS_WEIGHTS` (E) | `AXIS_RISK` axis vocabulary | live import const | no¹ |

¹ Subset-only: `_compute_risk_score` iterates `weights.items()` and looks each
axis up via `AXIS_RISK.get(axis, {}).get(state, 0.5)` — a weight-map axis
absent from AXIS_RISK silently injects the 0.5 default (the dangerous
direction). An AXIS_RISK axis the weights omit is an intentional 0-weight, not
a silent default, so full_coverage is off for these two.

**#1 is the T-216 seed** — the bug this layer exists for. **#2 is its exact
sibling** (Engine B regime-multiplier ↔ Engine E regime_summary): currently
correct, but it is the gate T-216 *should* have mirrored and didn't; registered
so it can never drift the way #1 did.

## 4. Proof the guard bites

With the pre-fix bug re-introduced in-memory (gate re-keyed to the dead
`{benign,cautious,stressed}` macro-vocab against `regime_gate.REGIMES`), Layer 4
FAILS with the diagnostic:

```
[Layer 4 dead-gate contract violation] ...
  gate keys        : ['benign', 'cautious', 'stressed']
  emitter vocab    : ['calm', 'cautious', 'crisis']  (regime_gate.REGIMES)
  FOREIGN gate keys: ['benign', 'stressed']
  No emitter produces these labels → the consuming .get(label, default)
  silently swallows them → the gate is (partly or wholly) DEAD.
```

On the actual (fixed) main, all 5 pairings pass: **24 passed, 1 xfailed** (the
pre-existing Layer-3b strict tracker), `0.6–1.3s`.

## 5. Sweep — other categorical→multiplier gates found

The codebase was swept for `.get(<categorical-label>)` against module-level
str→numeric dicts. Findings:

- **Registered (5 above).** All currently correct; the value is locking them
  against future drift, plus the T-216 seed as a regression anchor.
- **`governor._regime_weights` (F) — surveyed, NOT registered.** Consumed at
  `governor.py:420` via `self._regime_weights.get(label)`. It is a
  **runtime-populated per-instance dict** (`_rebuild_regime_weights_from_tracker`
  from `regime_tracker`), not a static constant — a static introspection test
  cannot pin it. Lower structural risk: its keys and the lookup `label` both
  derive from the macro_regime label source, so they co-vary. Flagged here as
  the one remaining gate the static suite is blind to; the right guard for it
  would be a producer-side TypedDict / runtime assert (same gap as the
  still-deferred Layer 3 signal-dict contract).
- **No NEW dead gate found.** Unlike the T-090 sweep (which found 7 live null-
  read bugs), every static gate dict in the sweep is currently vocabulary-
  correct. The disease was caught at the source (T-216 fix) before it spread.

## 6. Adding a pairing (for the next gate)

Append to `GATE_EMITTER_CONTRACTS`:
- `gate`: `{module, attr}` for a module-level dict, or `{module, cls, attr}`
  for a class attribute (no instantiation needed).
- `emitter`: `{const_module, const_attr}` to import the producing vocab
  (tuple/set/dict→keys; optional `extra` set for literal fallbacks), OR
  `{scrape_file, scrape_func}` to AST-scrape `return "..."` literals.
- `full_coverage`: `True` if the gate must be exhaustive over the vocab.

The bar: a gate whose keys don't match its emitter is a CI failure. No
allowlist — a gate key no emitter emits is never legitimate (unlike a dead
*config* key, which can sit harmlessly in JSON; a dead *gate* key actively
mis-routes live logic).

## 7. Compliance

- Test-only + CI-comment + this audit; **zero gate behavior changed**
  (`git diff` touches only `tests/test_contracts.py`,
  `.github/workflows/contract_tests.yml`, this doc).
- Runs in the existing `contract_tests.yml` CI gate.
- Branch push only; director merges.
