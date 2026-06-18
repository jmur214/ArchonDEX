"""Cross-sectional defensive screens/signals (Phase 1 beta-engineering).

These are COMPOSABLE signals — they produce per-ticker scores / exclusion
sets and are NOT wired into Engine-B admission or sizing (that application
is propose-first). Default-OFF by construction: nothing in the production
backtest path imports or calls them, so prod canon is unchanged.
"""
