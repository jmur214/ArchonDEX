# RR-1 RE-SCORE — paired-test pre-registration

N_trials 0. A descriptor of existing RE-SCORE pairs: not a trial, not a gate, no threshold.
Script: `scripts/rr1_paired_delta.py`.

## Part 1 — the anchor (written 2026-10-13, before computation)

Carried verbatim from the scratch pre-registration written before the first computation:

- Inputs: `portfolio_snapshots.csv` of run 4e963bf3 (before, seed-capital getter) and
  0a36df9a (after, cash getter). Daily simple returns of `equity` on the common dates.
- Sanity gate FIRST: each arm's recomputed annualized Sharpe (√252) must reproduce its
  recorded `sharpe` within 0.01. If either fails, STOP — the series is not the controller's.
- Statistic: ΔSharpe = after − before; ΔSortino likewise.
- Method: paired moving-block bootstrap (Künsch) — the SAME resampled block starts applied
  to both arms — block length 19 (the controller's recorded Politis-White length),
  1,000 iterations, seed 0.
- Report: Δ point, 95% percentile CI, share of resamples with Δ ≤ 0. Plus, descriptive:
  share of days with negative cash in each arm.

**Amendments after the first computation, stated as such.** (1) The first ΔSortino used an
RMS downside deviation that did not reproduce the recorded Sortino; the script uses the
codebase's definition (mean / std of negative days · √252) and reports ΔSortino only if both
arms' Sortino reproduce. (2) The script's Sharpe tolerance is 4 decimals (5e-5), tighter than
the 0.01 above; the first computation already met it (0.6048 / 0.8427). Neither amendment
touches the ΔSharpe statistic or its method.

## Part 2 — the three T-196 feature pairs (written 2026-10-13, before any series existed)

- Inputs: each arm's `<cell>_<arm>.series.csv`, captured by the driver from the gauntlet's
  first `treatment_effect_returns` call: the with-candidate book's and the baseline book's
  daily returns, exactly as validate_candidate passed them.
- Sanity gate FIRST: each of the four series (with_candidate and baseline, both arms), on its
  own captured dates, must reproduce the harness row's `with_candidate_sharpe` /
  `baseline_sharpe` to 4 decimals. Any failure: exit 2, no Δ printed.
- Statistics, on the four series aligned to their common dates:
  - Δ with-candidate Sharpe = after − before;
  - Δ baseline Sharpe = after − before (RR-1 moves the baseline book too);
  - Δ contribution = (with − baseline)_after − (with − baseline)_before.
- Method: as Part 1 — the same block starts for all four series, block 19, 1,000 iterations,
  seed 0.
- Report: Δ point, 95% percentile CI, share of resamples with Δ ≤ 0. Interpretation is
  written only after all three pairs are computed.
- Gate pass/fail verdicts are NOT analysed: they remain RR-2-affected on this code.
