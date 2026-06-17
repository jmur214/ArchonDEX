# Paper persistence — the host-INDEPENDENT pieces (T-185)

**Date:** 2026-06-17 · **Branch:** `feature/paper-persistence-t185` ·
**Agent:** E (deployment) · **Endpoint:** Alpaca **PAPER** only (no
live-money path; creds by env-NAME only).

## The gap the director caught

The paper loop ran ONCE (T-169 Day 1) and then sat idle — nobody would
have noticed if it silently stopped. T-185 makes the run actually
persistent by building the pieces that are **host-independent** (work the
same whether the eventual trigger is a Mac launchd plist or an
EventBridge→Fargate job). The host-SPECIFIC trigger is deliberately NOT
built here — it awaits the director+user host decision.

## What shipped

### 1. Trading-calendar awareness — `paper_trader/market_calendar.py` (new)
- `MarketCalendar(client=None, holidays=None)`. `is_trading_day(d)` uses
  the broker calendar (`AlpacaPaperClient.trading_days` →
  `get_calendar`) as authoritative; on ANY broker failure it falls back
  to weekday + a hard-coded 2026 holiday set (incl. Juneteenth 6/19) and
  **never raises**.
- Auction-window predicates: `is_opg_window(now)` (7:00pm–9:28am ET,
  spans midnight), `is_cls_window(now)` (< 15:50 ET),
  `auction_window_open(tif, now)` routes by TIF (`day`/unrestricted →
  always open), `window_reason(...)` for the human-readable defer note.
  `now_et()` module fn centralizes the ET clock.

### 2. Auction-window gate (the T-169 finding, FIXED) — `scheduler.py`
- Before the armed `submit_opg`/`submit_cls` actually POSTs, a gate checks
  `calendar.auction_window_open(tif, now)`. Outside the window the batch
  is **DEFERRED — held STAGED, nothing submitted** (log note records
  why). This eliminates the Alpaca `code 40310000` outside-window reject
  by construction: orders wait for the window rather than bouncing.
- `run_trading_day(...)` is the calendar-aware entry: a non-trading day
  prints a skip and returns `None` with NO heartbeat (the dead-man's
  switch treats non-trading days as alive, so a skip must leave no
  would-be-non-canonical record).

### 3. Dead-man's-switch heartbeat — `paper_trader/heartbeat.py` (new)
- `PaperHeartbeat.record_run(...)` writes `data/state/paper_heartbeat.json`
  (schema `paper_heartbeat/v1`) — called in `run_day`'s `finally`, so
  even a crash leaves a trace. **Canonical** = reconcile clean
  (total>0 and clean==total) AND not halted AND `account_flat is not
  False` AND (when a perf-summary is supplied) `core.census.assert_census`
  passes — the SAME census helper Engine C uses, so the verdict can't
  diverge between paths.
- `check(today, is_trading_day)` is the switch: non-trading day → alive;
  no heartbeat ever → ALARM "never ran"; today + canonical → alive;
  today + non-canonical → ALARM; last_date < today on a trading day →
  ALARM "silently stopped".
- **Alert = three channels** so one silent failure can't swallow it:
  (1) a loud `[PAPER-HEARTBEAT][ALERT]` log line, (2) the status file's
  `alert`/`alert_reason` flag the dashboard reads, (3) a notification
  path (append-only `data/state/paper_alerts.log` + optional
  `PAPER_NOTIFY_WEBHOOK` POST, best-effort, never raises).

### 4. Reconcile-on-restart self-heal — PROVEN
`tests/test_paper_persistence_t185.py::TestReconcileOnRestart`:
- crash mid-cycle → restart from the journal → re-adopts broker truth
  (ACKED), a resume `submit()` makes **ZERO new POSTs** (idempotent
  `client_order_id` across restart), then polls to FILLED;
- crash after the SUBMITTED intent but before the POST landed (broker has
  no record → ABSENT) → restart reverts to STAGED, so the in-window
  cadence deliberately re-submits rather than blind-resubmitting.

## Verification

- `tests/test_paper_persistence_t185.py` — **27 passed** (calendar
  fallback/authority/window-parametrized, scheduler defer-vs-submit,
  trading-day skip, heartbeat clean/miss/non-canonical/never-ran/
  non-trading/census-fail, reconcile-on-restart ×2).
- Full paper suite (`-k paper`) — **165 passed, 1 skipped**, no
  regressions from the scheduler/`__init__` edits.
- **Day-2 live PAPER run** (`scripts/run_paper_day_t185.py --confirm
  --allocator mean_variance`, 2026-06-17 16:08 ET): trading day
  confirmed via Alpaca calendar; OPG **DEFERRED** (outside window);
  **3/3 reconcile cycles clean** vs live broker truth; account left
  FLAT; heartbeat **canonical / alive / alert=false**; status file
  written for the dashboard.

## Honest limits

- **No real fill yet.** The OPG window is 7pm–9:28am ET; the Day-2 run at
  16:08 ET correctly deferred. The first real fill (and the
  slippage-vs-T-146 line) lands the first time the loop runs `submit_opg`
  inside the window at a market open.
- **Host trigger NOT built.** The "fire once per trading day" trigger is
  host-bound (launchd vs EventBridge→Fargate) and awaits the
  director+user decision. The loop logic above is host-agnostic and
  ready to be driven by either.
- The offline holiday fallback is a 2026 set; the broker calendar is
  authoritative whenever reachable, so the fallback only bites in an
  offline window and degrades safe (it can only ADD a skip, never
  fire on a real holiday the broker would've flagged).
