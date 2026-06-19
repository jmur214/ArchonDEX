# Regime-Conditional Trend Overlay — PRE-REGISTRATION (T-220, 2026-06-19)

**Written BEFORE measurement** (`[NN-MBL]`). Answers ONE question C/T-211
needs: **should T-204's trend overlay be applied ALWAYS, or gated to fire
only in HMM cautious/crisis regimes?** Reuses `core/trend_overlay.py` (T-204)
+ `engines/engine_e_regime/regime_gate.py` thresholds (T-217) — does NOT fork
either. Standalone E-lane sleeve diagnostic; C wires the portfolio.

## Honest prior (stated, not fought)
Absolute momentum is ALREADY self-timing — it goes flat when an asset's own
trend rolls over, which IS a regime response. Layering the HMM regime gate on
top is plausibly **redundant or lagging** → the expected outcome is **~null
(always-on is the right form)**. A clean null is the valuable result: it tells
C "keep the overlay always-on; don't regime-condition it." No lift will be
manufactured.

## The causal regime label (reuse the validated HMM; lookahead-clean)
- **p_crisis** = the causal forward-filter posterior of the crisis state from
  a GaussianHMM on the T-172 deep feature panel (`build_deep_panel`:
  spy_ret_5d, spy_vol_20d, bond_ret_20d, vix_level, yield_curve_spread,
  credit_spread). The forward filter (`_causal_filtered_posterior`, T-089
  lookahead-clean) is reused verbatim from `scripts/regime_oos_loco_t172.py`.
- **Frozen-HMM, train-once on 2000-01→2012-12** (includes dotcom + GFC for
  crisis-state identification = highest-vol state), then the causal posterior
  over the FULL panel. → the 2013+ gating decisions use a HMM frozen on past
  data only (no future leakage); the 2005-2012 span overlaps training (a
  disclosed caveat — it's needed for crisis-state ID). Seed-pinned (SEED=0,
  N_INIT=10, best train-LL).
- **3-state label** via the T-217 thresholds (NOT re-tuned):
  `calm` p<0.30, `cautious` 0.30≤p<0.60, `crisis` p≥0.60.
- **Causal gating:** the gate for day `t` uses `regime_{t-1}` (known at the
  prior close) — same one-bar shift as the overlay signal. No lookahead.

## Testbed + the pre-registered arms (small)
Testbed: the **3-asset EW sleeve** (SPY/AGG/GLD), **5-month lookback** (the
T-204 sweet spot — fixed, no lookback sweep), cash off-leg. Common window =
overlay window ∩ p_crisis availability (~2005 → 2026-04).

| arm | construction |
|---|---|
| **(a) no overlay** | 3-asset EW **buy-hold** (always fully invested) |
| **(b) always-on** | T-204 3-asset EW trend sleeve (overlay every day) |
| **(c) regime-gated** | overlay ACTIVE only when `regime_{t-1}∈{cautious,crisis}`; fully invested in calm |
| **(d) inverse-gated** | overlay active only in **calm**; fully invested in cautious/crisis — the **falsification control** |

(a) and (b) are T-204 re-measurements (already counted). The genuinely-new
structures are (c) and (d) → **N_trials += 2.** ONE lookback, no sweep.

## Metrics (fixed now; via `core/metrics_engine.py`)
Per arm: CAGR, **Sharpe (point + block-bootstrap `ci_low`, 1000 iter, seed=0;
`[NN-SHARPE-CI]`)**, MDD, monthly skew, per-crisis-window drawdown
(GFC/COVID/2022), capture-efficiency vs (a). Plus the regime-label **census**
(below).

## Decision rule (fixed now)
**Does (c) regime-gated beat (b) always-on on the SHAPE axis — materially
lower MDD AND/OR better tail (skew, crisis DD) AND capture-efficiency not
worse — net?**
- If **(c) ≤ (b)** on shape (the expected null): verdict = **"keep the overlay
  ALWAYS-ON; do not regime-condition it."**
- If **(c) > (b)** materially AND the inverse control **(d) is clearly worse
  than (c)** (proving the gate carries real information, not a coin flip):
  verdict = "regime-gating helps — C should gate it." A (c)>(b) that is NOT
  beaten-by-margin over (d) is treated as noise → keep always-on.

## Integrity guards
- **`[NN-FAIL-CLOSED]`:** HALT (raise) if the p_crisis series is missing,
  empty, constant, or degenerate (e.g. one regime ≥ 99% of bars) — a degraded
  regime label must NOT silently pass as a real measurement.
- **`[NN-CENSUS]`:** report the regime-label census — bar-share of
  calm/cautious/crisis, and the crisis-share inside the known crisis windows
  vs calm (the label must concentrate crisis mass IN crises). A degenerate
  census fails the run.
- **md5-deterministic** (seed-pinned HMM + on-disk data); reproduce:
  `python -m scripts.regime_conditional_overlay_t220`.

## Out of scope
- The portfolio COMPOSITION + the beat-the-robo measurement are C's lane.
- OFF-default / canon-unchanged: a new measurement script + reuse of existing
  OFF-default modules; no prod path touched.
