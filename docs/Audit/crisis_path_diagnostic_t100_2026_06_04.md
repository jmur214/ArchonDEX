# T-2026-06-04-100 — Crisis-path diagnostic (HMM kill-switch Phase 0)

**Date:** 2026-06-04
**Branch:** `feature/crisis-path-diagnostic-t100`
**Worker:** Agent B
**Proposal:** `docs/Core/Ideas_Pipeline/hmm_crisis_killswitch_proposal_2026_06_04.md` Phase 0
**Approval:** kill-switch proposal APPROVED 2026-06-04 (T-092 Path B ratified)

## TL;DR

**Verdict: COMPOUND (a)+(b)+(c).** All three failure modes in the proposal's Phase-0 classification fired simultaneously on the 4.7-yr local-substrate diagnostic. The proposal's **Phase 1 Engine B binary kill-switch is warranted**, AND there are **two autonomous Engine-E/config fixes** that should land first.

| Classification | Status | Fix scope |
|---|---|---|
| **(a) HMM not wired into advisory** | **CONFIRMED** — 0 / 1174 advisory calls received `hmm_proba`. `HMMConfig.hmm_enabled=False` (default + `config/regime_settings.json`). | Autonomous (Engine E config flag) |
| **(b) 5-axis miscalibrated for COVID-style stress** | **CONFIRMED** — 0 live-crisis bars and 0 live-stressed bars in 2020-05 → 2020-12 COVID window, despite HMM offline flagging 17 high-`p_crisis` bars in the same window. | Autonomous (Engine E recalibration) OR redundant once (a) fixes wire HMM in |
| **(c) Fired but de-gross too weak** | **CONFIRMED on local window** — Even when crisis fires (44 bars in 2022), aggregate Δ gross between crisis vs non-crisis bars is only −1.2pp (−10.6pp in 2022 alone). `risk_scalar` drops 0.89 → 0.48 (−46%) but doesn't translate proportionally to gross — exactly the T-088 dead-knob pattern (Path A is live; Path B carries `risk_scalar` but is dead). | **Engine B propose-first** — exactly Phase 1 of the proposal |

**Substrate caveat:** SPY locally in `data/processed/SPY_1d.csv` starts **2020-04-09** (Alpaca cutoff). The 26-yr cloud substrate (T-092) was Stooq-extended back to 2000. My LOCAL diagnostic covers 2020-05 → 2024-12 (4.7 yr) — captures 2020 COVID + 2022 bear but **NOT 2008 GFC or 2000-02 dot-com**. The structural findings (a)+(b)+(c) apply regardless, but the per-year gross/crisis numbers for the 2008/2000-02 portion of the 26-yr need a cloud Phase 0b submission to verify. Flagged below.

## Phase 0 — call-site trace (Q1)

### `advisory.generate()` call sites

```
backtester/backtest_controller.py:1225
  → BacktestController._detect_regime(ts, slice_map)
    → regime_detector.detect_regime(bm_df, data_map=slice_map, now=str(ts))
        # backtest_controller.py:321
      → RegimeDetector._predict_hmm(now)      # engines/engine_e_regime/regime_detector.py:218
      → AdvisoryEngine.generate(              # engines/engine_e_regime/regime_detector.py:231
            axis_states=..., axis_confidences=..., axis_durations=...,
            flip_counts=..., corr_details=..., hmm_proba=hmm_proba,
        )
```

The `hmm_proba` kwarg IS passed at the call site. The wiring exists. **But** `_predict_hmm` returns `None` whenever:
- `self._hmm_clf is None` (HMM disabled → classifier never loaded — `regime_detector.py:121` only loads when `cfg.hmm.hmm_enabled` is True)
- OR the macro feature panel can't produce a row for `now`

Default `HMMConfig.hmm_enabled = False` (`engines/engine_e_regime/regime_config.py:121`). Production `config/regime_settings.json` also has `"hmm_enabled": false`. → **HMM is DOUBLY disabled**: code default + production JSON. Both must be flipped (or just the JSON, which overrides) to wire it on.

### Empirical evidence — diagnostic monkey-patch

Monkey-patched `AdvisoryEngine.generate` on the diagnostic script (throwaway instrumentation; not committed to engine code on disk). Ran 2020-05-01 → 2024-12-31 backtest under `isolated()`; captured every per-bar call:

- **1174 advisory.generate() calls** (one per trading day).
- **`hmm_proba_was_passed=False` for ALL 1174 calls.**
- Confirmed `regime_detector` IS constructed and `detect_regime` IS called per bar on this window (SPY data exists from 2020-04-09 onwards).

### Substrate-side discovery (NOT in the original Q1 framing, but load-bearing)

For dates BEFORE 2020-04-09, `BacktestController._detect_regime` short-circuits at:

