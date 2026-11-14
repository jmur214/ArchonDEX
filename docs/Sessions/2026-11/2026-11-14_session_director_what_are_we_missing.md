# Session Summary: 2026-11-12 → 11-14 (director) — cutover prep, then "what are we missing?"

## What was worked on

- **Cutover prep, built until blocked (user: "start building; I'll make the call only once you can no longer keep working").**
  - T-388 — the S3 guard switch-on: reviewed in three rounds. Its review found `scripts/audit_data_gaps.py` rewriting every canonical csv; that script is archived.
  - T-389 — the P6 pairs pin.
  - T-390 → T-393 → T-394 — the Stooq repair unit. It found a defect in the already-merged `era_tr` writer (yfinance's double-counted spin-offs; DHR 2016 +75 % vs +13 %). The defect was fixed, and 11 T-265-confirmed corrections were wired in. The cutover substrate is now **(a′) v5 + Tier 1**, in code on main.
  - T-391 — honest N, corrected to **371** (reviewed four times; held on a branch).
  - T-392 — the fundamentals toy fixture, fixed and merged; the registry `--check` change, reviewed and held.
- **The Mac's disk:** the user deleted the iOS 18.3.1 simulator orphan from Recovery Mode (10 → 25 GiB free). 26 merged agent worktrees were removed with the user's OK.
- **"What are we missing?" (user, 2026-11-14).**
  - Two independent audits: a fresh-eyes audit, and a salvage audit of ~60 kills.
  - New lines opened:
    - T-395 — odd-lot tenders as a dollar study;
    - T-396 — a lifecycle-leverage design note (it found a cost bug in T-315);
    - T-398 — the stacked trend overlay on investable funds;
    - T-399 — the T-315 correction;
    - T-400 — a two-account household design study.
- **The split fix: merged (`716ca04`) and deployed to the three live paper accounts on the user's word.** Image `paper-sha-716ca04`; jobdef revisions :39 / :21 / :9; No drift.

## What was decided

- **USER:**
  - Adopt the (a′) fix for the cutover (2026-11-12).
  - Cutover date: after B-6's stream.
  - "Deploy the fix" (the split fix, to paper).
  - The constraints are negotiable — "the goal is anything that can be automated".
  - The account may grow past $35k with trust.
  - Run a taxable and a Roth account as ONE system.
  - "No stone unturned — a broad kill may hide a slim case."
- **DIRECTOR:**
  - The gated honest-N rule is R3 (ruling 9.2, no borrowed correlation credit): **371, not 177**. This was my own correction after the user asked me to double-check.
  - Land every substrate change BEFORE any re-run.
  - Tier 1 only for the Stooq corrections (11 rows with a second vendor's measurement); 1,579 unverified rows stay labels.
  - A defect-corrected re-run of a frozen prereg consumes no new trial.
  - The cutover is deprioritised behind class-(1)/(3) work.
- **The diagnosis both audits reached independently:**
  - At N_eff ≈ 371 the required Sharpe is 2.96/√T. A true 2 %/yr long-only edge passes about 3 % of the time on ≤ 26 years.
  - Only three classes can pay: structural gains needing no test; century-long premia where the question is the owner's belief; per-event niches.
  - 85/15 is the prior, not a finding.

## What was learned

- A batched "yes to all" needs each line re-checked against prior rulings, branch staleness and re-verify cost. Three of my calls were wrong or incomplete when the user asked.
- Reviewers by execution keep paying. Recent catches:
  - an unrouted writer of the whole price cache;
  - a merged writer adding double-counted spin-offs;
  - a rule that removed real dividends;
  - a honest-N rule that omitted 252 executed runs.
- A design note with no backtest found a real bug: T-315 charged its annual rebalance cost daily (`PeriodIndex.shift`), so "1.25× significantly LOSES" does not survive.
- `GOAL.md` keeps the real money in a robo until paper trading proves outperformance — evidence paper trading cannot produce (3-year MDE ~4.4 %/yr).
- The "Roth retires half the alpha map" claim is not supported by the kill record.
- Disk: three concurrent agents grow swap to 6+ GB. `/private/tmp` (the scratchpad) is wiped on reboot.

## Pick up next time

1. **Monday 2026-11-16 after 09:55 ET — the split fix's first artifacts.** Read each account's first `corporate_actions` heartbeat block and the exit-70 seeding pages; run `python -m scripts.fleet_health`; close ledger row T-397. Then ask the user about account 2: reset, or a journaled basis adjustment.
2. **Receive and review:**
   - T-398 — prereg, then the run on investable trend funds;
   - T-395 — census and prereg;
   - T-399 — the corrected T-315 tables, and the State lines to replace;
   - T-400 — the household study, to present to the user;
   - B-6 — the pre-data H_OOS amendment, then the T-265 census and freeze.
3. **Merge T-391 after its refresh** (referee delegation). The `CLAUDE.md` `[NN-MBL]` replacement text needs the user's approval. T-392b awaits the user.
4. **For the user's decision:**
   - where the real money sits;
   - the two advisor-memo questions (school funding; HSA plan);
   - retiring the never-fed `damped_offense_t298` book;
   - $39/month survivorship-free data, or university access (T-374);
   - the five cutover choices, if the cutover is still wanted.
5. **Restart or retire the T-277 special-situations watcher,** after T-395 reports.

## Files touched

See `git log 75da10c..HEAD` on main (state, ledger and health docs; merges of T-389's pin tool, T-392a, T-393, T-394 and the split fix). `~/Dev/_director_tools/wt_data_layout.sh` now copies `_write_records/`.

## Subagents invoked

- **quant-dev:** T-384 … T-394, T-388, T-389, T-391, T-392.
- **regime-analyst:** T-396 / T-399, T-398.
- **edge-analyst:** T-395.
- **ml-architect:** B-6.
- **general-purpose:**
  - reviewers by execution, one per unit;
  - the fresh-eyes audit;
  - the salvage audit;
  - the T-400 design study.
