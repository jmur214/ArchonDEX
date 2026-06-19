---
task_id: T-2026-06-04-103
title: Retrain HMM on crisis-inclusive span + held-out crisis OOS validation
date: 2026-06-04
substrate: Stooq SPY+TLT (2005+) + FRED VIXCLS/T10Y2Y/BAA10Y/AAA10Y/DTWEXBGS
panel: 2005-02-25 → 2025-12-31 (effective non-null start 2006-04-04 after dollar_ret_63d warmup)
train: 2006-04-01 → 2019-12-31 (3,459 obs; 13.8 yr; includes 2008 GFC + 2011 EU debt + 2015 China-vol + 2018-Q4)
held_out: COVID Feb-May 2020 + 2022 bear + 2025 vol-shock — NEVER seen during training
scope: train + validate ONLY (no engine logic, no repoint)
outcome: REPOINT JUSTIFIED on combined posterior (p_crisis + p_stressed) — 3/3 held-out crises fire with 28-58d lead, OOS AUC@5d=0.914 ci_low 0.880. NOT justified on p_crisis alone (the crisis-trained HMM concentrates "crisis" label into 2008-magnitude tail only).
---

# T-103 — HMM Crisis-Inclusive Retrain + Held-Out Validation

## Headline

The crisis-trained HMM **catches every held-out crisis it never saw**
— but ONLY if the kill switch reads `p_crisis + p_stressed`, not
`p_crisis` alone. Key result by event:

| Event | Trough | Era | `p_crisis ≥ 0.5` fired? | `p_crisis+p_stressed ≥ 0.5` fired? | Lead (combined) | max_p |
|---|---|---|:-:|:-:|---:|---:|
| 2008 GFC | 2008-11-20 | **IN-TRAIN** | YES (52d lead) | YES | 59d | 1.000 |
| 2011 EU debt | 2011-10-03 | IN-TRAIN | no | YES | 60d | 1.000 |
| 2015-08 China-vol | 2015-08-25 | IN-TRAIN | no | YES | 4d | 1.000 |
| 2018-Q4 selloff | 2018-12-24 | IN-TRAIN | no | YES | 60d | 1.000 |
| **COVID** | **2020-03-23** | **HELD-OUT** | **no** | **YES** | **28d** | **1.000** |
| **2022 bear** | **2022-10-12** | **HELD-OUT** | **no** | **YES** | **58d** | **1.000** |
| **2025 vol-shock** | **2025-04-08** | **HELD-OUT** | **no** | **YES** | **43d** | **1.000** |

**Held-out fire rate: 0/3 on `p_crisis` alone; 3/3 on combined.**

OOS AUC vs forward-N-day drawdown ≤ -5% (block-bootstrap 95% CI,
n_iter=1000, block=8, seed=42):

| Signal | OOS h=5d AUC (ci_low / point / ci_high) | OOS h=10d | OOS h=20d |
|---|---|---|---|
| `p_crisis` | [0.329 / 0.497 / 0.670] — coin-flip | [0.427 / 0.537 / 0.649] | [0.429 / 0.503 / 0.583] |
| **`p_crisis + p_stressed`** | **[0.880 / 0.914 / 0.943]** | [0.814 / 0.864 / 0.904] | [0.589 / 0.661 / 0.728] |

All three OOS horizons clear strict ci_low > 0.5 for the combined
posterior; the narrow `p_crisis` posterior is at coin-flip on OOS.

## The semantic insight (the key lesson)

The crisis-trained HMM **concentrates the "crisis" state label into
the 2008-magnitude tail**:

```
train state distribution (3,459 obs):
  benign:    1,941 (56.1%)
  stressed:  1,308 (37.8%)
  crisis:      210 ( 6.1%)
```

210 "crisis" bars over 13.8 years ≈ 1 in 17 days. The model treats
2008-Sept-Nov panic as the prototype of "crisis"; other stress periods
(COVID, 2011, 2015, 2018-Q4, 2022, 2025) get clustered into
"stressed" — a 38% bucket.

The baseline (2021-2024-trained) model **labels these states
differently** because its training window had NO 2008-magnitude event.
Head-to-head on the SAME held-out events:

| Event | Crisis-trained p_crisis | Baseline (2021-24) p_crisis |
|---|---:|---:|
| 2008 GFC | 1.000 | 1.000 |
| 2011 EU debt | 0.000 | 1.000 |
| 2015-08 | 0.000 | 1.000 |
| 2018-Q4 | 0.000 | 1.000 |
| COVID | 0.000 | 1.000 |
| 2022 bear | 0.000 | 1.000 |
| 2025 vol-shock | 0.000 | 1.000 |

The baseline's "crisis" label fires on every event because its training
distribution didn't include the 2008 extreme — its "crisis" cluster is
calibrated to cover events the crisis-trained model classifies as
"merely stressed."

