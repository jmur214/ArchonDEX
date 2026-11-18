---
task_id: T-403
title: DRAFT pre-registration — forward paper probe of the near-close favorite–longshot bias on Kalshi (taker form)
date: 2026-11-17
worker: edge-analyst (worktree agent-a04169e789bfe3536)
status: DRAFT — NOT FROZEN. Nothing recorded, nothing run, no recorder built. The trial count is NOT stated here; the director rules it at freeze.
design_note: docs/Sources/design_note_prediction_markets_t403_2026-11-17.md
---

# T-403 DRAFT: does buying the favourite at the close, as a taker, beat Kalshi's fees?

> **DRAFT.** Every number below is proposed. It binds only once the director freezes this file: commits it with a freeze stamp, a start date and the ruled trial count, before the recorder writes its first decision row. Until then nothing may be recorded under this hypothesis's name.

## 1. Hypothesis (chosen ex ante from the literature, never from our data)

**H1.** On Kalshi, a binary contract's favourite side, bought as a **taker** at its displayed best ask in **[0.90, 0.99]**, between **24 h and 1 h before** the market's scheduled close, earns a **positive mean net return per event** after Kalshi's published taker fee. "Mean" is equal-weighted across events.

**H0.** The mean net return per event is ≤ 0.

**Theory, stated before any data:**
- Bettors over-weight small probabilities (Prospect Theory). Snowberg & Wolfers find misperception, not risk-love, drives the favorite–longshot bias [note S26].
- On Kalshi, Bürgi, Deng & Whelan (BDW) document the bias in every year 2021–25, every category, every horizon to 10 days, and every volume and transaction-size quintile [note S1].
- On the closing day, losses on cheap contracts are as large for makers as for takers, "a version of Page's (2012) Yogi Berra effect" [note S1 §4]. That is, favourites are cheapest near the close.

**What the literature says against H1** (recorded so the result cannot be spun):
- BDW: takers "still lose money on average" as prices rise.
- The positive post-fee cell is makers buying ≥ 50c (+2.6 %, SD 33 %), before maker fees existed.
- The bias coefficient for Jan–Apr 2025 (0.021) is less than half that of 2024 (0.048).
- My arithmetic from BDW's coefficients puts the taker's expected net edge at about 0 overall and about −1.3 % on the 2025 coefficients (design note §4).

**Prior: 20 %.**

**Scope.** This is ONE hypothesis. The other candidates are excluded (design note §4):
- the maker form, which cannot be paper-tested honestly;
- longshot selling, which is the same trade as H1;
- cross-venue gaps, which cannot be paper-tested.

No other rule, band, window, category subset or venue may be promoted from this record (§12).

## 2. Hard pre-commitments

1. **Forward only.** No backtest on any archive (`data/macro_data/alt/*`, Kalshi `/historical/*`, ForecastEx CSVs, or anything else) may be used to choose, tune or "sanity-check the edge of" this rule. The archive was used for a census only: counts, dates, field completeness and spreads (design note §1).
2. **One gating configuration**, given in full in §3–§4. Every parameter comes from BDW's sample definition or from what an hourly unattended job can execute; none was chosen by looking at returns.
3. **No tuning after any result.** The sensitivities in §11 are named now. They are reported beside the headline and never replace it.
4. **Append-only, timestamped before resolution.** Each decision row is written ≥ 1 h before the market's scheduled close and hash-chained. Nothing is back-filled from later data. Missed scans stay missed.
5. **Fees from the live venue,** at each decision. The recorder reads `fee_type` and `fee_multiplier` per series. When the schedule and the API disagree, it uses the **higher** fee.
6. **Fixed, result-blind evaluation timing** (§8.1). There is one futility look (§8.4) and no other peeking for decisions. Operational health is monitored through the census only (§9).
7. **No money, no account.** Public no-auth endpoints only. A generic User-Agent with no contact details.
8. **Determinism ×2 at evaluation.** The evaluation script's output JSON must be md5-identical over two runs on the frozen record before any number is quoted.

## 3. Universe and eligibility (applied at each scan)

A market is **eligible** at scan time `t` if ALL of the following hold:

