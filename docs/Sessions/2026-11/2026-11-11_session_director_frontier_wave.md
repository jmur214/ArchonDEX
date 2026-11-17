# Session Summary: 2026-11-11 → 11-12 (director) — the frontier wave, the drip defect, the cutover writer

## What was worked on

- **The user asked how the system could produce only two ETFs (85/15 SPY/MTUM)**, then said "just start working, I'm good with anything". The honest answer: of the ten alpha-frontier tests planned on 2026-09-30, only B-1 and B-3 had run; about 490 commits since then went to the referee, the substrate and ops. This session ran the rest of the queue that could run, all pre-registered first:
  - **B-9 (T-380), multi-factor tilts:** REFUTED, keep 85/15.
  - **B-2 (T-381), small-cap momentum and insider clusters:** both REFUTED.
  - **B-5 (T-382), levered-ETF diversified stacks:** REFUTED; financing is not what binds.
  - **B-10 (T-385), permanent 10% gold:** REFUTED on wealth; its drawdown cut is mostly the 10% held out of equity.
  - **B-8 (T-386), execution timing:** CLOSED WITHOUT RUNNING by pre-data power analysis, N 0.
  - **B-6 (T-383), Lazy Prices:**
    - the T-237 panel was invalid, so it was rebuilt from EDGAR (46,040 S&P filings);
    - the S&P window (d) is NOT EVALUABLE after a census halt;
    - window (c) was not met, but review found a missing §7.7 halt and join defects, and a corrected re-run is in flight;
    - the T-265 arm is streaming.
- **The canonical price cache's pre-seam "drip" was found era-wrong** (health HIGH, `d82f4b8`): it over-counts dividends by ~0.58× yield from 2011 to the seam and under-counts them in 2003–10, and cutover option (a) kept the defect.
  - T-384 built the (a′) fix on a copy. It was reviewed SOUND twice, and the USER RULED it adopted on 2026-11-12.
  - T-387 built it into the cutover writer: byte-identical to the reviewed candidate, label fallback fail-closed, merged as `4354d1e`. No canon write; cutover day stays the user's.
- **The Mac's disk (sixth fill-up):** a deep dive with the user freed 11.5 → 36 GB. The hidden mass was a 17 GB macOS versions store (`.DocumentRevisions-V100`), 16.7 GB of it orphaned. A Recovery-Mode deletion of the iOS 18.3.1 simulator orphan is owed by the user (memory reminder set).

## What was decided

- **USER, 2026-11-11:** the user's Gmail may be the SEC EDGAR User-Agent contact (SEC hosts only), and the LM dictionary download is approved.
- **USER, 2026-11-12:** the cutover ADOPTS (a′) v4 now, labelled as failing its own pre-declared test (on non-dividend Stooq defects), amending the 2026-10-22 option (a). Stooq's spin-offs and transient blocks get a separate repair unit under the same test.
- **Director rulings:**
  - **Ratified B-5's A2.2:** the SDMX −9999 sentinel void was a data-defect correction that ran AGAINST H1.
  - **Lowering a frozen gate after it fires is goalpost-moving, so it was refused.** When a pre-return census halts, the window is set by input availability instead (the B-1 precedent; B-6 (d) → (c)).
  - **A pre-data power analysis that settles the question closes a test without spending N** (B-8).
  - **Every hedge leg's drawdown benefit is scored against a CASH leg of the same weight** (from B-10's reviewer).
- **Process standard for every test:**
  1. a prereg-first worker in a worktree;
  2. the director's acknowledgement;
  3. the run;
  4. a fresh-context reviewer, by execution;
  5. follow-up commits only;
  6. the docs index regenerated on the branch;
  7. `merge_one.sh` in a quiet window;
  8. a push after each landing.

## What was learned

- **Settings' "Documents" figure on this Mac is mostly `~/Dev` plus the dot-folders.** Never move `~/Dev` to iCloud. `sudo du` needs Terminal with Full Disk Access.
- **The merge gate's `data/` write guard trips** ("N passed, 0 failed" with exit 1) when a research agent writes through the shared `data/research` symlink. Merge only when no agent is writing, and have agents write worktree-local.
- **Defects the wave turned up, each found by a worker or reviewer:**
  - **T-249's Sharpe was inflated 4.58×:** `periods=252` was applied to monthly returns.
  - **The T-237 panel:** 40% of its "OK" Item 1A rows were runaway spans.
  - **The T-306 cash leg** is quantized to 1 bp/day.
  - **T-311's hole guard** can never fail, and it forward-fills gold flat.
  - **FRED and the Fed's data feeds:** FRED's `fredgraph.csv` is blocked for this Mac, the Fed retired its custom-package downloads, and the SDMX ND sentinels read −9999.
  - **The honest-N registry** omits standalone-harness trials. The hand count is ≥ 283, against the gate's 231.
- **Reviewers by execution caught real defects in every unit:**
  - a missing §7.7 halt;
  - wrong-format joins (BRK-B vs BRK.B);
  - a label fallback that would have mislabelled every worktree;
  - a no-reference approximation that added dividends to non-payers;
  - overstated circular evidence.

## Pick up next time

1. **B-6 (T-383).**
   - Receive the corrected S&P (c) re-run, with §7.7 implemented, CIK-joined T-265 fills, the fixed parser, and the adjacent-pairing short-leg t reported (t was +2.27 before correction).
   - Send it to the reviewer, then merge.
   - When the T-265 stream completes (~30 h from 11-12), re-census with the FIXED parser, freeze the T-265 arm and run it.
   - The brief's refutation needs both arms.
2. **Cutover day is the user's.** The runbook decisions from 11-05 are still owed, plus (a′) at step S1b and re-pin #2 (+575 files).
3. **The Stooq spin-off and transient-block repair unit** goes under T-384's §1 test.
4. **After cutover, the re-run campaign:** B-1 (re-verify required), the RR-1 29+4, T-123/135/137/150/153/269, T-171/178, and B-4 (the GBM ranker, once B-1's panel is clean). B-7 waits on the HMM repoint.
5. **A candidate from B-6's adjacent-pairing short leg:** a pre-registered NEGATIVE-SCREEN test (exclude recent filing "changers" from a long book). Not yet run.
6. **The disk:**
   - `~/Dev/_substrate_candidates` holds ~8.4 GB, including the redundant T-387 check copy (byte-identical to v4) and the superseded v3 (keep its `yf/`). Deletions are the user's call.
   - The user's iOS 18.3.1 Recovery-Mode deletion is pending.

## Files touched

State, ledger, health and audit docs; merges of B-9, B-2, B-5, B-10, B-8, T-384 and T-387 (see `git log 3df64e1..fa47f05`); `~/Dev/_director_tools/wt_data_layout.sh` now copies `_write_records/`.

## Subagents invoked

- **Workers:**
  - regime-analyst: B-9, B-5, B-10
  - edge-analyst: B-2, B-8
  - ml-architect: B-6
  - quant-dev: the drip investigation, T-384, T-387
- **Fresh-context general-purpose reviewers by execution:** one per verdict. They returned:
  - B-9 APPROVE
  - B-2 NOT READY → APPROVE
  - B-5 NOT READY → fixed by diff
  - B-10 APPROVE
  - T-384 SOUND → SOUND
  - B-6 NOT READY
  - T-387 NOT READY → APPROVE
