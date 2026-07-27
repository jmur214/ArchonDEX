---
title: "TLH stack + cross-account wash-sale guard — SPEC (A/T-317)"
task: T-2026-07-27-317
status: SPEC ONLY — 0 N_trials, nothing built. E/B build after director review.
---

# T-317 — the tax-loss-harvesting stack + cross-account wash-sale guard

Taxable TLH is the review's **#2 wealth path (~80% prior)**: near-deterministic,
structural, **certain-sign**, and it requires beating no one — unlike everything
else in the program, it does not need an edge to pay. Its BLOCKING prerequisite is
advisor spec §9a. This is the spec; **E/B build**.

**Scope guard:** everything below is *design*. No behavior changes here, 0 N_trials.
The order-path guard touches Engine B / live_trader → **propose-first, hard-gated,
user-approved before any build** per CLAUDE.md.

---

## Part 1 — the cross-account wash-sale guard (order-path state machine)

### 1.1 Why the existing guard is NOT sufficient (the gap, precisely)

`engines/engine_b_risk/wash_sale_avoidance.py` exists and is sound for what it does,
but it fails the §9a case on **four** counts:

| Existing behavior | Required for §9a | Gap |
|---|---|---|
| **Single-account** ledger (`_last_loss_exit[ticker]`) | loss in TAXABLE must block a buy in **ROTH** (and vice versa) | **fatal** — the guard cannot see the other account |
| **Exact-ticker** match | **substantially identical** (SPY≈VOO≈IVV, AGG≈BND, GLD≈IAU) | a Roth VOO buy after a taxable SPY loss trips 2008-5 and passes today's guard |
| **30-day forward** window | **61-day** window: 30 days **BEFORE** ∪ sale day ∪ 30 days **AFTER** | a buy 20 days *before* the loss-sale also triggers it |
| `should_block_buy → bool`, silently skipped | **REFUSE loudly pre-submission** with a typed reason; never logged-and-allowed | silent-wrongness class |

**And the asymmetry that makes this urgent:** a normal wash sale merely *defers* the
loss (basis is added to the replacement lot). **Rev. Rul. 2008-5 — an IRA/Roth
purchase — PERMANENTLY DISALLOWS it. No basis addition. The loss is gone forever.**
A systematic monthly rebalancer running the same tickers in both accounts trips this
by construction. The guard is therefore **fail-closed by design**: when in doubt,
REFUSE the order — a refused rebalance costs basis points of tracking error; a
permanently-disallowed loss costs the entire TLH thesis.

### 1.2 The state machine

**New module** `engines/engine_b_risk/cross_account_wash_guard.py` (Engine B —
propose-first). Config `config/substantially_identical.json`.

**State: the cross-account tax-lot ledger** (durable, append-only, S3-synced —
`data/state/tax_lots.jsonl`; it must survive ephemeral Fargate runs or the 61-day
window silently resets — the T-308 durability lesson):

```
LotEvent := {event_id, ts, account: "taxable"|"roth"|<paper-N>, symbol,
             side: "buy"|"sell", qty, price, lot_id, realized_pnl?,
             is_loss_sale: bool, client_order_id}
```

**Equivalence classes** (config, not code — the mapping is a tax judgment that must
be reviewable and revisable without a deploy):

```json
{"version": "2026-07-27",
 "classes": {
   "US_LARGE_BLEND": ["SPY","VOO","IVV","SPLG"],
   "US_TOTAL":       ["VTI","ITOT","SCHB"],
   "AGG_CORE_BOND":  ["AGG","BND","SCHZ"],
   "GOLD":           ["GLD","IAU","GLDM","SGOL"]},
 "_doc": "Members of a class are treated as SUBSTANTIALLY IDENTICAL. Cross-class
          pairs (e.g. VOO vs VTI, S&P-500 vs total-market) are the court-tested
          DISTINCTION the harvest loop trades on. Conservative by construction:
          adding a ticker to a class only ever makes the guard stricter."}
```

