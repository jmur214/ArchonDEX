---
title: "Trade-desk gap analysis: how a desk decides vs how ArchonDEX decides (T-411)"
date: 2026-11-20
task: T-411
lens: System Architect / Auditor (read-only)
code_state: main at e68251b (every file:line below is at this commit)
status: DESIGN ONLY. Read-only on code. Nothing was run, nothing was backtested, no network was used, and no trials were consumed. Every build item is a PROPOSAL. Propose-first items are flagged with **[PF]**. LLM items are flagged with **[AI]**.
companion: T-410 (the census of untested IDEAS, including options as instruments and as information). This document covers the DECISION MACHINERY only, not new strategies.
---

# Trade-desk gap analysis: how a desk decides vs how ArchonDEX decides (T-411)

## Plain-language summary (for the owner)

1. **A trading desk is a loop.** People bring ideas. Each position gets a short written case: why, how much it should make, by when, and what would prove it wrong. Size follows confidence. A risk manager can say no. Positions are watched against their case, and every closed trade is reviewed. Money moves toward whoever has a track record. ArchonDEX has a piece of every one of these steps, but the pieces are not connected. Most of them are also on the practice side of the wall, not the side that places orders.

2. **What places orders today.** There are three paper accounts:
   - Account 1 holds SPY/AGG/GLD by a price-trend rule.
   - Account 2 holds a fixed 85/15 VOO/MTUM mix. It has been halted since 11-06.
   - Account 3 has an AI read news headlines and pick weights in SPY/AGG/GLD.

   That is all. None of the six engines (A–F) that the design documents describe is on the order path. The only exception is one small guard borrowed from the risk engine.

3. **Information, counted.** The live system touches 24 information sources.
   - **3** reach an order: prices, the stock-split feed, and news. News gets there only through the AI, and only onto three ETFs.
   - **6** feed only practice books or scoring. **4** of those 6 are blind in the cloud, because the file is not there when the code reads it.
   - **15** are archived and read by nothing. **12** of the 15 are still being collected.

4. **The surprise is that the most desk-like parts already exist.**
   - A "thesis" format that refuses any idea without a stated way to be proven wrong and a deadline.
   - An "event" format that turns a company filing into a direction, an importance score and a checkable prediction.
   - Practice books that size by confidence and close on the deadline.

   None of them trades, and two have been starved since they were built. The filing feed does not exist in the cloud, so the event desk has never opened a position. The "proven wrong" checks are never evaluated, so the thesis book closes only on deadlines.

5. **The biggest gaps, in order:**
   1. Information has no route to a sized order except the AI on three ETFs.
   2. Orders carry no reason: no thesis, no expected result, no exit condition. So no trade can be reviewed.
   3. Information we already collect never reaches the desks we already built.
   4. No risk manager watches the whole book. There is no pre-trade check, no price limit on orders, no loss limit, no event awareness, no stress test and no hedge.
   5. Size ignores confidence.
   6. The only calendar the system knows is Fed meeting dates.
   7. Nothing moves money between strategies by track record. That one is partly right, because the evidence for doing it is poor.

6. **What the design already gets right, and should keep:**
   - It fails closed everywhere and cannot look ahead.
   - The AI's output is checked, and rejected whole if it breaks a limit.
   - A halt never sells.
   - The split guard.
   - Practice books are compared with a "do nothing" twin and have promotion bars stated in advance.
   - The AI is scored against the market's own probabilities.
   - The trend rule has no regime switch on top. That was measured to hurt.

7. **The fix is not more data or a bigger AI. It is a small spine:**
   1. A source register that proves each day that every source reached its readers.
   2. A "decision record" on every order: why, how sure, for how long, the expected result, and what would kill it.
   3. The risk engine (B) turns confidence into size and holds a veto.
   4. A calendar of scheduled events. The regime engine (E) describes them; B decides what to do.
   5. A daily check of every open position against its stated kill condition.
   6. A per-decision review, owned by governance (F).

   Every piece must work without the AI first. The AI stays on account 3 and in the practice books.

8. **Why bother, if this will not prove an edge.** The 11-14 audits showed that no backtest of 26 years or less can prove a realistic edge. The one kind of evidence that builds up quickly is per-decision: every decision with a stated, checkable prediction is a data point. A desk-shaped machine turns the fleet from one return number a year into hundreds of scored decisions a year. That is the payoff: faster, honest learning and fewer avoidable mistakes. It is not a promise of beating the robo.

9. **The first week.** Make the information we already collect reach the desks we already built, and prove it every run:
   - Register the sources, and check that each reader runs after its data arrives.
   - Move one data sync earlier in the daily run.
   - Give the event desk a live filing feed.
   - Wire the "proven wrong" checks.

   No order changes. It touches the daily paper run, so it waits for your word.

10. **Honest limits.** Most of these sources have already failed as stand-alone signals: prediction markets are already priced, and insider clusters, filing-text change and 13F crowding were refuted. Expect the desk to improve risk control and learning speed, not returns. Your real money is in a taxable robo. Nothing here changes that decision.

---

## How to read this

- **Live** means the decision places paper broker orders. **Shadow** means a virtual, report-only book: no orders, ever. **Backtest-only** means the code runs only in the research stack (`engines/`, `backtester/`, `orchestration/`).
- The accounts are as provisioned (`scripts/provision_paper_fleet.py:43-92`; `infra/paper_cloud/job_definition.json:25`):
  - **Account 1** = `trend_sleeve` (jobdef "cloud-day", prefix `paper_state`). The LLM "intel pulse" runs **only** in this container.
  - **Account 2** = `deploy_candidate` (jobdef "offense-sso"; halted since 2026-11-06).
  - **Account 3** = `llm_analyst` (jobdef "ai-trader"). It pulls account 1's analyst note read-only from S3 (`run_paper_cloud_day.py:899-904`).
