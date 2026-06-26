# Trend-Sleeve Paper Validation — PROPOSAL (T-238, 2026-06-26)

**PROPOSE-FIRST / paper-live-adjacent. NOTHING enabled or built here** — this
is the wiring + forward-tracking + go-live plan for the director/user to
approve. The user greenlit paper validation after T-236 (the trend sleeve is
the first strategy to clear the full gauntlet on the tail yardstick). Engine-E
lane (I own the paper machine + the sleeve). `[NN-FAIL-CLOSED]`.

## What we are validating (and the honest frame — carry it to the user)
The 3-asset **trend sleeve** (EW SPY/AGG/GLD, long-flat 5-month absolute
momentum, cash off-leg — the pre-registered T-204 config, NO new sweep).
T-236 verdict: it clears the deploy gate vs both robos on the **defensive
yardstick** — Sortino 1.085 (ci_low 0.536), **MaxDD −12.2% vs 60_40 −36.7% /
schwab_like −27.2%, shallower in EVERY crisis incl dotcom (−7.5%)** — but it is
a **risk-return TRADE, not free alpha**: ~1%/yr LESS terminal wealth ($18K vs
$22K Roth over the cycle); its edge over schwab_like is **drawdown depth**, not
return; **Roth-only** (high turnover → taxable-hostile). **The paper run's job
is to confirm the drawdown edge holds FORWARD on REAL ETF fills** — closing the
T-236 index/synthetic-substrate gap (synthetic-treasury-TR & GC=F vs real AGG &
GLD; real slippage & whole-share rounding).

