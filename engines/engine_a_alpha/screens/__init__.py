"""Cross-sectional defensive screens/signals (Phase 1 beta-engineering).

These are COMPOSABLE signals — they produce per-ticker scores / exclusion
sets and are NOT wired into Engine-B admission or sizing (that application
is propose-first). They ARE imported by the Engine-C phase-1 composition
post-processor (engine_c_portfolio/phase1_composition.py:88-96), but only
behind phase1_composition_enabled (default False) — so prod canon is
unchanged. DORMANT (flag-gated default-OFF), not unreachable.
"""