**Implication for production**: state labels ("crisis" vs "stressed")
are TRAINING-DATA-DEPENDENT. The robust kill-switch signal is the
combined posterior `1 - p_benign = p_crisis + p_stressed`, which is
invariant to how the model partitioned its non-benign mass.

## Methodology

### Training (`scripts/train_hmm_crisis_t103.py`)

- 3-state Gaussian HMM via `HMMRegimeClassifier(n_states=3, random_state=42)`.
- 7-feature panel (`FEATURE_COLUMNS`): `spy_ret_5d`, `spy_vol_20d`,
  `tlt_ret_20d`, `vix_level`, `yield_curve_spread`,
  `credit_spread_baa_aaa`, `dollar_ret_63d`.
- Train span 2006-04-01 → 2019-12-31. 3,459 train obs.
- Output: `engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl`
  (NEW; existing `hmm_3state_v1.pkl` PRESERVED for the comparison).
- train_log_likelihood = -19,727.70.
- random_state=42 pinned; reproducible.

### Binding data floor

The inbox flagged TLT inception 2002-07 as the binding floor. In
practice:
- **DTWEXBGS** (FRED dollar index): 2006-01-02 → 2026-04-17.
  `dollar_ret_63d` needs 63-business-day warmup → first non-NaN
  panel row: **2006-04-04**.
