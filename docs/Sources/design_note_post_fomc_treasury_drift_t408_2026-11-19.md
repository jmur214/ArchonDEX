---
task_id: T-408
title: Post-FOMC announcement drift in Treasury yields (Brooks, Katz & Lustig) as a rule for this book's bond sleeve — supersession, free-data census, per-event power, and whether any form clears the bar
date: 2026-11-19
type: PRE-RUN DESIGN NOTE (the paper read in full; public Fed, SF Fed, NBER and FRED sources; read-only counts of the repo's calendar and price files)
status: PROPOSAL — recommendation CLOSE. Nothing measured. No yield change after any announcement and no rule return was computed. No DRAFT prereg is attached (the pass probability of every form that could license a trade is hopeless, §5). No trial spent.
follows: T-407 §6 item 4 (docs/Sources/design_note_prediction_market_information_t407_2026-11-19.md)
---

# T-408: can post-FOMC Treasury drift give this book's bond sleeve a rule?

## 0. The answer

**No. Close it without spending a trial.**

The effect is real in its paper, and every input is free. But the effect runs on the size of the Fed's *surprise* when it changes rates. Since the Fed began announcing its moves in advance, that surprise has shrunk by a factor of three to four. At today's surprise sizes, no test the free history allows can see the effect. And if it were fully real, it would earn this book about **5 to 14 basis points a year** (0.05–0.14 %), which is $0.50–$1.40 a year on $10k.

The version that needs no surprise data ("after a hike, shorten the bond sleeve; after a cut, lengthen it") is rate-cycle timing. That is the stay-dead list's "regime timing of anything".

In plain terms:

- **What the paper found** (1989–2008, in-sample):
  - after a Fed rate *change*, a 10 bp surprise keeps pushing the 10-year Treasury yield the same way for about 50 trading days, about 18–19 bp beyond the announcement day;
  - its April 2019 revision says the drift comes almost entirely from *hawkish* surprises;
  - the proposed cause: bond-fund investors sell after hikes, and the market absorbs that supply slowly.
- **What changed.** On rate-change days the typical surprise was 5–8 bp in 1994–2008. Since 2015 it is 1–2 bp (§3.2). The drift scales with the surprise, so it shrank by the same factor.
- **The arithmetic.**
  - After the paper's sample (April 2018 onward) there are 24 rate changes at scheduled meetings. 17 have a free surprise measure, of which 6 are hawkish.
  - Pass probability at the project's bar (z ≈ 2.96): **0.5 %** for a rule on every change, **1.2 %** for "exit duration after hawkish surprises". Even at a single-trial bar (z 1.645) it is 11–18 %.
  - 80 % power at the bar would need **170 to 2,500 events**. At one to three a year, that is 165 to 900 years.
- **The one test with real power is a replication.** It would use 1994–2026 and pass about 41 % of the time at the bar, but 97 % of its statistical weight is the paper's own 1994–2008 events (§5.3). A pass would confirm the paper. It could not license a trade today.
- **Not tested here before.** T-250, T-268 and T-291 tested an *equity* FOMC calendar cycle. T-247 and T-263 tested curve-slope timing of AGG, and T-259 and T-266 a trend-gated IEF leg. None tested post-FOMC bond drift. But the surprise-free form of this idea falls into those dead families (§1).

**My priors** (stated before any outcome was read; none was):

| Claim | Prior |
|---|---|
| The drift mechanism was real in the 1989–2008 data | ≈ 75 % |
| It still operates today, per basis point of surprise | ≈ 40 % |
| A rule built on it earns > 0.1 %/yr for this book, net | ≤ 5 % |
| Any form passes the project's bar on the free history | ≤ 1 % |

Behind the first prior: in-sample t ≈ 3.3, a documented flow mechanism and foreign replications in the same paper. Against it: an unrefereed NBER working paper, partly funded by AQR (disclosed), whose asymmetric headline was added in a later revision.

---

## 1. Supersession check — was this, or something that subsumes it, already tested?

**Method.**
- Ledger rows of `docs/State/TASK_LEDGER.md` for T-250, T-268, T-291, T-233, T-247, T-259, T-263, T-266, T-290, T-295 and T-333.
- `docs/State/conditional_shelf.md` entries 6, 9 and 10.
- The verdict docs `docs/Audit/calendar_flow_probe_t250_2026_06_26.md`, `evenweek_sleeve_t268_2026_07_02.md` and `event_interaction_verdict_t291_2026_07_07.md`.
- A grep of `docs/` for "post-FOMC", "announcement drift", "Lustig", "FOMC", "duration", "TLT" and "IEF".

| Prior work | What it tested | Verdict | Does it subsume T-408? |
|---|---|---|---|
| T-250 (2026-06-26) | Equity calendar effects on SPY: the FOMC even-week cycle (Cieslak–Morse–Vissing-Jorgensen) and turn-of-month. **Pre-FOMC drift was skipped** ("decayed post-2015") | Effect present; not a standalone robo-beater | No. Equity, and a calendar cycle, not a rate decision |
| T-268 (2026-07-02) | Even-week × the trend sleeve's SPY leg | H0, refuted | No |
| T-291 (2026-07-07) | Even-week × FOMC-week interaction | H0. Family-N = 3 per T-293 | No. Same equity calendar family |
| T-247 / T-263 (2026-07-02) | AGG curve-slope (carry) timing; then multi-asset carry over 21 years | "BETA": α t_hac 0.815 / 1.08, net of a duration factor | Partly. It is bond-duration *timing* on a slow state variable. Dead |
| T-259 / T-266 (2026-07-02) | A momentum off-leg holding IEF; then a 63-day IEF trend gate | Refuted; off-leg family closed (N = 2) | Partly. Trend-timed duration is the family the paper says its drift *feeds* ("time-series momentum in Treasurys") |
| T-233 (2026-06-25) | FRED credit / VIX-term as a crisis front-runner | Killed: lags the price trend | No |
| T-333 (2026-07-29) | Attribution of the trend sleeve's timing | Timing value-destroying in the modern era (−5.16 pp/yr, ci excludes 0) | Indirectly. Shows timing a sleeve costs this investor |
| T-290 / T-295 (infra) | FOMC calendar module; a free Yahoo ZQ (fed funds futures) rate-path reconstruction from 2016-07 | Infra, 0 trials | Data only (§3.2) |
| T-407 §6.4 (2026-11-19) | Suggested this idea | — | — |

**Verdict: not tested, and the mechanism is genuinely different.** Every prior FOMC test here was an equity calendar effect. Every prior duration test used a slow state variable: curve slope, a 63-day trend, or the sleeve's trend ensemble. This paper conditions on a *Fed action plus its surprise*, at a fixed horizon, in bonds.

**Is a post-announcement drift rule "regime timing in disguise"?** It depends on which form, and the two forms come out opposite ways.

1. **Direction-only rule** ("after a hike, hold SGOV over IEF for ~50 trading days; after a cut, the reverse"). **Yes, this is regime timing in disguise.**
   - Rate changes come in runs. In 1994–2008, **43 of 59** changes were followed by another change in the same direction within 70 calendar days (about 49 trading days). Since April 2018, **16 of 26** were.
   - The hold therefore chains into a position held through the whole hiking or cutting cycle. The independent units are cycles, not meetings. There are **21 same-direction runs since 1994 and 7 since April 2018** (§3.5).
   - Its OOS window also cannot be tested blind. Every cycle in it is market history the designer remembers, for example the 2022 bond rout during hikes.
   - The paper itself pitches the drift as a *source* of bond time-series momentum. The trend sleeve's AGG leg already harvests that, and the IEF trend-gate family is closed (T-266).
   - Verdict: stays dead with "regime timing of anything".
2. **Surprise-signed rule** ("after a *hawkish surprise* at a rate change, hold cash over IEF for days 2–49; after a dovish one, hold or extend"). **No, this is not regime timing.**
   - The sign of the surprise on change days is close to serially independent. The paper's Table 1 Panel B reports AC(1) of 0.047 (full sample) and 0.077 (post-1994).
   - The horizon is fixed, and one event is one observation. It is a genuine per-event design.
   - It passes the stay-dead filter. It fails for a different reason: its signal has collapsed (§3.2), and with it the power (§5).

---

## 2. The paper (read in full)

**What was read on 2026-11-19:**
- the NBER landing page (abstract; issue date October 2018, revision date April 2019);
- all three PDFs: `w25127.rev0.pdf` (October 2018), `w25127.rev1.pdf` (November 2018) and the current `w25127.pdf` (April 2019, 86 pages including the appendix);
- the separate data appendix `NBER_appendix.pdf` (Tables A1–A17).

Crossref lists an SSRN version (2017, doi:10.2139/ssrn.3086941) and the NBER version, and **no journal publication**. It is an unrefereed working paper.

**Disclosures.** Two authors are at AQR Capital Management. The research is "partly funded by AQR". Lustig has an ongoing consulting relationship with AQR.

**Data and sample.**
- The surprise is Kuttner's (2001) one-day fed funds futures surprise.
- Core sample: **157 scheduled FOMC meetings, 1989-06-05 → 2008-10-29**, of which **59 had a target change** (53 after 1994).
- Long sample (appendix Tables A2–A3): 224 meetings to 2018-03-21, with **64** target changes.
- Yields: Treasury constant-maturity series.
- Fund returns: CRSP. Daily fund returns start in 1998.

**Surprise sizes in the paper** (Table 1):
- On target-change days: sd **9.59 bp**, mean |s| **6.46 bp**. Post-1994: sd 7.98, mean |s| 5.43.
- On scheduled meetings without a change: sd 4.30.

**The effect.** Yield response in bp per 1 bp surprise, scheduled meetings **with a target change**:

| Source | Maturity | Day 1 | Day 20 | Day 50 | Day 100 | R² day 50 |
|---|---|---|---|---|---|---|
| Table 3, Panel B (1989–2008) | 5-year | 0.33 | 0.93 | **2.37** | 1.14 | 0.18 |
| | 10-year | 0.16 | 0.76 | **2.04** | 0.71 | 0.16 |
| Table A3, Panel B (to 2018-03) | 5-year | 0.34 | 0.92 | **2.33** | 1.11 | 0.17 |
| | 7-year | 0.22 | 0.85 | **2.13** | 0.78 | 0.16 |
| | 10-year | 0.16 | 0.75 | **2.00** | 0.69 | 0.15 |
| 2019 revision, Table 4 Panel A (positive surprises only, inter-meeting changes excluded; the caption counts 35 positive surprises including inter-meeting) | 7-year | 0.22 | 2.20 | **4.81** | 2.73 | 0.29 |
| | 10-year | 0.13 | 2.10 | **4.32** | 2.28 | 0.27 |

What the paper reports alongside these numbers:

- **Meetings without a change show no drift** (Table 3 Panel A; 10-year day 50: −0.14).
- **Inter-meeting changes weaken it** "considerably" (Table 4 of the November 2018 version; A4 of April 2019). Of the 25–26 inter-meeting changes, only 2 were increases.
- **Asymmetry** (added in April 2019): "the post-announcement drift is almost entirely due to surprise rate increases … The impulse response for negative surprises is small and does not show drift." This split appeared only in the later revision, so it is a researcher choice made after the first circulation. I treat it as in-sample.
- **Partial reversal after day 50**, visible in the day-100 column.
- **Other markets.** Similar patterns in swaps, corporates and TIPS. Abroad, similar in Australia, the UK, Germany and Switzerland, but not Canada or New Zealand.
- **Mechanism** (Tables 8–9, A10). Government bond fund outflows build for months after hikes. Flows respond to the *actual change* rather than the surprise ("salience"). Arbitrage capital is slow.

**Tradeable returns in the paper** (Table 7 Panel B: fund returns *excluding the announcement day*, per 1 bp surprise, 50 days):
- intermediate government funds −10.76 bp (HAC se 3.95, t 2.72);
- all government funds −7.36 bp (se 2.73, t 2.70).

So **even the paper's own in-sample tradeable statistic sits below this project's bar of 2.96.**

The paper's strategy claim (§4.2) is in-sample and long-short, not net of any cost, and treats mutual funds as if they could be shorted. It reads: "73.6 bps … over 50 days … or 3.68 % per annum", with the maximum unconditional Sharpe rising "from 0.48 to 0.98".

**After 2008.** The paper's "robust to extending the sample" (Tables A2–A3) adds 5–6 hikes from 2015–2018 whose surprises were about 0–2 bp. In a surprise-weighted regression those events carry about **0.4 % of the weight** (§5.3), so the robustness claim is a statement about 1989–2008. The paper offers **no evidence about the regime since the Fed began telegraphing moves**. I found no independent replication: a Crossref title search returned only the two versions above, and I know of none from memory (UNCONFIRMED, §8).

**Effect in instrument terms (planning values):**
- **IEF** (7–10-year Treasuries; modified duration ≈ 7.3, from memory):
  - all target changes: drift from day 2 to day 50 = mean(1.91, 1.84) bp of yield × 7.3 ≈ **13.7 bp of price per 1 bp surprise**;
  - hawkish surprises only: mean(4.59, 4.19) × 7.3 ≈ **32 bp per bp**.
  - Cross-check: the paper's intermediate-fund figure is 10.76 bp per bp, for funds of roughly 5-year duration. Consistent.
- **A typical event in the paper's sample** (6.5 bp surprise) moves IEF about 0.9 % over the hold. **A typical event since 2018** (1.7 bp) moves it about 0.23 %.

**Instrument: IEF**, with SGOV as the cash leg (or BIL / the 3-month bill before SGOV's 2020 inception).
- **Signal-to-noise.** The paper's object is Treasuries. Its day-50 R² on change days (Table 3 Panel B) is highest at 1–7 years (0.17–0.22), 0.16 at 10 years and lowest at 20–30 years (0.12–0.14). TLT therefore has the worst signal-to-noise, at twice IEF's noise (§4).
- **Why not AGG.** AGG is about 45 % non-Treasury, including about a quarter agency MBS (from memory). The paper finds **no drift in mortgage funds** (Table A7: −2.25 bp per bp, insignificant), so AGG dilutes the effect. The book's actual AGG sleeve would capture perhaps 60–70 % of IEF's per-unit-duration effect (my estimate, unconfirmed).
- **History.** IEF has total-return history on disk from 2005-02 and is Roth-holdable.

---

## 3. Census of free data (verified 2026-11-19)

### 3.1 Fed funds target changes

**Sources:**
- the Fed's own open-market tables: `federalreserve.gov/monetarypolicy/openmarket.htm` (2003→, page last updated 2026-09-16) and `openmarket_archive.htm` (1990–2002);
- cross-checked against FRED **DFEDTAR** (1982-09-27 → 2008-12-15, discontinued) and **DFEDTARU / DFEDTARL** (2008-12-16 → 2026-11-19). The series ids and spans were verified via the FRED API's metadata endpoint;
- the scheduled / unscheduled flag from the Bauer–Swanson workbook (§3.2), which marks the first announcement after a scheduled meeting.

**Result:**
- **110 target changes since 1990** (52 hikes, 58 cuts). The Fed page and FRED agree exactly.
- **A 25 bp hike on 2026-09-16** (to 3.75–4.00 %), after three cuts in Sep–Dec 2025, confirmed in the raw page HTML.

| Era | Changes | At scheduled meetings (hikes / cuts) | Unscheduled | Scheduled meetings (repo calendar) |
|---|---|---|---|---|
| E1 1990–1993 (no explicit announcements) | 18 | 4 (0 / 4) | 14 | — |
| **E2 1994 → 2008-10 (the paper's core)** | 59 | **52 (30 / 22)** | 7 | 120 (43 % had a change) |
| E3 2008-11 → 2015-11 (zero lower bound) | 1 (2008-12-16, to the 0–¼ range) | 1 | 0 | 56 (≈ 7 years with no change) |
| E4 2015-12 → 2018-03 (the paper's extension) | 6 | 6 (6 / 0) | 0 | 19 |
| **E5 2018-04 → 2026-11 (after the paper; out of sample)** | 26 | **24 (15 / 9)** | 2 (2020-03-03, 2020-03-15) | 69 |

Further detail:
- A second no-change stretch ran from 2020-03-16 to 2022-03-15: two years, 15 scheduled meetings.
- The repo's FOMC calendar is `config/fomc_calendar.json` (read by `engines/data_manager/macro_calendar.py`): 265 decision dates, 1994-02-04 → 2026-12-09. For the defect found in it, see §7.1.

### 3.2 The surprise: the signal this paper actually uses

**Free source:** the SF Fed's Bauer–Swanson workbook, `frbsf.org/…/monetary-policy-surprises-data.xlsx`, update of 2024-10-11.
- Coverage: one row per FOMC announcement, **1988-02-04 → 2023-12-13**.
- Columns: the `Unscheduled` flag; 30-minute changes in FF1 / FF2 (current- and next-month fed funds futures, **from January 2010 only**); ED1–ED4 (Eurodollar, SOFR from 2023); Treasury futures; and the MPS principal component.
- Kuttner's own one-day series, which the paper used, is on his Williams College page and ends in 2008. I did not fetch it.

**Gaps:**
- **2024-09 → 2026-09 (7 changes): no free 30-minute series.**
- A one-day Kuttner surprise can be built from Yahoo's front-month `ZQ=F` (T-295, daily from 2016-07) for 6 of the 7. The exception is 2025-10-29, which falls in a month's last three days, where Kuttner's rule needs the next-month contract and Yahoo delists expired contracts.
- Kalshi `KXFED` ladders exist from 2021. But they are one-sided near decisions (T-407 §1.1), and the Diercks–Katz–Wright paper finds them "exact" the day before every meeting since 2022.

**Surprise size on scheduled change days** (bp). The signal is the Kuttner FF surprise from 2010 (FF2 in a month's last three days) and ED1 before 2010. Only the signal columns were read; no Treasury-futures response was used.

| Era | n with a value | sd | mean \|s\| | median \|s\| | Hawkish (s > 0) | Hawkish per year | Mean s when hawkish |
|---|---|---|---|---|---|---|---|
| E2 1994 → 2008-10 | 52 | **7.16** | 5.26 | 3.88 | 23 | 1.55 | 5.45 |
| E4 2015-12 → 2018-03 | 6 | **0.98** | 0.73 | 0.34 | 3 | 1.29 | 1.34 |
| E5 2018-04 → 2023-12 | 17 | **2.17** | 1.70 | 1.71 | 6 | 1.04 | 2.79 |

The E2 figure uses ED1, the current-quarter Eurodollar contract, which mixes in some path news. The paper's own Kuttner measure for 1994–2008 has sd 7.98 and mean |s| 5.43, so the two agree.

**The signal shrank by a factor of 3.3 (sd) to 3.1 (mean |s|)** between the paper's era and the out-of-sample era. At 1–2 bp, the sign of a surprise is only a few futures ticks from zero.

### 3.3 Yields

FRED **DGS2** (from 1976-06-01), **DGS5** and **DGS10** (from 1962-01-02), and **DGS3MO** (from 1981-09-01), all through 2026-11-18 (API metadata).

The project's local copies under `data/macro/` cover 2000-01 → 2026-04-23. The keyless `fredgraph.csv` endpoint timed out from this machine (§7.2), so I pulled observations through the FRED API with the project's key. The key is read from `.env` and never printed.

### 3.4 Bond ETF prices on disk (read-only)

| Instrument | On disk | Inception (from memory) |
|---|---|---|
| IEF, TLT, AGG, SHY | Total-return files `data/processed/tr_reconciled/*_1d.csv`: **2005-02-22 → 2026-05-22**. Stooq raw (`data/raw/stooq/`) starts 2005-02-25 | IEF and TLT 2002-07; AGG 2003-09 |
| BIL | Total-return file 2007-05-30 → | 2007-05 |
| SGOV | Stooq raw only, **2020-05-29 → 2026-05-22**; no total-return file | 2020-05 |
| AGG (split-only) | `data/processed/AGG_1d.csv` from 2003-09-29. **Must not stand in** for total return (T-407 §7.7) | — |

**Scheduled changes inside the total-return span** (2005-02 → 2026-05) that have a surprise value: **42**.

### 3.5 How the events chain (calendar only)

The question is how often a change is followed, within one ~49-trading-day hold, by another change in the same direction:
- E2: **43 of 59**;
- E4: 0 of 6;
- E5: **16 of 26**.

Grouping changes into same-direction runs (gaps ≤ 120 days) gives **22 runs since 1990, 21 since 1994, 7 touching 2018-04 or later**. Examples: hikes 2004-06 → 2006-06 (17 changes); cuts 2001-01 → 2001-12 (11); hikes 2022-03 → 2023-07 (11).

A direction rule's independent sample is these runs, not the 110 changes.

---

## 4. Planning values and method

**Noise.** These are unconditional 48-trading-day excess returns over the 3-month bill, taken over **all start days**, never event days (as in T-407 §4):

| Instrument | sd 2005–2026 (bp) | sd 2018-04 onward (bp) |
|---|---|---|
| IEF | **292** | **309** |
| AGG | 202 | 243 |
| TLT | 601 | 643 |
| SHY | 68 | 79 |

For yields, the 48-day change in DGS10 has sd 40.5 bp (1989-06 onward), 41.3 (1994–2008) and 39.7 (2018-04 onward). DGS10 × 7.3 ≈ 296 bp, which matches IEF.

**The bar.**
- z_c = **2.96**, the expected maximum of N_eff ≈ 372 nulls (`[NN-MBL]`); also reported at one trial, z 1.645.
- Power 80 %.
- Effect-size haircut: none (the paper's number), and 50 % (McLean–Pontiff publication decay, as in T-250).

**Formulas:**
- surprise regression, expected z = b · sd(s) · √N / σ;
- sign or hawkish-mean test, expected z = (b · E|s|) / σ · √N;
- pass probability = Φ(z − z_c);
- MDE on the slope = (z_c + 0.84) · σ / (sd(s) · √N).

**Sanity check: the arithmetic reproduces the paper.** On the paper's own sample: 1.84 bp/bp × 9.59 bp × √59 / 41 bp = **3.3**. The paper's 10-year day-50 coefficient has HAC t = 2.04 / 0.61 = **3.3** (OLS 2.8). The planning values are therefore consistent with the published result before they are applied anywhere else.

---

## 5. Power and pass probability

### 5.1 The candidate designs

A long-only Roth that holds IEF (or AGG) and SGOV can act in either of these ways:
- **Surprise rule:** tilt the bond sleeve between IEF and cash by the surprise. On days 2–49 after a scheduled change, hold cash after hawkish surprises and IEF (or more of it) after dovish ones.
- **Hawkish exit:** move the sleeve IEF → cash after hawkish surprises only. This is the 2019 revision's asymmetric finding and the natural long-only form.

Results for IEF, against IEF noise of 309 bp (out of sample) or 292 bp (full span):

| Design | N | Signal | z expected (paper b) | P at z 2.96 | P at z 1.645 | z (50 % haircut) | P at 2.96 | P at 1.645 | MDE |
|---|---|---|---|---|---|---|---|---|---|
| **A.** Out of sample 2018-04 → 2023-12, surprise regression | 17 | sd(s) 2.17 | 0.40 | **0.5 %** | 10.6 % | 0.20 | 0.3 % | 7.4 % | 132 bp/bp (**9.6×** the paper) |
| **B.** Out of sample 2018-04 → 2026-11, all 24 scheduled (needs ZQ surprises for 2024–26) | 24 | 2.17 | 0.47 | **0.6 %** | 12.0 % | 0.23 | 0.3 % | 7.9 % | 111 bp/bp (8.1×) |
| **H.** Out of sample hawkish exit, 2018-04 → 2023-12 | 6 | mean s⁺ 2.79 | 0.71 | **1.2 %** | 17.5 % | 0.35 | 0.5 % | 9.8 % | — |
| **C.** Full 1994 → 2026 (re-uses the paper's events) | 76 | sd(s) 6.69 | 2.73 | 41 % | 86 % | 1.37 | 5.5 % | 39 % | 19 bp/bp (1.4×) |
| **D.** Tradeable-ETF span only, 2005-02 → 2026 | 42 | sd(s) 6.52 | 1.98 | 16 % | 63 % | 0.99 | 2.4 % | 26 % | 26 bp/bp (1.9×) |
| **Direction rule** (no surprise) | 21 runs since 1994 / 7 since 2018-04 | — | — | — | — | — | — | — | needs a per-cycle effect/σ of **0.83 / 1.44** for 80 % power at z 2.96 |

### 5.2 Per event, and how long a forward record would take

| Form | Per-event effect | Effect/σ | Events for 80 % power at z 2.96 | Years at today's rate |
|---|---|---|---|---|
| Sign rule, all changes | 13.7 × 1.70 ≈ 23 bp | **0.075** | 2,546 | ≈ 900 (2.8 events/yr) |
| Same, 50 % haircut | 12 bp | 0.038 | 10,185 | ≈ 3,600 |
| **Hawkish exit** | 32 × 2.79 ≈ 90 bp | **0.29** | 172 | ≈ 165 (1.04 events/yr) |
| Hawkish exit, 50 % haircut | 45 bp | 0.145 | 689 | ≈ 660 |

The hawkish exit is the only form near the fresh-eyes audit's per-event class (effect/σ ≳ 0.3; `docs/Audit/fresh_eyes_and_salvage_audits_2026-11-14.md`). But it gets **about one event a year**, so no human-scale horizon reaches power. At the paper era's surprise sizes (5.45 bp) its ratio would be about 0.6, and power would need about 40 events, roughly 26 years. The project would need a Fed that surprises again for that to matter.

### 5.3 Why design C does not count

Design C is the only design that is not hopeless. Here is how its regression weight (Σs², demeaned) is distributed:
- **78 %** comes from the paper's 1994–2008 events;
- **19 %** from the single 2008-12-16 move to the zero bound (a 25.75 bp ED1 surprise);
- **0.4 %** from 2015–2018;
- **2.6 %** from 2018-04 onward.

It is a **replication of the published sample**, not evidence about the regime the book would trade in. A pass would add one trial and confirm a 2018 paper. A fail would most likely say "drift at 1–2 bp surprises is invisible", which is already known from the arithmetic. Neither outcome changes a decision.

### 5.4 Payoff ceiling, if fully real

The book's bond sleeve is 15 % (the 85/15 book).

| Form | Paper effect size | With 50 % haircut |
|---|---|---|
| Sign rule, all changes | 65 bp/yr on the sleeve = **9.7 bp/yr of the book** | 4.9 bp/yr |
| Hawkish exit | 93 bp/yr on the sleeve = **14 bp/yr of the book** | 7 bp/yr |

This is gross of the extra round trips (about 2–6 sleeve switches a year at roughly 1–2 bp each, which is small). On $10k, it is **$0.50–$1.40 a year**.

### 5.5 Trial count if anything ran

One trial per arm. The bar would move from z_c 2.962 to 2.963. **I recommend running none.**

---

## 6. Recommendation

1. **Close T-408 unrun.** The precedent is B-8 (closed by power analysis, N_trials 0).
   - **No DRAFT prereg is attached.** The brief asked for one only if the pass probability was not hopeless. For every design that could license a forward trade (A, B, H), it is ≤ 1.2 % at the bar and ≤ 17.5 % even at a single-trial bar.
   - The only design that is not hopeless (C, 41 %) replicates the paper's own data and cannot license anything.
2. **Scope of the closure** (in the spirit of the 2026-11-14 "no stone unturned" directive):
   - The **direction-only form joins "regime timing of anything"**: its independent units are rate cycles (21 since 1994).
   - The **surprise-signed and hawkish-exit forms are closed on power, not on evidence.** Nothing here says the mechanism is false. It says its signal is now too small to see or to matter for this book.
3. **Reopen only if both of these hold:**
   - the Fed's surprise on change days returns to about 5 bp or more on average, sustained over several years (not one shock, such as a single emergency move);
   - the book's bond sleeve grows enough that 1 % a year on it is worth a trial.

   Even then, the hawkish exit needs about 40 hawkish events. A forward clock would run for decades. Do not build a recorder for it.
4. **Keep the SF Fed workbook as a reference source** for any future FOMC work. It is free, it is maintained, and it gives the scheduled/unscheduled flag and 30-minute surprises back to 1988. It is a much better event key than the hand-compiled calendar (§7.1).

---

## 7. Incidental findings (for the director)

1. **`config/fomc_calendar.json` includes one non-meeting.**
   - It lists **1994-04-18** as a "decision date". The Fed's 1994 meeting page (`fomchistorical1994.htm`, read today) shows that date as an "April 18 Conference Call", not a meeting, and Bauer–Swanson flag it `Unscheduled = 1`.
   - It also lists **2020-03-15**, which Bauer–Swanson flag as unscheduled.
   - The file calls itself the source of truth, inherited from the T-250 script.
   - Effect on T-250, T-268 and T-291: one extra meeting shifts even-week labels for about four weeks in 1994. That is immaterial to those nulls, but it is a defect in a reference file. Not fixed here: it is outside this task, and `macro_calendar`'s byte-identity retrofit pins it.
2. **FRED's keyless CSV host timed out from this machine on 2026-11-19.**
   - `fred.stlouisfed.org/graph/fredgraph.csv` gave HTTP/2 stream resets and then 45–90 s timeouts, with both the generic and a Mozilla user agent. `api.stlouisfed.org` answered normally.
   - Anything that uses the keyless endpoint would fail today, for example `scripts/build_multidecade_substrate_t306.py`. The keyed path in `engines/data_manager/macro_data.py` is unaffected.
   - Cause unknown: a block or an outage.
3. **The local FRED copies under `data/macro/` end 2026-04-23** (fetched 2026-04-25/28). The total-return ETF files end 2026-05-22 (already noted in T-407).
4. **The FOMC hiked 25 bp on 2026-09-16, to 3.75–4.00 %**, after cutting three times in Sep–Dec 2025. Sources: the Fed open-market page (last updated 2026-09-16) and FRED DFEDTARU. I flag it because a "cutting cycle" framing from earlier in the year would now be out of date. Its surprise is not in any free 30-minute series.
5. **Bauer–Swanson FF1/FF2 start only in January 2010.** Any pre-2010 Kuttner-style work needs ED1 or Kuttner's own one-day series. In 2022, ED1 (path news, e.g. +9.25 bp on 2022-09-21) and FF1 (decision news, −3.6 bp the same day) disagree in sign. A rule keyed on the *path* surprise would be a new, unpublished hypothesis, not this paper's claim.

---

## 8. UNCONFIRMED items

1. **ETF inception dates** (IEF/TLT 2002-07, AGG 2003-09, BIL 2007-05, SGOV 2020-05) are from memory. Only the first rows on disk were verified.
2. **IEF modified duration ≈ 7.3 and AGG's ~25 % MBS share** are from memory, used as planning values.
3. **No independent replication of the paper exists.** The basis is a Crossref title search (two versions found, no journal) plus memory. I did not run a full literature search.
4. **"The 2022 bond rout" and similar market history** are cited from memory, only to argue that a cycle-level rule cannot be tested blind. No return was looked up.
5. **Whether the FOMC treated 2020-03-15 as its rescheduled regular meeting or as an unscheduled one.** I used the Bauer–Swanson flag (unscheduled). Either way, March 2020 is outside every design above.
6. **The paper's daily fund-return regressions** (Tables 5–7) state 59 events, but its text says daily fund returns start in 1998. The effective N of those tables may be smaller than stated. This does not affect the yield-based planning values used here.

---

## Sources (read 2026-11-19 unless marked)

1. Brooks, J., Katz, M. & Lustig, H., "Post-FOMC Announcement Drift in U.S. Bond Markets", NBER Working Paper 25127, October 2018, revised November 2018 and April 2019, doi:10.3386/w25127.
   - Landing page: https://www.nber.org/papers/w25127.
   - PDFs: https://www.nber.org/system/files/working_papers/w25127/w25127.pdf (April 2019, read in full); `…/revisions/w25127.rev0.pdf` and `…/revisions/w25127.rev1.pdf`.
   - Separate appendix: https://data.nber.org/data-appendix/w25127/NBER_appendix.pdf (Tables A1–A3 and A7–A10 read).
   - SSRN version doi:10.2139/ssrn.3086941 (Crossref metadata only).
2. Bauer, M. D. & Swanson, E. T., "A Reassessment of Monetary Policy Surprises and High-Frequency Identification", NBER Macroeconomics Annual (2023; cited so in the workbook; article https://www.journals.uchicago.edu/doi/10.1086/723574). Data: SF Fed, "Monetary Policy Surprises", https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/ ; workbook `monetary-policy-surprises-data.xlsx` (update 2024-10-11). Read: description sheet, FOMC (update 2023) signal columns `Date, Unscheduled, FF1, FF2, ED1, MPS`.
3. Board of Governors, "Open Market Operations" policy-rate tables, https://www.federalreserve.gov/monetarypolicy/openmarket.htm (last updated 2026-09-16) and https://www.federalreserve.gov/monetarypolicy/openmarket_archive.htm ; "FOMC Meetings, 1994", https://www.federalreserve.gov/monetarypolicy/fomchistorical1994.htm .
4. FRED (St. Louis Fed): series metadata and observations via `api.stlouisfed.org/fred/series` and `/series/observations` for DFEDTAR, DFEDTARU, DFEDTARL, DFF, DGS2, DGS5, DGS10 and DGS3MO.
5. Kuttner, K., "Monetary policy surprises and interest rates: Evidence from the Fed funds futures market", Journal of Monetary Economics 47(3), 2001 (as described in source 1; not re-read).
6. McLean, R. D. & Pontiff, J., "Does Academic Research Destroy Stock Return Predictability?", Journal of Finance 71(1), 2016 (the 50 % haircut convention; from memory, as used in T-250).
7. Diercks, A. M., Katz, J. D. & Wright, J. H., "Kalshi and the Rise of Macro Markets", FEDS 2026-010 (as summarised in T-407 §2; not re-read).
8. Crossref metadata API, title search for source 1.
9. [REPO]
   - `docs/State/TASK_LEDGER.md` (rows T-233, T-247, T-250, T-259, T-263, T-266, T-268, T-290, T-291, T-295, T-333, T-407, T-408);
   - `docs/State/conditional_shelf.md` §6, §9 and §10;
   - `docs/Audit/calendar_flow_probe_t250_2026_06_26.md`, `evenweek_sleeve_t268_2026_07_02.md`, `event_interaction_verdict_t291_2026_07_07.md`, `fresh_eyes_and_salvage_audits_2026-11-14.md`;
   - `docs/Sources/rate_path_history_t295.md`, `design_note_prediction_market_information_t407_2026-11-19.md`;
   - `config/fomc_calendar.json`;
   - `data/processed/tr_reconciled/{IEF,AGG,TLT,SHY,BIL}_1d.csv` and `data/raw/stooq/…/{agg,ief,tlt,shy,bil,sgov}.us.txt` (read-only: spans, and the unconditional all-days noise of §4).

**Reproducibility.** The probe scripts and raw downloads are in the session scratchpad (`…/scratchpad/t408/`), not the repo. They are `census.py`, `power.py` and `weight_share.py`, which read signal columns and unconditional noise only, plus `parse_openmarket.py` and `fred_meta.py`.
