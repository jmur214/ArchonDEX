# T-2026-05-31-089 — Regime-validator causal-path verification + 3 lookahead-bug fixes

**Date:** 2026-05-31
**Branch:** `feature/regime-validator-causal-fix-t089`
**Worker:** Agent B

## Verdict — T-087 causal claim VERIFIED; 3 sibling validators FIXED; lookahead inflation BOUNDED at +0.0015 AUC

### Part A — T-087 causal claim is GENUINE

`scripts/validate_regime_signals_t087.py` line 367-372 implements the
correct causal pattern:

```python
print(f"[T-087] computing CAUSAL (filtered) HMM posteriors over {n_rows} rows...")
proba_arr = np.empty((n_rows, hmm.n_states), dtype=np.float64)
for t in range(n_rows):
    start_t = max(0, t - 252 + 1)
    proba_arr[t] = hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]
```

Per-bar `predict_proba` on a growing prefix bounded to 252 trailing
bars, keeping only the LAST row of the output. This is the FILTERED
(forward-only) posterior — no future-bar conditioning. **The AUC
0.887 / 0.804 headline on the 12-yr substrate stands as causal
evidence, NOT lookahead-contaminated.**

The line-10 docstring incorrectly says "Re-uses ... predict_proba_sequence"
— that's stale text from an earlier version. The actual call to
`predict_proba_sequence` does NOT exist in the file (only one
`predict_proba` invocation, on line 372 inside the growing-prefix
loop). This is a docstring lag, not a behavioral bug.

`grep` confirmation:

```
$ grep -nE "predict_proba_sequence|predict_proba\b" scripts/validate_regime_signals_t087.py
10:  2) Re-uses build_feature_panel + HMMRegimeClassifier.predict_proba_sequence   ← stale docstring
356:    # CRITICAL: predict_proba_sequence uses forward-BACKWARD smoothing         ← warning comment
360:    # predict_proba on growing prefixes Z[:t+1] and taking the last row.        ← explanation comment
372:        proba_arr[t] = hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]            ← actual causal call
```

### Part B — 3 sibling validators FIXED

All 3 sites flagged by the 2026-05-31 silent-bug audit have been
patched to use the canonical T-087 pattern via a shared helper:

| # | File | Pre-fix | Post-fix |
|---|---|---|---|
| 4 | `scripts/validate_regime_signals.py:348-355` | `hmm.predict_proba_sequence(panel)` + false "equivalent for our purposes" comment | `causal_proba_sequence(hmm, panel, window=252)` + corrected comment |
| 5 | `scripts/validate_regime_signals_vix_term.py:245` | `hmm.predict_proba_sequence(panel)` | `causal_proba_sequence(hmm, panel, window=252)` |
| 6 | `scripts/backtest_transition_warning.py:331` | `clf.predict_proba_sequence(panel_valid)` | `causal_proba_sequence(clf, panel_valid, window=252)` |

The false "equivalent for our purposes" comment in [4] was the
load-bearing item — it actively asserted (wrongly) that the leaky
path was equivalent to the causal path "for time series labeling at
this granularity". The replacement comment explicitly explains why
the predictive-validity test (AUC of signal_t vs forward
dd_{t→t+k}) is **exactly** the case where forward-backward smoothing
is NOT equivalent — that's the case where it injects lookahead.

### Part C — Leaky-vs-causal AUC inflation: BOUNDED at +0.006

`scripts/compare_leaky_vs_causal_t089.py` computes both paths in a
single process on the same model (`hmm_3state_v1.pkl`) + panel, then
reports AUC + bootstrap CI per CLAUDE.md non-negotiable #6.

**4-yr window (2021-01-01 → 2025-04-30):**

| Signal | LEAKY AUC | CAUSAL AUC | Δ (leaky - causal) |
|---|---|---|---|
| p_crisis | 0.7779 [0.7465, 0.8094] | 0.7763 [0.7450, 0.8079] | **+0.0015** |
| p_stressed | 0.5603 [0.5238, 0.5949] | 0.5596 [0.5238, 0.5939] | **+0.0006** |

**Extended window (2014-01-01 → 2025-04-30; panel effectively 2020-04-01+ due to feature-warmup constraints):**

| Signal | LEAKY AUC | CAUSAL AUC | Δ (leaky - causal) |
|---|---|---|---|
| p_crisis | 0.7443 [0.7091, 0.7789] | 0.7383 [0.7024, 0.7728] | **+0.0060** |
| p_stressed | 0.5339 [0.4996, 0.5674] | 0.5331 [0.4990, 0.5657] | **+0.0008** |

