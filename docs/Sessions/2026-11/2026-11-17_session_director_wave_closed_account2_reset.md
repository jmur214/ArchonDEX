# Session Summary: 2026-11-14 → 11-17 (director) — the class-(1)/(3) wave closed; the split fix's first artifact; account 2 ruled RESET

A weekly usage limit stopped the session from about 2026-11-14 01:20 to 2026-11-17. The T-398 and B-6 agents were killed at the stop and resumed on 11-17.

## What was worked on

- **Honest N, made real (T-391 merged, `9fed69f`).** The gate reads **N_eff 372.28**: the executed runs' 40.28, plus the registry's 231 at raw, plus 101 standalone trials at raw. The required Sharpe is 1.325 / 0.855 / 0.581 at 5 / 12 / 26 years. The `[NN-MBL]` text in `CLAUDE.md` and `NON_NEGOTIABLES.md` was updated with the user's approval (`685d763`). From now on, every closed ledger row needs a row in `config/honest_n_trials.json`.
- **The four lines opened on 11-14 are all closed:**
  - **T-400** (`b5a497d`): the two-account household study was delivered. Its gains are small and certain; the largest is an HSA, if the plan qualifies.
  - **T-399** (`b0e8861`): T-315's static-leverage arms had charged the annual rebalance cost every day. After the fix, no fixed leverage beats or loses to 1× with confidence. The old "1.25× significantly loses" claim is withdrawn.
  - **T-395** (`39c47aa`): closed without running. No broker offers an election API, and Alpaca charges $100 per election.
  - **T-398** (`a1e2f81`): refuted. The stacked trend overlay on investable net-of-fee funds gains +0.37 %/yr, with an interval of [−3.89, +4.17]. Two review rounds; the round-2 fixes changed text only.
- **The split fix's first artifact (T-397, `fc7254b`).** On 11-17, one day late because of the limit, all three heartbeats carried the v2 `corporate_actions` block. Accounts 1 and 3 are canonical 3/3. Account 2 froze MTUM, as designed.
- **The account 2 reset runbook** was drafted on the branch `docs/account2-reset-runbook` (`a5cf0b8`). It is not merged; it is propose-first.
- **B-6 (T-265 arm).**
  - The 252-firm gap fill ran clean: 11,195 filings, 0 failures.
  - The fill's pairing rates came in 4–8 points HIGHER than the panel's on 4 of 11 rates, plus 10-Q Risk OK at +3.4. That fails the two-sided 3-point tolerance in amendment 7. The worker stopped, as the rule required.

## What was decided

- **USER:**
  - The `[NN-MBL]` replacement text is approved.
  - Account 2 = **RESET** (2026-11-17). The broker's balance is not a valid seed: the paper broker scaled the 18 split-day shares by four, a ~$3,500 phantom, and the account holds ~$103.5k against a $10k–$11,166 tier.
  - The user has not yet chosen how to reset, so two questions are open:
    - **U1:** option B (sell everything and keep the account; my lean) or option A (a new Alpaca paper account).
    - **U2:** keep the $11,166 contributed cap (my lean) or re-base to $10,000.
- **DIRECTOR — B-6 condition (a).** I declined both of the worker's readings: reading the tolerance one-sided, or applying it only to the carve rates. Each rewrites a rule after seeing which side the data fell on. Instead I ordered ONE pre-written, population-controlled check, committed as amendment 8 before any count is computed:
  - It removes only "no prior filing" and "Item 1A not covered" from the denominator.
  - The band stays 3 points, two-sided.
  - If any conditioned rate fails, the arm does not freeze, and there is no second check.
  - The freeze becomes amendment 9, carrying +2 N_trials, recorded on main by the director.

## What was learned

- **Chain both lints with `&&`.** `748818a` was committed with the trials check red because the lints and the commit were chained with `;`. An unfrozen draft prereg states no trial count.
- **A tolerance on a rate that depends on how long firms have been filing measures the population, not the parser.** Split the two kinds of rate before seeing the data. (This is in the B-6 worker's memory too.)
- **The privacy plugin (`cc-plugin-privacy`) refuses any shell command that names a script holding the user's email.** SEC Archives work must read its contact from an environment variable the user sets. The B-6 fill did not need it.
- **My own first reports overstated three times; each was corrected to the user:**
  - T-399: I said every arm was ahead on point.
  - T-398: I relayed "25 % behind / 7 years behind".
  - Account 2: I said "$3,500 on a $10,000 account".
  - The lesson: read the frame (window, base, denominator) before relaying a number.

## Pick up next time

1. **Account 2:** the user's answers to U1 and U2. Then:
   - an independent review of the runbook and the liquidation script;
   - execution on the user's word;
   - D+1 seeding run (exit 70) and the D+2 arrival artifacts;
   - the epoch line.
2. **B-6:** receive the amendment 8 check, then either the verdict (independent review before merge; record T-265 +2 against amendment 9's hash) or a stop.
3. **Fleet repairs to propose:**
   - the F9 mirror base-cap defect (the mirror uses the base cap, not the contributed cap);
   - the `momentum_satellite` and `quality_satellite` book files, corrupt from 2026-11-05;
   - retiring `damped_offense_t298` (the owner's decision).
4. **Owner decisions still open:**
   - where the real money sits;
   - school funding and HSA eligibility;
   - $39/month data (T-374);
   - T-392b;
   - the cutover choices;
   - the T-277 watcher (likely retire);
   - an optional notify-only odd-lot watcher.
5. **Worktree cleanup** of merged branches (T-391, T-398, T-399, T-395, the reviewers) needs the user's OK. A removal deletes directories whose `data/` holds symlinks into shared data.

## Files touched

`git log --first-parent 8ad1a52..8dae2d9` on main:
- the ledger, `CURRENT_STATE.md`, `forward_plan.md`, `config/honest_n_trials.json`;
- `CLAUDE.md` and `docs/Core/NON_NEGOTIABLES.md` (`[NN-MBL]`);
- the T-315 audit;
- the T-398 verdict;
- the T-400 study.

## Subagents invoked

- **regime-analyst:** T-398 (two review rounds); T-399.
- **edge-analyst:** T-395.
- **ml-architect:** B-6 (gap fill, T-265 census on the harness grid, T-265 harness, built but never run on a price).
- **risk-ops-manager (worktree, propose-first):** the account 2 reset runbook.
- **general-purpose:** reviewers by execution (T-391 refresh, T-398, T-399).
