---
task_id: T-410
title: Census of what has NOT been tested (options-forward), of how ideas could be combined into a desk, and of what the evidence bar allows
date: 2026-11-20
type: DESIGN CENSUS. Read-only probes of data AVAILABILITY only (a few API calls, file spans, public CSV headers). No candidate's returns were computed; no price was joined to any outcome.
status: PROPOSAL for the director's queue. Nothing measured. N_trials consumed 0. The three pre-registration sketches in §7 state the trials they WOULD add; none is frozen.
lens: edge-analyst (docs/Core/roles.md)
follows: the owner's direction of 2026-11-20; the 2026-11-14 fresh-eyes and salvage audits; T-407 and T-408 (the closures this note copies for honesty and arithmetic)
---

# T-410: what has not been tried, what could be combined, and what the bar allows

## 0. The answer, in plain language

**Most options ideas in the record are dead for reasons that hold in any account, and they should stay dead for you. Three things were never tested and are now testable on free data. Each has roughly a one-in-twenty to one-in-ten chance of passing the project's bar in a form you could trade; the earnings-options pricing question itself has about one in five. If one is real, it is worth hundreds of dollars a year at your size, not thousands. "Combining" helps only in specific ways. Blending more signals is not one of them.**

- **What stays dead, and why, for you specifically.** Writing puts or covered calls *instead of* holding stock lowers long-run wealth. So do protective puts, collars and buffer funds, which cost about 3 percentage points a year over three decades (`docs/Sources/alpha_frontier_review_2026_09_30/02_route_research.md:274-295`). Leverage through long-dated calls was also dropped (T-396). You have said you maximize terminal wealth, buy through crashes, and accept ending at half the S&P in a bad stretch. Insurance is therefore the wrong purchase: you would pay the premium every year for protection you have said you do not need. In a taxable account, a collar or put on stock that has gained in value can also trigger the tax straddle rules or a "constructive sale" (IRS Publication 550, read today).
- **Three things were never tested and could be:**
  1. **E-1, earnings options as a per-event book.** Alpaca gives away option trade history back to January–February 2024, including expired contracts (verified today). That is about 11 earnings seasons, several thousand independent company events. The test asks whether the options market prices a company's earnings move too cheaply or too dearly. The signal is the option-implied move against that company's own past earnings moves. The test is decisive either way. **About 18 % that the pricing signal is real; about 4 % that it survives trading costs as a tradeable book.** A null closes an idea the record has proposed four times (G1, G2, G4, F-7) and never run.
  2. **O-1, selling small, capped-risk index options on top of the stocks you hold.** The stocks are used as collateral: nothing is sold and nothing is borrowed. This is the best-documented options premium in the literature, isolated from the parts of covered calls that do not pay. Cboe publishes free daily index histories of these trades back to 1986 (verified today). It needs a self-directed taxable account with options-spread approval, so it waits on your robo decision (T-409). **About 10 %, and less if retail option spreads are as wide as I fear (§4).**
  3. **E-2, an earnings-announcement stock basket in the Roth.** This buys the S&P 500 companies about to report each week. Stocks earn more in their announcement windows (Savor–Wilson 2016), and the record never event-studied it. **About 9 %. Very sensitive to trading cost.**
- **The dollars.** If any one of these is real, it is worth roughly $100–900 a year at your size. Odds times dollars puts each at **tens of dollars a year of expected value today**. That is the 11-14 audit's finding again. Where the money sits, taxes and contributions are worth an order of magnitude more, and they are certain (T-409, T-400). Run these tests because each is cheap and a null closes a family for good, not because they will change your year.
- **Combining, plainly.** The record's combination work failed (9 of 9 interaction tests null; the "ensemble paradox" refuted; the composition stack a defensive shape at a cost in wealth). The reason: combining signals that each carry no information gives no information, and every blend tried is another trial. Combining adds value in three ways only:
  - **many small independent bets in one book**, where evidence grows with the square root of the number of *independent* events;
  - **a conditioner with a stated reason, tested as the conditional**, which must raise the per-event effect by at least 1.4× if it keeps half the events, or 2× if it keeps a quarter;
  - **stacking a premium on top of the stock holding without selling stock**.
- **A rule of thumb for anything you might add to the book.** Something with no correlation to stocks must earn about **7.4 % a year** just to avoid lowering your long-run growth (§1.4). Something that falls with stocks faces a higher bar: about 9 % for put-writing. Gold, bonds, trend and merger arbitrage sit at or below their bars. In the record, put-writing has trailed its bar since 2010. None of them clears unless stacked with cheap financing. This is why "diversify into X" kept costing wealth in this record.
- **"Work like a trade desk."** A desk's durable advantages are its back office and its book:
  - the back office: tax lots, financing, costs;
  - the book: small independent bets with risk limits.
  
  The information sources the project archives belong on the desk's screen first (Kalshi, options-implied moves, the earnings calendar, VIX term structure, credit spreads). Each graduates into an order only through a pre-registered per-event test (§3.5, D-1). No information source in the record has graduated yet.
- **What needs your word before any of this can run as money:** whether to leave the robo for a self-directed taxable account (T-409 decision A); options-spread and margin approval on that account; and the Schwab phone call T-409 already lists. None of the three tests needs your word to *run*: they need only free data and a director's freeze.

---

## 1. The bar and the arithmetic used throughout

### 1.1 The bar
N_eff ≈ 372 (`[NN-MBL]`; T-391). The expected maximum of 372 null t-statistics is about **z_c = 2.96**. A real effect needs **E[t] ≈ 3.80** for 80 % power. Adding one trial moves N_eff to 373 and z_c by < 0.01, so I treat z_c as fixed.

### 1.2 Time-series premia (one return per period)
t = IR · √T. The information ratio needed:

| T (years) | at the bar (50 % power) | for 80 % power |
|---|---|---|
| 2.7 (Alpaca options history) | 1.80 | 2.31 |
| 21.8 (EDGAR 8-K item 2.02, 2004-08 → 2026-06) | 0.63 | 0.81 |
| 26 | 0.58 | 0.75 |
| 40.4 (Cboe strategy indices, 1986-06 → 2026-10) | 0.47 | 0.60 |
| 58 | 0.39 | 0.50 |

### 1.3 Per-event designs
t = ρ · √n_eff, where ρ = (mean per-event effect) / (per-event σ) and n_eff counts *independent* events. The events needed for 80 % power are n = (3.80 / ρ)²:

| ρ | 0.02 | 0.03 | 0.05 | 0.10 | 0.20 | 0.30 | 0.50 |
|---|---|---|---|---|---|---|---|
| events | 36,100 | 16,044 | 5,776 | 1,444 | 361 | 160 | 58 |

Two traps from the T-407/T-408 closures apply to every per-event idea below. I check both:
- **A persistent conditioner is a regime split.** If the conditioning variable stays high for months (implied vol, a recession probability, credit spreads), n_eff is the number of regimes, not events (`.claude/agent-memory/edge-analyst/feedback_per_event_effect_to_noise.md`).
- **Signal-variance collapse.** Census the conditioning variable's spread in recent years before computing power (`feedback_signal_variance_collapse.md`).

### 1.4 Combination arithmetic (the owner's main interest)

