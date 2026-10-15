# The cutover proposal — Agent R's single read of B's `docs/cutover-proposal-numbers` @ `ee25fe1`

> **Reviewer:** Agent R (independent, referee side). **Date:** 2026-10-15. **Unit:** `docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md` at `ee25fe1` (344 lines; docs only; merge-base `a556c15`; the diffs `a556c15→ec3385b` and `ec3385b→ee25fe1` read line by line), plus the write-pass addendum to `docs/Sources/proposal_price_cache_convention_guard_2026_10_15.md` on the same branch. No code in the unit. **Nothing in `data/processed/` was written by me**: the real cache's newest top-level file is dated 2026-06-17, and the 98 files the pass did not write are byte-identical between the copy and the cache.
>
> **Method:** every weight-bearing number recomputed from the inventories under `/Users/jacksonmurphy/Dev/_substrate_candidates/` (latest row per file) and from the copy against the real cache (730 files, Close by date); every cited `path:line` opened; the manifest verify RUN (read-only; the script writes only under `generate`, `gen_substrate_manifest.py:157-160`); every pinned md5 grepped for its sites repo-wide; §5's row set diffed against RR-1 §5 and against a repo-wide scan of `data/processed` readers (167 code files outside `Archive/` and `docs/`).

## 0. Verdict

**NOT READY for the user's batch as written. Four corrections, none a rebuild — and one new HIGH row the cutover exposed but does not own.** The proposal's measurements reproduce exactly (§2). The director's four checks: **(a) PASS** with one wording defect that tilts the treatment table; **(b) FAIL on omission** — a class of verdicts that move is not named; **(c) FAIL on two items** — one derived artifact is missing from the list and one claim on it is wrong; **(d) PASS**. §3.1 ("the cutover changes no live trading input") **PASS**.

### 0.1 (a) The withdrawn wording survives in the two places the user reads

§1 withdraws "the drip under-counted dividends" (median −0.10 %/yr; 36 % of names positive; the effect is dispersion). But option **(a)**'s consequence cell (line 98) still reads *"Knowingly keeps the dividend under-count (finding one)"*, and §5 (line 308) still gives *"§1's dividend under-count"* as a reason pre-seam numbers move. The user reads the treatment table, not §1's parenthetical; as written, option (a) is charged with a systematic bias that §1 says does not exist. Replace both with the dispersion wording. Also: (b)'s cell says *"a census field becomes a referee change"* — (a)'s "labelled universally" is the same census change; credit it to both or the comparison tilts.

### 0.2 (b) §5 inherits RR-1's row set, whose selection test is orthogonal to the cutover's

RR-1 §5 asked *"did the controller produce the number, or does the verdict consume its curve?"* The cutover asks *"does the evidence read pre-seam processed closes?"* §5 states the second test and then enumerates only RR-1's rows plus B-1, the T-306 family, the `tr_reconciled/` ETF verdicts and the three raw-Stooq harnesses. Independent harnesses that glob **every** `data/processed/*_1d.csv` over pre-seam windows never touched the controller, so RR-1 had no row for them — and §5 has none either:

| verdict | ledger status | what it reads | window start |
|---|---|---|---|
| **T-123** BAB referendum | refuted | `glob("data/processed/*_1d.csv")` (`analyze_bab_factor_t123.py:59`) | 2014 (pre-seam 2014–17) |
| **T-135** overnight/intraday | refuted | same glob (`:77`) | 2000 |
| **T-137** 8-K reactions | refuted | same glob (`:84`) | 2004 |
| **T-150** OHLC feature panel — *the arc's one positive screen, an Engine B live-risk finding* | done | same glob (`build_ohlc_features_t150.py:111`) | 1999 |
| **T-269** asymmetric exits | refuted | `data/processed/{tkr}_1d.csv` (`:50`), SPY (`:95`) | — |
| **T-153** vol-collapse assessment | in RR-1's "mechanism" list, which §5 relabels wholesale as "invariant to prices" | EWMA over `*_1d.csv` (`assess_vol_collapse_t153.py:145`) | — |

Whether each is RE-RUN or RE-LABELLED "refuted on the drip substrate" is a ruling; **naming them is the requirement §5 sets for itself** ("every verdict that moves"). Not in this class: T-265 (reads its own EPS/CIK panels, not the cache); T-262 (SPY/AGG/GLD only — all constant, §1.2).