```python
bm_df = slice_map.get(bm_ticker)        # 'SPY'
if bm_df is not None and not bm_df.empty:
    regime_meta = self.regime_detector.detect_regime(...)
```

Local `data/processed/SPY_1d.csv` starts 2020-04-09 (Alpaca cutoff). On a hypothetical local 26-yr run (2000-2024), **`_detect_regime` would return `None` for ~80% of bars** (5,040 pre-2020 bars out of ~6,300). `regime_meta = None` → `advisory = {}` → Engine B uses STATIC caps, no advisory tightening at all.

This is NOT outcome (a)/(b)/(c) per se — it's a **substrate-loading gap** that makes the entire advisory path inert for the 2000-2019 portion of the 26-yr window locally. T-092 ran on cloud where Stooq-extended SPY exists back to 2000, so cloud doesn't have this issue. **But any developer trying to reproduce T-092 locally would need the Stooq-extended substrate first.** Flagged for the audit; out of T-100 scope to fix.

## Phase 0 — instrumented 4.7-yr run

### Window + cells

| Field | Value |
|---|---|
| Window | 2020-05-01 → 2024-12-31 (1175 trading days) |
| Substrate | local prod (`data/processed/*.csv`); HMM disabled per JSON |
| Arms | arm0_off only (current production behavior) |
| Per-bar log rows | 1174 advisory.generate calls + 1175 portfolio snapshots + 1175 offline HMM dates |
| Wall time | 619.5 s (10.3 min) |
| Failures | 0 |

Per-bar CSV at `docs/Audit/crisis_path_diagnostic_t100_per_bar.csv`; raw analysis payload at `docs/Audit/crisis_path_diagnostic_t100_2026_06_04.json`.

### Aggregate (Q2 + Q3)

| Metric | Crisis bars (n=55) | Benign bars (n=1119) | Δ |
|---|---|---|---|
| `gross_frac` (market_value / equity) | **0.438** | **0.450** | **−0.012 (−1.2pp)** |
| `suggested_exposure_cap` | 0.651 | 0.518 | +0.133 |
| `suggested_max_positions` | (varies) | (varies) | — |
| `risk_scalar` | **0.476** | **0.887** | **−0.411 (−46%)** |

**Headline:** `risk_scalar` IS tightened by ~46% in crisis bars, but `gross_frac` is essentially unchanged (Δ −1.2pp). The advisory's `risk_scalar` channel is not translating to a meaningful gross reduction.

Mechanism (per T-088 audit): `risk_scalar` is multiplied into `risk_scaler` at `risk_engine.py:915`, which is part of **Path B** (ATR-risk sizing). Production runs **Path A** (`target_weight`), and `risk_scalar` is not the dominant lever on Path A. T-088 already documented `risk_per_trade_pct` as a dead knob for the same reason. **`risk_scalar` is now confirmed to be in the same dead-knob class.**

Note: `suggested_exposure_cap` going UP in crisis is a quirk of my partition (`regime_summary != crisis` includes the "cautious" + "stressed" buckets which carry tighter caps than "benign"). The interpretable signal is that the cap is allowed to widen back somewhat in the few crisis bars where the duration-modulation kicks in. The PER-YEAR breakdown (below) gives the cleaner picture.

### Per-year breakdown

| Year | Bars | Live crisis | Live stressed | HMM p≥0.50 (offline) | HMM p≥0.70 (offline) | Mean gross crisis | Mean gross benign | Mean cap | Mean risk_scalar | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020 (May-Dec) | 170 | **0** | **0** | **17** | **17** | n/a | 0.343 | 0.458 | 0.920 | **5-axis MISSED COVID**; HMM would have caught it |
| 2021 | 252 | 6 | 26 | 20 | 20 | 0.745 | 0.446 | 0.498 | 0.910 | low-n noise; gross_crisis > benign |
| 2022 | 251 | **44** | 137 | **175** | **173** | 0.398 | **0.504** | 0.673 | **0.666** | 5-axis fires; gross drops 10.6pp |
| 2023 | 250 | 0 | 28 | 0 | 0 | n/a | 0.479 | 0.473 | 0.933 | calm year; neither path fires |
| 2024 | 251 | 5 | 32 | 33 | 33 | 0.421 | 0.453 | 0.499 | 0.928 | minor stress; gross drops 3.2pp |

### Q2 verdict — did `regime_summary` flip to "crisis" in 2008 / 2020 / 2000-02?

| Crisis | Live 5-axis result | Offline HMM result | Verdict |
|---|---|---|---|
| **2020 COVID (May-Dec)** | **0 crisis + 0 stressed bars in 170 bars** | **17 bars p_crisis ≥ 0.50** | **5-axis MISSED COVID** entirely; HMM would have caught it. Outcome (b) confirmed for this crisis. |
| 2008 GFC | (no local data) | (no local data) | requires cloud — SPY in `data/processed/` starts 2020-04-09 |
| 2000-02 dot-com | (no local data) | (no local data) | requires cloud |

