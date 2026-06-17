# Paper-Run Scorecard (machine validation) — T-169

**Purpose:** the operational §5 promotion-criteria scorecard for the
sustained paper run (Roth-emulation, `mean_variance`, dyn-opt ON). Paper
validates the MACHINE (order lifecycle, 3-way reconciliation, kill-
monitor false-alarm rate) — NOT the edge. The EDGE is judged separately
against the Schwab robo, net-of-costs/after-tax (deployment_boundary.md).

The §5 criteria (all must hold before any real-money conversation):
1. **Duration** ≥ 60 trading days (≥1 OPEX week + ≥1 FOMC day)
2. **Slippage truth**: median |fill − T-146 expected print| ≤ 5bps,
   p95 ≤ 20bps over ≥100 auction fills
3. **Reconciliation**: clean-rate ≥ 99% of cycles, ZERO unexplained drifts
4. **Monitor consistency**: tier-1 false alarms within calibration (≤1/window)
5. **Operational uptime**: missed-cycle ≤ 2%; zero missed-OPG-cutoff days (our pipeline)
6. **Zero kill-rule violations** (no manual action other than REDUCE/FLATTEN)

| metric | target | status (thru Day 2, 2026-06-17) |
|---|---|---|
| trading days | ≥60 | **2** |
| auction fills (real) | ≥100 | **0** (see OPG-window note — first fill lands the first in-window run) |
| slippage median / p95 vs T-146 | ≤5 / ≤20 bps | pending real fills |
| reconcile clean-rate | ≥99% | **100%** (3/3 Day 1, 3/3 Day 2) |
| unexplained drifts | 0 | **0** (account verified flat both days) |
| tier-1 monitor false-alarms | ≤1/window | 0 (shadow; ~0 obs) |
| missed-OPG-cutoff (our pipeline) | 0 | 0 |
| kill-rule violations | 0 | 0 |
| heartbeat / dead-man's-switch | canonical daily | **canonical** (Day 2 — `paper_heartbeat.json`, alert=false) |

## Day 1 (2026-06-15) — machine armed end-to-end on the LIVE paper account

- Config: account=roth, allocator=**mean_variance** (== designated;
  interlock fired), dyn-opt ON, auction=moo_moc, $5K.
- The armed loop walked the full §1.1 clock; **3/3 reconcile cycles
  clean** vs real broker truth; **account left FLAT** (0 positions, 0
  open orders).
- **FINDING (live-vs-design, caught Day 1, zero risk): Alpaca rejects an
  OPG order outside the 7:00pm–9:28am ET window** — `APIError code
  40310000, status 403: "opg orders must be submitted after 7:00pm and
  before 9:28am"`. The synchronous driver ran the clock at 17:38 ET
  (before 7pm) → the OPG submit was rejected; the M1 per-order guard
  caught it, journaled a schema-complete `submit_error`, and the day
  completed clean. **This is a SCHEDULING constraint, not a reject of
  our orders** — on the real daily cadence the `submit_opg` step fires
  at ~09:00 ET (inside the window) and succeeds. It SHARPENS the T-146
  live one-pager: the eligible OPG window is **7:00pm (prev day) →
  9:28am**, not merely "before 9:28am."
- No real fill yet (market closed + the OPG window). The fill→slippage
  telemetry begins the first time the loop runs `submit_opg` inside the
  window at a market open.

## Day 2 (2026-06-17) — the HOST-INDEPENDENT persistence pieces, live (T-185)

The OPG-window pre-check from Day 1's "Next-cadence" list is now BUILT.
The Day-2 driver (`scripts/run_paper_day_t185.py`) wires the three
host-independent persistence pieces against the live paper account:

- **Trading-calendar awareness** (`paper_trader/market_calendar.py`):
  `is_trading_day(2026-06-17)=True` via the authoritative Alpaca
  `get_calendar` (offline fallback skips weekends + a hard holiday set
  incl. Juneteenth 6/19). Non-trading days SKIP with no false alert.
- **Auction-window gate** (the T-169 finding, FIXED): the `submit_opg`
  step ran at 16:08 ET → outside the 7pm–9:28am window → the OPG batch
  was **DEFERRED (held STAGED), NOT error-submitted**. No code-40310000
  reject is generated anymore; orders wait for the window instead of
  bouncing off the broker. (The first real fill lands the first time the
  loop runs `submit_opg` inside the window at a market open.)