Also missing, by RR-1's own second test: **T-171 and T-178 consume the frozen 26-yr arm0 curve** `data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv` (`mf_sleeve_deep_crisis_t171.py:43`, `regime_sleeve_sizer_t178.py:37`; T-174 reads it at `vrp_edge_t174.py:25`). That is the same controller product RR-1 §5 caught for T-170 ("blends DBMF against the T-128r 26-yr arm0 curve") and did not list for these two. The cutover inherits the miss.

### 0.3 (c) Two items on the re-pin list

1. **The base-curve CSV above is absent.** It is a controller product derived from the processed closes, read by three verdict scripts, under `data/external/` — which is in no `SUBSTRATE_DIRS` entry (`gen_substrate_manifest.py:37`; the manifest holds zero `data/external` lines). It belongs in §3.2's "derived files with no hash" and goes stale silently under both the RR-1 fix and the cutover.
2. **The `market_cap_tiers.json` claim is wrong.** §3.2 says *"It moves only for names the cutover rewrites, and the 75 delisted names are not rewritten."* The T-219 cohort is the 138 entries with `source: delist_shares` (processed Close × shares, `build_pit_cap_history_t219.py:61-68`), and the cohort is "left the PIT panel", not "left the exchange": **91 of the 138 are files the pass WROTE** (44 are among the 75 unfetchable; 0 outside the 730). 52 of the 91 carry a rescale ratio (0.955 – 18; median 0.989; tiers mid 51 / large 17 / small 17 / micro 6). The file is byte-pinned (`SUBSTRATE_FILES`) and baked (`Dockerfile.backtest:142`): re-pin #2 must regenerate it on the new substrate or freeze it with a stated reason.

Everything else on the list checks against every site I could find:

| pin | sites found (repo-wide grep, outside `Archive/` and `Sessions/`) | §3.2 |
|---|---|---|
| the four anchors `158fe678` / `3e9ea427` / `eb48742e` / `67784c1b…` | code: `gen_t118_campaign_spec.py:125-127`, `docs/Audit/t215_campaign_specs/t215_ab_spec.json:12`; otherwise audit prose and `health_check.md:70` | ✓ both code sites named |
| B-1 `d9d449d17f8f` / `5de36b89e0ad` / `bbf88ffc9f23` | docs only (verdict, prereg, ledger) | ✓ |
| `PRE_RR1_GOLDEN` | `tests/test_rescore_rr1_driver.py:26`, `scripts/rescore_rr1.py:10` | ✓; the ruling to RETIRE at cutover is consistent with "a lock that cannot be satisfied is retired, not loosened" |
| golden master | `tests/golden/` — equity, trades, signals, summary, `golden_input.sha256` (`test_golden_master.py:63-67`) | ✓ |
| manifest | `config/substrate_manifest.sha256` (14,120 lines; 2,049 `data/processed/`; last commit `ad03a97` 2026-06-18) | ✓ |
| S3 prefix | `.github/workflows/build_backtest_image.yml:112-117` (`md5sum config/substrate_manifest.sha256` → `substrate/$MD5/data`) | ✓ |
| research image | `Dockerfile.backtest:126` (`COPY data/processed/`), `:142` (cap tiers); `live_trader` excluded `:100` | ✓ |
| DAL constants | `exclusions.py:29-39`, `test_price_levels_item_d_2026_10_15.py` | ✓ |

### 0.4 NEW HIGH, pre-cutover, item (d)'s class — AZO, MTD and NVR sit at exactly ONE TENTH of their true price across their ENTIRE history in the canonical cache today

| | cache close 2021-06-01 | real print (approx.) | cache close 2026-04-24 | write-pass label | ratio (provider / cache) |
|---|---|---|---|---|---|
| **AZO** | 141.08 | ≈ 1,410 | 357.79 | `written:RESCALED` | **10.000000000000002** |
| **MTD** | 129.63 | ≈ 1,296 | 128.24 | `written:RESCALED` | **10.000000000000002** |
| **NVR** | 484.10 | ≈ 4,841 | 650.40 | `written:RESCALED` | **10.000000000000002** |

