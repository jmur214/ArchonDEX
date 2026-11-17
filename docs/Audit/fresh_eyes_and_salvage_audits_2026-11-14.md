# The fresh-eyes audit and the salvage audit of the kill record (2026-11-14)

**Provenance.** On 2026-11-14 the director commissioned two read-only audits from independent subagents, neither seeded with the director's views:
- a fresh-eyes audit of "what are we missing";
- a salvage audit that sorted every refuted idea by why it died.

Neither audit ran anything or edited any file. Their reports existed only in the director's session transcript. They are preserved here **verbatim** (2026-11-17), so that the memory notes and ledger rows that cite them point at a file. This is a point-in-time document per `[NN-AUDITS-NOT-CURRENT]`. Current truth is `docs/State/CURRENT_STATE.md`.

## Status of their recommendations at 2026-11-17 (director)

Closed or done:

| Recommendation | Status |
|---|---|
| Odd-lot tenders (fresh-eyes C; salvage test 1) | **CLOSED without running** (T-395): no broker offers an election API, and Alpaca charges $100 per election. |
| Lazy Prices negative screen (salvage test 2) | **CLOSED permanently** (T-383, T-265 arm, 2026-11-17): H_OOS changers minus universe was +0.49 %/yr, t +0.50, the wrong sign. Its independent review is pending. |
| Lifecycle leverage (fresh-eyes B; salvage item 3) | **Design note done** (T-396): hold 1×. A belief decision, the owner's. |
| T-315's leverage refutation | **Corrected** (T-399): it carried a cost bug. |
| Stacked trend overlay (from B-5 arm iv) | **REFUTED** (T-398): +0.37 %/yr [−3.89, +4.17]. |
| Two-account household (T-400) | **Delivered.** |

Open:

| Recommendation | Status |
|---|---|
| Survivorship-free data (salvage test 3; T-374) | **Blocked on the owner's decision:** $39/month, or university access. |
| The real-money location (fresh-eyes A) | **The owner's decision.** The broker and venue facts are being gathered in T-402. |

---

# Part 1 — the fresh-eyes audit (verbatim)

## Fresh-eyes audit, 2026-11-14 (read-only; no network, so external facts are from memory and marked)

### 1. Why the output is two ETFs
It is reality multiplied by an instrument that cannot see realistic edges. The search itself is not the cause.

- **The bar.** At N_eff ≈ 371 (T-391 row, `/Users/jacksonmurphy/Dev/trading_machine-2/docs/State/TASK_LEDGER.md`), the expected best of 371 nulls is about 2.96σ. Required Sharpe is 2.96/√T: 1.32 at 5 years, 0.58 at 26, 0.39 at 58, 0.30 at 99. For 80% power, 0.75 at 26 years.
- **What that means for a satellite.** Information ratio does not change with satellite weight. A satellite with 10% tracking error needs 5.8–7.5%/yr of net alpha, sustained for 26 years.
- **Plausible edges.** Long-only, free-data retail alpha is 0–2%/yr (IR ≤ 0.2). A true 2% edge passes the corrected bar about 3% of the time, which is the false-positive rate. Even the plain `ci_low > 0` rule passes it only 17% of the time. Detecting IR 0.2 at 80% power needs about 196 years.
- **Consequence.** Every ≤26-year backtest was decided before it ran. 85/15 is the prior, not a finding; it fails the bar itself (+0.079, ci_low −0.066, `/Users/jacksonmurphy/Dev/trading_machine-2/docs/Audit/b9_combo_tilts_verdict_2026-11-11.md`).
- **Dollars.** A proven 1%/yr is $100/yr at $10k and $1,000/yr at $100k.

Three classes can ever clear this bar:
- deterministic or structural items, which need no test;
- priced premia with 60–99 years of history (the equity premium, t ≈ 3–4), where the open question is the owner's forward belief;
- capacity-capped niches where evidence accrues per event rather than per year, which is where a tiny account is an advantage.

### 2. Not explored, or dismissed too quickly

