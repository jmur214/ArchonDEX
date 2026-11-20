---
task_id: T-407
title: DRAFT pre-registration — calibration check: does Kalshi's last pre-release forecast explain the release-day move of the book's bond sleeve (AGG)?
date: 2026-11-19
worker: edge-analyst (worktree agent-a8ac4e9ab27c1a591)
status: DRAFT — NOT FROZEN. Nothing measured. No release-day or event-conditioned return was read; only all-day volatility (for planning) and calendar-year AGG returns (for the TR convention check) were read. No Kalshi price was joined to any outcome or any asset return. This file states NO trial count; the director rules it at freeze.
design_note: docs/Sources/design_note_prediction_market_information_t407_2026-11-19.md
---

# T-407 DRAFT: is the Kalshi forecast a valid surprise instrument for this book?

> **DRAFT.** Every number below is proposed. It binds only after the director freezes this file: a commit with a freeze stamp, the ruled trial count and the frozen file's SHA-256 in the ledger row, before any Kalshi price is joined to any release outcome or any AGG return.

> **What a PASS buys, stated before the result:** exactly one thing — the project may show Kalshi's pre-release forecasts and the realised surprises to the owner as **labelled information** (the digest / advisor layer, attribution of a release-day move), and may use the measured surprise as an **input** to a later, separately pre-registered design. **A PASS licenses no trade, no tilt, no switch and no Engine A/B/E signal.** A FAIL retires the "explain the book's move" use. (Design note §5: every tradeable form fails its pass-probability arithmetic.)

## 1. Hypothesis (from the literature and a mechanism, not from our data)