An exact decimal factor is the fingerprint of a code-applied ÷10, not a corporate action (compare KLAC's **0.09976**, a real 10-for-1 adjustment after the cache's last bar). **Mechanism, from `_merge_meta.json`:** all three are `merge_case: both`, `correction_method: loglinear_fit`. Their 2020-07+ Alpaca segments have medians above 1000 in true terms (2,504 / 1,297 / 5,866), so the old loader's ÷10 auto-scale fired on the Alpaca leg BEFORE the merge, and `fit_ratio_loglinear` absorbed the 0.1 into its constant and carried it back through the Stooq years. The result is a uniform ÷10 file with no seam jump (no one-day move above 40 % in any of the three) and a median far under 1000 — which is exactly why item (d)'s signature could not see them: *"a loader that divided OHLC by 10 whenever the median close exceeded 1000 fired on exactly ONE cached series — DAL"* (`data_manager.py:559-561`) is true of the load path on today's merged files and silent on what the same rule baked in at write time. Byte-identical since the June 18 pin. No other written file carries the signature (sweep of every ratio near 10 or 0.1: AZO, MTD, NVR, SLE — SLE is a reused ticker, below; BKNG/TPL/CMG/ORLY/NVDA/AVGO/LRCX/ANET/DECK all agree with the provider at ratio ≈ 1).

**All three are in the PIT universe with no end date** (AZO since 1997-01-02, MTD since 2016-09-06, NVR since 2019-09-26). Item (d)'s consumers **L1** (ADV floor, five edges), **L2** (slippage bucket) and **L3** (borrow bucket) read a dollar-ADV ten times too small for them; L4's integer quantity is self-consistent in the backtest (qty × the same wrong price) but wrong against any real fill. Magnitude on any headline: unmeasured here.

**Consequences for the proposal:**
- **§4 and §2b hide 14 level changes of 2× – 18× inside "RESCALED".** §4's *"post-seam level ratio p10 0.979 / median 0.994 / p90 1.000"* and §2b's *"475 RESCALED (the steady state)"* are true at the percentiles and silent at the tails. The 14 with a ratio outside [0.80, 1.10]: KLAC 0.0998, CTVA 0.149, CVNA 0.200, CRWD 0.250, APH 0.4985, MNST 0.500, AIV 0.696, FDX 0.800, DD 2.975, AZO / MTD / NVR / SLE 10, POM 18. By class: corporate actions after the cache's last bar (legitimate back-adjustment of the whole history, levels move 2–10×); large distributions and a spin-off (AIV, FDX, DD); two **reused tickers where the cached file IS the reused entity** (SLE from 2019-02-26, POM from 2025-10-08 — Sara Lee and Pepco left the index years earlier; the identity rail passes because the tail agrees with itself; PIT masks them; their `delist_shares` cap entries are the reused entity's); and the three ÷10 files. **A constant ratio far outside the dividend band is a corporate action or a scale defect, never a dividend rescale, and the writer adopts it silently under a clean record.** The guard needs a declared band (or a per-file declaration, the DAL pattern) before cutover day. That rail is one I did not ask for in the guard-build review; it is mine.
- **Under option (a) the three files stay wrong, labelled "drip"; under (b) or (c) the cutover fixes them SILENTLY as RESCALED.** Either way the fix must be a DECLARED path with its own census key, and the three names go on `health_check.md` now, independent of the user's cutover decision.
- **The 98 unwritten files cannot be checked for the same defect by this method** (no provider series to compare); the 75 unfetchable hold 44 of the cap-tier cohort.

### 0.5 A consequence the proposal does not state: the cutover moves the cache's END

All 632 written files end **2026-10-14**; the 98 unwritten end 2026-04-17/24 or earlier. Until the §2b declared classes have run, **23 LIVE names** (17 span, 5 convention, BK) stop six months before the rest — a ragged end that any to-date run reads as "stopped trading". The canonical windows end 2025-12-31 and are unaffected; §6 step 2 runs the classes before cutover day; say it. The 33 later starts are ≤ 7 days, inside the writer's slack.

## 1. The director's checks, with the evidence

### 1.1 (a) Three treatments, consequences, no pick — PASS (with §0.1)
- *"This proposal rules nothing on it"*; §6 step 1 hands the user the choice; six "user's decision / choice" sentences; no recommendation anywhere in 344 lines.
- Under (b), the split is survivor-only **only after** the declared classes (AGG/EFA/VNQ, AMCR, BK, (ii)–(iv)) have been ruled and run; before that, 23 live names also sit on the old convention. §6 sequences this correctly; the (b) cell should say it.

