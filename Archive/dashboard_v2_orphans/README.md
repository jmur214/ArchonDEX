# Archive/dashboard_v2_orphans — retired dashboard_v2 modules (2026-07-03)

Archived per `[NN-ARCHIVE]` (archive, never delete). Verified imported/registered
nowhere before the move (grep over cockpit/, tests/, scripts/).

- `analytics_callbacks.py` + `analytics_tab.py` — pre-redesign orphans: never
  imported by app.py nor any navigation callback (the "Analytics" surface was
  rebuilt as `tabs/analytics_parent_tab.py` + `analytics_navigation_callbacks.py`).
- `_wse_compat.py` — the WS-E parallel-build bridge (import fallbacks for the
  frozen WS-A/WS-B APIs). Dead once `components.py`/`theme.py`/`demo_provider.py`
  landed; its duplicated demo auto-switch/honesty logic was a drift risk, so all
  `try/except ImportError` call sites now import the real modules directly.
