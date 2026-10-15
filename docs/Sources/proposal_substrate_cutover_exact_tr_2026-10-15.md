# Proposal: cut the canonical substrate over from the T-082b drip to EXACT total return

**For:** Agent R (review), then the director, then **the USER**. A change of the canonical
substrate is the user's decision. **Status:** PROPOSAL ONLY. The drip stays canonical until the user
rules. Nothing in the real `data/processed/` has been written. **N_trials: 0.**

**Direction already ruled** (director, 2026-10-15): exact ex-date total return is the honest form of
the TOTAL RETURN convention. But it is a **planned cutover**, not a refresh. The convention guard
switches on **on cutover day, all files at once, never before**, because its
`RESCALED → full re-fetch` path would otherwise adopt exact total return file by file, leaving a mixed
universe.

**Evidence base:** the merged writer `engines/data_manager/tr_writer.py` (main `8616f93`: one
provider for the universe, and the overlap refusal), run on a COPY of the cache at
`/Users/jacksonmurphy/Dev/_substrate_candidates/processed_exact_tr_2026-10-15/`. All paths below are
under `/Users/jacksonmurphy/Dev/_substrate_candidates/`:
- **the real cache, never written:** aggregate md5 `8ead63bc2271b38fc7adf56a0aa2918c` (2,172
  files), BEFORE and AFTER the write pass, identical;
- **the copy:** md5 `cb1ceca4…` before the write pass; `40f30344…` after the main pass (1,260 files
  changed = 630 written × csv + parquet); `2418dc67…` after the shared symbol table merged (main
  `47aca8a`) and BRK.B and BF.B were written (4 more files). Write log `write_log_2026-10-15.jsonl`
  (632 records); per-file outcomes `write_pass_2026-10-15.jsonl` (730 files, latest row per file);
