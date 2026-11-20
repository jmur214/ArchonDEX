# Session Summary: 2026-11-19 (director)

## What was worked on

- **T-404's first artifact (09:23 CST).** The 11-18 redeploy (`paper-sha-38d4917`) is verified on all three accounts. The same read found that the general Kalshi archive held ONLY zero-quote sports parlays since June (21,294 of 21,294 rows). My 11-17 "fail-closed" check had counted a zero quote as a price.
- **T-405: the Kalshi archive rebuilt by named macro series.** A builder plus an independent reviewer by execution ran four rounds: the review, then three delta reviews (series dropped between events, a mass-error day that alarmed nothing, the historical-API resolver, and pandas 3's mixed-timestamp NaT). It merged as `49331c7` and `6cf044c`. The first artifact is the 17:30 laptop run: 5,080 markets from 415 series, 99.2 % real quotes, 0 parlays, and the old rows intact.
- **Paper-path fixes merged and the fleet REDEPLOYED on the user's word (T-406, `paper-sha-d56ffa6`).** The redeploy carries the daily run's state-root fix (`231e5c0`, five writers, reviewed APPROVE after 27 drives), the dead-CEF / credit-OAS false-alarm fix (`d56ffa6`, a hand-resolved merge), and T-405. It went to cloud-day :41, offense-sso :23 and ai-trader :11, with an image-only diff and No drift.
- **Free research, on the user's word ("any research we don't have to pay for, let's start").** T-407 (prediction markets as information) and T-408 (post-FOMC Treasury drift) were both CLOSED unrun as pre-run design notes, with no trials spent.

## What was decided

- **The user decided:** merge and redeploy all three fixes tonight; start any free research.
- **Not rolling back T-404,** because the old image saved no Kalshi prices at all.
- **The T-405 follow-up merged BEFORE the 17:30 run** so that the first artifact read the code that stays.
- **T-407 is closed.** Kalshi's free history is rich (candles back to 2021) and its forecasts are good, but stocks and bonds price the same information and the surprise lands at 08:30 ET, before the book trades. The bar needs 600–2,400 releases against about 5 years. The H1 validity check (showing the numbers only) runs only if the owner wants it.
- **T-408 is closed.** The drift scales with the Fed's surprise, which forward guidance has shrunk threefold, so the pass probability is ≤ 1.2 %. The direction-only form is rate-cycle (regime) timing and joins the stay-dead class.
- **The T-394 test was fixed** to pass `--min-free-gb 0`; it had depended on the host's free disk (`447c467`).

## What was learned

- **"Present is not priced."** A check on not-null passes a field that is present but empty. Open real rows and count their categories before calling an archive fixed (memory: `feedback_present_is_not_priced_2026_11_19`).
- **pandas 3 infers a datetime format from the first value** and silently turns the other shape into NaT. Kalshi returns two shapes. Use `format="ISO8601"`.
- **Kalshi moves settled markets to `/historical` after about 61 days.** The live API then 404s, and a 404 is not "gone".
- **I attributed an artifact to code by the merge time I had planned,** not the actual one (the CEF merge landed at 19:55, after the 17:30 run). Read the reflog first.
- **I put line breaks inside a ledger row again.** A row is one line.
- **Disk is about 7 GiB free.** A test hit the 11 GB floor, and the user was asked to clear four /tmp review copies (~1.5 GB).

## Pick up next time

1. **T-406's first artifact (2026-11-20, after 09:55 ET; scheduled read at 09:23 CST):**
   - heartbeats on :41 / :23 / :11;
   - the kalshi line with about 415 series and no FAILED;
   - the cloud altdata reason without cef / credit_oas;
   - `fleet_health`;
   - news panel and alt-data reaching S3;
   - the T-401 books.
2. **The first Kalshi OUTCOMES** (`kalshi_resolutions.parquet`) from the 11-20 17:30 laptop run. That run is also the first without the CEF alarm (verify should be 0). Close T-405 when both are read.
3. **Open, the user's:**
   - the account 2 reset (option B ready; start size undecided), then the T-401 mirror fixes;
   - where the real money sits (both audits' top item);
   - the paid-data and leverage-belief research lines.
   Every free research line from the 11-14 audits is now closed.
4. **Small owed fixes:**
   - `news_panel._creds` loads the main repo's `.env` (health MEDIUM, propose-first);
   - `config/fomc_calendar.json` 1994-04-18;
   - the FRED keyless host used by `build_multidecade_substrate_t306.py`;
   - the damped-offense book (feed or retire).
