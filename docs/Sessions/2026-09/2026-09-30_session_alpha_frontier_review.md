# Session Summary: 2026-09-30 (alpha-frontier review — lead researcher, outsider pass)

**Branch** `research/alpha-frontier-2026-09-30` (not pushed, not merged). Deliverables:
`docs/Sources/alpha_frontier_review_2026_09_30/{00_what_the_machine_is,01_gap_report,02_route_research}.md`,
`docs/Sources/alpha_frontier_program_2026_09_30.md`, `tests/test_referee_repairs_proposed.py`
(16 xfail-strict), `scripts/probe_{gate4_permutation_null,mbl_n_effective,spy_ci_low_kill_threshold,engine_f_retirement_burden}.py`.

## What was worked on
- Phase 0: a one-page statement of what the machine is, from code (universe, data, signal → position
  → P&L → verdict, the deploy candidate).
- Phase 1: adversarial verification of nine seeded apparatus claims (4 confirmed, 4 narrowed, 1 mostly
  refuted) plus 14 defects the prior pass did not list, a strategic-mismatch table against the
  project's own alpha map, the verified never-tried list, and a ranking.
- Phase 2: route research A–J via five web-search passes with a September-2026 free-data liveness sweep.
- Phase 3: a ranked program of 7 referee-repair proposals, 10 free re-runs, 10 forward books, a
  4-item paid tier with triggers, and an honest prior (~25%).

## What was decided
- The referee is NOT modified (constitution). Every defect is a failing `xfail(strict=True)` test plus
  a repair brief; the director/user rule on merges.
- No experiment was run on real returns: `data/` is absent here, the AWS credentials are placeholders,
  and the proxy blocks every market-data host. Every number is from the referee's own code on
  synthetic/calibrated inputs and says so.
- The `git log --all` checks required fetching 234 remote heads (the clone was shallow at 2026-08-28);
  done read-only. No branch holds a fix for any defect found.

## What was learned
- Gate 4's null is a point mass, but it never killed anything: 93/93 recorded candidates died at Gate 1.
  The May-2026 gates audit misdiagnosed it as "mathematically correct."
- The backtester sizes from a frozen `portfolio.capital`; production Discovery overwrites the gauntlet
  verdict. Both invalidate what the equity-book H0 means; neither was known.
- The "straddling" verdicts are paired CIs against zero, not DSR-gated — a lower N_eff flips none.
- Four of five regime refutations used their own 2000+ panel; the HMM backfill landed 08-26 and the
  state docs are stale on it.
- The wrapper (Alpaca IRA: Level 2 options, no crypto, no margin/futures/shorts) retires half of the
  alpha map; the BTC leg's Roth vehicle is IBIT only.
- FRED truncated the HY OAS series to a rolling 3-year window in April 2026; free survivorship-complete
  pre-2016 daily prices do not exist (Norgate $630/yr remains the cheapest honest source).

## What's next
- Director: dispatch RR-1, RR-2, RR-3, RR-7 (P0) and B-1 (the raw-signal decile re-evaluation) first.
- The branch must be pushed by someone with the word to do so; the container is ephemeral.