**The decision function** (called pre-submission, for EVERY order in EVERY account):

```
check_order(account, symbol, side, ts, ledger, classes) -> Decision
  # Decision := ALLOW | REFUSE(reason, evidence)
  if side != "buy": return ALLOW          # sells never trip the guard
  cls  = class_of(symbol)                  # symbol's equivalence class (or itself)
  win  = [ts - 30d, ts + 30d]              # 61-day window, BOTH directions
  hits = ledger.loss_sales(class=cls, window=win, accounts=ALL)
  if not hits: return ALLOW
  if account is TAXABLE and hit.account is TAXABLE:
      return REFUSE("wash_sale_deferral", hits)      # deferred loss — still refuse
  return REFUSE("rev_rul_2008_5_permanent_disallowance", hits)  # ← the fatal one
```

**Two properties the build must preserve:**
- **Forward AND backward.** A loss-sale on day *T* must also poison buys already made
  in `[T−30, T)`. Implementation: the guard is consulted (a) pre-submission for new
  buys, and (b) **pre-submission of any loss-SALE** — if a substantially-identical buy
  occurred in the prior 30 days in ANY account, the *sale* is flagged
  `WOULD_BE_WASH` and either deferred past the window or accepted with the loss
  marked disallowed in the ledger (an explicit, recorded choice — never silent).
- **Refuse loudly.** `REFUSE` raises a typed `WashSaleRefusal` **before** the order
  reaches `OrderManager.submit()`, writes a journal line, and surfaces on the
  heartbeat. The order is NOT quietly dropped and NOT retried into the same window.

### 1.3 Interface against the existing seams (E builds to this)

- **Insertion point:** `paper_trader/order_manager.py` — pre-submission, alongside
  `_validate_order_values(order)`. Signature: `guard.check_order(...) -> Decision`;
  on `REFUSE`, `OrderManager` records `OrderState.REJECTED` with
  `reject_reason="wash_sale:<reason>"` and never calls the broker.
- **Ledger writes:** on every fill (`record_fill`), from the reconciliation path so
  broker truth — not intent — populates the lot ledger.
- **Reuse:** keep `WashSaleAvoidance` for the single-account intraday case; the new
  guard SUPERSEDES it for cross-account decisions (do not run two blockers on the
  same order — one authority, or they will disagree silently).
- **Durability:** `cloud_state.DURABLE_PATHS += data/state/tax_lots.jsonl`.
- **Tests the build must ship:** (1) taxable SPY loss-sale → Roth **VOO** buy inside
  61d ⇒ REFUSE `rev_rul_2008_5`; (2) the same at day 62 ⇒ ALLOW; (3) **backward** —
  Roth VOO buy on day 10, taxable SPY loss-sale on day 30 ⇒ the SALE flags
  `WOULD_BE_WASH`; (4) VOO→VTI (cross-class) ⇒ ALLOW; (5) refusal is loud (typed
  exception + journal + heartbeat), never silent; (6) ledger survives a simulated
  ephemeral restart.

---

## Part 2 — the ETF-pair harvest loop

**The pair.** Hold **VOO** (S&P 500); harvest into **VTI** (total market). Different
index, different holdings (VTI holds ~3,600 names incl. small/mid) — the
court-tested *not*-substantially-identical distinction. Alternate back on the next
harvest (VTI→VOO), so the book is always in one of the two and never out of market.
**Never** harvest VOO→IVV/SPLG (same class = a wash by construction).

**Trigger (all must hold):**
1. `unrealized_loss(lot) ≤ −max($500, 2% × lot_cost_basis)` — a **friction floor**;
   below it the round-trip spread/commission + tracking-error risk exceeds the
   harvest's tax value.
2. Lot is **outside** the 61-day window of any substantially-identical buy in EITHER
   account (Part 1 guard consulted — the guard is the authority, not a copy of it).
3. Not already harvested within the trailing 31 days (the **blackout ledger** below).
4. Annual realized-loss budget not yet exhausted (below).

