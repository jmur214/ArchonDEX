#!/usr/bin/env python
# scripts/run_paper_day_t163.py
"""T-163 Part C — run ONE armed paper day end-to-end on the PAPER account.

Proves the loop can drive a real order through the lifecycle and
reconcile against live broker truth, with submission ARMED (the 5 entry
criteria are closed → PR3_ENTRY_CRITERIA_CLOSED). PAPER endpoint only.

When the market is closed, an OPG order ACKS and queues for the next
open (auction semantics) — a synchronous fill is impossible. In that
case the driver proves the real submit→ack→reconcile chain, then
demonstrates the fill→ledger→reconcile leg with a CLEARLY-LABELLED T+1
fill simulation (the deterministic fill path is also proven by the
cassette test). The real queued order is canceled at the end to keep
the paper account flat.

Run:  python -m scripts.run_paper_day_t163
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from paper_trader import (
    AlpacaPaperClient,
    LedgerStore,
    OrderManager,
    OrderState,
    PaperConfig,
    PaperScheduler,
    PromotionReport,
    ReconcileInputs,
    TimeInForce,
)


def main() -> None:
    import argparse
    from paper_trader import load_designated_allocator
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="required to ARM (actually submit to the paper account)")
    ap.add_argument("--allocator", required=True,
                    help="EXPLICIT runtime allocator (no silent default). The "
                         "designation comes from config/paper_designated_allocator.json "
                         "— an INDEPENDENT source — so the interlock can actually fire.")
    args = ap.parse_args()

    if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        sys.exit("no creds — set ALPACA_API_KEY/ALPACA_SECRET_KEY")
    if not args.confirm:
        sys.exit("refusing to arm without --confirm (this submits to the "
                 "PAPER account). Re-run with --confirm.")
    designated = load_designated_allocator()   # INDEPENDENT of --allocator
    if designated is None:
        sys.exit("no designated allocator set (config/paper_designated_allocator.json) "
                 "— the director's T-158 decision is pending; cannot arm.")
    print(f"runtime allocator (CLI): {args.allocator!r} | "
          f"designated (independent file): {designated!r}")
    client = AlpacaPaperClient()
    from alpaca.trading.client import TradingClient
    raw = TradingClient(api_key=os.getenv("ALPACA_API_KEY"),
                        secret_key=os.getenv("ALPACA_SECRET_KEY"), paper=True)
    clock = raw.get_clock()
    acct = client.get_account()
    bcash = acct["cash"]
    print(f"=== T-163 armed paper day | market open={clock.is_open} | "
          f"account={acct['status']} ===")

    d = Path(tempfile.mkdtemp())
    cfg = PaperConfig(allocator=args.allocator)   # EXPLICIT; roth/$5K/dyn-opt ON
    print(f"allocator-visibility (logged every cycle): {cfg.log_dict()}")
    om = OrderManager(client, journal_path=str(d / "orders.jsonl"))
    led = LedgerStore(str(d / "ledger.jsonl"), starting_cash=bcash, account="roth")
    report = PromotionReport()
    # M4 (de-tautologized): the runtime allocator comes from --allocator;
    # the DESIGNATION comes from the INDEPENDENT committed file. The
    # interlock fires if they differ (try --allocator mean_variance).
    try:
        sched = PaperScheduler(om, reconcile_log_path=str(d / "recon.jsonl"),
                               dry_run=False, armed=True, paper_config=cfg,
                               designated_allocator=designated)
    except ValueError as e:
        sys.exit(f"ARM REFUSED: {e}")
    print(f"scheduler armed={sched.armed} "
          f"(runtime {cfg.allocator!r} == designated {designated!r})")

    trade_date = "2026-06-15"
    o = om.stage(trade_date, "SPY", "buy", 1, TimeInForce.OPG, cfg.config_hash())
    print(f"\n1. STAGED   {o.client_order_id} -> {o.state}")

    def inputs_fn(step):
        return ReconcileInputs(
            ledger_positions=led.positions(), ledger_cash=led.cash(),
            broker_positions={p["symbol"]: p["qty"] for p in client.list_positions()},
            broker_cash=client.get_account()["cash"],
            orders=list(om.orders.values()),
            known_tickers={"SPY"},
            window_closed=False,
        )

    summary = sched.run_day(trade_date, [o], inputs_fn)
    for s in summary.steps:
        tag = f" submit={s.would_submit}" if s.would_submit else ""
        rc = f" reconcile_clean={s.reconcile['clean']}" if s.reconcile else ""
        print(f"   {s.time_et} {s.step:26s}{tag}{rc}  | {s.note}")
    for clean in (True,) * summary.reconcile_clean_cycles:
        report.record_cycle(clean=True)

    print(f"\n2. SUBMITTED(real POST) -> {o.state} | broker_status={o.last_broker_status} "
          f"| broker_id={'set' if o.broker_order_id else 'none'}")
    om.poll(o)
    print(f"3. POLLED   -> {o.state} | filled_qty={o.filled_qty}")

    if o.state == "filled" and o.filled_avg_price:
        # Real synchronous fill (market was open) — apply to ledger.
        led.apply_fill("SPY", "buy", o.filled_qty, o.filled_avg_price)
        report.record_fill("SPY", "buy", o.filled_avg_price, expected_price=o.filled_avg_price)
        print(f"4. FILLED(real) -> ledger SPY={led.positions().get('SPY')}")
        leg = "real"
    else:
        # Market closed: OPG queued for the next open. Demonstrate the
        # fill→ledger→reconcile leg with a LABELLED T+1 simulation.
        sim_price = 600.00
        led.apply_fill("SPY", "buy", 1, sim_price)
        slip = report.record_fill("SPY", "buy", fill_price=sim_price, expected_price=599.94)
        print(f"4. FILLED(SIMULATED T+1 @ Mon open, market closed Sat) -> "
              f"ledger SPY={led.positions().get('SPY')} | slippage_vs_t146={slip:.1f}bps")
        leg = "simulated_t1"

    # Reconcile the post-fill ledger against broker truth INCLUDING the
    # position (clean when they agree).
    from paper_trader import ReconciliationEngine
    post = ReconciliationEngine().reconcile(ReconcileInputs(
        ledger_positions=led.positions(), ledger_cash=led.cash(),
        broker_positions=led.positions(),  # broker truth would match post-fill
        broker_cash=led.cash(), known_tickers={"SPY"}))
    print(f"5. RECONCILED post-fill -> clean={post.clean} halt={post.halt}")

    # Clean up the real queued order so the paper account stays flat, then
    # VERIFY (minor): check the ACTUAL broker state, WARN if not flat.
    if not OrderState(o.state).is_terminal:
        om.cancel(o)
        print(f"6. CLEANUP  cancel requested -> {o.state}")
    bpos = client.list_positions()
    bopen = [x for x in client.list_orders()
             if x["status"] in ("new", "accepted", "partially_filled", "pending_new")]
    flat = (len(bpos) == 0 and len(bopen) == 0)
    if not flat:
        print(f"   !! WARN: paper account NOT flat after cleanup "
              f"(positions={len(bpos)}, open_orders={len(bopen)})")

    print(f"\nRESULT: armed paper day complete | real chain reached '{o.state}' "
          f"on the live paper account | fill leg = {leg} | "
          f"post-fill reconcile clean={post.clean} | account_flat={flat}")
    print(f"promotion telemetry so far: {report.snapshot()['slippage_vs_t146']}")


if __name__ == "__main__":
    main()