**A. The real money is waiting for evidence that cannot arrive.**
- `/Users/jacksonmurphy/Dev/trading_machine-2/docs/State/GOAL.md` puts real capital in a Schwab robo until the system is paper-validated. `/Users/jacksonmurphy/Dev/trading_machine-2/docs/State/real_money_decision_package_2026_09.md` calls the robo "Dominated", sets no date, and has the owner waiting on the live record.
- The same file says paper validates execution, not returns. The B-10 verdict puts the 3-year minimum detectable effect at about 4.4%/yr (`/Users/jacksonmurphy/Dev/trading_machine-2/docs/Audit/b10_gold_leg_verdict_2026-11-11.md`).
- Size: on $7k/yr contributions over 2000–26, buy-hold reached $929K against the robo proxy's $495K (`/Users/jacksonmurphy/Dev/trading_machine-2/docs/Audit/dividend_reconcile_verdict_t287_2026_07_07.md`). My conversion is about 4 pp/yr dollar-weighted; forward I would expect 1–2.5 pp. That is $100–400/yr at $10k and $1–4k/yr at $100k.
- It needs two manual trades a year and no fleet. I could not verify where the money sits today.

**B. Lifecycle leverage on a lifetime-wealth bankroll.** No doc mentions Ayres–Nalebuff or lifetime wealth.
- T-315 (`/Users/jacksonmurphy/Dev/trading_machine-2/docs/Audit/static_leverage_t315_2026_07_27.md`) treats the account as the bankroll: the haircut table is lump-sum, and the 1929 test is "$10k → $152".
- Its own contribution race has the 2×→1× glide at $86.5M against $35.0M, run only with no haircut. Its Kelly leverage is 2.20 / 1.49 / 1.13 across haircuts.
- This account is roughly 5–10% of the present value of future contributions, so even the −3% haircut implies more than 1× early.
- The untested cell is haircut × accumulation × de-levering on the account-to-lifetime-wealth ratio.
- My estimate: +2.7–4.7%/yr arithmetic per levered dollar after SSO costs, so $270–470/yr at $10k, about zero by $100–200k, and +$45–90k at the end (4–8%).
- The risks: the median can be worse than 1× under a haircut (the gain is in the mean), and the early account can lose 90%, which is $10–35k.
- It cannot be tested to significance, since 2× straddles on 58 years. It is a belief decision; holding 1× is also a belief. Cost: one day, no new data.

**C. Per-event special situations.**
- T-277 called odd-lot tenders "un-backtestable" and "$-small" (`/Users/jacksonmurphy/Dev/trading_machine-2/docs/Audit/special_situations_monitor_t277_2026_07_02.md`). Dollar-small is percent-large at $10k.
- The "running watcher" stopped on 2026-07-02: 244 rows, `forward_value` filled on none (`/Users/jacksonmurphy/Dev/trading_machine-2/data/research/special_situations/events.parquet`).
- An EDGAR event study is free. With a 3–8% per-event effect against about 8% σ, some 30 events give t of 2–5. This is the one class where the bar is reachable.
- Its 18 hits were mostly non-traded interval funds, so I do not know the tradeable count. My guess is 3–10 a year, worth $100–500/yr: 1–5% at $10k, 0.1–0.5% at $100k.
- Prior that it is real: 60%. Prior that it is worth at least $300/yr: 25%. Cost: about a week.

**D. Slim cases inside refuted work.**
- CEF: what survives T-379 is a days-horizon reversal that dies at 30 bps a side with 93%/month turnover. Passive limit orders flip that cost's sign. Hundreds of round trips a year make it forward-evaluable in about two years, but only with small real money, because paper fills at the quote. Prior 15%.
- Its other failure, like gold's, was displacement: the universe trails SPY by 3.4–5.8 pp. A stacked form on capital freed by a levered ETF does not look like the gating arm in the ledger. It is mostly leverage; prior under 10%.
- B-6's short-leg t of +2.23 has no use for a long-only ETF holder.

**E. Broker incentives.** There are zero mentions in `docs/`, and the broker is "undecided". From memory and unverified, some brokers pay 1–3% on IRA contributions or transfers: $70–210/yr now, $1–2k one-time at $100k. Those brokers lack APIs, which shows the value of automating a 6.4%-turnover book is about zero.

**F. Two memo questions unanswered since 08-27** (`/Users/jacksonmurphy/Dev/trading_machine-2/docs/State/advisor_surface.md`): how school is funded, and whether the health plan qualifies for an HSA (about $1k/yr, certain). If any borrowing at 7–9% is involved, avoiding it dominates everything here.