| Kind of combination | What happens to the evidence | What happens to wealth |
|---|---|---|
| **Blend K signals into one score for the same decision** | For two signals with IRs a, b and correlation ρ: IR² = (a² + b² − 2ρab)/(1 − ρ²). If a ≈ b ≈ 0 the blend is ≈ 0. Every weight chosen on data is a trial. | Nothing to add if the parts are empty |
| **Pool independent bets in one book** | t_pooled = Σ nᵢμᵢ / √(Σ nᵢσᵢ²). Grows with √(independent events), but only if each part's edge is the same sign and > 0 | Fundamental-law diversification: IR = IC · √breadth |
| **Condition A on B** | If the filter keeps a fraction p of events, the conditional ρ must exceed ρ/√p to gain power. Keeping 25 % needs 2× the per-event effect. The condition must be named before the data | Fewer trades, lower cost |
| **Add an asset X at weight w, displacing stock** | Unchanged | Log growth changes by dg/dw ≈ μ_X − μ_E + σ_E² − ρσ_Eσ_X at small w. With μ_E ≈ 10 % and σ_E ≈ 16 % (planning), X must earn **> 7.4 % + ρσ_Eσ_X** a year, or growth falls |
| **Stack an overlay O on top of stock (no displacement)** | Unchanged | dg/dk ≈ μ_O − ρσ_Eσ_O − kσ_O². The overlay must earn more than its crash-correlated variance |

The displacement line is why gold (B-10: +0.042, ci_low −0.341), the trend sleeve (T-311: buy-and-hold 2.9× on wealth), CEF and the barbell (T-251: −1.6 %/yr) each cost wealth or straddled zero while improving drawdowns. It is planning arithmetic, not a measurement: it uses an assumed μ_E and is only a first-order (small-w) approximation.

### 1.5 Pass probability
P(pass) = Σ_s prior(s) · Φ(E[t | s] − 2.96), summed over a few effect scenarios s. The priors are mine and are stated in each card.

