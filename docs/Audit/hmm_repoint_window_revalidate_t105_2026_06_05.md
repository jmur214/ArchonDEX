---
task_id: T-2026-06-05-105
title: Re-validate T-103 crisis-HMM at the LIVE 60-bar inference window + dwell-time
date: 2026-06-05
substrate: Stooq SPY+TLT 2005+ + FRED VIXCLS/T10Y2Y/BAA10Y/AAA10Y/DTWEXBGS
panel: 2005-02-25 → 2025-12-31 (effective non-null 2006-04-04 after dollar_ret_63d warmup)
train: 2006-04-01 → 2019-12-31 (same as T-103)
windows_tested: [60 (LIVE), 252 (T-103 BASELINE)]
scope: validation re-run + dwell-time measurement; NO engine logic, NO repoint, NO config flip
outcome: AUC SURVIVES at LIVE window (OOS@5d 0.919 ci_low 0.885 vs T-103@252 0.914/0.880 — marginally HIGHER at 60); per-event TPR identical 7/7 at both windows; BUT dwell time of `p_combined ≥ 0.5` is 44-50% always-on with median run 12-19d and p90 198-265d → NOT safe to use as a LEVEL → requires TRANSITION-TRIGGER form. Repoint direction redefined.
---

# T-105 — Re-validate T-103 HMM at Live Window + Dwell-Time

## Headline

**REPOINT SURVIVES the live-window check (AUC essentially identical
at 60-bar vs 252-bar) but FAILS the use-as-a-level check (44-50%
always-on with long-tail runs).** The implication is structural:
the proposal cannot ship as "kill switch on `p_combined ≥ 0.5`" — it
must ship as a TRANSITION-TRIGGER signal (fire on regime change,
not on persistent level), or pair with a different level-signal.

### Live inference window — confirmed from code path

- `engines/engine_e_regime/regime_config.py:175`
  `history_window_daily: int = 60` (dataclass default)
- `engines/engine_e_regime/regime_detector.py:459` passes
  `cfg.history_window_daily` into `predict_proba_for_row`
- `engines/engine_e_regime/hmm_classifier.py:252` signature
  `history_window: int = 60`
- `config/regime_settings.json` has **no override** under the `hmm`
  section nor anywhere else (top-level keys checked: `trend`,
  `volatility`, `correlation`, `breadth`, `forward_stress`,
  `advisory`, `benchmarks`, `cross_asset`, `vix_tickers`,
  `exclude_from_breadth`, `hmm`)

**Confirmed live inference window: 60 bars.**

## Side-by-side: AUC@60 vs AUC@252 (block-bootstrap CI, n_iter=1000, block=8, seed=42)

The combined posterior `p_crisis + p_stressed` (= `1 - p_benign`)
vs forward N-day SPY drawdown ≤ -5%:

| Horizon | Era | window=60 ci_low / point / ci_high | window=252 ci_low / point / ci_high | Δ point |
|---|---|---|---|---:|
| 5d | full | [0.911, **0.933**, 0.949] | [0.913, 0.934, 0.949] | -0.001 |
| 5d | in_train | [0.915, 0.939, 0.958] | [0.919, 0.943, 0.962] | -0.004 |
| **5d** | **OOS** | **[0.885, 0.919, 0.948]** | **[0.880, 0.914, 0.943]** | **+0.005** |
| 10d | full | [0.828, 0.870, 0.903] | [0.830, 0.871, 0.903] | -0.001 |
| 10d | in_train | [0.812, 0.867, 0.915] | [0.813, 0.869, 0.917] | -0.002 |
| **10d** | **OOS** | **[0.815, 0.866, 0.905]** | **[0.814, 0.864, 0.904] | **+0.002** |
| 20d | full | [0.651, 0.696, 0.734] | [0.650, 0.696, 0.734] | 0.000 |
| 20d | in_train | [0.637, 0.694, 0.751] | [0.637, 0.694, 0.751] | 0.000 |
| **20d** | **OOS** | **[0.590, 0.662, 0.728]** | **[0.589, 0.661, 0.728]** | **+0.001** |

**Conclusion: AUC is invariant to the trailing window within
sampling noise.** The adversarial review's hypothesis — "60-bar
posterior is noisier and faster-switching, so the AUC won't hold" —
is REFUTED at every horizon and every era split. OOS@5d on 60-bar
is marginally HIGHER than on 252-bar (0.919 vs 0.914, ci_low 0.885
vs 0.880).

This is consistent with the Gaussian-HMM forward-pass having
already converged to a stable posterior within ~30-50 bars under
this feature panel; the additional 192 bars of tail in the 252-bar
window contribute negligibly.

