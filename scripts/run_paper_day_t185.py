#!/usr/bin/env python
# scripts/run_paper_day_t185.py
"""T-185 — a window-aware, calendar-aware, heartbeat-recording paper day.

The persistent Day-N driver. Unlike the T-163 one-shot, this wires the
HOST-INDEPENDENT persistence pieces:

  1. trading-calendar awareness (MarketCalendar, Alpaca-backed) — it only
     runs on a trading day and SKIPS weekends/holidays/early-closes;
  2. auction-window gating — an OPG/CLS batch outside its submission
     window is DEFERRED (held STAGED), never error-submitted (the T-169
     finding: Alpaca rejects an OPG outside 7pm-9:28am ET, code 40310000);
  3. the dead-man's-switch heartbeat — every run records a heartbeat +
     a daily check() verifies today ran AND was canonical, writing the
     status file the dashboard reads and ALERTING on a miss/non-canonical.

PAPER endpoint only. No live-money path. Creds by env-NAME only; values
are never printed.

Run:  python -m scripts.run_paper_day_t185 --confirm --allocator mean_variance
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from paper_trader import (
    AlpacaPaperClient,
    LedgerStore,
    MarketCalendar,
    OrderManager,
    PaperConfig,
    PaperHeartbeat,
    PaperScheduler,
    ReconcileInputs,
    TimeInForce,
    load_designated_allocator,
    now_et,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="required to ARM (actually submit to the paper account)")
    ap.add_argument("--allocator", required=True,
                    help="EXPLICIT runtime allocator; the designation comes from "
                         "config/paper_designated_allocator.json (independent source)")
    args = ap.parse_args()

    if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        sys.exit("no creds — set ALPACA_API_KEY/ALPACA_SECRET_KEY")
    if not args.confirm:
        sys.exit("refusing to arm without --confirm (this submits to the PAPER "
                 "account). Re-run with --confirm.")
    designated = load_designated_allocator()
    if designated is None:
        sys.exit("no designated allocator (config/paper_designated_allocator.json).")

    now = now_et()
    today = now.date()
    print(f"=== T-185 persistent paper day | now ET {now.isoformat()} "
          f"({now.strftime('%A')}) ===")
    print(f"runtime allocator (CLI): {args.allocator!r} | "
          f"designated (independent file): {designated!r}")

    client = AlpacaPaperClient()
    cal = MarketCalendar(client=client)               # Alpaca calendar authoritative
    hb = PaperHeartbeat()                             # writes data/state/paper_heartbeat.json

    # --- 1. calendar awareness --------------------------------------- #
    trading = cal.is_trading_day(today)
    print(f"\n1. CALENDAR  is_trading_day({today}) = {trading} | "
          f"OPG-window-open-now = {cal.is_opg_window(now)} | "
          f"CLS-window-open-now = {cal.is_cls_window(now)}")
    if not trading:
        print("   non-trading day → SKIP (no run, no false alert).")
        v = hb.check(today, is_trading_day=False)
        print(f"   heartbeat.check → alive={v.alive} alert={v.alert} ({v.reason})")
        return

    # --- 2. arm with the interlock ----------------------------------- #
    cfg = PaperConfig(allocator=args.allocator)
    acct = client.get_account()
    bcash = acct["cash"]
    print(f"   account status={acct['status']}  (cash redacted)")
    d = Path(tempfile.mkdtemp())
    om = OrderManager(client, journal_path=str(d / "orders.jsonl"))
    led = LedgerStore(str(d / "ledger.jsonl"), starting_cash=bcash, account="roth")
    try:
        sched = PaperScheduler(
            om, reconcile_log_path=str(d / "recon.jsonl"),
            dry_run=False, armed=True, paper_config=cfg,
            designated_allocator=designated, calendar=cal, heartbeat=hb)
    except ValueError as e:
        sys.exit(f"ARM REFUSED (interlock): {e}")
    print(f"\n2. ARMED     runtime {cfg.allocator!r} == designated {designated!r} "
          f"→ armed={sched.armed}")

    # --- 3. window-aware run ----------------------------------------- #
    o = om.stage(str(today), "SPY", "buy", 1, TimeInForce.OPG, cfg.config_hash())
    print(f"\n3. STAGED    {o.client_order_id} → {o.state}")

    def inputs_fn(step):
        return ReconcileInputs(
            ledger_positions=led.positions(), ledger_cash=led.cash(),
            broker_positions={p["symbol"]: p["qty"] for p in client.list_positions()},
            broker_cash=client.get_account()["cash"],
            orders=list(om.orders.values()),
            known_tickers={"SPY"},
            window_closed=False,
        )

    # account_flat: is the paper book flat right now? (True ⇒ canonical-eligible)
    flat = len(client.list_positions()) == 0
    summary = sched.run_trading_day(str(today), [o], inputs_fn, account_flat=flat)
    if summary is None:
        print("   run_trading_day returned None (skipped) — unexpected on a trading day.")
        return

    print("\n4. STEPS")
    for s in summary.steps:
        note = f"  — {s.note}" if getattr(s, "note", "") else ""
        print(f"   {s.time_et:>6s} {s.step:14s}{note}")
    print(f"   reconcile: {summary.reconcile_clean_cycles}/"
          f"{summary.reconcile_total_cycles} clean | halted={summary.halted}")
    print(f"   final order state: {o.state}")

    # --- 5. heartbeat / dead-man's-switch ---------------------------- #
    v = hb.check(today, is_trading_day=True)
    print(f"\n5. HEARTBEAT alive={v.alive} alert={v.alert} | {v.reason}")
    print(f"   status file: data/state/paper_heartbeat.json (dashboard reads this)")

    # keep the paper account flat: cancel any LIVE order we queued.
    for rec in list(om.orders.values()):
        if rec.state in ("acked", "submitted", "partial"):
            try:
                client.cancel_order(rec.broker_order_id)
                print(f"   cleanup: canceled live order {rec.broker_order_id}")
            except Exception as exc:
                print(f"   cleanup: cancel skipped ({type(exc).__name__})")


if __name__ == "__main__":
    main()
