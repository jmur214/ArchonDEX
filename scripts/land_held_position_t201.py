#!/usr/bin/env python
# scripts/land_held_position_t201.py
"""T-201 — land a REAL held position the cloud loop can explain.

The first OPG (`4dcffc7c`, first_real_fill_t186.py) was CANCELED at the
6/18 open with 0 fill, so the held-position path has never been
live-exercised. The user chose to land a fill via the CLOSE auction (CLS)
and then run the held-position live re-verify.

Generalized OPG/CLS sibling of first_real_fill_t186.py (which is left
untouched). Submits ONE real auction order through the loop's OrderManager
(so it is JOURNALED), leaves it QUEUED (never cancels — it must fill), and
pushes the journal to S3 so the cloud loop sees the FILLED order and can
``adopt_explained_broker_truth`` the resulting held position.

Auction-only by design (T-146 / TimeInForce is OPG|CLS only): there is no
instant market order, so the soonest a held position exists is the next
auction —
  * CLS: submit before the ~15:50 ET MOC cutoff → fills at the 16:00 close;
  * OPG: submit inside 7:00pm-9:28am ET → fills at the next 09:30 open.
Refuses cleanly (like the OPG script) if outside the chosen window.

PAPER only; creds by env-NAME only, never echoed. FAIL-SAFE: an
indeterminate submit ⇒ leave nothing half-known, never double-submit.

Run (CLS, before 15:50 ET):
  ARCHONDEX_PAPER_STATE_BUCKET=archondex-results-407539788432 \\
  AWS_PROFILE=archondex \\
  python -m scripts.land_held_position_t201 --confirm --tif cls --ticker SPY --qty 1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from paper_trader import (
    AlpacaPaperClient,
    MarketCalendar,
    OrderManager,
    OrderState,
    PaperConfig,
    TimeInForce,
    load_designated_allocator,
    now_et,
)
from paper_trader.cloud_state import CloudState

STATE_DIR = "data/paper_state"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="required — actually submits a real paper order")
    ap.add_argument("--tif", choices=["opg", "cls"], default="cls",
                    help="auction: cls (close, ~15:50 ET cutoff) or opg (open)")
    ap.add_argument("--ticker", default="SPY")
    ap.add_argument("--qty", type=int, default=1)
    ap.add_argument("--allocator", default="mean_variance")
    args = ap.parse_args()

    if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        print("no creds — set ALPACA_API_KEY/ALPACA_SECRET_KEY", file=sys.stderr)
        return 64
    if not args.confirm:
        print("refusing without --confirm (this submits a REAL paper order).",
              file=sys.stderr)
        return 1
    designated = load_designated_allocator()
    if designated != args.allocator:
        print(f"allocator interlock: runtime {args.allocator!r} != designated "
              f"{designated!r} — refusing.", file=sys.stderr)
        return 66

    now = now_et()
    today = now.date()
    client = AlpacaPaperClient()
    cal = MarketCalendar(client=client)
    tif = args.tif
    print(f"=== T-201 land held position ({tif.upper()}) | {now.isoformat()} "
          f"({now.strftime('%A')}) ===")

    if not cal.is_trading_day(today):
        print(f"{today} is not a trading day — refusing (next auction is a "
              "later session).", file=sys.stderr)
        return 2
    in_window = (cal.is_opg_window(now) if tif == "opg"
                 else cal.is_cls_window(now))
    if not in_window:
        win = ("7:00pm-9:28am ET" if tif == "opg"
               else "before ~15:50 ET (MOC cutoff)")
        print(f"NOT in the {tif.upper()} window ({win}) — a submit now would be "
              "rejected by the broker. Re-run inside the window (CLS fills at the "
              "16:00 close; OPG at the next 09:30 open).", file=sys.stderr)
        return 3

    root = Path(__file__).resolve().parents[1]
    cloud = CloudState(root=str(root))
    cloud.pull()
    state = root / STATE_DIR
    state.mkdir(parents=True, exist_ok=True)

    cfg = PaperConfig(allocator=args.allocator)
    acct = client.get_account()
    print(f"account status={acct['status']} (cash redacted) | "
          f"open positions before: {len(client.list_positions())}")

    om = OrderManager(client, journal_path=str(state / "orders.jsonl"))
    tkr = args.ticker.upper()
    tif_enum = TimeInForce.OPG if tif == "opg" else TimeInForce.CLS
    o = om.stage(str(today), tkr, "buy", args.qty, tif_enum, cfg.config_hash())
    print(f"\nSTAGED   {o.client_order_id} -> {o.state}")

    o = om.submit(o)
    print(f"SUBMIT   -> {o.state} | broker_order_id={o.broker_order_id}")

    if o.state not in (OrderState.ACKED.value, OrderState.FILLED.value,
                       OrderState.PARTIALLY_FILLED.value):
        print(f"\nUNEXPECTED post-submit state {o.state!r} — NOT leaving a "
              "half-known order; inspect before retry (fail-safe).", file=sys.stderr)
        cloud.push()
        return 4

    cloud.push()   # durably record the queued order for the cloud loop
    fill_when = ("the 16:00 ET close" if tif == "cls" else "the next 09:30 ET open")
    print(f"\nQUEUED ({tkr} x{args.qty} {tif.upper()}) — left on the book to fill "
          f"at {fill_when}. Durable journal pushed-to-s3={cloud.cfg.enabled}.")
    print("After it fills, run the held-position re-verify (Fargate paper job): "
          "the loop pulls this journal, polls the FILLED order, adopts the held "
          "position into the ledger, and reconciles clean → canonical.")
    print(f"\nbroker_order_id={o.broker_order_id}  state={o.state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