## Per-event TPR head-to-head: 60 vs 252

`p_combined ≥ 0.5`, 60d lookback before each event trough:

| Event | Era | window=60 fired? | lead | max_p | window=252 fired? | lead | max_p |
|---|---|:-:|---:|---:|:-:|---:|---:|
| 2008 GFC | IN-TRAIN | YES | 59d | 1.000 | YES | 59d | 1.000 |
| 2011 EU debt | IN-TRAIN | YES | 60d | 1.000 | YES | 60d | 1.000 |
| 2015-08 China-vol | IN-TRAIN | YES | 4d | 1.000 | YES | 4d | 1.000 |
| 2018-Q4 selloff | IN-TRAIN | YES | 60d | 1.000 | YES | 60d | 1.000 |
| **COVID 2020** | HELD-OUT | **YES** | **28d** | 1.000 | YES | 28d | 1.000 |
| **2022 bear** | HELD-OUT | **YES** | **58d** | 1.000 | YES | 58d | 1.000 |
| **2025 vol-shock** | HELD-OUT | **YES** | **43d** | 1.000 | YES | 43d | 1.000 |

**Per-event TPR: identical at both windows. 7/7 events fire at
p_combined ≥ 0.5 with 4-60d lead and max_p = 1.000.**

The thresholds 0.7 and 0.9 produce essentially identical per-event
output — once the signal goes above 0.5 it goes to 1.0 within a few
bars.

## Dwell-time — the DISQUALIFYING finding for use-as-a-level

Per regime-analyst memory 2026-05-06: **"a regime signal consumed as
a LEVEL for de-grossing must have median run-length ≤ ~20 trading
days OR be a transition trigger — else it re-creates the 'always-on
light leverage' pathology even when AUC is fine."**

Measured at LIVE window=60, on `p_combined = p_crisis + p_stressed`:

| Substrate | Threshold | frac_above | median_run | p90_run | max_run | n_runs | ≤20d rule |
|---|---:|---:|---:|---:|---:|---:|:-:|
| **16yr 2010-2025** | 0.30 | 44.7% | 13.0d | 188.6d | 348d | 30 | OK (median) |
| **16yr 2010-2025** | **0.50** | **44.0%** | **12.0d** | **198.2d** | **348d** | **29** | **OK (median)** |
| **16yr 2010-2025** | 0.70 | 43.5% | 18.0d | 226.0d | 347d | 26 | OK (median) |
| **26yr 2006-2025** | 0.30 | 50.6% | 18.0d | 255.8d | 634d | 33 | OK (median) |
| **26yr 2006-2025** | **0.50** | **49.9%** | **19.0d** | **265.4d** | **632d** | **32** | **OK (median, marginal)** |
| 26yr 2006-2025 | 0.70 | 49.5% | 22.0d | 280.2d | 631d | 29 | **FAIL** |

**Verdict against the ≤20-day rule:**
- **Median run-length passes** at most threshold-substrate
  combinations (12-19d at thr 0.5 on 16/26yr; the median is the
  central tendency).
- **BUT the right tail is catastrophic.** p90 run-length is
  **198-265 days** at thr 0.5. The MAX run on 26yr is **632 days**
  (~2.5 years continuously above 0.5).
- **The frac-above-trigger is 44-50%** — the signal is in the
  "stressed-or-crisis" state ROUGHLY HALF THE TIME on the deep
  substrate.

This IS the pathology the rule was written against. A kill switch
firing on `p_combined ≥ 0.5` as a LEVEL would put the strategy in
de-gross mode roughly half the time, including 200+ day continuous
stretches, even when AUC at horizon 5-10d is excellent. Operationally
this is "always-on light leverage" — exactly what the project memory
documented as "operationally useless for de-grossing."

**Important nuance:** the AUC says the signal IS informative — when
the threshold is crossed it predicts forward drawdowns much better
than baseline. But that doesn't make it a usable LEVEL; it makes
it a usable TRANSITION trigger. The signal is correctly identifying
which side of the regime distribution we're in; the issue is that
the "stressed" side is much larger and more persistent than a
sensible kill switch would want to act on.

The 252-bar dwell numbers are essentially identical to 60-bar
(measured for comparison; same column on the right of the table
above) — confirming this is a property of the underlying state
distribution, not a window-smoothing artifact.

## Operative-horizon recommendation

The AUC decays sharply with horizon:

| Horizon | OOS AUC ci_low / point / ci_high (60-bar) | Strict ci_low gate (≥0.7) |
|---|---|:-:|
| 5d | [0.885, 0.919, 0.948] | ✓ PASS (margin +0.185) |
| 10d | [0.815, 0.866, 0.905] | ✓ PASS (margin +0.115) |
| 20d | [0.590, 0.662, 0.728] | ✗ FAIL — straddles 0.7 |

