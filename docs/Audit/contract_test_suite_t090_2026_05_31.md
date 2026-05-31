# T-2026-05-31-090 — Contract-test suite: permanent guards against the silent-mismatch bug family

**Date:** 2026-05-31
**Branch:** `feature/contract-test-suite-t090`
**Worker:** Agent B

## Verdict — SUITE CAUGHT all 3 audit-flagged bugs PLUS surfaced 7 NEW ones

Current state of `tests/test_contracts.py` against `main`:

| Test | Status | Bug caught |
|---|---|---|
| Layer 1 — AlphaConfig vs alpha_settings.prod.json | PASS | — |
| Layer 1 — AlphaConfig vs alpha_settings.dev.json | PASS | — |
| Layer 1 — RiskConfig vs risk_settings.prod.json | **FAIL** | [3] T-088 target — silently-dropped risk_per_trade + max_position_value + 5 more |
| Layer 1 — RiskConfig vs risk_settings.dev.json | **FAIL** | same as prod (dev mirrors) |
| Layer 1 — GovernorConfig vs governor_settings.json | PASS | (max_turnover_per_month allowlisted as legit alias) |
| Layer 1 — PortfolioPolicyConfig vs portfolio_settings.json | PASS | (nested sub-config dicts allowlisted) |
| Layer 2a — producer constant in sync with source | PASS | meta-check |
| Layer 2b — consumer-read ⊆ producer-emit | **FAIL** | [1] Total Trades + [2] Sortino Ratio + **7 NEW BUGS** (see below) |
| Layer 2c — expected-violations documented | PASS | TODO landmark |
| Layer 3 — cross-engine signal-dict contract | PASS | DEFERRED — landmark in test file |

**Currently: 3 failures / 7 passes.** The 3 failures are all real bugs;
they are EXPECTED to fire pre-T-088 and will go green when T-088 merges
(for the Layer 1 risk config) and after the new bugs below are fixed in
follow-up dispatches (for Layer 2b).

## NEW silent-mismatch bugs surfaced (FLAGGED, NOT fixed — per dispatch hard constraint)

Beyond the 3 audit-flagged bugs (Total Trades, Sortino Ratio, risk config),
my consumer scan found **7 additional silent-mismatch sites** the audit
missed:

| # | Consumer-read key | Producer emits | Sites |
|---|---|---|---|
| N1 | `PSR` | (not in cockpit `_compute_summary`) | `core/observability/run_registry.py:117` |
| N2 | `Sharpe` (vs `Sharpe Ratio`) | `Sharpe Ratio` | `scripts/run_vol_target_arms.py:77`, `scripts/run_deterministic.py:167` |
| N3 | `Max Drawdown` (no `%`) | `Max Drawdown (%)` | `scripts/walk_forward_phase210.py:94` |
| N4 | `Max Drawdown%` (no parens) | `Max Drawdown (%)` | `scripts/run_vol_target_arms.py:79` |
| N5 | `Win Rate` (no `%`) | `Win Rate (%)` | `scripts/walk_forward_phase210.py:95` |
| N6 | `CAGR_pct` (snake_case) | `CAGR (%)` | `scripts/run_vol_target_arms.py:78` |
| N7 | `MDD_pct` (abbreviated) | `Max Drawdown (%)` | `scripts/run_vol_target_arms.py:79` |

All 7 read NULL silently. Each consumer's downstream field is corrupted.
None of these were called out in the 2026-05-31 silent-bug audit — the
contract suite catches MORE than what hand-grep found.

