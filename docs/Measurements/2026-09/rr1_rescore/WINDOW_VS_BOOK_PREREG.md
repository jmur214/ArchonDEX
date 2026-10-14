# RR-1 RE-SCORE — window vs book: pre-registration

Written 2026-10-14 by Agent C, **after** the §4 results and **before** this computation.
Director ruling of the same day: pre-register, commit, then compute; write up every outcome.
N_trials 0: a descriptor of series already recorded. No new backtest is run.
Script: `scripts/rr1_window_vs_book.py`.

## The question

§4 measured RR-1's effect on Sharpe twice, and the two results disagree in sign:

- the 26-year anchor book (`run_isolated`, 2000–2025): **+0.238** [−0.058, +0.508];
- the T-196 foundry baseline book (`validate_candidate` via `run_backtest_pure`, 2012–2024):
  **−0.324** [−0.696, +0.044].

Window and book both differ. This test holds the window fixed: both books, on the same days.

## Inputs

- Anchor: daily `equity` returns of runs `4e963bf3` (before) and `0a36df9a` (after), the series
  that passed §4's sanity gate.
- Foundry baseline: the `baseline` column of the captured `t196_*_{before,after}.series.csv`.
- **Days:** the 3,269 common days of the feature pairs. The anchor's returns are taken on exactly
  those dates; the anchor's equity is NOT reset at the window start, because a return is a return.

## Gates (any failure means STOP: exit 2, no Δ)

1. The anchor series reproduces its recorded full-window Sharpe to 4 decimals (both arms).
2. The foundry baseline column is identical across the three cells within each arm, and
   reproduces the recorded `baseline_sharpe` to 4 decimals.
3. All 3,269 days are present in both anchor arms. Missing days are counted and reported, never
   silently dropped.

## Statistics

The four series (anchor before/after, foundry before/after) are resampled with the **same block
starts**: block 19, 1,000 iterations, seed 0.

- **Primary — the difference-in-differences:**
  D = ΔSharpe_anchor(window) − ΔSharpe_foundry, with Δ = after − before.
- Secondary: ΔSharpe_anchor(window) alone; ΔSharpe_foundry is recomputed as a check against
  §4's −0.324.

Report: point, 95% percentile CI, and the share of resamples ≤ 0, for each.

## What each outcome would mean — fixed before computing

Read the rows in order; the first row that matches applies.

| # | outcome | reading |
|---|---|---|
| 1 | any gate fails | **No result.** Report which gate failed and why. |
| 2 | D's CI excludes 0 | **The two books still disagree within the same window**, and the disagreement is established: RR-1's effect on Sharpe depends on the book, not only on the period. |
| 3 | D's CI includes 0, and ΔSharpe_anchor(window) point ≤ 0 | **The window is the likelier explanation.** On 2012–2024 the anchor book moves the same way as the foundry book; the 26-year anchor's positive point owes something to the years outside 2012–2024. Not established at 95%. |
| 4 | D's CI includes 0, and ΔSharpe_anchor(window) point > 0 | **Unresolved.** The books point in opposite directions within the same window, but their difference is not established; neither window nor book is identified. |

**Null.** RR-1 moves both books' Sharpe by the same amount over the same days (D = 0).
Whatever the outcome, it describes two recorded books on one window. It does not generalize to
other books, and it asserts no mechanism.