**G. Data on disk.** The 13F ownership panel, 8-K panel, Form 4 files and news are all panels of 26 years or less, so power is about the false-positive rate. B-2's event study already had the power (MDE 4.7%) and found 2.0%, t 0.20. I see nothing there.

**H. The fleet.** Its legitimate uses are mechanics (it caught the MTUM split) and per-event niches. It is not return evidence.

### Constraint relaxations, ranked by expected value

| # | Relax | Opens | Cost and base rate | EV |
|---|---|---|---|---|
| 1 | Decision rule and benchmark frame | A, B, E, F. Keep the bootstrap gate for alpha claims; decide allocation, vehicle and structure by expected log lifetime wealth under owner-stated beliefs with bounded loss | $0. Risk is self-deception, so pre-state the beliefs | Highest |
| 2 | "Years of history" becomes "events"; tiny account as the asset | C, and prediction markets. Kalshi and Polymarket are already archived (`docs/State/forward_plan.md:168`). A 2% per-bet edge is detectable in about 3,500 bets | A new venue is propose-first; ordinary income; outside the Roth. Most retail accounts lose and professional market-makers are present (memory). Prior of a durable bot edge about 10%; $500–3k/yr if real | Medium |
| 3 | Taxable futures account beside the Roth | Cheap leverage: T-315's "1.25× loses" is expense-ratio amortisation, and I compute break-even at about 3.3% with futures financing against 7.04%. Also portable alpha and a multi-asset trend stack | Needs $35–65k (`docs/Audit/taxable_wrapper_frontier_scope_t281_2026_07_02.md`). §1256 drag is near zero in 0–12% bracket years. Most retail futures accounts lose (memory). Stacked trend +1–3%/yr, prior about 35% | Zero now, medium in about five years |
| 4 | University data | CRSP from 1926 cuts the bar to IR 0.30 (T-374 is blocked on the owner) | Free. The licence is academic-use and I do not know whether this qualifies. Prior that something clears and survives decay: 5–10% | Low to medium |
| 5 | Paid data | Longer small-cap history | $299–630/yr is 3–6% of the account and cannot pay back below about $100k | Negative |
| 6 | Intraday | The bar is passable if Sharpe ≥ 1.3 over five years | Fewer than 1% of day traders are persistently profitable (Barber et al., memory); T+1 cash settlement. Prior ≤ 3% | Low |
| 7 | Shorts, crypto carry | Long-short equity (long side already null); basis at about cash + 0–5% | Borrow and custody tails; displaces equity | Low or negative |
| 8 | Non-market automation | I know of no agent-run income stream with a positive documented base rate | The dependable version is labour: $500/month of paid work is 60%/yr of the account. Bank bonuses (about $1–2k/yr, taxable) are semi-manual; an agent can track them, not open them | Unknown, or labour |

### 3. Stop
- **Further ≤26-year long-only backtests**: B-4, B-7, and the re-run of the 33 equity-book verdicts. Pass probability is about 3% whether or not the edge is real, and each raises N.
- **Substrate refinement beyond T-394**: v5 changed 3 of 575 files, and no pending decision turns on it.
- **Reading shadow or LLM books as return evidence.**
- **Three accounts plus cloud for a two-ETF book**: 12 fills cost 1.33 bps (T-386).

If the system is a skill-builder or hobby, keep it and label it consumption.

### 4. Top five
1. **Move the real money out of the robo into VOO or 85/15 now, manually**, decoupled from the fleet.
2. **Answer the two memo questions**, then take the deterministic dollars: HSA, broker incentive, contribution rate. An extra $1k/yr is worth about $200k at year 40, equivalent to roughly 0.6%/yr of alpha.
3. **Build the lifecycle-leverage decision table**; the owner states a forward equity-premium belief and owns the result.
4. **Run the EDGAR tender event study and restart the dead watcher**; then one paper probe on prediction markets.
5. **Apply the stop list**; revisit a futures account at $35k taxable, and the data-licence question at school.

**First:** item 1. It is the only item whose evidence the repo already accepts, and waiting costs more per year than any candidate in the queue could earn.

---

# Part 2 — the salvage audit of the kill record (verbatim)

Salvage audit of the kill record (read-only; nothing run, nothing edited)

Paths are under `/Users/jacksonmurphy/Dev/trading_machine-2/docs/`. `L##` = line in `State/TASK_LEDGER.md`. Classes and the tally are my classification of the record, by idea family. I read verdict tables for about 25 docs and ledger rows only for the rest.

