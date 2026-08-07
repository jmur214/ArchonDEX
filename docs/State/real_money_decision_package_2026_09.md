# The Real-Money OPTION Package (renamed 2026-07-28 — EVIDENCE-triggered, no date exists)

> **TIMELINE POSTURE (user, 2026-07-28, supersedes all prior "September decision" framing):** the user is
> NOT planning to move real money on any date — "I am not nearly confident in its ability. I will most
> likely paper trade for some time just to assess the machine's performance." The gate-d maturation (~late
> Sept) merely OPENS the option; the user takes it only when the LIVE PERFORMANCE RECORD has earned their
> confidence. Nothing in the system implies a deployment date. The user's activity = performance
> assessment → the weekly digest (T-329) is the primary touchpoint; the live-performance roster (3 real
> accounts + ~10 benchmarked books, the Max-LIVE-Performance plan) is the evidence engine.

> **Status: RESEARCH INPUTS COMPLETE (2026-07-27 — the T-311→T-260→T-314 arc closed). Ripens on gate-d ≥60 clean days (~late Sept).** This doc mutates in place as evidence lands. It exists so the decision
> is prepared, not scrambled. Ripens when: (1) account-1's exec gate-d reaches ≥60 clean days
> (~late Sept, post-outage restart), (2) ✅ C's tilt verdicts LANDED 2026-07-27 (menu updated), (3) ✅ the conditional-leverage family REPORTED (T-314 #1 null; arc complete). Owner: director + the user. The DECISION is the user's.

## The question, stated honestly
The fork-resolution rule: real capital moves when the system is paper-valid (execution gates) AND beats the
robo on the honest bar. Both conditions are on track: the robo bar is cleared on EVERY axis at 64yr (T-311),
and gate-d accrues. But the user's north star upgraded past the robo — **max terminal wealth vs buy-hold
SPY** — so the September question is NOT "robo → sleeve?" It is: **"the robo balance → WHAT allocation?"**

## The menu (evidence state as of 2026-07-27)
| option | evidence | standing |
|---|---|---|
| **1× buy-hold SPY in the Roth (machine-executed)** | Wealth-maximizing under ANY forward-ERP haircut (T-315); tax-free; the user's genuine won't-sell makes it executable at full strength | **The default.** Requires no belief beyond owning equity |
| **+ momentum satellite (LONG-ONLY, e.g. 80/20)** | T-320: the ONLY tilt whose CI excludes zero (both weights; regret −5.7%, $568/$10k, 6.1yr) — BUT the post-publication-decayed variant straddles | **The one evidenced satellite** — offered with the decay caveat stated; a modest weight, eyes open |
| **+ quality satellite** | T-320: gentlest regret (−4.1%), the only NON-decayed premium, smallest edge, CI straddles | Optional-gentle; no CI case; defensible as diversification of premium source |
| **+ small-value satellite** | T-318: 100% of 40yr windows win yet CI straddles; premium ⅔ decayed; decayed-regret −25.1% never recovers | Weak; only with the regret consciously accepted |
| **growth/tech tilt (QQQ-style)** | T-320: REFUTED — 7-10% of TR windows, 0% Nasdaq; QQQ relative high never regained since 2000 | **Excluded from the menu** |
| **+ conditional leverage** | T-314 #1: NULL — a frontier MOVE not an improvement (in-sample +0.143 Sortino collapsed to +0.051 OOS, straddling); #2 (rate) & #3 (drawdown) unrun, FORWARD-ONLY by contamination ruling | **Not on the menu now.** The forward-only members may earn a row in future years; tripwires live |
| **defensive sleeve** | A REGIME OPTION, not a default (beats buy-hold only in high-cash-rate eras: 11.9% vs 10.0% 1962-89; loses 4.6pp/yr in cheap-money eras). CI-significant Sortino, 9/9 crisis drawdown win. **The macro bet, stated (2026-08-06):** T-333 shows the regime swing is 80% timing (significantly value-destroying net of cash in the modern era, −5.16pp/yr) / 20% cash term — so deploying the sleeve = an implicit bet that cash yields stay elevated, AGAINST the 700-yr Rogoff-Rossi-Schmelzing declining-trend result. Take it knowingly or not at all | Advisor-shelf: deployable IF the rate regime shifts decisively (a future pre-registered trigger, not a timing signal) — and only WITH the stated macro bet accepted |
| **glide on an OWNED ERP belief** | T-315's fork option (b): lever modestly IF the user states and owns "forward premium ≈ history" | Available; a BELIEF, not evidence — must be labeled as such in the row |
| **stay in the robo** | Beaten on every axis (T-311) | Dominated; exit on the gate |
| **BTC 5% leg** | T-272 exploratory; forward clocks accruing (shadow + basis) | Not ripe for real money; promotion gates frozen |

## Mechanics pre-staged (so execution is days, not weeks)
- **Wrapper**: the Roth first (zero-tax; the sleeve/turnover question is moot for buy-hold). Taxable follows
  with the TLH stack: the wash-sale guard is BUILT (T-319, byte-neutral); harvest loop + 40yr sim queue on
  account opening.
- **Execution**: the paper machine's own order path (fractional, DAY, exec-gates) — the transfer plan is
  robo-liquidate → ACAT/cash → machine-executed buys under the advisor row. Wash-sale note: robo positions
  sold at a loss must be checked against machine buys (the guard covers this once both accounts are wired).
- **The advisor row**: to be written when the menu resolves; carries validation_ref per the T-280 spec.
- **What the user must decide** (no earlier than ripeness): the allocation from the menu + whether any
  belief-labeled component (glide/ERP) is included. The machine recommends; the user rules.

## The honest caveats that ride with the package
- The paper record validates EXECUTION, not returns (monthly-scale signals ≈ no significant return sample).
- Every menu row's backtest evidence is subject to the standing discipline: pre-registered, CI-gated,
  family-N accounted. Nothing enters the row from vibes — including the manager-intuitive options.
- The 2-week outage cost ~10 clean days; gate-d ripeness moved accordingly. The DLQ/alarm hardening is in.


## Account mapping (updated 2026-07-28, user question: "are all three accounts maximizing learning?")
- **Account 1** — the validated sleeve's execution record + the intelligence-pulse carrier (both analysts,
  the books, news, events, cost ledger). Fully employed.
- **Account 2** — REPURPOSED (T-327): the September deployment REHEARSAL — buy-hold SPY core + the momentum
  satellite + simulated Rule-B contributions. The real-money path gets proven before the decision, so
  September becomes "flip a switch on a running system." The damped-offense spec is retired from the
  account (its lesson banked: 2.2bps); the standby patch keeps it revivable if T-314-family forward
  evidence ever earns it back.
- **Account 3** — the AI trader (stage-2), readiness-gated (not calendar-gated, per the user: "don't jump
  into things" ≠ "wait two weeks").