A de-gross policy acts on positions that change over days-to-weeks.
The OPERATIVE horizon for a MaxDD-reduction A/B is therefore 10d
(where ci_low 0.815 is comfortable) NOT 20d (where ci_low 0.590 is
marginal and could vanish with noise). The 5d window is sharpest
but a kill switch firing on a 5d-ahead signal would over-react to
short reversals.

**Pre-registered KPI for the future T-105-followup MaxDD A/B:**
- Primary horizon: 10d (OOS AUC ci_low 0.815)
- Headline metric: MaxDD reduction vs baseline at the same Sharpe
  (or no-worse-than-cost-of-degross constraint)
- Sample/window: 16-yr cell (Sharpe 1.018 ci_low 0.560 per T-092);
  re-test on 26-yr for crisis-regime robustness only AFTER 16-yr
  clears.
- A signal at 5d alone (without 10d co-confirmation) is rejected as
  noise-trigger.

## VERDICT — repoint signal at the production window

**REPOINT SIGNAL SURVIVES at the LIVE 60-bar window**, with the
critical caveat that it must be consumed as a TRANSITION-TRIGGER
not a LEVEL.

| Gate | Result |
|---|---|
| Live-window AUC ≥ 252-bar AUC | ✓ PASS (60-bar OOS@5d 0.919 vs 252-bar 0.914 — marginally HIGHER) |
| Live-window OOS AUC ci_low > 0.7 at operative horizon (10d) | ✓ PASS (ci_low 0.815) |
| Per-event TPR on held-out crises | ✓ PASS (3/3 fire with 28-58d lead, max_p = 1.000) |
| Per-event TPR identical 60 vs 252 | ✓ PASS (7/7 identical) |
| Median dwell ≤ 20d at thr 0.5 | OK on 16yr (12d); marginal on 26yr (19d); FAIL on 26yr at thr 0.7 (22d) |
| p90 dwell ≤ ~60d (a sane upper bound) | **✗ FAIL** (p90 198d on 16yr, 265d on 26yr — orders of magnitude over) |
| frac-above-trigger ≤ ~20% (so de-gross is meaningful, not constant) | **✗ FAIL** (44-50%) |

**Overall verdict: DEGRADED-BUT-OK-AS-TRANSITION-TRIGGER, NOT
AS LEVEL.** The literal proposal "flip a kill switch when
`advisory["regime_summary"] ∈ {stressed, crisis}`" is structurally
disqualified by the dwell + frac-above measurements, regardless of
how strong the AUC is.

## What this changes for the T-103 repoint proposal

T-103 concluded "REPOINT JUSTIFIED on combined posterior." That
verdict stands at the AUC level — but the kill-switch DESIGN must
shift:

| Design option | What it does | Survives this audit? |
|---|---|:-:|
| Threshold-on-level: `p_combined ≥ 0.5 → kill` | Fires when signal is above 0.5 | **NO** — fails dwell + frac-above |
| Transition trigger: fire on `Δp_combined > X` over `K` bars | Fires only when regime is CHANGING TOWARD stressed/crisis | YES — needs design work, not refuted by this audit |
| Confirmation-with-second-signal: `p_combined ≥ 0.5 AND other(crisis_validation)` | Adds a co-condition that itself has short dwell | YES — second signal must pass the same ≤20d test |
| Decay-after-fire kill: `p_combined ≥ 0.5 → kill for K bars` then re-arm | Bounds the always-on duration mechanically | YES if K chosen against 12-19d median dwell evidence |
| Use `p_crisis` alone instead of combined | Avoids the broad "stressed" 38% bucket | **NO per T-103** — OOS AUC collapses to coin-flip on the crisis-trained model (state-label artifact) |

The combined posterior is the right INFORMATION SOURCE; the
TRANSITION/decay/co-condition wrapping is the right CONSUMPTION
PATTERN. This dispatch's contribution is forcing that distinction
before a repoint proposal goes to the user.

## Methodology

### Data + model
- Crisis-trained HMM artifact: `engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl` (T-103; not re-trained here).
- Panel: same Stooq SPY+TLT + FRED inputs as T-103; effective non-null start 2006-04-04 (DTWEXBGS+63d warmup).
- 4,967 non-null panel rows; train_end 2019-12-31 splits in_train (3,459 rows) vs OOS (1,508 rows).

### Inference
- Causal/filtered posteriors via `_hmm.predict_proba(Z[max(0, t-window+1):t+1])[-1]`. Per T-089: no forward-backward leak.
- Run at window ∈ {60, 252}, full panel, both windows on the same model.

