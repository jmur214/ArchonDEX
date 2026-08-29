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
from paper_trader.trading_halt import HaltStatus, check_trading_halt

STATE_DIR = "data/paper_state"

# T-329 §3: the coid STREAM token per strategy — applied from ORDER #1 so the
# record is attributable to its decision-source without a retrofit. Absent ⇒
# the legacy untagged id (accounts 1/2 are byte-unchanged). When account-3's
# second stream lands (the event desk, on its T-304 bar), it gets its own token
# here and `stage(stream=...)` per order — never a shared one, because sharing
# tokens is how two independent decisions silently net into one fill.
STREAM_TOKEN = {"llm_analyst": "analyst-a3"}

# Strategies whose OrderManager consults the TRADING kill switch before every
# submit. Deliberately an explicit allow-list, not "everything": account-1's
# live path must consult NOTHING new ([NN-FIRST-ARTIFACT]'s sibling discipline —
# a safety feature added to a working record is still a change to that record).
# T-327 ruling 2026-08-28: the halt gate is FLEET-WIDE — the old
# HALT_GATED_STRATEGIES = {"llm_analyst"} opt-in set is retired; every
# OrderManager consults check_trading_halt (see om_halt below).

# The state prefix the analyst NOTES live under. `intel_pulse` runs only on the
# account-1 branch, so account-3 must read account-1's notes across prefixes,
# read-only. Overridable per-jobdef so the source is configuration, not a
# hard-coded assumption that would silently rot if account-1 ever moved.
NOTES_SOURCE_PREFIX_ENV = "ARCHONDEX_NOTES_SOURCE_PREFIX"
NOTES_RELS = ("data/intel/analyst_notes",)


def _news_universe_collapse_reason(universe, special_sits) -> "str | None":
    """T-290c: return a LOUD degraded reason if the news universe collapsed to
    just the (mostly-delisted) special-sits fallback — i.e. the PIT membership
    file is missing from the image, which yields n_new=0 every day while
    ``degraded`` would otherwise read False. None when the universe is healthy."""
    if len(universe) > len(special_sits):
        return None
    return (f"news universe COLLAPSED to {len(universe)} tickers "
            f"(sp500_membership_pit.parquet missing from image?) "
            f"— near-zero news is an artifact, not a quiet day")


class _FailClosed(Exception):
    """A [NN-FAIL-CLOSED] halt inside a strategy pipeline — carries the driver
    exit code + a message; main() emits a non-canonical metric + returns it."""
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


def _fresh_fill_slippage_bps(staged, arrival_px, arrival_ts):
    """Gate-(b) slippage from ONLY the fills that happened AFTER we captured the
    arrival price.

    T-288: ``client_order_id`` is a deterministic hash of (trade_date, ticker,
    side, qty, config) and ``target_qty`` is computed off the prior CLOSE — so a
    same-day re-submit produces the SAME coid, the broker returns the ALREADY-
    FILLED order, and its hours-old fill price gets measured against a fresh
    arrival. That fabricated a 146 bps "SSO slippage" that was pure artifact.
    A fill older than the arrival capture is not this run's execution.

    FAIL-CLOSED ON MEASUREMENT: an unknown/unparseable ``filled_at`` is EXCLUDED,
    never assumed fresh — a missing sample is honest, a fabricated one is not.
    Returns the mean bps over qualifying fills, or None when none qualify.

    T-301: the freshness gate now lives in ONE place — ``extract_fresh_fills`` —
    which the exec-cost ledger also consumes, so the gate-b headline and the
    ledger can never disagree on which fills counted."""
    from paper_trader.exec_cost_ledger import extract_fresh_fills
    rows, stale = extract_fresh_fills(staged, arrival_px, arrival_ts,
                                      account="_gateb", trade_date="_gateb")
    if stale:
        print(f"   SLIPPAGE   EXCLUDED {stale} — fill predates this run's arrival "
              f"capture (stale/re-discovered order); not measurable, not fabricated.",
              file=sys.stderr)
    return round(sum(r.slippage_bps for r in rows) / len(rows), 2) if rows else None


def _run_family_strategy(*, constructor, fetch_universe, tracking_universe,
                         client, om, cfg, today, broker_positions, cap,
                         stream=None, stage_orders=True):
    """Shared sleeve-FAMILY pipeline (T-288 fleet — offense_sso, sleeve_btc, and
    the future Stage-2 LLM account). Byte-for-byte the same steps the live
    trend_sleeve block runs, parameterised only by the constructor + universe:
    fetch daily closes → DROP the forming today-bar (causal) → [NN-FAIL-CLOSED]
    stale-bar HALT → size off min(equity, cap) → construct → capture ARRIVAL
    price → stage. The live account-1 (trend_sleeve) block stays INLINE +
    untouched (regression-safe); it can migrate here later under its own lock.

    Returns (plan, closes_latest, staged, arrival_px, arrival_ts, sizing_equity,
    equity, latest_bar_date). Raises _FailClosed(code, msg) on a fetch failure /
    stale bar."""
    import pandas as _pd
    try:
        closes = client.fetch_daily_closes(list(fetch_universe), lookback_days=400)
    except Exception as exc:
        raise _FailClosed(67, f"bars fetch failed: {type(exc).__name__}")
    closes = {t: s[s.index < _pd.Timestamp(today)] for t, s in closes.items()}
    stale = [t for t in fetch_universe
             if t not in closes or closes[t].empty
             or (_pd.Timestamp(today) - closes[t].index[-1]).days > 5]
    if stale:
        raise _FailClosed(68, f"price data missing/stale for {stale}")
    equity = float(client.get_account().get("equity", 0.0))
    sizing_equity = min(equity, cap) if cap else equity
    plan = constructor.construct(sizing_equity, broker_positions, closes)
    closes_latest = {t: float(closes[t].iloc[-1]) for t in tracking_universe
                     if t in closes and not closes[t].empty}
    # Stamp WHEN we captured arrival: gate-(b) may only measure fills that
    # happened after this instant (see _fresh_fill_slippage_bps).
    import datetime as _dt
    arrival_ts = _dt.datetime.now(_dt.timezone.utc)
    arrival_px = (client.fetch_latest_prices([o.ticker for o in plan.orders])
                  if plan.orders else {})
    # T-329: ``stage_orders=False`` (a TRADING HALT) still CONSTRUCTS and returns
    # the plan but stages nothing. Constructing under a halt is deliberate: the
    # record then shows what the halt prevented, which is the only evidence that
    # tells "the switch is doing something" apart from "the switch is pointed at
    # a dead stream". Nothing can reach the broker — there is no staged order to
    # submit, and submit() re-checks the halt anyway (defence in depth).
    staged = ([om.stage(str(today), s.ticker, s.side, s.qty,
                        s.stage_args()["tif"], cfg.config_hash(), stream=stream)
               for s in plan.orders] if stage_orders else [])
    # Freshest completed bar in the panel — the econ-health stale-data tripwire.
    latest_bar_date = max(
        (closes[t].index[-1].date() for t in fetch_universe
         if t in closes and not closes[t].empty), default=None)
    return (plan, closes_latest, staged, arrival_px, arrival_ts, sizing_equity,
            equity, latest_bar_date)


def _record_family_tracker(*, tracker_path, plan, closes_latest, equity,
                           sizing_equity, broker_positions, staged, arrival_px,
                           arrival_ts, summary, canonical, root, robo_closes):
    """Record a family strategy's forward tracker + report-only execution gates,
    reusing the exact T-238 gate logic (held_qty vs the achievable whole-share
    target on the sizing basis; slippage vs arrival; order-state errors; clean
    days). Per-strategy tracker file (accounts never collide). ``robo_closes``
    is the SPY/AGG/GLD benchmark; the account's equity is tracked vs it. Never
    raises to the caller (report-only) — a tracker failure must not fail the run."""
    from paper_trader.sleeve_tracker import SleeveTracker
    did_rebalance = bool(plan.orders)
    order_errs = ((summary.reconcile_total_cycles - summary.reconcile_clean_cycles)
                  + (1 if summary.halted else 0))
    trade = list(plan.target_qty)                 # tickers this strategy trades
    tgt_w = ({t: (plan.target_qty.get(t, 0) * closes_latest[t]) / sizing_equity
              for t in trade if t in closes_latest} if sizing_equity > 0 else {})
    held_w = None
    if not did_rebalance and sizing_equity > 0:
        held_w = {t: (broker_positions.get(t, 0) * closes_latest[t]) / sizing_equity
                  for t in trade if t in closes_latest}
    slippage_bps = _fresh_fill_slippage_bps(staged, arrival_px, arrival_ts)
    return SleeveTracker(path=tracker_path, root=str(root)).record(
        str(summary.trade_date), equity, robo_closes,
        target_weights=tgt_w, held_weights=held_w, slippage_bps=slippage_bps,
        order_errors=order_errs, canonical=canonical)


