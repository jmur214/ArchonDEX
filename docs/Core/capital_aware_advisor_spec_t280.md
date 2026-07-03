---
task_id: T-2026-07-02-280
title: Capital-aware advisor — policy-layer spec + tier-table schema (DESIGN, not build)
date: 2026-07-02
author: Agent D
type: design spec + config schema (the BUILD is assigned after B/T-278 + C/T-279 land)
status: SPEC — awaiting the validated rows that populate it
---

# T-280 — the capital-aware advisor spec

**User directive (recorded):** the system should act like an investment advisor — given what's in the
account, deploy the best VALIDATED configuration for that amount. This spec designs the policy layer that
makes that real: a **(wrapper × equity-band) → validated-configuration** lookup, populated ONLY from
cleared gauntlets, fail-conservative everywhere else.

## 1. The tier table — schema

The advisor is a pure lookup: `advisor(wrapper, equity) → row`. The table is a list of **rows**, each a cell
in the (wrapper × equity-band) grid. A row is only present if a gauntlet VALIDATED it; absent cells resolve
by fail-conservative fallback (§4).

```
Row := {
  id:              str          # stable slug, e.g. "roth_10k_sleeve"
  wrapper:         "roth" | "taxable" | "rollover"
  equity_min:      number       # inclusive band floor (USD)
  equity_max:      number|null  # exclusive band ceiling (null = open-ended top)
  instrument_set:  [str]        # concrete tradeable tickers, e.g. ["SPY","AGG","GLD"] or ["SPLG","AGG","GLDM"]
  active_legs:     [str]        # which validated capabilities are ON, e.g. ["trend_sleeve_ensemble"]
  sizing:          {            # the T-151 safe-f / CAR25 machinery knobs (the sizing dimension)
    car25_tolerance:  number    # drawdown-tolerance knob (glide-path input; declines with AUM/lifecycle)
    max_leg_weight:   number    # per-leg cap
    integer_shares:   bool      # true below the fractional-share threshold
  }
  validation_ref:  str          # the gauntlet that earned this row (task id + audit doc). MANDATORY.
  status:          "validated" | "pending:<taskid>" | "fallback"
  turnover_class:  "low" | "monthly" | "high"   # drives the wrapper/tax handling (§3)
}
```

**Invariant (`[NN-FAIL-CLOSED]`):** a row with `status != "validated"` MUST NOT be selected for a live
deploy. `validation_ref` is mandatory and must point at a real merged audit; a row whose ref is missing,
`pending:`, or points at a refuted task is treated as ABSENT (→ fallback, §4). No row is ever hand-authored
into `validated` — it is written only when the referenced gauntlet clears (mirrors the `edges.yml`
sole-authority discipline: config status is not self-certifying).

## 2. The equity bands (from the capital-milestones map, forward_plan.md §"Capital milestones")

The band boundaries are the live decision points from the audited milestones map — NOT invented here:

| band | boundary rationale | door (evidence ref) |
|---|---|---|
| **< $10K** | integer-share drag is material (1.1-2.4 pp/yr on SPY/AGG/GLD at $5K) → use low-price proxies | T-257 |
| **$10K – $25K** | integer-share drag negligible on SPY/AGG/GLD; micro-futures *possibly* feasible but approval-gated | T-257 / gap-audit Pt4 |
| **$25K – $65K** | Schwab IRA limited margin unlocks (GFV/cash-settlement friction gone; ~50% daily-turnover cap lifts) | T-270 |
| **$65K – $100K** | ONE cash-secured XSP put / 100-share covered call → direct premium harvesting becomes testable | T-261/putwrite |
| **$100K+** | multi-contract diversified premium program; 10+ concurrent special-situations | T-267/T-277 |

**Crucial:** these bands describe which doors *can* open — they do NOT mean a richer row EXISTS. A band's
row is the sleeve until a gauntlet validates the richer capability for that band (§4). The milestones map's
standing rule holds verbatim: *crossing a threshold triggers a fresh pre-registered scope, never an
automatic build* (`[NN-MBL]` N-accounting).

## 3. The wrapper dimension (load-bearing)

Roth annual contributions cap at ~$7K, so "much more capital" almost always means **taxable or rollover**.
The wrapper is not cosmetic — it changes both the *legal instrument set* and the *cost structure*:

- **Roth:** no margin / no shorting / no leverage. Payment for that constraint = **zero tax drag**. This is
  the aggressive-sleeve home (the glide-path item in forward_plan: "aggressive sleeve lives in the Roth").
