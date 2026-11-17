import json
from paper_trader.paper_client import AlpacaPaperClient
from paper_trader.market_calendar import ET     # America/New_York, as the daily run uses
D = "__D__"; ATTEMPT = __ATTEMPT__; TICKERS = __TICKERS__   # TICKERS=[] → a plain flat-check
c = AlpacaPaperClient(); a = c._client.get_account(); pos = c.list_positions()
TERM = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}
op = [o for o in c.list_orders() if str(o.get("status", "")).lower() not in TERM]
print("FLATCHECK " + json.dumps({"account_number": a.account_number, "status": str(a.status),
      "equity": str(a.equity), "cash": str(a.cash), "n_positions": len(pos),
      "n_open_orders": len(op), "positions": pos}, default=str))
for t in TICKERS:
    o = c.get_order(f"reset-a2-{D}-{t}-sell-a{ATTEMPT}")
    print("FILL " + t + " " + (json.dumps({k: o.get(k) for k in ("status", "filled_qty",
          "filled_avg_price", "filled_at")}, default=str) if isinstance(o, dict) else repr(o)))
clk = c._client.get_clock()                          # read-only: the operator sees the time
print("CLOCK " + json.dumps({"et": clk.timestamp.astimezone(ET).isoformat(), "is_open": clk.is_open,
      "next_close": clk.next_close.astimezone(ET).isoformat()}))
print("FLAT=%s" % (not pos and not op))
