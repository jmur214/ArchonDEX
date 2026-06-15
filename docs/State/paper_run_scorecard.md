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

## Next-cadence actions

- Run the loop daily with the submit step inside the OPG window (the
  §1.1 09:00 ET slot) → real fills → slippage-vs-T-146 telemetry begins.
- Reject-rate map: code 40310000 (outside-window) is a wall-clock
  artifact, not an order reject — exclude it from the genuine-reject
  rate; map it to a "submission-window" pre-check in the scheduler
  (followup: gate `submit_opg` on `7pm ≤ now < 9:28am`).
- Kill ACTIONS stay SHADOW for the first stretch (observe the divergence
  null + false-alarm rate); arm reduce/flatten later per the criteria.