- **Taxable / rollover:** re-opens margin / shorting / futures, BUT re-imposes **tax drag ~130 bps/yr on
  turnover** (T-148) and wash-sale accounting. Measured impact is large: T-151 safe-f conditions sizing on
  account and finds **Roth 1.602 vs taxable 0.273 on the same book (~6×)** — turnover is punitively taxed.

**How the table handles it (rules, not vibes):**
1. **Taxable rows prefer LOWER-turnover variants of the same validated capability.** The sleeve rebalances
   monthly (`turnover_class: monthly`); a taxable sleeve row should carry the lower-turnover buffered
   variant (T-148 Carver buffering, already shipped, OFF-default) as its default, because the tax channel
   is ~29× the transaction-cost channel for a taxable account. The Roth row keeps the un-buffered variant
   (no tax channel → buffering only saves txn cost, marginal).
2. **The wrapper-blocked list re-opens ONLY behind a fresh pre-registered scope.** Blocked at any size in a
   Roth: full CTA replication (long-short levered futures), risk parity, levered vol-targeting, the short
   leg of every long-short premium. A taxable/rollover row may *legally* express these, but each is a
   NAMED, currently-un-validated capability → it enters the table only when its own gauntlet clears under
   the taxable cost model (tax drag charged). Never assumed by wrapper alone.
3. **Sizing is wrapper-conditioned via T-151 safe-f** (the shipped machinery): `sizing.car25_tolerance`
   feeds the safe-f fraction, which is already account-aware. The advisor sets the knob per (wrapper,
   band); it does not re-derive safe-f.

## 4. Fail-conservative fallback (the core safety rule)

`advisor(wrapper, equity)` resolves in this order:
1. Exact validated row for `(wrapper, band(equity))` → return it.
2. Else the **nearest validated LOWER equity band, same wrapper** (never a higher band — never assume an
   un-earned door is open).
3. Else the **Roth-equivalent validated row** de-rated to the wrapper's legal instrument set (drop any
   margin/short/futures legs the wrapper can't hold; keep the long-only core).
4. Else **HALT** (`[NN-FAIL-CLOSED]`) — no plausible-looking default. An out-of-table `(wrapper, equity)`
   with no lower validated row is an error, not a silent pass to "some sleeve."

Un-validated higher tiers therefore **degrade to the validated sleeve**, not to an aspirational config.

## 5. The table AS OF 2026-07-02 (what actually populates today)

Only ONE capability is validated AND wired end-to-end: the **trend sleeve** as it actually runs in
`paper_trader/sleeve_constructor.py` — EW **SPY/AGG/GLD**, **single 5-month (105-day)** long-flat
absolute-momentum overlay (`SLEEVE_LOOKBACK = 105`), Carver deadband 0.10. Validation: T-236 (full-cycle
incl dotcom) → T-255 (fair re-run: beats schwab_like on wealth+drawdown, ties 60_40 on wealth with 3×
shallower drawdown). So **every populated row today is the single-105d sleeve**, differing only by
share-rounding instrument set:

| wrapper | band | row (today) |
|---|---|---|
| roth | <$10K | sleeve on **SPLG/AGG/GLDM** (low-price proxies; integer_shares=true) — validation T-236/T-255 |
| roth | $10K–$100K+ | sleeve on **SPY/AGG/GLD** (105d single-speed) — validation T-236/T-255 |
| taxable/rollover | any | sleeve, **buffered (low-turnover) variant** (T-148, `position_buffering`) — *pending a taxable-cost-model re-gauntlet* → until then, fail-conservative to the Roth long-only sleeve row de-rated (no leverage) |

**The {2,5,10}mo multi-speed ensemble (T-260) is NOT the deployed default — and the table must not pretend
it is.** T-260 found it a *mild robustness win that is directional, NOT CI-significant* (paired ΔSortino CI
straddled zero once run cleanly), and explicitly recommended it as an OPTIONAL hardening subject to a
director/user promotion decision — `sleeve_constructor.py` was deliberately left on single-105d. So the
ensemble is a `status: validated-variant` row **available for promotion**, not the active default; the
advisor would only select it if/when the director promotes it (a config flip, not a re-gauntlet).

**Pending rows (stubs, `status: pending:*`) — do NOT populate as validated until their gauntlet clears:**
- `*_futures_*` (micro-futures, $15-25K+) — pending scope (gap-audit Pt4).
- `*_65k_premium` (cash-secured put / covered call, $65K+) — **pending C/T-279**.
- `*_100k_premium_program` (multi-contract) — pending T-267/T-277.
- any BTC leg — **pending the T-276 forward gates**.
- per-tier sleeve sizing rows — **pending B/T-278**.

Each stub's cell holds its `validation_ref: pending:<taskid>` so the table is self-documenting about what
would fill it; the advisor treats every stub as ABSENT (§4).