**Blackout ledger** (`data/state/tlh_blackout.jsonl`): every harvest writes
`{symbol, class, harvest_ts, blackout_until = harvest_ts + 31d}`. No repurchase of
the sold class before `blackout_until`. 31 days (not 30) is deliberate — an
off-by-one here is a permanently-disallowed loss.

**Loss accounting** (the value model, not just the trade):
- Realized losses offset realized gains dollar-for-dollar; **excess offsets up to
  $3,000/yr of ordinary income**; the remainder **carries forward indefinitely**.
- The carryforward is an asset — the sim (Part 3) must track it, not discard it.
- **Ride winners forever.** The user's stated won't-sell behavior turns deferral into
  **permanent avoidance at the step-up in basis**. TLH's value is therefore
  *asymmetric*: harvest losses aggressively, realize gains never.

**Interaction with contributions.** New contributions buy the **currently-held** side
of the pair, never the blacked-out side — a contribution is a purchase and trips the
wash rule exactly like a rebalance buy. Rebalances route through the same guard.

---

## Part 3 — the deterministic 40-yr after-tax sim (design)

**Question (pre-registered before running):** what is the honest expected value of
the harvest rule vs the identical un-harvested book, after tax, over ~40 years, at
the user's bracket?

**Design — a PAIRED race, same paths, one difference:**
- **Arm A (control):** buy-and-hold the pair-equivalent exposure, contributions on
  schedule, **no harvesting**.
- **Arm B (treatment):** identical exposure/contributions + the Part-2 harvest loop
  (friction floor, 31-day blackout, guard-respecting).
- **Identical** price paths, contribution schedule, and rebalance calendar — the ONLY
  difference is the harvest rule (so the Δ is attributable, exactly the T-259
  control-discipline that made that A/B trustworthy).
- **Machinery:** T-141/T-191 FIFO lot accounting + `TaxRates`/`TaxProfile` from
  `core/combined_candidate_scorecard.py` (short/long-term rates, `long_term_min_days`,
  the user's actual bracket + state). Deterministic; seeded; no `Date.now()`-style
  nondeterminism.
- **Paths:** the multi-decade substrate (T-306 D-A/D-B, ~58–64yr) block-bootstrapped
  into 40-yr paths — NOT a single historical path (one path is an anecdote).
- **Metric:** **paired Δ terminal after-tax wealth** with a **block-bootstrap CI**
  (`[NN-SHARPE-CI]`), plus Δ effective tax drag %/yr. Report the **ci_low**.
- **Honest expectation (stated up front):** the review's ~**0.1–0.3%/yr blended**.
  Small — but free and, unlike every other program lever, **certain in SIGN**. The
  sim exists to size it honestly, not to discover whether it works.
- **Report per tier** (capital-adaptive directive): the harvest value scales with
  taxable balance; state it at each tier rather than one blended number.
- **Sensitivities:** bracket (incl. a future higher-income case), the $3k ordinary
  offset, harvest-frequency cap, and the friction floor.

**Honest caveats the sim must state:**
- TLH **defers**, it does not create alpha; its terminal value depends on the
  step-up assumption holding (current law) and on never realizing the winners.
- Harvest value is **highest early** (unrealized losses are most available in the
  first years / after drawdowns) and decays as basis resets upward.
- Tax law is a MODEL INPUT, not a constant — pin the assumed rules with the run.
- This is not tax advice; the adopted rule needs the user's (or their CPA's) sign-off.

---

## Deliverable summary + build order (recommended)

1. **Part 1 guard FIRST** — it is the blocking prerequisite (§9a) and the *only*
   piece that prevents a permanent, unrecoverable loss of value. Nothing in Part 2
   may ship before it. **Engine B / order path → propose-first, user-approved.**
2. **Part 3 sim SECOND** — it sizes the prize before we build the machinery to chase
   it (measure-before-optimize).
3. **Part 2 harvest loop LAST** — mechanical once the guard exists and the sim has
   justified the thresholds.

**T-317 spec ready.** 0 N_trials, nothing built.