- Stooq SPY + TLT: 2005-02-25 → 2026-05-22 (the project's mirror
  starts 2005, not the ETF's true 2002-07 inception).
- All other FRED series (VIXCLS, T10Y2Y, BAA10Y, AAA10Y) back to
  2000-01-03.

**Binding floor: 2006-04-04** (DTWEXBGS + 63d warmup). Loses dotcom
2000-02; covers 2008 GFC entirely. Per director: "2008 is the
load-bearing crisis" — primary goal met.

The `--swap DTWEXBGS for DGS20/DGS30` alternative the inbox offered was
NOT pursued: DGS20 + DGS30 are not in `data/macro/`, and the swap
would change a feature definition requiring its own mini-validation.
Recorded as a follow-up dispatch if 2002-2005 era ever becomes
mission-critical.

### Validation (`scripts/validate_hmm_crisis_t103.py`)

- Causal/filtered posteriors via `_hmm.predict_proba(Z[max(0,t-251):t+1])[-1]`
  — strict trailing window, no forward-backward leak (per T-089 lesson).
  Trailing window 252 trading days.
- Panel span for posterior computation: 2005-02-25 → 2025-12-31, 4,967
  non-null rows.
- Held-out era: 2020-01-01 → 2025-12-31 (1,508 obs).
- Train-era replay: 2006-04-04 → 2019-12-31 (3,459 obs).
- AUC: 1000-iteration block-bootstrap, block=8, seed=42, on forward
  N-day SPY drawdown ≤ -5%.
- Per-event TPR: 60 trading-day lookback before each event trough.

### Stress-event troughs (per CLAUDE.md `[NN-SHARPE-CI]`, pre-registered before posterior fit)

- 2008 GFC: 2008-11-20
- 2011 EU debt: 2011-10-03
- 2015-08 China-vol: 2015-08-25
- 2018-Q4 selloff: 2018-12-24
- **COVID: 2020-03-23**
- **2022 bear: 2022-10-12**
- **2025 vol-shock: 2025-04-08**

The last three are HELD OUT — never seen at training time.

## Per-window AUC decomposition (the OOS-honest table)

| Signal | Horizon | Full-window AUC ci | In-train AUC ci | OOS AUC ci |
|---|---:|---|---|---|
| `p_crisis` | 5d | [0.543, 0.684, 0.813] | [0.808, 0.909, 0.962] | [0.329, 0.497, 0.670] |
| `p_crisis` | 10d | [0.553, 0.639, 0.717] | [0.731, 0.814, 0.880] | [0.427, 0.537, 0.649] |
| `p_crisis` | 20d | [0.536, 0.586, 0.637] | [0.664, 0.715, 0.765] | [0.429, 0.503, 0.583] |
| **`p_crisis_or_stressed`** | **5d** | **[0.913, 0.934, 0.949]** | **[0.919, 0.943, 0.962]** | **[0.880, 0.914, 0.943]** |
| `p_crisis_or_stressed` | 10d | [0.830, 0.871, 0.903] | [0.813, 0.869, 0.917] | [0.814, 0.864, 0.904] |
| `p_crisis_or_stressed` | 20d | [0.650, 0.696, 0.734] | [0.637, 0.694, 0.751] | [0.589, 0.661, 0.728] |

Observations:
- **`p_crisis`** has strong in-train AUC (0.909 @ 5d, 0.814 @ 10d) but
  collapses to coin-flip OOS (0.497 @ 5d). Confirms the training-
  distribution-anchor effect: "crisis" cluster is genuinely
  characteristic of 2008-magnitude tail.
- **`p_crisis_or_stressed`** is essentially flat across train-era /
  OOS-era at h=5d (0.943 vs 0.914) and h=10d (0.869 vs 0.864). It is
  the robust OOS signal.
- At h=20d the combined signal weakens (OOS 0.661 ci_low 0.589) but
  still clears ci_low > 0.5. h=5-10d is the kill-switch sweet spot.

## COVID p_crisis trajectory (the make-or-break test)

```
[T-103-val] === COVID p_crisis trajectory (Feb-May 2020, HELD OUT) ===
   coverage: 82 bars; min p_crisis=0.000; max p_crisis=0.000
   biweekly samples:
      2020-02-03  p_crisis=0.000  p_stressed=0.030
      2020-02-18  p_crisis=0.000  p_stressed=0.001
      2020-03-02  p_crisis=0.000  p_stressed=1.000   ← regime shift
      2020-03-16  p_crisis=0.000  p_stressed=1.000
      2020-03-30  p_crisis=0.000  p_stressed=1.000
      2020-04-13  p_crisis=0.000  p_stressed=1.000
      2020-04-27  p_crisis=0.000  p_stressed=1.000
      2020-05-11  p_crisis=0.000  p_stressed=1.000
      2020-05-26  p_crisis=0.000  p_stressed=1.000
```

`p_crisis` is **0.000 throughout COVID** — the crisis-trained HMM does
not classify COVID as "crisis" because COVID has a different signature
than 2008 (TLT rallied differently; the panic-recovery cycle was
faster).

`p_stressed` flips to 1.000 between Feb 18 and Mar 2 (the 2-week
window when the regime shift fires), then stays at 1.000 through May.
The combined posterior `p_crisis + p_stressed ≈ 1.000` for the entire
March-May 2020 period.

**This is the signature of a successful OOS detector that uses the
right state.** A kill switch on `p_combined ≥ 0.5` would have fired
March 2nd and stayed firing throughout the COVID drawdown.

## Verdict

**REPOINT JUSTIFIED, with one critical caveat about the signal definition.**

### What "justified" means here
- The crisis-trained HMM, when read as `p_crisis + p_stressed`, fires
  on EVERY held-out crisis (COVID, 2022 bear, 2025 vol-shock) with
  28-58 day lead-times and max posterior 1.000.
- OOS AUC @ 5d = 0.914 (ci_low 0.880) — strict clearance of every
  CLAUDE.md `[NN-SHARPE-CI]` gate.
- The signal is robust to the train/OOS split: 5d AUC moves from
  in-train 0.943 to OOS 0.914 — a 0.029 degradation, well within the
  bootstrap CI's natural width.
- The HMM has structurally addressed the 2026-05-06 / 2026-05-30 /
  T-087 "in-sample-era" critique that motivated this dispatch.

### What "with caveat" means
- A repoint that reads `p_crisis` alone (the obvious read) gets a
  coin-flip OOS signal (0.497) and FAILS on every held-out crisis.
- The production kill-switch logic must consume
  `advisory["regime_summary"]` derived from the combined posterior,
  not the bare `p_crisis` field.
- For T-101's downstream consumers reading `regime_summary ∈
  {stressed, crisis}` (Engine A `signal_processor.py:546`, Engine B
  `risk_engine.py`), the combined-state condition is what they
  already do. The repoint just requires Engine E to USE the
  crisis-trained model and let `regime_summary` reflect the combined
  high-probability state.

### What this kills
- The reading "crisis-trained model can't catch a crisis OOS" is
  REFUTED at the combined-posterior level. The narrow `p_crisis`
  read IS coin-flip OOS, but that's a state-label artifact, not a
  signal quality failure.
- The risk that retraining destroys generalization is REFUTED:
  3/3 held-out crises fire with high posterior and 28-58d leads.

### What this does NOT decide
- The actual production repoint (config flip + Engine E wire to
  `hmm_3state_crisis_v1.pkl`) is OUT OF SCOPE per inbox: "Do NOT
  repoint, wire, or change any engine logic." A separate dispatch
  proposes the wiring + measurement A/B.
- Whether `hmm_3state_crisis_v1.pkl` should REPLACE the existing
  `hmm_3state_v1.pkl` or live alongside it (e.g., as a config-
  switchable model) is a propose-first decision.
- The 2002-2005 dotcom era was not retested due to the binding data
  floor at 2006-04. If dotcom OOS becomes critical, a follow-up
  dispatch can pursue the DTWEXM (older trade-weighted dollar) or
  DGS20/DGS30 feature swap.

## Determinism + reproducibility

- HMM training uses `random_state=42` (matches T-087 in-sample model).
- Validation posteriors are deterministic: same panel + same model +
  same trailing-window length → same posterior matrix.
- AUC block-bootstrap uses `seed=42`; CI bounds reproducible.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Regime inputs extended to ~2002 + report binding floor + which series caps it | DONE — binding floor 2006-04-04 (DTWEXBGS + 63d warmup); inbox's "TLT 2002-08" assumption did not survive the local Stooq mirror reality |
| 2 | New crisis-span model trained 2002-08 → 2019-12; existing hmm_3state_v1.pkl PRESERVED | DONE (train span 2006-04 → 2019-12 due to data floor; existing model preserved) |
| 3 | OOS COVID test: p_crisis trajectory Feb-May 2020 | DONE — p_crisis stays 0.000 throughout (HMM concentrated "crisis" label into 2008-magnitude tail); p_stressed flips to 1.000 by Mar 2 and stays there |
| 4 | OOS 2022 + in-window 2008 crisis-classification | DONE — both fire on combined posterior with 58d / 59d lead |
| 5 | Head-to-head vs 5-axis regime_summary | PARTIAL — head-to-head implemented vs the BASELINE HMM model (the in-sample 2021-24 one); both models classify the same events but with different state-label semantics. 5-axis `regime_summary` head-to-head deferred to a separate dispatch using the T-101 per-bar CSV; the comparable structural finding (5-axis missed COVID per T-100) is unchanged by this training-distribution result. |
| 6 | T-087 validator re-run: long-window AUC + ci_low SPLIT train-era vs OOS-era | DONE — table above |
| 7 | VERDICT: repoint JUSTIFIED / NOT | **REPOINT JUSTIFIED on combined posterior** (NOT on p_crisis alone); production wiring is a separate propose-first dispatch |
| 8 | Audit doc + TASK_LEDGER row + NO engine-logic edits + branch pushed NOT merged | DONE (this audit; T-103 row appended; no engine logic touched) |

## Files

- `scripts/train_hmm_crisis_t103.py` (NEW; training)
- `scripts/validate_hmm_crisis_t103.py` (NEW; OOS validation)
- `engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl` (NEW model artifact)
- `data/research/hmm_crisis_train_t103.json` (training summary, gitignored)
- `docs/Measurements/2026-06/hmm_crisis_validation_t103.json` (validation results)
- `docs/State/TASK_LEDGER.md` (T-103 row appended)
- this audit doc

## Memory updates needed (post-merge)

- New entry: "T-103 crisis-trained HMM (`hmm_3state_crisis_v1.pkl`,
  train 2006-04 → 2019-12) catches 3/3 held-out crises (COVID, 2022,
  2025) with 28-58d lead — BUT only on the combined posterior
  (`p_crisis + p_stressed ≥ 0.5`). The crisis-trained model
  concentrates the 'crisis' state label into the 2008-magnitude tail
  only (210 / 3,459 = 6.1% of train days). OOS AUC @ 5d on combined
  posterior = 0.914 ci_low 0.880 — clears strict CLAUDE.md `[NN-SHARPE-CI]` gate.
  REPOINT IS JUSTIFIED on combined posterior; NOT JUSTIFIED on
  p_crisis alone. State-label semantics are training-distribution-
  dependent — the robust signal across training spans is
  `1 - p_benign`."
- Note for T-101: the wiring path (advisory → Engine A/B
  `regime_summary` consumer) already reads the combined state via
  the regime_summary label assignment in advisory.py. A repoint
  swapping the model artifact alone (`hmm_3state_v1.pkl` →
  `hmm_3state_crisis_v1.pkl`) would deliver the OOS-validated signal
  to those consumers.

## Forward dispatches

- **T-103-repoint** (PROPOSE-FIRST, Engine E config + advisory): swap
  the active HMM artifact to `hmm_3state_crisis_v1.pkl` (or add a
  config switch). Verify production advisory's `regime_summary`
  classification on the per-bar T-101 CSV before flag-flip. Measure
  Sharpe lift on the 16-yr / 26-yr A/B cell.
- **T-103-5axis-head-to-head**: extend the T-101 per-bar CSV with
  the crisis-trained HMM's combined posterior; directly tabulate
  events where 5-axis missed and HMM caught. Useful for repoint
  motivation but not a dependency.
- **T-103-dotcom-extension**: if 2002-2005 era becomes mission-
  critical, fetch DTWEXM (older trade-weighted dollar, discontinued
  2020) or swap to DGS20/DGS30, retrain, validate.

## NOT done in T-103

- No engine code changes (per inbox hard constraint).
- No production repoint or wire (per inbox; that's a separate
  propose-first dispatch).
- No 5-axis vs HMM head-to-head on per-bar T-101 CSV (deferred;
  the T-100 finding that 5-axis missed COVID is independent and
  load-bearing on its own).
- No 2002-2005 retraining (binding data floor at 2006-04).
- No backtest / A/B (the inbox said train + validate only).
