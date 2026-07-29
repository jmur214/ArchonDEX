---
task_id: T-2026-07-30-330
title: The transition runbook — a TABLETOP rehearsal of the Schwab-side move no paper account can practise
date: 2026-07-30
author: Agent D
type: runbook (docs only; 0 N_trials; NO dates, NO trigger, NO recommendation to move)
status: TABLETOP — for review. Nothing here authorizes or schedules anything.
---

# The transition runbook (tabletop)

**What this is:** preparation, not prediction. **No date exists.** Nothing in this document recommends moving
money, and nothing in it is a trigger. If the user's confidence one day exercises the real-money OPTION, the
Schwab-side sequence is the one part that **cannot be rehearsed on Alpaca** — so it gets rehearsed on paper,
here, in advance and unhurried.

**What this is NOT:** a readiness claim. The machine's readiness is governed elsewhere (the advisor spec's
row status, the forward paper record, the pre-registered gates). This document assumes those are satisfied
and asks only: *mechanically, what happens, in what order, and what breaks?*

---

## ⚠️ HARD PRECONDITION — CORRECTED 2026-07-30 (T-330b): the guard is BUILT, not wired
**Correction to this document's first draft, which said the guard was "spec only — nothing built." That was
wrong.** The cross-account wash-sale guard was **BUILT and merged (T-319)**: the order-path guard module, the
FIFO cross-account tax-lot ledger, the equivalence config (`config/substantially_identical.json`), and the
61-day both-directions check all exist on main, with `tests/test_cross_account_wash_guard_t319.py` **passing
(11 tests — the dispatch said 13; the file contains 11)**.

**The accurate status is `BUILT — SEAM-WIRED — NOT ENFORCING`, and the distinction matters here:**
- `paper_trader/order_manager.py` carries the seam: `OrderManager(..., wash_guard=None)`, with
  `check_order(...)` called pre-submit and a fill-side hook. **The plumbing is real.**
- **But the parameter defaults to `None` and NO caller passes it** — verified across `paper_trader/`,
  `scripts/`, `live_trader/`, **including `scripts/run_paper_cloud_day.py` (the live pulse)**. So today the
  guard is inert in every running path: it would neither block nor log a collision.