### 1.2 (b) §5 — see §0.2. What it names correctly, reproduced
- **T-306 family / SPY:** copy ÷ cache over 8,361 common bars: min = max = **0.99496**, std(log ratio) 2.9e-7, max |Δ log-return| 2.0e-6 — a constant. The five scripts read SPY only from the flat cache (`fair_t236_rerun_t255.py:17`, `vehicle_bakeoff_t294.py:16`, `asymmetric_damping_t298.py:14`, `tilt_decision_measure_t318_t320.py:262`, `build_multidecade_substrate_t306.py:76`); the rest is `data/macro/` and `tr_reconciled/`.
- **The ETF set the sleeve-era scripts read from the flat cache** (37 T-2xx/T-3xx scripts; all read SPY only, except T-262 SPY/AGG/GLD and T-269 equities): TLT, IEF, QQQ, IWM, DBC, UUP, GLD — every one a pure constant (max |Δ log-return| ≤ 1.7e-6); AGG/EFA/VNQ untouched.
- **`tr_reconciled/`:** 40 files, sorted per-file md5 identical between copy and cache.
- **T-204 / T-213 / T-239:** `data/raw/stooq/daily/us/…` at `trend_overlay_validation_t204.py:33-38`, `industry_momentum_t213.py:25-29`, `moonshot_rescore_t239.py:11`. Confirmed.
- **B-1:** DAL masked (PIT from 2013; `dal_pre2007_excluded` at load) — consistent with my B-1 read.
- Of the 632 written files, **540 move in returns** (pre-seam drip replaced) and **92 are pure constant rescales**; the 98 unwritten do not move. The 540 are the re-qualification.

### 1.3 (c) — see §0.3.

### 1.4 (d) The two forensic questions — PASS; both narrowed, neither answered
- The guard proposal's addendum: AMCR's tail (two missed ex-dates, 2025-09-05 and 2025-11-28) and BK's 2026 bars are both pinned at `ad03a97` and byte-identical today, so "the writer is one that ran before the June pin" — narrowed, not answered, and labelled so. ✓
- **The manifest, reproduced.** `python scripts/gen_substrate_manifest.py verify` exits **1** in 6.8 s. Printed: 20 EXTRA, 5 CHANGED (`data/macro/VIX.parquet`, `VIX3M`, `VIX6M`, `VIX9D`, `_meta.json`), MISSING 0, then *"… and 79 more"*. The footer prints `total − 60`, so total = 139 = **EXTRA 134 + CHANGED 5** — B's re-measured counts exactly, and B's RR-7 note that the footer hides lines (130 EXTRA on 09-30 → 134 now). **No `data/processed` file is CHANGED.** The +4 are `data/processed/parquet/{CVNA,KG,SII,S}_fundamentals.parquet`, mtimes 2026-10-14 02:45–03:06 (the B-1 run); the dir holds 1,319 against 1,315 pinned. RR-7 Deliverable 3 (`:160-205`) carries the 09-30 numbers as cited. TWO re-pins, each with its reason: stated at `ee25fe1`.
- **The submit gate, reproduced:** `submit_arms_campaign.py:268-271` tests `{"canon_md5","source","image"} <= set(anchor.keys())` and nothing reads the value. **Nothing automated compares after the run either:** `:367` copies each cell's `canon_md5` into the summary CSV (`:491-497`) "so the analyst can verify post-run" — a manual step. The HIGH row should read "no automated compare at submit OR post-run".