**Bottom line:** nothing in the record is a hidden winner. The salvage is one dead forward clock, one data purchase that makes five kills decidable, and one leverage decision that no backtest can settle.

## 1. Every killed idea, by class

| Idea (task, ledger line) | Class |
|---|---|
| Spinoff edge (T-041b/c, L22-23) | C: "+0.000 contribution" through the controller; never event-studied |
| Vol-target (T-055c-h, L28-32); confidence gate (T-057/b, L33-34); no-trade band (T-098, L50); corr cap (T-107, L58) | C: controller-era, frozen-capital sizing (`State/health_check.md:95-97`) |
| Drawdown kill-switch (T-106, L59) | C: dead knob, never fired |
| Compression (T-117, L66); metalearner (T-149, L92); concentration (T-241); composition (T-211/215); foundry 0/35 (T-196, L143) | C: demoted UNTESTED |
| VRP in ensemble (T-122, L69) | C: allocator cancels uniform signals (`Sources/whole_project_gap_audit_2026_07_02.md:22`) |
| VRP overlay (T-174, L122); put-write (T-261 L181, T-279) | A on role; E on options level and account size |
| BAB (T-123/129, L72/76) | A: upper-bound zero on survivors |
| Overnight long-short (T-135 L80, T-157 L169) | E: gross real, killed by cost, shorts and size |
| 8-K (T-137, L82); Form 4 (T-144, L87); 13F (T-145, L91); small-cap insiders (T-381, L282) | A |
| HMM de-gross (T-118r, L115); sleeve sizer (T-178, L126); regime-gated overlay (T-220) | A |
| In-house spot sleeve (T-128r, L116) | C: engine scale-dependence |
| Industry momentum long-short (T-213, L160) | D: long-only form deliberately not run |
| Credit/VIX front-runner (T-233) | C: BAA−AAA proxy failed its own gate at corr 0.636 (T-336, L240) |
| Lazy Prices v1 (T-237) | C: invalid panel (`health_check.md:121`) |
| Lazy Prices rebuilt (T-383, L284) | B: MDE 0.10-0.11, point −0.03; window (d) not evaluable |
| Carry (T-247; T-263, L183) | T-247 C (split-only AGG, `health_check.md:285`); T-263 A as an ETF proxy; futures carry never tested |
| Small-cap momentum (T-249; T-381, L282) | C (Sharpe 4.58× inflated), then B (MDE 0.43), point negative |
| FOMC even-week (T-250/268/291, L188/194) | A |
| Barbell (T-251); HRP (T-248) | B on the confidence-interval rule; gives back wealth |
| Vol-target into sleeve (T-262, L182); factor momentum (T-254); breadth and VIX-term tilts (T-273/274); asymmetric exits (T-269, L189) | A |
| Managed-futures ETF satellite (T-253) | D: pays only in 2022-type bears; no validated switch |
| Off-leg (T-259/266, L179/186) | B+C |
| Small-cap PEAD (T-265, L185) | A: 24,990 events, spread t ≈ 0.4 |
| CEF discount (T-267 L187, T-379 L280) | E: real before 2011; killed by cost, day-2 decay, long-only |
| Intraday (T-270, L190) | A gross |
| Index deletions (T-271, L191) | B |
| News interactions (T-289, L193); return stack (T-296, L221); intl (T-313); adaptation rule (T-314, L225) | A |
| Leverage vehicle (T-294 L198, T-294b L200); gated offense (T-298/312, L201/205); static leverage (T-315, L206) | E, plus the confidence-interval rule |
| Small-value, quality (T-318/320, L222-223); multi-factor tilts (T-380, L281) | B: underpowered by construction |
| Growth tilt (T-320) | A |
| Levered stacks (T-382, L283) | A overall; D on correlation regime |
| Gold (T-385, L286) | A on wealth |
| Execution timing (T-386 L287, T-341) | B, but the ceiling is ~1 bp/yr |
| Decile re-evaluation (T-365, L266) | C: drip defect, re-verify required (`health_check.md:25-31`) |
| Trend sleeve vs buy-hold (T-311 L202, T-333 L236) | F: real drawdown insurance, costs wealth |

## 2. The trap
- T-391 (L292) puts effective N at about 371.
- No slice suggested by a table can be certified by another backtest on the same data.

