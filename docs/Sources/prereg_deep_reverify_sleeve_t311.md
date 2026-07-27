---
task_id: T-2026-07-27-311
title: Pre-registration — DEEP re-verify the trend sleeve (T-255) on the 58-64yr substrate
date: 2026-07-27
worker: Agent B
branch: feature/deep-reverify-sleeve-t311
status: DRAFT — awaiting director FREEZE before any run. N_trials += 1 on run (ONE family, jointly reported).
---

# T-311 pre-registration — does the sleeve's verdict survive the deep window?

## Why this run
`[NN-SUBSTRATE-REVERIFY]` is in effect since T-306. The headline T-255 verdict —
*"the fair sleeve BEATS schwab_like on wealth+Sortino+DD, TIES 60/40 on wealth,
structural win = drawdown"* — now reads **"DEFENSIBLE (prior substrate); re-verify
required."** This is the FIRST and most decision-relevant re-run: the fork-resolution
rule (real capital only when paper-valid AND beating the robo on the honest bar) reads
against THIS verdict, and the ~60-day paper gate matures ~September. The deep window
(2-asset ~64yr / 3-asset ~58yr) is the first that clears MBL, so it — not the
2000–2026 shallow window — becomes the real-money reference.

## This is a RE-MEASUREMENT of a FROZEN config, not a fit (N accounting)
The sleeve is the **already-deployed** configuration — ensemble `{42,105,210}`,
equal-weight, long/flat, the T-255 fair conventions. **Nothing is tuned or searched.**
So this consumes exactly **N_trials += 1** (one family: sleeve vs 3 baselines × 2
substrates, jointly reported). No per-cell inflation.

## Substrate (frozen)
Consume the T-306 deep substrate `data/research/substrate_multidecade/` (regenerate via
`scripts/build_multidecade_substrate_t306.py`; per-splice provenance cited; the deep
bond-synth reproduced the frozen `bond_synth_t255` EXACTLY on 2000–2026 overlap).
- **PRIMARY — D-A 2-asset (equity+bond), 1962-01→2026 (~64yr).** Gold-free is the
  honest *deepest* window (gold floors at 1968). This is the headline.
- **SECONDARY — D-B 3-asset (equity+bond+gold), 1968→2025 (~58yr).** Gold basis is
  confirmed in-spec (LBMA-fix vs gold_gcf: levels match 1.0002, timing-artifact only,
  21-day corr 0.965 → immaterial to a 42-210d sleeve). Restores the deployed 3-asset shape.

Calendar alignment: `core.calendar_guard.reindex_onto` (ffill) onto the equity trading
calendar (legs have native US-market/London calendars) — the established T-255 pattern;
`assert_no_calendar_holes` on the aligned frame before any metric.

## The arm + baselines (frozen — verbatim T-255 fair conventions)
Fair conventions (from `scripts/fair_t236_rerun_t255.py`): ER charged when long AND on
the robo legs (`{equity:0.0009, bond:0.0003, gold:0.0040}` ETF-equivalent); 1.5 bps txn
BOTH sides; flat leg + robo `_cash` earn the short rate (my `cash_daily` = FF RF daily).
- **SLEEVE (the deploying config):** ensemble `pos = mean(binary long-flat signal over
  [42,105,210] days).shift(1)` (causal — T-273 lag), equal-weight over the assets
  (½ each 2-asset / ⅓ each 3-asset); `r = pos·(assetTR − ER/252) + (1−pos)·cash −
  flip·(1/n)·1.5bp`.
- **(a) schwab_like:** `{equity 0.45, bond 0.30, gold 0.05, _cash 0.20}`, monthly-rebal,
  net ER, 1.5bps rebal. Variant A `_cash`@short-rate; Variant B @ (short−125bps) sweep.
  *2-asset primary:* renormalize the gold-free weights → `{0.474, 0.316, _cash 0.211}`
  (disclosed adaptation; the 3-asset secondary restores the full weights).
- **(b) 60/40:** `{equity 0.60, bond 0.40}`, monthly-rebal, net ER, 1.5bps.
- **(c) buy-hold equity** (the SPY-equivalent): 100% equity TR, net ER (the un-timed core).

**Honest cost caveat (disclose in the result):** charging ETF-equivalent ERs on the
pre-ETF deep segment (pre-1993/2005) is anachronistic but CONSERVATIVE (it over-charges
the sleeve+robos symmetrically). The pre-1993 equity leg is broad-market TR (not S&P-500)
per T-306 — labeled as such.

## The questions the deep window answers that 2000–2026 could not
Named **independent crises** the 2-asset window (1962+) now spans — **9**, vs the shallow
window's 4: **1970 · 1973-74 stagflation · 1980-82 Volcker · 1987 · 1990 · dotcom
2000-02 · GFC 2007-09 · COVID 2020 · 2022** (the 3-asset secondary drops 1962-67, keeps
1970 on).
1. **Does the drawdown-structural win HOLD across 9 crises?** (trend-overlay ≈halves MDD
   by mechanism — expected robust, but 1970s stagflation + Volcker are regimes the
   shallow window never tested.)
2. **The 60/40 wealth TIE → win, loss, or hold?** (deep bond bull 1981→2020 vs the
   sleeve's flat-leg cash drag — genuinely uncertain.)
3. **Is the Sortino edge — DIRECTIONAL on 2000-2026 — now CI-SIGNIFICANT at MBL-cleared N?**

## Gates (FROZEN)
Per baseline, paired **sleeve − baseline** on aligned daily returns, **21-day
block-bootstrap, 1000 iter, seed=0** (the [NN-SHARPE-CI] standard):
- **ΔSortino** — sleeve wins iff `ci_low > 0`.
- **Δwealth** (terminal value of $1, lump-sum) — reported with CI; win iff `ci_low > 0`.
- **ΔMaxDD** — sleeve wins (shallower) iff `ci_high < 0`.
Headline metrics also reported per arm: Sortino, CAGR, MaxDD, terminal-$, %underwater,
with the Sortino/Sharpe **bootstrap ci_low** (never a bare point estimate).

**MBL / DSR (state explicitly):** at ~64yr (primary), `T_required = 2·ln(N)/SR²`; at
N≈76 (current ~75 + this trial), required SR ≈ **0.37** — the sleeve's ~1.1-1.2 Sortino
clears it with margin. **The 2000-2026 verdict could not clear DSR; this one does** —
state the honest-N and the DSR margin in the result.

**Verdict rule:** the deep-window result **SUPERSEDES** the 2000-2026 T-255 as the
real-money reference (or CONFIRMS it, if the signs hold). A metric that flips sign or
loses CI significance is reported honestly — a structural win that fails to generalize
across the 1970s regimes is a real finding, not a failure to hide.

## Honest prior (BEFORE the run)
- Drawdown-structural win: **HOLDS** (~70%) — mechanism-robust.
- 60/40 wealth: **toss-up** (the deep bond bull is a strong 60/40 tailwind).
- Sortino CI-significance at deep N: **MEDIUM** — more crises add signal, but the 1970s
  stagflation is exactly where a long/flat trend sleeve can whipsaw; deep N cuts both ways.

## Sequence / N
Draft → **director FREEZE** → run → results + verdict here → outbox. **T-260
(ensemble-speed selection) is QUEUED behind this — same substrate, do NOT start until
T-311 closes** (shared N, honest sequencing). N_trials += 1 on run.
