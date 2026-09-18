---
name: pulse-gate-short-circuit
description: PulseGate no_update short-circuit for wide pulse callbacks — blank-page race, Dash 200/28B envelope (not 204), wire-verification method, review-fix patterns (2026-07-03)
metadata:
  type: project
---

2026-07-03 review-fix wave on dashboard_v2 (10 issues). Patterns that worked:

**PulseGate short-circuit** (`utils/refresh_gate.py` + `home_pulse_token()`/`ops_pulse_token()` in the callbacks): wide pulse callbacks (Home 14 outputs ~1.22MB JSON, Ops 13 ~1.16MB per 2s tick) now return `no_update` for all outputs when a cheap mtime_ns token over EVERY source file (+ calendar day + tabs value) is unchanged AND `ctx.triggered_id == "pulse"`.
- **THE BLANK-PAGE RACE:** a callback also re-fires when its outputs are (re-)mounted (tab switch swaps `tab-content` children) with `triggered_id` None — those calls MUST always render or freshly mounted shells stay empty forever. Never short-circuit on token alone; discriminate on the trigger. Verified over the wire: tabs-trigger with an unchanged token still ships the full 1.2MB.
- **Dash all-no_update multi-output response is HTTP 200 with a 28-byte `{"multi":true,"response":{}}` envelope, NOT 204.** Assert on body size/emptiness, not status.
- Adding `Input("tabs","value")` also makes off-tab pulses ~free (the old code rebuilt Home every 2s even when Home wasn't shown).
- Token must include EVERY file the view reads (tracker, heartbeat, TR CSVs, demo fixtures, BTC state, sits parquet/jsonl, advisor json+schema, T-279 audit existence, ledger) + `date.today()` for rolling live-window/STALE flags. Read paths from their owning modules at CALL time so monkeypatches are honored.
- **Wire verification:** POST `/_dash-update-component` with the callback's `output` string from `/_dash-dependencies`, `changedPropIds: ["pulse.n_intervals"]`, bumping n. Gate state persists per server process — a "first" tick in a second test script may already be cached from an earlier script.

**Other patterns from the wave:**
- `components.sparkline_figure()` split out of `sparkline()` — callbacks whose Output is a declared `dcc.Graph`'s `figure` prop can't consume a component-returning helper; give them the bare-figure builder and keep the component wrapper for layout-time use.
- Pending-card taxonomy inside a demo strip: the provider marks real pending-clock cards (`{"pending": True}` on the card dict, e.g. "Days tracked: 0 — starts at go-live"); the renderer gives them `.kpi.pending` amber style and suppresses the DEMO badge (`demo=is_demo and not pending`). CSS `.kpi.pending` border/value rules added.
- Callback-injected components must be id-LESS (intel `render_btc_demo_section` Graph) — an id on a sometimes-absent component invites a future callback to bind to it.
- CURRENT-tier highlight single-sourced in `record_loader.derive_current_tier_ids(table, load_live_account_equity())` (validated+covered → equity-band disambiguation → honest () when ambiguous pre-go-live). Both advisor_callbacks and home_callbacks consume it; the hardcoded row-id constant is gone.
- websocket_manager state machine: missing alpaca-py = permanent `unavailable` (ONE log line ever, `start_if_needed` returns None); `_run_loop` finally-resets `running=False` so a died thread reads honestly; one retry per `RETRY_COOLDOWN_S=300`. Test by monkeypatching `AlpacaStreamManager._main` with an async no-op (NOT `_run_loop` — that bypasses the finally-reset).
- `_wse_compat.py` bridge + pre-redesign orphans (`analytics_callbacks.py`, `analytics_tab.py`) archived to `Archive/dashboard_v2_orphans/` with README; all try/except-ImportError call sites now import components/theme/demo_provider directly. Bridge tests repointed at the production demo_provider via `monkeypatch.setattr(dp, "FIXTURES_DIR", tmp_path)` + `dp.clear_caches()`; the meta-only KPI demo branch needs the full meta keys (maxdd_pct/finals_per_10k/sortino/sortino_ci_low).
- `any_demo_active()` must include EVERY resolver with an independent demo branch (curves + BTC + KPIs) or the global banner can be absent while demo data shows.
- Stale nav copy: "the Operations tab" no longer exists — grep-clean to "Home / Execution → Sleeve Ops" (tests assert the copy; `test_exec_nav_routes` relies on the literal H3 "Operations" in ops_layout, which is a page title, not a nav pointer — left as-is).

Related: [[dashboard-v2-idiom]], [[ops-tab-ws1-patterns]], [[demo-layer-ws-b]].
