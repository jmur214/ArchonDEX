# Pre-registration note — the HMM production repoint

**Date:** 2026-08-26 · **Agent:** B · Branch `feature/hmm-repoint` · **0 N_trials** (config/plumbing)
**Change:** `config/regime_settings.json` `hmm.model_path` → `hmm_3state_crisis_v1.pkl`
(also the `HMMConfig` dataclass default, so there is ONE answer to "which HMM").

## 1. Live consumers today — VERIFIED context-only, nothing gates

The dispatch required this be verified and listed, not asserted. Full census of everything
that reads HMM output:

| # | consumer | why it does not gate today |
|---|---|---|
| 1 | `advisory.risk_scalar` ← HMM entropy (`advisory.py:204-210`) → Engine B | Consumed **only** in the legacy Path-B `else:` (`risk_engine.py` ~987). Production runs **Path A, which never reaches it**; `advisory_risk_scalar_apply_on_path_a=False`. T-116's comment records that **T-101 proved flipping `hmm_enabled` on did nothing for exactly this reason.** The *field value* changes after the swap; **no production behavior does.** |
| 2 | `hmm_regime_label` → `g_regime` (`signal_processor.py:546-548`) | Only reached when `ensemble.mode == "conjunctive"`. Default is `weighted_mean` and **no config sets conjunctive** — dead path. |
| 3 | `regime_meta['hmm_regime']['probabilities']` (`engine_b_risk/regime_transition_overlay.py:175`) | T-118 overlay, `enabled: bool = False`, no config enables it; T-118 refuted. |
| 4 | `transition_warning` (`regime_detector.py:530-544`) | No consumer outside Engine E. |
| 5 | multi-res daily model = `hmm.model_path` (`regime_detector.py:472`) | `multires_enabled=False`, unset in config. ⚠ **but this repoint does re-point the multi-res daily model too** if it is ever enabled. |
| 6 | `regime_meta["hmm_regime"]` in the detector's output dict | observability/display — context only. |
| 7 | `hmm_p_crisis` | **no live consumer**; every reference is under `Archive/`. |

**Conclusion: the premise holds.** Every path is inert by construction, off by default flag,
or display-only. Engine B is touched by **nothing** in this change.

## 2. Why the swap is drop-in (verified against the artifacts, not the docs)

- **`feature_names` are byte-identical** across both models (7 features), so `feature_set`
  stays `"legacy"`. *The config comment claiming legacy = 4 features was stale — corrected
  against the pickles, which are the authority.*
- **State index order DIFFERS** — `('crisis','stressed','benign')` → `('stressed','crisis','benign')`.
  This is safe **only** because the classifier keys posteriors by label at its own boundary;
  no live code reads a raw state index (verified — only `Archive/` training scripts do).
  Tested, because it is the exact shape of a silent crisis/stressed inversion.
- Both models load and predict on the current panel (observed, not assumed).

## 3. Provenance — and TWO corrections to the dispatch's numbers

**Old:** `hmm_3state_v1` — trained **2021-01-04 → 2024-12-31**, 1,005 obs (essentially one
stress event). **New:** `hmm_3state_crisis_v1` — trained **2006-04-04 → 2019-12-31**, 3,459
obs, **including the GFC**. Deeper, better-conditioned training is the substantive reason.

**⚠ Correction 1 — the old model is not "the AUC-0.49 model".** T-087 measured it at
**p_crisis 5d AUC 0.887 / combined 0.848**. The honest like-for-like comparison on the
combined posterior is **0.848 → 0.914-0.919** (T-103 window_252 / T-105 window_60,
ci_low 0.880). The repoint remains justified; the stated margin does not.

**⚠ Correction 2 — 0.49 is real, but it belongs to the NEW model's `p_crisis` channel.**
T-103's OOS `p_crisis` @5d = **0.497** (CI [0.329, 0.670]) — a coin flip. T-103 pre-stated
its own scope in its header: *"REPOINT JUSTIFIED on combined posterior (p_crisis +
p_stressed)… **NOT justified on p_crisis alone**."*
**Therefore: shelf entries described as "`hmm_p_crisis`-gated" must be armed on the COMBINED
posterior.** Arming them on `p_crisis` after this repoint would gate them on a coin flip.

## 4. Purpose — and the blocker this verification found

Stated purpose: honest arming of the `hmm_p_crisis`-gated shelf entries and
conditional-leverage #3's future consumer. **The repoint alone does NOT achieve that**, for a
reason unrelated to the model:

`tlt_ret_20d` is **NaN for 82.1%** of the feature panel — everything before **2020-05-08** —
because the panel loads `data/processed/TLT_1d.csv`, which **starts 2020-04-09**. Only
**1,493 / 8,361 rows (17.9%)** have all 7 features. On every other bar the classifier hits
`if not np.all(np.isfinite(vals)): return self._uniform_proba()` and returns a **uniform
posterior — indistinguishable from genuine maximum uncertainty**, with no `degraded` flag.
The backtest census does **not** catch it: `regime_unknown_bars` counts `macro_regime`, not
the HMM.

So any shelf backtest conditioning on the HMM over a deep window silently gets a uniform
posterior on 82% of bars — a plausible number that means nothing. **This is the
`[NN-FAIL-CLOSED]` defect class exactly.**

**The fix is a REPOINT, not a rebuild** (`feedback_prefer_repoint_over_rebuild`): a
TR-reconciled TLT going back to **2005-02-22** already sits in `data/processed/tr_reconciled/`.
Measured effect of pointing the panel at it:

| | complete rows | span | 2008 GFC | COVID |
|---|---|---|---|---|
| as-is | 1,493 (17.9%) | 2020-05-08 → 2026-04-17 | **0 bars** | **0 bars** |
| with deep TLT | **5,041 (60.3%)** | **2006-04-04** → 2026-04-17 | **378 bars** | **62 bars** |

**2006-04-04 is exactly the crisis model's `train_start`** — the panel regressed after the
model was trained; restoring deep TLT restores the model's native domain precisely.

**NOT APPLIED HERE — proposing first.** It changes Engine E's feature inputs across all
history, so every measurement reading regime output shifts. That is a substrate change
(`[NN-SUBSTRATE-REVERIFY]` in spirit) and deserves its own review, not a quiet ride-along in
a config repoint. One-line change, ready on request.

## 5. Rollback
Revert `hmm.model_path` (JSON + dataclass default). No state, no migration, no artifact
rewrite — the old pickle stays on disk per `[NN-ARCHIVE]`.

## 6. Tests
`tests/test_hmm_repoint_t_2026_08_26.py` (7) — feature-name identity; index-order difference;
label-keyed posteriors; production config pointer; **the uniform-posterior defect pinned**
(documents current behavior — it SHOULD fail when the fail-closed fix lands); deep TLT exists
on disk; and T-103's combined-vs-p_crisis scope. Plus a lock in
`tests/test_hmm_variant_c_wire.py` that the JSON and the dataclass default can never diverge.