| # | Condition | Source / rationale |
|---|---|---|
| E1 | Kalshi market, `status = open`, `market_type = binary`, not multivariate (`mve_filter=exclude`) | BDW universe |
| E2 | Its series `category` ≠ `Sports` | BDW is mostly pre-sports. In-play sports is a latency game ("sports data feeds will be required", note S2), and state legal risk applies |
| E3 | Series `frequency` ∉ {`hourly`, `fifteen_min`}, and the market was open ≥ 24 h (`close_time − open_time ≥ 24 h`) | BDW: "markets that are open at least 24 hours" |
| E4 | `close_time − 24 h ≤ t ≤ close_time − 1 h` | Closing-day horizon (BDW's day 0). The 1 h margin is the minimum an hourly unattended scan can honour; it does not try to race the final minutes |
| E5 | Traded volume `volume_fp ≥ 1,000` contracts at `t` | Proxy for BDW's ≥ $1,000 final-volume floor (the final volume is unknowable at decision time) |
| E6 | One side's best ask (from the order book: 1 − the best bid on the other side) is in **[0.90, 0.99]**, and that side's own best bid is > 0 | BDW's top price bin. 0.99 is kept: excluding it would be tuning |
| E7 | Spread on that side (ask − bid) ≤ 0.20 | BDW: "drop contracts where the final bid–ask spread is larger than 20c" |
| E8 | `fee_type` ∈ {`quadratic`, `quadratic_with_maker_fees`, `quadratic_with_combo_maker_fees`} with a numeric `fee_multiplier` | Any other value → skip and log (fail closed) |
| E9 | No decision already recorded for this market | One decision per market, at its first eligible scan |

Given E7, at most one side can satisfy E6. That side is **the favourite**.

## 4. The decision rule (paper)

- **Scan cadence:** hourly, at minute 05 UTC.
- **Order:** BUY the favourite side, at its best ask `a`, as a taker.
- **Size:** `C = floor(min(25.00, a × depth_at_best_ask) / a)` contracts. That is up to $25 of contract cost, at the best level only; the rule never walks the book.
  - If `C × a < 5.00`, skip and count the market as `skipped_depth` (no decision row).
- **Fee:** `fee = ceil_to_cent(0.07 × fee_multiplier × C × a × (1 − a))`, for the whole order.
  - If the series is an S&P 500 / Nasdaq-100 series with the 0.035 specific schedule, use `max(0.035, 0.07 × fee_multiplier)` as the coefficient.
- **Cost:** `C × a + fee`.
- **Hold to settlement.** No exit, no re-entry, no averaging.
- **Payout at settlement:** `C × settlement_value_for_the_side`. This is 1.00 or 0.00, or a fraction if the exchange settles at a "last fair price" (temperature contract terms, note S15).
  - **Void or cancelled:** the payout equals the cost, so net 0, and the market is counted as `void`.

## 5. Recorded at decision time (append-only, `decisions` stream)

| Field | Meaning |
|---|---|
| `decision_id` | `sha256(ticker ‖ rule_version)` |
| `scan_id`, `decision_ts_utc` | Local UTC time, plus the server `Date` header. The scan is degraded if they differ by > 30 s |
| `rule_version` | git SHA of the recorder + SHA-256 of the frozen rule config |
| `market_ticker`, `event_ticker`, `series_ticker`, `category`, `frequency`, `market_type` | Identity |
| `open_time`, `close_time`, `expected_expiration_time`, `hours_to_close` | Timing (E3, E4) |
| `fav_side`, `best_ask`, `depth_at_best_ask`, `second_level_ask`, `second_level_depth` | The executable price |
| `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `spread_fav` | The quote |
| `volume_fp`, `open_interest_fp`, `liquidity_dollars`, `last_price_dollars` | Context; never used to decide anything beyond E5 |
| `fee_type`, `fee_multiplier`, `fee_coefficient_used`, `contracts`, `fee`, `cost` | Fee-inclusive cost |
| `decision` | Always `BUY_FAV` (an ineligible market writes no row; its counts go to `scans`) |
| `prev_hash`, `row_hash` | SHA-256 chain over the whole stream |

Each day's file SHA-256 is written to a write-once, versioned S3 object (object lock) **before** the next day begins. The evaluation recomputes the chain and every daily hash. Any break voids the affected day and is reported.

## 6. Resolution recording (append-only, `resolutions` stream)

- **Polling.** From `close_time + 1 h`, poll `GET /markets/{ticker}` once an hour until `status ∈ {settled, finalized}` and `result ∈ {yes, no}`, or a void or scalar settlement is reported.
- **Row:**
  - `market_ticker`, `observed_ts_utc`, `status`, `result`;
  - `settlement_value_dollars` (for the favourite side), `settlement_ts`;
  - `is_void`, `payout`, `net_pnl = payout − cost`;
  - `prev_hash`, `row_hash`.
- **Integrity.** A resolution row may never be written for a decision whose `decision_ts_utc` is not < `close_time − 1 h`. The evaluation re-checks this for every pair.
- **Unresolved after 14 days:** flagged in the census. At evaluation, a decision still unresolved is counted at **net −cost**, a total loss, for the headline. This is conservative and announced, never dropped.

## 7. Unit of analysis and dependence

- **Unit = the Kalshi event (`event_ticker`).** Event net return `r_e = Σ net_pnl / Σ cost` over the event's recorded markets.
  - Mutually exclusive buckets of one event are perfectly dependent, so they are never treated as independent.
- **Clusters = resolution date** (the ET calendar date of the event's last settlement). All events of a date move together in the bootstrap and in the cluster-robust SE.
- **Sensitivity clustering:** (series, ISO week). This catches multi-day weather systems and repeated releases.

## 8. Metric, gate and verdicts (numbers fixed now)

### 8.1 When the one evaluation happens (result-blind)

- The evaluation runs at the first month-end at which BOTH hold:
  - ≥ 12 months have passed since the first decision row;
  - ≥ 3,650 events have resolved.
- Otherwise it runs at 24 months, whichever comes first.
- Resolutions get 14 days of grace after the cutoff.

### 8.2 The headline

- `r̄` = equal-weighted mean of `r_e` over all evaluated events.
- `ci_low`: a one-sided lower bound from a **moving-block bootstrap over resolution dates**.
  - The block length is chosen by Politis–White on the daily mean series; there are 2,000 iterations with a fixed seed.
  - The confidence level is one-sided `1 − α`, where `α = 1 − Φ(z_c)` and `z_c = max(1.645, E[max of N_ruled iid N(0,1)])`, with `N_ruled` the director's trial count at freeze.
- `t_CR`: the cluster-robust t-statistic (CR1, clusters = resolution date).

### 8.3 Verdicts

**PASS** requires ALL of:

| # | Condition |
|---|---|
| P1 | `ci_low > 0` |
| P2 | `t_CR ≥ z_c` |
| P3 | `r̄ ≥ +0.50 %` per event (materiality) |
| P4 | Projected net dollars per year = `r̄ × mean cost per event × events per year (observed)` ≥ **$300** |
| P5 | No single category supplies > 50 % of total net P&L, AND `r̄ > 0` in ≥ 3 of the 4 calendar quarters of the first 12 months |
| P6 | Census clean: ≤ 5 % of scheduled scans degraded or missing; ≤ 1 % of decisions unresolved at evaluation; zero chain breaks outside voided days; ≥ 200 distinct resolution dates |

**REFUTED** if `r̄ ≤ 0` at evaluation, or at the futility look (§8.4).

**INCONCLUSIVE** if `r̄ > 0` but any of P1–P5 fails. The probe closes. A re-test is a new pre-registration and a new trial; there is no extension beyond §8.1.

**VOID** if P6 fails, or any integrity check in §5–§6 fails. The record cannot be scored. Whether a corrected restart is allowed is the director's ruling.

### 8.4 One futility look (it can only stop for failure)

At 6 months: if `r̄ ≤ −0.50 %` AND `t_CR ≤ −2.0`, the probe stops as **REFUTED**. There is no early stop for success.

### 8.5 Minimum detectable effect (planning; design note §5)

Planning values: per-event SD 0.20, design effect 1.5, 80 % power. At 20 events/day the MDE is:
- **0.71 %** at 12 months at `z_c` 1.645;
- **1.09 %** at `z_c` 2.96 (N_eff ≈ 372).

At 10 events/day the MDE is 1.01 % / 1.54 %. A true edge of +0.3 % passes at 12 months with probability 28 % at z 1.645 and 3 % at z 2.96. **The probe is a kill-test first.**

## 9. Fail-closed and census requirements

These are the probe's version of `[NN-FAIL-CLOSED]` and `[NN-CENSUS]`.

- **Each scan writes a `scans` row:**
  - scheduled time and actual time;
  - pages read, and whether the market list was truncated;
  - markets seen, screened by E1–E8, eligible, `skipped_depth` and decisions written;
  - orderbook read failures, clock skew;
  - `degraded` (bool) and `skip_reason`.
- **A degraded scan writes no decisions** for the markets it could not read fully. It never fills from stale or zero data.
- **Daily census** (also written to S3):
  - scans scheduled / run / degraded;
  - decisions; resolutions; unresolved > 7 days; voids;
  - chain-verification result;
  - the day's fee-type mix.
- **Alarms:** zero decisions on a day with ≥ 50 screened markets, a chain break, or > 24 h with no scan alerts the director's channel. The alarm is designed to fire only on these conditions, not on ordinary quiet days, so that it does not cry wolf.
- **`[NN-FIRST-ARTIFACT]`:** the probe is "started" only when a scheduled cloud firing has written a decision row, a later firing has written its resolution, and both have been read back from S3 and chain-verified.

## 10. Holding it to the same gates as everything else, later

1. **This probe** is gate 1: forward, pre-registered, with a CI-aware decision (`[NN-SHARPE-CI]` analogue, gating on `ci_low`) and a trial-count-aware bar (`[NN-MBL]` analogue: z_c from the ruled N).
   - A daily-P&L Sharpe with its block-bootstrap `ci_low` is also reported for comparability, but it does not gate.
2. **A PASS buys only a pre-registered real-money pilot** (owner's account, tax ruling, small capital).
   - Paper → real is a substrate change (`[NN-SUBSTRATE-REVERIFY]`). The pilot must reproduce `r̄ > 0` with `ci_low > 0`, using real fills, real slippage and the real fees.
3. **Integration** into the system would then face:
   - the after-tax, net-of-cost comparison with the same capital's alternative use (the robo / VOO frame);
   - DSR at the honest N;
   - the census;
   - Engine F's lifecycle;
   - Engine B's risk limits (propose-first);
   - the `live_trader` boundary.
4. **No AI component** is involved (`[NN-AI-GATE]`).

## 11. Sensitivities (reported, never gating)

- **Ask sub-bands:** [0.90, 0.95), [0.95, 0.99), {0.99}.
- **By category:** each with ≥ 300 events.
- **By hours-to-close tercile** at decision.
- **Clustering:** by (series, ISO week) instead of by date.
- **Weighting:** dollar-weighted instead of event-weighted `r̄`.
- **Unresolved decisions** treated as dropped instead of as total losses.
- **Fee coefficient** as read from the API versus the higher of schedule and API.
- **An exploratory, non-gating maker view.** If the best bid recorded at decision had instead been joined, how often a later trade-through would have filled it (from the public trade tape). Exploratory only; it can never become a headline or a promotion basis.

## 12. Not allowed

- Choosing or changing any E-condition, the band, the window, the stake, the fee rule or the unit after the first decision row.
- Adding categories or venues, or a second hypothesis, under this registration.
- Promoting any sub-band, category, horizon or maker view from §11.
- Back-filling missed scans; editing any row; re-running the recorder over past timestamps.
- Reading `/historical/*`, the alt-data archive or ForecastEx CSVs to "check" the rule's edge before evaluation.

## 13. Freeze checklist (the director's, at freeze)

1. Rule the **trial count** and hence `z_c`.
2. Fix the **start date** and confirm the recorder's first artifact (§9).
3. Approve **where the recorder runs** (cloud hourly job: propose-first), the S3 prefix and object lock.
4. Approve the recorder code after independent review and the full suite. Its fee function must reproduce the published schedule table exactly.
5. Confirm §3–§8 unchanged, and stamp the frozen file's SHA-256 in the ledger row.
