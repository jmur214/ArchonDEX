# UX Engineer Memory

- [dashboard_v2 idiom](project_dashboard_v2_idiom.md) — 3-layer split, 4 app.py edits per tab, post-redesign 8-tab nav (tab-home default, Execution parent), theme-first + banner-slot app.py additions, headless curl-per-tab smoke.
- [Pulse-gate short-circuit](pulse_gate_short_circuit_patterns.md) — PulseGate no_update on unchanged mtime token (28B vs 1.2MB/tick), blank-page race (mount triggers ALWAYS render), Dash 200/28B envelope not 204, single-source CURRENT-tier, _wse_compat archived.
- [Home tab WS-C patterns](home_tab_ws_c_patterns.md) — frozen-API parallel builds + stub harness, demo-layer Resolved consumption, dual curve-key vocab, callback-rendered card-title badges.
- [Visible-gaps degrade patterns](feedback_visible_gaps_over_blank.md) — "silent gaps must be VISIBLE": pending-state UI, census banner, doc-mirror scorecard, paper-data realities + lru_cache-by-mtime for slow bootstraps.
- [Record-tab static-file patterns](record_tabs_static_file_patterns.md) — git-tracked-missing vs pending framing, drift/STALE badge (status-from-file + auto-clear), doc-mirror constants, ledger pipe-table parsing, filter_query quoting.
- [UI never mutates machine state](feedback_ui_never_mutates_machine_state.md) — no UI-written files shadowing data/paper_state/; Command Center = argparse-verified whitelist, no order-arming commands.
- [Ops tab WS1 patterns](project_ops_tab_ws1_patterns.md) — semantic accents, production-writer fixtures, splice honesty, wide pulse tuple (13 post-WS-E), manual-only AWS buttons, te=null/gate-b no-data handling.
- [WS-E Execution parent + restyle](redesign_ws_parallel_build_patterns.md) — guarded-import bridge for unlanded sibling APIs, demo nav-key contract (fixture keys ≠ tracker keys), reactive DEMO badge slots, pending-clock gates.
- [Theme system WS-A](project_theme_system_ws_a.md) — archon_dark register-on-import, components.py contract, CSS token/class inventory, footguns removed, `.venv/bin/python -m pytest` (not the pytest shim).
- [Demo layer WS-B](demo_layer_ws_b_patterns.md) — resolver-above-loader auto-switch, two-gate fail-closed fixture generator, T-255 audit MIXES end-dates (gold-blind tail; common-window finals differ), meta-only demo KPIs.
- [WS-D secondary restyle patterns](ws_d_secondary_restyle_patterns.md) — DataTable-on-theme wrapping, demo renderer takes Resolved param + dual DEMO markers, derived-highlight attribution, premise-keyed conditional tests.
