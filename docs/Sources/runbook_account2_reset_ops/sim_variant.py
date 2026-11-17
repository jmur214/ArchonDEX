"""Reviewer simulation (no network, no AWS, no broker): drive the REAL
scripts/run_paper_cloud_day.main() for account 2 from an EMPTY state prefix on a
FLAT broker (option B after liquidation), for D+1 (seeding) and D+2 (arrival)
and D+3 (first settled day). Everything is written under a temp root.

Usage: PYTHONDONTWRITEBYTECODE=1 python -I sim_variant.py <repo_root> <work_root> [cash] [rebase_start_date]
"""
import sys, os, json, shutil, datetime as dt
from zoneinfo import ZoneInfo

repo, work = sys.argv[1], sys.argv[2]
start_cash = float(sys.argv[3]) if len(sys.argv) > 3 else 103514.78
sys.path.insert(0, repo)
# COMMITTED COPY, 2026-11-17: the reviewer's original ran shutil.rmtree(work) here. A
# committed script must never delete a caller-supplied path ([NN-ARCHIVE]; a repo path
# passed by mistake would be wiped), so it now REFUSES an existing path or one inside
# the repo. Nothing else in this file differs from the reviewer's copy.
if os.path.exists(work):
    sys.exit(f"REFUSE: work root {work} already exists — pass a fresh path (this script never deletes)")
if os.path.realpath(work).startswith(os.path.realpath(repo) + os.sep):
    sys.exit(f"REFUSE: work root {work} is inside the repo")
os.makedirs(work)
os.chdir(work)  # any stray relative write lands in the scratch root, never the repo

# never let any import pull a .env into this process
import dotenv, dotenv.main
dotenv.load_dotenv = lambda *a, **k: False
dotenv.main.load_dotenv = lambda *a, **k: False
os.environ.pop("ALPACA_API_KEY", None); os.environ.pop("ALPACA_SECRET_KEY", None)
os.environ["ARCHONDEX_PAPER_ACCOUNT"] = "offense-sso"

import types
import pandas as pd
import scripts.run_paper_cloud_day as drv
from paper_trader.paper_client import FakePaperClient

os.makedirs(os.path.join(work, "config"))
for f in ("deploy_candidate.json", "substantially_identical.json"):
    shutil.copy(os.path.join(repo, "config", f), os.path.join(work, "config", f))
shutil.copy(os.path.join(repo, "config", "llm_settings.json"),
            os.path.join(work, "config", "llm_settings.json"))
# VARIANT (2026-11-17): optional 4th arg re-bases contributions.start_date in the
# WORK copy of config/deploy_candidate.json (the repo's file is never touched).
REBASE = sys.argv[4] if len(sys.argv) > 4 else None
if REBASE:
    _p = os.path.join(work, "config", "deploy_candidate.json")
    _c = json.load(open(_p)); _c["contributions"]["start_date"] = REBASE
    json.dump(_c, open(_p, "w"), indent=2)
    print("REBASED contributions.start_date ->", REBASE)

PX = {"VOO": 680.26, "MTUM": 65.71, "SGOV": 100.58, "SPY": 739.95, "AGG": 95.15,
      "GLD": 352.93}
ET = ZoneInfo("America/New_York")


class Cloud:
    def __init__(self):
        self.metrics = []
        self.cfg = types.SimpleNamespace(enabled=False, s3_root="LOCAL",
                                         prefix="paper_state_offense_sso")
    def pull(self): self.pull_denied = []; return False
    def push(self): return True
    def emit_metrics(self, *, happened, canonical): self.metrics.append((happened, canonical))