- **the inventories, latest row per file:** `measure_2026-10-15.jsonl` (730 files; its first pass
  routed by span, see §2a), `measure_2026-10-15_yfinance172.jsonl` (the 172 Alpaca-routed files
  re-measured on yfinance), `measure_2026-10-15_retry.jsonl` and `retry_2026-10-15.log` (the serial
  retry of every error row, with yfinance's own stated reason per symbol kept unfiltered);
- **an independent current status:** Alpaca's asset endpoint, read-only, for every file yfinance
  could not fetch (`asset_status_2026-10-15.json` in the agent's scratchpad, quoted in §2);
- **how §3 was enumerated:** a READ-ONLY subagent read the code and classified about 40 candidate
  files. Agent B verified every weight-bearing claim BY HAND:
  - the paper path's reads and bakes;
  - the T-306 SPY reads;
  - the RR-1 constants;
  - the manifest counts and verify;
  - the submit gate;
  - the workflow's S3 prefix;
  - the canon anchors;
  - the four tests that turned out not to be pins.

  The rest are cited path:line from the subagent's read.

---

## 1. Finding one: the cutover changes per-name RETURNS — as DISPERSION across names, not a systematic shift

T-082b's `apply_dividend_strip` gave pre-seam history a smooth constant-yield drip. Replacing it with
exact ex-date total return does not just move price levels: it moves each name's pre-seam RETURN.
Measured as exact minus drip, annualised log return from the file's start to its seam, over all 559
files with a pre-seam span (yfinance throughout):

| percentile | p1 | p5 | p10 | p25 | **median** | p75 | p90 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| exact − drip, %/yr | −3.32 | −1.88 | −1.34 | −0.71 | **−0.10** | +0.08 | +0.58 | +0.90 | +2.03 |

The median is near zero (mean −0.28%/yr; 36% of names positive), so the drip is **not** a systematic
under- or over-count across the universe. What the cutover adds is **dispersion**: 102 of the 559
names move by more than 1%/yr in one direction or the other. XOM's +1.98%/yr, the trial that first
surfaced the effect, sits at the 98.7th percentile, a tail rather than the typical name. *(This
section's first wording, "the drip under-counted dividends", generalised from that tail and is
withdrawn.)*

**Consequence: every pre-2018 equity-book number is still a RE-QUALIFICATION, not a relabel.**
Equity-book verdicts are cross-sectional (deciles, ranks, long/short spreads). A per-name return
shift reorders names, and that moves a cross-section even when the median shift is near zero.
*(Wording endorsed by R and adopted by the director, 2026-10-15.)* Post-seam the cache is already
exact: see §4.

## 2. Finding two: delisted names cannot be re-fetched, so a naive cutover splits the universe on SURVIVORSHIP

yfinance returns **nothing** for delisted tickers. **Measured: 75 of the 730 files (10.3%) are
unfetchable.** The pass first found 78 files yfinance would not serve. Every one was retried serially
after the re-measure ended (3 tries, 10/20/30 s backoff): none recovered, and the log holds no
rate-limit message. Each failure carries yfinance's own reason, and Alpaca's asset endpoint gives an
independent current status:

| of the 78 | files | yfinance says | Alpaca says | resolution |
|---|---|---|---|---|
| **share-class spelling** | BRK.B, BF.B | "no timezone" / "no price data" for the dot form | ACTIVE | **written**: Yahoo spells a class with a dash; the shared symbol table (main `47aca8a`) fetches BRK-B and BF-B (§2b) |
| **ticker change** | BK | "no price data found" | BK unknown; **BNY ACTIVE** ("Bank of New York Mellon Corporation") | BK → BNY; identity across the change is the declared class's ruling (§2b) |
| **delisted** | **75** | 45 "no timezone found", 30 "no price data found" | **none ACTIVE**: 50 INACTIVE, 25 unknown | unfetchable from the universe provider |

By cache end date, 66 of the 75 ended early, before the substrate's common end dates (2026-04-17 and
2026-04-24). 9 ended **on** a common date: AVB, CTRA, EA, LEG, QRVO and WBD (INACTIVE on Alpaca),
EQR and MHS (unknown to Alpaca), and CA (INACTIVE, now an Xtrackers municipal-bond ETF; the cached CA
starts 2023-12-15, a reused ticker). A common end date proves a name was listed **at the snapshot**,
not today: these 9 delisted between the 2026-04-24 snapshot and the pass. The trial's ABMD, ABS, ALXN
and ANSS are among the 75.

A naive cutover would therefore move live names to exact total return and leave delisted names on the
drip. The survivorship-corrected universe would be split into two conventions **exactly along
survivor status**. Given finding one, that is not a cosmetic split: it converts the existing upward
survivorship bias into an upward bias whose SHAPE differs by survivor status.

**This proposal rules nothing on it.** The three candidate treatments, with their consequences:

| option | what it does | consequences |
|---|---|---|
| **(a) One convention everywhere: keep the drip, labelled universally** | No cutover of deep history until a delisted-capable total-return source exists. Every deep history is labelled "drip (constant-yield approximation)", everywhere. | Homogeneous and survivorship-consistent. **Knowingly keeps** the dividend under-count (finding one) in every pre-seam number, labelled rather than fixed. Post-seam is already exact. Cheapest; no re-qualification beyond the label. |
| **(b) Exact where available, drip where not, with a per-name convention field** | Live names cut over; delisted names stay on the drip. Each file carries a `convention` field (`exact_tr` / `drip`); the **census reads it**, and every equity-book measurement reports the split (share of names, share of weight, on each convention). | The most exact per name. The universe is **mixed by construction**, and the mix correlates with survivor status, so a long/short or cross-sectional result can partly reflect the convention split. That is visible because it is reported, but it is a confound. A census field becomes a referee change. |
| **(c) Buy a survivorship-complete total-return source** | Acquire a source that covers delisted names with exact total return (the B-1 prereg's re-verification clause already names this path). One provider, one convention, the whole universe. | The only option that is exact AND homogeneous. Costs money and is a new external dependency (a propose-first gate under CLAUDE.md), plus provider evaluation and a manifest of its own. Until it lands, (a) or (b) must hold. |

## 2a. The provider rule: ONE provider for the whole universe (C-1's per-span rule overturned by measurement)

The writer was first built to C-1's per-span rule: Alpaca (`adjustment="all"`) for files whose span
starts on or after 2016, and yfinance for deeper files. The first measure pass overturned it. The
project's Alpaca feed is IEX, and its daily history starts **2020-07-27**:

- of the 172 files the rule sent to Alpaca, **69 came back empty**;
- **69 of the 103** that returned could not cover the cached span (52 of them start exactly on
  2020-07-27);
- **99 of the 103** read DIFFERENT_CONVENTION against the cache, because an IEX tail is not the tape
  the cache was built from.

**Ruled (director, 2026-10-15), and confirmed by the re-measure:** one provider for the whole
universe, **yfinance**. Of the 104 Alpaca-routed files yfinance served, **103 cover the cached span**
(Alpaca covered 34 of 103); the one that does not, NFX, is a reused ticker (§2b). The writer has no per-file route. The Alpaca writer
provider is archived (`Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py`), and a providers
map without yfinance is refused (`af97347`). The span check and the two-mode basis measure stay.

## 2b. Files the writer REFUSES, and what each class needs at cutover

The writer refuses to replace a file unless the re-fetch covers the cached span AND agrees with the
last 252 cached bars up to a rescale (`3618688`). Agent R reproduced the gap this closes: a split-only
provider's two modes are identical, so the basis measure reads "unverified" (exactly as for a
non-payer) and, unguarded, the writer replaced a total-return cache with a nominal series under a
clean write record. The window is a trading year because a 40-bar tail is blind to any payer whose
last ex-date is older than the window: inside it, a total-return tail and a split-only tail are
identical.

**The write pass** (the merged writer, on the copy, every file's data chosen by its latest inventory
row, no non-yfinance row replayed) gives every one of the 730 files an outcome:

| outcome | files |
|---|---|
| **written** | **632**: 475 RESCALED (the steady state), 157 APPEND (incl. BRK.B and BF.B, under the shared symbol table) |
| refused: DIFFERENT_CONVENTION | 5: AGG, EFA, VNQ, AMCR, CPWR |
| refused: span | 17: BBBY, PSKY, NFX; DAL; C, INTC, JPM, ELV, MAR, PLD, AXP, WMT; CHTR, KDP, TDC, UAL, WU |
| ticker change, held | 1: BK (below) |
| unfetchable (delisted) | 75 (§2) |

The refusals, by class:

| class | files | why refused | treatment at cutover |
|---|---|---|---|
| **Split-only in the canonical cache** | **AGG, EFA, VNQ** | DIFFERENT_CONVENTION. One writer, `scripts/backfill_t052_macro_data.py`, wrote exactly these three with `auto_adjust=False`; the yfinance/cache ratio steps up at every ex-date | **Adopted:** a DECLARED split-only path. The declaration is verified against the provider's split-only mode, recorded, and only then is the file re-fetched over its whole span. Not built. |
| **Mixed-convention cache** | **AMCR** | DIFFERENT_CONVENTION. log(yfinance TR / cache) is constant at −0.0614 from 2018 through 2025-09-04, then steps +1.5% on 2025-09-05 and again on 2025-11-28 (each about one quarter of AMCR's dividend), and is constant after: the cache applied total return, then missed two ex-dates | **Adopted:** a whole-span re-fetch after a declared check, as for the split-only trio. **Open:** which writer produced that tail (the guard proposal's writer inventory, §4) |
| **Ticker change, held for the declared class** | **BK** (→ BNY) | Under the merged writer: "the provider returned no bars" (Yahoo BK is empty). The **evidence for BK → BNY**: Alpaca has no BK, and BNY is ACTIVE ("Bank of New York Mellon Corporation"); log(BNY TR / BK cache) is CONSTANT at −0.0088 from 2018 through 2025, with no step; against BNY's split-only series the cache shows all 33 ex-date steps (so the cache is total return and BNY is the same security). With BK → BNY tried in the table (measure-only, never merged), the rail **still refuses**: DIFFERENT_CONVENTION over 252 bars, two steps of +0.042% (2026-01-20, 2026-02-06), about a tenth of a BNY dividend, an adjustment-factor disagreement | **The declared class.** The table encodes what the writer may USE, and this entry enables no write, so it is not in code (R, adopted by the director, 2026-10-15). The entry lands WITH the class on cutover day; the rail is not loosened |
| **(i) Ticker reuse — identity** | **BBBY, PSKY, NFX** (span: yfinance's history for the symbol starts in 2026-07, a different entity); **CPWR** (DIFFERENT_CONVENTION: ratio 0.16, slope 4.9 log units; Compuware was acquired in 2014); **CA** (unfetchable; the cached file is a 2023 reuse of the symbol) | span, or DIFFERENT_CONVENTION | **Refused forever.** The identity rail is the span check plus the DIFFERENT_CONVENTION refusal. These are never re-fetched under the reused symbol. |
| **(ii) Stitched identity** | **DAL** | span: cache from 1980, yfinance from 2007-05-03 (pre-2007 is old Delta) | **The user's decision:** declared truncation vs a declared seam. Note: the writer does not yet apply DAL's declared load-time exclusion (`dal_pre2007_excluded`) to the span it must cover. |
| **(iii) Stooq history deeper than yfinance** | **C** (+7 yr), **INTC** (+8), **JPM** (+10), **ELV** (+8), **MAR** (+4.5), **PLD** (+2), **AXP** and **WMT** (+5 months) | span | **The user's decision:** declared truncation (lose the oldest years) vs a declared seam (keep the drip before yfinance's first bar — a two-convention file, the T-082b class, but declared and census-recorded) |
| **(iv) Start-window leads, 9–34 days** | **CHTR, KDP, TDC, UAL, WU** | span: yfinance starts 9–34 days after the cache, past the 7-day slack (listing or emergence windows) | **The user's decision**, the same choice as (iii) at a much smaller scale |

**Share-class spelling (BRK.B, BF.B).** The writer as first merged passed the cache's dot form,
which Yahoo does not know. The shared symbol table (main `47aca8a`) fetches BRK-B and BF-B, records
"symbol mapped: X -> Y (share class)", and never tries a second symbol. Both are now **written on the
copy**: BRK.B APPEND from 1996-05-09, the cache's exact start (no dividend, so 'unverified'); BF.B
RESCALED 0.983, measured_tr. The real cache's md5 was unchanged by that step too.

**One-bar stubs.** RX (one bar, 2018-02-22) and SRCL (one bar, 2026-03-02, after the company's 2024
acquisition) are too short for any overlap (`OVERLAP_MIN_BARS` = 10), so the writer refuses them as
INSUFFICIENT whenever a fetch returns. In the pass both were unfetchable (among the 75). A one-bar file is not a history to agree with. Both are
data-quality items in their own right, and SRCL's is likely an identity problem. A cache of 10–251
bars reads normally: a 252-bar slice of a shorter file is the whole file.

## 3. The re-pin list (every pinned artifact the cutover moves)

Enumerated read-only on 2026-10-15. A first grep found about 40 candidate files; each was classified
by reading the code, and the claims that carry weight were checked by hand. The kinds are: **reads
at run time**, **bakes at build**, **fixed-number test**, **CI workflow**, **canon / manifest**, and
**not a reader**.

### 3.1 The live / paper path: settled first, because it decides who rules

**The cutover changes NO live trading input.** As far as the artifacts reach:

- **Trading closes come from Alpaca at run time** (`scripts/run_paper_cloud_day.py:651`,
  `client.fetch_daily_closes` for the sleeve; every other close fetch on the path, `:156`, `:222` and
  `:995`–`:1227`, is the same Alpaca client). `paper_trader/*.py` never references `data/processed`. There is no
  `live_trader/` directory.
- **The paper image bakes no file the cutover rewrites.** `scripts/build_paper_image.sh` stages:
  - a `git archive` (:28-29); `data/` is gitignored, so no cache comes with it;
  - `data/universe/sp500_membership_pit.parquet` (:38-46);
  - `data/processed/tr_reconciled/*.csv` (:58-66), for the agentic analyst's `query_prices`
    (`intelligence/analyst/agentic_readers.py:144,322`).

  `tr_reconciled/` is outside the cutover: the write pass changed exactly 1,264 top-level files (632
  × csv + parquet) and nothing under `tr_reconciled/`. `Dockerfile.paper:48-55` says the same: "No
  other data substrate is baked."
- **One run-time read of the flat files, report-only.** The eval harness resolves analyst predictions
  for symbols outside the sleeve by falling back to `data/processed/<SYM>_1d.csv`
  (`run_paper_cloud_day.py:1249-1257` → `intelligence/analyst/eval_harness.py:37,55-58`). The path is
  hard-coded, not env-driven. By the build script those files are not in the image, so the fallback
  returns None. But the comments at `run_paper_cloud_day.py:638-640` and `:1250-1253` call them
  "baked". The two artifacts disagree. **Unverified: needs the image listing**, the container's
  actual file list. This question **joins the image-audit job's questions** (director, 2026-10-15),
  the audit already waiting on the user. Either way the read is report-only: no order, no size, no
  risk input depends on it.
- **The container's environment:** `Dockerfile.paper:58-59` sets only `PYTHONUNBUFFERED` and
  `AWS_DEFAULT_REGION`. The Batch job definition's environment is **unverified locally**: it needs the
  job definition, part of the same audit.
- **Not on the cloud paper path:** the old local dry-run loop (`scripts/run_paper_loop.py` →
  `orchestration/mode_controller.py:551`, `cache_dir=data/processed`) reads the cache. It is launched
  only by `scripts/start_stack.py:31`, and nothing schedules it.

**Consequence for who rules and when:** no live redeploy follows from the cutover. The one open
question, whether the image listing shows the flat CSVs, decides only whether report-only eval
resolutions change at the next image build.

### 3.2 Pins the cutover moves

| artifact | kind | what is pinned | why the cutover moves it | re-pin |
|---|---|---|---|---|
| `tests/test_golden_master.py` | fixed-number test | the backtester's golden summary | its fixture reads the processed closes | regenerate the golden in the cutover commit |
| `tests/test_rescore_rr1_driver.py:25-28` (also `scripts/rescore_rr1.py:10`) | fixed-number test | `PRE_RR1_GOLDEN`: Sharpe 0.04946…, 171 trades, turnover 4,047,969.47, max position 47,956.64 | computed on the processed closes through the golden master's pipeline; no input-hash guard, so a data change reads as a code change | **RETIRE at cutover** (director's ruling, 2026-10-15). Its purpose, proving the before arm reproduced main as of 09-30 bit for bit, was served and is recorded. After the cutover the data it pins no longer exists, and a lock that cannot be satisfied is retired, not loosened. The reason goes in the test and in RR-1's §4; the record keeps the number |
| `engines/data_manager/exclusions.py:29-39` (+ `tests/test_price_levels_item_d_2026_10_15.py:114-123`) | declared constant | DAL cutoff 2007-05-03; `max_close_after` 1000 | DAL's treatment is the user's §2b (ii) decision; the check fails closed on a mismatch | re-declare with the ruling |
| the 26-yr anchor `158fe678`; 16-yr `3e9ea427` and 2022 `eb48742e` (`scripts/gen_t118_campaign_spec.py:124-129`); T-215 GFC `67784c1b…` (`docs/Audit/t215_campaign_specs/t215_ab_spec.json:11-15`) | canon | arm-0 canon md5 per window | new substrate, new canons. **The submit gate checks only that the keys exist** (`scripts/submit_arms_campaign.py:266-271`), so a stale anchor passes silently: a referee fail-open, a HIGH row, D's unit (ruled 2026-10-15). D's design has the gate check a nightly verify STAMP by digest and refuse while it is stale or absent; the nightly full verify that writes the stamp is Agent B's janitor unit | `run_isolated` N=5 bitwise per window on the new image; edit the generator and spec |
| B-1: panel `d9d449d17f8f`; results `5de36b89e0ad…`; 2012 window `bbf88ffc9f23…` (`docs/Audit/b1_raw_signal_decile_verdict_2026-10-14.md`) | canon | "must reproduce" md5s | built from the processed closes (R's lock 7: the panel must move VISIBLY) | the verdict doc's §12 commands |
| `config/substrate_manifest.sha256` | manifest | sha256 of 14,120 substrate files (2,049 under `data/processed/`) | every rewritten file | `scripts/gen_substrate_manifest.py generate` in the cutover commit. **See the note below: it already fails verify today** |
| the content-addressed S3 substrate prefix = md5 of the manifest (`.github/workflows/build_backtest_image.yml:112-117`); the image label (`scripts/build_backtest_image.sh:127,161,168`) | CI workflow | the substrate snapshot the backtest image is built from | a new manifest gives a new md5, and that prefix will not exist yet | a manual `aws s3 sync` to `substrate/<md5>/data` (no script), then `workflow_dispatch`. The workflow's `data/processed/**` trigger never fires, because `data/` is untracked |
| `Dockerfile.backtest:126` (`COPY data/processed/`) | bakes at build | the research image's substrate | the image carries whatever the cache is at build time | rebuild after cutover (research only; the image excludes `live_trader`, :100) |
| the exact-TR candidate's own manifest | manifest | the copy as a fixed object | — | pin after the §2b declared paths run (§6) |

**Derived files with no hash, which would go stale silently:**
- `data/universe/market_cap_tiers.json`: its delisted-name entries are processed Close × shares
  (`scripts/build_pit_cap_history_t219.py:61-68`), byte-pinned, and baked into the research image
  (`Dockerfile.backtest:142`). It moves only for names the cutover rewrites, and the 75 delisted
  names are not rewritten (§2).
- the T-306 SPY leg of `substrate_multidecade` (`scripts/build_multidecade_substrate_t306.py:75-77`).
  SPY is RESCALED by a constant 0.99496 over its whole span (§5 row below), so only its level moves.
- `ohlc_features_t150`.
- `_merge_meta.json`, which nothing reads.

**The manifest already fails verify, before any cutover: the known B-7 blocker.** This was first
recorded on 2026-09-30 in RR-7 Deliverable 3 (`docs/Sources/referee_repair_proposal_RR-7_2026-09-30.md`):
pinned 14,120, host 14,250, MISSING 0, EXTRA 130, CHANGED 5; the backtest image cannot be rebuilt
until the manifest is re-pinned; the verify footer hides lines.

Re-measured 2026-10-15 with the generator's own `build_manifest()`: **MISSING 0, EXTRA 134, CHANGED
5**. Every one of the 2,049 pinned `data/processed` files is byte-identical today.
- **The 5 CHANGED** (VIX, VIX3M, VIX6M, VIX9D, `_meta.json`) were all written in one minute,
  2026-07-02 03:09, by `scripts/fetch_vix_term_structure.py` (the T-256 and T-274 day). Against the
  June versions held in the content-addressed S3 snapshot (whose sha256 match the manifest), the run
  was a **pure extension**: every June row is present and bit-identical (1,339 common rows, max |Δ|
  0.0), and history was extended both ways. `_meta.json` gained a VVIX key. **A legitimate refresh;
  no wrong reason.**
- **The +4 EXTRA since 09-30** are fundamentals parquets cached by `DataManager`
  (`data_manager.py:167`) during the B-1 run on 2026-10-14. That is a runtime cache writing INTO the
  manifest's scope, so the re-pin must decide whether to exclude the pattern or pin it.

The paper image bakes `tr_reconciled/`, and it is **not pinned**. That goes on the image re-bake
checklist (`docs/Sources/proposal_observability_shipping_2026_10_13.md` §5), beside the Gate-7
cache. **The re-pin lands WITH the cutover** (director, 2026-10-15): one re-pin since June, not two.

### 3.3 Checked: NOT a pin the cutover moves

- `tests/test_golden_path.py`: synthetic fixture data.
- `tests/test_substrate_completeness_t167.py`: synthetic bounds and a SPY depth bound (≤ 1994);
  SPY keeps its 1993 start.
- `tests/test_hmm_repoint_t_2026_08_26.py`: its AUC thresholds read a FROZEN 2026-06 measurement
  (`docs/Measurements/2026-06/hmm_crisis_validation_t103.json`), not the cache.
- `tests/test_run_backtest_pure.py:229-269`: compares two runs to each other.
- `tests/test_discovery_seed_foundry_perf.py`: None checks and loose bounds.
- `tests/test_price_levels_item_d_2026_10_15.py`: md5 before == after; nothing stored.
- `tests/test_processed_cache_adjustment_class_2026_10_15.py`: the TR-drift floors over 2023-25
  still hold after the cutover (post-seam, and the cache stays total return).
- `.github/workflows/contract_tests.yml`: the golden master auto-skips there (:105-107).
- `core/benchmark.py` and `engines/engine_e_regime/macro_features.py`: recompute live; no stored
  value. `engines/engine_c_portfolio/phase1_composition.py` is tested NOT to read processed closes.
- `config/honest_n_pin.json`: pins the run registry, not prices.
- `scripts/t139_fixture_data.py`: a frozen extract; nothing compares against it.
- `docs/Audit/*_manifest.json`: historical records.

## 4. Measured deltas per file

Over the 652 files yfinance served (latest inventory row per file, yfinance throughout):

| measure | n | result |
|---|---|---|
| span coverage | 652 | 635 cover; 17 do not (§2b, span) |
| basis (two-mode, last 90 days) | 652 | 461 measured_tr; 190 "unverified: no ex-date in window"; 1 too few common bars |
| overlap over the last 252 cached bars (the write pass) | 652 | 474 RESCALED; 156 APPEND; 5 DIFFERENT_CONVENTION; 17 span refusals were never compared. (Outside the 652: BRK.B APPEND and BF.B RESCALED, under the shared symbol table) |
| **pre-seam** return delta, exact − drip | 559 | median −0.10%/yr; p10 −1.34; p90 +0.58; 102 move more than 1%/yr (§1) |
| pre-seam level ratio, exact / drip (median per file) | 561 | p10 0.968; median 1.007; p90 1.124 |
| **post-seam** return delta | 647 | median 0.00; p10 and p90 0.00. Only 4 files move more than 0.5%/yr, and they are exactly refused ones: AGG +3.19, EFA +2.66, VNQ +4.30 (their dividend yields, split-only) and CPWR −9.19 (identity) |
| post-seam level ratio (median per file) | 649 | p10 0.979; median 0.994; p90 1.000: a constant rescale from ex-dates since the cache was written |

**The post-seam cache is already exact total return everywhere except the files the writer
refuses.** The cutover's effect on returns is confined to the pre-seam drip (§1). The per-file
detail is in the inventories listed in the evidence base.

## 5. Per-verdict re-qualification plan under `[NN-SUBSTRATE-REVERIFY]`: first classification

**Scope authority:** `docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md` §5, the verdict list
read row by row. The cutover's own test is different from RR-1's. **Does the verdict's evidence read
PRE-SEAM equity closes in `data/processed/`, or a dollar-ADV computed from them?** There are two
reasons a pre-seam number moves: §1's dividend under-count, and the item (d) dollar-ADV deflation
(`docs/Sources/scan_price_level_consumers_item_d_2026_10_15.md`).

| class | verdicts | cutover action |
|---|---|---|
| **Controller-produced (RR-1: UNTESTED under corrected sizing, 29)** | T-066, T-092, T-126, T-140, T-140-fu3, T-180; T-055c/d/e/g/h, T-057, T-057b, T-109, T-118-rerun, T-120, T-121, T-128r, T-154, T-162, T-174; T-041b, T-122, T-129, T-144, T-145, T-196, T-241; T-211 | **RE-RUN, once, on the post-cutover substrate** (see the sequencing below) |
| **Consumes a controller curve (2)** | T-170, T-206 | **RE-RUN** with their inputs |
| **B-1** (raw-signal deciles, PIT S&P 500 2000–2025, verdict 2026-10-14) | reads the processed closes across 2000–2018 pre-seam | **RE-RUN** on the cutover substrate. DAL is not a factor (masked; PIT from 2013) |
| **Mechanism, determinism, infra (RR-1: unaffected)** | T-038-CONT … T-218 (RR-1 §5) | **RE-LABEL**: the claims are invariant to prices. Determinism canon md5s **re-pin** and the claim is re-confirmed on the new substrate (bitwise N=5) |
| **T-306-substrate family** (sleeve T-255/T-311; tilts T-318/T-320; offense T-294/T-294b/T-298/T-312/T-315) | built from FF, DGS10 and LBMA data, **and SPY from `data/processed/SPY_1d.csv`** (`fair_t236_rerun_t255.py:17`, `vehicle_bakeoff_t294.py:16`, `asymmetric_damping_t298.py:14`, `tilt_decision_measure_t318_t320.py:262`, and the T-306 SPY leg) | **UNAFFECTED in substance, measured:** SPY has no seam and reads RESCALED by a constant 0.99496 over its whole 1993–2026 span (annualised return delta 6e-9). A constant factor cancels in returns. *(This row first said the family reads no processed closes; that was wrong, and the scan of 2026-10-15 corrected it.)* |
| **ETF verdicts on `tr_reconciled/`** | already exact total return; untouched by this cutover | **UNAFFECTED** |
| **Independent harnesses on RAW Stooq files** (CONFIRMED from each script, 2026-10-15) | T-204 (`trend_overlay_validation_t204.py:35-37`: SPY/AGG/GLD from `data/raw/stooq/daily/us/nyse etfs/…`), T-213 (`industry_momentum_t213.py:25-30`: sector ETFs globbed from `data/raw/stooq/daily/us/**`), T-239 (`moonshot_rescore_t239.py:11`: `data/raw/stooq/daily/us/**/<t>.us.txt`) | **UNAFFECTED by this cutover**, which rewrites only `data/processed/`. Their basis is raw Stooq, split-only before about 2011 (R's per-era finding). That is T-256's known question, not a cutover one, and is noted here, not reopened |
| **RR-1's "needs a reviewer" (7)** | T-136, T-148, T-166, T-169, T-172, T-214, T-220 | inherit RR-1's resolution, then the same test |

**Sequencing (RULED 2026-10-15 by the director, for the user to override).** The 31 controller and consumer verdicts are
already slated for re-scoring under the corrected referee (RR-1/RR-5). The cutover changes their
substrate too. Re-scoring them on the drip substrate and again after the cutover would spend the
campaign twice and leave two incompatible sets of numbers. **Recommended: one re-run, on the
post-cutover substrate, after the referee repairs and the cutover both land**, with the RE-SCORE
labels carrying both reasons.

## 6. Sequence, if the user approves

1. The user's choice among (a), (b) and (c), and the user's choice for §2b classes (ii)–(iv):
   declared truncation vs a declared seam.
2. The write pass on the copy: **DONE** under the merged writer (§2b; the real cache untouched,
   md5 identical before and after; BRK.B and BF.B written once the shared symbol table merged).
   Then the §2b declared paths run, with BK's table entry landing WITH its class
   (split-only trio verified against the provider's split-only mode; the (ii)–(iv) declarations
   applied); the candidate manifest is pinned.
3. Re-qualification runs per §5.
4. Cutover day: the copy replaces the canonical substrate in one step; every §3 pin is re-pinned
   together; the guard switches on at every writer in the §4 inventory of the guard proposal, all at
   once. **A hard requirement of the switch-on commit (R's O-3):** the one live write path, an
   uncached ticker saved by `save_cache`, goes through `full_refetch` or is refused in canonical runs.
   Otherwise the first new ticker after cutover re-opens the basis mix.
5. First artifact: the next canonical run's census reports the convention, and, under (b), the split.