- What remains is **(i) wiring it enforcing** (account 2 only — E/T-327 Act 2) and **(ii) exercising it**
  end-to-end (the drill's guard-refusal path). A guard that has never refused anything in a live path is
  not yet evidence — that is the T-289/T-295 "code-complete ≠ confirmed end-to-end" lesson applied here.

**Consequence for this runbook (branch marks unchanged, precondition text corrected):**
- **(a) Roth-only transition** — no taxable ⇒ no wash-sale exposure ⇒ the guard is not on the critical path.
  **Still the recommended first move on its own merits** (simpler, fewer irreversible failure modes), and the
  director endorses it independently of the guard's status.
- **(b) Any taxable involvement** — the guard must be **wired enforcing AND exercised** (a real refusal
  observed) before the first taxable trade. It is no longer "must be built"; it is "must be turned on and
  proven to fire."

Everything below is written for both, with the branch marked at each step.

---

## Part 1 — Robo-side liquidation mechanics (what actually happens at Schwab)

**What a Schwab robo (Intelligent Portfolios) liquidation does.** The portfolio is a basket of ETFs plus the
program's **mandatory cash allocation**. "Liquidate" = market-sell every ETF position, settling to cash in
the same account. Points that matter:
1. **You do not control the lots or the order.** The program sells to unwind the whole allocation; you are not
   picking tax lots at the UI level unless you exit position-by-position yourself.
2. **The mandatory cash sleeve is already cash** — that portion needs no sale and no settlement wait.
3. **Settlement:** equity/ETF trades settle **T+1** (US markets moved to T+1 in May 2024). Cash is not
   transferable until settled. Budget a day, not an hour.
4. **Fractional shares:** robo positions commonly include fractional quantities; these liquidate to cash but
   **cannot transfer in-kind** (see Part 2 — this is the single most common ACAT surprise).

**Tax lots on exit — ONLY if the robo account is taxable:**
- Each ETF sale is a realization event. A years-old robo account will hold **both gains and losses**.
- **Default lot method is usually FIFO** unless specifically set otherwise; a specific-lot election generally
  must be made **at or before sale**, not retroactively. If lot selection matters, it must be decided *before*
  the liquidation instruction, not after.
- **The robo's own tax-loss harvesting may have already sold losses recently.** That is the wash-sale hazard:
  a machine-side purchase of a substantially-identical fund within the **61-day** window (30 days before ∪ sale
  day ∪ 30 days after, per T-317) **permanently disallows** the loss if the buy lands in an IRA (Rev. Rul.
  2008-5 — no basis addition, the loss is simply gone).
- **In a Roth: none of this applies.** No realization, no lots, no wash-sale interaction. (This is a large part
  of why path (a) is preferred.)

**Timing:** liquidation instructions given during market hours execute that session; after-hours instructions
queue to the next session. Add T+1 settlement before any transfer can move the cash.

---

## Part 2 — ACAT vs cash transfer (the trade-off, honestly)

| | **ACAT (in-kind)** | **Cash transfer (liquidate → move cash)** |
|---|---|---|
| what moves | the positions themselves | settled dollars |
| **market exposure during transit** | **stays invested** (positions move, market risk retained) | **OUT of the market** for the duration |
| typical timeline | ~3-6 business days (full ACAT); partial can be slower | liquidation + T+1 settle, then ~1-3 business days (ACH) or same-day-ish (wire, fee) |
| taxable realization | **none** at transfer (basis + holding period carry over) | **full realization** at liquidation |
| fractional shares | **cannot transfer** — typically liquidated or cash-adjusted by the delivering firm | not applicable (all cash) |
| account freeze | positions typically **frozen during transit** (no trading) | source account simply empties |
| failure surface | mismatched registration, ineligible/proprietary securities, partial rejects | market gap during the out-of-market window |

**The decision rule, plainly:**
- **Roth → Roth:** either works and there is no tax consequence. **ACAT is preferred if the destination can hold
  the same instruments** (keeps exposure continuous, avoids the out-of-market gap). But note: our target book is
  a *different* allocation (SPY/AGG/GLD or the sleeve's instruments), so an in-kind transfer of robo ETFs is
  followed by a **sell-and-rebuy anyway** — in which case a cash transfer is simpler and the difference is only
  *when* you take the market gap.
- **Taxable → anything:** ACAT's "no realization" is a **genuine and large** advantage (deferral is the whole
  finding of T-294b). But it only helps if you intend to *keep* the positions; if the machine's book differs,
  you realize on the rebuy anyway. **Blocked regardless until the §9a guard is WIRED ENFORCING and exercised** (it is built — see the precondition).
- **The honest asymmetry:** the out-of-market window is a real, unhedged, one-shot market risk. Historically the
  market is up more days than down, so being out is negative-expectancy *on average* — but it is small relative
  to the decision itself. **Do not optimize this; do not time it.** Pick the simpler path and accept the gap.

---

## Part 3 — The arrival-day sequence (our side)

Assumes settled cash has landed in the destination account and the machine is otherwise running its normal
pulse. Each step names its branch and its abort condition.

| # | step | (a) Roth-only | (b) taxable involved | abort if |
|---|---|---|---|---|
| 1 | **Confirm cash is SETTLED, not merely "posted"** | required | required | unsettled → wait; never trade unsettled cash (good-faith / GFV violations) |
| 2 | **Reconcile the arrival against the expected amount** (partial transfers are common — Part 4) | required | required | mismatch > tolerance → HALT, investigate before any order |
| 3 | **Wash-sale guard check: robo-side loss-sales (last 30d) vs the machine's intended buys** | **N/A** | **REQUIRED — guard is BUILT but NOT ENFORCING (see precondition)** | any substantially-identical collision in the 61-day window → the buy is deferred or re-instrumented (SPY↔VOO↔IVV, AGG↔BND, GLD↔IAU per `config/substantially_identical.json`) |
| 4 | **Select the advisor row for (wrapper, equity)** — the advisor is a pure lookup; only `status=="validated"` auto-deploys | required | required | no validated row for the band → fail-conservative to the nearest validated LOWER band; if none → HALT |
| 5 | **Deploy per Rule B (always-invest-immediately, T-299 adopted)** | required | required | — |
| 6 | **First pulse runs the normal path** (adopt → rebalance → gates) with the book now real | required | required | any gate fails → the standing fail-closed behaviour, unchanged |

**On Rule B, with its honest caveat:** T-299 adopted always-invest-immediately, but recorded that **the effect
is sub-1%** — the contribution rule barely matters for a ~1.1× arm because the gate already manages the book.
It also found the better rule is **leverage-dependent** (a higher-leverage config marginally flips toward
withholding). So: follow Rule B, and do **not** treat the deployment-timing decision as high-stakes. It isn't.

**One-shot vs staged entry:** Rule B says deploy immediately. The *psychological* case for staging (thirds over
a few weeks) is real but the measured effect is sub-1% — if staging is what makes the move tolerable, the cost
is negligible and that is a legitimate reason to stage. Say so honestly rather than pretending the data forbids it.

---

## Part 4 — Failure modes, per step

| failure | where | what it looks like | response |
|---|---|---|---|
| **Partial transfer** | ACAT | some positions/cash arrive, some don't; source account not empty | do NOT deploy the partial as if it were the whole — re-run step 2's reconcile, deploy only what is settled, re-check the row (a smaller balance may select a different band) |
| **Fractional shares stranded** | ACAT | small residual cash or an un-transferable sliver left behind | expected, not an error; sweep it later, do not chase it |
| **Dividend in flight** | either | a distribution with record date before transfer, pay date after | it typically pays to the **old** account and must be swept separately; a residual balance appears weeks later — expect it, don't treat it as a reconciliation break |
| **In-kind arrives when cash was expected** (or vice-versa) | ACAT | positions show up instead of buying power | HALT deployment; the book is not what the advisor row assumes. Liquidate to cash first (taxable: this is a realization — the thing ACAT was meant to avoid), then resume at step 1 |
| **Unsettled-cash trade** | step 1 | order rejects, or a good-faith violation is flagged | this is why step 1 exists; wait for settlement |
| **Amount mismatch** | step 2 | arrived ≠ expected | HALT. Never deploy through an unexplained discrepancy — it is more likely a transfer error than a windfall |
| **Wash-sale collision** | step 3 | robo harvested a loss in SPY within 30d; machine wants to buy SPY/VOO/IVV | defer the buy past the window OR use a non-substantially-identical instrument. **In a Roth the disallowance is PERMANENT — there is no basis recovery** |
| **Market gap during the out-of-market window** | Part 2 | the market moves while cash is in transit | accepted, unhedgeable, one-shot. Do not attempt to time re-entry |
| **The destination can't hold an instrument** | step 4 | e.g. a fund unavailable at the destination | re-instrument to the row's documented equivalent before deploying, not after |

---

## Part 5 — The rollback story

**Be honest about what is and isn't reversible:**
- **Reversible:** the *deployment* decision. If the machine's book is wrong for any reason, it can be sold back
  to cash in one session. Nothing about our book is illiquid — it is large-cap ETFs.
- **Reversible with friction:** the *transfer*. Cash can be moved back; another ACAT can be initiated. Cost is
  time (days) and, if positions were sold, a second market gap.
- **NOT reversible:** **realized taxes** (taxable path) and **disallowed wash-sale losses**. A permanently
  disallowed loss in a Roth cannot be recovered by any subsequent action. This is why step 3 is a hard gate and
  why path (a) is preferred.
- **NOT reversible:** the market moves that happened while out of the market. They are simply taken.

**Rollback trigger:** there is no automated one. If the user wants to unwind, it is a manual, unhurried decision
— sell to cash, transfer back, done. The machine never initiates a transfer, never moves money between
institutions, and never liquidates on its own (the standing propose-never-execute discipline for anything
touching real money or account boundaries).

---

## Cross-references
- **T-317 spec → T-319 BUILD — the cross-account wash-sale guard** (`docs/Core/tlh_washsale_spec_t317.md`,
  `tests/test_cross_account_wash_guard_t319.py`): the 61-day two-directional window, the
  substantially-identical set, the pre-submission checks. **BUILT and merged; seam-wired in `OrderManager`;
  NOT YET ENFORCING (no caller passes `wash_guard=`) and never exercised in a live path.** Wiring +
  exercising is E/T-327 Act 2 — the blocking item for any taxable path.
- **Advisor spec** (`docs/Core/capital_aware_advisor_spec_t280.md`): §4 fail-conservative row selection, §5b the
  offense-arc row statuses, §9b the after-tax bar, and the placement model for a two-account world.
- **T-299** (`prereg_contribution_rule_t299.md`): Rule B adopted; sub-1% effect; leverage-dependent caveat.
- **T-294b**: why deferral is worth so much in the taxable column — the reason ACAT's no-realization property
  is a genuine advantage there.

---
**TABLETOP ONLY.** No date, no trigger, no recommendation. This document exists so that *if* the option is ever
exercised, the sequence is already rehearsed, the failure modes are already named, and the one blocking
engineering requirement (§9a) is visible in advance rather than discovered on the day.