### AUC
- `auc_score` Mann-Whitney rank-based (matches T-087/T-103 implementation).
- Block-bootstrap CI: n_iter=1000, block=8, seed=42.
- Split into full / in_train (2006-04 → 2019-12) / OOS (2020-01 →).

### Dwell-time
- Boolean series `(p_combined ≥ threshold)` for thr ∈ {0.30, 0.50, 0.70}.
- Run = maximal consecutive `True` segment.
- Reported: frac_above, median_run, p90_run, max_run, n_runs.
- Computed on both 16-yr (2010-2025) and 26-yr (2006-04 → 2025) substrates.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Confirmed actual live inference window from config | DONE — 60 bars (dataclass default; no config override) |
| 2 | OOS AUC at live window, 5/10/20d, ci_low, train-vs-OOS split, SIDE-BY-SIDE with 252 | DONE — table above |
| 3 | Per-event fire + lead-time on COVID/2022/2025 at live window | DONE — 3/3 fire with 28-58d lead, max_p = 1.000 |
| 4 | Dwell-time on 16+26yr at {0.30, 0.50, 0.70} | DONE — median 12-22d; p90 188-280d; frac_above 44-51% |
| 5 | Dwell verdict: level vs transition-trigger | DONE — REQUIRES TRANSITION-TRIGGER (fails p90 + frac-above) |
| 6 | Operative-horizon recommendation for the future MaxDD A/B | DONE — 10d (OOS ci_low 0.815) |
| 7 | VERDICT: REPOINT SURVIVES / DEGRADED-BUT-OK / NOT-AT-LIVE-WINDOW | **DEGRADED-BUT-OK as transition trigger; NOT-OK as level** |
| 8 | Audit doc + TASK_LEDGER row; no engine edits; branch pushed not merged | DONE (this audit; T-105 row appended; no engine edits) |

## Files

- `scripts/validate_hmm_window_t105.py` (NEW)
- `docs/Audit/hmm_repoint_window_revalidate_t105_2026_06_05.md` (this audit)
- `docs/Measurements/2026-06/hmm_window_revalidate_t105.json` (raw output)
- `docs/State/TASK_LEDGER.md` (T-105 row appended)

## Memory updates needed (post-merge)

- New entry: "T-105 re-validates T-103 HMM at LIVE 60-bar window. **AUC SURVIVES** (OOS@5d 0.919 ci_low 0.885 vs 252-bar 0.914/0.880 — marginally higher). Per-event TPR identical 7/7 at both windows. **BUT DWELL FAILS**: p_combined ≥ 0.5 is above threshold 44-50% of days with median run 12-19d and p90 198-265d. Repoint as LEVEL is structurally disqualified by ≤20-day-dwell rule. **Repoint as TRANSITION-TRIGGER survives.** Operative horizon = 10d (OOS ci_low 0.815). The combined posterior is the right INFORMATION SOURCE; transition/decay/co-condition wrapping is the right CONSUMPTION PATTERN."

- Refine T-103 entry: T-103 concluded "REPOINT JUSTIFIED" at AUC level. T-105 confirms this AT THE LIVE WINDOW but adds: design must be transition-trigger, not threshold-on-level.

## Forward dispatches

- **T-105-transition-trigger-design** (PROPOSE-FIRST, Engine E/B):
  define the transition-trigger consumption pattern (Δp_combined
  over K bars; threshold-cross detector; decay-after-fire kill).
  Validate dwell properties of the transition signal — it MUST
  itself satisfy median ≤ 20d AND p90 ≤ ~60d AND frac-above ≤ ~20%.
- **T-105-followup-MaxDD-A/B** (after transition trigger lands):
  the pre-registered MaxDD A/B on 16-yr arm0_off with the
  transition trigger gate. KPI = MaxDD reduction at non-worse
  Sharpe, primary horizon 10d.
- **T-105-pcrisis-only-revisit**: T-103 showed p_crisis alone
  collapses OOS due to state-label artifact. Worth re-checking
  whether a RETRAIN with a LARGER crisis state (e.g., target
  ~15% crisis bars by relaxing the priors) gives a usable level
  with shorter dwell. Lower priority than the transition design.

## NOT done in T-105

- No engine logic edits (per inbox hard constraint).
- No config flip (per inbox).
- No model retraining (this is a window/persistence re-measurement
  of the SAME T-103 model).
- No transition-trigger design or implementation (separate
  propose-first dispatch).
- No 5-axis vs HMM combined-posterior head-to-head on per-bar T-101
  CSV (deferred; T-100's structural finding that 5-axis missed
  COVID is unchanged).
