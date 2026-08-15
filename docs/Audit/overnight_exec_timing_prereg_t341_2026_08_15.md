# T-341 — the OVERNIGHT EXECUTION-TIMING probe: PRE-REGISTRATION (DRAFT for director freeze)

**Date:** 2026-08-15 · **Agent:** C · Branch `feature/overnight-exec-timing-prereg-t341` · **0 N_trials until frozen**
**Design only. Nothing run. No trading change — any live sleeve change is a separate propose-first gate.**
Source: SSRN 3829582's honest core — overnight-vs-intraday asymmetry is **cost-dead as a strategy** but potentially free as **execution timing**: conditioning *when* an already-decided rebalance executes, at zero incremental trades.

---

## ⚠ READ FIRST — the honest minimum detectable effect says the RETURN arm cannot be resolved
Measured on our own data before drafting (the T-337 discipline):

**SPY open→close execution-price gap, 2000-2026: mean +0.9 bps, SD 97.9 bps (n=6,612).**

| available n | MDE (80% power, α=0.05) |
|---|--:|
| **n = 700** — *all ~58yr of monthly rebalances* | **10.4 bps** |
| n = 300 — 25yr monthly | 15.8 bps |
| **n = 3** — *our real fills to date* | **158 bps** |

**Plausible true effect of open-vs-close timing for liquid ETFs at retail size: ~1-3 bps.**

> **So the return-timing arm is underpowered by 3-10× even using ALL available history, and by ~50× on live fills.** This is not a reason to skip the probe — it is a reason to pre-register *which* question we are actually answering, and to forbid a verdict on the one we cannot.

**Second grounding fact:** our realized slippage to date is **0.26 / 0.51 / 1.02 bps (mean 0.60)**. We are already executing within ~1 bp of arrival. **The maximum recoverable saving is therefore ~1 bp** — smaller than the MDE of every arm. The ceiling on this idea is low regardless of what the measurement says.

---

## The design split that makes the probe answerable
The question decomposes into two quantities with wildly different variance. Conflating them is what would make this an alpha hunt in disguise:

| arm | quantity | SD | answerable? |
|---|---|--:|---|
| **A — COST** | realized spread/impact **at each time-of-day** (effective spread vs the prevailing mid) | ~0.4 bps | **YES** — low variance, modest n suffices |
| **B — RETURN** | *which price you got* (open vs close execution) | **97.9 bps** | **NO** — needs ~16,000 events for a 2 bp effect |

**Arm A is the real execution-cost question** (the class twice found binding). **Arm B is the timing-return question — the one the source paper already found cost-dead.** The probe runs A as the measurement and B as a pre-registered *underpowered report*.

## Method (frozen)
1. **Arm A (primary).** For each candidate execution time — **market open**, **our live 9:45 ET**, **close** — measure realized execution cost as effective spread vs prevailing mid.
   - *Backtest side:* daily panels carry `Open`/`Close`, so open-vs-close is available on the full deep history. **The 9:45 point requires minute bars and NO client method exists** (`AlpacaPaperClient` has only `fetch_daily_closes` / `fetch_latest_prices` / `fetch_btc_usd_history`) — Alpaca's free tier serves minute bars to ~2016, so this is a **build cost to be approved, not an assumed capability**.
   - *Real-fill side:* the exec-cost ledger + gate-b. **n = 3 today**; at monthly rebalance cadence, reaching n=30 takes **~2.5 years**. This arm is a **validation check on the backtest arm's cost model, NOT a measurement** — pre-stated so it can never be quoted as one.
2. **Arm B (secondary, pre-registered underpowered).** The open-vs-close realized-return delta over historical rebalance dates, reported **with its CI and its MDE, and NO verdict**. Pre-stating "underpowered" is what stops a noise result being read as a finding in either direction.

## Pre-stated gate
- **Arm A PASSES** iff the block-bootstrap CI on the per-time-of-day cost delta **excludes zero** AND the point estimate is **≥ 0.5 bps** (below that it cannot beat the ~1 bp ceiling and is not worth an operational change).
- **Arm B has NO PASS CONDITION.** It reports CI + MDE only. **A CI straddling zero on Arm B is the EXPECTED result and must not be reported as evidence either way.**
- **Fail-closed:** any time-of-day whose spread cannot be measured from the artifact is **excluded and named**, never assumed equal to another slot.
- **If Arm A clears:** the live A/B is **report-only first** — the paper lab twins one book's execution timing against the untimed baseline (my existing `LiveBook` twin machinery; `days_accrued` + NOT-EVALUABLE guard apply). **Any change to the live sleeve's execution is a separate propose-first gate requiring director + user approval.**

## N_trials
**N += 1** on freeze (Arm A). Arm B consumes **no additional trial** — it is a reported quantity with no verdict, not a hypothesis test.

## Honest prior
**LOW.** Three independent reasons, stated before any run: (1) we already execute within ~1 bp, so the recoverable saving is ~1 bp at most; (2) the plausible effect (1-3 bps) is below the MDE of every available arm for the return question; (3) the source's own finding is that this asymmetry is cost-dead. **The most likely honest outcome is "Arm A shows no cost difference large enough to act on, and Arm B is uninformative by construction"** — which is worth knowing cheaply, and is why the probe should stay narrow.

## What this can and cannot become
- **CAN:** retire an execution-timing question with a receipt, at low cost.
- **CANNOT:** become an alpha claim. Arm B is the alpha-shaped question and it is pre-registered as unresolvable; no result here may be cited as return evidence.

**Awaiting director freeze. Nothing run; no trading change.**