Per dispatch hard constraint ("New bug surfaced → FLAG in outbox, don't
fix"), I have not patched any of these. Recommended follow-up: a single
"key-rename sweep" dispatch that aligns each consumer to the canonical
producer key (or augments the producer to emit the read name).

## Layers implemented

### Layer 1 — config-key ⊆ dataclass-field contract

Parametric over 6 (json_path, dataclass) pairs. Each test:
1. Loads JSON.
2. Introspects the dataclass via `dataclasses.fields`.
3. Asserts every JSON key maps to a real field or is in an explicit
   `known_aliases` set.

Allowlists are MINIMAL and documented inline:

- `AlphaConfig`: `edge_params`, `fill_share_cap`, `metalearner` (legit
  sub-config maps consumed by other components).
- `RiskConfig`: NO aliases. Every key must be a real field. This is
  what makes the suite catch T-088's bug.
- `GovernorConfig`: `max_turnover_per_month` (downstream throttle).
- `PortfolioPolicyConfig`: `lt_hold_preference`, `portfolio_optimizer`,
  `wash_sale_avoidance` (nested sub-config dicts).

Failure message names the JSON file, dataclass module/class, and every
offending key. Reader can act on the diagnostic immediately.

### Layer 2 — performance-summary producer/consumer key contract

Three sub-tests:

- **Layer 2a — producer constant sync check**: scrapes
  `cockpit/metrics.py:_compute_summary()` for its key literals, asserts
  the `PRODUCER_SUMMARY_KEYS` constant in the test file matches. Keeps
  the test honest when the producer evolves.
- **Layer 2b — consumer-read ⊆ producer-emit**: walks `scripts/` +
  `core/observability/`, captures every `.get("...")` / `_safe_float(...)`
  pattern, asserts each key is in the producer set OR a documented alias.
- **Layer 2c — expected-violations documented**: a TODO landmark
  asserting the `EXPECTED_PRE_T088_VIOLATIONS` set exists so the
  reviewer remembers to remove it when T-088 closes the audit-flagged
  bugs.

Consumer-scan patterns are conservative: only `summary.get`, `perf.get`,
`perf_summary.get`, `stats.get`, and `_safe_float(perf, "key")` are
captured. This bounds false positives (e.g., random `.get()` calls on
unrelated dicts won't trigger).

### Layer 3 — cross-engine signal-dict contract — DEFERRED

The Engine A → Engine B/C per-ticker signal dict is shaped at runtime
based on per-bar conditions (edge triggers, regime context, meta-
injection). Static analysis misses dynamic key construction; verifying
this contract requires either:

(a) Defining a `TypedDict` / Pydantic model on the producer (Engine A)
    — propose-first since it touches engine logic.
(b) Wiring a runtime assertion into the producer's emit point (Engine A
    end-of-bar). Permanent enforcement at every bar.
(c) A 1-day micro-backtest in this test file with mocked data + per-bar
    key inspection.

Recommended: **(b)**, deferred to a separate dispatch. A landmark test
`test_layer3_cross_engine_signal_dict_contract_deferred` lives in the
file so the deferral isn't forgotten — when (b) lands, replace the
test body with the actual assertion.

## What each contract WOULD'VE caught historically

The 2026-05-31 silent-bug audit (`docs/Audit/silent_bug_audit_2026_05_31.md`)
plus the 7 NEW bugs found here trace back to:

| Bug | Layer that would have fired | Time saved per the audit |
|---|---|---|
| T-055g v1 patch-keys (silently-dropped vol target overlay multipliers) | Layer 1 | ~3-4 hr of campaign re-run |
| Cockpit `peak_equity` slot bug (T-030 → T-034) | Layer 1 alignment + a column-name guard (not implemented yet — flag for follow-up) | ~2 days of bug-hunting |
| hunt() ticker= (T-054) | Engine A → Engine D signal-shape contract (Layer 3, deferred) | ~3-4 days of investigation |
| risk_per_trade vs risk_per_trade_pct (T-088, current) | Layer 1 (LIVE — catching it right now) | indefinite |
| `Sharpe Ratio` vs `Sharpe` (mode_controller fallback) | Layer 2b would've caught the abbreviated form | minor |
| run_registry `Sortino Ratio` (null column every run) | Layer 2b | every measurement lost a sortino value |
| 13 harnesses `Total Trades` (null in every JSON) | Layer 2b | all A/B JSONs missing trade count |
| NEW 7 bugs (PSR, Sharpe, Max Drawdown variants, Win Rate, CAGR_pct, MDD_pct) | Layer 2b (caught now) | every measurement using these scripts had silently null fields |

## Known-alias allowlist mechanism

The dispatch required explicit documentation of how aliases are managed
so legit legacy aliases don't false-positive without being noticed.

Mechanism:
- Layer 1: per-contract `known_aliases: Set[str]` in the parametric
  matrix. Inline code comment justifies each alias.
- Layer 2: three module-level constants:
  - `PRODUCER_SUMMARY_METRICS_EXTRA_KEYS` — keys in `summary_metrics()`
    only, not in `summary()`. Currently `{"Trades"}`.
  - `KNOWN_DOWNSTREAM_AUGMENT_KEYS` — keys added by callers AFTER the
    producer returns. Currently `{"timestamp", "run_id"}`.
  - `KNOWN_CONSUMER_ALIAS_KEYS` — defensive lowercase fallbacks that
    are intentional. Documented inline.
- `EXPECTED_PRE_T088_VIOLATIONS` — explicit set documenting which keys
  WILL fire pre-T-088. Test `test_layer2c_expected_pre_t088_violations_documented`
  exists to anchor a TODO so the reviewer removes the set when T-088 lands.

Every allowlist entry should have a one-line justification comment
adjacent to where it's defined. KEEP THE ALLOWLIST MINIMAL — each
entry is a permission slip.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | `tests/test_contracts.py` with Layers 1 + 2 + Layer 3 landmark | **PASS** |
| 2 | Parametrized, assert invariants (not hardcoded values) | **PASS** |
| 3 | Each failure names key + producer + consumer | **PASS** |
| 4 | Run NOW; report currently-failing contracts | **PASS** — 3 fails (RiskConfig × 2 + Layer 2b); cross-refs the audit + flags 7 NEW bugs |
| 5 | Explicit known-alias allowlist mechanism | **PASS** — documented above + inline justifications |
| 6 | Audit doc | **PASS** (this) |
| 7 | Branch push only; director merges AFTER T-088 lands | **PASS** |

## Hard constraints — confirmed met

- [x] TEST CODE ONLY. NO engine logic, dataclass, or config changes.
- [x] No edits to Engine B / live_trader / risk config files (A's
  domain).
- [x] Layer 1/2 are STATIC (introspection + JSON parse + regex scan).
  No backtest run. Total runtime: <1 second.
- [x] Tests live in `tests/`, runnable via `pytest`.
- [x] NEW bugs flagged in this doc + outbox; NOT fixed.

## Files

- **NEW** `tests/test_contracts.py` — 10 parametric tests
  implementing Layers 1 + 2 + Layer 3 landmark. ~440 lines.
- **NEW** `docs/Audit/contract_test_suite_t090_2026_05_31.md` (this).

## CI runtime

`tests/test_contracts.py` runs in **<1 second** end-to-end. Cheap
enough to gate every PR + add to a fast-feedback CI tier.

## Surprises

1. **Layer 2b found 7 NEW silent-mismatch bugs the hand-grep audit
   missed.** This is the strongest justification for the suite: the
   audit looked at well-known sites (the 13 harnesses, run_registry);
   the regex-based scan covers everything in scripts/, including
   ad-hoc one-off scripts (run_vol_target_arms.py, walk_forward_phase210.py,
   run_deterministic.py) that no one was checking.

2. **PSR violation is in run_registry** — same file as the audit-flagged
   Sortino Ratio violation. The hand audit caught one read but not the
   adjacent one. The regex sweep catches all sibling reads
   automatically.

3. **Two abbreviation patterns are widespread** — snake_case
   (`CAGR_pct`, `MDD_pct`) and stripped-parens (`Max Drawdown` vs
   `Max Drawdown (%)`). These are convenience aliases that drifted
   from the producer; the suite forces the convention back.

4. **GovernorConfig + PortfolioPolicyConfig passed** because their
   "extras" are nested sub-config dicts consumed by separate loaders.
   If a future PR moves consumption back into the parent dataclass,
   the allowlist would need to shrink correspondingly — the inline
   comments make that audit trail traceable.

5. **Layer 3 is genuinely hard to do statically.** The
   `signal["meta"]["edges_triggered"]` shape is built per-bar in
   signal_processor.py via dict-comp over runtime edge state.
   Proposing a TypedDict on the producer + runtime assertion is the
   right path; doing it post-hoc via static analysis would chase
   false positives forever.

## Forward-look — when T-088 lands

When A's T-088 merges + the Layer 2b NEW bugs are fixed:
1. The 3 currently-failing tests all go green.
2. Remove `EXPECTED_PRE_T088_VIOLATIONS` from the test file (the
   landmark test `test_layer2c` is the TODO anchor).
3. Wire `tests/test_contracts.py` into CI via the
   `feature-foundry-gate` workflow as the model.
4. After CI gates the contract, the silent-mismatch family is
   structurally impossible to merge — the bug-hunt cost goes from
   "found by accident weeks later" to "blocked at PR open."

## Follow-up dispatch candidates

1. **Key-rename sweep** to fix the 7 NEW bugs found by Layer 2b.
   Trivial: each is a 1-line consumer rename or a producer-augment
   to emit the read name.
2. **Layer 3 producer-side TypedDict** for the Engine A → B/C signal
   dict (propose-first, Engine A touch).
3. **Layer 1 extension** to cover BacktestParams, MetaLearnerSettings,
   any other dataclass with a JSON consumer not in this PR's scope.
4. **CI integration** of `tests/test_contracts.py` after the 3
   current failures go green.