- **Dead-man's-switch heartbeat** (`paper_trader/heartbeat.py`): every
  run records to `data/state/paper_heartbeat.json` (schema
  `paper_heartbeat/v1`) in `run_day`'s `finally` (so even a crash leaves
  a trace); a daily `check()` verifies today RAN and was CANONICAL,
  alerting on a miss or non-canonical run via three channels (loud log +
  status-file `alert` flag the dashboard reads + append-only alert log /
  optional `PAPER_NOTIFY_WEBHOOK`). Day-2 verdict: **canonical, alive,
  alert=false** ("today's run happened + canonical"). Canonical for a
  paper run reuses C's `core/census.py:assert_census` so the
  canonical/non-canonical verdict can't diverge between paths.

Day-2 result: **3/3 reconcile cycles clean** vs live broker truth,
account left FLAT, OPG correctly deferred, heartbeat green. The machine
is now safe to run unattended on a trading day — it refuses to fire
outside the window, skips non-trading days, and screams if a day is
missed or non-canonical.

**Reconcile-on-restart self-heal: PROVEN** (not assumed) —
`tests/test_paper_persistence_t185.py::TestReconcileOnRestart`: a crash
mid-cycle → restart from the journal → re-adopts broker truth, ZERO new
POSTs (idempotent `client_order_id` across restart), resumes to fill;
and a crash after the SUBMITTED intent but before the POST landed →
restart reverts to STAGED (deliberate re-submit, never blind-resubmit).

Still host-SPECIFIC and NOT yet built (awaits director+user host
decision): the actual scheduler trigger — launchd plist (Mac) OR
EventBridge→Fargate (cloud). The loop logic is host-agnostic; only the
"fire once per trading day" trigger is host-bound.

## Combined-candidate vs robo (the real deploy gate — director rec, T-172)

Paper validates the MACHINE; the **EDGE** is judged separately against
the Schwab robo, net-of-costs/after-tax (`GOAL.md`). Track BOTH lines:

- **`base alone`** — the system's equity book (26yr re-anchor: Sharpe
  0.751, ci_low 0.382, −33% MDD; honest near-term read: likely does NOT
  beat a robo net-of-cost today — bull-conditional/beta-driven).
- **`base + 20% DBMF`** (the real candidate) — 80% base + 20% bought
  managed-futures sleeve (DBMF), monthly rebal. The 20% DBMF is
  SIMULATED from its free daily returns (Stooq `dbmf.us`, inception
  ~2019) — **not actually held in the paper account** (nothing to
  validate in a buy-and-hold ETF). This is the validated crisis FLOOR
  (T-170/171). The T-172/178 regime amplifier was TESTED (T-178) and did
  NOT beat always-on 20% net-of-cost OOS → **always-on 20% is the
  deployable sleeve; the combined line uses the fixed 20%, not a
  dynamic sizer.**
- **robo benchmark** — a low-cost moderate index+satellite proxy
  (≈60/40: 60% SPY / 40% AGG, or Schwab SWYGX moderate-growth), net of
  a typical robo fee (~0.08%/yr). Net-of-cost AND after-tax (taxable
  sleeve via the T-141 model; Roth = pre-tax).

**Status (2026-06-16):** methodology fixed; the live comparison accrues
as the paper run produces base returns. The historical
`base+20%DBMF vs robo` computation is the bought-MF-sleeve A/B lane's
deliverable (A's T-170/171, on the 26yr re-anchor) — to be folded here
once that A/B posts. The honest prior (GOAL.md): base-alone likely
loses to the robo today; the combined line is where the real candidate
must win.

## Next-cadence actions

- Run the loop daily with the submit step inside the OPG window (the
  §1.1 09:00 ET slot) → real fills → slippage-vs-T-146 telemetry begins.
  The first in-window run (e.g. a 7pm–9:28am ET invocation) submits the
  queued OPG → fills at the next open → the slippage line starts moving.
- ~~Reject-rate map: code 40310000 (outside-window)... map it to a
  "submission-window" pre-check in the scheduler~~ **DONE (T-185)** —
  the scheduler now DEFERS an outside-window auction batch (holds it
  STAGED), so 40310000 is no longer generated. The genuine-reject rate
  is clean of wall-clock artifacts by construction.
- Kill ACTIONS stay SHADOW for the first stretch (observe the divergence
  null + false-alarm rate); arm reduce/flatten later per the criteria.

## Live-size cap — canonical deep-window safe_f (T-178)

**safe_f = 0.928** on the canonical 26yr re-anchor curve (158fe678, MDD −33%; mdd95@f1 21.3%). The eventual live size cap = `min(1, safe_f)` = **0.928** (book ~7% oversized at f=1). Supersedes the benign-2024 1.602 and the 12yr-interim 1.104.