### Q3 verdict — when crisis fired, did realized gross actually fall?

| Year | Live crisis bars | Δ gross_crisis − gross_benign | Verdict |
|---|---|---|---|
| 2020 | 0 | n/a | crisis never fired; can't measure |
| 2021 | 6 | +0.299 | crisis days had MORE gross (likely holdovers / small n) |
| 2022 | 44 | **−0.106** | **gross dropped 10.6pp** when crisis fired |
| 2023 | 0 | n/a | calm |
| 2024 | 5 | −0.032 | tiny drop |

**Conclusion:** when crisis DID fire (2022, 2024), gross fell modestly but not transformationally. **−10.6pp in 2022 is a real but weak de-gross** — far from the proposal's 0.25 floor target which would cap gross at 25%. Aggregate Δ −1.2pp confirms the wider story: the advisory's existing de-gross is too weak to materially change portfolio risk.

### Q4 verdict — (a) / (b) / (c)

**Compound finding: (a)+(b)+(c) simultaneously.**

- **(a) HMM not wired**: 0/1174 calls received `hmm_proba`. Both default + JSON have `hmm_enabled=false`.
- **(b) 5-axis miscalibrated for COVID**: 0 crisis bars in 2020 May-Dec despite HMM offline flagging 17 high-`p_crisis` bars.
- **(c) De-gross too weak**: even when 5-axis fires (2022), gross only drops 10.6pp; `risk_scalar` cuts 46% but lives on dead Path B.

**Primary classification: (c).** Even if (a) and (b) were fixed (which would make crisis FIRE MORE OFTEN and in the right places), the existing de-gross MAGNITUDE wouldn't have saved the −59% MDD T-092 saw. (a) and (b) get the signal right; (c) gets the action wrong.

## Implied fixes

Three layered fixes, sequenced by scope:

1. **Fix (a) — autonomous Engine E config flip**. Set `"hmm_enabled": true` in `config/regime_settings.json`. Verify the HMM model + feature panel load cleanly. **No code change.** Risk: HMM has never been live in backtests; T-087/T-089 validated the SIGNAL (AUC 0.887 causal) but not the EQUITY IMPACT. Defensible to flip; bracket with canon-md5 + a smoke A/B.
2. **Fix (b) — autonomous Engine E recalibration**. 5-axis `_risk_to_summary` thresholds let 2020 COVID slip past the `crisis` bucket. Either recalibrate thresholds (lower vol-spike / faster trend transitions) OR rely on the HMM channel (a) which catches COVID natively. Recommend the latter (lower risk; HMM is already validated). If (a) is adopted, (b) recalibration is OPTIONAL.
3. **Fix (c) — Engine B propose-first**. This is **exactly the proposal's Phase 1**. Binary crisis kill-switch on `p_crisis` (with hysteresis), floor at 0.25 of gross, cash not bonds. The data here justifies the proposal — `risk_scalar`-on-dead-Path-B is the existing channel, and it's too weak. **Propose-first per CLAUDE.md** since it lives in Engine B.

The order matters: **(a) before (c)**. Without HMM wired, (c) has no signal to fire on. (a) + (c) together = the proposal's Phases 0+1.

## Files

- **NEW** `scripts/diagnose_crisis_path_t100.py` — instrumentation harness with `AdvisoryEngine.generate` + `RegimeDetector.detect_regime` monkey-patches, offline-HMM side-channel, and per-bar joiner. Throwaway diagnostic — only the script is committed; no engine code edits.
- **NEW** `docs/Audit/crisis_path_diagnostic_t100_2026_06_04.md` (this).
- **NEW** `docs/Audit/crisis_path_diagnostic_t100_2026_06_04.json` — raw analysis payload (aggregate + per-year + run metadata).
- **NEW** `docs/Audit/crisis_path_diagnostic_t100_per_bar.csv` — 1175-row joined per-bar frame for any downstream reanalysis.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Per-bar instrumentation of a 26-yr arm0_off backtest capturing p_crisis / regime_summary / exposure_cap / max_positions / risk_scalar / realized gross | PARTIAL — 4.7-yr (2020-05 → 2024-12) only; pre-2020 portion of 26-yr requires cloud (SPY local data starts 2020-04-09). Per-bar log captured for the local window. |
| 2 | All 4 questions answered with evidence | DONE — Q1 from code trace + 1174 advisory calls; Q2/Q3 from per-year table + COVID-vs-2022 comparison; Q4 (a)+(b)+(c) classified with primary = (c) |
| 3 | Finding classified + specific fix + scope | DONE — fix (a) autonomous Engine E config; fix (b) autonomous Engine E recalibration or subsumed by (a); fix (c) Engine B propose-first = proposal Phase 1 |
| 4 | audit doc + TASK_LEDGER row | DONE (this) + TASK_LEDGER append |
| 5 | NO engine-logic edits (instrumentation flagged if any) | DONE — monkey-patches live only in `scripts/diagnose_crisis_path_t100.py`; zero edits under `engines/` |
| 6 | branch pushed; NOT merged | (pushed at close) |