## Part 1 — Wire the sleeve into the paper machine (propose to BUILD on approval)
The cloud loop (`run_paper_cloud_day.py`, T-185/186/198) is today **reconcile-
only**: it polls/adopts broker truth (T-198), records the heartbeat (T-185),
and passes **`[]`** staged orders (line ~170, "the engine-driven order set is
the separate content layer"). The sleeve IS that content layer — and it is far
simpler than the equity book (3 liquid ETFs, a daily long/flat signal, no
A→C→B pipeline).

**Proposed new module `paper_trader/sleeve_constructor.py`** (pure, OFF until
wired; reuses `core/trend_overlay.py` — forks nothing):
```
SleeveОrderConstructor(universe=[SPY,AGG,GLD], lookback=105, off_leg=cash)
  daily, given (account_equity, current_broker_positions, price_history):
    1. signal_i = TrendOverlay(105).exposure(close_i)  # as-of yesterday's close (causal)
    2. target_w_i = (1/3) * signal_{i,t-1}             # off → 0 (cash); EW of the 3
    3. target_$_i = account_equity * target_w_i
       target_qty_i = floor(target_$_i / last_price_i) # whole shares (ETFs)
    4. delta_i = target_qty_i − current_qty_i
    5. emit auction orders for nonzero deltas (TIF = CLS rebalance at the close,
       or OPG at the open) via OrderManager.stage(...)
  → returns the staged-order list that replaces `[]` in run_trading_day(...)
```
**Turnover control (reuse T-148 Carver buffering):** only trade when a signal
FLIPS or |target_w − held_w| exceeds a deadband (propose 0.10) — avoids daily
churn + tiny auction orders. Pre-register the band; it does not change the
strategy, only suppresses no-op rebalances.

**Reused, unchanged:** the order-state machine + auction TIF (T-160/163), the
held-position reconcile/adopt (T-198 — already converges the ledger to the
held sleeve each morning), the dead-man's-switch (T-185, 3-channel), the
durable S3 state (T-186), the calendar/window gate (T-185), the expire-window
fix (T-201/202, jobdef rev 5).

**One genuinely-new dependency to flag — daily ETF price history in-loop.** The
signal needs ~210 trailing daily closes per asset. Propose the loop fetch
SPY/AGG/GLD daily bars from the Alpaca data API (already authenticated) each
run, cached to S3 with the rest of the durable state; `[NN-FAIL-CLOSED]` if a
bar is missing/stale (do NOT trade on a stale signal). (The stooq cache is the
offline fallback for backtests, not the live signal.)

## Part 2 — Forward-track vs BOTH robos (drawdown-LED, per the Sortino/tail directive)
Each trading day, after the cycle, record to the durable scorecard (extend
`docs/State/paper_run_scorecard.md` + a `data/state/sleeve_tracking.json`
pushed to S3 for C's dashboard):
- **paper sleeve equity** (broker account value) + daily return + running MaxDD.
- **robo proxies on the SAME dates** via `core/benchmark.py`: `60_40`
  (SPY/TLT 60/40) and `schwab_like` (its multi-asset blend) — computed from the
  same real ETF closes, so it is an apples-to-apples forward comparison.
- **Lead metric = MaxDD / drawdown** (the T-236 edge + the user's tail
  yardstick): does the sleeve's running MaxDD stay materially shallower than
  both robos' FORWARD? Then **Sortino, Calmar, per-crisis DD** (if a stress
  event occurs in-window), and **Roth money-EV** (terminal $ — to keep the
  ~1%/yr-less honest). Sharpe is secondary (per the 2026-06-25 directive).
- **The index-vs-ETF gap close:** the forward number is on REAL AGG (not
  synthetic treasury) + real GLD + real fills/slippage/rounding — if the −12%
  vs −27% edge survives that, it is the honest deployable read.

**Success criterion (propose to pre-register):** over a forward window of
**≥ 60 trading days AND ≥ 1 equity-stress episode (SPY −5%+ pullback)**, the
sleeve's forward MaxDD is materially shallower than both robos' AND its Sortino
ci_low ≥ schwab_like's — confirming the gauntlet edge is not a backtest
artifact. (A clean "the edge did NOT hold forward" is a valid, valuable
outcome — it keeps real money in the robo, honestly.)

## Part 3 — Go-live checklist (the user's open decisions; nothing here is auto-done)
| # | action | who | status |
|---|---|---|---|
| 1 | **Confirm the SNS alert email** — click the AWS confirmation link sent to `jsm13700@gmail.com` (subscribed in T-186-exec). Until confirmed, the dead-man's-switch alarms fire to SNS but reach no inbox. I CANNOT verify this programmatically (claude-code-cli lacks `SNS:ListSubscriptionsByTopic`) — **user must confirm in their inbox / SNS console.** | USER | PENDING |
| 2 | **Approve + I build** the `sleeve_constructor` wiring (Part 1) + the forward-tracking (Part 2), with unit tests + a manual cloud verify run that trades the sleeve correctly on the paper account (whole-share deltas, held-reconcile clean, heartbeat canonical). | director→E | awaiting approval |
| 3 | **Rebuild the lean image + re-register the jobdef + re-point the schedule** to the sleeve-wired image (the T-202 pattern; schedule STAYS disabled through this). | E | after #2 |
| 4 | **ENABLE the EventBridge schedule** (`archondex-paper-daily`, currently **DISABLED**, targets jobdef rev 5): `aws scheduler update-schedule --name archondex-paper-daily --state ENABLED …`. **The user's explicit go-live word** — only after #1-3 are clean. | USER/director | gated |
| 5 | Designate the paper strategy mode = `trend_sleeve` (a new `PaperConfig` mode; the sleeve does NOT use the equity-book allocator interlock). | E (in #2) | — |

## Part 4 — Boundaries / flags (propose-first honored)
- **Nothing enabled or built in this task** — proposal only.
- The sleeve order-construction is **Engine-E + paper_trader lane** (the sleeve
  is standalone — 3 ETFs, no equity-book composition), so E can wire it solo.
  **FLAG:** if the user later wants the sleeve COMBINED with the equity book
  into one paper portfolio, that is C's composition lane (propose-first then).
- **No Engine-B-risk dependency:** the sleeve is long/flat liquid ETFs sized to
  the account; it does not invoke the equity-book risk engine. Any real-money
  sizing/risk-cap change stays propose-first.
- PAPER endpoint only; the live-money boundary (paper-valid AND beats-robo)
  is unchanged. Roth-emulation account.

## Recommendation
**Approve Part 1+2 (build the sleeve wiring + forward-tracking, schedule stays
DISABLED).** It is the cleanest possible first live strategy (3 ETFs, validated
config), reuses the entire paper machine we already proved, and produces the
one number that decides real money: **does the −12%-vs-−27% drawdown edge hold
forward on real ETFs?** Go-live (#4) remains the user's explicit, gated word
after a clean manual verify.
