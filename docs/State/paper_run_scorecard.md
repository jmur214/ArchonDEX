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

| metric | target | status (Day 1, 2026-06-15) |
|---|---|---|
| trading days | ≥60 | **1** |
| auction fills (real) | ≥100 | **0** (see OPG-window note) |
| slippage median / p95 vs T-146 | ≤5 / ≤20 bps | pending real fills |
| reconcile clean-rate | ≥99% | **100%** (3/3 cycles Day 1) |
| unexplained drifts | 0 | **0** (account verified flat) |
| tier-1 monitor false-alarms | ≤1/window | 0 (shadow; ~0 obs) |
| missed-OPG-cutoff (our pipeline) | 0 | 0 |
| kill-rule violations | 0 | 0 |

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
- Reject-rate map: code 40310000 (outside-window) is a wall-clock
  artifact, not an order reject — exclude it from the genuine-reject
  rate; map it to a "submission-window" pre-check in the scheduler
  (followup: gate `submit_opg` on `7pm ≤ now < 9:28am`).
- Kill ACTIONS stay SHADOW for the first stretch (observe the divergence
  null + false-alarm rate); arm reduce/flatten later per the criteria.

## Live-size cap — canonical deep-window safe_f (T-178)

**safe_f = 0.928** on the canonical 26yr re-anchor curve (158fe678, MDD −33%; mdd95@f1 21.3%). The eventual live size cap = `min(1, safe_f)` = **0.928** (book ~7% oversized at f=1). Supersedes the benign-2024 1.602 and the 12yr-interim 1.104.
