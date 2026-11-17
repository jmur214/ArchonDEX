import datetime as dt, inspect, json, sys
from paper_trader.paper_client import AlpacaPaperClient
D = "__D__"; ATTEMPT = __ATTEMPT__; EXECUTE = __EXECUTE__      # the execute job changes ONLY EXECUTE
EXPECT = __EXPECT__          # from step 1's slice, re-confirmed at step 8
NO_TRADE_DATES = {"2026-11-26", "2026-11-27"}         # Thanksgiving; the 13:00 ET early close
c = AlpacaPaperClient()
acct = c._client.get_account()                       # read-only
clock = c._client.get_clock()                        # read-only
mins_left = (clock.next_close - clock.timestamp).total_seconds() / 60.0
raw = c.list_positions()
pos = {p["symbol"]: int(p["qty"]) for p in raw}
entry = {p["symbol"]: p.get("avg_entry_price") for p in raw}
TERM = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}
open_o = [o for o in c.list_orders() if str(o.get("status", "")).lower() not in TERM]
print("RESET-A2 account_number=%s equity=%s cash=%s" % (acct.account_number, acct.equity, acct.cash))
print("RESET-A2 positions_before=" + json.dumps(pos, sort_keys=True))
print("RESET-A2 broker_avg_entry=" + json.dumps(entry, sort_keys=True))
print("RESET-A2 open_orders=%d market_open=%s minutes_to_close=%.0f attempt=%d execute=%s"
      % (len(open_o), clock.is_open, mins_left, ATTEMPT, EXECUTE))
why = []
if D in NO_TRADE_DATES: why.append(f"D={D} is excluded")
if clock.timestamp.date().isoformat() != D: why.append(f"broker date {clock.timestamp.date()} != D {D}")
if not clock.is_open: why.append("market closed")
if mins_left < 30: why.append(f"only {mins_left:.0f} min to the close")
if pos != EXPECT: why.append(f"positions {pos} != EXPECT {EXPECT}")
if open_o: why.append(f"{len(open_o)} open order(s)")
if why:
    print("RESET-A2 REFUSED: " + "; ".join(why)); sys.exit(70)
failed = []
for t, q in sorted(pos.items()):
    kw = dict(client_order_id=f"reset-a2-{D}-{t}-sell-a{ATTEMPT}", symbol=t, qty=q,
              side="sell", tif="day")
    try:
        inspect.signature(c.submit_order).bind(**kw)
        if EXECUTE:
            print("RESET-A2 submitted " + json.dumps(c.submit_order(**kw), default=str)[:300])
        else:
            print(f"RESET-A2 DRY-RUN would sell {q} {t} coid={kw['client_order_id']} (signature binds)")
    except Exception as exc:                          # one failure never hides the others
        failed.append(t)
        print(f"RESET-A2 FAILED {t}: {type(exc).__name__}: {str(exc)[:200]}")
print("RESET-A2 RESULT " + ("FAILED " + ",".join(failed) if failed else "ok"))
sys.exit(70 if failed else 0)