### 1.5 §3.1 — the live / paper path — PASS, every line opened
| claim | artifact | result |
|---|---|---|
| closes from Alpaca at run time | `run_paper_cloud_day.py:651` (`fetch_daily_closes(SLEEVE_UNIVERSE, 400)`); `:156`, `:222`, `:995-1227` all the same client | ✓ |
| `paper_trader/*.py` never references `data/processed` | grep: empty | ✓ |
| no `live_trader/` | absent | ✓ |
| the image bakes no file the cutover rewrites | `build_paper_image.sh:29` (`git archive`), `:38-46` (PIT parquet), `:58-66` (`tr_reconciled/*.csv`); `tr_reconciled/` byte-identical copy vs cache | ✓ |
| the `_disk_price` fallback | `run_paper_cloud_day.py:1249-1257` → `eval_harness.py:37,55-58`, hard-coded `ROOT/data/processed/<SYM>_1d.csv`; `paper_cloud_entrypoint.sh` pulls nothing from S3 and names no `processed` path | **dead by construction of BOTH build and entrypoint**; only the comments (`:638-640`, `:1250-1253`) say "baked". The listing remains the proof, and the proposal rightly leaves it with the audit |
| `Dockerfile.paper:48-55` "No other data substrate is baked" | that comment says *"exactly one data file"* (`:49`) while the build script stages two things — **the comment the proposal cites in support is itself stale.** A stale comment corroborates nothing; the build script and the entrypoint are the artifacts | note for B |
| `Dockerfile.paper:58-59` env | `PYTHONUNBUFFERED`, `AWS_DEFAULT_REGION` only | ✓ |
| `run_paper_loop.py` launched only by `start_stack.py:31` | grep: the one site; `mode_controller.py:551` `cache_dir=data/processed` | ✓ |

**The director's adjacent decision** (re-pin #1 pins the fundamentals cache; canonical runs record a miss under `fundamentals_blind` and do NOT fetch) is fail-closed and right. Its consequence needs the sentence: a universe change in a canonical run then reads `fundamentals_blind > 0`, which is **non-canonical under `[NN-CENSUS]` while a value edge is active**, so the fundamentals prefetch becomes a declared re-bake step with the re-pin, never a run-time fetch.

## 2. Numbers reproduced, two ways

| claim (proposal) | mine | from |
|---|---|---|
| outcomes 475 RESCALED / 157 APPEND / 75 unfetchable / 17 span / 5 DIFFERENT_CONVENTION / 1 held | **identical** | latest row per file, `write_pass_2026-10-15.jsonl` (796 rows → 730) |
| pre-seam exact − drip, n 559: p1 −3.32 … median −0.10 … p99 +2.03; mean −0.28; 36 % positive; 102 > 1 %/yr | **identical to 2 dp** | `measure_*.jsonl`, provider yfinance, latest row |
| post-seam n 647, p10/50/90 = 0.00; 4 above 0.5 %/yr: AGG, CPWR, EFA, VNQ | identical | same |
| 9 ended on a common date: AVB, CA, CTRA, EA, EQR, LEG, MHS, QRVO, WBD; 66 early | **identical** | the 75's last rows in the real cache |
| SPY constant 0.99496 | identical (min = max) | copy vs cache |
| `tr_reconciled/` untouched; real cache untouched | identical md5s; newest cache file 2026-06-17; 98 unwritten byte-identical | copy vs cache |
| RX one bar 2018-02-22; SRCL one bar 2026-03-02 (its one bar has O/H/L = 0.0); CA from 2023-12-15 | identical | the files |
| manifest EXTRA 134 / CHANGED 5 / MISSING 0, exits 1 | identical (footer arithmetic) | the script, run |
| 632 written ⇒ 1,264 files; copy 737 top-level entries as the cache | 737 both; 632 + 98 = 730 | the dirs |

## 3. Not verified, or out of reach
- **Network:** none. yfinance's series were not re-fetched; "75 unfetchable" is accepted from the retry log, the per-symbol reasons and the Alpaca status file, not re-run.
- **The aggregate md5 `8ead63bc…`** of the real cache: B's method is not stated; verified instead by mtimes and by byte-identity of the unwritten set.
- **The image listing** — with the audit, as the proposal says.
- **Minor, for B:** §1 pre-seam n = 559 but §4's pre-seam level ratio n = 561 — two files have a level ratio and no return delta; say which and why.

## 4. Lessons (mine, to `reviewer_checklist_agent_r.md` §6 in a later unit)
- **A constant overlap ratio outside the dividend band is a corporate action or a scale defect, never a dividend rescale.** I reviewed the guard's overlap check for the split-only trap and never asked for a band on the ratio it accepts; the pass then adopted three ÷10 files and two reused tickers under "RESCALED". Read the tails of every "steady-state" distribution, not its percentiles.
- **A derived-artifact scan must walk the unpinned directories** (`data/external/`), because that is where a stale product hides from `verify`.
- **One proposal's row set is not the next proposal's verdict list.** RR-1's rows were selected by the sizing test; reusing them for the substrate test silently drops every harness the first test had no reason to list. Re-derive the set from the new test (here: a glob of the readers).