## 3. B–F items, ranked by expected value

**Group 1: ex-ante theory, and either existing evidence or never validly measured**

1. **Odd-lot tenders (T-277), class E/F.**
   - Theory: holders of under 100 shares are contractually exempt from proration, and the 99-share cap keeps institutions out. A $10k account is the advantaged party.
   - Evidence: none. `Audit/special_situations_monitor_t277_2026_07_02.md` says "status: running", but `data/research/special_situations/events.jsonl` has 244 rows, last file_date 2026-07-02, 0 `forward_value` filled, and nothing in `paper_trader/` references it. The clock has not ticked since day one on local disk; S3 was not checked.
   - Size: not established. My arithmetic, not the record's: 99 shares × $20-60 × 3-8% ≈ $60-475 per listed deal. Listed deals per year are unknown (18 odd-lot filings in 90 days, some non-traded funds).
   - Honest prior of net-positive: 35%. Forward-only, consumes no backtest N.

2. **Survivorship-free prices (T-374, L275), a relaxed constraint and not a strategy.**
   - Sharadar is $39/month; CRSP is free if university access applies.
   - It makes five kills decidable: T-365, T-381 (9 years, MDE 0.43), T-383 window (d), T-271 (128 events of 752 deletions, `Audit/index_deletion_t271_2026_07_02.md:26,70`), and the unrun B-4.
   - My prior that any satellite then passes is 10-15%. T-381's alpha vs IWM is −0.9%/yr (t −0.25) and PEAD is null, so expect confirmations.
   - Size if one passes: 25% × 2-3%/yr ≈ $50-75/yr.

3. **Leverage early in the contribution schedule (T-315/T-283b), class E plus the rule.**
   - `Audit/static_leverage_t315_2026_07_27.md:114-119,175`: the 2×→1× glide wins the contribution race, $86.5M vs $35.0M, but every interval straddles zero.
   - Lines 135-141: a −2% forward equity-premium haircut makes every arm lose. The 1929 path takes $10k to $152.
   - The 1.25× loss is the levered fund's 0.89% fee. The alternatives need size: LEAPS at $65k+, box spreads at $125k+ (line 198), futures at ~$100k+ (L200).
   - Theory: time diversification. $10k at 2× risks little against ~$200k of future contributions.
   - This is an equity-premium bet, not an edge. It cannot be certified (about 2.5 independent 40-year windows), and the verdict already says the owner must state and own the assumption.

4. **Quality tilt (T-320), class B.**
   - `Audit/tilt_decision_verdicts_t318_t320_2026_07_27.md`, T-320 table: decayed 80/20 interval [+0.003, +0.163]; smallest regret; the only premium that did not decay (+1.15 → +1.49%/yr).
   - Size: about +0.26%/yr, $26/yr at $10k.
   - The record contradicts itself: `Sources/alpha_frontier_review_2026_09_30/02_route_research.md:15` calls quality "dead for terminal wealth". Not established.
   - Reuse: the `quality_satellite` live book (T-328, L231).

5. **Spinoffs (T-041b), class C.**
   - 150 events (`Audit/spinoff_reversion_v1_gauntlet_2026_05_12.md:73`); never measured as an event study.
   - My MDE is about 10% against a plausible 3-8%, so underpowered. Its forward corpus is the same dead T-277 watcher.

**Group 2: suggested by the tables only; forward or out-of-sample confirmation, never a re-backtest**

6. **Lazy Prices negative screen (T-383).** `Audit/b6_lazy_prices_verdict_2026-11-12.md` §3.3: the short-leg t of +2.23 appears only under the non-gated adjacent pairing, on one 69-month window. It needs single names or shorts.
7. **Index deletions, 2020-25 era.** +7.2% (t 1.61) against −1.7% in 2016-19 (`index_deletion_t271:74-90`).
8. **Correlation-switched stack.** +3.5%/yr in negative-correlation years against −1.8 to −6.4, classified ex post (`Audit/b5_levered_diversified_verdict_2026-11-11.md:285-332`).
9. **Off-leg.** Its hard-gate failure was a cash-basis artifact (`State/conditional_shelf.md:404-418`). It only matters if the sleeve is held, and the sleeve loses on wealth.
10. **HY spread on the real series.** Recovered by T-336; a timing input, and T-333 shows timing costs this investor.