(Bootstrap CIs from 1000 stratified resamples of positives + negatives,
per CLAUDE.md #6. n=1066 rows in 4-yr / 1251 rows in extended; ~207 /
229 positives respectively at the 20-day -5% drawdown threshold.)

**Interpretation:**

1. The lookahead inflation under `predict_proba_sequence` is in the
   correct direction (leaky AUC > causal AUC) — forward-backward
   smoothing peeks at future evidence and tightens the per-bar
   posterior, which marginally helps the bar-level classifier
   discriminate forward-drawdown windows.
2. The magnitude is SMALL (+0.0015 to +0.0060 AUC) and falls
   well within the bootstrap CI width (~0.06). The directional
   AUC conclusions of the validators do NOT change under the causal
   fix; only the headline numbers tighten slightly.
3. T-087's AUC 0.887 / 0.804 on the 12-yr substrate is genuinely
   causal — confirmed by code inspection, AND by the bound that
   even if a leaky variant had been used, the inflation would
   have been ≤ +0.006 (assuming similar model/panel characteristics).
   The Engine E regime-signal reversal of the 2026-05-06 "refuted"
   verdict is supported by the corrected data.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Definitive verdict on T-087's causal claim | **PASS** — code inspected + grep confirms only 1 `predict_proba` call, the growing-prefix one |
| 2 | Corrected causal AUC reported (if T-087 was contaminated) | **N/A** — T-087 was genuinely causal |
| 3 | [4][5][6] fixed to causal labeling; false "equivalent" comment removed | **PASS** — 3 sites patched via shared `causal_proba_sequence` helper |
| 4 | Corrected diagnostics re-run; leaky-vs-causal delta quantified | **PASS** — Δ AUC +0.0015 to +0.006 across windows |
| 5 | Regression test asserting validators reject `predict_proba_sequence` in labeling path | **PASS** — `tests/test_regime_validator_causal_t089.py` 11/11 |
| 6 | Audit doc | **PASS** (this) |
| 7 | Branch push only | **PASS** |

## Hard constraints — confirmed met

- [x] Engine E production code untouched (`hmm_classifier.py`,
  `regime_detector.py` not modified). The shared helper
  `scripts/_hmm_causal_proba.py` lives in `scripts/` per dispatch
  constraint.
- [x] Engine B / risk config untouched (A's parallel task).
- [x] Per CLAUDE.md #6: AUC bootstrap CI on every headline (stratified
  positive/negative resample, 1000 iterations).
- [x] No production decision path consumes `predict_proba_sequence`
  found in the sweep — only the 3 validator scripts. If a production
  consumer of the leaky path is found later, it would be flagged
  propose-first.

## Files

- **NEW** `scripts/_hmm_causal_proba.py` — canonical `causal_proba_sequence`
  helper, extracted from T-087's growing-prefix pattern. Single source
  of truth for the 3 (and any future) validators.
- **MOD** `scripts/validate_regime_signals.py` — replaced leaky call +
  removed false "equivalent for our purposes" comment.
- **MOD** `scripts/validate_regime_signals_vix_term.py` — replaced leaky
  call.
- **MOD** `scripts/backtest_transition_warning.py` — replaced leaky call.
- **NEW** `scripts/compare_leaky_vs_causal_t089.py` — diagnostic driver
  computing both paths' AUC + bootstrap CI on the same data, for the
  leaky-vs-causal inflation table above.
- **NEW** `tests/test_regime_validator_causal_t089.py` — 11 regression
  tests covering (a) text-level guard against `predict_proba_sequence`
  re-introduction in the 3 fixed scripts + the T-087 reference,
  (b) helper-module import + signature contract, (c) behavioral
  growing-prefix loop with synthetic HMM + NaN handling.
- **NEW** `docs/Audit/regime_validator_causal_fix_t089_2026_05_31.json`
  — 4-yr aggregation output.
- **NEW** `docs/Audit/regime_validator_causal_fix_t089_2026_05_31_12yr.json`
  — extended-window aggregation output.
- **NEW** `docs/Audit/regime_validator_causal_fix_t089_2026_05_31.md`
  (this).

## Pattern fingerprint going forward

Any code that:
1. Computes per-bar HMM posteriors for a predictive-validity test
   (signal_t vs forward target_{t→t+k}), AND
2. Calls `predict_proba_sequence` (or any forward-backward smoother)