## 6. Runtime behavior (the hook, fail-closed, and the paper-vs-live-row flag)

**Selection hook (concrete):** the sleeve is built by `paper_trader/sleeve_constructor.py ::
SleeveOrderConstructor`, whose `__init__(universe, lookback, deadband, tif)` holds the config and whose
`construct(equity, current_positions, closes) -> SleevePlan` builds the orders. `equity` is already read
LIVE from the broker each run (`scripts/run_paper_cloud_day.py` → `acct["cash"]`). The advisor inserts
BEFORE construction:
```
row = advisor(wrapper, equity)                       # pure lookup over config/advisor_tier_table.json
ctor = SleeveOrderConstructor(universe=row.instrument_set,
                              lookback=row.sizing.lookback,       # 105 today
                              deadband=row.sizing.deadband)       # 0.10 today
plan = ctor.construct(equity, current_positions, closes)
```
i.e. the advisor **replaces the hardcoded `SLEEVE_UNIVERSE / SLEEVE_LOOKBACK / SLEEVE_DEADBAND` module
constants with the row's values** — a config-selection layer in front of the existing constructor, not a
change to the constructor's math. `active_legs` beyond the trend sleeve (premium, futures) attach as
additional constructors only when their row is validated. The advisor is a pure function of (config,
wrapper, equity); it holds no state and never trades.

**Wrapper source:** read from the existing `config/account_routing.json` (which already carries
`default_account` + per-sleeve `account` + `st_heavy` + wash-sale `blackout_31d`) and the paper/live
`account` key (`paper_config.py account="roth"`). The advisor does NOT invent a parallel wrapper key — it
consumes the account-routing config that already exists.

**Fail-closed inputs (`[NN-FAIL-CLOSED]`):**
- `utils/config_loader.load_json` returns `{}` on a missing file — the advisor MUST reject an empty or
  ref-less table and HALT, never proceed on a `{}`/one-key fallback (this is the exact "load-bearing config
  from {}" defect class the census rules guard). Require ≥1 `status:"validated"` row on load.
- Unknown wrapper, non-positive equity, or equity below the smallest band with no `<$10K` row → HALT.
- Any selected row whose `validation_ref` is `pending:*` / missing / points at a refuted task → treat as
  absent, fall back (§4); if the fallback chain is empty → HALT.

**Paper-vs-live-row flag (load-bearing honesty — and a discrepancy to reconcile):** the brief states paper
runs at **$100K** and live deploys at **$5-15K** — DIFFERENT bands, DIFFERENT rows. But the code tells a
different story worth pinning: `paper_config.py` sets `starting_equity = 5_000.0` (T-159 §5 Roth-emulation)
and the runtime then **overrides it with live broker cash** (`acct["cash"]`). So the equity the sleeve
actually sizes to is whatever the Alpaca paper account holds during the validation window — which is $100K
if the paper account is left at Alpaca's default funding, or $5K if reset per T-159. **This must be pinned,
not assumed:** the go-live doc must record the EXACT `acct["cash"]` the paper evidence was gathered at, and
state which live band that covers. Today it is moot (every band runs the same single-105d sleeve
capability, so paper at any band validates the same EXECUTION mechanics the $5-15K live row needs). **It
stops being moot the moment a richer high-band row is validated** (e.g. a $65K+ premium leg via T-279):
paper at $100K would then exercise a capability the $5-15K live row does NOT run, and paper would NO LONGER
cover the live row. The advisor therefore stamps each row with `paper_evidence: covered | not-covered`
(and the pinned equity), so the go-live gate can assert the live row is paper-covered before any real money
moves.

## 7. Transition triggers (propose, never auto-switch)

When account equity crosses a band boundary, the advisor **proposes** the next row to the user — it never
auto-switches (real-money path; same discipline as the paper-schedule enable). The proposal carries: the
new row, its `validation_ref`, the turnover/tax implication, and (if the new row adds a wrapper-blocked or
pending capability) a note that a fresh pre-registered scope is required first. The user confirms; only then
does the active row change. Downward crossings (equity fell below a band) auto-apply the lower row
immediately (fail-conservative — de-risking never needs confirmation).

## 8. Build hand-off (out of scope for this task)

The BUILD is assigned after B/T-278 (per-tier sleeve rows) + C/T-279 ($65K+ premium row) land. This spec
defines: the row schema (§1), the band boundaries (§2), the wrapper rules (§3), the fallback (§4), the
current population (§5), the runtime contract (§6), and the transition policy (§7). The config artifact
(`config/advisor_tier_table.schema.json` + a seed `config/advisor_tier_table.json` holding only the
validated sleeve rows) accompanies this doc.