## 4. Which constraint killed what (about 60 families, primary cause)

| Constraint | Families | Which |
|---|---|---|
| Defective instrument or referee | ~17 | section 1 class C |
| True null | ~26 | section 1 class A |
| "Beat SPY with a positive bootstrap lower bound", despite a positive point estimate | ~10 | T-380, small-value, quality, off-leg, damped offense, glide/2×, barbell, deletions, BTC, CEF satellite |
| Free-data limit | 4 primary, ~5 co-cause | T-374, T-383(d), T-313, T-233; plus T-365, T-381, T-271, CEF, BAB |
| Cost | 5 | overnight, CEF at 30 bps, 1.25× fee, levered-fund leak, execution timing |
| Roth wrapper as sole killer | 3 tested, ~4 never dispatched | futures vehicle, overnight shorts, Lazy Prices short leg; crypto basis, futures carry, dispersion, box financing |
| Account size | 3 | put-write tier, LEAPS/box/futures granularity, integer rounding |
| Taxable relaxation dies on tax | 3 | T-294b, T-141, overnight taxable arm |
| Daily bars | 2 | CEF, overnight |

- **The confidence-interval rule is the largest non-evidence killer.** A 15-25% satellite with 2-4%/yr tracking error cannot show +0.5%/yr at 80% power in under about 280 years (my arithmetic). The rule is right for mined signals, but it can never pass a small published premium.
- **"The Roth wrapper retires half the alpha map" (`State/CURRENT_STATE.md:184`) is not supported.** Where blocked forms were measured anyway, they died on evidence:
  - put-write (T-261/279);
  - VRP overlay (T-174);
  - long-short sector momentum (Sharpe 0.057);
  - the long-short momentum factor (regret −37.6%, worse than long-only);
  - levered stacks at 0 bp financing (ci_low −1.41%/yr);
  - taxable futures (§1256 takes the 1.81%/yr).
- What the wrapper alone blocks: the futures vehicle (+0.86 to +1.81%/yr on a config that itself straddles), single-name shorts, crypto basis and futures carry. The last two were never tested here, and their evidence is external only.
- The Roth's zero tax is what keeps turnover alive: the book in taxable is −13.34% after tax (T-141, L85).
- "Any Roth ⇒ no futures" rests on an assumed Alpaca IRA with the broker undecided. I believe some brokers allow futures in IRAs; I did not verify that.

**With constraints relaxed** (automatable; all need more than $10k)
- Overnight long-short in a margin account: about 340 names, auction cost at or below 0.5 bp a side, then 35% short-term tax.
- Futures for the gated config: about $100k.
- CEF long cheap quintile against a short universe hedge: post-2011 t 1.5, fails at 30 bps.

## 5. Stay dead
- Class A in section 1.
- Execution and contribution timing (ceiling about 1 bp/yr, `Audit/overnight_exec_timing_prereg_t341_2026_08_15.md:22-24`).
- CEF long-only.
- Growth tilt.
- Regime-timing of anything (three nulls, and T-333 at −5.16pp/yr).
- Combination grids (9 of 9 null, `conditional_shelf.md:502-510`).

## 6. Reuse without a new backtest
- The `quality_satellite`, `damped_offense_t298`, BTC and DBMF forward books.
- The paper fleet's auction fill journal, to measure the overnight cost assumption.
- The pending T-265 arm of T-383.
- The T-315 and T-283b tables, for the leverage decision.

## 7. First three tests
1. **Revive T-277 as a forward odd-lot log.** Listed securities only, at most 99 shares, enter at the next close when price is below tender price minus costs. Falsified if, after 20 resolved events, mean net dollars per event ≤ 0, or more than 25% are cancelled or prorated, or there are fewer than 4 listed deals a year.
2. **Negative screen, out of sample.** Before the T-265 arm's returns are read, freeze "adjacent-10-Q changers underperform the universe, t_HAC ≥ 2". Wrong sign or t < 2 closes it permanently. A pass earns only a 24-month paper book.
3. **One month of survivorship-free data.** One pre-registered family: small-cap 12-1 momentum alpha vs IWM, and deletion CAR on all 752 events. t_HAC < 2 on 25 years closes the small-cap price niche for good.

The leverage glide is not a test. It is a decision that needs the owner's stated forward equity-premium assumption.