- Each "consumer" was found by tracing callers in code (grep for the file name, the reader function and the call site), never from docstrings. Where the code shows a defect but the cloud artifact was not read, the claim says **"artifact check owed"**. This document read no S3 object.
- **The cloud availability rule this audit relies on:**
  - The paper image is `git archive` plus exactly two staged data sets: the PIT membership parquet and `data/processed/tr_reconciled/` (`scripts/build_paper_image.sh`; the 10-22 image audit counted 40 data files). No `data/` file is tracked in git.
  - So a file under `data/` exists in a cloud container only if:
    - (a) the run's early pull brings it (`DURABLE_PATHS`/`DURABLE_DIRS`, `paper_trader/cloud_state.py:40-202`, pulled at `run_paper_cloud_day.py:433`), or
    - (b) a later pull brings it: alt-data at `:1658`, the news tape at `:1320`, news months at `:1698`, or account 3's note pull at `:900`.
  - A reader that runs before its pull, or reads a file no pull brings, is blind in the cloud.

---

## Part 1 — What a desk does, step by step

This is concrete practice, the way a small multi-strategy desk actually runs, not textbook.

1. **Idea generation and the pipeline.** Ideas come from analysts, the news flow, screens, conversations, and the PM's own book. Each idea goes into a log: owner, date, one-line claim, status (watch → work-up → pitch → live → closed). Most die at "watch". The pipeline is reviewed weekly, so that dead ideas are closed out loud rather than left to drift.
2. **Information intake.** A desk subscribes to sources because a decision reads them:
   - prices (intraday);
   - news (tagged to the book's names and sectors);
   - filings (8-K, 10-Q/K, Form 4, 13D/G, 13F);
   - a macro calendar (CPI, payrolls, FOMC, auctions, earnings dates for every holding, ex-dividend and index-rebalance dates);
   - positioning (short interest, borrow cost, futures COT, fund flows, margin);
   - options-implied information (implied vol, skew, term structure, the implied move into an event);
   - prediction markets (as the market's probability for a binary event).

   An unread source gets cancelled.
3. **A written thesis per position.** Before the trade: the claim, the catalyst, the expected payoff (a range, or a target and a probability), the horizon, and the **invalidation point**. The invalidation is a price, a data release, or a dated "if X hasn't happened by D, I'm wrong". The thesis is one paragraph, filed, and reviewed when the position closes.
4. **Conviction-based sizing.** Size follows conviction and risk, within a fixed budget per idea. That means risk per unit of conviction, scaled by volatility, capped per name, sector and gross. Conviction is earned: a PM whose high-conviction calls do no better than his low-conviction calls gets flat sizing.
5. **Portfolio-level risk.** The risk manager sees the whole book, not each position:
   - gross and net exposure, beta, factor exposures, correlation clusters;
   - scenario and stress tests ("what does the book lose in a 2008 / 2020 / 2022 replay", "what if rates +100bp");
   - event exposure ("we are long three names reporting this week");
   - hedges, often options: index puts or put spreads, collars on concentrated names, buying vol into events. The other route is reducing gross.
6. **Execution.** Limit or marketable-limit orders around the arrival price. Avoid trading into a scheduled event unless the event is the trade. Slice size relative to volume, measure slippage against arrival, and feed the cost back into sizing.
7. **Monitoring against the thesis.** Every day, for every position: has the invalidation fired? Has the catalyst happened? Is the position still sized right for its conviction now? Exits are triggered by the thesis, not by the mood.
8. **Post-trade review and attribution.** For each closed trade: was the thesis right (did the prediction resolve true)? Was the money made for the stated reason or by market beta? What did execution cost? Per PM: hit rate, payoff ratio, and whether high-conviction calls do better than low-conviction calls (calibration).
9. **Capital allocation across strategies and traders.** Capital moves toward PMs and strategies with a track record. It moves slowly, with minimum evidence and caps. New strategies run on paper or small capital first, with a stated promotion bar.
10. **A risk manager with veto power.** An independent function that can refuse a trade, force a reduction, or stop a PM at a loss limit, with written reasons. It does not generate ideas.

---

## Part 2 — What ArchonDEX has for each desk function

| # | Desk function | What ArchonDEX has today (traced) | Evidence | Status |
|---|---|---|---|---|
| 1 | Idea generation and pipeline | Research ideas live in docs and the ledger (`docs/Core/Ideas_Pipeline/`, `docs/State/TASK_LEDGER.md`). Engine D's discovery runs in backtests only. The LLM thematic scan files theses weekly into a SHADOW book. No idea reaches a real order. (T-410 audits the ideas themselves.) | `paper_trader/intel_pulse.py:357-394`; `engines/engine_d_discovery/` | **PARTIAL** |
| 2a | Intake: prices | Alpaca daily closes, fetched fresh each run; the forming bar is dropped (causal). No intraday. | `run_paper_cloud_day.py:724,735`; `:156-159` | **PRESENT** (daily only) |
| 2b | Intake: news | Alpaca news panel → one decision consumer, the account-3 LLM note, which can trade only SPY/AGG/GLD. ETFs carry almost no company tags (the code says so). | `intelligence/analyst/context_builder.py:70-160`; `paper_trader/llm_analyst_constructor.py:156-167` | **PARTIAL** |
| 2c | Intake: filings (8-K, Form 4, 13F) | 8-K panel: absent in the cloud, frozen locally at 2026-06-10. Form 4 index: archived, 0 consumers. 13F: research-only (T-145, refuted). | Part 3, rows 7, 12; `scripts/build_13f_panel_t145.py` | **ABSENT in practice** |
| 2d | Intake: macro calendar | FOMC decision dates only (`config/fomc_calendar.json`). Its only reader (Engine E `EventStateDetector`) is default-OFF, backtest-only, and T-291 refuted it. No CPI/payrolls/earnings/ex-dividend calendar on any decision path. | `engines/data_manager/macro_calendar.py:1-30`; `engines/engine_e_regime/regime_config.py:107` | **ABSENT** |
| 2e | Intake: positioning | Five FINRA/SEC/NAAIM sets archived daily or weekly with **zero code consumers** (the archiver's own comments say so). | `paper_trader/altdata_archive.py:98-109` | **ABSENT** (collected, unread) |
| 2f | Intake: options-implied | None. The eval harness says it plainly: "We have no option-surface on disk". | `intelligence/analyst/eval_harness.py:277-282` | **ABSENT** |
| 2g | Intake: prediction markets | Kalshi general series, the KXFED ladder and Polymarket are archived daily. Only the KXFED ladder has a reader (scoring), and it is dark in the cloud at read time (Part 3, row 5). T-407 closed the trading question: the forecasts are already priced. | `eval_harness.py:77,271-299` | **PARTIAL** (scoring only) |
| 3 | Written thesis per position | **Two desk-grade schemas exist:** `thesis_call/v1` (conviction, horizon, entry basis, REQUIRED falsifiers with a `check_by` date and a machine resolver) and `event_call/v1` (direction, materiality, ≥1 resolvable prediction). **Both live only in shadow books.** Real orders carry no thesis: `OrderRecord` has no reason field, and the account-3 action is a bare weight, "EXACTLY four fields … an extra field VOIDS the whole note". | `intelligence/thesis_desk/thesis_schema.py:60-126`; `intelligence/event_call/event_schema.py:51-74`; `paper_trader/order_manager.py:164-184`; `config/prompts/analyst/daily_v4.md:44-46` | **PARTIAL** (built, on the wrong side of the wall) |
| 4 | Conviction-based sizing | **Live:** the trend sleeve's exposure is the mean of three speeds, {0, ⅓, ⅔, 1}, a crude agreement-as-conviction scale. The 85/15 has none. Account 3's LLM sets final weights directly, with no calibration. **Shadow:** three different conviction→size rules (thesis gross = 0.60 × conviction; event weight = 0.20 × materiality; backtest Engine B risk scaler = 0.5 + strength). `forward_plan.md` gap 4 already records "the book ignores the difference". | `paper_trader/sleeve_constructor.py:66-100`; `paper_trader/thesis_book.py:211`; `paper_trader/event_shadow_book.py:242`; `engines/engine_b_risk/risk_engine.py:1207-1209` | **PARTIAL** |
| 5 | Portfolio-level risk (exposure, correlation, scenario, stress, hedging) | **Backtest:** Engine B has ATR stops, trailing stops, regime-widened stops, sector caps, ADV caps and a vol target; Engine C has HRP/MVO. **Live:** per-constructor caps and the notional cap only. Nothing aggregates exposure across accounts (the fleet mirror is display-only). No ex-ante stress test (`MetricsEngine` VaR/ES are ex-post report metrics). No hedging. No pre-trade gate at submit (09-17 audit A5, still open). | `risk_engine.py:40,65-69`; `paper_trader/fleet_mirror.py`; `core/metrics_engine.py:260`; `docs/Audit/fresh_eyes_program_audit_2026_09_17.md:49` | **ABSENT on the live path** (PRESENT in backtest) |
| 6 | Execution | Strong mechanics: idempotent client order ids, journal-before-POST, whole shares, arrival-price slippage ledger, the corporate-action gate. Market orders only (`MarketOrderRequest`), with no price collar (09-17 A2, still open) and no event-aware timing. | `paper_trader/paper_client.py:208-214`; `paper_trader/exec_cost_ledger.py` | **PARTIAL** |
| 7 | Monitoring against the thesis | **Shadow:** the thesis book closes on falsifier or horizon, but the falsifier-resolution channel (`falsifiers_fired`) is **never passed in production** (only a test passes it), so exits are deadline-only. The event book closes on horizon only. **Live:** monitoring is reconciliation plus econ-health tripwires (report-only), not the thesis. | `thesis_book.py:251-269`; `run_paper_cloud_day.py:1216`; `tests/test_thesis_book_t326.py:128` | **ABSENT** (live) / **PARTIAL** (shadow) |
| 8 | Post-trade review and attribution | Per stream: sleeve vs the two robos (`sleeve_tracker`); per-fill slippage; Brier scoring with market-implied and persistence baselines (`eval_harness`); shadow books vs an SPY or 60/40 twin; the weekly digest. **Per trade on real orders: none.** The journals carry no sizing or reason metadata (health LOW row "journals carry NO sizing metadata"). | `eval_harness.py:454-551`; `intelligence/analyst/performance_digest.py` | **PARTIAL** |
| 9 | Capital allocation by track record | Fixed sub-budgets per account. Pre-registered promotion bars exist: the stage-2 clock, D's T-304 bar #5 for the event desk, D's T-324 `promotion_check` for theses. They are report-only, and promotion is the user's call (correct). Engine F's governor (EMA weights, lifecycle) runs only in backtests. | `paper_trader/stage2_clock.py:48-95`; `event_shadow_book.py:52-60`; `intelligence/thesis_desk/thesis_scoring.py:101` | **PARTIAL** (gates exist; no allocator) |
| 10 | Risk manager with veto | **Strong on integrity:** a manual halt from three sources that never liquidates; fail-closed refusals on stale data; corporate-action stand-down; the LLM firewall (rejects the whole note, never clamps); the wash guard (account 2); the arm interlock. **Absent on market risk:** no automatic veto on loss, exposure, concentration across accounts, or scheduled events. The halt is written only by a human. | `paper_trader/trading_halt.py:1-60`; `run_paper_cloud_day.py:600-606,746-755`; `llm_analyst_constructor.py:169-181` | **PARTIAL** |

**The structural fact behind the table.** The live product is `scripts/run_paper_cloud_day.py` plus `paper_trader/` plus `intelligence/`.
- Its only imports from the A–F stack are Engine B's wash guard (`run_paper_cloud_day.py:539,576`), Engine C's policy config (`paper_trader/paper_config.py:81`), and `core/` utilities (`TrendOverlay`, `MetricsEngine`, census).
- `PaperOrderConstructor`, the adapter that would put A→C→B on the paper path, has **only test callers** (`paper_trader/order_construction.py:48`; callers: `paper_trader/__init__.py`, `tests/test_paper_pr3_partB_t163.py`).
- `engine_charters.md`, every engine `index.md` and `docs/README.md` mention `paper_trader` or `intelligence/` **zero** times (checked 2026-11-20).
- The charters describe a desk that runs only in backtests. The desk that trades is unchartered.

---

## Part 3 — The information-to-decision audit

Each row was traced from the file or reader to its callers. **"Decision"** means an order or sizing decision on a paper account. Shadow books and scoring are listed, but they are not decisions.

| # | Source (where it lands) | Code consumers (traced) | Decision it affects | Live in | Verdict |
|---|---|---|---|---|---|
| 1 | Alpaca daily bars (in-memory, per run) | `sleeve_constructor.py:81-125` via `run_paper_cloud_day.py:724,776`; `_run_family_strategy` `:156,173` | Account 1: trend signal and size. Account 2: bands and size. Account 3: share counts. | 1, 2 (halted), 3 | **LIVE** |
| 2 | Alpaca corporate-actions (split) feed (`data/state/price_basis_marks.json`) | `run_paper_cloud_day.py:632-667` (gate); `:775-784`, `:171-186` (sizing basis + screen) | Share basis for sizing; book stand-down veto | 1, 2, 3 | **LIVE** (risk) |
| 3 | Alpaca news panel (`data/intel/news_panel/`, S3 `news_panel/`; tape pulled at `:1320` before the pulse) | `context_builder.py:70-126` (scoped) and `:129-160` (market tape) → constrained analyst note (`intel_pulse.py:233-265`) → `llm_analyst_constructor.py:183` on account 3. Also the agentic arm, the thesis scan and the watchdog (shadow/ops). | Account 3 target weights, SPY/AGG/GLD only, ≤20% each | 3 (via the LLM only) | **LIVE via the LLM** [AI] |
| 4 | Kalshi KXFED Fed-meeting ladder (`data/macro_data/alt/kalshi_kxfed_snapshots.parquet`) | `eval_harness.py:77,83-88,112-134,271-299` (settlement resolution and the market-implied baseline) | none (scoring) | none | **SCORING ONLY, and blind in the cloud at read time.** The eval runs at `:1403`; the alt-data dirs are first synced into the container at `:1658`; neither path is in `DURABLE_PATHS` (artifact check owed) |
| 5 | FRED rate path (`.../fred_rate_path.parquet`) | `eval_harness.py:78,104-141` (FOMC resolution); `agentic_readers.py:165-196` (the agentic tool); `intel_pulse.py:178-192` (the thesis-scan context) | none (scoring / shadow) | none | **SHADOW ONLY, and blind in the cloud at read time** (same step order; artifact check owed) |
| 6 | EDGAR 8-K items (`data/edgar/8k/panel_8k_items.parquet`) | `intelligence/event_call/eightk_feed.py:29,73-105` → `run_forward.py:105` → `event_calls.jsonl` → `event_shadow_book.py` | none (shadow event desk) | none | **DEAD BY CONSTRUCTION.** The file is in no image and no sync, so `new_8k_documents` returns `[]` silently (`eightk_feed.py:82-83`) and the pulse reports "ok, 0 documents". The local copy is batch-built and ends 2026-06-10. On 2026-09-18 the event desk had opened **0** positions in 38 observed sessions (`docs/Measurements/2026-09/reviewer_liveness_sweep_2026_09_18.md`). |
| 7 | Special-situations events (`data/research/special_situations/events.parquet`) | `context_builder.py:31,163-181` (analyst context); `eightk_feed.py:30,108-134` (event desk) | none | none | **DEAD.** Absent in the cloud (the bundle section reads `no_events_file`); the watcher has been stopped since 2026-07-02 (11-14 audit) |
| 8 | BTC-USD, IBIT, DBMF, BIL closes | `btc_shadow.py`, `dbmf_shadow.py`, `live_books.py` via `run_paper_cloud_day.py:1100-1292` | none | none | **SHADOW ONLY** |
| 9 | `tr_reconciled` ETF closes (baked into the image) | `agentic_readers.py:139-162` (`query_prices`) | none (agentic shadow) | none | **SHADOW ONLY.** Research-grade, frozen at build time (the local copy's SPY ends 2026-05-22) |
| 10 | Kalshi macro series (`kalshi_snapshots.parquet`, rebuilt T-405) | none (freshness check `altdata_archive.py:47`; tests) | — | — | **ARCHIVED, READ BY NOTHING** |
| 11 | Polymarket snapshots | none in the live path. Engine E's `EventStateDetector` globs the alt dir (`event_state_detector.py:157`) but is default-OFF, backtest-only and refuted (T-291). | — | — | **ARCHIVED, READ BY NOTHING** |
| 12 | Polymarket resolutions | none (archiver only) | — | — | **ARCHIVED, READ BY NOTHING** |
| 13 | EDGAR Form 4 index (`edgar_form4_index.parquet`) | none (freshness only). Engine A's insider edge reads a different cache (`data/insider/`), backtest-only, refuted (B-2: t 0.20). | — | — | **ARCHIVED, READ BY NOTHING** |
| 14 | EPU daily and monthly | none | — | — | **ARCHIVED, READ BY NOTHING** |
| 15 | GPR daily and monthly | none ("no cloud consumer", `altdata_archive.py:86-87`) | — | — | **ARCHIVED, READ BY NOTHING** (laptop only) |
| 16 | USASpending awards | none | — | — | **ARCHIVED, READ BY NOTHING** |
| 17 | Credit OAS (`credit_spread_oas.parquet`) | none ("no cloud consumer", `altdata_archive.py:92-96`). The credit series in the FRED macro panel feed Engine E and A in backtests only (row 25). | — | — | **ARCHIVED, READ BY NOTHING** (laptop only) |
| 18 | FINRA Reg SHO short volume | none | — | — | **ARCHIVED, READ BY NOTHING** |
| 19 | FINRA short interest | none | — | — | **ARCHIVED, READ BY NOTHING** |
| 20 | SEC fails-to-deliver | none | — | — | **ARCHIVED, READ BY NOTHING** |
| 21 | FINRA margin debt | none | — | — | **ARCHIVED, READ BY NOTHING** (laptop only) |
| 22 | NAAIM exposure | none ("ZERO code consumers", `altdata_archive.py:100-104`) | — | — | **ARCHIVED, READ BY NOTHING; collector broken since 2026-07-29** |
| 23 | GDELT tone | none (retired T-335) | — | — | **RETIRED** |
| 24 | CEF daily panel | `scripts/cef_wide_lagged_probe_t379.py` (thread closed) | — | — | **RETIRED 2026-11-19** |
| 25 | Backtest research panels: the multi-decade price substrate; the FRED macro panel (yield curve, credit, unemployment, dollar, real rate); the Engine E HMM regime; SimFin fundamentals (4 of the registry's 6 active edges); CFTC COT; the insider cache; earnings; the VIX term structure; the 13F panel; the Lazy-Prices similarity panel; dictionary news sentiment (`news_features` → `scripts/news_interaction_tests_t289.py` only) | `engines/`, `backtester/`, `core/feature_foundry/`, research scripts | none live | none | **BACKTEST-ONLY.** Not counted in the headline. |

### The headline

Rows 1–24 are the sources the live system reaches.

- **3 of 24 feed a paper-order decision**: prices, the split feed and news. **Only 2 feed a decision without an LLM in between**: prices and the split feed.
- **6 of 24 feed only shadow books or scoring** (rows 4–9). **4 of those 6 are blind in the cloud**: rows 4 and 5 by step order, rows 6 and 7 because the file is not there.
- **15 of 24 are archived and read by nothing** (rows 10–24). **12 are still collected**, daily or weekly. Each one is a network dependency, a user-agent and privacy surface, and an alarm surface.
- Account 3's own resolved and open predictions feed back into its next note (`context_builder.py:184-204`). That is internal feedback, not a source, and is not counted.

### Three ways information is lost

All three are silent today.

1. **Not in the container.**
   - The 8-K panel and special-sits files are in no image and no sync, and the readers return an empty list rather than a degraded flag (`eightk_feed.py:82-83,111-112`). The run reports "ok, 0 documents".
   - This is the `[NN-FAIL-CLOSED]` / silent-wrongness shape: a stopped clock with a good excuse.
2. **Read before it is synced.**
   - The intel pulse (`run_paper_cloud_day.py:1325-1336`) and the eval harness (`:1382-1410`) read `data/macro_data/alt/`. In a fresh Fargate container that directory first appears at the alt-data pull (`:1658`), which runs after both.
   - The 11-19 health row notes these readers only as "reads only, no production effect". The step order, which blinds them in the cloud, is not recorded anywhere.
   - Artifact check owed: in the cloud `data/intel/analyst_eval_summary.json`, `unresolvable_reasons` for `event_occurs` resolvers should read `source_absent_or_unsettled`.
3. **Fed by nobody.**
   - `ThesisBook.record(..., falsifiers_fired=...)` has no production caller. The driver calls `_tb.record(str(today), closes=_tpx)` (`run_paper_cloud_day.py:1216`), and the eval harness never loads `thesis_calls.jsonl`.
   - Every machine-checkable falsifier therefore degrades to its `check_by` deadline (`thesis_book.py:258-263`).

### The instrument-universe mismatch

This structural point limits everything above.
- The information the project collects is overwhelmingly **single-name**: 8-K, Form 4, short interest, FTDs, company-tagged news.
- Every book that places orders trades **two or three ETFs**.
- A desk maps information to instruments. Here, single-name information has nowhere to go except the shadow books: the event desk and the thesis book can name any ticker; the real-order books cannot. Better plumbing does not fix this. It is a choice about which instruments each stream may trade, and that choice belongs to the owner's risk preference and the wrapper.

---

## Part 4 — The gap, ranked by how much it limits the system

**G1. No route from information to a sized decision outside the LLM.** *Limits everything.*
- The two non-AI books read prices only, by design. That is defensible: the trend rule and the static core are the measured defaults, and regime-gating the trend rule was measured to hurt (charters, Engine E validated finding 4).
- But the consequence is that "use more information" can only mean "give the LLM more to read", and the LLM can only act on three ETFs.
- The charter path (A emits a signal → B sizes → C composes) is not on the paper path at all (`PaperOrderConstructor` is unwired).

**G2. Orders carry no reason, so nothing can be reviewed.** *Limits learning.*
- `OrderRecord` (`order_manager.py:164-184`) stores ticker, side, quantity, TIF and fills: no stream rule, no thesis id, no expected payoff, no invalidation, no sizing basis.
- Account 3's predictions (scored by the eval harness) are **decoupled** from its positions (bare weights). So "was the AI right?" and "did the AI's trades make money?" are separate records that cannot be joined.
- Without the join there is no per-trade review, no monitoring against the thesis, and no calibration evidence for conviction sizing.

**G3. The desks that have theses don't trade; the desk that trades has no thesis.** *Limits the AI track's value as evidence.*
- `thesis_call/v1` and `event_call/v1` are desk-grade: falsifiers with dates and resolvers, materiality, direction, resolvable predictions.
- Account 3 uses a third, thesis-less contract instead.
- The account-3 prompt still says "You … take NO actions, and place NO orders" (`daily_v4.md:23-26`) two paragraphs before saying the actions are consumed (`:37-41`). It also cites a "99% SSO position" (`:55-57`) that no account has held since account 2 was repurposed on 2026-09-11.
- The note is also built with account 1's holdings as its portfolio context (`run_paper_cloud_day.py:1331`, `portfolios={"sleeve": _held_w}`), and those weights are then applied to account 3.

**G4. Information we collect never reaches the desks we built.** *Cheap to fix, and it unblocks the only fast evidence class.*
- The three mechanisms above (Part 3): the 8-K feed and special-sits are absent, the rate path and the KXFED ladder are read before they are synced, and falsifier resolution is never fed.
- The event desk is the one place where evidence accrues per event: T-304 measured ~14–18 allowlisted 8-K items a day, and its bar is ≥30 closed per event type. It has been starved since birth.

**G5. No risk manager over the whole book on the live path.** *Limits safety before real money; small effect on paper P&L.*
- No pre-trade gate at submit (09-17 A5), no price collar (A2), no exposure aggregation across the fleet, no automatic loss-limit halt, no stress readout, no event-risk rule, no hedge.
- Engine B's backtest machinery (stops, vol target, sector caps, conviction scaler) never reaches the fleet.

**G6. Sizing ignores conviction where conviction exists.**
- Three inconsistent conviction→size rules in shadow books (`thesis_book.py:211`; `event_shadow_book.py:242`; `risk_engine.py:1209`). None is calibrated, and none lives in Engine B, which the charter names as the owner ("If higher confidence should mean larger size, that should be expressed through A's strength value", Engine B design notes).
- On account 3 the LLM sizes directly. That is the charter's "B becomes a second alpha engine" anti-pattern, inverted: the alpha source has become the sizer.

**G7. No event calendar beyond FOMC dates.**
- Nothing on any live path knows a CPI, payrolls, earnings or ex-dividend date.
- The Kalshi macro archive (row 10, zero consumers) already holds expiry times and implied probabilities for scheduled releases. It is a free calendar source no one reads.

**G8. No allocation across streams by track record.**
- Correctly human-gated today. The gates exist (stage-2 clock, T-304 bar 5, T-324), but there is no single per-stream scorecard and no composer.
- **The prior is poor:** the 07-02 whole-project audit records that "smarter allocator above strategies" failed three internal tests and a 50-year external test.
- Lowest priority of the buildable items.

**G9. No options layer.**
- The wrapper allows long options (conservatively Level 2), but there is no options data, chain, or order type anywhere.
- As a hedging layer, a crisis hedge's value cannot be proven from history (there are too few crises), so it is a belief decision. T-410 covers options as ideas.

**G10. Architecture drift makes every new desk piece expensive.**
- `main()` is **1,403 lines** (`run_paper_cloud_day.py:381-1783`), up from 1,156 at the 09-17 audit, with every report-only step inlined into the account-1 branch.
- The step-registry extraction (director YES, pending the user's word, per `CURRENT_STATE.md` In-flight) is a prerequisite for G2 and G5. Otherwise each piece lands in the god-function.

**Where the existing design is already right** (keep it verbatim):
- signal at t, fill at t+1, and the PIT guards;
- reject-whole-never-clamp firewalls;
- a halt that never liquidates;
- the corporate-action gate;
- desk-grade thesis and event schemas;
- shadow books with matched twins and pre-stated promotion bars, which is exactly how a desk incubates a new PM;
- Brier scoring against market-implied and persistence baselines;
- the trend rule without a regime gate;
- keeping the LLM on its own account;
- fail-closed stale-data refusals;
- the arrival-price slippage ledger.

---

## Part 5 — A minimal target architecture

**Design rule:** reuse what exists. Every component must work for a **non-AI** stream first (the trend sleeve, the static core, a deterministic per-event rule). LLM streams use the same contracts but stay on account 3 and in shadow books under `[NN-AI-GATE]`.

```
Data Manager — SOURCE REGISTRY: path · cadence · PIT column · where available · sync step · declared readers
   │   census each run: every declared reader ran AFTER its source was present; every source has a reader or a retirement reason
   ├──► E — CONTEXT + EVENT CALENDAR: FOMC · macro releases (Kalshi series expiries + implied probabilities) · earnings/ex-div for holdings
   ├──► A / STREAMS — each emits decision/v1 {stream, direction, conviction, horizon, expected payoff (resolver/v1), invalidation (resolver/v1 | level, check_by)}
   │        non-AI: trend sleeve · static core · per-event rules      [AI, account 3 + shadow]: analyst · agentic · event interpreter · thesis scan
   ├──► B — RISK DESK (veto): conviction→size (one function, FLAT until calibrated) · pre-trade gate · collar · event-risk rule · loss-limit halt · stress readout
   ├──► C.1 — LEDGER links every fill to decision_id     C.2 — netting + fleet risk budget (later: the portfolio brain)
   ├──► MONITOR — daily: resolve each open decision's invalidation with A's resolvers → exit PROPOSAL through B
   └──► F — REVIEW: per-decision outcome vs expectation · P&L = thesis + beta + execution + cost · per-stream scorecard · promotion bars (F proposes; the user decides)
```

| Component | Owner (per charter) | Reuse (repoint, don't rebuild) | New | Validation (forward, per decision; never a ≤26-yr backtest) | Flags |
|---|---|---|---|---|---|
| **C1 Source registry + census** | Data Manager (neutral module, like `core/edge_registry_io.py`) | `altdata_archive._FEED_HEALTH` (`:78-110`), `cloud_state` path lists (`:40-215`), `clock_census` registry and channel liveness | One declared table with `available_in` and `readers`; two census checks | First artifact: the census line on all three accounts. Proven by reversion: move the sync back and the check FAILS. | Census wiring is in the daily run **[PF]**; report-only |
| **C2 Event calendar** | **E** (it describes; it never sizes or vetoes) | `engines/data_manager/macro_calendar.py`, `config/fomc_calendar.json`, the Kalshi macro series (row 10), `engines/data_manager/earnings_data.py`, the Alpaca corporate-actions feed (dividends) | A calendar context object published to B and to the bundles | As context: by first artifact. As a risk input (C5's event rule): a pre-registered per-event record (realized move and slippage on event vs matched non-event days, and the rule's cost in skipped drift), registered in `config/honest_n_trials.json`. T-291 already refuted FOMC state as a *return* predictor, so the claim here is risk/process only, with a small prior. | Charter text for E's inputs **[PF]** |
| **C3 Decision record (`decision/v1`)** | **A** forms it; **C.1** ledgers it (journal `decision_id`) | `thesis_call/v1`, `event_call/v1`, `note_schema.Prediction`, resolver/v1, the OrderManager stream token, the lot-recorder pattern (`run_paper_cloud_day.py:555-591`: record, never alter, the submit path) | A schema; one journal field; a `decisions.jsonl` per account | First artifact: every staged order on all three accounts has a decision row. Lock: the submit payload is byte-identical. Systematic streams carry a STANDING thesis (the rule and its pre-registered expectation, e.g. the sleeve's "MaxDD shallower than both robos"); discretionary streams carry one per trade. | Paper path **[PF]**; closes the LOW "journals carry no sizing metadata" row |
| **C4 Conviction → size** | **B** (charter: A emits strength; B maps it to size) | `risk_engine.py:1207-1209`, `thesis_book._basket_weights`, `event_shadow_book` sizing, all replaced by ONE function | Calibration-gated `f(conviction)`, flat until it clears | Per stream: reliability slope of conviction vs resolved outcome, block-bootstrap `ci_low > 0` over ≥ N resolved calls (powered by count, not years). Then a paired shadow A/B (flat vs scaled) on IDENTICAL calls. Pre-registered; trials registered. | Engine B **[PF]** |
| **C5 Risk desk: veto + overlay** | **B** | 09-17 audit A2/A5 design (marketable-limit collar; gate: notional ≤ cap, sell ≤ held on long-only, orders/day ≤ K); `trading_halt.py` (the loss-limit writes the halt file with a reason and never liquidates); `fleet_mirror` slices (fleet exposure); the T-306 substrate and `MetricsEngine.expected_shortfall` (stress readout) | Gate in the `OrderManager.submit` seam; loss-limit rule; event-risk rule (from C2); stress readout (report-only) | Drills that force each refusal and observe the journal line (the 09-17 protocol); the stress readout checked by construction (replaying a shock reproduces the T-306 number for the same weights). Options hedging: later, only as an owner belief decision, with new data. | Engine B + paper path **[PF]**; after the `main()` extraction |
| **C6 Monitor and invalidation** | **B** enforces; **A**'s eval harness resolves | `eval_harness.resolve` (`:207-267`) already resolves every resolver/v1 type; the `ThesisBook` `falsifiers_fired` parameter exists | One wiring call; an exit proposal through the same pipeline for real-order streams | First artifact: a resolver falsifier resolves TRUE and the book closes the next session. Track invalidation exits vs deadline exits. | Paper path **[PF]**; LLM-filed theses stay shadow **[AI]** |
| **C7 Review and attribution** | **F** (charter inputs: trade logs with attribution from C.1) | `thesis_book.outcomes`, event-book closed records, `eval_harness` summary, `exec_cost_ledger`, `fleet_scoring`, `performance_digest` | Per-decision rows; the split P&L = thesis (excess vs twin) + beta (twin) + execution (vs arrival) + cost | Identity check: attributed P&L sums to the account's P&L to the cent, per day. | F's charter says "edges"; extending it to "streams" is charter language **[PF]** |
| **C8 Stream allocation** | **C.2** composes; **F** gates | Stage-2 clock, T-304 bar 5, T-324 `promotion_check`, `forward_plan`'s "portfolio brain" (report-only brain book; authority only by beating its twin) | Nothing new until per-stream records exist | The existing bars, unchanged. F proposes; the user decides; the gates are never autonomously modifiable. | **[PF]**; lowest priority (poor prior) |

**Boundary rulings this architecture implies** (each one is a charter-language change **[PF]**):

1. **Chart the product.** Map the paper-path modules into the engines:
   - constructors → A (signal) + B (size);
   - corporate-action gate, halt and firewall → B;
   - `ledger_store`, reconciliation → C.1;
   - trackers, digest, eval harness → F;
   - `altdata_archive`, `news_panel` → Data Manager;
   - the calendar → E;
   - the intelligence layer → A, on the exploration track.
2. **An LLM stream emits forecasts, not weights.** On account 3 today the model's output is final target weights, so the model does A's, B's and C's jobs, and the deterministic layer only vetoes. In the target, the LLM emits a `decision/v1` (direction, conviction, horizon, expected payoff, invalidation) and **B sizes it**. As A, the model then sees **no** portfolio state (A's forbidden inputs). That fixes the account-1-portfolio-in-the-bundle oddity by removal, not by substitution. This is a prompt version (daily/v5) on the AI track, logged in `docs/Core/prompt_evolution_log.md`. **[AI][PF]**
3. **One conviction→size function, in B.** Retire the three local rules into it (shadow books first).
4. **E publishes the calendar; it never acts on it.** B decides what an event means for size. That respects the Double-Counting Matrix: the event fact affects at most B (constraint) and A (feature).

**How the AI fits (`[NN-AI-GATE]`).** The system without AI has not beaten the robo: 85/15 is "the prior, not a finding" (B-9: +0.079, ci_low −0.066), and the last digest quoted in `CURRENT_STATE.md` (10-30) reads 0 of 9 streams beating. So:
- every LLM component (constrained analyst, agentic analyst, event interpreter, thesis scan, watchdog) stays on the exploration track: shadow books plus account 3;
- C1–C8 are AI-agnostic and are validated first on the non-AI streams;
- the event interpreter is the strongest exploration candidate, because its evidence accrues per event. It still reaches orders only on account 3, and only after its own pre-registered bar (T-304 bar 5).

---

## Part 6 — Phased plan

### Phase 1 (about one week): let the information we collect reach the desks we built, and prove it every run

No order changes. Everything below is report-only in effect.

1. **Source registry and census checks (C1).**
   - Declare every row of Part 3 with `available_in` and `readers`.
   - The census fails a day when a declared reader ran before its source was present, and lists every source with no reader.
   - The module is buildable now; wiring it into the daily run is **[PF]**.
2. **Step order.** Sync the two small files the pulse and the eval read (`kalshi_kxfed_snapshots`, `fred_rate_path`; ~230 KB), or the whole alt-data pull (~80 MB, already pulled at `:1658`), before the intel pulse. **[PF]**
3. **A live 8-K feed for the event desk.**
   - A daily EDGAR filings pull for the tracked universe in the alt-data step, writing a forward panel under the synced `altdata/` prefix. EDGAR is already called by the Form 4 pull and the 8-K body fetch, so this is not a new external service.
   - `eightk_feed` reads the forward panel.
   - A missing panel becomes `degraded` with a reason, never a silent `[]`.
   - **[PF][AI]**: the interpreter is an LLM; its output stays in the shadow event desk.
4. **Falsifier wiring (C6, shadow half).** The eval harness resolves open theses' resolver-kind falsifiers and passes `falsifiers_fired` to `ThesisBook.record` (`:1216`). **[PF]**

**First artifacts** (all must be observed, per `[NN-FIRST-ARTIFACT]`):
- the census line on all three accounts;
- `event_calls.jsonl` gaining rows;
- the event desk's first opened position;
- the eval summary showing a KXFED or FOMC resolution, or a market-implied baseline;
- a falsifier resolving.

**Drills:** remove the synced file and the census fails; stall the 8-K feed and the day is `degraded`, not "ok".

**Honest scale:** at T-304's measured volume, the common event types could reach the bar's 30 closes in weeks to months. That should be measured on the first artifact, not assumed.

### Phase 2 (weeks 2–4): every order carries its reason

Prerequisite: the `main()` step-registry extraction, which is already sequenced first by the director, pending the user's word.

1. `decision/v1` plus the journal's `decision_id` on all three accounts. Standing theses for the trend sleeve and the static core; per-trade records for account 3 (note id, prompt version and its predictions). The submit path is byte-identical (lock). **[PF]**
2. The account-3 prompt moves to forecasts, not weights, with B sizing **flat** until calibration clears (C4). **[AI][PF]**
3. Per-decision rows in the weekly digest, with the P&L identity check (C7).

**First artifact:** the next run's journal rows carry decision ids on all three accounts, and the digest's first per-decision table reconciles to the cent.

### Phase 3 (month 2 onward): a risk desk with a veto

1. The Engine B pre-trade gate and collar (09-17 A2/A5), the fleet exposure read, a pre-registered per-stream loss-limit halt, and the stress readout (report-only). **[PF]**
2. The event-risk rule from E's calendar, as a pre-registered per-event test. Kill it if it does not clear. **[PF]**
3. The conviction→size function turns on only for a stream whose calibration slope clears (C4). **[PF]**
4. Only then: the portfolio brain (C8) as a report-only book. Options hedging only as an owner belief decision.

---

## Part 7 — Findings for `docs/State/health_check.md`

This task was briefed not to edit `docs/State/*`, so these are **proposed rows** for the director to land. Dates are 2026-11-20; each was found by this audit at `e68251b`.

1. **[MEDIUM] The event desk's input has never existed in the cloud.**
   - The 8-K panel (`data/edgar/8k/panel_8k_items.parquet`) and the special-sits file are in no image and no sync, and `eightk_feed` returns `[]` silently (`intelligence/event_call/eightk_feed.py:82-83,111-112`).
   - The local panel is batch-built and frozen at 2026-06-10. The desk had opened 0 positions in 38 sessions as of the 09-18 sweep.
   - **Next step:** decide a forward 8-K feed (Phase 1, item 3) or retire the desk. Either way, make a missing panel a `degraded` reason.
2. **[MEDIUM] Step order blinds three report-only readers in the cloud.**
   - The intel pulse (`run_paper_cloud_day.py:1325-1336`) and the eval harness (`:1382-1410`) read `data/macro_data/alt/` before the first alt-data sync (`:1658`).
   - Affected: the agentic `query_rate_path`, the thesis-scan rate path, the eval's `kalshi_settlement` / `fomc_calendar` resolutions, and the KXFED market-implied baseline.
   - **Next step:** an artifact check (the cloud eval summary's `unresolvable_reasons`); then move the sync earlier. **[PF]**
3. **[MEDIUM] Thesis-book falsifiers are never resolved.**
   - `falsifiers_fired` has no production caller (`run_paper_cloud_day.py:1216`; only `tests/test_thesis_book_t326.py:128` passes it), and the eval harness does not load `thesis_calls.jsonl`. Resolver falsifiers are deadline-only.
   - **Next step:** wire the resolution (Phase 1, item 4), or relabel the falsifiers as deadlines in the book's output.
4. **[MEDIUM] Account 3's AI trader decides from a note that misdescribes its own situation.**
   - The bundle's portfolio is account 1's sleeve (`run_paper_cloud_day.py:1331`).
   - The prompt says it places no orders (`config/prompts/analyst/daily_v4.md:23-26`) and cites a 99% SSO position no account holds (`:55-57`).
   - The model sets final weights, collapsing A/B/C into one output.
   - **Next step:** an AI-track prompt revision plus the boundary ruling in Part 5. **[AI][PF]**
5. **[LOW] `PaperOrderConstructor` (A→C→B on the paper path) has only test callers.**
   - Its docstring claims it "wires the PRODUCTION order-construction path" (`paper_trader/order_construction.py:1-16,48`).
   - **Next step:** archive it, or adopt it as C3/C4's seam.
6. **[LOW] `main()` is 1,403 lines** (`run_paper_cloud_day.py:381-1783`), up from 1,156 at the 09-17 audit.
   - **Next step:** the already-proposed step-registry extraction.
7. **[LOW] A bare `sigma <= 0` guard in the measurement path** (`intelligence/analyst/eval_harness.py:319`, the persistence baseline). This is the `[NN-FP-GUARDS]` pattern.
   - **Next step:** a tolerance guard (`< 1e-12 or not finite`).
8. **[LOW] Twelve archived sources are still collected with zero code consumers** (Part 3, rows 10–21).
   - Each is a daily network, user-agent and alarm surface. The project's own rule (GDELT/NAAIM precedent) is "retire or name a consumer".
   - **Next step:** the owner decides keep-as-asset vs retire per source. The C1 registry makes the choice explicit.

---

## What this document does not claim

- It does not claim that any information source carries a tradeable edge. The kill record says most do not as stand-alone signals.
- It does not claim that the desk architecture will raise returns. Its claims are process, risk and the speed of honest evidence.
- No Sharpe is quoted. No measurement was made. 0 trials were consumed.
- Cloud-side states marked "artifact check owed" were inferred from code and step order, not observed.
- Line numbers are at `e68251b`.