**H1.** Across scheduled US macro releases that carried a quoted Kalshi ladder just before the release, the release-day total return of **AGG** is **negatively** related to the **hawkish-signed, standardised Kalshi surprise** `s_e` (actual minus Kalshi's implied median, signed so that positive = hawkish, scaled within family).

**H0.** The pooled slope `b ≥ 0`.

**Mechanism, stated ex ante.** A hotter-than-expected inflation print, a stronger jobs or growth print, or a higher-than-expected policy rate raises the expected path of short rates; bond prices fall. Any instrument that measures "expected" well should therefore carry the sign. Diercks, Katz & Wright (FEDS 2026-010, Feb 2026) find Kalshi's day-of-release CPI forecast at least as accurate as the Bloomberg consensus (headline CPI MAE 0.069 mean / 0.063 median vs 0.081; core CPI and unemployment statistically tied), and Kalshi's Fed ladder exact on the day before every meeting since 2022. They study the response of the *Kalshi fed-funds distribution* to surprises; they do not test asset returns. That gap is what H1 checks for the asset this book holds.

**What argues against a clean pass** (recorded so the result cannot be spun):
- DKW find **no significant** response of the fed-funds distribution to **payroll** surprises over 2022–25, and only a small one to **PCE** (much of PCE is known from CPI and PPI). Pooling those families dilutes the slope.
- FOMC surprises measured against Kalshi's last pre-meeting price are ≈ 0 by construction (DKW: exact since 2022), so FOMC events carry almost no slope information. The census also finds FOMC ladders one-sided before the meeting (0 of 8 sampled events with ≥ 3 two-sided strikes), so few FOMC events will be eligible at all.
- Core PCE ladders are thin (in the census, 4 of 26 settled events had ≥ 3 two-sided strikes before the release).
- A total-return series is required: AGG pays monthly; a split-only close puts a ≈ −0.3 % step on every ex-date (`CURRENT_STATE.md`: AGG is split-only in the canonical cache).

**Prior that H1 is true at a material size (|ρ| ≥ 0.25):** 85 %. **Prior that it passes this gate:** ≈ 70 % at `z_c` 2.96 and ≈ 92 % at 1.645 (§10). A fail is therefore more likely "not demonstrable on this many days" than "Kalshi mis-measures", and the verdict text must say so.

## 2. Hard pre-commitments

1. **No look before freeze.** No Kalshi price may be joined to any release value or any asset return before this file is frozen. The census in the design note read quotes and volumes only.
2. **One gating configuration** (§3–§6). Every choice below is fixed by mechanism, by Kalshi's own contract definitions, or by availability; none was chosen by looking at a slope.
3. **Fixed sample**: every eligible event whose release date is in **[2022-01-01, END]**, where END = the earlier of 2026-10-31 and the last date of the frozen AGG total-return file. (`tr_reconciled/AGG_1d.csv` ends 2026-05-22 today; refreshing it through the total-return writer is a pre-run step, or END stays 2026-05-22. The director fixes END at freeze.) Later events are not added.
4. **Determinism ×2**: the evaluation's output JSON must be md5-identical over two runs before any number is quoted.
5. **Fail closed** (`[NN-FAIL-CLOSED]`): a missing candle, a missing settled value, an unparseable timestamp, or an AGG series that is not total-return HALTS the run; it never drops the event silently or fills a zero. Every exclusion is by a rule in §3 and is counted in the census (§7).

## 3. Events, snapshot and surprise

### 3.1 Families (fixed now)

| Family | Kalshi series (legacy tickers are inside the KX series) | Released value | Hawkish sign |
|---|---|---|---|
| CPI | `KXCPI` (headline CPI m/m, "Above x %" ladder) | BLS first print, to 0.1 | + (hotter) |
| Core PCE | `KXPCECORE` | BEA first print | + |
| Payrolls | `KXPAYROLLS` (+ legacy `PROLLS`/`PAYROLLS` events inside it and in `KXPROLLS`) | BLS first print, thousands | + (stronger) |
| GDP | `KXGDP` (advance estimate, q/q SAAR) | BEA advance | + (stronger) |
| FOMC | `KXFED` ("above x %" upper bound after the meeting) | target upper bound | + (higher) |

- **One surprise per release day.** Core CPI (`KXCPICORE`), CPI y/y and the unemployment rate are the same releases as CPI and payrolls; they are **sensitivities only** (§8), never extra events.
- **Excluded:** jobless claims (the Kalshi record has a gap from 2022-12 to 2025-05, and a weekly claim moves bonds little); ISM, retail sales, recession, tariffs, shutdown, index-level and yield-level markets.

### 3.2 Snapshot

- **Release date `D`.** `D` is the ET date of the event's `close_time` if that time is before 12:00 ET (FOMC: before 15:00 ET); otherwise it is the next business day.
  - Most ladders close at 08:25–08:29 ET on release day (FOMC at 13:55 ET). Some 2021–22 events closed at 19:00 or 23:59 ET the evening before.
  - `D` is cross-checked against the official BLS / BEA / Federal Reserve release calendars; a mismatch HALTS.
- **Snapshot cutoff** = the earlier of `close_time` and 08:00 ET on `D` (FOMC: 13:00 ET on `D`). A candle ending after the release instant is **never** used.
  - This matters: the census found a few events whose ladders closed **after** the 08:30 release (close times 08:33, 10:00, 10:01, 11:13 ET). A plain "last candle before the close" would read post-release prices for those events and manufacture a near-zero surprise.
- **Duplicate events.** Two events of one family for the same release (census: `PROLLS-23DEC` and `PROLLS-23DECB`, both for 2024-01-05): keep the one with the larger total volume; the other is counted as `duplicate_event`.
- The snapshot is the **last hourly candle ending at or before the cutoff**.
  - **Candles are sparse.** An hour with no quote change and no trade has no candle, so the state carried is that of the last candle, provided it ends within the **30 hours** before the cutoff. An older last candle makes the strike unquoted for this event (`stale_quote`).
  - Each market's carried-candle age is reported in the census.
  - Market tickers are URL-encoded: one 2022 GDP event's tickers contain a space.
- Source: `GET /historical/markets/{ticker}/candlesticks` (settled before Kalshi's moving cutoff) or `GET /series/{series}/markets/{ticker}/candlesticks` (after it), `period_interval=60`, public, no auth, generic User-Agent.
- **A quoted strike:** `0 < yes_bid.close`, `yes_ask.close < 1`, `ask − bid ≤ 0.10`. Its probability is the mid `(bid + ask)/2`. Last-trade prices are **never** used (stale in thin hours).

### 3.3 Implied median and eligibility

- Order the quoted strikes `x_1 < … < x_K`. `S_k` = the mid of "above `x_k`". Enforce `S` non-increasing in `x` by pool-adjacent-violators (equal weights).
- **Rounding boundary.** The released figure is reported in steps of `h_f`, and "above `x`" pays only if the print is ≥ `x + h_f`. So `S_k` is placed at the boundary `b_k = x_k + h_f/2`. The steps are: CPI, core PCE and GDP 0.1 pp; payrolls 1k; FOMC 0.25 pp. Without this, a linear interpolation is biased by up to half a step, and the bias varies with the ladder.
- **Range-bucket events.** Some 2022–23 payroll events (`PROLLS-…`, a few early `PAYROLLS-…`) list mutually exclusive ranges instead of "above" strikes (census: `strike_type` between/less, or numeric-range subtitles). Their survival `S` at each bucket's lower edge is the cumulative sum of the bucket mids from the top. If the mids sum outside [0.90, 1.10], the event is ineligible (`buckets_incoherent`).
- **Implied median** `m_e`: the linear interpolation of `S = 0.5` between the bracketing boundaries.
- **Eligible** if `K ≥ 3` and 0.5 is bracketed (some `S_k ≥ 0.5` and some `S_k ≤ 0.5`). Otherwise the event is **ineligible**, counted by reason.

### 3.4 Released value and surprise

- **Actual** `A_e`: the settled value Kalshi resolved on (the market's `expiration_value`); cross-checked against the highest "above" strike that settled YES. A disagreement HALTS.
- **Raw surprise** `u_e = A_e − m_e`, in the family's units.
- **Standardised, hawkish-signed** `s_e = sign_f · u_e / SD_f`, where `SD_f` is the sample SD of `u_e` within family `f` over the fixed sample. (The scale uses only release outcomes and Kalshi prices, never AGG; it cannot leak the slope.)

## 4. The asset return

- `r_e` = AGG **total-return** close-to-close return from the last trading day before the release date to the release date (both 08:30 and 14:00 releases fall inside it). A release on a non-trading day uses the next trading day.
- **Shared days.** Some trading days carry two families (for example, CPI at 08:30 and FOMC at 14:00 on the same day). Such a day enters **once**: `s` is the sum of the families' `s_e`, and the day takes the fixed effect of the family listed first in §3.1. The count of shared days is reported in the census.
- Source: the substrate's total-return AGG file (`tr_reconciled`, or the post-cutover exact-TR file).
  - Checked 2026-11-19 on calendar-year returns, not on event days: `tr_reconciled/AGG_1d.csv` beats the canonical `data/processed/AGG_1d.csv` by +3.31 / +3.69 / +4.12 pp in 2023 / 2024 / 2025, which is about the yield. The first is total-return; the canonical file is split-only and **must not** be used. **Convention check:** the run verifies that no monthly ex-dividend date in the window shows a split-only step (an AGG close drop ≥ 0.2 % with the TR series flat); one failure HALTS.

## 5. Statistic

- OLS with **family fixed effects**: `r_e = a_f + b · s_e + ε_e`, pooled over all eligible events.
- One-sided test of `b < 0`.
- `t_HC3`: the heteroskedasticity-robust (HC3) t-statistic of `b`.
- **Block bootstrap** (`[NN-SHARPE-CI]` analogue): a moving-block bootstrap over events in release-date order, block length by Politis–White on the ordered residuals (minimum 3), 2,000 iterations, seed 407. `ci_high` = the one-sided `1 − α` upper bound of `b`, `α = 1 − Φ(z_c)`.
- `z_c = max(1.645, E[max of N_ruled iid N(0,1)])`, with `N_ruled` the director's trial count at freeze. At N_eff ≈ 372, `z_c` ≈ 2.96.

## 6. Verdicts (numbers fixed now)

**VALIDATED** requires all of:

| # | Condition |
|---|---|
| V1 | `t_HC3 ≤ −z_c` |
| V2 | `ci_high < 0` |
| V3 | Materiality: the pooled partial correlation of `r_e` with `s_e` (after family effects) ≤ −0.20 |
| V4 | The CPI family's own slope is negative (point estimate) — the family the mechanism and DKW both put first |
| V5 | Census clean (§7): ≥ 85 eligible release days (80 % of the design note's planning count of 107 to 2026-05-22; set from quote availability, not from any outcome); ≤ 10 % of events ineligible for a data fault (`no_settled_value`, `asset_missing`), as opposed to a market-structure reason (`k_lt_3`, `median_not_bracketed`, `buckets_incoherent`); zero halts |

**NOT VALIDATED** if any of V1–V4 fails: the "explain the book's move" use is retired; nothing else changes.

**VOID** if V5 fails or any §2 integrity check fails.

There is no "inconclusive, extend the window": a re-test is a new pre-registration.

## 7. Census (written by the run, `[NN-CENSUS]` analogue)

Per family: events listed by Kalshi; settled; with any candle at the snapshot; eligible; ineligible by reason (`k_lt_3`, `median_not_bracketed`, `buckets_incoherent`, `no_settled_value`, `asset_missing`, `duplicate_event`); strikes dropped as `stale_quote`; the distribution of carried-candle ages; the median spread at the snapshot; the first and last eligible release dates. Also: the AGG convention check result; the two md5s of the determinism check.

## 8. Sensitivities (reported, never gating)

- Instrument: **TLT** and **SPY** in place of AGG (SPY's sign is regime-dependent; reported, not interpreted as a test).
- CPI family surprise from **core** CPI m/m instead of headline.
- **DKW's construction** instead of ours: last-traded prices, with monotonicity enforced outward from the mode. DKW found that mids misbehave on wide-spread tail strikes; our ≤ 10c spread rule drops those strikes instead.
- Implied **mean** instead of median: the survival sum `b_1 − h_f/2 + h_f · Σ S_k` on the quoted ladder, with the tails truncated at the outer quoted strikes.
- Snapshot at the **prior trading day's 16:00 ET** instead of just before the release. This measures how much of the surprise was already knowable at the prior close; it is NOT a trading test and can never become one under this registration.
- Excluding FOMC; CPI family alone; 2022 alone vs 2023–2026.
- Family-specific slopes with their own HC3 t.

## 9. Not allowed

- Changing any family, sign, snapshot, quote rule, eligibility rule, the instrument or the window after freeze.
- Promoting any sensitivity to the headline.
- **Using this registration, its data or its result to choose, tune or "sanity-check" any trading rule.** A tradeable per-event design needs its own registration and trial; the design note's arithmetic (§5) says none currently clears the bar.

## 10. Planning power (design note §4)

- **Planning count** (quotes only; design note §4): 107 eligible release days from 2022-01 to 2026-05-22 (CPI 45, payrolls 44, GDP 14, core PCE 4, FOMC 0), or 117 to 2026-10-31 if AGG is refreshed.
- **Minimum detectable |ρ|** at 80 % power: 0.36 / 0.34 at `z_c` 2.96; 0.24 / 0.23 at 1.645.
- **Pass probability:**
  - at |ρ| 0.30: 58 % / 63 % (z 2.96);
  - at |ρ| 0.40: 91 % / 94 %;
  - weighted over the prior (0.2: 15 %, 0.3: 30 %, 0.4: 35 %, 0.5: 20 %): ≈ 72 % / 75 % at z 2.96 and ≈ 93 % / 94 % at z 1.645.
- **Why the N is not larger:** FOMC ladders are one-sided before the meeting, and core-PCE ladders are thin. Neither can be fixed by rule: they are how the markets trade.

## 11. Freeze checklist (the director's)

1. Rule the **trial count** (hence `z_c`). This is a calibration check with no trading consequence; whether it belongs in the strategy family's N is the director's ruling, not this file's.
2. Confirm the AGG total-return source and its convention check, and fix END (§2.3).
3. Approve the evaluation script after independent review; it must reproduce the census counts in the design note before reading any return.
4. Confirm §3–§6 unchanged; stamp the frozen file's SHA-256 in the ledger row.
