import json
from paper_trader.paper_client import AlpacaPaperClient
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
print("FLAT=%s" % (not pos and not op))