def _digest_streams(root) -> dict:
    """T-344 wiring — assemble the 8 digest streams from PERSISTED state.

    Per stream fail-open to {} (the generator lists it under 'Not reporting',
    never drops it). THE UNIT TRAP (stated in the wiring spec so it cannot be
    re-introduced): the live books publish DOLLAR NAVs against DIFFERENT
    notionals — pass each book's own NORMALIZED growth ratios, which
    ``LiveBook.summary()`` already provides; raw nav pairs only for the
    index-at-1.0 shadow streams."""
    import json as _json
    from pathlib import Path as _Path
    streams: dict = {}

    def _load(rel):
        p = _Path(root) / rel
        return _json.loads(p.read_text()) if p.exists() else None

    def _dd(navs):
        """Current drawdown off the running peak of a nav series."""
        try:
            peak, last = max(navs), navs[-1]
            return round(float(last) / float(peak) - 1.0, 5) if peak else None
        except Exception:  # noqa: BLE001
            return None

    try:
        from paper_trader.live_books import ALL_BOOKS, LiveBook
        for spec in ALL_BOOKS:
            key = f"book: {spec.name}"
            try:
                lb = LiveBook(spec, root=str(root))
                s = lb.summary()
                clean = [d for d in lb._state()["days"] if not d.get("degraded")]
                s["current_drawdown_pct"] = _dd([d["book_nav"] for d in clean])
                streams[key] = s
            except Exception:  # noqa: BLE001
                streams[key] = {}
    except Exception:  # noqa: BLE001
        pass

    # account-1 sleeve vs the 60/40 robo twin: book growth EXACT from the equity
    # series; twin growth inverted from the tracker's own robo CAGR over the same
    # window (cagr = growth**(252/n) - 1 round-trips, so the inversion is faithful).
    try:
        t = _load("data/state/sleeve_tracking.json") or {}
        pts = [p for p in (t.get("points") or []) if p.get("sleeve_equity")]
        robo = ((t.get("summary") or {}).get("robos") or {}).get("60_40") or {}
        n = int(robo.get("n_days") or 0)
        if pts and n and robo.get("cagr") is not None:
            eqs = [float(p["sleeve_equity"]) for p in pts]
            streams["account-1 trend sleeve (paper)"] = {
                "book_growth": eqs[-1] / eqs[0],
                "twin_growth": (1.0 + float(robo["cagr"])) ** (n / 252.0),
                "n_days": n, "current_drawdown_pct": _dd(eqs),
                "cash_adj": (t.get("summary") or {}).get("cash_adj") or {}}
        else:
            streams["account-1 trend sleeve (paper)"] = {}
    except Exception:  # noqa: BLE001
        streams["account-1 trend sleeve (paper)"] = {}

    # the three shadow streams publish index-at-1.0 nav pairs
    for name, rel, va, ba in (
            ("btc 5% shadow (exploratory)",
             "data/state/btc_shadow_tracking.json", "variant_nav", "base_nav"),
            ("dbmf shadow (3rd-stream clock)",
             "data/state/dbmf_shadow_tracking.json", "variant_nav", "base_nav"),
            ("llm analyst shadow book",
             "data/state/llm_shadow_book.json", "book_nav", "twin_nav")):
        try:
            d = _load(rel) or {}
            pts = d.get("points") or d.get("days") or []
            last = pts[-1] if pts else {}
            if last.get(va) is not None and last.get(ba) is not None:
                streams[name] = {
                    "book_nav": last[va], "twin_nav": last[ba], "n_days": len(pts),
                    "current_drawdown_pct": _dd(
                        [p[va] for p in pts if p.get(va) is not None])}
            else:
                streams[name] = {}
        except Exception:  # noqa: BLE001
            streams[name] = {}
    return streams