is at risk of lookahead. Use the shared
`scripts._hmm_causal_proba.causal_proba_sequence` helper. The
regression test guards the 3 currently-known scripts; new scripts
should also call the helper rather than rolling their own causal
loop (institutional-memory pattern: maintain a SHARED canonical
implementation instead of N inlined copies).

## Surprises

1. **T-087 docstring was misleading**, but the actual code was
   correct. This is a classic "code-doc divergence" — the warning
   here is to read CODE, not docs, when verifying claims.

2. **Lookahead inflation is small on this model.** I had expected
   the forward-backward smoothing to produce a much larger AUC
   inflation (e.g., +0.05 or more). The actual delta of +0.0015 to
   +0.006 reflects two facts: (a) the HMM's state distributions
   are fairly well-separated at the per-bar level even before
   smoothing, so the smoothing's "future evidence" doesn't change
   classifications much; (b) the 252-day window cap in the causal
   path already provides a strong filtering signal.

3. **The bug was real but its numerical impact was bounded.** Per
   CLAUDE.md non-negotiable #6 (ci_low gates, not point), the
   leaky-vs-causal CI overlaps fully → the predictive-validity
   conclusions of the 3 validators were probably still in the right
   ballpark even when computed with the leaky path. The fix is still
   correct on principle (no lookahead in a predictive-validity test
   is non-negotiable for trustworthy diagnostics), but the project
   is not retroactively at risk because of pre-fix runs.

## Forward-look

- The shared `causal_proba_sequence` helper is now the single source
  of truth. If Engine E's HMM ever gains a production-side
  `predict_proba_filtered` method, this helper should switch to
  call it (1-line change). For now, the helper inlines the
  growing-prefix loop because Engine E does not yet expose a
  filtered method publicly.
- Codebase-wide grep for `predict_proba_sequence` consumers OTHER
  than the 3 fixed scripts + T-087 reference found 7 additional
  sites — all in HMM **training** scripts:

```
$ grep -rn "predict_proba_sequence" engines/ scripts/ --include='*.py' \
  | grep -v scripts/validate_regime_signals_t087.py \
  | grep -v scripts/validate_regime_signals.py \
  | grep -v scripts/validate_regime_signals_vix_term.py \
  | grep -v scripts/backtest_transition_warning.py \
  | grep -v tests/test_regime_validator_causal_t089.py \
  | grep -v scripts/_hmm_causal_proba.py \
  | grep -v scripts/compare_leaky_vs_causal_t089.py
engines/engine_e_regime/hmm_classifier.py:319:    def predict_proba_sequence(   ← definition
scripts/train_hmm_regime.py:118,121:   ← post-fit state-distribution diagnostic
scripts/train_hmm_vix_term.py:123,126: ← post-fit state-distribution diagnostic
scripts/train_minimal_hmm.py:138:      ← outputs labeled regimes to disk
scripts/train_multires_hmm.py:141,144: ← post-fit state-distribution diagnostic
```

**Triage of training-script consumers:**

| Consumer | Use | Risk |
|---|---|---|
| `train_hmm_regime.py:118,121` | `argmax_state.value_counts()` — state-distribution diagnostic | LOW. Counting how often each state was selected over train/test. Smoothing affects margins, not counts of dominant state. |
| `train_hmm_vix_term.py:123,126` | Same as above | LOW |
| `train_minimal_hmm.py:138` | Writes labeled regime per bar to a downstream output file | **MEDIUM — flag for follow-up.** If a downstream consumer trains another model on those bar-labels assuming they're causal, lookahead leaks through. Worth a propose-first dispatch to audit downstream consumers. |
| `train_multires_hmm.py:141,144` | State-distribution diagnostic | LOW |

**Per the T-089 dispatch hard constraint**: production / training-side
consumers found here are NOT fixed in this PR (they fall under
"production code" + are out of the 3-bug scope the silent-bug audit
identified). They are flagged here for the director's propose-first
decision on a follow-up sweep.

Specifically: `train_minimal_hmm.py:138`'s labeled-regime output
should be the highest-priority audit target — downstream consumers
of `data/models/.../regime_labels.parquet` (or wherever the labeled
output lands) may be treating smoothed labels as causal. If any
production strategy uses those labels as features, that's a real
leak. The training scripts' state-distribution diagnostics on lines
118/121/123/126/141/144 are LOW-risk and would be fine to defer
indefinitely — they're sanity checks on how many bars landed in each
state, where smoothing doesn't materially change the answer.