### 1.6 The owner's size (planning values)
Taxable ≈ $40k (under $50k; today inside the Schwab robo). Roth ≈ $15k ($10–25k; broker unknown). Contributions ≈ $500/month (T-409's default). One SPY or XSP option controls ≈ **$71.8k** of index (SPX 7,175.83 on 2026-11-19, per the SqueezeMetrics file read today). That is more than either account.

---

## 2. The map: what was tested, in exactly what form, and what never was

A verdict is quoted with its scope. **"UNTESTED (RR-1)"** marks a verdict whose number came from the frozen-capital controller. RR-1 §5 demotes those, and `[NN-SUPERSEDED]` applies (`docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md:472-479`).

### 2.1 Options as INSTRUMENTS

| Family | Exact form tested (task) | Verdict | Never tested | For this owner |
|---|---|---|---|---|
| **Selling premium instead of stock** (put-write, covered call, buy-write) | T-261 (2026-07-02), a screen only (0 trials): CBOE PUT, BXMD and JEPI as an income leg beside the trend sleeve. T-279: 70 % trend sleeve + 30 % CBOE PUT, 2000–2026, on Sortino and MDD gates | T-261: refuted as a diversifier ("sells exactly the convexity the sleeve needs"). T-279: negative addition; paired CIs straddle zero, points worse; one XSP put ≈ $60k then | Any test against the *current* core (85/15 or 100 % VOO); any after-tax test; the weekly (WPUT) and condor (CNDR, BFLY) forms | **Stays dead as a substitute.** Israelov–Nielsen 2015: a covered call is equity + short vol (realized SR ≈ 1.0, < 10 % of risk) + an *uncompensated* reversal bet. The only form worth testing is the short-vol leg alone, stacked (O-1) |
| **Selling premium ON TOP of stock** (defined-risk, collateralized by the stock's loan value) | Never | — | Everything | **O-1** (taxable only; Level 3 spreads) |
| **Buying convexity**: protective puts, tail hedges, collars, buffer funds | No trial. Literature dismissals in route research D1/D3/D6: PPUT 6.64 % vs S&P 9.80 % (1986–2018); Israelov–Klein on collars; "Pathetic Protection" (Israelov 2018, title verified); "Rebuffed" (2025). T-342: a VIX-term conditioner for the "lever into the crash" rule, DRAFT, not run; it fires on **3 episodes** | Dead on literature | A measured test | **Stays dead: wrong purchase for a won't-sell wealth maximizer.** Tax hazard in taxable: a put or collar on appreciated VOO is a straddle (loss deferral; holding-period effects) and can be a constructive sale (IRS Pub 550) |
| **Defined-risk spreads** (verticals, condors) | Never (an IRA is Level 2: no spreads) | — | Everything | Taxable opens them. O-1 for the index; the single-name version is E-1's short leg (weak: ordinary-rate gains) |
| **Event volatility, single-name earnings** | Never run. Route research G1 (long small-cap straddles, forward, N 0), G2 (short vol-crush; "dead in the Roth"), G4 (skew and term factors; "blocked"); program F-7 (a forward book, never built) | — | Any historical test. The free data now exists (§4) | **E-1** |
| **Event volatility, macro releases** (CPI, FOMC, NFP via index options) | Never | — | — | **Closed by arithmetic, unrun.** About 32 events a year; ρ ≈ 0.1 needs 1,444 events (45 years); the same wall as T-407 |
| **Calendar and term-structure trades** | Never | — | — | Data-blocked: no free historical chains (§4); Level 3 in taxable. Dew-Becker et al. say the premium sits in *short-dated* variance. Low priority |
| **Collars on the core holding** | No trial (literature, D1) | Dead | — | **Stays dead**, doubly so in taxable (the straddle rules) |
| **LEAPS** as leverage | T-396: design note, arithmetic only | Hold 1×; do not build a LEAPS path | A priced historical test (no data) | Closed as a decision |
| **Box spreads** as financing | T-409 rev. 2, arm B6: conditional on Schwab confirming Reg-T short-box proceeds are usable | Open: a decision item | — | T-409's Schwab call |
| **VIX products** (SVXY, VIXY) | Route research G3: SVXY −95 % NAV Feb-2018 | Dead | — | Stays dead |
| **Dispersion, 0DTE, intraday gamma** | Route research: listed dead | Dead | — | Stays dead (legs, size, intraday) |
| **Futures** (MES) for leverage or carry | T-294 / T-294b; T-409 rev. 2: taxable futures dropped below ~$76k | Granularity | Futures carry (never tested) | At ~$36k notional per MES, revisit at size |

### 2.2 Options as INFORMATION

| Family | Exact form tested | Verdict | Never tested | Status |
|---|---|---|---|---|
| **VRP (VIX − RV21) as exposure timing** | T-174: median overlay on the 0.751 book, 1995–2025. T-122: VRP factor inside the ensemble | Ledger rows say "refuted"; **both UNTESTED (RR-1)**: the base curve was a controller curve | VRP timing of a static 100 % equity core on the fair harness | **Closed by class, not by evidence.** Regime timing measured dead three times (T-333 −5.16 pp/yr; T-274; T-289 sizing tilts). VRP is persistent, so n_eff = regimes. Do not re-run |
| **IV term structure, VVIX** | T-274 (fair harness): VIX/VIX3M + VVIX tilt on the trend sleeve, 2006–2026. T-233: VIX-term front-runner. T-087: VVIX-z | H0 (P(implied > null) = 28 %); trigger-happy; NO-GO | On a static core | Closed by class |
| **SKEW index** (1990+) | Never as a signal (ingested by T-256) | — | — | Timing class: closed. The single-stock smirk is X-1 |
| **Put/call ratios, open interest** | Never | — | — | Timing class: closed. The free Cboe archive ends 2019-10-04 (§4) |
| **Implied vs realized move around events** | Never | — | — | **E-1** for earnings; macro events are closed by arithmetic |
| **Dealer gamma (GEX)** | Never (F-6 forward conditioner, never built) | — | — | Vol-timing class. At most a *later* conditioner inside O-1; not a first trial |
| **Implied correlation, dispersion** (COR1M/COR3M 2006+, DSPX 2014+) | Never | — | — | Timing class: closed |
| **Single-stock option signals** (call-minus-put IV spread, smirk, option/stock volume) | Never | — | — | **X-1** (Alpaca 2024+ trade prints; weak power) |

### 2.3 Alt-data the project already ARCHIVES (spans read today, §4)

| Source | Tested as | Verdict | Untested forms worth naming |
|---|---|---|---|
| Kalshi, Polymarket | T-403 (taker favourite-longshot probe, DRAFT); T-407 (information for the held book) | T-407 closed the trading use unrun (effect/σ ≈ 0.1); T-403's own prior ≈ 2 % at the bar in 12 months | Kalshi × options event-vol (≈ 150 events: closed by arithmetic); the T-403 probe as drafted (P-1) |
| News (771k articles, 2015–2026) | T-289: four frozen interaction tests | All null; the sizing-tilt family closed | News intensity as a conditioner inside E-1. Forbidden in a first run (trial inflation) |
| EDGAR Form 4 | T-144 (UNTESTED, RR-1); T-381 small-cap insider clusters on T-265 (fair) | T-381 null (t_HAC 0.20; the Mar-2020 cluster drives the pooled CAR) | — |
| EDGAR 8-K | T-137 | Null | **Item 2.02 acceptance times as an earnings-timing source** for E-1 and E-2. Never used this way |
| EDGAR 13F | T-145 (UNTESTED, RR-1) | — | Low prior |
| Lazy Prices (10-Q/10-K text) | T-383 | Refuted in both arms | — |
| RegSHO short volume, short interest, FTD, margin debt, NAAIM | Never. The 2026-08-26 prereg: "NOT TESTABLE on the current accrual" | — | Free history exists outside the archive (§4), but as timing it is the closed class; as a cross-sectional screen, low prior |
| EPU (1985+), GPR (1900+) | Never | — | Timing class: closed. Elections are priced in options (Kelly–Pástor–Veronesi 2016), but there is about one US event every two years: closed by arithmetic |
| Credit OAS (1996+, recovered by T-336) | T-233 (the BAA−AAA proxy failed its own gate); salvage item 10 | Timing class | — |
| Fed-meeting ladder, rate path | T-295 (baseline); T-291 (even-week × FOMC, H0); T-408 (closed by power) | Closed | — |
| CEF discounts | T-267, T-379 | Real before 2011; killed by cost and day-2 decay | The days-horizon passive form (salvage D); real money only |
| USAspending awards, GDELT tone | Never | — | Short archives (GDELT from 2025-07); low prior |

### 2.4 Macro and cross-asset (brief; all in CURRENT_STATE)
- Trend: a regime option. It costs wealth at depth (T-311, T-333); the stacked form on investable funds was refuted (T-398).
- Carry: the ETF proxy null (T-263); futures carry never tested (size).
- Gold: refuted on wealth (B-10).
- Factor tilts: momentum is the only CI-significant tilt, with its decayed variant straddling (T-320); small-value and quality straddle (T-318, T-320); combinations refuted (B-9).
- Leverage: no form CI-beats 1× (T-312, B-5, T-315 as corrected by T-399); a belief decision (T-396, T-409).
- Elsewhere: BTC (T-272), international (T-313), managed-futures ETFs (T-110/112/253, DBMF shadow).

Nothing in this group is re-proposed here.

---

## 3. Combinations: why the earlier work failed, and what can still add value

### 3.1 The record
1. **The composition stack** (T-211/T-215): UNTESTED (RR-1). Its fair-harness relatives, the barbell (T-251) and HRP (T-248), are a real drawdown improvement, with ci_low < 0 on risk-adjusted terms and −1.6 %/yr of wealth.
2. **The combination grids** (`docs/State/conditional_shelf.md` #15): 9 of 9 pre-registered interactions null. They were news-volume × momentum, sentiment × 8-K, novelty × reversal, the aggregate-news tilt, the breadth tilt, the calendar tilt, even-week × FOMC, regime-gating the overlay, and the return-stack double trend.
3. **The ensemble paradox** (2026-04-30): SUPERSEDED. The "alpha appears when capital is split" was an impact-cost artifact on a survivorship-inflated substrate; T-241's concentration test refuted it.
4. **The conjunctive "True Edge" selector** (T-216): built, 2-way H0. The foundry vocabulary it gates is 0/35 (T-196, itself UNTESTED by RR-2/RR-3).
5. **B-9 multi-factor tilts:** the power premise failed on both inputs (tilt active-return ρ −0.07, not −0.3; the value leg's TE 19.9 %, not 8 %).
6. **Stacks:** B-5 levered stock/bond stacks are a bet on the sign of the stock–bond correlation. T-296's double trend *interferes*: the managed-futures uptrend masks SPY's decline.

### 3.2 Why, mechanically
- **Products of zeros.** Each component of the grids had no standalone information on the honest substrate (cross-sectional 0/16, foundry 0/35). An interaction cannot conjure an effect that neither side carries, unless a theory says the effect lives *only* in the joint state. None of the nine had one strong enough to survive the ρ/√p cost of conditioning.
- **Persistent conditioners.** Most conditioners were states (news regime, breadth, calendar, regime-HMM). Their independent observations were regimes, not days.
- **Redundancy.** On the trend sleeve, every vol-state tilt fired when trend had already exited (T-274, T-262).
- **Displacement.** Every diversifier that lowered drawdown also displaced equity at below the §1.4 threshold, so wealth fell. The owner's objective (terminal wealth, no selling) makes this the dominant cost.

### 3.3 What kinds of combination can still add value

| # | Combination | Mechanism (ex-ante) | Why it is not a richer model of the exhausted price data, nor regime timing | Independent observations |
|---|---|---|---|---|
| **C1** | **A pooled book of independent per-event bets** (E-1 long leg + E-2 + later M-1, P-1) | Each family has its own counterparty reason. Pooling multiplies evidence by √(families) when the signs agree | Events are firm-level jumps, deals or contracts, not market states. The evidence statistic is cross-sectional within each event week | E-1 ≈ 4–8k events; E-2 ≈ 700–1,100 weeks; M-1 ≈ 2–3k deals [R] |
| **C2** | **Options information × the firm's own history × the event calendar** (E-1: implied earnings move ÷ the firm's trailing realized earnings moves, sorted *within* each announcement week) | Implied earnings moves under-weight firm-specific jump history (Gao–Xing–Zhang 2018: investors underestimate earnings uncertainty; Goyal–Saretto 2009: realized-minus-implied vol sorts straddle returns) | The conditioner is a different market's price (options), set against that firm's own history, on a pre-scheduled event. Sorting within each week removes the market-wide vol level, so it cannot become regime timing | ≈ 4–8k events; n_eff ≈ 2–4k after week clustering (to be censused) |
| **C3** | **Options as a risk or convexity layer on the core** | Insurance pays in crashes at the cost of the variance premium | — | The number of crashes: ≈ 3–10 in 40–58 years. **Never evidence; a decision.** For this owner the answer is no (§2.1) |
| **C4** | **Information as a filter on WHEN or HOW MUCH for the core** | — | It is regime timing | The number of regimes: ≈ 5–15. **Closed** |
| **C5** | **Stack a premium on the core using its buying power** (O-1: defined-risk XSP short options) | The short-vol leg of a covered call carries the premium (Israelov–Nielsen 2015). Short-dated variance is what investors pay to hedge (Dew-Becker et al.; Coval–Shumway 2001: zero-beta ATM index straddles lose ≈ 3 %/week). Hedgers are the structural counterparty | A priced premium with 40 years of free history (the fresh-eyes audit's class 2), not a mined signal. No conditioner in the first run | ≈ 485 months (crash-clustered); tail evidence ≈ 3 crashes |
| **C6** | **Kalshi probability × options-implied event move** (buy event straddles when Kalshi's distribution is wider than the options') | Two markets pricing the same event | It is per-event | ≈ 150 events since 2022. **Closed by arithmetic** (needs ≥ 1,444) |
| **C7** | **News or 8-K intensity × earnings straddles** | Attention raises jump size | — | Inside E-1, but a second conditioner is a second trial. **Only after E-1** |

**The one sizing rule that combines information legitimately.** Inside a per-event book, size each bet in proportion to its pre-registered predicted edge (fractional Kelly), with the predictor frozen before the data. That uses information for "how much" without timing the core.

### 3.4 Where each idea lives

| Idea | Roth | Taxable (self-directed, after leaving the robo) | Reason |
|---|---|---|---|
| VOO core | — | **here** | Deferral of gains (T-400) |
| E-1 long straddles | **here** (Level 2; Alpaca IRA verified per T-402 [S17]) | allowed, but ordinary-rate gains | Turnover; equity options are not §1256 |
| E-1 short leg (single-name condors) | not allowed | Level 3; ordinary-rate gains | Weak after tax |
| O-1 index premium overlay | not allowed (Level 2) | **here**: spreads + margin approval; XSP is §1256, 60/40 and marked to market | Needs the core as collateral |
| E-2 announcement basket | **here** | no (≈ 52 round trips a year) | Tax |
| M-1 merger arbitrage | unlevered: loses by displacement | stacked only with box financing (T-409 B6) | §1.4 |
| P-1 Kalshi | no venue for IRAs (T-403) | a separate Kalshi account; tax character unsettled (T-403) | — |

### 3.5 What "work like a trade desk" can honestly mean here

| Desk function | What it is here | Evidence it needs | Engine / path (boundaries per `docs/Core/engine_charters.md`) |
|---|---|---|---|
| **The book** | Independent per-event sub-books, each behind its own frozen test, pooled as C1 | A pre-registered per-event test per family | Engine A signals; Engine C sizing |
| **The risk desk** | A cap on combined worst-month loss across the core and any short-vol overlay, against the owner's 0.5 × S&P bound; per-event concurrency caps | Structural limits, no test | Engine B: propose-first |
| **The back office** | Tax lots; §1256 versus equity-option character; the cross-account wash-sale guard (single-account today, T-358); financing (box, T-409); the execution-cost ledger (exists) | Deterministic | `paper_trader/` / `live_trader/`: propose-first. **No options order path exists in the code** (T-396 §3). Building one touches the live path |
| **The screen** | Kalshi ladders; options-implied event moves (forward, from the free snapshot's IV and greeks); the earnings calendar; VIX term structure; credit OAS; GEX. **Display only**, each tagged "not a trading input" | None, because it changes no order | `cockpit/dashboard_v2/` only |
| **Graduation** | A screen item becomes a book input only through a frozen per-event prereg that clears z ≥ 2.96 | The bar | Engine F governance |

Under `[NN-AI-GATE]`, no LLM interprets the screen into orders. This census proposes no AI component.

---

## 4. Data realities

**V** = verified today (2026-11-20) by a probe or a document read. **R** = recalled or taken from the record, not re-verified.

### 4.1 Options prices and implied vol

| Source | What it gives | History | Cost | Status |
|---|---|---|---|---|
| **Alpaca options market data** | Historical **bars** (OHLC, volume, VWAP, trade count) and historical **trades** (price, size, exchange, condition), **including expired contracts**: AAPL 2024-05-03 175C returned 31 daily bars and trade prints. **No historical quotes:** `/v1beta1/options/quotes` → HTTP 404, and Alpaca's own API index lists only bars, trades, latest quotes, latest trades, snapshots and chain. **Snapshots and the chain carry `impliedVolatility` and greeks** (delta, gamma, rho, theta, vega) for near-ATM contracts, *current only*. Bars take no `feed` parameter | Docs: "only … since February 2024"; a Feb-2024 SPY contract returned bars from 2024-01-18 | Basic (free): the indicative real-time feed ("not actual OPRA quotes … just indicative derivatives"); historical access except "latest 15 minutes"; 200 calls/min. Algo Trader Plus **$99/month**: OPRA real-time, 10,000 calls/min | **V** |
| Alpaca trading | Multi-leg orders (Level 3) on the Trading API (iron-condor examples). Index options SPX, SPXW, XSP, VIX and DJX are documented on the **Broker API** pages (XSP fee $0 below 10 contracts; underlying index levels "not at initial launch"). IRA options up to Level 2 | — | — | **V** for the docs; **R** for the IRA level (T-402 [S17]). Whether retail Trading API or paper accounts can trade index options: **unverified** |
| **Cboe free index histories** (`cdn.cboe.com/api/global/us_indices/daily_prices/<SYM>_History.csv`) | VIX 1990-01; VIX1D 2022-05; VIX9D 2011-01; VIX3M 2009-09 (the on-disk file starts 2006-07); VIX6M 2008-01; VIX1Y 2007-01; VVIX 2006-03; SKEW 1990-01; VXTH 2006-03; PUT 1991-03 (on disk from 1986 via Wayback, T-261); BXM 2002-03; **BXMD, BFLY, CNDR, CLLZ, CMBO, PPUT 1986-06**; BXY 1988-06; **WPUT 2006-01**; BXMW 2012-06; CLL 2008-08; COR1M/COR3M 2006-01; DSPX/VIXEQ 2014-06; VXN/RVX/OVX/GVZ 2009-09; all current to 2026-11-19 | as listed | free | **V**. Trap (record): strategy indices are gross, with VWAP-window fills, and were backfilled to 1986 at launch; retail fills are worse |
| Cboe put/call ratios (`cdn.cboe.com/resources/options/volume_and_call_put_ratios/{total,equity,index,vix,etp}pc.csv`) | Daily calls, puts and P/C | **2006-11-01 → 2019-10-04 only** | free | **V**. After 2019 only the daily web pages |
| SqueezeMetrics DIX/GEX CSV | Daily DIX, GEX and SPX price | 2011-05-02 → 2026-11-19 | free | **V** |
| OptionMetrics IvyDB (via WRDS) | Full surfaces, PIT, 1996+ | 1996+ | university subscription | **R**. Whether the owner's school subscribes is unknown. It would unblock G4 single-stock factors, calendar trades and a quote-based E-1 to 1996 (≈ 30 years, ≈ 100k+ events) |
| ORATS; Databento OPRA; Cboe DataShop | Surfaces; tick NBBO; SPX EOD chains | 2007+ / 2012+ / varies | ORATS $99–199/mo; Databento pay-as-you-go; DataShop ≈ $100–300 per history-year | **R** (program doc P-2/P-3, search-verified 2026-09) |
| Dolt options mirror | EOD chains | 2019+ | free | **R**: survivorship-biased per the record |
| Minneapolis Fed options-implied probabilities | — | — | — | Three URLs returned 404 today. Treat as unavailable |

**What this means for each family:**
- **Earnings options (E-1):** testable on free data from 2024 with trade prints. No historical NBBO anywhere free, so the *gross* premium is testable and the *net-of-spread* claim is not. Costs must come from trade-print effective-spread estimates or real fills. Paper fills hit the indicative feed and are invented (`feedback_paper_probe_taker_only.md`). F-5 and F-7 were specified with "cost = paid spread from the OPRA history". **That cost source does not exist** on Alpaca (§8).
- **Index premium (O-1):** free 40-year *index* proxies, gross. Retail XSP spreads are the binding unknown. Measure them from real quotes before the freeze: one month of the $99 OPRA feed, or Schwab's quote screen.
- **IV history:** none free. The snapshot's IV and greeks can be **archived forward** daily at no cost. That would start the clock on a quote-based record.

### 4.2 The project's own holdings (read-only spans)

| File | Span | Note |
|---|---|---|
| `data/macro/VIX*.parquet`, `VVIX`, `SKEW` | ends **2026-06-26 / 07-01** | **Stale ~5 months.** The Cboe CDN is current |
| `data/positioning/*` | RegSHO 2026-06-01 → 11-19 (110 days); short interest 10 snapshots 2026-05 → 10; FTD 2026-05 → 10; margin debt 19 months; NAAIM 2006 → 2026-07 | The free history outside the archive: FINRA consolidated (CNMS) short-volume files served for 2018-08 (**V**; 2009–2010 CNMS → 403); SEC FTD back to 2004 (**R**; SEC host not fetched under the UA policy) |
| `data/macro_data/alt/*` | Kalshi and Polymarket snapshots; OAS 1996-12 → 2026-11-16; EPU daily; GPR monthly 1900 → 2026-10; GDELT 2025-07 → 2026-07; USAspending; Form-4 index | as above |
| `data/earnings/*_calendar.parquet` | **117** large caps, 2020-04 → 2026-04, with `hour` (before or after the open) | A check on 8-K timing |
| `data/research/t265/ann_dates.parquet` | 88,866 announcement dates, 2004-08-24 → 2026-07-01 | The CIK-level T-265 panel (not survivorship-complete) |
| `data/edgar/8k/panel_8k_items.parquet` | 183,278 filings, 1994-01 → **2026-06-10**, with `acceptance_dt` | Item 2.02 acceptance times give earnings timing. Needs a refresh, by the director's SEC-host mechanism |
| `data/universe/sp500_membership_pit.parquet` | 1,255 intervals | 386 in-window names lack price files (the 2026-10-23 survivorship search) |
| Option chains of any kind | **none on disk** | — |

### 4.3 Tax facts (IRS Publication 550, read today, **V**)
- Section 1256 contracts include **nonequity options**, which include **broad-based stock index options** (SPX, XSP). They are marked to market at year end, and gains and losses are **60 % long-term / 40 % short-term** whatever the holding period. SPY options are equity options: they are not §1256 and follow the ordinary holding-period rules.
- **The straddle rules** apply to stock plus an offsetting position: loss deferral, plus capitalization of interest and carrying charges. One exception is **qualified covered calls** on optioned stock.
- **Constructive sales of appreciated financial positions:** certain hedges of an appreciated position are treated as a sale.

Consequence: options cannot be used to dodge the robo-switch tax (T-409 decision A). A collar or protective put on the taxable VOO core is a tax hazard, not a neutral hedge.

---

## 5. The candidates

Each card gives: theory; data and cost; class; independent observations; pass-probability arithmetic (or "decision / forward-record item"); wrapper; dollars at the owner's size. "Planning" means an assumption to be replaced by a pre-freeze census on non-outcome data.

### E-1: earnings variance pricing, conditioned on the firm's own history (options, per-event)
- **Theory (ex-ante).**
  - Option prices embed an earnings-jump component (Dubinsky–Johannes, *Earnings Announcements and Option Prices*, WP abstract read; RFS 2018 version title verified).
  - Gao–Xing–Zhang (JFQA 2018): ATM straddles from 3 days before to the announcement earned **+3.34 %**, more so in small, volatile and costly-to-trade names. "Investors underestimate the magnitude of uncertainty around earnings."
  - Goyal–Saretto (JFE 2009): straddles sorted on historical-minus-implied volatility earn significant monthly returns.
  - Against the effect:
    - Coval–Shumway (JF 2001): zero-beta ATM *index* straddles lose ≈ 3 %/week, so options are generally dear;
    - the record's reading of Duarte–Jones–Khorram–Mo–Wang (RFS 2026), not read by me: option-strategy Sharpes inflated by ex-post quote filters;
    - Muravyev–Pearson (RFS 2020): effective spreads for traders who time executions are < 40 % of the conventional measure, so cost assumptions must be measured.
- **Primary statistic.** Within each announcement week, sort events by q = (straddle-implied move) / (median of the firm's last 8 realized earnings moves). Take the bottom-minus-top tercile mean straddle return.
- **Data and cost.**
  - Alpaca option bars and trades, 2024-01 → 2026-10 (free).
  - Underlying prices.
  - Announcement timing from 8-K item 2.02 acceptance times (on disk to 2026-06; refresh needed), checked against the 117 calendars.
  - Zero dollars. Days of API pulls at 200/min. A few hundred MB.
- **Class:** per-event. **Observations:** ≈ 4–8k events (count to be censused). n_eff ≈ 2,500 planning (week clusters, design effect 2).
- **Pass arithmetic (H1b, the tercile spread).** σ_event ≈ 0.8 (planning), so the tercile-spread SE ≈ 0.8·√(6/2,500) = 3.9 pp.

  | Scenario spread | 20 pp | 10 pp | 5 pp | 0 |
  |---|---|---|---|---|
  | E[t] | 5.1 | 2.6 | 1.3 | 0 |
  | P(t ≥ 2.96 \| s) | 0.98 | 0.36 | 0.05 | 0.002 |
  | prior | 0.10 | 0.20 | 0.30 | 0.40 |

  **P(H1b) ≈ 18 %.** The deployable long leg net of costs (H1c: bottom tercile, n_eff ≈ 830, SE 2.8 pp; priors of +10/+5/0/−5 pp at 0.05/0.15/0.40/0.40) gives **P ≈ 4–5 %**.
- **Wrapper:** the long leg in the Roth (Level 2). The short leg is taxable Level 3 at ordinary rates: weak.
- **Dollars:** ≤ 10 concurrent at 1 % of NAV ($150), about 150 events a year, so **$225/yr per percentage point of net edge**. A real +3 pp would be ≈ $700/yr against a year-to-year SD of ≈ $1,500. Even a true edge would take years of real trading to see.

### O-1: a stacked, defined-risk index premium overlay on the taxable core (options, priced premium)
- **Theory.**
  - Israelov–Nielsen (FAJ 2015): a covered call = equity + short volatility (realized Sharpe ≈ 1.0, < 10 % of risk) + an uncompensated equity-reversal exposure. The efficient way to own the premium is the short-vol leg alone, stacked on equity instead of displacing it.
  - Dew-Becker–Giglio–Le–Rodriguez (2014/2017): only transitory realized variance is priced, so the premium sits in short-dated options.
  - Coval–Shumway (2001).
  - The counterparty is hedgers buying index protection.
  - T-279 and T-261 tested the PUT index only as a 30 % *substitute* inside the trend sleeve, on Sortino. The stacked form on terminal wealth was never tested.
- **Data and cost.**
  - Cboe CNDR (iron condor), BFLY and PUT daily, 1986-06 → 2026-11, free.
  - The T-306 equity series.
  - T-409's after-tax engine (DRAFT) for §1256.
  - **Retail XSP cost is the binding unknown.** One condor ≈ 35 points of wing (≈ $3,400 requirement). The entry half-spread on 4 legs ≈ $12–40 [R] plus Schwab $0.65 × 4 (T-402 [S9]), so ≈ 0.4–1.3 % of the requirement per month. That could eat a large part of the premium. Measure real quotes before freezing (§4.1).
- **Class:** a priced premium on a long free history (class 2); time series. **Observations:** ≈ 485 monthly outcomes; ≈ 3 crash episodes.
- **Pass arithmetic.** T = 40.4 years needs a net overlay IR ≥ 0.47 at the bar.

  | Scenario net overlay IR | 0.6 | 0.4 | 0.2 | ≤ 0 |
  |---|---|---|---|---|
  | E[t] | 3.81 | 2.54 | 1.27 | 0 |
  | P(pass \| s) | 0.80 | 0.34 | 0.05 | 0.002 |
  | prior | 0.07 | 0.20 | 0.38 | 0.35 |

  That is 0.14 before the decay condition. Requiring a positive 2010+ point estimate (about 70 % given a pass) gives **≈ 10 % (6–14 % across cost assumptions)**.
- **Wrapper:** taxable only. It needs leaving the robo, plus margin and spreads approval [R; one Schwab call]. Reg-T lets the core's loan value cover the spread requirement without a debit balance [R]. A cash buffer equal to the worst-month overlay loss avoids forced sales.
- **Dollars:** at k = 0.10 (overlay requirement = 10 % of equity, so the worst overlay month ≈ −10 % of the account on top of the equity loss), **$40/yr per 1 %/yr of net excess on the requirement**. At a planning 5 %: ≈ $200/yr, or $500 at k = 0.25 with a −25 % worst month. §1256 tax at the law-school brackets is light. Small.

### E-2: the earnings-announcement premium as a weekly basket (equity, per-event)
- **Theory.** Savor–Wilson (JF 2016): firms scheduled to report earn an **annualized abnormal return of 9.9 %**, persistent across stocks. They give a risk-based explanation: announcement risk covaries with market news. The record put it only into the foundry vocabulary (`earnings_proximity_5d`; T-196 UNTESTED) and excluded it from B-1 (`docs/Audit/b1_raw_signal_decile_verdict_2026-10-14.md:83-87`). It was never event-studied.
- **Data and cost.**
  - Predicted announcement dates: the prior year's same-quarter date + 364 days, so no look-ahead. Actual dates come from 8-K item 2.02.
  - The PIT S&P 500 membership.
  - Canonical prices. A survivorship gap of 386 names is a known bias.
  - Zero dollars.
- **Class:** per-event, aggregated weekly. **Observations:** ≈ 700–1,100 event-weeks over 21.8 years.
- **Pass arithmetic.**
  - Planning: 9.9 % × 5/252 ≈ 0.20 % gross per event-week, minus 10 bp round trip, ≈ 0.10 % net; a weekly basket TE of 1.0–1.5 %. So ρ_week ≈ 0.07–0.10 and IR ≈ 0.5–0.7 *if undecayed*.

  | Scenario IR_net | 0.8 | 0.5 | 0.25 | ≤ 0 |
  |---|---|---|---|---|
  | E[t] | 3.74 | 2.33 | 1.17 | 0 |
  | P \| s | 0.78 | 0.26 | 0.04 | 0.002 |
  | prior | 0.05 | 0.15 | 0.35 | 0.45 |

  **P ≈ 9 %.** It is cost-fragile: if the premium sits in 3 days rather than 5, the net is ≈ 0.
- **Wrapper:** the Roth only. **Dollars:** $150/yr per 1 %/yr of net alpha with the whole Roth in the basket, so $300–450/yr at 2–3 %, against a TE-driven SD of ≈ $1,200–1,500/yr.

### S-1: options and tax hygiene rules for the taxable account (structural, no test)
1. If index options are ever used in taxable, use **XSP or SPX** (§1256, 60/40, and losses are usable), not SPY options.
2. **Never collar or put-protect appreciated VOO lots** (straddle rules; a possible constructive sale).
3. **No covered calls on the taxable core.** They are negative on wealth (Israelov–Nielsen), with short-term gains and a risk of being called away into realizing long-term gains.
4. **Options cannot defer the switch tax.**

Certainty: the rules are verified (IRS Pub 550). Dollars: avoided losses, which could be four to five figures on one mistaken collar over embedded gains. $0 if options are never used. Wrapper: taxable.

### D-1: the desk screen and the graduation rule (operations, no test)
- Build the §3.5 screen (display only) in `cockpit/dashboard_v2/`.
- Start a free daily archive of the options-chain snapshot (IV and greeks) for the S&P 500 and the E-1 universe. It is the only route to a free quote-based record.
- Write the graduation rule into governance.
- Decision item: propose-first if it touches `paper_trader/`. Dollars: $0 direct. It is what makes the system a desk rather than a set of experiments.

### X-1: single-stock option information as a long-only Roth screen
- **Theory:**
  - Cremers–Weinbaum (JFQA 2010): stocks with relatively expensive calls beat those with expensive puts by **50 bp/week**;
  - Xing–Zhang–Zhao (JFQA 2010): the steepest smirks underperform by **10.9 %/yr**;
  - Johnson–So (JFE 2012): the low option/stock-volume decile beats the high by **1.47 %/month**.
  
  The samples end in the mid-2000s, so decay is the default. Informed traders choosing the options market is a different modality from the stock's own price.
- **Data:** Alpaca 2024+ trade prints. IV has to be backed out of prints, which is noisy. Heavy pulls.
- **Class:** cross-sectional. **Observations:** ≈ 140 weekly cross-sections.
- **Arithmetic:** T = 2.7 years needs an IC IR ≥ 1.8 at the bar. Scenarios of 2.0/1.0/0.5/0 with priors 0.05/0.15/0.30/0.50 give the IC test **P ≈ 5 %**, and the long-only deployable form ≈ 1–2 %.
- **Wrapper:** the Roth. **Dollars:** tens per year. Better deferred until a quote-based archive (D-1) or OptionMetrics exists.

### M-1: merger arbitrage, per deal (equity, per-event)
- **Theory [R; no paper read for this note]:** index and mutual funds sell targets after a deal is announced, and arbitrageurs are paid to bear the deal risk. The return profile is like a short index put.
- **Data:** EDGAR (deal filings, free) plus **survivorship-free prices**, because every target is a dead ticker. That is the owner's $39/month decision (T-374).
- **Observations:** ≈ 2–3k cash deals [R].
- **Arithmetic:** against T-bills, n_eff ≈ 1,700 at ρ 0.2/0.1/0.05/0 (priors 0.35/0.30/0.20/0.15) gives **P ≈ 60 %**. Against VOO for this owner it is the §1.4 threshold: arbitrage at bills + 3–5 % with crash correlation sits at break-even, so **P ≈ 3 %**. It adds wealth only stacked with box financing (T-409 B6, unverified), with ordinary-rate gains against 60/40 box deductions.
- **Decision-dependent.** Dollars: ≈ $300–400/yr on a $10k stack if real.

### C-1: a pooled per-event evidence rule (combination design)
- Pre-register **one** inverse-variance pooled statistic across E-1's long leg, E-2 and, later, M-1. That is one trial, not three, with the component tests descriptive.
- Arithmetic: components at t 1.2 and 1.9 pool to (1.2 + 1.9)/√2 = 2.2 with equal weights. That still misses 2.96. Pooling reaches the bar only with three or four same-signed families.
- Not an independent candidate. It is how C1 is evidenced without inflating N.

### E-3: a real-fill options cost record (forward record item, conditional)
- Only if E-1's H1b or O-1 passes.
- 50–100 real fills at ≤ $150 each measure the effective spread to about ±10–15 % (relative). That is the only honest cost input, because paper fills are invented.
- A cost measurement, not an edge test.

### P-1: the Kalshi favourite-longshot taker probe (T-403, existing DRAFT)
- Its own record: effect exists 20 %, material 8 %, **passes at N_eff 372 within 12 months ≈ 2 %**. No IRA venue; the taxable treatment is unsettled.
- Listed so the queue sees it. This census does not re-estimate it.

### Closed by arithmetic: do not run (0 trials)
- VRP, VIX-term, SKEW, put/call, implied correlation, GEX, EPU/GPR, credit, NAAIM or COT as timing for the core (regimes, not events; T-333).
- Macro-event implied-move trades (≈ 32 events a year).
- Kalshi × options events (≈ 150).
- Election options (≈ 1 per 2 years).
- Protective puts, collars, tail funds and buffers on the core.
- Covered calls or cash-secured puts on the core or on contributions (granularity $71.8k; Israelov–Nielsen).
- LEAPS leverage (T-396).
- VIX products; dispersion; 0DTE.
- Calendar and term trades until a chain source exists.
- Positioning feeds on their current accrual (the 2026-08-26 prereg).

---

## 6. Ranked top 10

The ranking is P(pass on the deployable form) × feasibility now, with ties broken on closure value: does a null retire a family the record keeps re-proposing? **Expected value is about equal and small across the top three, tens of dollars a year each at the owner's size.** The order reflects decisiveness and readiness, not money.

| Rank | Item | Class | Independent obs. | P(pass) at the bar | Wrapper | $/yr at owner's size if real | Trials |
|---|---|---|---|---|---|---|---|
| 1 | **E-1** earnings options, conditioned | per-event | ≈ 4–8k events | 18 % information; **4–5 % deployable** | Roth (long leg) | ≈ $225 per pp of net edge; ~$700 at +3 pp | +1 (H1b), +1 if H1c is gated |
| 2 | **O-1** stacked defined-risk index premium | priced premium | ≈ 485 months | **≈ 10 %** (6–14 %) | taxable, after leaving the robo | ≈ $200 (k 0.10) to $500 (k 0.25) | +1 |
| 3 | **E-2** announcement-premium basket | per-event (weekly) | ≈ 700–1,100 weeks | **≈ 9 %** | Roth | $300–450 | +1 |
| 4 | **S-1** options tax hygiene | structural | — | n/a (certain) | taxable | avoided losses | 0 |
| 5 | **D-1** desk screen + graduation rule + free IV archive | operations | — | n/a | — | $0 direct | 0 |
| 6 | **X-1** single-stock option-information screen | cross-sectional | ≈ 140 weeks | ≈ 5 % (IC); 1–2 % deployable | Roth | tens | +1 |
| 7 | **M-1** merger arbitrage | per-event | ≈ 2–3k deals | ≈ 60 % vs bills; **≈ 3 % decision-relevant** | taxable stack (box) | $300–400 on a $10k stack | +1; needs $39/mo data |
| 8 | **C-1** pooled event rule | combination design | sum of parts | depends on parts | — | — | replaces component trials |
| 9 | **E-3** real-fill options cost record | forward record | 50–100 fills | n/a (cost measurement) | Roth / taxable | — | 0 |
| 10 | **P-1** Kalshi taker probe (T-403) | per-event | thousands of contracts | ≈ 2 % (its own record) | neither wrapper | per T-403 | per T-403 |

---

## 7. Pre-registration sketches for the top 3 (DRAFTS; nothing frozen; nothing run)

### 7.1 E-1: does the options market misprice earnings uncertainty relative to the firm's own history?
- **Hypothesis (primary H1b):** among US-listed stocks with an earnings announcement and an expiry ≤ 7 calendar days after it, the straddle return is higher in the lowest tercile of q than in the highest. q = (ATM straddle price ÷ spot) ÷ the median of the firm's previous 8 absolute earnings-window returns, sorted within each announcement week. The bottom-minus-top mean must have **t ≥ 2.96, clustered by announcement week**.
- **Secondary (gated on H1b):** H1c, bottom-tercile mean return net of the pre-frozen cost schedule > 0 at t ≥ 2.96. H1a, the unconditional mean, is descriptive only.
- **Design:**
  - **Timing.** From the 8-K item 2.02 acceptance time: before 09:30 ET, entry at the prior day's close; after 16:00, entry that day's close. Intraday filings are excluded. Misclassification is checked against the 117-name calendars before the freeze.
  - **Entry.** Each leg's 1-minute VWAP over 15:30–16:00. Each leg needs ≥ 5 prints in that window; the filter is ex-ante, which answers the DJKMW point.
  - **Payoff.** Intrinsic value at expiry from the underlying's close; no option exit price is needed.
  - **Exclusions.** Adjusted (non-standard) contracts.
- **Data:** Alpaca bars and trades 2024-01 → 2026-10 (free); underlying daily closes; the 8-K panel refreshed by the director's SEC-host mechanism.
- **Pre-freeze census (counts and the conditioning variable only, no straddle returns):** event counts by season; sd(log q) by quarter; the share of events per announcement week; the intra-week correlation of |realized move| (from stock data outside the test window) to fix the design effect.
- **Falsifier:** H1b t < 2.96 **closes the earnings-options family in every form** (G1, G2, G4, F-7) for both wrappers until a quote-based source (OptionMetrics) exists. A wrong-sign result closes it too. A pass licenses only E-3, the real-fill cost record.
- **Trials:** +1 (H1b); +1 more if H1c is gated.

### 7.2 O-1: does a defined-risk short-index-volatility overlay, stacked on 100 % equity without displacing it, raise after-tax terminal wealth?
- **Hypothesis:** r_stack = r_equity + k · (r_CNDR − r_bill − c), with k = 0.10 (the overlay's requirement as a fraction of equity, frozen ex-ante for a bounded worst month). Pass needs Δ log terminal wealth vs 100 % equity with a **block-bootstrap ci_low > 0** and a point t ≥ 2.96, 1986-06 → 2026-10, after the §1256 tax of the T-409 engine.
- **Necessary conditions:** the 2010-01 → 2026-10 point estimate is > 0, the decay check; the stack's worst cohort is ≥ 0.5 × S&P terminal (the owner's bound).
- **Design:**
  - CNDR is frozen as the overlay, being the most delta-neutral defined-risk index in the free set; BFLY and PUT are descriptive only.
  - c is a cost schedule frozen from **measured real XSP quotes**, one month of OPRA or Schwab screens, before the freeze. It has two levels; the higher one gates.
  - A cash buffer equal to the worst historical overlay month is held in bills and charged as a drag.
  - Block bootstrap per `[NN-SHARPE-CI]` (Politis–White block length).
- **Data:** Cboe CNDR/BFLY/PUT CSVs (free); the T-306 equity and cash series; the T-409 tax engine.
- **Falsifier:** ci_low ≤ 0, point t < 2.96, or a negative 2010+ point **closes premium selling for this owner in every wrapper**. Together with T-279 and T-261 that is the whole family.
- **Trials:** +1.
- **Caveat stated up front:** a pass on a gross, VWAP-filled index is an upper bound for retail. A pass licenses a small real-money record (E-3), never a full-size overlay.

### 7.3 E-2: do S&P 500 stocks earn a premium in their predicted announcement week, net of cost?
- **Hypothesis:**
  - Each week t, the basket = PIT S&P 500 members whose *predicted* announcement date falls in [t+1, t+5] (prior year's same-quarter date + 364 days), equal weight, entered at the close of t and exited at the close of t+5.
  - The weekly basket-minus-SPY return net of 5 bp per side has mean > 0 with **t_HAC ≥ 2.96** and block-bootstrap ci_low > 0, 2004-08 → 2026-06.
  - Weeks with < 10 predicted announcers hold SPY and contribute zero.
- **Design:** raw Δ vs SPY is the decision quantity. Beta-adjusted and DGTW-style versions are descriptive.
- **Pre-freeze census:** the count of predicted announcers per week; the share of predicted dates that miss by more than 5 days. That census is outcome-free.
- **Data:** the 8-K item 2.02 dates (on disk); the PIT membership; canonical prices. The 386-name survivorship gap is reported and biases toward finding a premium; the direction is stated.
- **Falsifier:** t_HAC < 2.96 or ci_low ≤ 0 closes the announcement premium on large caps. A pass licenses a Roth paper book with real taker fills at the close.
- **Trials:** +1.

---

## 8. Where the record contradicts itself

1. **T-174 (VRP overlay) and T-122 (the VRP factor) carry `refuted` in `docs/State/TASK_LEDGER.md`**, but RR-1 §5 lists both among the 29 controller-produced verdicts demoted to UNTESTED (`referee_repair_proposal_RR-1_2026_09_30.md:478-479`). The same holds for T-129 (BAB), T-144 (Form 4) and T-145 (13F). The salvage audit classes the VRP overlay as "A on role" and the ledger row says "VRP joins … the closed pile". Under `[NN-SUPERSEDED]` these are not current evidence. The family stays closed by *class* (regime timing), not by these numbers.
2. **The objective moved under the options verdicts.** T-184 (2026-06-17) ranked options low because short variance is "structurally NEGATIVE skew", under the tail-capture mandate. The owner's later directives are terminal wealth, will not sell, and accepts 0.5 × S&P. T-279 judged the PUT against the **trend sleeve**, which is now a shelved regime option; the deploy candidate is 85/15. Neither verdict speaks to premium added to the current core. That is a baseline change in the spirit of `[NN-SUBSTRATE-REVERIFY]`.
3. **Route research G1/G5 and program F-5/F-7** specify forward books marked "from the >15-min OPRA history endpoint" with "cost = paid spread from the OPRA history". Alpaca serves **no historical option quotes**: HTTP 404 today, and its API index lists none. Those specs would have marked at trade prints and invented the spread.
4. **`data/macro/VIX*.parquet` end 2026-06/07**, about five months stale, while Cboe's CDN is current. Any VIX-term consumer reading the local files is reading a frozen series.
5. **Granularity has worsened.** T-279 sized one XSP at ≈ $60k (SPX ~6,000). Today it is ≈ $71.8k.
6. **Minor items:**
   - Alpaca's docs say "since February 2024"; a Feb-2024 contract returned bars from 2024-01-18.
   - The 2026-08-26 positioning prereg says 24,063 symbols on a date are "≈ one observation". That is right for time-series tests and overstated for cross-sectional tests, where the market factor differences out.
   - The fresh-eyes stop list ("≤26-year long-only backtests ≈ 3 %") is right for IR ≈ 0.2 tilts. It does not cover per-event baskets whose plausible IR is higher; E-2 is that case.
7. **CURRENT_STATE's wrapper facts** describe a Roth at Level 2. Alpaca's docs now also describe index options (SPX/XSP) on the Broker API. Whether a retail or IRA account can trade them is unverified, so nothing here relies on it.

---

## 9. Method and provenance

- **Read:**
  - the fresh-eyes and salvage audits (2026-11-14);
  - TASK_LEDGER rows T-108/110/112, T-122, T-174, T-184, T-211/215/216, T-241, T-248, T-251, T-261, T-274, T-279, T-289, T-291, T-306, T-315/T-399, T-336, T-380, T-382, T-385, T-396, T-398, T-409;
  - `conditional_shelf.md` #10, #14, #15;
  - CURRENT_STATE;
  - the alpha-frontier program and route research (Routes D, G, H);
  - the T-403, T-407, T-408 and T-409 rev. 2 notes;
  - the T-342 DRAFT; the positioning DRAFT; RR-1 §5; the B-1 verdict's exclusions.
- **Probes (availability only; generic UA `ArchonDEX-research/1.0`; no personal details):**
  - Alpaca: 8 GETs with the paper key, never printed. Option bars, trades, quotes, snapshots and the chain, on expired and live contracts. Counts and field names only.
  - The Alpaca docs pages listed in §4.
  - Cboe: 32 CDN CSVs, header and last row only.
  - The Cboe put/call archive (5 files); SqueezeMetrics (1 CSV); FINRA CNMS (3 dates); IRS Pub 550; Crossref metadata and abstracts for the citations; doi.org resolution (all 302).
  - Local `data/` spans, read-only.
- **No return of any candidate was computed. No option price was joined to an outcome.** Scratch files are under the session scratchpad (`…/scratchpad/t410/`), not the repo.
- **Not checked:** SEC hosts (UA policy); Schwab approval levels (the pages did not render them); OptionMetrics access at the owner's school.

## 10. References

Read means the abstract or text, via Crossref or the publisher. "Title verified" means existence only; its content is taken from the record. All DOIs resolved on 2026-11-20.

- Coval, Shumway (2001), *Expected Option Returns*, JF. doi:10.1111/0022-1082.00352 (abstract read)
- Cremers, Weinbaum (2010), *Deviations from Put-Call Parity and Stock Return Predictability*, JFQA. doi:10.1017/s002210901000013x (abstract read)
- Dew-Becker, Giglio, Le, Rodriguez (2014), *The Price of Variance Risk*, SSRN. doi:10.2139/ssrn.2471079 (abstract read; JFE 2017 version not read)
- Dubinsky, Johannes, Kaeck, Seeger (2018 online; RFS), *Option Pricing of Earnings Announcement Risks*, RFS. doi:10.1093/rfs/hhy060 (title verified; the 2004 WP abstract, doi:10.2139/ssrn.600593, read)
- Gao, Xing, Zhang (2018), *Anticipating Uncertainty: Straddles around Earnings Announcements*, JFQA. doi:10.1017/s0022109018000285 (abstract read)
- Goyal, Saretto (2009), *Cross-section of option returns and volatility*, JFE. doi:10.1016/j.jfineco.2009.01.001 (the 2006 WP abstract read)
- Israelov, Nielsen (2015), *Covered Calls Uncovered*, FAJ. doi:10.2469/faj.v71.n6.1 (the SSRN abstract read)
- Israelov (2018), *Pathetic Protection: The Elusive Benefits of Protective Puts*, JAI. doi:10.3905/jai.2018.1.066 (title verified)
- Johnson, So (2012), *The option to stock volume ratio and future returns*, JFE. doi:10.1016/j.jfineco.2012.05.008 (the SSRN abstract read)
- Jones, Shemesh (2018), *Option Mispricing around Nontrading Periods*, JF. doi:10.1111/jofi.12603 (abstract read)
- Kelly, Pástor, Veronesi (2016), *The Price of Political Uncertainty*, JF. doi:10.1111/jofi.12406 (abstract read)
- Lucca, Moench (2015), *The Pre-FOMC Announcement Drift*, JF. doi:10.1111/jofi.12196 (abstract read; context only, since T-291 closed the FOMC calendar family)
- Muravyev, Ni (2020), *Why do option returns change sign from day to night?*, JFE. doi:10.1016/j.jfineco.2018.12.006 (the SSRN abstract read)
- Muravyev, Pearson (2020), *Options Trading Costs Are Lower than You Think*, RFS. doi:10.1093/rfs/hhaa010 (abstract read)
- Savor, Wilson (2016), *Earnings Announcements and Systematic Risk*, JF. doi:10.1111/jofi.12361 (abstract read)
- Xing, Zhang, Zhao (2010), *What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?*, JFQA. doi:10.1017/s0022109010000220 (abstract read)
- Bollerslev, Tauchen, Zhou (2009), *Expected Stock Returns and Variance Risk Premia*, RFS. doi:10.1093/rfs/hhp008 (title verified; content per T-174)
- Duarte, Jones, Khorram, Mo, Wang (RFS 2026), *Too Good to Be True*: **not read**; cited only through `02_route_research.md:325-328`
- IRS Publication 550 (2025), *Investment Income and Expenses*, irs.gov/publications/p550 (read: §1256, the straddle rules, constructive sales)
- Alpaca docs, read 2026-11-20: the historical option data page; the market-data plans; Options Level 3 trading; index options (Broker API); `docs.alpaca.markets/us/llms.txt`
