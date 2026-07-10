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
                         client, om, cfg, today, broker_positions, cap):
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
    staged = [om.stage(str(today), s.ticker, s.side, s.qty,
                       s.stage_args()["tif"], cfg.config_hash())
              for s in plan.orders]
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
    ap.add_argument("--strategy",
                    choices=["reconcile_only", "trend_sleeve", "offense_sso", "sleeve_btc"],
                    default="reconcile_only",
                    help="reconcile_only = the daily pulse (no orders, the proven "
                         "default); trend_sleeve = the T-238 defensive sleeve "
                         "(Account 1, LIVE); offense_sso = the T-284 gated-2× SSO "
                         "offense (Account 2); sleeve_btc = the T-272 sleeve+IBIT "
                         "(Account 3) — the T-288 fleet, one account per jobdef. "
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

    elif args.strategy in ("offense_sso", "sleeve_btc"):
        # T-288 fleet Accounts 2/3 — the sleeve-FAMILY shared pipeline. The live
        # account-1 (trend_sleeve) block above stays inline + untouched.
        sleeve_tif = os.getenv("ARCHONDEX_SLEEVE_TIF", "day").lower()
        if sleeve_tif not in ("day", "opg"):
            print(f"FATAL: [NN-FAIL-CLOSED] invalid ARCHONDEX_SLEEVE_TIF="
                  f"{sleeve_tif!r} (want day|opg).", file=sys.stderr)
            cloud.emit_metrics(happened=True, canonical=False); cloud.push()
            return 69
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
                    cap=args.sleeve_notional_cap)
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
              f"{[(o.ticker, o.side, o.qty) for o in plan.orders]}")

    summary = sched.run_trading_day(str(today), staged, inputs_fn,
                                    account_explained=account_explained)

    # --- 3. heartbeat verdict → metrics + exit code ------------------- #
    v = hb.check(today, is_trading_day=True)
    canonical = bool(v.alive and not v.alert)
    print(f"3. CYCLE     reconcile {summary.reconcile_clean_cycles}/"
          f"{summary.reconcile_total_cycles} clean | halted={summary.halted}")
    print(f"4. HEARTBEAT alive={v.alive} alert={v.alert} | {v.reason}")

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
            # sleeve daily return from the last two tracked equities + adds a
            # trend-ruled BTC leg. Fetches BTC/IBIT fail-closed — DEGRADED (leg
            # parked in cash) when the lean image lacks yfinance/network, until
            # BTC data is threaded (safe per the T-276 spec). ------------------ #
            try:
                from paper_trader.btc_shadow import BtcShadowTracker
                from paper_trader.sleeve_tracker import RF_ANNUAL
                _prev = [p for p in tracker._load() if p["date"] < str(today)]
                _sleeve_ret = (equity / _prev[-1]["sleeve_equity"] - 1.0) if _prev else 0.0
                bsum = BtcShadowTracker(root=str(root)).record(
                    str(today), _sleeve_ret, cash_daily_rate=RF_ANNUAL / 252.0)
                print(f"   BTC-SHADOW n_days={bsum.get('n_days')} "
                      f"clean={bsum.get('n_clean')} degraded={bsum.get('n_degraded')} "
                      f"(report-only T-272 forward validation)")
            except Exception as exc:
                print(f"   BTC-SHADOW warn: {type(exc).__name__} (non-fatal)")
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
                _es = _eh.run(str(today), directional=_shadow_twin)
                _g1 = _es.get("g1_skill", {}).get("vs_market_implied") or {}
                print(f"   EVAL resolved={_es.get('n_resolvable', 0)}/{_es.get('n_records', 0)} "
                      f"brier={_es.get('brier')} g1_vs_implied_ci_low={_g1.get('diff_ci_low')} "
                      f"clears={_g1.get('clears')} (report-only prediction ledger)")
            except Exception as exc:
                print(f"   EVAL warn: {type(exc).__name__} (non-fatal)")
        except Exception as exc:
            print(f"   TRACK warn: {type(exc).__name__} (non-fatal)")

    elif args.strategy in ("offense_sso", "sleeve_btc") and sleeve_closes and family_state:
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
            # construction check. The BTC-USD leg lives in Account 1's degraded
            # BtcShadowTracker until BTC data threads (D's panel); until then we
            # report the account's own IBIT leg + flag the divergence as PENDING
            # that data — never a fabricated basis number.
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
        hb.record_altdata(degraded=ar.degraded, reason=ar.reason,
                          fresh_rows=ar.fresh_rows)
        cloud.push_altdata()                    # durable under altdata/ prefix
        print(f"7. ALTDATA   degraded={ar.degraded} | {ar.reason}")
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
        cloud.push_news_month(today)            # push current month only
        hb.record_news(nres)
        print(f"8. NEWS      append_today n_new={nres.get('n_new')} "
              f"n_total={nres.get('n_total')} degraded={nres.get('degraded')} "
              f"| {nres.get('reason')}")
    except Exception as exc:
        # Fail-open: even importing D's module failing must not touch trading.
        print(f"8. NEWS      WARN append failed ({type(exc).__name__}: {exc}) "
              f"— fail-open, trading unaffected", file=sys.stderr)
        try:
            hb.record_news({"n_new": 0, "n_total": 0, "degraded": True,
                            "reason": f"news append raised: {type(exc).__name__}"})
        except Exception:
            pass

    if not canonical:
        print("RESULT: NON-CANONICAL — exiting non-zero so the job is marked "
              "FAILED and the alarm fires.", file=sys.stderr)
        return 70
    print("RESULT: canonical/alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
