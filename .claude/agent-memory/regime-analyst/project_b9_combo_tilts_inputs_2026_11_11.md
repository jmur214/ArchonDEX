---
name: project-b9-combo-tilts-inputs-2026-11-11
description: B-9 (T-380) VOO/MTUM/AVUV multi-factor tilt test REFUTED (arm 60/20/20 ci_low −0.24, t 1.24 vs predicted 2.2); why the power premise failed (value-leg TE 20% not 8%, long-only active ρ −0.07 not −0.3); no local TR for VOO/MTUM/AVUV; deployed mix is 85/15
metadata:
  type: project
---

**Outcome (2026-11-11, branch `research/combo-tilts-b9`, prereg `16432da` + amendment `60e51a5`):**
H1 NOT MET. Arm (i) 60/20/20 vs 1× SPY-TR, 2000-01→2026-06: Δ log TW +0.279, ci_low −0.241
(block 7), −0.477 (block 60). No arm cleared, incl. momentum-only 80/20 (ci_low −0.093) and the
deployed 85/15 REF (+0.079, ci_low −0.066). French-only 1963–2026: all signs +, all block CIs
straddle (REF 60-blk ci_low +0.009 the only positive). Verdict: `docs/Audit/b9_combo_tilts_verdict_2026-11-11.md`.

**How factor edges actually behaved (the reusable lesson):**
- **Long-only tilt legs do NOT inherit long/short factor correlations.** value×momentum L/S ρ ≈ −0.3
  (AMP 2013), but the long-only legs' active returns vs SPY correlated −0.07 — size/beta deviations
  dominate. Any "diversified tilts = more power" argument must use the measured long-only active ρ.
- **Small-value active TE vs SPY ≈ 20%/yr** (French `SMALL HiBM HiOP` cell, 22–55 firms; and AVUV
  vs mega-cap S&P), not the 8% assumed. Momentum (BIG HiPRIOR / MTUM) TE ≈ 8.6% — as assumed.
- **Regime dependence:** arm (i)'s whole gain came 2000–2013 (value-friendly, haircut French era);
  relative wealth peaked 2014-06, −25% to 2020-03, still below peak after 12y. The mega-cap-growth
  regime is exactly where a small-value tilt bleeds — a 15-yr regret window catches it.
- Momentum-alone at 15–20% has the smallest regret (−4–6%, recovered 5.4y) but is "positive, not
  significant" on 2000–2026 with a 50% haircut — B-9 does NOT re-confirm T-320's CI-excludes-0.

**Inputs (reusable for any ETF-tilt study):** no local TR for VOO/MTUM/AVUV (raw Stooq is
partially dividend-adjusted — refuse it); TR = yfinance Adj Close via
`scripts/reconcile_stooq_tr_t256.py:fetch_yf_tr` only (its `reconcile()` writes into
`data/processed/tr_reconciled/`, a symlink to main in worktrees). Snapshot once with md5s; the
director required a per-ETF dividend check (Adj−Close CAGR gap in [0.3%, 4%]) — measured VOO 2.0%,
MTUM 1.4%, AVUV 1.9%. Deployed mix = VOO 85 / MTUM 15 (`config/deploy_candidate.json`).

**Why:** future tilt/allocation proposals will re-propose value or multi-factor sleeves.
**How to apply:** don't re-propose multi-factor value+momentum at deployable weights without a NEW
pre-registered construction (e.g. a broader small-value cell) and its own N; quote the 20% TE and
ρ −0.07 when anyone argues the power case. Related: [[project_macro_signal_lead_coincident_classification_2026_05_06]].