def main(argv=None, *, now=None, client=None, cloud=None, root=None) -> int:
    """Run one cloud paper day. ``now``/``client``/``cloud``/``root`` are injectable
    for tests (drive a non-trading day, a held position, etc. without a
    real broker); production passes none and they are constructed live.

    ``root`` is the state/config base. Without it a test that drives ``main()`` writes
    its journal, ledger and heartbeat into the REPO's own ``data/`` — which is how a
    smoke test silently edits the state a developer is looking at."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocator", required=True,
                    help="EXPLICIT runtime allocator; designation is the "
                         "independent config/paper_designated_allocator.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the cycle WITHOUT arming submission (observe only)")
    ap.add_argument("--strategy",
                    choices=["reconcile_only", "trend_sleeve", "offense_sso",
                             "sleeve_btc", "llm_analyst"],
                    default="reconcile_only",
                    help="reconcile_only = the daily pulse (no orders, the proven "
                         "default); trend_sleeve = the T-238 defensive sleeve "
                         "(Account 1, LIVE); offense_sso = the T-284 gated-2× SSO "
                         "offense (Account 2); sleeve_btc = the T-272 sleeve+IBIT "
                         "(RETIRED — its science moved to the virtual btc_shadow "
                         "book; kept runnable for the record); llm_analyst = the "
                         "T-329 stage-2 AI trader (Account 3): yesterday's VALIDATED "
                         "analyst note → real paper orders. One account per jobdef. "
                         "trend_sleeve = construct + submit the T-204 "
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

    root = Path(root) if root else Path(__file__).resolve().parents[1]
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
    # root-relative, like every other state surface this driver owns. (It used to
    # take the module default — identical in production, where root IS the repo
    # root, but it meant an injected root could not fully redirect the run's state.)
    hb = PaperHeartbeat(root=str(root))

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
    # T-329 account-3: this account's orders carry a per-STREAM coid token from
    # ORDER #1 (None for the others — the coid record stays byte-identical).
    # T-327 RULING (2026-08-28): the TRADING kill switch is a FLEET PROPERTY —
    # EVERY strategy's OrderManager consults it before every submit, from birth.
    # Semantics unchanged: a halt STOPS NEW ORDERS (buys AND sells) and NEVER
    # liquidates. With no halt set, check_trading_halt returns not-halted and
    # submit proceeds identically — the no-halt path stays behaviorally
    # byte-equivalent for accounts 1/2 (locked by test).
    om_stream = STREAM_TOKEN.get(args.strategy)
    om_halt = (lambda: check_trading_halt(root=str(root)))
    om = OrderManager(client, journal_path=str(state / "orders.jsonl"),
                      stream=om_stream, halt_check=om_halt)
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
        bpos = {p["symbol"]: int(p["qty"]) for p in client.list_positions()}
        bcash = client.get_account()["cash"]
        # T-238 Option A: a market DAY order fills IN THIS SAME cycle (after the
        # pre-submit adopt above), unlike an OPG that fills on a later run. So
        # re-converge the ledger to EXPLAINED broker truth before each reconcile
        # — else the just-filled, ledger-unadopted position reads as a spurious
        # position_drift → non-canonical. Explained-ONLY: a genuine UNEXPLAINED
        # position stays unadopted and is still flagged as drift (safety intact).
        adopt_explained_broker_truth(led, bpos, bcash, list(om.orders.values()),
                                     reason=f"cloud cycle {today} reconcile")
        return ReconcileInputs(
            ledger_positions=led.positions(), ledger_cash=led.cash(),
            broker_positions=bpos, broker_cash=bcash,
            orders=list(om.orders.values()),
            known_tickers=ktickers,
            window_closed=False,
        )

    # --- content layer: reconcile-only pulse OR the trend sleeve (T-238) -- #
    staged: list = []
    sleeve_closes: dict = {}
    # T-331: the FULL PIT-trimmed close SERIES (ticker -> pd.Series), handed to the
    # eval harness so predictions resolve against LIVE prices. Without it the harness
    # falls back to the BAKED data/processed/*.csv substrate (which ends 2026-04-17 and
    # is never refreshed) → every resolution would fail closed as `source_absent_or_stale`
    # forever: a SECOND broken clock sitting behind the first.
    eval_price_series: dict = {}
    arrival_px: dict = {}                       # gate-(b) slippage reference
    arrival_ts = None                           # when arrival was captured
    latest_bar_date = None                      # econ-health stale-data tripwire
    plan = None                                 # set by the content-layer block
    family_state = None                         # T-288 fleet Accounts 2/3 context
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
        # T-331: hand these LIVE, causally-trimmed series to the eval harness (below).
        eval_price_series = closes
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
        # T-238 Option A: env-gate the TIF. PAPER trades market DAY (Alpaca
        # paper fills DAY orders but EXPIRES OPG auction orders unfilled); a
        # future LIVE path sets ARCHONDEX_SLEEVE_TIF=opg to hit the real opening
        # auction the T-236/T-255 backtest assumes.
        sleeve_tif = os.getenv("ARCHONDEX_SLEEVE_TIF", "day").lower()
        if sleeve_tif not in ("day", "opg"):
            print(f"FATAL: [NN-FAIL-CLOSED] invalid ARCHONDEX_SLEEVE_TIF="
                  f"{sleeve_tif!r} (want day|opg).", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return 69
        plan = SleeveOrderConstructor(tif=sleeve_tif).construct(
            sizing_equity, broker_positions, closes)
        sleeve_closes = {t: float(closes[t].iloc[-1]) for t in SLEEVE_UNIVERSE}
        latest_bar_date = max((closes[t].index[-1].date() for t in SLEEVE_UNIVERSE
                               if t in closes and not closes[t].empty), default=None)
        # Arrival price (latest trade) captured BEFORE submission = the gate-(b)
        # slippage reference (paper controls |fill − arrival| on a DAY order).
        # arrival_ts stamps WHEN: only fills after it are this run's execution.
        if plan.orders:
            import datetime as _dt
            arrival_ts = _dt.datetime.now(_dt.timezone.utc)
            arrival_px = client.fetch_latest_prices([o.ticker for o in plan.orders])
        print(f"   SLEEVE     tif={sleeve_tif} signals={plan.signals} "
              f"targets={plan.targets} → {len(plan.orders)} order(s): "
              f"{[(o.ticker, o.side, o.qty) for o in plan.orders]}")
        for spec in plan.orders:
            staged.append(om.stage(str(today), spec.ticker, spec.side, spec.qty,
                                   spec.stage_args()["tif"], cfg.config_hash()))

    elif args.strategy in ("offense_sso", "sleeve_btc", "llm_analyst"):
        # T-288 fleet Accounts 2/3 — the sleeve-FAMILY shared pipeline. The live
        # account-1 (trend_sleeve) block above stays inline + untouched.
        # T-329 joins account-3's LLM analyst to the SAME pipeline: the point of
        # stage 2 is that the model's decision rides the existing deterministic
        # order/exec/reconcile stack unchanged — the AI supplies target weights and
        # nothing else. A separate order path for the AI would be the special
        # pleading `[NN-AI-GATE]` forbids.
        sleeve_tif = os.getenv("ARCHONDEX_SLEEVE_TIF", "day").lower()
        if sleeve_tif not in ("day", "opg"):
            print(f"FATAL: [NN-FAIL-CLOSED] invalid ARCHONDEX_SLEEVE_TIF="
                  f"{sleeve_tif!r} (want day|opg).", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return 69
        # Only the halt-gated strategies resolve a halt; for the others this
        # stays a literal "clear" and the pipeline is byte-identical.
        halt, note_pull = HaltStatus(False), None
        if args.strategy == "offense_sso":
            from paper_trader.offense_sso_constructor import OffenseSSOConstructor
            # T-298 flip: damping is a CONFIG flip (a jobdef env var), not a code
            # fork — default "symmetric" is byte-preserved for the undamped arm.
            # "asymmetric" damps future RE-ENTRY only (never de-risking); the held
            # position is unaffected the day of the flip.
            damping = os.getenv("ARCHONDEX_OFFENSE_DAMPING", "symmetric").lower()
            if damping not in ("symmetric", "asymmetric"):
                print(f"FATAL: [NN-FAIL-CLOSED] invalid ARCHONDEX_OFFENSE_DAMPING="
                      f"{damping!r} (want symmetric|asymmetric).", file=sys.stderr)
                cloud.emit_metrics(happened=True, canonical=False); cloud.push()
                return 69
            constructor = OffenseSSOConstructor(tif=sleeve_tif, damping=damping)
            fetch_u = ("SPY", "SSO", "AGG", "GLD")   # SPY signal, SSO trade, AGG/GLD robo bench
            family_state = {"tracker_file": "offense_tracking.json", "label": "OFFENSE-SSO"}
            # Config visible in the dead-man banner (silent-wrongness doctrine:
            # a flip must announce itself, not just be true in the jobdef).
            print(f"   OFFENSE-SSO  damping={damping}"
                  f"{' (T-298: damp re-entry, never de-risk)' if damping=='asymmetric' else ''}")
        elif args.strategy == "llm_analyst":
            # --- T-329 ACCOUNT 3, the stage-2 AI trader. Day-1 stream = the
            # CONSTRAINED analyst only (the ladder's event desk joins on its T-304
            # bar, the thesis book on promotion_check — NOT here). ------------- #
            from paper_trader.llm_analyst_constructor import LLMAnalystConstructor
            from paper_trader.sleeve_constructor import SLEEVE_UNIVERSE

            # 1. THE CROSS-ACCOUNT NOTE PULL. The notes are written by intel_pulse,
            # which runs on the ACCOUNT-1 branch only, so they live in account-1's
            # state prefix. Without this the constructor would find an empty dir and
            # HOLD every day forever while reporting a perfectly plausible
            # "no_note:no notes dir yet" — a stopped clock with a good excuse.
            notes_src = os.getenv(NOTES_SOURCE_PREFIX_ENV, "paper_state")
            note_pull = cloud.pull_readonly_from(notes_src, NOTES_RELS)
            _npf = note_pull["rels"].get(NOTES_RELS[0], {})
            print(f"   NOTE-PULL  from s3://…/{notes_src}/ ok={note_pull['ok']} "
                  f"notes_on_disk={_npf.get('n_files', 0)}"
                  + (f" — {note_pull['reason']}" if note_pull.get("reason") else ""))

            # 2. THE TRADING KILL SWITCH, resolved BEFORE construction. On a trip
            # the day is reconcile-only: the plan is still built (so the record
            # shows what was prevented) but NOTHING is staged. A halt stops new
            # actions; it never liquidates, so held positions are untouched.
            halt = check_trading_halt(root=str(root))
            if halt.halted:
                print(f"   {halt.banner()}")

            constructor = LLMAnalystConstructor(
                trade_date=str(today), root=str(root), tif=sleeve_tif,
                # Day 1 the analyst is the ONLY stream, so it gets the whole
                # capped budget (sub_budget=1.0 × min(equity, $10k cap)). The
                # per-stream structure is already here for stream 2 — no netting
                # decision is deferred, only a second number.
                sub_budget=float(os.getenv("ARCHONDEX_LLM_SUB_BUDGET", "1.0")),
                # Defence in depth: intel_pulse already allowlists the constrained
                # analyst to the sleeve universe, but the constructor re-enforces
                # it so a note written under some OTHER pulse configuration can
                # never reach a name this run cannot price or halt on.
                allowlist=tuple(SLEEVE_UNIVERSE))
            fetch_u = tuple(SLEEVE_UNIVERSE)          # SPY/AGG/GLD — also the robo bench
            family_state = {"tracker_file": "llm_analyst_tracking.json",
                            "label": "LLM-ANALYST"}
        else:
            from paper_trader.sleeve_btc_constructor import SleeveBtcConstructor
            constructor = SleeveBtcConstructor(tif=sleeve_tif)
            fetch_u = ("SPY", "AGG", "GLD", "IBIT")
            family_state = {"tracker_file": "sleeve_btc_tracking.json", "label": "SLEEVE-BTC"}
        try:
            (plan, sleeve_closes, staged2, arrival_px, arrival_ts, sizing_equity,
             equity, latest_bar_date) = \
                _run_family_strategy(
                    constructor=constructor, fetch_universe=fetch_u,
                    tracking_universe=fetch_u, client=client, om=om, cfg=cfg,
                    today=today, broker_positions=broker_positions,
                    cap=args.sleeve_notional_cap,
                    stream=STREAM_TOKEN.get(args.strategy),
                    stage_orders=not halt.halted)
            staged.extend(staged2)
        except _FailClosed as fc:
            print(f"FATAL: [NN-FAIL-CLOSED] {args.strategy} {fc.msg} — refusing "
                  f"to trade.", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return fc.code
        if args.sleeve_notional_cap:
            print(f"   {family_state['label']}  notional cap "
                  f"${args.sleeve_notional_cap:,.0f} (equity ${equity:,.0f})")
        print(f"   {family_state['label']}  tif={sleeve_tif} signals={plan.signals} "
              f"targets={plan.targets} → {len(plan.orders)} order(s): "
              f"{[(o.ticker, o.side, o.qty) for o in plan.orders]}"
              + (f" [HALTED — {len(plan.orders)} order(s) NOT staged]"
                 if halt.halted else ""))
        if args.strategy == "llm_analyst":
            print(f"   LLM-ANALYST note_as_of={plan.note_as_of} "
                  f"degraded={plan.degraded} "
                  f"reason={plan.reject_reason or 'none'} halted={halt.halted}")

    summary = sched.run_trading_day(str(today), staged, inputs_fn,
                                    account_explained=account_explained)

    # --- 3. heartbeat verdict → metrics + exit code ------------------- #
    v = hb.check(today, is_trading_day=True)
    canonical = bool(v.alive and not v.alert)
    print(f"3. CYCLE     reconcile {summary.reconcile_clean_cycles}/"
          f"{summary.reconcile_total_cycles} clean | halted={summary.halted}")
    print(f"4. HEARTBEAT alive={v.alive} alert={v.alert} | {v.reason}")

    # --- T-329: the STREAM's own daily verdict. AFTER record_run, like every other
    # heartbeat block — record_run REPLACES the status file, so anything stamped
    # before it is silently erased. A zero-order day is ambiguous between four very
    # different things (no note yet / the note asked for no change / the firewall
    # REJECTED it / the switch is pulled) and only a named reason tells them apart;
    # the notes-pull outcome rides along because a fail-closed HOLD is honest
    # evidence only if the note was actually reachable. Report-only. ---------- #
    if args.strategy == "llm_analyst" and plan is not None:
        try:
            hb.record_stream("llm_analyst", {
                "stream": STREAM_TOKEN["llm_analyst"], "note_as_of": plan.note_as_of,
                "n_orders": len(plan.orders), "targets": plan.targets,
                "degraded": bool(plan.degraded), "reject_reason": plan.reject_reason,
                # T-329c: a zero-order day now always names its cause. `no_view`
                # is the HEALTHY zero (the analyst looked and chose to hold, with
                # a stated reason); a bare zero with neither this nor a
                # reject_reason would mean the channel is dead again.
                "no_view": bool(plan.no_view), "no_view_reason": plan.no_view_reason,
                "prompt_version": (plan.note_prompt_version or "unknown"),
                "halted": bool(halt.halted), "halt_reason": halt.reason or None,
                "notes_pull_ok": bool((note_pull or {}).get("ok")),
                "notes_on_disk": (note_pull or {}).get(
                    "rels", {}).get(NOTES_RELS[0], {}).get("n_files"),
                "sub_budget_usd": (min(equity, args.sleeve_notional_cap)
                                   if args.sleeve_notional_cap else equity),
            })
        except Exception as exc:
            print(f"   LLM-ANALYST stream-record WARN {type(exc).__name__} "
                  f"(non-fatal, report-only)", file=sys.stderr)

    # --- T-238 Part 2: forward-track the sleeve vs both robos + feed the
    # pre-registered EXECUTION-fidelity gates (report-only, never changes
    # trading). Tracking-error is recorded ONLY on SETTLED (non-rebalance)
    # days — a rebalance morning's book is pre-fill, so its held≠target is
    # intent, not a fidelity failure; rebalance-day fill quality is the
    # slippage gate's job (fed once the auction print is observed). --------- #
    if args.strategy == "trend_sleeve" and sleeve_closes:
        try:
            from paper_trader.sleeve_tracker import SleeveTracker
            equity = float(client.get_account().get("equity", broker_cash))
            did_rebalance = bool(plan.orders)
            # order-state errors this cycle: any un-clean reconcile + a halt.
            order_errs = ((summary.reconcile_total_cycles
                           - summary.reconcile_clean_cycles)
                          + (1 if summary.halted else 0))
            # Gate (a) EXECUTION fidelity = held vs the ACHIEVABLE WHOLE-SHARE
            # target, both on the SIZING basis (min(equity, cap)). The fractional
            # →whole-share rounding AND the notional cap are INTENDED, not
            # fidelity failures — plan.target_qty already embeds both. (Comparing
            # held-on-full-equity vs the fractional exposure spuriously fails on a
            # capped sleeve: 4 SPY of a $10k slice reads 0.03 of $100k vs a 0.33
            # target → te 0.60.) On a settled day held_qty==target_qty → te≈0.
            tgt_w = ({t: (plan.target_qty.get(t, 0) * sleeve_closes[t]) / sizing_equity
                      for t in sleeve_closes} if sizing_equity > 0 else dict(plan.targets))
            held_w = None
            if not did_rebalance and sizing_equity > 0:
                held_w = {t: (broker_positions.get(t, 0) * sleeve_closes[t]) / sizing_equity
                          for t in sleeve_closes}
            # gate (b): realized DAY-fill slippage vs the ARRIVAL price, counting
            # ONLY fills that happened after the arrival capture (a stale/
            # re-discovered fill is not this run's execution — T-288).
            slippage_bps = _fresh_fill_slippage_bps(staged, arrival_px, arrival_ts)
            tracker = SleeveTracker(root=str(root))
            tsum = tracker.record(
                str(today), equity, sleeve_closes,
                target_weights=tgt_w,
                held_weights=held_w,
                slippage_bps=slippage_bps,   # DAY fill vs arrival price (gate b)
                order_errors=order_errs,
                canonical=canonical)
            eg = tsum.get("execution_gates", {})
            print(f"6. TRACK     sleeve forward vs robos: {tsum.get('status')} "
                  f"({tsum.get('n_days', tsum.get('sleeve', {}).get('n_days'))} pts)"
                  + (f" | sleeve MaxDD shallower than both robos="
                     f"{tsum.get('sleeve_mdd_shallower_than_both')}"
                     if tsum.get('status') == 'tracking' else ""))
            if eg:
                print(f"   EXEC-GATE  overall={eg.get('overall')} "
                      f"(execution fidelity only — NOT a performance verdict)")
            # --- T-276 BTC shadow: REPORT-ONLY forward validation of the +5%
            # BTC arm (never touches orders/weights/canonical). Reuses the REAL
            # sleeve daily return + a trend-ruled BTC leg. T-307: the BTC-USD signal
            # + IBIT basis price are now THREADED via Alpaca (crypto data is public,
            # IBIT via the stock client — both on alpaca-py already in the image), so
            # the shadow un-degrades and the T-272 clocks genuinely run. Fail-OPEN:
            # a None fetch → the shadow degrades that day (never fabricates). -------- #
            try:
                from paper_trader.btc_shadow import BtcShadowTracker
                from paper_trader.sleeve_tracker import RF_ANNUAL
                _prev = [p for p in tracker._load() if p["date"] < str(today)]
                _sleeve_ret = (equity / _prev[-1]["sleeve_equity"] - 1.0) if _prev else 0.0
                _btc_hist = client.fetch_btc_usd_history()          # Alpaca crypto (public)
                _ibit = None
                try:
                    _ir = client.fetch_daily_closes(["IBIT"])       # Alpaca stock (keyed)
                    if _ir.get("IBIT") is not None and len(_ir["IBIT"]):
                        _ibit = float(_ir["IBIT"].iloc[-1])
                except Exception:
                    _ibit = None
                bsum = BtcShadowTracker(root=str(root)).record(
                    str(today), _sleeve_ret, cash_daily_rate=RF_ANNUAL / 252.0,
                    btc_hist=_btc_hist, ibit_close=_ibit)
                print(f"   BTC-SHADOW n_days={bsum.get('n_days')} "
                      f"clean={bsum.get('n_clean')} degraded={bsum.get('n_degraded')} "
                      f"(report-only T-272 forward validation; BTC threaded via Alpaca)")
            except Exception as exc:
                print(f"   BTC-SHADOW warn: {type(exc).__name__} (non-fatal)")
            # --- T-316 DBMF SHADOW: the 5% managed-futures leg, report-only. This is
            # the ONLY live clock that can answer the "3rd uncorrelated stream" question
            # (T-248/T-263 tripwire #2) — every BACKTEST proxy hit a data wall, not a
            # verdict (T-296 basis-walled; T-313 refuted at the data stage). The leg is
            # deliberately UNGATED (DBMF is itself a trend program; T-296 measured that
            # stacking our gate on an internally-overlaid fund INTERFERES). Fail-OPEN:
            # no price → the day degrades, the leg parks at 0, never fabricated. ------ #
            try:
                from paper_trader.dbmf_shadow import DBMF_TICKER, DbmfShadowBook
                _prev_d = [p for p in tracker._load() if p["date"] < str(today)]
                _sleeve_ret_d = (equity / _prev_d[-1]["sleeve_equity"] - 1.0) if _prev_d else 0.0
                _dbmf = None
                try:
                    _dr = client.fetch_daily_closes([DBMF_TICKER])   # Alpaca stock (keyed)
                    if _dr.get(DBMF_TICKER) is not None and len(_dr[DBMF_TICKER]):
                        _dbmf = float(_dr[DBMF_TICKER].iloc[-1])
                except Exception:
                    _dbmf = None
                dsum = DbmfShadowBook(root=str(root)).record(
                    str(today), _sleeve_ret_d, dbmf_close=_dbmf)
                print(f"   DBMF-SHADOW n_days={dsum.get('n_days')} "
                      f"clean={dsum.get('n_clean')} degraded={dsum.get('n_degraded')}"
                      + (f" corr={dsum.get('corr_dbmf_sleeve_todate')}"
                         if dsum.get('corr_dbmf_sleeve_todate') is not None else "")
                      + " (report-only T-316 3rd-stream forward clock)")
            except Exception as exc:
                print(f"   DBMF-SHADOW warn: {type(exc).__name__} (non-fatal)")
            # --- T-322 EVENT DESK: D's typed event calls become a TRADING record, not
            # just Brier predictions ("act like a trader" — a filing drops, you size it).
            # Two desks on ONE machinery (parameterized, not forked): D's event feed and
            # E/T-321's agentic-analyst feed (the latter dormant until its feed lands).
            # The gate is D's OWN T-304 bar #5, so the desk record and the Brier record
            # share one standard. Report-only; fail-closed parking, never a fake fill. --- #
            try:
                from paper_trader.event_shadow_book import (ANALYST_DESK, EVENT_DESK,
                                                            TWIN_TICKER, EventShadowBook)
                for _cfg in (EVENT_DESK, ANALYST_DESK):
                    _bk = EventShadowBook(cfg=_cfg, root=str(root))
                    _stt = _bk._state()
                    _calls, _why = _bk._load_calls(str(today))
                    # prices for: open positions + today's call symbols + the twin
                    _syms = sorted({p["symbol"] for p in _stt.get("open", [])}
                                   | {str(c.get("symbol", "")).upper() for c in _calls}
                                   | {TWIN_TICKER})
                    _px = {}
                    if _syms:
                        try:
                            _fetched = client.fetch_daily_closes(_syms, lookback_days=10)
                            _px = {t: float(s.iloc[-1]) for t, s in _fetched.items()
                                   if s is not None and len(s)}
                        except Exception:
                            _px = {}          # → the desk parks the day (never fabricates)
                    _es = _bk.record(str(today), closes=_px, calls=_calls or None)
                    print(f"   EVENT-DESK[{_cfg.name}] days={_es.get('n_days')} "
                          f"open={_es.get('n_open')} closed={_es.get('n_closed')}"
                          + (f" mean_excess_vs_twin={_es.get('mean_excess_vs_twin')}"
                             if _es.get('mean_excess_vs_twin') is not None else "")
                          + " (report-only T-322; gate = D/T-304 bar)")
            except Exception as exc:
                print(f"   EVENT-DESK warn: {type(exc).__name__} (non-fatal)")
            # --- T-326 THESIS BOOKS: D's thesis desk gets a virtual book. Differs from
            # the fixed-horizon desks: months-long holds, FALSIFIER-triggered exits, and
            # multi-leg baskets. Two channel sub-books (machine / user_seeded) so the
            # records never blend. Scoring defers to D's OWN T-324 promotion_check —
            # one standard, not a second. Report-only, fail-closed. -------------------- #
            try:
                from paper_trader.thesis_book import (MACHINE_DESK, USER_DESK, ThesisBook)
                for _tcfg in (MACHINE_DESK, USER_DESK):
                    _tb = ThesisBook(cfg=_tcfg, root=str(root))
                    # T-343: the fetch FOLLOWS the book — pending legs + open legs + the
                    # twin + the legs of the session `record()` will actually consume.
                    # The old gather read theses dated TODAY while record() consumes the
                    # PRIOR session, so a newly-filed leg was never priced and the thesis
                    # parked. Nobody can pre-list what the machine will pick (FN, AMTM).
                    _tsyms = _tb.pending_symbols(str(today))
                    _tpx = {}
                    if _tsyms:
                        try:
                            _f = client.fetch_daily_closes(_tsyms, lookback_days=10)
                            _tpx = {t: float(v.iloc[-1]) for t, v in _f.items()
                                    if v is not None and len(v)}
                        except Exception:
                            _tpx = {}      # → the book parks the day (never fabricates)
                    _miss = [s for s in _tsyms if s not in _tpx]
                    # record() loads the prior session's theses itself; do NOT pass today's.
                    _ts = _tb.record(str(today), closes=_tpx)
                    # T-347: an approaching expiry must reach the NOTIFY path, not
                    # just the book's own reasons — the window is a deadline on us.
                    if _ts.get("expiring"):
                        try:
                            hb.record_thesis_expiry(_tcfg.name, _ts["expiring"])
                        except Exception as _e:
                            print(f"   THESIS-EXPIRY warn: {type(_e).__name__} (non-fatal)")
                    print(f"   THESIS-BOOK[{_tcfg.name}] days={_ts.get('n_days')} "
                          f"open={_ts.get('n_open')} closed={_ts.get('n_closed')}"
                          + (f" falsified={_ts.get('n_falsified')}"
                             if _ts.get('n_falsified') else "")
                          + (f" pending={_ts.get('n_pending')}"
                             if _ts.get('n_pending') else "")
                          + (f" fetched={len(_tpx)}/{len(_tsyms)}"
                             f" no-price={','.join(_miss)}" if _miss
                             else f" fetched={len(_tpx)}/{len(_tsyms)}")
                          + " (report-only T-326; gate = D/T-324 bar)")
            except Exception as exc:
                print(f"   THESIS-BOOK warn: {type(exc).__name__} (non-fatal)")
            # --- T-328 LIVE BOOKS: the performance laboratory. Four report-only NAV-vs-twin
            # books (SPY null / damped-offense T-298 / quality satellite / sleeve-at-$50K).
            # Performance testing scales through BOOKS, not accounts. The sleeve + offense
            # books need a live STANCE, supplied from this run's own plan signals — absent
            # it they park (never a fabricated exposure). Report-only, zero order effect. -- #
            try:
                from paper_trader.live_books import (ALL_BOOKS, CASH_RATE_TICKER,
                                                     LiveBook)
                # T-332a: BIL rides the SAME fetch — its daily total return prices the
                # cash-drag ANNOTATION (live paper cash earns 0%; the backtest spec credits
                # the short rate). Absent it the books accrue NOTHING and say so.
                _bsyms = sorted({s for bk in ALL_BOOKS for s in bk.symbols}
                                | {CASH_RATE_TICKER})
                _bpx = {}
                try:
                    _bf = client.fetch_daily_closes(_bsyms, lookback_days=10)
                    _bpx = {t: float(v.iloc[-1]) for t, v in _bf.items()
                            if v is not None and len(v)}
                except Exception:
                    _bpx = {}
                # the live stances this run already computed (never re-derived)
                for _t, _e in (getattr(plan, "signals", {}) or {}).items():
                    _bpx[f"_sleeve_expo_{_t}"] = float(_e)
                if args.strategy == "offense_sso":
                    for _t, _e in (getattr(plan, "signals", {}) or {}).items():
                        _bpx[f"_offense_expo_{_t}"] = float(_e)
                for _spec in ALL_BOOKS:
                    _lb = LiveBook(_spec, root=str(root))
                    _ls = _lb.record(str(today), _bpx)
                    print(f"   LIVE-BOOK[{_spec.name}] days_accrued={_ls.get('days_accrued')} "
                          f"nav={_ls.get('book_nav')} twin={_ls.get('twin_nav')}"
                          + (f" excess_growth={_ls.get('excess_growth')}"
                             if _ls.get('excess_growth') is not None else "")
                          + " (report-only T-328; NOT EVALUABLE on a short record)")
            except Exception as exc:
                print(f"   LIVE-BOOK warn: {type(exc).__name__} (non-fatal)")
            # (T-329d3: the T-338 clock census + T-342 channel liveness used to run
            # HERE — before the intel pulse, shadow book, eval, and news append whose
            # artifacts five of its clocks measure, so those clocks false-MISSED every
            # day. Both now run at the TRUE tail of the run, after step 8. Found by
            # the census's own first in-cloud emission on 2026-08-26.)
            # --- T-310 INTEL PULSE: the day's report-only LLM steps — the analyst
            # note (PERSISTED to data/intel/analyst_notes/, which is what wakes the
            # shadow book below the NEXT day + feeds the eval harness), A's ops
            # watchdog, and D's forward-only event interpreter. All fail-open +
            # KEY-OPTIONAL: with no ANTHROPIC_API_KEY every step clean-skips (an
            # honest "no adapter" record, never a fabricated note). Runs on the
            # account-1 branch only; report-only, never touches the trading verdict.
            # --- T-325 (post-Wed zero-thesis fix): pull the recent news TAPE from
            # S3 BEFORE the intel pulse. The whole pulse (analyst + agentic + weekly
            # scan) reads the news panel, but the current-month append/push happens
            # LATER (step 8) — so without this the panel is EMPTY at read time and
            # the strong-tier scan files 0 on an empty bundle (the Wed 2026-07-29
            # defect: n_documents=0). Weekly scan-due → deeper 4-month pull for a rich
            # thematic tape; else current month only (cheap daily read-path). Report-
            # only, never fatal. ------------------------------------------------- #
            try:
                from intelligence.thesis_desk.thesis_scan import due as _scan_due
                _sd = _scan_due(str(today), path=root / "data/intel/thesis_scan_state.json")
                # ≥3 months every day so the daily analysts have real recent depth
                # (early in a month the current partition alone is thin); 4 when the
                # weekly scan is due for a richer thematic tape. ~25MB, not the 264MB
                # history — the read-path cost the original 1-month design guarded.
                _npm = cloud.pull_news_recent(today, n_months=(4 if _sd else 3))
                print(f"   NEWS-TAPE  pulled {_npm} recent month(s) before the pulse "
                      f"(scan_due={_sd})")
            except Exception as exc:
                print(f"   NEWS-TAPE warn: {type(exc).__name__} (non-fatal)")
            try:
                from paper_trader.intel_pulse import run_intel_pulse
                _eq = float(client.get_account().get("equity", broker_cash)) or 1.0
                _held_w = {t: round(broker_positions.get(t, 0) * sleeve_closes[t] / _eq, 4)
                           for t in sleeve_closes} if sleeve_closes else {}
                _ip = run_intel_pulse(
                    str(today), portfolios={"sleeve": _held_w},
                    allowlist=list(SLEEVE_UNIVERSE), root=str(root),
                    now_iso=now_et().isoformat())
                print(f"   INTEL      {_ip.summary_line()}")
            except Exception as exc:
                print(f"   INTEL warn: {type(exc).__name__} (non-fatal, report-only)")
            # --- T-302 LLM shadow book: REPORT-ONLY virtual book of the analyst's
            # hypothetical actions vs a 60/40 twin (never touches orders/weights).
            # Gated on a note EXISTING → ships dormant-but-armed; wakes the day E's
            # first validated note lands. Fill = yesterday's note @ today's close
            # (signal-t/fill-t+1, no look-ahead); firewall re-enforced fail-closed. -- #
            _shadow_twin = None
            try:
                from paper_trader.llm_shadow_book import LlmShadowBook
                _lsb = LlmShadowBook(root=str(root))
                _note, _reason = _lsb._load_yesterday_note(str(today))
                _held = list(_lsb._state()["book"]["positions"].keys())
                if _note is None and not _held:
                    print("   LLM-SHADOW dormant (no analyst note yet — armed, waiting on first note)")
                else:
                    _syms = set(_held) | {"SPY", "AGG"} | {
                        a["symbol"] for a in (_note or {}).get("hypothetical_actions", [])
                        if a.get("account") == "shadow"}
                    _closes = None
                    try:
                        _raw = client.fetch_daily_closes(sorted(_syms))
                        _closes = {s: float(v.iloc[-1]) for s, v in _raw.items() if len(v)}
                    except Exception:
                        _closes = None      # fail-closed → degraded (positions hold)
                    lsum = _lsb.record(str(today), closes=_closes, note=_note, note_reason=_reason)
                    _shadow_twin = {"book_nav": lsum.get("book_nav"), "twin_nav": lsum.get("twin_nav"),
                                    "n_days": lsum.get("n_days")}
                    print(f"   LLM-SHADOW n_days={lsum['n_days']} clean={lsum['n_clean']} "
                          f"book_nav={lsum['book_nav']} vs twin={lsum['twin_nav']} "
                          f"rejected={lsum['n_rejected']} (report-only analyst record)")
            except Exception as exc:
                print(f"   LLM-SHADOW warn: {type(exc).__name__} (non-fatal)")
            # --- T-308 EVAL HARNESS: resolve expired analyst + event-call predictions
            # against prices/Kalshi/FRED/calendar; append-only log + summary (skill,
            # calibration, g1_skill). REPORT-ONLY, fully fail-open (never blocks trading).
            # Consumes analyst notes + D's event_calls.jsonl (note-shaped, unchanged) +
            # the shadow-book twin for the directional G1 leg. -------------------------- #
            try:
                from intelligence.analyst import eval_harness as _eh

                def _price_fn(sym, _live=eval_price_series):
                    """T-331: prefer the LIVE PIT-trimmed series fetched this pulse;
                    fall back to the baked substrate for symbols outside the sleeve
                    universe. Without this every resolution fails closed forever on
                    the stale baked CSVs (the second broken clock)."""
                    s = _live.get(sym)
                    if s is not None and len(s):
                        return s
                    return _eh._disk_price(sym)

                _es = _eh.run(str(today), price_fn=_price_fn, directional=_shadow_twin)
                _g1 = _es.get("g1_skill", {}).get("vs_market_implied") or {}
                print(f"   EVAL resolved={_es.get('n_resolvable', 0)}/{_es.get('n_records', 0)} "
                      f"brier={_es.get('brier')} g1_vs_implied_ci_low={_g1.get('diff_ci_low')} "
                      f"clears={_g1.get('clears')} (report-only prediction ledger)")
            except Exception as exc:
                print(f"   EVAL warn: {type(exc).__name__} (non-fatal)")
            # --- T-344 DIGEST: the weekly performance digest as a FRIDAY pulse
            # step (docs/Core/digest_wiring_spec_t344.md — closing 'the surface
            # built to watch everything was the last unwatched clock').
            # REPORT-ONLY + FAIL-OPEN, exactly the T-308 eval contract. Runs LAST
            # in this branch: it reads the trackers/books/shadow state the steps
            # above just wrote. NO Monday catch-up — a digest is a weekly
            # snapshot; back-dating one would stamp Monday's state as Friday's
            # (the miss is made visible by C's artifact-derived census clock,
            # never repaired here). ------------------------------------------ #
            try:
                import datetime as _dt
                if _dt.date.fromisoformat(str(today)).weekday() == 4:   # Friday
                    from intelligence.analyst.performance_digest import generate
                    _dg = generate(_digest_streams(root), as_of=str(today))
                    print(f"   DIGEST     streams={_dg.get('streams')} "
                          f"ok={_dg.get('ok')} path={_dg.get('path')}"
                          + ("" if _dg.get("ok") else f" err={_dg.get('error')}"))
                    # Durability: the container cannot git-commit, so push the
                    # render to S3 under the account's own (already-granted)
                    # paper_state prefix — a digest that renders and evaporates
                    # is the failure class this step exists to close.
                    if _dg.get("ok") and cloud.cfg.enabled:
                        for _p in filter(None, (_dg.get("path"), _dg.get("archived"))):
                            _r = cloud._aws("s3", "cp", str(_p),
                                            f"{cloud.cfg.s3_root}/docs/{Path(_p).name}")
                            if getattr(_r, "returncode", 1) != 0:
                                print("   DIGEST     WARN s3 push failed "
                                      f"({Path(_p).name}) — render is container-local only",
                                      file=sys.stderr)
            except Exception as exc:
                print(f"   DIGEST warn: {type(exc).__name__} (non-fatal, report-only)")
        except Exception as exc:
            print(f"   TRACK warn: {type(exc).__name__} (non-fatal)")

    elif (args.strategy in ("offense_sso", "sleeve_btc", "llm_analyst")
          and sleeve_closes and family_state):
        # T-288 fleet Accounts 2/3 forward tracker + report-only execution gates
        # (shared helper; per-strategy tracker file; robo benchmark = SPY/AGG/GLD).
        try:
            equity = float(client.get_account().get("equity", broker_cash))
            robo_closes = {t: sleeve_closes[t] for t in ("SPY", "AGG", "GLD")
                           if t in sleeve_closes}
            tsum = _record_family_tracker(
                tracker_path=f"data/state/{family_state['tracker_file']}",
                plan=plan, closes_latest=sleeve_closes, equity=equity,
                sizing_equity=sizing_equity, broker_positions=broker_positions,
                staged=staged, arrival_px=arrival_px, arrival_ts=arrival_ts,
                summary=summary,
                canonical=canonical, root=root, robo_closes=robo_closes)
            eg = tsum.get("execution_gates", {})
            print(f"6. TRACK     {family_state['label']} forward: {tsum.get('status')} "
                  f"({tsum.get('n_days', tsum.get('sleeve', {}).get('n_days'))} pts)"
                  + (f" | exec-gate overall={eg.get('overall')}" if eg else ""))
            # Account 3 (sleeve_btc): the live IBIT-vs-BTC-USD basis is the T-272
            # construction check. T-307 threaded the BTC-USD leg (Alpaca crypto) into
            # Account 1's BtcShadowTracker, which now records IBIT + BTC-USD daily —
            # its forward_gates() basis line accrues a real number (≥30 clean days).
            # We still print Account-3's own IBIT leg here; the cross-account basis
            # reads off Account 1's shadow, never a fabricated number.
            if args.strategy == "sleeve_btc":
                ibit_w = plan.targets.get("IBIT")
                print(f"   IBIT-BASIS  account-3 IBIT target_w={ibit_w} | "
                      f"divergence-vs-BTC-USD shadow = PENDING BTC-data thread "
                      f"(D panel) — report-only")
        except Exception as exc:
            print(f"   TRACK warn: {type(exc).__name__} (non-fatal)")

    # --- T-288 econ-health: the economic/behavioral tripwires the dead-man's-
    # switch can't see (no-trade-in-N-days, stale bars, orphan holdings). RUNS
    # BEFORE the push so the econ_health status block persists this run (the
    # heartbeat json is in DURABLE_PATHS). REPORT-ONLY + fully fail-open: it must
    # NEVER touch `canonical` (an economically-stale day is investigate-signal,
    # not an operational failure) — the whole block is try/excepted so it can't
    # raise into the trading path. A trip fires the heartbeat's separate loud
    # notify channel so silent economic drift can't hide behind a green light. -- #
    try:
        import datetime as _dt
        from paper_trader.econ_health import evaluate_econ_health
        managed_universe = list(plan.targets.keys()) if plan is not None else None
        last_trade_date = max(
            (_dt.date.fromisoformat(o.trade_date) for o in om.orders.values()),
            default=None)
        # exact (start, end] trading-day count, calendar-backed (holiday-aware).
        def _td_count(a, b):
            return sum(1 for n in range(1, (b - a).days + 1)
                       if cal.is_trading_day(a + _dt.timedelta(n)))
        report = evaluate_econ_health(
            today=today, managed_universe=managed_universe,
            broker_positions=broker_positions, last_trade_date=last_trade_date,
            latest_bar_date=latest_bar_date, trading_day_counter=_td_count)
        hb.record_econ_health(report)
        print(f"9. ECON-HEALTH {report.summary_line()}")
    except Exception as exc:
        # Fail-open: an econ-health miss must never touch the trading exit code.
        print(f"9. ECON-HEALTH WARN {type(exc).__name__} (non-fatal, report-only)",
              file=sys.stderr)

    # --- T-301 / P2.1 exec-cost ledger: append THIS run's proven-fresh fills
    # (per account, per instrument) to the append-only ledger + surface the
    # per-instrument aggregate in the heartbeat. Runs BEFORE the push so the
    # ledger + its status block persist this run (both are in DURABLE_PATHS).
    # Uses the SAME extract_fresh_fills gate as gate-b (no divergence), inherits
    # the no-fabricated-samples doctrine, and is REPORT-ONLY (never flips
    # canonical). Fully fail-open — the whole block is try/excepted. ---------- #
    try:
        from paper_trader.exec_cost_ledger import ExecCostLedger, extract_fresh_fills
        acct_label = os.getenv("ARCHONDEX_PAPER_ACCOUNT", "account-1")
        rows, _stale = extract_fresh_fills(staged, arrival_px, arrival_ts,
                                           account=acct_label, trade_date=str(today))
        ecl = ExecCostLedger("data/state/exec_cost_ledger.jsonl", root=str(root))
        n_appended = ecl.append(rows)
        agg = ecl.aggregate()
        hb.record_exec_cost_ledger(agg)
        print(f"10. EXEC-COST +{n_appended} fill(s) → ledger "
              f"({agg['n_rows']} rows, {agg['n_instruments']} instruments)"
              + "".join(
                  f" | {v['instrument']}@{v['account']} med={v['median_slippage_bps']}bps n={v['n']}"
                  for v in agg["per_instrument"].values()))
    except Exception as exc:
        print(f"10. EXEC-COST WARN {type(exc).__name__} (non-fatal, report-only)",
              file=sys.stderr)

    # PUSH BEFORE emitting metrics: a durable-state push that silently failed
    # means the NEXT run starts from stale state and a held position reads as
    # unexplained. That is an integrity failure, so it must flip canonical (→
    # non-zero exit → Batch FAILED → alarm), never a cheerful "pushed=True".
    # (T-288: the fleet's first armed runs lost their ledger/journal/tracker to
    # an IAM prefix denial while this line printed cfg.enabled, not the result.)
    pushed = cloud.push()
    if cloud.cfg.enabled and not pushed:
        print("FATAL: durable-state push FAILED — the next run would resume from "
              "STALE state (held positions would read as unexplained). Marking "
              "NON-CANONICAL so the dead-man's-switch fires.", file=sys.stderr)
        canonical = False
    cloud.emit_metrics(happened=True, canonical=canonical)
    print(f"5. STATE     pushed-to-s3={pushed} | "
          f"metrics: PaperRunHappened=1 PaperRunCanonical={int(canonical)}")

    # --- T-290 d1: POST-reconcile alt-data + positioning archiving. Runs
    # LAST, AFTER every reconcile/tracking/state-push, and is FAIL-OPEN: the
    # whole block is try/excepted so a network hiccup, a changed endpoint, or a
    # broken archiver can NEVER raise into the trading path or change the run's
    # canonical verdict (alt-data is not load-bearing for orders). A zero-
    # snapshot day — which the parquet dedup would otherwise hide on disk —
    # flags LOUDLY via the heartbeat's separate alt-data channel. The hoard is
    # persisted under the distinct S3 ``altdata/`` prefix. ------------------- #
    try:
        from paper_trader.altdata_archive import run_altdata_archive
        cloud.pull_altdata()                    # history down → dedup accrues
        ar = run_altdata_archive(str(root))
        for line in ar.reports:
            print(f"7. ALTDATA   {line}")
        # T-325 (2026-08-05): push BEFORE recording, and fold a failed push into the
        # degraded flag (altdata/ had the same missing-grant silent-push failure as
        # news_panel/). record_altdata was previously called before the push, so a
        # push failure could never reach the heartbeat.
        altdata_pushed = cloud.push_altdata()   # durable under altdata/ prefix
        _ad_degraded = ar.degraded or (not altdata_pushed)
        _ad_reason = (ar.reason if altdata_pushed else
                      (f"{ar.reason} | " if ar.reason else "")
                      + "s3_push_failed: altdata hoard did NOT persist to S3")
        hb.record_altdata(degraded=_ad_degraded, reason=_ad_reason,
                          fresh_rows=ar.fresh_rows)
        print(f"7. ALTDATA   degraded={_ad_degraded} pushed={altdata_pushed} | {_ad_reason}")
    except Exception as exc:
        # Fail-open: even the orchestrator dying must not touch the trading
        # exit code. Record the miss loudly so it isn't silent.
        print(f"7. ALTDATA   WARN orchestrator failed ({type(exc).__name__}: "
              f"{exc}) — fail-open, trading unaffected", file=sys.stderr)
        try:
            hb.record_altdata(degraded=True,
                              reason=f"archiver orchestrator raised: {type(exc).__name__}",
                              fresh_rows={})
        except Exception:
            pass

    # --- T-290b: POST-reconcile news-panel forward append (D's T-289). Same
    # fail-open contract as the alt-data block — runs LAST, wrapped so nothing
    # here can touch the trading exit code. Touches ONLY the current month's
    # partition (pull it so the within-month idempotent upsert accumulates,
    # append today, push it) — NOT the ~264 MB history. ``append_today`` is
    # itself fail-open (returns degraded=True, never raises); the degraded flag
    # is recorded for measurement gates (which treat it as a FAIL) but never
    # flips the trading verdict. This is the forward-accrual clock — every
    # un-wired day is a day of news lost from the S3 record. --------------- #
    try:
        from intelligence import news_panel
        from scripts.build_news_panel_t289 import full_universe, SPECIAL_SITS
        cloud.pull_news_month(today)            # current month only (small)
        run_id = f"pulse_{today.isoformat()}"
        # T-290c: guard the SILENT universe collapse. full_universe() falls back
        # to just the ~10 hardcoded SPECIAL_SITS (nearly all delisted: SIVB/FRC/
        # TWTR/BBBY/ATVI…) when data/universe/sp500_membership_pit.parquet is
        # absent from the image — yielding n_new=0 EVERY day while degraded reads
        # False (looks like a benign quiet day; is actually a dead forward clock).
        # Proven: the special-sits-only universe returns 0 articles on a busy
        # market day. Flag it LOUD via append_today's degraded_reason so a missing
        # panel universe can't masquerade as "no news today."
        universe = full_universe()
        degraded_reason = _news_universe_collapse_reason(universe, SPECIAL_SITS)
        nres = news_panel.append_today(today, universe, run_id,
                                       degraded_reason=degraded_reason)
        # T-325 (2026-08-05): the push now RETURNS a bool. A failed push (e.g. the
        # missing news_panel/* grant that lost the panel silently for weeks) MUST
        # degrade the heartbeat's news channel — a lost news day can never again be
        # a log-only WARN (the append can look perfect while nothing lands in S3).
        news_pushed = cloud.push_news_month(today)   # push current month only
        if not news_pushed:
            nres = dict(nres)
            nres["degraded"] = True
            nres["reason"] = ((f"{nres.get('reason')} | " if nres.get("reason") else "")
                              + "s3_push_failed: news panel did NOT persist to S3 "
                                "(the forward tape cannot accrue)")
        hb.record_news(nres)
        print(f"8. NEWS      append_today n_new={nres.get('n_new')} "
              f"n_total={nres.get('n_total')} degraded={nres.get('degraded')} "
              f"pushed={news_pushed} | {nres.get('reason')}")
    except Exception as exc:
        # Fail-open: even importing D's module failing must not touch trading.
        print(f"8. NEWS      WARN append failed ({type(exc).__name__}: {exc}) "
              f"— fail-open, trading unaffected", file=sys.stderr)
        try:
            hb.record_news({"n_new": 0, "n_total": 0, "degraded": True,
                            "reason": f"news append raised: {type(exc).__name__}"})
        except Exception:
            pass

    # --- T-338 CLOCK CENSUS + T-342 CHANNEL LIVENESS — at the TRUE tail (T-329d3).
    # The census asserts every forward-accruing record ACTUALLY ADVANCED today,
    # verified from the ARTIFACT never the config; fail-closed (unreadable = MISS);
    # read-only. It originally ran before the intel pulse / shadow book / news
    # append, so five clocks measured state their producing steps had not yet
    # written and false-MISSED every day — the cry-wolf shape that gets a census
    # tuned away (caught by its own first in-cloud emission, 2026-08-26). Account-1
    # only: the fleet accounts' records are gated in their own containers (see the
    # per-clock exemptions in clock_census.py). ------------------------------- #
    if args.strategy == "trend_sleeve":
        try:
            from paper_trader.clock_census import (census_line, channel_liveness,
                                                   liveness_line, run_census)
            _cc = run_census(root=str(root), as_of=str(today))
            print(f"9. CENSUS    {census_line(_cc)}")
            hb.record_clock_census(_cc)
            # T-342: the census asks whether clocks ADVANCED; this asks whether the
            # fields they CONSUME have ever been non-empty. The shadow book ran 17
            # honest days over a structurally empty channel — only this sees that.
            _lv = channel_liveness(root=str(root))
            print(f"   {liveness_line(_lv)}")
            hb.record_channel_liveness(_lv)
        except Exception as exc:
            # even the census failing must be LOUD — a silent census is the disease
            print(f"   [CLOCK-CENSUS][ALERT] census itself failed: {type(exc).__name__} "
                  f"— clocks UNVERIFIED today")

    # --- Tail heartbeat re-sync (T-329d3). The main durable push (step 5) sealed
    # the day's canonical verdict, but steps 7 (altdata), 8 (news), and the census
    # above all mutate the heartbeat AFTER it — without this second push their
    # records (including, ironically, step 8's s3_push_failed degraded flag from
    # the T-325 loud-push fix) never left the container: the S3 heartbeat carried
    # no news block at all. Best-effort and NEVER touches canonical — the verdict
    # is sealed; a failure here is loud but only delays these blocks one day. --- #
    try:
        if not cloud.push():
            print("   TAIL-PUSH  WARN: heartbeat tail re-sync failed — census/news "
                  "blocks reach S3 on the next run's push", file=sys.stderr)
    except Exception as exc:
        print(f"   TAIL-PUSH  WARN: {type(exc).__name__} (non-fatal)", file=sys.stderr)

    if not canonical:
        print("RESULT: NON-CANONICAL — exiting non-zero so the job is marked "
              "FAILED and the alarm fires.", file=sys.stderr)
        return 70
    print("RESULT: canonical/alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
