---
task_id: T-413
title: DRAFT pre-registration — E-1, earnings straddles conditioned on the option-implied move relative to the firm's own earnings history
date: 2026-11-20
worker: edge-analyst (worktree agent-a44a03b091ff6efa5)
status: CLOSED UNRUN 2026-11-24 (director's ruling), 0 trials. Never frozen; nothing measured. Superseded passages are marked and kept; corrections in §16–§18.
design_origin: docs/Sources/ideas_census_desk_t410_2026-11-20.md (§5 E-1, §7.1)
code: NOT ON MAIN. scripts/t413_e1_earnings_options.py and tests/test_t413_e1_earnings_options.py exist only on branch worktree-agent-a44a03b091ff6efa5 at a9c12c1
---

# T-413 DRAFT: do options misprice a firm's earnings move relative to its own history?

> **CLOSED UNRUN 2026-11-24, 0 trials (director's ruling after an independent execution review of `a9c12c1`: NOT READY, 4 blockers and 6 REQUIRED items).**
> - **Why.**
>   - The reviewer's updated P(H1b) is ≈ 2–4 % (σ 1.0) / 1–2.5 % (σ 1.24), and the design detects only ≈ 24–30 pp per event.
>   - A FAIL would barely move belief in a plausible 5–15 pp effect. A PASS would more likely be a data fault.
>   - The fetch and refresh code was never written, and the fail-closed path has holes (§16.4, §18).
> - **This closure refutes nothing.** Earnings options were not tested.
> - **Reopens if** (a) the forward options archive (T-416) holds ≥ ~2 years of real quotes, or a quote/IV history becomes available (Cboe DataShop, OptionMetrics); or (b) a conditioner that raises the per-event effect appears. The reviewer's mean-of-8 versus median-of-8 option is recorded, not adopted.
> - **How to read this file.** The original text below is kept as written. A passage marked **[SUPERSEDED]** is not current truth; §16–§18 hold the corrections. Where the text speaks of running, freezing or recommending, read it as history.

> **DRAFT.** Every number below is proposed. It binds only once the director freezes this file: a commit with a freeze stamp, the ruled trial count, and the md5 pins written into the script. Until then, no straddle return may be computed under this hypothesis's name. The census (§15) used counts, timestamps and the conditioning variable only. The smoke (§10) was blind.

## 0. Read this first: the free data supports an honest test, but a weak one

> **[SUPERSEDED 2026-11-24]** by the notice above and §16. The probabilities are the author's draft values, the "47 %" is a sub-sample figure (§16.4), and the recommendation to run is withdrawn.

- **Events.** 4,304 S&P 500 earnings events pass the calendar rules to the 8-K panel's end (2026-06-10). Refreshing to 2026-11-06 projects ≈ 5,130.
  - In a 150-event sample, only **41 %** survive the market-data rules.
  - The binding one is structural: **47 % of S&P 500 events have no listed expiry within 7 days.** Those names list monthlies only, e.g. AMT, MNST, AZO and AXON in Jan–Apr 2024, against CRM's weeklies.
  - Thin entry prints remove another 9 %.
  - Projection: ≈ 2,100 included events, of which ≈ **1,230 fall in the tercile arms** of sortable weeks.
- **Power.** The bottom-minus-top spread has SE ≈ **6.4–7.9 pp** per event and an 80 %-power minimum detectable effect (MDE80) of **24–30 pp**.
  - P(H1b passes) ≈ **4.5–8 %** on the T-410 priors. T-410's ≈ 18 % assumed 2,500 effective events and σ_event 0.8, giving an SE of 3.9 pp. The census measures ≈ 1,460 effective events (1.5 × 1,230 arm events ÷ design effect 1.26, about 60 % of T-410's figure) and a planning σ of 1.0–1.24.
  - P(the deployable long leg passes net of the gating cost) < **1 %**.
- **What a null can close.** It cannot close "earnings options in every form", as the census sketch says. It refutes only the **large-effect form** (a tercile spread of ≳ 25 pp per event). §9 scopes the falsifier to what this power supports.
- **Recommendation: freeze with the §14 defaults and run.** The cost is one trial at N_eff ≈ 372, $0, and ≈ 2 h of API pulls. The owner asked to test and exhaust ideas, and an H1b pass is the only thing that would justify buying quote data. Close unrun instead if the director prefers not to spend a trial on a ≈ 6 % test.

## 1. Hypothesis (from the literature, before any data)

**H1b (primary).** Take S&P 500 earnings events that have a listed expiry within 7 calendar days of the announcement. Sort them within each reaction week on

  q = ((C + P) / S0) / m8.

The straddle return (payoff = intrinsic value at expiry) is **higher in the lowest tercile of q than in the highest**.

**H0.** The bottom-minus-top mean is ≤ 0.

**Theory:**
- Gao–Xing–Zhang (JFQA 2018): pre-announcement ATM straddles earn positive returns, more so in small, volatile, costly-to-trade names. "Investors underestimate the magnitude of uncertainty around earnings."
- Goyal–Saretto (JFE 2009): straddles sorted on historical-minus-implied volatility earn large spreads.
- Dubinsky–Johannes (RFS 2018 version): option prices embed an earnings-jump component.

H1b asks whether that component is mispriced relative to the firm's own jump history.

**Against the effect (recorded so the result cannot be spun):**
- Coval–Shumway (2001): options are generally dear. Index straddles lose ≈ 3 %/week.
- In the census sample the median q is **1.26**. The implied move (median 5.3 %) is above the historical median move (4.7 %). A normal |move| has mean ≈ 1.18 × median, so straddles look slightly rich on average.
- Duarte–Jones–Khorram–Mo–Wang (RFS 2026; the record's reading, not mine): option Sharpes are inflated by ex-post quote filters. Here every filter is ex ante (§3).
- The sample's 2024–26 period follows the papers by 9–17 years, so decay is the default expectation.

**Per-event ratio (`feedback_per_event_effect_to_noise`).**
- A 10 pp spread against σ_event ≈ 1.0–1.24 is a ratio of ≈ 0.09.
- 80 % power at the bar needs ≈ 8,800 arm events (≈ 15,000 included events). That is about 7× what the free data holds.
- So only a large effect is detectable.

**Persistent-conditioner check (outcome-free).** In 2016–2023 stock data, the firm lag-1 autocorrelation of the proxy straddle return is **0.08**. The two-way (week × firm) SE is a necessary condition (§7), so persistent firm-level traits cannot masquerade as per-event evidence. sd(log q) in the census sample is **0.40**, so the conditioning signal has not collapsed (`feedback_signal_variance_collapse`). **[SUPERSEDED: unsupported, §16.2]**

## 2. Hard pre-commitments

1. **No outcome before the freeze.** The census (§15) used counts, timestamps, print counts and q only. The smoke (§10) computed returns for one reaction week, hashed them and never printed them. The smoke week is therefore included in the test.
2. **One gating configuration** (§3–§7). The window, thresholds and rules come from the T-410 sketch or from outcome-free census facts. The one census-driven question, a 60-minute entry window, was checked and **rejected**: it adds 2 of 150 events. The sketch's 15:30–16:00 stands.
3. **No tuning after any result.** The §8 descriptives are named now. They are reported beside the headline and never replace it.
4. **Determinism ×2.** `run` computes the analysis twice from the pinned archive and halts if the results md5 differ. The smoke has already shown this on real data (§10).
5. **Paper only; never real money.** No result here moves money, enters `live_trader/` or `paper_trader/`, or becomes an Engine A edge. The owner will not fund the machine until it confidently outperforms. §9 says what a pass licenses.

## 3. Universe and event rules (all outcome-free, applied in this order)

| # | Rule | Source / reason |
|---|---|---|
| U1 | S&P 500 point-in-time member on the reaction date (`data/universe/sp500_membership_pit.parquet`, md5 `7c142ab6…`). After the file's last change (2026-06-02), membership is evaluated as of that date (stated staleness). One share class per CIK, as in the 8-K panel | Liquid names. T-410's "S&P 500 / liquid names with weeklies" |
| T1 | 8-K (never 8-K/A) carrying item 2.02 | The release |
| T2 | **Scheduled**, judged on past information only: the CIK has an item 2.02 within ±7 days of (date − 364), and no item 2.02 in the prior 45 days | The trade needs a known date. 364 days keeps the weekday. 89.7 % of 2019–23 filings match last year within ±7 days. Unscheduled releases would bias toward a false pass (§13) |
| T3 | Session by acceptance time (ET): BMO < 09:30, AMC ≥ 16:00, OFFDAY (weekend or holiday) treated as BMO. **INTRA (09:30–16:00) excluded.** Entry day = the last trading day whose 16:00 close precedes acceptance; reaction day = the next one | 2023+ acceptance times are true timestamps (UTC verified on AAPL: raw `21:30:30Z` = 16:30 ET) |
| T4 | Excluded if the ticker's first Benzinga EPS-flash headline in [acceptance − 36 h, acceptance] is **at or before the entry close** | The release preceded our entry. 16 of 3,776 audited events (0.4 %) |
| T5 | Entry ≥ 2024-01-18, the first date Alpaca serves option data (verified: a Mar-2024 contract has bars from 2024-01-18 only). Announcement ≤ 2026-11-06, so every expiry is ≤ 2026-11-13 and settled | Data span |
| T6 | Eight prior scheduled events, the oldest entry within 1,100 days, each with a horizon-matched move (§4) | m8 needs them. 97.5 % of candidates have them |
| T7 | Expiry = the nearest **standard** expiry (root = the class root, size 100) in [reaction day, announcement + 7 calendar days] | T-410 sketch. Adjusted contracts are never eligible |
| T8 | Strike = the listed strike nearest the underlying's entry VWAP that lists both a call and a put. Ties go to the lower strike | ATM |
| T9 | Each leg has **≥ 5 single-leg prints** in [15:30, 16:00) ET on the entry day | T-410 sketch; an ex-ante liquidity filter |
| T10 | Excluded if the raw/adjusted close ratio moves > 5 % between the entry and expiry closes | Splits are announced in advance; adjusted strikes |

**Missing inputs.** A missing load-bearing input (spot, calendar position, a daily bar) on > 1 % of candidates **HALTS**. A missing raw close at expiry for any included event **HALTS**: it is never dropped, because a delisting inside the window is outcome-related. **[SUPERSEDED: false of the code as written, §18 A2]**

## 4. The conditioning variable, exactly

- **Spot.** S0 = the VWAP of the underlying's SIP 1-minute bars in [15:30, 16:00) ET on the entry day. Raw prices.
- **Entry prices.** C and P = each leg's VWAP over the single-leg prints in the same window.
  - Admitted OPRA conditions: I AUTO, S ISO, a/b single-leg auction, c/d single-leg cross, e single-leg floor. The codes come from Alpaca's `/v1beta1/options/meta/conditions/trade`.
  - Excluded: cancels, late and out-of-sequence prints (A–H, J), every multi-leg and stock-tied code (f–s), proprietary codes (t, u) and extended hours (v).
  - Multi-leg prints are **47 %** of the tape in the census archive. Their leg prices are package-relative, not the leg's own price.
- **History.** k = trading days from the entry close to the expiry close (1–5 in the census sample) **[SUPERSEDED: k reached 6, §16.4]**.
  - m8 = the median, over the firm's eight prior scheduled events j, of |ln(A[e_j + k] / A[e_j])|.
  - A is Alpaca's split- and dividend-adjusted close; e_j is that event's own entry day.
  - So m8 measures the **same horizon** relative to the announcement. That removes the confound from residual diffusion days: an event with a longer residual life prices more ordinary variance.
- **q** = ((C + P) / S0) / m8.

## 5. Entry and payoff

- **Entry.** Buy one ATM call and one ATM put at their window VWAPs. One unit per event, equally weighted.
- **Payoff.** |S_T − K|, with S_T the underlying's raw SIP close on the expiry date.
  - Holding to expiry is a feasible strategy for a long holder, and intrinsic value is the payoff of holding.
  - No option exit price is needed.
- **Gross return.** r = |S_T − K| / (C + P) − 1.

## 6. Cost model: what it can and cannot represent

> **[SUPERSEDED IN PART 2026-11-24]** See §16.5 on level H and on why H1c is not deployable.

Alpaca serves **no historical option quotes** (`/v1beta1/options/quotes` → 404; verified in T-410). A net-of-spread claim therefore rests on an assumption. The design keeps it out of the primary test: H1b is gross and long–short.

The deployable claim (H1c, §7) is gated on a deliberately conservative schedule:

| Level | Entry half-spread per leg | Exit (ITM leg) | Fees | Role |
|---|---|---|---|---|
| B | max(½ tick, 2 % of leg price) | max(½ tick, 1 % of intrinsic) | $0.06/contract/side | descriptive only |
| **H** | max(1 tick, **5 %** of leg price, the leg's print half-range†) | max(1 tick, 2.5 % of intrinsic) | $0.06/contract/side | **gates H1c** |

Tick = $0.01 below $3 and $0.05 at or above $3 (the penny-interval assumption). † When a leg has fewer than 3 two-sided minutes, H charges twice the schedule.

The print half-range is the median, over minutes with ≥ 2 single-leg prints, of (max − min) / 2. In the census sample it is a **median 0.59 %** of the leg price (90th percentile 1.27 %), available on 76 % of legs. B and H charge 3–8× that on purpose.

- **It can represent:**
  - a one-lot taker paying a half-spread over the window VWAP on both legs at entry;
  - a half-spread on the ITM leg's sale at expiry;
  - per-contract fees;
  - for H, an event-specific floor wherever both sides printed within a minute.
- **It cannot represent:**
  - the NBBO at the moment of the order;
  - quote widening into earnings;
  - whether the window VWAP sits at the mid (prints mix buys, sells and auction-improved fills);
  - broker price improvement;
  - the exit mechanics of an IRA (selling vs exercising; a long ITM put without stock), recalled and not verified [R].

  The print half-range **understates** the quoted spread when prints cluster on one side or at improved prices. That is why it is only a floor inside H.
- **What would fix it.** One month of Alpaca Algo Trader Plus ($99, OPRA NBBO) recorded across an earnings season would calibrate the schedule against real quotes. It is recommended **only if H1b passes**. Paper fills on the free feed are invented (`feedback_paper_probe_taker_only`) and cannot do this.

## 7. Test statistic, clustering and pass rules

**The arms.** Take each reaction week (Monday of the reaction day) with **n_w ≥ 6** included events. Bottom = the ⌊n_w/3⌋ lowest q; top = the ⌊n_w/3⌋ highest. Ties break by ticker. The arms are equal in size.

**The regression.** Regress r on D (+½ bottom, −½ top) with week fixed effects. The estimate β equals Σ_w m_w s_w / Σ_w m_w, where s_w is the week's bottom-minus-top mean (`tests/…::test_spread_equals_weighted_week_mean_and_cluster_se`).

**Standard errors** (CGM, each with the G/(G−1) factor):
- week-clustered;
- firm-clustered;
- two-way, V = max(V_week + V_firm − V_het, V_week, V_firm), the conservative floor.

**Bootstrap.** Weeks resampled with replacement, 10,000 draws, seed 413, giving a percentile 95 % CI.

**H1b passes only if ALL hold:**
1. t_week ≥ **2.96** (`[NN-MBL]` bar at N_eff ≈ 372);
2. t_two-way ≥ 2.96;
3. the week-bootstrap ci_low(95 %) > 0;
4. **sensitivity:** t_week ≥ 2.96 after dropping events followed by another item 2.02 within 45 days. That flag uses later filings, so it is never an inclusion rule. 2.8 % of candidates carry it, mostly habitual pre-releases such as TSLA deliveries or EQT operational updates;
5. **split half:** the point estimate is > 0 in both halves of the sample, split at the median reaction week.

A NaN t (degenerate SE) never passes (`[NN-FP-GUARDS]`).

**H1c** is evaluated **only if H1b passes**: the bottom arm's mean return net of level H > 0, with the same three statistical conditions (t_week, t_two-way, bootstrap ci_low).

**Descriptives** (decide nothing): **[SUPERSEDED: mostly unimplemented, §17 finding 9]**
- H1a, the mean gross return over all included events;
- H1c at level B;
- by-year and by-session (BMO/AMC) spreads;
- corr(q, |S0 − K|/S0), the strike-offset check;
- the share of |β| contributed by the top 1 % of events.

**Wrong sign.** t_week ≤ −2.96 is recorded and is **not a pass**. A theory-specified reverse-direction test would need its own prereg on **new data**, never this sample (that would be data-led).

No Sharpe ratio is computed or quoted. The headline is a per-event mean spread with its bootstrap CI (`[NN-SHARPE-CI]`).

## 8. Power and pass probability (arithmetic)

> **[SUPERSEDED IN PART 2026-11-24]** See §16.1 and §16.3. The power gate quoted below was lowered after the census; see §18 A1.

Planning values (outcome-free; §15):

| Quantity | Value | Source |
|---|---|---|
| Candidates to 2026-11-06 | ≈ 5,130 | 4,304 on disk + ≈ 450 (Jul–Aug 2026) + ≈ 380 (Oct 13–Nov 6), projected from ≈ 430/quarter [R] |
| Inclusion | 0.41 (86 of 210 sampled) | census samples (150 + 60) |
| Arm events after week thinning | **≈ 1,230** (1,100–1,360 for inclusion 0.37–0.45) | Monte Carlo thinning of the observed week sizes; weeks falling below 6 drop out |
| Sortable weeks | ≈ 68 | same |
| σ_event | 1.0 central; 1.24 conservative | 2016–23 proxy, \|R_k\| / (1.18·m8) − 1, sd 1.24 (0.96–1.45 by year). The real straddle forecasts better than m8, so the true σ is likely lower |
| Design effect, spread | 1.26 (two-way = week) | pre-2024 within-week sort on a history-only pseudo-q |
| Design effect, level | 1.78 | same |

**Spread.** SE = σ·√(4·DE / n_arm) gives **6.4 pp (σ 1.0)** and **7.9 pp (σ 1.24)**. MDE80 = 3.8·SE = **24–30 pp**.

| Scenario spread | 20 pp | 10 pp | 5 pp | 0 |
|---|---|---|---|---|
| P(t ≥ 2.96 \| s), σ 1.0 | 0.57 | 0.08 | 0.015 | 0.002 |
| P(t ≥ 2.96 \| s), σ 1.24 | 0.33 | 0.045 | 0.010 | 0.002 |
| Prior (T-410) | 0.10 | 0.20 | 0.30 | 0.40 |

**P(H1b) ≈ 7.8 % (σ 1.0) / 4.5 % (σ 1.24)**, before conditions 4–5, which cost little when the effect is real. **[SUPERSEDED: §16.3]**

**H1c.** The bottom arm has n ≈ 615. SE = σ·√(1.78/615) = 5.4–6.7 pp. Net-of-H priors of +10/+5/0/−5 pp at 0.05/0.15/0.40/0.40 give P ≈ 0.6–1.1 %. Level H costs ≈ 6–7 pp against gross, so even these priors are generous. **P(H1b ∧ H1c) < 1 %.**

**Power gate** (code: `power_gate`, run on the inclusion stage before any payoff is read). The test proceeds only if arm events ≥ **1,000** and sortable weeks ≥ **40**. Otherwise it closes unrun for power and consumes 0 trials. At 1,000 arm events and σ 1.24 the MDE80 is ≈ 33 pp.

**What would make it decisive.**
- A quote-based history: Cboe DataShop end-of-day option files with 15:45 bid/ask (2004+, priced per year) [R], OptionMetrics via WRDS (1996+), or ORATS.
- About 20 years would give ≈ 35,000 S&P events, an MDE of ≈ 6–7 pp, and real quotes for H1c.
- **That is the version to buy data for, and only after a free-data H1b pass.**

## 9. Falsifier, and what each outcome licenses

> **[SUPERSEDED 2026-11-24]** This section treats a power-gate closure as a FAIL and lets a FAIL close G1, G2, G4 and F-7. Both are wrong. See §16.1.

**FAIL** (any condition in §7 unmet, or the power gate closes it):
- Refutes the **large-effect form**: a bottom-minus-top tercile spread of ≳ 25 pp per event in S&P 500 ≤ 7-day earnings straddles, 2024-01 → 2026-11.
- **Closes the earnings-options family on free data.** That covers G1 long straddles, G2 vol-crush, G4 skew/term and F-7 forward books, in both wrappers. No re-test on Alpaca prints with another conditioner, universe slice, window, expiry rule or entry time (the anti-salvage rule; `feedback_no_stone_unturned_salvage`).
- It does **not** refute a moderate (5–15 pp) effect. That form stays UNTESTED until a quote-based history exists, under a new prereg.
- This deliberately narrows the T-410 sketch's "closes … in every form". At this power that claim is not supportable.

**H1b PASS, H1c FAIL.** The pricing signal is real at the 25 pp scale. That licenses only:
- (a) recommending one month of OPRA quotes to measure entry costs;
- (b) a forward **paper** record of the H1b rule on the next seasons (taker rule; gross spread; marks labelled indicative);
- (c) proposing the quote-based long-history test.

**H1b + H1c PASS.** The same as above, and the E-3 real-fill cost record becomes **proposable to the owner**. Real money remains the owner's decision and is out of scope: the owner will not fund the machine until it confidently outperforms.

**Never licensed:** live integration, an Engine A edge, a sizing change, or any real-money order (`[NN-AI-GATE]` spirit; `[NN-NO-MANUAL-EDGES]`).

## 10. Controls and smoke (already run; code path proven, no hypothesis measured)

> **[SUPERSEDED IN PART 2026-11-24]** "Code path proven" is wrong. The controls ran and gave the figures below, but they pass with planted faults in the payoff, the history and the entry price. See §17 finding 6.

**Synthetic controls.** These are `run_controls()`, run at the start of every `run` and `smoke`. Each builds a synthetic market (360 firms, Alpaca-schema contracts, trades and bars) with a **known expected return per event** and runs the full pipeline: events → schedule → session → history → contracts → prints → q → payoff → statistic. The estimate is checked against the oracle spread (the same arms applied to the known expected returns).

| Scenario | Estimate | Oracle | t_week | t_two-way | Required | Result |
|---|---|---|---|---|---|---|
| positive (options priced at the truth × e^ε, ε ~ N(0, 0.30)) | +0.377 | +0.398 | +12.6 | +11.3 | H1b passes; \|est − oracle\| ≤ 4 SE | ok |
| null (priced at the truth) | +0.017 | 0.000 | +0.49 | +0.49 | no pass; \|t\| < 2.96 | ok |
| negative (price over-weights the firm's history) | −0.744 | −0.744 | −16.2 | −16.1 | t ≤ −2.96; no pass | ok |

**Every scenario also checks** that the injected split event, the thin-print legs, the unscheduled filings and the intraday filings were all excluded, and that no load-bearing input went missing.

**Reversion proofs** (tests). Each leg carries junk prints at 3× the price: multi-leg, cancelled, one before the window and one at 16:00:01.
- Admitting the multi-leg and cancel codes makes the controls **halt**.
- Widening the window by one minute also makes them **halt**.

**Smoke** (`smoke`, reaction week 2024-02-26, BLIND):
- 29 candidates → 8 included. Exclusions: 17 with no expiry ≤ 7 days, 2 thin, 2 lacking history. That leaves 2 bottom and 2 top arm events.
- The arms are disjoint and differ (by md5 of their sorted returns, never printed).
- Payoffs are finite and ≥ 0, and the cost ordering H ≤ B ≤ gross holds.
- Two offline re-runs give results md5 `2aad5755…` both times. A second end-to-end invocation read only the archive (0 API calls) and reproduced the same md5 and manifest `ffd0b4dc…`.
- The 17 no-expiry names list only monthlies; for AMT, MNST, AZO and AXON this was witnessed over Jan–Apr 2024. So the exclusion is a listing fact, not a data gap. **[SUPERSEDED: not established, §16.4 and §18 A3]**

## 11. Inputs, pins and archive

- **Archive (proposed).** `data/research/t413/`, written **only** by the post-freeze `fetch` step and never by tests. It holds:
  - `stock_daily_{raw,all}/`, `stock_1min_1530-1600/`, `contracts/`, `option_trades_1530-1600/` (gzip JSON, mtime 0);
  - `edgar/` (raw submissions JSON and `panel_8k_items_t413.parquet`);
  - `MANIFEST.json` (file → md5).

  Estimated ≈ 120–150 MB and ≈ 22,000 Alpaca calls (≈ 2 h at the free plan's 200/min).
- **Durable copy.** Following T-398, copy the archive to `/Users/jacksonmurphy/Dev/_research_snapshots/t413_e1_earnings_options_<date>/`.
- **Pins.** At freeze the script sets `PINNED_MANIFEST_MD5`, `PINNED_PANEL_MD5` (the refreshed panel) and `PINNED_MEMBERSHIP_MD5` (`7c142ab698da86ef601426d4f30de65d` today). `run` refuses while any is None or mismatched (tested). **[SUPERSEDED IN PART: §17 findings 4 and 10]**
- **8-K refresh, needed for Jul–Nov 2026 and for the 34 PIT names missing from the panel.** The missing names: ANSS, BF-B, BNY, BRK-B, CDAY, CMA, CTLT, CTRA, DAY, DFS, FDXF, FI, FIS, FLT, FOXA, GOOGL, HES, HOLX, IPG, IR, JNPR, K, MMC, MRO, NWSA, OXY, PARA, PCG, PEAK, PPG, PXD, VEEV, WBA, WRK.
  - Fetch submissions JSON through the project's SEC helper only: `scripts.archive_altdata_t136._get`, which routes the contact User-Agent to sec.gov hosts only.
  - Parse with `scripts.fetch_8k_edgar_t137._rows_from_filing_arrays`.
  - The dead names' CIKs come from the Form 4 zips (`ISSUERTRADINGSYMBOL`).
  - **Not written in Phase 1.** `fetch` is disabled.
  - Dual-class names (GOOG/GOOGL, FOX/FOXA, NWS/NWSA) keep one class per CIK.
- **News refresh.** T4 needs `data/intel/news_panel/news_2026{10,11}.parquet`, via `scripts/build_news_panel_t289.py` (a director step). `run` halts on a missing month (tested in `load_flash_news`). **[SUPERSEDED IN PART: a truncated month is accepted, §17 finding 2]**
- **Scratch only (this phase).** The census and smoke archives live under the session scratchpad. They are not durable and are not inputs to the run.

## 12. Trial count (proposed; the director rules)

> **[SUPERSEDED 2026-11-24]** Ruled: **0 trials**.

- **+1** at the run (H1b with its necessary conditions 1–5).
- **+1 more only if H1b passes** and H1c is evaluated at level H.
- **0** for:
  - the census probes, which covered 210 sampled events and only the conditioning variable;
  - the outcome-free pre-2024 planning proxy (its spread estimate is never reported);
  - the blind smoke;
  - the descriptives.
- `config/honest_n_trials.json`: 372 → 373 (or 374). The bar is unchanged at this precision.

## 13. Known biases and their direction (stated before the result)

| Bias | Size | Direction |
|---|---|---|
| Unscheduled releases that pass T2. The options do not price them and their q is low, so they land in the bottom arm | ≤ 1–2 % of events (2.8 % carry the next-2.02 flag) | **Toward a false pass.** Condition 4 guards it |
| Release before entry (T4 misses months without news) | 0.4 % before T4 | Toward null (a post-news straddle is fair-priced) |
| 34 PIT names missing until the refresh, mostly later-acquired **[SUPERSEDED: never classified, §18 A4]** | ≈ 3 % of events | Unknown; the refresh removes it |
| PIT membership stale after 2026-06-02 | additions after June are absent | Small; unknown |
| VWAP vs mid. Gross returns are relative to the window VWAP, not the ask | equal across arms unless spreads differ by q | Second-order for H1b; H1c charges for it |
| Heavy right tail (proxy q99 = +480 %) | — | t is approximately conservative for an upper-tail test on right-skewed arms; the bootstrap CI is required |

## 14. Decisions for the director (one-word defaults)

> **[SUPERSEDED 2026-11-24]** Ruled: close unrun. No default below was adopted.

| # | Decision | Default | Alternative |
|---|---|---|---|
| D1 | Universe | **U1** (S&P 500 PIT) | U2: add non-S&P names with weeklies. About 2× events, P(pass) ≈ 8–12 %. It needs an EDGAR item-2.02 universe build over all filers and a dead-ticker mapping (the T-265 survivorship lesson) |
| D2 | Run or close | **RUN** (1 trial, $0, ≈ 2 h of pulls) | CLOSE-UNRUN for power, 0 trials |
| D3 | Falsifier scope | **SCOPED** (§9) | The T-410 sketch's "every form" (not supportable at this power) |
| D4 | Power gate | **1,000 arm events / 40 weeks** | — |
| D5 | Refresh 8-K + news to 2026-11 | **YES** | NO: the window ends 2026-06-10 and the count falls ≈ 16 % |

## 15. Census record (outcome-free; reproducible)

**Disk** (`census-disk`; 8-K panel md5 `5b7d58964bd758ee00d142924d7ef5f3`, membership md5 `7c142ab6…`):
- **Panel.** 183,278 8-Ks (1994-01 → 2026-06-10); 49,656 with item 2.02 across 617 tickers.
- **Candidates.** 4,304, with 389/428/427/429/417/439/452/453/435/435 by quarter from 2024Q1 to 2026Q2. 2024Q1 starts 01-18.
  - Excluded before market data: 1,078 non-members, 805 unscheduled or clustered, 136 intraday.
  - Sessions: BMO 2,397, AMC 1,906, OFFDAY 1.
- **Weeks.** 124 reaction weeks; 98 with ≥ 6 candidates. The top 10 weeks hold 33 % of events.
- **Timing audit against Benzinga EPS flashes** (±36 h):
  - 3,776 events matched;
  - acceptance − first flash: median +1.9 min, 5–95 % [−12, +71] min;
  - 16 flashes at or before the entry close;
  - 528 events without a flash (329 with a guidance-type headline only).
- **Correction to T-410 §4.2.** The 117 `data/earnings/*_calendar.parquet` files have an **empty** `hour` field (2,698 of 2,698 rows). They cannot check sessions. The news flash replaces them.
- **Pre-2024 planning** (11,088 events, 2016–23, price cache, census-only):
  - σ_proxy 1.24 (0.96–1.45 by year); q01/q99 −0.98 / +4.80;
  - design effect 1.26 for the spread (two-way equal to week) and 1.78 for the level;
  - firm lag-1 autocorrelation 0.08.

**Alpaca sample** (`census-sample`; 150 events, seed 4131; 60 events, seed 4130; no payoffs):
- **Inclusion.** 61/150 (40.7 %): 70 had no expiry ≤ 7 days, 14 were thin, 5 lacked history. In the 60-event sample, 25/60 (41.7 %).
- **60-minute window.** 63/150. Rejected (§2).
- **Prints per leg.** Percentiles 10/25/50/75/90 = 7/12/28/64/196.
- **Horizon k.** k = 1: 10, k = 2: 24, k = 3: 13, k = 4: 12, k = 5: 2.
- **Conditioning variable.**
  - q percentiles 10/25/50/75/90 = 0.81/0.96/1.26/1.60/2.11; sd(log q) 0.40.
  - Implied move: median 5.3 %. m8: median 4.7 %.
  - Premium per share: 10/50/90 = $1.55/$6.30/$18.3.
- **Condition mix** (6,932 prints in the archive) **[60-event archive only, §18 A5]**:
  - single-leg I 33 %, a 15 %, S 4 %;
  - multi-leg f 27 %, g 17 %, j 3 %;
  - stock-tied < 1 %.
- **Listings.** Witnessed that AMT, MNST, AZO and AXON list monthlies only in Jan–Apr 2024, against CRM's weekly chain.

**Reproduce:** the commands are in the execution manual's T-413 section on branch `worktree-agent-a44a03b091ff6efa5` (`a9c12c1`); that section is not on main.

---

## 16. Corrections (2026-11-24)

**Provenance.** The reviewer's findings and numbers were relayed by the director. The author has not seen the review itself and, as ruled, re-ran nothing. Figures are attributed, not re-verified, except where a line says what was checked: the author's saved census output, or the code at `a9c12c1` by reading.

### 16.1 The falsifier (finding 3; corrects §8 and §9)
- A **power-gate closure is not a FAIL and refutes nothing.**
- A FAIL refutes only spreads **above the bootstrap ci_high**. It does not refute "≳ 25 pp" by default.
- The reviewer's probabilities of a FAIL whose ci_high is ≥ 25 pp, i.e. a FAIL that leaves even a 25 pp effect unrefuted:

| True spread | SE 6.4 pp | SE 7.9 pp |
|---|---|---|
| 20 pp | 0.32 | 0.57 |
| 10 pp | 0.27 | 0.48 |

- P(FAIL | true 10 pp) is 92–95 %. This agrees with §8's own table (1 − 0.08 and 1 − 0.045).
- A FAIL would **not** close G1 (small-cap), G2 (short vol) or G4 (skew/term). None of them is what this design tests.

### 16.2 The conditioning signal (finding 7; corrects §1's persistence paragraph and any reliance on it in §4 and §7)
- "The conditioning signal has not collapsed" is **unsupported**. The measured sd(log q), 0.392, equals the sampling-noise floor of the denominator alone: the log of a median of 8 half-normals has sd 0.390, and 0.417 for t4.
- The 0.392 is on the 84 unique events. corr(log q, log m8) = −0.64 and corr(log q, log implied) = +0.10. Much of the sort is therefore a sort on noise in m8.
- The noise-corrected slope of log implied on log m8 is 1.11, which shows no footprint of options under-weighting the firm's history.

### 16.3 The power numbers (corrects §0 and §8)
- P(H1b) of 7.8 % / 4.5 % **reproduces as stated** from the T-410 priors.
- Updating on the observed var(log q), the reviewer gets **2–4 % (σ 1.0) / 1–2.5 % (σ 1.24)**.
- The reviewer's thinning gives 1,228 arms over 68 weeks (effective clusters ≈ 46), or 1,236 arms over 70 weeks when expiry-aware. That agrees with §8's ≈ 1,230 and ≈ 68.
- P(H1b) through all five conditions is 0.58 at a true 20 pp, 0.14 at 12 pp and 0.01 at 5.5 pp.
- **Not reconciled.** The first ruling said conditions 2–5 cost more than §8 states. The five-condition 0.58 at 20 pp is about equal to §8's value for condition 1 alone (0.57 at σ 1.0), so these figures do not themselves show an added cost.

### 16.4 Data caveats
- "47 % no expiry" is the 150-event sample. Pooled over both samples it is **44 % (92 of 210)**; checked against the author's saved census output (70 + 22).
- The 86 included events are **84 unique** events, because the two samples overlap.
- k reaches **6**; checked (one event in the 60-event sample).
- Contract-**listing gaps** exist, so a "no expiry" exclusion can be a data gap: FISV 2025-07-25 lists 0 contracts (FI lists 110); CPAY 2024-02-16 lists 0 (FLT lists 78); BRK.B 2025-05-09 lists 0, yet 14 of 14 constructed OCC symbols have bars.
- The news files for 2026-08 (ends 08-05) and 2026-09 (ends 09-02) are **truncated**, so rule T4 leaves about 122 candidates unprotected. The loader checked only that a month's file exists.
- The fetch and refresh code was **never written**.

### 16.5 Level H and H1c (findings 8 and 11; corrects §6, §7 and §9)
- **H1c is not deployable as specified.** The arms are terciles of the whole week, so Monday's arm needs Friday's q.
- H1c would need trailing thresholds. The same look-ahead biases H1b little: +0.1 to +0.5 pp in a fair-priced null with common vol shocks.
- Level H behaves as an effectively **flat cost** of about 8 pp (7.1, 9.3 or 11.3 with both, one or no print ranges), not as an event-specific charge. The print-range floor never binds at 5 %.

## 17. Review findings and their resolution

Independent execution review of `a9c12c1`: **4 blockers, 6 REQUIRED, 1 minor.** Findings are as relayed by the director on 2026-11-24. Line numbers are the review's, against `a9c12c1`. **Every finding's resolution is "not fixed: study closed".** The last column says what the corrections above already state, and what the author confirmed by reading the code (nothing was run).

| # | Level | Finding | Covered in this file? |
|---|---|---|---|
| 1 | BLOCKER | **A delisting inside the window is silently dropped, never a halt.** T10 in `stage_inclusion` (code 854–860; prereg 82) turns a missing expiry close into `missing_input:daily_bar`, tolerated to 1 % (~50 events). The halt in `stage_outcomes` is unreachable from `run`. With one firm's bars truncated at entry, the pipeline completed and the event vanished. The existing test calls `stage_outcomes` directly. NaN closes also pass T10 | Partly: §18 A2 states the drop, the unreachable halt and the test. NaN closes and the demonstration are new. Drop path confirmed by reading |
| 2 | BLOCKER | **The T4 news input is truncated and accepted.** `news_202608.parquet` ends 08-05 and `news_202609.parquet` ends 09-02. `load_flash_news` on 2026-07..09 did not halt (368/152/3 flash rows), leaving ~122 candidates without T4. The prereg refreshes only months 10–11, and the files are not md5-pinned | Partly: §16.4 states the truncation, the 122 and the existence-only check. The refresh scope and missing pins are new. Existence-only check confirmed by reading |
| 3 | BLOCKER | **The falsifier is wrong** (prereg 205–208). (a) A power-gate closure is listed as a FAIL. (b) A FAIL often leaves ci_high ≥ 25 pp (§16.1's table). (c) It closes G1/G2/G4, which are untested. P(FAIL \| true 10 pp) is 92–95 % | Yes: §16.1. Text confirmed by reading |
| 4 | BLOCKER (process) | **`fetch`, the 8-K refresh and the dead-name mapping are unwritten, and the freeze is circular:** the pins need the post-freeze archive. Without the refresh, arms ≈ 1,030 [998–1,062] against a gate of 1,000: a coin flip, given ±3.4 pp uncertainty in the inclusion rate | Partly: §16.4 states the unwritten code. The circular freeze and the coin flip are new. See also §18 A1: that gate of 1,000 replaced 2,400 |
| 5 | REQUIRED | **Data gaps are filed under legitimate exclusions** (code 819–853). 10 % of firms with no daily bars → `insufficient_history`, no halt. All adjusted bars missing → a power-gate halt that reads as "closed for power". Contracts empty or renamed for 50 % of firms → `no_expiry_within_7d`. Empty trades or negative prices → `thin_entry_prints`. Live cases: FISV, CPAY, BRK.B (§16.4). `drop_duplicates("accession")` (line 229) mishandles one CIK under two tickers | Partly: §16.4 and §18 A3 state the listing gaps. The rest is new. The labels and line 229 confirmed by reading |
| 6 | REQUIRED | **The three controls do not prove the code path.** Payoff read at entry+1, payoff from adjusted closes, m8 always at k = 1, and 10 % entry-price noise all pass. The 4-SE tolerance (~13–16 pp) is the size of the effect | No: new. §10's "code path proven" is marked superseded. From §10's own estimates and t, 4 SE is ≈ 12, 14 and 18 pp |
| 7 | REQUIRED | **"The conditioning signal has not collapsed" is unsupported** (prereg 56). sd(log q) 0.392 on 84 unique events against a floor of 0.390 (t4: 0.417); corr(log q, log m8) −0.64; corr(log q, log implied) +0.10; noise-corrected slope 1.11. Pre-freeze option, **not adopted**: mean of 8 (noise sd 0.28 / 0.35), P(all five) at a 15 % mispricing sd of 0.14 → 0.35 | Yes: §16.2. The mean-of-8 figures are new |
| 8 | REQUIRED | **H1c is not deployable:** Monday's arm needs Friday's q. It would need trailing thresholds. The bias on H1b is small (+0.1 to +0.5 pp) | Yes: §16.5 |
| 9 | REQUIRED | **The named descriptives are unimplemented** (prereg 159; `analyze`, code 914): by-year, by-session, corr(q, strike offset), top-1 % share of \|β\|. Level B exists only after an H1b pass | No: new. Confirmed by reading: only H1a is always computed |
| 10 | REQUIRED | **Pinning and data-guard holes.** `verify_manifest` passes with an extra un-manifested file that the run then reads (needs set equality). The outside-`data/` guard (1512) is bypassed when `data/research` is a symlink (agent worktrees): resolve both sides | No: new. Both confirmed by reading |
| 11 | MINOR | Pooled no-expiry is 92/210 = 44 %; thin prints 12 %; k reaches 6; 84 unique of 86 events. Level H drag ≈ 8 pp (7.1/9.3/11.3 with both, one or no print ranges); the print-range floor never binds at 5 %. `_get` does not retry connection resets. Determinism ×2 reuses one in-memory source. No parity or no-arbitrage guard on entry VWAPs (sample max \|error\| 11 %, sd 2 %; 0 of 11,839 prints > 50 % off the leg median: low practical risk). At least 22 pre-announcements beyond TSLA/ABBV (SMCI 2025-04-29, HOOD, GS, EQT); a past-only rule removes most | Partly: §16.4 states 44 %, 84 and k = 6; §16.5 states level H. The rest is new |

## 18. The author's own disclosures

A1, A3, A4 and A5 are the author's. **A2 is the review's finding 1**, named in the ruling first; the author only confirmed it in the code and adds that the promise was false when written.

- **A1. The power gate was lowered after the census.**
  - The code set `POWER_GATE_MIN_ARM_EVENTS = 2_400`, written before any census ran and committed in `fbfcbd7`. After the census had projected ≈ 1,230 arm events, `5eedef9` changed it to 1,000.
  - No outcome had been seen, so "set before any outcome" was true. It was also misleading: the commit message, §8, §14 D4 and the hand-back all gave 1,000 without saying it replaced 2,400.
  - At the original gate, the study would have closed itself unrun.
- **A2 (found by the review). §3's delisting promise was false.** `stage_inclusion` reads the expiry-day bar for the corporate-action ratio, and on a `KeyError` it counts `missing_input:daily_bar` and skips the event. It halts only above 1 % of candidates. The halt in `stage_outcomes` is never reached for such an event. The test that "proved" the halt called `stage_outcomes` directly.
- **A3. Contrary evidence on listings was seen and not reported.**
  - The author's own probe showed TSN with weekly expiries through 2024-08-02 and then only 2024-08-16 in the 35 days after an 08-05 announcement.
  - The monthly-only "witness" for AMT, MNST, AZO and AXON came from the same Alpaca contract list whose completeness was in question. It was not independent.
- **A4. "Mostly later-acquired" was never checked.** The 34 missing names were not classified. They include share classes (BF-B, BRK-B, FOXA, GOOGL, NWSA) and renames.
- **A5. The condition mix** was counted on the 60-event archive alone, before the 150-event run.