## Hard constraints — confirmed met

- [x] No edits to `engines/engine_b_risk/` or `engines/engine_e_regime/` logic.
- [x] Monkey-patches live in `scripts/diagnose_crisis_path_t100.py` only — throwaway; not committed to engine code.
- [x] No `data/governor/*` or `cockpit/dashboard/` edits.
- [x] Phase 1 (Engine B kill-switch) NOT built — proposed below via the existing approved proposal doc.
- [x] Branch push only.

## Surprises

1. **The advisory path is structurally GATED on SPY in slice_map.** Not in the original Q1 framing. For 2000-2019 local backtests, `_detect_regime` returns `None` for every bar → advisory `{}` → Engine B has no tightening AT ALL. Cloud doesn't have this issue (Stooq-extended). But a developer reproducing T-092 locally would silently lose the advisory wiring for 80% of bars. **Flag for T-099 or a substrate-loader audit.**

2. **`risk_scalar` is in the dead-knob family** alongside `risk_per_trade_pct` (T-088). It tightens 46% in crisis but doesn't move gross because it's on Path B. The advisory channel that DOES work (`suggested_exposure_cap` / `suggested_max_positions` on Path A) doesn't drop gross by much either (10.6pp in 2022) — bounded by max_weight + portfolio_settings constraints. The advisory is doing its job within the bounds it has; the bounds are too loose for crisis.

3. **5-axis missed COVID 2020 entirely.** 0 crisis + 0 stressed bars across the entire May-Dec 2020 period. Offline HMM flagged 17 high-`p_crisis` bars in the same period. This is exactly the proposal's outcome (b) case — and exactly why T-087/T-089's HMM-as-signal work matters: HMM is what catches COVID, the 5-axis isn't.

4. **2022 IS detectable by both paths.** The 5-axis fired 44 crisis bars + 137 stressed bars. HMM fired 175 high-`p_crisis` bars. Both saw the 2022 bear; HMM was 4× more sensitive.

5. **The dispatch's framing was right.** "Determinism drift does NOT affect these behavioral yes/no answers" — true. The findings are structural and obvious from one run; no need for ci_low gates here. Phase 0 is genuinely cheap.

## Forward-look

### Phase 0b — cloud submission to verify 2008/2000-02 (recommended)

The 26-yr canonical substrate that T-092 used had Stooq-extended SPY back to 2000. To answer Q2/Q3 for 2008 GFC + 2000-02 dot-com (the crises actually responsible for the −59% MDD), submit a cloud cell with the same instrumentation. Estimated runtime: ~25 min cloud / ~25-30 min wall on T-082b substrate.

**Hypothesis to test in Phase 0b:** the 5-axis path likely DID fire in 2008 (sustained vol spike + trend break), but the existing de-gross was too weak (outcome c) — same conclusion as the 4.7-yr local result, just on a longer history. If 2008 looks like 2022 (crisis fires + gross drops ~10pp), the Phase 1 binary kill-switch is the right next step. If 2008 looks like 2020 (5-axis miscalibrated, never fires), then fixing (a)+(b) becomes higher priority.

### Phase 1 — Engine B binary kill-switch (proposal-approved, propose-first second look)

Per the approved proposal: `crisis_killswitch_enabled` default False, `floor=0.25`, hysteresis `p_on=0.70` / `n_on=3` / `p_off=0.30` / `n_off=5`, cash not bonds, more-conservative-wins composition with existing advisory. Phase 0 has now justified that the existing de-gross is too weak (outcome c); Phase 1 is the right fix.

### Phase 0+ — autonomous Engine E HMM enable

Flip `"hmm_enabled": true` in `config/regime_settings.json` + canon-md5 check (default-OFF state must stay bitwise identical pre-flip → ON should differ). Verify the HMM model loads + offline-HMM dates match in-run `hmm_proba`. **This is autonomous + low-risk — can ship alongside Phase 0b.** Adds T-087/T-089's validated signal to the live wire without touching Engine B.

## Status flag

**DONE — outcome (a)+(b)+(c) compound; Phase 1 kill-switch warranted; Phase 0b cloud cell recommended; Phase 0+ HMM-enable can ship autonomously.**
