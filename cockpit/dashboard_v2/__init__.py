"""
Trading Machine Cockpit v2 — modular Dash app.

Run it via:
    python -m cockpit.dashboard_v2.app
or:
    python cockpit_dashboard_v2.py

Note: This version is isolated from cockpit/dashboard.py
so you can switch between v1 and v2 without conflicts.

The app module is imported LAZILY (PEP 562; 2026-11-04). `python -m cockpit.dashboard_v2.app`
imports this package BEFORE it runs app.py as __main__, and the eager `from .app import ...`
that used to live here pulled in every callback module — several read the Alpaca keys at
module level — before the entry's own .env load could run, so the keys never reached them. It
also made importing any tab module (the test suite's path) import the whole app.
`from cockpit.dashboard_v2 import run_dashboard, create_dash_app` still works.
"""
__all__ = ["run_dashboard", "create_dash_app"]


def __getattr__(name: str):
    if name in __all__:
        from . import app
        return getattr(app, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
