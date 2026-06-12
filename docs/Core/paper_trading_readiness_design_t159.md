# Paper-Trading Readiness Design (T-159) — propose-first package

**Status:** DESIGN ONLY. Zero production code shipped with this doc.
Anything below that touches `live_trader/`, Engine B, or broker configs
is hard-gated on explicit user approval per CLAUDE.md; this package
exists so that approval is a 30-minute decision, not a month of
discovery. Authored by the agent that shipped the deployment stack it
integrates (T-139/141/146/148/151/152) — every hook point cites shipped
code.

**Context:** the outside review (T-156,
`docs/Audit/fresh_view_full_system_review_2026_06_11.md:31,110,189`)
lands the structural critique: world-class measurement apparatus, zero
trading days, not even paper; its P1 is "start paper trading." The
deployment boundary (`docs/State/deployment_boundary.md`, cited at
review :110) currently says no paper trading — adopting this design is
the explicit, user-gated act that moves that boundary.

---

## 1. Gap inventory — what exists vs what a paper loop needs

### What exists (read in full; cited)

**`live_trader/` is a 64-line stub with three disqualifying properties:**

- [`broker_interface.py:16-34`](../../live_trader/broker_interface.py#L16-L34)
  `place_order` submits **market orders with `time_in_force: "gtc"`**
  (`:23`) — not OPG/CLS, so it pays spread at arbitrary times and is the
  exact live-vs-backtest fill-mechanism divergence T-146 exists to kill.
  Fire-and-forget POST: **no `client_order_id`** (no idempotency — a
  crash-and-retry double-submits), no ack/fill polling, no order state.
  Paper URL hardcoded (`:14`); env keys `ALPACA_API_KEY` /
  `ALPACA_SECRET_KEY` (names only; values live in `.env`).
- [`live_controller.py:16-23`](../../live_trader/live_controller.py#L16-L23)
  `on_market_tick` calls `prepare_order(sig, self.state["cash"], …)` —
  **no `target_weights` argument**, so Engine B sizes via Path B
  (ATR-risk), the path T-088 established as dead/non-prod; the entire
  Engine C chain (policy → dyn-opt → buffering) is bypassed. Only
  `side != "none"` routes — **signal exits never reach the broker**.
  Equity is a cached `state["cash"]`, never marked to market.
- No reconciliation: [`broker_interface.py:36-43`](../../live_trader/broker_interface.py#L36-L43)
  `get_positions` exists but **nothing calls it**.
- Sidecar deps: [`storage/state_manager.py:10-16`](../../storage/state_manager.py#L10-L16)
  (a cash/positions/open_orders JSON at `data/state/trader_state.json`)
  and [`brokers/alpaca_broker.py:10`](../../brokers/alpaca_broker.py#L10).

**Plus two OTHER partial paths in `orchestration/mode_controller.py`:**
[`AlpacaExecutionAdapter`](../../orchestration/mode_controller.py#L145-L176)
sends an order and then **fabricates a synthetic fill at the intended
price** (`price` fallback 0.0!) "to keep the portfolio consistent" —
i.e., our books would record fills that never happened at prices we
made up; and `LiveTradeController` (`:384+`) / `PaperTradeController`
(`:191+`), where the paper loop **re-implements fill/SL-TP semantics
for parity** with the backtester (the review's :122 critique; its :202
recommends extracting shared semantics; its :208 demands deciding which
path is real).

**Decision proposed here (user ratifies):** the `mode_controller` /
`BacktestController` lineage is the real one — it is where signals,
Engine C targets
([`portfolio_engine.py:412/:430/:439`](../../engines/engine_c_portfolio/portfolio_engine.py#L412)),
Engine B sizing
([`backtest_controller.py:539→584`](../../backtester/backtest_controller.py#L539)),
fills, logging, and all six deployment-stack features already live.
**`live_trader/`, `storage/state_manager.py`, and
`brokers/alpaca_broker.py` are archived** (PR-4, hard-gated); the paper
loop is a NEW `paper_trader/` package that reuses the production
order-CONSTRUCTION path verbatim and replaces only the execution layer.

### What a paper loop needs (the gap, itemized)

| Capability | Current state | Needed |
|---|---|---|
| Order lifecycle | fire-and-forget POST | submit → ack → (fill \| partial \| reject \| expire) → reconcile, with an append-only order journal |
| Idempotency / restart | none (gtc + no client id) | deterministic `client_order_id` = hash(trade_date, ticker, side, qty, config_hash); on restart, journal replay + broker `GET /orders` diff; NEVER blind-resubmit after the 9:28 OPG cutoff (T-146 audit, live one-pager) |
| Fill mechanism | gtc market | OPG/CLS auction orders (`tif=opg` before 9:28 ET; `tif=cls` before 15:50 NYSE / 15:55 NASDAQ-imbalance-only) matching the T-146 backtest convention ([`execution_simulator.py:58,212`](../../backtester/execution_simulator.py#L58)) |
| Sizing path | Path B via stub | the production Path A chain: `compute_target_allocations` with dyn-opt ON ([`portfolio_engine.py:430`](../../engines/engine_c_portfolio/portfolio_engine.py#L430) — auction orders are whole-share-only, the integer book is REQUIRED) + buffering per the enable decision (`:439`) → `prepare_order(target_weights=…)` |
| State | one JSON blob, trusted blindly | positions-as-we-believe ledger + order journal (append-only) + broker truth, three-way reconciled every cycle (§2) |
| Schedule | none (`on_market_tick`) | the daily clock (§1.1) |
| Kill layer | none | §3 (T-152 + T-151, pre-registered) |
| Account semantics | one anonymous account | T-141 router: Roth-first (§4) |

### 1.1 The daily schedule (ET; all times config, these are the proposal)

```
T+0 16:05  pull close bars → data cache append
T+0 17:00  signals + targets compute off T+0 closes
           (Engine A → Engine C [dyn-opt → buffering] → Engine B
            prepare_order; orders staged to the journal, NOT submitted)
T+1 08:30  pre-flight: reconcile (§2) MUST be clean; risk caps;
           T-141 router/blackout shadow check; buying-power check
T+1 09:00  OPG batch submit (deadline 09:25; hard cutoff 09:28 —
           a missed cutoff degrades to SKIP-AND-LOG, never to a
           market order, else the fill log silently mixes mechanisms)
T+1 09:35  ack sweep (every order acked or alarm)
T+1 10:00  fill reconciliation #1 (auction prints vs T-146 expected)
T+1 15:40  CLS batch for close-auction legs, if the enabled convention
           routes any (deadline 15:45; cutoff 15:50)
T+1 16:10  post-close reconcile #2 + EOD snapshot + T-152 monitor
           update + journal flush
Fri 17:00  weekly: T-151 safe-f/CAR25 on the rolling paper record
           (once ≥126 obs); promotion-criteria report refresh
```

Crash mid-order: on restart, the loop replays the journal, diffs
against broker `GET /orders` + `GET /positions`, adopts broker truth
for anything acked, cancels anything staged-but-unacked past its
window, and refuses new submissions until reconciliation is clean.

---

## 2. Broker-truth reconciliation

Every cycle (≥2×/day per the schedule) diff three states: **(a)** the
ledger (positions-as-we-believe), **(b)** broker truth (`GET
/positions`, `GET /account`, `GET /orders?after=…`), **(c)**
expected-from-journal (what fills the journal implies). Divergence
taxonomy with PRE-REGISTERED responses (the T-152 philosophy — chosen
now, not during the event):

| class | detection | pre-registered response |
|---|---|---|
| missed fill (acked, no fill by window close) | order open past auction | cancel; log; NO chase — the name re-enters via tomorrow's normal signal path |
| partial fill | broker qty < order qty | ledger adopts broker truth; remainder canceled (at <0.001% ADV partials should be ≈never — a partials rate >1/wk is itself an alarm) |
| reject | API status | classify {fractional, after-cutoff, buying-power, other}; skip ticker for the day; >3 rejects/week = config bug alarm |
| price drift | \|fill − expected auction print\| > `auction_safety_bps` + 5bps | accept fill (it is truth); feed the slippage-error series (promotion criterion §5.2) |
| cash drift | \|ledger cash − broker cash\| > $1 | HALT new submissions until manually reconciled (the only halt-class) |
| position drift | ledger qty ≠ broker qty outside any open order | HALT new submissions; adopt broker truth only after the journal explains it |
| corporate action | symbol/qty morphs (split, ticker change) | halt the ticker; manual review (the single intentionally-manual class) |

Reconciliation writes an append-only `reconcile_log` with a per-cycle
`clean: bool` — the promotion criteria consume its clean-rate.

---

## 3. Kill-layer wiring (two-tier, pre-registered)

**Tier 1 — daily, fast (vol/regime-scale):** T-152 monitors consume the
paper stream through their streaming contract —
[`CusumMonitor.update`](../../backtester/divergence_monitors.py#L64) /
[`PageHinkleyMonitor.update`](../../backtester/divergence_monitors.py#L97)
(streaming==batch is tested). Feed: daily innovation `z_t = (r_paper_t −
μ_backtest_t)/σ_backtest_t` where the **expectation stream is the
BACKTEST's rolling stats** (not self-stats — the live semantics from
the T-152 calibration), via
[`standardized_innovations`](../../backtester/divergence_monitors.py#L115)
with the expectation series supplied. Operating points AS SHIPPED
([defaults at `divergence_monitors.py:155`](../../backtester/divergence_monitors.py#L155),
calibrated ≤1 false alarm/yr, T-152 audit): CUSUM-mean k=1.0/h=5.0,
CUSUM-var k=2.0/h=12.0, PH δ=0.05/λ=20σ. One monitor set per account.

**Pre-registered actions (proposal; frozen unless re-registered BEFORE
go-live):** first tier-1 alarm → REDUCE gross to 50% same day; second
alarm within 20 trading days OR any CUSUM-var alarm → FLATTEN;
re-entry only after a written review + (if parameters change) a fresh
registration. Per the T-152 calibration, tier 1 catches vol-scale
breaks in ~13-16 trading days and CANNOT catch alpha decay — that is
tier 2's job, by design.

**Tier 2 — weekly/monthly, slow (alpha-scale):**
[`compute_safef_car25`](../../backtester/safef_car25.py#L94) weekly on
the rolling paper record (once ≥126 obs; `min_history_days` guard);
**alarm = safe_f < 1.0 sustained 2 consecutive weeks → REDUCE to
safe_f × gross; safe_f < 0.5 → FLATTEN + review.** Monthly: deep-window
re-measurement cadence (the T-151/T-152 refresh commands) compared
against the paper record.

**The manual-action rule (ops playbook, restated as the contract): the
only permitted manual interventions are REDUCE and FLATTEN.** No
manual adds, no threshold loosening while running, no "just this once."

---

## 4. Account routing (Roth-first) and what paper cannot teach

Paper emulates the **Roth** account: T-141's verdict is now
thrice-convicted for taxable at current turnover (tax>profit; tax
channel 29× cost; taxable safe_f 0.273), and
[`validate_routing`](../../core/account_router.py#L85) RULE A already
flags the st-heavy core book in taxable without after-tax evidence.
Paper config: one Alpaca paper account, $5K starting equity (the
deployment tier — which is exactly why dyn-opt must be ON), config
labeled `account=roth`.

**Router enforcement in shadow:** even single-account, the
[`CrossAccountWashSaleChecker.check_trade`](../../core/account_router.py#L216)
runs on every staged order with taxable losses fed from a simulated
taxable twin (`record_taxable_loss`,
[`:209`](../../core/account_router.py#L209)) so the blackout logic
accumulates operational history before it ever gates real orders.

**What paper structurally CANNOT teach (stated per the brief):** tax
drag (paper has no taxes — the after-tax gate stays in the loop by
running [`compute_after_tax_report`](../../backtester/after_tax_metrics.py#L74)
over the paper fill log as an as-if-taxable counterfactual, reported
weekly); real multi-account wash-sale interplay; auction queue behavior
at sizes that matter (ours don't); and anything about ALPHA (60 paper
days is statistically nothing — paper validates the MACHINE, the
deep-window measurements validate the edge; promotion criteria are
therefore operational, not performance-based).

---

## 5. Promotion criteria (pre-registered numbers — proposal, user-gated)

Paper must show ALL of the following before any real-money
conversation (calendar-gated AND event-gated):

1. **Duration:** ≥60 trading days (~3 months), including ≥1 OPEX week
   and ≥1 FOMC day.
2. **Slippage truth:** median |fill − T-146 expected auction print| ≤ 5
   bps and p95 ≤ 20 bps across ≥100 auction fills (else the T-146
   safety-bps parameter is re-fit and the clock restarts).
3. **Reconciliation:** clean-rate ≥ 99% of cycles; ZERO unexplained
   cash/position drifts (every halt-class event root-caused).
4. **Monitor consistency:** tier-1 false alarms within calibration (≤1
   expected over the window; >3 ⇒ recalibrate against the paper regime
   — never loosen in place).
5. **Operational uptime:** missed-cycle rate ≤ 2%; zero
   missed-OPG-cutoff days caused by our pipeline (broker outages
   excluded, logged).
6. **Zero kill-rule violations:** no manual action other than
   REDUCE/FLATTEN occurred.

Passing ⇒ a user decision meeting with: the paper report, the
deep-window safe-f number, and the after-tax counterfactual. Failing
any criterion restarts its clock; three restarts of the same criterion
⇒ design review, not threshold relaxation.

---

## 6. The smallest build (3-4 propose-first PRs)

| PR | contents | gate class | effort | independently testable via |
|---|---|---|---|---|
| **PR-1 `paper_trader/` core** | `OrderManager` (submit/ack/poll, OPG+CLS TIF, deterministic `client_order_id`, journal append-only), `LedgerStore` (positions/cash as-we-believe), Alpaca paper REST client (env keys by NAME only) | **pure-new** (new dir; no engine imports; no live_trader edits) — buildable pre-approval in a sandbox if the user gates it that way | ~1 day | recorded-cassette tests + a real paper-API smoke (`submit 1 share OPG, poll, cancel`) |
| **PR-2 reconciliation + scheduler** | `ReconciliationEngine` (three-way diff, §2 taxonomy + responses, reconcile_log), daily scheduler skeleton with DRY-RUN mode (stages+logs, submits nothing) | **pure-new** | ~1 day | unit fixtures per divergence class + a dry-run day against the paper account |
| **PR-3 the loop** | `PaperLoopController`: production order-construction verbatim (Engine A signals → [`compute_target_allocations`](../../engines/engine_c_portfolio/portfolio_engine.py#L412) with dyn-opt ON → `prepare_order(target_weights=…)`) → OrderManager; T-152 feed adapter (backtest-expectation innovations → monitors → tier-1 actions in SHADOW first); T-141 shadow checker; T-151 weekly job; promotion-report generator | **propose-first** (imports production engines read-only; flips dyn-opt ON in the PAPER config only — backtest configs untouched) | ~1-2 days | one full simulated day (staged clock) + shadow week |
| **PR-4 cutover + archive** | archive `live_trader/`, `storage/state_manager.py`, `brokers/alpaca_broker.py` → `Archive/` (CLAUDE.md: never delete); remove/deprecate `AlpacaExecutionAdapter`'s synthetic-fill path; `deployment_boundary.md` update; arm tier-1 actions (shadow → live-on-paper) | **HARD-GATED** (touches `live_trader/` + the boundary doc) | ~0.5-1 day | the promotion-criteria report runs end-to-end |

Sequencing note: PR-1/PR-2 are safe to build immediately on approval of
this design (they touch nothing that exists); PR-3 is the integration
review; PR-4 is the formal boundary move. Total ≈ 3.5-5 agent-days.

**The single biggest gap, named:** there is no order-state machine
anywhere in the codebase — every existing path (stub, adapter, paper
controller) assumes submit==filled-at-intended-price. Everything else
(sizing, fills convention, kill metrics, routing, reconciliation
philosophy) already exists as shipped, tested code waiting to be
plugged in.
