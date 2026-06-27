#!/usr/bin/env python
# scripts/run_paper_cloud_day.py
"""T-186 — one paper day in the cloud (EventBridge → Fargate → here).

The host-bound trigger fires this once per day. Everything host-INDEPENDENT
(calendar self-skip, auction-window DEFER, the dead-man's-switch heartbeat,
reconcile-on-restart) is T-185; this driver adds the cloud glue:

  1. PULL durable state from S3 (orders journal / ledger / heartbeat /
     alert log) → local disk, so a fresh container resumes yesterday's
     memory (Fargate disk is ephemeral). A first-ever run starts clean.
  2. Run the T-185 calendar-aware daily cycle (run_trading_day) — it
     self-skips weekends/holidays and DEFERS out-of-window auctions.
  3. PUSH durable state back to S3 + EMIT the CloudWatch dead-man's-switch
     datapoints (PaperRunHappened / PaperRunCanonical).
  4. EXIT NON-ZERO if the run was non-canonical, so Batch marks the job
     FAILED and the failure alarm fires (defence-in-depth with the
     metric alarm + the heartbeat status file the dashboard reads).

By default this runs the daily PULSE (reconcile broker truth + record the
heartbeat) with NO staged orders — it proves the loop ran and the account
state reconciles, WITHOUT accumulating a position. The engine-driven order
set (PaperOrderConstructor, the content layer) is wired separately; this
is the trigger/persistence/heartbeat milestone.

Creds: ALPACA_API_KEY / ALPACA_SECRET_KEY arrive as env vars injected by
the Batch job definition's ``secrets`` block (AWS Secrets Manager) — this
script never fetches or logs them. PAPER endpoint only.

Run (locally, against the paper account, durable state in S3):
  ARCHONDEX_PAPER_STATE_BUCKET=archondex-results-407539788432 \\
  AWS_PROFILE=archondex \\
  python -m scripts.run_paper_cloud_day --allocator mean_variance
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from paper_trader import (
    AlpacaPaperClient,
    LedgerStore,
    MarketCalendar,
    OrderManager,
    OrderState,
    PaperConfig,
    PaperHeartbeat,
    PaperScheduler,
    ReconcileInputs,
    load_designated_allocator,
    now_et,
)
from paper_trader.cloud_state import CloudState
from paper_trader.held_reconcile import (
    adopt_explained_broker_truth,
    known_tickers_for,
)

STATE_DIR = "data/paper_state"


def main(argv=None, *, now=None, client=None, cloud=None) -> int:
    """Run one cloud paper day. ``now``/``client``/``cloud`` are injectable
    for tests (drive a non-trading day, a held position, etc. without a
    real broker); production passes none and they are constructed live."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocator", required=True,
                    help="EXPLICIT runtime allocator; designation is the "
                         "independent config/paper_designated_allocator.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the cycle WITHOUT arming submission (observe only)")
    ap.add_argument("--strategy", choices=["reconcile_only", "trend_sleeve"],
                    default="reconcile_only",
                    help="reconcile_only = the daily pulse (no orders, the proven "
                         "default); trend_sleeve = construct + submit the T-204 "
                         "3-asset trend sleeve (T-238 paper validation)")
    ap.add_argument("--sleeve-notional-cap", type=float, default=None,
                    help="cap the $ the sleeve sizes to (cautious FIRST armed run); "
                         "unset = full account equity (the real validation)")
    args = ap.parse_args(argv)

    if client is None and not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        print("FATAL: no Alpaca creds in env (expected from Secrets Manager).",
              file=sys.stderr)
        return 64
    designated = load_designated_allocator()
    if designated is None:
        print("FATAL: no designated allocator.", file=sys.stderr)
        return 65

    root = Path(__file__).resolve().parents[1]
    cloud = cloud if cloud is not None else CloudState(root=str(root))
    now = now or now_et()
    today = now.date()
    client = client or AlpacaPaperClient()
    print(f"=== T-186 cloud paper day | {now.isoformat()} ({now.strftime('%A')}) "
          f"| state={'S3:' + cloud.cfg.s3_root if cloud.cfg.enabled else 'LOCAL'} ===")

    # --- 1. pull durable state (resume yesterday's memory) ------------- #
    pulled = cloud.pull()
    print(f"1. STATE     pulled-from-s3={pulled} (clean start if False)")

    cal = MarketCalendar(client=client)
    hb = PaperHeartbeat()

    # Non-trading day: skip cleanly. Still emit a 'happened' pulse so the
    # silent-stop alarm sees the schedule fired (the calendar — not a dead
    # loop — is why nothing traded). The heartbeat check() treats it alive.
    if not cal.is_trading_day(today):
        print(f"2. CALENDAR  {today} is not a trading day → SKIP (no run).")
        cloud.emit_metrics(happened=True, canonical=True)
        cloud.push()
        v = hb.check(today, is_trading_day=False)
        print(f"3. HEARTBEAT alive={v.alive} alert={v.alert} ({v.reason})")
        return 0

    # --- 2. armed daily cycle ----------------------------------------- #
    cfg = PaperConfig(allocator=args.allocator)
    state = root / STATE_DIR
    state.mkdir(parents=True, exist_ok=True)
    acct = client.get_account()
    om = OrderManager(client, journal_path=str(state / "orders.jsonl"))
    led = LedgerStore(str(state / "ledger.jsonl"),
                      starting_cash=acct["cash"], account="roth")
    armed = not args.dry_run
    try:
        sched = PaperScheduler(
            om, reconcile_log_path=str(state / "recon.jsonl"),
            dry_run=args.dry_run, armed=armed,
            paper_config=cfg if armed else None,
            designated_allocator=designated if armed else None,
            calendar=cal, heartbeat=hb)
    except ValueError as e:
        print(f"FATAL: ARM REFUSED (interlock): {e}", file=sys.stderr)
        cloud.emit_metrics(happened=True, canonical=False)
        cloud.push()
        return 66
    print(f"2. ARMED     armed={sched.armed} (runtime {cfg.allocator!r} "
          f"== designated {designated!r})")

    # --- T-198: converge the ledger to broker truth for the EXPLAINED part
    # BEFORE the reconcile cycles run, so a legitimately-held position (e.g.
    # the manual first fill, filled at the open) does NOT read as drift. ---
    # Poll non-terminal orders so the journal reflects any fills.
    for o in list(om.orders.values()):
        st = OrderState(o.state)
        if not st.is_terminal and st != OrderState.STAGED:
            try:
                om.poll(o)
            except Exception:
                pass   # FAIL-SAFE: an indeterminate poll ⇒ assume nothing
    broker_positions = {p["symbol"]: int(p["qty"]) for p in client.list_positions()}
    broker_cash = client.get_account()["cash"]
    journal_orders = list(om.orders.values())
    account_explained = adopt_explained_broker_truth(
        led, broker_positions, broker_cash, journal_orders,
        reason=f"cloud cycle {today}")
    ktickers = known_tickers_for(journal_orders, led.positions())
    print(f"   RECONCILE  broker_positions={broker_positions} "
          f"account_explained={account_explained} (adopted into ledger)"
          if broker_positions else "   RECONCILE  account flat")

    def inputs_fn(step):
        return ReconcileInputs(
            ledger_positions=led.positions(), ledger_cash=led.cash(),
            broker_positions={p["symbol"]: int(p["qty"]) for p in client.list_positions()},
            broker_cash=client.get_account()["cash"],
            orders=list(om.orders.values()),
            known_tickers=ktickers,
            window_closed=False,
        )

    # --- content layer: reconcile-only pulse OR the trend sleeve (T-238) -- #
    staged: list = []
    sleeve_closes: dict = {}
    if args.strategy == "trend_sleeve":
        from paper_trader.sleeve_constructor import SleeveOrderConstructor, SLEEVE_UNIVERSE
        try:
            closes = client.fetch_daily_closes(list(SLEEVE_UNIVERSE), lookback_days=400)
        except Exception as exc:
            print(f"FATAL: [NN-FAIL-CLOSED] sleeve bars fetch failed: "
                  f"{type(exc).__name__}", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return 67
        # Causal guarantee: use ONLY completed prior-day closes — drop any
        # forming TODAY bar so the signal can never read an intraday price
        # (the 09:00 ET schedule is pre-open, but this holds at any run time).
        import pandas as _pd
        closes = {t: s[s.index < _pd.Timestamp(today)] for t, s in closes.items()}
        # [NN-FAIL-CLOSED]: never trade a STALE signal — every asset's last
        # completed bar must be recent (the prior session), else HALT.
        stale = [t for t in SLEEVE_UNIVERSE
                 if t not in closes or closes[t].empty
                 or (_pd.Timestamp(today) - closes[t].index[-1]).days > 5]
        if stale:
            print(f"FATAL: [NN-FAIL-CLOSED] sleeve price data missing/stale for "
                  f"{stale} — refusing to trade a stale signal.", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return 68
        equity = float(client.get_account().get("equity", broker_cash))
        sizing_equity = min(equity, args.sleeve_notional_cap) if args.sleeve_notional_cap else equity
        if args.sleeve_notional_cap:
            print(f"   SLEEVE     notional cap ${args.sleeve_notional_cap:,.0f} "
                  f"(account equity ${equity:,.0f}) — cautious first run")
        plan = SleeveOrderConstructor().construct(sizing_equity, broker_positions, closes)
        sleeve_closes = {t: float(closes[t].iloc[-1]) for t in SLEEVE_UNIVERSE}
        print(f"   SLEEVE     signals={plan.signals} targets={plan.targets} "
              f"→ {len(plan.orders)} order(s): "
              f"{[(o.ticker, o.side, o.qty) for o in plan.orders]}")
        for spec in plan.orders:
            staged.append(om.stage(str(today), spec.ticker, spec.side, spec.qty,
                                   spec.stage_args()["tif"], cfg.config_hash()))

    summary = sched.run_trading_day(str(today), staged, inputs_fn,
                                    account_explained=account_explained)

    # --- 3. heartbeat verdict → metrics + exit code ------------------- #
    v = hb.check(today, is_trading_day=True)
    canonical = bool(v.alive and not v.alert)
    print(f"3. CYCLE     reconcile {summary.reconcile_clean_cycles}/"
          f"{summary.reconcile_total_cycles} clean | halted={summary.halted}")
    print(f"4. HEARTBEAT alive={v.alive} alert={v.alert} | {v.reason}")

    # --- T-238 Part 2: forward-track the sleeve vs both robos ------------- #
    if args.strategy == "trend_sleeve" and sleeve_closes:
        try:
            from paper_trader.sleeve_tracker import SleeveTracker
            equity = float(client.get_account().get("equity", broker_cash))
            tsum = SleeveTracker(root=str(root)).record(str(today), equity, sleeve_closes)
            print(f"6. TRACK     sleeve forward vs robos: {tsum.get('status')} "
                  f"({tsum.get('n_days', tsum.get('sleeve', {}).get('n_days'))} pts)"
                  + (f" | sleeve MaxDD shallower than both robos="
                     f"{tsum.get('sleeve_mdd_shallower_than_both')}"
                     if tsum.get('status') == 'tracking' else ""))
        except Exception as exc:
            print(f"   TRACK warn: {type(exc).__name__} (non-fatal)")

    cloud.emit_metrics(happened=True, canonical=canonical)
    cloud.push()
    print(f"5. STATE     pushed-to-s3={cloud.cfg.enabled} | "
          f"metrics: PaperRunHappened=1 PaperRunCanonical={int(canonical)}")

    if not canonical:
        print("RESULT: NON-CANONICAL — exiting non-zero so the job is marked "
              "FAILED and the alarm fires.", file=sys.stderr)
        return 70
    print("RESULT: canonical/alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