class Broker(FakePaperClient):
    """Flat paper broker; market DAY orders fill instantly at PX."""
    def __init__(self, cash, positions):
        super().__init__()
        self.cash = cash; self.pos = dict(positions); self.today = None
        self.orders_by_coid = {}
    def get_account(self):
        eq = self.cash + sum(q * PX[t] for t, q in self.pos.items())
        return {"equity": eq, "cash": self.cash, "status": "ACTIVE"}
    def list_positions(self):
        return [{"symbol": s, "qty": q} for s, q in self.pos.items() if q]
    def submit_order(self, client_order_id, symbol, qty, side, tif):
        px = PX[symbol]
        sgn = 1 if side == "buy" else -1
        self.pos[symbol] = self.pos.get(symbol, 0) + sgn * int(qty)
        self.cash -= sgn * int(qty) * px
        o = {"broker_order_id": "b-" + client_order_id[-10:], "client_order_id": client_order_id,
             "status": "filled", "symbol": symbol, "qty": int(qty), "filled_qty": int(qty),
             "filled_avg_price": px,
             "filled_at": dt.datetime.now(dt.timezone.utc).isoformat(),
             "side": side, "tif": tif}
        self.orders_by_coid[client_order_id] = o
        self.submitted.append(o)
        return dict(o)
    def get_order(self, client_order_id):
        from paper_trader.paper_client import ORDER_ABSENT
        o = self.orders_by_coid.get(client_order_id)
        return dict(o) if o else ORDER_ABSENT
    def list_orders(self, after=None):
        return [dict(v) for v in self.orders_by_coid.values()]
    def fetch_daily_closes(self, tickers, lookback_days=400):
        idx = pd.bdate_range(end=pd.Timestamp(self.today) - pd.Timedelta(days=1), periods=80)
        return {t: pd.Series([PX[t]] * len(idx), index=idx) for t in tickers if t in PX}
    def get_clock(self):  # the scheduler's DAY-window gate asks the broker clock
        return types.SimpleNamespace(is_open=True)
    def fetch_latest_prices(self, tickers):
        return {t: PX[t] for t in tickers if t in PX}
    def trading_days(self, start, end):
        s, e = dt.date.fromisoformat(str(start)[:10]), dt.date.fromisoformat(str(end)[:10])
        out = set(); d = s
        while d <= e:
            if d.weekday() < 5 and d != dt.date(2026, 11, 26):
                out.add(d)
            d += dt.timedelta(days=1)
        return out


broker = Broker(start_cash, {})


def run(day):
    broker.today = day
    now = dt.datetime(day.year, day.month, day.day, 9, 50, tzinfo=ET)
    cloud = Cloud()
    rc = drv.main(["--allocator", "mean_variance", "--strategy", "deploy_candidate",
                   "--sleeve-notional-cap", "10000"],
                  now=now, client=broker, cloud=cloud, root=work)
    hb = json.load(open(os.path.join(work, "data/state/paper_heartbeat.json")))
    lr = hb["last_run"]; ca = hb.get("corporate_actions", {})
    print(f"\n######## {day} rc={rc} metrics={cloud.metrics}")
    print("last_run:", json.dumps({k: lr.get(k) for k in ("run_date", "canonical", "reason",
          "reconcile_clean_cycles", "reconcile_total_cycles", "halted", "submitted",
          "fills", "account_explained")}))
    print("ca:", json.dumps({k: ca.get(k) for k in ("feed", "frozen", "frozen_persisted",
          "seeding", "marks_age_sessions", "stand_down", "refused_orders")}, default=str))
    p = os.path.join(work, "data/state/fleet_mirror_slice.json")
    print("mirror:", open(p).read() if os.path.exists(p) else "ABSENT")
    led = [json.loads(l) for l in open(os.path.join(work, "data/paper_state/ledger.jsonl"))]
    print("ledger rows:", len(led), "last:", {k: led[-1][k] for k in ("event", "cash", "positions")})
    tr = json.load(open(os.path.join(work, "data/state/deploy_candidate_tracking.json")))
    print("tracker points:", [(q["date"], round(q["sleeve_equity"], 2), q.get("exec")) for q in tr["points"]])
    tl = os.path.join(work, "data/state/tax_lots.jsonl")
    print("tax lots:", open(tl).read().strip().splitlines() if os.path.exists(tl) else "ABSENT")
    ec = os.path.join(work, "data/state/exec_cost_ledger.jsonl")
    print("exec_cost rows:", len(open(ec).read().strip().splitlines()) if os.path.exists(ec) else "ABSENT")
    mk = json.load(open(os.path.join(work, "data/state/price_basis_marks.json")))
    print("marks:", {k: mk.get(k) for k in ("account", "seed_sessions", "frozen")}, sorted(mk["marks"]))
    print("broker now:", broker.pos, round(broker.cash, 2))


for d in (dt.date(2026, 11, 19), dt.date(2026, 11, 20), dt.date(2026, 11, 23)):
    run(d)
