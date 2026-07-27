# The Real-Money Decision Package — pre-staged 2026-07-27 for the ~September gate

> **Status: PRE-STAGED, not ripe.** This doc mutates in place as evidence lands. It exists so the decision
> is prepared, not scrambled. Ripens when: (1) account-1's exec gate-d reaches ≥60 clean days
> (~late Sept, post-outage restart), (2) C's tilt measurements (T-318/T-320) land, (3) the conditional-
> leverage family (T-260 → T-314) reports. Owner: director + the user. The DECISION is the user's.

## The question, stated honestly
The fork-resolution rule: real capital moves when the system is paper-valid (execution gates) AND beats the
robo on the honest bar. Both conditions are on track: the robo bar is cleared on EVERY axis at 64yr (T-311),
and gate-d accrues. But the user's north star upgraded past the robo — **max terminal wealth vs buy-hold
SPY** — so the September question is NOT "robo → sleeve?" It is: **"the robo balance → WHAT allocation?"**

## The menu (evidence state as of 2026-07-27)
| option | evidence | standing |
|---|---|---|
| **1× buy-hold SPY in the Roth (machine-executed)** | Wealth-maximizing under ANY forward-ERP haircut (T-315); tax-free; the user's genuine won't-sell makes it executable at full strength | **The default.** Requires no belief beyond owning equity |
| **+ factor tilt satellite (momentum / quality / small-value)** | T-318/T-320 RUNNING — regret-led verdicts pending | OPEN — populate on results |
| **+ conditional leverage (vol-stress / rate / drawdown-conditional)** | T-314 family: #1 frozen (runs after T-260), #2-#3 pre-stated | OPEN — the only honest leverage form left (static CLOSED: T-315; gated straddles: T-312) |
| **defensive sleeve** | A REGIME OPTION, not a default (beats buy-hold only in high-cash-rate eras: 11.9% vs 10.0% 1962-89; loses 4.6pp/yr in cheap-money eras). CI-significant Sortino, 9/9 crisis drawdown win | Advisor-shelf: deployable IF the rate regime shifts decisively (a future pre-registered trigger, not a timing signal) |
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
